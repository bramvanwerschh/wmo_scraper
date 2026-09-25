"""Punt 2 (verbeterronde 2): tekst uit externe pdf-bijlagen van kern/waardering-
documenten die verdacht weinig passage-tekst hebben (< 3.000 tekens) terwijl
heeft_bijlage=True. Scans zonder tekstlaag worden alleen gevlagd, niet ge-OCR'd."""

import csv
import logging
from pathlib import Path

import pdfplumber

from src.api import CvdrClient
from src.config import ROOT
from src.parsen import PASSAGE_KOLOMMEN, _splits_grote_passage

BIJLAGE_PDF_KOLOMMEN = PASSAGE_KOLOMMEN


def vind_kandidaten(config: dict, drempel_tekens: int = 3000) -> list[dict]:
    with open(ROOT / config["paden"]["documenten_csv"], encoding="utf-8") as f:
        documenten = list(csv.DictReader(f))
    with open(ROOT / config["paden"]["passages_csv"], encoding="utf-8") as f:
        passages = list(csv.DictReader(f))

    tekens_per_doc: dict[tuple, int] = {}
    for p in passages:
        key = (p["cvdr_id"], p["versie"])
        tekens_per_doc[key] = tekens_per_doc.get(key, 0) + int(p["n_tekens"])

    kandidaten = []
    for d in documenten:
        if d["categorie"] not in ("kern", "waardering"):
            continue
        if d["heeft_bijlage"] != "True" or not d["bijlage_urls"]:
            continue
        tekens = tekens_per_doc.get((d["cvdr_id"], d["versie"]), 0)
        if tekens < drempel_tekens:
            kandidaten.append(d)
    return kandidaten


def _extraheer_pdf_tekst(pdf_pad: Path) -> tuple[str, bool]:
    """Geeft (tekst, heeft_tekstlaag) terug. Een scan zonder tekstlaag levert lege
    tekst -- die wordt alleen gevlagd, niet ge-OCR'd."""
    delen = []
    with pdfplumber.open(pdf_pad) as pdf:
        for pagina in pdf.pages:
            t = pagina.extract_text() or ""
            if t.strip():
                delen.append(t.strip())
    tekst = "\n\n".join(delen)
    return tekst, bool(tekst.strip())


def haal_bijlagen_op(config: dict, client: CvdrClient) -> tuple[list[dict], list[dict]]:
    """Geeft (passages, status_rijen) terug. status_rijen legt per bijlage vast of
    er een tekstlaag was, hoeveel tekens gewonnen, of een fout."""
    kandidaten = vind_kandidaten(config)
    raw_bijlagen = ROOT / "data" / "raw" / "bijlagen"
    raw_bijlagen.mkdir(parents=True, exist_ok=True)

    alle_passages = []
    status_rijen = []
    volgorde_teller = 0

    for d in kandidaten:
        urls = [u.strip() for u in d["bijlage_urls"].split(";") if u.strip()]
        for i, url in enumerate(urls, 1):
            bestandsnaam = f"{d['cvdr_id']}_{d['versie']}_bijlage{i}.pdf"
            pdf_pad = raw_bijlagen / bestandsnaam
            status = "ok"
            tekst = ""
            heeft_tekstlaag = False
            try:
                content = client.haal_op_of_cache(url, pdf_pad)
                if not content.startswith(b"%PDF"):
                    status = "fout: geen PDF (mogelijk andere bestandsvorm of foutpagina)"
                else:
                    tekst, heeft_tekstlaag = _extraheer_pdf_tekst(pdf_pad)
                    if not heeft_tekstlaag:
                        status = "gevlagd: scan zonder tekstlaag (geen OCR uitgevoerd)"
            except RuntimeError as e:
                status = f"fout: {e}"
            except Exception as e:
                status = f"fout: pdf-parsing mislukt ({e})"

            status_rijen.append({
                "cvdr_id": d["cvdr_id"], "versie": d["versie"], "gemeente_code": d["gemeente_code"],
                "bestand": bestandsnaam, "url": url, "status": status, "n_tekens_geextraheerd": len(tekst),
            })

            if tekst.strip():
                volgorde_teller += 1
                basis_passage = {
                    "passage_id": f"{d['cvdr_id']}_{d['versie']}__bijlage_pdf__{i}",
                    "parent_passage_id": "",
                    "cvdr_id": d["cvdr_id"], "versie": d["versie"], "gemeente_code": d["gemeente_code"],
                    "categorie": d["categorie"],
                    "pad": f"Bijlage {i} (pdf)",
                    "hoofdstuk_titel": "", "artikel_nr": "", "artikel_titel": "", "lid_nr": "",
                    "toelichting_kop": "", "toelichting_sub": "", "toelichting_artikel_ref": "",
                    "koppeling_status": "", "wet_label": "",
                    "sectietype": "bijlage_pdf", "domein_hint": "onbekend",
                    "tekst": tekst.strip(), "n_tekens": len(tekst.strip()), "volgorde": volgorde_teller,
                }
                for deel in _splits_grote_passage(basis_passage):
                    alle_passages.append(deel)

    return alle_passages, status_rijen


def schrijf_bijlage_passages_csv(config: dict, passages: list[dict]):
    pad = ROOT / config["paden"]["rapportage"] / "bijlage_pdf_passages.csv"
    pad.parent.mkdir(parents=True, exist_ok=True)
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=BIJLAGE_PDF_KOLOMMEN)
        w.writeheader()
        for p in passages:
            w.writerow(p)


def voeg_bijlage_passages_toe_aan_corpus(config: dict, bijlage_passages: list[dict]):
    """Voegt de pdf-bijlage-passages toe aan data/passages.csv. Let op: stap 'parsen'
    schrijft dat bestand steeds volledig opnieuw (vanuit de XML's, die geen
    bijlage-inhoud bevatten) -- 'bijlagen' moet dus ná 'parsen' draaien."""
    passages_pad = ROOT / config["paden"]["passages_csv"]
    with open(passages_pad, encoding="utf-8") as f:
        bestaande = list(csv.DictReader(f))
    bestaande_ids = {p["passage_id"] for p in bestaande}
    nieuw = [p for p in bijlage_passages if p["passage_id"] not in bestaande_ids]

    with open(passages_pad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=BIJLAGE_PDF_KOLOMMEN)
        w.writeheader()
        for p in bestaande + nieuw:
            w.writerow({k: p.get(k, "") for k in BIJLAGE_PDF_KOLOMMEN})
    return len(nieuw)


def schrijf_bijlage_status_csv(config: dict, status_rijen: list[dict]):
    pad = ROOT / config["paden"]["rapportage"] / "bijlage_pdf_status.csv"
    pad.parent.mkdir(parents=True, exist_ok=True)
    kolommen = ["cvdr_id", "versie", "gemeente_code", "bestand", "url", "status", "n_tekens_geextraheerd"]
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=kolommen)
        w.writeheader()
        for r in status_rijen:
            w.writerow(r)
