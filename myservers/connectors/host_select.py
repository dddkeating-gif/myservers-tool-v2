from __future__ import annotations

from myservers.core.models import Server


def candidate_hosts(server: Server) -> list[str]:
    """Return hosts in priority order: internal_primary, internal_secondary, external_primary, external_secondary.
    Skips empty strings.
    """
    hosts = []
    if server.hosts.internal_primary:
        hosts.append(server.hosts.internal_primary)
    if server.hosts.internal_secondary:
        hosts.append(server.hosts.internal_secondary)
    if server.hosts.external_primary:
        hosts.append(server.hosts.external_primary)
    if server.hosts.external_secondary:
        hosts.append(server.hosts.external_secondary)
    return hosts


def choose_best_host(server: Server) -> str | None:
    """Return first non-empty host in priority order, or None if all empty."""
    candidates = candidate_hosts(server)
    return candidates[0] if candidates else None
