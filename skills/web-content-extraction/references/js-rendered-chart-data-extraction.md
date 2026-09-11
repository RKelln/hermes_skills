# Extracting charts from JS-rendered pages (the figure that isn't an image)

**Verified 2026-09-10** on OpenAI's "Research acceleration: The view inside OpenAI"
(`openai.com/index/research-acceleration-view-inside-openai/`). The post's load-bearing
figure — the one showing a safety restriction moving compute rather than reducing it —
was an inline Vega-Lite chart. There was:

- no `<img>`, no PNG, no CDN asset (grep of `images.ctfassets.net` returned only OG/social
  cards — a false lead worth knowing about),
- no trace in the text extraction (`webx`, trafilatura, `web_extract` all returned clean
  prose with the figure simply absent),
- but a complete copy of the chart's **underlying data series in the page's JS payload**.

Text extractors drop figures silently. Nothing errors. The extracted markdown reads
fine and is incomplete. So an article whose argument says "as shown below" or "the plot
above" can hand you a raw source that is missing its own evidence.

## When to suspect it

Run this whenever the extracted prose points at a figure:

```bash
grep -nE 'as shown below|the plot above|shown here|see the chart|figure [0-9]' page.md
```

If the prose references a chart and the extracted markdown has no `![`, no `[IMAGE:`,
and no image URL near that sentence, the figure was dropped. (Note: `web_extract` is
documented to emit `[IMAGE: alt]` placeholders — if even those are absent, the figure
was never in the DOM as an image.)

## Recipe

### 1. Get the full page HTML — plain curl may not be enough

```bash
curl -sL "<URL>" -o page.html; wc -c page.html
```

If that returns a small file (~10KB) with a Cloudflare challenge body
(`Enable JavaScript and cookies to continue`, `__CF$cv$params`, a `<meta refresh>`),
you have the challenge page, not the article. Re-fetch impersonating Chrome:

```bash
uvx curl-cffi get "<URL>" --impersonate chrome --body > page.html
wc -c page.html   # verified: 9,842 bytes → 2,296,823 bytes on the same URL
```

This is the same `curl-cffi --impersonate chrome` rescue `webx` uses internally — here it
is needed for the *raw HTML*, because the chart payload is in the framework bundle and
`webx` has already thrown that away by the time it hands you markdown.

### 2. Confirm a chart exists and learn its shape from its own strings

Chart *titles*, axis titles, and legend labels usually survive as plain strings in the
payload even though the drawing does not. Grep for them:

```bash
grep -oE '(?:alt|title|caption)"?\s*:\s*"[^"]{4,160}"' page.html | sort -u
```

On the verified case this surfaced the chart's real title and axes —
`Relative GPU allocation (Jul 1-Aug 15 daily peak = 100%)`, `Compute class`,
`Relative GPU allocation (%)`, `Total relative GPU allocation (%)` — plus the sibling
charts on the page. That is enough to know what figure you are looking for and to cite
its exact title.

### 3. Extract the data array

The payload is a JS literal, not JSON, so unescape first, then locate a column name you
learned in step 2, then depth-count brackets to lift the array out:

```python
import re, json, pathlib
t = pathlib.Path('page.html').read_text(encoding='utf-8', errors='replace')
u = t.replace('\\u002F', '/').replace('\\"', '"').replace('\\\\n', '\n').replace('\\\\', '\\')

key = 'astra_before_restrictions_pct'      # a column name from the chart spec
i = u.find(key)
start = u.rfind('[', 0, i)                 # the array that holds these objects
depth = 0
for j in range(start, len(u)):
    if u[j] == '[': depth += 1
    elif u[j] == ']':
        depth -= 1
        if depth == 0:
            end = j + 1; break
rows = json.loads(u[start:end])            # 34 daily rows with all series
```

Bracket-depth counting (rather than a regex) is what makes this robust — the array
contains nested objects and the payload escapes everything, so a non-greedy regex
stops in the wrong place.

### 4. Verify before using, and record the gap

Save the rows to CSV beside the chart, then **re-derive any percentage the source states
in prose**. On the verified case the post said Astra-class fell 59.2% and other classes
rose 17.2%; reconstructing the same week from the published data (Aug 1–6 vs Aug 8–15)
gave −54.3% and +22.6%, with the total up 4.1% rather than flat. Direction and magnitude
agreed; the decimals did not, and the source does not publish its comparison window.

That gap is the deliverable. Report it as: *their numbers are theirs; here is what the
published data reproduces.* Never silently substitute your reconstruction for their
quoted figure, and never present your reconstruction as a correction unless you can
name the window they used.

## False leads

- **`images.ctfassets.net` / CDN grep hits are usually not charts.** On the verified page
  all four hits were social-share cards (`SEO_Card__11_.png`, `navier-stokes-art-card.png`)
  and the `srcset` widths of the same assets. Dedupe by asset ID, not URL, or the width
  variants read as ~8 distinct figures.
- **`<svg>` count is not a signal.** The page had 38 `<svg>` tags and none was the chart —
  they were icons. Vega-Lite draws to canvas/SVG at runtime from the spec, so the DOM
  holds the *spec*, not the drawing.

## Storing the result

This is extracted source data, so it belongs with the deck artifacts and the receipts:
CSV + the build script + the rendered PNG in the deck's media tree, with the extraction
date noted. The source publishes no image, so there is nothing to reuse and nothing to
license — but the data is theirs, so label whose arithmetic is whose on the chart face
and in the receipt (see the `data-viz-with-receipts` skill).
