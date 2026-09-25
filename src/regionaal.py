"""Regionale/gemeenschappelijke-regeling-documenten (punt 5, verbeterronde 2).

Landelijke SRU-zoekactie (title~wmo|maatschappelijke ondersteuning|sociaal domein,
organisatietype != Gemeente) leverde 45 documenten op. Hiervan zijn er 11, verdeeld
over 3 regio's, met tekstonderzoek geverifieerd als (a) substantieve Wmo-regelgeving
(geen zuiver bestuurlijke archief-/controleverordening) en (b) met een geverifieerde
deelnemerslijst:

- Drechtsteden (organisatie "Sociaal" in CVDR): Alblasserdam, Dordrecht,
  Hardinxveld-Giessendam, Hendrik-Ido-Ambacht, Papendrecht, Sliedrecht, Zwijndrecht.
- ISD Bollenstreek: Hillegom, Lisse, Noordwijk, Teylingen.
- Samenwerking De Bevelanden: Borsele, Goes, Kapelle, Noord-Beveland, Reimerswaal.

De overige ~34 gevonden organisaties/documenten (vooral Modulaire Gemeenschappelijke
Regeling Sociaal Domein Centraal Gelderland / Limburg-Noord, GGD-toezichtmandaten,
Eemkracht) zijn wel gevonden (review/gr_organisaties_volledig.csv) maar NIET
toegevoegd: overwegend bestuurlijke documenten (archiefverordening, controle-
verordening, mandaatbesluiten) zonder substantiële Wmo-inhoud, of deelnemerslijst
niet geverifieerd. Kan op verzoek alsnog uitgebreid worden.
"""

import csv

from src.config import ROOT

REGIO_DEELNEMERS = {
    "drechtsteden": ["Alblasserdam", "Dordrecht", "Hardinxveld-Giessendam",
                      "Hendrik-Ido-Ambacht", "Papendrecht", "Sliedrecht", "Zwijndrecht"],
    "isd_bollenstreek": ["Hillegom", "Lisse", "Noordwijk", "Teylingen"],
    "de_bevelanden": ["Borsele", "Goes", "Kapelle", "Noord-Beveland", "Reimerswaal"],
}

# (cvdr_id, versie, titel, geldig_vanaf, xml_url, regio_id, bron_organisatie)
REGIONALE_DOCUMENTEN = [
    ("CVDR762052", "1", "Beleidsregels maatschappelijke ondersteuning Drechtsteden", "2026-06-01",
     "https://repository.officiele-overheidspublicaties.nl/cvdr/CVDR762052/1/xml/CVDR762052_1.xml",
     "drechtsteden", "Sociaal (Drechtsteden)"),
    ("CVDR676732", "1", "Mandaat- en aanwijzingsbesluit toezichthouders Wmo 2015 Drechtsteden", "2022-05-18",
     "https://repository.officiele-overheidspublicaties.nl/cvdr/CVDR676732/1/xml/CVDR676732_1.xml",
     "drechtsteden", "Sociaal (Drechtsteden)"),
    ("CVDR749069", "1", "Uitvoeringsbesluit maatschappelijke ondersteuning ISD Bollenstreek 2026", "2026-01-01",
     "https://repository.officiele-overheidspublicaties.nl/cvdr/CVDR749069/1/xml/CVDR749069_1.xml",
     "isd_bollenstreek", "Intergemeentelijke Sociale Dienst (ISD) Bollenstreek"),
    ("CVDR749070", "1", "Uitvoeringsregels maatschappelijke ondersteuning ISD Bollenstreek 2026", "2026-01-01",
     "https://repository.officiele-overheidspublicaties.nl/cvdr/CVDR749070/1/xml/CVDR749070_1.xml",
     "isd_bollenstreek", "Intergemeentelijke Sociale Dienst (ISD) Bollenstreek"),
    ("CVDR700433", "1", "Beleidsregels maatschappelijke ondersteuning - Versie 2023 - 1. Algemeen kader", "2023-04-01",
     "https://repository.officiele-overheidspublicaties.nl/cvdr/CVDR700433/1/xml/CVDR700433_1.xml",
     "de_bevelanden", "Samenwerking De Bevelanden"),
    ("CVDR700435", "1", "Beleidsregels maatschappelijke ondersteuning - Versie 2023 - 2. Vervoers- en rolstoelvoorzieningen", "2023-04-01",
     "https://repository.officiele-overheidspublicaties.nl/cvdr/CVDR700435/1/xml/CVDR700435_1.xml",
     "de_bevelanden", "Samenwerking De Bevelanden"),
    ("CVDR700436", "1", "Beleidsregels maatschappelijke ondersteuning - Versie 2023 - 3. Woonvoorzieningen", "2023-04-01",
     "https://repository.officiele-overheidspublicaties.nl/cvdr/CVDR700436/1/xml/CVDR700436_1.xml",
     "de_bevelanden", "Samenwerking De Bevelanden"),
    ("CVDR722634", "1", "Beleidsregels maatschappelijke ondersteuning - Versie 2024 - 4. Huishoudelijke ondersteuning", "2024-07-18",
     "https://repository.officiele-overheidspublicaties.nl/cvdr/CVDR722634/1/xml/CVDR722634_1.xml",
     "de_bevelanden", "Samenwerking De Bevelanden"),
    ("CVDR722637", "2", "Beleidsregels maatschappelijke ondersteuning - Versie 2024 - 5. Begeleiding en dagbesteding", "2024-09-18",
     "https://repository.officiele-overheidspublicaties.nl/cvdr/CVDR722637/2/xml/CVDR722637_2.xml",
     "de_bevelanden", "Samenwerking De Bevelanden"),
    ("CVDR700443", "1", "Beleidsregels maatschappelijke ondersteuning - Versie 2023 - 6. Sportvoorzieningen", "2023-04-01",
     "https://repository.officiele-overheidspublicaties.nl/cvdr/CVDR700443/1/xml/CVDR700443_1.xml",
     "de_bevelanden", "Samenwerking De Bevelanden"),
    ("CVDR722633", "2", "Beleidsregels maatschappelijke ondersteuning - Versie 2024 - 7. Pgb", "2022-05-30",
     "https://repository.officiele-overheidspublicaties.nl/cvdr/CVDR722633/2/xml/CVDR722633_2.xml",
     "de_bevelanden", "Samenwerking De Bevelanden"),
]


