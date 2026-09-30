# A7: Verslag handmatige steekproefcontrole (29-09-2026)

**Uitgevoerd door:** Claude (op verzoek van Bram), via zoekopdrachten op lokaleregelgeving.overheid.nl en controle van elke kandidaat op de documentpagina (uitgevende gemeente + geldigheid).
**Vraag:** mist het corpus (v1.1) geldende Wmo-kerndocumenten voor deze 10 gemeenten?

## Werkwijze
1. Per gemeente 1–2 webzoekopdrachten, beperkt tot lokaleregelgeving.overheid.nl, op: maatschappelijke ondersteuning / Wmo / nadere regels / beleidsregels / sociaal domein / mantelzorg.
2. Elke gevonden regeling die níet in het controleformulier stond, is op de documentpagina gecontroleerd: welke gemeente heeft hem uitgegeven, en geldt hij op de peildatum?

## Resultaat: 0 gemiste kerndocumenten

| Gemeente | Kandidaat niet in corpus | Uitkomst |
|---|---|---|
| Hilvarenbeek | CVDR705882 Besluit jeugdhulp en mo Hilvarenbeek 2023 | vervallen per 25-08-2026 (vervangen door Nadere regels 2026, CVDR765680, zit in corpus) |
| Hilvarenbeek | CVDR435582 Beleidsregels WMO 2017 | andere gemeente (Leeuwarden), vervallen 2017 |
| Hilvarenbeek | CVDR760311 Beleidsregels jeugdhulp en mo 2026 | andere gemeente (Venlo) |
| Voerendaal | CVDR716845 Beleidsregels mo Wmo 2024 | andere gemeente (Elburg) |
| Voerendaal | CVDR715722 Besluit mo: Nadere regels Wmo 2024 | andere gemeente (Wijk bij Duurstede) |
| Zoeterwoude | CVDR731220 Beleidsregels mo Zoeterwoude 2024 | vervallen per 01-01-2026 (2026-versie zit in corpus) |
| Kaag en Braassem | CVDR628220 Nadere regels sociaal domein | vervallen per 01-01-2021 |
| Amersfoort | CVDR760720 Beleidsregels mo 2026 | andere gemeente (Veldhoven) |
| Bergen (L.) | CVDR89402 Besluit nadere regels Verordening voorzieningen mo | vervallen per 01-01-2012 |
| Geertruidenberg | CVDR633509 Verordening mo Geertruidenberg 2020 | vervallen per 01-07-2025 (Integrale verordening 2025 zit in corpus) |
| Geertruidenberg | CVDR56819 Wmo-beleidsplan 2009–2012 | vervallen per 01-01-2015 |
| Barendrecht | CVDR735081 Nadere regels mo Barendrecht 2025 | vervallen per 01-01-2026 (2026-versie zit in corpus) |
| Leiden | CVDR688252 Nadere regels mo 2026 | andere gemeente (Eemsdelta) |
| Leiden | CVDR751623 Beleidsregels mo 2026 | andere gemeente (Ooststellingwerf) |
| Voorst | – | alleen oudere, vervangen versies gevonden |

In het ingevulde formulier (`steekproef_controleformulier_ingevuld.csv`) staat bij 24 van de 74 corpusdocumenten "ja": die kwamen ook in de zoekresultaten voor. De overige 50 zitten wel in het corpus, maar kwamen niet in de zoekresultaten voor. Dat is geen probleem, want de vraag was of er iets **ontbreekt**.

## Bijvangst
- **Oude regelingen blijven "geldend" in CVDR.** Voorbeelden: Amersfoort (Verstrekkingenboek, CVDR23126; Besluit individuele voorzieningen 2011), Voerendaal (Protocollen 2015 én 2018), Geertruidenberg (Beleidsregels mo 2015, Beleidsplan Wmo 2015). De vlag `mogelijk_verouderd` is dus belangrijk voor de analyse.
- **Zoekresultaten mengen gemeenten.** Een zoekactie op gemeentenaam levert veel regelingen van andere gemeenten met dezelfde titel op. Handmatig controleren zonder de uitgever te checken leidt tot valse "gemist"-meldingen.

## Beperkingen
- Een webzoekmachine is niet uitputtend. Dit is een gerichte controle, geen volledige inventaris per gemeente.
- De gemeentewebsites zelf zijn niet doorzocht. Die vallen onder module 2 (websites/beleidsplannen).

## Conclusie
Checkpoint A7 is gehaald: in de steekproef van 10 gemeenten mist het corpus geen geldend kerndocument.
