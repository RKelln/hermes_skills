#!/usr/bin/env python3
"""propose-facts.py — propose golden facts for each bench case, WITH grep evidence.

Complements derive-facts.py (which ranks candidates broadly). This one is narrow and
mechanical, because a fixture fact is only trustworthy if it is (a) taken from a
content region that a *good* extraction must preserve, and (b) provably present in
the ground truth.

Preference order per case:
  1. ld+json `articleBody` / `description`  -> proves the case rewards structured-data reading
  2. first substantive <p> inside the main content region (the lead paragraph)
  3. ld+json `name` / <h1>                   -> title-level fact
List items, references, sidebars and related-post blocks are deliberately NOT used:
they are present on the page but they are not what extraction is judged on.

Every proposal is verified with a literal substring search against the ground truth
file, and the evidence offset is recorded. Facts that do not verify are dropped, not
patched. Nothing is written into cases.json by this tool — it writes a sidecar file
for review, because a human still has to agree that a string is content worth
requiring.

Ground truth (impersonated fetch, saved by probe-candidates.py):
  $workdir/<mangled-url>.cffi.html
PDF cases fall back to pdftotext output when present.

Usage:
  propose-facts.py --cases cases.json --out facts-proposed.json
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import os
import re
import subprocess
import sys

TAG_RE = re.compile(r"<(script|style|noscript)\b.*?</\1>", re.I | re.S)
LDJSON_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I | re.S
)
H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.I | re.S)
P_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.I | re.S)
MAIN_HINT = re.compile(
    r'(<(?:article|main)\b|role=["\']main["\']|class=["\'][^"\']*'
    r'(?:entry-content|post-content|article-body)[^"\']*["\'])',
    re.I,
)
BOILER = ("cookie", "consent", "subscribe", "newsletter", "sign in", "log in",
          "advertisement", "all rights reserved", "javascript", "enable js")


def clean(s: str) -> str:
    s = TAG_RE.sub(" ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmllib.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def jsonld_blocks(html: str) -> list[dict]:
    out = []
    for raw in LDJSON_RE.findall(html):
        try:
            obj = json.loads(raw.strip())
        except Exception:
            continue
        stack = [obj]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                out.append(cur)
                stack.extend(cur.values())
            elif isinstance(cur, list):
                stack.extend(cur)
    return out


def usable(t: str, lo: int = 35, hi: int = 150) -> bool:
    if not (lo <= len(t) <= hi):
        return False
    low = t.lower()
    if any(b in low for b in BOILER):
        return False
    if not re.search(r"[A-Za-z]{3}", t):
        return False
    return True


def first_sentence(t: str) -> str:
    m = re.split(r"(?<=[.!?])\s+", t)
    for s in m:
        if usable(s):
            return s.strip()
    return ""


def propose(url: str, html: str) -> dict:
    props: list[tuple[str, str]] = []      # (fact, provenance)
    blocks = jsonld_blocks(html)
    for b in blocks:
        for key in ("articleBody", "description"):
            v = b.get(key)
            if isinstance(v, str):
                s = first_sentence(clean(v))
                if s:
                    props.append((s, f"jsonld.{key}"))
        name = b.get("name") or b.get("headline")
        if isinstance(name, str) and usable(clean(name), 20, 120):
            props.append((clean(name), "jsonld.name"))

    region = html
    m = MAIN_HINT.search(html)
    if m:
        region = html[m.start():]
    for pm in P_RE.finditer(region):
        t = clean(pm.group(1))
        s = first_sentence(t)
        if s:
            props.append((s, "lead<p>"))
            break
    h1 = H1_RE.search(html)
    if h1 and usable(clean(h1.group(1)), 15, 120):
        props.append((clean(h1.group(1)), "<h1>"))

    # verify against ground truth, de-dup, cap
    seen, facts, evidence = set(), [], {}
    for fact, prov in props:
        if fact in seen:
            continue
        idx = html.find(fact)
        if idx < 0:
            continue
        seen.add(fact)
        facts.append(fact)
        evidence[fact] = {"provenance": prov, "offset": idx}
        if len(facts) >= 3:
            break
    return {"facts": facts, "evidence": evidence,
            "jsonld_blocks": len(LDJSON_RE.findall(html))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workdir", default="/tmp/webx-bench-probe")
    args = ap.parse_args()

    cases = json.load(open(args.cases, encoding="utf-8"))["cases"]
    report = []
    for case in cases:
        safe = re.sub(r"[^a-zA-Z0-9]+", "_", case["url"])[:90]
        html_path = os.path.join(args.workdir, f"{safe}.cffi.html")
        rec = {"id": case["id"], "url": case["url"], "expect": case["expect"]}
        if not os.path.exists(html_path):
            rec["status"] = "no-ground-truth"
            report.append(rec)
            print(f"{case['id']:26} NO GROUND TRUTH")
            continue
        html = open(html_path, encoding="utf-8", errors="replace").read()
        got = propose(case["url"], html)
        rec.update(got)
        rec["status"] = "proposed" if got["facts"] else "no-facts-found"
        report.append(rec)
        print(f"{case['id']:26} {len(got['facts'])} fact(s)  [ld+json x{got['jsonld_blocks']}]")
        for f in got["facts"]:
            print(f"      ({rec['evidence'][f]['provenance']:18}) {f[:110]}")

    json.dump({"proposals": report}, open(args.out, "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
