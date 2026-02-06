from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from myservers.storage.sqlite_store import SqliteStore


@dataclass
class IdentityMeta:
    id: int
    name: str
    username: str | None
    kind: str
    key_path: str | None


@dataclass
class SshProfileMeta:
    server_name: str
    port: int
    identity_id: Optional[int]
    username_override: Optional[str]


class IdentitiesStore:
    """Metadata CRUD for identities and SSH profiles (no secrets)."""

    def __init__(self, backend: SqliteStore) -> None:
        self._backend = backend
        self._conn = backend._conn  # internal use within core layer

    # -------- identities --------

    def list_identities(self) -> List[IdentityMeta]:
        cur = self._conn.cursor()
        cur.execute("SELECT id, name, username, kind, key_path FROM identities ORDER BY name")
        return [
            IdentityMeta(
                id=row["id"],
                name=row["name"],
                username=row["username"],
                kind=row["kind"],
                key_path=row["key_path"],
            )
            for row in cur.fetchall()
        ]

    def get_identity(self, identity_id: int) -> Optional[IdentityMeta]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT id, name, username, kind, key_path FROM identities WHERE id = ?",
            (identity_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return IdentityMeta(
            id=row["id"],
            name=row["name"],
            username=row["username"],
            kind=row["kind"],
            key_path=row["key_path"],
        )

    def create_identity_metadata(
        self, name: str, username: str | None, kind: str, key_path: str | None = None
    ) -> int:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO identities(name, username, kind, key_path) VALUES (?, ?, ?, ?)",
            (name.strip(), (username or "").strip() or None, kind, (key_path or "").strip() or None),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def update_identity_metadata(
        self,
        identity_id: int,
        name: str,
        username: str | None,
        kind: str,
        key_path: str | None = None,
    ) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "UPDATE identities SET name = ?, username = ?, kind = ?, key_path = ? WHERE id = ?",
            (name.strip(), (username or "").strip() or None, kind, (key_path or "").strip() or None, identity_id),
        )
        self._conn.commit()

    def delete_identity_metadata(self, identity_id: int) -> None:
        cur = self._conn.cursor()
        cur.execute("DELETE FROM identities WHERE id = ?", (identity_id,))
        self._conn.commit()

    # -------- ssh_profiles --------

    def get_ssh_profile(self, server_name: str) -> Optional[SshProfileMeta]:
        cur = self._conn.cursor()
        cur.execute("SELECT id FROM servers WHERE name = ?", (server_name.strip(),))
        srow = cur.fetchone()
        if srow is None:
            return None
        server_id = srow["id"]
        cur.execute(
            "SELECT port, identity_id, username_override FROM ssh_profiles WHERE server_id = ?",
            (server_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return SshProfileMeta(
            server_name=server_name,
            port=row["port"],
            identity_id=row["identity_id"],
            username_override=row["username_override"],
        )

    def set_ssh_profile(
        self,
        server_name: str,
        port: int,
        identity_id: Optional[int],
        username_override: Optional[str],
    ) -> None:
        cur = self._conn.cursor()
        cur.execute("SELECT id FROM servers WHERE name = ?", (server_name.strip(),))
        srow = cur.fetchone()
        if srow is None:
            # no such server; nothing to do
            return
        server_id = srow["id"]
        cur.execute(
            """
            INSERT INTO ssh_profiles(server_id, port, identity_id, username_override)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(server_id) DO UPDATE SET
                port = excluded.port,
                identity_id = excluded.identity_id,
                username_override = excluded.username_override
            """,
            (
                server_id,
                port,
                identity_id,
                (username_override or "").strip() or None,
            ),
        )
        self._conn.commit()

