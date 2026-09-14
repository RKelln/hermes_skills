#!/usr/bin/env python3
"""run-bench.py — cross-engine extraction bench over cases.json.

WHY IT EXISTS
  Comparing extraction engines by output size is actively misleading: byte counts
  reward nav chrome and punish clean extraction. A tool that returns 1.7x more
  markdown may simply be keeping the menu. This harness scores FACT RECALL — a case
  declares distinctive content strings that must survive extraction — and records
  each engine's own failure/success signal alongside.

WHAT IT MEASURES, PER CASE PER ENGINE
  status          ok | empty | error | timeout | refused
  chars           extracted characters (reported, never used as the score)
  facts           hit/total against the case's must_contain list
  leak            case must_not_contain strings that appear (boilerplate/block pages)
  method          the engine's own account of what it did
                    webx     -> extraction path from its metadata
                    crw      -> renderDecision + sourceHash + statusCode
                    webclaw  -> whether structured_data (JSON-LD) came back
  seconds         wall clock
  artifacts       raw output kept per case so a human can read the disagreement

VALIDATE MODE
  `--validate` checks every declared fact against the GROUND TRUTH: the tag-stripped,
  whitespace-normalised text of the served page (or pdftotext output for PDF cases).
  Raw HTML is the wrong target — a sentence containing inline links is split by markup
  in the source but intact in extracted text, so validating against raw HTML produces
  false fixture errors. Ground truth comes from probe-candidates.py saves.

USAGE
  run-bench.py --validate
  run-bench.py --engines webx,webclaw,crw [--group web|togather] [--only ID,ID]
  run-bench.py --engines webx --only w-static-article --show
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_WORKDIR = "/tmp/webx-bench"
PROBE_WORKDIR = "/tmp/webx-bench-probe"
TIMEOUT = 120

TAG_RE = re.compile(r"<(script|style|noscript)\b.*?</\1>", re.I | re.S)


def match_norm(s: str) -> str:
    """Normalise text for FACT MATCHING (not for display).

    Three legitimate equalities are collapsed, because they are rendering differences
    rather than content differences — an engine must not be scored as missing content
    that it plainly returned:

      1. HTML entities / non-breaking spaces   -> plain characters and spaces
      2. markdown emphasis and links           -> **bold** -> bold, [label](url) -> label
      3. markup noise (heading #, blockquote >, bullets) -> removed

    Facts and haystacks are normalised identically, so this can only ever make
    matching less brittle, never more permissive about absent words.
    """
    s = htmllib.unescape(s or "")
    s = s.replace("\u00a0", " ").replace("\u2009", " ").replace("\u202f", " ")
    s = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", s)     # md links/images -> label
    s = re.sub(r"\[(\d+)\]", " ", s)                     # wikipedia-style [1] refs
    s = re.sub(r"<[^>]+>", " ", s)                       # stray tags
    s = re.sub(r"[*_`#>|]+", " ", s)                     # md emphasis / heading / quote
    return re.sub(r"\s+", " ", s).strip()


def norm(s: str) -> str:
    """Whitespace-normalised text, for fact matching. Entities decoded."""
    s = htmllib.unescape(s or "")
    s = s.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", s).strip()


def strip_tags(s: str) -> str:
    """Tag-stripped text, KEEPING structured-data payloads.

    <script> blocks are normally not 'content', but an application/ld+json block and a
    __NEXT_DATA__ payload ARE part of the served page and are exactly what a
    structured-data-aware engine reads. Dropping them makes every JSON-LD-sourced
    fixture fact look like a fixture error, which is how this bug was caught.
    """
    s = re.sub(r"<(script|style|noscript)\b([^>]*)>(.*?)</\1>",
               keep_script, s, flags=re.I | re.S)
    return strip_inline(s)


def keep_script(m: re.Match) -> str:
    open_tag, body = m.group(0)[:200], m.group(3)
    if re.search(r'application/ld\+json|__NEXT_DATA__', open_tag, re.I):
        return " " + body + " "
    return " "


def strip_inline(s: str) -> str:
    return norm(re.sub(r"<[^>]+>", " ", s))


def snippet_for(fact: str, hay: str, width: int = 130) -> str:
    """Diagnostic: show where the fact's anchor word lands in the ground truth."""
    words = [w for w in re.findall(r"[A-Za-z0-9]{4,}", fact)]
    for w in words:
        i = hay.lower().find(w.lower())
        if i >= 0:
            return "…" + hay[max(0, i - 40): i + width].replace("\n", " ") + "…"
    return "(anchor word not found in ground truth at all)"


def ground_truth(case: dict, workdir: str) -> tuple[str, str]:
    """Return (text, source-label) for a case's ground truth.

    Prefers a RENDERED capture when the case says its facts came from a rendered view
    (`facts_source: rendered`). Those cases exist because the content genuinely is not
    in the served HTML — a JS shell — so served HTML cannot be the truth source for
    them. The capture is saved beside the served HTML as <mangled>.rendered.txt and is
    logged with its own label, so a fixture whose truth is engine-derived is always
    visible as such rather than passing itself off as page truth.
    """
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", case["url"])[:90]
    if case.get("facts_source") == "rendered":
        rendered = os.path.join(workdir, f"{safe}.rendered.txt")
        if os.path.exists(rendered):
            text = open(rendered, encoding="utf-8", errors="replace").read()
            return match_norm(text), f"rendered({len(text)}B)"
        return "", "missing-rendered"
    html_path = os.path.join(workdir, f"{safe}.cffi.html")
    if case["id"] == "w-pdf":
        pdf = os.path.join(workdir, f"{safe}.pdf")
        src = pdf if os.path.exists(pdf) else html_path
        if os.path.exists(src):
            try:
                r = subprocess.run(["pdftotext", "-layout", src, "-"],
                                   capture_output=True, text=True, timeout=60)
                if r.returncode == 0 and r.stdout.strip():
                    return norm(r.stdout), "pdftotext(served-pdf)"
            except Exception:
                pass
        return "", "missing"
    if not os.path.exists(html_path):
        return "", "missing"
    html = open(html_path, encoding="utf-8", errors="replace").read()
    return strip_tags(html), f"served-html({len(html)}B)"


# --------------------------------------------------------------------------- engines

def engine_cmds(case) -> dict:
    """Build each engine's command for a case, honouring per-case extra arguments.

    A case may carry "engine_args": {"crw": ["--js"]} so the bench can measure a
    capability behind a flag rather than only the out-of-the-box default. That
    distinction is not cosmetic: crw's default mode never renders a JS shell, so a
    default-only run would record "cannot render" for a tool that renders fine on
    request.
    """
    url = case["url"] if isinstance(case, dict) else case
    extra = (case.get("engine_args") or {}) if isinstance(case, dict) else {}
    crw = os.environ.get("CRW_BIN") or shutil.which("crw")
    if not crw:
        for cand in ("/tmp/crw-recon/bin/crw", os.path.expanduser("~/.local/bin/crw")):
            if os.path.exists(cand):
                crw = cand
                break
    webclaw = shutil.which("webclaw") or os.path.expanduser("~/.local/bin/webclaw")
    webx = shutil.which("webx") or os.path.expanduser("~/.local/bin/webx")
    return {
        "webx": [webx, url, "--json", *(extra.get("webx") or [])],
        "webclaw": [webclaw, url, "-f", "json", *(extra.get("webclaw") or [])],
        "crw": ([crw, "scrape", url, "--format", "json", *(extra.get("crw") or [])]
                if crw else None),
    }


CONTENT_KEY_RE = re.compile(r"^(markdown|content|text|body|main|article|extract)", re.I)


def pick_text(obj, depth: int = 0) -> str:
    """Find the engine's extracted text in its JSON envelope.

    Prefers an explicitly content-named field before recursing, so that a long nested
    string (a JSON-LD @graph, a metadata blob) cannot masquerade as the extraction —
    that bug made webclaw look like it had missed a sentence it had in fact returned.
    """
    if depth > 6 or obj is None:
        return ""
    if isinstance(obj, str):
        return ""
    if isinstance(obj, list):
        for v in obj:
            t = pick_text(v, depth + 1)
            if t:
                return t
        return ""
    if not isinstance(obj, dict):
        return ""
    named = [v for k, v in obj.items()
             if isinstance(v, str) and CONTENT_KEY_RE.match(k) and v.strip()]
    if named:
        return max(named, key=len)
    # some envelopes nest the payload one level down, e.g. {"data": {...}}
    for k, v in obj.items():
        if isinstance(v, (dict, list)):
            t = pick_text(v, depth + 1)
            if t:
                return t
    return ""


def engine_signal(name: str, parsed, stderr: str) -> str:
    if name == "crw" and isinstance(parsed, dict):
        rd = parsed.get("renderDecision") or {}
        bits = []
        if rd:
            bits.append(f"render={rd.get('kind') or rd.get('chosen')}"
                        + (f"/{rd.get('reason')}" if rd.get("reason") else ""))
            if rd.get("chain"):
                bits.append("chain=" + "->".join(rd["chain"]))
        md = parsed.get("metadata") or {}
        if md.get("statusCode"):
            bits.append(f"http={md['statusCode']}")
        if md.get("elapsedMs"):
            bits.append(f"engine={md['elapsedMs']}ms")
        if parsed.get("sourceHash"):
            bits.append("hash=yes")
        return " ".join(bits)
    if name == "webclaw" and isinstance(parsed, dict):
        sd = parsed.get("structured_data")
        n = len(sd) if isinstance(sd, list) else (1 if sd else 0)
        dd = (parsed.get("domain_data") or {}).get("domain_type")
        return f"structured_data={n}" + (f" domain={dd}" if dd else "")
    if name == "webx":
        m = re.search(r"method[=:\s]+([a-zA-Z0-9_-]+)", stderr or "")
        if not m:
            m = re.search(r"via (\w+)", stderr or "")
        return f"method={m.group(1)}" if m else ""
    return ""


def run_engine(name: str, cmd: list[str] | None, case: dict, outdir: str) -> dict:
    rec = {"engine": name, "status": "error", "chars": 0, "seconds": None,
           "facts": [], "facts_hit": 0, "leak": [], "method": "", "artifact": ""}
    if not cmd or not os.path.exists(cmd[0]):
        rec["status"] = "not-installed"
        return rec
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", case["url"])[:60]
    artifact = os.path.join(outdir, f"{case['id']}__{name}__{safe}.out")
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        rec["status"] = "timeout"
        rec["seconds"] = round(time.time() - t0, 2)
        return rec
    rec["seconds"] = round(time.time() - t0, 2)
    with open(artifact, "w", encoding="utf-8", errors="replace") as f:
        f.write(f"# cmd: {' '.join(cmd)}\n# rc: {r.returncode}\n# --- stdout ---\n{r.stdout}"
                f"\n# --- stderr ---\n{r.stderr}")
    rec["artifact"] = os.path.basename(artifact)

    parsed = None
    text = ""
    if r.stdout.strip():
        try:
            parsed = json.loads(r.stdout)
            text = pick_text(parsed)
        except Exception:
            text = r.stdout
    if not text:
        text = r.stdout

    rec["chars"] = len(norm(text))
    rec["method"] = engine_signal(name, parsed, r.stderr)
    if r.returncode != 0 and rec["chars"] < 200:
        rec["status"] = "error"
    elif rec["chars"] < 200:
        rec["status"] = "empty"
    else:
        rec["status"] = "ok"

    hay = match_norm(text)
    for fact in case.get("must_contain") or []:
        hit = match_norm(fact) in hay
        rec["facts"].append({"fact": fact, "hit": hit})
        if hit:
            rec["facts_hit"] += 1
    for bad in case.get("must_not_contain") or []:
        if match_norm(bad).lower() in hay.lower():
            rec["leak"].append(bad)
    return rec


# --------------------------------------------------------------------------- modes

def do_validate(cases: list[dict]) -> int:
    print("VALIDATE — checking declared facts against ground truth "
          "(tag-stripped served HTML; pdftotext for PDF cases)\n")
    errors = 0
    for case in cases:
        facts = case.get("must_contain") or []
        if not facts:
            continue
        gt, src = ground_truth(case, PROBE_WORKDIR)
        if not gt:
            print(f"  !! {case['id']:26} no ground truth ({src}) — cannot validate")
            errors += 1
            continue
        for fact in facts:
            if norm(fact) in gt:
                print(f"  ok {case['id']:26} {fact[:70]}")
            else:
                print(f"  FIXTURE ERROR {case['id']:26} {fact[:70]}")
                print(f"        near: {snippet_for(fact, gt)}")
                errors += 1
    print(f"\n{errors} fixture error(s)")
    return 1 if errors else 0


def do_run(cases: list[dict], engines: list[str], workdir: str, show: bool) -> int:
    os.makedirs(workdir, exist_ok=True)
    report = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "engines": engines, "results": []}
    for case in cases:
        row = {"id": case["id"], "group": case["group"], "axis": case["axis"],
               "url": case["url"], "expect": case["expect"],
               "facts_total": len(case.get("must_contain") or []), "engines": {}}
        cmds = engine_cmds(case)
        for eng in engines:
            rec = run_engine(eng, cmds.get(eng), case, workdir)
            row["engines"][eng] = rec
        report["results"].append(row)
        line = f"{case['id']:26}"
        for eng in engines:
            r = row["engines"][eng]
            f = (f"{r['facts_hit']}/{row['facts_total']}" if row["facts_total"] else "-")
            line += f" | {eng}:{r['status'][:5]}/{f}/{r['chars']}c/{r['seconds']}s"
        print(line, flush=True)
    out = os.path.join(workdir, "report.json")
    json.dump(report, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\nreport: {out}\nartifacts: {workdir}/")
    if show:
        for row in report["results"]:
            print(f"\n===== {row['id']}  {row['url']}")
            for eng, r in row["engines"].items():
                print(f"  {eng:8} {r['status']:5} {r['chars']:>7}c {str(r['seconds']):>6}s "
                      f"facts {r['facts_hit']}/{row['facts_total']}  {r['method']}"
                      + (f"  LEAK={r['leak']}" if r["leak"] else ""))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=os.path.join(HERE, "cases.json"))
    ap.add_argument("--engines", default="webx,webclaw,crw")
    ap.add_argument("--group", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--workdir", default=DEFAULT_WORKDIR)
    args = ap.parse_args()

    cases = json.load(open(args.cases, encoding="utf-8"))["cases"]
    if args.group:
        cases = [c for c in cases if c["group"] == args.group]
    if args.only:
        want = {x.strip() for x in args.only.split(",") if x.strip()}
        cases = [c for c in cases if c["id"] in want]
    if args.validate:
        return do_validate(cases)
    engines = [e.strip() for e in args.engines.split(",") if e.strip()]
    return do_run(cases, engines, args.workdir, args.show)


if __name__ == "__main__":
    sys.exit(main())
