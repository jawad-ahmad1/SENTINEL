# 📦 Installation Guide

> **Estimated time:** 15–30 minutes (Docker) · 45–60 minutes (manual)

## System Requirements

### Minimum

| Component | Requirement |
|-----------|-------------|
| CPU | 2 cores |
| RAM | 4 GB |
| Disk | 10 GB SSD |
| OS | Ubuntu 20.04+ / Windows 10+ / macOS 12+ |
| Python | 3.12+ (manual install only) |
| Docker | 24.0+ with Compose v2 (Docker install) |

### Hardware

| Item | Cost | Purpose |
|------|------|---------|
| USB RFID Reader (125kHz EM4100) | ~$6 | Card scanning |
| RFID Cards (EM4100/TK4100) | ~$0.10/card | Employee badges |

→ Full hardware guide: [HARDWARE_SETUP_GUIDE.md](HARDWARE_SETUP_GUIDE.md)

---

## Method 1: Docker (Recommended)

### Prerequisites

- [Docker Desktop](https://docs.docker.com/get-docker/) (includes Compose v2)
- Git

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/jawad-ahmad1/sentinel-attendance.git
cd sentinel-attendance

# 2. Configure environment
cp .env.example .env

# 3. Generate secrets (Linux/macOS)
sed -i "s/CHANGE_ME_generate_with_openssl_rand_hex_32/$(openssl rand -hex 32)/" .env

# 4. Deploy
docker compose up -d --build
```

### Windows

Double-click `run_docker.bat` or run:

```powershell
copy .env.example .env
# Edit .env with your values
docker compose up -d --build
```

### Verify

```bash
# Check all 4 containers are running
docker compose ps

# Expected output:
# NAME                STATUS
# sentinel-app        Up
# sentinel-db         Up
# sentinel-redis      Up
# sentinel-nginx      Up

# Test the API
curl http://localhost/api/v1/health
# → {"status": "healthy", "database": "ok", "redis": "ok"}
```

### Access

| Page | URL |
|------|-----|
| 🖥️ Kiosk | http://localhost |
| 🔐 Admin Login | http://localhost/login.html |
| 📊 Dashboard | http://localhost/admin.html |
| 📖 API Docs | http://localhost/docs |

Login with `DEFAULT_ADMIN_EMAIL` / `DEFAULT_ADMIN_PASSWORD` from your `.env`.

---

## Method 2: Manual Installation

### 1. Install Python 3.12

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip
```

**Windows:**
Download from [python.org](https://www.python.org/downloads/) — check "Add to PATH".

**macOS:**
```bash
brew install python@3.12
```

### 2. Install PostgreSQL 16

**Ubuntu:**
```bash
sudo apt install -y postgresql-16
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql -c "CREATE USER sentinel WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "CREATE DATABASE attendance OWNER sentinel;"
```

**Windows:**
Download from [postgresql.org](https://www.postgresql.org/download/windows/) and run the installer.

### 3. Install Redis 7

**Ubuntu:**
```bash
sudo apt install -y redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**Windows:**
```powershell
# Via WSL2 or Docker
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### 4. Setup Application

```bash
# Clone
git clone https://github.com/jawad-ahmad1/sentinel-attendance.git
cd sentinel-attendance

# Virtual environment
python3.12 -m venv venv
source venv/bin/activate      # Linux/macOS
# .\venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your database credentials
```

### 5. Initialize Database

```bash
# Run Alembic migrations
alembic upgrade head
```

### 6. Start the Server

```bash
# Development
uvicorn app.main:app --reload --port 8000

# Production
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Windows Quick Start

Double-click `run_app.bat` for local development with SQLite.

---

## Method 3: Windows Local Development (SQLite)

For quick local testing without PostgreSQL:

```powershell
# 1. Clone and setup
git clone https://github.com/jawad-ahmad1/sentinel-attendance.git
cd sentinel-attendance

# 2. Run the batch file
.\run_app.bat
```

This starts a local server at http://localhost:8000 using SQLite (no PostgreSQL needed).

---

## Post-Installation

### Verify Everything Works

1. Open http://localhost (or :8000) — kiosk page loads
2. Open http://localhost/login.html — login page loads
3. Login with admin credentials from `.env`
4. Navigate to Dashboard, Employees, Reports
5. Plug in RFID reader → scan a card at the kiosk

### Next Steps

- 📖 Read the [User Guide](USER_GUIDE.md) for daily operations
- ⚙️ Read [CONFIGURATION.md](CONFIGURATION.md) for tuning
- 🚀 Read [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for production setup
- 🔌 Read [HARDWARE_SETUP_GUIDE.md](HARDWARE_SETUP_GUIDE.md) for RFID setup

---

## Troubleshooting Installation

<details>
<summary><strong>Docker: "port 80 already in use"</strong></summary>

Stop the conflicting service:
```bash
sudo lsof -i :80
sudo systemctl stop apache2  # or nginx
```

Or change the port in `docker-compose.yml`:
```yaml
ports:
  - "8080:80"  # Use port 8080 instead
```
</details>

<details>
<summary><strong>Python: "ModuleNotFoundError"</strong></summary>

Ensure your virtual environment is activated:
```bash
source venv/bin/activate
pip install -r requirements.txt
```
</details>

<details>
<summary><strong>PostgreSQL: "connection refused"</strong></summary>

Check PostgreSQL is running:
```bash
sudo systemctl status postgresql
sudo systemctl start postgresql
```

Verify `DATABASE_URL` in `.env` matches your credentials.
</details>

<details>
<summary><strong>Redis: "Connection refused"</strong></summary>

Start Redis:
```bash
sudo systemctl start redis
# or
docker run -d --name redis -p 6379:6379 redis:7-alpine
```
</details>

---

[← Back to README](README.md)
