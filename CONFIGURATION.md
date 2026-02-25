# ⚙️ Configuration Guide

All configuration is done via environment variables in `.env`. Copy the template:

```bash
cp .env.example .env
```

---

## Environment Variables Reference

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `sentinel` | PostgreSQL username |
| `POSTGRES_PASSWORD` | *(required)* | PostgreSQL password — generate with `openssl rand -hex 32` |
| `POSTGRES_DB` | `attendance` | Database name |
| `DATABASE_URL` | `postgresql+asyncpg://sentinel:...@db:5432/attendance` | Full async connection string |

### Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |

> Redis is used for caching live-stats (15s TTL). The app gracefully falls back to database queries if Redis is unavailable.

### Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(required)* | JWT signing key — generate with `openssl rand -hex 32` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |

> ⚠️ The app will log a warning at startup if `SECRET_KEY` is left at the default placeholder.

### RFID / Scanning

| Variable | Default | Description |
|----------|---------|-------------|
| `BOUNCE_WINDOW_SECONDS` | `2` | Minimum seconds between duplicate scans from the same card |

> The bounce window prevents accidental double-taps from creating duplicate events.

### Cookie Security

| Variable | Default | Description |
|----------|---------|-------------|
| `COOKIE_SECURE` | `false` | Set `true` in production (requires HTTPS) |

### CORS

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `["http://localhost", "http://localhost:80"]` | JSON array of allowed origins |

**Example for production:**
```bash
CORS_ORIGINS=["https://attendance.company.com"]
```

### Default Admin

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_ADMIN_EMAIL` | `admin@company.com` | Seeded admin email (first startup only) |
| `DEFAULT_ADMIN_PASSWORD` | *(required)* | Seeded admin password — **change immediately** |

> The admin account is only created if no users exist in the database.

---

## Attendance Settings

These are configured via the **Admin Panel → Settings** page (not environment variables):

| Setting | Default | Description |
|---------|---------|-------------|
| Work Start | `09:00` | Expected start of work day |
| Work End | `17:00` | Expected end of work day |
| Grace Period | `15 min` | Minutes after work start before marked "late" |
| Timezone Offset | `5` | UTC offset in hours (e.g., `5` for PKT) |

---

## Docker Compose Ports

Default port mappings in `docker-compose.yml`:

| Service | Internal Port | External Port | Notes |
|---------|---------------|---------------|-------|
| Nginx | 80 | 80 | HTTP reverse proxy |
| FastAPI | 8000 | *(internal only)* | Proxied by Nginx |
| PostgreSQL | 5432 | 5432 | Bound to localhost |
| Redis | 6379 | 6379 | Bound to localhost |

To change external ports, edit `docker-compose.yml`:

```yaml
services:
  nginx:
    ports:
      - "8080:80"  # Change 80 → 8080
```

---

## Nginx Configuration

Located at `nginx/nginx.conf`. Key settings:

| Setting | Value | Description |
|---------|-------|-------------|
| Rate limit (login) | 5 req/min | Brute-force protection |
| Rate limit (API) | 100 req/min | General flood protection |
| Gzip | Enabled (level 4) | ~60-80% size reduction |
| Cache-Control | `no-cache` for HTML | Prevents stale pages |

---

## Security Best Practices

1. **Generate all secrets** before first deploy:
   ```bash
   openssl rand -hex 32  # → SECRET_KEY
   openssl rand -hex 32  # → POSTGRES_PASSWORD
   ```

2. **Set `COOKIE_SECURE=true`** when using HTTPS

3. **Restrict `CORS_ORIGINS`** to your domain only

4. **Change admin password** immediately after first login

5. **Never commit `.env`** — it's in `.gitignore`

---

## Example Production `.env`

```bash
# Database
POSTGRES_USER=sentinel
POSTGRES_PASSWORD=a1b2c3d4e5f6789012345678abcdef01
POSTGRES_DB=attendance
DATABASE_URL=postgresql+asyncpg://sentinel:a1b2c3d4e5@db:5432/attendance

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=9f8e7d6c5b4a3210fedcba9876543210abcdef
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=3
COOKIE_SECURE=true

# CORS
CORS_ORIGINS=["https://attendance.company.com"]

# RFID
BOUNCE_WINDOW_SECONDS=2

# Admin (first start only)
DEFAULT_ADMIN_EMAIL=admin@company.com
DEFAULT_ADMIN_PASSWORD=MyStr0ng!P@ssw0rd
```

---

[← Back to README](README.md)
