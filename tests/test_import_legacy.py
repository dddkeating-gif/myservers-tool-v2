from pathlib import Path
import json

import pytest

from myservers.core.import_legacy import import_legacy_servers, import_legacy_into_store
from myservers.core.servers import ServerStore


def _make_legacy_file(tmp_path: Path) -> Path:
    data = {
        "Servers": {
            "ServerA": {
                "abc123": {},
                "Hosts": {
                    "Internal_Primary": "10.0.0.1",
                    "Internal_Secondary": "10.0.0.2",
                    "External_Primary": "203.0.113.1",
                    "External_Secondary": "203.0.113.2",
                },
                "SSH": {},
                "WEB": {},
            },
            "ServerB": {
                "def456": {},
                "Hosts": {
                    "Internal_Primary": "10.0.1.1",
                    "Internal_Secondary": "10.0.1.2",
                    "External_Primary": "203.0.114.1",
                    "External_Secondary": "203.0.114.2",
                },
                "SSH": {},
                "WEB": {},
            },
        }
    }
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_legacy_import_reads_two_servers(tmp_path: Path) -> None:
    legacy_path = _make_legacy_file(tmp_path)
    servers = import_legacy_servers(legacy_path)
    assert len(servers) == 2
    names = {s.name for s in servers}
    assert names == {"ServerA", "ServerB"}
    server_a = next(s for s in servers if s.name == "ServerA")
    assert server_a.hosts.internal_primary == "10.0.0.1"
    assert server_a.hosts.external_secondary == "203.0.113.2"


def test_legacy_import_collision_renames(tmp_path: Path) -> None:
    # existing data with ServerA
    store_path = tmp_path / "data.json"
    store = ServerStore(store_path)
    # create existing ServerA
    from myservers.core.models import Server, HostSet

    store.create_server(
        Server(
            name="ServerA",
            hosts=HostSet(
                internal_primary="10.0.0.10",
                internal_secondary="",
                external_primary="",
                external_secondary="",
            ),
        )
    )

    legacy_path = _make_legacy_file(tmp_path)
    result = import_legacy_into_store(legacy_path, store)
    assert result.imported_count == 2
    # one of them should have been renamed due to collision on ServerA
    assert result.renamed_count == 1

    names = {s.name for s in store.list_servers()}
    assert "ServerA" in names
    # ensure a renamed variant exists
    renamed = [n for n in names if n.startswith("ServerA (imported")]
    assert renamed, "Expected a renamed imported server"


def test_server_store_crud_via_jsonstore(tmp_path: Path) -> None:
    from myservers.core.models import Server, HostSet

    store = ServerStore(tmp_path / "servers.json")

    s1 = Server(name="Test", hosts=HostSet(internal_primary="10.0.0.1"))
    store.create_server(s1)
    fetched = store.get_server("Test")
    assert fetched is not None and fetched.hosts.internal_primary == "10.0.0.1"

    s1_edit = Server(name="TestRenamed", hosts=HostSet(internal_primary="10.0.0.2"))
    store.update_server("Test", s1_edit)
    assert store.get_server("Test") is None
    fetched2 = store.get_server("TestRenamed")
    assert fetched2 is not None and fetched2.hosts.internal_primary == "10.0.0.2"

    store.delete_server("TestRenamed")
    assert store.get_server("TestRenamed") is None

