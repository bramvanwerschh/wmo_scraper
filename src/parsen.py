"""Stap 5: parsen naar passages.

Werkt op de CVDR-XML (klassieke <cvdr>-schema, zie logs/bronverkenning.md). Twee
documentstijlen komen voor (beide geverifieerd op de testdocumenten uit de opdracht):

- nieuwere documenten: leden zijn expliciet getagd: <lid><lidnr>1.</lidnr>...</lid>
- oudere documenten: leden zijn NIET apart getagd. <lijst><li nr="1."> markeert een
  lid-grens, <li nr="a."> of losse <al>1°...</al> zijn onderdelen daarbinnen.
  Herkenning gebeurt dus op het patroon van het nr-attribuut, niet op nesting
  (§0 bronverkenning: de structuur is hier plat, niet betrouwbaar genest).

De toelichting (<nota-toelichting>) is een platte reeks <al>'s. Koppen zijn NIET
consequent opgemaakt: <vet>, <cursief> en <onderstreept> komen alle drie voor voor
dezelfde functie (2026-09-25, gevonden op CVDR753666: "Artikel 3.3 Mantelzorg" staat
in <cursief>, niet <vet>). Koppen worden daarom herkend op TEKSTPATROON, ongeacht
opmaak: kort (<120 tekens), geen afsluitende punt, en matchend op een artikel- of
subkop-patroon (of anders: generieke kop). Toelichtingnummers wijken soms af van de
echte artikelnummering (bijv. toelichting noemt "Artikel 3.3", de regeling heeft
"Artikel 2.4") -- koppeling valt dan terug op titelmatch.

Documenten in het nieuwere STOP/LVBB-schema (<lvbbu:Consolidaties>, ~0,4% van het
corpus) worden hier niet geparst -- ze leveren 0 passages en komen op de foutenlijst
van stap 5 (< 2%-marge uit de opdracht).
"""

import csv
import re

from lxml import etree

from src.config import ROOT

NS_STRIP = re.compile(r"^\{[^}]+\}")
LID_NR_PATROON = re.compile(r"^\d+[a-z]?\.$", re.IGNORECASE)

KORTE_KOP_MAX_LENGTE = 120
ARTIKEL_KOP_TEKST_PATROON = re.compile(r"^Artikel\s+([\d][\d.:]*)\.?\s*(.*)$", re.IGNORECASE)
SUBKOP_PATROON = re.compile(
    r"^(Lid\s+\d+|Eerste\s+lid|Tweede\s+lid|Derde\s+lid|Vierde\s+lid|Vijfde\s+lid|"
    r"Zesde\s+lid|Zevende\s+lid|Achtste\s+lid|Negende\s+lid|Tiende\s+lid|"
    r"Ad\s+[a-z]\b|Onderdeel\s+[a-z]\b)",
    re.IGNORECASE,
)
HOOFDSTUK_KOP_PATROON = re.compile(r"^Hoofd?stuk\b", re.IGNORECASE)
NUMMER_KOP_PATROON = re.compile(r"^\d+(\.\d+)*\.?\s+\S")

_WET_TOKEN = r"(PW|Jeugdwet|Wmo(\s*2015)?|IOAW|IOAZ|Awb)"
WET_LABEL_PATROON = re.compile(
    rf"^\[?\s*{_WET_TOKEN}(\s*,\s*{_WET_TOKEN})*\s*\]?$",
    re.IGNORECASE,
)

PASSAGE_KOLOMMEN = [
    "passage_id", "parent_passage_id", "cvdr_id", "versie", "gemeente_code", "categorie",
    "pad", "hoofdstuk_titel", "artikel_nr", "artikel_titel", "lid_nr",
    "toelichting_kop", "toelichting_sub", "toelichting_artikel_ref", "koppeling_status",
    "wet_label", "sectietype", "domein_hint", "tekst", "n_tekens", "volgorde",
]


def _tag(el):
    t = el.tag
    if not isinstance(t, str):
        return None
    return NS_STRIP.sub("", t)


def _strip_voorloop(tekst: str) -> str:
    return re.sub(r"^[.\s]+", "", tekst)


