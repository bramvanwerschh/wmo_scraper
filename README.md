# wmo_scraper — CVDR-corpus Wmo-mantelzorg

Corpus van geldende Wmo-regelgeving van alle Nederlandse gemeenten (peildatum
2026-10-01), opgeknipt in passages met behoud van structuur (hoofdstuk > artikel >
lid, toelichting), voor latere thematische analyse (mantelzorger-positie in het
keukentafelgesprek). Deze pijplijn scrapet, selecteert en parseert — codeert niet.

## Setup

```bash
python3.12 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

## Gebruik

```bash
./.venv/bin/python3 run.py --stap <naam>
./.venv/bin/python3 run.py --stap inventaris --gemeenten "'s-Gravenhage,Aa en Hunze,Tiel"   # pilotmodus
```

Stappen (in volgorde): `gemeenten` → `inventaris` → `selectie` → `ophalen` → `parsen`
→ `kwaliteit` → `bijlagen` → `termen` (nog te bouwen). **Volgorde is belangrijk:**
`bijlagen` moet ná `parsen` draaien (voegt pdf-bijlage-passages toe aan een bestand
dat `parsen` volledig herschrijft), en `kwaliteit` (mogelijk_verouderd) ná `ophalen`.

Selectieregels en vangnettermen staan in `config.yaml`, niet in de code.

## Bestanden (kolommen)

- `data/gemeenten.csv` — 342 gemeenten, CBS↔CVDR-naamkoppeling, inwonertal
- `data/inventaris.csv` — alle regelgeving per gemeente op de peildatum, incl. regionale documenten (`regionaal`, `bron_organisatie`, `regio_id`)
- `data/gr_deelnemers.csv` — welke gemeenten meedoen in welke regionale regeling
- `data/selectie.csv` — inventaris + `categorie`/`reden`
- `data/documenten.csv` — opgehaalde ruwe bestanden, incl. `mogelijk_verouderd`
- `data/passages.csv` — het corpus: zie `src/parsen.py` voor de volledige kolomlijst (`passage_id`, `pad`, `sectietype`, `domein_hint`, `wet_label`, `toelichting_kop`/`_sub`/`_artikel_ref`, `koppeling_status`, `tekst`, ...)
- `data/raw/` — ruwe XML/pdf, nooit handmatig wijzigen

## Selectieregels/termen aanpassen

Pas `config.yaml` aan (`selectie:` voor titelregels, `vangnet_termen:` voor de
volledige-tekst-zoekactie) en draai `--stap selectie` opnieuw — alles daarna
(`ophalen`, `parsen`) is hervatbaar en pakt automatisch alleen nieuw geclassificeerde
documenten op.

## Testen

```bash
./.venv/bin/python3 -m pytest tests/ -v
```

`tests/test_parsen.py` bevat harde, geautomatiseerde verwachtingen op 5 testdocumenten
(Den Haag, Aa en Hunze verordening + nadere regels, Hilversum, een wetlabel-testcase).
Draai dit na elke wijziging aan `src/parsen.py`.

## Bekende beperkingen

- **2,18% van de opgehaalde documenten (128 van 5.880) heeft 0 artikelpassages.**
  Uitgesplitst: 25 in het nieuwere STOP/LVBB-schema (`<lvbbu:Consolidaties>`, niet
  ondersteund door deze parser — allemaal categorie `twijfel`, dus geen kern-content
  gemist); 22 hebben een letterlijk lege `<artikel>` in de brondata; ~81 hebben een
  leeg `<regeling-tekst>` waarbij de inhoud (vaak een kort mandaatbesluit) volledig in
  de `<aanhef>` staat — die blijft wel bewaard als aanhef-passage. De striktere
  maatstaf "documenten met écht nul passages van welke soort dan ook" is **0,46%**.
- **Conservatiecheck (som van passagetekens vs. brontekst, exclusief structuurlabels):**
  5,2% van alle documenten en **6,6%** van kern+waardering zit onder 95% (v1.1 — was
  7,8% in v1.0). Belangrijkste resterende oorzaken: (a) inhoud die in externe
  pdf-bijlagen staat — voor 28 kandidaten met `heeft_bijlage=True` en weinig
  passagetekst zijn de pdf's alsnog opgehaald en als `sectietype='bijlage_pdf'`
  toegevoegd (`data/rapportage/bijlage_pdf_status.csv`); 3 daarvan zijn scans zonder
  tekstlaag en dus **niet** verwerkt (geen OCR uitgevoerd); (b) een handvol kleine
  documenten (<5.000 brontekens) met een marginaal verschil, vermoedelijk ruis in de
  meetmethode zelf eerder dan echt verlies. Grondig onderzocht op de 6 grootste
  uitschieters (`logs/werklog.md`, v1.1): drie échte parserbugs gevonden en gefixt
  (meerdere `<nota-toelichting>`-elementen per document, kop-misclassificatie van
  zinnen eindigend op ':', meerdere opmaak-elementen als siblings binnen één `<al>`).
- **Sittard-Geleen heeft geen enkel `kern`-document met "verordening" in de titel** op
  de peildatum (wel Beleidsregels/Besluit Wmo). Eerdere verordeningen bestonden wel
  (laatste: 2025) maar zijn kennelijk vervallen zonder vervanger. Gevlagd in
  `data/rapportage/dekking.csv` (`verordening_niet_in_cvdr`).
- **Bunschoten en Druten hebben geen apart `nadere regels`/`beleidsregel`-document**
  naast de verordening (wel toezicht-/mandaatdocumenten, tarievenlijsten en een
  "Omgekeerde Verordening"). Voor 6 van de oorspronkelijk 8 vergelijkbare gemeenten is
  dit opgelost door regionale documenten (Drechtsteden, ISD Bollenstreek, Samenwerking
  De Bevelanden) aan de inventaris toe te voegen; voor deze twee is geen relevante
  regionale organisatie gevonden in CVDR.
- **`mogelijk_verouderd`-vlag in `documenten.csv`**: 118 documenten gevlagd omdat
  dezelfde gemeente een document heeft met een (bijna) gelijke titel en een recentere
  geldig_vanaf-datum. Alleen gevlagd, niet verwijderd — kan op de peildatum
  legitiem naast elkaar bestaan (bijv. nog niet formeel ingetrokken).
- **Regionale/gemeenschappelijke regelingen**: een landelijke zoekactie vond 45
  niet-gemeentelijke organisaties met wmo/maatschappelijke ondersteuning/sociaal
  domein in de titel (`review/gr_organisaties_volledig.csv`). Hiervan zijn er 11
  (Drechtsteden, ISD Bollenstreek, Samenwerking De Bevelanden) toegevoegd aan het
  corpus, met geverifieerde deelnemerslijst. De overige ~34 (vooral Modulaire
  Gemeenschappelijke Regeling Sociaal Domein Centraal Gelderland/Limburg-Noord,
  GGD-toezichtmandaten) zijn **niet** toegevoegd: overwegend bestuurlijke documenten
  (archiefverordening, controleverordening) zonder substantiële Wmo-inhoud, of
  deelnemerslijst niet geverifieerd.
- **`domein_hint`** is een heuristiek (wet_label → hoofdstuk/paragraaftitel →
  documenttitel → toelichting via gekoppeld artikel), geen garantie. Voor gecombineerde
  Wmo+Jeugd-documenten valt begripsbepalingen-achtige content vaak op `beide` terug
  (71% binnen die documentgroep) — inhoudelijk correct omdat zulke artikelen vaak
  voor beide domeinen gelden, maar niet zo scherp als een handmatige beoordeling.
- **Toelichting-koppeling** (`koppeling_status`): werkt via artikelnummer, met
  terugval op titelmatch als de toelichting een ander nummer noemt dan de regeling.
  Resteert een klein aantal `koppeling_status='geen'` waar geen van beide lukt.

Zie `logs/werklog.md` voor de volledige beslissingsgeschiedenis en `review/` voor de
onderliggende controlebestanden van deze bevindingen.
