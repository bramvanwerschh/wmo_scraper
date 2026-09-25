"""Harde, geautomatiseerde verwachtingen per testdocument (op verzoek van Bram,
2026-09-25, nadat "alles klopt" voor CVDR753666 achteraf niet klopte). Draai met:
    ./.venv/bin/python3 -m pytest tests/test_parsen.py -v
Vereist dat data/raw/docs/ de betreffende CVDR-documenten al bevat (stap 4).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.parsen import parse_document

DOCS = Path(__file__).resolve().parent.parent / "data" / "raw" / "docs"


def _parse(cvdr_id, versie, gemeente_code="GM0000", categorie="kern"):
    return parse_document(DOCS / f"{cvdr_id}_{versie}.xml", cvdr_id, versie, gemeente_code, categorie)


def test_denhaag_artikel_1_2_3_heeft_4_leden():
    p = _parse("CVDR619608", "8", "GM0518")
    assert len([x for x in p if x["artikel_nr"] == "1.2.3"]) == 4


def test_denhaag_mantelzorgwaardering_aanwezig():
    p = _parse("CVDR619608", "8", "GM0518")
    assert any("waardering van mantelzorgers" in x["pad"] for x in p)


def test_denhaag_geen_passage_boven_3000():
    p = _parse("CVDR619608", "8", "GM0518")
    assert all(x["n_tekens"] <= 3000 for x in p)


def test_aaenhunze_verordening_43_artikelen():
    p = _parse("CVDR753669", "1", "GM1680")
    nrs = {x["artikel_nr"] for x in p if x["sectietype"] in ("artikel", "begrippen") and x["artikel_nr"]}
    assert len(nrs) == 43


def test_aaenhunze_verordening_10_hoofdstukken():
    p = _parse("CVDR753669", "1", "GM1680")
    hs = {x["hoofdstuk_titel"] for x in p if x["hoofdstuk_titel"]}
    assert len(hs) == 10


def test_aaenhunze_verordening_artikel_15_aanwezig():
    p = _parse("CVDR753669", "1", "GM1680")
    assert any(x["artikel_nr"] == "15" for x in p)


def test_aaenhunze_verordening_toelichting_artikel_9_subkoppen():
    p = _parse("CVDR753669", "1", "GM1680")
    subs = [x["toelichting_sub"] for x in p if x["sectietype"] == "toelichting_artikel" and x["artikel_nr"] == "9"]
    assert "Lid 1" in subs
    assert "Ad a" in subs
    assert "Lid 2" in subs


def test_naderregels_geen_kop_only_passages():
    p = _parse("CVDR753666", "1", "GM1680")
    assert not [x for x in p if x["toelichting_kop"] and not x["tekst"].strip()]


def test_naderregels_mantelzorg_gekoppeld_via_titel():
    p = _parse("CVDR753666", "1", "GM1680")
    treffers = [x for x in p if "Mantelzorg" in (x["toelichting_kop"] or "")]
    assert treffers
    assert treffers[0]["artikel_nr"] == "2.4"
    assert treffers[0]["koppeling_status"] == "titel"


def test_naderregels_overbelasting_onder_artikel_3():
    p = _parse("CVDR753666", "1", "GM1680")
    treffers = [x for x in p if "overbelasting en gebruikelijke zorg" in (x["toelichting_kop"] or "").lower()]
    assert treffers
    assert treffers[0]["toelichting_artikel_ref"] == "3" or treffers[0]["artikel_nr"] == "3"


def test_hilversum_geen_passage_boven_3000():
    p = _parse("CVDR764261", "1", "GM0402")
    assert all(x["n_tekens"] <= 3000 for x in p)


def test_hilversum_kopjes_zichtbaar_in_pad():
    p = _parse("CVDR764261", "1", "GM0402")
    assert any("Inleiding" in x["pad"] for x in p)


def test_wetlabel_geen_losse_labelpassage():
    p = _parse("CVDR690468", "1")
    labels = {"[Jeugdwet]", "[Jeugdwet, Wmo]", "[Jeugdwet, Wmo, Awb]"}
    assert not [x for x in p if x["tekst"].strip() in labels]


def test_wetlabel_gevuld_op_vervolgpassage():
    p = _parse("CVDR690468", "1")
    assert any(x["wet_label"] for x in p)


def test_wetlabel_domein_hint_beide():
    p = _parse("CVDR690468", "1")
    assert any(x["wet_label"] and x["domein_hint"] == "beide" for x in p)


def test_tabel_gerenderd_als_regels_met_separator():
    p = _parse("CVDR706109", "1")
    assert any("Wetgeving" in x["tekst"] and " | " in x["tekst"] for x in p)
