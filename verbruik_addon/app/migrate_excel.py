"""Eenmalige migratie: leest de bestaande xlsx (tabs 'verbruiken Tienen'
en 'verbruiken Binkom') in en vult de maandverbruik-tabel.

De rommelige notitiekolommen (tekst als 'verschil gas 2022-2023',
'uitgespaard met zonnepanelen' her en der tussen andere maanden in) horen
bij het jaaroverzicht en worden hier bewust NIET meegenomen — die vul je
zelf in via de UI (zie gesprek: dat is een apart datamodel).

Gebruik:
    python migrate_excel.py /pad/naar/nettarieven_2023.xlsx
"""
import sys
from pathlib import Path
import openpyxl
from models import get_connection, init_db

SHEET_WONING = {
    "verbruiken Tienen": "Tienen",
    "verbruiken Binkom": "Binkom",
}

# Kolomnaam in de Excel -> veldnaam in de databank.
# Alleen ruwe invoervelden; berekende kolommen (zelfverbruik, totaal
# verbruik, prijzen/kWh, ...) slaan we niet op, zie calculations.py.
COLUMN_MAP = {
    "Piek verbruik": "piek_verbruik",
    "Dal verbruik": "dal_verbruik",
    "Piek export": "piek_export",
    "Dal export": "dal_export",
    "totaal export": "totaal_export",
    "totaal verbruik (afname engie)": "totaal_verbruik_afname",
    "zonopbrengst totaal": "zonopbrengst_totaal",
    "batterij laden": "batterij_laden",
    "Batterij laden": "batterij_laden",
    "batterij ontladen": "batterij_ontladen",
    "Batterij ontladen": "batterij_ontladen",
    "Gas m3": "gas_m3",
    "Gas kWh": "gas_kwh",
    "prijs gas": "prijs_gas_eur",
    "water(l)": "water_l",
    "engie injectie €": "engie_injectie_eur",
    "engie afname €": "engie_afname_eur",
    "bedrag engieapp": "bedrag_engie_app",
}


def clean(value):
    if value is None:
        return None
    try:
        f = float(value)
        # xlsx gebruikt soms 0 om "geen data" te betekenen in de rijen na
        # de laatste ingevulde maand (bv. 2026-10 e.v. in dit bestand) —
        # die laten we als None ipv 0, anders vervuilt dat latere
        # jaar-op-jaar-vergelijkingen.
        return f
    except (TypeError, ValueError):
        return None


def migrate(xlsx_path):
    init_db()
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    conn = get_connection()
    inserted, skipped = 0, 0

    for sheet_name, woning in SHEET_WONING.items():
        if sheet_name not in wb.sheetnames:
            print(f"Waarschuwing: tab '{sheet_name}' niet gevonden, overgeslagen")
            continue
        ws = wb[sheet_name]
        headers = [c.value for c in ws[1]]
        col_index = {h: i for i, h in enumerate(headers) if h in COLUMN_MAP}

        for row in ws.iter_rows(min_row=2, values_only=False):
            datum_cell = row[0]
            datum = datum_cell.value
            if datum is None:
                continue
            jaar, maand = datum.year, datum.month

            record = {"woning": woning, "jaar": jaar, "maand": maand}
            for header, idx in col_index.items():
                field = COLUMN_MAP[header]
                record[field] = clean(row[idx].value)

            # Rijen die volledig leeg zijn (toekomstige maanden zonder
            # data, zoals 2026-11/12 in dit bestand) overslaan.
            if all(v is None for k, v in record.items() if k not in ("woning", "jaar", "maand")):
                skipped += 1
                continue

            placeholders = ", ".join(f":{k}" for k in record)
            columns = ", ".join(record.keys())
            conn.execute(
                f"""INSERT INTO maandverbruik ({columns}) VALUES ({placeholders})
                    ON CONFLICT(woning, jaar, maand) DO UPDATE SET
                    {', '.join(f"{k}=excluded.{k}" for k in record if k not in ("woning","jaar","maand"))}
                """,
                record,
            )
            inserted += 1

    conn.commit()
    conn.close()
    print(f"Klaar: {inserted} maandrecords ingeladen, {skipped} lege maanden overgeslagen.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Gebruik: python migrate_excel.py <pad naar xlsx>")
        sys.exit(1)
    migrate(Path(sys.argv[1]))
