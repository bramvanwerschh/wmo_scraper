# Overdracht aan Ingeborg en Sjoerd

**Van:** Bram van Wersch, met Claude als bouwer/co-auteur van de pijplijn
**Datum:** 2026-09-30
**Repo:** https://github.com/bramvanwerschh/wmo_scraper (branch `main`, tags v1.0–v1.3)
**Corpus-versie:** v1.3 (bevroren 2026-09-30, peildatum regelgeving 2026-10-01)

## Wat dit is — en wat niet

Dit is **Activiteit 1 "Beleidsanalyse"** uit de gegunde offerte (1008762voo): een
webscraping-pijplijn die alle geldende Wmo-regelgeving (verordeningen, beleidsregels,
nadere regels) van de 342 gemeenten ophaalt via CVDR/lokaleregelgeving.overheid.nl en
opknipt in gestructureerde tekstpassages.

**Deze pijplijn scrapet, selecteert en parseert — hij codeert niet.** De
thematische codering (analysekader: positie/draagkracht/draaglast/behoeften/
instrumenten/jonge mantelzorgers) is de volgende stap en moet nog gebeuren.

**Niet gebouwd, wél onderdeel van Activiteit 1 in de offerte:** de webscraper van de
offerte doorzoekt ook **gemeentewebsites** (niet alleen lokaleregelgeving.overheid.nl)
en ook **beleidsplannen/uitvoeringsplannen/formulieren** (niet alleen CVDR-geregistreerde
verordeningen/beleidsregels). Die twee uitbreidingen zijn in eerdere overleggen met
Bram bewust "module 2" genoemd en zijn in dit project niet gebouwd. Of dat nog moet
gebeuren voor de volledige Activiteit 1, is een beslissing voor jullie/VWS.

## Snel starten

1. Lees `README.md` (setup, gebruik, bestandenoverzicht, bekende beperkingen).
2. Draai een stap in pilotmodus om te verifiëren dat de omgeving werkt, bijv.:
   `./.venv/bin/python3 run.py --stap selectie --gemeenten "'s-Gravenhage,Aa en Hunze,Tiel"`
   (dit is ook letterlijk de door het plan gevraagde overdrachtstoets — graag even
   bevestigen dat dit bij jullie lukt.)
3. Draai de tests: `./.venv/bin/python3 -m pytest tests/ -v` (moet 16/16 groen geven).
4. Het corpus zelf (`data/`) staat **niet** in git (te groot, .gitignore) — dat staat
   lokaal bij Bram. Vraag hem om `data/` te kopiëren, of draai de pijplijn opnieuw
   (alles is hervatbaar via de cache in `data/raw/`, kost geen nieuwe verzoeken).

## Belangrijkste openstaande aandachtspunten voor de analysefase

- **`twijfel`-categorie (1.518 documenten)** is niet handmatig beoordeeld — gaat
  ongefilterd mee naar deze fase. Bevat een mix van echte grensgevallen en ruis.
  `data/rapportage/twijfel.csv` is gesorteerd op frequentie van de titel, handig
  startpunt.
- **`buiten_scope`-categorie (600 documenten)**: beschermd wonen/maatschappelijke
  opvang en Participatiewet-gerelateerde documenten die wél een vangnet-treffer gaven
  maar bewust buiten de onderzoeksvraag vallen (andere toegangsroute dan het
  keukentafelgesprek). Bewuste keuze van Bram, geen bug — maar heroverweeg dit als
  jullie onderzoeksvraag breder wordt.
- **`mogelijk_verouderd`-vlag (125 documenten in `documenten.csv`)**: gemeenten met
  meerdere, bijna gelijk getitelde documenten waarvan er één een recentere
  `geldig_vanaf`-datum heeft. Alleen gevlagd, niet verwijderd — check dit voordat je
  een gemeente met zo'n vlag citeert.
- **`domein_hint`** (wmo/jeugd/beide/onbekend) is een heuristiek, geen garantie —
  vooral bij gecombineerde Wmo+Jeugd-documenten valt begripsbepalingen-achtige content
  vaak op `beide` terug. Zie README voor details.
- **`koppeling_status`**: een klein aantal toelichting-passages kon niet aan een
  artikel gekoppeld worden (`koppeling_status='geen'`).
- **2,10% van de documenten (137 van 6.513) heeft 0 artikelpassages.** Uitgezocht en
  verklaard (README, "Bekende beperkingen") — geen actie nodig, wel goed om te weten
  als je toevallig zo'n document tegenkomt.
- **Conservatiecheck**: bij ~6,6% van de kern+waardering-documenten dekt de som van
  de passagetekens niet de volledige brontekst (95%-drempel). Grondig onderzocht,
  grootste boosdoeners gefixt — resterende gevallen zijn kleine documenten met
  vermoedelijk meetruis. Zie `review/conservatie_check.csv`.
- **Sittard-Geleen** heeft geen `kern`-document met "verordening" in de titel op de
  peildatum (wel Beleidsregels/Besluit Wmo — verordening kennelijk vervallen zonder
  vervanger). **Bunschoten en Druten** hebben geen apart nadere-regels/beleidsregel-
  document naast de verordening.
- **Leiden (CVDR637925/4)**: de toelichting op de verordening staat alleen op de
  gemeentewebsite, niet in CVDR. Bevestigd, geen bug — komt terug als je Leiden
  handmatig napluist en de toelichting mist.
- **`vangnet_termen`** (v1.3, `config.yaml`) is recent uitgebreid n.a.v. de
  zoektermenlijst die de offerte aan VWS toezegt. "draagkracht" en "overbelasting"
  zijn bewust **niet** toegevoegd (grote cross-domein ruis met Participatiewet/
  bijstand) — staan wel in `src/termen.py`'s `STARTLIJST` voor gebruik tijdens de
  codering zelf, waar de documentset al gefilterd is. Zie `config.yaml`-comments en
  `logs/werklog.md` (laatste entry) voor de volledige onderbouwing.

## AI-verantwoording (offerteaanvraag, §"Toelichting op de inzet van AI")

De offerteaanvraag vraagt na oplevering van het eindrapport een informele
**"AI Toelichting"** (apart document, geen onderdeel van het formele eindproduct):
welke onderdelen zijn met AI gedaan, waarom, wat was de meerwaarde, hoe is
zorgvuldigheid geborgd. `logs/werklog.md` documenteert per stap wie een beslissing
nam (Bram vs. Claude) en waarom — dat is het natuurlijke brondocument om die
toelichting op te baseren voor het CVDR-scraping-onderdeel van het onderzoek.

## Contact

Bram is bereikbaar tot dinsdag 6 oktober 2026 (daarna vakantie). Voor vragen over de
pijplijn zelf: `logs/werklog.md` heeft de volledige beslissingsgeschiedenis
chronologisch, inclusief elke gevonden en gefixte bug en de reden voor elke
ontwerpkeuze.
