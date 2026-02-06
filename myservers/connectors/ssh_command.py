from __future__ import annotations

from myservers.connectors.host_select import choose_best_host
from myservers.core.identities_store import IdentityMeta, SshProfileMeta
from myservers.core.models import Server


def build_ssh_command(
    server: Server,
    ssh_profile: SshProfileMeta | None,
    identity: IdentityMeta | None,
) -> str:
    """Build SSH command string. Never embeds password/token secrets.

    Format: ssh -p <port> -i "<key_path>" <user>@<host>
    - Omit -i if no key_path
    - Omit user@ if no user
    - Use ssh_profile.port if set, else 22
    - Username: ssh_profile.username_override or identity.username or ""
    - key_path: identity.key_path (only for kind='ssh_key_path')
    """
    host = choose_best_host(server)
    if not host:
        return ""

    port = ssh_profile.port if ssh_profile else 22
    username = ""
    if ssh_profile and ssh_profile.username_override:
        username = ssh_profile.username_override
    elif identity and identity.username:
        username = identity.username

    key_path = None
    if identity and identity.kind == "ssh_key_path" and identity.key_path:
        key_path = identity.key_path

    parts = ["ssh"]
    if port != 22:
        parts.append(f"-p {port}")
    if key_path:
        parts.append(f'-i "{key_path}"')
    if username:
        parts.append(f"{username}@{host}")
    else:
        parts.append(host)

    return " ".join(parts)
