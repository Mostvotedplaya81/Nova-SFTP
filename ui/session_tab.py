import os
import re
import stat
import time
import asyncio
import asyncssh
import keyring
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from qasync import asyncSlot

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QLabel, QSplitter, QToolButton, QLineEdit, QStackedWidget,
    QTreeView, QTableView, QHeaderView, QMenu, QProgressBar,
    QMessageBox, QDialog, QPlainTextEdit, QTabWidget, QAbstractItemView,
    QInputDialog, QStyle
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor, QFileSystemModel, QTextCursor
from PyQt6.QtCore import Qt, QDir, pyqtSignal, QSortFilterProxyModel, QByteArray

from utils.formatting import format_size, format_date
from utils.icons import get_colored_icon
from ui.themes import CLEAN_LIGHT_THEME, DRACULA_THEME, MONOKAI_THEME, PREMIUM_DARK_THEME
from features.dialogs import SyncConfigDialog, PropertiesDialog
from features.text_editor import TextEditorDialog, EditorSyntaxHighlighter
from features.command_center import ServerMonitorWindow
from features.deep_search import DeepSearchWidget
from features.macros import MacroManagerWidget

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

        # 4. Deep Remote Search Tab
        self.deep_search_tab = DeepSearchWidget(self)
        self.bottom_tabs.addTab(self.deep_search_tab, "Deep Search")

        # 5. Macros & Snippets Tab
        self.macros_tab = MacroManagerWidget(self)
        self.bottom_tabs.addTab(self.macros_tab, "Macros & Snippets")

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

    # --- Macro Execution Injection ---
    def execute_macro(self, script):
        if hasattr(self, 'term_process') and self.term_process:
            self.bottom_tabs.setCurrentIndex(1)
            self.term_display.appendPlainText(f"\n\n--- Running Macro ---\n")
            
            cmd = script
            if not cmd.endswith('\n'):
                cmd += '\n'
            
            self.term_process.stdin.write(cmd)
        else:
            QMessageBox.warning(self, "Terminal Offline", "Interactive terminal is not connected.")

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
        if getattr(self, 'deep_search_tab', None):
            self.deep_search_tab.stop_search()
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
