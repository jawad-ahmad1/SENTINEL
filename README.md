<div align="center">

# 🛡️ Sentinel — RFID Attendance System

**A production-ready, async RFID attendance tracking system built with FastAPI, PostgreSQL, Redis, and Docker.**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-32%20Passed-brightgreen?logo=pytest&logoColor=white)](#testing)

</div>

---

Sentinel lets employees clock in and out by tapping RFID cards on a USB reader. The system auto-registers new cards, toggles IN/OUT state, tracks breaks, generates reports, and exports CSV — all behind JWT authentication with role-based access control.

**One command to deploy. Plug in a $6 USB reader. Done.**

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **RFID Scan** | Tap-to-clock IN/OUT with configurable bounce-window deduplication |
| **Row-Level Locking** | `SELECT...FOR UPDATE` prevents duplicate records under concurrent scans |
| **Break Tracking** | BREAK_START / BREAK_END events with duration deduction in reports |
| **Reports & Analytics** | Daily summary, monthly aggregation (weekday-aware), trends, CSV export |
| **Admin Dashboard** | Employee CRUD, user management, real-time attendance feed |
| **Security** | HttpOnly/SameSite cookies, bcrypt hashing, Pydantic validation, rate limiting |
| **Auto-Registration** | Unknown cards are automatically registered on first scan |

---

## 🏗️ Architecture

```
┌──────────┐     ┌───────────┐     ┌───────────┐     ┌────────────┐
│  RFID    │     │   Nginx   │     │  FastAPI   │     │ PostgreSQL │
│  Reader  │────>│  (Alpine) │────>│  (Uvicorn) │────>│    16      │
│  USB HID │     │  :80/:443 │     │   :8000    │     │  (asyncpg) │
└──────────┘     └───────────┘     └─────┬──────┘     └────────────┘
                  Rate limiting           │
                  TLS termination         ▼
                  Static files      ┌──────────┐
                                    │  Redis 7 │
                                    │  (cache) │
                                    └──────────┘
```

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Proxy | Nginx (Alpine) | Static files, rate limiting (5r/m login, 100r/m API), TLS |
| API | FastAPI + Gunicorn + 4 Uvicorn workers | REST endpoints, async I/O |
| Database | PostgreSQL 16 + asyncpg | Persistent storage, row-level locks |
| Cache | Redis 7 | Health checks, session support |
| Auth | JWT (HS256) via HttpOnly cookies | Access + refresh token rotation |
| Frontend | Vanilla HTML / CSS / JS | Kiosk display, admin panel, reports |

---

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose v2+
- Git

### 1. Clone & Configure

```bash
git clone https://github.com/yourusername/sentinel-attendance.git
cd sentinel-attendance
cp .env.example .env
```

Edit `.env` — at minimum, change these values:

```bash
# Generate secrets
openssl rand -hex 32   # → SECRET_KEY
openssl rand -hex 32   # → POSTGRES_PASSWORD
```

### 2. Deploy

```bash
docker compose up -d --build
```

That's it. Four containers start automatically:

| Service | Port | Status |
|---------|------|--------|
| Nginx | `localhost:80` | Reverse proxy + static files |
| FastAPI | `localhost:8000` | API (internal) |
| PostgreSQL | `127.0.0.1:5432` | Database (localhost only) |
| Redis | `127.0.0.1:6379` | Cache (localhost only) |

### 3. Access

| Page | URL |
|------|-----|
| 🖥️ Kiosk (employee scanning) | http://localhost |
| 🔐 Admin Login | http://localhost/login.html |
| 📊 Dashboard | http://localhost/admin.html |
| 📋 Reports | http://localhost/reports.html |
| 📖 API Docs (Swagger) | http://localhost/docs |

Login with the credentials from `DEFAULT_ADMIN_EMAIL` / `DEFAULT_ADMIN_PASSWORD` in your `.env`.

### Windows Quick Start

Double-click `run_docker.bat` for Docker deployment, or `run_app.bat` for local SQLite development.

---

## 📡 API Reference

All endpoints are prefixed with `/api/v1`. Interactive docs at `/docs`.

### Authentication
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/login` | Public | OAuth2 password flow → HttpOnly cookies |
| POST | `/auth/refresh` | Cookie | Rotate access token |
| POST | `/auth/logout` | Public | Clear auth cookies |

### Scanning & Breaks
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/scan` | User | RFID scan — auto-toggles IN/OUT |
| POST | `/break/start` | User | Start break for employee |
| POST | `/break/end` | User | End break for employee |

### Employees
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/employees` | User | List all employees (paginated) |
| POST | `/employees` | Admin | Create employee |
| PUT | `/employees/{id}` | Admin | Update employee |
| DELETE | `/employees/{id}` | Admin | Soft-delete (preserves records) |

### Reports & Analytics
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/attendance/today` | Public | Today's attendance feed (kiosk) |
| GET | `/reports/summary/{date}` | User | Daily summary with work hours |
| GET | `/reports/monthly/{year}/{month}` | User | Monthly report (weekday-aware) |
| GET | `/reports/daily/csv?date_str=` | User | CSV export for payroll |
| GET | `/analytics/trends?days=30` | User | Attendance trends |
| GET | `/analytics/employee/{id}` | User | Per-employee analytics |

### System
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | Public | DB + Redis connectivity check |
| GET | `/status` | User | System status |

---

## 📁 Project Structure

```
sentinel-attendance/
├── app/                          # Backend application
│   ├── api/v1/
│   │   ├── endpoints/
│   │   │   ├── auth.py           # Login, refresh, logout, user CRUD
│   │   │   ├── employees.py      # Scan, breaks, employee CRUD
│   │   │   └── reports.py        # Reports, analytics, CSV export
│   │   ├── api.py                # Router aggregation
│   │   └── deps.py               # Dependency injection (auth, DB session)
│   ├── core/
│   │   ├── config.py             # Settings via pydantic-settings
│   │   ├── security.py           # JWT creation/verification, bcrypt
│   │   └── exceptions.py         # Global exception handlers
│   ├── models/                   # SQLAlchemy ORM models
│   ├── schemas/                  # Pydantic request/response schemas
│   └── main.py                   # FastAPI app factory + lifespan
│
├── frontend/                     # Static frontend
│   ├── css/style.css             # 1,075-line design system
│   ├── js/
│   │   ├── script.js             # Kiosk logic + RFID capture
│   │   ├── admin.js              # Admin dashboard logic
│   │   └── reports.js            # Reports + CSV export
│   ├── index.html                # Kiosk scanning page
│   ├── login.html                # Authentication page
│   ├── admin.html                # Admin dashboard
│   ├── employees.html            # Employee management
│   ├── register.html             # Employee registration
│   └── reports.html              # Reports & analytics
│
├── nginx/nginx.conf              # Reverse proxy + rate limiting config
├── migrations/                   # Alembic database migrations
├── tests/                        # Async test suite (32 tests)
├── scripts/
│   ├── backup.sh                 # Automated PostgreSQL backup
│   └── monitor.sh                # Health monitoring + alerting
│
├── docker-compose.yml            # Multi-service orchestration
├── Dockerfile                    # Python 3.12-slim, non-root user
├── requirements.txt              # Pinned Python dependencies
├── .env.example                  # Environment variable template
├── run_docker.bat                # Windows Docker launcher
├── run_app.bat                   # Windows local dev launcher
│
├── DEPLOYMENT_GUIDE.md           # Production deployment (5-day plan)
├── HARDWARE_SETUP_GUIDE.md       # RFID readers, kiosks, setup
├── USER_GUIDE.md                 # Complete user & admin manual
└── LICENSE                       # MIT License
```

---

## 🔧 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(change this)* | JWT signing key — run `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | *(change this)* | Database password |
| `DATABASE_URL` | `postgresql+asyncpg://...@db:5432/attendance` | Async connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | JWT refresh token lifetime |
| `BOUNCE_WINDOW_SECONDS` | `2` | Anti-duplicate scan threshold |
| `COOKIE_SECURE` | `false` | Set `true` for HTTPS |
| `CORS_ORIGINS` | `["http://localhost"]` | Allowed origins (JSON array) |
| `DEFAULT_ADMIN_EMAIL` | `admin@attendance.local` | Seeded admin account |
| `DEFAULT_ADMIN_PASSWORD` | `changeme123` | Seeded admin password (**change this**) |

> ⚠️ Copy `.env.example` to `.env` and fill in production values. Never commit `.env` to git.

---

## 🔐 Security

| Feature | Implementation |
|---------|---------------|
| **Authentication** | JWT access + refresh tokens in HttpOnly, SameSite=Lax cookies |
| **Password Storage** | bcrypt hashing via passlib |
| **Concurrency Safety** | `SELECT...FOR UPDATE` row-level locking (prevents double scans) |
| **Rate Limiting** | Nginx: 5 req/min on login, 100 req/min on API |
| **Input Validation** | Pydantic schemas with regex patterns on all inputs |
| **Network Isolation** | PostgreSQL and Redis bound to 127.0.0.1 only |
| **Container Security** | App runs as non-root `appuser` inside Docker |
| **Cookie Security** | HttpOnly, Secure (HTTPS), SameSite=Lax flags |

---

## 🧪 Testing

```bash
# Run the full test suite
python -m pytest tests/ -v

# Or inside Docker
docker compose exec app python -m pytest tests/ -v
```

**32 tests** across 7 test files:

| File | Tests | Coverage |
|------|-------|----------|
| `test_scan.py` | 5 | RFID scan, auto-register, IN/OUT toggle, bounce protection |
| `test_employees.py` | 8 | CRUD operations, validation, soft-delete |
| `test_breaks.py` | 5 | Break start/end, error handling |
| `test_reports.py` | 9 | Daily/monthly reports, CSV export, analytics |
| `test_omega_fuzzer.py` | 3 | 250+ random/malicious payloads |
| `test_security_hardened.py` | 2 | SQL injection, XSS rejection |

---

## 🔌 Hardware Setup

**You need 2 things:** a USB RFID reader (~$6) and matching RFID cards (~$0.10/card).

The reader operates in USB HID keyboard-emulation mode — no drivers, no SDK. Plug it in, open the browser, tap a card.

→ **Full hardware guide:** [HARDWARE_SETUP_GUIDE.md](HARDWARE_SETUP_GUIDE.md)

---

## 🚢 Production Deployment

The deployment guide covers server provisioning, TLS setup, Docker deployment, automated backups, monitoring, and rollback procedures.

→ **Full deployment guide:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

---

## 📖 User Guide

Complete documentation covering admin workflows, employee management, reporting, API usage, and troubleshooting.

→ **Full user guide:** [USER_GUIDE.md](USER_GUIDE.md)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with FastAPI · PostgreSQL · Redis · Docker · Nginx**

</div>
