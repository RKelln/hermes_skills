# WordPress Targeted HTML Extraction

When trafilatura fails on WordPress sites — returns the wrong content (e.g. js-cookie docs) or 0 bytes — use targeted Python extraction on the downloaded HTML.

## Why trafilatura fails

WordPress sites often inline unrelated script bundles (libraries, widgets) that trafilatura's boilerplate detector misidentifies as the main content, or the article is outside its expected selectors.

## Fallback pipeline

```bash
# 1. Download with curl-cffi (never plain curl)
uvx curl-cffi get <URL> --impersonate chrome --body > /tmp/page.html
wc -c /tmp/page.html  # should be > 10KB for a real article

# 2. If trafilatura output is wrong or empty, use Python extraction
python3 << 'PYEOF'
import re

with open('/tmp/page.html') as f:
    html = f.read()

# Remove scripts and styles first
html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)

# Try common WordPress article selectors in order of reliability
patterns = [
    r'<article[^>]*>(.*?)</article>',           # <article> tag
    r'class="entry-content[^"]*"[^>]*>(.*?)</div>',  # .entry-content
    r'class="post-content[^"]*"[^>]*>(.*?)</div>',   # .post-content
    r'class="td-post-content[^"]*"[^>]*>(.*?)</div>', # .td-post-content
]

content = None
for pat in patterns:
    m = re.search(pat, html, re.DOTALL)
    if m:
        content = m.group(1)
        break

if content:
    text = re.sub(r'<[^>]+>', '\n', content)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text).strip()
    
    # Crop to article body (skip nav/ads before first meaningful heading/paragraph)
    for marker in ['Introduction', 'Abstract', 'Summary', 'Key Facts', 'What\'s New']:
        idx = text.find(marker)
        if idx > 0:
            text = text[idx:]
            break
    
    # Strip newsletter/subscribe/share junk from the end
    for em in ['Join our Newsletter', 'Sign up', 'Share this', 'Tags:', 'Editorial Notes']:
        idx = text.find(em)
        if idx > 0:
            text = text[:idx]
    
    print(text.strip())
else:
    print('ERROR: Could not find article content in HTML')
PYEOF
```

## When to use this

- Trafilatura returns <200 chars from a page with visible content
- Trafilatura returns the wrong content (library docs, nav text, footer)
- The site is WordPress (marktechpost.com, neurosciencenews.com, many tech blogs)

## Pitfall

This is a heuristic extraction — it can grab too much or too little depending on the theme. Always scan the output for completeness. If it's truncated, increase the regex greediness or try a different selector pattern.
