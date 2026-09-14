#!/usr/bin/env python3
"""rescore.py — re-score a bench run from its saved artifacts, without re-fetching.

Two channels are scored, because they answer different questions:

  facts_in_text     facts present in the engine's EXTRACTED TEXT. This is what you get
                    if you consume the tool the way we currently do — markdown out.
  facts_in_payload  facts present ANYWHERE in the engine's response, including side
                    channels we don't yet consume (webclaw's structured_data, crw's
                    links/metadata, webx's json-ld path).

The distinction matters and is not a technicality. On Togather's Tier-0 sources the
event names can be entirely absent from an engine's text output while sitting in its
parsed JSON-LD: webclaw returned "35 events found" plus the submission form as text,
with all the event names only in structured_data. Scoring text-only would call that a
total miss; scoring payload-only would call it a win. Both numbers belong in the report.

Because artifacts hold the full stdout/stderr of each run, scoring can be revisited
without repeating slow work (chrome renders cost ~15s per case).

Usage:
  rescore.py [--dir /tmp/webx-bench] [--cases cases.json] [--engines webx,webclaw,crw]
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load_harness():
    spec = importlib.util.spec_from_file_location(
        "runbench", os.path.join(HERE, "run-bench.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load run-bench.py for its normalisers")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def artifact_path(workdir: str, case_id: str, engine: str) -> str | None:
    hits = glob.glob(os.path.join(workdir, f"{case_id}__{engine}__*.out"))
    return hits[0] if hits else None


def payload_text(raw: str) -> str:
    """Full stdout of a run, normalised for matching.

    If stdout is JSON it is re-serialised so that escapes (\\", \\u2019) become real
    characters; matching against the raw JSON source under-counts facts that contain
    quotes. Falls back to the raw text for non-JSON output.
    """
    if "# --- stdout ---" not in raw:
        return raw
    out = raw.split("# --- stdout ---", 1)[1].split("# --- stderr ---", 1)[0]
    try:
        return json.dumps(json.loads(out), ensure_ascii=False, indent=1)
    except Exception:
        return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="/tmp/webx-bench")
    ap.add_argument("--cases",
                    default=os.path.join(HERE, "cases.json"))
    ap.add_argument("--engines", default="webx,webclaw,crw")
    ap.add_argument("--matrix", action="store_true")
    args = ap.parse_args()

    rb = load_harness()
    engines = [e.strip() for e in args.engines.split(",") if e.strip()]
    cases = json.load(open(args.cases, encoding="utf-8"))["cases"]

    rows, totals = [], {e: {"text": 0, "payload": 0, "n": 0,
                            "status": {}, "secs": 0.0} for e in engines}
    for case in cases:
        facts = case.get("must_contain") or []
        row = {"id": case["id"], "group": case["group"], "facts": len(facts), "engines": {}}
        for eng in engines:
            p = artifact_path(args.dir, case["id"], eng)
            if not p:
                row["engines"][eng] = {"status": "no-artifact"}
                continue
            raw = open(p, encoding="utf-8", errors="replace").read()
            rc = re.search(r"# rc: (-?\d+)", raw)
            rc = int(rc.group(1)) if rc else None
            out = payload_text(raw)
            parsed, text = None, ""
            if out.strip():
                try:
                    parsed = json.loads(out)
                    text = rb.pick_text(parsed)
                except Exception:
                    text = out
            if not text:
                text = out
            hay_text = rb.match_norm(text)
            hay_payload = rb.match_norm(out)
            hit_text = [f for f in facts if rb.match_norm(f) in hay_text]
            hit_payload = [f for f in facts if rb.match_norm(f) in hay_payload]
            status = ("error" if (rc not in (0, None) and len(text) < 200)
                      else "empty" if len(text) < 200 else "ok")
            row["engines"][eng] = {
                "status": status, "chars_text": len(text), "chars_payload": len(out),
                "facts_text": len(hit_text), "facts_payload": len(hit_payload),
                "missed_text": [f for f in facts if f not in hit_text],
            }
            t = totals[eng]
            t["text"] += len(hit_text)
            t["payload"] += len(hit_payload)
            t["n"] += len(facts)
            t["status"][status] = t["status"].get(status, 0) + 1
        rows.append(row)

    if args.matrix:
        hdr = f"{'case':26}{'facts':>6} " + "".join(f"{e:>19}" for e in engines)
        print(hdr)
        print("-" * len(hdr))
        for r in rows:
            line = f"{r['id']:26}{r['facts']:>6} "
            for e in engines:
                d = r["engines"].get(e, {})
                if d.get("status") == "no-artifact":
                    line += f"{'—':>19}"
                else:
                    line += f"{d['facts_text']}/{d['facts_payload']:<3}" \
                            f"{d['chars_text']:>7}c{d['status'][:4]:>6}"
            print(line)
        print("\n(columns: facts_in_text / facts_in_payload   then text chars, status)\n")

    print("TOTALS  (facts_in_text / facts_in_payload of all declared facts)")
    for e in engines:
        t = totals[e]
        n = t["n"] or 1
        print(f"  {e:9} text {t['text']:>3}/{t['n']:<3} ({100*t['text']/n:>4.0f}%)   "
              f"payload {t['payload']:>3}/{t['n']:<3} ({100*t['payload']/n:>4.0f}%)   "
              f"status {t['status']}")

    print("\nFACTS LOST FROM TEXT BUT PRESENT IN PAYLOAD (side-channel content):")
    any_side = False
    for r in rows:
        for e in engines:
            d = r["engines"].get(e, {})
            if d.get("facts_payload", 0) > d.get("facts_text", 0):
                any_side = True
                print(f"  {r['id']:26} {e:8} "
                      f"text {d['facts_text']} -> payload {d['facts_payload']}")
    if not any_side:
        print("  (none)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
