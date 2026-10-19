import os
import stat
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QCheckBox
)
from PyQt6.QtCore import Qt

class SyncConfigDialog(QDialog):
    def __init__(self, local_path, remote_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Sync Task")
        self.resize(500, 180)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.local_input = QLineEdit(local_path)
        self.remote_input = QLineEdit(remote_path)
        
        self.dir_combo = QComboBox()
        self.dir_combo.addItems(["Upload to Remote (Local -> Remote)", "Download to Local (Remote -> Local)"])

        form.addRow("Source Local Path:", self.local_input)
        form.addRow("Target Remote Path:", self.remote_input)
        form.addRow("Sync Direction:", self.dir_combo)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Sync")
        self.start_btn.setStyleSheet("background-color: #10b981; color: white;")
        self.start_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.start_btn)
        layout.addLayout(btn_layout)
        
    def get_config(self):
        return self.local_input.text(), self.remote_input.text(), self.dir_combo.currentIndex()

class CommandPalette(QDialog):
    def __init__(self, main_app, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.main_app = main_app
        self.resize(550, 350)
        
        theme = self.main_app.app_settings.get("theme", "dark")
        if theme == "light":
            bg_color = "#ffffff"; border_color = "#cbd5e1"; text_color = "#0f172a"; sel_color = "#3b82f6"
        elif theme == "dracula":
            bg_color = "#282a36"; border_color = "#44475a"; text_color = "#f8f8f2"; sel_color = "#bd93f9"
        elif theme == "monokai":
            bg_color = "#272822"; border_color = "#3e3d32"; text_color = "#f8f8f2"; sel_color = "#f92672"
        else:
            bg_color = "#18181b"; border_color = "#3f3f46"; text_color = "#f4f4f5"; sel_color = "#4f46e5"
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 6px; }}
            QLineEdit {{ font-size: 16px; padding: 12px; border: none; border-bottom: 1px solid {border_color}; background-color: transparent; color: {text_color}; }}
            QListWidget {{ border: none; background-color: transparent; font-size: 14px; padding: 5px; }}
            QListWidget::item {{ padding: 10px; border-radius: 6px; }}
            QListWidget::item:selected {{ background-color: {sel_color}; color: {"#282a36" if theme == "dracula" else ("white" if theme != "monokai" else "#f8f8f2")}; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a command or > connect [site]...")
        self.input_field.textChanged.connect(self.filter_commands)
        self.input_field.returnPressed.connect(self.execute_selected)
        
        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.execute_selected)

        layout.addWidget(self.input_field)
        layout.addWidget(self.results_list)
        self.populate_base_commands()

    def populate_base_commands(self):
        self.results_list.clear()
        sites = self.main_app.sidebar.sites
        for site_name in sites.keys():
            self.results_list.addItem(f"> connect {site_name}")

        self.results_list.addItem("> action: new connection")
        self.results_list.addItem("> search: open deep search")
        self.results_list.addItem("> theme: dark")
        self.results_list.addItem("> theme: light")
        self.results_list.addItem("> theme: dracula")
        self.results_list.addItem("> theme: monokai")
        self.results_list.addItem("> ui: close active tab")
        
        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)

    def filter_commands(self, text):
        text = text.lower()
        for i in range(self.results_list.count()):
            item = self.results_list.item(i)
            item.setHidden(text not in item.text().lower())
        
        for i in range(self.results_list.count()):
            if not self.results_list.item(i).isHidden():
                self.results_list.setCurrentRow(i)
                break

    def execute_selected(self):
        item = self.results_list.currentItem()
        if not item or item.isHidden(): return
        cmd = item.text()
        self.accept()
        
        if cmd.startswith("> connect "):
            site_name = cmd.replace("> connect ", "").strip()
            self.main_app.sidebar.connect_to_site(site_name)
        elif cmd == "> action: new connection":
            self.main_app.open_session_tab()
        elif cmd == "> search: open deep search":
            idx = self.main_app.session_tabs.currentIndex()
            if idx != -1:
                tab = self.main_app.session_tabs.widget(idx)
                tab.bottom_tabs.setCurrentWidget(tab.deep_search_tab)
                tab.deep_search_tab.query_input.setFocus()
        elif cmd.startswith("> theme: "):
            theme_map = {"dark": 0, "light": 1, "dracula": 2, "monokai": 3}
            theme_choice = cmd.replace("> theme: ", "").strip()
            if theme_choice in theme_map:
                self.main_app.set_theme(theme_map[theme_choice])
        elif cmd == "> ui: close active tab":
            idx = self.main_app.session_tabs.currentIndex()
            if idx != -1: self.main_app.close_tab(idx)

