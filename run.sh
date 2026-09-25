#!/usr/bin/with-contenv bashio
cd /app
export VERBRUIK_DB=/data/verbruik.db
python3 -c "from models import init_db; init_db()"
exec python3 main.py
