#!/usr/bin/env python3
"""Verify project setup: paths, core imports, JsonStore CRUD, optional GUI."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_PATHS = ["myservers", "tests", "README.md", "requirements.txt"]


def main() -> int:
    # 1) Validate required paths exist
    os.chdir(REPO_ROOT)
    missing = [p for p in REQUIRED_PATHS if not (REPO_ROOT / p).exists()]
    if missing:
        print(f"Missing required paths: {missing}", file=sys.stderr)
        return 1
    print("Required paths OK")

    # 2) Import core modules + JsonStore
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from support.support_functions import MainFileIO  # noqa: F401
        from myservers.core.storage import JsonStore
    except Exception as e:
        print(f"Import failed: {e}", file=sys.stderr)
        return 1
    print("Core imports OK")

    # 3) Minimal JsonStore CRUD using a temp file
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_path = f.name
    try:
        store = JsonStore(tmp_path)
        store.set("sect", "key1", {"a": 1})
        assert store.get("sect", "key1") == {"a": 1}
        store.set("sect", "key2", {"b": 2})
        store.delete("sect", "key1")
        assert store.get("sect", "key1") is None
        assert store.get("sect", "key2") == {"b": 2}
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    print("JsonStore CRUD OK")

    # 4) Attempt GUI imports (PySide6 + MainWindow); if fail, SKIP GUI and exit 0
    try:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from main import MainWindow
        _app = QApplication.instance() or QApplication([])
        _win = MainWindow()
        del _win
        print("GUI imports OK")
    except Exception as e:
        print("SKIP GUI")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
