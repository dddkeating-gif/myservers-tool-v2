from __future__ import annotations

# This Python file uses the following encoding: utf-8
"""Thin UI: MainWindow for v2.

Business logic lives in myservers/core; storage in myservers/storage.
"""

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QMessageBox,
    QDialog,
    QFormLayout,
    QLineEdit,
    QFileDialog,
)

from myservers.core.models import Server, HostSet
from myservers.core.servers import ServerStore
from myservers.core.import_legacy import import_legacy_into_store


class ServerDialog(QDialog):
    """Simple dialog to add/edit a server."""

    def __init__(self, parent: QWidget | None = None, server: Server | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Server")
        self._name_edit = QLineEdit()
        self._int_primary = QLineEdit()
        self._int_secondary = QLineEdit()
        self._ext_primary = QLineEdit()
        self._ext_secondary = QLineEdit()

        form = QFormLayout(self)
        form.addRow("Name", self._name_edit)
        form.addRow("Internal primary", self._int_primary)
        form.addRow("Internal secondary", self._int_secondary)
        form.addRow("External primary", self._ext_primary)
        form.addRow("External secondary", self._ext_secondary)

        buttons_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(ok_btn)
        buttons_layout.addWidget(cancel_btn)
        form.addRow(buttons_layout)

        if server is not None:
            self._name_edit.setText(server.name)
            self._int_primary.setText(server.hosts.internal_primary)
            self._int_secondary.setText(server.hosts.internal_secondary)
            self._ext_primary.setText(server.hosts.external_primary)
            self._ext_secondary.setText(server.hosts.external_secondary)

    def get_server(self) -> Server:
        name = self._name_edit.text().strip()
        hosts = HostSet(
            internal_primary=self._int_primary.text().strip(),
            internal_secondary=self._int_secondary.text().strip(),
            external_primary=self._ext_primary.text().strip(),
            external_secondary=self._ext_secondary.text().strip(),
        )
        return Server(name=name, hosts=hosts)


class MainWindow(QMainWindow):
    """v2 main window with thin UI and core-driven CRUD."""

    def __init__(self, store: ServerStore) -> None:
        super().__init__()
        self.setWindowTitle("MyServers")

        self._store = store

        central = QWidget()
        layout = QVBoxLayout(central)
        header = QLabel("MyServers v2")
        layout.addWidget(header)

        self._list = QListWidget()
        layout.addWidget(self._list)

        buttons = QHBoxLayout()
        self._add_btn = QPushButton("Add")
        self._edit_btn = QPushButton("Edit")
        self._del_btn = QPushButton("Delete")
        self._import_btn = QPushButton("Import legacy JSON...")
        buttons.addWidget(self._add_btn)
        buttons.addWidget(self._edit_btn)
        buttons.addWidget(self._del_btn)
        buttons.addWidget(self._import_btn)
        layout.addLayout(buttons)

        self._add_btn.clicked.connect(self._on_add)
        self._edit_btn.clicked.connect(self._on_edit)
        self._del_btn.clicked.connect(self._on_delete)
        self._import_btn.clicked.connect(self._on_import_legacy)

        self.setCentralWidget(central)
        self._refresh_list()

    # -------- internal helpers ---------

    def _refresh_list(self) -> None:
        self._list.clear()
        for server in self._store.list_servers():
            self._list.addItem(server.name)

    def _selected_name(self) -> str | None:
        item = self._list.currentItem()
        return item.text() if item is not None else None

    # -------- actions ---------

    def _on_add(self) -> None:
        dlg = ServerDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        server = dlg.get_server()
        try:
            self._store.create_server(server)
        except ValueError as exc:
            QMessageBox.warning(self, "Add server", str(exc))
            return
        self._refresh_list()

    def _on_edit(self) -> None:
        name = self._selected_name()
        if not name:
            QMessageBox.information(self, "Edit server", "Select a server first.")
            return
        current = self._store.get_server(name)
        if current is None:
            QMessageBox.warning(self, "Edit server", "Server no longer exists.")
            self._refresh_list()
            return

        dlg = ServerDialog(self, current)
        if dlg.exec() != QDialog.Accepted:
            return
        updated = dlg.get_server()
        try:
            self._store.update_server(name, updated)
        except (ValueError, KeyError) as exc:
            QMessageBox.warning(self, "Edit server", str(exc))
            return
        self._refresh_list()

    def _on_delete(self) -> None:
        name = self._selected_name()
        if not name:
            QMessageBox.information(self, "Delete server", "Select a server first.")
            return
        reply = QMessageBox.question(
            self,
            "Confirm delete",
            f"Delete server '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._store.delete_server(name)
        self._refresh_list()

    def _on_import_legacy(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Import legacy JSON",
            "",
            "JSON files (*.json);;All files (*)",
        )
        if not file_name:
            return
        try:
            from myservers.core.import_legacy import ImportResult  # type: ignore
            result = import_legacy_into_store(Path(file_name), self._store)
        except Exception as exc:
            QMessageBox.critical(self, "Import legacy JSON", f"Import failed: {exc}")
            return

        QMessageBox.information(
            self,
            "Import legacy JSON",
            f"Imported {result.imported_count} server(s).\n"
            f"Renamed {result.renamed_count} due to name collisions.",
        )
        self._refresh_list()

