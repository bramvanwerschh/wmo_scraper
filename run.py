#!/usr/bin/env python3
"""Eén toegangspunt voor de CVDR-pijplijn.

Gebruik:
    python run.py --stap inventaris [--gemeenten "'s-Gravenhage,Aa en Hunze,Tiel"]
    python run.py --alles [--gemeenten "..."]
"""

import argparse
import datetime
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.api import CvdrClient
from src.bijlagen import (
    haal_bijlagen_op,
    schrijf_bijlage_passages_csv,
    schrijf_bijlage_status_csv,
    voeg_bijlage_passages_toe_aan_corpus,
)
from src.config import ROOT, laad_config
from src.gemeenten import laad_gemeenten
from src.inventaris import bouw_inventaris, schrijf_inventaris_csv
from src.kwaliteit import (
    bouw_dekking,
    schrijf_dekking_csv,
    schrijf_dekking_samenvatting,
    schrijf_steekproef_controleformulier,
    trek_steekproef,
    voeg_mogelijk_verouderd_toe,
)
from src.ophalen import haal_teksten_op, schrijf_documenten_csv
from src.regionaal import schrijf_gr_deelnemers_csv, voeg_regionale_regelingen_toe_aan_inventaris
from src.termen import analyseer_termen, schrijf_termenverkenning_xlsx
from src.parsen import parse_alle_documenten, schrijf_parse_fouten_csv, schrijf_passages_csv
from src.rapportage_selectie import (
    schrijf_gemeenten_zonder_nadere_regels,
    schrijf_gemeenten_zonder_verordening,
    schrijf_ruis_verdacht,
    schrijf_twijfel,
    schrijf_unieke_titels,
    schrijf_vangnet_in_ruis,
)
from src.selectie import schrijf_conflicten_csv, schrijf_selectie_csv, selecteer

STAPPEN = ["gemeenten", "inventaris", "selectie", "ophalen", "parsen", "kwaliteit", "bijlagen", "termen"]


def zet_logging_op(config: dict) -> Path:
    logs_dir = ROOT / config["paden"]["logs"]
    logs_dir.mkdir(parents=True, exist_ok=True)
    tijdstempel = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_pad = logs_dir / f"run_{tijdstempel}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(log_pad, encoding="utf-8"), logging.StreamHandler()],
    )
    return log_pad


def draai_inventaris(config: dict, gemeente_filter: list[str] | None):
    gemeenten = laad_gemeenten(config, alleen=gemeente_filter)
    logging.info("Inventaris gestart voor %d gemeente(n)", len(gemeenten))
    client = CvdrClient(config)
    rijen = bouw_inventaris(config, gemeenten, client)
    schrijf_inventaris_csv(config, rijen)
    logging.info("Inventaris klaar: %d regelingen over %d gemeente(n)", len(rijen), len(gemeenten))

    per_gemeente: dict[str, int] = {}
    for r in rijen:
        per_gemeente[r["gemeente_code"]] = per_gemeente.get(r["gemeente_code"], 0) + 1
    for code, aantal in per_gemeente.items():
        logging.info("  %s: %d regelingen", code, aantal)


def draai_selectie(config: dict):
    rijen, conflicten = selecteer(config)
    schrijf_selectie_csv(config, rijen)
    schrijf_conflicten_csv(config, conflicten)
    schrijf_unieke_titels(config, rijen)
    schrijf_twijfel(config, rijen)
    schrijf_vangnet_in_ruis(config, rijen)
    schrijf_ruis_verdacht(config, rijen)
    zonder = schrijf_gemeenten_zonder_verordening(config, rijen)
    zonder_nadere = schrijf_gemeenten_zonder_nadere_regels(config, rijen)

    from collections import Counter
    tellingen = Counter(r["categorie"] for r in rijen)
    logging.info("Selectie klaar: %d regelingen geclassificeerd", len(rijen))
    for cat, n in tellingen.most_common():
        logging.info("  %s: %d", cat, n)
    logging.info("Kern-ruis conflicten (kern wint): %d unieke titels", len(conflicten))
    logging.info("Gemeenten zonder kern-verordening: %d", len(zonder))
    logging.info("Gemeenten zonder nadere regels/beleidsregels naast de verordening: %d", len(zonder_nadere))


def draai_ophalen(config: dict):
    client = CvdrClient(config)
    logging.info("Stap 4 (ophalen) gestart")
    rijen = haal_teksten_op(config, client)
    schrijf_documenten_csv(config, rijen)

    n_fout = sum(1 for r in rijen if not r["status"].startswith("ok"))
    foutpercentage = 100 * n_fout / len(rijen) if rijen else 0
    logging.info("Ophalen klaar: %d documenten, %d fouten (%.2f%%)", len(rijen), n_fout, foutpercentage)
    if foutpercentage > 1:
        logging.warning("FOUTPERCENTAGE BOVEN 1%% -- volgens de opdracht (stap 4) moet dit aan Bram gemeld worden.")
        for r in rijen:
            if not r["status"].startswith("ok"):
                logging.warning("  fout: %s/%s (%s): %s", r["cvdr_id"], r["versie"], r["categorie"], r["status"])


