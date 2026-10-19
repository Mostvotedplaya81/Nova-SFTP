import os
import sys
import json
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QToolButton, QLineEdit, QPushButton,
    QTabWidget, QSystemTrayIcon, QMenu, QMessageBox, QApplication
)
from PyQt6.QtGui import QIcon, QKeySequence, QAction
from PyQt6.QtCore import Qt, QByteArray, QDir

from ui.themes import CLEAN_LIGHT_THEME, DRACULA_THEME, MONOKAI_THEME, PREMIUM_DARK_THEME
from ui.sidebar import SidebarWidget
from ui.session_tab import SessionTab
from features.key_manager import SSHKeyManagerDialog
from features.dialogs import CommandPalette

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

class NovaSFTP(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nova SFTP")
        self.resize(1150, 720)

        icon_paths = [
            resource_path("nova-sftp.ico"),
            resource_path("nova-sftp.png"),
            resource_path("nova-sftp.svg"),
            "/usr/share/icons/hicolor/scalable/apps/nova-sftp.png",
            "/usr/share/icons/hicolor/scalable/apps/nova-sftp.svg",
            "nova-sftp.png",
            "nova-sftp.svg"
        ]
        for p in icon_paths:
            if os.path.exists(p):
                self.setWindowIcon(QIcon(p))
                break

        self.settings_file = os.path.expanduser("~/.config/nova_sftp/settings.json")
        self.app_settings = self.load_settings()
        self.local_home_path = os.path.normpath(self.app_settings.get("local_home", QDir.homePath()))
        if not os.path.exists(self.local_home_path):
            self.local_home_path = os.path.normpath(QDir.homePath())

        self.saved_sidebar_width = 250
        self.is_quitting = False
        
        self.init_ui()
        self.setup_tray_icon()
        self.apply_theme()

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as f: return json.load(f)
        return {}

    def save_settings(self):
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
        with open(self.settings_file, 'w') as f: json.dump(self.app_settings, f)

    def apply_theme(self):
        theme = self.app_settings.get("theme", "dark")
        if theme == "light": self.setStyleSheet(CLEAN_LIGHT_THEME)
        elif theme == "dracula": self.setStyleSheet(DRACULA_THEME)
        elif theme == "monokai": self.setStyleSheet(MONOKAI_THEME)
        else: self.setStyleSheet(PREMIUM_DARK_THEME)
            
        for i in range(self.session_tabs.count()):
            tab = self.session_tabs.widget(i)
            if hasattr(tab, 'theme_combo'):
                tab.theme_combo.blockSignals(True)
                theme_map = {"dark": 0, "light": 1, "dracula": 2, "monokai": 3}
                tab.theme_combo.setCurrentIndex(theme_map.get(theme, 0))
                tab.theme_combo.blockSignals(False)

    def set_theme(self, index):
        theme_names = ["dark", "light", "dracula", "monokai"]
        self.app_settings["theme"] = theme_names[index]
        self.save_settings()
        self.apply_theme()

    def init_ui(self):
        geom = self.app_settings.get('window_geometry')
        if geom: self.restoreGeometry(QByteArray.fromHex(geom.encode('utf-8')))
        state = self.app_settings.get('window_state')
        if state: self.restoreState(QByteArray.fromHex(state.encode('utf-8')))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.global_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.sidebar = SidebarWidget(self)
        self.global_splitter.addWidget(self.sidebar)

        self.workspace_panel = QWidget()
        workspace_layout = QVBoxLayout(self.workspace_panel)
        workspace_layout.setContentsMargins(15, 15, 15, 15)

        top_bar = QWidget()
        top_bar.setObjectName("TopBar")
        top_bar.setStyleSheet("#TopBar { background-color: transparent; border: none; }")
        top_layout = QHBoxLayout(top_bar)

        self.sidebar_toggle_btn = QToolButton()
        self.sidebar_toggle_btn.setText("☰")
        self.sidebar_toggle_btn.setProperty("class", "nav-btn")
        self.sidebar_toggle_btn.setToolTip("Toggle Sidebar")
        self.sidebar_toggle_btn.clicked.connect(self.toggle_sidebar)

        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("Host/IP")
        self.port_input = QLineEdit("22")
        self.port_input.setFixedWidth(60)
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username")
        
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.pass_toggle_btn = QToolButton()
        self.pass_toggle_btn.setText("👁")
        self.pass_toggle_btn.setCheckable(True)
        self.pass_toggle_btn.setToolTip("Toggle Password Visibility")
        self.pass_toggle_btn.clicked.connect(lambda: self.pass_input.setEchoMode(QLineEdit.EchoMode.Normal if self.pass_toggle_btn.isChecked() else QLineEdit.EchoMode.Password))

        self.key_btn = QToolButton()
        self.key_btn.setText("🔑 Key Manager")
        self.key_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.key_btn.clicked.connect(self.open_key_manager)
        self.active_key_path = ""

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.open_session_tab)

        for w in (self.sidebar_toggle_btn, self.host_input, self.port_input, self.user_input, self.pass_input, self.pass_toggle_btn, self.key_btn, self.connect_btn):
            top_layout.addWidget(w)
        
        workspace_layout.addWidget(top_bar)

        self.session_tabs = QTabWidget()
        self.session_tabs.setTabsClosable(True)
        self.session_tabs.tabCloseRequested.connect(self.close_tab)
        workspace_layout.addWidget(self.session_tabs)

        self.global_splitter.addWidget(self.workspace_panel)
        self.global_splitter.setStretchFactor(0, 0)
        self.global_splitter.setStretchFactor(1, 1)
        
        global_spl_state = self.app_settings.get('global_splitter')
        if global_spl_state: self.global_splitter.restoreState(QByteArray.fromHex(global_spl_state.encode('utf-8')))

        main_layout.addWidget(self.global_splitter)

        cmd_action = QAction(self)
        cmd_action.setShortcut(QKeySequence("Ctrl+P"))
        cmd_action.triggered.connect(self.show_command_palette)
        self.addAction(cmd_action)

        self.statusBar().showMessage("Ready - Press Spacebar on remote files for Quick Look preview.")

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.windowIcon())
        
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show Dashboard")
        show_action.triggered.connect(self.showNormal)
        quit_action = tray_menu.addAction("Quit Nova SFTP")
        quit_action.triggered.connect(self.quit_app)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()
            self.activateWindow()

    def toggle_sidebar(self):
        sizes = self.global_splitter.sizes()
        if sizes[0] > 0:
            self.saved_sidebar_width = sizes[0]
            self.global_splitter.setSizes([0, sizes[1] + sizes[0]])
        else:
            restore_width = getattr(self, 'saved_sidebar_width', 250)
            if restore_width == 0: restore_width = 250
            self.global_splitter.setSizes([restore_width, sizes[1] - restore_width])

    def show_command_palette(self):
        palette = CommandPalette(self, self)
        geo = self.geometry()
        x = geo.x() + (geo.width() - palette.width()) // 2
        y = geo.y() + (geo.height() - palette.height()) // 2
        palette.move(x, y)
        palette.exec()

    def open_key_manager(self):
        dialog = SSHKeyManagerDialog(self, self)
        dialog.exec()

    def open_session_tab(self, label=None):
        host = self.host_input.text().strip()
        port = int(self.port_input.text().strip() or 22)
        user = self.user_input.text().strip()
        pwd = self.pass_input.text()
        key_path = self.active_key_path

        if not host or not user:
            QMessageBox.warning(self, "Missing Credentials", "Host and Username are required to establish an SFTP session.")
            return

        tab_title = label if isinstance(label, str) and label else f"{user}@{host}"
        tab = SessionTab(host, port, user, pwd, key_path, self)
        tab.status_changed.connect(lambda s: self.statusBar().showMessage(s))
        idx = self.session_tabs.addTab(tab, tab_title)
        self.session_tabs.setCurrentIndex(idx)

    def close_tab(self, index):
        widget = self.session_tabs.widget(index)
        if widget:
            widget.close_tab_resources()
            widget.deleteLater()
        self.session_tabs.removeTab(index)

    def quit_app(self):
        self.is_quitting = True
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()  
        self.close()               
        QApplication.instance().quit()

    def closeEvent(self, event):
        if not self.is_quitting and QSystemTrayIcon.isSystemTrayAvailable():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Nova SFTP",
                "Minimized to tray. Live Sync and SSH tunnels remain active.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            return

        self.app_settings['window_geometry'] = self.saveGeometry().toHex().data().decode('utf-8')
        self.app_settings['window_state'] = self.saveState().toHex().data().decode('utf-8')
        self.app_settings['global_splitter'] = self.global_splitter.saveState().toHex().data().decode('utf-8')
        
        current_tab = self.session_tabs.currentWidget()
        if current_tab:
            self.app_settings['main_splitter'] = current_tab.main_splitter.saveState().toHex().data().decode('utf-8')
            self.app_settings['browser_splitter'] = current_tab.browser_splitter.saveState().toHex().data().decode('utf-8')
            self.app_settings['local_header'] = current_tab.local_view.header().saveState().toHex().data().decode('utf-8')
            self.app_settings['remote_header'] = current_tab.remote_view.header().saveState().toHex().data().decode('utf-8')
            
        self.save_settings()
        
        for i in range(self.session_tabs.count()):
            widget = self.session_tabs.widget(i)
            if widget: widget.close_tab_resources()
            
        event.accept()