def _tekst_van_table(table):
    """Punt 1 (verbeterronde 2): elke <row> als één tekstregel, cellen gescheiden
    door ' | ' (incl. koprij). Meerdere <al>'s binnen één <entry> worden met '; '
    samengevoegd zodat de rij één regel blijft."""
    regels = []
    for row in table.iter("{*}row"):
        cellen = []
        for entry in row.findall("{*}entry"):
            deeltjes = [d for d in (_tekst_van(al) for al in entry) if d] if len(entry) else []
            cel_tekst = "; ".join(deeltjes) if deeltjes else _tekst_van(entry)
            cel_tekst = re.sub(r"\s*\n\s*", " ", cel_tekst).strip()
            cellen.append(cel_tekst)
        if any(c for c in cellen):
            regels.append(" | ".join(cellen))
    return "\n".join(regels)


def _tekst_van(el, negeer_tabellen=False):
    """Platte tekst van el en nakomelingen, met behoud van opsommingstekens (li[@nr]).
    negeer_tabellen=True: sla <table>-inhoud over (die wordt dan apart als eigen
    bijlage-passage vastgelegd, bijv. bij een tabel die per ongeluk genest zit in
    <regeling-sluiting>, gevonden bij CVDR708764 -- anders staat de tabel dubbel/
    verkeerd gelabeld in de Ondertekening-tekst)."""
    if _tag(el) == "table":
        return "" if negeer_tabellen else _tekst_van_table(el)
    delen = []
    if el.text and el.text.strip():
        delen.append(el.text.strip())
    for kind in el:
        tag = _tag(kind)
        if tag is None:
            if kind.tail and kind.tail.strip():
                delen.append(kind.tail.strip())
            continue
        if tag == "li":
            nr = kind.attrib.get("nr", "")
            inhoud = _tekst_van(kind, negeer_tabellen)
            delen.append(f"{nr} {inhoud}".strip())
        elif tag == "table":
            if not negeer_tabellen:
                sub = _tekst_van_table(kind)
                if sub:
                    delen.append(sub)
        else:
            sub = _tekst_van(kind, negeer_tabellen)
            if sub:
                delen.append(sub)
        if kind.tail and kind.tail.strip():
            delen.append(kind.tail.strip())
    return "\n".join(d for d in delen if d)


def _tekst_van_lid(lid):
    delen = []
    for kind in lid:
        tag = _tag(kind)
        if tag in (None, "lidnr"):
            continue
        sub = _tekst_van(kind)
        if sub:
            delen.append(sub)
    return "\n".join(d for d in delen if d)


def domein_hint_van_titel(titel: str) -> str:
    t = (titel or "").lower()
    is_jeugd = bool(re.search(r"jeugd", t))
    is_wmo = bool(re.search(r"\bwmo\b|maatschappelijke ondersteuning", t))
    if is_jeugd and is_wmo:
        return "beide"
    if is_jeugd:
        return "jeugd"
    if is_wmo:
        return "wmo"
    return "onbekend"


def domein_hint_van_wet_label(label: str) -> str:
    if not label:
        return "onbekend"
    t = label.lower()
    is_jeugd = "jeugdwet" in t
    is_wmo = bool(re.search(r"wmo|\bpw\b|ioaw|ioaz|awb", t))
    if is_jeugd and is_wmo:
        return "beide"
    if is_jeugd:
        return "jeugd"
    if is_wmo:
        return "wmo"
    return "onbekend"


# --------------------------------------------------------------------------------
# Interne koppen binnen een blok platte tekst (artikel zonder nr, of toelichting):
# gedeelde herkenning ongeacht opmaak-tag (<vet>/<cursief>/<onderstreept>) of geheel
# zonder opmaak (alleen kort + geen afsluitende punt + evt. cijferpatroon).
# --------------------------------------------------------------------------------

def _emfasis_tekst(el):
    """Als <al> één of meer <vet>/<cursief>/<onderstreept>-kinderen heeft die samen de
    kop vormen (met evt. tekst erna in dezelfde <al>), geeft (koptekst, resttekst)
    terug. Meerdere sibling-emfasis-elementen komen voor (bijv. een figuurbijschrift
    opgeknipt in <cursief>Figuur 3: ...</cursief><cursief>Wmo</cursief><cursief> 2015
    ...</cursief>, gevonden bij CVDR706109) -- die worden allemaal samengevoegd,
    anders gaat het deel na de eerste run verloren."""
    if _tag(el) != "al":
        return None
    emfasis_kinderen = [k for k in el if _tag(k) in ("vet", "cursief", "onderstreept")]
    if not emfasis_kinderen:
        return None
    delen = []
    for i, k in enumerate(emfasis_kinderen):
        stuk = _tekst_van(k)
        if stuk:
            delen.append(stuk)
        if i < len(emfasis_kinderen) - 1 and k.tail and k.tail.strip():
            delen.append(k.tail.strip())
    koptekst = "".join(delen).strip()
    if not koptekst:
        return None
    rest = _strip_voorloop((emfasis_kinderen[-1].tail or "").strip())
    return koptekst, rest


