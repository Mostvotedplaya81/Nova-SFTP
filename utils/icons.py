import os
from PyQt6.QtWidgets import QStyle
from PyQt6.QtGui import QIcon, QPainter, QColor

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
