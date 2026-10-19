import asyncio
from PyQt6.QtWidgets import (
    QWidget, QMainWindow, QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QScrollArea, QStackedWidget, QPushButton, QToolButton,
    QMenu, QSizePolicy
)
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QPainterPath, QLinearGradient
)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, pyqtSlot

CURA_MONITOR_BG = "#0f0f13"
CURA_CARD_BG = "#1c1c22"
CURA_ACCENT_BLUE = "#3b82f6"
CURA_ACCENT_PURPLE = "#a855f7"
CURA_ACCENT_RED = "#ef4444"
CURA_ACCENT_GREEN = "#10b981"
CURA_TEXT_MUTED = "#a1a1aa"

class CircularGauge(QWidget):
    def __init__(self, title):
        super().__init__()
        self.title = title
        self.value = 0
        self.sub_text = ""
        self.color = QColor("#10b981") 
        self.setMinimumSize(140, 160)
        
    def update_data(self, val, sub_text=""):
        self.value = val
        self.sub_text = sub_text
        if val >= 85: self.color = QColor("#e11d48")     
        elif val >= 65: self.color = QColor("#f59e0b")   
        else: self.color = QColor("#10b981")             
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        
        size = min(rect.width(), rect.height()) - 50
        x = int((rect.width() - size) / 2)
        y = int((rect.height() - size) / 2) - 15
        draw_rect = QRectF(x, y, size, size)
        
        pen = QPen(QColor("#3f3f46"), 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(draw_rect, 0, 360 * 16)
        
        pen.setColor(self.color)
        painter.setPen(pen)
        span = int(-(self.value / 100.0) * 360 * 16)
        painter.drawArc(draw_rect, 90 * 16, span)
        
        text_color = self.palette().color(self.foregroundRole())
        font = painter.font()
        font.setPointSize(20)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(text_color)
        painter.drawText(QRectF(x, y, size, size), Qt.AlignmentFlag.AlignCenter, f"{self.value}%")
        
        font.setPointSize(11)
        font.setBold(False)
        painter.setFont(font)
        title_rect = QRectF(0, rect.bottom() - 40, rect.width(), 20)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, self.title)
        
        if self.sub_text:
            font.setPointSize(9)
            painter.setFont(font)
            painter.setPen(QColor("#71717a"))
            sub_rect = QRectF(0, rect.bottom() - 20, rect.width(), 15)
            painter.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, self.sub_text)

class LiveLineGraph(QWidget):
    def __init__(self, title, color_hex, max_val=100.0, is_percent=True):
        super().__init__()
        self.title = title
        self.color = QColor(color_hex)
        self.data = [0] * 60
        self.current_val = 0
        self.max_val = max_val
        self.is_percent = is_percent
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def update_data(self, val):
        self.current_val = val
        self.data.append(val)
        if len(self.data) > 60:
            self.data.pop(0)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        bg_rect = QRectF(rect)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(CURA_CARD_BG))
        painter.drawRoundedRect(bg_rect, 8, 8)

        painter.setPen(QColor(CURA_TEXT_MUTED))
        font = painter.font()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(15, 25, self.title)
        
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(self.color)
        val_str = f"{self.current_val}%" if self.is_percent else f"{self.current_val}"
        painter.drawText(rect.adjusted(0, 5, -15, 0), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight, val_str)

        path = QPainterPath()
        h = rect.height() - 40
        w = rect.width()
        dx = w / 59.0

        for i, val in enumerate(self.data):
            x = i * dx
            scaled_val = min(val, self.max_val)
            y = rect.height() - ((scaled_val / self.max_val) * h)
            if i == 0: path.moveTo(x, y)
            else: path.lineTo(x, y)

        fill_path = QPainterPath(path)
        fill_path.lineTo(w, rect.height())
        fill_path.lineTo(0, rect.height())
        fill_path.closeSubpath()

        grad = QLinearGradient(0, 40, 0, rect.height())
        grad.setColorAt(0, QColor(self.color.red(), self.color.green(), self.color.blue(), 100))
        grad.setColorAt(1, QColor(self.color.red(), self.color.green(), self.color.blue(), 0))
        painter.fillPath(fill_path, grad)

        pen = QPen(self.color, 1.5)
        painter.setPen(pen)
        painter.drawPath(path)

