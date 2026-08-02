# Starlight / Docusaurus Documentation Site Extraction

Extracted from a session exploring LiteParse docs at `developers.llamaindex.ai/liteparse/` (2026-06-21).

## The Problem

Documentation sites built with Starlight (Astro), Docusaurus (React), or similar static-site frameworks:
- Use **nested sidebar navigation** that isn't visible in the page HTML as `<a>` tags — refs are only in the accessibility tree as `link` elements with text but no href visible in `browser_snapshot`
- Have **tabbed code samples** (Python/TypeScript/Rust tabs) — only the active tab's content is in the DOM
- Return **truncated snapshot content** — the browser's accessibility tree snippet summarises long content
- `web_extract()` with ddgs backend fails entirely

## Technique: Extract sidebar links for targeted navigation

After `browser_navigate(url)`, use `browser_console` to dump all sidebar links with their hrefs:

```javascript
// Extract all nav links under the sidebar/main nav
JSON.stringify(
  Array.from(document.querySelectorAll('nav a[href*="/liteparse/"]'))
    .map(a => ({text: a.textContent.trim(), href: a.getAttribute('href')}))
)

// Or broader — all nav links
JSON.stringify(
  Array.from(document.querySelectorAll('nav a[href^="/"]'))
    .map(a => ({text: a.textContent.trim(), href: a.getAttribute('href')}))
)
```

This reveals the actual URL paths (e.g., `/liteparse/guides/library-usage/`, not just "Library Usage" text).

## Technique: Navigate tabbed code samples

Starlight/Docusaurus use `[role=tab]` elements. Click the tab you need:

```javascript
// Check available tabs
Array.from(document.querySelectorAll('[role=tab]')).map(t => t.textContent.trim())

// Click a specific tab by text (not ref ID)
document.querySelector('[role=tab]:nth-child(2)').click()
```

Or use the browser tool's click by ref: `browser_navigate → browser_snapshot → browser_click(ref)`.

After clicking, call `browser_snapshot(full=true)` to capture the newly-revealed tab panel content.

## Technique: Bullet-Proof Full Page Content

When the snapshot truncates or overlays hide content, extract everything via DOM:

```javascript
// Full rendered text — includes everything in the viewport
document.body.innerText

// Or targeted: the docs article body (Starlight convention)
document.querySelector('main')?.innerText || document.body.innerText

// Get all <p> and <li> and <code> content joined cleanly
Array.from(document.querySelectorAll('main p, main li, main code, main h1, main h2, main h3'))
  .map(el => el.textContent)
  .join('\n')
```

## How This Session Used It

1. `browser_navigate` → got overview, but sidebar links had no href in snapshot
2. `browser_console` with `querySelectorAll('nav a[href*="/liteparse/"]')` → got all real URLs
3. Navigated to each guide page directly
4. On each page: clicked Python tab → `browser_snapshot(full=true)` → read content
5. Extracted full Python code samples from the revealed tab panels
