# Corpus v1.0 — bevroren snapshot

**Datum bevriezing:** 2026-09-25
**Peildatum regelgeving:** 2026-10-01

## Cijfers
- 342 gemeenten
- 87.091 regelingen in de selectie (inclusief 57 regionale rijen via Drechtsteden/ISD Bollenstreek/Samenwerking De Bevelanden)
- 5.880 documenten opgehaald (0,00% fouten)
- 457.749 passages
- Foutpercentage 0-artikeldocumenten: 2,18% (128/5.880); documenten met echt 0 passages: 0,46%
- Conservatiecheck kern+waardering: 7,8% onder 95%

## Categorieverdeling (regelingen / passages)
| Categorie | Regelingen | Passages |
|---|---|---|
| ruis | 81.211 | 0 |
| kern | 2.469 | 201.157 |
| twijfel | 1.138 | 109.300 |
| jeugd | 990 | 79.191 |
| aanbod | 757 | 44.433 |
| buiten_scope | 476 | 22.843 |
| waardering | 50 | 825 |
| **totaal** | **87.091** | **457.749** |

Zie `review/categorie_tabel.md`.

## Checksums (SHA-256) van de kernbestanden
Zie `VERSIE_v1.0_checksums.txt` in de projectroot.

## Reproduceren
```bash
git checkout v1.0
./.venv/bin/python3 run.py --stap selectie
./.venv/bin/python3 run.py --stap ophalen
./.venv/bin/python3 run.py --stap parsen
./.venv/bin/python3 run.py --stap bijlagen
./.venv/bin/python3 run.py --stap kwaliteit
./.venv/bin/python3 -m pytest tests/ -v
```
`data/raw/` (ruwe XML/pdf) staat niet in git (te groot) maar blijft lokaal bewaard
als bron-van-waarheid; met die map aanwezig is bovenstaande volledig deterministisch
op de checksums na (SRU-landelijke queries voor de vangnettermen kunnen in theorie
nieuwe documenten opleveren als er na 2026-09-25 nieuwe regelgeving is gepubliceerd
die vóór de peildatum 2026-10-01 al geldig is).

Zie `README.md` ("Bekende beperkingen") voor de volledige lijst met afwijkingen en
uitzonderingen, en `logs/werklog.md` voor de volledige beslissingsgeschiedenis.