def schrijf_gr_deelnemers_csv(config: dict):
    with open(ROOT / config["paden"]["gemeenten_csv"], encoding="utf-8") as f:
        gemeenten = list(csv.DictReader(f))
    naam_naar_code = {g["gemeente_naam_cvdr"]: g["gemeente_code"] for g in gemeenten}

    pad = ROOT / "data" / "gr_deelnemers.csv"
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["regio_id", "bron_organisatie", "gemeente_code", "gemeente_naam_cvdr"])
        bron_org = {r[5]: r[6] for r in REGIONALE_DOCUMENTEN}
        for regio_id, namen in REGIO_DEELNEMERS.items():
            org = next((r[6] for r in REGIONALE_DOCUMENTEN if r[5] == regio_id), "")
            for naam in namen:
                code = naam_naar_code.get(naam, "ONBEKEND")
                w.writerow([regio_id, org, code, naam])


def voeg_regionale_regelingen_toe_aan_inventaris(config: dict) -> int:
    """Voegt per regionaal document één rij per deelnemende gemeente toe aan
    inventaris.csv (regionaal=True, bron_organisatie, regio_id ingevuld)."""
    with open(ROOT / config["paden"]["gemeenten_csv"], encoding="utf-8") as f:
        gemeenten = list(csv.DictReader(f))
    naam_naar_code = {g["gemeente_naam_cvdr"]: g["gemeente_code"] for g in gemeenten}

    inventaris_pad = ROOT / config["paden"]["inventaris_csv"]
    with open(inventaris_pad, encoding="utf-8") as f:
        bestaand = list(csv.DictReader(f))

    kolommen = list(bestaand[0].keys())
    for extra in ("regionaal", "bron_organisatie", "regio_id"):
        if extra not in kolommen:
            kolommen.append(extra)
    for r in bestaand:
        r.setdefault("regionaal", "False")
        r.setdefault("bron_organisatie", "")
        r.setdefault("regio_id", "")

    bestaande_sleutels = {(r["cvdr_id"], r["versie"], r["gemeente_code"]) for r in bestaand}

    nieuwe_rijen = []
    for cvdr_id, versie, titel, geldig_vanaf, xml_url, regio_id, bron_organisatie in REGIONALE_DOCUMENTEN:
        for naam in REGIO_DEELNEMERS[regio_id]:
            code = naam_naar_code.get(naam)
            if not code:
                continue
            sleutel = (cvdr_id, versie, code)
            if sleutel in bestaande_sleutels:
                continue
            nieuwe_rijen.append({
                "gemeente_code": code, "cvdr_id": cvdr_id, "versie": versie, "titel": titel,
                "soort_regeling": "", "indeling": "", "onderwerp": "",
                "geldig_vanaf": geldig_vanaf, "geldig_tot": "",
                "organisatie": bron_organisatie, "url": "", "xml_url": xml_url,
                "vangnet_treffer": "False", "vangnet_termen": "",
                "opgehaald_op": "", "regionaal": "True",
                "bron_organisatie": bron_organisatie, "regio_id": regio_id,
            })

    alle = bestaand + nieuwe_rijen
    with open(inventaris_pad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=kolommen)
        w.writeheader()
        for r in alle:
            w.writerow({k: r.get(k, "") for k in kolommen})

    return len(nieuwe_rijen)
