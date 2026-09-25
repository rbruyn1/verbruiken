# Verbruik Tienen/Binkom — Home Assistant add-on

Eigen add-on voor de maandelijkse en jaarlijkse energie/gas/water-registratie
van beide woningen (Tienen en Binkom), gebaseerd op nettarieven_2023.xlsx.

## Installatie als HA add-on

1. Kopieer deze hele map naar `/addons/verbruik_addon/` op je HA-instantie
   (via Samba-share of de SSH/terminal add-on).
2. Ga in HA naar Instellingen → Add-ons → Add-on store → vernieuw (⋮ rechtsboven).
3. De add-on verschijnt onder "Local add-ons" → installeren → starten.
4. Via ingress verschijnt "Verbruik" in het linkermenu van HA.

## Eenmalige migratie van je bestaande Excel

Na de eerste start (add-on-databank bestaat dan als leeg bestand):

    docker exec -it addon_verbruik_addon python3 migrate_excel.py /pad/naar/nettarieven_2023.xlsx

Zet het xlsx-bestand vooraf ergens bereikbaar in de container (bv. via de
`addon_config:rw` map die in config.yaml gemapt is), of kopieer het met
`docker cp` naar de container.

## Lokaal testen (buiten HA)

    cd app
    pip install flask openpyxl
    python3 migrate_excel.py /pad/naar/nettarieven_2023.xlsx   # eenmalig
    python3 main.py
    # open http://localhost:8099

## Structuur

- `app/models.py` — SQLite-schema (maandverbruik, jaaroverzicht)
- `app/calculations.py` — afgeleide waarden, geverifieerd tegen originele Excel-formules
- `app/migrate_excel.py` — eenmalige import van bestaande Excel-historiek
- `app/main.py` — Flask-app (overzicht, invoerformulieren)
- `config.yaml`, `Dockerfile`, `run.sh` — HA add-on-wrapper

## Bekende afwijking t.o.v. Excel

"Totaal verbruik (afname)" en "totaal export" zijn in de Excel niet altijd
gelijk aan piek+dal — voor sommige maanden staat er een apart ingevoerd
Engie-factuurcijfer. Daarom zijn dit ruwe invoervelden, geen berekende
som. Vul ze dus zelf in vanaf de factuur, niet als piek+dal opgeteld.
