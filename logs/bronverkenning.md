# Bronverkenning CVDR (Stap 0)

**Datum verkenning:** 2026-09-25
**Peildatum-voorstel in tests:** 2026-10-01 (nog niet bevestigd, A3)
**User-Agent gebruikt in alle tests:** `wmo-mantelzorg-onderzoek/0.1 (contact: bramvanwerschh@gmail.com)`
Alle ruwe responses staan in `data/raw/zoek/` en `data/raw/docs/`.

---

## 1. SRU-zoekdienst

### 1.1 Werkt de voorbeeld-url uit het plan?
Nee. `query=mantelzorg` (zonder index) geeft een diagnostic-fout:
`Unsupported index — cql.serverChoice`. Zie `data/raw/zoek/sru_test_mantelzorg.xml`.
Ook `cql.textAndIndexes`, `cql.allIndexes` en `dt.title` bestaan niet op deze index.

### 1.2 Echte indexen (via `operation=explain`)
Opgevraagd: `https://zoekservice.overheid.nl/sru/Search?version=1.2&operation=explain&x-connection=cvdr`
→ `data/raw/zoek/sru_explain.xml`. Database: **342.896 documenten** (CVDR Repository), bijgewerkt 2026-09-25.

Bruikbare indexen:
| index | gebruik |
|---|---|
| `dcterms.identifier`, `dcterms.title`, `dcterms.creator`, `dcterms.modified`, `dcterms.subject`, `dcterms.issued` | standaard Dublin Core-velden |
| `gemeente` | filter op organisatie, **exacte CVDR-naam**, bijv. `gemeente="'s-Gravenhage"` |
| `overheidrg.body` | volledige-tekst zoeken, bijv. `overheidrg.body="mantelzorg"` |
| `overheidrg.datumGeldendOp` | **peildatum-filter**, formaat `YYYY-MM-DD`, bijv. `overheidrg.datumGeldendOp=2026-10-01` |
| `overheidrg.indeling` | `beleidsregel` / `verordening overig` / `overig` (zelfde beperking als website: pas betrouwbaar vanaf 20-11-2023) |
| `overheidrg.onderwerp`, `overheidrg.kenmerk`, `overheidrg.inwerkingtredingDatum`, `overheidrg.uitwerkingtredingDatum` | overige metadata |

Combineren met `and`/`or` werkt met CQL-syntax, bijv.:
```
gemeente="'s-Gravenhage" and overheidrg.body="mantelzorg" and overheidrg.datumGeldendOp=2026-10-01
```

### 1.3 Validatie tegen de bekende controlewaarde
Bovenstaande query geeft **`numberOfRecords = 18`** — exact gelijk aan de 18 treffers die het plan noemt voor de website-zoekactie "mantelzorg" in Den Haag op 24-9-2026. Zie `data/raw/zoek/sru_denhaag_mantelzorg_peildatum.xml`. SRU en website geven dus dezelfde resultaten.

### 1.4 Velden per record (`enrichedData`)
Elk record bevat naast de bekende metadata (identifier, titel, creator/gemeente, type, subject, geldigheidsdata, indeling) een `enrichedData`-blok met **kant-en-klare links**:
```xml
<enrichedData>
   <organisatietype>Gemeente</organisatietype>
   <publicatieurl_xml>https://repository.officiele-overheidspublicaties.nl/cvdr/CVDR625849/3/xml/CVDR625849_3.xml</publicatieurl_xml>
   <preferred_url>https://lokaleregelgeving.overheid.nl/CVDR625849/3</preferred_url>
   <preferred_work_url>https://lokaleregelgeving.overheid.nl/CVDR625849</preferred_work_url>
</enrichedData>
```
Dit betekent: **geen aparte stap nodig om de XML-url te construeren of te zoeken** — die staat gewoon in het zoekresultaat.

### 1.5 Paginering
Standaard SRU: `startRecord` (1-based) + `maximumRecords`. Bij minder records dan gevraagd ontbreekt `nextRecordPosition`; anders geeft die het startpunt van de volgende pagina (getest: `maximumRecords=5` op de 18 Den-Haag-resultaten → `nextRecordPosition=6`). **Getest tot `maximumRecords=1000` in één verzoek** (landelijke query `overheidrg.body="mantelzorg" and overheidrg.datumGeldendOp=2026-10-01` → `numberOfRecords=3937`, 1000 records in de respons, geen foutmelding). Dat is veel efficiënter dan de website (max 200 per pagina).

### 1.6 Documenttekst via SRU (`publicatieurl_xml`)
Opgehaald: `CVDR619608_8.xml` (Regeling Maatschappelijke Ondersteuning Den Haag 2018) via de link uit `enrichedData`. Bevat een schone, gestructureerde XML met tags als `hoofdstuk`, `paragraaf`, `artikel`, `kop`/`label`/`nr`/`titel`, `lijst`/`li[@nr]`, `al` (alinea), `bijlage`, `table`.
- Artikel 1.2.3 "Gesprek" is aanwezig met de verwachte mantelzorg-inhoud (bevestigt de controle uit stap 5 van het plan).
- **Belangrijke bevinding voor stap 5 (parsen):** leden (`li nr="1."`) en onderdelen (`li nr="a."`, `li nr="1°"`) zitten **niet consequent genest** in de XML — na een lid-`<lijst>` volgt vaak een aparte sibling-`<lijst>` met de onderdelen, en losse onderdelen kunnen als kale `<al>` tussen twee `<lijst>`-blokken staan. Herkenning moet dus op het **patroon van het `nr`-attribuut** (cijfer+punt = lid, letter+punt = onderdeel, cijfer+° = sub-onderdeel), niet op nesting-diepte.
- Deze regeling heeft **geen apart `toelichting`-element**; de toelichtende tekst ("Toelichting") staat als platte alinea's in de `aanhef/preambule` — consistent met de constatering in §8.1 van het plan bij de Den Haag-subsidieregeling.