class PropertiesDialog(QDialog):
    def __init__(self, filename, mode, uid, gid, is_dir=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Properties: {filename}")
        self.resize(380, 480)
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        self.uid_input = QLineEdit(str(uid))
        self.gid_input = QLineEdit(str(gid))
        
        current_octal = oct(stat.S_IMODE(mode))[-3:].zfill(3)
        self.octal_input = QLineEdit(current_octal)
        self.octal_input.textChanged.connect(self.update_checkboxes_from_octal)

        form_layout.addRow("Owner UID:", self.uid_input)
        form_layout.addRow("Group GID:", self.gid_input)
        form_layout.addRow("Octal Mode:", self.octal_input)
        layout.addLayout(form_layout)

        self.perms = {
            'Owner': {'Read': stat.S_IRUSR, 'Write': stat.S_IWUSR, 'Execute': stat.S_IXUSR},
            'Group': {'Read': stat.S_IRGRP, 'Write': stat.S_IWGRP, 'Execute': stat.S_IXGRP},
            'Public': {'Read': stat.S_IROTH, 'Write': stat.S_IWOTH, 'Execute': stat.S_IXOTH}
        }
        self.cbs = []
        for group, modes in self.perms.items():
            hb = QHBoxLayout()
            lbl = QLabel(f"{group}:")
            lbl.setFixedWidth(60)
            hb.addWidget(lbl)
            for label, flag in modes.items():
                cb = QCheckBox(label)
                cb.setChecked(bool(mode & flag))
                cb.stateChanged.connect(self.update_octal_from_checkboxes)
                self.cbs.append((cb, flag))
                hb.addWidget(cb)
            layout.addLayout(hb)

        layout.addStretch()
        self.recursive_cb = QCheckBox("Apply recursively to folder contents (-R)")
        self.recursive_cb.setStyleSheet("color: #ef4444; font-weight: bold;")
        self.recursive_cb.setVisible(is_dir) 
        layout.addWidget(self.recursive_cb)
        
        self.btn = QPushButton("Apply Properties")
        self.btn.clicked.connect(self.accept)
        layout.addWidget(self.btn)

    def update_octal_from_checkboxes(self):
        if not self.isActiveWindow(): return
        new_mode = 0
        for cb, flag in self.cbs:
            if cb.isChecked(): new_mode |= flag
        self.octal_input.blockSignals(True)
        self.octal_input.setText(oct(new_mode)[-3:].zfill(3))
        self.octal_input.blockSignals(False)

    def update_checkboxes_from_octal(self):
        try:
            val = int(self.octal_input.text(), 8)
            for cb, flag in self.cbs:
                cb.blockSignals(True)
                cb.setChecked(bool(val & flag))
                cb.blockSignals(False)
        except ValueError:
            pass

    def get_properties(self):
        try: new_mode = int(self.octal_input.text(), 8)
        except: new_mode = None
        uid = int(self.uid_input.text()) if self.uid_input.text().isdigit() else -1
        gid = int(self.gid_input.text()) if self.gid_input.text().isdigit() else -1
        return new_mode, uid, gid, self.recursive_cb.isChecked()
