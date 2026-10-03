import sys
import os
import subprocess
import importlib.util

def ensure_dependencies():
    """Installs required packages on first run if missing."""
    dependencies = ['PyQt6', 'paramiko', 'keyring']
    missing = [req for req in dependencies if importlib.util.find_spec(req) is None]
    if missing:
        print(f"Installing missing dependencies: {', '.join(missing)}...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except subprocess.CalledProcessError:
            print(f"Error. Manually run: pip install {' '.join(missing)}")
            sys.exit(1)

ensure_dependencies()

import json
import stat
import keyring
import paramiko
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeView, QSplitter, QTableView, QLabel, QLineEdit, QPushButton, 
    QMessageBox, QMenu, QProgressBar, QHeaderView, QDialog, QListWidget, 
    QFormLayout, QInputDialog, QTextEdit, QStyle, QFileDialog, QToolButton, 
    QTabWidget, QCheckBox, QPlainTextEdit
)
from PyQt6.QtGui import (
    QFileSystemModel, QStandardItemModel, QStandardItem, QIntValidator, QIcon,
    QPainter, QColor, QTextFormat, QFont, QTextCursor, QSyntaxHighlighter, QTextCharFormat
)
from PyQt6.QtCore import QDir, Qt, QThread, pyqtSignal, QSortFilterProxyModel, QRect, QSize, QRegularExpression

PREMIUM_THEME = """
QWidget { background-color: #18181b; color: #e4e4e7; font-family: "Segoe UI", "Ubuntu", sans-serif; font-size: 13px; }
QTreeView, QTableView, QListWidget { background-color: #09090b; border: 1px solid #27272a; border-radius: 4px; alternate-background-color: #18181b; }
QHeaderView::section { background-color: #18181b; color: #a1a1aa; padding: 8px; border: none; border-right: 1px solid #27272a; border-bottom: 1px solid #27272a; font-weight: 600; }
QTreeView::item:selected, QTableView::item:selected, QListWidget::item:selected { background-color: #2563eb; color: white; }
QTreeView::item { padding: 4px; }
QLineEdit, QTextEdit { background-color: #09090b; border: 1px solid #3f3f46; padding: 6px 10px; border-radius: 4px; }
QLineEdit:focus, QTextEdit:focus { border: 1px solid #3b82f6; }
QPushButton { background-color: #2563eb; color: white; border: none; padding: 8px 16px; border-radius: 4px; font-weight: 600; }
QPushButton:hover { background-color: #3b82f6; }
QPushButton:disabled { background-color: #27272a; color: #71717a; }

/* Navigation buttons (Back, Up, Home) */
QToolButton.nav-btn {
    background-color: #27272a;
    color: #e4e4e7;
    border: 1px solid #3f3f46;
    border-radius: 4px;
    padding: 3px;
    min-width: 28px;
    max-width: 28px;
    min-height: 26px;
    max-height: 26px;
    font-size: 12px;
    font-weight: bold;
}
QToolButton.nav-btn:hover { background-color: #3f3f46; color: #ffffff; }
QToolButton.nav-btn:disabled { background-color: #18181b; color: #52525b; border-color: #27272a; }

QMenu { background-color: #18181b; border: 1px solid #27272a; border-radius: 4px; padding: 4px; }
QMenu::item { padding: 6px 24px; border-radius: 2px; }
QMenu::item:selected { background-color: #2563eb; }
QProgressBar { border: 1px solid #27272a; border-radius: 2px; text-align: center; color: white; background-color: #09090b; }
QProgressBar::chunk { background-color: #10b981; }
QMessageBox, QDialog { background-color: #18181b; }
QTabWidget::pane { border: 1px solid #27272a; border-radius: 4px; }
QTabBar::tab { background: #18181b; color: #a1a1aa; padding: 8px 16px; border: 1px solid #27272a; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }
QTabBar::tab:selected { background: #2563eb; color: white; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #3f3f46; border-radius: 3px; background: #09090b; }
QCheckBox::indicator:checked { background: #2563eb; border-color: #2563eb; }
"""

def create_ssh_client(host, port, username, password, key_path):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if key_path and os.path.exists(key_path):
        ssh.connect(host, port=port, username=username, key_filename=key_path, password=password, timeout=10)
    else:
        ssh.connect(host, port=port, username=username, password=password, timeout=10)
    return ssh

# --- Background Workers ---
class SFTPWorker(QThread):
    directory_loaded = pyqtSignal(list, str)
    error_occurred = pyqtSignal(str)
    def __init__(self, host, port, username, password, key_path, path='.'):
        super().__init__()
        self.host, self.port, self.username, self.password, self.key_path, self.path = host, port, username, password, key_path, path
    def run(self):
        try:
            ssh = create_ssh_client(self.host, self.port, self.username, self.password, self.key_path)
            sftp = ssh.open_sftp()
            if self.path == '.': self.path = sftp.normalize('.')
            file_list = [{'name': e.filename, 'is_dir': stat.S_ISDIR(e.st_mode), 'mode': e.st_mode} for e in sftp.listdir_attr(self.path)]
            file_list.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            sftp.close(); ssh.close()
            self.directory_loaded.emit(file_list, self.path)
        except Exception as e:
            self.error_occurred.emit(str(e))

