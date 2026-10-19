import sys
import os
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

# FORCE QASYNC TO BIND TO PYQT6 BEFORE ANY QT IMPORTS
os.environ["QT_API"] = "pyqt6"

import qasync
from PyQt6.QtWidgets import QApplication
from ui.main_window import NovaSFTP

if __name__ == "__main__":
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("litenova.novasftp.client.1.6")

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
