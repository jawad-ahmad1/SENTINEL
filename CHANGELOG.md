# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Employee self-service portal
- Multi-location support
- Shift scheduling
- Mobile app (PWA)

---

## [2.0.0] - 2026-02-25

### Added
- 🔒 **Rate limiting** on auth endpoints via slowapi (5/min login, 10/min refresh)
- 🎨 **Toast notification system** (`toast.js`) replacing all `alert()` calls
- 🧠 **Redis caching** for live-stats endpoint (15s TTL)
- ♿ **Accessibility improvements** — `:focus-visible`, `aria-label`, `for=` labels
- 📊 **Monthly absence reports** with daily breakdown and override support
- 🧪 **Comprehensive test suite** — 32 tests across 7 files including fuzz testing
- 🐳 **Docker Compose** multi-service orchestration (Nginx + FastAPI + PostgreSQL + Redis)
- 📈 **Analytics endpoints** — trends, per-employee stats, attendance rates
- 🔧 **Break tracking** — BREAK_START / BREAK_END events with duration deduction
- 📝 **Complete documentation suite** — 16+ markdown files covering all aspects
- ⚡ **Font preloading** — `preconnect` hints and async font loading on all pages
- 🗜️ **Nginx gzip compression** — 60-80% reduction in transfer sizes
- 🦴 **Skeleton loaders and empty states** — CSS classes for loading UX
- 🔐 **Input validation** — `maxlength`, `autocomplete`, LIKE metacharacter escaping
- 🛡️ **Mutable default fix** — `Field(default_factory=dict)` in Pydantic schemas

### Changed
- Upgraded Python to 3.12
- Switched to SQLAlchemy 2.0 async with asyncpg
- CSS version bumped to `?v=8` for cache busting
- Replaced silent `except: pass` with `logger.warning()` / `logger.debug()`
- Code formatted with Black (line-length 99) and isort

### Security
- JWT tokens stored in HttpOnly, SameSite=Lax cookies
- bcrypt password hashing (12 rounds)
- Row-level locking (`SELECT...FOR UPDATE`) preventing duplicate scans
- Nginx rate limiting (5 req/min login, 100 req/min API)
- Non-root Docker container user
- SQL LIKE metacharacter escaping

---

## [1.0.0] - 2026-01-15

### Added
- Initial release
- RFID card scanning (USB HID keyboard emulation)
- Auto-registration of unknown cards
- IN/OUT toggle with bounce-window deduplication
- Admin dashboard with real-time attendance feed
- Employee CRUD with soft-delete
- Daily attendance summary reports
- CSV export for payroll integration
- JWT authentication with access/refresh tokens
- PostgreSQL database with Alembic migrations
- Nginx reverse proxy with TLS termination
- Docker containerization
- `.env.example` with all configuration options
- MIT License

### Infrastructure
- FastAPI + Uvicorn async web server
- PostgreSQL 16 with asyncpg driver
- Redis 7 for caching
- Nginx Alpine for reverse proxy
- Docker Compose for orchestration

---

[← Back to README](README.md)
