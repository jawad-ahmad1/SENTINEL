# 🔧 Troubleshooting

Common issues and their solutions, organized by category.

---

## 🔌 RFID Reader Issues

<details>
<summary><strong>Reader not detected by computer</strong></summary>

**Symptoms:** No lights on reader, not in Device Manager

**Solutions:**
1. Unplug and replug the USB cable
2. Try a different USB port (front and back)
3. Check Device Manager (Windows) or `lsusb` (Linux) for the device
4. Try on a different computer — if still fails, reader may be defective
5. Avoid USB hubs; connect directly to the computer
</details>

<details>
<summary><strong>Card scans but nothing happens in browser</strong></summary>

**Symptoms:** Reader beeps, ID appears in Notepad, but kiosk doesn't respond

**Solutions:**
1. Click inside the browser window to ensure it has focus
2. Check that the kiosk page (`index.html`) is loaded
3. Open browser console (F12) and look for JavaScript errors
4. Verify the API is running: `curl http://localhost/api/v1/health`
5. Check that `script.js` is loaded (no 404 in Network tab)
</details>

<details>
<summary><strong>"Card Not Recognized" message</strong></summary>

**Symptoms:** Card scans, but shows error

**Solutions:**
1. This happens only if auto-registration is disabled
2. Register the card via Admin Panel → Employees → Register
3. Verify the card is 125kHz EM4100 (not 13.56MHz NFC)
4. Check that the employee's account is active
</details>

---

## 🗄️ Database Issues

<details>
<summary><strong>PostgreSQL connection refused</strong></summary>

**Symptoms:** `ConnectionRefusedError` or `could not connect to server`

**Solutions:**
1. Check PostgreSQL is running:
   ```bash
   docker compose ps   # Docker
   sudo systemctl status postgresql  # Local
   ```
2. Verify `DATABASE_URL` in `.env` matches your credentials
3. Check that PostgreSQL is listening on the expected port:
   ```bash
   docker compose logs db | tail -20
   ```
4. Ensure the database exists:
   ```bash
   docker compose exec db psql -U sentinel -d attendance -c "SELECT 1;"
   ```
</details>

<details>
<summary><strong>Alembic migration errors</strong></summary>

**Symptoms:** `alembic upgrade head` fails

**Solutions:**
1. Ensure database is running and accessible
2. Check `alembic.ini` has the correct `sqlalchemy.url`
3. For Docker, run inside the container:
   ```bash
   docker compose exec app alembic upgrade head
   ```
4. If tables already exist, stamp the current revision:
   ```bash
   alembic stamp head
   ```
</details>

---

## 🔐 Authentication Issues

<details>
<summary><strong>Can't login to admin panel</strong></summary>

**Symptoms:** Login page shows "Invalid credentials"

**Solutions:**
1. Verify credentials match `DEFAULT_ADMIN_EMAIL` / `DEFAULT_ADMIN_PASSWORD` in `.env`
2. Check that the admin user was seeded (first startup creates it)
3. Clear browser cookies and try again
4. Check API logs: `docker compose logs app | tail -20`
5. If locked out, recreate the admin by restarting with empty database
</details>

<details>
<summary><strong>"Session expired" constantly</strong></summary>

**Symptoms:** Keeps redirecting to login page

**Solutions:**
1. Check that `COOKIE_SECURE=false` for HTTP (or `true` for HTTPS)
2. Ensure cookies aren't being blocked by browser settings
3. Check `ACCESS_TOKEN_EXPIRE_MINUTES` isn't set too low
4. Verify clock sync between server and client
</details>

<details>
<summary><strong>Rate limited (429 Too Many Requests)</strong></summary>

**Symptoms:** Login returns 429 error

**Solutions:**
1. Wait 1 minute — login is limited to 5 attempts per minute
2. If behind a proxy, ensure `X-Forwarded-For` header is set correctly
3. Check `nginx.conf` rate limit settings
</details>

---

## 🐳 Docker Issues

<details>
<summary><strong>Port 80 already in use</strong></summary>

**Solutions:**
1. Find and stop the conflicting service:
   ```bash
   sudo lsof -i :80  # Linux
   netstat -ano | findstr :80  # Windows
   ```
2. Or change the port in `docker-compose.yml`:
   ```yaml
   ports:
     - "8080:80"
   ```
</details>

<details>
<summary><strong>Container keeps restarting</strong></summary>

**Solutions:**
1. Check logs: `docker compose logs app --tail 50`
2. Common causes:
   - Missing/invalid `.env` file
   - Database not ready (increase `depends_on` wait)
   - Python dependency issues (rebuild: `docker compose up --build`)
</details>

<details>
<summary><strong>Changes not reflected after code edit</strong></summary>

**Solutions:**
1. Rebuild containers:
   ```bash
   docker compose up -d --build
   ```
2. Clear browser cache (Ctrl+Shift+R)
3. Check CSS version: `.css?v=8` ensures cache busting
</details>

---

## 📊 Report Issues

<details>
<summary><strong>Reports show zero data</strong></summary>

**Solutions:**
1. Verify the date range has attendance data
2. Check timezone settings (Settings → Timezone Offset)
3. Ensure employees have `is_active = true`
4. Try a date you know has scans
</details>

<details>
<summary><strong>CSV export is empty</strong></summary>

**Solutions:**
1. Check date format: `YYYY-MM-DD` (e.g., `2026-02-25`)
2. Verify attendance exists for that date
3. Check browser console for download errors
</details>

---

## ⚡ Performance Issues

<details>
<summary><strong>Slow page loads</strong></summary>

**Solutions:**
1. Verify Nginx gzip is enabled (check `nginx.conf`)
2. Check Redis is running (used for live-stats caching)
3. Clear old attendance data (archive records older than 1 year)
4. Check server resources: `docker stats`
5. Increase Uvicorn workers in `docker-compose.yml`
</details>

<details>
<summary><strong>High CPU/memory usage</strong></summary>

**Solutions:**
1. Check container resources: `docker stats`
2. Optimize PostgreSQL: add indexes, run `VACUUM ANALYZE`
3. Reduce polling frequency on kiosk (increase `statsInterval` in `script.js`)
4. Check for runaway queries: `docker compose logs db | grep "slow"`
</details>

---

## 🌐 Network Issues

<details>
<summary><strong>CORS errors in browser console</strong></summary>

**Solutions:**
1. Update `CORS_ORIGINS` in `.env` to include your domain:
   ```bash
   CORS_ORIGINS=["https://attendance.company.com"]
   ```
2. Restart the app: `docker compose restart app`
3. Ensure the origin matches exactly (including protocol and port)
</details>

---

## Getting Help

If your issue isn't listed here:

1. Check [FAQ.md](FAQ.md) for common questions
2. Search [existing issues](https://github.com/jawad-ahmad1/sentinel-attendance/issues)
3. Open a [new issue](https://github.com/jawad-ahmad1/sentinel-attendance/issues/new/choose)
4. Include logs, screenshots, and environment details

---

[← Back to README](README.md)
