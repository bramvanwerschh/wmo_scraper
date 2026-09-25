"""Stap 7: termenverkenning. Telt en toont voorbeelden, interpreteert niet.

Twee kolomsets per term (verzoek Bram, verbeterronde 3): (a) heel corpus, (b) FILTER
= categorie in (kern, waardering), domein_hint in (wmo, beide), sectietype niet in
(begrippen, bijlage, ondertekening, aanhef) -- dat is het deel dat het meest
waarschijnlijk relevant is voor de latere codering.
"""

import csv
import random
import re
import sys
from collections import Counter

import openpyxl

from src.config import ROOT

csv.field_size_limit(sys.maxsize)

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

FILTER_CATEGORIEEN = {"kern", "waardering"}
FILTER_DOMEIN_HINTS = {"wmo", "beide"}
FILTER_UITGESLOTEN_SECTIETYPES = {"begrippen", "bijlage", "bijlage_pdf", "ondertekening", "aanhef"}


def _in_filter(p: dict) -> bool:
    return (
        p["categorie"] in FILTER_CATEGORIEEN
        and p["domein_hint"] in FILTER_DOMEIN_HINTS
        and p["sectietype"] not in FILTER_UITGESLOTEN_SECTIETYPES
    )


def _term_naar_patroon(term: str) -> list[re.Pattern]:
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
    with open(ROOT / config["paden"]["gemeenten_csv"], encoding="utf-8") as f:
        naam_by_code = {g["gemeente_code"]: g["gemeente_naam_cbs"] for g in csv.DictReader(f)}

    rng = random.Random(seed)
    resultaat = {}
    for thema, termen in STARTLIJST.items():
        thema_resultaat = []
        for term in termen:
            patronen = _term_naar_patroon(term)
            treffers_corpus = [p for p in passages if _matcht(p["tekst"], patronen)]
            treffers_filter = [p for p in treffers_corpus if _in_filter(p)]

            voorbeelden = rng.sample(treffers_filter, min(5, len(treffers_filter)))
            for v in voorbeelden:
                v["_gemeente_naam"] = naam_by_code.get(v["gemeente_code"], v["gemeente_code"])

            thema_resultaat.append({
                "term": term,
                "corpus": {
                    "n_gemeenten": len({p["gemeente_code"] for p in treffers_corpus}),
                    "n_passages": len(treffers_corpus),
                },
                "filter": {
                    "n_gemeenten": len({p["gemeente_code"] for p in treffers_filter}),
                    "n_passages": len(treffers_filter),
                    "categorie_verdeling": Counter(p["categorie"] for p in treffers_corpus),
                    "voorbeelden": voorbeelden,
                },
            })
        resultaat[thema] = thema_resultaat
    return resultaat


def schrijf_termenverkenning_xlsx(config: dict, resultaat: dict):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    for thema, rijen in resultaat.items():
        ws = wb.create_sheet(title=thema[:31])
        ws.append([
            "term",
            "n_gemeenten_corpus", "n_passages_corpus",
            "n_gemeenten_filter", "n_passages_filter",
            "categorie_verdeling (heel corpus)",
            "voorbeeld_gemeente", "voorbeeld_pad", "voorbeeld_tekst",
        ])
        for r in rijen:
            cat_str = "; ".join(f"{k}={v}" for k, v in r["filter"]["categorie_verdeling"].most_common())
            voorbeelden = r["filter"]["voorbeelden"]
            basisrij = [
                r["term"],
                r["corpus"]["n_gemeenten"], r["corpus"]["n_passages"],
                r["filter"]["n_gemeenten"], r["filter"]["n_passages"],
                cat_str,
            ]
            if not voorbeelden:
                ws.append(basisrij + ["", "", "(geen treffers binnen FILTER)"])
                continue
            for i, v in enumerate(voorbeelden):
                if i == 0:
                    ws.append(basisrij + [v["_gemeente_naam"], v["pad"], v["tekst"][:300]])
                else:
                    ws.append(["", "", "", "", "", "", v["_gemeente_naam"], v["pad"], v["tekst"][:300]])

    pad = ROOT / config["paden"]["rapportage"] / "termenverkenning.xlsx"
    pad.parent.mkdir(parents=True, exist_ok=True)
    wb.save(pad)
