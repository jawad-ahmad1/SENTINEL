# Test Plan

Date: 2026-03-09  
Project: RFID Attendance System

## 1) Validation Objectives
- Confirm attendance integrity across timezone/business-day boundaries.
- Verify auth/session/security hardening does not regress functionality.
- Validate report/export correctness, including CSV safety.
- Verify Docker-based startup and migration-first deployment path.

## 2) Environment Gate (Required)

### 2.1 Docker Integration Gate
1. `docker --version`
2. `docker compose config`
3. `docker compose up -d --build`
4. `docker compose ps`
5. Health checks:
   - `GET /api/v1/health`
   - `GET /api/v1/status`
6. Migration verification:
   - confirm `alembic upgrade head` executed in app startup logs.

Status in this run:
- `docker compose config` passed.
- `docker compose up -d --build` blocked due unavailable Docker daemon/service.

### 2.2 Python/Test Runtime Gate
1. Verify interpreter path resolves correctly.
2. Run test suite:
   - `pytest -q`
3. Collect pass/fail artifacts.

Status in this run:
- blocked by local Python launcher mismatch (`No Python at ... WindowsApps ...`).

## 3) Automated Test Matrix

### 3.1 Existing + Updated Test Coverage
- `tests/test_scan.py`
  - unknown UID auto-register
  - IN/OUT toggle
  - UID validation
  - business timezone date boundary (added)
- `tests/test_reports.py`
  - daily summary
  - CSV export
  - CSV formula sanitization (added)
  - invalid date validation (added)
  - monthly/trends/employee analytics/health/status
- `tests/test_settings_validation.py` (new)
  - invalid time format
  - invalid timezone format
  - invalid work window
  - valid updates
- `tests/test_security_hardened.py`
  - double-tap concurrency behavior
  - HttpOnly cookie flags

### 3.2 Required Additional Automated Cases
1. CSRF host-check behavior for cookie-backed mutating requests.
2. Absence override write with invalid employee id (expect 404).
3. Clear attendance range validation (`date_from > date_to`).
4. Scan endpoint abuse controls (if auth/isolation enforcement is added).

## 4) End-to-End Workflow Tests (Manual)

### 4.1 Kiosk Flow
1. Scan unknown UID -> employee auto-registered.
2. Re-scan same UID -> toggles IN/OUT.
3. Rapid double-tap (< bounce window) -> idempotent event response.
4. Break start/end recorded and reflected in reports.

Expected:
- No duplicate bounce events.
- Correct event sequence and timestamps.

### 4.2 Admin/Auth Flow
1. Login with seeded admin credentials.
2. Verify `/auth/me` response and protected page access.
3. Logout and verify cookie/session invalidation.

Expected:
- Protected pages deny unauthorized access.
- Session clears cleanly.

### 4.3 Employee CRUD
1. Create employee with unique RFID.
2. Attempt duplicate RFID (expect rejection).
3. Update employee fields.
4. Soft delete employee.

Expected:
- CRUD behavior consistent with API contract.
- Deactivated employee cannot be scanned as active.

### 4.4 Reports/Analytics
1. Daily summary for selected date.
2. Monthly report for selected month/year.
3. Trends endpoint for last N days.
4. Employee analytics endpoint.
5. Absence report and per-employee drilldown.

Expected:
- Date filters are respected.
- Totals and hours consistent with raw attendance events.

### 4.5 CSV Export
1. Export day with normal names.
2. Export day with formula-like name (`=cmd`) and newline inputs.

Expected:
- CSV fields are escaped/sanitized.
- No formula execution risk in spreadsheet clients.

## 5) Performance and Load Checks
1. 500 employees with one month of records.
2. Measure:
   - `/attendance/live-stats`
   - `/reports/absence/{year}/{month}`
   - `/reports/summary/{date}`
3. Observe response time and DB load.

Targets:
- P95 under 500 ms for common report/stats endpoints in local infra.

## 6) Exit Criteria
- `critical open issues = 0` (met in code).
- Docker integration gate executed successfully (pending).
- Automated tests executed and passing (pending in this environment).
- High open issue on scan trust boundary resolved by policy/architecture decision.

## 7) Blockers Logged
1. Docker daemon/service unavailable in current environment.
2. Local Python launcher mismatch preventing test execution.

Action required:
- Restore runtime prerequisites, then execute this plan exactly and attach logs to release notes.


