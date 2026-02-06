import sqlite3
from pathlib import Path

import keyring
import pytest
from keyring.backend import KeyringBackend

from myservers.core.identity import (
    SERVICE_NAME,
    create_identity,
    update_identity,
    delete_identity,
    get_secret,
)
from myservers.core.identities_store import IdentitiesStore
from myservers.core.models import Server, HostSet
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


def test_identity_secrets_in_keyring_not_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "data.sqlite3"
    backend = SqliteStore(db_path)
    ident_store = IdentitiesStore(backend)

    # create identity + secret
    identity_id = create_identity(ident_store, "id1", "user", "password", "s3cr3t")
    # secret available via keyring
    assert get_secret(identity_id) == "s3cr3t"

    # SQLite metadata has no secret field
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(identities)")
    cols = [row[1] for row in cur.fetchall()]
    assert "secret" not in cols

    cur.execute("SELECT name, username, kind FROM identities WHERE id = ?", (identity_id,))
    row = cur.fetchone()
    assert row is not None
    assert "s3cr3t" not in {str(v) for v in row}


def test_identity_metadata_crud(tmp_path: Path) -> None:
    db_path = tmp_path / "data.sqlite3"
    backend = SqliteStore(db_path)
    ident_store = IdentitiesStore(backend)

    identity_id = create_identity(ident_store, "id1", "user1", "password", "pw1")
    assert get_secret(identity_id) == "pw1"

    update_identity(ident_store, identity_id, "id1b", "user2", "token", None)
    meta = ident_store.get_identity(identity_id)
    assert meta is not None
    assert meta.name == "id1b"
    assert meta.username == "user2"
    assert meta.kind == "token"
    # secret unchanged when secret_optional is None
    assert get_secret(identity_id) == "pw1"

    update_identity(ident_store, identity_id, "id1b", "user2", "token", "pw2")
    assert get_secret(identity_id) == "pw2"

    delete_identity(ident_store, identity_id)
    assert ident_store.get_identity(identity_id) is None
    assert get_secret(identity_id) is None


def test_assign_identity_to_ssh_profile(tmp_path: Path) -> None:
    db_path = tmp_path / "data.sqlite3"
    backend = SqliteStore(db_path)
    store = ServerStore(backend)
    ident_store = IdentitiesStore(backend)

    # create a server
    s = Server(name="Srv1", hosts=HostSet(internal_primary="10.0.0.1"))
    store.create_server(s)

    # create identity
    identity_id = create_identity(ident_store, "id1", "user", "password", "secret")

    ident_store.set_ssh_profile("Srv1", port=2222, identity_id=identity_id, username_override="sshuser")
    profile = ident_store.get_ssh_profile("Srv1")
    assert profile is not None
    assert profile.port == 2222
    assert profile.identity_id == identity_id
    assert profile.username_override == "sshuser"

