from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from myservers.storage.sqlite_store import SqliteStore


@dataclass
class WebLink:
    id: int
    server_name: str
    label: str
    url: str


class WebLinksStore:
    """CRUD for web links (metadata only)."""

    def __init__(self, backend: SqliteStore) -> None:
        self._backend = backend
        self._conn = backend._conn

    def list_links(self, server_name: str) -> List[WebLink]:
        cur = self._conn.cursor()
        cur.execute("SELECT id FROM servers WHERE name = ?", (server_name.strip(),))
        srow = cur.fetchone()
        if srow is None:
            return []
        server_id = srow["id"]
        cur.execute(
            "SELECT id, label, url FROM web_links WHERE server_id = ? ORDER BY label",
            (server_id,),
        )
        return [
            WebLink(id=row["id"], server_name=server_name, label=row["label"], url=row["url"])
            for row in cur.fetchall()
        ]

    def create_link(self, server_name: str, label: str, url: str) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT id FROM servers WHERE name = ?", (server_name.strip(),))
        srow = cur.fetchone()
        if srow is None:
            raise ValueError("Server not found")
        server_id = srow["id"]
        cur.execute(
            "INSERT INTO web_links(server_id, label, url) VALUES (?, ?, ?)",
            (server_id, label.strip(), url.strip()),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def update_link(self, link_id: int, label: str, url: str) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "UPDATE web_links SET label = ?, url = ? WHERE id = ?",
            (label.strip(), url.strip(), link_id),
        )
        self._conn.commit()

    def delete_link(self, link_id: int) -> None:
        cur = self._conn.cursor()
        cur.execute("DELETE FROM web_links WHERE id = ?", (link_id,))
        self._conn.commit()
