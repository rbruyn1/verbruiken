# Changelog

## 0.2.22
- Jaaroverzicht: kolom "Zonopbrengst (kWh)" (totale opbrengst van het
  jaar, som van de maanden) toegevoegd als eerste kolom van het zonblok.

## 0.2.21
- Jaaroverzicht: kolom "Zelfverbruik (kWh)" toegevoegd (zonopbrengst -
  export, uit de maandsommen), tussen Zon export en Uitgespaard.

## 0.2.20
- Maandoverzicht: kolom "Zelfverbruik" (kWh, = zonopbrengst - export)
  toegevoegd naast het bestaande percentage.

## 0.2.19
- Grafieken: zonopbrengst en zelfverbruik zon waren allebei groen terwijl
  het verschillende grootheden zijn (zelfverbruik is een deel van de
  opbrengst). Zonopbrengst is nu teal, zelfverbruik blijft groen.

## 0.2.18
- Grafieken: één centraal kleurenpalet. Gas is nu overal paars (was
  oranje in "Gasverbruik", "Jaartotalen" en "verschil -1 jaar", wat
  botste met Dal); piek = blauw, dal = oranje, zon/zelfverbruik = groen.

## 0.2.17
- Tabellen herordend per thema: net → zon → batterij → kosten/vergelijking,
  met gas als laatste blok en dunne scheidingslijnen tussen de blokken.
  Jaaroverzicht: "Δ elek vs -1j" staat nu naast de elektriciteitskolommen
  i.p.v. helemaal rechts.
- Maandoverzicht: "Δ gas vs -1j" en "Gas m³" toegevoegd (naast Gas kWh).
- Gaskolommen en -invoervelden worden nu data-gedreven getoond: zodra een
  woning in zijn historiek gasdata heeft (Tienen) blijven ze zichtbaar,
  ook als er later geen nieuwe gasmaanden meer bijkomen; woningen zonder
  gasdata (Binkom) tonen ze niet. Vervangt de hardgecodeerde Binkom-check.

## 0.2.16
- Vorige wijziging teruggedraaid: de oorspronkelijke "Jaartotalen"-grafiek
  (elektriciteit afname/gas/zon) staat terug. De piek/dal/zelf/gas-versie
  is een aparte extra grafiek geworden i.p.v. een vervanging.

## 0.2.15
- "Jaartotalen"-grafiek toont nu dezelfde opbouw als "Totaal
  energieverbruik": piek + dal (net) + zelfverbruik zon + gas
  gestapeld, per jaar i.p.v. de vorige simpelere afname/gas/zon-weergave.

## 0.2.14
- Fix: grafieken hadden geen vaste hoogte, waardoor een grafiek die de
  volle breedte kreeg (bv. "Jaartotalen" bij Binkom, oneven aantal
  grafieken) onevenredig hoog uitviel. Alle grafiekkaarten hebben nu
  een vaste hoogte (320px), ongeacht hun breedte.
- Nieuwe grafiek "Totaal energieverbruik (kWh)": piek + dal (net) +
  zelfverbruik zon + gas gestapeld per maand, voor een volledig beeld
  van het werkelijke energieverbruik over alle bronnen heen.

## 0.2.13
- Alle gas-gerelateerde kolommen en invoervelden verborgen voor Binkom
  (geen gasaansluiting): maandtabel, jaaroverzicht-tabel, en beide
  invoerformulieren (live togglend bij het wisselen van woning in de
  dropdown, niet enkel bij het laden van de pagina). De grafieken
  verborgen de gasgrafiek al eerder.

## 0.2.12
- Layout: pagina is breder (max 1600px i.p.v. 1100px) en tabellen zitten
  nu in hun eigen scrollbaar kader (kleinere letter, minder padding)
  i.p.v. dat de hele pagina moest scrollen om brede tabellen te zien —
  vooral merkbaar bij het jaaroverzicht met veel kolommen.

## 0.2.11
- "Uitgespaard met zonnepanelen" wordt nu automatisch berekend (fallback,
  overschrijfbaar) als `(jaarprijs afname × zelfverbruik) + (jaarprijs
  injectie × export)` — zelfde opbouw als de Excel-formule, maar met de
  prijzen van het juiste jaar. De Excel-waarde voor 2026 bleek zelf een
  sleepfout te bevatten (gebruikte voor 11 van de 12 maanden de prijzen
  van 2025 i.p.v. 2026); die blijft gewoon staan als manueel ingevulde
  waarde (voorrang op auto), maar nieuwe/lege jaren krijgen de correcte
  berekening.