class TransferWorker(QThread):
    progress_updated = pyqtSignal(int, int)
    transfer_finished = pyqtSignal(int)
    error_occurred = pyqtSignal(int, str)
    def __init__(self, host, port, username, password, key_path, local_path, remote_path, direction, row_index):
        super().__init__()
        self.host, self.port, self.username, self.password, self.key_path = host, port, username, password, key_path
        self.local_path, self.remote_path, self.direction, self.row_index = local_path, remote_path, direction, row_index
    def _upload_dir(self, sftp, local_dir, remote_dir):
        try: sftp.stat(remote_dir)
        except IOError: sftp.mkdir(remote_dir)
        for item in os.listdir(local_dir):
            l_path, r_path = os.path.join(local_dir, item), f"{remote_dir}/{item}"
            if os.path.isdir(l_path): self._upload_dir(sftp, l_path, r_path)
            else: sftp.put(l_path, r_path)
    def _download_dir(self, sftp, remote_dir, local_dir):
        os.makedirs(local_dir, exist_ok=True)
        for item in sftp.listdir_attr(remote_dir):
            r_path, l_path = f"{remote_dir}/{item.filename}", os.path.join(local_dir, item.filename)
            if stat.S_ISDIR(item.st_mode): self._download_dir(sftp, r_path, l_path)
            else: sftp.get(r_path, l_path)
    def run(self):
        try:
            ssh = create_ssh_client(self.host, self.port, self.username, self.password, self.key_path)
            sftp = ssh.open_sftp()
            def cb(transferred, total):
                if total > 0: self.progress_updated.emit(self.row_index, int((transferred / total) * 100))
            if self.direction == 'upload':
                if os.path.isdir(self.local_path):
                    self.progress_updated.emit(self.row_index, 0)
                    self._upload_dir(sftp, self.local_path, self.remote_path)
                else: sftp.put(self.local_path, self.remote_path, callback=cb)
            else:
                is_r_dir = False
                try: is_r_dir = stat.S_ISDIR(sftp.stat(self.remote_path).st_mode)
                except: pass
                if is_r_dir:
                    self.progress_updated.emit(self.row_index, 0)
                    self._download_dir(sftp, self.remote_path, self.local_path)
                else: sftp.get(self.remote_path, self.local_path, callback=cb)
            sftp.close(); ssh.close()
            self.transfer_finished.emit(self.row_index)
        except Exception as e:
            self.error_occurred.emit(self.row_index, str(e))

class RemoteCommandWorker(QThread):
    command_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    def __init__(self, host, port, username, password, key_path, command, path, arg=None):
        super().__init__()
        self.host, self.port, self.username, self.password, self.key_path = host, port, username, password, key_path
        self.command, self.path, self.arg = command, path, arg
    def run(self):
        try:
            ssh = create_ssh_client(self.host, self.port, self.username, self.password, self.key_path)
            sftp = ssh.open_sftp()
            if self.command == 'mkdir': sftp.mkdir(self.path)
            elif self.command == 'rm': sftp.remove(self.path)
            elif self.command == 'rmdir': sftp.rmdir(self.path)
            elif self.command == 'chmod': sftp.chmod(self.path, self.arg)
            elif self.command == 'rename': sftp.rename(self.path, self.arg)
            sftp.close(); ssh.close()
            self.command_finished.emit()
        except Exception as e:
            self.error_occurred.emit(str(e))

class RemoteReadWorker(QThread):
    content_loaded = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    def __init__(self, host, port, username, password, key_path, remote_path):
        super().__init__()
        self.host, self.port, self.username, self.password, self.key_path, self.remote_path = host, port, username, password, key_path, remote_path
    def run(self):
        try:
            ssh = create_ssh_client(self.host, self.port, self.username, self.password, self.key_path)
            sftp = ssh.open_sftp()
            with sftp.open(self.remote_path, 'r') as f: content = f.read().decode('utf-8')
            sftp.close(); ssh.close()
            self.content_loaded.emit(content)
        except: self.error_occurred.emit("File appears to be binary.")

class RemoteWriteWorker(QThread):
    write_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    def __init__(self, host, port, username, password, key_path, remote_path, content):
        super().__init__()
        self.host, self.port, self.username, self.password, self.key_path, self.remote_path, self.content = host, port, username, password, key_path, remote_path, content
    def run(self):
        try:
            ssh = create_ssh_client(self.host, self.port, self.username, self.password, self.key_path)
            sftp = ssh.open_sftp()
            with sftp.open(self.remote_path, 'w') as f: f.write(self.content.encode('utf-8'))
            sftp.close(); ssh.close()
            self.write_finished.emit()
        except Exception as e: self.error_occurred.emit(str(e))

class RemoteTreeView(QTreeView):
    files_dropped = pyqtSignal(list)
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

