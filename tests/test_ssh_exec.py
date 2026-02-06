from pathlib import Path
from unittest.mock import patch, MagicMock

import keyring
import pytest
from keyring.backend import KeyringBackend

from myservers.connectors.exec_ssh import build_ssh_invocation_string, execute_ssh
from myservers.core.actions import ActionsStore
from myservers.core.identities_store import IdentitiesStore
from myservers.core.identity import create_identity, get_secret
from myservers.core.models import HostSet, Server
from myservers.core.servers import ServerStore
from myservers.storage.sqlite_store import SqliteStore


class InMemoryKeyring(KeyringBackend):
    priority = 1

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self._store.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self._store[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        self._store.pop((service, username), None)


@pytest.fixture(autouse=True)
def in_memory_keyring(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = InMemoryKeyring()

    def _get_keyring() -> KeyringBackend:
        return backend

    monkeypatch.setattr(keyring, "get_keyring", _get_keyring)
    keyring.set_keyring(backend)


def test_ssh_invocation_includes_safe_options() -> None:
    server = Server(name="Srv", hosts=HostSet(internal_primary="10.0.0.1"))
    from myservers.core.identities_store import SshProfileMeta, IdentityMeta

    profile = SshProfileMeta(server_name="Srv", port=2222, identity_id=1, username_override="admin")
    identity = IdentityMeta(id=1, name="id1", username="user", kind="ssh_key_path", key_path="/path/to/key")
    cmd = build_ssh_invocation_string(server, profile, identity, "echo hello")
    assert "BatchMode=yes" in cmd
    assert "ConnectTimeout=5" in cmd
    assert "StrictHostKeyChecking=accept-new" in cmd
    assert "-p 2222" in cmd
    assert '-i "/path/to/key"' in cmd
    assert "admin@10.0.0.1" in cmd
    assert "-- echo hello" in cmd


def test_ssh_invocation_omits_port_when_default() -> None:
    server = Server(name="Srv", hosts=HostSet(internal_primary="10.0.0.1"))
    from myservers.core.identities_store import SshProfileMeta

    profile = SshProfileMeta(server_name="Srv", port=22, identity_id=None, username_override=None)
    cmd = build_ssh_invocation_string(server, profile, None, "ls")
    assert "-p" not in cmd or "-p 22" not in cmd  # port 22 should be omitted
    assert "10.0.0.1" in cmd


def test_ssh_invocation_never_includes_secrets() -> None:
    server = Server(name="Srv", hosts=HostSet(internal_primary="10.0.0.1"))
    from myservers.core.identities_store import SshProfileMeta, IdentityMeta

    profile = SshProfileMeta(server_name="Srv", port=22, identity_id=1, username_override=None)
    identity = IdentityMeta(id=1, name="id1", username="user", kind="password", key_path=None)
    secret = "SECRET_PASSWORD"
    cmd = build_ssh_invocation_string(server, profile, identity, "echo test")
    assert secret not in cmd
    assert "password" not in cmd.lower()
    assert "SECRET" not in cmd


@patch("myservers.connectors.exec_ssh.subprocess.run")
def test_ssh_execution_calls_subprocess_correctly(mock_run: MagicMock) -> None:
    server = Server(name="Srv", hosts=HostSet(internal_primary="10.0.0.1"))
    from myservers.core.identities_store import SshProfileMeta, IdentityMeta

    profile = SshProfileMeta(server_name="Srv", port=2222, identity_id=1, username_override="admin")
    identity = IdentityMeta(id=1, name="id1", username="user", kind="ssh_key_path", key_path="/key")
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "output"
    mock_proc.stderr = ""
    mock_run.return_value = mock_proc

    ec, out, err, duration = execute_ssh(server, profile, identity, "echo hello", timeout_s=30)
    assert ec == 0
    assert out == "output"
    mock_run.assert_called_once()
    call_args = mock_run.call_args
    assert call_args[0][0][0] == "ssh"
    assert "-p" in call_args[0][0]
    assert "-o" in call_args[0][0]
    assert "--" in call_args[0][0]
    assert "echo hello" in call_args[0][0]


@patch("myservers.connectors.exec_ssh.subprocess.run")
def test_ssh_action_run_records_history(mock_run: MagicMock, tmp_path: Path) -> None:
    db_path = tmp_path / "test_ssh_action.db"
    backend = SqliteStore(db_path)
    store = ServerStore(backend)
    actions = ActionsStore(backend, store)

    s = Server(name="Srv1", hosts=HostSet(internal_primary="10.0.0.1"))
    store.create_server(s)

    ident_store = IdentitiesStore(backend)
    identity_id = create_identity(ident_store, "id1", "user", "ssh_key_path", "", "/path/to/key")
    ident_store.set_ssh_profile("Srv1", port=2222, identity_id=identity_id, username_override=None)

    action_id = actions.create_action(
        name="SSHAction",
        description="SSH test",
        command_template="echo {{server.name}}",
        requires_confirm=False,
        execution_target="ssh",
    )

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "Srv1"
    mock_proc.stderr = ""
    mock_run.return_value = mock_proc

    run = actions.run_action(action_id, "Srv1", dry_run=False)
    assert run.status == "success"
    assert run.exit_code == 0
    assert "Srv1" in run.stdout
    assert "echo Srv1" in run.command_rendered

    # Verify history
    cur = backend._conn.cursor()
    cur.execute("SELECT COUNT(*) FROM action_runs WHERE action_id = ?", (action_id,))
    assert cur.fetchone()[0] == 1


def test_ssh_action_dry_run_creates_history(tmp_path: Path) -> None:
    db_path = tmp_path / "test_ssh_dry.db"
    backend = SqliteStore(db_path)
    store = ServerStore(backend)
    actions = ActionsStore(backend, store)

    s = Server(name="Srv1", hosts=HostSet(internal_primary="10.0.0.1"))
    store.create_server(s)

    action_id = actions.create_action(
        name="SSHDry",
        description="SSH dry run",
        command_template="echo test",
        requires_confirm=False,
        execution_target="ssh",
    )

    run = actions.run_action(action_id, "Srv1", dry_run=True)
    assert run.status == "dry_run"
    assert run.exit_code is None
    assert run.stdout == ""
    assert run.stderr == ""


def test_local_execution_still_works(tmp_path: Path) -> None:
    db_path = tmp_path / "test_local_still.db"
    backend = SqliteStore(db_path)
    store = ServerStore(backend)
    actions = ActionsStore(backend, store)

    s = Server(name="Srv1", hosts=HostSet(internal_primary="10.0.0.1"))
    store.create_server(s)

    action_id = actions.create_action(
        name="LocalAction",
        description="Local test",
        command_template="python -c \"print('ok')\"",
        requires_confirm=False,
        execution_target="local",
    )

    run = actions.run_action(action_id, "Srv1", dry_run=False)
    assert run.status in ("success", "error")
    assert "ok" in (run.stdout + run.stderr)
