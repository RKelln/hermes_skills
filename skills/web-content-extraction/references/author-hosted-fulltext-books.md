# Author-hosted full-text books (the free-full-text route)

When the source you need to verify is an old trade book — 1990s tech and culture especially — check the author's own site before concluding you cannot read it. Many are hosted free in full, one URL per chapter. Canonical case: Kevin Kelly's *Out of Control* (1992).

## The pattern

- A landing/contents page (`kk.org/outofcontrol/contents.php`) that lists every chapter and section.
- One URL per **chapter section**, letter-suffixed: `ch<chapter>-<letter>.html` (`ch5-a` … `ch5-c`; `ch6-a` … `ch6-g`).
- Plain static HTML, ~17–28KB per file, HTTP 200, bot-friendly — plain `curl` plus a tag-strip is enough; no webx, curl-cffi or browser needed.
- **Every chapter file embeds the entire book table of contents** at the top, then the prose.

Bonus: the landing page carries the author's own commons note — "Cheaper than printing it out: buy the paperback book." Useful detail in a library context.

## Probe which letter file holds the section you want

```bash
cd "$(mktemp -d)"   # scratch dir for the probe fetches
for f in ch6-a ch6-b ch6-c ch6-d ch6-e ch6-f ch6-g; do
  code=$(curl -s -o "$f.html" -w "%{http_code}" "https://kk.org/mt-files/outofcontrol/$f.html")
  echo "$f $code $(wc -c < $f.html)"
done
```

All seven returned 200 on 2026-09-11. Section order inside a chapter follows the contents listing — ch. 6's final section, "The fourth discontinuity: the circle of becoming", lives in `ch6-g`.

## The trap, and how to beat it

A first-occurrence search hits the repeated TOC. On `ch5-a`, "chameleon" appeared **29 times before the prose**; the first extraction printed nothing but the contents list. Fix: slice from the **last** occurrence (or from the second occurrence of the section heading).

```python
import re, html as H
def clean(p):
    t = open(p, encoding='utf-8', errors='replace').read()
    t = re.sub(r'<script.*?</script>', ' ', t, flags=re.S | re.I)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = H.unescape(t)
    return re.sub(r'\s+', ' ', t).strip()

t = clean('ch5-a.html')
hits = [m.start() for m in re.finditer('chameleon', t, re.I)]
print('occurrences:', hits, 'len', len(t))   # always print both, to see the nav block
i = hits[-1]
print(t[max(0, i - 3000): i + 3000])
```

**Generalise:** any site that repeats a nav/TOC block on every page (chaptered books, docs sites, forum thread pages) needs last-occurrence or second-hit slicing. Print the occurrence list and the total length before slicing, so a nav-only extraction is visible instead of silent.

## Why this route matters to verification

The primary text is a couple of curls away, so there is no excuse for quoting a video's or an article's gloss of a book. It is also how the trimmed-tail failure mode gets caught: Kelly's sentence ends "I think that's a great bargain," four words the video dropped. See `claim-verification` → `references/citation-chains-and-revived-texts.md` for the pass this was used on.
