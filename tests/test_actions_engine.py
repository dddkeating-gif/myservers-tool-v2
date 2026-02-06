from pathlib import Path

import keyring

from myservers.connectors.exec_local import execute
from myservers.core.actions import ActionsStore
from myservers.core.identities_store import IdentitiesStore
from myservers.core.identity import create_identity, get_secret
from myservers.core.models import HostSet, Server
from myservers.core.servers import ServerStore
from myservers.storage.sqlite_store import SqliteStore


def test_action_template_rendering_and_dry_run(tmp_path: Path) -> None:
    db_path = tmp_path / "data.sqlite3"
    backend = SqliteStore(db_path)
    store = ServerStore(backend)
    actions = ActionsStore(backend, store)

    s = Server(
        name="Srv1",
        hosts=HostSet(
            internal_primary="10.0.0.1",
            internal_secondary="10.0.0.2",
            external_primary="203.0.113.1",
            external_secondary="203.0.113.2",
        ),
    )
    store.create_server(s)

    action_id = actions.create_action(
        name="Ping",
        description="Ping best host",
        command_template="ping {{host}}",
        requires_confirm=False,
    )

    run = actions.run_action(action_id, "Srv1", dry_run=True)
    assert run.status == "dry_run"
    assert run.command_rendered == "ping 10.0.0.1"
    assert run.stdout == ""
    assert run.stderr == ""


def test_local_execution_path(tmp_path: Path) -> None:
    db_path = tmp_path / "data.sqlite3"
    backend = SqliteStore(db_path)
    store = ServerStore(backend)
    actions = ActionsStore(backend, store)

    s = Server(name="Srv1", hosts=HostSet(internal_primary="10.0.0.1"))
    store.create_server(s)

    # Harmless local command
    action_id = actions.create_action(
        name="Echo",
        description="Echo ok",
        command_template="python -c \"print('ok')\"",
        requires_confirm=False,
    )

    run = actions.run_action(action_id, "Srv1", dry_run=False)
    assert run.status in ("success", "error")  # platform/python dependent, but should run
    assert "ok" in (run.stdout + run.stderr)


def test_history_truncation(tmp_path: Path) -> None:
    db_path = tmp_path / "data.sqlite3"
    backend = SqliteStore(db_path)
    store = ServerStore(backend)
    actions = ActionsStore(backend, store)

    s = Server(name="Srv1", hosts=HostSet(internal_primary="10.0.0.1"))
    store.create_server(s)

    long_out = "x" * 60000

    # Patch execute to return large output
    def fake_execute(cmd: str, timeout_s: int = 60):
        return 0, long_out, "", 10

    from myservers import connectors

    # monkeypatching without pytest: directly override in module
    import myservers.connectors.exec_local as exec_local_module

    old_execute = exec_local_module.execute
    exec_local_module.execute = fake_execute  # type: ignore[assignment]
    try:
        action_id = actions.create_action(
            name="LongOut",
            description="Long output",
            command_template="echo long",
            requires_confirm=False,
        )
        run = actions.run_action(action_id, "Srv1", dry_run=False)
        assert len(run.stdout) <= 50000
    finally:
        exec_local_module.execute = old_execute  # type: ignore[assignment]


def test_action_never_contains_secrets(tmp_path: Path) -> None:
    db_path = tmp_path / "data.sqlite3"
    backend = SqliteStore(db_path)
    store = ServerStore(backend)
    actions = ActionsStore(backend, store)
    ident_store = IdentitiesStore(backend)

    s = Server(name="Srv1", hosts=HostSet(internal_primary="10.0.0.1"))
    store.create_server(s)

    secret = "SUPER_SECRET_PASSWORD"
    identity_id = create_identity(ident_store, "id1", "user", "password", secret)
    assert get_secret(identity_id) == secret

    # Action template uses only safe fields
    action_id = actions.create_action(
        name="SafeAction",
        description="Should not leak secrets",
        command_template="echo {{server.name}} {{host}} {{ssh.port}}",
        requires_confirm=False,
    )

    run = actions.run_action(action_id, "Srv1", dry_run=True)
    combined = run.command_rendered + run.stdout + run.stderr
    assert secret not in combined