def _is_kop_kandidaat(tekst: str) -> bool:
    """Een kop is nooit een complete zin. Een zin die eindigt op ':' loopt door in wat
    volgt (bijv. "Artikel 4.1.1 van de Jeugdwet luidt als volgt:") en is dus, ook al
    matcht hij toevallig het artikelkop-patroon, GEEN kop maar content -- anders gaat
    die tekst verloren (gevonden bij CVDR706109, conservatiecheck-onderzoek)."""
    t = tekst.strip()
    return bool(t) and len(t) < KORTE_KOP_MAX_LENGTE and not t.endswith((".", ":"))


def _classificeer_kop(koptekst: str) -> str:
    """'artikel' | 'subkop' | 'hoofdstuk' | 'generiek'."""
    if ARTIKEL_KOP_TEKST_PATROON.match(koptekst):
        return "artikel"
    if SUBKOP_PATROON.match(koptekst):
        return "subkop"
    if HOOFDSTUK_KOP_PATROON.match(koptekst):
        return "hoofdstuk"
    return "generiek"


def _detecteer_kop(el):
    """Onderzoekt een <al>-element (of vergelijkbaar) op een ingebedde kop, ongeacht
    opmaak. Geeft (koptype, koptekst, resttekst) terug, of None als het geen kop is."""
    if _tag(el) != "al":
        return None
    emf = _emfasis_tekst(el)
    if emf is not None:
        koptekst, rest = emf
        kop_kandidaat = (_is_kop_kandidaat(koptekst) or ARTIKEL_KOP_TEKST_PATROON.match(koptekst))
        if kop_kandidaat and not koptekst.rstrip().endswith(":"):
            return _classificeer_kop(koptekst), koptekst, rest
        return None
    # geen opmaak: alleen als de hele <al> kort is en een cijfer- of subkop-patroon heeft
    tekst = _tekst_van(el)
    if _is_kop_kandidaat(tekst) and (NUMMER_KOP_PATROON.match(tekst) or SUBKOP_PATROON.match(tekst)
                                      or ARTIKEL_KOP_TEKST_PATROON.match(tekst)):
        return _classificeer_kop(tekst), tekst, ""
    return None


def _segmenteer_op_koppen(elementen):
    """Segmenteert een reeks elementen (kinderen van <artikel> of <al>'s van de
    toelichting) op ingebedde koppen. Geeft een lijst van dicts terug met
    kop/koptype/tekst -- gebruikt door zowel de vrijetekst-artikel-fallback als de
    toelichtingparser."""
    segmenten = []
    huidig = {"koptype": None, "kop": "", "delen": []}

    def flush():
        tekst = "\n".join(d for d in huidig["delen"] if d)
        if tekst.strip() or huidig["kop"]:
            segmenten.append({"koptype": huidig["koptype"], "kop": huidig["kop"], "tekst": tekst})

    for el in elementen:
        tag = _tag(el)
        if tag is None or tag == "kop":
            continue
        kop_info = _detecteer_kop(el)
        if kop_info is not None:
            koptype, koptekst, rest = kop_info
            flush()
            huidig = {"koptype": koptype, "kop": koptekst, "delen": [rest] if rest else []}
            continue
        tekst = _tekst_van(el)
        if tekst.strip():
            huidig["delen"].append(tekst)
    flush()
    return segmenten


