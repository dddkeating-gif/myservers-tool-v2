from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional, Protocol, runtime_checkable

from myservers.storage.json_store import JsonStore
from myservers.core.models import Server, HostSet


@runtime_checkable
class Storage(Protocol):
    def get(self, section: str, key: str | None = None, *, all_sections: bool = False) -> Any: ...

    def set(self, section: str, key: str, value: dict) -> None: ...

    def delete(self, section: str, key: str) -> None: ...


class ServerStore:
    """Server CRUD facade over a storage backend (JsonStore, SqliteStore, etc.).

    Data shape in JSON:
    {
      "Servers": {
        "Name": {"Hosts": {...}}
      }
    }
    """

    def __init__(self, backend: Storage | Path | str, section: str = "Servers") -> None:
        # Accept either a concrete backend instance or a filesystem path (legacy JSON).
        if isinstance(backend, (str, Path)):
            self._store: Storage = JsonStore(backend)
        else:
            self._store = backend
        self._section = section

    # -------- internal helpers ---------

    def _serialize(self, server: Server) -> dict:
        return {
            "Hosts": {
                "Internal_Primary": server.hosts.internal_primary,
                "Internal_Secondary": server.hosts.internal_secondary,
                "External_Primary": server.hosts.external_primary,
                "External_Secondary": server.hosts.external_secondary,
            }
        }

    def _deserialize(self, name: str, payload: dict) -> Server:
        hosts_raw = (payload or {}).get("Hosts", {}) or {}
        hosts = HostSet(
            internal_primary=hosts_raw.get("Internal_Primary", ""),
            internal_secondary=hosts_raw.get("Internal_Secondary", ""),
            external_primary=hosts_raw.get("External_Primary", ""),
            external_secondary=hosts_raw.get("External_Secondary", ""),
        )
        return Server(name=name, hosts=hosts)

    # -------- public API ---------

    def list_servers(self) -> List[Server]:
        bucket = self._store.get(self._section, None) or {}
        if not isinstance(bucket, dict):
            return []
        return [self._deserialize(name, data) for name, data in bucket.items()]

    def get_server(self, name: str) -> Optional[Server]:
        name = name.strip()
        if not name:
            return None
        data = self._store.get(self._section, name)
        if not data:
            return None
        return self._deserialize(name, data)

    def create_server(self, server: Server) -> None:
        name = server.name.strip()
        if not name:
            raise ValueError("Server name is required")
        bucket = self._store.get(self._section, None) or {}
        if name in bucket:
            raise ValueError("Server already exists")
        self._store.set(self._section, name, self._serialize(Server(name=name, hosts=server.hosts)))

    def update_server(self, original_name: str, server: Server) -> None:
        original_name = original_name.strip()
        new_name = server.name.strip()
        if not original_name:
            raise ValueError("Original name is required")
        if not new_name:
            raise ValueError("Server name is required")
        bucket = self._store.get(self._section, None) or {}
        if original_name not in bucket:
            raise KeyError("Server does not exist")
        if new_name != original_name and new_name in bucket:
            raise ValueError("Server with this name already exists")

        # Rename if needed
        if new_name != original_name:
            self._store.delete(self._section, original_name)
        self._store.set(self._section, new_name, self._serialize(Server(name=new_name, hosts=server.hosts)))

    def delete_server(self, name: str) -> None:
        name = name.strip()
        if not name:
            return
        self._store.delete(self._section, name)

