from flask import Flask, render_template, request, redirect, url_for, flash
from pathlib import Path
import calendar
import os
from datetime import date
from models import get_connection, init_db
from calculations import verrijk, jaaroverzicht_gem_per_maand

app = Flask(__name__)
app.secret_key = "verbruik-addon"  # lokale HA add-on, geen publieke login


class IngressPrefixMiddleware:
    """HA Supervisor stuurt ingress-requests door achter een dynamisch pad
    (/api/hassio_ingress/<token>/...), meegegeven via de X-Ingress-Path
    header. Zonder dit zet Flask's url_for() (en dus alle nav-links)
    root-relatieve paden neer die uit de ingress-iframe breken en in de
    kale HA-interface belanden."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        script_name = environ.get("HTTP_X_INGRESS_PATH", "")
        if script_name:
            environ["SCRIPT_NAME"] = script_name
            path_info = environ.get("PATH_INFO", "")
            if path_info.startswith(script_name):
                environ["PATH_INFO"] = path_info[len(script_name):]
        return self.wsgi_app(environ, start_response)


app.wsgi_app = IngressPrefixMiddleware(app.wsgi_app)

WONINGEN = ["Binkom", "Tienen"]
MAANDNAMEN = ["", "jan", "feb", "mrt", "apr", "mei", "jun",
              "jul", "aug", "sep", "okt", "nov", "dec"]

MAAND_INVOERVELDEN = [
    ("piek_verbruik", "Piek verbruik (kWh)"),
    ("dal_verbruik", "Dal verbruik (kWh)"),
    ("piek_export", "Piek export (kWh)"),
    ("dal_export", "Dal export (kWh)"),
    ("totaal_verbruik_afname", "Totaal verbruik / afname (kWh) — auto = piek+dal, overschrijfbaar bij afwijkend factuurcijfer"),
    ("totaal_export", "Totaal export (kWh) — auto = piek+dal, overschrijfbaar bij afwijkend factuurcijfer"),
    ("zonopbrengst_totaal", "Zonopbrengst totaal (kWh)"),
    ("batterij_laden", "Batterij laden (kWh)"),
    ("batterij_ontladen", "Batterij ontladen (kWh)"),
    ("gas_m3", "Gas (m³)"),
    ("gas_kwh", "Gas (kWh) — auto = m³ × laatst gekende factor, overschrijfbaar"),
    ("prijs_gas_eur", "Gasbedrag (€)"),
    ("water_l", "Water (l)"),
    ("engie_afname_eur", "Engie afname (€)"),
    ("engie_injectie_eur", "Engie injectie (€)"),
    ("bedrag_engie_app", "Bedrag Engie-app (€)"),
]

JAAR_INVOERVELDEN = [
    ("jaarverbruik_elektriciteit_kwh", "Jaarverbruik elektriciteit (kWh) — auto uit maandsommen, overschrijfbaar (bv. als Engie achterloopt)"),
    ("jaarverbruik_elektriciteit_kost_eur", "Jaarverbruik elektriciteit — kost (€) — auto, overschrijfbaar"),
    ("vaste_kost_uur", "Vaste kost (€/uur) — vaste bijdrage in de Engie-app; leeg = waarde van vorig jaar"),
    ("jaarverbruik_gas", "Jaarverbruik gas"),
    ("jaarverbruik_gas_eenheid", "Eenheid gas (m3 / kWh)"),
    ("jaarverbruik_gas_kost_eur", "Jaarverbruik gas — kost (€)"),
    ("opladen_zon_kwh", "Zon export (kWh) — auto, overschrijfbaar"),
    ("opladen_zon_kost_eur", "Zon export — kost (€) — auto, overschrijfbaar"),
    ("uitgespaard_zonnepanelen_eur", "Uitgespaard met zonnepanelen (€) — auto, overschrijfbaar"),
    ("batterij_laden_kwh", "Batterij laden (kWh) — auto, overschrijfbaar"),
    ("batterij_gebruik_kwh", "Batterij ontladen (kWh) — auto, overschrijfbaar"),
    ("batterij_gebruik_kost_eur", "Batterij gebruik (€)"),
    ("verschil_gas_vorig_jaar_m3", "Verschil gas t.o.v. vorig jaar (m³)"),
    ("verschil_gas_vorig_jaar_kwh", "Verschil gas t.o.v. vorig jaar (kWh-equiv.)"),
    ("verschil_elektriciteit_vorig_jaar_kwh", "Verschil elektriciteit t.o.v. vorig jaar (kWh) — auto, overschrijfbaar"),
    ("verschil_elektriciteit_vorig_jaar_eur", "Verschil elektriciteit t.o.v. vorig jaar (€)"),
]


def _get_records(woning):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM maandverbruik WHERE woning=? ORDER BY jaar, maand",
        (woning,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _heeft_gas(woning):
    """Een woning heeft gas zodra er in de hele historiek ooit gasdata is
    ingevuld. Tienen blijft dus gas tonen (ook als er later geen nieuwe
    gasmaanden meer bijkomen); Binkom heeft nooit gasdata en toont het niet."""
    conn = get_connection()
    row = conn.execute(
        """SELECT 1 FROM maandverbruik
           WHERE woning=? AND ((gas_kwh IS NOT NULL AND gas_kwh != 0)
                            OR (gas_m3 IS NOT NULL AND gas_m3 != 0)) LIMIT 1""",
        (woning,),
    ).fetchone()
    conn.close()
    return row is not None


def _gas_woningen():
    return [w for w in WONINGEN if _heeft_gas(w)]


def _enriched_records(woning):
    records = _get_records(woning)
    by_key = {(r["jaar"], r["maand"]): r for r in records}
    enriched = []
    for r in reversed(records):  # nieuwste eerst
        vorig = by_key.get((r["jaar"] - 1, r["maand"]))
        enriched.append(verrijk(r, vorig))
    return enriched


@app.route("/")
def index():
    woning = request.args.get("woning", WONINGEN[0])
    records = _get_records(woning)  # al chronologisch (jaar, maand) gesorteerd
    by_key = {(r["jaar"], r["maand"]): r for r in records}

    labels = []
    piek, dal = [], []
    gas = []
    zelfverbruik = []
    verschil_elek, verschil_gas = [], []
    heeft_gas = _heeft_gas(woning)

    for r in records:
        labels.append(f"{MAANDNAMEN[r['maand']]}-{str(r['jaar'])[2:]}")
        piek.append(r.get("piek_verbruik"))
        dal.append(r.get("dal_verbruik"))
        gas.append(r.get("gas_kwh"))
        if r.get("zonopbrengst_totaal") is not None:
            zelfverbruik.append(r["zonopbrengst_totaal"] - (r.get("totaal_export") or 0))
        else:
            zelfverbruik.append(None)

        vorig = by_key.get((r["jaar"] - 1, r["maand"]))
        enriched = verrijk(r, vorig)
        verschil_elek.append(enriched.get("verschil_vorig_jaar_elektriciteit"))
        verschil_gas.append(enriched.get("verschil_vorig_jaar_gas"))

    return render_template(
        "index.html",
        woningen=WONINGEN,
        woning=woning,
        heeft_gas=heeft_gas,
        labels=labels,
        piek=piek,
        dal=dal,
        gas=gas,
        zelfverbruik=zelfverbruik,
        verschil_elek=verschil_elek,
        verschil_gas=verschil_gas,
        maandrecords=_enriched_records(woning),
        maandnamen=MAANDNAMEN,
        **_jaartotalen(woning),
    )


def _jaartotalen(woning):
    conn = get_connection()
    rows = conn.execute(
        """SELECT jaar,
                  SUM(totaal_verbruik_afname) as afname,
                  SUM(piek_verbruik) as piek,
                  SUM(dal_verbruik) as dal,
                  SUM(gas_kwh) as gas,
                  SUM(zonopbrengst_totaal) as zon,
                  SUM(totaal_export) as export
           FROM maandverbruik WHERE woning=? GROUP BY jaar ORDER BY jaar""",
        (woning,),
    ).fetchall()
    conn.close()
    return {
        "jaar_labels": [str(r["jaar"]) for r in rows],
        "jaar_elektriciteit": [r["afname"] for r in rows],
        "jaar_gas": [r["gas"] for r in rows],
        "jaar_zon": [r["zon"] for r in rows],
        "jaar_piek": [r["piek"] for r in rows],
        "jaar_dal": [r["dal"] for r in rows],
        "jaar_zelfverbruik": [
            (r["zon"] - (r["export"] or 0)) if r["zon"] is not None else None for r in rows
        ],
    }


def _laatste_gas_factor(woning):
    """Meest recente werkelijke kWh/m³-omzetfactor uit de eigen data
    (deze schommelt in realiteit — Fluvius publiceert ze periodiek op
    basis van de calorische waarde — dus géén vaste online constante)."""
    conn = get_connection()
    row = conn.execute(
        """SELECT gas_kwh, gas_m3 FROM maandverbruik
           WHERE woning=? AND gas_m3 IS NOT NULL AND gas_m3 != 0
                 AND gas_kwh IS NOT NULL
           ORDER BY jaar DESC, maand DESC LIMIT 1""",
        (woning,),
    ).fetchone()
    conn.close()
    if row:
        return row["gas_kwh"] / row["gas_m3"]
    return None


@app.route("/invoer", methods=["GET", "POST"])
@app.route("/invoer/<woning>/<int:jaar>/<int:maand>", methods=["GET", "POST"])
def invoer(woning=None, jaar=None, maand=None):
    bestaand = None
    if woning and jaar and maand:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM maandverbruik WHERE woning=? AND jaar=? AND maand=?",
            (woning, jaar, maand),
        ).fetchone()
        conn.close()
        bestaand = dict(row) if row else None
    if request.method == "POST":
        woning = request.form["woning"]
        jaar = int(request.form["jaar"])
        maand = int(request.form["maand"])
        waarden = {"woning": woning, "jaar": jaar, "maand": maand}
        for veld, _ in MAAND_INVOERVELDEN:
            raw = request.form.get(veld, "").strip().replace(",", ".")
            waarden[veld] = float(raw) if raw else None

        conn = get_connection()
        kolommen = ", ".join(waarden.keys())
        placeholders = ", ".join(f":{k}" for k in waarden)
        update = ", ".join(
            f"{k}=excluded.{k}" for k in waarden if k not in ("woning", "jaar", "maand")
        )
        conn.execute(
            f"""INSERT INTO maandverbruik ({kolommen}) VALUES ({placeholders})
                ON CONFLICT(woning, jaar, maand) DO UPDATE SET {update}""",
            waarden,
        )
        conn.commit()
        conn.close()
        flash(f"Maand {maand}/{jaar} voor {woning} opgeslagen.")
        return redirect(url_for("index", woning=woning))

    return render_template(
        "invoer.html",
        woningen=WONINGEN,
        velden=MAAND_INVOERVELDEN,
        bestaand=bestaand,
        woning=woning,
        jaar=jaar,
        maand=maand,
        gas_factor=_laatste_gas_factor(woning or WONINGEN[0]),
        gas_woningen=_gas_woningen(),
    )


def _huidige_maand():
    vandaag = date.today()
    return (vandaag.year, vandaag.month)


def _vaste_kost_resolver(woning):
    """Functie jaar -> vaste kost (€/uur): de waarde van dat jaar, anders de
    laatst gekende van een eerder jaar, anders None."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT jaar, vaste_kost_uur FROM jaaroverzicht
           WHERE woning=? AND vaste_kost_uur IS NOT NULL ORDER BY jaar""",
        (woning,),
    ).fetchall()
    conn.close()
    bekend = [(r["jaar"], r["vaste_kost_uur"]) for r in rows]

    def resolve(jaar):
        waarde = None
        for j, v in bekend:
            if j <= jaar:
                waarde = v
        return waarde

    return resolve


def _jaartotalen_componenten(woning):
    """Som per jaar van de maandvelden die als basis dienen voor de
    auto-berekende jaaroverzicht-velden, plus de variabele energieprijs
    en de vergelijking met dezelfde maanden van vorig jaar."""
    conn = get_connection()
    maand_counts, componenten = {}, {}
    for r in conn.execute(
        """SELECT jaar, COUNT(*) as n,
                  SUM(totaal_verbruik_afname) as afname,
                  SUM(engie_afname_eur) as afname_eur,
                  SUM(gas_kwh) as gas_kwh,
                  SUM(gas_m3) as gas_m3,
                  SUM(batterij_ontladen) as batterij_ontladen,
                  SUM(batterij_laden) as batterij_laden,
                  SUM(totaal_export) as export,
                  SUM(engie_injectie_eur) as injectie_eur,
                  SUM(zonopbrengst_totaal) as zon
           FROM maandverbruik WHERE woning=? GROUP BY jaar""",
        (woning,),
    ):
        maand_counts[r["jaar"]] = r["n"]
        componenten[r["jaar"]] = dict(r)
    maanden = conn.execute(
        """SELECT jaar, maand, totaal_verbruik_afname AS afname, engie_afname_eur AS eur,
                  gas_kwh, gas_m3
           FROM maandverbruik WHERE woning=? ORDER BY jaar, maand""",
        (woning,),
    ).fetchall()
    conn.close()

    vaste_kost = _vaste_kost_resolver(woning)
    huidige = _huidige_maand()

    def uren(jaar, maand):
        return 24 * calendar.monthrange(jaar, maand)[1]

    # Onvolledige maanden: enkel waar Engie echt kan achterlopen, dus de
    # lopende maand, en de vorige maand als haar factuur onder de vaste kost
    # alleen ligt. Oudere maanden blijven altijd meetellen: wie ze zou
    # weglaten omdat de factuur "te laag" lijkt, laat net de maanden met de
    # laagste factuur vallen en trekt de variabele prijs kunstmatig omhoog.
    vorige = (huidige[0], huidige[1] - 1) if huidige[1] > 1 else (huidige[0] - 1, 12)
    onvolledig = set()
    for m in maanden:
        sleutel = (m["jaar"], m["maand"])
        vk = vaste_kost(m["jaar"])
        if sleutel == huidige:
            onvolledig.add(sleutel)
        elif sleutel == vorige and m["eur"] is not None and m["afname"] and vk is not None \
                and m["eur"] < vk * uren(m["jaar"], m["maand"]):
            onvolledig.add(sleutel)

    # (jaar, maand) -> waarde, enkel maanden met echte data (> 0).
    per_maand = {
        "afname": {(m["jaar"], m["maand"]): m["afname"] for m in maanden
                   if m["afname"] and m["afname"] > 0 and (m["jaar"], m["maand"]) not in onvolledig},
        "gas_kwh": {(m["jaar"], m["maand"]): m["gas_kwh"] for m in maanden
                    if m["gas_kwh"] and m["gas_kwh"] > 0 and (m["jaar"], m["maand"]) != huidige},
        "gas_m3": {(m["jaar"], m["maand"]): m["gas_m3"] for m in maanden
                   if m["gas_m3"] and m["gas_m3"] > 0 and (m["jaar"], m["maand"]) != huidige},
    }

    def verschil_zelfde_maanden(veld, jaar):
        """Dit jaar min vorig jaar, enkel over de maanden die in beide jaren
        data hebben — zo vergelijkt een lopend jaar niet met een vol jaar."""
        nu = {mnd: w for (j, mnd), w in per_maand[veld].items() if j == jaar}
        vorig = {mnd: w for (j, mnd), w in per_maand[veld].items() if j == jaar - 1}
        gemeenschappelijk = nu.keys() & vorig.keys()
        if not gemeenschappelijk:
            return None
        return sum(nu[x] for x in gemeenschappelijk) - sum(vorig[x] for x in gemeenschappelijk)

    for jaar, c in componenten.items():
        vk = vaste_kost(jaar)
        som_factuur = som_vast = som_kwh = 0.0
        gebruikt, uitgesloten = 0, []
        for m in maanden:
            if m["jaar"] != jaar or not m["afname"] or m["afname"] <= 0 or m["eur"] is None:
                continue
            if (jaar, m["maand"]) in onvolledig:
                uitgesloten.append(m["maand"])
                continue
            som_factuur += m["eur"]
            som_kwh += m["afname"]
            gebruikt += 1
            if vk is not None:
                som_vast += vk * uren(jaar, m["maand"])
        var = None
        if vk is not None and som_kwh > 0 and som_factuur - som_vast > 0:
            var = (som_factuur - som_vast) / som_kwh
        c["vaste_kost_uur"] = vk
        c["var_prijs"] = var
        c["var_maanden"] = gebruikt
        c["var_uitgesloten"] = uitgesloten
        c["verschil_afname"] = verschil_zelfde_maanden("afname", jaar)
        c["verschil_gas_kwh"] = verschil_zelfde_maanden("gas_kwh", jaar)
        c["verschil_gas_m3"] = verschil_zelfde_maanden("gas_m3", jaar)

    return maand_counts, componenten


def _bereken_jaaroverzicht(jaar, componenten):
    """Berekent alle auto-afleidbare jaaroverzicht-velden voor één jaar.
    Retourneert een dict met enkel de velden waarvoor een berekening
    mogelijk is (anders None)."""
    huidig = componenten.get(jaar, {})

    injectie = huidig.get("injectie_eur")
    opladen_zon_kost_eur = abs(injectie) if injectie is not None else None
    var = huidig.get("var_prijs")
    zon, export = huidig.get("zon"), huidig.get("export")
    ontladen = huidig.get("batterij_ontladen")

    # Uitgespaard met zonnepanelen = variabele prijs × zelfverbruik + wat de
    # injectie opbrengt. Enkel de VARIABELE prijs: de vaste kost betaal je
    # ook zonder panelen niet minder, dus die hoort niet in de besparing.
    uitgespaard = None
    if var is not None and zon is not None and export is not None:
        uitgespaard = var * (zon - export) + (opladen_zon_kost_eur or 0)

    # Batterij: ontladen kWh vermijdt aankoop aan de variabele prijs.
    batterij_eur = var * ontladen if var is not None and ontladen is not None else None

    return {
        "jaarverbruik_elektriciteit_kwh": huidig.get("afname"),
        "jaarverbruik_elektriciteit_kost_eur": huidig.get("afname_eur"),
        "batterij_gebruik_kwh": ontladen,
        "batterij_laden_kwh": huidig.get("batterij_laden"),
        "batterij_gebruik_kost_eur": batterij_eur,
        # "Opladen zon" blijkt zon-export te zijn (export naar het net),
        # geen batterijlading — geverifieerd tegen totaal_export/
        # engie_injectie_eur.
        "opladen_zon_kwh": export,
        "opladen_zon_kost_eur": opladen_zon_kost_eur,
        "uitgespaard_zonnepanelen_eur": uitgespaard,
        "verschil_elektriciteit_vorig_jaar_kwh": huidig.get("verschil_afname"),
        "verschil_gas_vorig_jaar_kwh": huidig.get("verschil_gas_kwh"),
        "verschil_gas_vorig_jaar_m3": huidig.get("verschil_gas_m3"),
    }


@app.route("/jaaroverzicht")
def jaaroverzicht():
    woning = request.args.get("woning", WONINGEN[0])
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM jaaroverzicht WHERE woning=? ORDER BY jaar DESC", (woning,)
    ).fetchall()
    conn.close()

    maand_counts, componenten = _jaartotalen_componenten(woning)

    resultaten = []
    for r in rows:
        rec = dict(r)
        jaar = rec["jaar"]
        berekend = _bereken_jaaroverzicht(jaar, componenten)

        for veld, waarde in berekend.items():
            # Een manueel ingevulde waarde (bv. omdat Engie een paar
            # dagen achterloopt) krijgt altijd voorrang op de berekende
            # som.
            if rec.get(veld) is None and waarde is not None:
                rec[veld] = waarde
                rec[f"_{veld}_berekend"] = True

        # Gas in m³ is puur informatief (naast het kWh-jaarverbruik),
        # altijd rechtstreeks uit de maandsommen — geen apart opslagveld.
        rec["jaarverbruik_gas_m3_berekend"] = componenten.get(jaar, {}).get("gas_m3")

        # Zelfverbruik zon (kWh) per jaar = zonopbrengst - export; puur
        # informatief, altijd uit de maandsommen (geen apart opslagveld).
        zon_j = componenten.get(jaar, {}).get("zon")
        export_j = componenten.get(jaar, {}).get("export")
        rec["zelfverbruik_kwh_berekend"] = (
            zon_j - (export_j or 0) if zon_j is not None else None
        )
        # Totale zonopbrengst van het jaar (som van de maanden); puur informatief.
        rec["zonopbrengst_kwh_berekend"] = zon_j
        rec["zelfverbruik_pct_berekend"] = (
            (zon_j - (export_j or 0)) / zon_j * 100 if zon_j else None
        )

        n_maanden = maand_counts.get(jaar)
        rec["gem_maand_elektriciteit"] = jaaroverzicht_gem_per_maand(
            rec.get("jaarverbruik_elektriciteit_kost_eur"), n_maanden
        )
        rec["gem_maand_gas"] = jaaroverzicht_gem_per_maand(
            rec.get("jaarverbruik_gas_kost_eur"), n_maanden
        )
        rec["gem_maand_zon"] = jaaroverzicht_gem_per_maand(
            rec.get("opladen_zon_kost_eur"), n_maanden
        )

        c = componenten.get(jaar, {})
        rec["var_prijs"] = c.get("var_prijs")
        vk = c.get("vaste_kost_uur")
        if c.get("var_prijs") is not None:
            tip = (f"Vaste kost {vk:.3f} €/uur (≈ {vk * 24 * 365 / 12:.1f} €/maand); "
                   f"{c['var_maanden']} maanden gebruikt")
            if c["var_uitgesloten"]:
                tip += "; niet meegeteld (onvolledig): " + ", ".join(
                    MAANDNAMEN[m] for m in c["var_uitgesloten"])
        elif vk is None:
            tip = "Geen vaste kost ingesteld voor dit jaar (zie 'bewerk')"
        else:
            tip = "Geen volledige maanden met factuur om de variabele prijs uit af te leiden"
        rec["var_tooltip"] = tip

        resultaten.append(rec)

    return render_template(
        "jaaroverzicht.html",
        woningen=WONINGEN,
        woning=woning,
        records=resultaten,
        heeft_gas=_heeft_gas(woning),
        maandrecords=_enriched_records(woning),
        maandnamen=MAANDNAMEN,
    )


@app.route("/jaaroverzicht/invoer", methods=["GET", "POST"])
@app.route("/jaaroverzicht/invoer/<woning>/<int:jaar>", methods=["GET", "POST"])
def jaaroverzicht_invoer(woning=None, jaar=None):
    bestaand = None
    if woning and jaar:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM jaaroverzicht WHERE woning=? AND jaar=?", (woning, jaar)
        ).fetchone()
        conn.close()
        bestaand = dict(row) if row else None

    if request.method == "POST":
        woning = request.form["woning"]
        jaar = int(request.form["jaar"])
        waarden = {"woning": woning, "jaar": jaar}
        for veld, _ in JAAR_INVOERVELDEN:
            raw = request.form.get(veld, "").strip()
            if veld == "jaarverbruik_gas_eenheid":
                waarden[veld] = raw or None
            else:
                raw = raw.replace(",", ".")
                waarden[veld] = float(raw) if raw else None

        conn = get_connection()
        kolommen = ", ".join(waarden.keys())
        placeholders = ", ".join(f":{k}" for k in waarden)
        update = ", ".join(
            f"{k}=excluded.{k}" for k in waarden if k not in ("woning", "jaar")
        )
        conn.execute(
            f"""INSERT INTO jaaroverzicht ({kolommen}) VALUES ({placeholders})
                ON CONFLICT(woning, jaar) DO UPDATE SET {update}""",
            waarden,
        )
        conn.commit()
        conn.close()
        flash(f"Jaaroverzicht {jaar} voor {woning} opgeslagen.")
        return redirect(url_for("jaaroverzicht", woning=woning))

    berekend = {}
    if woning and jaar:
        _, componenten = _jaartotalen_componenten(woning)
        berekend = _bereken_jaaroverzicht(jaar, componenten)
        berekend["vaste_kost_uur"] = _vaste_kost_resolver(woning)(jaar - 1)

    return render_template(
        "jaaroverzicht_invoer.html",
        woningen=WONINGEN,
        velden=JAAR_INVOERVELDEN,
        bestaand=bestaand,
        woning=woning,
        jaar=jaar,
        berekend=berekend,
        gas_woningen=_gas_woningen(),
    )


@app.route("/beheer/herstel-seed", methods=["GET", "POST"])
def herstel_seed():
    import shutil
    seed_path = Path(__file__).parent / "data" / "verbruik.db"
    huidige_path = Path(os.environ.get("VERBRUIK_DB", seed_path))

    if request.method == "POST":
        if not seed_path.exists():
            flash("Geen meegeleverde seed-databank gevonden in de image.")
            return redirect(url_for("herstel_seed"))
        if huidige_path.resolve() != seed_path.resolve():
            backup = huidige_path.with_suffix(".voor-herstel.db")
            if huidige_path.exists():
                shutil.copy2(huidige_path, backup)
            shutil.copy2(seed_path, huidige_path)
            init_db()  # schema-migraties toepassen op de teruggezette databank
            flash(
                f"Meegeleverde data hersteld. Vorige inhoud staat als backup in {backup.name}."
            )
        else:
            flash("Huidige databank is al de meegeleverde seed — niets te doen.")
        return redirect(url_for("index"))

    huidig_aantal = 0
    if huidige_path.exists():
        conn = get_connection()
        huidig_aantal = conn.execute("SELECT COUNT(*) AS n FROM maandverbruik").fetchone()["n"]
        conn.close()

    return render_template(
        "herstel_seed.html",
        huidig_aantal=huidig_aantal,
        seed_bestaat=seed_path.exists(),
    )


@app.route("/grafieken")
def grafieken():
    # Grafieken zijn samengevoegd met de hoofdpagina — oude links blijven werken.
    return redirect(url_for("index", **request.args))


if __name__ == "__main__":
    init_db()
    debug = os.environ.get("VERBRUIK_DEBUG") == "1"
    app.run(host="0.0.0.0", port=8099, debug=debug)
