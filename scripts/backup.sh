#!/bin/bash
# ─────────────────────────────────────────────────────────────────────
# Sentinel RFID Attendance System — Automated Backup
# Schedule: daily at 02:00 via crontab
#   0 2 * * * /opt/attendance/scripts/backup.sh >> /var/log/sentinel-backup.log 2>&1
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

COMPOSE_FILE="/opt/attendance/docker-compose.yml"
BACKUP_DIR="/opt/attendance/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

# Backup PostgreSQL database
docker compose -f "$COMPOSE_FILE" exec -T db \
  pg_dump -U sentinel attendance | gzip > "$BACKUP_DIR/db_${DATE}.sql.gz"
echo "[$(date)] Database backup: db_${DATE}.sql.gz"

# Backup configuration files (not code — that's in git)
tar -czf "$BACKUP_DIR/config_${DATE}.tar.gz" \
  /opt/attendance/.env \
  /opt/attendance/nginx/nginx.conf \
  /opt/attendance/docker-compose.yml \
  2>/dev/null || true
echo "[$(date)] Config backup: config_${DATE}.tar.gz"

# Prune old backups
find "$BACKUP_DIR" -name "*.gz" -type f -mtime +${RETENTION_DAYS} -delete
echo "[$(date)] Pruned backups older than ${RETENTION_DAYS} days"

echo "[$(date)] Backup completed successfully"