class ProcessCard(QFrame):
    manage_requested = pyqtSignal(str, str, str)

    def __init__(self, pid, user, cpu, mem, cmd):
        super().__init__()
        self.pid = pid
        self.cmd = cmd
        self.setStyleSheet(f"""
            QFrame {{ background-color: {CURA_CARD_BG}; border-radius: 10px; border: 1px solid #27272a; }}
            QLabel {{ border: none; background: transparent; }}
        """)
        self.setFixedHeight(75)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        top_row = QHBoxLayout()
        self.lbl_cmd = QLabel(cmd[:60] + "..." if len(cmd) > 60 else cmd)
        self.lbl_cmd.setStyleSheet("color: #f4f4f5; font-size: 13px; font-weight: bold;")
        
        self.btn_manage = QToolButton()
        self.btn_manage.setText("⋮")
        self.btn_manage.setStyleSheet(f"color: {CURA_TEXT_MUTED}; font-weight: bold; background: transparent; border: none; font-size: 20px;")
        self.btn_manage.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_manage.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        menu = QMenu()
        menu.setStyleSheet(f"QMenu {{ background-color: #18181b; border: 1px solid #27272a; border-radius: 6px; }} QMenu::item {{ padding: 6px 24px; color: #f4f4f5; }} QMenu::item:selected {{ background-color: {CURA_ACCENT_BLUE}; }}")
        
        for act_text, act_cmd in [("Kill Process (SIGTERM)", "kill"), ("Force Kill (SIGKILL)", "force_kill")]:
            action = menu.addAction(act_text)
            action.triggered.connect(lambda checked, a=act_cmd, p=self.pid, n=self.cmd: self.manage_requested.emit(a, p, n))
            
        self.btn_manage.setMenu(menu)
        
        top_row.addWidget(self.lbl_cmd)
        top_row.addStretch()
        top_row.addWidget(self.btn_manage)
        
        bot_row = QHBoxLayout()
        lbl_meta = QLabel(f"PID {pid}   {user}")
        lbl_meta.setStyleSheet(f"color: {CURA_TEXT_MUTED}; font-size: 12px;")
        
        self.lbl_cpu = QLabel(f"CPU {cpu}%")
        self.lbl_cpu.setStyleSheet(f"color: {CURA_ACCENT_BLUE}; font-size: 12px; font-weight: bold;")
        
        self.lbl_mem = QLabel(f"MEM {mem}%")
        self.lbl_mem.setStyleSheet(f"color: {CURA_ACCENT_PURPLE}; font-size: 12px; font-weight: bold;")
        
        bot_row.addWidget(lbl_meta)
        bot_row.addSpacing(15)
        bot_row.addWidget(self.lbl_cpu)
        bot_row.addSpacing(10)
        bot_row.addWidget(self.lbl_mem)
        bot_row.addStretch()
        
        layout.addLayout(top_row)
        layout.addLayout(bot_row)

    def update_data(self, cpu, mem):
        self.lbl_cpu.setText(f"CPU {cpu}%")
        self.lbl_mem.setText(f"MEM {mem}%")

