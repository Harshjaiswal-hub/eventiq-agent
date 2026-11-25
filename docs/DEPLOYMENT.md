# EventIQ Agent — Company Production Deployment Manual

## 1. System Requirements

- **Operating System:** Windows Server 2019/2022, Ubuntu 22.04+ LTS, Debian 12, or macOS 13+
- **Python Runtime:** Python 3.10, 3.11, or 3.12 (Python 3.11.9 recommended)
- **Memory:** Minimum 512 MB RAM (1 GB recommended)
- **Disk Space:** 500 MB for application, dependencies, logs, and database snapshots
- **Network:** Port 3000 (configurable via `PORT` environment variable)

---

## 2. Environment Configuration

Copy the template configuration file:
```bash
cp .env.example .env
```

Configure `.env` parameters before launching:

```ini
# Server Settings
PORT=3000
HOST=0.0.0.0
DEBUG=False

# Storage
DATABASE_PATH=./eventiq.db

# Security & CORS
ALLOWED_ORIGINS=https://analytics.yourcompany.com
SECURE_COOKIES=True
SECRET_KEY=generate-with-python-secrets-token-hex-32

# Production Passwords (set before first start)
INITIAL_ADMIN_PASSWORD=ComplexAdminPass2026!
INITIAL_EVALUATOR_PASSWORD=ComplexEvalPass2026!
INITIAL_LEAD_CC_PASSWORD=ComplexCodeCraftPass2026!
INITIAL_LEAD_CN_PASSWORD=ComplexCloudNinePass2026!

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/eventiq.log

# Automated Backup
BACKUP_DIR=./backups
BACKUP_RETAIN=7
```

---

## 3. Production Launch

### Option A: Direct Hardened Multi-Threaded Server (Zero Dependencies)
```bash
python server.py
```
Starts the native threaded HTTP server with structured logging, security headers, WAL mode SQLite, and auto-cleanup.

### Option B: Waitress WSGI Server
```bash
pip install waitress==3.0.0
python run_production.py
```

---

## 4. HTTPS & Reverse Proxy Configuration

In corporate environments, **HTTPS termination must be handled via a reverse proxy** to safeguard session cookies.

### Nginx Configuration (`/etc/nginx/sites-available/eventiq.conf`)

```nginx
server {
    listen 80;
    server_name analytics.yourcompany.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name analytics.yourcompany.com;

    ssl_certificate /etc/ssl/certs/eventiq.crt;
    ssl_certificate_key /etc/ssl/private/eventiq.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 2M;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
```

### Caddyfile (Automatic SSL)
```caddyfile
analytics.yourcompany.com {
    reverse_proxy 127.0.0.1:3000
}
```

---

## 6. Cloud Deployment (Render & Cloudflare)

### Live Production Deployment
- **Official Production URL:** [https://eventiq-agent.onrender.com](https://eventiq-agent.onrender.com)
- **Healthcheck:** [https://eventiq-agent.onrender.com/api/health](https://eventiq-agent.onrender.com/api/health)
- **Deployment Platform:** Render (Free Web Service via `render.yaml`)

### Deploying to Render via Blueprint
1. Connect your GitHub repository (`Harshjaiswal-hub/eventiq-agent`) to Render.
2. Select **Blueprint** and point to `render.yaml`.
3. Set the service name to `eventiq-agent` and deploy.
4. Auto-deploy triggers automatically whenever new commits are pushed to the `main` branch.

### Linux Systemd Service (`/etc/systemd/system/eventiq.service`)
```ini
[Unit]
Description=EventIQ Agent Institutional Analytics
After=network.target

[Service]
Type=simple
User=eventiq
WorkingDirectory=/opt/eventiq
EnvironmentFile=/opt/eventiq/.env
ExecStart=/usr/bin/python3 /opt/eventiq/server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now eventiq
```

### Windows Service
Use NSSM (Non-Sucking Service Manager) or Windows Task Scheduler:
```cmd
nssm install EventIQ "C:\Python311\python.exe" "C:\Users\Admin\Downloads\agentic_ai\server.py"
nssm set EventIQ AppDirectory "C:\Users\Admin\Downloads\agentic_ai"
nssm start EventIQ
```
