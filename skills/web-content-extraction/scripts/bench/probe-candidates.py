#!/usr/bin/env python3
"""probe-candidates.py — characterize candidate URLs for the extraction bench.

For each candidate URL, fetches it two ways and reports the *characteristics*
that decide which bench axis it belongs to, so cases are chosen by evidence
instead of by intuition.

  plain curl        -> status + size          (does the site bot-block plain clients?)
  curl-cffi chrome  -> status + size + HTML   (what a browser-fingerprinted client sees)
  curl-fetch via webclaw/webx is NOT used here: the point is to characterize the
  PAGE, not the engines.

Markers extracted from the impersonated HTML:
  ldjson        count of <script type="application/ld+json"> blocks
  schema_types  @type values seen inside those blocks (Event/Article/...)
  next_data     __NEXT_DATA__ present (Next.js SSR data)
  nuxt/gatsby/qwik  framework SSR payload markers
  text_chars    tag-stripped text length (tiny text + big HTML => JS shell)
  consentish    cookie/consent interstitial wording present in visible text
  scripts       <script> count (JS-heavy pages)

Output: JSON to stdout (or --out), plus a compact table to stderr.
Usage: probe-candidates.py [--file candidates.txt] [--out probe.json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

PLAIN_TIMEOUT = 45
CFFI_TIMEOUT = 90

SCRIPT_RE = re.compile(r"<script\b", re.I)
TAG_RE = re.compile(r"<(script|style)\b.*?</\1>", re.I | re.S)
ANYTAG_RE = re.compile(r"<[^>]+>")
LDJSON_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)
TYPE_RE = re.compile(r'"@type"\s*:\s*"([^"]+)"')
CONSENT_WORDS = (
    "accept all cookies",
    "we use cookies",
    "cookie preferences",
    "manage consent",
    "your privacy choices",
    "consent to the use",
)


def text_of(html: str) -> str:
    t = TAG_RE.sub(" ", html)
    t = ANYTAG_RE.sub(" ", t)
    t = re.sub(r"&nbsp;?", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def fetch_plain(url: str, dest: str) -> dict:
    """Plain curl — the un-impersonated view. Returns status + size."""
    try:
        r = subprocess.run(
            ["curl", "-sL", "-w", "%{http_code}", "-o", dest, url],
            capture_output=True, text=True, timeout=PLAIN_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "size": 0}
    status = (r.stdout or "").strip() or "000"
    size = os.path.getsize(dest) if os.path.exists(dest) else 0
    if r.returncode != 0:
        return {"status": f"err{r.returncode}", "size": size}
    return {"status": status, "size": size}


def fetch_cffi(url: str) -> tuple[str, str]:
    """curl-cffi with a Chrome TLS fingerprint, via uvx (same as webx uses)."""
    try:
        r = subprocess.run(
            ["uvx", "curl-cffi", "get", url, "--impersonate", "chrome", "--body"],
            capture_output=True, text=True, timeout=CFFI_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return "", "timeout"
    if r.returncode != 0:
        return "", f"err{r.returncode}"
    return r.stdout or "", "200" if r.stdout else "empty"


def characterize(url: str, cffi_html: str) -> dict:
    out: dict = {}
    blocks = LDJSON_RE.findall(cffi_html)
    out["ldjson_blocks"] = len(blocks)
    types: list[str] = []
    for b in blocks:
        for t in TYPE_RE.findall(b):
            if t not in types:
                types.append(t)
    out["schema_types"] = types[:8]
    low = cffi_html.lower()
    out["next_data"] = "__next_data__" in low
    out["nuxt"] = "__nuxt__" in low
    out["gatsby"] = "___gatsby" in low or "gatsby-focus-wrapper" in low
    out["scripts"] = len(SCRIPT_RE.findall(cffi_html))
    txt = text_of(cffi_html)
    out["text_chars"] = len(txt)
    out["consentish"] = any(w in txt.lower() for w in CONSENT_WORDS)
    # JS shell heuristic: real HTML but almost no text, lots of script
    out["js_shell"] = bool(out["text_chars"] < 1200 and out["scripts"] > 5
                           and len(cffi_html) > 20000)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--file", default=os.path.join(here, "candidates.txt"))
    ap.add_argument("--out", default="")
    ap.add_argument("--workdir", default=os.path.join(tempfile.gettempdir(), "webx-bench-probe"))
    args = ap.parse_args()

    os.makedirs(args.workdir, exist_ok=True)
    urls = []
    with open(args.file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("\t")]
            urls.append((parts[0], parts[1] if len(parts) > 1 else ""))

    results = []
    for i, (url, label) in enumerate(urls, 1):
        safe = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:90]
        plain_dest = os.path.join(args.workdir, f"{safe}.plain.html")
        plain = fetch_plain(url, plain_dest)
        html, cstatus = fetch_cffi(url)
        cffi = {"status": cstatus, "size": len(html.encode("utf-8", "replace"))}
        ch = characterize(url, html) if html else {}
        if html:
            with open(os.path.join(args.workdir, f"{safe}.cffi.html"), "w",
                      encoding="utf-8", errors="replace") as f:
                f.write(html)
        rec = {"url": url, "label": label, "plain": plain, "cffi": cffi, **ch}
        results.append(rec)
        print(f"[{i}/{len(urls)}] {url}\n"
              f"      plain {plain['status']}/{plain['size']}B  cffi {cstatus}/{cffi['size']}B  "
              f"ldjson={ch.get('ldjson_blocks', '-')} next={ch.get('next_data', '-')} "
              f"text={ch.get('text_chars', '-')} shell={ch.get('js_shell', '-')} "
              f"consent={ch.get('consentish', '-')} types={ch.get('schema_types', [])}",
              file=sys.stderr)

    payload = {"probed": len(results), "workdir": args.workdir, "results": results}
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"\nwrote {args.out}", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
