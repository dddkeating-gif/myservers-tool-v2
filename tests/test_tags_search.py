from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from myservers.core.models import HostSet, Server
from myservers.core.servers import ServerStore
from myservers.core.tags_store import ServerFilterItem, TagStore, filter_servers
from myservers.storage.sqlite_store import SqliteStore


def test_tag_persistence_crud(tmp_path: Path) -> None:
    db_path = tmp_path / "data.sqlite3"
    backend = SqliteStore(db_path)
    store = ServerStore(backend)
    tags = TagStore(backend)

    # Create servers
    s1 = Server(name="app1", hosts=HostSet(internal_primary="10.0.0.1"))
    s2 = Server(name="db1", hosts=HostSet(internal_primary="10.0.0.2"))
    store.create_server(s1)
    store.create_server(s2)

    # Set tags
    tags.set_server_tags("app1", ["Prod", "frontend", " prod "])
    tags.set_server_tags("db1", ["prod", "database"])

    # list_tags should show normalized, unique, sorted tags
    all_tags = tags.list_tags()
    assert all_tags == sorted(["prod", "frontend", "database"])

    # get_server_tags returns normalized, sorted tags per server
    assert tags.get_server_tags("app1") == ["frontend", "prod"]
    assert tags.get_server_tags("db1") == ["database", "prod"]

    # Replace semantics
    tags.set_server_tags("app1", ["staging"])
    assert tags.get_server_tags("app1") == ["staging"]


def test_filter_servers_by_name_hosts_notes_and_tags() -> None:
    items = [
        ServerFilterItem(
            name="app1",
            hosts=HostSet(internal_primary="10.0.0.1"),
            notes="frontend service",
            tags=["prod", "frontend"],
        ),
        ServerFilterItem(
            name="db1",
            hosts=HostSet(internal_primary="10.0.0.2"),
            notes="primary database",
            tags=["prod", "database"],
        ),
        ServerFilterItem(
            name="cache1",
            hosts=HostSet(internal_primary="10.0.0.3"),
            notes="cache tier",
            tags=["staging"],
        ),
    ]

    # Query matches name
    res = filter_servers(items, query="app1", tag=None)
    assert [s.name for s in res] == ["app1"]

    # Query matches host
    res = filter_servers(items, query="10.0.0.2", tag=None)
    assert [s.name for s in res] == ["db1"]

    # Query matches notes
    res = filter_servers(items, query="primary database", tag=None)
    assert [s.name for s in res] == ["db1"]

    # Tag filter alone
    res = filter_servers(items, query="", tag="prod")
    assert sorted(s.name for s in res) == ["app1", "db1"]

    # Tag + query combination
    res = filter_servers(items, query="frontend", tag="prod")
    assert [s.name for s in res] == ["app1"]

