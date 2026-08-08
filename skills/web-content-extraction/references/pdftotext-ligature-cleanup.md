# Cleaning `pdftotext` output: ligature & control-character artifacts

When `pdftotext -layout` extracts a paper PDF whose fonts encode ligatures (fi, fl, ff) and
formatting markers as **private-use / control characters**, the extracted text contains stray
control chars that break the "clean agent-readable markdown" goal. Hit 2026-08-07 on the
Common Wealth paper PDFs (Emad Mostaque / ii.inc, at `webstatics.ii.inc/.../pdfs/*.pdf`).

## Symptom

Text reads like `arti\x1ccial` instead of `artificial`, `the \x1door` instead of `the floor`,
`e\x1bort` instead of `effort`. Unicode/Greek math symbols (µ, τ, ρ, κ, Π) survive fine —
only ligatures and markers are mangled.

## First: detect which control chars exist

Don't guess the mapping — inventory them:

```python
t = open('paper.txt', encoding='utf-8', errors='replace').read()
special = {}
for ch in t:
    o = ord(ch)
    if o < 32 or o > 126:
        special[ch] = special.get(ch, 0) + 1
for ch, cnt in sorted(special.items(), key=lambda x: -x[1])[:8]:
    print(f"{ord(ch):#06x} {ch!r} x{cnt}")
```

Then confirm each mapping by reading short contexts around occurrences (a control char in
`arti\x1ccial` ⇒ `\x1c` = "fi"; in `the \x1door` ⇒ `\x1d` = "fl"; in `e\x1bort` ⇒ `\x1b` = "ff").

## Known mapping for the common ligature/marker font case

| Control char | Meaning |
|--------------|---------|
| `\x1c` | "fi" ligature |
| `\x1d` | "fl" ligature |
| `\x1b` | "ff" ligature |
| `\x10` / `\x11` | italic open / close markers (formatting only → drop) |
| `\x9f` | superscript/reference marker (footnote citation numbers → drop) |
| `\x0c` | form feed (page break → replace with blank line) |

**Always verify per-file** — the mapping is a strong default, not a guarantee. Check a handful
of contexts before mass-replacing.

## Cleanup recipe (download-then-process, no network pipes)

```python
import re
LIG = {'\x1c':'fi', '\x1d':'fl', '\x1b':'ff'}
t = open('paper.txt', encoding='utf-8', errors='replace').read()
for k, v in LIG.items():
    t = t.replace(k, v)
t = t.replace('\x10','').replace('\x11','')   # italics markers -> drop
t = t.replace('\x9f','')                       # superscript markers -> drop
t = t.replace('\x0c','\n\n')                   # page break -> blank line
# drop any remaining non-printable control chars (keep \n \t)
t = ''.join(ch if ch in '\n\t' or ord(ch) >= 32 else '' for ch in t)
t = re.sub(r'\n{3,}', '\n\n', t)               # collapse 3+ blank lines to 2
open('paper.md','w',encoding='utf-8').write(t)
# verify: zero leftover control chars
bad = [ch for ch in t if ord(ch) < 32 and ch not in '\n\t']
print("leftover control chars:", len(bad))
```

## Verification

- `leftover control chars: 0` after cleanup
- Spot-check resolved words: `grep -c -i artificial paper.md` should return matches; `floor`,
  `effort` present where expected
- Greek/math symbols (µ τ ρ κ Π) must be preserved — they arrive as proper Unicode and must NOT
  be stripped by the `<32 or >126` filter (they're >126, so they survive)

## General workflow note

The "readable landing page" (series overview) often gives only key-concept blurbs; the actual
prose is in per-work PDFs behind "Read"/"Download" links. If the landing page's structure block
cites PDFs (often under a static CDN like `webstatics.<domain>/microsites/<slug>/pdfs/*.pdf`),
grab those for the full text. Then fan out one subagent per PDF to read and summarize in parallel
rather than reading all ~160-185K chars yourself in-context.