class ServiceCard(QFrame):
    manage_requested = pyqtSignal(str, str)

    def __init__(self, name, status, desc):
        super().__init__()
        self.s_name = name
        self.setStyleSheet(f"""
            QFrame {{ background-color: {CURA_CARD_BG}; border-radius: 10px; border: 1px solid #27272a; }}
            QLabel {{ border: none; background: transparent; }}
        """)
        self.setFixedHeight(75)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        is_running = "running" in status.lower()
        is_failed = "failed" in status.lower()
        
        color = CURA_ACCENT_GREEN if is_running else (CURA_ACCENT_RED if is_failed else CURA_TEXT_MUTED)
        badge_text = status.upper()
        
        top_row = QHBoxLayout()
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; font-size: 14px;")
        
        lbl_name = QLabel(name)
        lbl_name.setStyleSheet("color: #f4f4f5; font-size: 13px; font-weight: bold;")
        
        lbl_badge = QLabel(badge_text)
        lbl_badge.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold; border: 1px solid {color}; border-radius: 4px; padding: 2px 6px;")
        
        self.btn_manage = QToolButton()
        self.btn_manage.setText("⋮")
        self.btn_manage.setStyleSheet(f"color: {CURA_TEXT_MUTED}; font-weight: bold; background: transparent; border: none; font-size: 20px;")
        self.btn_manage.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_manage.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        menu = QMenu()
        menu.setStyleSheet(f"QMenu {{ background-color: #18181b; border: 1px solid #27272a; border-radius: 6px; }} QMenu::item {{ padding: 6px 24px; color: #f4f4f5; }} QMenu::item:selected {{ background-color: {CURA_ACCENT_BLUE}; }}")
        
        for act_text, act_cmd in [("Start", "start"), ("Stop", "stop"), ("Restart", "restart"), ("Status Info", "status"), ("View Logs", "logs")]:
            action = menu.addAction(act_text)
            action.triggered.connect(lambda checked, a=act_cmd, n=self.s_name: self.manage_requested.emit(a, n))
            
        self.btn_manage.setMenu(menu)
        
        top_row.addWidget(dot)
        top_row.addWidget(lbl_name)
        top_row.addStretch()
        top_row.addWidget(lbl_badge)
        top_row.addSpacing(10)
        top_row.addWidget(self.btn_manage)
        
        bot_row = QHBoxLayout()
        lbl_desc = QLabel(desc[:70] + "..." if len(desc) > 70 else desc)
        lbl_desc.setStyleSheet(f"color: {CURA_TEXT_MUTED}; font-size: 12px;")
        bot_row.addWidget(lbl_desc)
        bot_row.addStretch()
        
        layout.addLayout(top_row)
        layout.addLayout(bot_row)

class DockerCard(QFrame):
    action_requested = pyqtSignal(str, str)

    def __init__(self, name, status, ports, c_id):
        super().__init__()
        self.c_name = name
        self.setStyleSheet(f"""
            QFrame {{ background-color: {CURA_CARD_BG}; border-radius: 10px; border: 1px solid #27272a; }}
            QLabel {{ border: none; background: transparent; }}
        """)
        self.setFixedHeight(85)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        is_up = "Up" in status
        color = CURA_ACCENT_GREEN if is_up else CURA_ACCENT_RED
        badge_text = "UP" if is_up else "EXITED"
        
        top_row = QHBoxLayout()
        lbl_name = QLabel(name)
        lbl_name.setStyleSheet("color: #f4f4f5; font-size: 14px; font-weight: bold;")
        
        lbl_badge = QLabel(badge_text)
        lbl_badge.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold; background-color: rgba({int(color[1:3],16)}, {int(color[3:5],16)}, {int(color[5:7],16)}, 0.15); border-radius: 4px; padding: 3px 8px;")
        
        self.btn_manage = QToolButton()
        self.btn_manage.setText("⋮")
        self.btn_manage.setStyleSheet(f"color: {CURA_TEXT_MUTED}; font-weight: bold; background: transparent; border: none; font-size: 20px;")
        self.btn_manage.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_manage.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        menu = QMenu()
        menu.setStyleSheet(f"QMenu {{ background-color: #18181b; border: 1px solid #27272a; border-radius: 6px; }} QMenu::item {{ padding: 6px 24px; color: #f4f4f5; }} QMenu::item:selected {{ background-color: {CURA_ACCENT_BLUE}; }}")
        
        for act_text, act_cmd in [("Start", "start"), ("Stop", "stop"), ("Restart", "restart"), ("View Logs", "logs")]:
            action = menu.addAction(act_text)
            action.triggered.connect(lambda checked, a=act_cmd, n=self.c_name: self.action_requested.emit(a, n))
            
        self.btn_manage.setMenu(menu)

        top_row.addWidget(lbl_name)
        top_row.addStretch()
        top_row.addWidget(lbl_badge)
        top_row.addSpacing(10)
        top_row.addWidget(self.btn_manage)
        
        bot_row = QHBoxLayout()
        lbl_desc = QLabel(f"ID: {c_id}  |  {ports}" if ports else f"ID: {c_id}")
        lbl_desc.setStyleSheet(f"color: {CURA_TEXT_MUTED}; font-size: 12px;")
        bot_row.addWidget(lbl_desc)
        bot_row.addStretch()
        
        layout.addLayout(top_row)
        layout.addLayout(bot_row)

