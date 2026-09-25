"""Parsen van ruwe SRU-responses van CVDR. Werkt op local-name() zodat de exacte
namespace-prefixes er niet toe doen (die verschillen per element, zie bronverkenning.md)."""

from lxml import etree


def _find(el, path):
    r = el.xpath(path)
    return r[0].text.strip() if r and r[0].text else None


def _findall_text(el, path):
    return [n.text.strip() for n in el.xpath(path) if n.text]


def parse_search_response(xml_bytes: bytes) -> tuple[list[dict], int | None, int | None]:
    """Geeft (records, number_of_records, next_record_position) terug."""
    root = etree.fromstring(xml_bytes)

    diag = root.xpath("//*[local-name()='diagnostic']")
    if diag:
        message = _find(diag[0], ".//*[local-name()='message']") or "onbekende fout"
        details = _find(diag[0], ".//*[local-name()='details']") or ""
        raise ValueError(f"SRU-diagnostic: {message} ({details})")

    n_text = _find(root, "//*[local-name()='numberOfRecords']")
    number_of_records = int(n_text) if n_text else None

    next_text = _find(root, "//*[local-name()='nextRecordPosition']")
    next_record_position = int(next_text) if next_text else None

    records = []
    for rec in root.xpath("//*[local-name()='record']"):
        identifier = _find(rec, ".//*[local-name()='identifier']")
        if not identifier:
            continue
        if "_" in identifier:
            cvdr_id, versie = identifier.rsplit("_", 1)
        else:
            cvdr_id, versie = identifier, ""

        titel = _find(rec, ".//*[local-name()='title']")
        organisatie = _find(rec, ".//*[local-name()='creator']")
        onderwerpen = _findall_text(rec, ".//*[local-name()='subject']")
        soorten = rec.xpath(
            ".//*[local-name()='type'][contains(@scheme, 'Rubriek')]/text()"
        )
        soort_regeling = soorten[0].strip() if soorten else None
        geldig_vanaf = _find(rec, ".//*[local-name()='inwerkingtredingDatum']")
        geldig_tot = _find(rec, ".//*[local-name()='uitwerkingtredingDatum']")
        indeling = _find(rec, ".//*[local-name()='indeling']")
        url = _find(rec, ".//*[local-name()='preferred_url']")
        xml_url = _find(rec, ".//*[local-name()='publicatieurl_xml']")

        records.append({
            "cvdr_id": cvdr_id,
            "versie": versie,
            "titel": titel,
            "soort_regeling": soort_regeling,
            "indeling": indeling,
            "onderwerp": "; ".join(onderwerpen),
            "geldig_vanaf": geldig_vanaf,
            "geldig_tot": geldig_tot,
            "organisatie": organisatie,
            "url": url,
            "xml_url": xml_url,
        })

    return records, number_of_records, next_record_position
