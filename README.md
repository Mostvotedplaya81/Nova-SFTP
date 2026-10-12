# Nova SFTP

**Nova SFTP** is a high-performance, purely asynchronous desktop SFTP and SSH client built natively for Linux with **PyQt6**, **asyncssh**, and **qasync**. Designed for system administrators and developers, it combines dual-pane file management, real-time directory synchronization, live log tailing, and an integrated code editor over a single multiplexed SSH tunnel.

---

## What's New in v1.4.0

* **Pure Asynchronous Engine (`qasync` + `asyncssh`):** Completely replaced legacy blocking threads with non-blocking `asyncio` coroutines for zero-latency UI responsiveness during heavy transfers.
* **Multiplexed SSH Tunnels:** File browsing, concurrent transfers, interactive terminal sessions, and live log streams all share a single persistent SSH connection per tab.
* **Dynamic Theme Switcher:** Switch instantly between **Midnight Dark**, **Clean Light**, **Dracula**, and **Monokai** via the toolbar dropdown or Command Palette without restarting.
* **Command Palette (`Ctrl+P`):** Quickly launch bookmarked servers, switch themes, open tabs, or jump directly to Live Logs from the keyboard.
* **Enhanced Code Editor & Quick Look:** Press `Spacebar` on any remote file for an instant syntax-highlighted Quick Look preview, or double-click to open the full editor with line numbers, Find & Replace (with auto-centering viewport), and dynamic text zoom.
* **Live Sync & Directory Comparison:** Watch local directories with `watchdog` to automatically push saved changes in real time, or run full bi-directional directory sync scans.
* **Live Log Tailing & Interactive Terminal:** Stream `syslog`, `auth.log`, `nginx` logs, `journalctl -f`, or `docker logs` directly inside a dedicated tab alongside an embedded interactive shell.

---

## Key Features

* **Multi-Tab Sessions:** Manage multiple remote servers simultaneously in isolated tabs with persistent layout and splitter memory.
* **Secure Authentication:** Connect via password or SSH private keys (with system keyring integration via `keyring`).
* **Concurrent Transfer Queue:** Upload and download files or recursive directories in parallel with real-time progress bars, active queue tab badges, and individual transfer cancellation.
* **Remote Context Actions:** Manage permissions (`chmod` / `chown` with recursive `-R` support), create/rename/delete folders, and compress/extract `.tar.gz` and `.zip` archives directly on the remote host.
* **Colorized File Iconography:** Automatically highlights code files, archives, media, images, and logs with distinct visual accents and human-readable sizes/relative timestamps.

---

## Installation

### Ubuntu & Debian (via Official Launchpad PPA)

Install Nova SFTP and receive automatic updates through the Launchpad Personal Package Archive:

```bash
# Add the Nova SFTP PPA
sudo add-apt-repository ppa:mostvotedplaya/ppa

# Update local package indexes
sudo apt update

# Install Nova SFTP
sudo apt install nova-sftp
To launch the application:Search for Nova SFTP in your system application launcher.Or run it directly from your terminal:Bashnova-sftp
Running from SourcePrerequisitesEnsure you have Python 3.10+ and pip installed on your system:Bashsudo apt install python3 python3-pip python3-pyqt6
Setup & LaunchClone the repository:Bashgit clone [https://github.com/Mostvotedplaya81/Nova-SFTP.git](https://github.com/Mostvotedplaya81/Nova-SFTP.git)
cd Nova-SFTP
Install Python dependencies:(Nova SFTP will automatically check for and install missing Python packages on first run, or you can install them manually):Bashpip install PyQt6 asyncssh qasync keyring watchdog
Run the application:Bashpython3 main.py
Keyboard ShortcutsShortcutActionCtrl + POpen the Command PaletteSpacebarQuick Look preview on selected remote fileEnter (in Editor Find)Jump to next match and center in viewportPackaging & DistributionThis repository contains full Debian packaging rules inside the debian/ directory. To build a signed source package locally for Launchpad:Bashdebuild -S -sd -i -I
LicenseThis project is licensed under the GNU General Public License v3.0 — see the LICENSE file for details.EOF
