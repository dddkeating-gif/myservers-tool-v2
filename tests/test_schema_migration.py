import sqlite3
from pathlib import Path

from myservers.core.identities_store import IdentitiesStore
from myservers.storage.sqlite_store import SqliteStore


def test_identities_key_path_migration(tmp_path: Path) -> None:
    """Test that existing identities survive key_path column addition."""
    db_path = tmp_path / "data.sqlite3"

    # Create DB with old schema (no key_path)
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE identities (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT UNIQUE NOT NULL,
            username TEXT,
            kind     TEXT NOT NULL CHECK (kind IN ('ssh_key_path','password','token'))
        );
        INSERT INTO identities(name, username, kind) VALUES ('old_id', 'user', 'password');
        """
    )
    conn.commit()
    conn.close()

    # Reopen with SqliteStore (should migrate)
    backend = SqliteStore(db_path)
    ident_store = IdentitiesStore(backend)

    # Verify existing identity still exists and has key_path=None
    identities = ident_store.list_identities()
    assert len(identities) == 1
    assert identities[0].name == "old_id"
    assert identities[0].key_path is None

    # Verify key_path column exists
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(identities)")
    cols = {row[1] for row in cur.fetchall()}
    assert "key_path" in cols
    conn.close()