def _segmenteer_artikel_inhoud(artikel):
    """Verenigde segmentatie van artikel-inhoud: verwerkt <lid> (expliciete tag),
    platte <lijst>/<li nr="1."> (lid-grens) vs. <li nr="a."|"1°"> (onderdeel, blijft
    bij het huidige lid), en losse <al>'s, allemaal in documentvolgorde. Sommige
    artikelen mengen <lid>-tags met losse <al>-siblings (bijv. CVDR633457/2) -- eerdere
    code die alleen naar <lid> keek zodra die er was, gooide dan de rest weg (§3.3
    schending). Geeft een lijst van (lid_nr_of_None, tekst) terug."""
    kinderen = [k for k in artikel if _tag(k) not in (None, "kop")]
    segmenten = []
    huidige_lidnr = None
    huidige_delen = []
    begonnen = False

    def flush():
        if begonnen:
            segmenten.append((huidige_lidnr, "\n".join(huidige_delen)))

    for kind in kinderen:
        tag = _tag(kind)
        if tag == "lid":
            flush()
            lidnr = (kind.findtext("{*}lidnr", "") or "").strip().rstrip(".")
            segmenten.append((lidnr, _tekst_van_lid(kind)))
            huidige_lidnr = None
            huidige_delen = []
            begonnen = False
            continue
        if tag == "lijst":
            for li in kind.findall("{*}li"):
                nr = li.attrib.get("nr", "")
                li_tekst = f"{nr} {_tekst_van(li)}".strip()
                if LID_NR_PATROON.match(nr):
                    flush()
                    huidige_lidnr = nr.rstrip(".")
                    huidige_delen = [li_tekst]
                    begonnen = True
                else:
                    huidige_delen.append(li_tekst)
                    begonnen = True
            continue
        tekst = _tekst_van(kind)
        if tekst.strip():
            huidige_delen.append(tekst)
            begonnen = True
    flush()
    return segmenten


class _Context:
    def __init__(self, cvdr_id, versie, gemeente_code, categorie):
        self.cvdr_id = cvdr_id
        self.versie = versie
        self.gemeente_code = gemeente_code
        self.categorie = categorie
        self.volgorde = 0
        self.pending_wet_label = ""
        # gevuld tijdens het wandelen door regeling-tekst, gebruikt door de toelichting:
        self.artikel_info: dict[str, dict] = {}   # nr -> {"titel", "domein_hint"}
        self.titel_naar_nr: dict[str, str] = {}   # genormaliseerde titel -> nr
        self.doc_domein_hint = "onbekend"

    def volgende(self):
        self.volgorde += 1
        return self.volgorde


def _normaliseer_titel_voor_match(titel: str) -> str:
    return re.sub(r"\s+", " ", (titel or "").strip().lower())


def _registreer_artikel(ctx, artikel_nr, artikel_titel, domein_hint):
    if not artikel_nr:
        return
    ctx.artikel_info[artikel_nr] = {"titel": artikel_titel, "domein_hint": domein_hint}
    genorm = _normaliseer_titel_voor_match(artikel_titel)
    if genorm:
        ctx.titel_naar_nr.setdefault(genorm, artikel_nr)


def _extraheer_wet_labels(tekst: str) -> tuple[str, list[str]]:
    """Punt 3: haalt regels die PUUR een wetlabel zijn (bijv. '[Jeugdwet]') eruit,
    ook als ze slechts één regel zijn binnen een groter, samengevoegd tekstblok."""
    labels = []
    overige_regels = []
    for regel in tekst.split("\n"):
        kandidaat = regel.strip()
        if kandidaat and WET_LABEL_PATROON.match(kandidaat):
            labels.append(kandidaat)
        else:
            overige_regels.append(regel)
    return "\n".join(overige_regels), labels


def _maak_passage(ctx, passage_id, pad, hoofdstuk_titel, artikel_nr, artikel_titel,
                   lid_nr, sectietype, domein_hint, tekst, *, parent_passage_id="",
                   toelichting_kop="", toelichting_sub="", toelichting_artikel_ref="",
                   koppeling_status=""):
    tekst = _strip_voorloop(tekst.strip()).strip()
    tekst, gevonden_labels = _extraheer_wet_labels(tekst)
    tekst = tekst.strip()
    for label in gevonden_labels:
        ctx.pending_wet_label = (ctx.pending_wet_label + "; " + label) if ctx.pending_wet_label else label

    if not tekst:
        return None

    wet_label = ctx.pending_wet_label
    ctx.pending_wet_label = ""

    if wet_label:
        wet_hint = domein_hint_van_wet_label(wet_label)
        if wet_hint != "onbekend":
            domein_hint = wet_hint

    return {
        "passage_id": passage_id,
        "parent_passage_id": parent_passage_id,
        "cvdr_id": ctx.cvdr_id,
        "versie": ctx.versie,
        "gemeente_code": ctx.gemeente_code,
        "categorie": ctx.categorie,
        "pad": pad,
        "hoofdstuk_titel": hoofdstuk_titel,
        "artikel_nr": artikel_nr,
        "artikel_titel": artikel_titel,
        "lid_nr": lid_nr,
        "toelichting_kop": toelichting_kop,
        "toelichting_sub": toelichting_sub,
        "toelichting_artikel_ref": toelichting_artikel_ref,
        "koppeling_status": koppeling_status,
        "wet_label": wet_label,
        "sectietype": sectietype,
        "domein_hint": domein_hint,
        "tekst": tekst,
        "n_tekens": len(tekst),
        "volgorde": ctx.volgende(),
    }