class PropertiesDialog(QDialog):
    def __init__(self, filename, mode, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Properties: {filename}")
        layout = QFormLayout(self)
        self.perms = {
            'Owner': {'Read': stat.S_IRUSR, 'Write': stat.S_IWUSR, 'Execute': stat.S_IXUSR},
            'Group': {'Read': stat.S_IRGRP, 'Write': stat.S_IWGRP, 'Execute': stat.S_IXGRP},
            'Public': {'Read': stat.S_IROTH, 'Write': stat.S_IWOTH, 'Execute': stat.S_IXOTH}
        }
        self.cbs = []
        for group, modes in self.perms.items():
            hb = QHBoxLayout()
            for label, flag in modes.items():
                cb = QCheckBox(label)
                cb.setChecked(bool(mode & flag))
                self.cbs.append((cb, flag))
                hb.addWidget(cb)
            layout.addRow(group, hb)
        self.btn = QPushButton("Apply Permissions")
        self.btn.clicked.connect(self.accept)
        layout.addRow(self.btn)
    def get_new_mode(self):
        new_mode = 0
        for cb, flag in self.cbs:
            if cb.isChecked(): new_mode |= flag
        return new_mode

# --- Multi-Language Syntax Highlighter ---
class EditorSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document, filename):
        super().__init__(document)
        self.highlightingRules = []
        ext = os.path.splitext(filename)[1].lower()
        
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor("#F92672"))
        keywordFormat.setFontWeight(QFont.Weight.Bold)
        
        builtinFormat = QTextCharFormat()
        builtinFormat.setForeground(QColor("#66D9EF"))
        
        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor("#E6DB74"))
        
        numberFormat = QTextCharFormat()
        numberFormat.setForeground(QColor("#AE81FF"))
        
        self.commentFormat = QTextCharFormat()
        self.commentFormat.setForeground(QColor("#75715E"))
        
        varFormat = QTextCharFormat()
        varFormat.setForeground(QColor("#FD971F"))
        
        tagFormat = QTextCharFormat()
        tagFormat.setForeground(QColor("#F92672"))
        
        attrFormat = QTextCharFormat()
        attrFormat.setForeground(QColor("#A6E22E"))

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
            
        elif ext in ['.c', '.cpp', '.h', '.hpp', '.cs', '.java']:
            keywords = ["if", "else", "while", "do", "for", "switch", "case", "break", "continue", "return", "class", "struct", "public", "private", "protected", "virtual", "override", "template", "typename", "new", "delete", "try", "catch", "throw", "namespace", "using", "inline", "true", "false", "null", "nullptr"]
            types = ["int", "float", "double", "char", "void", "bool", "auto", "long", "short", "unsigned", "signed", "size_t", "string"]
            self.highlightingRules.append((QRegularExpression(r"\b(" + "|".join(keywords) + r")\b"), keywordFormat))
            self.highlightingRules.append((QRegularExpression(r"\b(" + "|".join(types) + r")\b"), builtinFormat))
            self.highlightingRules.append((QRegularExpression(r"#[a-zA-Z]+"), keywordFormat)) 
            self.highlightingRules.append((QRegularExpression(r"//[^\n]*"), self.commentFormat))
            self.commentStartExpression = QRegularExpression(r"/\*")
            self.commentEndExpression = QRegularExpression(r"\*/")
            
        elif ext in ['.js', '.ts', '.jsx', '.tsx', '.json']:
            keywords = ["if", "else", "while", "do", "for", "switch", "case", "break", "continue", "return", "function", "var", "let", "const", "class", "extends", "super", "new", "try", "catch", "finally", "throw", "import", "export", "default", "yield", "await", "async", "typeof", "instanceof", "true", "false", "null", "undefined"]
            builtins = ["console", "window", "document", "Math", "JSON", "Promise", "String", "Number", "Boolean", "Array", "Object", "Map", "Set"]
            self.highlightingRules.append((QRegularExpression(r"\b(" + "|".join(keywords) + r")\b"), keywordFormat))
            self.highlightingRules.append((QRegularExpression(r"\b(" + "|".join(builtins) + r")\b"), builtinFormat))
            self.highlightingRules.append((QRegularExpression(r"//[^\n]*"), self.commentFormat))
            self.commentStartExpression = QRegularExpression(r"/\*")
            self.commentEndExpression = QRegularExpression(r"\*/")
            
        elif ext in ['.html', '.xml', '.vue']:
            self.highlightingRules.append((QRegularExpression(r"<\/?[\w:-]+"), tagFormat))
            self.highlightingRules.append((QRegularExpression(r"\/?>"), tagFormat))
            self.highlightingRules.append((QRegularExpression(r"\b[\w:-]+(?=\=)"), attrFormat))
            self.commentStartExpression = QRegularExpression(r"<!--")
            self.commentEndExpression = QRegularExpression(r"-->")
            
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
            commentLength = 0
            if endIndex == -1:
                self.setCurrentBlockState(1)
                commentLength = len(text) - startIndex
            else:
                commentLength = endIndex - startIndex + match.capturedLength()
            
            self.setFormat(startIndex, commentLength, self.commentFormat)
            nextMatch = self.commentStartExpression.match(text, startIndex + commentLength)
            startIndex = nextMatch.capturedStart()

# --- Editor UI Classes ---
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
        
        self.setStyleSheet("""
            QPlainTextEdit { background-color: #272822; color: #F8F8F2; selection-background-color: #49483E; border: 1px solid #18181b; border-radius: 4px; }
        """)
        
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
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor("#3E3D32"))
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#1E1F1C"))
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#75715E")) 
                painter.drawText(0, top, self.lineNumberArea.width() - 8, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(blockNumber + 1))
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            blockNumber += 1

