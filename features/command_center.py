import os
import sys
import json
import time
import asyncio
import subprocess
import asyncssh
import keyring
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, 
    QTableView, QHeaderView, QMenu, QMessageBox, QProgressBar,
    QTabWidget, QPushButton, QLineEdit, QSpinBox, QComboBox,
    QPlainTextEdit, QSystemTrayIcon, QStyle, QCheckBox
)
from PyQt6.QtCore import Qt, QPointF, QUrl
from PyQt6.QtGui import (
    QStandardItemModel, QStandardItem, QPainter, QPen, 
    QBrush, QColor, QPolygonF, QFont, QDesktopServices, QTextCursor
)


class LiveGraph(QWidget):
    def __init__(self, title, color_hex, dual=False, color_hex_2=None, suffix="%"):
        super().__init__()
        self.title = title
        self.color1 = QColor(color_hex)
        self.color2 = QColor(color_hex_2) if color_hex_2 else None
        self.dual = dual
        self.suffix = suffix
        self.history1 = [0.0] * 60
        self.history2 = [0.0] * 60
        self.max_val = 100.0 if not dual else 1.0
        self.setMinimumHeight(140)
        self.current_label1 = "0.0"
        self.current_label2 = "0.0"
        self.setStyleSheet("background-color: #09090b; border: 1px solid #27272a; border-radius: 8px;")

    def add_value(self, v1, v2=0.0):
        self.history1.append(float(v1))
        self.history1.pop(0)
        if self.dual:
            self.history2.append(float(v2))
            self.history2.pop(0)
            max_h = max(max(self.history1), max(self.history2))
            self.max_val = max(1.0, max_h * 1.2)
        
        self.current_label1 = f"{v1:.1f}"
        self.current_label2 = f"{v2:.1f}"
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        
        painter.setPen(QPen(QColor("#27272a"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(0, rect.height() // 2, rect.width(), rect.height() // 2)
        
        self.draw_line(painter, self.history1, self.color1)
        if self.dual:
            self.draw_line(painter, self.history2, self.color2)
            
        painter.setPen(QColor("#f4f4f5"))
        painter.setFont(QFont("Cascadia Mono", 10, QFont.Weight.Bold))
        painter.drawText(10, 20, f"{self.title}")
        
        if not self.dual:
            painter.drawText(10, 40, f"{self.current_label1}{self.suffix}")
        else:
            painter.setPen(self.color1)
            painter.drawText(10, 40, f"Rx/R: {self.current_label1} {self.suffix}")
            painter.setPen(self.color2)
            painter.drawText(10, 60, f"Tx/W: {self.current_label2} {self.suffix}")

    def draw_line(self, painter, history, color):
        w = self.width()
        h = self.height()
        pts = []
        dx = w / (len(history) - 1)
        for i, val in enumerate(history):
            x = i * dx
            y = h - (val / self.max_val) * h
            pts.append(QPointF(x, y))
        
        poly = QPolygonF(pts)
        poly.append(QPointF(w, h))
        poly.append(QPointF(0, h))
        brush = QBrush(QColor(color.red(), color.green(), color.blue(), 50))
        painter.setBrush(brush)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(poly)
        
        pen = QPen(color, 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolyline(QPolygonF(pts))


class ServerMonitorWindow(QWidget):
    def __init__(self, session_tab):
        super().__init__()
        self.session_tab = session_tab
        self.setWindowTitle(f"NMS Command Center - {session_tab.user}@{session_tab.host}")
        
        self.setStyleSheet("""
            QWidget { background-color: #09090b; color: #f4f4f5; font-family: 'Segoe UI', Ubuntu, sans-serif; }
            QTableView { background-color: #18181b; alternate-background-color: #27272a; border: none; gridline-color: #3f3f46; }
            QHeaderView::section { background-color: #09090b; color: #a1a1aa; font-weight: bold; padding: 6px; border: none; border-bottom: 1px solid #3f3f46; }
            QTabWidget::pane { border: 1px solid #27272a; }
            QTabBar::tab { background-color: #18181b; color: #a1a1aa; padding: 8px 14px; border: 1px solid #27272a; border-bottom: none; }
            QTabBar::tab:selected { background-color: #27272a; color: #f4f4f5; font-weight: bold; border-top: 2px solid #3b82f6; }
            QLineEdit, QSpinBox, QComboBox { background-color: #18181b; color: #f4f4f5; border: 1px solid #3f3f46; border-radius: 4px; padding: 4px 8px; }
            QPushButton { background-color: #27272a; color: #f4f4f5; border: 1px solid #3f3f46; border-radius: 4px; padding: 5px 12px; font-weight: bold; }
            QPushButton:hover { background-color: #3f3f46; }
        """)
        
        self.is_polling = False
        self.last_time = 0
        self.last_cpu_idle = 0
        self.last_cpu_total = 0
        self.last_net_rx = 0
        self.last_net_tx = 0
        self.last_disk_r = 0
        self.last_disk_w = 0
        self.disk_widgets = {}

        self.alerts_enabled = True
        self.known_running_containers = set()
        self.alert_cooldowns = {}
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.tray_icon.show()

        self.tunnels_file = os.path.expanduser("~/.nova_tunnels.json")
        self.saved_tunnels = self.load_saved_tunnels()
        self.active_listeners = {}

        self.backup_cfg_file = os.path.expanduser("~/.nova_backup_cfg.json")
        self.backup_process = None
        
        self.init_ui()
        self.start_polling()

    def start_polling(self):
        if not self.is_polling:
            self.is_polling = True
            asyncio.create_task(self.poll_loop())
            asyncio.create_task(self.refresh_snapshots())

    def showEvent(self, event):
        super().showEvent(event)
        self.start_polling()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 12, 15, 15)

        alert_bar = QHBoxLayout()
        self.btn_alerts = QPushButton("🔔 Desktop Alerts: ON")
        self.btn_alerts.setCheckable(True)
        self.btn_alerts.setChecked(True)
        self.btn_alerts.setStyleSheet("background-color: #059669; color: white; border: none;")
        self.btn_alerts.clicked.connect(self.toggle_alerts)

        self.cpu_thresh_spin = QSpinBox()
        self.cpu_thresh_spin.setRange(50, 100)
        self.cpu_thresh_spin.setValue(90)
        self.cpu_thresh_spin.setSuffix("%")

        self.disk_thresh_spin = QSpinBox()
        self.disk_thresh_spin.setRange(50, 100)
        self.disk_thresh_spin.setValue(90)
        self.disk_thresh_spin.setSuffix("%")

        self.chk_docker_crash = QCheckBox("Alert on Docker Crash")
        self.chk_docker_crash.setChecked(True)
        self.chk_docker_crash.setStyleSheet("color: #a1a1aa; font-weight: bold;")

        self.lbl_last_alert = QLabel("🟢 Watchdog Armed — No active alerts")
        self.lbl_last_alert.setStyleSheet("color: #10b981; font-weight: bold;")

        alert_bar.addWidget(self.btn_alerts)
        alert_bar.addSpacing(10)
        alert_bar.addWidget(QLabel("CPU Threshold:"))
        alert_bar.addWidget(self.cpu_thresh_spin)
        alert_bar.addSpacing(10)
        alert_bar.addWidget(QLabel("Disk Threshold:"))
        alert_bar.addWidget(self.disk_thresh_spin)
        alert_bar.addSpacing(10)
        alert_bar.addWidget(self.chk_docker_crash)
        alert_bar.addStretch()
        alert_bar.addWidget(self.lbl_last_alert)
        main_layout.addLayout(alert_bar)
        
        graph_layout = QHBoxLayout()
        self.cpu_graph = LiveGraph("CPU Usage", "#3b82f6", suffix="%")
        self.ram_graph = LiveGraph("RAM Usage", "#8b5cf6", suffix="%")
        self.net_graph = LiveGraph("Bandwidth", "#10b981", dual=True, color_hex_2="#f43f5e", suffix="Mbps")
        self.io_graph = LiveGraph("Disk I/O", "#f59e0b", dual=True, color_hex_2="#06b6d4", suffix="MB/s")
        
        graph_layout.addWidget(self.cpu_graph)
        graph_layout.addWidget(self.ram_graph)
        graph_layout.addWidget(self.net_graph)
        graph_layout.addWidget(self.io_graph)
        
        self.disk_container = QWidget()
        self.disk_container.setMinimumHeight(72)
        self.disk_layout = QHBoxLayout(self.disk_container)
        self.disk_layout.setContentsMargins(0, 6, 0, 6)
        
        self.bottom_tabs = QTabWidget()
        
        self.proc_model = QStandardItemModel(0, 6)
        self.proc_model.setHorizontalHeaderLabels(["PID", "User", "CPU %", "RAM %", "Command", "Action"])
        self.proc_table = QTableView()
        self.proc_table.setModel(self.proc_model)
        self.proc_table.setSortingEnabled(False)
        self.proc_table.setAlternatingRowColors(True)
        self.proc_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.proc_table.verticalHeader().setVisible(False)
        self.proc_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.proc_table.setColumnWidth(0, 80)
        self.proc_table.setColumnWidth(1, 100)
        self.proc_table.setColumnWidth(2, 80)
        self.proc_table.setColumnWidth(3, 80)
        self.proc_table.setColumnWidth(5, 90)
        self.proc_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.proc_table.customContextMenuRequested.connect(self.on_proc_context_menu)
        self.bottom_tabs.addTab(self.proc_table, "⚙️ Processes")

        self.docker_model = QStandardItemModel(0, 4)
        self.docker_model.setHorizontalHeaderLabels(["Container ID", "Name", "Status", "Actions"])
        self.docker_table = QTableView()
        self.docker_table.setModel(self.docker_model)
        self.docker_table.setSortingEnabled(False)
        self.docker_table.setAlternatingRowColors(True)
        self.docker_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.docker_table.verticalHeader().setVisible(False)
        self.docker_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.docker_table.setColumnWidth(0, 130)
        self.docker_table.setColumnWidth(1, 200)
        self.docker_table.setColumnWidth(2, 280)
        self.docker_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.docker_table.customContextMenuRequested.connect(self.on_docker_context_menu)
        self.bottom_tabs.addTab(self.docker_table, "🐳 Docker")

        self.init_tunnels_tab()
        self.init_recovery_tab()
        self.init_fleet_tab()
        self.init_updates_ssl_tab()
        
        splitter = QSplitter(Qt.Orientation.Vertical)
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addLayout(graph_layout)
        top_layout.addWidget(self.disk_container)
        
        splitter.addWidget(top_widget)
        splitter.addWidget(self.bottom_tabs)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)

    # ----------------------------------------------------
    # NEW TAB 6: UPDATES & SSL MONITOR
    # ----------------------------------------------------
    def init_updates_ssl_tab(self):
        upd_widget = QWidget()
        upd_layout = QVBoxLayout(upd_widget)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Side: APT Packages
        apt_container = QWidget()
        apt_layout = QVBoxLayout(apt_container)
        apt_layout.setContentsMargins(0,0,0,0)
        
        apt_bar = QHBoxLayout()
        apt_bar.addWidget(QLabel("📦 APT Package Updates", styleSheet="font-weight:bold; color:#10b981;"))
        btn_scan_apt = QPushButton("🔄 Scan")
        btn_scan_apt.clicked.connect(lambda: asyncio.create_task(self.scan_apt_async()))
        btn_upg_apt = QPushButton("⚡ Upgrade All")
        btn_upg_apt.setStyleSheet("background-color: #2563eb; color: white;")
        btn_upg_apt.clicked.connect(lambda: self.session_tab.execute_macro("sudo apt update && sudo apt upgrade -y\n"))
        apt_bar.addStretch()
        apt_bar.addWidget(btn_scan_apt)
        apt_bar.addWidget(btn_upg_apt)
        apt_layout.addLayout(apt_bar)

        self.apt_model = QStandardItemModel(0, 3)
        self.apt_model.setHorizontalHeaderLabels(["Package Name", "New Version", "Current Version"])
        self.apt_table = QTableView()
        self.apt_table.setModel(self.apt_model)
        self.apt_table.setAlternatingRowColors(True)
        self.apt_table.verticalHeader().setVisible(False)
        self.apt_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        apt_layout.addWidget(self.apt_table)

        # Right Side: SSL Certs
        ssl_container = QWidget()
        ssl_layout = QVBoxLayout(ssl_container)
        ssl_layout.setContentsMargins(0,0,0,0)

        ssl_bar = QHBoxLayout()
        ssl_bar.addWidget(QLabel("🔐 Let's Encrypt / SSL Monitor", styleSheet="font-weight:bold; color:#a855f7;"))
        btn_scan_ssl = QPushButton("🔄 Scan Certs")
        btn_scan_ssl.clicked.connect(lambda: asyncio.create_task(self.scan_ssl_async()))
        btn_ren_ssl = QPushButton("⚡ Force Renew")
        btn_ren_ssl.setStyleSheet("background-color: #2563eb; color: white;")
        btn_ren_ssl.clicked.connect(lambda: self.session_tab.execute_macro("sudo certbot renew\n"))
        ssl_bar.addStretch()
        ssl_bar.addWidget(btn_scan_ssl)
        ssl_bar.addWidget(btn_ren_ssl)
        ssl_layout.addLayout(ssl_bar)

        self.ssl_model = QStandardItemModel(0, 4)
        self.ssl_model.setHorizontalHeaderLabels(["Domain", "Expiry Date", "Days Left", "Status"])
        self.ssl_table = QTableView()
        self.ssl_table.setModel(self.ssl_model)
        self.ssl_table.setAlternatingRowColors(True)
        self.ssl_table.verticalHeader().setVisible(False)
        self.ssl_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        ssl_layout.addWidget(self.ssl_table)

        splitter.addWidget(apt_container)
        splitter.addWidget(ssl_container)
        upd_layout.addWidget(splitter)

        self.bottom_tabs.addTab(upd_widget, "📦 Updates & SSL")

    async def scan_apt_async(self):
        self.apt_model.removeRows(0, self.apt_model.rowCount())
        try:
            conn, _ = await self.session_tab.get_connection()
            res = await conn.run("apt list --upgradable 2>/dev/null")
            if res.exit_status == 0:
                for line in res.stdout.strip().splitlines():
                    if "Listing" in line or not line.strip(): continue
                    parts = line.split()
                    if len(parts) >= 6 and "[upgradable" in line:
                        pkg_name = parts[0].split('/')[0]
                        new_ver = parts[1]
                        old_ver = parts[5].strip(']')
                        self.apt_model.appendRow([
                            QStandardItem(pkg_name),
                            QStandardItem(new_ver),
                            QStandardItem(old_ver)
                        ])
            else:
                self.apt_model.appendRow([QStandardItem("System uses different package manager"), QStandardItem(""), QStandardItem("")])
        except Exception as e:
            pass

    async def scan_ssl_async(self):
        self.ssl_model.removeRows(0, self.ssl_model.rowCount())
        try:
            conn, _ = await self.session_tab.get_connection()
            cmd = """sudo -S bash -c 'for d in /etc/letsencrypt/live/*; do if [ -d "$d" ] && [ -f "$d/cert.pem" ]; then exp=$(openssl x509 -enddate -noout -in "$d/cert.pem" | cut -d= -f2); echo "$(basename $d)|$exp"; fi; done'"""
            pwd_input = self.session_tab.password + "\n" if self.session_tab.password else None
            res = await conn.run(cmd, input=pwd_input)

            if res.stdout and "|" in res.stdout:
                for line in res.stdout.strip().splitlines():
                    if '|' not in line: continue
                    domain, exp_str = line.split('|', 1)
                    try:
                        exp_date = datetime.strptime(exp_str.strip(), "%b %d %H:%M:%S %Y %Z")
                        days_left = (exp_date - datetime.utcnow()).days
                        stat_item = QStandardItem("🟢 Valid" if days_left > 15 else "🔴 Expiring")
                        stat_item.setForeground(QColor("#10b981") if days_left > 15 else QColor("#ef4444"))
                        
                        self.ssl_model.appendRow([
                            QStandardItem(domain),
                            QStandardItem(exp_date.strftime("%Y-%m-%d")),
                            QStandardItem(str(days_left)),
                            stat_item
                        ])
                    except Exception:
                        self.ssl_model.appendRow([QStandardItem(domain), QStandardItem(exp_str), QStandardItem("?"), QStandardItem("Unknown")])
            else:
                self.ssl_model.appendRow([QStandardItem("No certs found in /etc/letsencrypt/live"), QStandardItem(""), QStandardItem(""), QStandardItem("")])
        except Exception as e:
            pass

    # ----------------------------------------------------
    # TAB 3: VISUAL SSH TUNNELS (PORT FORWARDING)
    # ----------------------------------------------------
    def init_tunnels_tab(self):
        tunnel_widget = QWidget()
        layout = QVBoxLayout(tunnel_widget)

        form_bar = QHBoxLayout()
        self.tunnel_preset = QComboBox()
        self.tunnel_preset.addItems([
            "Custom Tunnel...",
            "Portainer Web UI (9000 -> 9000)",
            "MariaDB / MySQL (3307 -> 3306)",
            "Nginx / HTTP Web (8080 -> 80)",
            "Pi-hole Web Admin (8081 -> 80)",
            "Prowlarr (9696 -> 9696)",
            "Byparr (8191 -> 8191)"
        ])
        self.tunnel_preset.currentIndexChanged.connect(self.on_tunnel_preset_changed)

        self.tun_name_input = QLineEdit()
        self.tun_name_input.setPlaceholderText("Service Name (e.g. Portainer)")
        
        self.tun_local_port = QSpinBox()
        self.tun_local_port.setRange(1024, 65535)
        self.tun_local_port.setValue(9000)

        self.tun_remote_host = QLineEdit("127.0.0.1")
        self.tun_remote_host.setFixedWidth(120)

        self.tun_remote_port = QSpinBox()
        self.tun_remote_port.setRange(1, 65535)
        self.tun_remote_port.setValue(9000)

        btn_add_tun = QPushButton("➕ Save & Start Tunnel")
        btn_add_tun.setStyleSheet("background-color: #2563eb; color: white; border: none;")
        btn_add_tun.clicked.connect(self.add_and_start_tunnel)

        form_bar.addWidget(QLabel("Preset:"))
        form_bar.addWidget(self.tunnel_preset)
        form_bar.addWidget(QLabel("Label:"))
        form_bar.addWidget(self.tun_name_input)
        form_bar.addWidget(QLabel("Local Port:"))
        form_bar.addWidget(self.tun_local_port)
        form_bar.addWidget(QLabel("➔ Remote Host:"))
        form_bar.addWidget(self.tun_remote_host)
        form_bar.addWidget(QLabel("Remote Port:"))
        form_bar.addWidget(self.tun_remote_port)
        form_bar.addWidget(btn_add_tun)
        layout.addLayout(form_bar)

        self.tunnel_model = QStandardItemModel(0, 5)
        self.tunnel_model.setHorizontalHeaderLabels(["Service Name", "Local Address", "Remote Target", "Status", "Actions"])
        self.tunnel_table = QTableView()
        self.tunnel_table.setModel(self.tunnel_model)
        self.tunnel_table.setAlternatingRowColors(True)
        self.tunnel_table.verticalHeader().setVisible(False)
        self.tunnel_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.tunnel_table.setColumnWidth(0, 180)
        self.tunnel_table.setColumnWidth(1, 180)
        self.tunnel_table.setColumnWidth(2, 180)
        self.tunnel_table.setColumnWidth(3, 140)
        layout.addWidget(self.tunnel_table)

        self.bottom_tabs.addTab(tunnel_widget, "🚇 Tunnels")
        self.render_tunnels_table()

    def on_tunnel_preset_changed(self, idx):
        presets = {
            1: ("Portainer", 9000, "127.0.0.1", 9000),
            2: ("MariaDB", 3307, "127.0.0.1", 3306),
            3: ("Remote Web", 8080, "127.0.0.1", 80),
            4: ("Pi-hole Admin", 8081, "127.0.0.1", 80),
            5: ("Prowlarr", 9696, "127.0.0.1", 9696),
            6: ("Byparr", 8191, "127.0.0.1", 8191),
        }
        if idx in presets:
            name, lport, rhost, rport = presets[idx]
            self.tun_name_input.setText(name)
            self.tun_local_port.setValue(lport)
            self.tun_remote_host.setText(rhost)
            self.tun_remote_port.setValue(rport)

    def load_saved_tunnels(self):
        if os.path.exists(self.tunnels_file):
            try:
                with open(self.tunnels_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def save_tunnels_to_disk(self):
        try:
            with open(self.tunnels_file, "w") as f:
                json.dump(self.saved_tunnels, f, indent=2)
        except Exception:
            pass

    def add_and_start_tunnel(self):
        name = self.tun_name_input.text().strip() or f"Tunnel-{self.tun_local_port.value()}"
        lport = self.tun_local_port.value()
        rhost = self.tun_remote_host.text().strip() or "127.0.0.1"
        rport = self.tun_remote_port.value()

        self.saved_tunnels = [t for t in self.saved_tunnels if t.get("lport") != lport]
        tun_obj = {"name": name, "lport": lport, "rhost": rhost, "rport": rport}
        self.saved_tunnels.append(tun_obj)
        self.save_tunnels_to_disk()
        asyncio.create_task(self.toggle_tunnel_async(tun_obj, start=True))

    async def toggle_tunnel_async(self, tun_obj, start=True):
        lport = tun_obj["lport"]
        if not start:
            listener = self.active_listeners.pop(lport, None)
            if listener:
                listener.close()
            self.render_tunnels_table()
            return

        if lport in self.active_listeners:
            return

        try:
            conn, _ = await self.session_tab.get_connection()
            listener = await conn.forward_local_port("127.0.0.1", lport, tun_obj["rhost"], tun_obj["rport"])
            self.active_listeners[lport] = listener
            self.render_tunnels_table()
        except Exception as e:
            QMessageBox.warning(self, "Tunnel Error", f"Could not bind local port {lport}:\n{str(e)}")
            self.render_tunnels_table()

    def remove_saved_tunnel(self, lport):
        listener = self.active_listeners.pop(lport, None)
        if listener:
            listener.close()
        self.saved_tunnels = [t for t in self.saved_tunnels if t.get("lport") != lport]
        self.save_tunnels_to_disk()
        self.render_tunnels_table()

    def render_tunnels_table(self):
        self.tunnel_model.removeRows(0, self.tunnel_model.rowCount())
        for row_idx, t in enumerate(self.saved_tunnels):
            lport = t["lport"]
            is_active = lport in self.active_listeners

            status_item = QStandardItem("🟢 ACTIVE (Forwarding)" if is_active else "⚪ STOPPED")
            status_item.setForeground(QColor("#10b981") if is_active else QColor("#a1a1aa"))

            self.tunnel_model.appendRow([
                QStandardItem(t["name"]),
                QStandardItem(f"127.0.0.1:{lport}"),
                QStandardItem(f"{t['rhost']}:{t['rport']}"),
                status_item,
                QStandardItem("")
            ])

            btn_wrap = QWidget()
            btn_layout = QHBoxLayout(btn_wrap)
            btn_layout.setContentsMargins(5, 2, 5, 2)
            btn_layout.setSpacing(8)

            if is_active:
                btn_toggle = QPushButton("⏹ Stop")
                btn_toggle.setStyleSheet("background-color: #f59e0b; color: #09090b; border: none;")
                btn_toggle.clicked.connect(lambda checked=False, obj=t: asyncio.create_task(self.toggle_tunnel_async(obj, start=False)))
            else:
                btn_toggle = QPushButton("▶ Start")
                btn_toggle.setStyleSheet("background-color: #10b981; color: #09090b; border: none;")
                btn_toggle.clicked.connect(lambda checked=False, obj=t: asyncio.create_task(self.toggle_tunnel_async(obj, start=True)))

            is_db = t['rport'] in [3306, 5432, 27017, 6379, 11211, 1433]
            
            btn_open = QPushButton("🌐 Open in Browser")
            btn_open.setEnabled(is_active and not is_db)
            if is_db:
                btn_open.setText("💾 DB Tunnel Active")
                btn_open.setStyleSheet("background-color: #27272a; color: #a1a1aa; border: none;")
            else:
                btn_open.clicked.connect(lambda checked=False, p=lport: QDesktopServices.openUrl(QUrl(f"http://127.0.0.1:{p}")))

            btn_del = QPushButton("🗑️ Delete")
            btn_del.setStyleSheet("background-color: #7f1d1d; color: white; border: none;")
            btn_del.clicked.connect(lambda checked=False, p=lport: self.remove_saved_tunnel(p))

            btn_layout.addWidget(btn_toggle)
            btn_layout.addWidget(btn_open)
            btn_layout.addWidget(btn_del)
            btn_layout.addStretch()

            self.tunnel_table.setIndexWidget(self.tunnel_model.index(row_idx, 4), btn_wrap)

    # ----------------------------------------------------
    # TAB 4: DISASTER RECOVERY (SNAPSHOTS & RCLONE)
    # ----------------------------------------------------
    def init_recovery_tab(self):
        rec_splitter = QSplitter(Qt.Orientation.Horizontal)

        snap_widget = QWidget()
        snap_layout = QVBoxLayout(snap_widget)
        snap_layout.addWidget(QLabel("📸 1-Click Directory Snapshots (~/.nova_snapshots)", styleSheet="font-weight: bold; font-size: 13px; color: #38bdf8;"))

        snap_bar = QHBoxLayout()
        self.snap_target_input = QLineEdit(self.session_tab.current_remote_path or "/etc/nginx")
        btn_grab_path = QPushButton("📍 Active Path")
        btn_grab_path.clicked.connect(lambda: self.snap_target_input.setText(self.session_tab.current_remote_path))
        btn_take_snap = QPushButton("📸 Snapshot")
        btn_take_snap.setStyleSheet("background-color: #059669; color: white; border: none;")
        btn_take_snap.clicked.connect(lambda: asyncio.create_task(self.create_snapshot_async()))

        snap_bar.addWidget(self.snap_target_input, 1)
        snap_bar.addWidget(btn_grab_path)
        snap_bar.addWidget(btn_take_snap)
        snap_layout.addLayout(snap_bar)

        self.snap_model = QStandardItemModel(0, 4)
        self.snap_model.setHorizontalHeaderLabels(["Snapshot Archive", "Size", "Created", "Actions"])
        self.snap_table = QTableView()
        self.snap_table.setModel(self.snap_model)
        self.snap_table.setAlternatingRowColors(True)
        self.snap_table.verticalHeader().setVisible(False)
        self.snap_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.snap_table.setColumnWidth(1, 80)
        self.snap_table.setColumnWidth(2, 130)
        self.snap_table.setColumnWidth(3, 190)
        snap_layout.addWidget(self.snap_table)

        rclone_widget = QWidget()
        rclone_layout = QVBoxLayout(rclone_widget)
        rclone_layout.addWidget(QLabel("☁️ Rclone & Cloud Backup Runner", styleSheet="font-weight: bold; font-size: 13px; color: #a855f7;"))

        cmd_bar = QHBoxLayout()
        saved_cmd = "bash ~/cloud_backup.sh"
        if os.path.exists(self.backup_cfg_file):
            try:
                with open(self.backup_cfg_file, "r") as f:
                    saved_cmd = json.load(f).get("cmd", saved_cmd)
            except Exception:
                pass

        self.backup_cmd_input = QLineEdit(saved_cmd)
        self.backup_cmd_input.setPlaceholderText("e.g. bash ~/cloud_backup.sh or rclone sync / gdrive:")

        btn_run_backup = QPushButton("🚀 Run Backup")
        btn_run_backup.setStyleSheet("background-color: #7c3aed; color: white; border: none;")
        btn_run_backup.clicked.connect(lambda: asyncio.create_task(self.run_backup_script_async()))

        btn_stop_backup = QPushButton("⏹ Abort")
        btn_stop_backup.setStyleSheet("background-color: #7f1d1d; color: white; border: none;")
        btn_stop_backup.clicked.connect(self.abort_backup_script)

        cmd_bar.addWidget(self.backup_cmd_input, 1)
        cmd_bar.addWidget(btn_run_backup)
        cmd_bar.addWidget(btn_stop_backup)
        rclone_layout.addLayout(cmd_bar)

        preset_bar = QHBoxLayout()
        btn_p1 = QPushButton("Preset: ~/cloud_backup.sh")
        btn_p1.clicked.connect(lambda: self.backup_cmd_input.setText("bash ~/cloud_backup.sh"))
        btn_p2 = QPushButton("Preset: List Rclone Remotes")
        btn_p2.clicked.connect(lambda: self.backup_cmd_input.setText("rclone listremotes --long"))
        preset_bar.addWidget(btn_p1)
        preset_bar.addWidget(btn_p2)
        preset_bar.addStretch()
        rclone_layout.addLayout(preset_bar)

        self.backup_output = QPlainTextEdit()
        self.backup_output.setReadOnly(True)
        self.backup_output.setStyleSheet('background-color: #0c0a09; color: #38bdf8; font-family: "Cascadia Mono", monospace; font-size: 12px; border: 1px solid #27272a; border-radius: 6px;')
        rclone_layout.addWidget(self.backup_output)

        rec_splitter.addWidget(snap_widget)
        rec_splitter.addWidget(rclone_widget)

        self.bottom_tabs.addTab(rec_splitter, "🛡️ Backups")

    async def create_snapshot_async(self):
        target = self.snap_target_input.text().strip().rstrip("/")
        if not target or target == ".": target = self.session_tab.current_remote_path.rstrip("/")
        if not target or target == "/":
            QMessageBox.warning(self, "Invalid Path", "Please specify a valid folder (not root '/') to snapshot.")
            return

        parent_dir = os.path.dirname(target) or "/"
        base_name = os.path.basename(target)
        ts = time.strftime("%Y%m%d_%H%M%S")
        archive_name = f"{base_name}__{ts}.tar.gz"

        try:
            conn, _ = await self.session_tab.get_connection()
            cmd = f"mkdir -p ~/.nova_snapshots && tar -czf ~/.nova_snapshots/\"{archive_name}\" -C \"{parent_dir}\" \"{base_name}\""
            res = await conn.run(cmd)
            if res.exit_status != 0:
                QMessageBox.warning(self, "Snapshot Error", f"Failed creating snapshot:\n{res.stderr}")
            else:
                await self.refresh_snapshots()
                QMessageBox.information(self, "Snapshot Created", f"Saved snapshot:\n~/.nova_snapshots/{archive_name}")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    async def refresh_snapshots(self):
        try:
            conn, _ = await self.session_tab.get_connection()
            cmd = """mkdir -p ~/.nova_snapshots && ls -lh --time-style=long-iso ~/.nova_snapshots/*.tar.gz 2>/dev/null | awk '{print $8 "|" $5 "|" $6 " " $7}'"""
            res = await conn.run(cmd)
            self.snap_model.removeRows(0, self.snap_model.rowCount())
            if res.exit_status == 0 and res.stdout.strip():
                for row_idx, line in enumerate(res.stdout.strip().splitlines()):
                    parts = line.split("|")
                    if len(parts) == 3:
                        full_path, size_str, date_str = parts
                        fname = os.path.basename(full_path)
                        self.snap_model.appendRow([
                            QStandardItem(fname),
                            QStandardItem(size_str),
                            QStandardItem(date_str),
                            QStandardItem("")
                        ])

                        btn_wrap = QWidget()
                        bl = QHBoxLayout(btn_wrap)
                        bl.setContentsMargins(4, 2, 4, 2)
                        bl.setSpacing(6)

                        btn_restore = QPushButton("⏪ Restore")
                        btn_restore.setStyleSheet("background-color: #059669; color: white; border: none;")
                        btn_restore.clicked.connect(lambda checked=False, f=fname: asyncio.create_task(self.restore_snapshot_async(f)))

                        btn_del = QPushButton("🗑️")
                        btn_del.setStyleSheet("background-color: #7f1d1d; color: white; border: none;")
                        btn_del.clicked.connect(lambda checked=False, f=fname: asyncio.create_task(self.delete_snapshot_async(f)))

                        bl.addWidget(btn_restore)
                        bl.addWidget(btn_del)
                        bl.addStretch()
                        self.snap_table.setIndexWidget(self.snap_model.index(row_idx, 3), btn_wrap)
        except Exception:
            pass

    async def restore_snapshot_async(self, archive_name):
        dest = self.snap_target_input.text().strip().rstrip("/") or self.session_tab.current_remote_path
        parent_dir = os.path.dirname(dest) or "/"
        reply = QMessageBox.question(self, "Confirm Rollback", f"Extract '{archive_name}' back into '{parent_dir}'?\nExisting files in that directory will be overwritten.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        try:
            conn, _ = await self.session_tab.get_connection()
            res = await conn.run(f"tar -xzf ~/.nova_snapshots/\"{archive_name}\" -C \"{parent_dir}\"")
            if res.exit_status == 0:
                QMessageBox.information(self, "Rollback Complete", f"Successfully restored {archive_name} into {parent_dir}.")
                asyncio.create_task(self.session_tab.load_remote_directory(self.session_tab.current_remote_path, record_history=False))
            else:
                QMessageBox.warning(self, "Restore Failed", res.stderr)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    async def delete_snapshot_async(self, archive_name):
        try:
            conn, _ = await self.session_tab.get_connection()
            await conn.run(f"rm -f ~/.nova_snapshots/\"{archive_name}\"")
            await self.refresh_snapshots()
        except Exception:
            pass

    async def run_backup_script_async(self):
        cmd = self.backup_cmd_input.text().strip()
        if not cmd: return
        try:
            with open(self.backup_cfg_file, "w") as f:
                json.dump({"cmd": cmd}, f)
        except Exception: pass

        self.backup_output.clear()
        self.backup_output.appendPlainText(f"=== Launching: {cmd} ===\n")
        try:
            conn, _ = await self.session_tab.get_connection()
            self.backup_process = await conn.create_process(cmd, term_type="xterm")
            while True:
                chunk = await self.backup_process.stdout.read(1024)
                if not chunk: break
                self.backup_output.insertPlainText(chunk.replace("\r", "\n"))
                self.backup_output.moveCursor(QTextCursor.MoveOperation.End)
            self.backup_output.appendPlainText("\n=== Task Finished ===")
        except Exception as e:
            self.backup_output.appendPlainText(f"\n[Execution Error]: {str(e)}")
        finally:
            self.backup_process = None

    def abort_backup_script(self):
        if self.backup_process:
            self.backup_process.terminate()
            self.backup_output.appendPlainText("\n[Aborted by User]")

    # ----------------------------------------------------
    # TAB 5: THE FLEET MATRIX (MULTI-SERVER OVERVIEW)
    # ----------------------------------------------------
    def init_fleet_tab(self):
        fleet_widget = QWidget()
        layout = QVBoxLayout(fleet_widget)

        top_bar = QHBoxLayout()
        btn_scan = QPushButton("🔄 Poll Entire Fleet Now")
        btn_scan.setStyleSheet("background-color: #2563eb; color: white; border: none;")
        btn_scan.clicked.connect(lambda: asyncio.create_task(self.scan_fleet_async()))

        self.lbl_fleet_status = QLabel("Click 'Poll Entire Fleet Now' to query all saved servers in parallel.")
        self.lbl_fleet_status.setStyleSheet("color: #a1a1aa;")

        top_bar.addWidget(btn_scan)
        top_bar.addSpacing(12)
        top_bar.addWidget(self.lbl_fleet_status)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.fleet_model = QStandardItemModel(0, 7)
        self.fleet_model.setHorizontalHeaderLabels([
            "Server Name", "Host", "Status", "Load Avg (1m)", "RAM Usage", "Root Disk /", "Docker Stack & Uptime"
        ])
        self.fleet_table = QTableView()
        self.fleet_table.setModel(self.fleet_model)
        self.fleet_table.setAlternatingRowColors(True)
        self.fleet_table.verticalHeader().setVisible(False)
        self.fleet_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.fleet_table.setColumnWidth(0, 160)
        self.fleet_table.setColumnWidth(1, 160)
        self.fleet_table.setColumnWidth(2, 120)
        self.fleet_table.setColumnWidth(3, 120)
        self.fleet_table.setColumnWidth(4, 120)
        self.fleet_table.setColumnWidth(5, 120)
        layout.addWidget(self.fleet_table)

        self.bottom_tabs.addTab(fleet_widget, "🌐 Fleet")

    async def probe_single_site(self, site_name, site_data):
        host = site_data.get("host", "")
        port = site_data.get("port", 22)
        user = site_data.get("user", "")
        key_path = site_data.get("key_path", "")
        password = keyring.get_password("nova_sftp", site_name)

        probe_cmd = """python3 -c '
import json, subprocess
res = {"load": "0.00", "ram": "0%", "disk": "0%", "docker": "No Docker", "uptime": ""}
try:
    with open("/proc/loadavg") as f: res["load"] = f.read().split()[0]
except: pass
try:
    m = subprocess.check_output(["free", "-m"]).decode().splitlines()[1].split()
    res["ram"] = f"{float(m[2])*100/float(m[1]):.1f}%"
except: pass
try:
    d = subprocess.check_output(["df", "-hP", "/"]).decode().splitlines()[1].split()
    res["disk"] = f"{d[4]} ({d[2]}/{d[1]})"
except: pass
try:
    up = subprocess.check_output(["uptime", "-p"]).decode().strip()
    res["uptime"] = up
except: pass
try:
    dk = subprocess.check_output(["docker", "ps", "-a", "--format", "{{.State}}"], stderr=subprocess.DEVNULL).decode().splitlines()
    run = sum(1 for x in dk if x.strip() == "running")
    res["docker"] = f"{run}/{len(dk)} Running"
except: pass
print(json.dumps(res))
'"""
        try:
            if host == self.session_tab.host and port == self.session_tab.port and user == self.session_tab.user:
                conn, _ = await self.session_tab.get_connection()
                out = await asyncio.wait_for(conn.run(probe_cmd), timeout=6.0)
                info = json.loads(out.stdout.strip())
                return (site_name, f"{host}:{port}", True, info)

            connect_kwargs = {"host": host, "port": port, "username": user, "known_hosts": None}
            if key_path and os.path.exists(key_path):
                connect_kwargs["client_keys"] = [key_path]
                if password: connect_kwargs["passphrase"] = password
            elif password:
                connect_kwargs["password"] = password

            async with asyncio.timeout(6.0):
                async with asyncssh.connect(**connect_kwargs) as conn:
                    out = await conn.run(probe_cmd)
                    info = json.loads(out.stdout.strip())
                    return (site_name, f"{host}:{port}", True, info)
        except Exception as e:
            return (site_name, f"{host}:{port}", False, {"error": str(e)})

    async def scan_fleet_async(self):
        sites = dict(self.session_tab.main_app.sidebar.sites)
        if not sites:
            sites[f"Active ({self.session_tab.host})"] = {
                "host": self.session_tab.host, "port": self.session_tab.port,
                "user": self.session_tab.user, "key_path": self.session_tab.key_path
            }

        self.lbl_fleet_status.setText(f"Scanning {len(sites)} server(s) in parallel...")
        tasks = [self.probe_single_site(name, data) for name, data in sites.items()]
        results = await asyncio.gather(*tasks)

        self.fleet_model.removeRows(0, self.fleet_model.rowCount())
        online_count = 0
        for site_name, host_str, is_online, info in results:
            if is_online:
                online_count += 1
                st_item = QStandardItem("🟢 ONLINE")
                st_item.setForeground(QColor("#10b981"))
                self.fleet_model.appendRow([
                    QStandardItem(site_name), QStandardItem(host_str), st_item,
                    QStandardItem(str(info.get("load", ""))), QStandardItem(str(info.get("ram", ""))),
                    QStandardItem(str(info.get("disk", ""))), QStandardItem(f"🐳 {info.get('docker', '')}  |  ⏱️ {info.get('uptime', '')}")
                ])
            else:
                st_item = QStandardItem("🔴 OFFLINE")
                st_item.setForeground(QColor("#ef4444"))
                self.fleet_model.appendRow([
                    QStandardItem(site_name), QStandardItem(host_str), st_item,
                    QStandardItem("-"), QStandardItem("-"), QStandardItem("-"),
                    QStandardItem(f"Unreachable: {info.get('error', 'Timeout')[:60]}")
                ])

        self.lbl_fleet_status.setText(f"Fleet Scan Complete: {online_count}/{len(results)} Online ({time.strftime('%H:%M:%S')})")

    # ----------------------------------------------------
    # THRESHOLD DESKTOP ALERTS ENGINE
    # ----------------------------------------------------
    def toggle_alerts(self):
        self.alerts_enabled = self.btn_alerts.isChecked()
        if self.alerts_enabled:
            self.btn_alerts.setText("🔔 Desktop Alerts: ON")
            self.btn_alerts.setStyleSheet("background-color: #059669; color: white; border: none;")
        else:
            self.btn_alerts.setText("🔕 Desktop Alerts: OFF")
            self.btn_alerts.setStyleSheet("background-color: #52525b; color: white; border: none;")

    def trigger_desktop_alert(self, key, title, message):
        if not self.alerts_enabled: return
        now = time.time()
        if now - self.alert_cooldowns.get(key, 0) < 60: return
        self.alert_cooldowns[key] = now

        self.lbl_last_alert.setText(f"⚠️ {title}: {message}")
        self.lbl_last_alert.setStyleSheet("color: #ef4444; font-weight: bold;")

        try:
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Warning, 5000)
        except Exception: pass

        if sys.platform.startswith("linux"):
            try: subprocess.Popen(["notify-send", "-u", "critical", title, message])
            except Exception: pass

    # ----------------------------------------------------
    # PYTHON INJECTION & DATA POLLING
    # ----------------------------------------------------
    async def poll_loop(self):
        payload = """python3 -c '
import json, subprocess, os
res = {"cpu_idle":0, "cpu_total":0, "ram":0, "net_rx":0, "net_tx":0, "disk_r":0, "disk_w":0, "disk":[], "procs":[], "docker":[]}
try:
    with open("/proc/stat") as f:
        p = f.readline().split()
        res["cpu_idle"] = int(p[4])
        res["cpu_total"] = sum(int(x) for x in p[1:8])
except: pass
try:
    out = subprocess.check_output(["free", "-m"]).decode("utf-8", "ignore").splitlines()[1].split()
    res["ram"] = float(out[2]) * 100 / float(out[1])
except: pass
try:
    with open("/proc/net/dev") as f:
        rx = tx = 0
        for l in f:
            if ":" in l:
                p = l.split(":")[1].split()
                rx += int(p[0]); tx += int(p[8])
        res["net_rx"] = rx; res["net_tx"] = tx
except: pass
try:
    with open("/proc/diskstats") as f:
        r = w = 0
        for l in f:
            p = l.split()
            if p[2].startswith("sd") or p[2].startswith("nvme") or p[2].startswith("vd"):
                r += int(p[5]); w += int(p[9])
        res["disk_r"] = r; res["disk_w"] = w
except: pass
try:
    df = subprocess.check_output(["df", "-hP"]).decode("utf-8", "ignore").splitlines()
    for l in df[1:]:
        p = l.split()
        if len(p) >= 6 and p[0] not in ["tmpfs", "devtmpfs", "overlay"]:
            res["disk"].append({"mount": p[5], "size": p[1], "used": p[2], "pct": p[4]})
except: pass
try:
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    ps = subprocess.check_output(["ps", "-eo", "pid,user,%cpu,%mem,comm", "--sort=-%cpu"], env=env).decode("utf-8", "ignore").splitlines()
    for l in ps[1:151]:
        p = l.split(None, 4)
        if len(p) == 5:
            res["procs"].append({"pid": int(p[0]), "user": p[1], "cpu": float(p[2].replace(",", ".")), "mem": float(p[3].replace(",", ".")), "cmd": p[4].strip()})
except: pass
try:
    dk = subprocess.check_output(["docker", "ps", "-a", "--format", "{{.ID}}|{{.Names}}|{{.State}}|{{.Status}}"], stderr=subprocess.DEVNULL).decode("utf-8", "ignore").splitlines()
    for l in dk:
        if l.strip():
            p = l.split("|", 3)
            res["docker"].append({"id": p[0], "name": p[1] if len(p)>1 else "", "state": p[2] if len(p)>2 else "", "status": p[3] if len(p)>3 else ""})
except: pass
print(json.dumps(res))
'"""
        
        while self.is_polling:
            try:
                conn, _ = await self.session_tab.get_connection()
                result = await conn.run(payload)
                if result.exit_status == 0:
                    try:
                        data = json.loads(result.stdout.strip())
                        self.update_dashboard(data)
                    except Exception: pass
            except Exception: pass
            await asyncio.sleep(1.5)

    def update_dashboard(self, data):
        current_time = time.time()
        dt = current_time - self.last_time
        
        cpu_idle = data.get('cpu_idle', 0)
        cpu_total = data.get('cpu_total', 0)
        
        if self.last_time > 0 and dt > 0:
            d_idle = cpu_idle - self.last_cpu_idle
            d_total = cpu_total - self.last_cpu_total
            cpu_pct = (1.0 - d_idle / d_total) * 100.0 if d_total > 0 else 0.0
            self.cpu_graph.add_value(cpu_pct)

            if cpu_pct >= self.cpu_thresh_spin.value():
                self.trigger_desktop_alert("cpu_high", f"High CPU on {self.session_tab.host}", f"CPU hit {cpu_pct:.1f}%")
            
            rx_bps = (data.get('net_rx', 0) - self.last_net_rx) / dt
            tx_bps = (data.get('net_tx', 0) - self.last_net_tx) / dt
            self.net_graph.add_value((rx_bps * 8) / 1048576, (tx_bps * 8) / 1048576)
            
            r_bps = ((data.get('disk_r', 0) - self.last_disk_r) * 512) / dt
            w_bps = ((data.get('disk_w', 0) - self.last_disk_w) * 512) / dt
            self.io_graph.add_value(r_bps / 1048576, w_bps / 1048576)
        else:
            self.cpu_graph.add_value(0)
            self.net_graph.add_value(0, 0)
            self.io_graph.add_value(0, 0)
            
        self.ram_graph.add_value(data.get('ram', 0))
        
        self.last_time = current_time
        self.last_cpu_idle = cpu_idle
        self.last_cpu_total = cpu_total
        self.last_net_rx = data.get('net_rx', 0)
        self.last_net_tx = data.get('net_tx', 0)
        self.last_disk_r = data.get('disk_r', 0)
        self.last_disk_w = data.get('disk_w', 0)

        self.update_disks(data.get('disk', []))
        self.update_processes(data.get('procs', []))
        self.update_docker(data.get('docker', []))

    def update_disks(self, disks):
        for d in disks:
            mount = d.get('mount', 'Unknown')
            try: pct = int(str(d.get('pct', '0%')).replace('%', ''))
            except: pct = 0
                
            lbl_text = f"{mount} ({d.get('used', '0')}/{d.get('size', '0')})"
            if mount not in self.disk_widgets:
                w = QWidget()
                w.setStyleSheet("background-color: #18181b; border-radius: 6px; padding: 5px;")
                l = QVBoxLayout(w)
                lbl = QLabel()
                lbl.setStyleSheet("color: #a1a1aa; font-size: 11px;")
                pb = QProgressBar()
                pb.setFixedHeight(12)
                pb.setTextVisible(False)
                l.addWidget(lbl)
                l.addWidget(pb)
                self.disk_layout.addWidget(w)
                self.disk_widgets[mount] = {'widget': w, 'lbl': lbl, 'pb': pb}
                
            ui = self.disk_widgets[mount]
            ui['lbl'].setText(lbl_text)
            ui['pb'].setValue(pct)
            
            color = "#10b981"
            if pct > 80: color = "#f59e0b"
            if pct > 90: color = "#ef4444"
            ui['pb'].setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; border-radius: 4px; }} QProgressBar {{ background-color: #27272a; border-radius: 4px; border: none; }}")

            if pct >= self.disk_thresh_spin.value():
                self.trigger_desktop_alert(f"disk_{mount}", f"Disk Space Critical ({self.session_tab.host})", f"Mount '{mount}' is at {pct}%")

    def update_processes(self, procs):
        new_pids = {str(p.get('pid', '')): p for p in procs if 'pid' in p}
        for row in reversed(range(self.proc_model.rowCount())):
            pid_item = self.proc_model.item(row, 0)
            pid = pid_item.text()
            if pid in new_pids:
                p = new_pids[pid]
                self.proc_model.item(row, 2).setData(float(p.get('cpu', 0)), Qt.ItemDataRole.DisplayRole)
                self.proc_model.item(row, 3).setData(float(p.get('mem', 0)), Qt.ItemDataRole.DisplayRole)
                del new_pids[pid]
            else:
                self.proc_model.removeRow(row)
                
        for pid, p in new_pids.items():
            self.proc_model.appendRow([
                self._num_item(p.get('pid', 0)), QStandardItem(str(p.get('user', ''))),
                self._num_item(p.get('cpu', 0)), self._num_item(p.get('mem', 0)),
                QStandardItem(str(p.get('cmd', ''))), QStandardItem("") 
            ])
            
            row_idx = self.proc_model.rowCount() - 1
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(5, 2, 5, 2)
            
            btn_kill = QPushButton("💀 Kill")
            btn_kill.setStyleSheet("QPushButton { background-color: #7f1d1d; color: white; border-radius: 4px; padding: 4px 10px; font-weight: bold; border: none; } QPushButton:hover { background-color: #991b1b; }")
            
            proc_pid = p.get('pid', 0)
            btn_kill.clicked.connect(lambda checked=False, i=proc_pid: asyncio.create_task(self.kill_process(i, 9)))
            
            btn_layout.addWidget(btn_kill)
            btn_layout.addStretch()
            self.proc_table.setIndexWidget(self.proc_model.index(row_idx, 5), btn_container)

    def update_docker(self, containers):
        for c in containers:
            cname = c.get("name", "")
            cstate = c.get("state", "").lower()
            if cstate == "running": self.known_running_containers.add(cname)
            elif cname in self.known_running_containers and cstate in ["exited", "dead"]:
                self.known_running_containers.discard(cname)
                if self.chk_docker_crash.isChecked():
                    self.trigger_desktop_alert(f"docker_crash_{cname}", f"Docker Crashed ({self.session_tab.host})", f"Container '{cname}' changed to {cstate.upper()}!")

        new_ids = {str(c.get('id', '')): c for c in containers if 'id' in c}
        for row in reversed(range(self.docker_model.rowCount())):
            cid = self.docker_model.item(row, 0).text()
            if cid in new_ids:
                c = new_ids[cid]
                state = c.get('state', '').lower()
                stat_text = c.get('status', '')
                disp = f"{state.upper()} ({stat_text})" if stat_text else state.upper()
                
                item = self.docker_model.item(row, 2)
                item.setText(disp)
                if state == 'running': item.setForeground(QColor("#10b981"))
                elif state in ['exited', 'dead']: item.setForeground(QColor("#ef4444"))
                else: item.setForeground(QColor("#f59e0b"))
                
                del new_ids[cid]
            else:
                self.docker_model.removeRow(row)
                
        for cid, c in new_ids.items():
            state = c.get('state', '').lower()
            stat_text = c.get('status', '')
            disp = f"{state.upper()} ({stat_text})" if stat_text else state.upper()
            
            stat_item = QStandardItem(disp)
            if state == 'running': stat_item.setForeground(QColor("#10b981"))
            elif state in ['exited', 'dead']: stat_item.setForeground(QColor("#ef4444"))
            else: stat_item.setForeground(QColor("#f59e0b"))

            self.docker_model.appendRow([
                QStandardItem(str(c.get('id', ''))), QStandardItem(str(c.get('name', ''))),
                stat_item, QStandardItem("") 
            ])
            
            row_idx = self.docker_model.rowCount() - 1
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(5, 2, 5, 2)
            btn_layout.setSpacing(8)
            
            btn_restart = QPushButton("▶ Restart")
            btn_stop = QPushButton("⏹ Stop")
            btn_kill = QPushButton("💀 Kill")
            btn_logs = QPushButton("📜 Logs")
            
            style_base = "QPushButton { background-color: #27272a; color: white; border-radius: 4px; padding: 4px 10px; font-weight: bold; border: none; } QPushButton:hover { background-color: #3f3f46; }"
            style_danger = "QPushButton { background-color: #7f1d1d; color: white; border-radius: 4px; padding: 4px 10px; font-weight: bold; border: none; } QPushButton:hover { background-color: #991b1b; }"
            
            btn_restart.setStyleSheet(style_base)
            btn_stop.setStyleSheet(style_base)
            btn_logs.setStyleSheet(style_base)
            btn_kill.setStyleSheet(style_danger)
            
            btn_layout.addWidget(btn_restart)
            btn_layout.addWidget(btn_stop)
            btn_layout.addWidget(btn_kill)
            btn_layout.addWidget(btn_logs)
            btn_layout.addStretch()
            
            container_id = c.get('id', '')
            container_name = c.get('name', '')
            
            btn_restart.clicked.connect(lambda checked=False, i=container_id: asyncio.create_task(self.docker_cmd("restart", i)))
            btn_stop.clicked.connect(lambda checked=False, i=container_id: asyncio.create_task(self.docker_cmd("stop", i)))
            btn_kill.clicked.connect(lambda checked=False, i=container_id: asyncio.create_task(self.docker_cmd("kill", i)))
            btn_logs.clicked.connect(lambda checked=False, n=container_name: self.tail_docker_log(n))
            
            self.docker_table.setIndexWidget(self.docker_model.index(row_idx, 3), btn_container)

    def _num_item(self, val):
        item = QStandardItem()
        item.setData(float(val), Qt.ItemDataRole.DisplayRole)
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return item

    def on_proc_context_menu(self, position):
        index = self.proc_table.indexAt(position)
        if not index.isValid(): return
        pid = int(self.proc_model.item(index.row(), 0).data(Qt.ItemDataRole.DisplayRole))
        menu = QMenu()
        term_action = menu.addAction(f"Graceful Terminate (PID: {pid})")
        kill_action = menu.addAction("Force Kill (SIGKILL)")
        action = menu.exec(self.proc_table.viewport().mapToGlobal(position))
        if action == term_action: asyncio.create_task(self.kill_process(pid, 15))
        elif action == kill_action: asyncio.create_task(self.kill_process(pid, 9))

    def on_docker_context_menu(self, position):
        index = self.docker_table.indexAt(position)
        if not index.isValid(): return
        cid = self.docker_model.item(index.row(), 0).text()
        name = self.docker_model.item(index.row(), 1).text()
        menu = QMenu()
        start_action = menu.addAction(f"▶ Start / Restart ({name})")
        stop_action = menu.addAction("⏹ Stop")
        kill_action = menu.addAction("💀 Force Kill")
        menu.addSeparator()
        logs_action = menu.addAction("📜 Tail Live Logs")
        action = menu.exec(self.docker_table.viewport().mapToGlobal(position))
        if action == start_action: asyncio.create_task(self.docker_cmd("restart", cid))
        elif action == stop_action: asyncio.create_task(self.docker_cmd("stop", cid))
        elif action == kill_action: asyncio.create_task(self.docker_cmd("kill", cid))
        elif action == logs_action: self.tail_docker_log(name)

    def tail_docker_log(self, name):
        self.session_tab.log_path_input.setCurrentText(f"docker logs -n 50 -f {name}")
        self.session_tab.start_log_tail()
        self.session_tab.bottom_tabs.setCurrentIndex(3)
        self.session_tab.main_app.activateWindow()

    async def docker_cmd(self, cmd, cid):
        try:
            conn, _ = await self.session_tab.get_connection()
            result = await conn.run(f"docker {cmd} {cid}")
            if result.exit_status != 0: QMessageBox.warning(self, "Docker Error", f"Failed to {cmd}:\n{result.stderr}")
        except Exception as e: QMessageBox.warning(self, "Error", str(e))
            
    async def kill_process(self, pid, sig):
        try:
            conn, _ = await self.session_tab.get_connection()
            result = await conn.run(f"kill -{sig} {pid}")
            if result.exit_status != 0: QMessageBox.warning(self, "Kill Failed", f"Failed:\n{result.stderr}")
        except Exception as e: QMessageBox.warning(self, "Error", str(e))

    def closeEvent(self, event):
        self.is_polling = False
        for listener in self.active_listeners.values(): listener.close()
        if self.backup_process: self.backup_process.terminate()
        super().closeEvent(event)
