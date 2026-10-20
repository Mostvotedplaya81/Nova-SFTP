import os
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLineEdit,
    QPlainTextEdit, QPushButton, QLabel, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt

class MacroManagerWidget(QWidget):
    def __init__(self, session_tab, parent=None):
        super().__init__(parent)
        self.session_tab = session_tab
        self.config_dir = os.path.expanduser("~/.config/nova_sftp")
        self.macros_file = os.path.join(self.config_dir, "macros.json")
        self.macros = self.load_macros()
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - List
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("<b>Saved Macros</b>"))
        
        self.macro_list = QListWidget()
        self.macro_list.addItems(self.macros.keys())
        self.macro_list.currentTextChanged.connect(self.populate_editor)
        left_layout.addWidget(self.macro_list)
        
        # Right panel - Editor
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Macro Name (e.g., Update Docker Stack)")
        
        self.script_editor = QPlainTextEdit()
        self.script_editor.setPlaceholderText("# Enter your shell commands here...\ngit pull\ndocker-compose down\ndocker-compose up -d")
        self.script_editor.setStyleSheet('font-family: "Cascadia Mono", "Consolas", "Ubuntu Mono", monospace; font-size: 13px;')
        
        right_layout.addWidget(QLabel("<b>Macro Name</b>"))
        right_layout.addWidget(self.name_input)
        right_layout.addWidget(QLabel("<b>Shell Commands</b>"))
        right_layout.addWidget(self.script_editor)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_new = QPushButton("New")
        self.btn_new.clicked.connect(self.clear_editor)
        
        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.save_macro)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setStyleSheet("background-color: #ef4444; color: white;")
        self.btn_delete.clicked.connect(self.delete_macro)
        
        self.btn_run = QPushButton("▶ Run Macro")
        self.btn_run.setStyleSheet("background-color: #10b981; color: white; font-weight: bold;")
        self.btn_run.clicked.connect(self.run_macro)
        
        btn_layout.addWidget(self.btn_new)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_run)
        
        right_layout.addLayout(btn_layout)
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        layout.addWidget(splitter)
        
    def load_macros(self):
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir, exist_ok=True)
        if os.path.exists(self.macros_file):
            try:
                with open(self.macros_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        # Default macros for a new user
        return {
            "Update System": "sudo apt update\nsudo apt upgrade -y\nsudo apt autoremove -y",
            "Restart Nginx": "sudo systemctl restart nginx\nsudo systemctl status nginx"
        }

    def clear_editor(self):
        self.macro_list.clearSelection()
        self.name_input.clear()
        self.script_editor.clear()
        
    def populate_editor(self, name):
        if name in self.macros:
            self.name_input.setText(name)
            self.script_editor.setPlainText(self.macros[name])
            
    def save_macro(self):
        name = self.name_input.text().strip()
        script = self.script_editor.toPlainText().strip()
        if not name or not script:
            QMessageBox.warning(self, "Warning", "Macro Name and Script cannot be empty.")
            return
            
        self.macros[name] = script
        with open(self.macros_file, 'w') as f:
            json.dump(self.macros, f, indent=4)
            
        if not self.macro_list.findItems(name, Qt.MatchFlag.MatchExactly):
            self.macro_list.addItem(name)
        self.macro_list.setCurrentItem(self.macro_list.findItems(name, Qt.MatchFlag.MatchExactly)[0])
        QMessageBox.information(self, "Saved", f"Macro '{name}' saved successfully.")

    def delete_macro(self):
        item = self.macro_list.currentItem()
        if not item: return
        name = item.text()
        
        reply = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete macro '{name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if name in self.macros:
                del self.macros[name]
                with open(self.macros_file, 'w') as f:
                    json.dump(self.macros, f, indent=4)
            self.macro_list.takeItem(self.macro_list.row(item))
            self.clear_editor()

    def run_macro(self):
        script = self.script_editor.toPlainText().strip()
        if not script:
            QMessageBox.warning(self, "Warning", "No script to run.")
            return
            
        self.session_tab.execute_macro(script)
