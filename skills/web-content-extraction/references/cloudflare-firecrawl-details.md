# Cloudflare & Firecrawl Details

Discovered 2026-05-30 from conversation about Guelph nature outing → web-to-markdown tool question.

## Cloudflare Markdown for Agents

- Announced 2026-02-12: https://blog.cloudflare.com/markdown-for-agents/
- Auto-converts HTML to markdown at the network edge
- Enabled via Cloudflare dashboard → zone → Quick Actions → toggle
- Beta, free for Pro/Business/Enterprise plans
- Also available via Workers AI `AI.toMarkdown()` and Browser Rendering `/markdown` REST API
- Sends `Content-Signal: ai-train=yes, search=yes, ai-input=yes` header
- Cloudflare Radar now tracks markdown content type in AI Insights

## Firecrawl CLI (v1.18.5)

Blog post: https://www.firecrawl.dev/blog/scrape-a-website-to-markdown (Apr 01, 2026)

Commands:
```bash
# Init (one-time)
npx -y firecrawl-cli@latest init --all --browser

# Scrape
npx -y firecrawl-cli@latest scrape <url> --format markdown
npx -y firecrawl-cli@latest scrape <url> --format markdown,links --pretty

# Search + scrape
npx -y firecrawl-cli@latest search "query" --limit 5 --scrape --scrape-formats markdown

# Parse local files (HTML/PDF/DOCX/ODT/RTF/XLSX/XLS)
npx -y firecrawl-cli@latest parse <file> --format markdown
```

Python SDK example:
```python
from firecrawl import Firecrawl
client = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])
doc = client.scrape("https://example.com", formats=["markdown"], only_main_content=True)
```

Has MCP server for Claude Desktop / Claude Code / Cursor / Windsurf.
Integrated with OpenClaw via `npx clawhub@latest install firecrawl/cli`.

## Firecrawl is the default Hermes web provider

Blog: https://www.firecrawl.dev/blog/hermes-agent (Apr 24, 2026)

Hermes ships with Firecrawl bundled at `plugins/web/firecrawl/provider.py`. It auto-detects on `FIRECRAWL_API_KEY` in `.env` — no config edit needed. Covers search + scrape + crawl (Tavily/Exa are search-only).

## Hermes Web Provider Architecture

Source: `~/.hermes/hermes-agent/plugins/web/`

- `WebSearchProvider` is an ABC in `agent/web_search_provider.py`
- Each backend: `plugins/web/<name>/provider.py`
- Config keys: `web.backend`, `web.search_backend`, `web.extract_backend`
- Set via `hermes config set web.backend <name>` (preferred; direct editing config.yaml may be denied as a protected file)
- Toolset `web` in Hermes uses the configured provider
- When all backends empty (`''`), web tools are unavailable
- Changes need a fresh session (`/reset` or new `hermes` process) to take effect
