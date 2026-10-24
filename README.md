# 🌌 Nova SFTP v1.6.0
**The Ultimate Remote Infrastructure Management Suite for Linux.**

Nova SFTP is a high-performance, asynchronous desktop SFTP client and server administration tool built in Python and PyQt6. It combines lightning-fast file transfers with a full suite of DevOps tools—eliminating the need to juggle separate terminal windows, IDEs, and database clients.

![Nova SFTP Dashboard](https://via.placeholder.com/1000x600.png?text=Nova+SFTP+Screenshot+Placeholder)

## ✨ Flagship Features

* **🌐 The Fleet Matrix:** Monitor your entire server fleet in parallel. View live CPU, RAM, Disk I/O, network bandwidth, and Docker container states across all your nodes in a single dashboard.
* **💻 Multi-Tab Code Workspace:** A built-in, non-blocking IDE. Edit remote `nginx.conf` or `docker-compose.yml` files with full syntax highlighting (Python, PHP, Bash, JSON, C++), multi-pass tokenization, Find/Replace, and native dark themes (Dracula, Monokai, Midnight). 
* **🐳 Visual Docker & Process Manager:** Right-click a `docker-compose.yml` to instantly pull/up/down stacks. View running containers, tail live logs, or send `SIGKILL` to rogue system processes natively.
* **⏰ Visual Cron Task Scheduler:** Parse, pause, edit, and instantly run remote `crontab` jobs without ever typing `crontab -e`.
* **🚇 Zero-Trust SSH Tunnels:** 1-click port forwarding. Securely map remote MariaDB or Portainer ports to your localhost over the encrypted SSH pipeline with persistent saving.
* **🛡️ Disaster Recovery & Backups:** Create instant timestamped `.tar.gz` rollbacks before editing configs, and execute native `rclone` backup scripts from a dedicated UI.
* **🔑 SSH Key Vault & Deployer:** Generate secure `Ed25519` keys locally and push them to any server's `authorized_keys` with a single click (Visual `ssh-copy-id`).
* **📦 Updates & SSL Monitor:** Automatically poll for APT package upgrades and track Let's Encrypt SSL certificate expirations in real-time.
* **🧮 Checksum Verifier:** Right-click any local or remote file to natively calculate and compare MD5 and SHA-256 hashes.
* **🧠 Smart Terminal:** An integrated SSH terminal featuring persistent Up/Down command history, remote path Tab-completion, and a "cd to Active Path" shortcut.

## 🚀 Installation

### Ubuntu / Debian (Recommended)
Download the latest `.deb` package from the [Releases page](https://github.com/yourusername/nova-sftp/releases) and install it:
```bash
sudo apt install ./nova-sftp_1.6.0-1_all.deb

From Source

Requires Python 3.10+ and pip.
Bash

git clone [https://github.com/yourusername/nova-sftp.git](https://github.com/yourusername/nova-sftp.git)
cd nova-sftp
pip3 install -r requirements.txt
python3 main.py

🛠️ Architecture & Tech Stack

    UI Framework: PyQt6 (Qt GUI toolkit)

    SSH/SFTP Engine: asyncssh for deeply multiplexed, non-blocking connections.

    Event Loop: qasync to bridge the Python asyncio loop with the Qt event loop.

    Security: keyring for OS-native credential storage (KWallet/Secret Service).

📄 License

MIT License. See LICENSE for more information.
