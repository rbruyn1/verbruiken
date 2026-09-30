# Changelog

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