def draai_parsen(config: dict):
    logging.info("Stap 5 (parsen) gestart")
    passages, fouten = parse_alle_documenten(config)
    schrijf_passages_csv(config, passages)
    schrijf_parse_fouten_csv(config, fouten)

    with open(ROOT / config["paden"]["documenten_csv"], encoding="utf-8") as f:
        import csv as _csv
        n_docs = sum(1 for _ in _csv.DictReader(f))
    foutpercentage = 100 * len(fouten) / n_docs if n_docs else 0
    logging.info("Parsen klaar: %d passages uit %d documenten, %d parse-fouten/0-artikeldocumenten (%.2f%%)",
                 len(passages), n_docs, len(fouten), foutpercentage)
    if foutpercentage > 2:
        logging.warning("BOVEN DE 2%%-MARGE UIT DE OPDRACHT (stap 5) -- melden aan Bram.")


def draai_kwaliteit(config: dict):
    logging.info("Stap 6 (kwaliteit/dekking) gestart")
    dekking = bouw_dekking(config)
    schrijf_dekking_csv(config, dekking)
    schrijf_dekking_samenvatting(config, dekking)

    with open(ROOT / config["paden"]["selectie_csv"], encoding="utf-8") as f:
        import csv as _csv
        selectie_rijen = list(_csv.DictReader(f))

    steekproef = trek_steekproef(config, dekking, n=10, seed=20260926, uitsluiten=config["pilot_gemeenten"])
    schrijf_steekproef_controleformulier(config, steekproef, selectie_rijen)

    n_verouderd = voeg_mogelijk_verouderd_toe(config)
    logging.info("mogelijk_verouderd gevlagd: %d documenten", n_verouderd)

    n_zonder_verordening = sum(1 for r in dekking if not r["heeft_verordening"])
    n_zonder_nadere = sum(1 for r in dekking if not r["heeft_nadere_of_beleidsregels"])
    logging.info("Dekking klaar voor %d gemeenten", len(dekking))
    logging.info("  zonder verordening: %d | zonder nadere/beleidsregels: %d", n_zonder_verordening, n_zonder_nadere)
    logging.info("Steekproef getrokken: %s", [r["gemeente_naam_cbs"] for r in steekproef])


def draai_bijlagen(config: dict):
    logging.info("Bijlagen (pdf) gestart")
    client = CvdrClient(config)
    passages, status_rijen = haal_bijlagen_op(config, client)
    schrijf_bijlage_passages_csv(config, passages)
    schrijf_bijlage_status_csv(config, status_rijen)
    n_toegevoegd = voeg_bijlage_passages_toe_aan_corpus(config, passages)
    logging.info("Bijlage-passages toegevoegd aan data/passages.csv: %d", n_toegevoegd)

    n_ok = sum(1 for r in status_rijen if r["status"] == "ok")
    n_scan = sum(1 for r in status_rijen if r["status"].startswith("gevlagd"))
    n_fout = sum(1 for r in status_rijen if r["status"].startswith("fout"))
    logging.info("Bijlagen klaar: %d bijlagen (%d ok, %d scans zonder tekstlaag, %d fouten), %d passages",
                 len(status_rijen), n_ok, n_scan, n_fout, len(passages))


def draai_termen(config: dict):
    logging.info("Termenverkenning (stap 7) gestart")
    resultaat = analyseer_termen(config)
    schrijf_termenverkenning_xlsx(config, resultaat)
    for thema, rijen in resultaat.items():
        for r in rijen:
            logging.info("  [%s] %s: corpus %d gem./%d pass. | filter %d gem./%d pass.", thema, r["term"],
                         r["corpus"]["n_gemeenten"], r["corpus"]["n_passages"],
                         r["filter"]["n_gemeenten"], r["filter"]["n_passages"])


def main():
    parser = argparse.ArgumentParser(description="CVDR-corpus Wmo-mantelzorg pijplijn")
    parser.add_argument("--stap", choices=STAPPEN, help="voer één stap uit")
    parser.add_argument("--alles", action="store_true", help="voer de hele pijplijn uit")
    parser.add_argument("--gemeenten", help="pilotmodus: kommagescheiden lijst CVDR-gemeentenamen")
    args = parser.parse_args()

    if not args.stap and not args.alles:
        parser.error("geef --stap <naam> of --alles op")

    config = laad_config()
    log_pad = zet_logging_op(config)
    logging.info("Configuratie geladen, peildatum=%s", config["peildatum"])
    logging.info("Logbestand: %s", log_pad)

    gemeente_filter = None
    if args.gemeenten:
        gemeente_filter = [g.strip() for g in args.gemeenten.split(",")]
        logging.info("Pilotmodus actief voor: %s", gemeente_filter)

    if args.stap == "inventaris":
        draai_inventaris(config, gemeente_filter)
    elif args.stap == "selectie":
        draai_selectie(config)
    elif args.stap == "ophalen":
        draai_ophalen(config)
    elif args.stap == "parsen":
        draai_parsen(config)
    elif args.stap == "kwaliteit":
        draai_kwaliteit(config)
    elif args.stap == "bijlagen":
        draai_bijlagen(config)
    elif args.stap == "termen":
        draai_termen(config)
    elif args.alles:
        logging.error("--alles is nog niet geimplementeerd (stappen worden stap-voor-stap gebouwd)")
        sys.exit(1)
    else:
        logging.error("Stap '%s' is nog niet geimplementeerd", args.stap)
        sys.exit(1)


if __name__ == "__main__":
    main()
