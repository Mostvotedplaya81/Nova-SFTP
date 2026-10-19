import os
import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QPlainTextEdit, QTextEdit, QWidget
)
from PyQt6.QtGui import (
    QColor, QTextFormat, QFont, QTextCursor, QSyntaxHighlighter, 
    QTextCharFormat, QPainter
)
from PyQt6.QtCore import Qt, QRect, QSize, QRegularExpression
from ui.themes import CLEAN_LIGHT_THEME, DRACULA_THEME, MONOKAI_THEME, PREMIUM_DARK_THEME

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
