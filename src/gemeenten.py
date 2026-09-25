"""Laden van data/gemeenten.csv (opgebouwd in stap 1)."""

import csv
from pathlib import Path

from src.config import ROOT


def laad_gemeenten(config: dict, alleen: list[str] | None = None) -> list[dict]:
    """Leest data/gemeenten.csv. `alleen` filtert op gemeente_naam_cvdr (pilotmodus)."""
    pad = ROOT / config["paden"]["gemeenten_csv"]
    with open(pad, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if alleen:
        namen = {n.strip() for n in alleen}
        rows = [r for r in rows if r["gemeente_naam_cvdr"] in namen]
    return rows
