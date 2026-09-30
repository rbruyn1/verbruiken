#!/usr/bin/with-contenv bashio
cd /app
export VERBRUIK_DB=/data/verbruik.db

# Eenmalige seed: bij een verse install (persistente /data-map nog leeg)
# de meegeleverde, al-gemigreerde databank overnemen. Nadien blijft
# /data leidend en wordt dit nooit meer overschreven, dus latere
# invoer via de UI gaat niet verloren bij een update.
if [ ! -f /data/verbruik.db ] && [ -f /app/data/verbruik.db ]; then
    bashio::log.info "Eerste opstart: bestaande data-seed overnemen naar /data"
    cp /app/data/verbruik.db /data/verbruik.db
fi

python3 -c "from models import init_db; init_db()"
exec python3 main.py
