from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtGui import QColor, QPainter, QTextCursor, QFont, QTextFormat
from PyQt5.QtWidgets import (QWidget, QPlainTextEdit, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QLabel, QFrame)

class LineNumberArea(QWidget):
    """A custom widget to draw the line numbers on the left side."""
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)


class CodeEditor(QPlainTextEdit):
    """The main editor canvas that manages the line number margin."""
    def __init__(self):
        super().__init__()
        self.lineNumberArea = LineNumberArea(self)
        
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        
        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()
        
        # Set a monospaced default font
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)

    def lineNumberAreaWidth(self):
        digits = 1
        max_val = max(1, self.blockCount())
        while max_val >= 10:
            max_val /= 10
            digits += 1
        # Use horizontalAdvance for newer PyQt versions; fallback to width() if needed
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#18181b")) # Dark background for line numbers
        
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QColor("#71717a")) # Muted grey for text
                painter.drawText(0, top, self.lineNumberArea.width() - 5, 
                                 self.fontMetrics().height(),
                                 Qt.AlignRight | Qt.AlignVCenter, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber += 1

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QPlainTextEdit.ExtraSelection()
            lineColor = QColor("#27272a") # Subtle highlight for the active row
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)


class AdvancedTextEditor(QWidget):
    """The complete widget packaging the editor, search bar, and size controls."""
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Build Toolbar
        self.toolbar = QFrame()
        self.toolbar.setStyleSheet("""
            QFrame { background-color: #18181b; border-bottom: 1px solid #3f3f46; }
            QLineEdit { background-color: #27272a; color: #f4f4f5; border: 1px solid #3f3f46; padding: 4px; border-radius: 4px;}
            QPushButton { background-color: #2563eb; color: white; border: none; padding: 5px 10px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #3b82f6; }
            QLabel { color: #a1a1aa; font-weight: bold; }
        """)
        tb_layout = QHBoxLayout(self.toolbar)
        tb_layout.setContentsMargins(8, 8, 8, 8)
        
        # Search & Replace Inputs
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Find...")
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace with...")
        
        self.btn_find = QPushButton("Find Next")
        self.btn_replace = QPushButton("Replace")
        self.btn_replace_all = QPushButton("Replace All")
        
        # Zoom Controls
        self.btn_zoom_out = QPushButton("A-")
        self.btn_zoom_reset = QPushButton("Reset")
        self.btn_zoom_in = QPushButton("A+")

        # Construct Toolbar Layout
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

        # Build Editor
        self.editor = CodeEditor()
        self.editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #09090b; /* Deep black/grey for reading contrast */
                color: #f4f4f5;
                border: none;
                selection-background-color: #2563eb;
            }
        """)
        
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.editor)

        # Connect Logic
        self.btn_find.clicked.connect(self.find_text)
        self.btn_replace.clicked.connect(self.replace_text)
        self.btn_replace_all.clicked.connect(self.replace_all_text)
        self.btn_zoom_in.clicked.connect(lambda: self.zoom(1))
        self.btn_zoom_out.clicked.connect(lambda: self.zoom(-1))
        self.btn_zoom_reset.clicked.connect(lambda: self.zoom(0))
        
        self.base_font_size = 11

    def find_text(self):
        text = self.find_input.text()
        if text:
            found = self.editor.find(text)
            if not found:
                # Wrap to the beginning of the document and search again
                self.editor.moveCursor(QTextCursor.Start)
                self.editor.find(text)

    def replace_text(self):
        cursor = self.editor.textCursor()
        # Ensure we only replace if the exact search term is currently highlighted
        if cursor.hasSelection() and cursor.selectedText() == self.find_input.text():
            cursor.insertText(self.replace_input.text())
        # Automatically jump to the next match
        self.find_text()

    def replace_all_text(self):
        find_str = self.find_input.text()
        replace_str = self.replace_input.text()
        if not find_str: return
        
        # Start from top
        self.editor.moveCursor(QTextCursor.Start)
        self.editor.textCursor().beginEditBlock() # Groups all replacements into a single Undo action
        
        while self.editor.find(find_str):
            self.editor.textCursor().insertText(replace_str)
            
        self.editor.textCursor().endEditBlock()

    def zoom(self, direction):
        font = self.editor.font()
        if direction == 0:
            font.setPointSize(self.base_font_size)
        else:
            new_size = font.pointSize() + (direction * 2) # Step size of 2 points
            if 8 <= new_size <= 36:
                font.setPointSize(new_size)
        self.editor.setFont(font)
        # Force the line number margin to recalculate its width based on the new font size
        self.editor.updateLineNumberAreaWidth(0)
