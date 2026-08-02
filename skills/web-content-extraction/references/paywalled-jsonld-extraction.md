# Paywalled Article Extraction: JSON-LD articleBody + trafilatura Python-lib fallback

Discovered 2026-08-02 extracting HBR (`hbr.org/2026/07/3-questions-to-pressure-test-your-priorities`). HBR and other Next.js-era CMS sites serve only a summary + lede in rendered HTML but embed the FULL article body in structured data (JSON-LD). This beats browser fallback and paywall-triangulation when the same page carries the whole text.

## The pattern

1. **Download the page** (curl-cffi, `--body > file`, verify size):
   ```bash
   uvx curl-cffi get "<URL>" --impersonate chrome --body > page.html
   wc -c page.html   # verify; ~137KB for a typical HBR article page
   ```
2. **Check for the JSON-LD body:**
   ```bash
   grep -c 'articleBody' page.html   # ≥1 = full body present
   ```
3. **Extract with a local python3 heredoc over the file** (mandatory: download-then-process, never pipe from network):
   ```bash
   python3 - <<'EOF'
   import json, re, hashlib
   html = open('page.html').read()
   m = re.search(r'"articleBody"\s*:\s*(".*?")\s*,\s*"', html, re.DOTALL)
   body = json.loads(m.group(1))
   open('body.txt','w').write(body)
   print("len:", len(body), "sha256:", hashlib.sha256(body.encode()).hexdigest())
   EOF
   ```
4. **sha256 goes in the raw-article frontmatter** (research-assistant Phase 2b: `raw/articles/YYYY-MM-DD-slug.md`).

Result this session: trafilatura got 423 chars (summary + lede); JSON-LD `articleBody` got the full 8,025-char body.

## Reading single-line extracted files

Extracted bodies are one giant line; `read_file` truncates the display. Wrap first:
```bash
fold -s -w 110 body.txt > body-wrapped.txt
```
then `read_file` the wrapped file.

## trafilatura CLI `-i` misfire → Python library API

`uvx trafilatura -i page.html --output-format markdown` can treat the file's *content* as a URL (warning: "Discarding URL: <!DOCTYPE html>...") and exit 0 with 0 bytes, even for a valid page — on bot-protected AND plain Next.js pages. Check output size, not exit code. Cheaper fallback than regex-stripping HTML:
```bash
uvx --from trafilatura python3 -c "
import trafilatura
html = open('page.html').read()
text = trafilatura.extract(html, output_format='markdown', include_links=True)
open('page.md','w').write(text or '')
"
```
Still tiny (<500 chars) after a working extraction? The page is genuinely paywalled → JSON-LD pattern above.

## Notes

- No `articleBody`? Check for `<script id="__NEXT_DATA__">` and walk its JSON for long string fields named `articleBody` / `body` / `content`.
- Check JSON-LD/NEXT_DATA before reaching for browser-based extraction of paywalled pages — structured data is faster and needs no browser.
- Related but distinct: `references/paywalled-article-triangulation.md` covers finding the article text elsewhere when the page itself hides it entirely.
