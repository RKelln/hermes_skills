#!/usr/bin/env python3
"""Generic zero-dependency HTML -> readable-markdown extractor.

Use when pages are already downloaded to disk (curl/webx --keep) and you need
whole-page text across several files at once, or when webx/trafilatura are
unavailable. Supplements webx (which is per-URL and prefers article selectors);
this one keeps the full page, headings intact.

Usage:  python3 html_extract.py page1.html [page2.html ...]
Writes <name>.md next to each input. Prints output char count per file —
verify counts are non-trivial (a styled 404 or interstitial extracts to a few
chars; 4xx/5xx pages should have been rejected at download time).

Strips <script>/<style>/<nav>/<footer>, preserves headings as markdown
(# level), converts li/p/br/tr/div to newlines, unescapes entities, collapses
blank-line runs. Write the result unedited to the raw layer; synthesize
elsewhere.

Why a file and not an inline one-liner: `python3 -c "..."` chained inside a
shell `||` fallback silently breaks when shell variables interpolate into the
inline code (hit 2026-08-08, Olares research: empty outputs, no error).
"""
import html
import os
import re
import sys


def extract(f):
    with open(f, encoding="utf-8", errors="replace") as fh:
        h = fh.read()
    h = re.sub(r"<script.*?</script>", "", h, flags=re.S)
    h = re.sub(r"<style.*?</style>", "", h, flags=re.S)
    h = re.sub(r"<nav.*?</nav>", "", h, flags=re.S)
    h = re.sub(r"<footer.*?</footer>", "", h, flags=re.S)
    h = re.sub(
        r"<h([1-6])[^>]*>(.*?)</h\1>",
        lambda m: "\n\n" + "#" * int(m.group(1)) + " " + m.group(2) + "\n\n",
        h,
        flags=re.S,
    )
    h = re.sub(r"<(li|p|br|tr|div)[^>]*>", "\n", h, flags=re.I)
    t = re.sub(r"<[^>]+>", "", h)
    t = html.unescape(t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    return t


def main():
    if len(sys.argv) < 2:
        print("usage: python3 html_extract.py file1.html [file2.html ...]")
        return 1
    for f in sys.argv[1:]:
        if not os.path.exists(f):
            print(f"skip (missing): {f}")
            continue
        out = os.path.splitext(f)[0] + ".md"
        text = extract(f)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"{out}: {len(text)} chars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
