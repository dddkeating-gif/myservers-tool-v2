"""SQLite-backed storage for servers and hosts.

Implements the same minimal API as JsonStore: get/set/delete on sections.
Only the "Servers" section is supported.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class SqliteStore:
    """Relational storage for servers and their hosts."""

    def __init__(self, db_path: Path | str, json_migration_path: Path | str | None = None) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        should_init = not self._path.exists()
        self._conn = sqlite3.connect(self._path)
        self._conn.row_factory = sqlite3.Row
        if should_init:
            self._init_schema()
            if json_migration_path is not None and Path(json_migration_path).exists():
                self._migrate_from_json(Path(json_migration_path))

    # ---------- schema & migration ----------

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS servers (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT UNIQUE NOT NULL,
                notes   TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS hosts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id  INTEGER NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
                kind       TEXT NOT NULL,       -- 'internal' or 'external'
                priority   INTEGER NOT NULL,    -- 1 or 2 (primary/secondary)
                address    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tags (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS server_tags (
                server_id  INTEGER NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
                tag_id     INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY (server_id, tag_id)
            );

            CREATE TABLE IF NOT EXISTS identities (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                name     TEXT UNIQUE NOT NULL,
                username TEXT,
                kind     TEXT NOT NULL CHECK (kind IN ('ssh_key_path','password','token'))
            );

            CREATE TABLE IF NOT EXISTS ssh_profiles (
                server_id        INTEGER PRIMARY KEY REFERENCES servers(id) ON DELETE CASCADE,
                port             INTEGER NOT NULL DEFAULT 22,
                identity_id      INTEGER REFERENCES identities(id) ON DELETE SET NULL,
                username_override TEXT
            );
            """
        )
        self._conn.commit()

    def _migrate_from_json(self, json_path: Path) -> None:
        """Import existing JSON data (v2 or legacy-shaped) into SQLite."""
        try:
            raw = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        servers = (raw or {}).get("Servers", {}) or {}
        for name, payload in servers.items():
            if not isinstance(payload, dict):
                continue
            hosts_raw = payload.get("Hosts", {}) or {}
            internal_primary = hosts_raw.get("Internal_Primary", "") or ""
            internal_secondary = hosts_raw.get("Internal_Secondary", "") or ""
            external_primary = hosts_raw.get("External_Primary", "") or ""
            external_secondary = hosts_raw.get("External_Secondary", "") or ""
            self._insert_server_with_hosts(
                name,
                internal_primary,
                internal_secondary,
                external_primary,
                external_secondary,
            )
        self._conn.commit()

    def _insert_server_with_hosts(
        self,
        name: str,
        internal_primary: str,
        internal_secondary: str,
        external_primary: str,
        external_secondary: str,
    ) -> None:
        cur = self._conn.cursor()
        cur.execute("INSERT OR IGNORE INTO servers(name) VALUES (?)", (name.strip(),))
        cur.execute("SELECT id FROM servers WHERE name = ?", (name.strip(),))
        row = cur.fetchone()
        if row is None:
            return
        server_id = row["id"]
        # clear existing hosts for id if any
        cur.execute("DELETE FROM hosts WHERE server_id = ?", (server_id,))

        def _add_host(kind: str, priority: int, address: str) -> None:
            address = (address or "").strip()
            if not address:
                return
            cur.execute(
                "INSERT INTO hosts(server_id, kind, priority, address) VALUES (?, ?, ?, ?)",
                (server_id, kind, priority, address),
            )

        _add_host("internal", 1, internal_primary)
        _add_host("internal", 2, internal_secondary)
        _add_host("external", 1, external_primary)
        _add_host("external", 2, external_secondary)

    # ---------- JsonStore-like API ----------

    def get(self, section: str, key: str | None = None, *, all_sections: bool = False) -> Any:
        """Return data in the same shape ServerStore expects."""
        if all_sections:
            # only "Servers" is supported; return full mapping
            return {"Servers": self.get("Servers", None)}

        if section != "Servers":
            return {}

        cur = self._conn.cursor()
        if key is None:
            cur.execute("SELECT id, name, notes FROM servers ORDER BY name")
            rows = cur.fetchall()
            result: dict[str, dict[str, Any]] = {}
            for row in rows:
                server_id = row["id"]
                hosts = self._load_hosts(server_id)
                result[row["name"]] = {"Hosts": hosts, "Notes": row["notes"]}
            return result

        # specific server
        cur.execute("SELECT id, name, notes FROM servers WHERE name = ?", (key.strip(),))
        row = cur.fetchone()
        if row is None:
            return None
        hosts = self._load_hosts(row["id"])
        return {"Hosts": hosts, "Notes": row["notes"]}

    def _load_hosts(self, server_id: int) -> dict[str, str]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT kind, priority, address FROM hosts WHERE server_id = ?",
            (server_id,),
        )
        mapping: dict[str, str] = {
            "Internal_Primary": "",
            "Internal_Secondary": "",
            "External_Primary": "",
            "External_Secondary": "",
        }
        for row in cur.fetchall():
            kind = row["kind"]
            priority = row["priority"]
            key: str | None = None
            if kind == "internal" and priority == 1:
                key = "Internal_Primary"
            elif kind == "internal" and priority == 2:
                key = "Internal_Secondary"
            elif kind == "external" and priority == 1:
                key = "External_Primary"
            elif kind == "external" and priority == 2:
                key = "External_Secondary"
            if key:
                mapping[key] = row["address"]
        return mapping

    def set(self, section: str, key: str, value: dict) -> None:
        if section != "Servers":
            return
        name = key.strip()
        if not name:
            return
        hosts_raw = (value or {}).get("Hosts", {}) or {}
        internal_primary = hosts_raw.get("Internal_Primary", "") or ""
        internal_secondary = hosts_raw.get("Internal_Secondary", "") or ""
        external_primary = hosts_raw.get("External_Primary", "") or ""
        external_secondary = hosts_raw.get("External_Secondary", "") or ""
        self._insert_server_with_hosts(
            name,
            internal_primary,
            internal_secondary,
            external_primary,
            external_secondary,
        )
        self._conn.commit()

    def delete(self, section: str, key: str) -> None:
        if section != "Servers":
            return
        name = key.strip()
        if not name:
            return
        cur = self._conn.cursor()
        cur.execute("DELETE FROM servers WHERE name = ?", (name,))
        self._conn.commit()

