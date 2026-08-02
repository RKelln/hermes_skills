# Next.js / Client-Side Rendered Blog Extraction

When a page is built with Next.js (or similar SSR frameworks) and the article body is rendered client-side, **neither `web_extract` nor `trafilatura` can extract the content** — the static HTML only contains navigation shell, `<script>` tags, and a `<div id="__next">` that gets populated by JavaScript after page load.

## Recognizing a Next.js CSR page

- Page source has `<div id="__next">` as a near-empty shell
- Content only appears when JavaScript executes
- `curl` may return a 404 page even though the browser shows it fine (SSG build didn't include this path)
- The `__NEXT_DATA__` JSON script tag exists but only holds page metadata, NOT body content

## Three extraction strategies (in order)

### Strategy A: Find the content elsewhere (fastest)

Lab blog posts (Kyutai, Anthropic, etc.) are often duplicated:

1. **GitHub README** — Search `github.com/<org>/<repo>` for the project README
2. **Technical report page** — separate route on the same domain (e.g. `/pocket-tts-technical-report/`)
3. **arXiv paper** — if backed by a published paper
4. **Third-party coverage** — Grokipedia, Towards AI, BrightCoding etc.

### Strategy B: Try the Next.js data route

```
BUILD_ID=$(python3 -c "
import json, re
with open('/tmp/page.html') as f:
    m = re.search(r'<script id=\"__NEXT_DATA__\" type=\"application/json\">(.*?)</script>', f.read(), re.DOTALL)
    if m:
        data = json.loads(m.group(1))
        print(data.get('buildId', ''))
")
curl -sL "https://<domain>/_next/data/$BUILD_ID/<slug>.json" -o /tmp/next-data.json
```

Often returns metadata only — if so, fall to Strategy C immediately.

### Strategy C: Browser tool (content rendered by JS)

```
browser_navigate(url)
browser_console(expression='document.body.innerText')
```

See `browser-content-extraction` reference for the full pattern.

## What NOT to do

- Do NOT grep for content in raw HTML — it's not there
- Do NOT use trafilatura on CSR pages — returns 0 bytes
- Do NOT try multiple curl approaches on the same URL — if it's CSR, no curl variant works

## Worked example: Kyutai Pocket TTS (July 2026)

`kyutai.org/blog/2026-01-13-pocket-tts/`:
- `curl -sL` → 404 (SSG didn't include it)
- `curl-cffi --impersonate chrome` → shell with metadata only
- `trafilatura` → 0 bytes
- `_next/data/` JSON → metadata only
- **Working:** GitHub README (15KB) + technical report page + arXiv paper
