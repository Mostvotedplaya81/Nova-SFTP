import os
import re
import asyncio
from PyQt6.QtWidgets import (
    QWidget, QPlainTextEdit, QTextEdit, QVBoxLayout, QHBoxLayout,
    QPushButton, QTabWidget, QTabBar, QMessageBox, QMainWindow, QLabel,
    QLineEdit, QInputDialog, QDialog, QComboBox
)
from PyQt6.QtGui import (
    QColor, QTextCharFormat, QFont, QSyntaxHighlighter, QPainter, QTextFormat,
    QKeySequence, QShortcut, QTextDocument, QTextCursor, QPen
)
from PyQt6.QtCore import Qt, QRect, QSize


# ----------------------------------------------------
# THEME PALETTES (IDE CHROME + SYNTAX COLORS)
# ----------------------------------------------------
EDITOR_THEMES = {
    "dark": {
        "name": "Midnight Dark",
        "win_bg": "#09090b",
        "bar_bg": "#18181b",
        "editor_bg": "#0c0a09",
        "editor_fg": "#e4e4e7",
        "gutter_bg": "#121215",
        "gutter_fg": "#52525b",
        "gutter_active_fg": "#f4f4f5",
        "border": "#27272a",
        "line_highlight": "#18181b",
        "selection_bg": "#264f78",
        "accent": "#a855f7",
        "scroll_handle": "#3f3f46",
        "scroll_hover": "#52525b",
        "syntax": {
            "keyword": "#c678dd",
            "type": "#e5c07b",
            "class": "#e5c07b",
            "func": "#61afef",
            "string": "#98c379",
            "number": "#d19a66",
            "constant": "#d19a66",
            "comment": "#5c6370",
            "variable": "#e06c75",
            "decorator": "#56b6c2",
            "tag": "#e06c75",
            "attr": "#d19a66",
        }
    },
    "dracula": {
        "name": "Dracula",
        "win_bg": "#191a21",
        "bar_bg": "#21222c",
        "editor_bg": "#282a36",
        "editor_fg": "#f8f8f2",
        "gutter_bg": "#21222c",
        "gutter_fg": "#6272a4",
        "gutter_active_fg": "#f8f8f2",
        "border": "#44475a",
        "line_highlight": "#343746",
        "selection_bg": "#44475a",
        "accent": "#bd93f9",
        "scroll_handle": "#44475a",
        "scroll_hover": "#6272a4",
        "syntax": {
            "keyword": "#ff79c6",
            "type": "#8be9fd",
            "class": "#8be9fd",
            "func": "#50fa7b",
            "string": "#f1fa8c",
            "number": "#bd93f9",
            "constant": "#bd93f9",
            "comment": "#6272a4",
            "variable": "#ffb86c",
            "decorator": "#50fa7b",
            "tag": "#ff79c6",
            "attr": "#50fa7b",
        }
    },
    "monokai": {
        "name": "Monokai",
        "win_bg": "#1e1f1c",
        "bar_bg": "#272822",
        "editor_bg": "#272822",
        "editor_fg": "#f8f8f2",
        "gutter_bg": "#1e1f1c",
        "gutter_fg": "#75715e",
        "gutter_active_fg": "#f8f8f2",
        "border": "#3e3d32",
        "line_highlight": "#383830",
        "selection_bg": "#49483e",
        "accent": "#f92672",
        "scroll_handle": "#49483e",
        "scroll_hover": "#75715e",
        "syntax": {
            "keyword": "#f92672",
            "type": "#66d9ef",
            "class": "#a6e22e",
            "func": "#a6e22e",
            "string": "#e6db74",
            "number": "#ae81ff",
            "constant": "#ae81ff",
            "comment": "#75715e",
            "variable": "#fd971f",
            "decorator": "#66d9ef",
            "tag": "#f92672",
            "attr": "#a6e22e",
        }
    },
    "light": {
        "name": "Clean Light",
        "win_bg": "#f6f8fa",
        "bar_bg": "#eaeef2",
        "editor_bg": "#ffffff",
        "editor_fg": "#24292f",
        "gutter_bg": "#f6f8fa",
        "gutter_fg": "#8c959f",
        "gutter_active_fg": "#24292f",
        "border": "#d0d7de",
        "line_highlight": "#f0f4f8",
        "selection_bg": "#add6ff",
        "accent": "#0969da",
        "scroll_handle": "#c1c8d1",
        "scroll_hover": "#8c959f",
        "syntax": {
            "keyword": "#cf222e",
            "type": "#953800",
            "class": "#953800",
            "func": "#8250df",
            "string": "#0a3069",
            "number": "#0550ae",
            "constant": "#0550ae",
            "comment": "#6e7781",
            "variable": "#953800",
            "decorator": "#8250df",
            "tag": "#116329",
            "attr": "#0550ae",
        }
    }
}


