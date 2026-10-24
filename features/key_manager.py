import os
import shlex
import subprocess
import asyncio
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QPlainTextEdit, QMessageBox, QInputDialog, QSplitter
)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt

class SSHKeyManagerWindow(QWidget):
    def __init__(self, session_tab):
        super().__init__()
        self.session_tab = session_tab
        self.keys_dir = os.path.expanduser("~/.nova_keys")
        self.setWindowTitle(f"SSH Key Vault & Deployer - {session_tab.user}@{session_tab.host}")
        
        if not os.path.exists(self.keys_dir):
            os.makedirs(self.keys_dir, exist_ok=True)
            
        self.init_ui()
        self.load_keys()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.setStyleSheet("""
            QWidget { background-color: #09090b; color: #f4f4f5; font-family: 'Segoe UI', Ubuntu, sans-serif; }
            QListWidget { background-color: #18181b; border: 1px solid #27272a; border-radius: 6px; padding: 5px; outline: none; }
            QListWidget::item { padding: 8px; border-radius: 4px; }
            QListWidget::item:selected { background-color: #264f78; font-weight: bold; }
            QPlainTextEdit { background-color: #0c0a09; color: #38bdf8; border: 1px solid #3f3f46; border-radius: 6px; padding: 10px; }
            QPushButton { background-color: #27272a; color: #f4f4f5; border: 1px solid #3f3f46; border-radius: 4px; padding: 6px 14px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #3f3f46; }
        """)

        header = QLabel("🔐 Nova Local Key Vault (~/.nova_keys)")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #10b981;")
        layout.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Pane: Key List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.key_list = QListWidget()
        self.key_list.itemSelectionChanged.connect(self.on_key_selected)
        left_layout.addWidget(self.key_list)

        btn_generate = QPushButton("➕ Generate Ed25519 Key")
        btn_generate.setStyleSheet("background-color: #059669; color: white;")
        btn_generate.clicked.connect(self.generate_new_key)
        left_layout.addWidget(btn_generate)

        # Right Pane: Preview & Deploy
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_preview = QLabel("Public Key Preview:")
        self.lbl_preview.setStyleSheet("color: #a1a1aa; font-weight: bold;")
        right_layout.addWidget(self.lbl_preview)

        self.key_preview = QPlainTextEdit()
        self.key_preview.setReadOnly(True)
        self.key_preview.setFont(QFont("Cascadia Mono", 10))
        right_layout.addWidget(self.key_preview)

        action_bar = QHBoxLayout()
        
        self.btn_delete = QPushButton("🗑️ Delete Key")
        self.btn_delete.setStyleSheet("background-color: #7f1d1d; color: white;")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self.delete_selected_key)
        
        self.btn_deploy = QPushButton(f"🚀 Push to {self.session_tab.host}")
        self.btn_deploy.setStyleSheet("background-color: #2563eb; color: white; padding: 8px 16px; font-size: 13px;")
        self.btn_deploy.setEnabled(False)
        self.btn_deploy.clicked.connect(lambda: asyncio.create_task(self.push_key_to_server()))

        action_bar.addWidget(self.btn_delete)
        action_bar.addStretch()
        action_bar.addWidget(self.btn_deploy)
        right_layout.addLayout(action_bar)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

    def load_keys(self):
        self.key_list.clear()
        self.key_preview.clear()
        self.btn_deploy.setEnabled(False)
        self.btn_delete.setEnabled(False)

        if os.path.exists(self.keys_dir):
            for file in sorted(os.listdir(self.keys_dir)):
                if file.endswith(".pub"):
                    base_name = file[:-4]
                    self.key_list.addItem(base_name)

    def on_key_selected(self):
        selected = self.key_list.selectedItems()
        if not selected:
            self.key_preview.clear()
            self.btn_deploy.setEnabled(False)
            self.btn_delete.setEnabled(False)
            return

        key_name = selected[0].text()
        pub_path = os.path.join(self.keys_dir, f"{key_name}.pub")

        if os.path.exists(pub_path):
            with open(pub_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                self.key_preview.setPlainText(content)
            self.btn_deploy.setEnabled(True)
            self.btn_delete.setEnabled(True)

    def generate_new_key(self):
        name, ok = QInputDialog.getText(self, "New SSH Key", "Enter a name for the new key (e.g. 'nova_master'):")
        if not ok or not name.strip():
            return
            
        name = name.strip()
        key_path = os.path.join(self.keys_dir, name)

        if os.path.exists(key_path) or os.path.exists(key_path + ".pub"):
            QMessageBox.warning(self, "Error", f"A key named '{name}' already exists.")
            return

        try:
            # Generate highly secure Ed25519 key with no passphrase for automation
            cmd = ["ssh-keygen", "-t", "ed25519", "-f", key_path, "-N", "", "-C", f"{name}@nova-sftp"]
            subprocess.run(cmd, check=True, capture_output=True)
            self.load_keys()
            QMessageBox.information(self, "Success", f"Generated Ed25519 key pair:\n{name}")
        except subprocess.CalledProcessError as e:
            QMessageBox.warning(self, "Generation Failed", f"Could not generate SSH key:\n{e.stderr.decode()}")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def delete_selected_key(self):
        selected = self.key_list.selectedItems()
        if not selected: return
        key_name = selected[0].text()

        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to permanently delete both the private and public keys for '{key_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            priv_path = os.path.join(self.keys_dir, key_name)
            pub_path = os.path.join(self.keys_dir, f"{key_name}.pub")
            try:
                if os.path.exists(priv_path): os.remove(priv_path)
                if os.path.exists(pub_path): os.remove(pub_path)
                self.load_keys()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to delete keys: {e}")

    async def push_key_to_server(self):
        selected = self.key_list.selectedItems()
        if not selected: return
        pub_key_content = self.key_preview.toPlainText().strip()
        if not pub_key_content: return

        self.btn_deploy.setEnabled(False)
        self.btn_deploy.setText("Deploying...")

        try:
            conn, _ = await self.session_tab.get_connection()
            # The holy grail of authorized_keys configuration
            escaped_key = shlex.quote(pub_key_content)
            cmd = (
                f"mkdir -p ~/.ssh && "
                f"chmod 700 ~/.ssh && "
                f"echo {escaped_key} >> ~/.ssh/authorized_keys && "
                f"chmod 600 ~/.ssh/authorized_keys"
            )
            res = await conn.run(cmd)
            
            if res.exit_status == 0:
                QMessageBox.information(self, "Key Deployed", f"Successfully installed public key to '{self.session_tab.host}'.\n\nYou can now connect to this server securely without a password.")
            else:
                QMessageBox.warning(self, "Deployment Failed", f"Server rejected key payload:\n{res.stderr}")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
        finally:
            self.btn_deploy.setEnabled(True)
            self.btn_deploy.setText(f"🚀 Push to {self.session_tab.host}")
