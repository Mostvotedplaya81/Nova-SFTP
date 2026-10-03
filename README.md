```markdown
# Nova SFTP

Nova SFTP is a fast, lightweight, and modern desktop SFTP client built natively for Linux. Designed with a clean dark-mode interface, Nova SFTP simplifies remote server management, file transfers, and directory synchronization over secure SSH connections.

---

## Features

- **Dual-Pane Navigation:** Browse local directories alongside remote server filesystems seamlessly.
- **Secure SSH/SFTP Support:** Connect safely using password authentication or SSH key pairs (RSA, Ed25519).
- **Background Transfers:** Queue large file and directory uploads/downloads without freezing the interface.
- **Remote File Management:** Create, rename, edit permissions (`chmod`), and delete files directly on remote machines.
- **Session Bookmarks:** Save frequently accessed servers with port, username, and custom configurations for fast reconnects.
- **Native Desktop Integration:** Full system menu integration with custom application iconography and desktop environment compliance.

---

## Installation

### Ubuntu & Debian (via Launchpad PPA)

Install Nova SFTP and receive automatic updates through the official Launchpad Personal Package Archive:

```bash
# Add the Nova SFTP PPA
sudo add-apt-repository ppa:mostvotedplaya/ppa

# Update local package indexes
sudo apt update

# Install Nova SFTP
sudo apt install nova-sftp

```

To launch the application:

* Search for **Nova SFTP** in your application launcher (Super/Windows key).
* Or run it directly from the terminal:
```bash
nova-sftp

```



---

## Running from Source

If you prefer to run the development version or build the application manually:

### Prerequisites

Ensure you have Python 3.10+ and the required development dependencies installed:

```bash
sudo apt install python3 python3-pip python3-pyqt6

```

### Setup & Launch

1. **Clone the repository:**
```bash
git clone [https://github.com/Mostvotedplaya81/Nova-SFTP.git](https://github.com/Mostvotedplaya81/Nova-SFTP.git)
cd Nova-SFTP

```


2. **Install Python dependencies:**
```bash
pip install -r requirements.txt

```


*(Or install the core libraries manually: `pip install PyQt6 paramiko`)*
3. **Run the application:**
```bash
python3 main.py

```



---

## Packaging & Distribution

This repository contains full Debian packaging rules inside the `debian/` directory. To build source packages for Launchpad or Debian archives locally:

```bash
# Build source package without binary compilation
debuild -S -sa

```

---

## License

This project is licensed under the MIT License — see the [LICENSE](https://www.google.com/search?q=LICENSE) file for details.

```
