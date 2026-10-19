"""Koppeling met het Energiedashboard van Home Assistant.

De add-on praat via de Supervisor-proxy (ws://supervisor/core/websocket, met
SUPERVISOR_TOKEN) met de WebSocket-API van Home Assistant, net zoals het
Energiedashboard zelf:
  - energy/get_prefs                     -> welke bronnen er in Energie staan
  - recorder/get_statistics_metadata     -> eenheden van die bronnen
  - recorder/statistics_during_period    -> de maandtotalen (period=month, change)
Niets wordt automatisch opgeslagen: de waarden worden enkel in het maandformulier
ingevuld nadat je op "Overnemen uit Energie" klikt.
"""
import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

try:
    import websocket  # pakket: websocket-client
except ImportError:  # pragma: no cover
    websocket = None

WS_URL = os.environ.get("HA_WS_URL", "ws://supervisor/core/websocket")

# Velden van het maandformulier waaraan een Energie-bron gekoppeld kan worden.
KOPPEL_VELDEN = [
    ("", "— niet overnemen —"),
    ("piek_verbruik", "Piek verbruik (afname)"),
    ("dal_verbruik", "Dal verbruik (afname)"),
    ("piek_export", "Piek export (injectie)"),
    ("dal_export", "Dal export (injectie)"),
    ("zonopbrengst_totaal", "Zonopbrengst"),
    ("batterij_laden", "Batterij laden"),
    ("batterij_ontladen", "Batterij ontladen"),
    ("gas", "Gas (m³ of kWh, volgens de eenheid)"),
    ("water_l", "Water (liter)"),
]
GELDIGE_VELDEN = {v for v, _ in KOPPEL_VELDEN if v}
ENERGIE_VELDEN = {"piek_verbruik", "dal_verbruik", "piek_export", "dal_export",
                  "zonopbrengst_totaal", "batterij_laden", "batterij_ontladen"}

# omrekenfactoren naar kWh en naar m³
ENERGIE_NAAR_KWH = {"Wh": 0.001, "kWh": 1.0, "MWh": 1000.0, "MJ": 1 / 3.6, "GJ": 1000 / 3.6}
VOLUME_NAAR_M3 = {"m³": 1.0, "m3": 1.0, "L": 0.001, "l": 0.001, "ft³": 0.0283168,
                  "CCF": 2.83168, "gal": 0.00378541}


class HAFout(Exception):
    """Fout bij het praten met Home Assistant (met een leesbare boodschap)."""


