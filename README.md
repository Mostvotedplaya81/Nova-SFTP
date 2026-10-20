# Nova SFTP

**Nova SFTP** is a high-performance, purely asynchronous desktop SFTP and SSH client built for **Linux** and **Windows** with **PyQt6**, **asyncssh**, and **qasync**. Designed for system administrators and developers, it combines dual-pane file management, remote-to-remote server bridging, and an advanced graphical Command Center over a single multiplexed SSH tunnel.

---

## 🔥 What's New in v1.5.x (The Modular & Macros Updates)

- **Automated Macros & Snippets:** Write, save, and 1-click execute multi-step deployment scripts directly into the active interactive terminal.
- **Deep Remote Search Engine:** Non-blocking native `find` and `grep` execution for rapid file and content searching across your server.
- **Advanced SSH Key Manager:** Generate Ed25519/RSA keypairs and push public keys to remote servers with a single click.
- **Standalone Command Center:** A completely overhauled, Cura-inspired server telemetry dashboard with live scrolling graphs (CPU, RAM, Swap, Load).
- **Graphical Stack Management:** Manage your server stack natively with dedicated tabs for Top Processes, Docker Containers, and Systemd Services.
- **The SFTP Bridge (Dual-Remote Browser):** Swap the local file browser for a second remote server connection. Drag and drop files between two separate Linux servers seamlessly using in-memory proxying or native `rsync`.
- **Modular Enterprise Architecture:** The massive monolithic codebase has been dismantled into a lightweight `main.py` bootloader with deeply organized `ui/` and `features/` directories.

---

## Key Features

- **Multi-Tab Sessions:** Manage multiple remote servers simultaneously in isolated tabs with persistent layout memory.
- **Smart Auto-Resume:** Automatically detects interrupted file transfers and resumes from the exact byte on reconnect.
- **Secure Authentication:** Connect via password or SSH private keys (with native system keyring integration via `keyring`).
- **Concurrent Transfer Queue:** Upload and download files or recursive directories in parallel with real-time progress bars and individual task cancellation.
- **Live Sync Engine:** Watch local directories with `watchdog` to automatically push saved changes in real time.
- **Live Log Tailing & Interactive Terminal:** Stream `syslog`, `nginx` logs, `journalctl -f`, or `docker logs` directly inside a dedicated tab alongside an embedded interactive shell.
- **Advanced Code Editor:** Integrated text editor with syntax highlighting, find/replace, and font scaling for quick config edits.
- **Spacebar Quick Look:** Press `Spacebar` on any remote file for an instant syntax-highlighted preview.
- **Dynamic Theme Switcher:** Instantly switch between **Midnight Dark**, **Clean Light**, **Dracula**, and **Monokai**.

---

## Installation

### Windows 10 / 11 (Standalone `.exe`)

No installation or Python setup is required on Windows:

1. **[Download `Nova-SFTP.exe` (Latest Release)](https://github.com/Mostvotedplaya81/Nova-SFTP/releases/latest/download/Nova-SFTP.exe)**
2. Double-click **`Nova-SFTP.exe`** to launch.

---

### Ubuntu & Debian (via Official Launchpad PPA)

Install Nova SFTP and receive automatic updates through the Launchpad Personal Package Archive:

```bash
# Add the Nova SFTP PPA
sudo add-apt-repository ppa:mostvotedplaya/ppa

# Update local package indexes
sudo apt update

# Install Nova SFTP
sudo apt install nova-sftp

Running from Source

Ensure you have Python 3.10+ and pip installed on your system.

    Clone the repository:
    Bash

    git clone [https://github.com/Mostvotedplaya81/Nova-SFTP.git](https://github.com/Mostvotedplaya81/Nova-SFTP.git)
    cd Nova-SFTP

    Install Python dependencies:
    (Nova SFTP will automatically check for and install missing packages on first run, or install manually):
    Bash

    pip install PyQt6 asyncssh qasync keyring watchdog

    Run the application:
    Bash

    python3 main.py

Packaging & Distribution

    Linux (Debian / Launchpad PPA): Contains full Debian packaging rules inside debian/. To build a signed source package locally: debuild -S -sa

    Windows (GitHub Actions + PyInstaller): Automatically compiles Nova-SFTP.exe and publishes to GitHub Releases via .github/workflows/windows-build.yml.

License

This project is licensed under the GNU General Public License v3.0 — see the LICENSE file for details.
