#!/bin/bash

# IntralogisticsAI Backup Script
# Usage: ./scripts/backup.sh [--backup-dir /path/to/backup] [--compress] [--cleanup-days 7]

set -e

# Default settings
BACKUP_DIR="/tmp/backups"
COMPRESS=false
CLEANUP_DAYS=7
DATE=$(date +%Y%m%d_%H%M%S)

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --backup-dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --compress)
            COMPRESS=true
            shift
            ;;
        --cleanup-days)
            CLEANUP_DAYS="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo "  --backup-dir DIR    Backup directory (default: /tmp/backups)"
            echo "  --compress          Compress backup files"
            echo "  --cleanup-days N    Remove backups older than N days (default: 7)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

log_info "Starting backup to: $BACKUP_DIR"

# Get site name
SITE_NAME=$(docker compose exec -T backend ls /home/frappe/frappe-bench/sites | grep -v assets | grep -v common | grep -v apps | head -1)
SITE_NAME=$(echo "$SITE_NAME" | tr -d '\r\n')

if [[ -z "$SITE_NAME" ]]; then
    echo "Error: No Frappe site found"
    exit 1
fi

log_info "Backing up site: $SITE_NAME"

# Database backup
log_info "Creating database backup..."
docker compose exec -T backend bench --site "$SITE_NAME" backup \
    --with-files \
    --backup-path "/tmp/backup_$DATE"

# Copy backup files from container
log_info "Copying backup files..."
docker compose cp backend:/tmp/backup_$DATE/ "$BACKUP_DIR/"

# Rename backup files for consistency
cd "$BACKUP_DIR/backup_$DATE"
if [[ -f *.sql.gz ]]; then
    mv *.sql.gz "database_${DATE}.sql.gz"
fi
if [[ -f *.tar ]]; then
    mv *.tar "files_${DATE}.tar"
fi

# Compress if requested
if [[ "$COMPRESS" == "true" ]]; then
    log_info "Compressing backup..."
    cd "$BACKUP_DIR"
    tar czf "backup_${DATE}.tar.gz" "backup_$DATE/"
    rm -rf "backup_$DATE/"
    log_info "Backup compressed to: backup_${DATE}.tar.gz"
else
    mv "$BACKUP_DIR/backup_$DATE" "$BACKUP_DIR/backup_${DATE}_${SITE_NAME}"
    log_info "Backup saved to: $BACKUP_DIR/backup_${DATE}_${SITE_NAME}/"
fi

# Container volumes backup (optional but recommended)
log_info "Backing up Docker volumes..."
docker run --rm \
    -v intralogisticsai_sites:/source:ro \
    -v "$BACKUP_DIR":/backup \
    alpine tar czf "/backup/volumes_${DATE}.tar.gz" -C /source .

# Cleanup old backups
if [[ "$CLEANUP_DAYS" -gt 0 ]]; then
    log_info "Cleaning up backups older than $CLEANUP_DAYS days..."
    find "$BACKUP_DIR" -name "backup_*" -mtime +$CLEANUP_DAYS -exec rm -rf {} \; 2>/dev/null || true
    find "$BACKUP_DIR" -name "volumes_*" -mtime +$CLEANUP_DAYS -exec rm -f {} \; 2>/dev/null || true
fi

log_info "Backup completed successfully!"

# Backup verification
log_info "Verifying backup integrity..."
if [[ "$COMPRESS" == "true" ]]; then
    tar tzf "$BACKUP_DIR/backup_${DATE}.tar.gz" >/dev/null && log_info "✅ Backup archive is valid"
else
    [[ -f "$BACKUP_DIR/backup_${DATE}_${SITE_NAME}/database_${DATE}.sql.gz" ]] && log_info "✅ Database backup exists"
    [[ -f "$BACKUP_DIR/backup_${DATE}_${SITE_NAME}/files_${DATE}.tar" ]] && log_info "✅ Files backup exists"
fi

[[ -f "$BACKUP_DIR/volumes_${DATE}.tar.gz" ]] && log_info "✅ Volumes backup exists"

echo ""
echo "📦 Backup Summary"
echo "================"
echo "Site: $SITE_NAME"
echo "Date: $(date)"
echo "Location: $BACKUP_DIR"
if [[ "$COMPRESS" == "true" ]]; then
    echo "Size: $(du -h "$BACKUP_DIR/backup_${DATE}.tar.gz" | cut -f1)"
else
    echo "Size: $(du -h "$BACKUP_DIR/backup_${DATE}_${SITE_NAME}" | tail -1 | cut -f1)"
fi
echo ""
echo "To restore this backup:"
echo "  ./scripts/restore.sh $BACKUP_DIR/backup_${DATE}*"