# curl-cffi + trafilatura Pipeline

Fetch web pages past bot detection and extract clean markdown, no browser needed.

## Quick Reference

```bash
# Safe two-step — download first, then extract (always use this)
uvx curl-cffi get <URL> --impersonate chrome --body > /tmp/page.html
wc -c /tmp/page.html  # confirm download succeeded
uvx trafilatura -i /tmp/page.html --output-format markdown

# Save output to file
uvx curl-cffi get <URL> --impersonate chrome --body > /tmp/page.html
wc -c /tmp/page.html
uvx trafilatura -i /tmp/page.html --output-format markdown -o /tmp/article.md
```

**Never pipe curl-cffi output directly into trafilatura or any other tool.** Always download to file first. This is both a security rule (no pipe-from-network) and a reliability practice (you can verify the download succeeded before processing).

## When to use which

| Situation | Command |
|-----------|---------|
| Bot-protected article | `uvx curl-cffi get URL --body > /tmp/p.html && trafilatura -i /tmp/p.html` |
| API, raw file, GitHub raw, PDF | `curl -sL -o /tmp/file URL` (stable endpoints, no bot detection) |

## Real test: Anthropic research page (blocked curl, worked with curl-cffi)

The page `https://www.anthropic.com/research/global-workspace` blocks bare curl
and the browser tool. curl-cffi bypassed it, trafilatura extracted clean markdown:

```bash
uvx curl-cffi get "https://www.anthropic.com/research/global-workspace" \
  --impersonate chrome --body > /tmp/page.html
wc -c /tmp/page.html  # verify download
uvx trafilatura -i /tmp/page.html --output-format markdown
```

Result: 215KB HTML → clean markdown of the full article text. No nav, no SVG
logos, no JS bundles, no SVG icons embedded in the output.

## Impersonation targets

`--impersonate chrome` is the default. Also available:

- `--impersonate chrome131` — specific version
- `--impersonate firefox` — fallback if Chrome fingerprint is blocked
- `--impersonate safari` — for sites that check Safari specifically

## When trafilatura returns near-empty output

Trafilatura's boilerplate detection fails on card-based CMS layouts (Webflow,
Squarespace, WordPress listing pages). If output is <200 chars and the page
has visible content, fall back to:

1. Browser tool (Method 4 in the skill)
2. BeautifulSoup targeted extraction (Method 7)

## Dependencies

- `curl-cffi` — ~10MB first install via uvx, cached after
- `trafilatura` — ~2MB, 17 packages, installs in ~23ms via uvx
- Both run via `uvx`, no permanent installation needed
