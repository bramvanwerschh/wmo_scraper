"""Scraper voor gemeentelijk WMO-beleid en -verordeningen."""

from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup


@dataclass
class WmoDocument:
    gemeente: str
    titel: str
    url: str
    tekst: str


def fetch_page(url: str) -> BeautifulSoup:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")
