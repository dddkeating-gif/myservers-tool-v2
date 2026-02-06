from pathlib import Path

from myservers.core.models import Server, HostSet
from myservers.core.servers import ServerStore
from myservers.core.web_links_store import WebLinksStore
from myservers.storage.sqlite_store import SqliteStore


def test_web_links_crud(tmp_path: Path) -> None:
    db_path = tmp_path / "data.sqlite3"
    backend = SqliteStore(db_path)
    store = ServerStore(backend)
    links_store = WebLinksStore(backend)

    s = Server(name="Srv1", hosts=HostSet(internal_primary="10.0.0.1"))
    store.create_server(s)

    link_id = links_store.create_link("Srv1", "Dashboard", "https://example.com/dash")
    links = links_store.list_links("Srv1")
    assert len(links) == 1
    assert links[0].label == "Dashboard"
    assert links[0].url == "https://example.com/dash"

    links_store.update_link(link_id, "Admin Panel", "https://example.com/admin")
    links = links_store.list_links("Srv1")
    assert links[0].label == "Admin Panel"
    assert links[0].url == "https://example.com/admin"

    links_store.delete_link(link_id)
    links = links_store.list_links("Srv1")
    assert len(links) == 0
