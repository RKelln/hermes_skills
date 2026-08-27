# Hacker News Thread Extraction + Bot-Blocked Primary Fallback

Verified 2026-08-25 on the Anna's Archive book-destruction story (HN item 49383026, 645 pts, 901 comments).

## HN threads via the Algolia items API

HN pages are JS-heavy and the comment tree doesn't render in static HTML. The Algolia items API returns the ENTIRE comment tree in one JSON document:

```bash
curl -sL "https://hn.algolia.com/api/v1/items/49383026" -o .tmp/hn-49383026.json   # download first, never pipe
```

The story item carries: `title`, `author`, `points`, `url` (often the PRIMARY SOURCE — follow it), `num_comments`. Then walk the tree locally:

```python
import json
d = json.load(open('hn-49383026.json'))
comments = []
def walk(node, depth=0):
    if node.get('type') == 'comment':
        comments.append({'author': node.get('author'),
                         'points': node.get('points') or 0,
                         'text': (node.get('text') or '')[:1200],
                         'depth': depth})
    for c in node.get('children', []):
        walk(c, depth + 1)
walk(d)
```

## Pitfalls

- **The items API does NOT include comment points** — every comment comes back points-less/0. You cannot rank comments by score from this API. Instead: identify the named commenters from secondary coverage (articles quoting the thread), pull their exchanges by author, and read the reply chains — the substance lives in the back-and-forth (worked: the tptacek/runarberg "dead stock vs unknowable rarity" exchange WAS the balance of the story).
- **Comment text is HTML-escaped** (`&#x27;` = apostrophe, `<p>` tags) — unescape before quoting into notes.
- **The story's `url` field is frequently the original source** (HN is a link aggregator) — the Anna's Archive HN post pointed at the primary post on annas-archive.gl, which was otherwise hard to find.

## Bot-blocked primary → labeled secondary raws

When the primary source refuses extraction (webx: "no credible extraction" on 404media.co; web_extract returned only a thin head-only slice on Tom's Hardware; browser tool unavailable because Chrome isn't running):

1. **Retry the same URL with the webx CLI before concluding anything** — `web_extract` can return a thin head-only slice (headline + first pull-quote) and report SUCCESS. `webx <URL> --out <file>` got the full 9.5K-char article where web_extract gave ~450 chars. Check output size; if suspiciously short for the article, retry with webx.
2. **Mirror-hunt via web_search** — search the story's distinctive phrases plus the outlet name ("404media.co tracked shipment rare books Amazon AI facility"). Aggregators and re-publishers (temperature2, metatalks, gigazine, uniladtech), LinkedIn posts of the article, and secondary outlets quoting it carry the facts.
3. **Build ONE combined secondary raw** — frontmatter `source_url:` lists primary + mirrors; body starts with a label: "Secondary sources — not the primary text. Original: <URL>". Save under raw/articles/ with the usual sha256 flow. Never present mirror text as the primary's.
4. **Record the access limitation in the research note's Open questions** ("original bot-blocked from this box; re-extract when Chrome is available") so a future session knows the gap and can close it.
