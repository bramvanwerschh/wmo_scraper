"""Rapportages voor stap 3 (selectie): unieke titels, twijfellijst, vangnet-in-ruis,
gemeenten zonder verordening. Basis voor checkpoint A5 + A6."""

import csv
import re
from collections import defaultdict

from src.config import ROOT


def normaliseer_titel(titel: str, gemeente_naam: str) -> str:
    t = titel or ""
    t = re.sub(r"\b(19|20)\d{2}(\s*[-–/]\s*(19|20)?\d{2,4})?\b", "", t)
    if gemeente_naam:
        t = re.sub(re.escape(gemeente_naam), "", t, flags=re.IGNORECASE)
    t = re.sub(r"\bgemeente\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip(" -–,")
    return t


def schrijf_unieke_titels(config: dict, rijen: list[dict]):
    groepen: dict[tuple[str, str], int] = defaultdict(int)
    for r in rijen:
        genorm = normaliseer_titel(r["titel"], r["organisatie"])
        groepen[(genorm, r["categorie"])] += 1

    pad = ROOT / config["paden"]["rapportage"] / "unieke_titels.csv"
    pad.parent.mkdir(parents=True, exist_ok=True)
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["titel_genormaliseerd", "categorie", "aantal"])
        for (titel, categorie), aantal in sorted(groepen.items(), key=lambda x: (-x[1], x[0][0])):
            w.writerow([titel, categorie, aantal])


def schrijf_twijfel(config: dict, rijen: list[dict]):
    twijfel = [r for r in rijen if r["categorie"] == "twijfel"]
    # Sorteren op frequentie van de genormaliseerde titel, zodat de meest voorkomende
    # (en dus meest impactvolle) gevallen bovenaan staan voor Bram's beoordeling.
    frequentie: dict[str, int] = defaultdict(int)
    for r in twijfel:
        frequentie[normaliseer_titel(r["titel"], r["organisatie"])] += 1
    twijfel_gesorteerd = sorted(
        twijfel,
        key=lambda r: (-frequentie[normaliseer_titel(r["titel"], r["organisatie"])], r["titel"] or ""),
    )
    _schrijf_subset(config, twijfel_gesorteerd, "twijfel.csv")


def schrijf_vangnet_in_ruis(config: dict, rijen: list[dict]):
    subset = [r for r in rijen if r["categorie"] == "ruis" and r["vangnet_treffer"] == "True"]
    _schrijf_subset(config, subset, "vangnet_in_ruis.csv")


# Tolerant voor de typo "Verordering" i.p.v. "Verordening" die in de brondata voorkomt
# (bijv. Alkmaar, CVDR636733/2): verorde + n of r + ing.
_VERORDENING_PATROON = re.compile(r"verorde[nr]ing", re.IGNORECASE)

RUIS_VERDACHT_PATROON = re.compile(
    r"zorg|welzijn|sociaal|ondersteuning|hulp|maatschappelijk|mantelzorg", re.IGNORECASE
)


def schrijf_ruis_verdacht(config: dict, rijen: list[dict]):
    """Ruis-titels met een mogelijk sociaal-domeinsignaal, ter controle op gemiste
    documenten (punt 8, checkpoint stap 3)."""
    verdacht = [
        r for r in rijen
        if r["categorie"] == "ruis" and RUIS_VERDACHT_PATROON.search(r["titel"] or "")
    ]
    groepen: dict[str, int] = defaultdict(int)
    voorbeeld: dict[str, dict] = {}
    for r in verdacht:
        genorm = normaliseer_titel(r["titel"], r["organisatie"])
        groepen[genorm] += 1
        voorbeeld.setdefault(genorm, r)

    pad = ROOT / config["paden"]["rapportage"] / "ruis_verdacht.csv"
    pad.parent.mkdir(parents=True, exist_ok=True)
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["titel_genormaliseerd", "aantal", "voorbeeld_titel", "voorbeeld_gemeente", "voorbeeld_cvdr_id"])
        for genorm, aantal in sorted(groepen.items(), key=lambda x: (-x[1], x[0])):
            v = voorbeeld[genorm]
            w.writerow([genorm, aantal, v["titel"], v["organisatie"], v["cvdr_id"]])


