"""Stap 6: kwaliteitscontrole en dekking."""

import csv
import random
import re
from collections import Counter, defaultdict

from src.config import ROOT
from src.rapportage_selectie import (
    _NADERE_REGELS_PATROON,
    _TOEZICHT_MANDAAT_PATROON,
    _VERORDENING_PATROON,
    normaliseer_titel,
)

MANTELZORG_PATROON = re.compile(r"mantelzorg", re.IGNORECASE)
JAARTAL_PATROON = re.compile(r"\b(20\d{2})\b")


def _laad(pad):
    with open(pad, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def bouw_dekking(config: dict) -> list[dict]:
    gemeenten = _laad(ROOT / config["paden"]["gemeenten_csv"])
    inventaris = _laad(ROOT / config["paden"]["inventaris_csv"])
    selectie = _laad(ROOT / config["paden"]["selectie_csv"])
    passages = _laad(ROOT / config["paden"]["passages_csv"])

    inv_per_gemeente = defaultdict(list)
    for r in inventaris:
        inv_per_gemeente[r["gemeente_code"]].append(r)

    sel_per_gemeente = defaultdict(list)
    for r in selectie:
        sel_per_gemeente[r["gemeente_code"]].append(r)

    pas_per_gemeente = defaultdict(list)
    for r in passages:
        pas_per_gemeente[r["gemeente_code"]].append(r)

    rijen = []
    for g in gemeenten:
        code = g["gemeente_code"]
        inv = inv_per_gemeente.get(code, [])
        sel = sel_per_gemeente.get(code, [])
        pas = pas_per_gemeente.get(code, [])

        tellingen = Counter(r["categorie"] for r in sel)
        kern_docs = [r for r in sel if r["categorie"] == "kern"]
        verordening_docs = [r for r in kern_docs if _VERORDENING_PATROON.search(r["titel"] or "")]
        heeft_verordening = bool(verordening_docs)

        detail_kandidaten = [
            r for r in kern_docs
            if not _TOEZICHT_MANDAAT_PATROON.search(r["titel"] or "")
            and not _VERORDENING_PATROON.search(r["titel"] or "")
        ]
        heeft_nadere_of_beleidsregels = any(
            _NADERE_REGELS_PATROON.search(r["titel"] or "") for r in detail_kandidaten
        )

        datum_laatste_wijziging = ""
        if verordening_docs:
            datums = [r["geldig_vanaf"] for r in verordening_docs if r["geldig_vanaf"]]
            if datums:
                datum_laatste_wijziging = max(datums)

        n_passages_mantelzorg = sum(1 for p in pas if MANTELZORG_PATROON.search(p["tekst"] or ""))

        rijen.append({
            "gemeente_code": code,
            "gemeente_naam_cbs": g["gemeente_naam_cbs"],
            "inwoners": g["inwoners"],
            "n_inventaris": len(inv),
            "n_kern": tellingen.get("kern", 0),
            "n_waardering": tellingen.get("waardering", 0),
            "n_jeugd": tellingen.get("jeugd", 0),
            "n_aanbod": tellingen.get("aanbod", 0),
            "heeft_verordening": heeft_verordening,
            "heeft_nadere_of_beleidsregels": heeft_nadere_of_beleidsregels,
            "datum_laatste_wijziging_verordening": datum_laatste_wijziging,
            "n_passages": len(pas),
            "n_passages_met_mantelzorg": n_passages_mantelzorg,
        })
    return rijen


DEKKING_KOLOMMEN = [
    "gemeente_code", "gemeente_naam_cbs", "inwoners", "n_inventaris", "n_kern", "n_waardering",
    "n_jeugd", "n_aanbod", "heeft_verordening", "heeft_nadere_of_beleidsregels",
    "datum_laatste_wijziging_verordening", "n_passages", "n_passages_met_mantelzorg",
]


def schrijf_dekking_csv(config: dict, rijen: list[dict]):
    pad = ROOT / config["paden"]["rapportage"] / "dekking.csv"
    pad.parent.mkdir(parents=True, exist_ok=True)
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=DEKKING_KOLOMMEN)
        w.writeheader()
        for r in rijen:
            w.writerow(r)


