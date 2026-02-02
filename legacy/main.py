# This Python file uses the following encoding: utf-8
import secrets
import json, sys, random, base64
from unicodedata import name
from unittest import case
from support.support_variables import *
#from support.support_functions import *
from support.support_functions import MainFileIO, GenUUID, DebugPrint
from functionbar import FunctionBar
from ViewController import MainWindow as ViewMainWindow

MainWindow = ViewMainWindow  # for tests and verify_setup
from pathlib import Path
import subprocess
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QKeySequence, QShortcut
from PySide6.QtGui import QIcon
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
    QToolButton,
    QVBoxLayout,
    QWidget,
)

pageDefs = {"Pages": {}}
BigProgramDict = { 
    "Pages": {
        "HomeView": {
            "Functions": {
                "Add": "homeview.add",
                "OnSelect": {
                    "Edit": "homeview.edit",
                    "Delete": "homeview.delete"
                }
            },
            "Buttons":{
            }
            
        },
        "ServerView": {

        },
        "ServerEdit":{
            "Functions": {
                "Save": "ServerEdit.save",
                "Delete": "ServerEdit.delete",
                "Cancel": "ServerEdit.cancel"
            },
            "Buttons":{
                "OpenIdentityManager": "ServerEdit.open_identity_manager"
            }
        },
        "Settings": {
                "Functions": {
                    "Apply": "settings.apply",
                    "cancel": "cancel"
                }
            
        }
    },
    "ProgramData": {
        "Servers": {}
    }
}

DebugPrint("",)
DebugPrint("", info=True)
DebugPrint("", warn=True, fromprocess="TestWarn")
DebugPrint("", alert=True)