def _voeg_toe(passages, p):
    if p is not None:
        passages.append(p)


# --------------------------------------------------------------------------------
# Generieke opsplitsing van te grote passages (> 3.000 tekens) in stukken van
# ~800-1.500 tekens, op alinea-grenzen, met behoud van eventuele kopjes in het pad.
# --------------------------------------------------------------------------------

MAX_PASSAGE_LENGTE = 3000
DOEL_CHUNK_LENGTE = 1200


def _splits_grote_passage(p: dict) -> list[dict]:
    if len(p["tekst"]) <= MAX_PASSAGE_LENGTE:
        return [p]

    regels = p["tekst"].split("\n")
    chunks = []
    huidige_kop = ""
    huidige_regels = []
    huidige_lengte = 0

    def flush():
        if huidige_regels:
            chunks.append((huidige_kop, "\n".join(huidige_regels)))

    for regel in regels:
        regel_kandidaat = regel.strip()
        is_kop = (
            _is_kop_kandidaat(regel_kandidaat)
            and (NUMMER_KOP_PATROON.match(regel_kandidaat) or SUBKOP_PATROON.match(regel_kandidaat)
                 or ARTIKEL_KOP_TEKST_PATROON.match(regel_kandidaat))
        )
        if is_kop and huidige_lengte > 0:
            flush()
            huidige_kop = regel_kandidaat
            huidige_regels = []
            huidige_lengte = 0
            continue
        huidige_regels.append(regel)
        huidige_lengte += len(regel)
        if huidige_lengte >= DOEL_CHUNK_LENGTE:
            flush()
            huidige_regels = []
            huidige_lengte = 0
    flush()

    if len(chunks) <= 1:
        return [p]

    resultaat = []
    for i, (kop, tekst) in enumerate(chunks, 1):
        if not tekst.strip():
            continue
        pad = f"{p['pad']} > {kop}" if kop else f"{p['pad']} > deel {i}"
        nieuw = dict(p)
        nieuw["passage_id"] = f"{p['passage_id']}__deel{i}"
        nieuw["parent_passage_id"] = p["passage_id"]
        nieuw["pad"] = pad
        nieuw["tekst"] = tekst.strip()
        nieuw["n_tekens"] = len(nieuw["tekst"])
        resultaat.append(nieuw)
    return resultaat


def _splits_alle_grote_passages(passages: list[dict]) -> list[dict]:
    resultaat = []
    for p in passages:
        resultaat.extend(_splits_grote_passage(p))
    return resultaat


# --------------------------------------------------------------------------------

def _parse_artikel(artikel, ctx, pad_delen, hoofdstuk_titel, domein_hint, passages):
    kop = artikel.find("{*}kop")
    nr_ruw = (kop.findtext("{*}nr", "") if kop is not None else "").strip()
    titel = (kop.findtext("{*}titel", "") if kop is not None else "").strip()

    # Punt 5: soms bevat <nr> zelf "29. Intrekking van eerdere regelingen" (titel
    # lekt in het nr-veld) -- alleen het cijferdeel als artikel_nr, rest naar titel.
    nr_match = re.match(r"^([\d][\d.:]*)\.?\s*(.*)$", nr_ruw)
    if nr_match:
        artikel_nr = nr_match.group(1).rstrip(".")
        if not titel and nr_match.group(2):
            titel = nr_match.group(2)
    else:
        artikel_nr = nr_ruw.rstrip(".")

    sectietype = "begrippen" if re.search(r"begripsbepaling", titel, re.IGNORECASE) else "artikel"
    artikel_pad = f"Artikel {nr_ruw} {titel}".strip()

    _registreer_artikel(ctx, artikel_nr, titel, domein_hint)

    if not nr_ruw:
        kinderen = [k for k in artikel if _tag(k) not in (None, "kop")]
        gesegmenteerd = _segmenteer_op_koppen(kinderen)
        if len(gesegmenteerd) >= 2:
            for i, seg in enumerate(gesegmenteerd, 1):
                pad = " > ".join(pad_delen + [seg["kop"]]) if seg["kop"] else " > ".join(pad_delen)
                pid = f"{ctx.cvdr_id}_{ctx.versie}__vrijetekst__{ctx.volgorde + 1}"
                _voeg_toe(passages, _maak_passage(
                    ctx, pid, pad, hoofdstuk_titel, "", seg["kop"], "",
                    sectietype, domein_hint, seg["tekst"],
                ))
            return

    segmenten = _segmenteer_artikel_inhoud(artikel)
    meerdere_leden = len([s for s in segmenten if s[0]]) > 1
    for lidnr, tekst in segmenten:
        if lidnr and meerdere_leden:
            pad = " > ".join(pad_delen + [artikel_pad, f"lid {lidnr}"])
            passage_id = f"{ctx.cvdr_id}_{ctx.versie}__art{artikel_nr}__lid{lidnr}"
        else:
            pad = " > ".join(pad_delen + [artikel_pad])
            passage_id = f"{ctx.cvdr_id}_{ctx.versie}__art{artikel_nr}"
        _voeg_toe(passages, _maak_passage(
            ctx, passage_id, pad, hoofdstuk_titel, artikel_nr, titel,
            lidnr if meerdere_leden else "", sectietype, domein_hint, tekst,
        ))


