# Issues And Fixes (Prioritized)

Date: 2026-03-09  
Status legend: `Fixed`, `Open`, `Blocked-by-environment`

## Critical

### Issue 1 - Docker image missing migration assets (`Fixed`)
- Severity: `CRITICAL`
- Category: Deployment / Data Integrity
- Location: `Dockerfile`
- Impact if unfixed: in-container `alembic upgrade head` fails; schema drift and broken startup in clean environments.

Current code (before):
```dockerfile
COPY app/ app/
COPY frontend/ frontend/
```

Fixed code:
```dockerfile
COPY app/ app/
COPY migrations/ migrations/
COPY alembic.ini .
COPY frontend/ frontend/
```

Why this works:
- Alembic runtime now has migration scripts and config inside image.

Testing:
- `docker compose config` succeeds.
- Full runtime apply/test remains blocked by unavailable Docker daemon in this environment.

Estimated fix time: `0.5h` (completed)

### Issue 2 - Business-day drift in reporting (`Fixed`)
- Severity: `CRITICAL`
- Category: Functional Correctness / Payroll Integrity
- Location: `app/api/v1/endpoints/reports.py`
- Impact if unfixed: wrong day boundaries around UTC offset transitions cause incorrect attendance, late, and absence calculations.

Current code (before):
```python
start = (date.today() - timedelta(days=days)).isoformat()
today = date.today()
```

Fixed code:
```python
tz_offset = await _get_timezone_offset(db)
today_local = parse_iso_date(business_date_str(tz_offset, utc_now()))
start = (today_local - timedelta(days=days)).isoformat()
```

Why this works:
- All date boundaries now derive from configured business timezone offset.

Testing:
- Added regression test in `tests/test_scan.py` for business-timezone date boundary.

Estimated fix time: `1.5h` (completed)

## High

### Issue 3 - Cookie-backed CSRF mutating requests (`Fixed`)
- Severity: `HIGH`
- Category: Security
- Location: `app/api/v1/deps.py`
- Impact if unfixed: authenticated browser session could be abused cross-site for state-changing requests.

Current code (before):
```python
# Cookie accepted without same-origin checks
```

Fixed code:
```python
if cookie_session and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
    host = request.headers.get("host", "")
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    ...
    if origin and not _is_same_host(origin):
        raise HTTPException(status_code=403, detail="Cross-site request blocked")
```

Why this works:
- Mutating cookie-auth requests now require same-host origin/referrer.

Testing:
- Validate 403 for cross-site Origin and 200 for same-origin requests.

Estimated fix time: `2h` (completed)

### Issue 4 - CSV formula injection risk (`Fixed`)
- Severity: `HIGH`
- Category: Security / Export Safety
- Location: `app/api/v1/endpoints/reports.py`
- Impact if unfixed: exported CSV can execute formulas in spreadsheet clients.

Current code (before):
```python
csv_data += f"{emp_id},{name},{date},{first_in},{last_out},{hours}\n"
```

Fixed code:
```python
writer.writerow([
    _safe_csv_cell(emp_id),
    _safe_csv_cell(names[emp_id]),
    _safe_csv_cell(date_str),
    _safe_csv_cell(_fmt_time(first_in_ts)),
    _safe_csv_cell(_fmt_time(last_out_ts)),
    _safe_csv_cell(hours),
])
```

Why this works:
- Formula-leading prefixes are neutralized; newline content is normalized.

Testing:
- Added `test_reports_daily_csv_sanitizes_formula_cells`.

Estimated fix time: `1h` (completed)

### Issue 5 - Public scan endpoint trust boundary (`Open`)
- Severity: `HIGH`
- Category: Security / Architecture
- Location: `app/api/v1/endpoints/employees.py` (`/scan`)
- Impact if unfixed: if endpoint exposed beyond trusted kiosk network, spoofed scans can be injected.

Current behavior:
```python
@router.post("/scan")
async def scan_card(...):
    ...
```

Recommended fix:
```text
Either:
1) require kiosk auth/session/token for /scan and /break/*, or
2) strictly isolate route by network ACL/reverse proxy and deny internet access.
```

Why this matters:
- Payroll-adjacent systems require strict event authenticity.

Testing:
- Pen-test route from untrusted network path and verify denial.

Estimated fix time: `1-2d` (architecture + rollout)

### Issue 6 - Full runtime validation blocked (`Blocked-by-environment`)
- Severity: `HIGH`
- Category: Release Gate
- Location: local runtime environment
- Impact if unresolved: no end-to-end execution evidence for this run.

