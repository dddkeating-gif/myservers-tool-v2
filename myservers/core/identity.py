from __future__ import annotations

"""Keyring-backed secret management for identities.

Secrets are stored ONLY in the OS keyring, never in SQLite or JSON.
"""

from typing import Optional

import keyring

from myservers.core.identities_store import IdentitiesStore

SERVICE_NAME = "myservers-tool-v2"


def _key(identity_id: int) -> str:
    return f"identity:{identity_id}"


def create_identity(
    store: IdentitiesStore,
    name: str,
    username: str | None,
    kind: str,
    secret: str,
) -> int:
    """Create identity metadata + store secret in keyring."""
    identity_id = store.create_identity_metadata(name, username, kind)
    keyring.set_password(SERVICE_NAME, _key(identity_id), secret)
    return identity_id


def update_identity(
    store: IdentitiesStore,
    identity_id: int,
    name: str,
    username: str | None,
    kind: str,
    secret_optional: Optional[str] = None,
) -> None:
    """Update identity metadata and optionally rotate secret."""
    store.update_identity_metadata(identity_id, name, username, kind)
    if secret_optional is not None:
        keyring.set_password(SERVICE_NAME, _key(identity_id), secret_optional)


def delete_identity(store: IdentitiesStore, identity_id: int) -> None:
    """Delete identity metadata and remove secret from keyring."""
    store.delete_identity_metadata(identity_id)
    try:
        keyring.delete_password(SERVICE_NAME, _key(identity_id))
    except Exception:
        # If the secret is already gone, treat as success.
        pass


def get_secret(identity_id: int) -> Optional[str]:
    """Lookup secret for identity_id in keyring."""
    return keyring.get_password(SERVICE_NAME, _key(identity_id))

