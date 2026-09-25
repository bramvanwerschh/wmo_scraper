# Corpus v1.1 — bevroren snapshot

**Datum bevriezing:** 2026-09-25 (na v1.0, zelfde dag)
**Peildatum regelgeving:** 2026-10-01

## Wat is er veranderd t.o.v. v1.0

### Punt 1 — Conservatiecheck-onderzoek op 6 grote kern-documenten
Onderzocht: CVDR706109, 745744, 756693, 635708, 752802, 460221 (ratio <0,65, >40k
brontekens). Twee echte parserbugs gevonden en gefixt (geen meetfout):
1. **Meerdere `<nota-toelichting>`-elementen per document** (40 van 5.880 documenten)
   — `.find()` pakte alleen de eerste (soms een lege placeholder), waardoor bij één
   document (CVDR635708) ~44.000 tekens volledig verloren gingen. Nu worden alle
   `<nota-toelichting>`-elementen verwerkt.
2. **Kop-misclassificatie**: een zin als "Artikel 4.1.1 van de Jeugdwet luidt als
   volgt:" werd door het artikelkop-patroon foutief als koptekst gelezen (en dus
   weggegooid) omdat er geen check was op een dubbele punt aan het eind. Gefixt:
   koppen die eindigen op ':' tellen niet meer als kop.
3. **Meerdere `<vet>`/`<cursief>`-elementen als siblings binnen één `<al>`** (bijv.
   een figuurbijschrift opgeknipt in 3 stukjes) — alleen de eerste werd gelezen. Nu
   worden ze samengevoegd.

Resultaat: conservatie kern+waardering van **7,8% → 6,6%** onder 95%. Van de 6
onderzochte documenten: 5 nu op 0 gemiste tekstfragmenten (>=30 tekens), 1 nog met
11 korte "Hoofdstuk N ..."-navigatiekopjes zonder eigen inhoud (verwaarloosbaar).

### Punt 2 — Termenverkenning met FILTER-kolommen
`src/termen.py` uitgebreid: elke term krijgt nu zowel (a) heel-corpus-aantallen als
(b) FILTER-aantallen (categorie in kern/waardering, domein_hint in wmo/beide,
sectietype niet begrippen/bijlage/ondertekening/aanhef), plus een categorie-
verdeling en 5 voorbeelden uit de FILTER-set met **gemeentenaam** (niet code).
Specifiek gecontroleerd:
- `belastbaarheid`: 283 gem./918 pass. (corpus) → 161 gem./297 pass. (filter)
- `EDIZ`: 14/14 → 5/5 (smal, en het gros valt buiten de strikte filter)
- `jonge mantelzorger*`: 99/281 → 70/186
- `gelijkgericht*`: 2/2 → **0/0** (beide treffers vallen buiten de FILTER-criteria)

### Punt 3 — Waarom 19 → 16 testasserts?
Geen verlies: de 16 permanente testfuncties in `tests/test_parsen.py` bevatten
**21 losse `assert`-statements** (meer dan de oorspronkelijke 19-20 losse checks) —
een aantal checks over hetzelfde document/concept zijn samengevoegd tot één
testfunctie met meerdere asserts (bijv. Lid 1/Ad a/Lid 2 van art. 9 zijn nu 3
asserts binnen `test_aaenhunze_verordening_toelichting_artikel_9_subkoppen`).

### Punt 4 — Genest bijlage-materiaal in `<regeling-sluiting>`
Gevonden bij CVDR708764: een `<table>` met 67.213 tekens artikel-achtige inhoud
zat genest in `<slotformulering>` (onderdeel van `<regeling-sluiting>`) en werd
meegevouwen in de platte Ondertekening-tekst. Nu wordt zo'n geneste tabel apart
als `sectietype='bijlage'` vastgelegd, en uit de Ondertekening-tekst gehouden.

## Cijfers
- 451.674 passages uit `parsen` + 1.760 pdf-bijlage-passages = **453.434 passages**
- 5.880 documenten opgehaald (0,00% fouten)
- Foutpercentage 0-artikeldocumenten: 2,18% (ongewijzigd — deze ronde ging over
  kwaliteit van bestaande passages, niet over de resterende 128 lege documenten)
- Conservatie kern+waardering: **6,6%** onder 95% (was 7,8% in v1.0)
- 16 testfuncties / 21 asserts, allemaal groen

## Checksums
Zie `VERSIE_v1.1_checksums.txt`.

## Reproduceren
```bash
git checkout v1.1
./.venv/bin/python3 run.py --stap selectie
./.venv/bin/python3 run.py --stap ophalen
./.venv/bin/python3 run.py --stap parsen
./.venv/bin/python3 run.py --stap bijlagen
./.venv/bin/python3 run.py --stap kwaliteit
./.venv/bin/python3 run.py --stap termen
./.venv/bin/python3 -m pytest tests/ -v
```

Zie `README.md` ("Bekende beperkingen") en `logs/werklog.md` voor de volledige
beslissingsgeschiedenis.
