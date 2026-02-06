from __future__ import annotations

from pathlib import Path
from typing import List

import keyring
import pytest
from keyring.backend import KeyringBackend

from myservers.core.identities_store import IdentitiesStore
from myservers.core.import_ssh_config import (
    SshConfigCandidate,
    apply_ssh_config_import,
    parse_ssh_config,
)
from myservers.core.servers import ServerStore
from myservers.storage.sqlite_store import SqliteStore


SSH_CONFIG_SAMPLE = """
# Sample SSH config
Host app-server
    HostName app.internal.example.com
    User deploy
    Port 2222
    IdentityFile ~/.ssh/app_deploy

Host db-server
    HostName 10.0.0.5

Host *
    User ignored
"""


class InMemoryKeyring(KeyringBackend):
    """Simple in-memory keyring to ensure no secrets are written."""

    priority = 1

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:  # type: ignore[override]
        return self._store.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:  # type: ignore[override]
        self._store[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:  # type: ignore[override]
        self._store.pop((service, username), None)


@pytest.fixture(autouse=True)
def in_memory_keyring(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install in-memory keyring so tests never hit OS keychain."""

    backend = InMemoryKeyring()

    def _get_keyring() -> KeyringBackend:
        return backend

    monkeypatch.setattr(keyring, "get_keyring", _get_keyring)
    keyring.set_keyring(backend)


def test_parse_ssh_config_basic() -> None:
    candidates: List[SshConfigCandidate] = parse_ssh_config(SSH_CONFIG_SAMPLE)
    # Should ignore wildcard Host * entry
    assert len(candidates) == 2

    app = next(c for c in candidates if c.host_alias == "app-server")
    assert app.host_name == "app.internal.example.com"
    assert app.username == "deploy"
    assert app.port == 2222
    assert "app_deploy" in (app.identity_file or "")

    db = next(c for c in candidates if c.host_alias == "db-server")
    assert db.host_name == "10.0.0.5"
    assert db.username is None
    assert db.port is None
    assert db.identity_file is None


def test_import_ssh_config_creates_servers_profiles_and_identities(tmp_path: Path) -> None:
    db_path = tmp_path / "data.sqlite3"
    backend = SqliteStore(db_path)
    servers = ServerStore(backend)
    identities = IdentitiesStore(backend)

    candidates = parse_ssh_config(SSH_CONFIG_SAMPLE)
    apply_ssh_config_import(candidates, servers, identities)

    # Servers created
    app = servers.get_server("app-server")
    db = servers.get_server("db-server")
    assert app is not None
    assert db is not None
    assert app.hosts.internal_primary == "app.internal.example.com"
    assert db.hosts.internal_primary == "10.0.0.5"

    # SSH profiles set
    app_profile = identities.get_ssh_profile("app-server")
    db_profile = identities.get_ssh_profile("db-server")
    assert app_profile is not None
    assert app_profile.port == 2222
    assert app_profile.username_override == "deploy"
    assert app_profile.identity_id is not None

    assert db_profile is not None
    assert db_profile.port == 22  # default
    assert db_profile.username_override is None
    assert db_profile.identity_id is None

    # Identity created and keyed by path
    idents = identities.list_identities()
    assert len(idents) == 1
    ident = idents[0]
    assert ident.kind == "ssh_key_path"
    assert ident.key_path is not None


def test_import_reuses_identities_by_key_path(tmp_path: Path) -> None:
    db_path = tmp_path / "data.sqlite3"
    backend = SqliteStore(db_path)
    servers = ServerStore(backend)
    identities = IdentitiesStore(backend)

    candidates = parse_ssh_config(SSH_CONFIG_SAMPLE)
    # Duplicate first candidate with same key path but different alias
    extra = SshConfigCandidate(
        host_alias="app-server-2",
        host_name="app.internal.example.com",
        username="deploy",
        port=2222,
        identity_file=candidates[0].identity_file,
    )
    candidates.append(extra)

    apply_ssh_config_import(candidates, servers, identities)

    idents = identities.list_identities()
    # Only one identity for the same key path
    assert len(idents) == 1
    ident_id = idents[0].id

    profile1 = identities.get_ssh_profile("app-server")
    profile2 = identities.get_ssh_profile("app-server-2")
    assert profile1 is not None and profile2 is not None
    assert profile1.identity_id == ident_id
    assert profile2.identity_id == ident_id


def test_import_does_not_touch_keyring_for_ssh_key_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = tmp_path / "data.sqlite3"
    backend = SqliteStore(db_path)
    servers = ServerStore(backend)
    identities = IdentitiesStore(backend)

    called: list[str] = []

    def fake_set_password(service: str, username: str, password: str) -> None:
        called.append(f"{service}:{username}")

    monkeypatch.setattr(keyring, "set_password", fake_set_password)

    candidates = parse_ssh_config(SSH_CONFIG_SAMPLE)
    apply_ssh_config_import(candidates, servers, identities)

    # No secrets should be written for ssh_key_path identities
    assert called == []