# Nederlandse wetgevingshiërarchie boven artikel-niveau. Niet elke regeling gebruikt
# hoofdstuk/paragraaf; sommige (oudere) documenten wikkelen alles in boek/deel/titel/
# afdeling/subparagraaf. Generiek behandeld zodat we niets missen (§7 stap 5, punt 0).
STRUCTUUR_CONTAINERS = {"boek", "deel", "titel", "hoofdstuk", "afdeling", "paragraaf", "subparagraaf"}
HOOFDSTUK_NIVEAU = {"boek", "deel", "titel", "hoofdstuk", "afdeling"}


def _loop_secties(container, ctx, pad_delen, hoofdstuk_titel, ouder_domein_hint, passages):
    for kind in container:
        tag = _tag(kind)
        if tag in ("tekst", "structuurtekst"):
            inhoud = _tekst_van(kind)
            pid = f"{ctx.cvdr_id}_{ctx.versie}__tekst__{ctx.volgorde + 1}"
            pad = " > ".join(pad_delen) or "Tekst"
            _voeg_toe(passages, _maak_passage(
                ctx, pid, pad, hoofdstuk_titel, "", "", "",
                "artikel", ouder_domein_hint, inhoud,
            ))
        elif tag in STRUCTUUR_CONTAINERS:
            kop = kind.find("{*}kop")
            label = (kop.findtext("{*}label", "") if kop is not None else "").strip()
            nr = (kop.findtext("{*}nr", "") if kop is not None else "").strip()
            titel = (kop.findtext("{*}titel", "") if kop is not None else "").strip()
            volledige_titel = " ".join(x for x in [label, nr, titel] if x).strip()
            dh = domein_hint_van_titel(titel)
            if dh == "onbekend":
                dh = ouder_domein_hint
            nieuwe_hoofdstuk_titel = volledige_titel if (tag in HOOFDSTUK_NIVEAU and volledige_titel) else hoofdstuk_titel
            nieuw_pad = pad_delen + [volledige_titel] if volledige_titel else pad_delen
            _loop_secties(kind, ctx, nieuw_pad, nieuwe_hoofdstuk_titel, dh, passages)
        elif tag == "artikel":
            _parse_artikel(kind, ctx, pad_delen, hoofdstuk_titel, ouder_domein_hint, passages)


def _resolveer_toelichting_referentie(ctx, ref_nr, ref_titel):
    """Punt 1: koppeling via nummer, anders via titelmatch, anders geen."""
    if ref_nr and ref_nr in ctx.artikel_info:
        info = ctx.artikel_info[ref_nr]
        return ref_nr, info["titel"], info["domein_hint"], "nummer"
    genorm = _normaliseer_titel_voor_match(ref_titel)
    if genorm and genorm in ctx.titel_naar_nr:
        nr = ctx.titel_naar_nr[genorm]
        info = ctx.artikel_info[nr]
        return nr, info["titel"], info["domein_hint"], "titel"
    # losse substring-match als exacte titel niet lukt (bijv. kop heeft extra woorden)
    if genorm:
        for kandidaat_titel, nr in ctx.titel_naar_nr.items():
            if genorm == kandidaat_titel or (len(genorm) > 3 and genorm in kandidaat_titel):
                info = ctx.artikel_info[nr]
                return nr, info["titel"], info["domein_hint"], "titel"
    return "", "", "onbekend", "geen"


