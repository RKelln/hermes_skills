# Wikipedia API Extraction

A safe, structured alternative to scraping Wikipedia's HTML pages. The JSON API returns clean plain text without navigation, sidebars, or bot-detection overhead.

## When to use

- Researching a concept, movement, historical event, or biography
- Wikipedia is the best open-source reference for term definitions
- You want clean text without extracting HTML (avoiding `browser_navigate` bot detection on Wikipedia)
- The information is factual/historical — not time-sensitive breaking news

## Method: JSON API (safe, structured)

**Safety:** This method uses `curl -o` (download to file) then parses the local JSON. No pipe-to-interpreter pattern.

```bash
# Step 1: Download the JSON response to a file
curl -sL "https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext&titles=Neo-Luddism&format=json" -o /tmp/wiki.json

# Step 2: Parse the local file for the extract
python3 -c "
import json
with open('/tmp/wiki.json') as f:
    data = json.load(f)
pages = data['query']['pages']
for pid, page in pages.items():
    print(page.get('extract', 'No extract'))
"
```

## Key Parameters

| Parameter | Value | Effect |
|-----------|-------|--------|
| `action` | `query` | Standard read query |
| `prop` | `extracts` | Returns plain text extract of the article |
| `explaintext` | (presence) | Strips HTML, returns plain text. Omit for limited HTML |
| `titles` | Page title | URL-encode spaces as `_`. Use `%7C` (pipe) for multiple: `Title1%7CTitle2` |
| `format` | `json` | Returns structured JSON |

## Working with Multiple Pages

Request several titles at once (free, fast):

```bash
curl -sL "https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exlimit=5&explaintext&titles=Neo-Luddism%7CLuddite%7CUnabomber&format=json" -o /tmp/wiki.json
```

The `exlimit` parameter controls how many extracts to return (default 1, max 20 for non-bots). Each page appears as a key in the `pages` dict keyed by page ID.

## Getting the Full Article (Beyond the Intro)

The default extract returns only the lead section (intro paragraph). For the full article, you need `exintro=false` (or omit it) and fetch sections separately. The better approach for factual research is to rely on the lead section + the `extracts` function with a higher character limit:

```bash
# Get first 10000 chars of the article
curl -sL "https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exlimit=1&explaintext&titles=Neo-Luddism&format=json&exchars=10000" -o /tmp/wiki.json
```

Note: `exchars` and `exintro` are mutually exclusive. If `exintro` is set, `exchars` is ignored and you get the lead only. Omit `exintro` to control length with `exchars`.

## Pitfalls

- **`exchars` + `exintro` conflict.** If you include both `exintro` and `exchars`, the API silently ignores `exchars` and returns only the lead. Omit `exintro` when you want the full article up to `exchars` characters.
- **Max `exlimit` is ~20** for standard API access. For large batch extraction, use `generator=allpages` (different endpoint).
- **Categories, references, and infoboxes are omitted** from the `extracts` output. The JSON API returns a simplified extract. For the full wikitext with all metadata, use `action=parse&prop=text` instead — but that returns HTML, not clean text.
- **Page title case sensitivity.** Wikipedia page titles are case-sensitive except for the first character. "Neo-Luddism" works; "neo-luddism" does not. Use the exact title as it appears in the URL.
- **Rate limits.** Standard Wikipedia API allows ~200 requests/second for read queries. You won't hit this in normal use. Be polite anyway — no tight loops.
- **Cache aggressively.** Write the JSON response to a file and parse from there. Don't re-fetch the same article on every turn.
- **Some topics are very long** (e.g., "Artificial intelligence" is ~150KB+ of text). Use `exchars` to limit the response, or the response will be truncated by the API.
