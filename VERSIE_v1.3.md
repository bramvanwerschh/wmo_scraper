# Corpus v1.3 — bevroren snapshot

**Datum bevriezing:** 2026-09-30
**Peildatum regelgeving:** 2026-10-01

## Wat is er veranderd t.o.v. v1.2

### Alignment-check tegen de officiële opdrachtdocumenten
Op verzoek van Bram gecontroleerd tegen de Offerteaanvraag (RFP, kenmerk
201865006.025.667), de Gunningsbrief en de gegunde Ecorys-offerte (1008762voo).
Sterke aansluiting bevestigd: dit corpus is Activiteit 1 "Beleidsanalyse" uit de
offerte, en de offerte prijst expliciet dezelfde iteratieve, handmatig-geverifieerde
werkwijze die in dit project is gevolgd.

Eén concreet gat gevonden en gedicht: de offerte zegt aan VWS een zoektermenlijst toe
("mantelzorg, keukentafelgesprek, draagkracht, draaglast, overbelasting,
ondersteuningsbehoefte, respijtzorg, sociaal netwerk en jonge mantelzorger") waarvan
`vangnet_termen` er maar 2 dekte. Toegevoegd: `draaglast`, `ondersteuningsbehoefte*`,
`respijtzorg*`, `"sociaal netwerk"`, `"jonge mantelzorger"`.

**`draagkracht`** is getest maar weer verwijderd: gaf 2.310 pure kruisdomein-
ruistreffers (Participatiewet/bijstand/inburgering/leerlingenvervoer) — hetzelfde
patroon als de eerder (2026-09-25) verwijderde term `overbelast*`, ditmaal 4x zo
groot. `overbelasting` zelf is om dezelfde, herbevestigde reden niet toegevoegd. Zie
`config.yaml` en `logs/werklog.md` voor de volledige onderbouwing.

## Cijfers
- Inventaris: 87.091 regelingen (incl. 57 rijen regionale documenten over 3
  samenwerkingsverbanden)
- Selectie: kern 2.469 · waardering 50 · jeugd 990 (alle drie ongewijzigd t.o.v.
  v1.2 — titel-gedreven, dus terecht) · aanbod 886 (was 769) · buiten_scope 600
  (was 476) · twijfel 1.518 (was 1.138) · ruis 80.578
- Ophalen: **6.513 documenten**, 0 fouten (0,00%) — was 5.892
- Parsen: 490.986 passages, 137 0-artikeldocumenten (2,10%, was 2,18%) — gecontroleerd,
  zelfde bekende oorzaken (STOP/LVBB-schema, lege brondata) als v1.1/v1.2, geen nieuwe
  parserbug
- Bijlagen: 1.760 pdf-bijlage-passages (ongewijzigd — kern/waardering-set niet
  aangeraakt door deze wijziging)
- **Totaal: 492.746 passages**
- `mogelijk_verouderd`: 125 documenten gevlagd (was 118)
- 16/16 tests groen

## Checksums
Zie `VERSIE_v1.3_checksums.txt`.

Zie `README.md` ("Bekende beperkingen") en `logs/werklog.md` voor de volledige
beslissingsgeschiedenis.
