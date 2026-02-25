# 🔐 Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.0.x   | ✅ Active support |
| 1.0.x   | ⚠️ Critical fixes only |
| < 1.0   | ❌ No support |

## Reporting a Vulnerability

**⚠️ Do NOT open a public GitHub issue for security vulnerabilities.**

If you discover a security vulnerability, please report it responsibly:

1. **Email:** Send details to **security@company.com**
2. **Subject:** `[SECURITY] Sentinel — <brief description>`
3. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline

| Stage | Timeline |
|-------|----------|
| Acknowledgment | Within 48 hours |
| Triage & assessment | Within 5 business days |
| Patch development | Within 14 business days |
| Public disclosure | After patch is released |

We will credit you in the release notes unless you prefer to remain anonymous.

---

## Security Architecture

### Authentication & Authorization

| Feature | Implementation |
|---------|---------------|
| Password hashing | bcrypt via passlib (12 rounds) |
| Token format | JWT (HS256) access + refresh tokens |
| Token storage | HttpOnly, SameSite=Lax cookies |
| Token lifetime | Access: 30 min, Refresh: 7 days |
| Role-based access | Admin / User roles via middleware |
| Rate limiting | 5 req/min on login (slowapi + Nginx) |

### Data Protection

| Feature | Implementation |
|---------|---------------|
| Input validation | Pydantic schemas with regex patterns |
| SQL injection | SQLAlchemy ORM (parameterized queries) |
| LIKE injection | Metacharacter escaping (`%`, `_`) |
| XSS prevention | No server-side template rendering |
| CORS | Configurable origin allowlist |
| Network isolation | PostgreSQL/Redis bound to localhost |

### Infrastructure

| Feature | Implementation |
|---------|---------------|
| Container security | Non-root `appuser` inside Docker |
| Secrets management | Environment variables, never in source |
| TLS termination | Nginx with Let's Encrypt |
| Dependency scanning | Bandit for Python security linting |
| Concurrency safety | `SELECT...FOR UPDATE` row-level locking |

---

## Security Best Practices for Deployment

1. **Change all default credentials** in `.env` before production deployment
2. **Generate strong secrets:** `openssl rand -hex 32` for `SECRET_KEY` and `POSTGRES_PASSWORD`
3. **Enable HTTPS:** Set `COOKIE_SECURE=true` in production
4. **Restrict network access:** PostgreSQL and Redis should not be publicly accessible
5. **Keep dependencies updated:** Run `pip list --outdated` regularly
6. **Monitor logs:** Check for unusual authentication patterns
7. **Backup regularly:** Use the provided `scripts/backup.sh`
8. **Use firewall rules:** Only expose ports 80/443 publicly

---

## Known Security Considerations

- **RFID Cards (EM4100/TK4100):** These cards use 125kHz passive RFID without encryption. Card IDs can be cloned. For high-security environments, consider upgrading to 13.56MHz MIFARE DESFire cards with encrypted communication.
- **Default Admin Account:** The system seeds a default admin on first startup. Change the password immediately via the admin panel.
- **B105 Bandit Finding:** The `config.py` contains a default `SECRET_KEY` placeholder that triggers a Bandit B105 warning. This is by design — it produces a runtime warning at startup if unchanged.

---

[← Back to README](README.md)
