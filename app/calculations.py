"""Afgeleide waarden.

LET OP: 'totaal_verbruik_afname' en 'totaal_export' zijn RUWE invoervelden,
géén som van piek+dal. In de originele Excel bleek dat inconsistent:
voor sommige maanden was het een formule (piek+dal), voor andere een los
ingevoerd cijfer (vermoedelijk het werkelijke Engie-factuurbedrag i.p.v.
de eigen piek/dal-metersplitsing — die kunnen licht verschillen). Zelf
herberekenen als piek+dal gaf aantoonbaar foute waarden bij verificatie
tegen de originele data, dus deze twee blijven invoer, niet afgeleid.
"""


def zelfverbruik(rec):
    return (rec.get("zonopbrengst_totaal") or 0) - (rec.get("totaal_export") or 0)


def zelfverbruik_pct(rec):
    zon = rec.get("zonopbrengst_totaal") or 0
    if zon == 0:
        return None
    return zelfverbruik(rec) / zon * 100


def prijs_per_kwh_gas(rec):
    gas_kwh = rec.get("gas_kwh") or 0
    if gas_kwh == 0:
        return None
    return (rec.get("prijs_gas_eur") or 0) / gas_kwh


def gem_prijs_kwh_afname(rec):
    verbruik = rec.get("totaal_verbruik_afname") or 0
    if verbruik == 0:
        return None
    return (rec.get("engie_afname_eur") or 0) / verbruik


def gem_prijs_kwh_injectie(rec):
    export = rec.get("totaal_export") or 0
    if export == 0:
        return None
    return (rec.get("engie_injectie_eur") or 0) / export * -1


def verschil_vorig_jaar(huidig_rec, vorig_jaar_rec, veld):
    """veld: 'totaal_verbruik_afname' | 'zonopbrengst_totaal' | 'gas_kwh'"""
    if vorig_jaar_rec is None:
        return None
    huidig = huidig_rec.get(veld) or 0
    vorig = vorig_jaar_rec.get(veld) or 0
    if huidig == 0:
        return 0
    return huidig - vorig


def verrijk(rec, vorig_jaar_rec=None):
    """Neemt een ruwe maandverbruik-record (dict) en geeft er alle
    betrouwbaar afgeleide velden bij, zonder de ruwe velden te wijzigen."""
    out = dict(rec)
    out["zelfverbruik"] = zelfverbruik(rec)
    out["zelfverbruik_pct"] = zelfverbruik_pct(rec)
    out["prijs_per_kwh_gas"] = prijs_per_kwh_gas(rec)
    out["gem_prijs_kwh_afname"] = gem_prijs_kwh_afname(rec)
    out["gem_prijs_kwh_injectie"] = gem_prijs_kwh_injectie(rec)
    out["verschil_vorig_jaar_elektriciteit"] = verschil_vorig_jaar(
        rec, vorig_jaar_rec, "totaal_verbruik_afname"
    )
    out["verschil_vorig_jaar_zon"] = verschil_vorig_jaar(
        rec, vorig_jaar_rec, "zonopbrengst_totaal"
    )
    out["verschil_vorig_jaar_gas"] = verschil_vorig_jaar(
        rec, vorig_jaar_rec, "gas_kwh"
    )
    return out


def jaaroverzicht_gem_per_maand(jaartotaal, aantal_maanden_met_data):
    if not aantal_maanden_met_data:
        return None
    return jaartotaal / aantal_maanden_met_data
