from __future__ import annotations

import subprocess
import time
from typing import Tuple


def execute(command: str, timeout_s: int = 60) -> Tuple[int, str, str, int]:
    """Execute a local shell command.

    Returns (exit_code, stdout, stderr, duration_ms).
    """
    start = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            shell=True,
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
    duration_ms = int((time.monotonic() - start) * 1000)
    return exit_code, stdout, stderr, duration_ms