def _parse_toelichting(nt, ctx, passages):
    kinderen = [k for k in nt if _tag(k) not in (None, "kop")]
    segmenten = _segmenteer_op_koppen(kinderen)

    huidig_artikel_nr = ""
    huidig_artikel_domein = "onbekend"
    huidig_sub = ""
    huidig_kop = ""
    huidig_artikel_ref = ""
    huidig_koppeling = "geen"

    for seg in segmenten:
        koptype, kop, tekst = seg["koptype"], seg["kop"], seg["tekst"]

        if koptype == "artikel":
            m = ARTIKEL_KOP_TEKST_PATROON.match(kop)
            ref_nr = m.group(1).rstrip(".") if m else ""
            ref_titel = m.group(2).strip() if m else ""
            huidig_artikel_ref = ref_nr
            resolved_nr, resolved_titel, resolved_domein, status = _resolveer_toelichting_referentie(
                ctx, ref_nr, ref_titel
            )
            huidig_artikel_nr = resolved_nr
            huidig_artikel_domein = resolved_domein
            huidig_koppeling = status
            huidig_sub = ""
            huidig_kop = kop
        elif koptype == "hoofdstuk":
            huidig_artikel_nr = ""
            huidig_artikel_domein = "onbekend"
            huidig_artikel_ref = ""
            huidig_koppeling = "geen"
            huidig_sub = ""
            huidig_kop = kop
            huidig_kop = kop
        elif koptype == "subkop":
            huidig_sub = kop
            huidig_kop = kop
        else:
            if kop:
                huidig_kop = kop

        if not tekst.strip():
            continue

        sectietype = "toelichting_artikel" if huidig_artikel_nr else "toelichting_algemeen"
        pad = "Toelichting" + (f" > Artikel {huidig_artikel_nr}" if huidig_artikel_nr else " > Algemeen")
        if huidig_kop:
            pad += f" > {huidig_kop}"
        pid = f"{ctx.cvdr_id}_{ctx.versie}__{sectietype}__{ctx.volgorde + 1}"
        _voeg_toe(passages, _maak_passage(
            ctx, pid, pad, "", huidig_artikel_nr, "", "",
            sectietype, huidig_artikel_domein, tekst,
            toelichting_kop=huidig_kop, toelichting_sub=huidig_sub,
            toelichting_artikel_ref=huidig_artikel_ref, koppeling_status=huidig_koppeling,
        ))


def _bepaal_doc_domein_hint(root) -> str:
    """Punt 4, fallback op documenttitel: geen jeugd-term => 'wmo'."""
    titel_el = root.find(".//{*}intitule")
    titel = titel_el.text if titel_el is not None and titel_el.text else ""
    t = titel.lower()
    is_jeugd = bool(re.search(r"jeugd", t))
    is_wmo = bool(re.search(r"\bwmo\b|maatschappelijke ondersteuning|mantelzorg|huishoudelijke ondersteuning", t))
    if is_jeugd and is_wmo:
        return "beide"
    if is_jeugd:
        return "jeugd"
    return "wmo"


