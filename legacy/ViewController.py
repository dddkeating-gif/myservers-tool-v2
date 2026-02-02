# This Python file uses the following encoding: utf-8
import secrets
import json, sys, random, base64
from unicodedata import name
from support.support_variables import *
#from support.support_functions import *
from support.support_functions import MainFileIO, GenUUID, DebugPrint
from pathlib import Path
import subprocess
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QDockWidget,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

#####################################################################################
#  CODE      ++++++++      CODE      ++++++++      CODE     ++++++++      CODE  ####
#####################################################################################
#== Layout Sections ======================================================
class TabBar(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("tabBar")
        self.setFixedHeight(75)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)
        self._home_button = QPushButton("Home")
        self._home_button.setObjectName("tabHomeButton")
        self._home_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self._home_button, alignment=Qt.AlignLeft)
        layout.addStretch()

    def set_home_action(self, handler) -> None:
        if handler is None:
            return
        self._home_button.clicked.connect(handler)


class MainView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    def set_content(self, widget: QWidget) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            child = item.widget()
            if child is not None:
                child.setParent(None)
        self._layout.addWidget(widget)


class CommandBar(QFrame):
    def __init__(self, actions: dict | None = None, on_action=None) -> None:
        super().__init__()
        self.setObjectName("functionBar")
        self.setFixedHeight(36)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 4, 12, 4)
        self._layout.setSpacing(8)
        self._on_action = on_action
        self._layout.addStretch()
        self._settings_button = QPushButton("Settings")
        self._settings_button.setObjectName("functionButton")
        self._settings_button.setCursor(Qt.PointingHandCursor)
        self._layout.addWidget(self._settings_button)
        self.set_buttons(actions or {})

    def set_buttons(self, actions: dict, on_action=None) -> None:
        if on_action is not None:
            self._on_action = on_action
        while self._layout.count() > 2:
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for label, action_id in actions.items():
            button = QPushButton(str(label))
            button.setObjectName("functionButton")
            button.setCursor(Qt.PointingHandCursor)
            if self._on_action and action_id:
                button.clicked.connect(lambda _=False, aid=action_id: self._on_action(aid))
            else:
                button.setEnabled(False)
            self._layout.insertWidget(self._layout.count() - 2, button)


# Page name <-> index for tests and navigation
_PAGE_NAME_TO_INDEX = {"Home": 0, "ServerHome": 1, "NewServer": 2, "EditServer": 3, "Settings": 4}
_INDEX_TO_PAGE_NAME = {v: k for k, v in _PAGE_NAME_TO_INDEX.items()}
_PAGE_INDEX_FUNCTIONS = {2: [("Save", "servers.save"), ("Cancel", "servers.cancel")]}


