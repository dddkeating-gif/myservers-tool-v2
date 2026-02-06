from myservers.connectors.host_select import candidate_hosts, choose_best_host
from myservers.core.models import HostSet, Server


def test_candidate_hosts_priority_order() -> None:
    server = Server(
        name="Test",
        hosts=HostSet(
            internal_primary="10.0.0.1",
            internal_secondary="10.0.0.2",
            external_primary="203.0.113.1",
            external_secondary="203.0.113.2",
        ),
    )
    candidates = candidate_hosts(server)
    assert candidates == ["10.0.0.1", "10.0.0.2", "203.0.113.1", "203.0.113.2"]


def test_candidate_hosts_skips_empty() -> None:
    server = Server(
        name="Test",
        hosts=HostSet(
            internal_primary="10.0.0.1",
            internal_secondary="",
            external_primary="203.0.113.1",
            external_secondary="",
        ),
    )
    candidates = candidate_hosts(server)
    assert candidates == ["10.0.0.1", "203.0.113.1"]


def test_choose_best_host_returns_first() -> None:
    server = Server(
        name="Test",
        hosts=HostSet(internal_primary="10.0.0.1", internal_secondary="10.0.0.2"),
    )
    assert choose_best_host(server) == "10.0.0.1"


def test_choose_best_host_returns_none_if_all_empty() -> None:
    server = Server(name="Test", hosts=HostSet())
    assert choose_best_host(server) is None
