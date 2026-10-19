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
