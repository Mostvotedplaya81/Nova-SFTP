import sys
import os
import re
import stat
import json
import time
import math
from datetime import datetime, timedelta
import subprocess
import importlib.util
import asyncio

def ensure_dependencies():
    if getattr(sys, 'frozen', False):
        return
    dependencies = ['PyQt6', 'asyncssh', 'keyring', 'watchdog', 'qasync']
    missing = [req for req in dependencies if importlib.util.find_spec(req) is None]
    if missing:
        print(f"Installing missing dependencies: {', '.join(missing)}...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except subprocess.CalledProcessError:
            sys.exit(1)

ensure_dependencies()

import keyring
import asyncssh

# FORCE QASYNC TO BIND TO PYQT6
os.environ["QT_API"] = "pyqt6"

import qasync
from qasync import asyncSlot
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeView, QSplitter, QTableView, QLabel, QLineEdit, QPushButton,
    QMessageBox, QMenu, QProgressBar, QHeaderView, QDialog, QListWidget,
    QFormLayout, QInputDialog, QTextEdit, QStyle, QFileDialog, QToolButton,
    QTabWidget, QCheckBox, QPlainTextEdit, QComboBox, QFrame, QSystemTrayIcon,
    QScrollArea, QGridLayout, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QStackedWidget, QSizePolicy
)
from PyQt6.QtGui import (
    QFileSystemModel, QStandardItemModel, QStandardItem, QIntValidator, QIcon,
    QPainter, QColor, QTextFormat, QFont, QTextCursor, QSyntaxHighlighter, 
    QTextCharFormat, QPixmap, QKeySequence, QAction, QPen, QPainterPath, QLinearGradient
)
from PyQt6.QtCore import (
    QDir, Qt, pyqtSignal, QSortFilterProxyModel, QRect, QRectF, QSize, 
    QRegularExpression, QByteArray, pyqtSlot
)

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

# ==========================================
# MODERN UI THEMES
# ==========================================

PREMIUM_DARK_THEME = """
QWidget { background-color: #18181b; color: #e4e4e7; font-family: "Segoe UI", "Ubuntu", sans-serif; font-size: 13px; }
QTreeView, QTableView, QTableWidget, QListWidget, QPlainTextEdit { background-color: #09090b; border: 1px solid #27272a; border-radius: 6px; alternate-background-color: #18181b; }
QHeaderView::section { background-color: #18181b; color: #a1a1aa; padding: 8px; border: none; border-right: 1px solid #27272a; border-bottom: 1px solid #27272a; font-weight: 600; }
QTreeView::item:selected, QTableView::item:selected, QTableWidget::item:selected, QListWidget::item:selected { background-color: #4f46e5; color: white; }
QTreeView::item, QTableWidget::item { padding: 4px; }
QLineEdit, QTextEdit, QComboBox { background-color: #09090b; border: 1px solid #3f3f46; padding: 6px 10px; border-radius: 6px; color: #f4f4f5; }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 1px solid #6366f1; }
QComboBox QAbstractItemView { background-color: #09090b; color: #e4e4e7; selection-background-color: #4f46e5; border: 1px solid #3f3f46; border-radius: 6px; }
QPushButton { background-color: #4f46e5; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; }
QPushButton:hover { background-color: #6366f1; }
QPushButton:disabled { background-color: #27272a; color: #71717a; }
QToolButton { background-color: #27272a; color: #e4e4e7; border: 1px solid #3f3f46; border-radius: 6px; padding: 4px; }
QToolButton:hover { background-color: #3f3f46; color: #ffffff; border-color: #52525b; }
QToolButton.nav-btn { min-width: 32px; max-width: 32px; min-height: 30px; max-height: 30px; }
QToolButton.nav-btn:disabled { background-color: #18181b; border-color: #27272a; }
QMenu { background-color: #18181b; border: 1px solid #27272a; border-radius: 6px; padding: 4px; }
QMenu::item { padding: 6px 24px; border-radius: 4px; }
QMenu::item:selected { background-color: #4f46e5; }
QProgressBar { border: 1px solid #27272a; border-radius: 4px; text-align: center; color: white; background-color: #09090b; }
QProgressBar::chunk { background-color: #10b981; border-radius: 2px;}
QMessageBox, QDialog { background-color: #18181b; }
QMessageBox QLabel { color: #f4f4f5; font-size: 13px; min-width: 260px; min-height: 45px; }
QTabWidget::pane { border: 1px solid #27272a; border-radius: 6px; }
QTabBar::tab { background: #18181b; color: #a1a1aa; padding: 8px 16px; border: 1px solid #27272a; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; }
QTabBar::tab:selected { background: #4f46e5; color: white; border-color: #4f46e5;}
QCheckBox { spacing: 8px; color: #e4e4e7;}
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #3f3f46; border-radius: 4px; background: #09090b; }
QCheckBox::indicator:checked { background: #4f46e5; border-color: #4f46e5; }
QSplitter::handle { background-color: transparent; }
"""

CLEAN_LIGHT_THEME = """
QWidget { background-color: #f8fafc; color: #0f172a; font-family: "Segoe UI", "Ubuntu", sans-serif; font-size: 13px; }
QTreeView, QTableView, QTableWidget, QListWidget, QPlainTextEdit { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; alternate-background-color: #f1f5f9; }
QHeaderView::section { background-color: #f8fafc; color: #475569; padding: 8px; border: none; border-right: 1px solid #cbd5e1; border-bottom: 1px solid #cbd5e1; font-weight: 600; }
QTreeView::item:selected, QTableView::item:selected, QTableWidget::item:selected, QListWidget::item:selected { background-color: #3b82f6; color: white; }
QTreeView::item, QTableWidget::item { padding: 4px; }
QLineEdit, QTextEdit, QComboBox { background-color: #ffffff; border: 1px solid #94a3b8; padding: 6px 10px; border-radius: 6px; color: #0f172a; }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 1px solid #3b82f6; }
QComboBox QAbstractItemView { background-color: #ffffff; color: #0f172a; selection-background-color: #3b82f6; border: 1px solid #cbd5e1; border-radius: 6px; }
QPushButton { background-color: #3b82f6; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; }
QPushButton:hover { background-color: #2563eb; }
QPushButton:disabled { background-color: #e2e8f0; color: #94a3b8; }
QToolButton { background-color: #ffffff; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px; }
QToolButton:hover { background-color: #f1f5f9; color: #0f172a; border-color: #94a3b8; }
QToolButton.nav-btn { min-width: 32px; max-width: 32px; min-height: 30px; max-height: 30px; }
QToolButton.nav-btn:disabled { background-color: #f8fafc; border-color: #e2e8f0; color: #cbd5e1;}
QMenu { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px; }
QMenu::item { padding: 6px 24px; border-radius: 4px; }
QMenu::item:selected { background-color: #3b82f6; color: white;}
QProgressBar { border: 1px solid #cbd5e1; border-radius: 4px; text-align: center; color: #0f172a; background-color: #f1f5f9; }
QProgressBar::chunk { background-color: #10b981; border-radius: 2px;}
QMessageBox, QDialog { background-color: #f8fafc; }
QMessageBox QLabel { color: #0f172a; font-size: 13px; min-width: 260px; min-height: 45px; }
QTabWidget::pane { border: 1px solid #cbd5e1; border-radius: 6px; }
QTabBar::tab { background: #f1f5f9; color: #64748b; padding: 8px 16px; border: 1px solid #cbd5e1; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; }
QTabBar::tab:selected { background: #3b82f6; color: white; border-color: #3b82f6;}
QCheckBox { spacing: 8px; color: #0f172a;}
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #94a3b8; border-radius: 4px; background: #ffffff; }
QCheckBox::indicator:checked { background: #3b82f6; border-color: #3b82f6; }
QSplitter::handle { background-color: transparent; }
"""

DRACULA_THEME = """
QWidget { background-color: #282a36; color: #f8f8f2; font-family: "Segoe UI", "Ubuntu", sans-serif; font-size: 13px; }
QTreeView, QTableView, QTableWidget, QListWidget, QPlainTextEdit { background-color: #1e1f29; border: 1px solid #44475a; border-radius: 6px; alternate-background-color: #282a36; }
QHeaderView::section { background-color: #282a36; color: #6272a4; padding: 8px; border: none; border-right: 1px solid #44475a; border-bottom: 1px solid #44475a; font-weight: 600; }
QTreeView::item:selected, QTableView::item:selected, QTableWidget::item:selected, QListWidget::item:selected { background-color: #bd93f9; color: #282a36; }
QTreeView::item, QTableWidget::item { padding: 4px; }
QLineEdit, QTextEdit, QComboBox { background-color: #1e1f29; border: 1px solid #44475a; padding: 6px 10px; border-radius: 6px; color: #f8f8f2; }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 1px solid #ff79c6; }
QComboBox QAbstractItemView { background-color: #1e1f29; color: #f8f8f2; selection-background-color: #bd93f9; border: 1px solid #44475a; border-radius: 6px; }
QPushButton { background-color: #bd93f9; color: #282a36; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; }
QPushButton:hover { background-color: #ff79c6; color: #282a36; }
QPushButton:disabled { background-color: #44475a; color: #6272a4; }
QToolButton { background-color: #44475a; color: #f8f8f2; border: 1px solid #6272a4; border-radius: 6px; padding: 4px; }
QToolButton:hover { background-color: #6272a4; color: #ffffff; border-color: #bd93f9; }
QToolButton.nav-btn { min-width: 32px; max-width: 32px; min-height: 30px; max-height: 30px; }
QToolButton.nav-btn:disabled { background-color: #282a36; border-color: #44475a; color: #6272a4; }
QMenu { background-color: #282a36; border: 1px solid #44475a; border-radius: 6px; padding: 4px; }
QMenu::item { padding: 6px 24px; border-radius: 4px; }
QMenu::item:selected { background-color: #bd93f9; color: #282a36; }
QProgressBar { border: 1px solid #44475a; border-radius: 4px; text-align: center; color: #f8f8f2; background-color: #1e1f29; }
QProgressBar::chunk { background-color: #50fa7b; border-radius: 2px;}
QMessageBox, QDialog { background-color: #282a36; }
QMessageBox QLabel { color: #f8f8f2; font-size: 13px; min-width: 260px; min-height: 45px; }
QTabWidget::pane { border: 1px solid #44475a; border-radius: 6px; }
QTabBar::tab { background: #1e1f29; color: #6272a4; padding: 8px 16px; border: 1px solid #44475a; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; }
QTabBar::tab:selected { background: #bd93f9; color: #282a36; border-color: #bd93f9;}
QCheckBox { spacing: 8px; color: #f8f8f2;}
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #6272a4; border-radius: 4px; background: #1e1f29; }
QCheckBox::indicator:checked { background: #bd93f9; border-color: #bd93f9; }
QSplitter::handle { background-color: transparent; }
"""

