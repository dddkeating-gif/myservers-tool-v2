from myservers.connectors.ssh_command import build_ssh_command
from myservers.core.identities_store import IdentityMeta, SshProfileMeta
from myservers.core.models import HostSet, Server


def test_ssh_command_with_user_port_key_path() -> None:
    server = Server(name="Srv", hosts=HostSet(internal_primary="10.0.0.1"))
    profile = SshProfileMeta(server_name="Srv", port=2222, identity_id=1, username_override="admin")
    identity = IdentityMeta(id=1, name="id1", username="user", kind="ssh_key_path", key_path="/path/to/key")
    cmd = build_ssh_command(server, profile, identity)
    assert cmd == 'ssh -p 2222 -i "/path/to/key" admin@10.0.0.1'


def test_ssh_command_without_user() -> None:
    server = Server(name="Srv", hosts=HostSet(internal_primary="10.0.0.1"))
    profile = SshProfileMeta(server_name="Srv", port=22, identity_id=None, username_override=None)
    cmd = build_ssh_command(server, profile, None)
    assert cmd == "ssh 10.0.0.1"


def test_ssh_command_without_key_path() -> None:
    server = Server(name="Srv", hosts=HostSet(internal_primary="10.0.0.1"))
    profile = SshProfileMeta(server_name="Srv", port=22, identity_id=1, username_override=None)
    identity = IdentityMeta(id=1, name="id1", username="user", kind="password", key_path=None)
    cmd = build_ssh_command(server, profile, identity)
    assert cmd == "ssh user@10.0.0.1"


def test_ssh_command_no_secrets_in_command() -> None:
    server = Server(name="Srv", hosts=HostSet(internal_primary="10.0.0.1"))
    profile = SshProfileMeta(server_name="Srv", port=22, identity_id=1, username_override=None)
    identity = IdentityMeta(id=1, name="id1", username="user", kind="password", key_path=None)
    cmd = build_ssh_command(server, profile, identity)
    assert "password" not in cmd.lower()
    assert "secret" not in cmd.lower()
    assert "token" not in cmd.lower()


def test_ssh_command_empty_host_returns_empty() -> None:
    server = Server(name="Srv", hosts=HostSet())
    profile = SshProfileMeta(server_name="Srv", port=22, identity_id=None, username_override=None)
    cmd = build_ssh_command(server, profile, None)
    assert cmd == ""
