#!/bin/sh
# Roda toda vez que o container do app sobe: espera o banco, aplica migrações e inicia.
set -e

echo "Aguardando o banco de dados..."
python - <<'EOF'
import os, time
import psycopg
for tentativa in range(30):
    try:
        psycopg.connect(
            dbname=os.environ.get("POSTGRES_DB", "oficina"),
            user=os.environ.get("POSTGRES_USER", "oficina"),
            password=os.environ.get("POSTGRES_PASSWORD", "oficina"),
            host=os.environ.get("POSTGRES_HOST", "db"),
            port=os.environ.get("POSTGRES_PORT", "5432"),
            connect_timeout=3,
        ).close()
        break
    except Exception:
        time.sleep(2)
else:
    raise SystemExit("Banco de dados não respondeu.")
EOF

python manage.py migrate --noinput
exec "$@"
