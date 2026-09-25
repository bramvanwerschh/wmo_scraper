"""Stap 4: volledige tekst ophalen voor alle geselecteerde documenten (categorie != ruis).

WTI-pagina (?show-wti=true) alleen voor kern en waardering (op verzoek van Bram,
2026-09-25) -- geeft bijlage-info en het wijzigingsoverzicht, maar kost een extra
verzoek per document, dus alleen waar het telt.
"""

import csv
import logging
import re
from pathlib import Path

from lxml import etree

from src.api import CvdrClient
from src.config import ROOT

WTI_CATEGORIEEN = {"kern", "waardering"}
TE_OPHALEN_CATEGORIEEN = {"kern", "waardering", "jeugd", "aanbod", "twijfel", "buiten_scope"}

DOCUMENTEN_KOLOMMEN = [
    "cvdr_id", "versie", "gemeente_code", "categorie", "bestand", "wti_bestand",
    "formaat", "n_bytes", "heeft_bijlage", "bijlage_urls", "status",
]

_BIJLAGE_PATROON = re.compile(
    r"<th[^>]*>\s*Externe bijlagen\s*</th>\s*<td[^>]*>(.*?)</td>", re.S | re.IGNORECASE
)


def _valideer_xml(content: bytes, verwachte_titel: str) -> str:
    """Controleert alleen of het welgevormde XML is (parseerbaar), niet het schema --
    CVDR levert zowel het klassieke <cvdr>-schema als het nieuwere STOP/LVBB
    consolidatie-schema (<lvbbu:Consolidaties>) af, beide zijn geldig (§7 stap 4)."""
    if not content:
        return "fout: leeg bestand"
    try:
        etree.fromstring(content)
    except etree.XMLSyntaxError as e:
        return f"fout: geen geldige XML (mogelijk foutpagina): {e}"
    return "ok"


def _detecteer_bijlage_in_wti(wti_html: bytes) -> tuple[bool, str]:
    """De WTI-pagina heeft een tabelrij <th>Externe bijlagen</th><td>...</td>.
    Een lege <td> betekent: geen bijlage. Anders: naam en/of link uit de cel."""
    tekst = wti_html.decode("utf-8", errors="ignore")
    match = _BIJLAGE_PATROON.search(tekst)
    if not match:
        return False, ""
    cel = match.group(1)
    zonder_markup = re.sub(r"<[^>]+>", " ", cel).strip()
    if not zonder_markup:
        return False, ""
    links = re.findall(r'href="([^"]+)"', cel)
    return True, "; ".join(links) if links else zonder_markup


def haal_teksten_op(config: dict, client: CvdrClient) -> list[dict]:
    with open(ROOT / config["paden"]["selectie_csv"], encoding="utf-8") as f:
        rijen = list(csv.DictReader(f))

    te_doen = [r for r in rijen if r["categorie"] in TE_OPHALEN_CATEGORIEEN]
    raw_docs = ROOT / config["paden"]["raw_docs"]
    raw_docs.mkdir(parents=True, exist_ok=True)

    resultaten = []
    for i, rij in enumerate(te_doen, 1):
        cvdr_id, versie = rij["cvdr_id"], rij["versie"]
        bestand = f"{cvdr_id}_{versie}.xml"
        doel_pad = raw_docs / bestand

        status = "ok"
        n_bytes = 0
        heeft_bijlage = "onbekend (WTI niet opgehaald)"
        bijlage_urls = ""
        wti_bestand = ""

        try:
            content = client.haal_op_of_cache(rij["xml_url"], doel_pad)
            status = _valideer_xml(content, rij["titel"])
            n_bytes = len(content)
        except RuntimeError as e:
            status = f"fout: {e}"

        if status == "ok" and rij["categorie"] in WTI_CATEGORIEEN and rij["url"]:
            wti_bestand = f"{cvdr_id}_{versie}_wti.html"
            wti_pad = raw_docs / wti_bestand
            try:
                wti_content = client.haal_op_of_cache(f"{rij['url']}?show-wti=true", wti_pad)
                heeft_bijlage, bijlage_urls = _detecteer_bijlage_in_wti(wti_content)
            except RuntimeError as e:
                wti_bestand = ""
                heeft_bijlage = f"onbekend (WTI-fout: {e})"

        resultaten.append({
            "cvdr_id": cvdr_id,
            "versie": versie,
            "gemeente_code": rij["gemeente_code"],
            "categorie": rij["categorie"],
            "bestand": bestand,
            "wti_bestand": wti_bestand,
            "formaat": "xml",
            "n_bytes": n_bytes,
            "heeft_bijlage": heeft_bijlage,
            "bijlage_urls": bijlage_urls,
            "status": status,
        })

        if i % 200 == 0:
            n_fout = sum(1 for r in resultaten if not r["status"].startswith("ok"))
            logging.info("  %d/%d verwerkt (%d fouten tot nu toe)", i, len(te_doen), n_fout)

    return resultaten


def schrijf_documenten_csv(config: dict, rijen: list[dict]):
    pad = ROOT / config["paden"]["documenten_csv"]
    pad.parent.mkdir(parents=True, exist_ok=True)
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=DOCUMENTEN_KOLOMMEN)
        w.writeheader()
        for r in rijen:
            w.writerow(r)