- Bugfix: crash wanneer injectie-€ ontbrak terwijl export wel > 0 was.

## 0.2.10
- Jaaroverzicht: aparte "Gas (m³)"-kolom toegevoegd naast de bestaande
  kWh-waarde — automatisch berekend uit de som van de maandelijkse
  gas-m³-invoer.

## 0.2.9
- Verbruikscijfers (kWh/m³) in de maand- en jaaroverzichtstabellen tonen
  nu consequent 2 cijfers na de komma, i.p.v. de eerdere mix van 0/1
  decimalen.

## 0.2.8
- Jaaroverzicht-invoerformulier: dubbelklik op een auto-berekend veld
  maakt het leeg (terug naar automatische berekening bij opslaan), met
  de huidige berekende waarde als placeholder ter referentie — zelfde
  patroon als bij het maand-invoerformulier.
- Interne refactor: de jaaroverzicht-berekeningslogica zit nu in
  herbruikbare functies (`_jaartotalen_componenten`,
  `_bereken_jaaroverzicht`), gedeeld tussen de overzichtspagina en het
  invoerformulier.

## 0.2.7
- Jaaroverzicht: alle auto-berekende velden (elektriciteit kWh/€, zon
  export, batterij laden/ontladen, verschil -1 jaar elektriciteit) zijn
  terug manueel overschrijfbaar via "+ Jaar invoeren" / "bewerk" — nodig
  omdat Engie (energieapp) soms een paar dagen achterloopt op de
  realiteit. Fallback-gedrag: een manueel ingevulde waarde heeft altijd
  voorrang op de berekende som; auto-waarden krijgen een `*` ter
  onderscheid.
- Nieuwe kolom `batterij_laden_kwh` in de databank (met automatische
  schema-migratie voor bestaande installaties).

## 0.2.6
- "Opladen zon" bleek zon-export te zijn (export naar het net), geen
  batterijlading — geverifieerd tegen `totaal_export`/`engie_injectie_eur`
  (klopt tot op afrondingsniveau). Hernoemd naar "Zon export (kWh)" en
  nu ook automatisch berekend uit de maandsommen; uit het
  invoerformulier gehaald.

## 0.2.5
- Jaaroverzicht: "Batterij laden" toegevoegd naast "ontladen" (beide nu
  automatisch berekend uit de maandsommen), kolom hernoemd naar
  "Batterij laden/ontladen (kWh)" met het €-bedrag ernaast apart.
- Bugfix: jaaroverzicht crashte op jaren zonder batterijdata (ontbrekende
  dict-sleutel werd door Jinja niet als "leeg" herkend).

## 0.2.4
- Jaaroverzicht: alle elektrische waarden die betrouwbaar uit de
  maandsommen af te leiden zijn, worden nu altijd automatisch berekend
  i.p.v. de losse Excel-notitie te tonen — jaarverbruik elektriciteit
  (kWh + €), batterijgebruik (kWh), en verschil -1 jaar elektriciteit
  (kWh). Deze velden zijn uit het invoerformulier gehaald (niet meer
  nodig). "Opladen zon" blijft manueel: dat cijfer komt niet overeen
  met de `batterij_laden`-kolom in de maanddata (~1,9x verschil), dus
  is het kennelijk een apart gemeten grootheid.

## 0.2.3
- Gas (kWh) vult zich nu automatisch in op basis van gas (m³) in het
  maand-invoerformulier. Gebruikt de laatst gekende werkelijke
  omzetfactor uit je eigen data — géén vaste online constante, want
  die factor blijkt in de praktijk te schommelen (5 tot 13,6 kWh/m³
  over de jaren, Fluvius past hem periodiek aan). Overschrijfbaar zoals
  de andere auto-velden (dubbelklik = terug naar auto).

## 0.2.2
- Maandoverzicht en Grafieken samengevoegd tot één startpagina ("/").
  De aparte "Maandoverzicht"-tab is weg; "Grafieken" als los item ook
  (alles staat nu op de hoofdpagina). Oude `/grafieken`-links blijven
  werken via een redirect.

## 0.2.1
- Fix: grafiekenlayout bij Binkom (geen gas → 3 i.p.v. 4 grafieken) liet
  een lege plek in de grid. Nu count-onafhankelijk: de laatste grafiek
  krijgt automatisch de volle breedte bij een oneven aantal.

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
