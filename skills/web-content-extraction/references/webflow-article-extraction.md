# Webflow Article Extraction

**Trigger:** Corporate/startup blog on Webflow — page source contains `data-wf-*` attributes (`data-wf-site`, `data-wf-collection`, `data-wf-item-slug`), article bodies in `<div class="w-richtext ...">` or `blog-post-content` divs.

**When to use:** trafilatura gave 0 bytes or wrong content, OR the `-i` flag was misused (see SKILL.md `-i` pitfall — `-i` reads a URL list, not HTML). For a Webflow ARTICLE page this python slice beats the browser tool: cheaper, no JS overhead, validated on a 150KB page.

## Validated recipe (LangChain blog, 2026-08-09)

Download first (never pipe network to interpreter):

```bash
uvx curl-cffi get "<URL>" --impersonate chrome --body > page.html
```

Verify size with `wc -c page.html` before extracting (LangChain page ≈ 150KB; the article is only ~11.5K chars — theme JS/CSS dominates).

Then extract with python (execute_code or a script file, never inline `-c` in a shell fallback):

```python
import re, html
raw = open('page.html', encoding='utf-8', errors='replace').read()

# Slice: first <h1> (article headline) to a footer/related marker.
# Webflow blogs end articles right before the related-content block.
h1s = [m.start() for m in re.finditer(r'<h1', raw)]
start = h1s[0] if h1s else 0
markers = ['Related Blog Posts', 'About the author', 'footer']
ends = [m.start() for m in re.finditer('|'.join(map(re.escape, markers)), raw)]
end = min((e for e in ends if e > start), default=start + 200000)
body = raw[start:end]

body = re.sub(r'<script.*?</script>', ' ', body, flags=re.DOTALL)
body = re.sub(r'<style.*?</style>', ' ', body, flags=re.DOTALL)
body = re.sub(r'<(h[1-6])[^>]*>', r'\n\n## ', body)
body = re.sub(r'</(h[1-6])>', r'\n', body)
body = re.sub(r'<(p|li|div|tr|br)[^>]*>', r'\n', body)
body = re.sub(r'</(p|li|div|tr|ul|ol|pre|code)>', r'\n', body)
body = re.sub(r'<[^>]+>', '', body)
body = html.unescape(body)
body = re.sub(r'\n\s*\n+', '\n\n', body)
text = '\n'.join(l.strip() for l in body.split('\n') if l.strip())
```

## Verification checks

- Exactly one `<h1>` before slicing (one article per page; if more, take the one after the nav).
- Extracted length sane: LangChain article ≈ 11.5K chars. Tiny result (<2K for a normal post) = slice markers missed; try `</article>` or the first `<h2>` cluster.
- Tail contains CTA/newsletter boilerplate ("Sign up for our newsletter"): acceptable in the raw file, trim in the research note.
- Headings survive as `## ` via the h1/h2 → `\n\n## ` conversion — keeps structure for section mapping in the note.
