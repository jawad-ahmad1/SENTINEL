# 🧪 Testing Guide

## Overview

Sentinel uses **pytest** with **async support** for testing. The test suite covers authentication, RFID scanning, employee CRUD, break tracking, reports, and security hardening.

| Metric | Value |
|--------|-------|
| Total tests | 32 |
| Test files | 7 |
| Framework | pytest + pytest-asyncio + httpx |
| Database | In-memory SQLite (test isolation) |
| Avg runtime | ~15 seconds |

---

## Running Tests

### Quick Start

```bash
# Run all tests
python -m pytest tests/ -v

# Inside Docker
docker compose exec app python -m pytest tests/ -v
```

### Specific Tests

```bash
# Single file
python -m pytest tests/test_scan.py -v

# Single test
python -m pytest tests/test_scan.py::test_scan_creates_in_event -v

# By keyword
python -m pytest tests/ -k "scan" -v
```

### With Coverage

```bash
# Terminal report
python -m pytest tests/ --cov=app --cov-report=term-missing

# HTML report
python -m pytest tests/ --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

---

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures (client, db_session, test user)
├── test_scan.py                   # RFID scan, auto-register, IN/OUT toggle (5 tests)
├── test_employees.py              # Employee CRUD, validation, soft-delete (8 tests)
├── test_breaks.py                 # Break start/end, error handling (5 tests)
├── test_reports.py                # Daily/monthly reports, CSV export (9 tests)
├── test_omega_fuzzer.py           # 250+ random/malicious payloads (3 tests)
└── test_security_hardened.py      # SQL injection, XSS rejection (2 tests)
```

---

## Test Categories

### 1. RFID Scan Tests (`test_scan.py`)

| Test | Description |
|------|-------------|
| `test_scan_creates_in_event` | First scan creates an IN event |
| `test_scan_toggles_out` | Second scan creates an OUT event |
| `test_scan_auto_registers` | Unknown UID auto-creates employee |
| `test_scan_bounce_protection` | Rapid duplicate scans are rejected |
| `test_scan_row_locking` | Concurrent scans don't create duplicates |

### 2. Employee Tests (`test_employees.py`)

| Test | Description |
|------|-------------|
| `test_create_employee` | POST creates employee with valid data |
| `test_create_duplicate_uid` | Duplicate RFID UID is rejected (409) |
| `test_list_employees` | GET returns paginated employee list |
| `test_update_employee` | PUT updates employee fields |
| `test_soft_delete` | DELETE marks inactive, preserves records |
| `test_search_employees` | Search by name/department with LIKE |
| `test_validation_rejects_empty` | Empty required fields return 422 |
| `test_admin_required` | Non-admin users get 403 on CRUD |

### 3. Report Tests (`test_reports.py`)

| Test | Description |
|------|-------------|
| `test_daily_summary` | Returns correct present/absent counts |
| `test_monthly_report` | Aggregates across weekdays only |
| `test_csv_export` | CSV download has correct headers |
| `test_analytics_trends` | Returns 30-day trend data |
| `test_employee_analytics` | Per-employee attendance stats |
| `test_absence_report` | Monthly absence with overrides |
| `test_live_stats` | Real-time dashboard statistics |
| `test_empty_date_range` | Empty results return zeroed stats |
| `test_future_date` | Future dates handled gracefully |

### 4. Security Tests

| Test | Description |
|------|-------------|
| `test_sql_injection_rejected` | SQL injection payloads return 422 |
| `test_xss_payload_rejected` | Script tags in inputs are rejected |
| `test_fuzz_random_payloads` | 250+ random strings don't crash API |
| `test_fuzz_unicode_payloads` | Unicode edge cases handled safely |
| `test_fuzz_overflow_payloads` | Extremely long strings are rejected |

---

## Writing New Tests

### Test Template

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_feature_description(client: AsyncClient, db_session):
    """Clear description of what this test verifies."""
    # Arrange — set up test data
    employee = await create_test_employee(db_session, uid="TEST001")

    # Act — perform the action
    response = await client.post(
        "/api/v1/scan",
        json={"uid": "TEST001", "type": "IN"},
    )

    # Assert — verify the result
    assert response.status_code == 200
    data = response.json()
    assert data["event_type"] == "IN"
    assert data["employee_name"] == employee.name
```

### Fixtures (from `conftest.py`)

| Fixture | Description |
|---------|-------------|
| `client` | Async HTTP client with auth cookies |
| `db_session` | Isolated database session (rolled back after test) |
| `test_user` | Pre-created admin user for authentication |
| `test_employee` | Pre-created employee with RFID UID |

### Best Practices

1. **One assertion per concept** — test one behavior at a time
2. **Descriptive names** — `test_scan_bounce_rejects_duplicate_within_window`
3. **Arrange-Act-Assert** — clear three-part structure
4. **Isolation** — each test runs in its own DB transaction (rolled back)
5. **Happy + sad paths** — test both success and error cases
6. **No external deps** — tests use in-memory SQLite, no Redis/network needed

---

## Continuous Integration

### GitHub Actions (Example)

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: python -m pytest tests/ -v --tb=short
```

---

## Quality Gates

Before merging a PR, all of these must pass:

| Check | Command | Threshold |
|-------|---------|-----------|
| Tests | `pytest tests/ -v` | 100% pass |
| Lint | `flake8 app --select=F` | 0 warnings |
| Quality | `pylint app --disable=C,R` | ≥ 9.5/10 |
| Security | `bandit -r app -ll` | 0 Medium/High |
| Format | `black --check app tests` | 0 changes |
| Types | `mypy app --ignore-missing-imports` | No errors (except stubs) |

---

[← Back to README](README.md)
