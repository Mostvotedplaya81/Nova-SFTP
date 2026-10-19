import os
import asyncio
import asyncssh
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QFrame, QFormLayout, QLineEdit, QComboBox, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt
from utils.formatting import format_size
from ui.themes import CLEAN_LIGHT_THEME, DRACULA_THEME, MONOKAI_THEME, PREMIUM_DARK_THEME

class SSHKeyManagerDialog(QDialog):
    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.setWindowTitle("Advanced SSH Key Management")
        self.resize(750, 450)
        
        theme = self.main_app.app_settings.get("theme", "dark")
        if theme == "light": self.setStyleSheet(CLEAN_LIGHT_THEME)
        elif theme == "dracula": self.setStyleSheet(DRACULA_THEME)
        elif theme == "monokai": self.setStyleSheet(MONOKAI_THEME)
        else: self.setStyleSheet(PREMIUM_DARK_THEME)

        self.ssh_dir = os.path.expanduser("~/.ssh")
        if not os.path.exists(self.ssh_dir):
            os.makedirs(self.ssh_dir, mode=0o700)

        layout = QHBoxLayout(self)

        left_panel = QVBoxLayout()
        self.key_list = QListWidget()
        self.key_list.itemSelectionChanged.connect(self.on_key_selected)
        
        btn_refresh = QPushButton("↻ Refresh Keys")
        btn_refresh.clicked.connect(self.load_keys)
        
        left_panel.addWidget(QLabel("<b>Local SSH Keys (~/.ssh)</b>"))
        left_panel.addWidget(self.key_list)
        left_panel.addWidget(btn_refresh)
        
        layout.addLayout(left_panel, 1)

        right_panel = QVBoxLayout()
        
        self.lbl_details = QLabel("Select a key to view details or push to server.")
        self.lbl_details.setWordWrap(True)
        self.lbl_details.setStyleSheet("color: #a1a1aa; margin-bottom: 10px;")
        right_panel.addWidget(self.lbl_details)

        push_frame = QFrame()
        push_frame.setStyleSheet("QFrame { border: 1px solid #3f3f46; border-radius: 6px; padding: 10px; }")
        push_layout = QFormLayout(push_frame)
        
        self.push_host = QLineEdit(self.main_app.host_input.text())
        self.push_user = QLineEdit(self.main_app.user_input.text())
        self.push_port = QLineEdit(self.main_app.port_input.text() or "22")
        self.push_pwd = QLineEdit(self.main_app.pass_input.text())
        self.push_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        
        push_layout.addRow("Target Host:", self.push_host)
        push_layout.addRow("Target Port:", self.push_port)
        push_layout.addRow("Target User:", self.push_user)
        push_layout.addRow("Auth Password:", self.push_pwd)
        
        self.btn_push = QPushButton("🚀 Push Public Key to Server")
        self.btn_push.setStyleSheet("background-color: #10b981; color: white;")
        self.btn_push.setEnabled(False)
        self.btn_push.clicked.connect(self.push_key)
        push_layout.addRow("", self.btn_push)
        right_panel.addWidget(push_frame)

        gen_frame = QFrame()
        gen_frame.setStyleSheet("QFrame { border: 1px solid #3f3f46; border-radius: 6px; padding: 10px; margin-top: 10px; }")
        gen_layout = QFormLayout(gen_frame)
        
        self.gen_name = QLineEdit("id_ed25519_nova")
        self.gen_type = QComboBox()
        self.gen_type.addItems(["ssh-ed25519 (Recommended)", "ssh-rsa"])
        self.gen_pass = QLineEdit()
        self.gen_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.gen_pass.setPlaceholderText("Optional Passphrase")
        
        gen_layout.addRow(QLabel("<b>Generate New Keypair</b>"))
        gen_layout.addRow("Filename:", self.gen_name)
        gen_layout.addRow("Key Type:", self.gen_type)
        gen_layout.addRow("Passphrase:", self.gen_pass)
        
        self.btn_gen = QPushButton("⚡ Generate Key")
        self.btn_gen.clicked.connect(self.generate_key)
        gen_layout.addRow("", self.btn_gen)
        right_panel.addWidget(gen_frame)

        right_panel.addStretch()
        
        self.btn_use = QPushButton("Use Selected Key for Connection")
        self.btn_use.setEnabled(False)
        self.btn_use.clicked.connect(self.use_key)
        right_panel.addWidget(self.btn_use)

        layout.addLayout(right_panel, 2)
        
        self.load_keys()

    def load_keys(self):
        self.key_list.clear()
        if not os.path.exists(self.ssh_dir): return
        
        for f in sorted(os.listdir(self.ssh_dir)):
            if f in ['known_hosts', 'known_hosts.old', 'config', 'authorized_keys']: continue
            full_path = os.path.join(self.ssh_dir, f)
            if os.path.isfile(full_path):
                with open(full_path, 'r', errors='ignore') as file:
                    head = file.read(64)
                    if "PRIVATE KEY" in head or f.endswith('.pub') or "ssh-" in head:
                        item = QListWidgetItem(f)
                        item.setData(Qt.ItemDataRole.UserRole, full_path)
                        self.key_list.addItem(item)

    def on_key_selected(self):
        items = self.key_list.selectedItems()
        if not items:
            self.btn_push.setEnabled(False)
            self.btn_use.setEnabled(False)
            self.lbl_details.setText("Select a key to view details.")
            return
            
        path = items[0].data(Qt.ItemDataRole.UserRole)
        is_pub = path.endswith('.pub')
        
        pub_path = path if is_pub else path + ".pub"
        has_pub = os.path.exists(pub_path)
        
        self.btn_use.setEnabled(not is_pub)
        self.btn_push.setEnabled(has_pub)
        
        size = format_size(os.path.getsize(path))
        info = f"<b>File:</b> {path}<br><b>Size:</b> {size}<br>"
        info += f"<b>Public Key Available:</b> {'Yes' if has_pub else 'No (Cannot push without public key)'}"
        
        self.lbl_details.setText(info)

    def use_key(self):
        items = self.key_list.selectedItems()
        if not items: return
        path = items[0].data(Qt.ItemDataRole.UserRole)
        self.main_app.active_key_path = path
        self.main_app.key_btn.setStyleSheet("background-color: #10b981; color: white;")
        self.accept()

    def generate_key(self):
        name = self.gen_name.text().strip()
        if not name: return
        
        priv_path = os.path.join(self.ssh_dir, name)
        pub_path = priv_path + ".pub"
        
        if os.path.exists(priv_path):
            QMessageBox.warning(self, "Error", f"Key {name} already exists!")
            return
            
        k_type = "ssh-ed25519" if "ed25519" in self.gen_type.currentText() else "ssh-rsa"
        pwd = self.gen_pass.text()
        pwd_bytes = pwd.encode() if pwd else None
        
        try:
            priv_key = asyncssh.generate_private_key(k_type)
            priv_key.write_private_key(priv_path, passphrase=pwd_bytes)
            os.chmod(priv_path, 0o600)
            
            with open(pub_path, 'w') as f:
                f.write(priv_key.export_public_key().decode('utf-8'))
                
            QMessageBox.information(self, "Success", f"Generated {k_type} key pair successfully:\n{priv_path}")
            self.load_keys()
        except Exception as e:
            QMessageBox.critical(self, "Generation Error", str(e))

    def push_key(self):
        items = self.key_list.selectedItems()
        if not items: return
        
        path = items[0].data(Qt.ItemDataRole.UserRole)
        pub_path = path if path.endswith('.pub') else path + ".pub"
        
        host = self.push_host.text().strip()
        user = self.push_user.text().strip()
        port = int(self.push_port.text().strip() or 22)
        pwd = self.push_pwd.text()
        
        if not host or not user or not pwd:
            QMessageBox.warning(self, "Missing Credentials", "Host, User, and Password are required to inject the key.")
            return
            
        asyncio.create_task(self._push_task(host, port, user, pwd, pub_path))
        
    async def _push_task(self, host, port, user, pwd, pub_path):
        self.btn_push.setText("Pushing...")
        self.btn_push.setEnabled(False)
        try:
            with open(pub_path, 'r') as f:
                pub_key_text = f.read().strip()
                
            conn = await asyncssh.connect(host, port=port, username=user, password=pwd, known_hosts=None)
            cmd = f"mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '{pub_key_text}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
            res = await conn.run(cmd)
            
            if res.exit_status == 0:
                QMessageBox.information(self, "Success", "Public key successfully injected into remote authorized_keys!\n\nYou can now connect without a password.")
            else:
                QMessageBox.warning(self, "Failed", f"Server returned error:\n{res.stderr}")
        except Exception as e:
            QMessageBox.critical(self, "Push Error", str(e))
        finally:
            self.btn_push.setText("🚀 Push Public Key to Server")
            self.btn_push.setEnabled(True)
