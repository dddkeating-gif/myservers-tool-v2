# This Python file uses the following encoding: utf-8
"""V2 entrypoint: PySide6 + MainWindow from myservers.ui.main_window.

Uses SQLite storage by default and will migrate from legacy/v2 JSON if present.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from myservers.core.servers import ServerStore
from myservers.storage.sqlite_store import SqliteStore
from myservers.ui.main_window import MainWindow


def _get_default_paths() -> tuple[Path, Path]:
    """Return (sqlite_db_path, legacy_json_path) in the user's home directory."""
    home = Path.home()
    data_dir = home / ".myservers-tool-v2"
    data_dir.mkdir(parents=True, exist_ok=True)
    sqlite_path = data_dir / "data.sqlite3"
    json_path = data_dir / "data.json"
    return sqlite_path, json_path


def main() -> int:
    app = QApplication(sys.argv)
    sqlite_path, json_path = _get_default_paths()
    backend = SqliteStore(sqlite_path, json_migration_path=json_path)
    store = ServerStore(backend)
    window = MainWindow(store)
    window.resize(900, 600)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
