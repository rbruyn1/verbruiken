# Changelog

## 0.2.0
- Grafieken-pagina: maandtabel toegevoegd onderaan (zelfde als op
  Maandoverzicht), en een nieuwe "Jaartotalen"-grafiek (elektriciteit
  afname, gas, zonopbrengst per jaar — berekend uit de maanddata).
- Jaaroverzicht-pagina: maandtabel ook daar onderaan toegevoegd.

## 0.1.9
- "Verschil -1 jaar" (elektriciteit en gas) wordt nu, als er geen losse
  Excel-notitie voor was, automatisch berekend uit de al-ingevoerde
  maanddata (dit jaar t.o.v. vorig jaar). Vult zo Tienen 2021 en 2022
  aan. Berekende waarden krijgen een `*` met tooltip ter onderscheid
  van de rechtstreeks uit de Excel overgenomen cijfers.

## 0.1.8
- Jaaroverzicht-data uit de Excel gemigreerd (Tienen 2021-2026, Binkom
  2025-2026) — stond verspreid als losse cellen tussen de maandrijen,
  nu overgenomen in de jaaroverzicht-tabel. Zie
  `app/migrate_jaaroverzicht.py` voor de precieze celverwijzingen en
  onderbouwing.
  - Tienen 2021 en 2022 hebben geen "verschil -1 jaar"-cijfers: de
    enige cellen die daarvoor in aanmerking kwamen droegen een
    foutief/verouderd label ("2022-2023" in een rij die 2021 of 2022
    voorstelt) en zijn daarom bewust weggelaten i.p.v. gegokt.
  - Binkoms "verschil elektriciteit"-cijfer voor 2026 is letterlijk
    gelabeld "2024-2026" in de Excel (2-jaars-span) — ongewijzigd
    overgenomen.
- Bugfix: jaaroverzicht-pagina crashte op een jaar zonder ingevulde
  gas- of zonopladen-kost (None / aantal-maanden deling).

## 0.1.7
- Binkom staat nu als eerste tab en is de standaardweergave (was Tienen)
  — logisch gezien de aankomende verhuis.

## 0.1.6
- Nieuw: "Grafieken"-pagina, dezelfde 3 grafieken als in de originele
  Excel — gasverbruik (bar), elektriciteitsverbruik piek+dal gestapeld
  (bar), en verschil -1 jaar elektriciteit/gas (lijn). Binkom toont
  geen gasgrafiek (geen gasaansluiting). Chart.js is lokaal gebundeld
  (`static/vendor/chart.min.js`), geen CDN-afhankelijkheid.

## 0.1.5
- Nieuw: "Data herstellen"-pagina (rechtsboven in de nav) om de
  meegeleverde, al-gemigreerde databank alsnog te herstellen als de
  actieve databank leeg/onvolledig bleek (bv. door test-invoer vóór de
  0.1.4-seedfix). Maakt eerst een backup van de huidige inhoud.
- "Totaal verbruik/afname" en "totaal export" in het maand-invoerformulier
  vullen zich nu automatisch (piek+dal) terwijl je typt, blijven wel
  overschrijfbaar voor een afwijkend factuurcijfer (dubbelklik = terug
  naar auto).

## 0.1.4
- Fix: meegeleverde, al-gemigreerde databank werd genegeerd op een verse
  install — `/data/verbruik.db` (persistente map) bleef leeg terwijl de
  data wél in de image zat. `run.sh` seedt nu eenmalig vanuit de
  meegeleverde databank als `/data` nog leeg is.

## 0.1.3
- Fix: nav-links braken uit de ingress-iframe naar de kale HA-interface
  (Flask respecteerde de `X-Ingress-Path`-header van Supervisor niet).

## 0.1.2
- Fix: `s6-overlay-suexec: fatal: can only run as pid 1` — `init: false`
  toegevoegd aan config.yaml (baseimage brengt al eigen s6-init mee).

## 0.1.1
- Fix: `build.yaml` toegevoegd (BUILD_FROM per architectuur ontbrak).
- Dockerfile vereenvoudigd op de `-base-python`-baseimage.

## 0.1.0
- Eerste versie: maand- en jaaroverzicht voor Tienen en Binkom,
  bestaande Excel-historiek gemigreerd.
