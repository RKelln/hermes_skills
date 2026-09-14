#!/usr/bin/env python3
"""jsonld_extract.py <page.html> — publisher-declared content, as a JSON envelope.

Called by webx as a helper process on the already-downloaded page. Emits ONE line of
JSON:

    {"text": ..., "title": ..., "types": [...], "blocks": [...], "truncated": bool}

    text    the publisher's own article body — articleBody, or a long-text field inside
            __NEXT_DATA__ — PREFIXED with that node's headline.
    title   the headline used, or null.
    types   every @type seen anywhere in the ld+json graph (deduped, capped).
    blocks  the parsed ld+json blocks themselves, size-capped.
    truncated  true when blocks were dropped to stay inside the cap.

Why the envelope rather than plain text (the previous behaviour):

  1. The old helper returned articleBody ALONE. Whenever the JSON-LD candidate won the
     scoring, the page title was lost from the output — measurable, and it cost a
     benchmark case: webx returned 8,025 chars of HBR body text with no title at all,
     which is why it scored 1/2 on the paywall case while two other engines scored 2/2.
  2. The graph was parsed and then thrown away. That is the expensive half: for event
     sources the useful payload is not prose, it is the Event nodes. Emitting them lets
     callers read structured fields instead of re-parsing HTML they already handed us.

The graph is capped because some pages carry enormous graphs (a Wix events page in the
bench carried a 381-entry graph); the body text is always independent of the cap.

Stdlib only, deliberately: this runs in a subprocess on every page and must never be the
thing that breaks a fetch.
"""
import json
import os
import re
import sys

MAX_GRAPH_BYTES = int(os.environ.get("WEBX_STRUCTURED_MAX_BYTES", "20000"))
MAX_BLOCKS = 40
MAX_TYPES = 40
MIN_BODY = 200
BLOCK_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)
NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL)
LONG_TEXT_KEYS = ("articleBody", "body", "content", "text")


def walk(obj, fn):
    if isinstance(obj, dict):
        fn(obj)
        for value in obj.values():
            walk(value, fn)
    elif isinstance(obj, list):
        for item in obj:
            walk(item, fn)


def parse_blocks(html: str) -> list:
    blocks = []
    for match in BLOCK_RE.finditer(html):
        try:
            blocks.append(json.loads(match.group(1)))
        except Exception:
            continue
    return blocks


def parse_next_data(html: str):
    match = NEXT_DATA_RE.search(html)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except Exception:
        return None


def best_from_blocks(blocks: list) -> tuple:
    """Longest articleBody, plus the headline from the SAME node that carried it."""
    types: list = []
    state: dict = {"body": None, "title": None}

    def visit(node):
        node_type = node.get("@type")
        for cand in (node_type if isinstance(node_type, list) else [node_type]):
            if isinstance(cand, str) and cand not in types:
                types.append(cand)
        body = node.get("articleBody")
        if isinstance(body, str) and len(body) >= MIN_BODY:
            if state["body"] is None or len(body) > len(state["body"]):
                state["body"] = body
                head = node.get("headline") or node.get("name")
                state["title"] = (head.strip()
                                  if isinstance(head, str) and 0 < len(head) < 300 else None)

    for block in blocks:
        walk(block, visit)
    return state["body"], state["title"], types


def best_from_next_data(next_data) -> str | None:
    found: list = []

    def visit(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, str) and len(value) > 500 and key in LONG_TEXT_KEYS:
                    found.append(value)
                visit(value)
        elif isinstance(node, list):
            for item in node[:5]:
                visit(item)

    visit(next_data)
    return max(found, key=len) if found else None


def shrink(obj, max_items: int = 3, max_depth: int = 4, max_str: int = 2000, depth: int = 0):
    """A bounded stand-in for an oversized node: keep shape, sample items evenly.

    Sampling the HEAD of a list is the wrong default for the pages this exists for.
    An events page ships one flat list of hundreds of Event nodes whose order is
    arbitrary, so taking the first three kept three unknown events and dropped the
    rest; spreading the sample across the list at least represents the whole set.
    """
    if depth > max_depth:
        return "…"
    if isinstance(obj, dict):
        return {k: shrink(v, max_items, max_depth, max_str, depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        if len(obj) <= max_items:
            picked = list(obj)
        else:
            step = len(obj) / max_items
            picked = [obj[min(len(obj) - 1, int(i * step))] for i in range(max_items)]
        return [shrink(v, max_items, max_depth, max_str, depth + 1) for v in picked]
    if isinstance(obj, str) and len(obj) > max_str:
        return obj[:max_str] + "…"
    return obj


# Item budgets tried in order when a single block is larger than the cap: use as much
# of the available budget as the block's own shape allows, rather than guessing one size.
SHRINK_STEPS = (3, 10, 25, 60, 150)


def cap_graph(blocks: list) -> tuple:
    """Keep whole blocks while they fit the byte budget; report truncation.

    An all-or-nothing cap is wrong here. A single oversized block is usually the
    *interesting* one — a Wix or Events-Calendar page ships the whole event list inside
    one ld+json block, so dropping it wholesale means detecting `Event` types while
    handing the caller nothing to read.
    """
    kept, used, truncated = [], 0, False
    for block in blocks[:MAX_BLOCKS]:
        try:
            size = len(json.dumps(block, ensure_ascii=False))
        except Exception:
            truncated = True
            continue
        if used + size <= MAX_GRAPH_BYTES:
            kept.append(block)
            used += size
            continue
        if not kept:
            best = None
            for items in SHRINK_STEPS:
                candidate = shrink(block, max_items=items)
                try:
                    csize = len(json.dumps(candidate, ensure_ascii=False))
                except Exception:
                    continue
                if used + csize <= MAX_GRAPH_BYTES:
                    best = candidate
                else:
                    break          # this budget already overflows; smaller ones were kept
            if best is None:
                best = shrink(block, max_items=SHRINK_STEPS[0])
            kept.append({"_shrunk": True,
                         "_note": ("block exceeded the graph cap; lists sampled, not complete. "
                                   "Raise WEBX_STRUCTURED_MAX_BYTES for the full graph."),
                         "data": best})
            try:
                used += len(json.dumps(best, ensure_ascii=False))
            except Exception:
                pass
        truncated = True
    return kept, truncated or len(blocks) > len(kept)


def build(html: str) -> dict:
    blocks = parse_blocks(html)
    body, title, types = best_from_blocks(blocks)
    if body is None:
        next_data = parse_next_data(html)
        if next_data is not None:
            body = best_from_next_data(next_data)
            if body is not None and title is None:
                title = None      # NEXT_DATA payloads have no reliable headline field
    text = ""
    if body:
        text = (("# " + title + "\n\n") if title else "") + body.strip()
    kept, truncated = cap_graph(blocks)
    return {
        "text": text,
        "title": title,
        "types": types[:MAX_TYPES],
        "blocks": kept,
        "truncated": truncated,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"text": "", "title": None, "types": [], "blocks": [],
                          "truncated": False}))
        return 0
    with open(sys.argv[1], encoding="utf-8", errors="replace") as fh:
        html = fh.read()
    print(json.dumps(build(html), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
