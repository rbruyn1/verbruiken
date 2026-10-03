from flask import Flask, render_template, request, redirect, url_for, flash
from pathlib import Path
import os
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
    heeft_gas = any(r.get("gas_kwh") is not None for r in records)

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
                  SUM(totaal_verbruik_afname) as elek,
                  SUM(gas_kwh) as gas,
                  SUM(zonopbrengst_totaal) as zon
           FROM maandverbruik WHERE woning=? GROUP BY jaar ORDER BY jaar""",
        (woning,),
    ).fetchall()
    conn.close()
    return {
        "jaar_labels": [str(r["jaar"]) for r in rows],
        "jaar_elektriciteit": [r["elek"] for r in rows],
        "jaar_gas": [r["gas"] for r in rows],
        "jaar_zon": [r["zon"] for r in rows],
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
    )


def _jaartotalen_componenten(woning):
    """Som per jaar van de maandvelden die als basis dienen voor de
    auto-berekende jaaroverzicht-velden."""
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
    conn.close()
    return maand_counts, componenten


def _bereken_jaaroverzicht(jaar, componenten):
    """Berekent alle auto-afleidbare jaaroverzicht-velden voor één jaar
    (dit jaar t.o.v. vorig jaar waar relevant). Retourneert een dict met
    enkel de velden waarvoor een berekening mogelijk is (anders None)."""
    huidig = componenten.get(jaar, {})
    vorig = componenten.get(jaar - 1, {})

    def verschil(veld):
        h, v = huidig.get(veld), vorig.get(veld)
        return h - v if h is not None and v is not None else None

    injectie = huidig.get("injectie_eur")
    opladen_zon_kost_eur = abs(injectie) if injectie is not None else None
    opladen_zon_kwh = huidig.get("export")

    # Uitgespaard met zonnepanelen = (jaarprijs afname × jaarlijks
    # zelfverbruik) + (jaarprijs injectie × jaarlijkse export). Zelfde
    # opbouw als de Excel-formule, maar met de prijzen van het JUISTE
    # jaar — in de Excel bleek dit voor 2026 door een sleepfout de
    # prijzen van 2025 te gebruiken voor 11 van de 12 maanden.
    uitgespaard = None
    afname_kwh, afname_eur = huidig.get("afname"), huidig.get("afname_eur")
    zon, export = huidig.get("zon"), huidig.get("export")
    if None not in (afname_kwh, afname_eur, zon, export) and afname_kwh and export:
        prijs_afname = afname_eur / afname_kwh
        prijs_injectie = (
            opladen_zon_kost_eur / opladen_zon_kwh
            if opladen_zon_kwh and opladen_zon_kost_eur is not None
            else 0
        )
        zelfverbruik = zon - export
        uitgespaard = prijs_afname * zelfverbruik + prijs_injectie * export

    return {
        "jaarverbruik_elektriciteit_kwh": huidig.get("afname"),
        "jaarverbruik_elektriciteit_kost_eur": huidig.get("afname_eur"),
        "batterij_gebruik_kwh": huidig.get("batterij_ontladen"),
        "batterij_laden_kwh": huidig.get("batterij_laden"),
        # "Opladen zon" blijkt zon-export te zijn (export naar het net),
        # geen batterijlading — geverifieerd tegen totaal_export/
        # engie_injectie_eur.
        "opladen_zon_kwh": opladen_zon_kwh,
        "opladen_zon_kost_eur": opladen_zon_kost_eur,
        "uitgespaard_zonnepanelen_eur": uitgespaard,
        "verschil_elektriciteit_vorig_jaar_kwh": verschil("afname"),
        "verschil_gas_vorig_jaar_kwh": verschil("gas_kwh"),
        "verschil_gas_vorig_jaar_m3": verschil("gas_m3"),
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

        resultaten.append(rec)

    return render_template(
        "jaaroverzicht.html",
        woningen=WONINGEN,
        woning=woning,
        records=resultaten,
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

    return render_template(
        "jaaroverzicht_invoer.html",
        woningen=WONINGEN,
        velden=JAAR_INVOERVELDEN,
        bestaand=bestaand,
        woning=woning,
        jaar=jaar,
        berekend=berekend,
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
