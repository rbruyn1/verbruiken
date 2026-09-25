"""Datamodel voor de verbruik-addon (SQLite)."""
import os
import sqlite3
from pathlib import Path

# In de HA add-on wordt dit naar /data gezet (persistente add-on-config-map,
# overleeft updates). Lokaal draaien/testen valt terug op app/data/.
DB_PATH = Path(os.environ.get("VERBRUIK_DB", Path(__file__).parent / "data" / "verbruik.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS maandverbruik (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    woning TEXT NOT NULL CHECK (woning IN ('Tienen', 'Binkom')),
    jaar INTEGER NOT NULL,
    maand INTEGER NOT NULL CHECK (maand BETWEEN 1 AND 12),

    piek_verbruik REAL,
    dal_verbruik REAL,
    piek_export REAL,
    dal_export REAL,
    totaal_verbruik_afname REAL,
    totaal_export REAL,
    zonopbrengst_totaal REAL,
    batterij_laden REAL,
    batterij_ontladen REAL,

    gas_m3 REAL,
    gas_kwh REAL,
    prijs_gas_eur REAL,
    water_l REAL,

    engie_afname_eur REAL,
    engie_injectie_eur REAL,
    bedrag_engie_app REAL,

    UNIQUE(woning, jaar, maand)
);

CREATE TABLE IF NOT EXISTS jaaroverzicht (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    woning TEXT NOT NULL CHECK (woning IN ('Tienen', 'Binkom')),
    jaar INTEGER NOT NULL,

    jaarverbruik_elektriciteit_kwh REAL,
    jaarverbruik_elektriciteit_kost_eur REAL,

    jaarverbruik_gas REAL,
    jaarverbruik_gas_eenheid TEXT CHECK (jaarverbruik_gas_eenheid IN ('m3', 'kWh')),
    jaarverbruik_gas_kost_eur REAL,

    opladen_zon_kwh REAL,
    opladen_zon_kost_eur REAL,

    uitgespaard_zonnepanelen_eur REAL,

    batterij_gebruik_kwh REAL,
    batterij_gebruik_kost_eur REAL,

    verschil_gas_vorig_jaar_m3 REAL,
    verschil_gas_vorig_jaar_kwh REAL,

    verschil_elektriciteit_vorig_jaar_kwh REAL,
    verschil_elektriciteit_vorig_jaar_eur REAL,

    UNIQUE(woning, jaar)
);
"""


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database geïnitialiseerd op {DB_PATH}")