def parse_document(xml_pad, cvdr_id, versie, gemeente_code, categorie) -> list[dict]:
    tree = etree.parse(str(xml_pad))
    root = tree.getroot()
    ctx = _Context(cvdr_id, versie, gemeente_code, categorie)
    ctx.doc_domein_hint = _bepaal_doc_domein_hint(root)
    passages: list[dict] = []

    aanhef = root.find(".//{*}aanhef")
    if aanhef is not None:
        tekst = _tekst_van(aanhef)
        pid = f"{cvdr_id}_{versie}__aanhef__{ctx.volgorde + 1}"
        _voeg_toe(passages, _maak_passage(
            ctx, pid, "Aanhef", "", "", "", "", "aanhef", ctx.doc_domein_hint, tekst,
        ))

    regeling_tekst = root.find(".//{*}regeling-tekst")
    if regeling_tekst is not None:
        _loop_secties(regeling_tekst, ctx, [], "", ctx.doc_domein_hint, passages)

    regeling = root.find(".//{*}regeling")
    if regeling is not None:
        for bijlage in regeling.findall("{*}bijlage"):
            tekst = _tekst_van(bijlage)
            pid = f"{cvdr_id}_{versie}__bijlage__{ctx.volgorde + 1}"
            _voeg_toe(passages, _maak_passage(
                ctx, pid, "Bijlage", "", "", "", "", "bijlage", ctx.doc_domein_hint, tekst,
            ))

    sluiting = root.find(".//{*}regeling-sluiting")
    if sluiting is not None:
        # Punt 4 (verbeterronde 3): een <table> die (per ongeluk) genest zit binnen
        # <regeling-sluiting>/<slotformulering> hoort niet in de Ondertekening-tekst
        # maar is eigenlijk bijlage-achtige inhoud -- apart gelabeld als sectietype='bijlage'.
        for i, tabel in enumerate(sluiting.findall(".//{*}table"), 1):
            tabel_tekst = _tekst_van_table(tabel)
            pid = f"{cvdr_id}_{versie}__bijlage_in_sluiting__{i}"
            _voeg_toe(passages, _maak_passage(
                ctx, pid, "Bijlage (genest in ondertekening)", "", "", "", "",
                "bijlage", ctx.doc_domein_hint, tabel_tekst,
            ))

        tekst = _tekst_van(sluiting, negeer_tabellen=True)
        pid = f"{cvdr_id}_{versie}__ondertekening__{ctx.volgorde + 1}"
        _voeg_toe(passages, _maak_passage(
            ctx, pid, "Ondertekening", "", "", "", "", "ondertekening", ctx.doc_domein_hint, tekst,
        ))

    # Sommige documenten (40 van 5.835, steekproefsgewijs vastgesteld) hebben MEERDERE
    # <nota-toelichting>-elementen als sibling van <regeling-tekst> -- vaak een lege
    # placeholder plus de echte, substantiële toelichting. .find() pakte voorheen
    # alleen de eerste (soms de lege), waardoor tot ~44.000 tekens verloren gingen
    # bij één enkel document (CVDR635708). Nu worden ze allemaal verwerkt.
    for nt in root.findall(".//{*}nota-toelichting"):
        _parse_toelichting(nt, ctx, passages)

    # Punt 4: fallback domein_hint (wet_label > hoofdstuk/paragraaf > documenttitel)
    # is al toegepast tijdens het bouwen; hier alleen nog: passages die nog steeds
    # 'onbekend' zijn krijgen de documenttitel-hint (documenttitel heeft de laagste
    # prioriteit van de vier genoemde niveaus).
    for p in passages:
        if p["domein_hint"] == "onbekend":
            p["domein_hint"] = ctx.doc_domein_hint

    passages = _splits_alle_grote_passages(passages)
    return passages


def parse_alle_documenten(config: dict) -> tuple[list[dict], list[dict]]:
    """Parst alle documenten uit documenten.csv (status ok). Geeft (passages, fouten) terug."""
    with open(ROOT / config["paden"]["documenten_csv"], encoding="utf-8") as f:
        documenten = list(csv.DictReader(f))

    raw_docs = ROOT / config["paden"]["raw_docs"]
    alle_passages: list[dict] = []
    fouten: list[dict] = []

    for doc in documenten:
        if not doc["status"].startswith("ok"):
            continue
        xml_pad = raw_docs / doc["bestand"]
        try:
            passages = parse_document(xml_pad, doc["cvdr_id"], doc["versie"], doc["gemeente_code"], doc["categorie"])
        except etree.XMLSyntaxError as e:
            fouten.append({**doc, "parse_fout": f"XMLSyntaxError: {e}"})
            continue
        if not any(p["sectietype"] in ("artikel", "begrippen") for p in passages):
            fouten.append({**doc, "parse_fout": "0 artikelpassages"})
        alle_passages.extend(passages)

    return alle_passages, fouten


def schrijf_passages_csv(config: dict, passages: list[dict]):
    pad = ROOT / config["paden"]["passages_csv"]
    pad.parent.mkdir(parents=True, exist_ok=True)
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PASSAGE_KOLOMMEN)
        w.writeheader()
        for p in passages:
            w.writerow(p)


def schrijf_parse_fouten_csv(config: dict, fouten: list[dict]):
    pad = ROOT / config["paden"]["rapportage"] / "parse_fouten.csv"
    pad.parent.mkdir(parents=True, exist_ok=True)
    kolommen = ["cvdr_id", "versie", "gemeente_code", "categorie", "bestand", "parse_fout"]
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=kolommen)
        w.writeheader()
        for r in fouten:
            w.writerow({k: r.get(k, "") for k in kolommen})
