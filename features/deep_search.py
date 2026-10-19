import os
import asyncio
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox
)
from PyQt6.QtCore import Qt

class DeepSearchWidget(QWidget):
    def __init__(self, session_tab, parent=None):
        super().__init__(parent)
        self.session_tab = session_tab
        self.search_process = None
        self.is_searching = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        controls_layout = QHBoxLayout()

        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems(["Filename (find)", "File Content (grep)"])
        self.search_type_combo.setFixedWidth(160)

        self.root_path_input = QLineEdit()
        self.root_path_input.setPlaceholderText("Search root path (default: current directory)")

        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Search query...")
        self.query_input.returnPressed.connect(self.toggle_search)

        self.btn_search = QPushButton("🔍 Search")
        self.btn_search.setStyleSheet("background-color: #4f46e5; color: white; font-weight: bold;")
        self.btn_search.clicked.connect(self.toggle_search)

        controls_layout.addWidget(QLabel("Mode:"))
        controls_layout.addWidget(self.search_type_combo)
        controls_layout.addWidget(QLabel("In:"))
        controls_layout.addWidget(self.root_path_input, 1)
        controls_layout.addWidget(QLabel("Query:"))
        controls_layout.addWidget(self.query_input, 2)
        controls_layout.addWidget(self.btn_search)

        layout.addLayout(controls_layout)

        self.status_lbl = QLabel("Ready to search.")
        self.status_lbl.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        layout.addWidget(self.status_lbl)

        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["Path", "Line", "Match / Snippet"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.results_table.setColumnWidth(0, 360)
        self.results_table.setColumnWidth(1, 60)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results_table.setShowGrid(False)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.itemDoubleClicked.connect(self.on_result_double_clicked)
        self.results_table.setStyleSheet("QTableWidget::item { padding: 4px; }")

        layout.addWidget(self.results_table)

    def toggle_search(self):
        if self.is_searching:
            self.stop_search()
        else:
            self.start_search()

    def start_search(self):
        query = self.query_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Missing Query", "Please enter a search term.")
            return

        target_dir = self.root_path_input.text().strip()
        if not target_dir:
            target_dir = self.session_tab.current_remote_path
            if target_dir in [".", ""]:
                target_dir = "/"

        mode = self.search_type_combo.currentIndex()
        if mode == 0:  
            safe_query = query.replace('"', '\\"')
            cmd = f'find "{target_dir}" -maxdepth 8 -iname "*{safe_query}*" 2>/dev/null | head -n 250'
        else:  
            safe_query = query.replace('"', '\\"')
            cmd = f'grep -rnIH --exclude-dir={{.git,node_modules,vendor,cache}} "{safe_query}" "{target_dir}" 2>/dev/null | head -n 250'

        self.results_table.setRowCount(0)
        self.is_searching = True
        self.btn_search.setText("⏹ Stop")
        self.btn_search.setStyleSheet("background-color: #ef4444; color: white; font-weight: bold;")
        self.status_lbl.setText(f"Searching in {target_dir}...")

        asyncio.create_task(self._run_search_async(cmd, mode))

    def stop_search(self):
        self.is_searching = False
        if getattr(self, 'search_process', None):
            self.search_process.terminate()
            self.search_process = None
        self.btn_search.setText("🔍 Search")
        self.btn_search.setStyleSheet("background-color: #4f46e5; color: white; font-weight: bold;")
        self.status_lbl.setText("Search stopped by user.")

    async def _run_search_async(self, cmd, mode):
        conn = getattr(self.session_tab, 'ssh_conn', None)
        if not conn:
            self.stop_search()
            self.status_lbl.setText("Connection unavailable.")
            return

        count = 0
        try:
            self.search_process = await conn.create_process(cmd)
            buf = ""
            while self.is_searching:
                chunk = await self.search_process.stdout.read(2048)
                if not chunk:
                    break
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    row = self.results_table.rowCount()
                    self.results_table.insertRow(row)

                    if mode == 0:  
                        item_path = QTableWidgetItem(line)
                        self.results_table.setItem(row, 0, item_path)
                        item_line = QTableWidgetItem("-")
                        item_line.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.results_table.setItem(row, 1, item_line)
                        self.results_table.setItem(row, 2, QTableWidgetItem(os.path.basename(line)))
                    else:  
                        parts = line.split(":", 2)
                        if len(parts) >= 3:
                            self.results_table.setItem(row, 0, QTableWidgetItem(parts[0]))
                            item_line = QTableWidgetItem(parts[1])
                            item_line.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                            self.results_table.setItem(row, 1, item_line)
                            self.results_table.setItem(row, 2, QTableWidgetItem(parts[2].strip()))
                        else:
                            self.results_table.setItem(row, 0, QTableWidgetItem(line))
                            item_line = QTableWidgetItem("-")
                            item_line.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                            self.results_table.setItem(row, 1, item_line)
                            self.results_table.setItem(row, 2, QTableWidgetItem(""))

                    count += 1
                    self.status_lbl.setText(f"Found {count} result(s)...")

            self.status_lbl.setText(f"Search complete. Total matches: {count}")
        except Exception as e:
            self.status_lbl.setText(f"Error: {e}")
        finally:
            self.stop_search()

    def on_result_double_clicked(self, item):
        row = item.row()
        path_item = self.results_table.item(row, 0)
        if not path_item:
            return

        remote_path = path_item.text().strip()
        filename = os.path.basename(remote_path)

        asyncio.create_task(self.session_tab.read_and_edit_file(filename, remote_path))
