import os
import json
import keyring
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QListWidget, 
                             QFormLayout, QLineEdit, QHBoxLayout, 
                             QToolButton, QPushButton, QScrollArea, QFrame)
from PyQt6.QtCore import Qt

class SidebarWidget(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.config_dir = os.path.expanduser("~/.config/nova_sftp")
        self.config_file = os.path.join(self.config_dir, "sites.json")
        self.sites = self.load_data()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Bookmarks")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #a1a1aa; padding: 10px;")
        layout.addWidget(header)

        self.site_list = QListWidget()
        self.site_list.addItems(self.sites.keys())
        self.site_list.currentTextChanged.connect(self.populate_fields)
        self.site_list.itemDoubleClicked.connect(lambda item: self.connect_to_site(item.text()))
        layout.addWidget(self.site_list)

        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setContentsMargins(10, 10, 10, 10)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Site Alias")
        
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("IP or Domain")
        
        self.port_input = QLineEdit("22")
        self.port_input.setPlaceholderText("Port")
        self.port_input.setFixedWidth(60)
        
        host_layout = QHBoxLayout()
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.addWidget(self.host_input)
        host_layout.addWidget(self.port_input)
        
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username")
        
        pass_layout = QHBoxLayout()
        pass_layout.setContentsMargins(0, 0, 0, 0)
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("Password / Phrase")
        
        self.pass_toggle_btn = QToolButton()
        self.pass_toggle_btn.setText("👁")
        self.pass_toggle_btn.setCheckable(True)
        self.pass_toggle_btn.setToolTip("Toggle Password Visibility")
        self.pass_toggle_btn.clicked.connect(lambda: self.pass_input.setEchoMode(QLineEdit.EchoMode.Normal if self.pass_toggle_btn.isChecked() else QLineEdit.EchoMode.Password))
        pass_layout.addWidget(self.pass_input)
        pass_layout.addWidget(self.pass_toggle_btn)
        
        btn_layout = QHBoxLayout()
        self.new_btn = QPushButton("New")
        self.new_btn.clicked.connect(self.clear_fields)
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_site)
        self.del_btn = QPushButton("Del")
        self.del_btn.setStyleSheet("background-color: #ef4444; color: white;")
        self.del_btn.clicked.connect(self.delete_site)
        
        btn_layout.addWidget(self.new_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.del_btn)

        form_layout.addRow(self.name_input)
        form_layout.addRow(host_layout)
        form_layout.addRow(self.user_input)
        form_layout.addRow(pass_layout)
        form_layout.addRow(btn_layout)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        # Replacing NoFrame with raw integer to avoid Qt enum version issues
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setWidget(form_widget)
        scroll_area.setMinimumHeight(200)
        
        layout.addWidget(scroll_area)

    def load_data(self):
        if not os.path.exists(self.config_dir): os.makedirs(self.config_dir)
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f: return json.load(f)
        return {}

    def clear_fields(self):
        self.site_list.clearSelection()
        self.name_input.clear()
        self.host_input.clear()
        self.port_input.setText("22")
        self.user_input.clear()
        self.pass_input.clear()
        self.main_app.active_key_path = ""

    def populate_fields(self, site_name):
        if site_name in self.sites:
            data = self.sites[site_name]
            self.name_input.setText(site_name)
            self.host_input.setText(data.get('host', ''))
            self.port_input.setText(str(data.get('port', 22)))
            self.user_input.setText(data.get('user', ''))
            saved_pass = keyring.get_password("nova_sftp", site_name)
            self.pass_input.setText(saved_pass if saved_pass else "")
            
            self.main_app.host_input.setText(data.get('host', ''))
            self.main_app.port_input.setText(str(data.get('port', 22)))
            self.main_app.user_input.setText(data.get('user', ''))
            self.main_app.pass_input.setText(saved_pass if saved_pass else "")
            self.main_app.active_key_path = data.get('key_path', '')

    def save_site(self):
        name = self.name_input.text().strip()
        if not name: return
        port_val = self.port_input.text().strip()
        port = int(port_val) if port_val.isdigit() else 22
        
        self.sites[name] = { 
            'host': self.host_input.text(), 
            'port': port, 
            'user': self.user_input.text(), 
            'key_path': self.main_app.active_key_path 
        }
        with open(self.config_file, 'w') as f: json.dump(self.sites, f)
        if self.pass_input.text(): 
            keyring.set_password("nova_sftp", name, self.pass_input.text())
        if not self.site_list.findItems(name, Qt.MatchFlag.MatchExactly): 
            self.site_list.addItem(name)
        self.clear_fields()

    def delete_site(self):
        item = self.site_list.currentItem()
        if not item: return
        name = item.text()
        if name in self.sites:
            del self.sites[name]
            with open(self.config_file, 'w') as f: json.dump(self.sites, f)
            try: keyring.delete_password("nova_sftp", name)
            except: pass
        self.site_list.takeItem(self.site_list.row(item))
        self.clear_fields()

    def connect_to_site(self, site_name):
        self.populate_fields(site_name)
        self.main_app.open_session_tab(label=site_name)
