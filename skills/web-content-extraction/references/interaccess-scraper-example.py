#!/usr/bin/env python3
"""Scrape https://www.interaccess.org/ homepage into structured markdown.

Demonstrates the BeautifulSoup targeted-extraction pattern for Webflow CMS
listing pages — the class of site where trafilatura and html2text produce
near-empty output because card-based layouts look like boilerplate.

Usage:
    uv run python3 interaccess-scraper-example.py                    # stdout
    uv run python3 interaccess-scraper-example.py -o interaccess.md  # to file

Dependencies: requests, beautifulsoup4
Install: uv pip install requests beautifulsoup4
"""

import requests
from bs4 import BeautifulSoup
import re
import sys
from datetime import datetime

URL = "https://www.interaccess.org/"
BASE = "https://www.interaccess.org"

def full_url(href):
    if not href:
        return ''
    if href.startswith('http'):
        return href
    return BASE + href

def scrape():
    resp = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    output = []
    output.append(f"# InterAccess — {datetime.now().strftime('%B %d, %Y')}")
    output.append(f"[{URL}]({URL})")
    output.append("")

    # Vector Festival banner
    banner = soup.find('a', class_='link-block-2')
    if banner:
        banner_text = banner.get_text(strip=True)
        banner_href = banner.get('href', '')
        output.append(f"> **[{banner_text}]({full_url(banner_href)})**")
        output.append("")

    sections = [
        ('bg-exhibitions', 'Exhibitions'),
        ('bg-events', 'Events'),
        ('bg-workshops', 'Workshops'),
        ('bg-news', 'News'),
    ]

    for css_class, section_name in sections:
        section = soup.find('section', class_=lambda c: c and 'section-aricle-lister-preview' in c and css_class in c)
        if not section:
            continue

        output.append(f"## {section_name}")
        output.append("")

        cards = section.find_all('a', class_='card')
        if not cards:
            dyn_items = section.find('div', class_='w-dyn-items')
            if dyn_items:
                cards = dyn_items.find_all('a', class_='card')

        for card in cards:
            href = card.get('href', '')
            furl = full_url(href)

            # Title: h3 first, fall back to image alt (exhibition h3s are JS-populated)
            title_el = card.find('h3', class_='heading-style-h3')
            title = title_el.get_text(strip=True) if title_el else ''
            if not title:
                img = card.find('img', class_='card-image')
                title = img.get('alt', '') if img else ''
            if not title:
                title = '(untitled)'

            # Description
            desc_el = card.find('div', class_='card-description')
            desc = desc_el.get_text(strip=True) if desc_el else ''

            # Dates — filter out separator divs
            date_wrapper = card.find('div', class_='card-term')
            dates = []
            if date_wrapper:
                for ds in date_wrapper.find_all('div', class_='text-size-small'):
                    t = ds.get_text(strip=True)
                    classes = ds.get('class', [])
                    if t and t != '-' and 'separator' not in classes:
                        dates.append(t)
            date_str = ' — '.join(dates) if dates else ''

            output.append(f"### [{title}]({furl})")
            if date_str:
                output.append(f"**{date_str}**")
            if desc:
                output.append(desc)
            output.append("")

        # "More" link
        more_link = section.find('a', string=re.compile(r'More', re.I))
        if not more_link:
            more_link = section.find('a', class_='button')
        if more_link:
            more_href = more_link.get('href', '')
            if more_href:
                output.append(f"[More {section_name} →]({full_url(more_href)})")
        output.append("")

    # Footer
    footer = soup.find('footer')
    if footer:
        output.append("---")
        output.append("### Visit")
        addr_div = footer.find('div', class_='pre-nav-text')
        if addr_div:
            raw = addr_div.get_text('\n', strip=False)
            clean_lines = [l.strip() for l in raw.split('\n') if l.strip()]
            output.append('\n'.join(clean_lines[:12]))

    return '\n'.join(output)

if __name__ == '__main__':
    md = scrape()
    if '-o' in sys.argv:
        idx = sys.argv.index('-o')
        path = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else 'interaccess.md'
        with open(path, 'w') as f:
            f.write(md)
        print(f"Saved to {path} ({len(md)} chars)", file=sys.stderr)
    else:
        print(md)
