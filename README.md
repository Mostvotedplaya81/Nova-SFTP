# Nova SFTP

**Nova SFTP** is a high-performance, purely asynchronous desktop SFTP and SSH client built for **Linux** and **Windows** with **PyQt6**, **asyncssh**, and **qasync**[cite: 1, 2]. Designed for system administrators and developers, it combines dual-pane file management, real-time directory synchronization, live log tailing, and an integrated code editor over a single multiplexed SSH tunnel[cite: 1, 2].

---

## What's New in v1.4.0

* **Pure Asynchronous Engine (`qasync` + `asyncssh`):** Completely replaced legacy blocking threads with non-blocking `asyncio` coroutines for zero-latency UI responsiveness during heavy transfers[cite: 1, 2].
* **Multiplexed SSH Tunnels:** File browsing, concurrent transfers, interactive terminal sessions, and live log streams all share a single persistent SSH connection per tab[cite: 1, 2].
* **Cross-Platform Windows Support:** Now available as a standalone portable `Nova-SFTP.exe` for Windows 10/11 with native Windows Credential Manager integration and drive root (`C:\`, `D:\`) navigation.
* **Dynamic Theme Switcher:** Switch instantly between **Midnight Dark**, **Clean Light**, **Dracula**, and **Monokai** via the toolbar dropdown or Command Palette without restarting[cite: 1, 2].
* **Command Palette (`Ctrl+P`):** Quickly launch bookmarked servers, switch themes, open tabs, or jump directly to Live Logs from the keyboard[cite: 2].
* **Enhanced Code Editor & Quick Look:** Press `Spacebar` on any remote file for an instant syntax-highlighted Quick Look preview, or double-click to open the full editor with line numbers, Find & Replace (with auto-centering viewport), and dynamic text zoom[cite: 2].
* **Live Sync & Directory Comparison:** Watch local directories with `watchdog` to automatically push saved changes in real time, or run full bi-directional directory sync scans[cite: 2].
* **Live Log Tailing & Interactive Terminal:** Stream `syslog`, `auth.log`, `nginx` logs, `journalctl -f`, or `docker logs` directly inside a dedicated tab alongside an embedded interactive shell[cite: 2].

---

## Key Features

* **Multi-Tab Sessions:** Manage multiple remote servers simultaneously in isolated tabs with persistent layout and splitter memory[cite: 1, 2].
* **Secure Authentication:** Connect via password or SSH private keys (with native system keyring integration via `keyring` on both Linux and Windows)[cite: 2].
* **Concurrent Transfer Queue:** Upload and download files or recursive directories in parallel with real-time progress bars, active queue tab badges, and individual transfer cancellation[cite: 1, 2].
* **Remote Context Actions:** Manage permissions (`chmod` / `chown` with recursive `-R` support), create/rename/delete folders, and compress/extract `.tar.gz` and `.zip` archives directly on the remote host[cite: 1, 2].
* **Colorized File Iconography:** Automatically highlights code files, archives, media, images, and logs with distinct visual accents and human-readable sizes/relative timestamps[cite: 1, 2].

---

## Installation

### Windows 10 / 11 (Standalone `.exe`)

No installation or Python setup is required on Windows:

1. **[Download `Nova-SFTP.exe` (Latest Release)](https://github.com/Mostvotedplaya81/Nova-SFTP/releases/latest/download/Nova-SFTP.exe)** *(or browse the [GitHub Releases page](https://github.com/Mostvotedplaya81/Nova-SFTP/releases))*.
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

To launch the application[cite: 1]:
* Search for **Nova SFTP** in your system application launcher[cite: 1].
* Or run it directly from your terminal[cite: 1]:
  ```bash
  nova-sftp
  ```

---

## Running from Source

### Prerequisites

Ensure you have Python 3.10+ and `pip` installed on your system[cite: 1]:

```bash
# Ubuntu / Debian
sudo apt install python3 python3-pip python3-pyqt6
```

### Setup & Launch

1. **Clone the repository[cite: 1]:**
   ```bash
   git clone [https://github.com/Mostvotedplaya81/Nova-SFTP.git](https://github.com/Mostvotedplaya81/Nova-SFTP.git)
   cd Nova-SFTP
   ```

2. **Install Python dependencies[cite: 1, 2]:**
   *(Nova SFTP will automatically check for and install missing Python packages on first run, or you can install them manually)[cite: 2]*:
   ```bash
   pip install PyQt6 asyncssh qasync keyring watchdog
   ```

3. **Run the application[cite: 1]:**
   ```bash
   python3 main.py
   ```

---

## Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| **`Ctrl + P`** | Open the Command Palette[cite: 2] |
| **`Spacebar`** | Quick Look preview on selected remote file[cite: 2] |
| **`Enter`** *(in Editor Find)* | Jump to next match and center in viewport |

---

## Packaging & Distribution

* **Linux (Debian / Launchpad PPA):** Contains full Debian packaging rules inside `debian/`[cite: 1]. To build a signed source package locally[cite: 1]:
  ```bash
  debuild -S -sd -i -I
  ```
* **Windows (GitHub Actions + PyInstaller):** Automatically compiles `Nova-SFTP.exe` and publishes to GitHub Releases via `.github/workflows/windows-build.yml`.

---

## License

This project is licensed under the **GNU General Public License v3.0** — see the [LICENSE](LICENSE) file for details[cite: 1].