Observed blocker:
- Docker daemon service unavailable.
- Local Python launcher path mismatch (Windows Store shim), preventing test execution.

Recommended fix:
- Restore Docker Desktop service and a working Python runtime, then run full test plan.

Estimated fix time: `0.5-1d` environment operations

## Medium

### Issue 7 - Absence override write without employee existence pre-check (`Fixed`)
- Severity: `MEDIUM`
- Category: Data Integrity / Error Handling
- Location: `app/api/v1/endpoints/reports.py`
- Fix:
```python
emp_result = await db.execute(select(Employee.id).where(Employee.id == body.employee_id))
if emp_result.scalar_one_or_none() is None:
    raise HTTPException(status_code=404, detail="Employee not found")
```

### Issue 8 - Settings update accepted invalid work windows (`Fixed`)
- Severity: `MEDIUM`
- Category: Functional Correctness
- Location: `app/api/v1/endpoints/settings.py`
- Fix:
```python
if end_time <= start_time:
    raise HTTPException(status_code=422, detail="work_end must be later than work_start in the same day")
```

### Issue 9 - Weak validation on settings/date inputs (`Fixed`)
- Severity: `MEDIUM`
- Category: Input Validation
- Location: `app/schemas/attendance.py`, `app/api/v1/endpoints/reports.py`
- Fixes:
  - strict `HH:MM` and `Â±HH:MM` regex validation
  - strict date parsing and month format checks
  - date range ordering checks

### Issue 10 - Password strength not enforced for user create/update (`Fixed`)
- Severity: `MEDIUM`
- Category: Security
- Location: `app/schemas/user.py`
- Fix:
```python
if len(password) < 10 or not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
    raise ValueError(...)
```

### Issue 11 - Parameter bounds missing (`Fixed`)
- Severity: `MEDIUM`
- Category: API Hardening
- Location: `app/api/v1/endpoints/employees.py`, `app/api/v1/endpoints/reports.py`
- Fixes:
  - `skip`/`limit` query bounds
  - `employee_id` query `ge=1` where relevant

### Issue 12 - Frontend dynamic message rendering sink (`Fixed`)
- Severity: `MEDIUM`
- Category: Frontend Security
- Location: `frontend/js/toast.js`, `frontend/register.html`, `frontend/reports.html`
- Fixes:
  - switched user-provided message rendering to `textContent`
  - safer dropdown population via DOM APIs in reports page

## Low

### Issue 13 - Alembic model import completeness (`Fixed`)
- Severity: `LOW`
- Category: Migration Hygiene
- Location: `migrations/env.py`
- Fix: ensured key model modules are imported for metadata discovery.

### Issue 14 - Duplicate style injection in layout init (`Fixed`)
- Severity: `LOW`
- Category: Frontend Maintainability
- Location: `frontend/js/layout.js`
- Fix: guard style injection by `id` to avoid repeated insertions.

### Issue 15 - Docs/config drift for admin env names (`Fixed`)
- Severity: `LOW`
- Category: Documentation / Ops
- Location: `.env.example`, `README.md`, `CONFIGURATION.md`, `DEPLOYMENT_GUIDE.md`, `INSTALLATION.md`, `TROUBLESHOOTING.md`, `API_DOCUMENTATION.md`
- Fix: aligned to `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD` and documented backward-compatible aliases.

### Issue 16 - Reverse-usage mapping is heuristic (`Open`)
- Severity: `LOW`
- Category: Reporting Accuracy
- Location: `artifacts/file-inventory.csv` generation approach
- Impact: possible false positives/negatives in `UsedBy` references.
- Recommendation: switch to AST/linker-based dependency graph in future tooling.

## Priority Roadmap

### Week 1
1. Close `HIGH` open issue for scan endpoint trust boundary (auth strategy or enforced network isolation).
2. Unblock Docker/Python runtime and execute full integration test plan.
3. Confirm release gate with test evidence + logs.

### Week 2
1. Refactor top-complexity report handlers into smaller service functions.
2. Add CI dependency vulnerability scanning (`pip-audit` / equivalent).
3. Add E2E browser tests for core attendance/admin/report flows.

### Week 3
1. Reduce frontend inline-script/template complexity.
2. Improve inventory tooling from heuristic references to parser-backed graph.
3. Additional performance profiling and caching review under production-like load.


