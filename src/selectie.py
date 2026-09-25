"""Stap 3: selectie. Kent per regeling een categorie + reden toe op basis van
titelregels in config.yaml (§3.2 / §7 stap 3 van de opdracht). Eerste match wint.

Volgorde (2026-09-25, op verzoek van Bram): waardering en aanbod blijven vóór kern
gecontroleerd (specifieker dan kern's kale "mantelzorg"-patroon, anders zou kern die
altijd wegkapen). kern is nu vóór ruis gezet ("kern wint van ruis" voor gecombineerde
titels) -- dat is de enige gevraagde ordeningswijziging. jeugd blijft laatste (kern
wint ook van jeugd, ongewijzigd).
"""

import csv
import re

from src.config import ROOT

CATEGORIE_VOLGORDE = ["waardering_titel", "aanbod_titel", "kern_titel", "ruis_titel", "jeugd_titel"]
CATEGORIE_NAAM = {
    "waardering_titel": "waardering",
    "aanbod_titel": "aanbod",
    "kern_titel": "kern",
    "ruis_titel": "ruis",
    "jeugd_titel": "jeugd",
}

# Aanbod-verfijning (2026-09-25, punt 4): "subsidie" alleen aanbod als de titel ook een
# sociaal-domeinsignaal bevat, of als er een vangnet-treffer is. Anders -> ruis.
AANBOD_SOCIAAL_SIGNAAL = re.compile(
    r"mantelzorg|welzijn|zorg|sociaal|informele|respijt|vrijwillig|ontmoeting", re.IGNORECASE
)

# 'buiten_scope' (2026-09-25, punt 3): consistent labelen van twee domeinen die wel
# vangnet-treffers geven maar buiten de scope van dit onderzoek vallen. Wordt alleen
# toegepast binnen de twijfelgroep -- documenten met 'wmo'/'maatschappelijke ondersteuning'
# in de titel zijn al eerder als kern geclassificeerd en komen hier niet meer voorbij.
BUITEN_SCOPE_BESCHERMD_WONEN = re.compile(
    r"beschermd wonen|maatschappelijke opvang|\bopvang\b", re.IGNORECASE
)
BUITEN_SCOPE_PARTICIPATIEWET_DOMEIN = re.compile(
    r"studietoeslag|tegenprestatie|bijzondere bijstand|inburgering|kinderopvang|"
    r"blijverslening|woonvisie|aanwijzingsbesluit (elektronische|digitale) kanalen",
    re.IGNORECASE,
)


def _compileer_regels(selectie_config: dict) -> dict[str, list[tuple[str, re.Pattern]]]:
    gecompileerd = {}
    for groep in CATEGORIE_VOLGORDE:
        patronen = selectie_config.get(groep, [])
        gecompileerd[groep] = [(p, re.compile(p, re.IGNORECASE)) for p in patronen]
    return gecompileerd


def classificeer_titel(titel: str, regels: dict[str, list[tuple[str, re.Pattern]]]) -> tuple[str, str, bool]:
    """Geeft (categorie, reden, matched) terug. matched=False betekent: geen enkele
    titelregel matchte en de regeling valt terug op het ruis-vangnet (§3.2: "ruis = al
    het andere"). Dat onderscheid is nodig voor de vangnet-regel in stap 3 punt 2."""
    if not titel:
        return "ruis", "geen titel beschikbaar (standaard: ruis)", False
    for groep in CATEGORIE_VOLGORDE:
        for patroon_tekst, patroon in regels[groep]:
            if patroon.search(titel):
                return CATEGORIE_NAAM[groep], f"{groep}: {patroon_tekst}", True
    return "ruis", "geen enkele titelregel matchte (standaard: ruis)", False


def vind_kern_ruis_conflicten(rijen: list[dict], regels: dict[str, list[tuple[str, re.Pattern]]]) -> list[dict]:
    """Titels die zowel een kern_titel- als een ruis_titel-patroon matchen (ongeacht
    welke uiteindelijk wint) -- voor transparantie bij de ordeningswijziging (punt 3)."""
    gezien: dict[str, dict] = {}
    for rij in rijen:
        titel = rij["titel"] or ""
        if titel in gezien:
            continue
        kern_matches = [p for p, pat in regels["kern_titel"] if pat.search(titel)]
        ruis_matches = [p for p, pat in regels["ruis_titel"] if pat.search(titel)]
        if kern_matches and ruis_matches:
            gezien[titel] = {
                "titel": titel,
                "kern_regels": "; ".join(kern_matches),
                "ruis_regels": "; ".join(ruis_matches),
                "winnaar_nu": "kern",
            }
    return list(gezien.values())


def selecteer(config: dict) -> tuple[list[dict], list[dict]]:
    regels = _compileer_regels(config["selectie"])
    with open(ROOT / config["paden"]["inventaris_csv"], encoding="utf-8") as f:
        rijen = list(csv.DictReader(f))

    conflicten = vind_kern_ruis_conflicten(rijen, regels)

    resultaat = []
    for rij in rijen:
        categorie, reden, matched = classificeer_titel(rij["titel"], regels)
        vangnet_treffer = rij["vangnet_treffer"] == "True"

        # Vangnet-regel (§7 stap 3, punt 2): alleen regelingen die GEEN titelregel
        # matchten (en dus op het ruis-vangnet terugvielen) worden bij een vangnet-treffer
        # 'twijfel'. Regelingen die expliciet een ruis_titel-regel matchten, blijven ruis
        # (en komen op de aparte vangnet_in_ruis-lijst).
        if vangnet_treffer and not matched:
            categorie = "twijfel"
            reden = f"vangnet: {rij['vangnet_termen']}"

        # Aanbod-verfijning (punt 4)
        if categorie == "aanbod":
            titel = rij["titel"] or ""
            if not AANBOD_SOCIAAL_SIGNAAL.search(titel) and not vangnet_treffer:
                categorie = "ruis"
                reden = "subsidie zonder sociaal-domeinsignaal in titel en geen vangnet-treffer (standaard: ruis)"

        # 'buiten_scope' (punt 3): alleen binnen de twijfelgroep
        if categorie == "twijfel":
            titel = rij["titel"] or ""
            if BUITEN_SCOPE_BESCHERMD_WONEN.search(titel):
                categorie = "buiten_scope"
                reden = "buiten_scope: beschermd wonen/maatschappelijke opvang (andere toegangsroute)"
            elif BUITEN_SCOPE_PARTICIPATIEWET_DOMEIN.search(titel):
                categorie = "buiten_scope"
                reden = "buiten_scope: Participatiewet-domein"

        nieuwe_rij = dict(rij)
        nieuwe_rij["categorie"] = categorie
        nieuwe_rij["reden"] = reden
        resultaat.append(nieuwe_rij)
    return resultaat, conflicten


def schrijf_selectie_csv(config: dict, rijen: list[dict]):
    pad = ROOT / config["paden"]["selectie_csv"]
    pad.parent.mkdir(parents=True, exist_ok=True)
    kolommen = list(rijen[0].keys()) if rijen else []
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=kolommen)
        w.writeheader()
        for r in rijen:
            w.writerow(r)


def schrijf_conflicten_csv(config: dict, conflicten: list[dict]):
    pad = ROOT / config["paden"]["rapportage"] / "conflicten.csv"
    pad.parent.mkdir(parents=True, exist_ok=True)
    kolommen = ["titel", "kern_regels", "ruis_regels", "winnaar_nu"]
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=kolommen)
        w.writeheader()
        for r in conflicten:
            w.writerow(r)
