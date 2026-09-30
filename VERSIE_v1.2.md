# Corpus v1.2 — bevroren snapshot

**Datum bevriezing:** 2026-09-30
**Peildatum regelgeving:** 2026-10-01

## Wat is er veranderd t.o.v. v1.1

### A7 — checkpoint gehaald
Handmatige steekproefcontrole van 10 gemeenten afgerond: **0 gemiste geldende
Wmo-kerndocumenten** (`review/A7_steekproefcontrole_verslag.md`).

### Aanvullende, SRU-onafhankelijke controle (website-route)
Voor de 9 steekproefgemeenten (exclusief Hilvarenbeek) rechtstreeks via
lokaleregelgeving.overheid.nl gezocht (tekst=mantelzorg*, titel=maatschappelijke,
titel=wmo, titel="sociaal domein", geldend op de peildatum, verse sessie per
zoekvraag) en vergeleken met `selectie.csv`. 86 geldende regelingen gevonden die
niet in kern/waardering/twijfel zaten — allemaal terecht in ruis/aanbod/jeugd/
buiten_scope, op **één concrete fout na**:

- **"Subsidieregeling regionaal innovatiebudget Wmo"** (en 11 vergelijkbare
  Wmo-subsidieregelingen elders) vielen in `ruis` omdat de aanbod-verfijningsregel
  "wmo" niet als sociaal-domeinsignaal herkende, ondanks dat het woord letterlijk
  in de titel staat. **Gefixt**: `\bwmo\b` toegevoegd aan `AANBOD_SOCIAAL_SIGNAAL`
  in `src/selectie.py`. 12 documenten ruis→aanbod, opnieuw opgehaald en geparst.

Volledige lijst: `review/A7_aanvullende_websitecontrole.csv`.

### Leiden CVDR637925/4 — toelichting-check
Bevestigd: **geen `<nota-toelichting>` in de CVDR-XML**, geen toelichtingtekst in
de aanhef, en geen los CVDR-record voor een toelichting gevonden (SRU: 0
resultaten). Leidens toelichting staat kennelijk alleen op de eigen
gemeentewebsite — dat valt buiten deze module (module 2). Geen bug, bevestigde,
gedocumenteerde beperking.

## Cijfers
- 452.090 passages (parsen) + 1.760 pdf-bijlage-passages = **453.850 passages**
- 5.892 documenten opgehaald (0,00% fouten)
- aanbod: 757 → **769** (+12 via de A7-fix)
- 16/16 tests groen

## Checksums
Zie `VERSIE_v1.2_checksums.txt`.

Zie `README.md` ("Bekende beperkingen") en `logs/werklog.md` voor de volledige
beslissingsgeschiedenis.
