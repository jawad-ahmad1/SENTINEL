#!/bin/bash
# ─────────────────────────────────────────────────────────────────────
# Sentinel RFID Attendance System — Health Monitor
# Schedule: every 5 minutes via crontab
#   */5 * * * * /opt/attendance/scripts/monitor.sh
# ─────────────────────────────────────────────────────────────────────
set -uo pipefail

COMPOSE_FILE="/opt/attendance/docker-compose.yml"
ALERT_EMAIL="${ALERT_EMAIL:-admin@company.com}"
HOSTNAME=$(hostname)

alert() {
  local subject="[Sentinel/$HOSTNAME] $1"
  local body="$2"
  echo "$body" | mail -s "$subject" "$ALERT_EMAIL" 2>/dev/null || \
    echo "[$(date)] ALERT (mail failed): $subject — $body"
}

# Check all containers are running and healthy
for svc in db redis app nginx; do
  STATUS=$(docker compose -f "$COMPOSE_FILE" ps "$svc" --format '{{.Status}}' 2>/dev/null)
  if [[ ! "$STATUS" =~ "Up" ]]; then
    alert "$svc DOWN" "Container $svc is not running. Status: $STATUS"
  fi
done

# Check health endpoint
HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 10 http://localhost:8000/api/v1/health 2>/dev/null || echo "000")
if [ "$HTTP_CODE" != "200" ]; then
  alert "Health check failed" "GET /api/v1/health returned HTTP $HTTP_CODE"
fi

# Check disk space
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 85 ]; then
  alert "Disk space warning" "Root partition at ${DISK_USAGE}% usage"
fi

# Check backup freshness (warn if no backup in last 26 hours)
LATEST_BACKUP=$(find /opt/attendance/backups -name "db_*.sql.gz" -mmin -1560 2>/dev/null | head -1)
if [ -z "$LATEST_BACKUP" ]; then
  alert "Backup stale" "No database backup found in the last 26 hours"
fi
