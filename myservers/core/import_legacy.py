from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from myservers.core.models import Server, HostSet
from myservers.core.servers import ServerStore


def import_legacy_servers(path: Path) -> List[Server]:
    """Parse legacy JSON into a list of Server objects.

    Expected shape:
    {
      "Servers": {
        "Name": {
          "<id_key>": {},
          "Hosts": {...},
          "SSH": {...},
          "WEB": {...}
        }
      }
    }
    """

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    servers_node = data.get("Servers", {}) or {}
    servers: List[Server] = []
    for name, payload in servers_node.items():
        if not isinstance(payload, dict):
            continue
        hosts_raw = payload.get("Hosts", {}) or {}
        hosts = HostSet(
            internal_primary=hosts_raw.get("Internal_Primary", ""),
            internal_secondary=hosts_raw.get("Internal_Secondary", ""),
            external_primary=hosts_raw.get("External_Primary", ""),
            external_secondary=hosts_raw.get("External_Secondary", ""),
        )
        servers.append(Server(name=name, hosts=hosts))
    return servers


@dataclass
class ImportResult:
    imported_count: int
    renamed_count: int


def import_legacy_into_store(path: Path, store: ServerStore) -> ImportResult:
    """Import from legacy JSON into the given ServerStore with collision handling.

    - Existing names are not overwritten.
    - Duplicates are auto-renamed as \"Name (imported 2)\", \"Name (imported 3)\", ...
    """

    servers = import_legacy_servers(path)
    existing_names = {s.name for s in store.list_servers()}
    imported = 0
    renamed = 0

    for server in servers:
        base = server.name.strip()
        if not base:
            continue
        candidate = base
        suffix = 2
        while candidate in existing_names:
            candidate = f"{base} (imported {suffix})"
            suffix += 1
        if candidate != server.name:
            renamed += 1
        to_save = Server(name=candidate, hosts=server.hosts)
        store.create_server(to_save)
        existing_names.add(candidate)
        imported += 1

    return ImportResult(imported_count=imported, renamed_count=renamed)