MONOKAI_THEME = """
QWidget { background-color: #272822; color: #f8f8f2; font-family: "Segoe UI", "Ubuntu", sans-serif; font-size: 13px; }
QTreeView, QTableView, QTableWidget, QListWidget, QPlainTextEdit { background-color: #1e1f1c; border: 1px solid #3e3d32; border-radius: 6px; alternate-background-color: #272822; }
QHeaderView::section { background-color: #272822; color: #75715e; padding: 8px; border: none; border-right: 1px solid #3e3d32; border-bottom: 1px solid #3e3d32; font-weight: 600; }
QTreeView::item:selected, QTableView::item:selected, QTableWidget::item:selected, QListWidget::item:selected { background-color: #f92672; color: #f8f8f2; }
QTreeView::item, QTableWidget::item { padding: 4px; }
QLineEdit, QTextEdit, QComboBox { background-color: #1e1f1c; border: 1px solid #3e3d32; padding: 6px 10px; border-radius: 6px; color: #f8f8f2; }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 1px solid #66d9ef; }
QComboBox QAbstractItemView { background-color: #1e1f1c; color: #f8f8f2; selection-background-color: #f92672; border: 1px solid #3e3d32; border-radius: 6px; }
QPushButton { background-color: #f92672; color: #f8f8f2; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; }
QPushButton:hover { background-color: #ff5995; }
QPushButton:disabled { background-color: #3e3d32; color: #75715e; }
QToolButton { background-color: #3e3d32; color: #f8f8f2; border: 1px solid #75715e; border-radius: 6px; padding: 4px; }
QToolButton:hover { background-color: #75715e; color: #ffffff; border-color: #f92672; }
QToolButton.nav-btn { min-width: 32px; max-width: 32px; min-height: 30px; max-height: 30px; }
QToolButton.nav-btn:disabled { background-color: #272822; border-color: #3e3d32; color: #75715e; }
QMenu { background-color: #272822; border: 1px solid #3e3d32; border-radius: 6px; padding: 4px; }
QMenu::item { padding: 6px 24px; border-radius: 4px; }
QMenu::item:selected { background-color: #f92672; color: #f8f8f2; }
QProgressBar { border: 1px solid #3e3d32; border-radius: 4px; text-align: center; color: #f8f8f2; background-color: #1e1f1c; }
QProgressBar::chunk { background-color: #a6e22e; border-radius: 2px;}
QMessageBox, QDialog { background-color: #272822; }
QMessageBox QLabel { color: #f8f8f2; font-size: 13px; min-width: 260px; min-height: 45px; }
QTabWidget::pane { border: 1px solid #3e3d32; border-radius: 6px; }
QTabBar::tab { background: #1e1f1c; color: #75715e; padding: 8px 16px; border: 1px solid #3e3d32; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; }
QTabBar::tab:selected { background: #f92672; color: #f8f8f2; border-color: #f92672;}
QCheckBox { spacing: 8px; color: #f8f8f2;}
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #75715e; border-radius: 4px; background: #1e1f1c; }
QCheckBox::indicator:checked { background: #f92672; border-color: #f92672; }
QSplitter::handle { background-color: transparent; }
"""

CURA_MONITOR_BG = "#0f0f13"
CURA_CARD_BG = "#1c1c22"
CURA_ACCENT_BLUE = "#3b82f6"
CURA_ACCENT_PURPLE = "#a855f7"
CURA_ACCENT_RED = "#ef4444"
CURA_ACCENT_GREEN = "#10b981"
CURA_TEXT_MUTED = "#a1a1aa"

# ==========================================
# FORMATTING & ICON HELPERS
# ==========================================

def format_size(size):
    if size == 0: return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p, 2)
    return f"{s:g} {size_names[i]}"

def format_date(timestamp):
    dt = datetime.fromtimestamp(timestamp)
    now = datetime.now()
    if dt.date() == now.date():
        return f"Today at {dt.strftime('%H:%M')}"
    elif dt.date() == (now - timedelta(days=1)).date():
        return f"Yesterday at {dt.strftime('%H:%M')}"
    else:
        return dt.strftime('%d %b %Y %H:%M')

def get_colored_icon(style, filename, is_dir):
    if is_dir:
        return style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
    
    ext = os.path.splitext(filename)[1].lower()
    base_pixmap = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon).pixmap(16, 16)
    
    color = None
    if ext in ['.py', '.js', '.html', '.css', '.php', '.sh', '.json', '.xml', '.vue']: color = QColor("#0ea5e9") 
    elif ext in ['.zip', '.tar', '.gz', '.rar', '.7z']: color = QColor("#ef4444") 
    elif ext in ['.png', '.jpg', '.jpeg', '.svg', '.gif', '.webp']: color = QColor("#10b981") 
    elif ext in ['.mp3', '.wav', '.flac', '.mp4', '.mkv', '.avi']: color = QColor("#a855f7") 
    elif ext in ['.txt', '.md', '.log', '.csv']: color = QColor("#a1a1aa") 
    
    if color:
        painter = QPainter(base_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(base_pixmap.rect(), color)
        painter.end()
        return QIcon(base_pixmap)
    return QIcon(base_pixmap)

class LocalChangeHandler(FileSystemEventHandler):
    def __init__(self, loop, callback):
        super().__init__()
        self.loop = loop
        self.callback = callback
        self.last_triggered = {}

    def on_modified(self, event):
        if not event.is_directory: self._handle_event(event.src_path)
    def on_created(self, event):
        if not event.is_directory: self._handle_event(event.src_path)
    def _handle_event(self, path):
        current_time = time.time()
        if current_time - self.last_triggered.get(path, 0) > 1.5:
            self.last_triggered[path] = current_time
            self.loop.call_soon_threadsafe(lambda: asyncio.create_task(self.callback(path)))

# ==========================================
# CUSTOM WIDGETS FOR SERVER MONITOR (CURA STYLE)
# ==========================================

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
    manage_requested = pyqtSignal(str, str, str) # action, pid, name

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
    manage_requested = pyqtSignal(str, str) # action, name

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
    action_requested = pyqtSignal(str, str) # action, container_name

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

        # --- TAB 0: LIVE MONITOR ---
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

        # --- TAB 1: PROCESSES ---
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

        # --- TAB 2: HEALTH (SERVICES & SYSTEM) ---
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

        # --- TAB 3: DOCKER ---
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

# ==========================================
# UI COMPONENTS & SYNTAX HIGHLIGHTER
# ==========================================

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
        elif cmd.startswith("> theme: "):
            theme_map = {"dark": 0, "light": 1, "dracula": 2, "monokai": 3}
            theme_choice = cmd.replace("> theme: ", "").strip()
            if theme_choice in theme_map:
                self.main_app.set_theme(theme_map[theme_choice])
        elif cmd == "> ui: close active tab":
            idx = self.main_app.session_tabs.currentIndex()
            if idx != -1: self.main_app.close_tab(idx)

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
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Private Key (Optional)")
        self.key_btn = QToolButton()
        self.key_btn.setText("...")
        self.key_btn.clicked.connect(self.browse_key)
        
        key_layout = QHBoxLayout()
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.addWidget(self.key_input)
        key_layout.addWidget(self.key_btn)
        
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
        form_layout.addRow(key_layout)
        form_layout.addRow(btn_layout)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setWidget(form_widget)
        scroll_area.setMinimumHeight(200)
        
        layout.addWidget(scroll_area)

    def load_data(self):
        if not os.path.exists(self.config_dir): os.makedirs(self.config_dir)
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f: return json.load(f)
        return {}

    def browse_key(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select SSH Private Key", QDir.homePath())
        if file: self.key_input.setText(file)

    def clear_fields(self):
        self.site_list.clearSelection()
        self.name_input.clear()
        self.host_input.clear()
        self.port_input.setText("22")
        self.user_input.clear()
        self.pass_input.clear()
        self.key_input.clear()
        self.main_app.active_key_path = ""
        self.main_app.key_btn.setStyleSheet("")

    def populate_fields(self, site_name):
        if site_name in self.sites:
            data = self.sites[site_name]
            self.name_input.setText(site_name)
            self.host_input.setText(data.get('host', ''))
            self.port_input.setText(str(data.get('port', 22)))
            self.user_input.setText(data.get('user', ''))
            self.key_input.setText(data.get('key_path', ''))
            saved_pass = keyring.get_password("nova_sftp", site_name)
            self.pass_input.setText(saved_pass if saved_pass else "")
            
            self.main_app.host_input.setText(data.get('host', ''))
            self.main_app.port_input.setText(str(data.get('port', 22)))
            self.main_app.user_input.setText(data.get('user', ''))
            self.main_app.pass_input.setText(saved_pass if saved_pass else "")
            self.main_app.active_key_path = data.get('key_path', '')
            self.main_app.key_btn.setStyleSheet("background-color: #10b981;" if self.main_app.active_key_path else "")

    def save_site(self):
        name = self.name_input.text().strip()
        if not name: return
        port_val = self.port_input.text().strip()
        port = int(port_val) if port_val.isdigit() else 22
        
        self.sites[name] = { 
            'host': self.host_input.text(), 
            'port': port, 
            'user': self.user_input.text(), 
            'key_path': self.key_input.text() 
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

class RemoteTreeView(QTreeView):
    files_dropped = pyqtSignal(list)
    quick_look_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths: self.files_dropped.emit(paths)
        event.acceptProposedAction()
        
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Space.value, 32):
            idx = self.currentIndex()
            if idx.isValid():
                item = self.model().sourceModel().item(self.model().mapToSource(idx).row(), 0)
                data = item.data(Qt.ItemDataRole.UserRole)
                if not data['is_dir'] and item.text() != "..":
                    self.quick_look_requested.emit(item.text())
                    return 
        super().keyPressEvent(event)

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

class EditorSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document, filename):
        super().__init__(document)
        self.highlightingRules = []
        ext = os.path.splitext(filename)[1].lower()

        keywordFormat = QTextCharFormat(); keywordFormat.setForeground(QColor("#F92672")); keywordFormat.setFontWeight(QFont.Weight.Bold)
        builtinFormat = QTextCharFormat(); builtinFormat.setForeground(QColor("#66D9EF"))
        stringFormat = QTextCharFormat(); stringFormat.setForeground(QColor("#E6DB74"))
        numberFormat = QTextCharFormat(); numberFormat.setForeground(QColor("#AE81FF"))
        self.commentFormat = QTextCharFormat(); self.commentFormat.setForeground(QColor("#75715E"))
        varFormat = QTextCharFormat(); varFormat.setForeground(QColor("#FD971F"))

        self.highlightingRules.append((QRegularExpression(r"\b[0-9]+(\.[0-9]+)?\b"), numberFormat))
        self.highlightingRules.append((QRegularExpression(r'".*?"'), stringFormat))
        self.highlightingRules.append((QRegularExpression(r"'.*?'"), stringFormat))
        self.commentStartExpression = QRegularExpression()
        self.commentEndExpression = QRegularExpression()

        if ext in ['.py']:
            keywords = ["def", "class", "if", "elif", "else", "while", "for", "in", "return", "yield", "import", "from", "pass", "break", "continue", "and", "or", "not", "is", "lambda", "global", "nonlocal", "assert", "del", "async", "await", "True", "False", "None", "try", "except", "finally", "with", "as"]
            builtins = ["print", "len", "range", "str", "int", "float", "list", "dict", "set", "tuple", "open", "super", "type", "self"]
            self.highlightingRules.append((QRegularExpression(r"\b(" + "|".join(keywords) + r")\b"), keywordFormat))
            self.highlightingRules.append((QRegularExpression(r"\b(" + "|".join(builtins) + r")\b"), builtinFormat))
            self.highlightingRules.append((QRegularExpression(r"#[^\n]*"), self.commentFormat))
            self.commentStartExpression = QRegularExpression(r'"""')
            self.commentEndExpression = QRegularExpression(r'"""')
        elif ext in ['.php']:
            keywords = ["if", "else", "elseif", "while", "do", "for", "foreach", "as", "switch", "case", "break", "continue", "return", "require", "include", "require_once", "include_once", "class", "public", "private", "protected", "static", "function", "echo", "print", "new", "throw", "try", "catch", "namespace", "use", "true", "false", "null"]
            self.highlightingRules.append((QRegularExpression(r"\b(" + "|".join(keywords) + r")\b"), keywordFormat))
            self.highlightingRules.append((QRegularExpression(r"<\?php|\?>"), keywordFormat))
            self.highlightingRules.append((QRegularExpression(r"\$[a-zA-Z_\x7f-\xff][a-zA-Z0-9_\x7f-\xff]*"), varFormat))
            self.highlightingRules.append((QRegularExpression(r"//[^\n]*"), self.commentFormat))
            self.highlightingRules.append((QRegularExpression(r"#[^\n]*"), self.commentFormat))
            self.commentStartExpression = QRegularExpression(r"/\*")
            self.commentEndExpression = QRegularExpression(r"\*/")
        elif ext in ['.sql']:
            keywords = ["select", "from", "where", "insert", "into", "values", "update", "set", "delete", "join", "inner", "left", "right", "outer", "on", "as", "and", "or", "not", "group by", "order by", "having", "limit", "offset", "create", "table", "drop", "alter", "index", "view", "union", "all", "null", "is", "exists", "between", "like", "in"]
            self.highlightingRules.append((QRegularExpression(r"(?i)\b(" + "|".join(keywords).replace(" ", r"\s+") + r")\b"), keywordFormat))
            self.highlightingRules.append((QRegularExpression(r"--[^\n]*"), self.commentFormat))
            self.commentStartExpression = QRegularExpression(r"/\*")
            self.commentEndExpression = QRegularExpression(r"\*/")
        else:
            keywords = ["if", "then", "else", "fi", "elif", "for", "while", "do", "done", "case", "esac", "echo", "export", "return", "function", "true", "false"]
            self.highlightingRules.append((QRegularExpression(r"\b(" + "|".join(keywords) + r")\b"), keywordFormat))
            self.highlightingRules.append((QRegularExpression(r"#[^\n]*"), self.commentFormat))
            self.highlightingRules.append((QRegularExpression(r"//[^\n]*"), self.commentFormat))
            self.commentStartExpression = QRegularExpression(r"/\*")
            self.commentEndExpression = QRegularExpression(r"\*/")

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            matchIterator = pattern.globalMatch(text)
            while matchIterator.hasNext():
                match = matchIterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)
        self.setCurrentBlockState(0)
        startIndex = 0
        if self.previousBlockState() != 1:
            match = self.commentStartExpression.match(text)
            startIndex = match.capturedStart()
        while startIndex >= 0:
            match = self.commentEndExpression.match(text, startIndex)
            endIndex = match.capturedStart()
            if endIndex == -1:
                self.setCurrentBlockState(1)
                commentLength = len(text) - startIndex
            else:
                commentLength = endIndex - startIndex + match.capturedLength()
            self.setFormat(startIndex, commentLength, self.commentFormat)
            nextMatch = self.commentStartExpression.match(text, startIndex + commentLength)
            startIndex = nextMatch.capturedStart()

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor
    def sizeHint(self): return QSize(self.codeEditor.lineNumberAreaWidth(), 0)
    def paintEvent(self, event): self.codeEditor.lineNumberAreaPaintEvent(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()
        
        font = QFont("Fira Code", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(' ') * 4)

    def lineNumberAreaWidth(self):
        digits = 1
        max_value = max(1, self.blockCount())
        while max_value >= 10:
            max_value /= 10
            digits += 1
        return 20 + self.fontMetrics().horizontalAdvance('9') * digits

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy: self.lineNumberArea.scroll(0, dy)
        else: self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()): self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            cursor = self.textCursor()
            if not cursor.hasSelection():
                selection = QTextEdit.ExtraSelection()
                selection.format.setBackground(QColor("#27272a"))
                selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
                selection.cursor = cursor
                extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#18181b"))
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#71717a"))
                painter.drawText(0, top, self.lineNumberArea.width() - 8, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(blockNumber + 1))
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            blockNumber += 1

