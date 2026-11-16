#!/bin/bash
# Backup do banco. Agende no cron da VPS (todo dia às 2h):
#   0 2 * * * cd /home/ryan/oficina && bash scripts/backup.sh >> backups/backup.log 2>&1
set -uo pipefail
cd "$(dirname "$0")/.."
# Lê só as variáveis necessárias do .env
lerenv() { grep -E "^$1=" .env | head -1 | cut -d= -f2- | tr -d '\r'; }
POSTGRES_USER=$(lerenv POSTGRES_USER); POSTGRES_DB=$(lerenv POSTGRES_DB)
RCLONE_DESTINO=$(lerenv RCLONE_DESTINO); BACKUP_ALERTA_URL=$(lerenv BACKUP_ALERTA_URL)

mkdir -p backups
ARQ="backups/oficina_$(date +%Y%m%d_%H%M).sql.gz"
COMPOSE="docker compose -f docker-compose.prod.yml"

avisar() {  # $1 = "" (sucesso) ou "/fail"
  [ -n "${BACKUP_ALERTA_URL:-}" ] && curl -fsS -m 10 "${BACKUP_ALERTA_URL}$1" >/dev/null 2>&1 || true
}

echo "[$(date '+%F %T')] Iniciando backup"
if ! $COMPOSE exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists | gzip > "$ARQ"; then
  echo "ERRO no pg_dump"; rm -f "$ARQ"; avisar "/fail"; exit 1
fi
if [ "$(stat -c%s "$ARQ")" -lt 1000 ]; then
  echo "ERRO: arquivo de backup pequeno demais"; avisar "/fail"; exit 1
fi

# Mantém 30 dias na VPS
find backups -name 'oficina_*.sql.gz' -mtime +30 -delete

# Envia para fora da VPS (Google Drive, Backblaze...) se configurado
if [ -n "${RCLONE_DESTINO:-}" ]; then
  if ! rclone copy "$ARQ" "$RCLONE_DESTINO"; then echo "ERRO no envio rclone"; avisar "/fail"; exit 1; fi
  rclone delete "$RCLONE_DESTINO" --min-age 90d >/dev/null 2>&1 || true
fi

echo "[$(date '+%F %T')] OK: $ARQ"
avisar ""
