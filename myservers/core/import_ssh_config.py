from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from myservers.core.identities_store import IdentitiesStore, IdentityMeta
from myservers.core.models import HostSet, Server
from myservers.core.servers import ServerStore


@dataclass
class SshConfigCandidate:
    """Single host entry discovered in an SSH config."""

    host_alias: str
    host_name: str
    username: Optional[str]
    port: Optional[int]
    identity_file: Optional[str]


def parse_ssh_config(text: str) -> List[SshConfigCandidate]:
    """Parse a minimal subset of OpenSSH config syntax.

    Supported directives per task requirements:
    - Host <pattern> (we ignore wildcard-only patterns like '*')
    - HostName
    - User
    - Port
    - IdentityFile

    We only keep concrete host aliases (no wildcards) and ignore the
    implicit wildcard Host * section by default.
    """

    candidates: list[SshConfigCandidate] = []

    current_aliases: list[str] = []
    host_name: Optional[str] = None
    user: Optional[str] = None
    port: Optional[int] = None
    identity_file: Optional[str] = None

    def _flush() -> None:
        nonlocal current_aliases, host_name, user, port, identity_file
        if not current_aliases:
            return
        # Ignore wildcard-only or obviously pattern-based host entries by default.
        filtered_aliases = [
            a for a in current_aliases if "*" not in a and "?" not in a and a.strip() != "*"
        ]
        if not filtered_aliases:
            current_aliases = []
            host_name = None
            user = None
            port = None
            identity_file = None
            return

        # Use the first alias as the primary server name.
        primary_alias = filtered_aliases[0]
        # If HostName not set, use alias as address.
        target_host = (host_name or primary_alias).strip()

        candidates.append(
            SshConfigCandidate(
                host_alias=primary_alias.strip(),
                host_name=target_host,
                username=(user or "").strip() or None,
                port=port,
                identity_file=(identity_file or "").strip() or None,
            )
        )

        current_aliases = []
        host_name = None
        user = None
        port = None
        identity_file = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        if not parts:
            continue

        key = parts[0]
        value = " ".join(parts[1:])

        if key.lower() == "host":
            # Start of a new host block.
            _flush()
            # Host may list several aliases; we keep all for now.
            current_aliases = value.split()
        elif not current_aliases:
            # Ignore directives outside of host blocks.
            continue
        else:
            kl = key.lower()
            if kl == "hostname":
                host_name = value
            elif kl == "user":
                user = value
            elif kl == "port":
                try:
                    port = int(value)
                except ValueError:
                    port = None
            elif kl == "identityfile":
                # Only metadata: file path; we do NOT touch key contents.
                identity_file = value

    # Flush last host block.
    _flush()
    return candidates


def _find_identity_by_key_path(
    store: IdentitiesStore, key_path: str
) -> Optional[IdentityMeta]:
    """Return existing identity with kind='ssh_key_path' and matching key_path, if any."""
    key_path_norm = key_path.strip()
    if not key_path_norm:
        return None
    for ident in store.list_identities():
        if ident.kind == "ssh_key_path" and (ident.key_path or "").strip() == key_path_norm:
            return ident
    return None


def apply_ssh_config_import(
    candidates: List[SshConfigCandidate],
    server_store: ServerStore,
    identities: IdentitiesStore,
) -> None:
    """Apply selected SSH config candidates into servers + ssh_profiles + identities.

    Behaviour:
    - Create or update servers:
        * Server name == host_alias
        * internal_primary is set to host_name (other host fields preserved if updating)
    - Create or update ssh_profile for each server:
        * port from candidate (default 22)
        * username_override from candidate.username (if provided)
        * identity_id referencing an IdentityMeta (kind='ssh_key_path') when key_path provided
    - Identity metadata:
        * kind='ssh_key_path'
        * key_path stored in key_path column
        * NEVER store key contents or touch keyring for ssh_key_path identities
        * de-duplicate by key_path
    """

    for cand in candidates:
        alias = cand.host_alias.strip()
        if not alias:
            continue

        # Ensure a server entry exists (update existing if found).
        existing = server_store.get_server(alias)
        if existing is None:
            hosts = HostSet(internal_primary=cand.host_name)
            server = Server(name=alias, hosts=hosts)
            server_store.create_server(server)
        else:
            # Update internal_primary but keep other host fields as-is.
            hosts = HostSet(
                internal_primary=cand.host_name,
                internal_secondary=existing.hosts.internal_secondary,
                external_primary=existing.hosts.external_primary,
                external_secondary=existing.hosts.external_secondary,
            )
            server_store.update_server(existing.name, Server(name=existing.name, hosts=hosts))

        # Decide on identity metadata.
        identity_id: Optional[int] = None
        if cand.identity_file:
            existing_ident = _find_identity_by_key_path(identities, cand.identity_file)
            if existing_ident is not None:
                identity_id = existing_ident.id
            else:
                # Create new metadata-only identity for this key path.
                # We never touch keyring for ssh_key_path identities.
                from os.path import basename

                name = f"ssh-key:{basename(cand.identity_file)}"
                identity_id = identities.create_identity_metadata(
                    name=name,
                    username=cand.username,
                    kind="ssh_key_path",
                    key_path=cand.identity_file,
                )

        # Upsert SSH profile for this server.
        port = cand.port if cand.port is not None else 22
        username_override = cand.username or None
        identities.set_ssh_profile(alias, port=port, identity_id=identity_id, username_override=username_override)