class AdvancedTextEditor(QWidget):
    def __init__(self, main_app=None, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.toolbar = QFrame()
        self.toolbar.setStyleSheet("""
            QFrame { background-color: transparent; border-bottom: 1px solid #3f3f46; }
            QLineEdit { padding: 4px; }
            QPushButton { padding: 5px 10px; font-weight: bold; }
            QLabel { font-weight: bold; }
        """)
        tb_layout = QHBoxLayout(self.toolbar)
        tb_layout.setContentsMargins(8, 8, 8, 8)
        
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Find...")
        self.find_input.returnPressed.connect(self.find_text)
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace with...")
        
        self.btn_find = QPushButton("Find Next")
        self.btn_replace = QPushButton("Replace")
        self.btn_replace_all = QPushButton("Replace All")
        
        self.btn_zoom_out = QPushButton("A-")
        self.btn_zoom_reset = QPushButton("Reset")
        self.btn_zoom_in = QPushButton("A+")

        tb_layout.addWidget(self.find_input)
        tb_layout.addWidget(self.btn_find)
        tb_layout.addWidget(self.replace_input)
        tb_layout.addWidget(self.btn_replace)
        tb_layout.addWidget(self.btn_replace_all)
        tb_layout.addStretch()
        tb_layout.addWidget(QLabel("Text Size:"))
        tb_layout.addWidget(self.btn_zoom_out)
        tb_layout.addWidget(self.btn_zoom_reset)
        tb_layout.addWidget(self.btn_zoom_in)

        self.editor = CodeEditor()
        
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.editor)

        self.btn_find.clicked.connect(self.find_text)
        self.btn_replace.clicked.connect(self.replace_text)
        self.btn_replace_all.clicked.connect(self.replace_all_text)
        self.btn_zoom_in.clicked.connect(lambda: self.zoom(1))
        self.btn_zoom_out.clicked.connect(lambda: self.zoom(-1))
        self.btn_zoom_reset.clicked.connect(lambda: self.zoom(0))
        
        self.base_font_size = 13
        self.current_font_size = 13
        self.zoom(0) 

    def find_text(self):
        text = self.find_input.text()
        if not text:
            return
            
        found = self.editor.find(text)
        if not found:
            self.editor.moveCursor(QTextCursor.MoveOperation.Start)
            found = self.editor.find(text)
            
        if found:
            self.editor.centerCursor()
            self.editor.setFocus()

    def replace_text(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == self.find_input.text():
            cursor.insertText(self.replace_input.text())
        self.find_text()

    def replace_all_text(self):
        find_str = self.find_input.text()
        replace_str = self.replace_input.text()
        if not find_str: return
        
        self.editor.moveCursor(QTextCursor.MoveOperation.Start)
        self.editor.textCursor().beginEditBlock() 
        while self.editor.find(find_str):
            self.editor.textCursor().insertText(replace_str)
        self.editor.textCursor().endEditBlock()

    def zoom(self, direction):
        if direction == 0:
            self.current_font_size = self.base_font_size
        else:
            new_size = self.current_font_size + (direction * 2) 
            if 8 <= new_size <= 36:
                self.current_font_size = new_size
                
        theme = self.main_app.app_settings.get("theme", "dark") if self.main_app else "dark"
        if theme == "light":
            bg = "#ffffff"; text = "#0f172a"; sel = "#3b82f6"
        elif theme == "dracula":
            bg = "#1e1f29"; text = "#f8f8f2"; sel = "#bd93f9"
        elif theme == "monokai":
            bg = "#1e1f1c"; text = "#f8f8f2"; sel = "#f92672"
        else:
            bg = "#09090b"; text = "#f4f4f5"; sel = "#4f46e5"

        self.editor.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {bg}; 
                color: {text};
                border: none;
                selection-background-color: {sel};
                font-family: "Fira Code", "Cascadia Mono", "Consolas", "Ubuntu Mono", monospace;
                font-size: {self.current_font_size}px;
            }}
        """)
        self.editor.updateLineNumberAreaWidth(0)

class TextEditorDialog(QDialog):
    def __init__(self, filename, content, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Editing: {filename}")
        self.resize(900, 700)
        
        self.main_app = parent.main_app if parent else None
        
        if self.main_app:
            theme = self.main_app.app_settings.get("theme", "dark")
            if theme == "light": self.setStyleSheet(CLEAN_LIGHT_THEME)
            elif theme == "dracula": self.setStyleSheet(DRACULA_THEME)
            elif theme == "monokai": self.setStyleSheet(MONOKAI_THEME)
            else: self.setStyleSheet(PREMIUM_DARK_THEME)
        
        layout = QVBoxLayout(self)
        
        header_layout = QHBoxLayout()
        header_lbl = QLabel(f"File: {filename}")
        header_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(header_lbl)
        header_layout.addStretch()
        
        self.advanced_editor = AdvancedTextEditor(self.main_app)
        self.advanced_editor.editor.setPlainText(content)
        self.highlighter = EditorSyntaxHighlighter(self.advanced_editor.editor.document(), filename)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save & Upload")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("background-color: #ef4444; color: white;")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(header_layout)
        layout.addWidget(self.advanced_editor)
        layout.addLayout(btn_layout)

    def get_content(self):
        return self.advanced_editor.editor.toPlainText()

class SessionTab(QWidget):
    status_changed = pyqtSignal(str)

    def __init__(self, host, port, user, password, key_path, main_app):
        super().__init__()
        self.host, self.port, self.user, self.password, self.key_path = host, port, user, password, key_path
        self.main_app = main_app
        
        self.left_mode = 'local'
        self.left_ssh_conn = None
        self.left_sftp_client = None
        self.current_left_remote_path = "."
        self.left_remote_history = []
        
        self.current_remote_path = "."
        self.local_history, self.remote_history = [], []
        
        self.transfer_tasks = {}
        self.sync_running = False
        self.log_running = False
        self.monitor_window = None
        
        self.ssh_conn = None
        self.sftp_client = None
        self.term_process = None
        self.log_process = None
        self.live_sync_observer = None

        self.dir_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)

        self.init_ui()
        asyncio.create_task(self.connect_and_init())

    async def connect_and_init(self):
        try:
            self.status_changed.emit("Establishing Multiplexed Tunnel...")
            await self.get_connection()
            asyncio.create_task(self.load_remote_directory('.'))
            asyncio.create_task(self.run_terminal())
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            self.status_changed.emit("Connection Failed.")

    async def get_connection(self):
        if self.ssh_conn is None:
            connect_kwargs = {'host': self.host, 'port': self.port, 'username': self.user, 'known_hosts': None}
            if self.key_path and os.path.exists(self.key_path):
                connect_kwargs['client_keys'] = [self.key_path]
                if self.password: connect_kwargs['passphrase'] = self.password
            elif self.password:
                connect_kwargs['password'] = self.password
            
            self.ssh_conn = await asyncssh.connect(**connect_kwargs)
            self.sftp_client = await self.ssh_conn.start_sftp_client()
        return self.ssh_conn, self.sftp_client

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        sync_bar = QHBoxLayout()
        
        self.btn_monitor = QPushButton("📊 Launch Command Center")
        self.btn_monitor.setStyleSheet("background-color: #4f46e5; color: white;")
        self.btn_monitor.clicked.connect(self.launch_monitor)
        
        self.btn_live_sync = QPushButton("Live Sync: OFF")
        self.btn_live_sync.setCheckable(True)
        self.btn_live_sync.setStyleSheet("background-color: #64748b; color: white;")
        self.btn_live_sync.clicked.connect(self.toggle_live_sync)
        
        self.sync_btn = QPushButton("Configure Sync Task...")
        self.sync_btn.setStyleSheet("background-color: #059669; color: white;")
        self.sync_btn.clicked.connect(self.open_sync_dialog)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Midnight Dark", "Clean Light", "Dracula", "Monokai"])
        self.theme_combo.setFixedWidth(140)
        
        theme_map = {"dark": 0, "light": 1, "dracula": 2, "monokai": 3}
        current_theme = self.main_app.app_settings.get("theme", "dark")
        self.theme_combo.setCurrentIndex(theme_map.get(current_theme, 0))
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        
        sync_bar.addWidget(self.btn_monitor)
        sync_bar.addSpacing(15)
        sync_bar.addWidget(QLabel("Directory Sync:", styleSheet="font-weight: bold; color: #10b981;"))
        sync_bar.addWidget(self.btn_live_sync)
        sync_bar.addWidget(self.sync_btn)
        sync_bar.addStretch()
        sync_bar.addWidget(self.theme_combo)
        layout.addLayout(sync_bar)

        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.browser_splitter = QSplitter(Qt.Orientation.Horizontal)

        local_widget = QWidget()
        local_layout = QVBoxLayout(local_widget)
        local_layout.setContentsMargins(0, 0, 0, 0)
        
        local_header_layout = QHBoxLayout()
        self.left_source_combo = QComboBox()
        self.left_source_combo.setStyleSheet("font-weight: bold; font-size: 13px; padding: 5px;")
        self.left_source_combo.addItem("💻 Local System (Default)")
        for site in self.main_app.sidebar.sites.keys():
            self.left_source_combo.addItem(f"🌐 {site}")
        self.left_source_combo.currentIndexChanged.connect(self.on_left_source_changed)
        local_header_layout.addWidget(self.left_source_combo)
        local_layout.addLayout(local_header_layout)

        local_nav = QHBoxLayout()
        self.local_back_btn = QToolButton(); self.local_back_btn.setProperty("class", "nav-btn")
        self.local_back_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        self.local_back_btn.setEnabled(False); self.local_back_btn.clicked.connect(self.go_local_back)
        
        self.local_up_btn = QToolButton(); self.local_up_btn.setProperty("class", "nav-btn")
        self.local_up_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        self.local_up_btn.clicked.connect(self.go_local_up)
        
        self.local_home_btn = QToolButton(); self.local_home_btn.setProperty("class", "nav-btn")
        self.local_home_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon))
        self.local_home_btn.clicked.connect(self.go_local_home)
        
        self.local_path_input = QLineEdit(self.main_app.local_home_path)
        self.local_path_input.returnPressed.connect(self.on_local_path_entered)
        local_nav.addWidget(self.local_back_btn); local_nav.addWidget(self.local_up_btn)
        local_nav.addWidget(self.local_home_btn); local_nav.addWidget(self.local_path_input)
        local_layout.addLayout(local_nav)

        self.left_stack = QStackedWidget()
        
        self.local_view = QTreeView()
        self.local_model = QFileSystemModel()
        self.local_model.setRootPath("")
        self.local_view.setModel(self.local_model)
        self.local_view.setRootIndex(self.local_model.index(self.main_app.local_home_path))
        self.local_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.local_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.local_view.customContextMenuRequested.connect(self.on_local_context_menu)
        self.local_view.doubleClicked.connect(self.on_local_double_click)
        self.left_stack.addWidget(self.local_view)

        self.left_remote_view = RemoteTreeView()
        self.left_remote_model = QStandardItemModel()
        self.left_remote_model.setHorizontalHeaderLabels(["Name", "Size", "Date Modified", "Permissions"])
        self.left_proxy_model = QSortFilterProxyModel()
        self.left_proxy_model.setSourceModel(self.left_remote_model)
        self.left_proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.left_remote_view.setModel(self.left_proxy_model)
        self.left_remote_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.left_remote_view.doubleClicked.connect(self.on_left_remote_double_click)
        self.left_remote_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.left_remote_view.customContextMenuRequested.connect(self.on_left_remote_context_menu)
        self.left_stack.addWidget(self.left_remote_view)

        local_layout.addWidget(self.left_stack)

        remote_widget = QWidget()
        remote_layout = QVBoxLayout(remote_widget)
        remote_layout.setContentsMargins(0, 0, 0, 0)
        remote_nav = QHBoxLayout()
        
        self.remote_back_btn = QToolButton(); self.remote_back_btn.setProperty("class", "nav-btn")
        self.remote_back_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        self.remote_back_btn.setEnabled(False); self.remote_back_btn.clicked.connect(self.go_remote_back)
        
        self.remote_up_btn = QToolButton(); self.remote_up_btn.setProperty("class", "nav-btn")
        self.remote_up_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        self.remote_up_btn.clicked.connect(self.go_remote_up)
        
        self.remote_home_btn = QToolButton(); self.remote_home_btn.setProperty("class", "nav-btn")
        self.remote_home_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon))
        self.remote_home_btn.clicked.connect(self.go_remote_home)
        
        self.remote_path_input = QLineEdit(); self.remote_path_input.setPlaceholderText("Connecting...")
        self.remote_path_input.returnPressed.connect(self.on_remote_path_entered)
        self.remote_search_input = QLineEdit(); self.remote_search_input.setPlaceholderText("Filter..."); self.remote_search_input.setFixedWidth(130)
        self.remote_search_input.textChanged.connect(self.filter_remote_files)
        
        remote_nav.addWidget(self.remote_back_btn); remote_nav.addWidget(self.remote_up_btn)
        remote_nav.addWidget(self.remote_home_btn)
        remote_nav.addWidget(self.remote_path_input); remote_nav.addWidget(self.remote_search_input)

        self.remote_view = RemoteTreeView()
        self.remote_view.files_dropped.connect(self.on_files_dropped)
        self.remote_view.quick_look_requested.connect(self.trigger_quick_look)
        
        self.remote_model = QStandardItemModel()
        self.remote_model.setHorizontalHeaderLabels(["Name", "Size", "Date Modified", "Permissions"])
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.remote_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        self.remote_view.setModel(self.proxy_model)
        self.remote_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        rem_hdr = self.main_app.app_settings.get('remote_header')
        if rem_hdr: self.remote_view.header().restoreState(QByteArray.fromHex(rem_hdr.encode('utf-8')))
        
        self.remote_view.doubleClicked.connect(self.on_remote_double_click)
        self.remote_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.remote_view.customContextMenuRequested.connect(self.on_remote_context_menu)

        remote_layout.addWidget(QLabel(f"Remote: {self.user}@{self.host}", styleSheet="font-weight: bold;"))
        remote_layout.addLayout(remote_nav)
        remote_layout.addWidget(self.remote_view)

        self.browser_splitter.addWidget(local_widget)
        self.browser_splitter.addWidget(remote_widget)
        
        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.setMinimumHeight(200)

        # 0. Transfer Queue
        queue_widget = QWidget()
        queue_layout = QVBoxLayout(queue_widget); queue_layout.setContentsMargins(0, 0, 0, 0)
        self.queue_table = QTableView()
        self.queue_table.setAlternatingRowColors(True)
        self.queue_table.setShowGrid(False)
        self.queue_table.verticalHeader().setVisible(False)
        self.queue_model = QStandardItemModel(0, 4)
        self.queue_model.setHorizontalHeaderLabels(["Dir", "Target", "Status", "Progress"])
        self.queue_table.setModel(self.queue_model)
        self.queue_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.queue_table.setColumnWidth(0, 50); self.queue_table.setColumnWidth(2, 120)
        self.queue_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.queue_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.queue_table.customContextMenuRequested.connect(self.on_queue_context_menu)
        queue_layout.addWidget(self.queue_table)
        
        cancel_all_btn = QPushButton("Cancel All Transfers")
        cancel_all_btn.setStyleSheet("background-color: #ef4444; border-radius: 0px; color: white;")
        cancel_all_btn.clicked.connect(self.cancel_all_transfers)
        queue_layout.addWidget(cancel_all_btn)
        self.bottom_tabs.addTab(queue_widget, "Transfer Queue")

        # 1. Interactive Terminal
        term_widget = QWidget()
        term_layout = QVBoxLayout(term_widget); term_layout.setContentsMargins(5, 5, 5, 5)
        self.term_display = QPlainTextEdit()
        self.term_display.setReadOnly(True)
        self.term_display.setStyleSheet('background-color: #0c0a09; color: #4ade80; font-family: "Cascadia Mono", "Consolas", "Ubuntu Mono", monospace; font-size: 13px; border: 1px solid #27272a; border-radius: 6px;')
        term_input_layout = QHBoxLayout()
        term_prompt = QLabel("$ ")
        term_prompt.setStyleSheet('color: #38bdf8; font-weight: bold; font-family: "Cascadia Mono", "Consolas", "Ubuntu Mono", monospace;')
        self.term_input = QLineEdit()
        self.term_input.setStyleSheet('background-color: #18181b; color: #f4f4f5; font-family: "Cascadia Mono", "Consolas", "Ubuntu Mono", monospace; border-radius: 6px;')
        self.term_input.returnPressed.connect(self.send_terminal_cmd)
        term_send_btn = QPushButton("Send")
        term_send_btn.clicked.connect(self.send_terminal_cmd)
        
        term_ctrl_c = QPushButton("Ctrl+C")
        term_ctrl_c.setStyleSheet("background-color: #ef4444; color: white;")
        term_ctrl_c.clicked.connect(self.send_terminal_ctrl_c)

        term_input_layout.addWidget(term_prompt)
        term_input_layout.addWidget(self.term_input)
        term_input_layout.addWidget(term_send_btn)
        term_input_layout.addWidget(term_ctrl_c)
        term_layout.addWidget(self.term_display)
        term_layout.addLayout(term_input_layout)
        self.bottom_tabs.addTab(term_widget, "Interactive Terminal")

        # 2. Sync Engine Log
        sync_log_widget = QWidget()
        sync_log_layout = QVBoxLayout(sync_log_widget)
        sync_log_layout.setContentsMargins(0, 0, 0, 0)
        self.sync_log_view = QPlainTextEdit()
        self.sync_log_view.setReadOnly(True)
        self.sync_log_view.setStyleSheet('background-color: #0c0a09; color: #e4e4e7; font-family: "Cascadia Mono", "Consolas", "Ubuntu Mono", monospace; font-size: 12px; border-radius: 0px;')
        
        self.cancel_sync_btn = QPushButton("Abort Sync Scan")
        self.cancel_sync_btn.setStyleSheet("background-color: #ef4444; border-radius: 0px; color: white;")
        self.cancel_sync_btn.setEnabled(False)
        self.cancel_sync_btn.clicked.connect(self.abort_sync)
        
        sync_log_layout.addWidget(self.sync_log_view)
        sync_log_layout.addWidget(self.cancel_sync_btn)
        self.bottom_tabs.addTab(sync_log_widget, "Sync Engine Log")

        # 3. Live Logs Tab
        logs_widget = QWidget()
        logs_layout = QVBoxLayout(logs_widget)
        logs_layout.setContentsMargins(5, 5, 5, 5)

        log_ctrl_layout = QHBoxLayout()
        
        self.log_path_input = QComboBox()
        self.log_path_input.setEditable(True)
        self.log_path_input.lineEdit().setPlaceholderText("Enter custom path or select preset...")
        self.log_path_input.addItems([
            "", "/var/log/syslog", "/var/log/auth.log", "/var/log/messages",
            "/var/log/nginx/error.log", "journalctl -f", "docker logs -n 50 -f [container]"
        ])
        self.log_path_input.setCurrentText("")
        self.log_path_input.lineEdit().returnPressed.connect(self.start_log_tail)
        
        self.btn_start_log = QPushButton("Tail Log")
        self.btn_start_log.clicked.connect(self.start_log_tail)
        
        self.btn_stop_log = QPushButton("Stop")
        self.btn_stop_log.setStyleSheet("background-color: #ef4444; color: white;")
        self.btn_stop_log.setEnabled(False)
        self.btn_stop_log.clicked.connect(self.stop_log_tail)

        self.btn_clear_log = QPushButton("Clear")
        self.btn_clear_log.setStyleSheet("background-color: #64748b; color: white;")
        self.btn_clear_log.clicked.connect(lambda: self.log_display.clear())

        log_ctrl_layout.addWidget(QLabel("Command/Path:"))
        log_ctrl_layout.addWidget(self.log_path_input, 1) 
        log_ctrl_layout.addWidget(self.btn_start_log)
        log_ctrl_layout.addWidget(self.btn_stop_log)
        log_ctrl_layout.addWidget(self.btn_clear_log)

        self.log_display = QPlainTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet('background-color: #0c0a09; color: #fbbf24; font-family: "Cascadia Mono", "Consolas", "Ubuntu Mono", monospace; font-size: 12px; border: 1px solid #27272a; border-radius: 6px;')

        logs_layout.addLayout(log_ctrl_layout)
        logs_layout.addWidget(self.log_display)
        self.bottom_tabs.addTab(logs_widget, "Live Logs")

        self.main_splitter.addWidget(self.browser_splitter)
        self.main_splitter.addWidget(self.bottom_tabs)
        
        main_spl_state = self.main_app.app_settings.get('main_splitter')
        if main_spl_state: 
            self.main_splitter.restoreState(QByteArray.fromHex(main_spl_state.encode('utf-8')))
        else:
            self.main_splitter.setSizes([450, 300])

        browser_spl_state = self.main_app.app_settings.get('browser_splitter')
        if browser_spl_state: 
            self.browser_splitter.restoreState(QByteArray.fromHex(browser_spl_state.encode('utf-8')))

        layout.addWidget(self.main_splitter)

    def launch_monitor(self):
        if not self.monitor_window:
            self.monitor_window = ServerMonitorWindow(self)
        self.monitor_window.show()
        self.monitor_window.activateWindow()

    def on_theme_changed(self, index):
        self.main_app.set_theme(index)

    # ----------------------------------------------------
    # SFTP BRIDGE (IN-MEMORY PROXY & RSYNC INJECTION)
    # ----------------------------------------------------
    async def run_bridge_transfer(self, src_path, dst_path, direction, row_index):
        try:
            if direction == 'left_to_right':
                src_sftp = self.left_sftp_client
                dst_sftp = self.sftp_client
            else:
                src_sftp = self.sftp_client
                dst_sftp = self.left_sftp_client
                
            def progress_cb(transferred, total):
                task = self.transfer_tasks.get(row_index)
                if task and task.cancelled(): raise asyncio.CancelledError()
                if total > 0: self.update_progress(row_index, int((transferred / total) * 100))

            async def transfer_item(s_path, d_path):
                st = await src_sftp.stat(s_path)
                if stat.S_ISDIR(st.permissions):
                    try: await dst_sftp.mkdir(d_path)
                    except Exception: pass
                    for entry in await src_sftp.readdir(s_path):
                        if entry.filename in ('.', '..'): continue
                        await transfer_item(f"{s_path.rstrip('/')}/{entry.filename}", f"{d_path.rstrip('/')}/{entry.filename}")
                else:
                    file_size = st.size
                    async with src_sftp.open(s_path, 'rb') as f_in:
                        async with dst_sftp.open(d_path, 'wb') as f_out:
                            transferred = 0
                            while True:
                                task = self.transfer_tasks.get(row_index)
                                if task and task.cancelled(): raise asyncio.CancelledError()
                                chunk = await f_in.read(1024 * 1024)
                                if not chunk: break
                                await f_out.write(chunk)
                                transferred += len(chunk)
                                progress_cb(transferred, file_size)

            self.sync_log_view.appendPlainText(f"[Bridge] Starting Memory Proxy: {src_path} -> {dst_path}")
            await transfer_item(src_path, dst_path)
            self.transfer_complete(row_index, 'bridge')
            
            if direction == 'left_to_right':
                asyncio.create_task(self.load_remote_directory(self.current_remote_path, record_history=False))
            else:
                asyncio.create_task(self.load_left_remote_directory(self.current_left_remote_path, record_history=False))
                
        except asyncio.CancelledError:
            self.transfer_error(row_index, "Cancelled")
        except Exception as e:
            self.transfer_error(row_index, str(e))

    def start_bridge_transfer(self, src_path, dst_path, direction):
        row = self.queue_model.rowCount()
        self.queue_model.insertRow(row)
        dir_icon = "L->R" if direction == "left_to_right" else "R->L"
        self.queue_model.setItem(row, 0, QStandardItem(dir_icon))
        self.queue_model.item(row, 0).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.queue_model.setItem(row, 1, QStandardItem(f"🌉 {os.path.basename(src_path)}"))
        
        status_item = QStandardItem("Bridging...")
        status_item.setForeground(QColor("#a855f7")) 
        self.queue_model.setItem(row, 2, status_item)
        
        pb = QProgressBar(); pb.setValue(0)
        self.queue_table.setIndexWidget(self.queue_model.index(row, 3), pb)

        task = asyncio.create_task(self.run_bridge_transfer(src_path, dst_path, direction, row))
        self.transfer_tasks[row] = task
        
        self.update_queue_badge()
        self.bottom_tabs.setCurrentIndex(0)

    async def run_rsync_transfer(self, src_path, dst_path, direction):
        self.bottom_tabs.setCurrentIndex(2) 
        self.sync_log_view.appendPlainText(f"\n[rsync] Initiating direct transfer: {src_path} -> {dst_path}")
        
        target_host, target_port, target_user, target_pass = "", 22, "", ""
        if direction == 'left_to_right':
            src_conn = self.left_ssh_conn
            target_host, target_port, target_user, target_pass = self.host, self.port, self.user, self.password
        else:
            src_conn = self.ssh_conn
            site_name = self.left_source_combo.currentText().replace("🌐 ", "")
            site_data = self.main_app.sidebar.sites.get(site_name, {})
            target_host = site_data.get('host', '')
            target_port = site_data.get('port', 22)
            target_user = site_data.get('user', '')
            target_pass = keyring.get_password("nova_sftp", site_name) or ""

        if target_pass:
            check_sshpass = await src_conn.run("command -v sshpass")
            if check_sshpass.exit_status != 0:
                self.sync_log_view.appendPlainText("[rsync] Warning: 'sshpass' is not installed on the source server. Transfer may hang if SSH keys are not set up!")
                cmd = f"rsync -avz --progress -e 'ssh -p {target_port} -o StrictHostKeyChecking=no' \"{src_path}\" \"{target_user}@{target_host}:{dst_path}\""
            else:
                safe_pass = target_pass.replace("'", "'\\''")
                cmd = f"sshpass -p '{safe_pass}' rsync -avz --progress -e 'ssh -p {target_port} -o StrictHostKeyChecking=no' \"{src_path}\" \"{target_user}@{target_host}:{dst_path}\""
        else:
            cmd = f"rsync -avz --progress -e 'ssh -p {target_port} -o StrictHostKeyChecking=no' \"{src_path}\" \"{target_user}@{target_host}:{dst_path}\""

        try:
            process = await src_conn.create_process(cmd)
            while True:
                data = await process.stdout.read(1024)
                if not data:
                    break
                self.sync_log_view.insertPlainText(data.replace('\r', ''))
                self.sync_log_view.moveCursor(QTextCursor.MoveOperation.End)
                
            err = await process.stderr.read()
            if err:
                self.sync_log_view.appendPlainText(f"\n[rsync Error] {err}")
                
            self.sync_log_view.appendPlainText(f"\n[rsync] Transfer completed with exit status {process.exit_status}")
            
            asyncio.create_task(self.load_remote_directory(self.current_remote_path, record_history=False))
            if self.left_mode == 'remote':
                asyncio.create_task(self.load_left_remote_directory(self.current_left_remote_path, record_history=False))
                
        except Exception as e:
            self.sync_log_view.appendPlainText(f"\n[rsync Exception] {str(e)}")

    # ----------------------------------------------------
    # LEFT PANE CONNECTION METHODS
    # ----------------------------------------------------
    def on_left_source_changed(self, index):
        if index == 0:
            self.left_mode = 'local'
            self.left_stack.setCurrentIndex(0)
            self.set_local_path(self.main_app.local_home_path)
        else:
            self.left_mode = 'remote'
            self.left_stack.setCurrentIndex(1)
            site_name = self.left_source_combo.currentText().replace("🌐 ", "")
            asyncio.create_task(self.connect_left_remote(site_name))

    async def connect_left_remote(self, site_name):
        self.local_path_input.setText(f"Connecting to {site_name}...")
        site_data = self.main_app.sidebar.sites.get(site_name)
        if not site_data: return
        
        if self.left_sftp_client: self.left_sftp_client.exit()
        if self.left_ssh_conn: self.left_ssh_conn.close()
        
        try:
            host = site_data.get('host')
            port = site_data.get('port', 22)
            user = site_data.get('user')
            key_path = site_data.get('key_path')
            password = keyring.get_password("nova_sftp", site_name)
            
            connect_kwargs = {'host': host, 'port': port, 'username': user, 'known_hosts': None}
            if key_path and os.path.exists(key_path):
                connect_kwargs['client_keys'] = [key_path]
                if password: connect_kwargs['passphrase'] = password
            elif password:
                connect_kwargs['password'] = password
            
            self.left_ssh_conn = await asyncssh.connect(**connect_kwargs)
            self.left_sftp_client = await self.left_ssh_conn.start_sftp_client()
            await self.load_left_remote_directory('.')
        except Exception as e:
            QMessageBox.critical(self, "Left Pane Connection Error", str(e))
            self.local_path_input.setText(f"Failed connecting to {site_name}")

    async def load_left_remote_directory(self, path, record_history=True):
        if not self.left_sftp_client: return
        if path == '.': path = self.main_app.app_settings.get("remote_homes", {}).get(self.left_source_combo.currentText().replace("🌐 ", ""), '.')
        if record_history and self.current_left_remote_path != "." and self.current_left_remote_path != path:
            self.left_remote_history.append(self.current_left_remote_path)
            self.local_back_btn.setEnabled(True)
            
        self.local_path_input.setText(f"Loading {path}...")
        try:
            if path == '.': path = await self.left_sftp_client.realpath('.')
            entries = await self.left_sftp_client.readdir(path)
            file_list = []
            for e in entries:
                if e.filename in ['.', '..']: continue
                is_dir = stat.S_ISDIR(e.attrs.permissions)
                file_list.append({
                    'name': e.filename, 'is_dir': is_dir,
                    'mode': e.attrs.permissions, 'size': getattr(e.attrs, 'size', 0), 
                    'mtime': getattr(e.attrs, 'mtime', 0),
                    'uid': getattr(e.attrs, 'uid', 0), 'gid': getattr(e.attrs, 'gid', 0)
                })
            file_list.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            
            self.current_left_remote_path = path
            self.left_remote_model.removeRows(0, self.left_remote_model.rowCount())
            self.local_path_input.setText(path)

            if path != '/':
                up_item = QStandardItem("..")
                up_item.setIcon(self.dir_icon)
                up_item.setData({'is_dir': True, 'mode': 0, 'uid': 0, 'gid': 0}, Qt.ItemDataRole.UserRole)
                self.left_remote_model.appendRow([up_item, QStandardItem(""), QStandardItem(""), QStandardItem("")])

            for f in file_list:
                name_item = QStandardItem(f['name'])
                name_item.setIcon(get_colored_icon(self.style(), f['name'], f['is_dir']))
                name_item.setData({'is_dir': f['is_dir'], 'mode': f['mode'], 'uid': f['uid'], 'gid': f['gid']}, Qt.ItemDataRole.UserRole)
                
                size_str = "" if f['is_dir'] else format_size(f['size'])
                size_item = QStandardItem(size_str)
                size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                
                date_str = format_date(f['mtime'])
                date_item = QStandardItem(date_str)
                date_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                
                mode_str = stat.filemode(f['mode'])
                mode_item = QStandardItem(mode_str)
                
                self.left_remote_model.appendRow([name_item, size_item, date_item, mode_item])
                
        except Exception as e:
            QMessageBox.critical(self, "Left SFTP Error", str(e))
            self.local_path_input.setText("Error loading directory.")

    def on_left_remote_double_click(self, proxy_index):
        source_index = self.left_proxy_model.mapToSource(proxy_index)
        item = self.left_remote_model.item(source_index.row(), 0)
        data = item.data(Qt.ItemDataRole.UserRole)
        if data['is_dir']:
            folder = item.text()
            new_path = "/".join(self.current_left_remote_path.rstrip('/').split('/')[:-1]) if folder == ".." else f"{self.current_left_remote_path.rstrip('/')}/{folder}"
            asyncio.create_task(self.load_left_remote_directory(new_path or "/"))

    def on_left_remote_context_menu(self, position):
        if self.current_left_remote_path == ".": return
        proxy_index = self.left_remote_view.indexAt(position)
        if not proxy_index.isValid(): return
        
        source_index = self.left_proxy_model.mapToSource(proxy_index)
        item = self.left_remote_model.item(source_index.row(), 0)
        if item.text() == "..": return
        
        menu = QMenu()
        bridge_action = menu.addAction("🌉 Bridge Transfer to Right Pane (Memory Proxy)")
        rsync_action = menu.addAction("🚀 Direct Transfer to Right Pane (rsync)")
        
        action = menu.exec(self.left_remote_view.viewport().mapToGlobal(position))
        if action == bridge_action:
            src = f"{self.current_left_remote_path.rstrip('/')}/{item.text()}"
            dst = f"{self.current_remote_path.rstrip('/')}/{item.text()}"
            self.start_bridge_transfer(src, dst, 'left_to_right')
        elif action == rsync_action:
            src = f"{self.current_left_remote_path.rstrip('/')}/{item.text()}"
            dst = self.current_remote_path.rstrip('/') + '/'
            asyncio.create_task(self.run_rsync_transfer(src, dst, 'left_to_right'))

    # ----------------------------------------------------
    # CORE ASYNC METHODS (Right Pane & Transfers)
    # ----------------------------------------------------

    async def load_remote_directory(self, path, record_history=True):
        self.remote_search_input.clear()
        if path == '.': path = self.main_app.app_settings.get("remote_homes", {}).get(self.host, '.')
        if record_history and self.current_remote_path != "." and self.current_remote_path != path:
            self.remote_history.append(self.current_remote_path)
            self.remote_back_btn.setEnabled(True)
            
        self.status_changed.emit(f"Loading {path}...")
        try:
            conn, sftp = await self.get_connection()
            if path == '.': path = await sftp.realpath('.')
            
            entries = await sftp.readdir(path)
            file_list = []
            for e in entries:
                if e.filename in ['.', '..']: continue
                is_dir = stat.S_ISDIR(e.attrs.permissions)
                file_list.append({
                    'name': e.filename, 'is_dir': is_dir,
                    'mode': e.attrs.permissions, 'size': getattr(e.attrs, 'size', 0), 
                    'mtime': getattr(e.attrs, 'mtime', 0),
                    'uid': getattr(e.attrs, 'uid', 0), 'gid': getattr(e.attrs, 'gid', 0)
                })
            
            file_list.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            self.on_directory_loaded(file_list, path)
        except Exception as e:
            QMessageBox.critical(self, "SFTP Error", str(e))
            self.status_changed.emit("Error loading directory.")

    async def run_terminal(self):
        try:
            conn, _ = await self.get_connection()
            self.term_process = await conn.create_process(term_type='xterm', term_size=(100, 35))
            while True:
                data = await self.term_process.stdout.read(2048)
                if not data: break
                clean_text = re.sub(r'\x1b\[[0-9;?]*[a-zA-Z]|\x1b\].*?(?:\x07|\x1b\\)|\x1b[78=><cEHMNOZ]', '', data)
                self.on_terminal_data(clean_text)
            self.term_display.appendPlainText("\n[Session Closed]\n")
        except Exception as e:
            self.term_display.appendPlainText(f"\n[Terminal Error: {e}]\n")

    async def run_log_tail(self, cmd):
        self.log_running = True
        try:
            conn, _ = await self.get_connection()
            self.log_process = await conn.create_process(cmd, term_type='xterm')
            while self.log_running:
                data = await self.log_process.stdout.read(2048)
                if not data: break
                clean_text = re.sub(r'\x1b\[[0-9;?]*[a-zA-Z]|\x1b\].*?(?:\x07|\x1b\\)|\x1b[78=><cEHMNOZ]', '', data)
                self.on_log_data(clean_text)
        except Exception as e:
            self.log_display.appendPlainText(f"\n[Log Tail Error: {e}]\n")
        finally:
            if hasattr(self, 'log_process') and self.log_process:
                self.log_process.terminate()
            self.on_log_stopped()

    async def run_transfer(self, local_path, remote_path, direction, row_index):
        try:
            conn, sftp = await self.get_connection()
            
            def progress_cb(src, dst, transferred, total):
                task = self.transfer_tasks.get(row_index)
                if task and task.cancelled():
                    raise asyncio.CancelledError()
                if total > 0:
                    self.update_progress(row_index, int((transferred / total) * 100))
            
            if direction == 'upload':
                if os.path.isdir(local_path):
                    await sftp.put(local_path, remote_path, recurse=True, progress_handler=progress_cb)
                else:
                    local_size = os.path.getsize(local_path)
                    remote_size = 0
                    try:
                        st = await sftp.stat(remote_path)
                        remote_size = st.size
                    except: pass
                    
                    if 0 < remote_size < local_size:
                        self.sync_log_view.appendPlainText(f"[Resume] Resuming upload: {os.path.basename(local_path)} (starting at {format_size(remote_size)})")
                        status_item = self.queue_model.item(row_index, 2)
                        status_item.setText("Resuming...")
                        
                        async with sftp.open(remote_path, 'a') as rf:
                            with open(local_path, 'rb') as lf:
                                lf.seek(remote_size)
                                chunk_size = 1024 * 1024
                                transferred = remote_size
                                while True:
                                    task = self.transfer_tasks.get(row_index)
                                    if task and task.cancelled(): raise asyncio.CancelledError()
                                    chunk = lf.read(chunk_size)
                                    if not chunk: break
                                    await rf.write(chunk)
                                    transferred += len(chunk)
                                    progress_cb(local_path, remote_path, transferred, local_size)
                    else:
                        await sftp.put(local_path, remote_path, progress_handler=progress_cb)
            else:
                is_r_dir = False
                remote_size = 0
                try: 
                    st = await sftp.stat(remote_path)
                    is_r_dir = stat.S_ISDIR(st.permissions)
                    remote_size = st.size
                except: pass
                
                if is_r_dir:
                    await sftp.get(remote_path, local_path, recurse=True, progress_handler=progress_cb)
                else:
                    local_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0
                    if 0 < local_size < remote_size:
                        self.sync_log_view.appendPlainText(f"[Resume] Resuming download: {os.path.basename(remote_path)} (starting at {format_size(local_size)})")
                        status_item = self.queue_model.item(row_index, 2)
                        status_item.setText("Resuming...")
                        
                        async with sftp.open(remote_path, 'rb') as rf:
                            await rf.seek(local_size)
                            with open(local_path, 'ab') as lf:
                                chunk_size = 1024 * 1024
                                transferred = local_size
                                while True:
                                    task = self.transfer_tasks.get(row_index)
                                    if task and task.cancelled(): raise asyncio.CancelledError()
                                    chunk = await rf.read(chunk_size)
                                    if not chunk: break
                                    lf.write(chunk)
                                    transferred += len(chunk)
                                    progress_cb(remote_path, local_path, transferred, remote_size)
                    else:
                        await sftp.get(remote_path, local_path, progress_handler=progress_cb)
            
            self.transfer_complete(row_index, direction)
        except asyncio.CancelledError:
            self.transfer_error(row_index, "Cancelled")
        except Exception as e:
            self.transfer_error(row_index, str(e))

    async def run_sync_scan(self, local_dir, remote_dir, direction):
        try:
            conn, sftp = await self.get_connection()
            count = 0
            self.sync_log_view.appendPlainText(f"Starting directory comparison between [{local_dir}] and [{remote_dir}]...")
            
            if direction == 'upload':
                remote_files = {}
                try:
                    entries = await sftp.readdir(remote_dir)
                    for e in entries: remote_files[e.filename] = e
                except asyncssh.sftp.SFTPNoSuchFile:
                    await sftp.mkdir(remote_dir)

                for f in os.listdir(local_dir):
                    if not self.sync_running:
                        self.sync_log_view.appendPlainText("\n--- Sync Scan Aborted by User ---")
                        break
                        
                    l_path = os.path.join(local_dir, f)
                    if os.path.isfile(l_path):
                        l_stat = os.stat(l_path)
                        r_attr = remote_files.get(f)
                        if r_attr:
                            if l_stat.st_mtime <= getattr(r_attr.attrs, 'mtime', 0) and l_stat.st_size == getattr(r_attr.attrs, 'size', 0):
                                continue
                        r_path = f"{remote_dir.rstrip('/')}/{f}"
                        self.sync_log_view.appendPlainText(f"Queued upload: {f}")
                        self.start_transfer(l_path, r_path, 'upload')
                        count += 1
            else:
                entries = await sftp.readdir(remote_dir)
                for attr in entries:
                    if not self.sync_running:
                        self.sync_log_view.appendPlainText("\n--- Sync Scan Aborted by User ---")
                        break
                        
                    if not stat.S_ISDIR(attr.attrs.permissions):
                        l_path = os.path.join(local_dir, attr.filename)
                        r_path = f"{remote_dir.rstrip('/')}/{attr.filename}"
                        if os.path.exists(l_path):
                            l_stat = os.stat(l_path)
                            if getattr(attr.attrs, 'mtime', 0) <= l_stat.st_mtime and getattr(attr.attrs, 'size', 0) == l_stat.st_size:
                                continue
                        self.sync_log_view.appendPlainText(f"Queued download: {attr.filename}")
                        self.start_transfer(l_path, r_path, 'download')
                        count += 1

            self.sync_log_view.appendPlainText(f"Sync inspection complete. {count} files queued.")
            self.cancel_sync_btn.setEnabled(False)
        except Exception as e:
            self.cancel_sync_btn.setEnabled(False)
            QMessageBox.critical(self, "Sync Error", str(e))

    async def fetch_file_content(self, remote_path, size_limit=None):
        conn, sftp = await self.get_connection()
        async with sftp.open(remote_path, 'rb') as f:
            if size_limit:
                chunk = await f.read(size_limit)
                content = chunk.decode('utf-8', errors='ignore')
                if len(chunk) == size_limit: content += "\n\n... [Truncated due to Quick Look size limit] ..."
            else:
                chunk = await f.read()
                content = chunk.decode('utf-8')
        return content

    async def write_file_content(self, remote_path, content):
        conn, sftp = await self.get_connection()
        async with sftp.open(remote_path, 'w') as f:
            await f.write(content)

    async def run_remote_command_async(self, cmd, target_path, arg=None):
        try:
            conn, sftp = await self.get_connection()
            if cmd == 'exec':
                result = await conn.run(arg)
                if result.exit_status != 0 and result.stderr:
                    raise Exception(result.stderr)
            else:
                if cmd == 'mkdir': await sftp.mkdir(target_path)
                elif cmd == 'rm': await sftp.remove(target_path)
                elif cmd == 'rmdir': await sftp.rmdir(target_path)
                elif cmd == 'rename': await sftp.rename(target_path, arg)
                elif cmd == 'properties':
                    mode, uid, gid = arg
                    if mode is not None: await sftp.chmod(target_path, mode)
                    if uid != -1 or gid != -1:
                        if uid == -1 or gid == -1:
                            st = await sftp.stat(target_path)
                            if uid == -1: uid = st.uid
                            if gid == -1: gid = st.gid
                        await sftp.chown(target_path, uid, gid)
            asyncio.create_task(self.load_remote_directory(self.current_remote_path, record_history=False))
        except Exception as e:
            QMessageBox.critical(self, "Command Failed", str(e))

    async def read_and_edit_file(self, filename, remote_path):
        try:
            content = await self.fetch_file_content(remote_path)
            dialog = TextEditorDialog(filename, content, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                await self.write_file_content(remote_path, dialog.get_content())
                QMessageBox.information(self, "Success", "File saved.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load or save file: {str(e)}")

    # ----------------------------------------------------
    # UI CONTROLLERS & EVENT ROUTING
    # ----------------------------------------------------

    def open_sync_dialog(self):
        local = self.local_path_input.text()
        remote = self.current_remote_path
        if remote in ['.', ''] or not os.path.isdir(local):
            QMessageBox.warning(self, "Warning", "Please navigate to valid local and remote directories first.")
            return
            
        dialog = SyncConfigDialog(local, remote, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            local_dir, remote_dir, dir_idx = dialog.get_config()
            direction = 'upload' if dir_idx == 0 else 'download'
            
            self.sync_log_view.clear()
            self.bottom_tabs.setCurrentIndex(2)
            self.cancel_sync_btn.setEnabled(True)
            self.sync_running = True
            
            asyncio.create_task(self.run_sync_scan(local_dir, remote_dir, direction))

    def toggle_live_sync(self):
        if self.btn_live_sync.isChecked():
            local_dir = self.local_path_input.text()
            if not os.path.isdir(local_dir) or self.current_remote_path in ['.', '']:
                QMessageBox.warning(self, "Live Sync", "Navigate to a valid local and remote directory first.")
                self.btn_live_sync.setChecked(False)
                return
            
            self.btn_live_sync.setText("Live Sync: ON")
            self.btn_live_sync.setStyleSheet("background-color: #f59e0b; color: #18181b;") 
            
            self.live_sync_handler = LocalChangeHandler(asyncio.get_running_loop(), self.on_live_file_changed)
            self.live_sync_observer = Observer()
            self.live_sync_observer.schedule(self.live_sync_handler, local_dir, recursive=False)
            self.live_sync_observer.start()
            
            self.sync_log_view.appendPlainText(f"--- Live Sync Started on {local_dir} ---")
            self.bottom_tabs.setCurrentWidget(self.sync_log_view)
        else:
            self.btn_live_sync.setText("Live Sync: OFF")
            self.btn_live_sync.setStyleSheet("background-color: #64748b; color: white;")
            if getattr(self, 'live_sync_observer', None):
                self.live_sync_observer.stop()
                self.live_sync_observer.join()
                self.live_sync_observer = None
            self.sync_log_view.appendPlainText("--- Live Sync Stopped ---")

    async def on_live_file_changed(self, local_filepath):
        filename = os.path.basename(local_filepath)
        remote_filepath = f"{self.current_remote_path.rstrip('/')}/{filename}"
        self.sync_log_view.appendPlainText(f"[Auto-Sync] Pushing changed file: {filename}")
        self.start_transfer(local_filepath, remote_filepath, "upload")

    @asyncSlot(str)
    async def trigger_quick_look(self, filename):
        remote_path = f"{self.current_remote_path.rstrip('/')}/{filename}"
        self.status_changed.emit(f"Fetching preview for {filename}...")
        try:
            content = await self.fetch_file_content(remote_path, size_limit=15360)
            self.show_quick_look(filename, content)
        except Exception as e:
            QMessageBox.warning(self, "Preview Error", str(e))

    def show_quick_look(self, filename, content):
        self.status_changed.emit("Ready")
        preview_dialog = QDialog(self)
        preview_dialog.setWindowTitle(f"Quick Look: {filename}")
        preview_dialog.resize(700, 500)
        
        theme = self.main_app.app_settings.get("theme", "dark")
        if theme == "light": preview_dialog.setStyleSheet(CLEAN_LIGHT_THEME)
        elif theme == "dracula": preview_dialog.setStyleSheet(DRACULA_THEME)
        elif theme == "monokai": preview_dialog.setStyleSheet(MONOKAI_THEME)
        else: preview_dialog.setStyleSheet(PREMIUM_DARK_THEME)
        
        layout = QVBoxLayout(preview_dialog)
        text_edit = QPlainTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(content)
        
        highlighter = EditorSyntaxHighlighter(text_edit.document(), filename)
        text_edit.highlighter = highlighter 
        
        layout.addWidget(text_edit)
        preview_dialog.exec()

    def launch_monitor(self):
        if not self.monitor_window:
            self.monitor_window = ServerMonitorWindow(self)
        self.monitor_window.show()
        self.monitor_window.activateWindow()

    def start_log_tail(self):
        path = self.log_path_input.currentText().strip()
        if not path: return
        
        if not path.startswith("tail") and not path.startswith("docker") and not path.startswith("journalctl"):
            cmd = f"tail -f {path}"
        else:
            cmd = path

        self.btn_start_log.setEnabled(False)
        self.btn_stop_log.setEnabled(True)
        self.log_display.appendPlainText(f"--- Starting: {cmd} ---\n")
        
        asyncio.create_task(self.run_log_tail(cmd))

    def stop_log_tail(self):
        self.log_running = False
        if hasattr(self, 'log_process') and self.log_process:
            self.log_process.terminate()

    def on_log_data(self, text):
        text = text.replace('\r\n', '\n')
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_display.setTextCursor(cursor)
        self.log_display.insertPlainText(text)
        self.log_display.moveCursor(QTextCursor.MoveOperation.End)

    def on_log_stopped(self):
        self.btn_start_log.setEnabled(True)
        self.btn_stop_log.setEnabled(False)
        self.log_display.appendPlainText("\n--- Tail Stopped ---")

    def on_terminal_data(self, text):
        text = text.replace('\r\n', '\n')
        cursor = self.term_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.term_display.setTextCursor(cursor)
        for char in text:
            if char == '\r':
                cursor.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.KeepAnchor)
                cursor.removeSelectedText()
            elif char == '\b' or char == '\x08':
                cursor.deletePreviousChar()
            else:
                cursor.insertText(char)
        self.term_display.setTextCursor(cursor)

    def send_terminal_cmd(self):
        cmd = self.term_input.text()
        if hasattr(self, 'term_process') and self.term_process:
            self.term_process.stdin.write(cmd + '\n')
            self.term_input.clear()

    def send_terminal_ctrl_c(self):
        if hasattr(self, 'term_process') and self.term_process:
            self.term_process.stdin.write('\x03')

    def update_queue_badge(self):
        active = sum(1 for task in self.transfer_tasks.values() if task and not task.done())
        if active > 0:
            self.bottom_tabs.setTabText(0, f"Transfer Queue ({active})")
        else:
            self.bottom_tabs.setTabText(0, "Transfer Queue")

    def abort_sync(self):
        self.sync_running = False
        self.cancel_sync_btn.setEnabled(False)

    def on_queue_context_menu(self, position):
        index = self.queue_table.indexAt(position)
        if not index.isValid(): return
        row = index.row()
        
        status_item = self.queue_model.item(row, 2)
        if status_item and (status_item.text() in ["Done", "Cancelled"] or status_item.text().startswith("Failed")):
            return
            
        menu = QMenu()
        cancel_action = menu.addAction("Cancel Transfer")
        action = menu.exec(self.queue_table.viewport().mapToGlobal(position))
        if not action: return
        
        if action == cancel_action:
            task = self.transfer_tasks.get(row)
            if task and not task.done():
                task.cancel()
            status_item.setText("Cancelling...")
            status_item.setForeground(QColor("#ef4444"))

    def cancel_all_transfers(self):
        for row, task in self.transfer_tasks.items():
            if task and not task.done():
                task.cancel()
                status_item = self.queue_model.item(row, 2)
                if status_item:
                    status_item.setText("Cancelling...")
                    status_item.setForeground(QColor("#ef4444"))

    def start_transfer(self, local_path, remote_path, direction):
        row = self.queue_model.rowCount()
        self.queue_model.insertRow(row)
        dir_icon = "UP" if direction == "upload" else "DOWN"
        self.queue_model.setItem(row, 0, QStandardItem(dir_icon))
        self.queue_model.item(row, 0).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.queue_model.setItem(row, 1, QStandardItem(os.path.basename(local_path)))
        
        status_item = QStandardItem("Transferring...")
        status_item.setForeground(QColor("#0ea5e9")) 
        self.queue_model.setItem(row, 2, status_item)
        
        pb = QProgressBar(); pb.setValue(0)
        self.queue_table.setIndexWidget(self.queue_model.index(row, 3), pb)

        task = asyncio.create_task(self.run_transfer(local_path, remote_path, direction, row))
        self.transfer_tasks[row] = task
        
        self.update_queue_badge()
        self.bottom_tabs.setCurrentIndex(0)

    def update_progress(self, row, pct):
        pb = self.queue_table.indexWidget(self.queue_model.index(row, 3))
        if pb: pb.setValue(pct if pct > 0 else 0)

    def transfer_complete(self, row, direction):
        status_item = self.queue_model.item(row, 2)
        status_item.setText("Done")
        status_item.setForeground(QColor("#10b981")) 
        
        pb = self.queue_table.indexWidget(self.queue_model.index(row, 3))
        if pb: pb.setValue(100)
        if direction == "upload":
            asyncio.create_task(self.load_remote_directory(self.current_remote_path, record_history=False))
        elif direction == 'bridge':
            pass 
            
        self.update_queue_badge()

    def transfer_error(self, row, error_msg):
        status_item = self.queue_model.item(row, 2)
        if status_item.text() != "Cancelling...":
            status_item.setText(f"Failed: {error_msg}")
            status_item.setForeground(QColor("#ef4444")) 
        else:
            status_item.setText("Cancelled")
        self.update_queue_badge()

    def set_local_path(self, target_path, record_history=True):
        if target_path == "":
            curr = self.local_path_input.text()
            if record_history and curr != "":
                self.local_history.append(curr)
                self.local_back_btn.setEnabled(True)
            self.local_view.setRootIndex(self.local_model.index(""))
            self.local_path_input.setText("")
            return

        target_path = os.path.normpath(target_path)
        if not os.path.exists(target_path): return
        curr = self.local_path_input.text()
        if record_history and curr != target_path:
            self.local_history.append(curr)
            self.local_back_btn.setEnabled(True)
        self.local_view.setRootIndex(self.local_model.index(target_path))
        self.local_path_input.setText(target_path)

    # ----------------------------------------------------
    # DUAL-MODE NAVIGATION
    # ----------------------------------------------------

    def go_local_back(self):
        if self.left_mode == 'local':
            if self.local_history:
                prev = self.local_history.pop()
                self.local_back_btn.setEnabled(len(self.local_history) > 0)
                self.set_local_path(prev, record_history=False)
        else:
            if self.left_remote_history:
                prev = self.left_remote_history.pop()
                self.local_back_btn.setEnabled(len(self.left_remote_history) > 0)
                asyncio.create_task(self.load_left_remote_directory(prev, record_history=False))

    def go_local_up(self):
        if self.left_mode == 'local':
            curr = self.local_path_input.text().strip()
            if not curr: return
            qdir = QDir(curr)
            if qdir.cdUp():
                self.set_local_path(os.path.normpath(qdir.absolutePath()))
            elif sys.platform == "win32":
                self.set_local_path("")
        else:
            if self.current_left_remote_path not in [".", "/"]:
                parent = "/".join(self.current_left_remote_path.rstrip('/').split('/')[:-1]) or "/"
                asyncio.create_task(self.load_left_remote_directory(parent))

    def go_local_home(self):
        if self.left_mode == 'local':
            self.set_local_path(self.main_app.local_home_path)
        else:
            asyncio.create_task(self.load_left_remote_directory('.'))

    def on_local_path_entered(self):
        if self.left_mode == 'local':
            self.set_local_path(self.local_path_input.text().strip())
        else:
            asyncio.create_task(self.load_left_remote_directory(self.local_path_input.text().strip()))

    def on_local_double_click(self, index):
        if self.local_model.isDir(index): self.set_local_path(self.local_model.filePath(index))

    def go_remote_back(self):
        if self.remote_history:
            prev = self.remote_history.pop()
            self.remote_back_btn.setEnabled(len(self.remote_history) > 0)
            asyncio.create_task(self.load_remote_directory(prev, record_history=False))

    def go_remote_up(self):
        if self.current_remote_path not in [".", "/"]:
            parent = "/".join(self.current_remote_path.rstrip('/').split('/')[:-1]) or "/"
            asyncio.create_task(self.load_remote_directory(parent))

    def go_remote_home(self):
        target = self.main_app.app_settings.get("remote_homes", {}).get(self.host, '.')
        asyncio.create_task(self.load_remote_directory(target))

    def filter_remote_files(self, text): self.proxy_model.setFilterRegularExpression(text)
    def on_remote_path_entered(self): asyncio.create_task(self.load_remote_directory(self.remote_path_input.text().strip()))

    def on_directory_loaded(self, file_list, current_path):
        self.current_remote_path = current_path
        self.remote_model.removeRows(0, self.remote_model.rowCount())
        self.remote_path_input.setText(current_path)

        if current_path != '/':
            up_item = QStandardItem("..")
            up_item.setIcon(self.dir_icon)
            up_item.setData({'is_dir': True, 'mode': 0, 'uid': 0, 'gid': 0}, Qt.ItemDataRole.UserRole)
            self.remote_model.appendRow([up_item, QStandardItem(""), QStandardItem(""), QStandardItem("")])

        for f in file_list:
            name_item = QStandardItem(f['name'])
            name_item.setIcon(get_colored_icon(self.style(), f['name'], f['is_dir']))
            name_item.setData({'is_dir': f['is_dir'], 'mode': f['mode'], 'uid': f['uid'], 'gid': f['gid']}, Qt.ItemDataRole.UserRole)
            
            size_str = "" if f['is_dir'] else format_size(f['size'])
            size_item = QStandardItem(size_str)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            date_str = format_date(f['mtime'])
            date_item = QStandardItem(date_str)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            mode_str = stat.filemode(f['mode'])
            mode_item = QStandardItem(mode_str)
            
            self.remote_model.appendRow([name_item, size_item, date_item, mode_item])

        self.status_changed.emit(f"Connected: {current_path}")

    def on_remote_double_click(self, proxy_index):
        source_index = self.proxy_model.mapToSource(proxy_index)
        item = self.remote_model.item(source_index.row(), 0)
        data = item.data(Qt.ItemDataRole.UserRole)
        if data['is_dir']:
            folder = item.text()
            new_path = "/".join(self.current_remote_path.rstrip('/').split('/')[:-1]) if folder == ".." else f"{self.current_remote_path.rstrip('/')}/{folder}"
            asyncio.create_task(self.load_remote_directory(new_path or "/"))
        else:
            filename = item.text()
            remote_path = f"{self.current_remote_path.rstrip('/')}/{filename}"
            asyncio.create_task(self.read_and_edit_file(filename, remote_path))

    def on_local_context_menu(self, position):
        index = self.local_view.indexAt(position)
        if not index.isValid(): return
        file_path = self.local_model.filePath(index)
        is_dir = os.path.isdir(file_path)
        
        menu = QMenu()
        upload_action = menu.addAction(f"Upload {'Folder' if is_dir else 'File'}")
        
        set_home_action = None
        if is_dir:
            menu.addSeparator()
            set_home_action = menu.addAction("Set as Default Local Home")
            
        action = menu.exec(self.local_view.viewport().mapToGlobal(position))
        if not action: return
        
        if action == upload_action and self.current_remote_path != ".":
            self.start_transfer(file_path, f"{self.current_remote_path.rstrip('/')}/{os.path.basename(file_path)}", "upload")
        elif action == set_home_action:
            self.main_app.local_home_path = file_path
            self.main_app.app_settings["local_home"] = file_path
            self.main_app.save_settings()
            QMessageBox.information(self, "Home Set", f"Local home directory set to:\n{file_path}")

    def on_files_dropped(self, paths):
        if self.current_remote_path == ".": return
        for p in paths:
            self.start_transfer(p, f"{self.current_remote_path.rstrip('/')}/{os.path.basename(p)}", "upload")

    def on_remote_context_menu(self, position):
        if self.current_remote_path == ".": return
        proxy_index = self.remote_view.indexAt(position)
        menu = QMenu()
        new_folder_action = menu.addAction("New Folder")
        download_action, rename_action, delete_action, prop_action, set_home_action = None, None, None, None, None
        tar_action, untar_action, zip_action, unzip_action = None, None, None, None
        bridge_action, rsync_action = None, None
        item, data = None, None

        if proxy_index.isValid():
            source_index = self.proxy_model.mapToSource(proxy_index)
            item = self.remote_model.item(source_index.row(), 0)
            data = item.data(Qt.ItemDataRole.UserRole)
            if item.text() != "..":
                menu.addSeparator()
                download_action = menu.addAction(f"Download {'Folder' if data['is_dir'] else 'File'}")
                
                if self.left_mode == 'remote':
                    bridge_action = menu.addAction("🌉 Bridge Transfer to Left Pane (Memory Proxy)")
                    rsync_action = menu.addAction("🚀 Direct Transfer to Left Pane (rsync)")
                    
                rename_action = menu.addAction("Rename")
                
                custom_menu = menu.addMenu("Custom Commands")
                if data['is_dir']:
                    tar_action = custom_menu.addAction("Tar (Compress to .tar.gz)")
                    zip_action = custom_menu.addAction("Zip (Compress to .zip)")
                else:
                    ext = item.text().lower()
                    if ext.endswith(('.tar.gz', '.tar', '.tgz')):
                        untar_action = custom_menu.addAction("Untar (Extract .tar.gz)")
                    if ext.endswith('.zip'):
                        unzip_action = custom_menu.addAction("Unzip (Extract .zip)")
                if custom_menu.isEmpty():
                    custom_menu.setEnabled(False)
                
                menu.addSeparator()
                prop_action = menu.addAction("Properties (chmod / chown)")
                delete_action = menu.addAction("Delete")
                if data['is_dir']:
                    menu.addSeparator()
                    set_home_action = menu.addAction("Set as Default Remote Home")

        action = menu.exec(self.remote_view.viewport().mapToGlobal(position))
        if not action: return
        
        if action == new_folder_action:
            name, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
            if ok and name: 
                asyncio.create_task(self.run_remote_command_async('mkdir', f"{self.current_remote_path.rstrip('/')}/{name}"))
        elif action == download_action and item:
            if self.left_mode == 'local':
                local_idx = self.local_view.currentIndex()
                local_dir = self.local_model.filePath(local_idx) if local_idx.isValid() else QDir.homePath()
                if not local_dir or not os.path.isdir(local_dir):
                    local_dir = os.path.dirname(local_dir) if local_dir else QDir.homePath()
                self.start_transfer(os.path.join(local_dir, item.text()), f"{self.current_remote_path.rstrip('/')}/{item.text()}", "download")
        elif action == bridge_action and item:
            src = f"{self.current_remote_path.rstrip('/')}/{item.text()}"
            dst = f"{self.current_left_remote_path.rstrip('/')}/{item.text()}"
            self.start_bridge_transfer(src, dst, 'right_to_left')
        elif action == rsync_action and item:
            src = f"{self.current_remote_path.rstrip('/')}/{item.text()}"
            dst = self.current_left_remote_path.rstrip('/') + '/'
            asyncio.create_task(self.run_rsync_transfer(src, dst, 'right_to_left'))
        elif action == rename_action and item:
            new_name, ok = QInputDialog.getText(self, "Rename", "Enter new name:", text=item.text())
            if ok and new_name and new_name != item.text():
                asyncio.create_task(self.run_remote_command_async('rename', f"{self.current_remote_path.rstrip('/')}/{item.text()}", f"{self.current_remote_path.rstrip('/')}/{new_name}"))
        elif action == delete_action and item:
            if QMessageBox.question(self, "Delete", f"Delete {item.text()}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                cmd = 'rmdir' if data['is_dir'] else 'rm'
                asyncio.create_task(self.run_remote_command_async(cmd, f"{self.current_remote_path.rstrip('/')}/{item.text()}"))
        elif action == prop_action and item:
            dialog = PropertiesDialog(item.text(), data['mode'], data['uid'], data['gid'], data['is_dir'], self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_mode, new_uid, new_gid, is_recursive = dialog.get_properties()
                target_path = f"{self.current_remote_path.rstrip('/')}/{item.text()}"
                
                if is_recursive:
                    cmds = []
                    if new_mode is not None:
                        octal_mode = oct(new_mode)[-3:].zfill(3)
                        cmds.append(f"chmod -R {octal_mode} \"{target_path}\"")
                    if new_uid != -1 or new_gid != -1:
                        u = str(new_uid) if new_uid != -1 else ""
                        g = str(new_gid) if new_gid != -1 else ""
                        chown_str = f"{u}:{g}" if g else f"{u}"
                        if not u and g: chown_str = f":{g}"
                        cmds.append(f"chown -R {chown_str} \"{target_path}\"")
                    
                    if cmds:
                        asyncio.create_task(self.run_remote_command_async('exec', '', " && ".join(cmds)))
                else:
                    asyncio.create_task(self.run_remote_command_async('properties', target_path, (new_mode, new_uid, new_gid)))
        elif action == set_home_action and item:
            target_path = f"{self.current_remote_path.rstrip('/')}/{item.text()}"
            if "remote_homes" not in self.main_app.app_settings:
                self.main_app.app_settings["remote_homes"] = {}
            self.main_app.app_settings["remote_homes"][self.host] = target_path
            self.main_app.save_settings()
            QMessageBox.information(self, "Home Set", f"Remote home directory for '{self.host}' set to:\n{target_path}")
            
        elif action == tar_action and item:
            cmd = f"cd \"{self.current_remote_path}\" && tar -czvf \"{item.text()}.tar.gz\" \"{item.text()}\""
            asyncio.create_task(self.run_remote_command_async('exec', '', cmd))
        elif action == zip_action and item:
            cmd = f"cd \"{self.current_remote_path}\" && zip -r \"{item.text()}.zip\" \"{item.text()}\""
            asyncio.create_task(self.run_remote_command_async('exec', '', cmd))
        elif action == untar_action and item:
            cmd = f"cd \"{self.current_remote_path}\" && tar -xzvf \"{item.text()}\""
            asyncio.create_task(self.run_remote_command_async('exec', '', cmd))
        elif action == unzip_action and item:
            cmd = f"cd \"{self.current_remote_path}\" && unzip -o \"{item.text()}\""
            asyncio.create_task(self.run_remote_command_async('exec', '', cmd))

    def close_tab_resources(self):
        if getattr(self, 'monitor_window', None):
            self.monitor_window.is_polling = False
            self.monitor_window.close()
        if getattr(self, 'live_sync_observer', None):
            self.live_sync_observer.stop()
            self.live_sync_observer.join()
        self.log_running = False
        if getattr(self, 'log_process', None): self.log_process.terminate()
        if getattr(self, 'term_process', None): self.term_process.terminate()
        
        self.cancel_all_transfers()
        self.abort_sync()
        
        if getattr(self, 'sftp_client', None): self.sftp_client.exit()
        if getattr(self, 'ssh_conn', None): self.ssh_conn.close()
        
        if getattr(self, 'left_sftp_client', None): self.left_sftp_client.exit()
        if getattr(self, 'left_ssh_conn', None): self.left_ssh_conn.close()

# ==========================================
# MAIN WINDOW & TABBED SESSION CONTROLLER
# ==========================================

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
        top_bar.setStyleSheet("background-color: transparent; border: none;")
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
        self.key_btn.setIcon(QIcon.fromTheme("dialog-password", self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)))
        self.key_btn.setText(" Key")
        self.key_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.key_btn.clicked.connect(self.browse_key)
        self.active_key_path = ""

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.open_session_tab)

        for w in (self.sidebar_toggle_btn, self.host_input, self.port_input, self.user_input, self.key_btn, self.pass_input, self.pass_toggle_btn, self.connect_btn):
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

    def browse_key(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select SSH Key", QDir.homePath())
        if file:
            self.active_key_path = file
            self.key_btn.setStyleSheet("background-color: #10b981; color: white;")

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
        self.close()

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

if __name__ == "__main__":
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("litenova.novasftp.client.1.5")

    app = QApplication(sys.argv)
    app.setApplicationName("Nova SFTP")
    app.setDesktopFileName("nova-sftp")
    app.setQuitOnLastWindowClosed(False)
    
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    window = NovaSFTP()
    window.show()
    
    with loop:
        loop.run_forever()