def schrijf_gemeenten_zonder_verordening(config: dict, rijen: list[dict]):
    heeft_verordening = set()
    for r in rijen:
        if r["categorie"] == "kern" and _VERORDENING_PATROON.search(r["titel"] or ""):
            heeft_verordening.add(r["gemeente_code"])

    with open(ROOT / config["paden"]["gemeenten_csv"], encoding="utf-8") as f:
        gemeenten = list(csv.DictReader(f))
    zonder = [g for g in gemeenten if g["gemeente_code"] not in heeft_verordening]

    pad = ROOT / config["paden"]["rapportage"] / "gemeenten_zonder_verordening.csv"
    pad.parent.mkdir(parents=True, exist_ok=True)
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["gemeente_code", "gemeente_naam_cbs", "gemeente_naam_cvdr", "provincie"])
        w.writeheader()
        for g in zonder:
            w.writerow({k: g[k] for k in ["gemeente_code", "gemeente_naam_cbs", "gemeente_naam_cvdr", "provincie"]})
    return zonder


_TOEZICHT_MANDAAT_PATROON = re.compile(r"toezicht|mandaat", re.IGNORECASE)
_NADERE_REGELS_PATROON = re.compile(
    r"nadere regels|beleidsregel|besluit|uitvoering|regeling|protocol gebruikelijke|handboek",
    re.IGNORECASE,
)


def schrijf_gemeenten_zonder_nadere_regels(config: dict, rijen: list[dict]):
    """Gemeenten zonder enig kern-document naast de verordening zelf dat op uitvoerings-
    detail wijst (nadere regels/beleidsregel/besluit/etc.). Toezicht-/mandaatdocumenten
    tellen niet mee (punt 2, checkpoint na stap 4)."""
    per_gemeente: dict[str, list[dict]] = defaultdict(list)
    for r in rijen:
        if r["categorie"] == "kern":
            per_gemeente[r["gemeente_code"]].append(r)

    with open(ROOT / config["paden"]["gemeenten_csv"], encoding="utf-8") as f:
        gemeenten = list(csv.DictReader(f))

    zonder = []
    for g in gemeenten:
        kern_docs = per_gemeente.get(g["gemeente_code"], [])
        kandidaten = [
            r for r in kern_docs
            if not _TOEZICHT_MANDAAT_PATROON.search(r["titel"] or "")
            and not _VERORDENING_PATROON.search(r["titel"] or "")
        ]
        heeft_detail = any(_NADERE_REGELS_PATROON.search(r["titel"] or "") for r in kandidaten)
        if not heeft_detail:
            zonder.append(g)

    pad = ROOT / config["paden"]["rapportage"] / "gemeenten_zonder_nadere_regels.csv"
    pad.parent.mkdir(parents=True, exist_ok=True)
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["gemeente_code", "gemeente_naam_cbs", "gemeente_naam_cvdr", "provincie"])
        w.writeheader()
        for g in zonder:
            w.writerow({k: g[k] for k in ["gemeente_code", "gemeente_naam_cbs", "gemeente_naam_cvdr", "provincie"]})
    return zonder


def _schrijf_subset(config: dict, rijen: list[dict], bestandsnaam: str):
    pad = ROOT / config["paden"]["rapportage"] / bestandsnaam
    pad.parent.mkdir(parents=True, exist_ok=True)
    kolommen = list(rijen[0].keys()) if rijen else [
        "gemeente_code", "cvdr_id", "versie", "titel", "categorie", "reden",
    ]
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=kolommen)
        w.writeheader()
        for r in rijen:
            w.writerow(r)
