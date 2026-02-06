from __future__ import annotations

# This Python file uses the following encoding: utf-8
"""Thin UI: MainWindow for v2.

Business logic lives in myservers/core; storage in myservers/storage.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QClipboard, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
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
from myservers.core.identities_store import IdentitiesStore, IdentityMeta, SshProfileMeta
from myservers.core import identity as identity_core
from myservers.core.web_links_store import WebLinksStore, WebLink
from myservers.storage.sqlite_store import SqliteStore
from myservers.connectors.ssh_command import build_ssh_command


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


class IdentityManagerDialog(QDialog):
    """Manage identities (metadata + keyring secrets)."""

    def __init__(self, parent: QWidget | None, store: IdentitiesStore) -> None:
        super().__init__(parent)
        self.setWindowTitle("Identity Manager")
        self._store = store

        layout = QVBoxLayout(self)
        self._list = QListWidget()
        layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        self._add = QPushButton("Add")
        self._edit = QPushButton("Edit")
        self._delete = QPushButton("Delete")
        btn_row.addWidget(self._add)
        btn_row.addWidget(self._edit)
        btn_row.addWidget(self._delete)
        layout.addLayout(btn_row)

        self._add.clicked.connect(self._on_add)
        self._edit.clicked.connect(self._on_edit)
        self._delete.clicked.connect(self._on_delete)

        self._refresh()

    def _refresh(self) -> None:
        self._list.clear()
        for ident in self._store.list_identities():
            item = QListWidgetItem(f"{ident.name} ({ident.kind})")
            item.setData(Qt.UserRole, ident.id)
            self._list.addItem(item)

    def _selected_id(self) -> int | None:
        item = self._list.currentItem()
        if item is None:
            return None
        return int(item.data(Qt.UserRole))

    def _edit_dialog(self, identity: IdentityMeta | None = None) -> tuple[str, str, str, str | None, str | None] | None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Identity")
        form = QFormLayout(dlg)
        name_edit = QLineEdit()
        user_edit = QLineEdit()
        kind_edit = QLineEdit()
        key_path_edit = QLineEdit()
        secret_edit = QLineEdit()
        secret_edit.setEchoMode(QLineEdit.Password)

        if identity is not None:
            name_edit.setText(identity.name)
            user_edit.setText(identity.username or "")
            kind_edit.setText(identity.kind)
            key_path_edit.setText(identity.key_path or "")

        form.addRow("Name", name_edit)
        form.addRow("Username", user_edit)
        form.addRow("Kind", kind_edit)
        form.addRow("Key Path (for ssh_key_path)", key_path_edit)
        form.addRow("Secret (for password/token)", secret_edit)

        btns = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(dlg.accept)
        cancel_btn.clicked.connect(dlg.reject)
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        form.addRow(btns)

        if dlg.exec() != QDialog.Accepted:
            return None
        name = name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Identity", "Name is required.")
            return None
        username = user_edit.text().strip()
        kind = kind_edit.text().strip() or "password"
        key_path = key_path_edit.text().strip() or None
        secret = secret_edit.text()
        return name, username, kind, secret or None, key_path

    def _on_add(self) -> None:
        data = self._edit_dialog(None)
        if data is None:
            return
        name, username, kind, secret, key_path = data
        identity_core.create_identity(self._store, name, username or None, kind, secret or "", key_path)
        self._refresh()

    def _on_edit(self) -> None:
        identity_id = self._selected_id()
        if identity_id is None:
            QMessageBox.information(self, "Identity", "Select an identity first.")
            return
        current = self._store.get_identity(identity_id)
        if current is None:
            self._refresh()
            return
        data = self._edit_dialog(current)
        if data is None:
            return
        name, username, kind, secret, key_path = data
        identity_core.update_identity(self._store, identity_id, name, username or None, kind, secret, key_path)
        self._refresh()

    def _on_delete(self) -> None:
        identity_id = self._selected_id()
        if identity_id is None:
            return
        reply = QMessageBox.question(
            self,
            "Delete identity",
            "Delete selected identity?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        identity_core.delete_identity(self._store, identity_id)
        self._refresh()


class SshProfileDialog(QDialog):
    """Edit SSH profile metadata for a server."""

    def __init__(
        self,
        parent: QWidget | None,
        profile: SshProfileMeta,
        identities: list[IdentityMeta],
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"SSH Settings - {profile.server_name}")
        self._profile = profile
        self._identities = identities

        form = QFormLayout(self)
        self._port_edit = QLineEdit(str(profile.port))
        self._user_override = QLineEdit(profile.username_override or "")
        self._identity_combo = QListWidget()

        form.addRow("Port", self._port_edit)
        form.addRow("Username override", self._user_override)
        form.addRow("Identity", self._identity_combo)

        none_item = QListWidgetItem("<None>")
        none_item.setData(Qt.UserRole, None)
        self._identity_combo.addItem(none_item)

        for ident in identities:
            item = QListWidgetItem(f"{ident.name} ({ident.kind})")
            item.setData(Qt.UserRole, ident.id)
            self._identity_combo.addItem(item)
            if ident.id == profile.identity_id:
                item.setSelected(True)

        btns = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        form.addRow(btns)

    def get_profile(self) -> SshProfileMeta:
        try:
            port = int(self._port_edit.text())
        except ValueError:
            port = 22
        selected_items = self._identity_combo.selectedItems()
        identity_id = None
        if selected_items:
            identity_id = selected_items[0].data(Qt.UserRole)
        username_override = self._user_override.text().strip() or None
        return SshProfileMeta(
            server_name=self._profile.server_name,
            port=port,
            identity_id=identity_id,
            username_override=username_override,
        )


class WebLinksDialog(QDialog):
    """Edit web links for a server."""

    def __init__(self, parent: QWidget | None, server_name: str, store: WebLinksStore) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Web Links - {server_name}")
        self._server_name = server_name
        self._store = store

        layout = QVBoxLayout(self)
        self._list = QListWidget()
        layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        self._add = QPushButton("Add")
        self._edit = QPushButton("Edit")
        self._delete = QPushButton("Delete")
        btn_row.addWidget(self._add)
        btn_row.addWidget(self._edit)
        btn_row.addWidget(self._delete)
        layout.addLayout(btn_row)

        btns = QHBoxLayout()
        ok_btn = QPushButton("Close")
        ok_btn.clicked.connect(self.accept)
        btns.addWidget(ok_btn)
        layout.addLayout(btns)

        self._add.clicked.connect(self._on_add)
        self._edit.clicked.connect(self._on_edit)
        self._delete.clicked.connect(self._on_delete)

        self._refresh()

    def _refresh(self) -> None:
        self._list.clear()
        for link in self._store.list_links(self._server_name):
            item = QListWidgetItem(f"{link.label}: {link.url}")
            item.setData(Qt.UserRole, link.id)
            self._list.addItem(item)

    def _selected_id(self) -> int | None:
        item = self._list.currentItem()
        if item is None:
            return None
        return int(item.data(Qt.UserRole))

    def _edit_dialog(self, link: WebLink | None = None) -> tuple[str, str] | None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Web Link")
        form = QFormLayout(dlg)
        label_edit = QLineEdit()
        url_edit = QLineEdit()

        if link is not None:
            label_edit.setText(link.label)
            url_edit.setText(link.url)

        form.addRow("Label", label_edit)
        form.addRow("URL", url_edit)

        btns = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(dlg.accept)
        cancel_btn.clicked.connect(dlg.reject)
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        form.addRow(btns)

        if dlg.exec() != QDialog.Accepted:
            return None
        label = label_edit.text().strip()
        url = url_edit.text().strip()
        if not label or not url:
            QMessageBox.warning(self, "Web Link", "Label and URL are required.")
            return None
        return label, url

    def _on_add(self) -> None:
        data = self._edit_dialog(None)
        if data is None:
            return
        label, url = data
        self._store.create_link(self._server_name, label, url)
        self._refresh()

    def _on_edit(self) -> None:
        link_id = self._selected_id()
        if link_id is None:
            QMessageBox.information(self, "Web Link", "Select a link first.")
            return
        links = self._store.list_links(self._server_name)
        current = next((l for l in links if l.id == link_id), None)
        if current is None:
            self._refresh()
            return
        data = self._edit_dialog(current)
        if data is None:
            return
        label, url = data
        self._store.update_link(link_id, label, url)
        self._refresh()

    def _on_delete(self) -> None:
        link_id = self._selected_id()
        if link_id is None:
            return
        reply = QMessageBox.question(
            self,
            "Delete link",
            "Delete selected link?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._store.delete_link(link_id)
        self._refresh()


class WebLinkPickerDialog(QDialog):
    """Pick a web link from multiple options."""

    def __init__(self, parent: QWidget | None, links: list[WebLink]) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Web Link")
        self._links = links

        layout = QVBoxLayout(self)
        self._list = QListWidget()
        for link in links:
            item = QListWidgetItem(f"{link.label}: {link.url}")
            item.setData(Qt.UserRole, link.id)
            self._list.addItem(item)
        layout.addWidget(self._list)

        btns = QHBoxLayout()
        ok_btn = QPushButton("Open")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def get_selected(self) -> WebLink | None:
        item = self._list.currentItem()
        if item is None:
            return None
        link_id = int(item.data(Qt.UserRole))
        return next((l for l in self._links if l.id == link_id), None)


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
        self._ssh_btn = QPushButton("SSH Settings...")
        self._identity_btn = QPushButton("Identity Manager...")
        self._copy_ssh_btn = QPushButton("Copy SSH Command")
        self._web_links_btn = QPushButton("Web Links...")
        self._open_web_btn = QPushButton("Open Web...")
        self._import_btn = QPushButton("Import legacy JSON...")
        buttons.addWidget(self._add_btn)
        buttons.addWidget(self._edit_btn)
        buttons.addWidget(self._del_btn)
        buttons.addWidget(self._ssh_btn)
        buttons.addWidget(self._identity_btn)
        buttons.addWidget(self._copy_ssh_btn)
        buttons.addWidget(self._web_links_btn)
        buttons.addWidget(self._open_web_btn)
        buttons.addWidget(self._import_btn)
        layout.addLayout(buttons)

        self._add_btn.clicked.connect(self._on_add)
        self._edit_btn.clicked.connect(self._on_edit)
        self._del_btn.clicked.connect(self._on_delete)
        self._ssh_btn.clicked.connect(self._on_edit_ssh)
        self._identity_btn.clicked.connect(self._on_open_identity_manager)
        self._copy_ssh_btn.clicked.connect(self._on_copy_ssh_command)
        self._web_links_btn.clicked.connect(self._on_edit_web_links)
        self._open_web_btn.clicked.connect(self._on_open_web)
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

    def _ensure_sqlite_backend(self) -> SqliteStore | None:
        backend = getattr(self._store, "_store", None)
        if not isinstance(backend, SqliteStore):
            QMessageBox.information(
                self,
                "Identities",
                "Identities and SSH metadata are only available with the SQLite backend.",
            )
            return None
        return backend

    def _on_open_identity_manager(self) -> None:
        backend = self._ensure_sqlite_backend()
        if backend is None:
            return
        store = IdentitiesStore(backend)
        dlg = IdentityManagerDialog(self, store)
        dlg.exec()

    def _on_edit_ssh(self) -> None:
        name = self._selected_name()
        if not name:
            QMessageBox.information(self, "SSH Settings", "Select a server first.")
            return
        backend = self._ensure_sqlite_backend()
        if backend is None:
            return
        ident_store = IdentitiesStore(backend)
        profile = ident_store.get_ssh_profile(name) or SshProfileMeta(
            server_name=name, port=22, identity_id=None, username_override=None
        )
        identities = ident_store.list_identities()
        dlg = SshProfileDialog(self, profile, identities)
        if dlg.exec() != QDialog.Accepted:
            return
        updated = dlg.get_profile()
        ident_store.set_ssh_profile(
            name,
            updated.port,
            updated.identity_id,
            updated.username_override,
        )

    def _on_copy_ssh_command(self) -> None:
        name = self._selected_name()
        if not name:
            QMessageBox.information(self, "Copy SSH Command", "Select a server first.")
            return
        backend = self._ensure_sqlite_backend()
        if backend is None:
            return
        server = self._store.get_server(name)
        if not server:
            QMessageBox.warning(self, "Copy SSH Command", "Server not found.")
            return
        ident_store = IdentitiesStore(backend)
        profile = ident_store.get_ssh_profile(name)
        identity = None
        if profile and profile.identity_id:
            identity = ident_store.get_identity(profile.identity_id)
        cmd = build_ssh_command(server, profile, identity)
        if not cmd:
            QMessageBox.information(self, "Copy SSH Command", "No host configured for this server.")
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(cmd)
        QMessageBox.information(self, "Copy SSH Command", f"Copied:\n{cmd}")

    def _on_edit_web_links(self) -> None:
        name = self._selected_name()
        if not name:
            QMessageBox.information(self, "Web Links", "Select a server first.")
            return
        backend = self._ensure_sqlite_backend()
        if backend is None:
            return
        links_store = WebLinksStore(backend)
        dlg = WebLinksDialog(self, name, links_store)
        dlg.exec()

    def _on_open_web(self) -> None:
        name = self._selected_name()
        if not name:
            QMessageBox.information(self, "Open Web", "Select a server first.")
            return
        backend = self._ensure_sqlite_backend()
        if backend is None:
            return
        links_store = WebLinksStore(backend)
        links = links_store.list_links(name)
        if not links:
            QMessageBox.information(self, "Open Web", "No web links configured for this server.")
            return
        if len(links) == 1:
            QDesktopServices.openUrl(links[0].url)
        else:
            dlg = WebLinkPickerDialog(self, links)
            if dlg.exec() == QDialog.Accepted:
                selected = dlg.get_selected()
                if selected:
                    QDesktopServices.openUrl(selected.url)

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

