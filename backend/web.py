"""
Web search via DuckDuckGo lite endpoint — no API key required.

ponytail: scraping the lite endpoint with requests + BeautifulSoup.
Upgrade path: swap for Tavily/Serper API when you have a key for richer
snippets and rate-limit headroom.
"""

from __future__ import annotations

import logging
import re
from typing import List, Dict
from urllib.parse import urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DDG_URL = "https://lite.duckduckgo.com/lite/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Referer": "https://lite.duckduckgo.com/",
    "Accept": "text/html,application/xhtml+xml",
}


def web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Return list of {title, url, snippet} dicts for the query.

    Returns [] on any failure (logged). DuckDuckGo requires no API key.
    """
    if not query or not query.strip():
        return []
    try:
        resp = requests.get(
            DDG_URL, params={"q": query}, headers=HEADERS, timeout=15
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("web search unavailable: %s", type(exc).__name__)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results: List[Dict[str, str]] = []

    # On the lite endpoint each result is a sequence of <tr> siblings:
    #   row A: title (contains <a href="...uddg=...">)
    #   row B: snippet text
    #   row C: visible URL
    # We pick the anchor row, then grab the next tr's text as the snippet.
    for a in soup.find_all("a", href=True):
        if "uddg=" not in a["href"]:
            continue
        url = _decode_uddg(a["href"])
        if not url:
            continue
        title = _clean(a.get_text())
        snippet = _snippet_from_sibling(a)
        results.append({"title": title, "url": url, "snippet": snippet})
        if len(results) >= max_results:
            break

    return results[:max_results]


def _decode_uddg(href: str) -> str:
    try:
        qs = parse_qs(urlparse(href).query)
        val = qs.get("uddg", [None])[0]
        return unquote(val) if val else ""
    except Exception:
        return ""


def _snippet_from_sibling(a) -> str:
    """Find the snippet row adjacent to the result link row.

    Walk up to the containing <tr>, then take the text of the next sibling <tr>.
    """
    row = a
    while row is not None and getattr(row, "name", None) != "tr":
        row = row.parent
    if row is None:
        return ""
    nxt = row.find_next_sibling("tr")
    if nxt is None:
        return ""
    return _clean(nxt.get_text())


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def search_context(query: str, max_results: int = 5) -> str:
    """Build a text block of search results for prompt context injection."""
    hits = web_search(query, max_results=max_results)
    if not hits:
        return ""
    parts = []
    for i, h in enumerate(hits, 1):
        parts.append(f"[{i}] {h['title']}\nURL: {h['url']}\n{h['snippet']}")
    return "\n\n".join(parts)


def citations_md(hits: List[Dict[str, str]]) -> str:
    """Render hits as a Markdown numbered source list for the UI."""
    if not hits:
        return ""
    lines = []
    for i, h in enumerate(hits, 1):
        title = h.get("title") or "(no title)"
        url = h.get("url") or ""
        lines.append(f"{i}. [{title}]({url})")
    return "\n".join(lines)
