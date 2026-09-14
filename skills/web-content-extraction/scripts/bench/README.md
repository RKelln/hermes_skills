# Extraction bench — comparing extraction engines on real pages

Cross-engine comparison for the tools we actually use to turn web pages into text:

| engine | what it is | how it's called |
|---|---|---|
| `webx` | our own CLI — tirith gate → curl-cffi → trafilatura → JSON-LD/`__NEXT_DATA__` → regex → validate | `webx <url> --json` |
| `webclaw` | third-party Rust binary, JSON-LD/`__NEXT_DATA__`-first, 29 typed verticals, cloud-only render fallback | `webclaw <url> -f json` |
| `crw` (fastCRW) | third-party Rust binary, local renderer ladder (lightpanda/chrome/camoufox), crawl/map/watch | `crw scrape <url> --format json` |

## Why this exists, and why it scores facts instead of bytes

Comparing these tools by output size is worse than useless — it is inverted. A tool that
returns 1.7× more markdown may simply be keeping the navigation menu; a tool that returns
a tidy 3 KB may have dropped the article. Byte counts reward chrome and punish clean
extraction. That is exactly how the fastCRW evaluation first went wrong: ago.ca looked like
a 1.7× win for one engine until the two outputs were diffed and found to contain
*different halves of the page*.

So each case declares **`must_contain` facts** — distinctive content strings that must
survive extraction — and the primary score is **fact recall**. Size, wall time and each
engine's own success/failure signal are recorded alongside, but they are evidence, not
the score.

## Files

| file | role |
|---|---|
| `cases.json` | the test set. Cases carry `group`, `axis`, `expect`, `why`, `must_contain`, `must_not_contain` |
| `probe-candidates.py` | characterize candidate URLs (plain vs impersonated fetch, ld+json, framework payloads, text volume, consent wording) → picks axes from evidence |
| `derive-facts.py` | rank candidate fact strings from the page, broadly |
| `propose-facts.py` | propose facts from *lead content and JSON-LD only*, each verified against ground truth with its offset |
| `peek.py` | print the main-content text of a probed URL so a human can choose facts cheaply |
| `fill-facts.py` | the reviewed fact choices, in one reviewable place |
| `add-js-cases.py` | capability-flag variants of the shell cases (captures rendered ground truth) |
| `run-bench.py` | the harness: `--validate` (fixture integrity) and the run itself |
| `candidates*.txt` | probe lists, with the rationale per URL |

Ground truth is saved by `probe-candidates.py` to `/tmp/webx-bench-probe/<mangled-url>.cffi.html`
(the impersonated view of the page). Run artifacts land in `/tmp/webx-bench/`.

## Two groups, two purposes

**`web`** — the generic extraction axes we hit while reading for research: baseline prose,
very long page, newsletter platform, WordPress, corporate blog, code blocks, tables,
paywall-with-`articleBody`, huge single page, JS shell, vendor-blocked (403 and 401),
PDF, non-English, intentionally thin page, code host page, and an HTTP 404 that renders
as a page (`expect: fail`).

**`togather`** — the axes that come from a real failure list rather than from imagination.
They were drawn from an integration audit of Togather's event sources, where every
disabled source was recorded with a verified root cause, so the cases are named after
the *cause*, not the site:

- Tier-0 ideal (many `schema.org Event` blocks), single-block Event, Event on a calendar
- SSR shell: thin served text, content inside `__NEXT_DATA__`
- consent banner on a Tier-0 source
- React SPA that never renders *(disabled: headless never resolves the list)*
- third-party widget that never renders *(disabled: Wix OOI, render timeout)*
- freeform layout, no repeating container *(disabled: concert blocks are loose `h2`/`hr` siblings)*
- dates only in narrative prose *(disabled)*
- dates only on detail pages *(disabled)*
- event URLs hidden in `data-*` attributes *(disabled)*
- Cloudflare managed challenge / Cloudflare 403 *(disabled)*
- `robots.txt: Disallow /*` *(disabled)* — assertion is **compliance**, not extraction quality
- two dates concatenated by an icon element *(disabled: `Thu Aug 06 2026Wed Aug 19 2026`)*
- content-model mismatch: news posts, not events *(disabled — a negative control)*

The Togather group is the reason this bench is worth keeping: it tests our own tools
against **the failures we already documented**, and the clearest question it answers is
whether a general extractor or a different renderer gets content that a bespoke CSS
selector scraper could not.

## Usage

