"""Configuratie laden uit config.yaml. Geen termen of regels hardcoden buiten dit bestand."""

import csv
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

# Sommige passages (begrippenlijsten, lange toelichtingen) overschrijden Python's
# standaard CSV-veldlimiet (131072 bytes) -- pipeline-breed opgehoogd.
csv.field_size_limit(sys.maxsize)


def laad_config(pad: str = "config.yaml") -> dict:
    with open(ROOT / pad, encoding="utf-8") as f:
        return yaml.safe_load(f)
