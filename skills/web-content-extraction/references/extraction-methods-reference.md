# Web Content Extraction Methods — Reference

Detailed extraction methods that live on-demand. Load via `skill_view` when needed.

## Method 2: html2text (local, free, no API)

For static HTML pages not behind Cloudflare's feature. **Never pipe curl into Python.** Always download first, then process from a local file.

```bash
pip install html2text

# SAFE: pre-scan, download to file first, then parse
tirith run --no-exec "https://example.com/page"
curl -s https://example.com/page -o /tmp/page.html
python3 -m html2text /tmp/page.html

# SAFE: ignore links, after pre-scan
curl -s https://example.com/page -o /tmp/page.html
python3 -m html2text --ignore-links /tmp/page.html
```

Limitations: Cannot handle JavaScript-rendered content. Only works if `curl` gets the real content.

**Installation gotcha in Hermes venv:** The bundled Hermes venv at `~/.hermes/hermes-agent/venv/` may not have pip installed. Bootstrap it first:
```bash
~/.hermes/hermes-agent/venv/bin/python -m ensurepip --upgrade
~/.hermes/hermes-agent/venv/bin/python -m pip install html2text
```
To use from anywhere, run via the Hermes Python on a local file:
```bash
curl -s https://example.com/page -o /tmp/page.html
~/.hermes/hermes-agent/venv/bin/python -m html2text /tmp/page.html
```

## Method 3: Firecrawl CLI

Runs a headless browser, handles JS rendering, strips navigation/footers/cookie banners, returns clean markdown. Requires a Firecrawl API key (free tier: 1,000 credits/month).

```bash
# Install
npx -y firecrawl-cli@latest init --all --browser

# Scrape single URL to markdown
npx -y firecrawl-cli@latest scrape https://example.com --format markdown

# Search + scrape results
npx -y firecrawl-cli@latest search "query" --limit 5 --scrape --scrape-formats markdown

# Parse local files (HTML, PDF, DOCX) to markdown
npx -y firecrawl-cli@latest parse ./page.html --format markdown
```

## Method 5: Curl-Based Search + Extraction

When search engines block the browser with captchas, use the safe three-step pattern: scan, download to file, then parse locally.

### Step 1: Search via DuckDuckGo HTML

```bash
# SAFE: scan, download, then parse locally
tirith run --no-exec "https://html.duckduckgo.com/html?q=YOUR+SEARCH+QUERY"

SEARCH_RESULTS="/tmp/ddg_results.html"
curl -sL "https://html.duckduckgo.com/html?q=YOUR+SEARCH+QUERY" \
  -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0" \
  -H "Accept: text/html" \
  -o "$SEARCH_RESULTS"
```

### Step 2: Parse the local file

Use the reusable `parse_duck.py` script (bundled with the `duck-search` skill):
```bash
python3 ~/.hermes/skills/research/duck-search/scripts/parse_duck.py /tmp/ddg_results.html
```
Outputs JSON array of `{title, url, snippet}`. No network calls, reads from disk only.

### Step 3: Read individual articles

Same safety-first approach — tirith scan, download to file, never pipe:

```bash
# SAFE: static page, pre-scan then download then html2text
tirith run --no-exec https://target-url.com/article
curl -sL https://target-url.com/article -o /tmp/article.html
python3 -m html2text /tmp/article.html

# SAFE: Cloudflare-hosted, try markdown endpoint
tirith run --no-exec https://target-url.com/article
curl -H "Accept: text/markdown" https://target-url.com/article -o /tmp/article.md
cat /tmp/article.md

# JS-heavy -> browser tool (inherently safe, no pipes)
browser_navigate(url)
browser_snapshot(full=true)
```

### Escalation Decision Flow

```
Need to search the web?
-> Did the browser tool load a search engine?
   YES -> Use browser search as usual
   NO  -> (captcha/block) -> tirith + curl -o DDG HTML (Method 5)
   Also blocked? -> Wayback Machine search (Method 6)

Found search results, need full article content?
-> Is the target URL static HTML?
   YES -> curl -o + html2text (Method 2)
   NO  -> browser_navigate + browser_snapshot (Method 4)
   -> On Cloudflare? Try Accept: text/markdown first (Method 1)
   -> Cloudflare or login blocks both curl and browser?
      -> Wayback Machine archived copy (Method 6)
```

## Method 6: Wayback Machine (fallback)

When the target site returns a Cloudflare challenge, login wall, paywall, or JS-loaded content that won't render in curl or the browser tool, check the Internet Archive's Wayback Machine.

```bash
# Navigate to a specific archived snapshot
browser_navigate("https://web.archive.org/web/20260313020031/https://example.com/page")

# Or search the Wayback Machine for available snapshots
browser_navigate("https://web.archive.org/web/*/https://example.com/page")
```

**Limitations:** Only available for pages that have been crawled. Recent pages may have no snapshots.

## Method 7: BeautifulSoup Targeted Extraction (CMS listing pages)

When `trafilatura` or `html2text` fail on card-based CMS layouts (Webflow, Squarespace, WordPress listing pages), and the site serves static HTML (no JS rendering needed), write a targeted BeautifulSoup script.

### Pattern

1. **Study the structure** — use `browser_navigate` + `browser_snapshot` to read the accessibility tree
2. **Identify CSS class patterns** — Webflow sites use predictable classes
3. **Write a targeted script** — ~60 lines, requests + BeautifulSoup, extract by class
4. **Output structured markdown** — one `###` per card

### Sitemap-based discovery (Webflow and most CMS platforms)

Listing-page card scraping only catches featured items. Webflow and most CMS platforms auto-generate `sitemap.xml` with the full inventory. Parse with `xml.etree.ElementTree`.

### Key pitfalls in targeted extraction

- **CMS h3 elements may be empty in static HTML** — fall back to `img.get('alt')`
- **BeautifulSoup `class_` filter does substring matching** — use lambda to avoid BEM-style duplicates
- **URL resolution** — resolve absolute paths against base URL

### Example: InterAccess scraper

See `references/interaccess-scraper.py` for a complete working example handling three page types (standard detail, VF microsite, listing).

### Incremental sync with change detection (cron-ready)

For recurring scraping, use manifest-based sync: sitemap diff → HTTP HEAD checks → content hash verification. See `references/last-sync-schema.md`.

### Markdown normalization for stable hashing

Before hashing scraped content, normalize: strip HTML comment headers, collapse blank lines, fix double-encoding artifacts. See the full normalization function in `references/utf8-double-encoding-artifacts.md`.

## Method 8: Wikipedia API

For encyclopedic/historical/conceptual research, Wikipedia's JSON API returns clean plain text.

```bash
curl -sL "https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext&titles=Neo-Luddism&format=json" -o /tmp/wiki.json
python3 -c "
import json
with open('/tmp/wiki.json') as f:
    data = json.load(f)
pages = data['query']['pages']
for pid, page in pages.items():
    print(page.get('extract', 'No extract'))
"
```

See `references/wikipedia-api-extraction.md` for full parameter reference.

## Long-Form Web-Native Research Papers

Transformer Circuits / Distill style papers need chunk-reading via browser_console. See `references/long-form-web-paper-reading.md`.

## Documentation Sites (Starlight/Docusaurus)

Use browser_console to extract sidebar links and switch code-sample tabs. See `references/starlight-docs-extraction.md`.

## Web Provider Config

```yaml
web:
  backend: ddgs
  search_backend: ddgs
  extract_backend: ddgs
```

Available backends: `ddgs`, `brave_free`, `searxng`, `firecrawl`, `tavily`, `exa`, `xai`.
