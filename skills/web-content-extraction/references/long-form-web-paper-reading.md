# Reading Long-Form Web-Native Research Papers (Transformer Circuits style)

Some research venues publish papers as **long-form web pages** rather than PDFs:
- **Transformer Circuits** (`transformer-circuits.pub`) — Anthropic's interpretability venue
- **Distill** (`distill.pub`) — similar interactive papers
- Some arXiv HTML papers, project pages with embedded results

These are **not** PDFs — they're JS-rendered, multi-section documents with:
- 50K-200K+ characters of text
- Interactive visualizations (the figures won't survive text extraction, but the surrounding text is complete)
- Section headers, inline equations, code blocks embedded in HTML
- Bot detection / Cloudflare on the primary domain (Anthropic.com)

## Workflow

### 1. Skip web_extract — it won't help

`web_extract` on Anthropic.com or similar JS-heavy venues returns bot-detection errors. The ddgs backend is search-only anyway. Go directly to browser.

### 2. Navigate with browser

```python
browser_navigate(url)
```

Check `success` — if the page says "This page couldn't load" (bot detection), the actual paper may be hosted on a subdomain (e.g., `transformer-circuits.pub`). Search for the paper title to find the real venue.

### 3. Try full snapshot first

```python
browser_snapshot(full=True)
```

For transformer-circuits papers, this usually succeeds in loading but the output gets truncated at ~19K lines. The paper *is there* — you just can't read it all in one snapshot.

### 4. Read via browser_console text chunks

Use `browser_console(expression=...)` with `document.body.innerText.slice()` to read the paper in controlled chunks:

```python
# First chunk: introduction + methods
contents = browser_console(expression="document.body.innerText.slice(0, 8000)")

# Subsequent chunks: scroll forward through the paper
# Typical chunk sizes: 8,000-12,000 chars per call
# A 220K-char paper needs ~18-25 chunk reads
contents = browser_console(expression="document.body.innerText.slice(8000, 16000)")
contents = browser_console(expression="document.body.innerText.slice(16000, 24000)")
# ... continue until you reach the end
```

### 5. Target key sections (faster approach)

Instead of reading the entire paper linearly, you can target specific sections:

```javascript
// Find where a specific section starts
document.body.innerText.indexOf("5Using the J-lens for alignment auditing")
// Returns character offset ~150000 — start reading from there
```

Then read from that offset:

```python
browser_console(expression="document.body.innerText.slice(150000, 162000)")
```

### 6. Don't try to preserve interactive figures

The interactive visualizations (clickable heatmaps, hoverable tables, slider controls) are implemented in JavaScript/React on the page. They do not survive text extraction. **Do not try to capture them** — the text content (section prose, figure captions, example annotations) is the primary source. The paper's authors wrote the text to be self-contained; the interactives are supplementary exploration tools.

If a figure is essential and you need to see it, use `browser_get_images()` to find image URLs, or describe what the snapshot shows (e.g., "A heatmap with three panels showing layer-by-layer activation of tokens at each position"). If the text references a figure by number and you can't see it, say so — don't fabricate figure content.

## Typical reading budget

| Paper length | Chunks needed | Time estimate |
|---|---|---|
| Short (~50K chars) | 5-7 chunks | Quick read |
| Medium (~120K chars) | 10-15 chunks | Moderate |
| Long (~220K chars) | 18-25 chunks | Heavy — plan this |

For **long papers** (~220K chars), concentrate on the sections most relevant to the user's request: abstract + introduction, key methods, results, and discussion. Skip appendices unless the user asks about them.

## Pitfalls

- **The browser_console slice method returns the FULL rendered text of a section of the DOM.** It does not parse markdown, extract equations, or capture figure images. What you get is raw text (not HTML, not markdown). That's fine for LLM consumption — it's already much leaner than HTML.
- **Figures described as "[IMAGE: ...]" in the snapshot are NOT accessible via text extraction.** The interactive visualizations in transformer-circuits papers are `<canvas>` elements annotated with SVG overlays. They render differently each time. Don't try to describe what the figure *shows* from the snapshot alone — if you need to understand a figure, navigate the paper with browser tools and use `browser_snapshot` at the figure position to get the accessibility tree description.
- **Don't save the full paper text to disk during reading.** Unlike PDFs (which you save as permanent references), web-native papers are always accessible at their URL. Save only your analysis notes. The raw extracted text is transient — you'll re-extract if you need to revisit.
- **The page may lazy-load content on scroll.** If you hit a section that seems empty or truncated in the text, scroll down (`browser_scroll(direction='down')`) before the console query. Some sections trigger rendering only when scrolled into view.
- **Equations are rendered as SVG/MathML** in transformer-circuits papers. In the extracted text, they appear as raw Unicode or collapsed. Don't worry about this — the prose surrounding them carries the meaning. If an equation reference is critical (e.g., "the J-space is defined as the set..."), the paragraph text will describe it.
- **Code blocks are plain text** in the HTML and survive extraction fine. You can copy them from the browser_console output.
