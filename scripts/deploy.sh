#!/bin/bash
# Atualiza o sistema na VPS com a última versão do GitHub.
#   bash scripts/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/.."
git pull --ff-only
docker compose -f docker-compose.prod.yml up -d --build
docker image prune -f >/dev/null
sleep 10   # tempo para o app subir e aplicar as migrações
docker compose -f docker-compose.prod.yml ps
echo "----- últimas linhas do app -----"
docker compose -f docker-compose.prod.yml logs app --tail 20
