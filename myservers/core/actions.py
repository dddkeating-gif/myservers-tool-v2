from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from myservers.connectors.host_select import choose_best_host
from myservers.connectors.exec_local import execute
from myservers.connectors.exec_ssh import execute_ssh, build_ssh_invocation_string
from myservers.core.identities_store import IdentitiesStore
from myservers.core.models import Server
from myservers.core.servers import ServerStore
from myservers.storage.sqlite_store import SqliteStore


MAX_TEXT = 50_000


@dataclass
class ActionTemplate:
    id: int
    name: str
    description: str | None
    command_template: str
    requires_confirm: bool
    execution_target: str  # 'local' or 'ssh'


@dataclass
class ActionRun:
    id: int
    action_id: int
    server_name: str
    started_at: str
    finished_at: str
    status: str
    exit_code: Optional[int]
    duration_ms: int
    command_rendered: str
    stdout: str
    stderr: str


class ActionsStore:
    """Actions (templates) and execution history."""

    def __init__(self, backend: SqliteStore, server_store: ServerStore) -> None:
        self._backend = backend
        self._conn = backend._conn
        self._servers = server_store
        self._idents = IdentitiesStore(backend)

    # ---------- actions ----------

    def list_actions(self) -> List[ActionTemplate]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT id, name, description, command_template, requires_confirm, execution_target FROM actions ORDER BY name"
        )
        return [
            ActionTemplate(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                command_template=row["command_template"],
                requires_confirm=bool(row["requires_confirm"]),
                execution_target=row["execution_target"] or "local",
            )
            for row in cur.fetchall()
        ]

    def create_action(
        self,
        name: str,
        description: str | None,
        command_template: str,
        requires_confirm: bool = True,
        execution_target: str = "local",
    ) -> int:
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO actions(name, description, command_template, requires_confirm, execution_target)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name.strip(), description, command_template, 1 if requires_confirm else 0, execution_target),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def update_action(
        self,
        action_id: int,
        name: str,
        description: str | None,
        command_template: str,
        requires_confirm: bool,
        execution_target: str,
    ) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            UPDATE actions
            SET name = ?, description = ?, command_template = ?, requires_confirm = ?, execution_target = ?
            WHERE id = ?
            """,
            (name.strip(), description, command_template, 1 if requires_confirm else 0, execution_target, action_id),
        )
        self._conn.commit()

    def delete_action(self, action_id: int) -> None:
        cur = self._conn.cursor()
        cur.execute("DELETE FROM actions WHERE id = ?", (action_id,))
        self._conn.commit()

    # ---------- runs ----------

    def run_action(self, action_id: int, server_name: str, *, dry_run: bool) -> ActionRun:
        """Render and optionally execute an action on a server."""
        cur = self._conn.cursor()
        cur.execute(
            "SELECT id, name, description, command_template, requires_confirm, COALESCE(execution_target, 'local') as execution_target FROM actions WHERE id = ?",
            (action_id,),
        )
        arow = cur.fetchone()
        if arow is None:
            raise ValueError("Action not found")
        template = ActionTemplate(
            id=arow["id"],
            name=arow["name"],
            description=arow["description"],
            command_template=arow["command_template"],
            requires_confirm=bool(arow["requires_confirm"]),
            execution_target=arow["execution_target"],
        )

        server: Optional[Server] = self._servers.get_server(server_name)
        if server is None:
            raise ValueError("Server not found")

        # server_id for history FK
        cur.execute("SELECT id FROM servers WHERE name = ?", (server_name.strip(),))
        srow = cur.fetchone()
        if srow is None:
            raise ValueError("Server row not found")
        server_id = srow["id"]

        # Build context (no secrets)
        host = choose_best_host(server) or ""
        ssh_profile = self._idents.get_ssh_profile(server_name)
        ssh_port = ssh_profile.port if ssh_profile else 22

        ctx = {
            "server.name": server.name,
            "host": host,
            "hosts.internal_primary": server.hosts.internal_primary,
            "hosts.internal_secondary": server.hosts.internal_secondary,
            "hosts.external_primary": server.hosts.external_primary,
            "hosts.external_secondary": server.hosts.external_secondary,
            "ssh.port": str(ssh_port),
        }

        command_rendered = _render_template(template.command_template, ctx)

        started = datetime.now(timezone.utc)
        if dry_run:
            status = "dry_run"
            exit_code = None
            duration_ms = 0
            stdout = ""
            stderr = ""
        elif template.execution_target == "ssh":
            host = choose_best_host(server)
            if not host:
                raise ValueError("No host available for SSH execution")
            ssh_profile = self._idents.get_ssh_profile(server_name)
            identity = None
            if ssh_profile and ssh_profile.identity_id:
                identity = self._idents.get_identity(ssh_profile.identity_id)
            ec, out, err, duration_ms = execute_ssh(server, ssh_profile, identity, command_rendered)
            status = "success" if ec == 0 else "error"
            exit_code = ec
            stdout = out or ""
            stderr = err or ""
        else:
            ec, out, err, duration_ms = execute(command_rendered)
            status = "success" if ec == 0 else "error"
            exit_code = ec
            stdout = out or ""
            stderr = err or ""

        finished = datetime.now(timezone.utc)
        run_id = self._insert_run(
            action_id=template.id,
            server_id=server_id,
            server_name=server.name,
            started_at=started.isoformat(),
            finished_at=finished.isoformat(),
            status=status,
            exit_code=exit_code,
            duration_ms=duration_ms,
            command_rendered=command_rendered,
            stdout=stdout,
            stderr=stderr,
        )

        return ActionRun(
            id=run_id,
            action_id=template.id,
            server_name=server.name,
            started_at=started.isoformat(),
            finished_at=finished.isoformat(),
            status=status,
            exit_code=exit_code,
            duration_ms=duration_ms,
            command_rendered=command_rendered,
            stdout=stdout[:MAX_TEXT],
            stderr=stderr[:MAX_TEXT],
        )

    def _insert_run(
        self,
        *,
        action_id: int,
        server_id: int,
        server_name: str,
        started_at: str,
        finished_at: str,
        status: str,
        exit_code: Optional[int],
        duration_ms: int,
        command_rendered: str,
        stdout: str,
        stderr: str,
    ) -> int:
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO action_runs(
                action_id,
                server_id,
                started_at,
                finished_at,
                status,
                exit_code,
                duration_ms,
                command_rendered,
                stdout,
                stderr
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action_id,
                server_id,
                started_at,
                finished_at,
                status,
                exit_code,
                duration_ms,
                (command_rendered or "")[:MAX_TEXT],
                (stdout or "")[:MAX_TEXT],
                (stderr or "")[:MAX_TEXT],
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)


def _render_template(template: str, ctx: dict[str, str]) -> str:
    """Very small template renderer for {{var}} placeholders."""
    result = template
    for key, value in ctx.items():
        placeholder = "{{" + key + "}}"
        result = result.replace(placeholder, value)
    return result