def schrijf_dekking_samenvatting(config: dict, rijen: list[dict]):
    n = len(rijen)
    zonder_verordening = [r for r in rijen if not r["heeft_verordening"]]
    zonder_nadere = [r for r in rijen if not r["heeft_nadere_of_beleidsregels"]]
    zonder_mantelzorg_passage = [r for r in rijen if r["n_kern"] > 0 and r["n_passages_met_mantelzorg"] == 0]

    n_kern_lijst = sorted(r["n_kern"] for r in rijen)
    n_passages_lijst = sorted(r["n_passages"] for r in rijen)

    def mediaan(lijst):
        if not lijst:
            return 0
        m = len(lijst) // 2
        return lijst[m] if len(lijst) % 2 else (lijst[m - 1] + lijst[m]) / 2

    uitschieters_weinig_passages = sorted(
        [r for r in rijen if r["n_kern"] > 0], key=lambda r: r["n_passages"]
    )[:10]
    uitschieters_veel_passages = sorted(
        [r for r in rijen if r["n_kern"] > 0], key=lambda r: -r["n_passages"]
    )[:10]

    regels = []
    regels.append("# Dekkingssamenvatting (stap 6)\n")
    regels.append(f"Totaal aantal gemeenten: {n}\n")
    regels.append("## Verdelingen\n")
    regels.append(f"- n_kern per gemeente: mediaan {mediaan(n_kern_lijst)}, min {min(n_kern_lijst)}, max {max(n_kern_lijst)}")
    regels.append(f"- n_passages per gemeente: mediaan {mediaan(n_passages_lijst)}, min {min(n_passages_lijst)}, max {max(n_passages_lijst)}")
    regels.append(f"- Gemeenten met heeft_verordening=False: {len(zonder_verordening)}")
    regels.append(f"- Gemeenten met heeft_nadere_of_beleidsregels=False: {len(zonder_nadere)}")
    regels.append(f"- Gemeenten met kern-documenten maar 0 passages met 'mantelzorg': {len(zonder_mantelzorg_passage)}\n")

    regels.append("## Gemeenten zonder verordening\n")
    for r in zonder_verordening:
        regels.append(f"- {r['gemeente_naam_cbs']} ({r['gemeente_code']})")
    regels.append("")

    regels.append("## Gemeenten zonder nadere regels/beleidsregels naast de verordening\n")
    for r in zonder_nadere:
        regels.append(f"- {r['gemeente_naam_cbs']} ({r['gemeente_code']})")
    regels.append("")

    regels.append("## Gemeenten met kern-documenten maar 0 mantelzorg-passages\n")
    for r in zonder_mantelzorg_passage:
        regels.append(f"- {r['gemeente_naam_cbs']} ({r['gemeente_code']}): n_kern={r['n_kern']}, n_passages={r['n_passages']}")
    regels.append("")

    regels.append("## Uitschieters: minste passages (met >=1 kern-document)\n")
    for r in uitschieters_weinig_passages:
        regels.append(f"- {r['gemeente_naam_cbs']}: n_kern={r['n_kern']}, n_passages={r['n_passages']}, inwoners={r['inwoners']}")
    regels.append("")

    regels.append("## Uitschieters: meeste passages\n")
    for r in uitschieters_veel_passages:
        regels.append(f"- {r['gemeente_naam_cbs']}: n_kern={r['n_kern']}, n_passages={r['n_passages']}, inwoners={r['inwoners']}")
    regels.append("")

    pad = ROOT / config["paden"]["rapportage"] / "dekking_samenvatting.md"
    pad.write_text("\n".join(regels), encoding="utf-8")


def trek_steekproef(config: dict, dekking_rijen: list[dict], n: int = 10, seed: int = 20260925,
                     uitsluiten: list[str] | None = None) -> list[dict]:
    """Aselecte steekproef, gespreid naar grootte: sorteer op inwoners, verdeel in
    n even grote groepen, trek per groep één willekeurige gemeente (met vaste seed
    voor reproduceerbaarheid, gelogd in werklog.md). `uitsluiten` = CVDR-gemeentenamen
    die niet in de steekproef mogen komen (bijv. de pilotgemeenten, al uitvoerig bekeken)."""
    uitsluiten_codes = set()
    if uitsluiten:
        gemeenten = _laad(ROOT / config["paden"]["gemeenten_csv"])
        uitsluiten_codes = {g["gemeente_code"] for g in gemeenten if g["gemeente_naam_cvdr"] in uitsluiten}
    bruikbaar = [r for r in dekking_rijen if r["gemeente_code"] not in uitsluiten_codes]
    gesorteerd = sorted(bruikbaar, key=lambda r: int(r["inwoners"] or 0))
    groepen = [gesorteerd[i::n] for i in range(n)]
    rng = random.Random(seed)
    steekproef = [rng.choice(groep) for groep in groepen if groep]
    return steekproef


