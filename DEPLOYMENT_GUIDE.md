# Sentinel RFID Attendance System — Enterprise Deployment Guide

**Version:** 2.1.0 | **Stack:** Docker Compose · FastAPI · PostgreSQL 16 · Redis 7 · Nginx  
**Timeline:** Code → Production in 5 business days

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase 1: Pre-Deployment Preparation (Day 1)](#phase-1-pre-deployment-preparation-day-1)
3. [Phase 2: Infrastructure & Deployment (Day 2–3)](#phase-2-infrastructure--deployment-day-23)
4. [Phase 3: Testing & Validation (Day 4)](#phase-3-testing--validation-day-4)
5. [Phase 4: Go-Live (Day 5)](#phase-4-go-live-day-5)
6. [Phase 5: Post-Deployment (Ongoing)](#phase-5-post-deployment-ongoing)
7. [Rollback Plan](#rollback-plan)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Production Server** | 2 CPU, 4 GB RAM, 50 GB SSD | 4 CPU, 8 GB RAM, 100 GB SSD |
| **RFID Readers** | Any USB HID keyboard-emulation reader | ACR122U, RD200, or equivalent |
| **Kiosk Terminal** | Any device with a modern browser | Dedicated tablet/touchscreen + USB reader |

> [!NOTE]
> The RFID reader must operate in **keyboard-emulation (HID) mode**. The kiosk frontend captures
> scans via a hidden input field — no serial drivers, no special libraries required.

### Software Requirements

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Docker Engine | ≥ 24.0 | Container runtime |
| Docker Compose | ≥ 2.20 (v2 plugin) | Service orchestration |
| Git | Any | Source code retrieval |
| OpenSSL | Any | Secret key generation |
| Domain + DNS | — | `attendance.company.com` → server IP |
| SSL Certificate | — | Let's Encrypt or commercial |

### Network Requirements

| Port | Protocol | Purpose |
|------|----------|---------|
| 22 | TCP | SSH administration |
| 80 | TCP | HTTP → HTTPS redirect |
| 443 | TCP | HTTPS (Nginx terminates TLS) |

> [!IMPORTANT]
> Ports 5432 (PostgreSQL) and 6379 (Redis) must **NOT** be exposed externally.
> Docker Compose already binds them to `127.0.0.1` only.

---

## Phase 1: Pre-Deployment Preparation (Day 1)

### Step 1 — Provision the Server

```bash
# Ubuntu 22.04 LTS / Debian 12 recommended
sudo apt update && sudo apt upgrade -y
sudo hostnamectl set-hostname sentinel-attendance

# Install Docker Engine
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose v2 (included with modern Docker)
docker compose version  # verify ≥ 2.20

# Install supporting tools
sudo apt install -y git curl ufw htop
```

### Step 2 — Configure Firewall

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP redirect
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
sudo ufw status
```

### Step 3 — Obtain SSL Certificate

**Option A: Let's Encrypt (free, recommended)**

```bash
# Install certbot standalone (runs before Nginx starts)
sudo apt install -y certbot

# Obtain certificate (server must be reachable on port 80)
sudo certbot certonly --standalone -d attendance.company.com

# Certificates saved to:
#   /etc/letsencrypt/live/attendance.company.com/fullchain.pem
#   /etc/letsencrypt/live/attendance.company.com/privkey.pem

# Auto-renewal (certbot installs a systemd timer automatically)
sudo certbot renew --dry-run
```

**Option B: Commercial certificate**

```bash
sudo mkdir -p /etc/ssl/sentinel
sudo cp fullchain.pem /etc/ssl/sentinel/
sudo cp privkey.pem /etc/ssl/sentinel/
sudo chmod 600 /etc/ssl/sentinel/privkey.pem
```

### Step 4 — Clone the Repository

```bash
cd /opt
sudo git clone https://github.com/yourcompany/sentinel-attendance.git attendance
sudo chown -R $USER:$USER /opt/attendance
cd /opt/attendance
```

### Step 5 — Create the Production `.env` File

```bash
cp .env.example .env
nano .env
```

Fill in all values — see the [Environment Variables](#environment-variables) reference below.

```bash
# Generate cryptographic secrets
openssl rand -hex 32   # → paste as SECRET_KEY
openssl rand -hex 32   # → paste as POSTGRES_PASSWORD

# Lock down permissions
chmod 600 .env
```

### Environment Variables

| Variable | Example Value | Description |
|----------|--------------|-------------|
| `POSTGRES_USER` | `sentinel` | Database username |
| `POSTGRES_PASSWORD` | `<generated-hex-32>` | Database password (**change this**) |
| `POSTGRES_DB` | `attendance` | Database name |
| `DATABASE_URL` | `postgresql+asyncpg://sentinel:<pw>@db:5432/attendance` | SQLAlchemy async URL |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `SECRET_KEY` | `<generated-hex-32>` | JWT signing key (**change this**) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | JWT refresh token lifetime |
| `BOUNCE_WINDOW_SECONDS` | `2` | Anti-double-tap threshold |
| `COOKIE_SECURE` | `true` | Set `true` for HTTPS production |
| `CORS_ORIGINS` | `["https://attendance.company.com"]` | Allowed origins (JSON array) |
| `DEFAULT_ADMIN_EMAIL` | `admin@company.com` | Auto-seeded admin email |
| `DEFAULT_ADMIN_PASSWORD` | `<strong-password>` | Auto-seeded admin password (**change this**) |

> [!CAUTION]
> Never commit the `.env` file to version control. The `.gitignore` excludes it by default.
> The Dockerfile is designed to **not** copy `.env` into the image — it is injected at runtime
> via `env_file` in `docker-compose.yml`.

---

## Phase 2: Infrastructure & Deployment (Day 2–3)

### Step 6 — Configure Nginx for TLS Termination

Edit `nginx/nginx.conf` to add an HTTPS server block. The existing config handles HTTP on port 80. For production, add TLS:

```bash
nano nginx/nginx.conf
```

Add this **above** the existing `server` block:

```nginx
server {
    listen 443 ssl http2;
    server_name attendance.company.com;

    ssl_certificate     /etc/letsencrypt/live/attendance.company.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/attendance.company.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # --- Copy all location blocks from the port-80 server block ---
    # (rate limiting, static files, proxy_pass, etc.)
}
```

Mount the certificate directory in `docker-compose.yml` under the `nginx` service:

```yaml
nginx:
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./frontend:/usr/share/nginx/html:ro
    - /etc/letsencrypt:/etc/letsencrypt:ro   # <-- add this line
  ports:
    - "80:80"
    - "443:443"   # <-- add this port
```

### Step 7 — Deploy with Docker Compose

```bash
cd /opt/attendance

# Build and start all services in detached mode
docker compose up -d --build

# Expected output:
#  ✔ Network attendance_system_default  Created
#  ✔ Container attendance_system-db-1   Healthy
#  ✔ Container attendance_system-redis-1 Healthy
#  ✔ Container attendance_system-app-1  Healthy
#  ✔ Container attendance_system-nginx-1 Started
```

### Step 8 — Verify All Services

```bash
# Check all containers are healthy
docker compose ps

# Expected:
# NAME           STATUS              PORTS
# db             running (healthy)   127.0.0.1:5432->5432/tcp
# redis          running (healthy)   127.0.0.1:6379->6379/tcp
# app            running (healthy)   127.0.0.1:8000->8000/tcp
# nginx          running             0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp

# Check application logs
docker compose logs app --tail 50

# Look for:
#   "Application startup complete"
#   "Admin user seeded: admin@company.com"
#   "Tables created"

# Test health endpoint directly
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
# Expected: {"db": true, "redis": true}

# Test via Nginx
curl -s https://attendance.company.com/api/v1/health | python3 -m json.tool
```

### Step 9 — Verify Database Initialization

```bash
# Connect to PostgreSQL
docker compose exec db psql -U sentinel -d attendance

# Check tables exist
\dt

# Expected:
#  Schema |    Name     | Type  |  Owner
# --------+-------------+-------+---------
#  public | attendance  | table | sentinel
#  public | employees   | table | sentinel
#  public | users       | table | sentinel

# Check admin user was seeded
SELECT id, email, role, is_active FROM users;

# Exit
\q
```

---

## Phase 3: Testing & Validation (Day 4)

### Step 10 — Smoke Test

| Test | Command / Action | Expected Result |
|------|-----------------|-----------------|
| Kiosk page loads | Open `https://attendance.company.com` | Kiosk UI with scan ring and clock |
| Health check | `curl https://attendance.company.com/api/v1/health` | `{"db": true, "redis": true}` |
| Admin login | Navigate to `/login.html`, login with admin creds | Redirects to `/admin.html` dashboard |
| API docs | Navigate to `/docs` | Swagger UI with all 21 endpoints |
| RFID scan | Tap card on kiosk page | "Welcome Employee-XXXX" or registered name |

### Step 11 — Run Automated Test Suite

```bash
# Install test dependencies locally (or run inside container)
docker compose exec app pip install aiosqlite

# Run tests
docker compose exec app python -m pytest tests/ -v --tb=short

# Expected: 32 tests passed
#   test_scan.py         - 5 passed
#   test_employees.py    - 8 passed
#   test_breaks.py       - 5 passed
#   test_reports.py      - 9 passed
#   test_omega_fuzzer.py - 3 passed (250+ fuzz payloads)
#   test_security_hardened.py - 2 passed
```

### Step 12 — End-to-End Workflow Test

Execute these workflows manually to verify the complete system:

**Workflow 1: New Employee Onboarding**
1. Login as admin → Navigate to Registration page
2. Enter employee name, RFID UID, department → Submit
3. Go to kiosk → Scan the employee's card
4. Verify: "Welcome [Name]" appears, event = IN
5. Scan again → Verify event toggles to OUT
6. Check Reports → Daily summary shows the employee ✅

**Workflow 2: Full Day Cycle**
1. Scan card → IN
2. Hit Break Start → BREAK_START recorded
3. Hit Break End → BREAK_END recorded
4. Scan card → OUT
5. Check daily summary → Work hours minus break time ✅

**Workflow 3: Reports & Export**
1. Navigate to Reports → Daily tab → Select today
2. Verify employee list with work hours
3. Click "Export CSV" → Download opens correctly
4. Navigate to Monthly tab → Verify `total_working_days` excludes weekends ✅

### Step 13 — Load Test

```bash
# Install wrk
sudo apt install -y wrk

# Test kiosk page (static file via Nginx)
wrk -t4 -c100 -d30s https://attendance.company.com/
# Target: > 1000 req/sec, 0 errors

# Test API health endpoint
wrk -t4 -c50 -d30s https://attendance.company.com/api/v1/health
# Target: > 500 req/sec, avg latency < 100ms

# Test scan endpoint (write load)
wrk -t2 -c10 -d10s -s scan_bench.lua https://attendance.company.com/api/v1/scan
# Where scan_bench.lua contains:
#   wrk.method = "POST"
#   wrk.body   = '{"uid":"BENCH-001"}'
#   wrk.headers["Content-Type"] = "application/json"
```

### Step 14 — Security Validation

```bash
# SSL grade check
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=attendance.company.com
# Target: Grade A or A+

# Test rate limiting (login endpoint: 5 req/min)
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST https://attendance.company.com/api/v1/auth/login \
    -d "username=test&password=test"
done
# Expected: First 5 return 401, remaining return 429 (Too Many Requests)

# Test XSS rejection
curl -s -X POST https://attendance.company.com/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{"uid":"<script>alert(1)</script>"}'
# Expected: 422 (validation error, regex rejects special chars)

# Test SQL injection rejection
curl -s -X POST https://attendance.company.com/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{"uid":"'\'' OR 1=1 --"}'
# Expected: 422 (validation error)

# Verify HttpOnly cookies
curl -v -X POST https://attendance.company.com/api/v1/auth/login \
  -d "username=admin@company.com&password=yourpassword" 2>&1 | grep -i set-cookie
# Expected: HttpOnly; Secure; SameSite=Lax
```

---

## Phase 4: Go-Live (Day 5)

### Step 15 — Pre-Go-Live Checklist

```
Infrastructure:
[  ] All 4 Docker containers show "healthy" status
[  ] SSL certificate valid (check expiry date)
[  ] Firewall only allows ports 22, 80, 443
[  ] PostgreSQL and Redis NOT exposed externally
[  ] .env file has production secrets (not defaults)
[  ] COOKIE_SECURE=true
[  ] CORS_ORIGINS set to production domain only

Functionality:
[  ] Kiosk page loads < 3 seconds
[  ] Admin login works with production credentials
[  ] RFID scan records attendance correctly
[  ] IN/OUT toggle works for consecutive scans
[  ] Break start/end records correctly
[  ] Daily report shows accurate data
[  ] Monthly report shows correct working days
[  ] CSV export downloads correctly
[  ] Employee CRUD works (create/edit/delete)

Security:
[  ] SSL Labs grade ≥ A
[  ] Rate limiting active (login: 5/min, API: 100/min)
[  ] No stack traces leaked on errors
[  ] HttpOnly + Secure cookies confirmed
[  ] Default SECRET_KEY replaced
[  ] Default admin password changed

Operations:
[  ] Automated backups configured
[  ] Container auto-restart enabled (restart: unless-stopped)
[  ] Log rotation configured
[  ] Monitoring alerts set up
[  ] Rollback plan documented and tested
```

### Step 16 — Go-Live Execution

```bash
# Final restart to ensure clean state
docker compose down
docker compose up -d --build

# Monitor logs in real-time during go-live
docker compose logs -f --tail 100
```

**Go-Live Day Schedule:**

| Time | Action |
|------|--------|
| 08:00 | Final system verification, all containers healthy |
| 08:30 | Announce go-live to staff (email, signage at kiosks) |
| 09:00 | First employee scans — monitor logs and DB for correct records |
| 10:00 | First-hour review: count successful scans, note any issues |
| 12:00 | Lunch rush — monitor performance under higher load |
| 13:00 | Generate first daily report, verify data accuracy |
| 17:00 | End-of-day report, review with management |
| 18:00 | Post-go-live team debrief, document lessons learned |

---

## Phase 5: Post-Deployment (Ongoing)

### Automated Backups

Create `/opt/attendance/scripts/backup.sh`:

```bash
#!/bin/bash
# Sentinel Attendance System — Automated Backup
set -euo pipefail

BACKUP_DIR="/opt/attendance/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# Backup PostgreSQL database
docker compose -f /opt/attendance/docker-compose.yml exec -T db \
  pg_dump -U sentinel attendance | gzip > "$BACKUP_DIR/db_${DATE}.sql.gz"

# Backup .env and nginx config
tar -czf "$BACKUP_DIR/config_${DATE}.tar.gz" \
  /opt/attendance/.env \
  /opt/attendance/nginx/nginx.conf \
  /opt/attendance/docker-compose.yml

# Prune old backups
find "$BACKUP_DIR" -name "*.gz" -type f -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] Backup completed: db_${DATE}.sql.gz"
```

```bash
chmod +x /opt/attendance/scripts/backup.sh

# Add to crontab — daily at 02:00
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/attendance/scripts/backup.sh >> /var/log/sentinel-backup.log 2>&1") | crontab -
```

### Monitoring

Create `/opt/attendance/scripts/monitor.sh`:

```bash
#!/bin/bash
# Sentinel Attendance System — Health Monitor
ALERT_EMAIL="admin@company.com"

# Check all containers are running
for svc in db redis app nginx; do
  if ! docker compose -f /opt/attendance/docker-compose.yml ps "$svc" --format json | grep -q '"running"'; then
    echo "ALERT: $svc is down!" | mail -s "Sentinel: $svc DOWN" "$ALERT_EMAIL"
  fi
done

# Check health endpoint
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health)
if [ "$HTTP_CODE" != "200" ]; then
  echo "ALERT: Health endpoint returned $HTTP_CODE" | mail -s "Sentinel: Health Check Failed" "$ALERT_EMAIL"
fi

# Check disk space
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 85 ]; then
  echo "ALERT: Disk usage at ${DISK_USAGE}%" | mail -s "Sentinel: Disk Space Warning" "$ALERT_EMAIL"
fi
```

```bash
chmod +x /opt/attendance/scripts/monitor.sh

# Run every 5 minutes
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/attendance/scripts/monitor.sh") | crontab -
```

### SSL Certificate Renewal

```bash
# Let's Encrypt auto-renews via systemd timer
# Verify timer is active:
sudo systemctl list-timers | grep certbot

# Manual renewal (if needed):
sudo certbot renew

# After renewal, reload Nginx to pick up new certs:
docker compose restart nginx
```

### Log Management

```bash
# View application logs
docker compose logs app --tail 100

# View Nginx access/error logs
docker compose logs nginx --tail 100

# Docker handles log rotation automatically via json-file driver
# To configure max log size, add to docker-compose.yml service:
#   logging:
#     driver: json-file
#     options:
#       max-size: "10m"
#       max-file: "5"
```

### Maintenance Tasks

| Frequency | Task | Command |
|-----------|------|---------|
| **Daily** | Check container health | `docker compose ps` |
| **Daily** | Review error logs | `docker compose logs app --since 24h \| grep ERROR` |
| **Weekly** | Verify backup integrity | Restore latest backup to test DB |
| **Weekly** | Check disk space | `df -h` |
| **Monthly** | Apply OS security updates | `sudo apt update && sudo apt upgrade` |
| **Monthly** | Rebuild containers (pick up base image patches) | `docker compose build --pull && docker compose up -d` |
| **Monthly** | Check SSL certificate expiry | `sudo certbot certificates` |
| **Quarterly** | Rotate `SECRET_KEY` (invalidates all JWTs) | Update `.env`, restart app |
| **Quarterly** | Review and rotate admin password | Update via admin panel |

### Updating the Application

```bash
cd /opt/attendance

# Pull latest code
git pull origin main

# Rebuild and restart (zero-downtime with health checks)
docker compose up -d --build

# Verify health
docker compose ps
curl -s http://localhost:8000/api/v1/health
```

---

## Rollback Plan

### If Deployment Fails

```bash
# Stop all services
docker compose down

# Restore previous code version
git checkout <previous-commit-hash>

# Rebuild and start
docker compose up -d --build
```

### If Database Migration Fails

```bash
# Stop the app (keep DB running)
docker compose stop app nginx

# Restore database from backup
gunzip < /opt/attendance/backups/db_LATEST.sql.gz | \
  docker compose exec -T db psql -U sentinel -d attendance

# Restart app
docker compose up -d app nginx
```

### If Environment is Corrupted

```bash
# Nuclear reset: destroy everything and rebuild
docker compose down -v   # WARNING: -v deletes database volume

# Restore .env from backup
cp /opt/attendance/backups/config_LATEST/.env /opt/attendance/.env

# Rebuild from scratch
docker compose up -d --build

# Restore database
gunzip < /opt/attendance/backups/db_LATEST.sql.gz | \
  docker compose exec -T db psql -U sentinel -d attendance
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs for the failing container
docker compose logs <service> --tail 50

# Common causes:
# db:    POSTGRES_PASSWORD not set in .env
# app:   DATABASE_URL malformed, missing dependency
# redis: Port conflict with host Redis
# nginx: Config syntax error → docker compose logs nginx
```

### Database Connection Refused

```bash
# Check if DB is healthy
docker compose ps db

# Check DB logs
docker compose logs db --tail 20

# Verify DATABASE_URL matches docker-compose service name
# Must be: postgresql+asyncpg://user:pass@db:5432/dbname
# NOT:     postgresql+asyncpg://user:pass@localhost:5432/dbname
```

### RFID Scanner Not Working

| Symptom | Cause | Fix |
|---------|-------|-----|
| No response on scan | Browser tab not focused | Click on the kiosk page first |
| Card ID shows in URL bar | Scanner in wrong mode | Switch scanner to HID keyboard mode |
| "Employee not found" on break | Employee not registered | Register via admin panel or scan once on kiosk |
| Same event repeated | Bounce window too short | Increase `BOUNCE_WINDOW_SECONDS` in `.env` |

### Performance Issues

```bash
# Check container resource usage
docker stats

# Check PostgreSQL slow queries
docker compose exec db psql -U sentinel -d attendance \
  -c "SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Check connection pool status
docker compose logs app | grep -i "pool"

# If Redis is not connecting (non-critical — system works without it):
docker compose exec redis redis-cli ping
# Expected: PONG
```

### 502 Bad Gateway from Nginx

```bash
# App container is probably unhealthy or restarting
docker compose ps app
docker compose logs app --tail 30

# Restart app
docker compose restart app

# If persistent, check if port 8000 is blocked:
docker compose exec nginx curl -s http://app:8000/api/v1/health
```

---

## Architecture Reference

```
┌──────────────────────────────────────────────────────┐
│                    INTERNET                          │
│              (HTTPS :443 only)                       │
└────────────────────┬─────────────────────────────────┘
                     │
              ┌──────▼──────┐
              │    Nginx    │  Rate limiting, TLS termination,
              │  (Alpine)   │  static file serving (/frontend)
              └──────┬──────┘
                     │ proxy_pass :8000
              ┌──────▼──────┐
              │   FastAPI   │  Gunicorn + 4 Uvicorn workers
              │  (Py 3.12)  │  JWT auth, Pydantic validation
              └───┬─────┬───┘
                  │     │
          ┌───────▼─┐ ┌─▼───────┐
          │ Postgres │ │  Redis  │  Session cache
          │   16     │ │   7     │  (health check)
          │127.0.0.1 │ │127.0.0.1│
          └──────────┘ └─────────┘
```

**Data Flow: RFID Scan**
```
Card Tap → USB HID → Browser keydown → script.js buffer
  → POST /api/v1/scan {uid} → Pydantic validation
  → SQLAlchemy SELECT...FOR UPDATE (row lock)
  → bounce check → toggle IN/OUT → INSERT attendance
  → COMMIT → ScanResponse JSON → UI update
```
