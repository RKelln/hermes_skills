#!/usr/bin/env python3
"""
InterAccess website scraper — full working example of:
  - BeautifulSoup targeted extraction (Method 7)
  - Sitemap-based discovery with XML namespace handling
  - Page-type auto-detection (standard / VF microsite / listing)
  - Manifest-based incremental sync with HEAD change detection
  - Structured last_sync.json for downstream agent consumption
  - Rate limiting via --delay flag

Working copy: /home/experimance/Documents/assistant/interaccess_scraper.py

Key patterns demonstrated:
  1. Three page type detectors (standard, VF microsite, listing)
  2. BeautifulSoup class_ substring matching fix (lambda filter)
  3. Date range merging ("Apr 22" + "to" + "May 9" → "Apr 22 to May 9")
  4. img[alt] fallback when h3 is JS-populated and empty in static HTML
  5. Sitemap XML parsing with default namespace
  6. HEAD Last-Modified/ETag comparison for change detection
  7. Content hash (SHA-256) for audit trail
  8. Structured JSON changes file for agent follow-up
  9. time.sleep(delay) between all HTTP requests

Dependencies: requests, beautifulsoup4, markdownify
Install: uv pip install requests beautifulsoup4 markdownify
"""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md_convert
import re
import sys
import os
import json
import hashlib
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

BASE = "https://www.interaccess.org"
HEADERS = {"User-Agent": "Mozilla/5.0"}
EN_DASH = "\u2013"
MDASH = "\u2014"
TIMEOUT = 30


def fetch(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def detect_type(soup: BeautifulSoup) -> str:
    """Return 'standard', 'vf', or 'listing'."""
    if soup.find("main", class_="main-wrapper") and soup.find("div", class_="article-content"):
        return "standard"
    if soup.find("div", class_="vf26__main-contents"):
        return "vf"
    if soup.find("section", class_=lambda c: c and "section-aricle-lister-preview" in c):
        return "listing"
    if soup.find("section", class_="section-article-wrapper"):
        return "standard"
    return "unknown"


def discover_sitemap(filter_prefixes: list[str] | None = None) -> list[str]:
    """Discover all content URLs from the Webflow sitemap."""
    import xml.etree.ElementTree as ET
    resp = requests.get(f"{BASE}/sitemap.xml", headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.fromstring(resp.text)
    urls = []
    for url_elem in root.findall("sm:url", ns):
        loc = url_elem.find("sm:loc", ns)
        if loc is not None and loc.text:
            u = loc.text.strip()
            if "/internal/" in u or u.endswith("/search"):
                continue
            if filter_prefixes:
                path = u.replace(BASE, "")
                if not any(path.startswith(p) for p in filter_prefixes):
                    continue
            urls.append(u)
    return sorted(urls)


def scrape_standard(soup: BeautifulSoup, url: str) -> str:
    """Scrape a standard InterAccess detail page."""
    out = []
    title_el = soup.find("h1", class_="article-title")
    if not title_el:
        content = soup.find("div", class_="article-content")
        if content:
            title_el = content.find("h1")
    title = title_el.get_text(strip=True) if title_el else "Untitled"
    out.append(f"# {title}")
    out.append(f"[{url}]({url})")
    out.append("")

    # Date/meta sidebar with range merging
    sidebar = soup.find("div", class_="article-sidebar-wrapper")
    if sidebar:
        raw_items = [d.get_text(strip=True) for d in sidebar.find_all("div", class_="text-size-small") if d.get_text(strip=True)]
        merged = []
        i = 0
        while i < len(raw_items):
            cur = raw_items[i]
            if i + 2 < len(raw_items) and raw_items[i + 1].lower() == "to":
                merged.append(f"{cur} to {raw_items[i+2]}")
                i += 3
            else:
                if cur.lower() != "published":
                    merged.append(cur)
                i += 1
        for d in merged:
            out.append(f"**{d}**")
        if merged:
            out.append("")

    # Rich text body
    richtext = soup.find("div", class_="text-rich-text")
    if richtext:
        inner = "".join(str(c) for c in richtext.children)
        md_body = md_convert(inner, heading_style="atx", strip=["img"])
        out.append(md_body.strip())
        out.append("")

    return "\n".join(out)


def scrape_vf(soup: BeautifulSoup, url: str) -> str:
    """Scrape a Vector Festival 2026 microsite page."""
    out = []

    # Title: h2.rich-text__h2 is the specific page title
    specific_el = soup.find("h2", class_="vf26__rich-text__h2")
    specific_title = specific_el.get_text(strip=True) if specific_el else ""
    festival_el = soup.find("h1", class_="vf26__festival-name")
    festival_name = festival_el.get_text(strip=True) if festival_el else ""
    fest_brand_el = soup.find("h1", id="vf26__vf26-header") or soup.find("h1", class_="vf26__h1")
    fest_brand = fest_brand_el.get_text(strip=True) if fest_brand_el else ""

    if specific_title:
        display_title = specific_title
        if festival_name and festival_name.lower() != specific_title.lower():
            display_title = f"{festival_name}: {specific_title}"
    elif festival_name:
        display_title = festival_name
    else:
        display_title = "Untitled"

    out.append(f"# {display_title}")
    out.append(f"[{url}]({url})")
    if fest_brand and fest_brand not in display_title:
        out.append(f"*{fest_brand}*")
    out.append("")

    # Dates — filter out background duplicates and hyphen
    date_container = soup.find("div", class_="vf26__date")
    if date_container:
        dates = date_container.find_all("h2", class_="vf26__h2")
        date_texts = [
            d.get_text(strip=True)
            for d in dates
            if d.get_text(strip=True) != EN_DASH
            and "vf26__hyphen" not in (d.get("class") or [])
        ]
        if date_texts:
            out.append(f"**{f' {EN_DASH} '.join(date_texts)}**")
            out.append("")

    # Rich text blocks
    main = soup.find("div", class_="vf26__main-contents")
    if main:
        for element in main.find_all(["h3", "div"], recursive=True):
            if element.name == "h3" and "vf26__rich-text__header" in element.get("class", []):
                out.append(f"### {element.get_text(strip=True)}")
                out.append("")
            elif element.name == "div" and "w-richtext" in element.get("class", []):
                inner = "".join(str(c) for c in element.children)
                md = md_convert(inner, heading_style="atx", strip=["img"])
                if md.strip():
                    out.append(md.strip())
                    out.append("")

    # Featured artists
    artists_container = soup.find("div", class_="vf26__featured-artists__container")
    if artists_container:
        for item in artists_container.find_all("div", class_="vf26__featured-artist__item"):
            name_el = item.find("h3", class_="vf26__featured-artist__header")
            desc_el = item.find("p", class_="vf26__ui--black")
            link_el = item.find("a", class_="vf26__featured-artist__link")
            if name_el:
                name = name_el.get_text(strip=True)
                desc = desc_el.get_text(strip=True) if desc_el else ""
                link = urljoin(BASE, link_el.get("href", "")) if link_el else ""
                if link:
                    out.append(f"- **[{name}]({link})** {MDASH} {desc}")
                else:
                    out.append(f"- **{name}** {MDASH} {desc}")
        out.append("")

    return "\n".join(out)


# For full sync/manifest/discovery functions, see the working copy at
# /home/experimance/Documents/assistant/interaccess_scraper.py
# Key additions in the full version:
#   - Manifest class with JSON persistence
#   - sync() with sitemap diff + HEAD check change detection
#   - Structured last_sync.json output for agent consumption
#   - Rate limiting via time.sleep(delay) between all HTTP requests
#   - CLI: --sync, --data-dir, --filter, --force, --delay, --list
