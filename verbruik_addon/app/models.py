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
    batterij_laden_kwh REAL,
    batterij_gebruik_kost_eur REAL,
    vaste_kost_uur REAL,
    uitgespaard_excel_eur REAL,
    batterij_gebruik_kost_excel_eur REAL,

    verschil_gas_vorig_jaar_m3 REAL,
    verschil_gas_vorig_jaar_kwh REAL,

    verschil_elektriciteit_vorig_jaar_kwh REAL,
    verschil_elektriciteit_vorig_jaar_eur REAL,

    UNIQUE(woning, jaar)
);

-- Welke bron uit het Energiedashboard van Home Assistant bij welk formulierveld hoort
CREATE TABLE IF NOT EXISTS energie_koppeling (
    woning TEXT NOT NULL,
    statistic_id TEXT NOT NULL,
    veld TEXT NOT NULL,
    PRIMARY KEY (woning, statistic_id)
);

-- Welke standaardkoppelingen al eens zijn toegepast, zodat een veld dat je zelf leegmaakt leeg blijft
CREATE TABLE IF NOT EXISTS koppeling_seed (
    woning TEXT NOT NULL,
    veld TEXT NOT NULL,
    PRIMARY KEY (woning, veld)
);
"""


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


NIEUWE_JAAR_KOLOMMEN = {
    "batterij_laden_kwh": "REAL",
    "vaste_kost_uur": "REAL",
    "uitgespaard_excel_eur": "REAL",
    "batterij_gebruik_kost_excel_eur": "REAL",
}

# Vaste bijdrage die de Engie-app aanrekent (€ per uur, ook bij 0 kWh afname).
STANDAARD_VASTE_KOST_UUR = {"Tienen": 0.03, "Binkom": 0.05}


def _ensure_columns(conn):
    """Lichte schema-migratie: voegt kolommen toe die in SCHEMA staan maar
    nog niet in een bestaande (al-gemigreerde) databank zitten. SQLite's
    CREATE TABLE IF NOT EXISTS raakt een reeds bestaande tabel niet aan."""
    bestaand = {row[1] for row in conn.execute("PRAGMA table_info(jaaroverzicht)")}
    for kolom, type_ in NIEUWE_JAAR_KOLOMMEN.items():
        if kolom not in bestaand:
            conn.execute(f"ALTER TABLE jaaroverzicht ADD COLUMN {kolom} {type_}")


def _migratie_v1(conn):
    """Eenmalig (PRAGMA user_version): de variabele-prijsberekening vervangt
    de oude Excel-bedragen voor 'uitgespaard' en 'batterij €' (die rekenden
    met de bruto prijs, vaste kosten inbegrepen). De oude bedragen blijven
    bewaard in aparte kolommen; de hoofdkolommen worden leeg zodat de nieuwe
    berekening het overneemt. Daarna zijn manuele invoeren weer gewoon
    voorrangswaarden. De vaste kost wordt enkel ingevuld waar nog leeg."""
    if conn.execute("PRAGMA user_version").fetchone()[0] >= 1:
        return
    conn.execute(
        """UPDATE jaaroverzicht
           SET uitgespaard_excel_eur = uitgespaard_zonnepanelen_eur,
               uitgespaard_zonnepanelen_eur = NULL
           WHERE uitgespaard_zonnepanelen_eur IS NOT NULL AND uitgespaard_excel_eur IS NULL"""
    )
    conn.execute(
        """UPDATE jaaroverzicht
           SET batterij_gebruik_kost_excel_eur = batterij_gebruik_kost_eur,
               batterij_gebruik_kost_eur = NULL
           WHERE batterij_gebruik_kost_eur IS NOT NULL AND batterij_gebruik_kost_excel_eur IS NULL"""
    )
    for woning, tarief in STANDAARD_VASTE_KOST_UUR.items():
        conn.execute(
            "UPDATE jaaroverzicht SET vaste_kost_uur = ? WHERE woning = ? AND vaste_kost_uur IS NULL",
            (tarief, woning),
        )
    conn.execute("PRAGMA user_version = 1")


# Standaardkoppeling voor Tienen (gecontroleerd tegen de opgeslagen maanden: augustus komt exact overeen).
# P1-meter in de kelder: tarief 1 = dag/piek, tarief 2 = nacht/dal. Zon = SolarEdge-omvormer Tienen.
STANDAARD_KOPPELING = {
    "Tienen": {
        "sensor.p1_total_power_import_t1": "piek_verbruik",
        "sensor.p1_total_power_import_t2": "dal_verbruik",
        "sensor.p1_total_power_export_t1": "piek_export",
        "sensor.p1_total_power_export_t2": "dal_export",
        "sensor.solaredge_ac_energy_kwh": "zonopbrengst_totaal",
    },
}


def _seed_koppeling(conn):
    """Zet een standaardbron op een veld, maar enkel de eerste keer en enkel als dat veld voor die woning
    nog leeg is. Wat je zelf instelt of leegmaakt, blijft dus zoals jij het wil."""
    for woning, bronnen in STANDAARD_KOPPELING.items():
        for sid, veld in bronnen.items():
            gedaan = conn.execute("SELECT 1 FROM koppeling_seed WHERE woning=? AND veld=?",
                                  (woning, veld)).fetchone()
            if gedaan:
                continue
            bezet = conn.execute("SELECT 1 FROM energie_koppeling WHERE woning=? AND veld=?",
                                 (woning, veld)).fetchone()
            if not bezet:
                conn.execute(
                    "INSERT OR IGNORE INTO energie_koppeling (woning, statistic_id, veld) VALUES (?, ?, ?)",
                    (woning, sid, veld),
                )
            conn.execute("INSERT OR IGNORE INTO koppeling_seed (woning, veld) VALUES (?, ?)", (woning, veld))


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    _ensure_columns(conn)
    _migratie_v1(conn)
    _seed_koppeling(conn)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database geïnitialiseerd op {DB_PATH}")
