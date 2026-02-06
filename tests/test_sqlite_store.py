from pathlib import Path

from myservers.core.models import Server, HostSet
from myservers.core.servers import ServerStore
from myservers.storage.sqlite_store import SqliteStore
from myservers.storage.json_store import JsonStore


def test_sqlite_crud(tmp_path: Path) -> None:
    db_path = tmp_path / "data.sqlite3"
    backend = SqliteStore(db_path)
    store = ServerStore(backend)

    s1 = Server(name="Test", hosts=HostSet(internal_primary="10.0.0.1"))
    store.create_server(s1)
    got = store.get_server("Test")
    assert got is not None
    assert got.hosts.internal_primary == "10.0.0.1"

    s1b = Server(name="TestRenamed", hosts=HostSet(internal_primary="10.0.0.2"))
    store.update_server("Test", s1b)
    assert store.get_server("Test") is None
    got2 = store.get_server("TestRenamed")
    assert got2 is not None
    assert got2.hosts.internal_primary == "10.0.0.2"

    store.delete_server("TestRenamed")
    assert store.get_server("TestRenamed") is None


def test_sqlite_migration_from_json(tmp_path: Path) -> None:
    json_path = tmp_path / "data.json"
    db_path = tmp_path / "data.sqlite3"

    # Prepare v2-style JSON using JsonStore
    js = JsonStore(json_path)
    js.set(
        "Servers",
        "JsonServer",
        {
            "Hosts": {
                "Internal_Primary": "10.10.0.1",
                "Internal_Secondary": "10.10.0.2",
                "External_Primary": "198.51.100.1",
                "External_Secondary": "198.51.100.2",
            }
        },
    )

    # First SqliteStore init should migrate from JSON
    backend = SqliteStore(db_path, json_migration_path=json_path)
    store = ServerStore(backend)
    servers = store.list_servers()
    names = {s.name for s in servers}
    assert "JsonServer" in names
    migrated = next(s for s in servers if s.name == "JsonServer")
    assert migrated.hosts.internal_primary == "10.10.0.1"
    assert migrated.hosts.external_secondary == "198.51.100.2"

