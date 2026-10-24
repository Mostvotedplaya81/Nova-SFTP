import re
import shlex
import asyncio
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QLabel, QLineEdit, QTableView, QHeaderView, QMessageBox
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor, QFont
from PyQt6.QtCore import Qt

CRON_LINE_RE = re.compile(
    r"^\s*(?P<comment>#\s*)?"
    r"(?P<sched>(?:@[a-zA-Z]+)|(?:[^\s#]+\s+[^\s#]+\s+[^\s#]+\s+[^\s#]+\s+[^\s#]+))\s+"
    r"(?P<cmd>.+)$"
)

class CronManagerWindow(QWidget):
    def __init__(self, session_tab):
        super().__init__()
        self.session_tab = session_tab
        self.setWindowTitle(f"Cron Task Scheduler - {session_tab.user}@{session_tab.host}")
        self.resize(1050, 600)
        
        self.raw_lines = []
        self.cron_entries = []
        self.editing_line_idx = None

        self.init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        asyncio.create_task(self.load_crontab())

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.setStyleSheet("""
            QWidget { background-color: #09090b; color: #f4f4f5; font-family: 'Segoe UI', Ubuntu, sans-serif; }
            QTableView { background-color: #18181b; alternate-background-color: #27272a; border: 1px solid #27272a; gridline-color: #3f3f46; }
            QHeaderView::section { background-color: #09090b; color: #a1a1aa; font-weight: bold; padding: 6px; border: none; border-bottom: 1px solid #3f3f46; }
            QLineEdit, QComboBox { background-color: #18181b; color: #f4f4f5; border: 1px solid #3f3f46; border-radius: 4px; padding: 5px 8px; }
            QPushButton { background-color: #27272a; color: #f4f4f5; border: 1px solid #3f3f46; border-radius: 4px; padding: 5px 12px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #3f3f46; }
        """)

        # --- ROW 1: PRESETS & SCHEDULE ---
        top_row = QHBoxLayout()
        self.preset_sched = QComboBox()
        self.preset_sched.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.preset_sched.setMinimumWidth(180)
        self.preset_sched.addItems([
            "Schedule Preset...",
            "Every 5m (*/5 * * * *)",
            "Every 15m (*/15 * * * *)",
            "Hourly (0 * * * *)",
            "Daily Midnight (0 0 * * *)",
            "Daily 3:00 AM (0 3 * * *)",
            "Weekly Sun (0 0 * * 0)",
            "Monthly 1st (0 0 1 * *)",
            "On Reboot (@reboot)"
        ])
        self.preset_sched.currentIndexChanged.connect(self.on_sched_preset_changed)

        self.sched_input = QLineEdit("0 3 * * *")
        self.sched_input.setFixedWidth(140)
        self.sched_input.setPlaceholderText("m h dom mon dow")
        self.sched_input.setFont(QFont("Cascadia Mono", 10))

        self.preset_cmd = QComboBox()
        self.preset_cmd.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.preset_cmd.setMinimumWidth(200)
        self.preset_cmd.addItems([
            "Script Template...",
            "Cloud Backup (~/cloud_backup.sh)",
            "Python (~/torrent_cleaner.py)",
            "PHP (~/cli_master_maintenance.php)",
            "Docker Prune (system prune -af)"
        ])
        self.preset_cmd.currentIndexChanged.connect(self.on_cmd_preset_changed)

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setStyleSheet("background-color: #2563eb; color: white;")
        self.btn_refresh.clicked.connect(lambda: asyncio.create_task(self.load_crontab()))

        top_row.addWidget(self.preset_sched)
        top_row.addWidget(QLabel("Cron:"))
        top_row.addWidget(self.sched_input)
        top_row.addSpacing(10)
        top_row.addWidget(self.preset_cmd, 1)
        top_row.addWidget(self.btn_refresh)
        layout.addLayout(top_row)

        # --- ROW 2: COMMAND INPUT & SAVE ---
        cmd_row = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Command or script path (e.g. /usr/bin/python3 ~/script.py >> ~/cron.log 2>&1)")
        self.cmd_input.setFont(QFont("Cascadia Mono", 11))

        self.btn_save_job = QPushButton("➕ Add Cron Job")
        self.btn_save_job.setStyleSheet("background-color: #059669; color: white; padding: 6px 16px;")
        self.btn_save_job.clicked.connect(lambda: asyncio.create_task(self.save_or_add_job()))

        self.btn_cancel_edit = QPushButton("✖ Cancel")
        self.btn_cancel_edit.setStyleSheet("background-color: #52525b; color: white; padding: 6px 16px;")
        self.btn_cancel_edit.clicked.connect(self.reset_editor)
        self.btn_cancel_edit.hide()

        cmd_row.addWidget(QLabel("Command:"))
        cmd_row.addWidget(self.cmd_input, 1)
        cmd_row.addWidget(self.btn_save_job)
        cmd_row.addWidget(self.btn_cancel_edit)
        layout.addLayout(cmd_row)

        # --- CRON TABLE ---
        self.cron_model = QStandardItemModel(0, 5)
        self.cron_model.setHorizontalHeaderLabels(["Status", "Schedule", "Frequency", "Command / Script", "Actions"])

        self.cron_table = QTableView()
        self.cron_table.setModel(self.cron_model)
        self.cron_table.setAlternatingRowColors(True)
        self.cron_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.cron_table.verticalHeader().setVisible(False)
        self.cron_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.cron_table.setColumnWidth(0, 100)
        self.cron_table.setColumnWidth(1, 120)
        self.cron_table.setColumnWidth(2, 140)
        self.cron_table.setColumnWidth(4, 280)
        layout.addWidget(self.cron_table)

    def on_sched_preset_changed(self, idx):
        presets = {
            1: "*/5 * * * *", 2: "*/15 * * * *", 3: "0 * * * *",
            4: "0 0 * * *", 5: "0 3 * * *", 6: "0 0 * * 0",
            7: "0 0 1 * *", 8: "@reboot"
        }
        if idx in presets:
            self.sched_input.setText(presets[idx])

    def on_cmd_preset_changed(self, idx):
        presets = {
            1: "bash ~/cloud_backup.sh >> ~/backup_cron.log 2>&1",
            2: "/usr/bin/python3 ~/torrent_cleaner.py >> ~/cleaner.log 2>&1",
            3: "/usr/bin/php ~/cli_master_maintenance.php >> ~/maintenance.log 2>&1",
            4: "docker system prune -af --volumes"
        }
        if idx in presets:
            self.cmd_input.setText(presets[idx])

    @staticmethod
    def describe_schedule(sched):
        s = sched.strip()
        mapping = {
            "* * * * *": "Every minute", "*/5 * * * *": "Every 5 mins",
            "*/10 * * * *": "Every 10 mins", "*/15 * * * *": "Every 15 mins",
            "*/30 * * * *": "Every 30 mins", "0 * * * *": "Every hour",
            "0 0 * * *": "Daily at 00:00", "0 3 * * *": "Daily at 03:00",
            "0 0 * * 0": "Weekly (Sun)", "0 0 1 * *": "Monthly (1st)",
            "@reboot": "On System Boot", "@hourly": "Every hour",
            "@daily": "Daily at 00:00", "@weekly": "Weekly", "@monthly": "Monthly"
        }
        if s in mapping: return mapping[s]
        parts = s.split()
        if len(parts) == 5 and parts[0].isdigit() and parts[1].isdigit() and parts[2:] == ["*", "*", "*"]:
            return f"Daily at {int(parts[1]):02d}:{int(parts[0]):02d}"
        return "Custom"

    async def load_crontab(self):
        try:
            conn, _ = await self.session_tab.get_connection()
            result = await conn.run("crontab -l 2>/dev/null || true")
            text = result.stdout or ""
            self.raw_lines = text.splitlines()
            self.parse_and_render()
        except Exception as e:
            QMessageBox.warning(self, "Crontab Error", f"Failed to load remote crontab:\n{str(e)}")

    def parse_and_render(self):
        self.cron_entries.clear()
        self.cron_model.removeRows(0, self.cron_model.rowCount())

        for idx, line in enumerate(self.raw_lines):
            stripped = line.strip()
            if not stripped: continue
            match = CRON_LINE_RE.match(stripped)
            if not match: continue

            sched = match.group("sched").strip()
            cmd = match.group("cmd").strip()
            is_commented = bool(match.group("comment"))

            if not sched.startswith("@"):
                fields = sched.split()
                if len(fields) != 5 or not all(re.match(r"^[\d\*\/\,\-]+$", f) for f in fields):
                    continue

            entry = {"line_idx": idx, "enabled": not is_commented, "schedule": sched, "command": cmd}
            self.cron_entries.append(entry)

        for row_idx, entry in enumerate(self.cron_entries):
            status_item = QStandardItem("🟢 ACTIVE" if entry["enabled"] else "⏸️ PAUSED")
            status_item.setForeground(QColor("#10b981") if entry["enabled"] else QColor("#f59e0b"))

            sched_item = QStandardItem(entry["schedule"])
            sched_item.setFont(QFont("Cascadia Mono", 10))

            freq_item = QStandardItem(self.describe_schedule(entry["schedule"]))
            freq_item.setForeground(QColor("#a1a1aa"))

            cmd_item = QStandardItem(entry["command"])
            cmd_item.setFont(QFont("Cascadia Mono", 11))

            self.cron_model.appendRow([status_item, sched_item, freq_item, cmd_item, QStandardItem("")])

            btn_wrap = QWidget()
            btn_layout = QHBoxLayout(btn_wrap)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)

            btn_toggle = QPushButton("⏸ Pause" if entry["enabled"] else "▶ Enable")
            btn_toggle.setStyleSheet(
                "background-color: #f59e0b; color: #09090b; padding: 4px 8px;"
                if entry["enabled"] else
                "background-color: #10b981; color: #09090b; padding: 4px 8px;"
            )
            btn_toggle.clicked.connect(lambda checked=False, e=entry: asyncio.create_task(self.toggle_job(e)))

            btn_run = QPushButton("⚡ Run")
            btn_run.setStyleSheet("background-color: #2563eb; color: white; padding: 4px 8px;")
            btn_run.clicked.connect(lambda checked=False, c=entry["command"]: self.run_job_now(c))

            btn_edit = QPushButton("✏️ Edit")
            btn_edit.setStyleSheet("background-color: #27272a; color: white; padding: 4px 8px;")
            btn_edit.clicked.connect(lambda checked=False, e=entry: self.load_job_into_editor(e))

            btn_del = QPushButton("🗑️")
            btn_del.setStyleSheet("background-color: #7f1d1d; color: white; padding: 4px 8px;")
            btn_del.clicked.connect(lambda checked=False, e=entry: asyncio.create_task(self.delete_job(e)))

            btn_layout.addWidget(btn_toggle)
            btn_layout.addWidget(btn_run)
            btn_layout.addWidget(btn_edit)
            btn_layout.addWidget(btn_del)
            btn_layout.addStretch()

            self.cron_table.setIndexWidget(self.cron_model.index(row_idx, 4), btn_wrap)

    async def write_crontab_to_server(self):
        content = "\n".join(self.raw_lines).strip()
        if content: content += "\n"
        try:
            conn, _ = await self.session_tab.get_connection()
            escaped = shlex.quote(content)
            cmd = f"printf %s {escaped} | crontab -" if content else "crontab -r 2>/dev/null || true"
            res = await conn.run(cmd)
            if res.exit_status != 0:
                QMessageBox.warning(self, "Cron Save Error", f"Invalid cron syntax rejected by server:\n{res.stderr}")
                await self.load_crontab()
                return False
            await self.load_crontab()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            return False

    async def save_or_add_job(self):
        sched = self.sched_input.text().strip()
        cmd = self.cmd_input.text().strip()
        if not sched or not cmd:
            QMessageBox.warning(self, "Missing Fields", "Please provide both a cron schedule and a command.")
            return

        new_line = f"{sched} {cmd}"
        if self.editing_line_idx is not None and 0 <= self.editing_line_idx < len(self.raw_lines):
            self.raw_lines[self.editing_line_idx] = new_line
        else:
            if not self.raw_lines: await self.load_crontab()
            self.raw_lines.append(new_line)

        if await self.write_crontab_to_server():
            self.reset_editor()

    def load_job_into_editor(self, entry):
        self.editing_line_idx = entry["line_idx"]
        self.sched_input.setText(entry["schedule"])
        self.cmd_input.setText(entry["command"])
        self.btn_save_job.setText("💾 Update Job")
        self.btn_cancel_edit.show()

    def reset_editor(self):
        self.editing_line_idx = None
        self.cmd_input.clear()
        self.btn_save_job.setText("➕ Add Cron Job")
        self.btn_cancel_edit.hide()

    async def toggle_job(self, entry):
        idx = entry["line_idx"]
        if 0 <= idx < len(self.raw_lines):
            if entry["enabled"]: self.raw_lines[idx] = f"# {entry['schedule']} {entry['command']}"
            else: self.raw_lines[idx] = f"{entry['schedule']} {entry['command']}"
            await self.write_crontab_to_server()

    async def delete_job(self, entry):
        idx = entry["line_idx"]
        if 0 <= idx < len(self.raw_lines):
            del self.raw_lines[idx]
            await self.write_crontab_to_server()

    def run_job_now(self, command):
        self.session_tab.execute_macro(command)
        self.session_tab.main_app.activateWindow()