#####################################################################################
#  CODE      ++++++++      CODE      ++++++++      CODE     ++++++++      CODE  ####
#####################################################################################
#== Main Views ===========================================================
class HomeView(QWidget):
    def __init__(
        self,
        on_view_servers,
        servers: list[str],
        on_select_server,
        on_selection_change=None,
        on_delete_selected=None,
    ) -> None:
        super().__init__()
        servers_from_dict = list(
            BigProgramDict.get("ProgramData", {}).get("Servers", {}).keys()
        )
        if servers_from_dict:
            servers = servers_from_dict

        self._on_view_servers = on_view_servers
        self._on_select_server = on_select_server
        self._on_selection_change = on_selection_change
        self._on_delete_selected = on_delete_selected
        self._home_view_buttons = []
        self._home_view_button_group = QButtonGroup(self)
        self._home_view_button_group.setExclusive(True)
        self._last_selected_button = None
        self._last_selected_name = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        layout.addWidget(self._quick_connect_block())
        layout.addWidget(self._servers_selection_block())

        self.set_homeview_buttons(servers)
        layout.addStretch()
    
    ## Button Setup  ################################################
    def set_homeview_buttons(self, servers: list[str]) -> None:

        servers= self._on_view_servers
        self._home_view_buttons = []
        self._home_view_button_group = QButtonGroup(self)
        self._home_view_button_group.setExclusive(True)
        self._last_selected_button = None
        for idx, name in enumerate(servers):
            button = QPushButton(name)
            button.setObjectName("serverNavButton")
            button.setFlat(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setCheckable(True)
            button.clicked.connect(lambda _=False, b=button, n=name: self._handle_homeview_button_clicks(b, n))
            button.setFixedHeight(65)
            button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            button.setIcon(QIcon("Resources/blankicon.png"))
            button.setIconSize(QSize(50, 50))
            button.setStyleSheet("text-align: left; padding-left: 10px;")
            row = (idx // 2) + 2
            col = idx % 2
            self._servers_layout.addWidget(button, row, col, alignment=Qt.AlignHCenter)
            self._home_view_buttons.append(button)
            self._home_view_button_group.addButton(button)
        self._servers_layout.setColumnStretch(0, 1)
        self._servers_layout.setColumnStretch(1, 1)
        self._update_server_button_widths()
    
    def _handle_homeview_button_clicks(self, button: QPushButton, name: str) -> None:
        DebugPrint("Handling action: {} with handler: {}".format(name, button), "HomeView._handle_homeview_button_clicks")
        if self._last_selected_button is button and button.isChecked():
            self._on_select_server(name)
            DebugPrint("Loop Broken", "HomeView._handle_homeview_button_clicks")
            return
        self._last_selected_button = button
        self._last_selected_name = name
        if self._on_selection_change:
            self._on_selection_change(True)
    
    
    ##  Event Handlers  ################################################
    def mousePressEvent(self, event) -> None:
        DebugPrint("Mouse Press Event Detected in HomeView", "HomeView.mousePressEvent")
        if self._last_selected_button is not None:
            clicked_widget = self.childAt(event.position().toPoint())
            widget = clicked_widget
            while widget is not None and widget is not self:
                if isinstance(widget, QPushButton) and widget in self._home_view_buttons:
                    break
                widget = widget.parent()
            if widget is None or widget is self:
                self._home_view_button_group.setExclusive(False)
                self._last_selected_button.setChecked(False)
                self._home_view_button_group.setExclusive(True)
                self._last_selected_button = None
                self._last_selected_name = None
                if self._on_selection_change:
                    self._on_selection_change(False)
        super().mousePressEvent(event)
    
    def keyPressEvent(self, event) -> None:
        DebugPrint("Key Press Event Detected in HomeView: {}".format(event.key()), "HomeView.keyPressEvent")
        if event.key() == Qt.Key_Delete and self._last_selected_name:
            if self._on_delete_selected:
                self._on_delete_selected(self._last_selected_name)
            return
        super().keyPressEvent(event)
    
    def get_selected_server_name(self) -> str | None:
        return self._last_selected_name
    
    def resizeEvent(self, event) -> None:
        self._update_server_button_widths()
        super().resizeEvent(event)
    
    def _update_server_button_widths(self) -> None:
        target_width = int(self.width() * 0.45)
        for button in self._home_view_buttons:
            button.setFixedWidth(target_width)
        self._servers_container.setFixedHeight(int(self.height() * 0.6))
    
    
    ## UI Blocks  ################################################
    def _quick_connect_block(self) -> QWidget:     # Create Title (Name) Block for Add New Server Page
        header = QFrame()
        header.setObjectName("addHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)
        
        
        section = QFrame()
        section.setObjectName("sectionFrame")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)
        
        self._server_name_field2 = QLineEdit()
        self._server_name_field2.setObjectName("serverNameField")
        self._server_name_field2.setPlaceholderText("SSH Quick Connect")
        self._server_name_value = self._server_name_field2.text()
        self._server_name_field2.textChanged.connect(
            lambda text: setattr(self, "_server_name_value", text)
        )
        header_layout.addWidget(self._server_name_field2)
    
        return header
    
    def _servers_selection_block(self) -> QWidget:
        self._servers_container = QWidget()
        self._servers_container.setObjectName("serverGridGroup")
        self._servers_layout = QGridLayout(self._servers_container)
        self._servers_layout.setContentsMargins(15, 0, 15, 15)
        self._servers_layout.setHorizontalSpacing(12)
        self._servers_layout.setVerticalSpacing(12)
        self._servers_layout.setAlignment(Qt.AlignTop)
        self._servers_banner = QFrame()
        self._servers_banner.setObjectName("serverGridBanner")
        self._servers_banner.setFixedHeight(25)
        self._servers_layout.addWidget(self._servers_banner, 0, 0, 1, 2)
        self._servers_layout.setRowMinimumHeight(1, 15)
        return self._servers_container



class ServerView(QWidget):
    def __init__(self, servers: list[str] | None = None) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._header = QLabel("Server")
        self._header.setObjectName("mainHeader")
        layout.addWidget(self._header)
        self._servers_container = QWidget()
        self._servers_layout = QVBoxLayout(self._servers_container)
        self._servers_layout.setContentsMargins(0, 0, 0, 0)
        self._servers_layout.setSpacing(6)
        layout.addWidget(self._servers_container)
        self.set_homeview_buttons(servers or [])
        layout.addStretch()

    def set_header(self, text: str) -> None:
        self._header.setText(text)

    def set_homeview_buttons(self, servers: list[str]) -> None:
        while self._servers_layout.count():
            item = self._servers_layout.takeAt(0)
            child = item.widget()
            if child is not None:
                child.deleteLater()
        for name in servers:
            label = QLabel(name)
            label.setObjectName("navLabel")
            self._servers_layout.addWidget(label)

class SettingsView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QLabel("Settings")
        header.setObjectName("mainHeader")
        layout.addWidget(header)
        layout.addStretch()
    
    def _function_action(self, a=0):
        print("Function Action called with {} and {}".format(a, b ))

class ServerEdit(QWidget):
    def __init__(self, app_controller) -> None:
        super().__init__()
        self.app_controller = app_controller
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QLabel("Edit Server")
        header.setObjectName("mainHeader")
        layout.addWidget(header)
        layout.addStretch()

    def _page_ServerEdit(self) -> QWidget:       # Create Add New Server Page]
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(8, 6, 8, 0)
        layout.setSpacing(12)

        layout.addWidget(self._server_edit__name_block())
        layout.addWidget(self._server_edit__ip_block())

        bottom_row = QWidget()
        bottom_row_layout = QHBoxLayout(bottom_row)
        bottom_row_layout.setContentsMargins(0, 0, 0, 0)
        bottom_row_layout.setSpacing(12)

        connections = self._server_edit__connections_block()
        identity = self._server_edit__identity_block()
        connections.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        identity.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        bottom_row_layout.addWidget(connections)
        bottom_row_layout.addWidget(identity)
        bottom_row_layout.setAlignment(connections, Qt.AlignTop)
        bottom_row_layout.setAlignment(identity, Qt.AlignTop)
        bottom_row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout.addWidget(bottom_row, 1)

        self._serveredit_buttons_container = QWidget()
        self._serveredit_buttons_layout = QGridLayout(self._serveredit_buttons_container)
        self._serveredit_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self._serveredit_buttons_layout.setHorizontalSpacing(12)
        self._serveredit_buttons_layout.setVerticalSpacing(12)
        layout.addWidget(self._serveredit_buttons_container)
        
        #layout.addWidget(self._build_accounts_section())
        return view
    
    def _server_edit__name_block(self) -> QWidget:     # Create Title (Name) Block for Add New Server Page
        header = QFrame()
        header.setObjectName("addHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(12)
        
        icon = QFrame()
        icon.setObjectName("serverIcon")
        icon.setFixedSize(48, 48)
        header_layout.addWidget(icon)
        
        section = QFrame()
        section.setObjectName("sectionFrame")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)
        
        self._server_name_field2 = QLineEdit()
        self._server_name_field2.setObjectName("serverNameField")
        self._server_name_field2.setPlaceholderText("Server Name")
        self._server_name_field2.setText("test")
        self._server_name_value = self._server_name_field2.text()
        self._server_name_field2.textChanged.connect(
            lambda text: setattr(self, "_server_name_value", text)
        )
        header_layout.addWidget(self._server_name_field2)
    
        return header
    
    def _server_edit__ip_block(self) -> QWidget:       # Create IP / Hostname Block for Add New Server Page
        section = QFrame()
        section.setObjectName("sectionFrame")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)
        
        title = QLabel("IP / Hostname")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        
        primary_label = QLabel("Primary:")
        primary_label.setAlignment(Qt.AlignCenter)
        secondary_label = QLabel("Secondary:")
        secondary_label.setAlignment(Qt.AlignCenter)
        grid.addWidget(primary_label, 0, 1)
        grid.addWidget(secondary_label, 0, 3)
        
        grid.addWidget(QLabel("Internal:"), 1, 0)
        self._InternalPrimaryHost_field = self.app_controller._make_input_field("192.168.1.X")
        self._server_InternalPrimaryHost_value = self._InternalPrimaryHost_field.text()
        self._InternalPrimaryHost_field.textChanged.connect(
            lambda text: setattr(self, "_server_InternalPrimaryHost_value", text)
        )
        grid.addWidget(self._InternalPrimaryHost_field, 1, 1)
        
        self._InternalSecondaryHost_field = self.app_controller._make_input_field("192.168.1.X")
        self._server_InternalSecondaryHost_value = self._InternalSecondaryHost_field.text()
        self._InternalSecondaryHost_field.textChanged.connect(
            lambda text: setattr(self, "_server_InternalSecondaryHost_value", text)
        )
        grid.addWidget(self._InternalSecondaryHost_field, 1, 3)

        grid.addWidget(QLabel("External:"), 2, 0)
        self._ExternalPrimaryHost_field = self.app_controller._make_input_field("192.168.1.X")
        self._server_ExternalPrimaryHost_value = self._ExternalPrimaryHost_field.text()
        self._ExternalPrimaryHost_field.textChanged.connect(
            lambda text: setattr(self, "_server_ExternalPrimaryHost_value", text)
        )
        grid.addWidget(self._ExternalPrimaryHost_field, 2, 1)
        
        self._ExternalSecondaryHost_field = self.app_controller._make_input_field("192.168.1.X")
        self._server_ExternalSecondaryHost_value = self._ExternalSecondaryHost_field.text()
        self._ExternalSecondaryHost_field.textChanged.connect(
            lambda text: setattr(self, "_server_ExternalSecondaryHost_value", text)
        )
        grid.addWidget(self._ExternalSecondaryHost_field, 2, 3)

        layout.addLayout(grid)
        return section
    
    def _server_edit__connections_block(self) -> QWidget:   # Create Connections Block for Add New Server Page
        section = QFrame()
        section.setObjectName("sectionFrame")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Connections")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

    

        return section
    
    def _server_edit__identity_block(self) -> QWidget: # Create Identity Block for Add New Server Page
        section = QFrame()
        section.setObjectName("sectionFrame")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Identities")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        open_button = QPushButton("Open Identity Manager")
        open_button.setObjectName("identityManagerButton")
        open_button.setCursor(Qt.PointingHandCursor)
        open_button.clicked.connect(self.app_controller._open_identity_manager)
        layout.addWidget(open_button, alignment=Qt.AlignLeft)
        layout.addStretch()

        return section
    
    def set_ServerEdit_buttons(self, buttons: list[str]) -> None:
        if not hasattr(self, "_serveredit_buttons_layout"):
            return
        while self._serveredit_buttons_layout.count():
            item = self._serveredit_buttons_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for idx, name in enumerate(buttons):
            button = QPushButton(name)
            button.setObjectName("serverNavButton")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _=False, n=name: self._handle_homeview_button_clicks(None, n))
            row = idx // 2
            col = idx % 2
            self._serveredit_buttons_layout.addWidget(button, row, col, alignment=Qt.AlignLeft)
    

    def _handle_homeview_button_clicks(self, button: QPushButton, name: str) -> None:
        DebugPrint("Handling action: {} with handler: {}".format(name, button), "HomeView._handle_homeview_button_clicks")
        if name is "OpenIdentityManager":
            script_path = Path(__file__).with_name("IdentyManager.py")
            subprocess.Popen([sys.executable, str(script_path)])

    def mousePressEvent(self, event) -> None:
        DebugPrint("Mouse Press Event Detected in ServerEdit", "ServerEdit.mousePressEvent")
        if self._last_selected_button is not None:
            clicked_widget = self.childAt(event.position().toPoint())
            widget = clicked_widget
            while widget is not None and widget is not self:
                if isinstance(widget, QPushButton) and widget in self._serveredit_buttons:
                    break
                widget = widget.parent()
            if widget is None or widget is self:
                self._serveredit_buttons_layout.setExclusive(False)
                self._last_selected_button.setChecked(False)
                self._serveredit_buttons_layout.setExclusive(True)
                self._last_selected_button = None
                self._last_selected_name = None
                if self._on_selection_change:
                    self._on_selection_change(False)
        super().mousePressEvent(event)
    