class HAClient:
    def __init__(self, url=None, token=None, timeout=15):
        self.url = url or WS_URL
        self.token = token or os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HA_TOKEN")
        self.timeout = timeout
        self.ws = None
        self._id = 0

    def __enter__(self):
        if websocket is None:
            raise HAFout("Het Python-pakket 'websocket-client' ontbreekt in de add-on.")
        if not self.token:
            raise HAFout("Geen toegangstoken voor Home Assistant (SUPERVISOR_TOKEN). "
                         "Draait de add-on met 'homeassistant_api' aan? Herinstalleer/herbouw na de update.")
        try:
            self.ws = websocket.create_connection(self.url, timeout=self.timeout)
        except Exception as e:
            raise HAFout(f"Kon Home Assistant niet bereiken ({e}).")
        try:
            eerste = json.loads(self.ws.recv())
            if eerste.get("type") != "auth_required":
                raise HAFout("Onverwacht antwoord van Home Assistant bij het aanmelden.")
            self.ws.send(json.dumps({"type": "auth", "access_token": self.token}))
            antwoord = json.loads(self.ws.recv())
        except HAFout:
            self.__exit__()
            raise
        except Exception as e:
            self.__exit__()
            raise HAFout(f"Verbinding met Home Assistant verbroken tijdens het aanmelden ({e}).")
        if antwoord.get("type") != "auth_ok":
            self.__exit__()
            raise HAFout("Home Assistant weigert de toegang (ongeldig token of geen rechten).")
        return self

    def __exit__(self, *exc):
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass
        self.ws = None

    def call(self, type_, **payload):
        self._id += 1
        try:
            self.ws.send(json.dumps({"id": self._id, "type": type_, **payload}))
            while True:
                antwoord = json.loads(self.ws.recv())
                if antwoord.get("id") != self._id:
                    continue
                if not antwoord.get("success", False):
                    fout = antwoord.get("error") or {}
                    raise HAFout(f"Home Assistant gaf een fout op '{type_}': {fout.get('message', fout)}")
                return antwoord.get("result")
        except HAFout:
            raise
        except Exception as e:
            raise HAFout(f"Verbinding met Home Assistant verbroken bij '{type_}' ({e}).")

    # ---------- bronnen in het Energiedashboard ----------
    def _eenheden(self, ids):
        if not ids:
            return {}
        meta = self.call("recorder/get_statistics_metadata", statistic_ids=list(ids)) or []
        return {m.get("statistic_id"): m.get("statistics_unit_of_measurement") for m in meta}

    def _namen(self, ids):
        try:
            return {s["entity_id"]: (s.get("attributes") or {}).get("friendly_name")
                    for s in (self.call("get_states") or []) if s.get("entity_id") in ids}
        except HAFout:
            return {}

    def energie_bronnen(self):
        prefs = self.call("energy/get_prefs") or {}
        bronnen = []

        def voeg(sid, soort):
            if sid:
                bronnen.append({"statistic_id": sid, "soort": soort})

        for bron in prefs.get("energy_sources", []):
            t = bron.get("type")
            if t == "grid":
                for f in bron.get("flow_from", []) or []:
                    voeg(f.get("stat_energy_from"), "net afname")
                for f in bron.get("flow_to", []) or []:
                    voeg(f.get("stat_energy_to"), "net injectie")
            elif t == "solar":
                voeg(bron.get("stat_energy_from"), "zon")
            elif t == "battery":
                voeg(bron.get("stat_energy_from"), "batterij ontladen")
                voeg(bron.get("stat_energy_to"), "batterij laden")
            elif t == "gas":
                voeg(bron.get("stat_energy_from"), "gas")
            elif t == "water":
                voeg(bron.get("stat_energy_from"), "water")
        ids = [b["statistic_id"] for b in bronnen]
        eenheden, namen = self._eenheden(ids), self._namen(set(ids))
        for b in bronnen:
            b["naam"] = namen.get(b["statistic_id"]) or b["statistic_id"]
            b["eenheid"] = eenheden.get(b["statistic_id"])
            b["voorstel"] = voorstel(b["soort"], f'{b["statistic_id"]} {b["naam"]}')
        return bronnen

    def alle_statistieken(self):
        """Alle statistieken met een som (kWh, m3, L, ...) die de recorder bijhoudt, ook die
        niet in het Energiedashboard staan. Zo kun je bv. losse piek/dal-sensoren koppelen."""
        lijst = self.call("recorder/list_statistic_ids", statistic_type="sum") or []
        keuzes = []
        for m in lijst:
            eenheid = m.get("statistics_unit_of_measurement")
            if eenheid in ENERGIE_NAAR_KWH or eenheid in VOLUME_NAAR_M3:
                keuzes.append({"statistic_id": m.get("statistic_id"), "eenheid": eenheid,
                               "naam": m.get("name") or ""})
        namen = self._namen({k["statistic_id"] for k in keuzes})
        for k in keuzes:
            k["naam"] = namen.get(k["statistic_id"]) or k["naam"] or k["statistic_id"]
        return sorted(keuzes, key=lambda k: k["statistic_id"])

    # ---------- maandtotalen ----------
    def maand_waarden(self, koppeling, jaar, maand):
        """koppeling: lijst (statistic_id, veld). Geeft {'waarden': {formulierveld: waarde},
        'waarschuwingen': [...]} terug, omgerekend naar kWh, m³ en liter."""
        waarschuwingen = []
        tz = ZoneInfo((self.call("get_config") or {}).get("time_zone") or "UTC")
        start = datetime(jaar, maand, 1, tzinfo=tz)
        eind = datetime(jaar + (maand == 12), maand % 12 + 1, 1, tzinfo=tz)
        ids = sorted({sid for sid, _ in koppeling})
        eenheden = self._eenheden(ids)
        stats = self.call(
            "recorder/statistics_during_period",
            start_time=start.isoformat(), end_time=eind.isoformat(),
            statistic_ids=ids, period="month", types=["change"],
        ) or {}

        uit = {}
        for sid, veld in koppeling:
            delen = [b.get("change") for b in (stats.get(sid) or []) if b.get("change") is not None]
            if not delen:
                waarschuwingen.append(f"Geen gegevens voor {sid} in {maand}/{jaar}.")
                continue
            waarde, eenheid = sum(delen), eenheden.get(sid)
            if veld in ENERGIE_VELDEN:
                factor = ENERGIE_NAAR_KWH.get(eenheid)
                doel, waarde = veld, (waarde * factor if factor else None)
            elif veld == "gas":
                if eenheid in ENERGIE_NAAR_KWH:
                    doel, waarde = "gas_kwh", waarde * ENERGIE_NAAR_KWH[eenheid]
                elif eenheid in VOLUME_NAAR_M3:
                    doel, waarde = "gas_m3", waarde * VOLUME_NAAR_M3[eenheid]
                else:
                    doel, waarde = "gas_m3", None
            elif veld == "water_l":
                factor = VOLUME_NAAR_M3.get(eenheid)
                doel, waarde = "water_l", (waarde * factor * 1000 if factor else None)
            else:
                continue
            if waarde is None:
                waarschuwingen.append(f"Onbekende eenheid '{eenheid}' voor {sid}: overgeslagen.")
                continue
            uit[doel] = uit.get(doel, 0.0) + waarde

        for sleutel in uit:
            uit[sleutel] = round(uit[sleutel], 1 if sleutel == "water_l" else 3)
        nu = datetime.now(tz)
        if (nu.year, nu.month) == (jaar, maand):
            waarschuwingen.append("Deze maand is nog bezig: de waarden lopen tot nu.")
        return {"waarden": uit, "waarschuwingen": waarschuwingen}


_PIEK = r"(^|[^a-z])(piek|peak|dag|day|t1|tarief_?1|tariff_?1)([^a-z0-9]|$)"
_DAL = r"(^|[^a-z])(dal|low|offpeak|off_peak|nacht|night|t2|tarief_?2|tariff_?2)([^a-z0-9]|$)"


def voorstel(soort, tekst):
    """Gok bij welk formulierveld een Energie-bron hoort (de gebruiker kan het wijzigen)."""
    t = tekst.lower()
    if soort in ("net afname", "net injectie"):
        richting = "verbruik" if soort == "net afname" else "export"
        if re.search(_DAL, t):
            return f"dal_{richting}"
        if re.search(_PIEK, t):
            return f"piek_{richting}"
        return ""
    return {"zon": "zonopbrengst_totaal", "batterij ontladen": "batterij_ontladen",
            "batterij laden": "batterij_laden", "gas": "gas", "water": "water_l"}.get(soort, "")
