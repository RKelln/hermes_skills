# Print-to-PDF sites, and documents that live in several routes

For sources that are not one article and not one file: a landing page for a document, a report site with a PDF build plus supplement pages, a JS app whose real content lives at `/summary`, `/footnotes`, `/supplements/*`. The failure this prevents is reading the teaser and treating it as the source, or reading 300k characters of raw text to learn what its table of contents is.

## 1. Harvest the link list before extracting anything

A landing page whose prose **ends mid-argument** (a cliffhanger paragraph, then a form or a "choose your path" widget) is a teaser. The document is usually reachable by link. Download the HTML once and read its `href`s:

```bash
curl -sL -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36" "$URL" -o .tmp/page.html
wc -c .tmp/page.html
grep -o 'href="[^"]*"' .tmp/page.html | sort -u
```

One screen shows the shape: a downloadable PDF, a notes page, chapter or supplement routes, an about page. Fetch from that list instead of guessing paths. External hrefs in the same list are also the document's own citation set; where the rendered page hides them behind anchor text ("here", "this paper"), the HTML is the only place the targets survive.

## 2. Build a section outline before reading the body

For a print-to-PDF of a web page (check `pdfinfo` — `Creator: HeadlessChrome`, Letter page size):

- **Extract with `pdftotext` reading order, NOT `-layout`.** Marginal and footnote columns get clipped at the column edge under `-layout`, producing half-sentences that look like source text, and two-column bodies interleave. Default `pdftotext doc.pdf out.txt` follows reading order and keeps sentences whole. Reserve `-layout` for single-column academic PDFs.
- **Find the type sizes, then print only the headings.** A font-size histogram separates body from headings in one pass — the size carrying the most characters is body; everything meaningfully larger is a heading:

```python
import pymupdf, collections
d = pymupdf.open('doc.pdf')
sizes = collections.Counter()
for p in d:
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                sizes[round(s['size'], 1)] += len(s['text'].strip())
print(sorted(sizes.items(), key=lambda x: -x[1])[:12])   # body = the top count
```

Then print page markers plus every line whose max span size is at heading size. A 90-page document collapses to a few thousand characters — a real table of contents with page numbers — and it tells you which chapters to read in full before you spend the context.

- **`pdfinfo` first:** page count, producer, creation date. Hundreds of pages with a `HeadlessChrome` producer means a website build, so expect the web version to be more complete than the PDF (marginal notes, interactive charts) and plan to fetch both.

## 3. Split the raw layer when the PDF is lossy

A print-to-PDF can be the only complete copy of the *narrative* while the *notes* are complete only on the site. Archive both, as two raw files, each frontmatter saying what it is and what it is not:

- `raw/articles/<date>-<slug>.md` — the document text (extraction method, page count, producer in frontmatter).
- `raw/articles/<date>-<slug>-footnotes-and-supplements.md` — the site's notes page plus every supplement page concatenated, each under a `<!-- ===== <slug> ===== -->` marker so a later session can grep one section instead of reading the whole file.

State in the frontmatter what is NOT archived (interactive charts, model spreadsheets, images) and where those numbers survive instead; repeat the limits in the note as what was read in full, in outline, or not at all.

**Order of operations for `sha256`:** write the file, compute the hash with `~/.hermes/scripts/raw-sha256.sh <file>`, *then* patch the `sha256:` field. That helper hashes the body only (everything after the second `---` fence), so editing frontmatter afterwards cannot invalidate the hash — no re-hash loop.

## 4. Batch-fetch many sub-pages without flooding context

Fifteen supplement pages through `web_extract` (five URLs per call, head+tail each) floods the session. Write a URL list and loop the CLI, one file per page:

```bash
while read -r u; do
  slug=$(echo "$u" | sed -E 's#https?://[^/]+/?##; s#/#-#g; s#^$#index#')
  webx "$u" --out "$slug.md" >/dev/null 2>&1
done < urls.txt
ls -la | awk '{print $5, $9}'   # verify every page landed; check the sizes
```

Then grep or read individual files on demand, so context stays proportional to what you actually need and the files survive a timeout.

## 5. Read the document's apparatus before judging it

Long structured documents carry their caveats in the apparatus, not the narrative: footnotes, the appendix saying which figures are recommendations rather than predictions, the published internal dissent. Extract the note text as its own artifact (§3) and read the notes attached to any claim you will repeat.

**And check the document against itself.** A multi-route document can carry different numbers on different routes — a summary page and a deep supplement disagreeing by a quarter is common when one was written earlier. Before quoting a figure, find it on the most detailed route and note where another route differs, rather than silently picking the one you read first. The same check catches a claim the narrative states more flatly than the note it cites.

## 6. Second pass: the note's follow-up list is the work order

A document this size is normally read in two passes, and the note should say so. Rules that keep the pair honest:

- In the note's top block, state by section name what was read **in full**, what was read later **at source**, what is **outline only**, and what is **not read**. A later session can then tell an unexamined claim from a checked one.
- The follow-up list is a work order, not decoration. On the second pass, mark items `[x]` and say **what changed in the note** ("two new sections", "the reception was upgraded to the primary source") instead of rewriting the note or writing a second note for the same source. Same source, second pass → extend the existing note and its raw files.
- Keep the note's revision line **number-free**. Inserting a section renumbers every pointer after it, so a numbered cross-reference goes stale the moment the note improves.
- Print chosen line ranges **with their line numbers** (`for i in range(a-1, b): print(f"{i+1}: {lines[i]}")`) so a section can be re-found later without re-scanning the file.
- When the second pass upgrades a critic's argument, go to the critic's own text. A critique summarised inside a magazine round-up loses the mechanism (and the numbers) that makes it usable — and the round-up's version will not survive being quoted.
