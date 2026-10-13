"""Чтение: свежие статьи бесплатных польских порталов (RSS) и чистый текст статьи.

    .venv/bin/python tools/read.py feed naukawpolsce        # последние статьи (или любой URL RSS)
    .venv/bin/python tools/read.py text https://…           # текст статьи
Текст берётся через читалку r.jina.ai (отправляет туда только адрес статьи); не вышло — из <p> страницы.
"""
import html
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import common  # noqa: F401  — UTF-8 вывод на Windows

FEEDS = {  # бесплатные, без пейвола — проверено 2026-10-14
    "naukawpolsce": "https://naukawpolsce.pl/rss.xml",   # Nauka w Polsce (PAP): наука, здоровье, Земля
    "natemat": "https://natemat.pl/rss/wszystkie",       # naTemat: общество, быт — источник текстов экзамена
}
UA = {"User-Agent": "Mozilla/5.0"}
MAX_CHARS = 6000


def fetch(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_feed(xml_text: str, limit: int = 8) -> list[tuple[str, str, str]]:
    """[(дата ГГГГ-ММ-ДД, заголовок, ссылка)] из RSS, свежие первыми."""
    root = ET.fromstring(xml_text)
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        try:
            date = parsedate_to_datetime((item.findtext("pubDate") or "").strip()).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            date = ""
        if title and link:
            items.append((date, html.unescape(title), link))
    return sorted(items, key=lambda x: x[0], reverse=True)[:limit]


def paragraphs(page: str) -> str:
    """Запасной путь: текст из <p>…</p>."""
    found = re.findall(r"<p[^>]*>(.*?)</p>", page, flags=re.S | re.I)
    text = " ".join(html.unescape(re.sub(r"<[^>]+>", "", p)).strip() for p in found)
    return re.sub(r"\s+", " ", text).strip()


def article(url: str) -> str:
    try:
        text = fetch(f"https://r.jina.ai/{url}", timeout=40)
        text = text.split("Markdown Content:", 1)[-1].strip()
    except OSError:
        text = paragraphs(fetch(url))
    return text[:MAX_CHARS]


def main() -> None:
    if len(sys.argv) < 3 or sys.argv[1] not in ("feed", "text"):
        print(__doc__)
        print("Ленты:", ", ".join(FEEDS))
        return
    if sys.argv[1] == "feed":
        for date, title, link in parse_feed(fetch(FEEDS.get(sys.argv[2], sys.argv[2]))):
            print(f"{date} · {title} · {link}")
    else:
        print(article(sys.argv[2]))


if __name__ == "__main__":
    main()