class TextEditorDialog(QDialog):
    def __init__(self, filename, content, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Editing: {filename}")
        self.resize(900, 700)
        
        layout = QVBoxLayout(self)
        
        header_layout = QHBoxLayout()
        header_lbl = QLabel(f"File: {filename}")
        header_lbl.setStyleSheet("color: #a1a1aa; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(header_lbl)
        header_layout.addStretch()
        
        self.editor = CodeEditor()
        self.editor.setPlainText(content)
        self.highlighter = EditorSyntaxHighlighter(self.editor.document(), filename)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save & Upload")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("background-color: #ef4444;")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(header_layout)
        layout.addWidget(self.editor)
        layout.addLayout(btn_layout)
        
    def get_content(self): 
        return self.editor.toPlainText()

class SiteManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Site Manager")
        self.resize(600, 450)
        self.config_dir = os.path.expanduser("~/.config/sftp_elite")
        self.config_file = os.path.join(self.config_dir, "sites.json")
        self.sites = self.load_data()

        layout = QHBoxLayout(self)
        self.site_list = QListWidget()
        self.site_list.addItems(self.sites.keys())
        self.site_list.currentTextChanged.connect(self.populate_fields)
        layout.addWidget(self.site_list, 1)

        edit_layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.host_input = QLineEdit()
        self.port_input = QLineEdit("2206")
        self.port_input.setValidator(QIntValidator(1, 65535, self))
        self.user_input = QLineEdit()
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("Password or Key Passphrase")
        
        key_layout = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Leave blank for password auth")
        self.key_btn = QPushButton("Browse")
        self.key_btn.clicked.connect(self.browse_key)
        key_layout.addWidget(self.key_input)
        key_layout.addWidget(self.key_btn)

        form_layout.addRow("Site Name:", self.name_input)
        form_layout.addRow("Host/IP:", self.host_input)
        form_layout.addRow("Port:", self.port_input)
        form_layout.addRow("Username:", self.user_input)
        form_layout.addRow("Private Key:", key_layout)
        form_layout.addRow("Password:", self.pass_input)
        edit_layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        
        self.new_btn = QPushButton("Clear / New")
        self.new_btn.setStyleSheet("background-color: #52525b;")
        self.new_btn.clicked.connect(self.clear_fields)
        
        self.save_btn = QPushButton("Save / Update")
        self.save_btn.clicked.connect(self.save_site)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setStyleSheet("background-color: #ef4444;")
        self.delete_btn.clicked.connect(self.delete_site)
        
        self.load_btn = QPushButton("Connect")
        self.load_btn.setStyleSheet("background-color: #10b981;")
        self.load_btn.clicked.connect(self.accept)

        btn_layout.addWidget(self.new_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.load_btn)
        edit_layout.addLayout(btn_layout)
        layout.addLayout(edit_layout, 2)

        self.clear_fields()

    def browse_key(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select SSH Private Key", QDir.homePath())
        if file: self.key_input.setText(file)

    def load_data(self):
        if not os.path.exists(self.config_dir): os.makedirs(self.config_dir)
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f: return json.load(f)
        return {}

    def populate_fields(self, site_name):
        if site_name in self.sites:
            data = self.sites[site_name]
            self.name_input.setText(site_name)
            self.host_input.setText(data.get('host', ''))
            self.port_input.setText(str(data.get('port', 2206)))
            self.user_input.setText(data.get('user', ''))
            self.key_input.setText(data.get('key_path', ''))
            saved_pass = keyring.get_password("sftp_elite", site_name)
            self.pass_input.setText(saved_pass if saved_pass else "")

    def clear_fields(self):
        self.site_list.clearSelection()
        self.name_input.clear()
        self.host_input.clear()
        self.port_input.setText("2206")
        self.user_input.clear()
        self.key_input.clear()
        self.pass_input.clear()

    def save_site(self):
        name = self.name_input.text().strip()
        if not name: return
        self.sites[name] = { 'host': self.host_input.text(), 'port': int(self.port_input.text() or 2206), 'user': self.user_input.text(), 'key_path': self.key_input.text() }
        with open(self.config_file, 'w') as f: json.dump(self.sites, f)
        if self.pass_input.text(): keyring.set_password("sftp_elite", name, self.pass_input.text())
        if not self.site_list.findItems(name, Qt.MatchFlag.MatchExactly): self.site_list.addItem(name)
        QMessageBox.information(self, "Saved", f"Site '{name}' saved.")
        self.clear_fields()

    def delete_site(self):
        item = self.site_list.currentItem()
        if not item: return
        name = item.text()
        if name in self.sites:
            del self.sites[name]
            with open(self.config_file, 'w') as f: json.dump(self.sites, f)
            try: keyring.delete_password("sftp_elite", name)
            except: pass
        self.site_list.takeItem(self.site_list.row(item))
        self.clear_fields()

    def get_selected_site(self):
        return { 'host': self.host_input.text(), 'port': self.port_input.text(), 'user': self.user_input.text(), 'key_path': self.key_input.text(), 'password': self.pass_input.text() }

class SFCPClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nova SFTP")
        
        icon_png = os.path.expanduser("~/SFCP-Elite/nova-sftp.png")
        icon_svg = os.path.expanduser("~/SFCP-Elite/nova-sftp.svg")
        if os.path.exists(icon_png): self.setWindowIcon(QIcon(icon_png))
        elif os.path.exists(icon_svg): self.setWindowIcon(QIcon(icon_svg))
            
        self.resize(1340, 920)
        self.current_remote_path = "."
        self.active_transfers = []
        self.current_key_path = ""
        
        self.settings_file = os.path.expanduser("~/.config/sftp_elite/settings.json")
        self.app_settings = self.load_settings()
        
        self.local_home_path = self.app_settings.get("local_home", QDir.homePath())
        if not os.path.exists(self.local_home_path):
            self.local_home_path = QDir.homePath()
            
        self.remote_home_path = "."
        self.local_history = []
        self.remote_history = []
        
        self.dir_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        self.file_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        toolbar_widget = QWidget()
        toolbar_widget.setStyleSheet("background-color: #18181b; border: 1px solid #27272a; border-radius: 6px;")
        conn_layout = QHBoxLayout(toolbar_widget)
        
        self.site_mgr_btn = QPushButton("Bookmarks")
        self.site_mgr_btn.setStyleSheet("background-color: #4f46e5;")
        self.site_mgr_btn.clicked.connect(self.open_site_manager)
        
        self.host_input = QLineEdit(); self.host_input.setPlaceholderText("Host/IP")
        self.port_input = QLineEdit("2206"); self.port_input.setFixedWidth(70)
        self.user_input = QLineEdit(); self.user_input.setPlaceholderText("Username")
        self.key_btn = QToolButton(); self.key_btn.setText("🔑"); self.key_btn.clicked.connect(self.browse_main_key)
        self.pass_input = QLineEdit(); self.pass_input.setPlaceholderText("Passphrase"); self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(lambda: self.load_remote_directory('.'))

        self.native_term_btn = QPushButton(">_ Terminal")
        self.native_term_btn.setStyleSheet("background-color: #3f3f46;")
        self.native_term_btn.setToolTip("Launch Native Ubuntu Terminal with full shell access")
        self.native_term_btn.clicked.connect(self.open_native_terminal)
        
        for w in (self.site_mgr_btn, self.host_input, self.port_input, self.user_input, self.key_btn, self.pass_input, self.connect_btn, self.native_term_btn):
            conn_layout.addWidget(w)
        main_layout.addWidget(toolbar_widget)

        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.browser_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- Local Pane ---
        local_widget = QWidget()
        local_layout = QVBoxLayout(local_widget)
        local_layout.setContentsMargins(0, 0, 0, 0)
        
        local_nav_layout = QHBoxLayout()
        self.local_back_btn = QToolButton(); self.local_back_btn.setProperty("class", "nav-btn"); self.local_back_btn.setText("◀")
        self.local_back_btn.setEnabled(False); self.local_back_btn.clicked.connect(self.go_local_back)
        self.local_up_btn = QToolButton(); self.local_up_btn.setProperty("class", "nav-btn"); self.local_up_btn.setText("▲")
        self.local_up_btn.clicked.connect(self.go_local_up)
        self.local_home_btn = QToolButton(); self.local_home_btn.setProperty("class", "nav-btn"); self.local_home_btn.setText("🏠")
        self.local_home_btn.clicked.connect(self.go_local_home)

        self.local_path_input = QLineEdit(self.local_home_path)
        self.local_path_input.returnPressed.connect(self.on_local_path_entered)
        
        local_nav_layout.addWidget(self.local_back_btn)
        local_nav_layout.addWidget(self.local_up_btn)
        local_nav_layout.addWidget(self.local_home_btn)
        local_nav_layout.addWidget(self.local_path_input)
        
        self.local_view = QTreeView()
        self.local_model = QFileSystemModel()
        self.local_model.setRootPath(QDir.rootPath())
        self.local_view.setModel(self.local_model)
        self.local_view.setRootIndex(self.local_model.index(self.local_home_path))
        self.local_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.local_view.customContextMenuRequested.connect(self.on_local_context_menu)
        self.local_view.doubleClicked.connect(self.on_local_double_click)
        
        local_layout.addWidget(QLabel("Local System", styleSheet="color: #a1a1aa; font-weight: bold;"))
        local_layout.addLayout(local_nav_layout)
        local_layout.addWidget(self.local_view)
        
        # --- Remote Pane ---
        remote_widget = QWidget()
        remote_layout = QVBoxLayout(remote_widget)
        remote_layout.setContentsMargins(0, 0, 0, 0)
        
        remote_nav_layout = QHBoxLayout()
        self.remote_back_btn = QToolButton(); self.remote_back_btn.setProperty("class", "nav-btn"); self.remote_back_btn.setText("◀")
        self.remote_back_btn.setEnabled(False); self.remote_back_btn.clicked.connect(self.go_remote_back)
        self.remote_up_btn = QToolButton(); self.remote_up_btn.setProperty("class", "nav-btn"); self.remote_up_btn.setText("▲")
        self.remote_up_btn.clicked.connect(self.go_remote_up)
        self.remote_home_btn = QToolButton(); self.remote_home_btn.setProperty("class", "nav-btn"); self.remote_home_btn.setText("🏠")
        self.remote_home_btn.clicked.connect(self.go_remote_home)

        self.remote_path_input = QLineEdit(); self.remote_path_input.setPlaceholderText("Not Connected")
        self.remote_path_input.returnPressed.connect(self.on_remote_path_entered)
        self.remote_search_input = QLineEdit(); self.remote_search_input.setPlaceholderText("Filter..."); self.remote_search_input.setFixedWidth(130)
        self.remote_search_input.textChanged.connect(self.filter_remote_files)
        
        remote_nav_layout.addWidget(self.remote_back_btn)
        remote_nav_layout.addWidget(self.remote_up_btn)
        remote_nav_layout.addWidget(self.remote_home_btn)
        remote_nav_layout.addWidget(self.remote_path_input)
        remote_nav_layout.addWidget(self.remote_search_input)
        
        self.remote_view = RemoteTreeView()
        self.remote_view.files_dropped.connect(self.on_files_dropped)
        self.remote_model = QStandardItemModel()
        self.remote_model.setHorizontalHeaderLabels(["Name"])
        
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.remote_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.remote_view.setModel(self.proxy_model)
        self.remote_view.doubleClicked.connect(self.on_remote_double_click)
        self.remote_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.remote_view.customContextMenuRequested.connect(self.on_remote_context_menu)
        
        remote_layout.addWidget(QLabel("Remote Server", styleSheet="color: #a1a1aa; font-weight: bold;"))
        remote_layout.addLayout(remote_nav_layout)
        remote_layout.addWidget(self.remote_view)
        
        self.browser_splitter.addWidget(local_widget)
        self.browser_splitter.addWidget(remote_widget)
        self.main_splitter.addWidget(self.browser_splitter)
        
        # --- Bottom Tabs (Transfers Only) ---
        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.setFixedHeight(220)
        
        queue_widget = QWidget()
        queue_layout = QVBoxLayout(queue_widget)
        queue_layout.setContentsMargins(0,0,0,0)
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
        queue_layout.addWidget(self.queue_table)
        
        self.bottom_tabs.addTab(queue_widget, "Transfer Queue")
        self.main_splitter.addWidget(self.bottom_tabs)
        
        main_layout.addWidget(self.main_splitter)
        self.statusBar().showMessage("Ready")

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as f: return json.load(f)
        return {}

    def save_settings(self):
        if not os.path.exists(os.path.dirname(self.settings_file)):
            os.makedirs(os.path.dirname(self.settings_file))
        with open(self.settings_file, 'w') as f: json.dump(self.app_settings, f)

    def set_as_local_home(self, path):
        self.local_home_path = path
        self.app_settings["local_home"] = path
        self.save_settings()
        QMessageBox.information(self, "Home Set", f"Local home directory set to:\n{path}")

    def set_as_remote_home(self, path):
        host = self.host_input.text()
        if not host: return
        if "remote_homes" not in self.app_settings:
            self.app_settings["remote_homes"] = {}
        self.app_settings["remote_homes"][host] = path
        self.save_settings()
        QMessageBox.information(self, "Home Set", f"Remote home directory for '{host}' set to:\n{path}")

    # --- Native OS Terminal Launcher ---
    def open_native_terminal(self):
        host = self.host_input.text().strip()
        user = self.user_input.text().strip()
        port = self.port_input.text().strip() or "22"
        
        if not host or not user:
            QMessageBox.warning(self, "Missing Info", "Connect to a server first to launch the terminal.")
            return
            
        ssh_cmd = ["ssh", "-p", port]
        if self.current_key_path and os.path.exists(self.current_key_path):
            ssh_cmd.extend(["-i", self.current_key_path])
        
        if self.current_remote_path and self.current_remote_path not in [".", "/"]:
            ssh_cmd.extend(["-t", f"{user}@{host}", f"cd '{self.current_remote_path}' ; exec $SHELL -l"])
        else:
            ssh_cmd.append(f"{user}@{host}")
            
        try:
            subprocess.Popen(["gnome-terminal", "--"] + ssh_cmd)
        except Exception:
            try:
                subprocess.Popen(["x-terminal-emulator", "-e", " ".join(ssh_cmd)])
            except Exception as ex:
                QMessageBox.critical(self, "Error", f"Could not launch native terminal: {ex}")

    # --- Local Navigation Actions ---
    def set_local_path(self, target_path, record_history=True):
        if not os.path.exists(target_path): return
        current_path = self.local_path_input.text()
        if record_history and current_path != target_path:
            self.local_history.append(current_path)
            self.local_back_btn.setEnabled(True)
        self.local_view.setRootIndex(self.local_model.index(target_path))
        self.local_path_input.setText(target_path)

    def go_local_back(self):
        if self.local_history:
            prev = self.local_history.pop()
            self.local_back_btn.setEnabled(len(self.local_history) > 0)
            self.set_local_path(prev, record_history=False)

    def go_local_up(self):
        current = self.local_path_input.text()
        parent = os.path.dirname(current.rstrip(os.sep))
        if parent and os.path.exists(parent): self.set_local_path(parent)

    def go_local_home(self): self.set_local_path(self.local_home_path)
    def on_local_path_entered(self): self.set_local_path(self.local_path_input.text())
    def on_local_double_click(self, index):
        if self.local_model.isDir(index): self.set_local_path(self.local_model.filePath(index))

    # --- Remote Navigation Actions ---
    def go_remote_back(self):
        if self.remote_history:
            prev = self.remote_history.pop()
            self.remote_back_btn.setEnabled(len(self.remote_history) > 0)
            self.load_remote_directory(prev, record_history=False)

    def go_remote_up(self):
        if self.current_remote_path != "." and self.current_remote_path != "/":
            parent = "/".join(self.current_remote_path.rstrip('/').split('/')[:-1]) or "/"
            self.load_remote_directory(parent)

    def go_remote_home(self):
        host = self.host_input.text()
        if host:
            target = self.app_settings.get("remote_homes", {}).get(host, self.remote_home_path)
            self.load_remote_directory(target)

    def filter_remote_files(self, text):
        self.proxy_model.setFilterRegularExpression(text)

    def browse_main_key(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select SSH Key", QDir.homePath())
        if file:
            self.current_key_path = file
            self.key_btn.setStyleSheet("background-color: #10b981;") 

    def on_remote_path_entered(self):
        if self.host_input.text(): self.load_remote_directory(self.remote_path_input.text().strip())

    def open_site_manager(self):
        dialog = SiteManagerDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            site_data = dialog.get_selected_site()
            if site_data['host']:
                self.host_input.setText(site_data['host'])
                self.port_input.setText(site_data['port'])
                self.user_input.setText(site_data['user'])
                self.pass_input.setText(site_data['password'])
                self.current_key_path = site_data['key_path']
                self.key_btn.setStyleSheet("background-color: #10b981;" if self.current_key_path else "")
                self.load_remote_directory('.')

    def load_remote_directory(self, path, record_history=True):
        if not self.host_input.text() or not self.user_input.text(): return
        
        host = self.host_input.text()
        if path == '.':
            path = self.app_settings.get("remote_homes", {}).get(host, '.')
            
        if record_history and self.current_remote_path != "." and self.current_remote_path != path:
            self.remote_history.append(self.current_remote_path)
            self.remote_back_btn.setEnabled(True)

        self.connect_btn.setEnabled(False)
        self.statusBar().showMessage(f"Connecting to {self.host_input.text()}...")
        self.worker = SFTPWorker(self.host_input.text(), int(self.port_input.text()), self.user_input.text(), self.pass_input.text(), self.current_key_path, path)
        self.worker.directory_loaded.connect(self.on_directory_loaded)
        self.worker.error_occurred.connect(self.on_network_error)
        self.worker.start()

    def on_directory_loaded(self, file_list, current_path):
        self.current_remote_path = current_path
        host = self.host_input.text()
        
        if host not in self.app_settings.get("remote_homes", {}) and self.remote_home_path == ".":
            self.remote_home_path = current_path
            
        self.remote_model.removeRows(0, self.remote_model.rowCount())
        self.remote_path_input.setText(current_path)
        
        if current_path != '/':
            up_item = QStandardItem("..")
            up_item.setIcon(self.dir_icon)
            up_item.setData({'is_dir': True, 'mode': 0}, Qt.ItemDataRole.UserRole)
            self.remote_model.appendRow(up_item)
            
        for f in file_list:
            item = QStandardItem(f['name'])
            item.setIcon(self.dir_icon if f['is_dir'] else self.file_icon)
            item.setData({'is_dir': f['is_dir'], 'mode': f['mode']}, Qt.ItemDataRole.UserRole) 
            self.remote_model.appendRow(item)
            
        self.connect_btn.setText("Connected"); self.connect_btn.setStyleSheet("background-color: #10b981;")
        self.connect_btn.setEnabled(True)
        self.statusBar().showMessage(f"Connected to {current_path}")

    def on_network_error(self, error_msg):
        self.connect_btn.setEnabled(True); self.connect_btn.setStyleSheet("background-color: #2563eb;")
        QMessageBox.critical(self, "Error", f"Operation failed:\n{error_msg}")

    def run_remote_command(self, command, target_path, arg=None):
        self.cmd_worker = RemoteCommandWorker(self.host_input.text(), int(self.port_input.text()), self.user_input.text(), self.pass_input.text(), self.current_key_path, command, target_path, arg)
        self.cmd_worker.command_finished.connect(lambda: self.load_remote_directory(self.current_remote_path, record_history=False))
        self.cmd_worker.error_occurred.connect(self.on_network_error)
        self.cmd_worker.start()

    def on_remote_double_click(self, proxy_index):
        source_index = self.proxy_model.mapToSource(proxy_index)
        item = self.remote_model.itemFromIndex(source_index)
        data = item.data(Qt.ItemDataRole.UserRole)
        
        if data['is_dir']:
            folder_name = item.text()
            if folder_name == "..": new_path = "/".join(self.current_remote_path.rstrip('/').split('/')[:-1])
            else: new_path = f"{self.current_remote_path.rstrip('/')}/{folder_name}"
            self.load_remote_directory(new_path or "/")
        else:
            filename = item.text()
            remote_path = f"{self.current_remote_path.rstrip('/')}/{filename}"
            self.read_worker = RemoteReadWorker(self.host_input.text(), int(self.port_input.text()), self.user_input.text(), self.pass_input.text(), self.current_key_path, remote_path)
            self.read_worker.content_loaded.connect(lambda content: self.open_editor(filename, remote_path, content))
            self.read_worker.error_occurred.connect(self.on_network_error)
            self.read_worker.start()

    def open_editor(self, filename, remote_path, content):
        dialog = TextEditorDialog(filename, content, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.write_worker = RemoteWriteWorker(self.host_input.text(), int(self.port_input.text()), self.user_input.text(), self.pass_input.text(), self.current_key_path, remote_path, dialog.get_content())
            self.write_worker.write_finished.connect(lambda: QMessageBox.information(self, "Success", "File saved."))
            self.write_worker.error_occurred.connect(self.on_network_error)
            self.write_worker.start()

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
        
        if action == upload_action and self.current_remote_path != ".":
            self.start_transfer(file_path, f"{self.current_remote_path.rstrip('/')}/{os.path.basename(file_path)}", "upload")
        elif action == set_home_action:
            self.set_as_local_home(file_path)

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
        item, data = None, None
        
        if proxy_index.isValid():
            source_index = self.proxy_model.mapToSource(proxy_index)
            item = self.remote_model.itemFromIndex(source_index)
            data = item.data(Qt.ItemDataRole.UserRole)
            if item.text() != "..":
                menu.addSeparator()
                download_action = menu.addAction(f"Download {'Folder' if data['is_dir'] else 'File'}")
                rename_action = menu.addAction("Rename")
                prop_action = menu.addAction("Properties (chmod)")
                delete_action = menu.addAction("Delete")
                if data['is_dir']:
                    menu.addSeparator()
                    set_home_action = menu.addAction("Set as Default Remote Home")
                
        action = menu.exec(self.remote_view.viewport().mapToGlobal(position))
        
        if action == new_folder_action:
            name, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
            if ok and name: self.run_remote_command('mkdir', f"{self.current_remote_path.rstrip('/')}/{name}")
        elif action == download_action and item:
            local_idx = self.local_view.currentIndex()
            local_dir = self.local_model.filePath(local_idx) if local_idx.isValid() else QDir.homePath()
            if not os.path.isdir(local_dir): local_dir = os.path.dirname(local_dir)
            self.start_transfer(os.path.join(local_dir, item.text()), f"{self.current_remote_path.rstrip('/')}/{item.text()}", "download")
        elif action == rename_action and item:
            new_name, ok = QInputDialog.getText(self, "Rename", "Enter new name:", text=item.text())
            if ok and new_name and new_name != item.text():
                self.run_remote_command('rename', f"{self.current_remote_path.rstrip('/')}/{item.text()}", f"{self.current_remote_path.rstrip('/')}/{new_name}")
        elif action == delete_action and item:
            if QMessageBox.question(self, "Delete", f"Delete {item.text()}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                self.run_remote_command('rmdir' if data['is_dir'] else 'rm', f"{self.current_remote_path.rstrip('/')}/{item.text()}")
        elif action == prop_action and item:
            dialog = PropertiesDialog(item.text(), data['mode'], self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.run_remote_command('chmod', f"{self.current_remote_path.rstrip('/')}/{item.text()}", dialog.get_new_mode())
        elif action == set_home_action and item:
            target_path = f"{self.current_remote_path.rstrip('/')}/{item.text()}"
            self.set_as_remote_home(target_path)

    def start_transfer(self, local_path, remote_path, direction):
        row = self.queue_model.rowCount()
        self.queue_model.insertRow(row)
        dir_icon = "⬆" if direction == "upload" else "⬇"
        self.queue_model.setItem(row, 0, QStandardItem(dir_icon))
        self.queue_model.item(row, 0).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.queue_model.setItem(row, 1, QStandardItem(os.path.basename(local_path)))
        self.queue_model.setItem(row, 2, QStandardItem("Transferring..."))
        
        pb = QProgressBar(); pb.setValue(0)
        self.queue_table.setIndexWidget(self.queue_model.index(row, 3), pb)
        
        worker = TransferWorker(self.host_input.text(), int(self.port_input.text()), self.user_input.text(), self.pass_input.text(), self.current_key_path, local_path, remote_path, direction, row)
        worker.progress_updated.connect(self.update_progress)
        worker.transfer_finished.connect(self.transfer_complete)
        worker.error_occurred.connect(self.transfer_error)
        self.active_transfers.append(worker)
        worker.start()
        self.bottom_tabs.setCurrentIndex(0)

    def update_progress(self, row, pct):
        pb = self.queue_table.indexWidget(self.queue_model.index(row, 3))
        if pb: pb.setValue(pct if pct > 0 else 0)

    def transfer_complete(self, row):
        self.queue_model.setItem(row, 2, QStandardItem("Done"))
        pb = self.queue_table.indexWidget(self.queue_model.index(row, 3))
        if pb: pb.setValue(100)
        if self.queue_model.item(row, 0).text() == "⬆":
            self.load_remote_directory(self.current_remote_path, record_history=False)
            
    def transfer_error(self, row, error_msg):
        self.queue_model.setItem(row, 2, QStandardItem(f"Failed: {error_msg}"))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Nova SFTP")
    app.setDesktopFileName("nova-sftp.desktop")
    app.setStyleSheet(PREMIUM_THEME)
    window = SFCPClient()
    window.show()
    sys.exit(app.exec())
