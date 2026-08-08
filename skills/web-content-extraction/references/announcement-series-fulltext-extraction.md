# Full prose from announcement / series landing sites

Announcement and "series" landing pages (Ghost/Next.js marketing sites) are built for human
eyeballs and hide the real prose. Two common failure modes, both hit together on
ii.inc/common-wealth (7 Aug 2026):

1. `webx` / trafilatura return only the announcement blurbs (a few KB) even though the page
   HTTP 200s with real content.
2. The actual full text lives *behind* per-work landing pages, each with a PDF behind a
   "Read" link — the landing pages only carry key-concept summaries.

The fix is a three-part recipe. Always download-to-file first (never pipe from network).

## A. Prose buried in `__NEXT_DATA__` → `mdxSource.compiledSource`

Ghost serves client-rendered MDX. The page's readable prose lives inside
`props.pageProps.mdxSource.compiledSource` as JS string literals.

```bash
curl -sL URL -o page.html            # HTTP 200, real body
grep -c __NEXT_DATA__ page.html      # expect >= 1
```

```python
import json, re
html = open('page.html', encoding='utf-8', errors='replace').read()
m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
data = json.loads(m.group(1))
src = data['props']['pageProps']['mdxSource']['compiledSource']
strings = re.findall(r'"((?:[^"\\]|\\.)*)"', src)
seen, out = set(), []
for s in strings:
    s = s.encode().decode('unicode_escape', errors='replace')
    if s in seen: continue
    seen.add(s)
    if len(s.strip()) >= 25 and not s.strip().startswith(('_', 'const', '{', 'function',
        'useMDX', 'components', 'props', 'children')):
        out.append(s.strip())
print("\n\n".join(out))               # the readable prose
```

This recovered the full announcement + closing argument where trafilatura/webx only got the
headline blurbs.

## B. Full text behind per-work PDF "Read" links

The series overview lists works but the *text* is on per-work pages / PDFs. Probe the asset
structure:

```python
import re
hrefs = re.findall(r'href="([^"]+)"', html)
for h in dict.fromkeys(hrefs):
    lh = h.lower()
    if any(k in lh for k in ['pdf','read','personhood','economics','last-court','last-republic',
        'webstatics','/media','download']):
        print(h)
```

For cw.ii.inc the PDFs lived on a static CDN with a clean slug pattern:
`https://webstatics.ii.inc/microsites/common-wealth/pdfs/<slug>.pdf`
(one of `personhood`, `intelligent-economics`, `the-last-court`, `the-last-republic`).
Once you see one PDF path, the sibling slugs usually follow the naming pattern. Verify each
download with `file x.pdf` and check it's a real PDF (not an interstitial page).

## C. PDF → clean agent-readable markdown (ligature fix)

`pdftotext -layout` on these papers emits font control-char ligatures instead of the letters
(`\x1c`=fi, `\x1d`=fl, `\x1b`=ff; `\x10`/`\x11`=italic markers; `\x9f`=superscript ref; `\x0c`=page break).
**Full detection-first recipe (inventory controls, verify per-file, cleanup code) is the
standalone reference: `references/pdftotext-ligature-cleanup.md`.** Do not re-derive the mapping
here — load that reference.

Worked example:

```bash
pdftotext -layout paper.pdf paper.txt
```

then clean per the ligature-cleanup reference. Preserves unicode math symbols (µ τ ρ κ Π).
Verify the fix landed by grepping for words containing fi/fl/ff — `grep -i artificial` on
personhood.md should return real hits (17 on the Common Wealth paper).

## Pitfall: these sites are human-only; produce the agent-readable artifact

Ghost/Next.js series sites don't ship a single machine-readable text export. If a request is
"make copies agents can actually read," the deliverable IS the consolidated markdown — save
each work's full text to `raw/common-wealth/*.md` (and the source PDFs under `pdfs/`) and link
them from the research note, rather than stopping at the announcement summary.