# ----------------------------------------------------
# LINE NUMBER GUTTER & CODE EDITOR CANVAS
# ----------------------------------------------------
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.lineNumberAreaPaintEvent(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, filepath=None, content="", theme_key="dark"):
        super().__init__()
        self.filepath = filepath
        self.theme_key = theme_key if theme_key in EDITOR_THEMES else "dark"
        self.line_number_area = LineNumberArea(self)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.on_cursor_changed)

        font = QFont("Cascadia Mono", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(' ') * 4)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.apply_theme(self.theme_key)
        self.update_line_number_area_width(0)

        if content:
            self.setPlainText(content)

    def apply_theme(self, theme_key):
        self.theme_key = theme_key if theme_key in EDITOR_THEMES else "dark"
        t = EDITOR_THEMES[self.theme_key]
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {t['editor_bg']};
                color: {t['editor_fg']};
                border: none;
                selection-background-color: {t['selection_bg']};
            }}
            QScrollBar:vertical {{
                background: {t['editor_bg']};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {t['scroll_handle']};
                min-height: 25px;
                border-radius: 5px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {t['scroll_hover']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: {t['editor_bg']};
                height: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background: {t['scroll_handle']};
                min-width: 25px;
                border-radius: 5px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {t['scroll_hover']};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """)
        self.highlight_current_line()
        self.line_number_area.update()

    def line_number_area_width(self):
        digits = 1
        m = max(1, self.blockCount())
        while m >= 10:
            m //= 10
            digits += 1
        return 22 + self.fontMetrics().horizontalAdvance('9') * max(2, digits)

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def on_cursor_changed(self):
        self.highlight_current_line()
        self.line_number_area.update()

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            t = EDITOR_THEMES[self.theme_key]
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor(t["line_highlight"]))
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def lineNumberAreaPaintEvent(self, event):
        t = EDITOR_THEMES[self.theme_key]
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(t["gutter_bg"]))

        # Subtle right-side border separating gutter from code
        painter.setPen(QPen(QColor(t["border"]), 1))
        painter.drawLine(
            self.line_number_area.width() - 1,
            event.rect().top(),
            self.line_number_area.width() - 1,
            event.rect().bottom()
        )

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        current_block_num = self.textCursor().blockNumber()
        font_metrics = self.fontMetrics()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                if block_number == current_block_num:
                    painter.setPen(QColor(t["gutter_active_fg"]))
                    f = painter.font()
                    f.setBold(True)
                    painter.setFont(f)
                else:
                    painter.setPen(QColor(t["gutter_fg"]))
                    f = painter.font()
                    f.setBold(False)
                    painter.setFont(f)

                painter.drawText(
                    0, top, self.line_number_area.width() - 8, font_metrics.height(),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, number
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            current_line = cursor.block().text()
            indent = ""
            for char in current_line:
                if char in (' ', '\t'):
                    indent += char
                else:
                    break
            stripped = current_line.strip()
            if stripped.endswith((':', '{', '[', '(')):
                indent += "    "
            super().keyPressEvent(event)
            self.insertPlainText(indent)
            return
        elif event.key() == Qt.Key.Key_Tab:
            self.insertPlainText("    ")
            return
        super().keyPressEvent(event)

    def find_text(self, query, forward=True):
        if not query:
            return
        flags = QTextDocument.FindFlag(0)
        if not forward:
            flags |= QTextDocument.FindFlag.FindBackward
        found = self.find(query, flags)
        if not found:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start if forward else QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)
            self.find(query, flags)

    def replace_text(self, query, replacement):
        if not query:
            return
        cursor = self.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == query:
            cursor.insertText(replacement)
        self.find_text(query)

    def replace_all(self, query, replacement):
        if not query:
            return 0
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.setTextCursor(cursor)
        count = 0
        while self.find(query):
            self.textCursor().insertText(replacement)
            count += 1
        cursor.endEditBlock()
        return count

    def jump_to_line(self, line_num):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.MoveAnchor, line_num - 1)
        self.setTextCursor(cursor)
        self.centerCursor()


# ----------------------------------------------------
# MULTI-PASS REGEX & BLOCK STATE SYNTAX HIGHLIGHTER
# ----------------------------------------------------
class EditorSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document, filename="", theme_key="dark", lang_override=None):
        super().__init__(document)
        self.filename = filename
        self.theme_key = theme_key if theme_key in EDITOR_THEMES else "dark"
        self.lang_override = lang_override
        self.lang = self.detect_language(filename, document.toPlainText()[:250])
        self.build_rules()

    @staticmethod
    def detect_language(filename, first_chunk=""):
        name = os.path.basename(filename).lower()
        ext = name.split('.')[-1] if '.' in name else ''

        if ext in ['py', 'pyw']:
            return 'python'
        if ext in ['php', 'phtml']:
            return 'php'
        if ext in ['js', 'jsx', 'ts', 'tsx', 'mjs', 'json']:
            return 'javascript'
        if ext in ['c', 'cpp', 'cc', 'cxx', 'h', 'hpp', 'ino']:
            return 'c'
        if ext in ['sh', 'bash', 'zsh', 'env'] or name in ['bashrc', '.bashrc', 'profile', '.profile', '.bash_profile', 'dockerfile']:
            return 'bash'
        if ext in ['sql']:
            return 'sql'
        if ext in ['rb', 'rake', 'gemspec'] or name == 'gemfile':
            return 'ruby'
        if ext in ['css', 'scss', 'less']:
            return 'css'
        if ext in ['html', 'htm', 'xml', 'svg', 'vue']:
            return 'html'
        if ext in ['yml', 'yaml', 'toml', 'ini', 'conf', 'cfg', 'service', 'vhost']:
            return 'yaml'

        # Fallback: Inspect Shebang or opening tag
        first_line = first_chunk.splitlines()[0] if first_chunk else ""
        if first_line.startswith("#!"):
            if "python" in first_line:
                return 'python'
            if any(sh in first_line for sh in ("bash", "sh", "zsh")):
                return 'bash'
            if "php" in first_line:
                return 'php'
            if "ruby" in first_line:
                return 'ruby'
            if "node" in first_line:
                return 'javascript'
        if "<?php" in first_chunk:
            return 'php'
        return 'yaml'

    def set_theme_and_lang(self, theme_key, lang_override=None):
        self.theme_key = theme_key if theme_key in EDITOR_THEMES else "dark"
        if lang_override and lang_override != "auto":
            self.lang = lang_override
        else:
            self.lang = self.detect_language(self.filename, self.document().toPlainText()[:250])
        self.build_rules()
        self.rehighlight()

    def _fmt(self, color_hex, bold=False, italic=False):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color_hex))
        if bold:
            fmt.setFontWeight(QFont.Weight.Bold)
        if italic:
            fmt.setFontItalic(True)
        return fmt

    def build_rules(self):
        s = EDITOR_THEMES[self.theme_key]["syntax"]
        self.code_rules = []
        self.string_rules = []
        self.comment_rules = []

        keyword_fmt = self._fmt(s["keyword"], bold=True)
        type_fmt = self._fmt(s["type"], italic=True)
        class_fmt = self._fmt(s["class"], bold=True)
        func_fmt = self._fmt(s["func"])
        string_fmt = self._fmt(s["string"])
        number_fmt = self._fmt(s["number"])
        const_fmt = self._fmt(s["constant"], bold=True)
        self.comment_fmt = self._fmt(s["comment"], italic=True)
        self.string_fmt = string_fmt
        var_fmt = self._fmt(s["variable"])
        dec_fmt = self._fmt(s["decorator"], italic=True)
        tag_fmt = self._fmt(s["tag"], bold=True)
        attr_fmt = self._fmt(s["attr"])

        lang = self.lang

        # 1. Numbers (Hex, Float, Integer)
        self.code_rules.append((re.compile(r"\b0[xX][0-9a-fA-F]+\b|\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b"), number_fmt))

        # 2. Universal Constants & Booleans
        consts = ['True', 'False', 'None', 'true', 'false', 'null', 'nullptr', 'NULL', 'NIL', 'nil', 'NaN', 'Infinity', 'ON', 'OFF', 'yes', 'no']
        self.code_rules.append((re.compile(r"\b(?:" + "|".join(consts) + r")\b"), const_fmt))

        # 3. Language-Specific Keywords & Types
        keywords, types = [], []
        if lang == 'python':
            keywords = ['and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield', 'async', 'await', 'match', 'case']
            types = ['int', 'float', 'str', 'bool', 'list', 'dict', 'set', 'tuple', 'bytes', 'object', 'Exception', 'self', 'cls', 'super', 'print', 'len', 'range', 'open', 'enumerate', 'zip', 'isinstance', 'getattr', 'setattr', 'hasattr']
        elif lang == 'php':
            keywords = ['abstract', 'and', 'array', 'as', 'break', 'callable', 'case', 'catch', 'class', 'clone', 'const', 'continue', 'declare', 'default', 'die', 'do', 'echo', 'else', 'elseif', 'empty', 'enddeclare', 'endfor', 'endforeach', 'endif', 'endswitch', 'endwhile', 'eval', 'exit', 'extends', 'final', 'finally', 'fn', 'for', 'foreach', 'function', 'global', 'goto', 'if', 'implements', 'include', 'include_once', 'instanceof', 'insteadof', 'interface', 'isset', 'list', 'match', 'namespace', 'new', 'or', 'print', 'private', 'protected', 'public', 'readonly', 'require', 'require_once', 'return', 'static', 'switch', 'throw', 'trait', 'try', 'unset', 'use', 'var', 'while', 'xor', 'yield']
            types = ['int', 'float', 'string', 'bool', 'array', 'object', 'callable', 'iterable', 'void', 'mixed', 'self', 'parent', 'PDO', 'Exception', 'stdClass']
        elif lang == 'javascript':
            keywords = ['break', 'case', 'catch', 'class', 'const', 'continue', 'debugger', 'default', 'delete', 'do', 'else', 'export', 'extends', 'finally', 'for', 'function', 'if', 'import', 'in', 'instanceof', 'new', 'of', 'return', 'super', 'switch', 'this', 'throw', 'try', 'typeof', 'var', 'void', 'while', 'with', 'yield', 'let', 'async', 'await', 'static', 'from', 'as']
            types = ['Array', 'Date', 'Error', 'Function', 'JSON', 'Math', 'Number', 'Object', 'Promise', 'RegExp', 'String', 'Symbol', 'Map', 'Set', 'console', 'window', 'document', 'fetch', 'process', 'module']
        elif lang == 'c':
            keywords = ['auto', 'break', 'case', 'catch', 'class', 'const', 'constexpr', 'continue', 'default', 'delete', 'do', 'else', 'enum', 'explicit', 'export', 'extern', 'for', 'friend', 'goto', 'if', 'inline', 'mutable', 'namespace', 'new', 'noexcept', 'operator', 'override', 'private', 'protected', 'public', 'register', 'return', 'sizeof', 'static', 'static_cast', 'struct', 'switch', 'template', 'this', 'throw', 'try', 'typedef', 'typename', 'union', 'using', 'virtual', 'volatile', 'while']
            types = ['bool', 'char', 'double', 'float', 'int', 'long', 'short', 'signed', 'unsigned', 'void', 'wchar_t', 'size_t', 'int8_t', 'int16_t', 'int32_t', 'int64_t', 'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t', 'string', 'vector', 'map', 'set', 'std']
        elif lang == 'bash':
            keywords = ['if', 'fi', 'then', 'elif', 'else', 'for', 'do', 'done', 'until', 'while', 'break', 'continue', 'case', 'esac', 'function', 'in', 'select', 'time', 'export', 'local', 'readonly', 'return', 'set', 'unset', 'shift', 'exit', 'trap', 'source']
            types = ['echo', 'printf', 'read', 'cd', 'pwd', 'ls', 'cp', 'mv', 'rm', 'mkdir', 'chmod', 'chown', 'grep', 'awk', 'sed', 'find', 'tar', 'curl', 'wget', 'systemctl', 'docker', 'rclone', 'apt', 'sudo', 'cat', 'tail', 'head', 'sort', 'uniq', 'wc', 'cut', 'tr']
        elif lang == 'sql':
            keywords = ['SELECT', 'FROM', 'WHERE', 'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE', 'TABLE', 'DATABASE', 'SCHEMA', 'DROP', 'ALTER', 'ADD', 'COLUMN', 'INDEX', 'VIEW', 'TRIGGER', 'PROCEDURE', 'FUNCTION', 'PRIMARY', 'FOREIGN', 'KEY', 'REFERENCES', 'UNIQUE', 'DEFAULT', 'AUTO_INCREMENT', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'OUTER', 'CROSS', 'ON', 'GROUP', 'BY', 'ORDER', 'ASC', 'DESC', 'HAVING', 'LIMIT', 'OFFSET', 'UNION', 'ALL', 'DISTINCT', 'AS', 'AND', 'OR', 'NOT', 'IS', 'EXISTS', 'BETWEEN', 'IN', 'LIKE', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'BEGIN', 'COMMIT', 'ROLLBACK', 'TRANSACTION', 'GRANT', 'REVOKE']
            types = ['INT', 'INTEGER', 'BIGINT', 'SMALLINT', 'TINYINT', 'DECIMAL', 'NUMERIC', 'FLOAT', 'DOUBLE', 'VARCHAR', 'CHAR', 'TEXT', 'LONGTEXT', 'MEDIUMTEXT', 'BLOB', 'DATE', 'DATETIME', 'TIMESTAMP', 'TIME', 'YEAR', 'BOOLEAN', 'BOOL', 'JSON', 'UUID', 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'COALESCE', 'NOW', 'IFNULL']
        elif lang == 'ruby':
            keywords = ['BEGIN', 'END', 'alias', 'and', 'begin', 'break', 'case', 'class', 'def', 'defined\\?', 'do', 'else', 'elsif', 'end', 'ensure', 'for', 'if', 'in', 'module', 'next', 'not', 'or', 'redo', 'rescue', 'retry', 'return', 'self', 'super', 'then', 'undef', 'unless', 'until', 'when', 'while', 'yield', 'require', 'include', 'attr_accessor', 'attr_reader', 'attr_writer']
            types = ['Array', 'Hash', 'String', 'Integer', 'Float', 'Symbol', 'Proc', 'Lambda', 'File', 'Dir', 'Time', 'Regexp', 'Exception', 'StandardError', 'puts', 'print', 'p', 'raise']
        elif lang == 'css':
            keywords = ['!important', '@media', '@import', '@keyframes', '@font-face', '@supports', 'from', 'to']
            types = ['color', 'background', 'background-color', 'margin', 'padding', 'border', 'border-radius', 'display', 'position', 'top', 'right', 'bottom', 'left', 'width', 'height', 'min-width', 'max-width', 'min-height', 'max-height', 'font', 'font-size', 'font-weight', 'font-family', 'text-align', 'justify-content', 'align-items', 'flex', 'flex-direction', 'grid', 'gap', 'opacity', 'overflow', 'cursor', 'z-index', 'box-shadow', 'transition', 'transform']
        elif lang == 'yaml':
            keywords = ['server', 'location', 'listen', 'server_name', 'root', 'index', 'proxy_pass', 'proxy_set_header', 'fastcgi_pass', 'include', 'try_files', 'return', 'rewrite', 'ssl_certificate', 'ssl_certificate_key', 'upstream', 'http', 'events', 'worker_processes', 'services', 'image', 'container_name', 'ports', 'volumes', 'environment', 'restart', 'networks', 'depends_on', 'build', 'command']

        if keywords:
            kw_flags = re.IGNORECASE if lang == 'sql' else 0
            self.code_rules.append((re.compile(r"\b(?:" + "|".join(keywords) + r")\b", kw_flags), keyword_fmt))
        if types:
            tp_flags = re.IGNORECASE if lang == 'sql' else 0
            self.code_rules.append((re.compile(r"\b(?:" + "|".join(types) + r")\b", tp_flags), type_fmt))

        # 4. Class / Struct / Function Definitions & Calls
        self.code_rules.append((re.compile(r"(?<=\bclass\s)[A-Za-z_][A-Za-z0-9_]*"), class_fmt))
        self.code_rules.append((re.compile(r"(?<=\bstruct\s)[A-Za-z_][A-Za-z0-9_]*"), class_fmt))
        self.code_rules.append((re.compile(r"(?<=\bdef\s)[A-Za-z_][A-Za-z0-9_]*"), func_fmt))
        self.code_rules.append((re.compile(r"(?<=\bfunction\s)[A-Za-z_][A-Za-z0-9_]*"), func_fmt))
        self.code_rules.append((re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\()"), func_fmt))

        # 5. Decorators, Preprocessors, INI Sections, YAML Keys
        if lang in ['python', 'javascript', 'php']:
            self.code_rules.append((re.compile(r"@[A-Za-z_][A-Za-z0-9_\.]*"), dec_fmt))
        if lang == 'c':
            self.code_rules.append((re.compile(r"^\s*#\s*[a-zA-Z_]+"), dec_fmt))
        if lang == 'yaml':
            self.code_rules.append((re.compile(r"^\s*\[[^\]]+\]"), dec_fmt))
            self.code_rules.append((re.compile(r"^\s*[\w\-\.]+(?=\s*[:=])"), attr_fmt))

        # 6. HTML / XML / PHP Tags & Attributes
        if lang in ['html', 'php', 'xml', 'svg']:
            self.code_rules.append((re.compile(r"<\?php|\?>|<\/?[A-Za-z0-9_:\-]+|\/?>"), tag_fmt))
            self.code_rules.append((re.compile(r"\b[A-Za-z_\-][A-Za-z0-9_:\-]*(?=\s*=)"), attr_fmt))

        # 7. Variables ($var,${var}, @ivar)
        if lang in ['php', 'bash', 'yaml']:
            self.code_rules.append((re.compile(r"\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|\$[\d@#\?\!\$\*\-]"), var_fmt))
        elif lang == 'ruby':
            self.code_rules.append((re.compile(r"@{1,2}[A-Za-z_][A-Za-z0-9_]*|\$[A-Za-z0-9_]+"), var_fmt))
        elif lang == 'css':
            self.code_rules.append((re.compile(r"\.[A-Za-z_\-][A-Za-z0-9_\-]*|#[A-Za-z_\-][A-Za-z0-9_\-]*"), class_fmt))

        # 8. Strings (Applied AFTER code rules so keywords inside strings stay string-colored)
        self.string_rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), string_fmt))
        self.string_rules.append((re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), string_fmt))
        if lang in ['javascript', 'bash', 'php', 'sql']:
            self.string_rules.append((re.compile(r"`[^`\\]*(\\.[^`\\]*)*`"), string_fmt))

        # 9. Single-line Comments (Applied LAST so everything inside a comment is muted)
        if lang in ['python', 'bash', 'ruby', 'yaml']:
            self.comment_rules.append((re.compile(r"#[^\n]*"), self.comment_fmt))
        elif lang == 'sql':
            self.comment_rules.append((re.compile(r"--[^\n]*|#[^\n]*"), self.comment_fmt))
        elif lang in ['php']:
            self.comment_rules.append((re.compile(r"//[^\n]*|#[^\n]*"), self.comment_fmt))
        elif lang in ['javascript', 'c', 'css']:
            self.comment_rules.append((re.compile(r"//[^\n]*"), self.comment_fmt))

    def highlightBlock(self, text):
        # Pass 1: Syntax tokens
        for pattern, fmt in self.code_rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)

        # Pass 2: Strings (override keywords/numbers inside quotes)
        for pattern, fmt in self.string_rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)

        # Pass 3: Single-line comments
        for pattern, fmt in self.comment_rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)

        # Pass 4: Multi-line block states (/* ... */, <!-- ... -->, Python """ ... """)
        self.setCurrentBlockState(0)
        if self.lang == 'python':
            if not self._apply_multiline(text, '"""', '"""', 1, self.string_fmt):
                self._apply_multiline(text, "'''", "'''", 2, self.string_fmt)
        elif self.lang in ['html', 'xml']:
            self._apply_multiline(text, "<!--", "-->", 1, self.comment_fmt)
        elif self.lang in ['c', 'javascript', 'php', 'css', 'sql']:
            self._apply_multiline(text, "/*", "*/", 1, self.comment_fmt)

    def _apply_multiline(self, text, start_delim, end_delim, state_id, fmt):
        prev_state = self.previousBlockState()
        if prev_state not in (-1, 0, state_id):
            return False

        start_idx = 0 if prev_state == state_id else text.find(start_delim)
        while start_idx >= 0:
            search_from = start_idx if prev_state == state_id else start_idx + len(start_delim)
            end_idx = text.find(end_delim, search_from)
            if end_idx == -1:
                self.setCurrentBlockState(state_id)
                length = len(text) - start_idx
                self.setFormat(start_idx, length, fmt)
                return True
            else:
                length = end_idx - start_idx + len(end_delim)
                self.setFormat(start_idx, length, fmt)
                prev_state = 0
                start_idx = text.find(start_delim, start_idx + length)
        return self.currentBlockState() == state_id


# ----------------------------------------------------
# MULTI-TAB IDE WORKSPACE WINDOW
# ----------------------------------------------------
class TabbedEditorWorkspace(QMainWindow):
    def __init__(self, initial_theme="dark"):
        super().__init__()
        self.current_theme = initial_theme if initial_theme in EDITOR_THEMES else "dark"
        self.setWindowTitle("Nova Code Workspace")
        self.resize(1180, 820)

        central = QWidget()
        self.main_layout = QVBoxLayout(central)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setCentralWidget(central)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(False)  # We inject explicit custom '✖' buttons on every tab
        self.tabs.setMovable(True)
        self.tabs.currentChanged.connect(self.on_tab_switched)
        self.main_layout.addWidget(self.tabs, 1)

        # Bottom Status Bar
        self.status_bar_widget = QWidget()
        status_layout = QHBoxLayout(self.status_bar_widget)
        status_layout.setContentsMargins(15, 4, 15, 4)

        self.lbl_cursor_pos = QLabel("Ln 1, Col 1")
        self.lbl_line_count = QLabel("Lines: 1")
        self.lbl_encoding = QLabel("UTF-8  |  4 Spaces")

        status_layout.addWidget(self.lbl_cursor_pos)
        status_layout.addSpacing(20)
        status_layout.addWidget(self.lbl_line_count)
        status_layout.addStretch()
        status_layout.addWidget(self.lbl_encoding)
        self.main_layout.addWidget(self.status_bar_widget)

        # Keyboard Shortcuts
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.activated.connect(self.save_current_tab)

        self.shortcut_find = QShortcut(QKeySequence("Ctrl+F"), self)
        self.shortcut_find.activated.connect(self.toggle_find_bar)

        self.shortcut_goto = QShortcut(QKeySequence("Ctrl+G"), self)
        self.shortcut_goto.activated.connect(self.goto_line)

        self.shortcut_close = QShortcut(QKeySequence("Ctrl+W"), self)
        self.shortcut_close.activated.connect(lambda: self.close_tab_widget(self.tabs.currentWidget()))

        self.apply_workspace_theme(self.current_theme)

    def apply_workspace_theme(self, theme_key):
        self.current_theme = theme_key if theme_key in EDITOR_THEMES else "dark"
        t = EDITOR_THEMES[self.current_theme]
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {t['win_bg']};
                color: {t['editor_fg']};
                font-family: 'Segoe UI', Ubuntu, sans-serif;
            }}
            QTabWidget::pane {{
                border: 1px solid {t['border']};
            }}
            QTabBar::tab {{
                background-color: {t['bar_bg']};
                color: {t['gutter_fg']};
                padding: 8px 14px;
                border: 1px solid {t['border']};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {t['editor_bg']};
                color: {t['editor_fg']};
                font-weight: bold;
                border-top: 2px solid {t['accent']};
            }}
            QComboBox, QLineEdit {{
                background-color: {t['win_bg']};
                color: {t['editor_fg']};
                border: 1px solid {t['border']};
                border-radius: 4px;
                padding: 4px 8px;
            }}
        """)
        self.status_bar_widget.setStyleSheet(
            f"background-color: {t['bar_bg']}; border-top: 1px solid {t['border']}; font-family: 'Cascadia Mono', monospace; font-size: 12px;"
        )

        # Update all open tabs
        for i in range(self.tabs.count()):
            c = self.tabs.widget(i)
            c.action_bar.setStyleSheet(f"background-color: {t['bar_bg']}; border-bottom: 1px solid {t['border']};")
            c.find_bar.setStyleSheet(f"background-color: {t['bar_bg']}; border-bottom: 1px solid {t['border']};")
            c.editor.apply_theme(self.current_theme)
            c.editor.highlighter.set_theme_and_lang(self.current_theme, c.lang_combo.currentData())

    def show_styled_msg(self, title, text, is_error=False):
        t = EDITOR_THEMES[self.current_theme]
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(QMessageBox.Icon.Warning if is_error else QMessageBox.Icon.Information)
        msg.setStyleSheet(f"""
            QMessageBox {{ background-color: {t['bar_bg']}; border: 1px solid {t['border']}; }}
            QLabel {{ color: {t['editor_fg']}; font-size: 13px; font-weight: normal; min-width: 260px; padding: 8px; }}
            QPushButton {{ background-color: #2563eb; color: white; border-radius: 4px; padding: 6px 20px; font-weight: bold; min-width: 80px; border: none; }}
            QPushButton:hover {{ background-color: #3b82f6; }}
        """)
        msg.exec()

    def add_file_tab(self, session_tab, filepath, content, is_local=False):
        # Sync initial theme with the session's active theme
        app_theme = session_tab.main_app.app_settings.get("theme", "dark")
        if self.tabs.count() == 0 and app_theme in EDITOR_THEMES:
            self.apply_workspace_theme(app_theme)

        filename = os.path.basename(filepath)
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if getattr(w, 'filepath', '') == filepath and getattr(w, 'is_local', False) == is_local:
                self.tabs.setCurrentIndex(i)
                return

        t = EDITOR_THEMES[self.current_theme]
        container = QWidget()
        container.session_tab = session_tab
        container.filepath = filepath
        container.filename = filename
        container.is_local = is_local
        container.is_dirty = False

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- TOP ACTION & SYNTAX BAR ---
        action_bar = QWidget()
        action_bar.setStyleSheet(f"background-color: {t['bar_bg']}; border-bottom: 1px solid {t['border']};")
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(15, 8, 15, 8)
        action_layout.setSpacing(10)
        container.action_bar = action_bar

        lbl_path = QLabel(f"💻 Local: {filepath}" if is_local else f"🌐 Remote: {filepath}")
        lbl_path.setStyleSheet("font-family: 'Cascadia Mono', monospace; font-size: 12px; font-weight: normal;")

        # Syntax Language Selector
        lang_combo = QComboBox()
        lang_options = [
            ("Auto-Detect", "auto"),
            ("Python", "python"),
            ("PHP", "php"),
            ("Bash / Shell", "bash"),
            ("SQL", "sql"),
            ("HTML / XML", "html"),
            ("JS / TS / JSON", "javascript"),
            ("CSS / SCSS", "css"),
            ("C / C++", "c"),
            ("Ruby", "ruby"),
            ("YAML / Nginx / Conf", "yaml"),
        ]
        for label, code in lang_options:
            lang_combo.addItem(label, code)
        container.lang_combo = lang_combo

        # Theme Selector
        theme_combo = QComboBox()
        theme_keys = ["dark", "dracula", "monokai", "light"]
        for tk in theme_keys:
            theme_combo.addItem(f"🎨 {EDITOR_THEMES[tk]['name']}", tk)
        theme_combo.setCurrentIndex(theme_keys.index(self.current_theme))
        container.theme_combo = theme_combo

        tool_btn_style = "QPushButton { background-color: #27272a; color: #f4f4f5; padding: 5px 12px; border-radius: 4px; font-weight: bold; border: none; } QPushButton:hover { background-color: #3f3f46; }"
        btn_find_toggle = QPushButton("🔍 Find (Ctrl+F)")
        btn_find_toggle.setStyleSheet(tool_btn_style)
        btn_find_toggle.clicked.connect(self.toggle_find_bar)

        btn_goto_line = QPushButton("🔢 Line (Ctrl+G)")
        btn_goto_line.setStyleSheet(tool_btn_style)
        btn_goto_line.clicked.connect(self.goto_line)

        btn_save = QPushButton("💾 Save & Sync (Ctrl+S)")
        btn_save.setStyleSheet("QPushButton { background-color: #059669; color: white; padding: 6px 16px; border-radius: 4px; font-weight: bold; border: none; } QPushButton:hover { background-color: #10b981; }")
        btn_save.clicked.connect(lambda: self.save_tab(container))

        action_layout.addWidget(lbl_path)
        action_layout.addStretch()
        action_layout.addWidget(QLabel("Syntax:"))
        action_layout.addWidget(lang_combo)
        action_layout.addWidget(theme_combo)
        action_layout.addWidget(btn_find_toggle)
        action_layout.addWidget(btn_goto_line)
        action_layout.addWidget(btn_save)

        # --- FIND & REPLACE BAR ---
        find_bar = QWidget()
        find_bar.setStyleSheet(f"background-color: {t['bar_bg']}; border-bottom: 1px solid {t['border']};")
        find_layout = QHBoxLayout(find_bar)
        find_layout.setContentsMargins(15, 6, 15, 6)
        container.find_bar = find_bar

        find_input = QLineEdit()
        find_input.setPlaceholderText("Find...")
        rep_input = QLineEdit()
        rep_input.setPlaceholderText("Replace with...")

        btn_prev = QPushButton("◀ Prev")
        btn_next = QPushButton("Next ▶")
        btn_rep = QPushButton("Replace")
        btn_rep_all = QPushButton("Replace All")
        btn_close_find = QPushButton("✖")

        for b in [btn_prev, btn_next, btn_rep, btn_rep_all]:
            b.setStyleSheet(tool_btn_style)
        btn_close_find.setStyleSheet("QPushButton { background-color: transparent; color: #a1a1aa; font-weight: bold; font-size: 15px; border: none; } QPushButton:hover { color: #ef4444; }")

        find_layout.addWidget(QLabel("Find:"))
        find_layout.addWidget(find_input)
        find_layout.addWidget(btn_prev)
        find_layout.addWidget(btn_next)
        find_layout.addSpacing(15)
        find_layout.addWidget(QLabel("Replace:"))
        find_layout.addWidget(rep_input)
        find_layout.addWidget(btn_rep)
        find_layout.addWidget(btn_rep_all)
        find_layout.addStretch()
        find_layout.addWidget(btn_close_find)
        find_bar.hide()

        container.find_input = find_input
        container.rep_input = rep_input

        # --- CODE EDITOR ---
        editor = CodeEditor(filepath, content, self.current_theme)
        editor.highlighter = EditorSyntaxHighlighter(editor.document(), filename, self.current_theme)
        container.editor = editor

        # Set combo box label to show detected language
        detected_lang = editor.highlighter.lang.upper()
        lang_combo.setItemText(0, f"Auto ({detected_lang})")

        # Wire events
        lang_combo.currentIndexChanged.connect(
            lambda: editor.highlighter.set_theme_and_lang(self.current_theme, lang_combo.currentData())
        )
        theme_combo.currentIndexChanged.connect(
            lambda: self.apply_workspace_theme(theme_combo.currentData())
        )
        btn_next.clicked.connect(lambda: editor.find_text(find_input.text(), True))
        btn_prev.clicked.connect(lambda: editor.find_text(find_input.text(), False))
        btn_rep.clicked.connect(lambda: editor.replace_text(find_input.text(), rep_input.text()))
        btn_rep_all.clicked.connect(lambda: self.do_replace_all(editor, find_input.text(), rep_input.text()))
        btn_close_find.clicked.connect(find_bar.hide)
        find_input.returnPressed.connect(lambda: editor.find_text(find_input.text(), True))

        editor.cursorPositionChanged.connect(lambda: self.update_status_bar(editor))
        editor.textChanged.connect(lambda: self.mark_tab_dirty(container, True))

        layout.addWidget(action_bar)
        layout.addWidget(find_bar)
        layout.addWidget(editor)

        index = self.tabs.addTab(container, filename)
        self.inject_close_button(index, container)
        self.tabs.setCurrentIndex(index)
        self.update_status_bar(editor)

    def inject_close_button(self, index, container):
        btn_close_tab = QPushButton("✖")
        btn_close_tab.setFixedSize(20, 20)
        btn_close_tab.setToolTip("Close Tab (Ctrl+W)")
        btn_close_tab.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #a1a1aa;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: white;
            }
        """)
        btn_close_tab.clicked.connect(lambda: self.close_tab_widget(container))
        self.tabs.tabBar().setTabButton(index, QTabBar.ButtonPosition.RightSide, btn_close_tab)

    def mark_tab_dirty(self, container, dirty=True):
        container.is_dirty = dirty
        idx = self.tabs.indexOf(container)
        if idx >= 0:
            title = f"● {container.filename}" if dirty else container.filename
            self.tabs.setTabText(idx, title)
        self.update_status_bar(container.editor)

    def on_tab_switched(self, index):
        if index >= 0:
            w = self.tabs.widget(index)
            if hasattr(w, 'editor'):
                self.update_status_bar(w.editor)

    def update_status_bar(self, editor):
        cursor = editor.textCursor()
        ln = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        self.lbl_cursor_pos.setText(f"Ln {ln}, Col {col}")
        self.lbl_line_count.setText(f"Lines: {editor.blockCount()}")
        lang = getattr(editor.highlighter, 'lang', 'txt').upper()
        self.lbl_encoding.setText(f"Syntax: {lang}  |  UTF-8  |  4 Spaces")

    def toggle_find_bar(self):
        idx = self.tabs.currentIndex()
        if idx >= 0:
            container = self.tabs.widget(idx)
            if container.find_bar.isVisible():
                container.find_bar.hide()
                container.editor.setFocus()
            else:
                container.find_bar.show()
                container.find_input.setFocus()
                container.find_input.selectAll()

    def goto_line(self):
        idx = self.tabs.currentIndex()
        if idx >= 0:
            t = EDITOR_THEMES[self.current_theme]
            editor = self.tabs.widget(idx).editor
            dialog = QInputDialog(self)
            dialog.setWindowTitle("Go To Line")
            dialog.setLabelText(f"Enter Line Number (1 - {editor.blockCount()}):")
            dialog.setIntRange(1, max(1, editor.blockCount()))
            dialog.setIntValue(editor.textCursor().blockNumber() + 1)
            dialog.setStyleSheet(f"""
                QInputDialog {{ background-color: {t['bar_bg']}; border: 1px solid {t['border']}; min-width: 300px; }}
                QLabel {{ color: {t['editor_fg']}; font-size: 13px; font-weight: bold; }}
                QSpinBox {{ background-color: {t['editor_bg']}; color: {t['editor_fg']}; border: 1px solid {t['border']}; border-radius: 4px; padding: 6px; font-size: 13px; }}
                QPushButton {{ background-color: #2563eb; color: white; border-radius: 4px; padding: 6px 16px; font-weight: bold; min-width: 80px; border: none; }}
                QPushButton:hover {{ background-color: #3b82f6; }}
            """)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                editor.jump_to_line(dialog.intValue())

    def do_replace_all(self, editor, query, replacement):
        if not query:
            return
        count = editor.replace_all(query, replacement)
        self.show_styled_msg("Replace All", f"Successfully replaced {count} occurrences.")

    def close_tab_widget(self, container):
        if not container:
            return
        idx = self.tabs.indexOf(container)
        if idx >= 0:
            self.tabs.removeTab(idx)
        if self.tabs.count() == 0:
            self.close()

    def save_current_tab(self):
        index = self.tabs.currentIndex()
        if index >= 0:
            self.save_tab(self.tabs.widget(index))

    def save_tab(self, container):
        content = container.editor.toPlainText()
        if container.is_local:
            try:
                with open(container.filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.mark_tab_dirty(container, False)
                self.show_styled_msg("Saved", f"Local file saved successfully:\n{container.filepath}")
            except Exception as e:
                self.show_styled_msg("Error", f"Failed to save local file:\n{str(e)}", is_error=True)
        else:
            asyncio.create_task(container.session_tab.write_file_content(container.filepath, content))
            self.mark_tab_dirty(container, False)
            self.show_styled_msg("Saved", f"Remote file uploaded successfully:\n{container.filepath}")


# Retained stub so session_tab.py import doesn't crash
class TextEditorDialog(QMainWindow):
    pass
