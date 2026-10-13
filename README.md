# Nova SFTP

**Nova SFTP** is a high-performance, purely asynchronous desktop SFTP and SSH client built for **Linux** and **Windows** with **PyQt6**, **asyncssh**, and **qasync**. Designed for system administrators and developers, it combines dual-pane file management, real-time directory synchronization, live log tailing, and an integrated code editor over a single multiplexed SSH tunnel.

---

## What's New in v1.4.0-3

* **Smart Auto-Resume:** Automatically detects interrupted file transfers and resumes from the exact byte on reconnect, saving massive amounts of time on large uploads/downloads.
* **System Tray Integration:** Close the main window to minimize Nova SFTP to the system tray, allowing the Live Sync engine to push folder updates silently in the background.
* **Enhanced Bookmarks:** Save custom SSH ports and securely toggle password visibility directly from the Sidebar.
* **Cross-Platform Windows Support:** Available as a standalone portable `Nova-SFTP.exe` for Windows 10/11 with native Windows Credential Manager integration.
* **Pure Asynchronous Engine:** Replaced legacy blocking threads with non-blocking `asyncio` coroutines for zero-latency UI responsiveness during heavy transfers.
* **Multiplexed SSH Tunnels:** File browsing, concurrent transfers, interactive terminal sessions, and live log streams all share a single persistent SSH connection per tab.
* **Dynamic Theme Switcher:** Switch instantly between **Midnight Dark**, **Clean Light**, **Dracula**, and **Monokai** via the toolbar dropdown or Command Palette.
* **Spacebar Quick Look:** Press `Spacebar` on any remote file for an instant syntax-highlighted preview.

---

## Key Features

* **Multi-Tab Sessions:** Manage multiple remote servers simultaneously in isolated tabs with persistent layout and splitter memory.
* **Secure Authentication:** Connect via password or SSH private keys (with native system keyring integration via `keyring` on both Linux and Windows).
* **Concurrent Transfer Queue:** Upload and download files or recursive directories in parallel with real-time progress bars, active queue tab badges, and individual transfer cancellation.
* **Live Sync & Directory Comparison:** Watch local directories with `watchdog` to automatically push saved changes in real time, or run full bi-directional directory sync scans.
* **Live Log Tailing & Interactive Terminal:** Stream `syslog`, `auth.log`, `nginx` logs, `journalctl -f`, or `docker logs` directly inside a dedicated tab alongside an embedded interactive shell.
* **Remote Context Actions:** Manage permissions (`chmod` / `chown` with recursive `-R` support), create/rename/delete folders, and compress/extract `.tar.gz` and `.zip` archives directly on the remote host.
* **Colorized File Iconography:** Automatically highlights code files, archives, media, images, and logs with distinct visual accents.

---

## Installation

### Windows 10 / 11 (Standalone `.exe`)

No installation or Python setup is required on Windows:

1. **[Download `Nova-SFTP.exe` (Latest Release)](https://github.com/Mostvotedplaya81/Nova-SFTP/releases/latest/download/Nova-SFTP.exe)**
2. Double-click **`Nova-SFTP.exe`** to launch.
   * *(Note: If Windows Defender SmartScreen prompts "Windows protected your PC" on first launch, click **More info** -> **Run anyway**).*

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
```

---

## Running from Source

Ensure you have Python 3.10+ and `pip` installed on your system.

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Mostvotedplaya81/Nova-SFTP.git](https://github.com/Mostvotedplaya81/Nova-SFTP.git)
   cd Nova-SFTP
   ```

2. **Install Python dependencies:**
   *(Nova SFTP will automatically check for and install missing packages on first run, or install manually)*:
   ```bash
   pip install PyQt6 asyncssh qasync keyring watchdog
   ```

3. **Run the application:**
   ```bash
   python3 main.py
   ```

---

## Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| **`Ctrl + P`** | Open the Command Palette |
| **`Spacebar`** | Quick Look preview on selected remote file |
| **`Enter`** *(in Editor Find)* | Jump to next match and center in viewport |

---

## Packaging & Distribution

* **Linux (Debian / Launchpad PPA):** Contains full Debian packaging rules inside `debian/`. To build a signed source package locally: `debuild -S -sd -i -I`
* **Windows (GitHub Actions + PyInstaller):** Automatically compiles `Nova-SFTP.exe` and publishes to GitHub Releases via `.github/workflows/windows-build.yml`.

---

## License

This project is licensed under the **GNU General Public License v3.0** — see the [LICENSE](LICENSE) file for details.