class AppController:
    def __init__(self) -> None:
        self.fileio = MainFileIO()
        self._load_program_data()
        self.window = ViewMainWindow()
        self.server_view = ServerView([])
        self.server_edit = ServerEdit(self)
        self.settings_view = SettingsView()
        self.show_page=None
        self.home_view = HomeView(
            self.get_server_list(),
            self.show_server("Server"),
            self._on_home_selection_change,
        )
        self.window.set_home_action(lambda: self.show("HomeView"))
        self.show("HomeView")

    # 0
    def _load_program_data(self) -> None:
        data = self.fileio.retrieve_user_data(all=True) or {}
        BigProgramDict.setdefault("ProgramData", {})
        BigProgramDict["ProgramData"]["Servers"] = data.get(SectServers, {})

    #  1
    def get_server_list(self) -> list[str]:
        serverlist = list(BigProgramDict.get("ProgramData", {}).get("Servers", {}).keys())
        pages = BigProgramDict.setdefault("Pages", {})
        home = pages.setdefault("HomeView", {})
        buttons = home.setdefault("Buttons", {})
        for server in serverlist:
            DebugPrint("Found Server: {}".format(server), "AppController.get_server_list")
            buttons[server] = "homeview.edit"
        return serverlist

    # 2 
    def show_server(self, name: str) -> None:
        self.server_view.set_header(name)
        self.server_view.set_homeview_buttons(self.get_server_list())
        self.window.set_main_view(self.server_view)

    #3  
    def _on_home_selection_change(self, selected: bool) -> None:
        DebugPrint("Selection changed. selected {}".format(self.home_view._last_selected_name), "AppController._on_home_selection_change")
        actions = self._get_function_actions(self.show_page, selected=selected)
        self.window.set_command_actions(actions, on_action=self._handle_action)
        

    # 4  
    def show(self, page_name) -> None:
        print("\n\n================= Showing Page: {} ===============".format(page_name))
        match page_name:
            case "HomeView":
                DebugPrint("Showing Home View")
                self.show_page="HomeView"
                self.home_view.set_homeview_buttons(self.get_server_list())
                self.window.set_main_view(self.home_view)
                self.window.set_command_actions(
                    self._get_function_actions("HomeView", selected=False),
                    on_action=self._handle_action,
                )
            case "ServerView":
                DebugPrint("Showing Server View")
                self.show_page="ServerView"
                #self.server_view.set_homeview_buttons(self.get_server_list())
                self.window.set_main_view(self.server_view)
                self.window.set_command_actions(
                    self._get_function_actions("ServerView"),
                    on_action=self._handle_action,
                )
            case "ServerEdit":
                DebugPrint("Showing Server Edit View")
                self.show_page="ServerEdit"                    # Show Page
                self.server_edit.set_ServerEdit_buttons(self._get_function_actions("ServerEdit" , subsec="Buttons")) #Do Buttons
                self.window.set_main_view(self.server_edit._page_ServerEdit())
                self.window.set_command_actions(
                    self._get_function_actions("ServerEdit"),
                    on_action=self._handle_action,
                )

            case "ServerADD":
                DebugPrint("Showing Server New View")






    

    


    ## Function Action Mapping  ################################################
    def _get_function_actions(self, page_name: str, subsec="Functions", selected: bool = False) -> dict: # Get Function Actions for a Pag
        pages = BigProgramDict.get("Pages", {})
        page_cfg = pages.get(page_name, {})
        functions = page_cfg.get(subsec, {})
        actions = {}
        self._action_handlers = {}
        for key, value in functions.items():
            if isinstance(value, dict):
                #if selected is False:  return
                if key == "OnSelect" and selected:
                    DebugPrint("Processing OnSelect FunctionKey: {} with value: ".format(key), multi=str(value).strip("{} ").split(","))
                    for sub_key, sub_val in value.items():
                        action_id = str(sub_key)
                        actions[sub_key] = action_id
                        self._action_handlers[action_id] = self._resolve_action(sub_val)
            else:
                DebugPrint("Processing FunctionKey: {} with value: {}".format(key, value))
                action_id = str(key)
                actions[key] = action_id
                self._action_handlers[action_id] = self._resolve_action(value)
        return actions
    
    def _resolve_action(self, action_value):               # Resolve Action from Action Value
        if callable(action_value):
            return action_value
        if not isinstance(action_value, str):
            return None
        name = action_value.strip().split(".")
        match name[0]:
            case "homeview":
                return lambda: self._function_action(name[0], name[1])
            case "ServerEdit":
                return lambda: self._function_action(name[0], name[1])
            case "settings":
                return lambda: self._function_action(name[0], name[1])
            case _:
                return None
            
    def _function_action(self, page_key: str, action_key: str) -> None:
        #print("Function Action called with {}".format(a))
        match (page_key, action_key):
            case ("homeview", "add") | ("homeview", "edit"):
                self.show("ServerEdit")
            case ("homeview", "delete"):
                self.delete_server(self.home_view._last_selected_name)
            case ("ServerEdit", "save"):
                self.show("HomeView")
            case ("ServerEdit", "delete"):
                self.delete_server(self.home_view._last_selected_name)
                self.show("HomeView")
            case ("ServerEdit", "cancel"):
                self.show("HomeView")
            case _:
                pass
    

    def _handle_action(self, action_id: str) -> None:      # Handle Action based on Action ID
        handler = getattr(self, "_action_handlers", {}).get(action_id)
        print("Handling action: {} with handler: {}".format(action_id, handler))
        if callable(handler):
            handler()

    


    ## Selections  ################################################
    
    
    def _open_identity_manager(self) -> None:            # Open Identity Manager Window
        script_path = Path(__file__).with_name("IdentyManager.py")
        subprocess.Popen([sys.executable, str(script_path)])
    
    def delete_server(self, name: str) -> None:
        servers = BigProgramDict.get("ProgramData", {}).get("Servers", {})
        if name in servers:
            SectServers = "Servers"
            del servers[name]
            self.fileio.delete_user_data(SectServers, name)
            DebugPrint("Deleted server: {}".format(name), "AppController.delete_server", info=True)
            self.home_view.set_homeview_buttons(self.get_server_list())


    
    def _make_input_field(self, placeholder: str) -> QLineEdit: # Create a styled input field
        field = QLineEdit()
        field.setObjectName("inputField")
        field.setPlaceholderText(placeholder)
        #DebugPrint("Created Input Field with placeholder: {}".format(placeholder), "main._make_input_field")
        return field

if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = AppController()
    controller.window.resize(900, 600)
    controller.window.show()
    sys.exit(app.exec())
