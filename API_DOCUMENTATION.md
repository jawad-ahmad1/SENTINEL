# 📡 API Documentation

## Overview

All endpoints are prefixed with `/api/v1`. Interactive Swagger docs are available at `/docs`.

| Property | Value |
|----------|-------|
| Base URL | `https://attendance.company.com/api/v1` |
| Auth | JWT tokens in HttpOnly cookies |
| Format | JSON |
| Rate Limit | 5/min (login), 100/min (general API) |

---

## Authentication

### POST `/auth/login`

Authenticate and receive JWT cookies.

**Auth:** Public · **Rate Limit:** 5/min

**Request:**
```bash
curl -X POST "http://localhost/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@company.com&password=yourpassword" \
  -c cookies.txt
```

**Response (200):**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

Cookies set: `access_token` (30min), `refresh_token` (7d) — both HttpOnly.

**Errors:**
- `401` — Invalid credentials
- `429` — Rate limit exceeded

---

### POST `/auth/refresh`

Rotate the access token using the refresh cookie.

**Auth:** Refresh cookie · **Rate Limit:** 10/min

```bash
curl -X POST "http://localhost/api/v1/auth/refresh" -b cookies.txt -c cookies.txt
```

---

### POST `/auth/logout`

Clear authentication cookies.

```bash
curl -X POST "http://localhost/api/v1/auth/logout" -b cookies.txt
```

---

### GET `/auth/me`

Get the currently authenticated user.

**Auth:** Required

```bash
curl "http://localhost/api/v1/auth/me" -b cookies.txt
```

**Response (200):**
```json
{
  "id": 1,
  "email": "admin@company.com",
  "role": "admin",
  "is_active": true
}
```

---

## RFID Scanning

### POST `/scan`

Record an RFID scan. Auto-toggles IN/OUT and auto-registers unknown cards.

**Auth:** Required

```bash
curl -X POST "http://localhost/api/v1/scan" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"uid": "AB12CD34", "type": "kiosk"}'
```

**Response (200):**
```json
{
  "employee_id": 42,
  "employee_name": "John Doe",
  "event_type": "IN",
  "timestamp": "2026-02-25T09:00:15",
  "message": "Welcome, John Doe!"
}
```

**Errors:**
- `409` — Bounce window (duplicate scan within configured seconds)
- `422` — Invalid UID format

---

## Employees

### GET `/employees`

List all employees (paginated).

**Auth:** Required

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | int | No | Page number (default: 1) |
| `limit` | int | No | Items per page (default: 50) |
| `search` | string | No | Search by name/department |
| `department` | string | No | Filter by department |

```bash
curl "http://localhost/api/v1/employees?page=1&limit=10&search=john" -b cookies.txt
```

**Response (200):**
```json
{
  "items": [
    {
      "id": 42,
      "uid": "AB12CD34",
      "name": "John Doe",
      "email": "john@company.com",
      "department": "Engineering",
      "position": "Developer",
      "phone": "+92-300-1234567",
      "is_active": true,
      "created_at": "2026-01-15T10:00:00"
    }
  ],
  "total": 75,
  "page": 1,
  "pages": 8
}
```

### POST `/employees`

Create a new employee.

**Auth:** Admin only

```bash
curl -X POST "http://localhost/api/v1/employees" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "uid": "NEW_RFID_UID",
    "name": "Jane Smith",
    "email": "jane@company.com",
    "department": "Sales",
    "position": "Manager",
    "phone": "+92-300-9876543"
  }'
```

### PUT `/employees/{id}`

Update an employee.

**Auth:** Admin only

```bash
curl -X PUT "http://localhost/api/v1/employees/42" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"department": "Marketing", "position": "Senior Manager"}'
```

### DELETE `/employees/{id}`

Soft-delete an employee (preserves attendance records).

**Auth:** Admin only

```bash
curl -X DELETE "http://localhost/api/v1/employees/42" -b cookies.txt
```

---

## Reports & Analytics

### GET `/attendance/today`

Today's attendance feed for the kiosk display.

**Auth:** Public

```bash
curl "http://localhost/api/v1/attendance/today"
```

### GET `/reports/summary/{date}`

Daily attendance summary.

**Auth:** Required

```bash
curl "http://localhost/api/v1/reports/summary/2026-02-25" -b cookies.txt
```

**Response (200):**
```json
{
  "date": "2026-02-25",
  "total_employees": 75,
  "present": 68,
  "absent": 7,
  "late": 5,
  "on_time": 63,
  "attendance_rate": 90.7,
  "employees": [...]
}
```

### GET `/reports/monthly/{year}/{month}`

Monthly attendance report (weekday-aware).

**Auth:** Required

```bash
curl "http://localhost/api/v1/reports/monthly/2026/2" -b cookies.txt
```

### GET `/reports/absence/{year}/{month}`

Monthly absence report with daily breakdown.

**Auth:** Required

```bash
curl "http://localhost/api/v1/reports/absence/2026/2" -b cookies.txt
```

### GET `/reports/daily/csv?date_str=YYYY-MM-DD`

Export daily report as CSV.

**Auth:** Required

```bash
curl "http://localhost/api/v1/reports/daily/csv?date_str=2026-02-25" \
  -b cookies.txt -o report.csv
```

### GET `/reports/live-stats`

Real-time dashboard statistics (cached 15s in Redis).

**Auth:** Required

```bash
curl "http://localhost/api/v1/reports/live-stats" -b cookies.txt
```

### GET `/analytics/trends?days=30`

Attendance trends over a time period.

**Auth:** Required

```bash
curl "http://localhost/api/v1/analytics/trends?days=30" -b cookies.txt
```

### GET `/analytics/employee/{id}`

Per-employee attendance analytics.

**Auth:** Required

```bash
curl "http://localhost/api/v1/analytics/employee/42" -b cookies.txt
```

---

## Breaks

### POST `/break/start`

Start a break for an employee.

**Auth:** Required

```bash
curl -X POST "http://localhost/api/v1/break/start" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"uid": "AB12CD34"}'
```

### POST `/break/end`

End a break for an employee.

**Auth:** Required

```bash
curl -X POST "http://localhost/api/v1/break/end" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"uid": "AB12CD34"}'
```

---

## System

### GET `/health`

Health check (database + Redis connectivity).

**Auth:** Public

```bash
curl "http://localhost/api/v1/health"
```

**Response (200):**
```json
{
  "status": "healthy",
  "database": "ok",
  "redis": "ok"
}
```

---

## Error Format

All errors follow this structure:

```json
{
  "detail": "Human-readable error message"
}
```

| Status | Meaning |
|--------|---------|
| `400` | Bad request (invalid parameters) |
| `401` | Unauthorized (missing/expired token) |
| `403` | Forbidden (insufficient role) |
| `404` | Not found |
| `409` | Conflict (duplicate scan, duplicate UID) |
| `422` | Validation error (Pydantic) |
| `429` | Rate limit exceeded |
| `500` | Internal server error |

---

## Code Examples

### Python

```python
import requests

session = requests.Session()

# Login
session.post("http://localhost/api/v1/auth/login", data={
    "username": "admin@company.com",
    "password": "yourpassword"
})

# Get employees
response = session.get("http://localhost/api/v1/employees")
employees = response.json()["items"]

for emp in employees:
    print(f"{emp['name']} ({emp['department']})")
```

### JavaScript

```javascript
// Login
await fetch('/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: 'username=admin@company.com&password=yourpassword',
  credentials: 'include'
});

// Get employees
const res = await fetch('/api/v1/employees', { credentials: 'include' });
const { items } = await res.json();
console.log(items);
```

---

[← Back to README](README.md)
