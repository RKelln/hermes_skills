#!/usr/bin/env python3
"""add-js-cases.py — add capability-flag variants of the JS-shell cases to cases.json.

Why these cases exist: the first bench run measured each engine in its DEFAULT mode,
which for crw means no rendering at all. That produced a true statement ("crw does not
render these shells") and a misleading one ("crw cannot render these shells") — the flag
`--js` recovers 14.8 KB of article and 8.5 KB of event listings from pages the default
mode returns 77 and 66 characters for.

So the fixture set needs both variants: the default case (out-of-the-box behaviour) and
the flag case (available capability). They are separate case ids on the same URL.

Ground truth for a rendered case cannot be the served HTML — the content is not in it.
It is a captured render, saved as <mangled>.rendered.txt beside the served HTML and
labelled `rendered` by the harness, so an engine-derived fixture can never pass itself
off as page truth.

Facts are proposed here and verified against the capture before being written; anything
that does not verify is dropped with a warning rather than written hopefully.

Idempotent: re-running replaces the case entries instead of duplicating them.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "cases.json")
PROBE = "/tmp/webx-bench-probe"
CRW = os.environ.get("CRW_BIN") or "/tmp/crw-recon/bin/crw"

# url -> (axis, why, candidate facts)
VARIANTS = {
    "https://kyutai.org/blog/2026-01-13-pocket-tts/": (
        "w-spa-shell-rendered",
        "JS shell + capability flag: content absent from served HTML",
        "Served HTML is 9.7 KB with 498 chars of text and no article. crw's default mode "
        "returns 77 chars; with --js its Lightpanda rung returns the full post. webx has "
        "no renderer at all, so this is the class where a render tier would be additive.",
        ["Pocket TTS: a high-quality TTS with voice cloning that runs on CPU",
         "We present Pocket TTS"],
    ),
    "https://www.anotherstory.ca/events/": (
        "t-spa-never-renders-rendered",
        "Togather 'SPA never renders' + capability flag",
        "Observed on the source: a headless browser never resolves the event list; the "
        "page spins on an Ant Design loading state. Default mode: 66 "
        "chars. With --js: real listings with titles, authors and Eventbrite links.",
        ["Amanda Sung", "Neither Here Nor There"],
    ),
    "https://www.churchwellesleyvillage.ca/events": (
        "t-wix-widget-rendered",
        "Togather: Wix OOI never renders within the scraper's render timeout + capability flag",
        "Observed on the source: the Wix OOI widget never renders within the scraper's render "
        "timeout. Default mode: 1,419 chars of nav. With --js: the rendered calendar grid appears.",
        ["October 2026"],
    ),
    "https://luma.com/1rg-calendar": (
        "t-ssr-payload-rendered",
        "negative control: rendering does NOT help when data is in a JSON payload",
        "Included as a counter-case. crw --js almost doubles the text here (1,120 -> 1,914 "
        "chars) and takes 20 s, but the events are in the __NEXT_DATA__ payload rather than "
        "the DOM, so no events appear. Rendering is not a universal fix; reading the payload "
        "is a different fix.",
        [],          # deliberately no facts
    ),
}


# Cases sharing a URL with a VARIANTS entry (the dict is keyed by URL, so a second case on
# the same page needs its own list). Tuple shape: (url, case_id, axis, why, candidates).
EXTRA_VARIANTS = [
    (
        "https://www.anotherstory.ca/events/",
        "t-spa-never-renders-fallback",
        "webx's own opt-in fallback, end to end",
        "Same page as t-spa-never-renders-rendered but a different question: webx alone "
        "fails here (63 chars), and this case asserts it reaches the facts when given "
        "--fallback-engine=crw. Ground truth is the same captured render, so the fixture "
        "cannot pretend webx solved it without the flag.",
        ["Amanda Sung", "Neither Here Nor There"],
    ),
]


def bench_safe(url: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", url)[:90]


# Per-case engine arguments that differ from the default {"crw": ["--js"]}. Used by the
# webx-fallback case, which exists to regression-test webx's own opt-in second engine
# end-to-end (webx may not reach the facts alone, and does with the flag).
EXTRA_ENGINE_ARGS = {
    "t-spa-never-renders-fallback": {"webx": ["--fallback-engine=crw"], "crw": ["--js"]},
}


def render(url: str) -> str:
    """Fetch with crw --js; return the markdown, or '' on failure."""
    try:
        res = subprocess.run([CRW, "scrape", url, "--js", "--format", "json"],
                             capture_output=True, text=True, timeout=180)
        data = json.loads(res.stdout)
        return data.get("markdown") or ""
    except Exception as exc:
        print(f"  !! render failed for {url}: {str(exc)[:90]}", file=sys.stderr)
        return ""


def main() -> int:
    if not os.path.exists(CRW):
        print(f"crw not found at {CRW}; set CRW_BIN", file=sys.stderr)
        return 1
    data = json.load(open(CASES, encoding="utf-8"))
    by_id = {c["id"]: c for c in data["cases"]}
    added, dropped = 0, 0

    for url, case_id, axis, why, candidates in (
            [(u, *spec) for u, spec in VARIANTS.items()] + EXTRA_VARIANTS):
        safe = bench_safe(url)
        text = render(url)
        if not text:
            continue
        rendered_path = os.path.join(PROBE, f"{safe}.rendered.txt")
        with open(rendered_path, "w", encoding="utf-8") as fh:
            fh.write(text)

        verified = []
        for fact in candidates:
            if fact in text:
                verified.append(fact)
            else:
                print(f"  dropped unverified fact for {url[:40]}: {fact[:60]}",
                      file=sys.stderr)
                dropped += 1

        case = {
            "id": case_id,
            "group": "web" if "kyutai" in url else "togather",
            "axis": axis,
            "url": url,
            "expect": "ok",
            "facts_source": "rendered",
            "engine_args": EXTRA_ENGINE_ARGS.get(case_id, {"crw": ["--js"]}),
            "why": why,
            "must_contain": verified,
            "must_not_contain": [],
            "ground_truth": f"{safe}.rendered.txt",
        }
        if case_id in by_id:
            by_id[case_id].update(case)
        else:
            data["cases"].append(case)
            added += 1
        print(f"  {case_id:46} {len(verified)} fact(s)  render {len(text)} chars")

    data["js_variants_added"] = "2026-09-13"
    json.dump(data, open(CASES, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\nadded {added} case(s), dropped {dropped} unverified fact(s), "
          f"{len(data['cases'])} total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
