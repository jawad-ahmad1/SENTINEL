# ❓ Frequently Asked Questions

## General

**Q: What is Sentinel?**
A: Sentinel is an open-source RFID attendance tracking system. Employees tap RFID cards to check in/out, and admins manage attendance through a web dashboard.

**Q: How much does it cost?**
A: The software is free (MIT License). Hardware costs ~$15 total: a USB RFID reader (~$6) and RFID cards (~$0.10 each).

**Q: How many employees can it handle?**
A: Tested with up to 500 employees on a single server. The architecture supports thousands with database indexing and Redis caching.

**Q: Does it work offline?**
A: The kiosk requires network access to the server. For offline resilience, deploy the server on a local machine (not cloud).

---

## Installation

**Q: Can I run it without Docker?**
A: Yes. See [INSTALLATION.md](INSTALLATION.md) — Method 2 (Manual) or Method 3 (Windows SQLite for testing).

**Q: What OS do I need?**
A: Any OS that runs Docker (Linux, Windows 10+, macOS). For manual install, Python 3.12+ on any OS.

**Q: Can I use MySQL instead of PostgreSQL?**
A: Not out of the box. The app uses `asyncpg` and PostgreSQL-specific features (`SELECT...FOR UPDATE`). Porting to MySQL would require code changes.

---

## RFID Hardware

**Q: What RFID reader do I need?**
A: Any **125kHz USB HID** reader (~$6 on Amazon/AliExpress). It must operate in keyboard emulation mode. See [HARDWARE_SETUP_GUIDE.md](HARDWARE_SETUP_GUIDE.md).

**Q: Do I need special drivers?**
A: No. The reader emulates a USB keyboard — plug and play on all operating systems.

**Q: Can I use NFC / phone for scanning?**
A: No. NFC (13.56MHz) is a different frequency than the RFID readers used here (125kHz). They are incompatible.

**Q: What if an employee loses their card?**
A: Admin deactivates the old card in the admin panel and assigns a new one. The old card is immediately blocked.

**Q: Can employees clone cards?**
A: EM4100/TK4100 cards can be cloned (they're not encrypted). For high-security environments, upgrade to MIFARE DESFire. For most offices, the convenience outweighs the risk.

---

## Usage

**Q: How does IN/OUT toggling work?**
A: The system alternates. First scan = IN, second scan = OUT, third scan = IN, etc. The scan type is determined by the last event for that employee today.

**Q: What's the bounce window?**
A: A configurable delay (default: 2 seconds) that prevents accidental double-taps from creating duplicate events.

**Q: Can employees scan for each other (buddy punching)?**
A: The system can't prevent this with basic RFID cards. Consider: security cameras at the kiosk, biometric add-ons for high-security, or random spot-checks.

**Q: What happens if the kiosk computer crashes?**
A: Employees can't scan until it's back online. The server (PostgreSQL) retains all data. Consider a backup kiosk or mobile admin access for manual entries.

---

## Admin

**Q: Can I have multiple admin accounts?**
A: Yes. Create additional users with `role: admin` through the admin panel.

**Q: Can I correct attendance after the fact?**
A: Yes. Use the absence report override feature to mark days as present, leave, or half-day.

**Q: How do I export data for payroll?**
A: Reports → Export CSV. The CSV includes employee name, check-in/out times, and total hours.

**Q: Can I configure different work hours for different departments?**
A: Not currently. The system uses a single global work schedule. This is on the roadmap.

---

## Technical

**Q: Is the API documented?**
A: Yes. Interactive Swagger docs at `/docs` and full reference in [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

**Q: How are passwords stored?**
A: bcrypt hashing (12 rounds) via passlib. Plaintext passwords are never stored.

**Q: What's the JWT token flow?**
A: Access token (30min) + refresh token (7 days), both stored as HttpOnly cookies. Access token is rotated via the refresh endpoint.

**Q: Can I integrate with other systems?**
A: Yes, via the REST API. All endpoints return JSON and accept JWT authentication.

**Q: Where are attendance records stored?**
A: PostgreSQL database. Each scan creates an `AttendanceEvent` row with employee ID, event type (IN/OUT/BREAK), and timestamp.

---

## Deployment

**Q: Can I deploy to AWS/Azure/DigitalOcean?**
A: Yes. See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for cloud deployment instructions.

**Q: How do I set up HTTPS?**
A: Use Let's Encrypt with Nginx. The deployment guide covers TLS setup.

**Q: How do I backup the database?**
A: Use `scripts/backup.sh` or set up automated backups via cron. See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

---

## Still Have Questions?

1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
2. Search [GitHub Issues](https://github.com/jawad-ahmad1/sentinel-attendance/issues)
3. Open a [new issue](https://github.com/jawad-ahmad1/sentinel-attendance/issues/new/choose)

---

[← Back to README](README.md)
