"""Stap 7: termenverkenning. Telt en toont voorbeelden, interpreteert niet."""

import csv
import random
import re
import sys
from collections import Counter, defaultdict

import openpyxl

from src.config import ROOT

csv.field_size_limit(sys.maxsize)

# Startlijst (§7 stap 7 van de opdracht). "term1 + term2" = combinatie (AND).
STARTLIJST = {
    "Positie": [
        "mantelzorger + (betrokken|betrekken|uitgenodigd|aanwezig|gesprek|onderzoek)",
        "cliëntondersteuning",
    ],
    "Draagkracht": [
        "belastbaarheid", "overbelast*", "draagkracht", "draaglast",
        "(dreigende) overbelasting", "huisarts|medisch advies",
    ],
    "Behoeften": [
        "ondersteuning van de mantelzorger", "respijt*", "logeer*", "dagbesteding",
        "mantelzorgondersteuning", "steunpunt",
    ],
    "Instrumenten": [
        "EDIZ", "zelfredzaamheidsmatrix|ZRM", "vragenlijst", "gespreksleidraad", "checklist",
    ],
    "Jonge mantelzorgers": [
        "jonge mantelzorger*", "kinderen + gebruikelijke hulp", "inwonende kinderen",
    ],
    "Kader": [
        "gelijkgericht*", "mantelzorgagenda",
    ],
}


def _term_naar_patroon(term: str) -> list[re.Pattern]:
    """Eén term kan een combinatie zijn ('a + b'): geeft een lijst regex terug die
    ALLEMAAL moeten matchen (AND). '*' = woorddeel-wildcard, '|' = OR binnen een deel."""
    delen = [d.strip() for d in term.split("+")]
    patronen = []
    for deel in delen:
        deel_patroon = deel.replace("(", r"\(?").replace(")", r"\)?")
        deel_patroon = deel_patroon.replace("*", r"\w*")
        patronen.append(re.compile(deel_patroon, re.IGNORECASE))
    return patronen


def _matcht(tekst: str, patronen: list[re.Pattern]) -> bool:
    return all(p.search(tekst) for p in patronen)


def analyseer_termen(config: dict, seed: int = 20260925) -> dict:
    with open(ROOT / config["paden"]["passages_csv"], encoding="utf-8") as f:
        passages = list(csv.DictReader(f))

    rng = random.Random(seed)
    resultaat = {}
    for thema, termen in STARTLIJST.items():
        thema_resultaat = []
        for term in termen:
            patronen = _term_naar_patroon(term)
            treffers = [p for p in passages if _matcht(p["tekst"], patronen)]
            gemeenten = {p["gemeente_code"] for p in treffers}
            sectietype_verdeling = Counter(p["sectietype"] for p in treffers)
            domein_verdeling = Counter(p["domein_hint"] for p in treffers)
            voorbeelden = rng.sample(treffers, min(5, len(treffers)))
            thema_resultaat.append({
                "term": term,
                "n_gemeenten": len(gemeenten),
                "n_passages": len(treffers),
                "sectietype_verdeling": sectietype_verdeling,
                "domein_verdeling": domein_verdeling,
                "voorbeelden": voorbeelden,
            })
        resultaat[thema] = thema_resultaat
    return resultaat


def schrijf_termenverkenning_xlsx(config: dict, resultaat: dict):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    for thema, rijen in resultaat.items():
        ws = wb.create_sheet(title=thema[:31])
        ws.append(["term", "n_gemeenten", "n_passages", "sectietype_verdeling", "domein_verdeling",
                   "voorbeeld_gemeente", "voorbeeld_pad", "voorbeeld_tekst"])
        for r in rijen:
            sectie_str = "; ".join(f"{k}={v}" for k, v in r["sectietype_verdeling"].most_common())
            domein_str = "; ".join(f"{k}={v}" for k, v in r["domein_verdeling"].most_common())
            if not r["voorbeelden"]:
                ws.append([r["term"], r["n_gemeenten"], r["n_passages"], sectie_str, domein_str, "", "", "(geen treffers)"])
                continue
            for i, v in enumerate(r["voorbeelden"]):
                if i == 0:
                    ws.append([r["term"], r["n_gemeenten"], r["n_passages"], sectie_str, domein_str,
                               v["gemeente_code"], v["pad"], v["tekst"][:300]])
                else:
                    ws.append(["", "", "", "", "", v["gemeente_code"], v["pad"], v["tekst"][:300]])

    pad = ROOT / config["paden"]["rapportage"] / "termenverkenning.xlsx"
    pad.parent.mkdir(parents=True, exist_ok=True)
    wb.save(pad)
