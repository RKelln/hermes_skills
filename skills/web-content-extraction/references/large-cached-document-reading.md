# Reading a large document already saved to disk as markdown

**Trigger:** `web_extract` (or `webx --out`) has left you a big markdown file on disk — the
`[TRUNCATED] … Full text saved to: <path>` footer, or any 100K+ char `.md`. You now need to
*actually read* it without burning context or spilling tool output.

This is distinct from `long-form-web-paper-reading.md` (which reads a JS-rendered paper *live
in the browser*). Here the content is already a local file; the problem is *consuming* it.

## The failure mode this avoids

`read_file` caps at ~100K chars per read and, when it overflows, **spills** the result to a
persisted-output JSON file (`~/.hermes/cache/spillover/call_*.txt`). You then have to page
through a JSON-wrapped dump (`{"content": "1|LINE..."}`) with lost line numbering — awkward
and wasteful. A 264K-char encyclical dumped this way on the very first read (2026-09-08).

**Don't blind-read a large file. Map its structure first, then read only the sections you need,
each sized under the spill cap.**

## Workflow

### 1. Map the structure with execute_code (one pass, ~3 lines)

```python
import re
text = open(path, encoding="utf-8", errors="replace").read()
print("chars", len(text), "lines", len(text.splitlines()))
lines = text.splitlines()
for i, ln in enumerate(lines):
    s = ln.strip()
    if not s: continue
    if re.search(r'\*\*', s) or s.startswith('***') or re.match(r'^[A-Z][A-Z\s&,.'-]{10,}$', s):
        print(f"{i:5d} | {s[:110]}")
```

The heading regex targets how HTML pages survive markdown extraction: bold `**…**` / `***…***`
section headers, ALL-CAPS title lines, and (add if needed) paragraph-number starts
`^\d{1,3}\.\s` for numbered legal/ecclesiastical documents (encyclicals, rulings).

### 2. Compute per-section char counts to size your chunks

```python
sections = {"intro": (0, 65), "ch3": (245, 341), "ch5": (463, 612)}
for name, (a, b) in sections.items():
    print(name, len("\n".join(lines[a:b])), "chars")
```

This tells you exactly how many lines fit under the ~100K spill threshold so each `read_file`
stays a clean, non-spilling read. Aim for 30–60K chars per chunk.

### 3. read_file by section, not by raw offset guessing

`read_file` uses **1-indexed** offsets; the `execute_code` `lines` list is **0-indexed**. So raw
line `245` = `read_file offset=246`. Read only the sections that matter; skip footnotes,
appendixes, and boilerplate unless the user asks.

## Why this beats alternatives

- **Full read_file** → spills to JSON, loses line numbers, floods context.
- **web_extract head+tail only** → you miss the middle 90% where the argument lives.
- **Outline-first** → you know the document's skeleton before spending a token on prose, and
  you read the 3 sections that matter instead of all 1000 lines.

## Worked example (encyclical, 2026-09-08)

Pope Leo XIV's *Magnifica Humanitas* (264K chars, 1005 lines) was saved to
`~/.hermes/cache/web/www.vatican.va-5a1ada1138.md`. Outline pass found the 5 chapters +
subsections in one `execute_code` call; section char-count pass showed each chapter ≈38–57K
chars; then four targeted `read_file` calls (offset 30/139/246/342/464, each ≤ ~150 lines)
covered the whole thing with zero spills and zero wasted tokens on the footnote apparatus.

## Pitfalls

- **Don't re-request the remote page after a spill.** The full text is already on disk; the
  spillover file (`call_*.txt`) is a JSON-wrapped copy, not the source. Read the original cache
  file with offset/limit instead.
- **Line-index drift:** cache file lines are 0-indexed in Python, 1-indexed in `read_file`.
  Off by one on a 1000-line doc silently lands you on the wrong paragraph.
- **Heading markers are site-specific.** Bold markers (`**`, `***`) and ALL-CAPS lines cover
  most markdown extractions; numbered documents add `^\d{1,3}\.\s`. If your outline looks empty,
  print the first 30 non-empty lines raw and eyeball the actual markers before guessing.
