from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from myservers.core.models import HostSet
from myservers.storage.sqlite_store import SqliteStore


@dataclass
class ServerFilterItem:
    """Lightweight view model for filtering/searching servers."""

    name: str
    hosts: HostSet
    notes: str
    tags: list[str]


class TagStore:
    """CRUD for tags and server-tag associations."""

    def __init__(self, backend: SqliteStore) -> None:
        self._backend = backend
        self._conn = backend._conn

    # -------- tag metadata --------

    def list_tags(self) -> List[str]:
        """Return all distinct tag names."""
        cur = self._conn.cursor()
        cur.execute("SELECT name FROM tags ORDER BY name COLLATE NOCASE")
        return [row["name"] for row in cur.fetchall()]

    def get_server_tags(self, server_name: str) -> List[str]:
        """Return tags for a given server name."""
        cur = self._conn.cursor()
        cur.execute("SELECT id FROM servers WHERE name = ?", (server_name.strip(),))
        srow = cur.fetchone()
        if srow is None:
            return []
        server_id = srow["id"]
        cur.execute(
            """
            SELECT t.name
            FROM server_tags st
            JOIN tags t ON st.tag_id = t.id
            WHERE st.server_id = ?
            ORDER BY t.name COLLATE NOCASE
            """,
            (server_id,),
        )
        return [row["name"] for row in cur.fetchall()]

    def set_server_tags(self, server_name: str, tags: list[str]) -> None:
        """Replace tags for the given server.

        Normalization rules:
        - trim whitespace
        - lower-case
        - drop empties
        - unique
        - sort alphabetically
        """

        name = server_name.strip()
        if not name:
            return

        normalized = sorted({t.strip().lower() for t in tags if t.strip()})

        cur = self._conn.cursor()
        cur.execute("SELECT id FROM servers WHERE name = ?", (name,))
        srow = cur.fetchone()
        if srow is None:
            return
        server_id = srow["id"]

        # Resolve / create tag ids
        tag_ids: list[int] = []
        for tag in normalized:
            cur.execute("SELECT id FROM tags WHERE name = ?", (tag,))
            row = cur.fetchone()
            if row is None:
                cur.execute("INSERT INTO tags(name) VALUES (?)", (tag,))
                tag_id = int(cur.lastrowid)
            else:
                tag_id = row["id"]
            tag_ids.append(tag_id)

        # Replace server_tags entries
        cur.execute("DELETE FROM server_tags WHERE server_id = ?", (server_id,))
        for tag_id in tag_ids:
            cur.execute(
                "INSERT INTO server_tags(server_id, tag_id) VALUES (?, ?)",
                (server_id, tag_id),
            )

        self._conn.commit()


def filter_servers(
    servers: Sequence[ServerFilterItem],
    query: str,
    tag: str | None,
) -> list[ServerFilterItem]:
    """Filter servers by text query and/or tag.

    - query matches against: name, any host address, notes (case-insensitive, substring)
    - tag (if provided and non-empty) must be one of the server's tags (case-insensitive)
    """

    q = (query or "").strip().lower()
    tag_norm = (tag or "").strip().lower()

    results: list[ServerFilterItem] = []
    for item in servers:
        # Tag filter
        if tag_norm:
            tags_lower = [t.lower() for t in item.tags]
            if tag_norm not in tags_lower:
                continue

        # Text filter
        if q:
            haystack_parts = [
                item.name,
                item.notes or "",
                item.hosts.internal_primary,
                item.hosts.internal_secondary,
                item.hosts.external_primary,
                item.hosts.external_secondary,
            ]
            haystack = " ".join(haystack_parts).lower()
            if q not in haystack:
                continue

        results.append(item)

    return results

