# Installation & Setup Guide

> Covers **macOS (Apple Silicon)**, **Ubuntu/Debian Linux**, and **Windows 10/11 (WSL 2)**.

---

## 1 · Clone repository

```bash
# choose a workspace folder
$ git clone https://github.com/your-org/secure-ftp-client.git
$ cd secure-ftp-client
```

---

## 2 · Python environment

Create and activate a virtual environment (recommended for all OS).

| OS                                        | Commands   |
| ----------------------------------------- | ---------- |
| **macOS & Linux**                         | \`\`\`bash |
| \$ python3 -m venv venv                   |            |
| \$ source venv/bin/activate               |            |
| (venv) \$ pip install --upgrade pip       |            |
| (venv) \$ pip install -r requirements.txt |            |

````|
| **Windows (cmd / PowerShell)** | ```powershell
> py -3 -m venv venv
> venv\Scripts\activate
(venv) > python -m pip install -r requirements.txt
``` |

---
## 3 · Install & configure ClamAV
### 3.1 macOS (Apple Silicon / Intel)
```bash
# Homebrew install
(venv) $ brew install clamav
# copy default configs ONCE
(venv) $ sudo cp $(brew --prefix)/etc/clamav/*sample $(brew --prefix)/etc/clamav/
# edit: comment‑out “Example” line in both files
(venv) $ sudo nano /opt/homebrew/etc/clamav/freshclam.conf
(venv) $ sudo nano /opt/homebrew/etc/clamav/clamd.conf
# update virus DB & launch clamd as a service
(venv) $ sudo freshclam
(venv) $ sudo brew services start clamav
````

### 3.2 Ubuntu / Debian

```bash
# packages
$ sudo apt update && sudo apt install clamav clamav-daemon -y
# first DB update (can take a while)
$ sudo systemctl stop clamav-freshclam
$ sudo freshclam
$ sudo systemctl start clamav-daemon
```

The UNIX‑socket path is usually `/var/run/clamav/clamd.ctl`.

### 3.3 Windows 10/11 (WSL 2 preferred)

1. Enable **WSL 2** and install Ubuntu from Microsoft Store.
2. Inside WSL:

```bash
$ sudo apt update && sudo apt install clamav clamav-daemon -y
$ sudo freshclam && sudo service clamav-daemon start
```

3. Expose the agent port to Windows if you plan to run the client outside WSL (e.g. `localhost:9000`).

> **Tip:** Use `sudo lsof -U | grep clamd` to confirm the socket path.

---

## 4 · Start core services

### 4.1 ClamAVAgent

```bash
(venv) $ python -m clamav_agent.server \
            --host 0.0.0.0 \
            --port 9000 \
            --clamd-socket /var/run/clamav/clamd.ctl  # adapt if different
```

You can override host/port later with env vars `CLAMAV_AGENT_HOST` / `PORT`.

### 4.2 Local FTP server (for testing)

```bash
(venv) $ mkdir /tmp/ftp_root && cd /tmp/ftp_root
(venv) $ python -m pyftpdlib -w \
           -u ftpuser -P password123 \
           -p 2121
```

For production you may use **vsftpd**, **ProFTPD**, or **FileZilla Server** – just ensure the credentials and passive ports match.

---

## 5 · Run the client

```bash
(venv) $ python -m ftp_client \
            --host localhost --port 2121 \
            --user ftpuser  --pass password123
```

If the agent listens on a remote host or custom port:

```bash
$ export CLAMAV_AGENT_HOST=192.168.1.50
$ export CLAMAV_AGENT_PORT=9000
```

---

## 6 · Troubleshooting

| Symptom                                          | Checklist                                                                |
| ------------------------------------------------ | ------------------------------------------------------------------------ |
| `socket.timeout` on connect                      | *Server up? Port 21/2121 reachable?* Use `nc -vz host 21`.               |
| `INFECTED` for EICAR but clean files skipped too | FreshClam DB outdated? `sudo freshclam` then restart `clamd`.            |
| `ERROR` from agent                               | Confirm the socket path in `clamd.conf` matches `--clamd-socket`.        |
| Passive data connection hangs                    | Open passive port range in firewall; or run client & server on same LAN. |

---

Happy hacking! Feel free to open issues or PRs if you hit setup problems on other distributions.