def schrijf_steekproef_controleformulier(config: dict, steekproef: list[dict], selectie_rijen: list[dict]):
    pad = ROOT / config["paden"]["rapportage"] / "steekproef_controleformulier.csv"
    pad.parent.mkdir(parents=True, exist_ok=True)
    kolommen = ["gemeente_naam_cbs", "inwoners", "cvdr_id", "versie", "titel", "categorie", "gevonden_via_website_of_handmatig"]
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=kolommen)
        w.writeheader()
        for g in steekproef:
            kern = [
                r for r in selectie_rijen
                if r["gemeente_code"] == g["gemeente_code"] and r["categorie"] in ("kern", "waardering")
            ]
            if not kern:
                w.writerow({
                    "gemeente_naam_cbs": g["gemeente_naam_cbs"], "inwoners": g["inwoners"],
                    "cvdr_id": "", "versie": "", "titel": "(geen kern/waardering-documenten gevonden)",
                    "categorie": "", "gevonden_via_website_of_handmatig": "",
                })
                continue
            for r in kern:
                w.writerow({
                    "gemeente_naam_cbs": g["gemeente_naam_cbs"], "inwoners": g["inwoners"],
                    "cvdr_id": r["cvdr_id"], "versie": r["versie"], "titel": r["titel"],
                    "categorie": r["categorie"], "gevonden_via_website_of_handmatig": "",
                })


def voeg_mogelijk_verouderd_toe(config: dict):
    """Punt 8 (checkpoint na stap 5): vlagt documenten waarvan dezelfde gemeente een
    document heeft met een (bijna) gelijke genormaliseerde titel en een recentere
    geldig_vanaf-datum (of jaartal als fallback). Alleen vlaggen, niet verwijderen."""
    inventaris = _laad(ROOT / config["paden"]["inventaris_csv"])
    inv_by_key = {(r["cvdr_id"], r["versie"]): r for r in inventaris}

    documenten_pad = ROOT / config["paden"]["documenten_csv"]
    documenten = _laad(documenten_pad)

    groepen: dict[tuple, list] = defaultdict(list)
    for d in documenten:
        key = (d["cvdr_id"], d["versie"])
        inv = inv_by_key.get(key)
        if not inv:
            continue
        titel = inv["titel"] or ""
        genorm = normaliseer_titel(titel, inv["organisatie"])
        jaren = JAARTAL_PATROON.findall(titel)
        groepen[(d["gemeente_code"], genorm)].append({
            "cvdr_id": d["cvdr_id"], "versie": d["versie"],
            "geldig_vanaf": inv["geldig_vanaf"] or "", "jaartal": max(jaren) if jaren else "",
        })

    def sorteersleutel(d):
        return (d["geldig_vanaf"] or "0000-00-00", d["jaartal"] or "0000")

    mogelijk_verouderd = set()
    for docs in groepen.values():
        if len(docs) < 2:
            continue
        gesorteerd = sorted(docs, key=sorteersleutel)
        nieuwste_sleutel = sorteersleutel(gesorteerd[-1])
        for d in gesorteerd[:-1]:
            if sorteersleutel(d) < nieuwste_sleutel:
                mogelijk_verouderd.add((d["cvdr_id"], d["versie"]))

    kolommen = list(documenten[0].keys())
    if "mogelijk_verouderd" not in kolommen:
        kolommen.append("mogelijk_verouderd")
    for d in documenten:
        d["mogelijk_verouderd"] = (d["cvdr_id"], d["versie"]) in mogelijk_verouderd

    with open(documenten_pad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=kolommen)
        w.writeheader()
        for d in documenten:
            w.writerow(d)

    return len(mogelijk_verouderd)