```bash
cd scripts/bench   # from the web-content-extraction skill directory

# 0. add cases, then probe them so they have ground truth
python3 probe-candidates.py --file candidates3.txt --out /tmp/webx-bench-probe/probe3.json

# 1. choose facts (propose -> peek -> review -> fill-facts.py)
python3 propose-facts.py --cases cases.json --out facts-proposed.json
python3 peek.py "orpheus" --chars 600
python3 fill-facts.py

# 2. gate: every declared fact must exist in the ground truth. Fix fixtures BEFORE running.
python3 run-bench.py --validate

# 3. run
python3 run-bench.py --group web
python3 run-bench.py --engines webx,webclaw,crw --only w-vendor-blocked-403,t-jsonld-event-13 --show
```

`crw` is located via `$CRW_BIN`, then `PATH`, then `/tmp/crw-recon/bin/crw`; a missing
engine reports `not-installed` rather than failing the run.

## Four ways this bench nearly lied (all found while building it)

These are the failure modes to guard when extending it — every one of them produced a
confident, wrong comparison before it was caught:

1. **Validating facts against raw HTML is wrong.** A sentence containing inline links is
   *split by markup* in the source but intact in extracted text, so raw-HTML validation
   rejects correct facts. Ground truth must be tag-stripped text.
2. **Tag-stripping must keep structured-data payloads.** `application/ld+json` and
   `__NEXT_DATA__` blocks are served content and are exactly what a structured-data-aware
   engine reads; deleting them made every Togather Tier-0 fact look like a fixture error.
   Two of the three engines read those payloads, so this bug was invisible in any
   comparison that only used DOM text.
3. **Literal matching punishes correct extraction.** `webx` returned
   `**Neo-Luddism** or **new Luddism** is a philosophy opposing…` — bold markers made a
   sentence it had plainly returned count as missing. Matching must normalise markdown
   emphasis, links, entity/nbsp variants and heading markers, identically on both sides.
4. **"Longest string field" is the wrong way to find an engine's output.** A nested
   JSON-LD `@graph` or metadata blob can outrank the real content field, making an engine
   look like it missed text it returned. Prefer an explicitly content-named key before
   recursing.

5. **A default-mode run measures defaults, not capability.** The first full run recorded
   crw returning 77 and 66 characters from two JS shells and concluded it had no
   renderer for that class. It has one: `crw scrape --js` returns 14,783 and 8,542
   characters from the same two pages in 2–4 s. Any "engine X cannot do Y" claim needs a
   second run with the capability flag on. Cases now carry
   `"engine_args": {"crw": ["--js"]}`, and flag variants are separate case ids on the
   same URL (see `add-js-cases.py`), so out-of-the-box behaviour and available
   capability stay distinguishable. Their ground truth is a captured render saved as
   `<mangled>.rendered.txt` and labelled `rendered` — an engine-derived fixture is fine
   as long as it can never masquerade as page truth.

Generalisation: in an extraction comparison, most apparent engine differences are
**measurement artifacts**. Diff the outputs by hand before believing a score.

## Known limitations

- **One page per axis.** n=1 per case. Treat differences as hypotheses, not verdicts;
  the point is to find where to dig, not to rank tools.
- **JS-shell cases cannot be scored from served HTML.** Their facts have to come from a
  rendered view, which means the fixture itself depends on a renderer. Cases without
  facts are marked by an empty `must_contain` and their result is qualitative.
- **Facts decay.** Pages are edited; 2 of the fixtures were already stale-looking within
  a day (an arXiv PDF whose saved copy came back corrupt from the text-mode probe fetch,
  and one Reel Asian heading). Re-run `--validate` before trusting a comparison, and
  move time-sensitive strings (market prices, "temporarily closed") out of fixtures.
- **`expect: policy`** assertions (robots.txt) do not measure extraction at all; they
  record whether an engine respects a site's stated wishes. That matters for civic
  infrastructure and should be reported separately from quality.
- **Binary staleness.** This box's `crw` lives in `/tmp` (unpacked, SHA-verified) because
  installing it is still an open decision; `webclaw` sits in `~/.local/bin`. Record
  versions with any results.
- **Repeated runs of identical cases do not always produce identical scores.** Observed
  while building: `t-freeform-layout` scored 2/3 in one run and 3/3 in the next, and the
  same `crw` cloudflare case took 13.3 s once and 0.1 s another time (chrome-rung cold
  start). Fact recall should be near-deterministic on static HTML, so treat a single
  point of difference as noise, run a case two or three times before drawing a
  conclusion from it, and never rank engines on a one-run margin of one or two facts.
