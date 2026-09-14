#!/usr/bin/env python3
"""derive-facts.py — propose golden fact strings for a case, from the page itself.

The bench scores *fact recall* (did the distinctive content survive extraction?)
rather than byte counts, because byte counts reward nav chrome and punish clean
extraction. A fact is only a valid fixture if a human has confirmed it is real
content on the page — so this tool proposes candidates and prints them; it never
writes a fixture by itself.

Ground truth is the saved HTML from probe-candidates.py (impersonated fetch). For
JS-shell pages the served HTML is not ground truth (the content is added client
side); those cases must take facts from a rendered view instead and be marked
accordingly in cases.json.

Candidates are ranked by how content-like they are:
  + inside the main content region (article/main/[role=main]/common CMS wrappers)
  + from <h1..h4>, <li>, or long <p>
  + contains a digit or a mid-sentence capital (dates, names, prices)
  + length in a useful band (25-140 chars)
  - boilerplate vocabulary (cookie, consent, subscribe, newsletter, menu, skip to)
  - pure nav (short, title-case, ends with "»"), image filenames, URLs

Usage:
  derive-facts.py <html-file> [--n 8]
  derive-facts.py --probe-json /tmp/webx-bench-probe/probe.json [--url SUBSTR]
"""
from __future__ import annotations

import argparse
import glob
import html as htmllib
import json
import os
import re
import sys

BOILER = (
    "cookie", "consent", "privacy", "subscribe", "newsletter", "sign up",
    "log in", "login", "sign in", "skip to", "menu", "search",
    "follow us", "newsletter", "advertisement", "accept all",
    "terms of use", "all rights reserved", "share this", "back to top",
    "donate", "twitter", "facebook", "instagram", "linkedin", "youtube",
)
MAIN_HINT = re.compile(
    r'(<(?:article|main)\b|role=["\']main["\']|id=["\'][^"\']*'
    r'(?:content|main|entry|post|event)[^"\']*["\']|class=["\'][^"\']*'
    r'(?:entry-content|post-content|article-body|event-|tribe-events)[^"\']*["\'])',
    re.I,
)
TAG_RE = re.compile(r"<(script|style|noscript)\b.*?</\1>", re.I | re.S)


def clean(s: str) -> str:
    s = TAG_RE.sub(" ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmllib.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def main_content(html: str) -> str:
    """Best-effort isolation of the main content region."""
    m = MAIN_HINT.search(html)
    if not m:
        return html
    return html[m.start():]


def candidates(html: str) -> list[tuple[float, str]]:
    region = main_content(html)
    out: list[tuple[float, str]] = []
    for tag in ("h1", "h2", "h3", "h4", "li", "p", "time"):
        for m in re.finditer(rf"<{tag}\b[^>]*>(.*?)</{tag}>", region, re.I | re.S):
            t = clean(m.group(1))
            if not (20 <= len(t) <= 160):
                continue
            low = t.lower()
            if any(b in low for b in BOILER):
                continue
            if re.search(r"\.(png|jpe?g|webp|svg|gif)\b", low) or "http" in low:
                continue
            if re.fullmatch(r"[A-Z][\w' -]{0,30}", t):   # single short title-case token
                continue
            score = 0.0
            if tag in ("h1", "h2", "h3"):
                score += 2.0
            elif tag == "li":
                score += 1.2
            else:
                score += 0.6
            if re.search(r"\d", t):
                score += 1.0            # dates, prices, times
            if re.search(r"\d{1,2}[:.]\d{2}", t) or re.search(
                    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)", t):
                score += 1.5
            words = t.split()
            if 5 <= len(words) <= 22:
                score += 0.8
            if t.count("|") + t.count("»") + t.count("←") > 0:
                score -= 1.5
            out.append((score, t))
    # de-dup, keep first occurrence, best score per unique string
    best: dict[str, float] = {}
    for sc, t in out:
        if t not in best or sc > best[t]:
            best[t] = sc
    return sorted(((s, t) for t, s in best.items()), reverse=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("html_file", nargs="?")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--probe-json", default="")
    ap.add_argument("--url", default="")
    ap.add_argument("--cases", default="", help="cases.json — derive for its URLs only")
    ap.add_argument("--workdir", default="/tmp/webx-bench-probe")
    args = ap.parse_args()

    targets: list[str] = []
    if args.cases:
        data = json.load(open(args.cases, encoding="utf-8"))
        for case in data.get("cases", []):
            safe = re.sub(r"[^a-zA-Z0-9]+", "_", case["url"])[:90]
            p = os.path.join(args.workdir, f"{safe}.cffi.html")
            if os.path.exists(p):
                targets.append(p)
            else:
                print(f"\n### MISSING GROUND TRUTH for {case['id']} — {case['url']}")
    elif args.probe_json:
        data = json.load(open(args.probe_json, encoding="utf-8"))
        for rec in data["results"]:
            if args.url and args.url not in rec["url"]:
                continue
            safe = re.sub(r"[^a-zA-Z0-9]+", "_", rec["url"])[:90]
            p = os.path.join(args.workdir, f"{safe}.cffi.html")
            if os.path.exists(p):
                targets.append(p)
    elif args.html_file:
        targets = [args.html_file]
    else:
        targets = sorted(glob.glob(os.path.join(args.workdir, "*.cffi.html")))

    for path in targets:
        html = open(path, encoding="utf-8", errors="replace").read()
        print(f"\n### {os.path.basename(path)[:95]}  ({len(html)}B)")
        for i, (sc, t) in enumerate(candidates(html)[: args.n], 1):
            print(f"  {i}. [{sc:4.1f}] {t[:140]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
