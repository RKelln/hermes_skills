# Recovering image-borne evidence (Substack screenshots, CMS posts, hosted-report figures)

## The failure mode (verified 2026-09-11)

A Substack essay's appendix was **20 screenshots**. `web_extract` → webx → trafilatura
returned the full prose and dropped every image: no `[IMAGE: alt]` placeholder, no
figcaption — because the post's images carry neither `alt` text nor `<figcaption>`.
The extract showed the appendix's section headings with *nothing under them*.

An agent reading only the extract concludes "the appendix is three bare headings" or
"the appendix is quoted text", when in fact the evidence is visual and the extract
never saw it.

> **Rule:** if a markdown extract ends a section at its heading, you have not read that
> section. When the artifact's evidence could be visual, recover the images before
> writing any sentence about what the evidence shows.

## Step 1 — provenance and metadata without the JS-rendered pages

Substack exposes JSON and RSS that the archive page hides behind JS:

```bash
curl -sL -H 'User-Agent: Mozilla/5.0' \
  "https://<pub>.substack.com/api/v1/archive?sort=new&limit=50" -o pub.json
curl -sL "https://<pub>.substack.com/feed" -o pub.xml
```

`api/v1/archive` returns per post: `post_date`, `title`, `subtitle`, `canonical_url`,
`publishedBylines` (name + byline id), `reaction_count`, `comment_count`,
`podcast_url`. That is the full publication inventory **with dates**, and it is the
fastest way to establish "this author has N posts, no audio, no comments, and no bio"
— for anonymous writers the `/about` page is only Substack boilerplate, and the
`/archive` page returns one screen without JS.

Useful for: dating a body-vs-appendix question, proving an author has only two posts,
and checking engagement without scraping.

## Step 2 — save the HTML, then pull images in document order

```bash
uvx curl-cffi get "<POST-URL>" --impersonate chrome --body > post.html
wc -c post.html   # verify before processing
```

Regex the **base** S3 path, not the CDN resize URLs — the CDN form appears once per
`srcset` variant, so you get ~8 duplicates per image and must dedupe by UUID while
keeping the first offset:

```python
seen, order = set(), []
for m in re.finditer(r'substack-post-media\.s3\.amazonaws\.com/public/images/([0-9a-f\-]+)_(\d+)x(\d+)\.(\w+)', html):
    uid, w, h, ext = m.groups()
    if uid in seen: continue
    seen.add(uid); order.append((m.start(), uid, w, h, ext))
```

Download at **native resolution** — the base URL with no `w_1456,c_limit,f_auto`
prefix:

```
https://substack-post-media.s3.amazonaws.com/public/images/<uuid>_<W>x<H>.<ext>
```

## Step 3 — map each image to its section (the interpretive step)

Captionless images are meaningful only by position. Sort headings and image offsets
into one event list and walk it:

```python
events = sorted([(pos, 'H', text) for pos, text in headings] +
                [(pos, 'I', uid)  for pos, uid, *_ in images])
```

**Bug to avoid:** when stripping tags from a heading match, strip the *text* group.
`re.sub(r'<[^>]+>', '', m.group(1))` returns "2"/"3" (the heading level) for every
heading, producing a section map with no names. Use `m.group(2)`.

Caveat: Substack HTML carries the post body twice (article HTML plus JSON-escaped in
the payload), so a naive heading list duplicates. The image→section assignment still
holds; dedupe if you print it.

## Step 4 — PIL contact sheets, then vision

Tiling two images per row at 900px wide each turns 20 vision calls into 5. PIL is
available in the session python3 (`PIL 12.3.0` verified):

```python
from PIL import Image
# scale each to width 900 (LANCZOS), tile cols x rows with ~12px gutters, save JPEG q=88
```

Vision reads 900px-wide screenshots fine. For fine print, do **not** re-montage —
call `vision_analyze(region=[x1,y1,x2,y2])` on the original image instead.

**Ask for, per panel:** a verbatim transcription, which turns are user vs model,
visible model name/version labels and dates, and — separately — whether the excerpt
looks like an unprompted statement or a reply to a leading question. That last
question is usually the whole point of reading the images.

## Variant: a hosted report's figure carries the section's own content

Verified 2026-09-14 on a lab threat-intelligence report (250,591 chars of clean prose
via webx, so the extract looked complete). Two independent gaps turned up:

1. **A section whose body is a figure.** The section's entire payload was "The
   following is a list of skills developed by threat actors…" and then nothing — the
   list is a 1920×1778 JPEG. The tell is the same one as a heading with nothing under
   it, one step further out: **a lead-in sentence promising a list, table or graphic,
   with no content after it.**
2. **A text chart that is a JPEG, not a data payload.** 52 figures in the report, all
   served as CDN images; only one carries numbers (a ranked bar chart). Text extraction
   can therefore lose the report's only quantified figure while returning 250k chars.

Inventory before reading anything: the page's embedded content JSON holds every figure
caption and image URL in document order, so one regex pass tells you the whole figure
set (and the caption tells you which ones are data). Then fetch each CDN URL straight
into `vision_analyze` — for hosted figures there is no need for the PIL contact-sheet
step above, which exists only for local screenshot batches.

Ask for a verbatim transcription of every label, value and legend. Then treat the
result as **the agent's reading of pixels**: mark transcribed numbers `~` rather than
✓ unless a text source corroborates them, and say in the note that the figure was
recovered by vision. A data-bearing caption whose text never appears in the extract is
also a hint that the publisher's own figure list is the better index of what the
report contains than the prose alone.

**Never skip a figure because the vision provider looks unavailable.** Reading pixels
is now a first-line capability rather than a luxury: the configured auxiliary vision
model handles this (an image-only review of a figure is cheap), and a local vision
model is the fallback — Ryan confirmed one is available as of 2026-09-14. If a vision
call fails, that is a provider problem to fix or route around, not a reason to write
"the section appears to be empty". Note also that a truncated URL is the most common
cause of a failed image fetch (`...slice(0,30)` style prints), so print URLs in full
before fetching them.


## Reporting discipline

Write the transcription to a file as a **working record, not a source**. It is the
agent's reading of pixels. Label it that way and tell the user to re-check against the
live post before quoting publicly.

Also tier the exhibits while you are in there (see `claim-verification` →
`references/testimony-and-self-report-verification.md`):

- **Screenshots with UI chrome** — form-authentic, still trivially editable. Not
  independent verification.
- **Plain quoted text with no UI** — cannot be verified as producer output at all.
- **Anything with a second witness** (a public thread, a dated handle, a third-party
  report) — the only tier that can actually be checked. Find it and check it first.
