from __future__ import annotations

import subprocess
import time
from typing import Tuple

from myservers.connectors.ssh_command import build_ssh_command
from myservers.core.identities_store import IdentityMeta, SshProfileMeta
from myservers.core.models import Server


def execute_ssh(
    server: Server,
    ssh_profile: SshProfileMeta | None,
    identity: IdentityMeta | None,
    remote_command: str,
    timeout_s: int = 60,
) -> Tuple[int, str, str, int]:
    """Execute a command remotely via SSH.

    Builds SSH invocation with safe options:
    - BatchMode=yes (non-interactive)
    - ConnectTimeout=5
    - StrictHostKeyChecking=accept-new

    Returns (exit_code, stdout, stderr, duration_ms).
    """
    ssh_base = build_ssh_command(server, ssh_profile, identity)
    if not ssh_base:
        return -1, "", "No host available", 0

    # Add safe SSH options and remote command
    ssh_opts = [
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=5",
        "-o", "StrictHostKeyChecking=accept-new",
    ]
    # Parse ssh_base into parts for subprocess (handle quoted paths)
    import shlex
    parts = shlex.split(ssh_base)
    ssh_cmd = parts[0]  # "ssh"
    ssh_args = parts[1:] + ssh_opts + ["--", remote_command]

    start = time.monotonic()
    try:
        proc = subprocess.run(
            [ssh_cmd] + ssh_args,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        exit_code = proc.returncode
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
    except subprocess.TimeoutExpired as exc:
        exit_code = -1
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + "\n[timeout]"
    except FileNotFoundError:
        exit_code = -1
        stdout = ""
        stderr = "ssh command not found"
    duration_ms = int((time.monotonic() - start) * 1000)
    return exit_code, stdout, stderr, duration_ms


def build_ssh_invocation_string(
    server: Server,
    ssh_profile: SshProfileMeta | None,
    identity: IdentityMeta | None,
    remote_command: str,
) -> str:
    """Build full SSH invocation string for preview (sanitized, no secrets)."""
    ssh_base = build_ssh_command(server, ssh_profile, identity)
    if not ssh_base:
        return ""
    opts = "-o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new"
    return f"{ssh_base} {opts} -- {remote_command}"
