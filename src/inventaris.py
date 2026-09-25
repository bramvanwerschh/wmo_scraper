"""Stap 2: inventaris (breed, alleen metadata) per gemeente + landelijke vangnet-vlag."""

import csv
import datetime
import re
from pathlib import Path

from src.api import CvdrClient
from src.config import ROOT
from src.cvdr_xml import parse_search_response

INVENTARIS_KOLOMMEN = [
    "gemeente_code", "cvdr_id", "versie", "titel", "soort_regeling", "indeling",
    "onderwerp", "geldig_vanaf", "geldig_tot", "organisatie", "url", "xml_url",
    "vangnet_treffer", "vangnet_termen", "opgehaald_op",
]


def _slug(tekst: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", tekst.lower()).strip("_")


def _cql_escape_gemeente(naam: str) -> str:
    return naam.replace('"', '\\"')


def _pagineer(client: CvdrClient, query: str, cache_prefix: Path) -> list[dict]:
    """Haalt alle pagina's van een SRU-zoekvraag op, met caching per pagina (hervatbaar)."""
    alle_records: list[dict] = []
    start = 1
    pagina = 1
    while True:
        cache_pad = cache_prefix.parent / f"{cache_prefix.name}_p{pagina}.xml"
        if cache_pad.exists():
            xml_bytes = cache_pad.read_bytes()
        else:
            xml_text = client.sru_search(query, start_record=start)
            xml_bytes = xml_text.encode("utf-8")
            cache_pad.parent.mkdir(parents=True, exist_ok=True)
            cache_pad.write_bytes(xml_bytes)

        records, n_total, next_pos = parse_search_response(xml_bytes)
        alle_records.extend(records)

        if not next_pos or next_pos <= start:
            break
        start = next_pos
        pagina += 1
    return alle_records


def haal_gemeente_inventaris(client: CvdrClient, config: dict, gemeente_naam: str) -> list[dict]:
    peildatum = config["peildatum"]
    query = (
        f'gemeente="{_cql_escape_gemeente(gemeente_naam)}" '
        f'and overheidrg.datumGeldendOp={peildatum}'
    )
    cache_prefix = ROOT / config["paden"]["raw_zoek"] / f"inventaris_{_slug(gemeente_naam)}_{peildatum}"
    return _pagineer(client, query, cache_prefix)


def _cql_relatie(term: str) -> str:
    """Meerwoordtermen (frases tussen aanhalingstekens) moeten met de adjacency-operator
    'adj' gezocht worden. Met '=' matcht de SRU-index losse woorden ongeacht volgorde/nabijheid
    (geverifieerd: "gebruikelijke zorg" matchte met '=' ook documenten waarin die twee woorden
    los van elkaar voorkomen, bijv. "...gebruikelijke wijze..." + "...secretaris zorgt...")."""
    kaal = term.strip('"')
    return "adj" if " " in kaal else "="


def haal_vangnet_matches(client: CvdrClient, config: dict) -> dict[str, set[str]]:
    """Landelijke zoekactie per vangnetterm. Geeft {term: {"CVDRid_versie", ...}} terug."""
    peildatum = config["peildatum"]
    resultaat: dict[str, set[str]] = {}
    for term in config["vangnet_termen"]:
        relatie = _cql_relatie(term)
        query = f'overheidrg.body {relatie} {term} and overheidrg.datumGeldendOp={peildatum}'
        cache_prefix = ROOT / config["paden"]["raw_zoek"] / f"vangnet_{_slug(term)}_{peildatum}"
        records = _pagineer(client, query, cache_prefix)
        resultaat[term] = {f"{r['cvdr_id']}_{r['versie']}" for r in records}
    return resultaat


def bouw_inventaris(config: dict, gemeenten: list[dict], client: CvdrClient) -> list[dict]:
    vangnet_matches = haal_vangnet_matches(client, config)

    alle_rijen = []
    for gemeente in gemeenten:
        records = haal_gemeente_inventaris(client, config, gemeente["gemeente_naam_cvdr"])
        opgehaald_op = datetime.datetime.now().isoformat(timespec="seconds")
        for r in records:
            identifier = f"{r['cvdr_id']}_{r['versie']}"
            treffer_termen = [term for term, ids in vangnet_matches.items() if identifier in ids]
            rij = {
                "gemeente_code": gemeente["gemeente_code"],
                "cvdr_id": r["cvdr_id"],
                "versie": r["versie"],
                "titel": r["titel"],
                "soort_regeling": r["soort_regeling"],
                "indeling": r["indeling"],
                "onderwerp": r["onderwerp"],
                "geldig_vanaf": r["geldig_vanaf"],
                "geldig_tot": r["geldig_tot"],
                "organisatie": r["organisatie"],
                "url": r["url"],
                "xml_url": r["xml_url"],
                "vangnet_treffer": bool(treffer_termen),
                "vangnet_termen": "; ".join(treffer_termen),
                "opgehaald_op": opgehaald_op,
            }
            alle_rijen.append(rij)
    return alle_rijen


def schrijf_inventaris_csv(config: dict, rijen: list[dict], overschrijven_pad: str | None = None):
    pad = ROOT / (overschrijven_pad or config["paden"]["inventaris_csv"])
    pad.parent.mkdir(parents=True, exist_ok=True)
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=INVENTARIS_KOLOMMEN)
        w.writeheader()
        for rij in rijen:
            w.writerow(rij)