### 1.7 Bulkdownload / dataset?
Gezocht op data.overheid.nl. Dataset **"Lokale regelingen"** (https://data.overheid.nl/dataset/lokale-regelingen) bevestigt: **geen bulkbestand beschikbaar**, toegang is uitsluitend via de SRU-zoekdienst (`http://zoekdienst.overheid.nl/sru/Search`, XML, CC0-licentie), met verwijzing naar een "Handleiding SRU" als officiële documentatie. **SRU is dus de door de bron zelf aangewezen route voor hergebruik.**

---

## 2. Websiteroute (aanvullend op §8.2 van het plan, al grotendeels geverifieerd 25-09)

### 2.1 Download-export: open vraag uit het plan getest
Vraag: geeft `count=200` ook echt (tot) 200 regels, i.p.v. alleen de getoonde pagina?
**Test:** POST naar `/ZoekResultaat/Download` met `count=200&page=1` voor de Den Haag/mantelzorg-zoekopdracht (18 treffers totaal).
**Resultaat:** xlsx met **19 rijen = 1 header + alle 18 resultaten** (`data/raw/zoek/download_test_count200.xlsx`). Dus: **bij `count` ≥ het totale aantal treffers geeft de export alles**, niet alleen de eerste 10. Er is geen "exporteer alles"-knop los van `count`; bij gemeenten/query's met > 200 treffers moet je dus alsnog per pagina exporteren (`count=200` is het praktische maximum via de UI-parameter).
Kolommen bevestigd: `Identifier, Titel, Datum inwerkingtreding, Datum uitwerkingtreding, Uitgegeven door, URL` — geen soort regeling, geen onderwerp (zoals het plan al meldde).

### 2.2 Documentpagina + WTI-pagina
Opgehaald: `CVDR478707/6` (html, 264 KB) en `?show-wti=true` (26 KB) → `data/raw/docs/CVDR478707_6*.html`.
WTI-pagina bevat (tekst geëxtraheerd, tags gestript): Overheidsorganisatie, Organisatietype, Officiële naam regeling, Citeertitel, Vastgesteld door, Onderwerp, Eigen onderwerp, Indeling regeling, Regeling onder de Omgevingswet, **Externe bijlagen** (bijv. "Raadsvoorstel" — bruikbaar voor `heeft_bijlage`/`bijlage_urls` uit stap 4), Wettelijke grondslag(en), Gedelegeerde regelgeving, en een volledig wijzigingsoverzicht (datum inwerkingtreding / uitwerkingtreding / betreft / bron bekendmaking / kenmerk per versie). Dit is dus de plek waar bijlage-informatie het makkelijkst vandaan komt.

---

## 3. Vergelijking en aanbeveling

| | SRU | Website (fallback) |
|---|---|---|
| Officieel aangewezen route (data.overheid.nl) | ✅ | — |
| Directe XML-link per document | ✅ (`enrichedData.publicatieurl_xml`) | via losse stap (zoeken op de doc-pagina) |
| Documenttekst-structuur | Schone XML met betekenisvolle tags (`hoofdstuk`, `artikel`, `lijst/li[@nr]`) | HTML met CSS-classes; section-id's **niet betrouwbaar** (plan §8.2) |
| Peildatum-filter | `overheidrg.datumGeldendOp` (index) | `datumrange=op&datumop=` (querystring) |
| Volledige-tekst zoeken (vangnet) | `overheidrg.body` (index) | `tekst=` (querystring) |
| Organisatiefilter | `gemeente=` (index, exacte CVDR-naam) | `gemeenten=` (querystring, zelfde namen) |
| Paginering | `startRecord`/`maximumRecords`, getest tot 1000/call | `page=`, max `count=200`/pagina |
| Bijlage-info, wijzigingsoverzicht | niet in SRU-record | **wel** op WTI-pagina (`?show-wti=true`) |
| Gemeente-/onderwerp-facetten (aantallen) | niet direct; wel af te leiden door te tellen | **wel**, kant-en-klaar in de zoekpagina-html |

**Voorstel:** SRU als **primaire route** voor inventaris (stap 2) én volledige tekst (stap 4, via `publicatieurl_xml`) — officieel aangewezen, structureel schonere data, minder requests door hogere paginagrootte. Website als **aanvulling**: (a) de WTI-pagina voor bijlage-info en het wijzigingsoverzicht bij geselecteerde documenten (stap 4), en (b) facetten als gratis controle op de inventaris-aantallen (stap 2, zoals het plan al voorstelt).

**Belangrijk voor stap 5:** de parser moet op basis van het `nr`-attribuutpatroon werken, niet op XML-nesting — dit wijkt af van wat je in de HTML-structuur (§8.2) zou verwachten en moet apart getest worden op beide testdocumenten.

---

## 4. Openstaand voor het checkpoint

- Route-keuze: **SRU primair + website/WTI aanvullend** — akkoord?
- Nog niet getest: het exacte gedrag van SRU bij méér dan 1000 records in één call (of je dan alsnog moet pagineren — vermoedelijk wel, standaard SRU-gedrag, maar niet expliciet geverifieerd).
- Nog niet getest: rate limits/quota van de SRU-dienst zelf (geen documentatie hierover gevonden; we hanteren sowieso de regel van 1 verzoek/seconde uit §4).
