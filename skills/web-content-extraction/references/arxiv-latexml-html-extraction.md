# LaTeXML arXiv HTML Extraction (Math-Heavy Papers)

> Technique developed 2026-08-21 on arXiv:2608.19013 (math-heavy cs.LG paper). Use when `webx`/trafilatura don't apply (raw arXiv HTML), the PDF is wanted only as fallback, and you need the full body as readable prose.

## Problem

`arxiv.org/html/<id>` pages are LaTeXML-rendered. A naive tag-strip produces:

1. **Per-line span fragmentation** — every word and math span on its own line (LaTeXML wraps tokens in spans), so the text reads as a vertical list of fragments with `\theta`-style math interleaved.
2. **TOC/body double markers** — every section heading appears TWICE: once in the nav TOC near the top, once at the actual body position. Slicing on the first occurrence gets you the TOC, not the section.
3. `<script>/<style>` noise — hundreds of lines of embedded JS/CSS if not removed first.

## Recipe

```python
import re, html

with open('paper.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 0. Strip script/style blocks FIRST (they dominate the noise)
content = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', content, flags=re.DOTALL|re.IGNORECASE)
# 1. Tag-strip, then unescape entities (or &lt; &amp; etc. mangle words)
text = html.unescape(re.sub(r'<[^>]+>', '\n', content))
# 2. Flatten: collapse the per-line fragments into continuous prose
flat = re.sub(r'\n\s*\n+', '\n\n', text)   # keep paragraph breaks first if you want them
prose = re.sub(r'\s+', ' ', flat)          # then flatten for section slicing

# 3. Slice sections by the SECOND occurrence of each marker
def all_pos(s, marker):
    return [m.start() for m in re.finditer(re.escape(marker), s)]

def section(prose, start_marker, end_marker):
    starts = all_pos(prose, start_marker)
    ends = all_pos(prose, end_marker)
    assert len(starts) >= 2, f"marker '{start_marker}' found {len(starts)}x — expected TOC + body"
    assert len(ends) >= 2, f"marker '{end_marker}' found {len(ends)}x — expected TOC + body"
    return prose[starts[1]:ends[1]]

sec = section(prose, '3.2 Harness State', '3.4 Connections')
```

## Verification

- Check `len(all_pos(...)) >= 2` per marker before assuming the second hit is the body — on 2608.19013 this held for every section marker (TOC at ~pos 100-800, body at ~15K+).
- File size sanity: a ~330KB HTML paper yields ~83KB of cleaned text.
- If a section slice comes back empty or wrong, print the positions and inspect — the TOC may be absent on some papers (then `starts[0]` IS the body and the guard catches it).
- The flattened prose is also the right input if you later compute a stable hash of the extraction (e.g. raw-sha256 on a `.txt` companion — though papers' raw source is the PDF; see wiki-maintenance raw-layer notes).

## Alternative: PDF extraction

If the HTML is unavailable or you want tables/figures: `curl -sL https://arxiv.org/pdf/<ID> -o paper.pdf`, verify `file` says PDF, then `pdftotext -layout paper.pdf -`. For control-char ligature cleanup on extracted PDF text see `references/pdftotext-ligature-cleanup.md` in this skill.
