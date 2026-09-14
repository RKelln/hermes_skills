#!/usr/bin/env python3
"""fill-facts.py — fill must_contain facts into cases.json from a reviewed mapping.

Facts are chosen by hand (from propose-facts.py output plus peek.py reading), then
written here so the choice is reviewable in one place and reproducible. Every fact is
subsequently checked by `run-bench.py --validate` against tag-stripped ground truth —
facts are NOT validated against raw HTML, because inline links split sentences in the
raw markup while extraction sees the text, so raw-HTML validation would wrongly reject
correct facts.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "cases.json")

FACTS = {
    # --- generic web axes -------------------------------------------------
    "w-static-article": [
        "Neo-Luddism or new Luddism is a philosophy opposing",
        "Luddite",
    ],
    "w-long-article": [
        "Artificial intelligence",
        "Turing test",
    ],
    "w-substack": [
        "6 months to live for open models",
        "The most serious test to date of open source AI",
    ],
    "w-wordpress-news": [
        "Rethinking the Prisoner",
        "How Cooperation Wins",
    ],
    "w-corporate-blog": [
        "NVIDIA and Japan Bring Full-Stack AI and Robotics to Every Industry",
        "NVIDIA and its partners in Japan are this week showcasing",
    ],
    "w-code-docs": [
        "Ownership is a set of rules that govern how a Rust program manages memory",
    ],
    "w-mdn-code-tables": [
        "Array.prototype.map()",
        "The map() method of Array instances creates a new array",
    ],
    "w-table-heavy": [
        "List of countries and dependencies by population",
        "World Population Prospects",
    ],
    "w-paywall-jsonld": [
        "Earlier this year, I was in a workshop with 10 leaders",
        "3 Questions to Pressure-Test Your Priorities",
    ],
    "w-huge-html": [
        "If the mind is an ocean, we spend our lives floating at the surface",
        "Verbalizable Representations Form a Global Workspace",
    ],
    "w-spa-shell": [],            # content absent from served HTML; facts need a rendered view
    "w-vendor-blocked-403": [
        "Acclaimed filmmaker Diego Marcon makes his Canadian debut",
        "Melissa Auf der Maur",
    ],
    "w-vendor-blocked-401": [
        "Find latest news from every corner of the globe at Reuters.com",
        "Brent crude futures",
    ],
    "w-pdf": [],                  # filled below from pdftotext ground truth
    "w-non-english": [
        "Inteligencia artificial",
        "aprendizaje autom",
    ],
    "w-thin-landing": [
        "Building the Internet of Agents (IoA)",
        "Federated registry for cross-framework",
    ],
    "w-github-readme": [
        "Unmute is a system that allows text LLMs to listen and speak",
    ],
    "w-false-success-404": [],
    # --- Togather event axes ---------------------------------------------
    "t-jsonld-event-13": [
        "Ballet Espressivo Late Spring 2024",
        "Events Archive - Dance Ontario",
    ],
    "t-jsonld-event-blues": [
        "Sunday Night Blues Jam",
        "The Sunday Junction Jam",
    ],
    "t-jsonld-event-jazz": [
        "Soul Jazz: An Evening with Donnybrook",
        "Alyssa Giammaria",
    ],
    "t-ssr-shell-luma": [
        "Civic Space Sunday",
        "Upcoming Events on 1RG Public Calendar",
    ],
    "t-consent-banner": [
        "Events Archive - Toronto Railway Museum",
        "Toronto Railway Museum",
    ],
    "t-spa-never-renders": [],    # served HTML has 73 chars of text — nothing to require
    "t-wix-widget": [],           # widget never in served HTML
    "t-freeform-layout": [
        "Runnymede United Church",
        "Orpheus closes out the season alongside guest artists",
        "Saturday May 02, 2026",
    ],
    "t-narrative-dates": [
        "Current Events - Reel Asian",
        "Upcoming Events",
    ],
    "t-detail-dates": [
        "Discover a season filled with musical storytelling",
        "2025/26 Season - Tafelmusik",
    ],
    "t-attr-urls": [
        "Extreme Toronto Sports Club",
        "Co-Ed Recreational Sports for Fun People",
    ],
    "t-cloudflare-challenge": [
        "Contact our events team and learn more about booking event spaces at UC",
    ],
    "t-cloudflare-403": [],
    "t-robots-disallow": [],
    "t-date-blob": [
        "Upcoming events",
    ],
    "t-content-mismatch": [
        "MOCA is Temporarily Closed for Installation",
    ],
}


def main() -> int:
    data = json.load(open(CASES, encoding="utf-8"))
    n = 0
    for case in data["cases"]:
        if case["id"] in FACTS:
            case["must_contain"] = FACTS[case["id"]]
            if FACTS[case["id"]]:
                case["facts_source"] = case.get("facts_source_hint", case["facts_source"])
            n += 1
    data["facts_filled"] = "2026-09-13"
    json.dump(data, open(CASES, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    empty = [c["id"] for c in data["cases"] if not c["must_contain"]]
    print(f"filled {n} cases; {len(empty)} with no facts: {', '.join(empty)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
