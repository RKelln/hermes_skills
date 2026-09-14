#!/usr/bin/env python3
"""peek.py — print the main-content text of a probed URL, for choosing fixture facts.

Facts must be chosen by a human (or at least eyeballed), so this makes the *reading*
cheap: it prints the region a good extraction should preserve, not the whole page.

Usage:
  peek.py <url-substring> [--chars 700] [--workdir /tmp/webx-bench-probe]
  peek.py --list                        # show probed URLs available
"""
from __future__ import annotations

import argparse
import glob
import html as htmllib
import os
import re
import sys

TAG_RE = re.compile(r"<(script|style|noscript)\b.*?</\1>", re.I | re.S)
MAIN_HINT = re.compile(
    r'(<(?:article|main)\b|role=["\']main["\']|class=["\'][^"\']*'
    r'(?:entry-content|post-content|article-body|wp-block|elementor)[^"\']*["\'])',
    re.I,
)


def clean(s: str) -> str:
    s = TAG_RE.sub(" ", s)
    s = re.sub(r"<(br|/p|/h[1-6]|/li|/div)\b[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmllib.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("needle", nargs="?", default="")
    ap.add_argument("--chars", type=int, default=700)
    ap.add_argument("--workdir", default="/tmp/webx-bench-probe")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--body", action="store_true", help="print whole main region")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.workdir, "*.cffi.html")))
    if args.list:
        for f in files:
            print(os.path.basename(f))
        return 0

    hits = [f for f in files if args.needle and args.needle in os.path.basename(f)]
    if not hits:
        print(f"no probed file matching {args.needle!r}; use --list", file=sys.stderr)
        return 1
    for f in hits:
        raw = open(f, encoding="utf-8", errors="replace").read()
        m = MAIN_HINT.search(raw)
        region = raw[m.start():] if m else raw
        text = clean(region)
        print(f"===== {os.path.basename(f)}")
        print(f"      ({len(raw)}B raw, main-region text {len(text)} chars)")
        print(text if args.body else text[: args.chars])
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