#== Main Application Window ==============================================
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MyServer Pro")
        
        self.FileIO = MainFileIO()
        self._server_InternalPrimaryHost_value = ""
        self._server_InternalSecondaryHost_value = ""
        self._server_ExternalPrimaryHost_value = ""
        self._server_ExternalSecondaryHost_value = ""

        self._build_main_window()
        self._apply_style()
    
    def _build_main_window(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self._tab_bar = TabBar()
        layout.addWidget(self._tab_bar)

        self._stack = QStackedWidget()
        for _ in range(5):
            self._stack.addWidget(QWidget())
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 18, 24, 14)
        content_layout.setSpacing(0)

        self._main_view = MainView()
        content_layout.addWidget(self._main_view)
        layout.addWidget(content)
        
        self._page_views = {}
        

        self._function_bar = CommandBar()
        layout.addWidget(self._function_bar)
        self.setCentralWidget(central)

    def set_main_view(self, widget: QWidget) -> None:
        self._main_view.set_content(widget)

    def set_command_actions(self, actions: dict, on_action=None) -> None:
        self._function_bar.set_buttons(actions, on_action=on_action)

    def set_home_action(self, handler) -> None:
        self._tab_bar.set_home_action(handler)

    def _get_page_info(self, entry, get_NameIndex=False, get_IndexName=False, get_Functions=False):
        if get_NameIndex and isinstance(entry, str):
            return _PAGE_NAME_TO_INDEX.get(entry, 0)
        if get_IndexName and isinstance(entry, int):
            return _INDEX_TO_PAGE_NAME.get(entry, "Home")
        if get_Functions and isinstance(entry, int):
            return _PAGE_INDEX_FUNCTIONS.get(entry, [])
        return None

    def _call_MainPage(self, name_or_index) -> None:
        if isinstance(name_or_index, str) and name_or_index.isdigit():
            self._stack.setCurrentIndex(int(name_or_index))
        else:
            idx = _PAGE_NAME_TO_INDEX.get(name_or_index, 0)
            self._stack.setCurrentIndex(idx)

    def _confirm_delete(self, name: str) -> bool:
        if not name:
            return False
        reply = QMessageBox.question(
            self, "Confirm", f"Delete {name}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        return reply == QMessageBox.Yes

    def _get_payload(self, section: str, name: str, uuid: str) -> dict:
        return {
            uuid: True,
            "Hosts": {
                "Internal_Primary": getattr(self, "_server_InternalPrimaryHost_value", ""),
                "Internal_Secondary": getattr(self, "_server_InternalSecondaryHost_value", ""),
                "External_Primary": getattr(self, "_server_ExternalPrimaryHost_value", ""),
                "External_Secondary": getattr(self, "_server_ExternalSecondaryHost_value", ""),
            },
        }

    def _apply_style(self) -> None:
        main_bg = "#1c1e2b"
        header_color = "#2d2f42"
        entry_color = "#3f414f"
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: """
            + main_bg
            + """;
            }
            QMainWindow::separator {
                background-color: #1c1e2b;
                width: 1px;
            }
            QDockWidget {
                border: none;
            }
            #leftPanel {
                background-color: #212536;
                border-right: 1px solid #272b3a;
            }
            #mainHeader {
                color: #f2f2f4;
                font-size: 18px;
                font-weight: 600;
            }
            #functionBar {
                background-color: #2d2f42;
            }
            #tabBar {
                background-color: #000000;
            }
            #dockToggleBar {
                background-color: rgb(28, 35, 47);
            }
            #addHeader {
                background-color: #2a2e40;
                border-radius: 14px;
            }
            #serverIcon {
                background-color: #3b3f52;
                border-radius: 12px;
            }
            #serverNavButton {
                background-color: #3b3f52;
                color: #e8e8ea;
                border: none;
                border-radius: 10px;
                padding: 6px 10px;
                font-size: 18px;
            }
            #serverNavButton:checked {
                border: 3px solid lime;
            }
            #serverNameField {
                background-color: #3b3f52;
                color: #e8e8ea;
                border: none;
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 16px;
                font-weight: 600;
            }
            #sectionFrame {
                background-color: #2a2e40;
                border-radius: 12px;
            }
            #serverGridGroup {
                border-radius: 12px;
                padding: 15px;
            }
            #sectionTitle {
                color: #c9cbd2;
                font-weight: 600;
            }
            #sectionFrame QLabel {
                color: #cfd1d8;
                font-size: 12px;
            }
            #inputField {
                background-color: #3b3f52;
                color: #e8e8ea;
                border: none;
                border-radius: 8px;
                padding: 6px 10px;
            }
            #accountRow {
                background-color: #3b3f52;
                border-radius: 8px;
            }
            #accountAction {
                color: #cfd1d8;
                font-weight: 600;
            }
            #accountName {
                color: #e1e3ea;
                font-weight: 600;
            }
            #connectionToggle {
                color: #cfd1d8;
                font-weight: 600;
                background-color: #3b3f52;
                border: none;
                border-radius: 9px;
                padding: 6px 10px;
            }
            #connectionToggle:checked {
                background-color: #2d6f92;
                color: #f2f2f4;
            }
            #identityManagerButton {
                background-color: #3b3f52;
                color: #e1e3ea;
                border: none;
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: 600;
            }
            #identityManagerButton:hover {
                background-color: #43485d;
            }
            #navIcon {
                border-radius: 0px;
            }
            #navLabel {
                color: #f2f2f4;
                font-size: 14px;
                font-weight: 600;
            }
            QLabel[isHome="true"] {
                font-size: 42px;
            }
            QWidget[selected="true"] {
                background-color: #2a2e40;
                border-radius: 8px;
            }
            #addServerButton {
                color: #f2f2f4;
                font-size: 13px;
                font-weight: 600;
                padding: 4px 2px;
            }
            """
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(900, 600)
    window.show()
    sys.exit(app.exec())