class HealthSummaryCard(QFrame):
    def __init__(self, title, val, is_bad=False):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{ background-color: {CURA_CARD_BG}; border-radius: 10px; border: 1px solid #27272a; }}
            QLabel {{ border: none; background: transparent; }}
        """)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_lbl = QLabel("🔴" if is_bad else "✅")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.val_lbl = QLabel(str(val))
        color = CURA_ACCENT_RED if is_bad and int(val) > 0 else CURA_ACCENT_GREEN
        self.val_lbl.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")
        self.val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {CURA_TEXT_MUTED}; font-size: 12px;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(icon_lbl)
        layout.addWidget(self.val_lbl)
        layout.addWidget(title_lbl)

    def update_val(self, val):
        self.val_lbl.setText(str(val))

class ServerMonitorWindow(QMainWindow):
    def __init__(self, session_tab):
        super().__init__(session_tab.main_app)
        self.session_tab = session_tab
        self.setWindowTitle(f"Command Center - {self.session_tab.host}")
        self.resize(500, 800)
        self.setStyleSheet(f"QMainWindow, QWidget {{ background-color: {CURA_MONITOR_BG}; font-family: 'Segoe UI', sans-serif; }}")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout(central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        nav_frame = QFrame()
        nav_frame.setStyleSheet(f"background-color: {CURA_MONITOR_BG}; border-bottom: 1px solid #27272a;")
        nav_layout = QHBoxLayout(nav_frame)
        
        self.tabs = QStackedWidget()
        
        self.btn_live = self.create_nav_btn("Live Monitor", 0, active=True)
        self.btn_proc = self.create_nav_btn("Processes", 1)
        self.btn_health = self.create_nav_btn("Health", 2)
        self.btn_docker = self.create_nav_btn("Docker", 3)
        
        nav_layout.addWidget(self.btn_live)
        nav_layout.addWidget(self.btn_proc)
        nav_layout.addWidget(self.btn_health)
        nav_layout.addWidget(self.btn_docker)
        
        self.layout.addWidget(nav_frame)
        self.layout.addWidget(self.tabs)

        # TAB 0: LIVE
        scroll_live = QScrollArea()
        scroll_live.setWidgetResizable(True)
        scroll_live.setFrameShape(QFrame.Shape.NoFrame)
        w_live = QWidget()
        l_live = QVBoxLayout(w_live)
        l_live.setContentsMargins(15, 15, 15, 15)
        
        self.cpu_graph = LiveLineGraph("CPU", CURA_ACCENT_BLUE)
        self.ram_graph = LiveLineGraph("RAM", CURA_ACCENT_PURPLE)
        self.swap_graph = LiveLineGraph("Swap", CURA_ACCENT_RED)
        self.load_graph = LiveLineGraph("Load Avg", CURA_ACCENT_GREEN, max_val=4.0, is_percent=False)
        
        l_live.addWidget(self.cpu_graph)
        l_live.addWidget(self.ram_graph)
        l_live.addWidget(self.swap_graph)
        l_live.addWidget(self.load_graph)
        l_live.addStretch()
        scroll_live.setWidget(w_live)
        self.tabs.addWidget(scroll_live)

        # TAB 1: PROCESSES
        self.scroll_proc = QScrollArea()
        self.scroll_proc.setWidgetResizable(True)
        self.scroll_proc.setFrameShape(QFrame.Shape.NoFrame)
        self.w_proc = QWidget()
        self.l_proc = QVBoxLayout(self.w_proc)
        self.l_proc.setContentsMargins(15, 15, 15, 15)
        self.l_proc.setSpacing(10)
        self.l_proc.addStretch()
        self.scroll_proc.setWidget(self.w_proc)
        self.tabs.addWidget(self.scroll_proc)
        self.proc_cards = {} 

        # TAB 2: HEALTH
        scroll_health = QScrollArea()
        scroll_health.setWidgetResizable(True)
        scroll_health.setFrameShape(QFrame.Shape.NoFrame)
        self.w_health = QWidget()
        self.l_health = QVBoxLayout(self.w_health)
        self.l_health.setContentsMargins(15, 15, 15, 15)
        self.l_health.setSpacing(15)
        
        sys_health_frame = QFrame()
        sys_health_frame.setStyleSheet(f"background-color: {CURA_CARD_BG}; border-radius: 10px;")
        sys_l = QVBoxLayout(sys_health_frame)
        lbl_sh = QLabel("System Health")
        lbl_sh.setStyleSheet("color: white; font-weight: bold; font-size: 15px;")
        self.lbl_reboot = QLabel("↻ Reboot required: Checking...")
        self.lbl_updates = QLabel("⬇ Pending updates: Checking...")
        sys_l.addWidget(lbl_sh)
        sys_l.addWidget(self.lbl_reboot)
        sys_l.addWidget(self.lbl_updates)
        self.l_health.addWidget(sys_health_frame)
        
        h_cards = QHBoxLayout()
        self.card_run = HealthSummaryCard("Running", 0)
        self.card_fail = HealthSummaryCard("Failed", 0, is_bad=True)
        self.card_stop = HealthSummaryCard("Stopped", 0)
        h_cards.addWidget(self.card_run)
        h_cards.addWidget(self.card_fail)
        h_cards.addWidget(self.card_stop)
        self.l_health.addLayout(h_cards)
        
        lbl_all = QLabel("All services")
        lbl_all.setStyleSheet(f"color: {CURA_TEXT_MUTED}; font-weight: bold; margin-top: 10px;")
        self.l_health.addWidget(lbl_all)
        
        self.l_services = QVBoxLayout()
        self.l_services.setSpacing(10)
        self.l_health.addLayout(self.l_services)
        self.l_health.addStretch()
        scroll_health.setWidget(self.w_health)
        self.tabs.addWidget(scroll_health)

        # TAB 3: DOCKER
        self.scroll_dock = QScrollArea()
        self.scroll_dock.setWidgetResizable(True)
        self.scroll_dock.setFrameShape(QFrame.Shape.NoFrame)
        self.w_dock = QWidget()
        self.l_dock = QVBoxLayout(self.w_dock)
        self.l_dock.setContentsMargins(15, 15, 15, 15)
        self.l_dock.setSpacing(10)
        self.l_dock.addStretch()
        self.scroll_dock.setWidget(self.w_dock)
        self.tabs.addWidget(self.scroll_dock)

        self.is_polling = False
        self.prev_cpu_idle = 0
        self.prev_cpu_total = 0
        asyncio.create_task(self.start_polling())

    def create_nav_btn(self, text, index, active=False):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn_style(btn, active)
        btn.clicked.connect(lambda: self.switch_tab(index))
        return btn

    def update_btn_style(self, btn, active):
        if active:
            btn.setStyleSheet(f"background: transparent; color: {CURA_ACCENT_BLUE}; font-weight: bold; font-size: 14px; border: none; border-bottom: 2px solid {CURA_ACCENT_BLUE}; padding-bottom: 8px;")
        else:
            btn.setStyleSheet(f"background: transparent; color: {CURA_TEXT_MUTED}; font-weight: bold; font-size: 14px; border: none; padding-bottom: 8px;")

    def switch_tab(self, index):
        self.tabs.setCurrentIndex(index)
        for i, btn in enumerate([self.btn_live, self.btn_proc, self.btn_health, self.btn_docker]):
            self.update_btn_style(btn, i == index)

    def closeEvent(self, event):
        self.is_polling = False
        event.accept()

    @pyqtSlot(str, str, str)
    def handle_process_manage(self, action, pid, name):
        if action == "kill":
            asyncio.create_task(self.session_tab.run_remote_command_async('exec', '', f"kill {pid}"))
        elif action == "force_kill":
            asyncio.create_task(self.session_tab.run_remote_command_async('exec', '', f"kill -9 {pid}"))

    @pyqtSlot(str, str)
    def handle_service_manage(self, action, name):
        if action in ['start', 'stop', 'restart']:
            asyncio.create_task(self.session_tab.run_remote_command_async('exec', '', f"sudo systemctl {action} {name}"))
        elif action == 'status':
            self.session_tab.bottom_tabs.setCurrentIndex(1) 
            self.session_tab.term_input.setText(f"systemctl status {name}")
            self.session_tab.send_terminal_cmd()
            self.session_tab.main_app.activateWindow()
            self.close()
        elif action == 'logs':
            self.session_tab.bottom_tabs.setCurrentIndex(3) 
            self.session_tab.log_path_input.setCurrentText(f"journalctl -u {name} -n 50 --no-pager -f")
            self.session_tab.start_log_tail()
            self.session_tab.main_app.activateWindow()
            self.close()

    @pyqtSlot(str, str)
    def handle_docker_manage(self, action, container):
        if action in ['start', 'stop', 'restart']:
            asyncio.create_task(self.session_tab.run_remote_command_async('exec', '', f"docker {action} {container}"))
        elif action == "logs":
            self.session_tab.bottom_tabs.setCurrentIndex(3) 
            self.session_tab.log_path_input.setCurrentText(f"docker logs -n 50 -f {container}")
            self.session_tab.start_log_tail()
            self.session_tab.main_app.activateWindow()
            self.close()

    async def start_polling(self):
        self.is_polling = True
        conn = self.session_tab.ssh_conn
        if not conn: return
            
        cmd = """
        echo "===SYS==="
        cat /proc/stat | grep '^cpu '
        cat /proc/meminfo | grep -E '^MemTotal|^MemAvailable|^SwapTotal|^SwapFree'
        cat /proc/loadavg
        [ -f /var/run/reboot-required ] && echo "Yes" || echo "No"
        apt-get -s upgrade 2>/dev/null | grep -P '^\d+ upgraded' | awk '{print $1}' || echo "0"
        echo "===PROC==="
        ps aux --sort=-%cpu | head -n 30
        echo "===DOCKER==="
        if command -v docker >/dev/null 2>&1; then docker ps -a --format '{{.ID}}|{{.Names}}|{{.Status}}|{{.Ports}}'; else echo "NO_DOCKER"; fi
        echo "===SERVICES==="
        if command -v systemctl >/dev/null 2>&1; then 
            systemctl list-units --type=service --all --plain --no-legend --no-pager | awk '{name=$1; load=$2; active=$3; sub_stat=$4; $1=$2=$3=$4=""; sub(/^[ \t]+/, ""); print name"|"active"|"sub_stat"|"$0}'
        else 
            echo "NO_SYSTEMD"
        fi
        """
        
        while self.is_polling:
            try:
                res = await conn.run(cmd)
                if res.exit_status == 0:
                    self.parse_and_update(res.stdout)
            except Exception as e:
                pass
            await asyncio.sleep(2.5)

    def parse_and_update(self, data):
        try:
            parts = data.split("===PROC===")
            sys_data = parts[0].replace("===SYS===", "").strip()
            parts2 = parts[1].split("===DOCKER===")
            proc_data = parts2[0].strip()
            parts3 = parts2[1].split("===SERVICES===")
            docker_data = parts3[0].strip()
            services_data = parts3[1].strip() if len(parts3) > 1 else ""
            
            # 1. SYS INFO
            lines = sys_data.split('\n')
            cpu_parts = lines[0].split()[1:]
            idle = float(cpu_parts[3]) + float(cpu_parts[4])
            total = sum(float(p) for p in cpu_parts)
            cpu_diff = total - self.prev_cpu_total
            idle_diff = idle - self.prev_cpu_idle
            cpu_pct = int(100.0 * (1.0 - idle_diff / cpu_diff)) if cpu_diff > 0 else 0
            self.prev_cpu_total, self.prev_cpu_idle = total, idle
            
            mem_tot = int(lines[1].split()[1]) if len(lines) > 1 else 0
            mem_avail = int(lines[2].split()[1]) if len(lines) > 2 and "MemAvailable" in lines[2] else mem_tot
            ram_pct = int(((mem_tot - mem_avail) / mem_tot) * 100) if mem_tot > 0 else 0
            
            swap_tot = int(lines[3].split()[1]) if len(lines) > 3 else 0
            swap_free = int(lines[4].split()[1]) if len(lines) > 4 else 0
            swap_pct = int(((swap_tot - swap_free) / swap_tot) * 100) if swap_tot > 0 else 0
            
            load_val = float(lines[5].split()[0]) if len(lines) > 5 else 0.0
            reboot_req = lines[6].strip() if len(lines) > 6 else "No"
            pending_upd = lines[7].strip() if len(lines) > 7 else "0"
            
            self.cpu_graph.update_data(cpu_pct)
            self.ram_graph.update_data(ram_pct)
            self.swap_graph.update_data(swap_pct)
            self.load_graph.update_data(load_val)
            
            c_reb = CURA_ACCENT_RED if reboot_req == "Yes" else CURA_ACCENT_GREEN
            self.lbl_reboot.setStyleSheet(f"color: {c_reb};")
            self.lbl_reboot.setText(f"↻ Reboot required: {reboot_req}")
            
            c_upd = CURA_ACCENT_BLUE if pending_upd != "0" else CURA_ACCENT_GREEN
            self.lbl_updates.setStyleSheet(f"color: {c_upd};")
            self.lbl_updates.setText(f"⬇ Pending updates: {pending_upd}")
            
            # 2. PROCESSES
            proc_lines = proc_data.split('\n')[1:] 
            active_pids = set()
            for line in proc_lines:
                p = line.split(None, 10)
                if len(p) >= 11:
                    user, pid, cpu, mem, cmd = p[0], p[1], p[2], p[3], p[10]
                    active_pids.add(pid)
                    if pid in self.proc_cards:
                        self.proc_cards[pid].update_data(cpu, mem)
                    else:
                        card = ProcessCard(pid, user, cpu, mem, cmd)
                        card.manage_requested.connect(self.handle_process_manage)
                        self.l_proc.insertWidget(self.l_proc.count() - 1, card)
                        self.proc_cards[pid] = card
            
            for pid in list(self.proc_cards.keys()):
                if pid not in active_pids:
                    card = self.proc_cards.pop(pid)
                    self.l_proc.removeWidget(card)
                    card.deleteLater()

            # 3. SERVICES (Health)
            if services_data and "NO_SYSTEMD" not in services_data:
                svc_lines = [l for l in services_data.split('\n') if l.strip()]
                for i in reversed(range(self.l_services.count())): 
                    w = self.l_services.itemAt(i).widget()
                    if w: w.setParent(None)
                
                run_c, fail_c, stop_c = 0, 0, 0
                for line in svc_lines:
                    p = line.split('|', 3)
                    if len(p) >= 4:
                        name, active, sub_stat, desc = p[0], p[1], p[2], p[3]
                        if active == 'active' and sub_stat == 'running': run_c += 1
                        elif active == 'failed': fail_c += 1
                        elif active == 'inactive': stop_c += 1
                        
                        if active == 'failed' or (active == 'active' and sub_stat == 'running' and run_c <= 15):
                            card = ServiceCard(name, sub_stat, desc)
                            card.manage_requested.connect(self.handle_service_manage)
                            self.l_services.addWidget(card)

                self.card_run.update_val(run_c)
                self.card_fail.update_val(fail_c)
                self.card_stop.update_val(stop_c)

            # 4. DOCKER
            if docker_data and "NO_DOCKER" not in docker_data:
                dock_lines = [l for l in docker_data.split('\n') if l.strip()]
                for i in reversed(range(self.l_dock.count() - 1)): 
                    w = self.l_dock.itemAt(i).widget()
                    if w: w.setParent(None)
                    
                for line in dock_lines:
                    p = line.split('|')
                    if len(p) >= 4:
                        c_id, name, status, ports = p[0], p[1], p[2], p[3]
                        card = DockerCard(name, status, ports, c_id)
                        card.action_requested.connect(self.handle_docker_manage)
                        self.l_dock.insertWidget(self.l_dock.count() - 1, card)

        except Exception as e:
            pass
