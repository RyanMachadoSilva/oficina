#!/bin/bash
# Restaura um backup no banco de produção.  ATENÇÃO: substitui os dados atuais.
#   bash scripts/restaurar.sh backups/oficina_20261116_0200.sql.gz
set -euo pipefail
cd "$(dirname "$0")/.."
# Lê só as variáveis necessárias do .env
lerenv() { grep -E "^$1=" .env | head -1 | cut -d= -f2- | tr -d '\r'; }
POSTGRES_USER=$(lerenv POSTGRES_USER); POSTGRES_DB=$(lerenv POSTGRES_DB)
RCLONE_DESTINO=$(lerenv RCLONE_DESTINO); BACKUP_ALERTA_URL=$(lerenv BACKUP_ALERTA_URL)

ARQ="${1:-}"
[ -f "$ARQ" ] || { echo "Uso: bash scripts/restaurar.sh CAMINHO_DO_BACKUP.sql.gz"; exit 1; }
read -r -p "Isso vai SUBSTITUIR os dados atuais por $ARQ. Digite SIM para continuar: " ok
[ "$ok" = "SIM" ] || { echo "Cancelado."; exit 1; }

gunzip -c "$ARQ" | docker compose -f docker-compose.prod.yml exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1
echo "Restaurado."
