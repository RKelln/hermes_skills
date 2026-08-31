# Reading lab research reports: announcement → full report, and long-report cache search

Two patterns for getting the FULL substance out of lab research publications, verified
2026-08-30 on the Anthropic AAR study (anthropic.com/research/automated-researchers-mitigate-alignment-failures
→ alignment.anthropic.com/2026/automated-alignment-researchers/).

## 1. Announcement pages are summaries — the report is elsewhere

anthropic.com/research, alignment.anthropic.com, OpenAI/DeepMind research pages announce a
longer report. The durable substance (methodology, verbatim quotes, limitations, failure
modes) lives in the full report, NOT in the summary page the user shared. In the AAR case
the summary had the headline numbers; the cheating-study categories with verbatim agent
quotes, the benchmark tables, and the failure-mode analysis were only in the full report.

When the user shares a lab research page:

1. **Locate the full report**: web_search the page title/claims (the announcement links it,
   often on the lab's blog/alignment subdomain — alignment.anthropic.com/YYYY/<slug>/ — or a
   CDN PDF). The announcement page itself may name it as "Read the paper" / "full report".
2. **Fetch BOTH**: the announcement (what the user gave) AND the full report (the durable
   source). Save both as separate raw articles; cite both in the note's Source line.
   Skipping the report produces a shallow note.
3. **Check predecessor lineage**: pages referencing "earlier experiments" link prior papers
   (Apr 2026 Automated Weak-to-Strong Researcher → Aug 2026 AARs). Note the lineage in the
   note so the thread carries its history. Classify as a paper (fetch the report), not a
   newsletter article — the analysis depth is a paper's.

## 2. web_extract head+tail truncation on long static reports

When web_extract SUCCEEDS on a long report but truncates to head+tail over the char budget,
the FULL text is cached to disk — the result footer gives the cache path
(e.g. `/home/experimance/.hermes/cache/web/<host>-<hash>.md`). The head carries the
intro/results, the tail the references; the load-bearing middle (limitations, methodology,
verbatim quotes) is omitted.

Don't page the middle blindly with read_file offsets. Instead:

1. **search_files the cache file for section anchors first**:
   `pattern: ^#{1,4} |cheat|monitor`, `path: <cache file>`, `context: 1` — one call maps the
   whole document's structure (headings + load-bearing terms). On the AAR report this found
   the cheating section, production experiment, and failure modes in a single pass.
2. **read_file the relevant line ranges** from the cache — targeted reads of exactly the
   ranges the anchor search revealed, instead of three blind paging calls.
3. **The cache file doubles as the raw-source copy**: `cp` it into `raw/articles/` and
   prepend frontmatter (research-assistant Phase 2b) — no second fetch, and the raw layer
   gets the complete text, not the truncated head+tail.

Same pattern for "follow the important links": grep the cached full text for hrefs/URLs
before deciding what to fetch, instead of re-fetching the page.

## Relationship to sibling references

- `announcement-series-fulltext-extraction.md` — the Ghost/Next.js MECHANICS (hidden prose
  in `__NEXT_DATA__`, sibling PDF discovery, ligature cleanup). This file is the WORKFLOW
  layer (which URLs carry the substance) for lab research pages specifically.
- `long-form-web-paper-reading.md` — browser chunk-slicing for JS-heavy venues; this file's
  section 2 is the no-browser variant when web_extract already succeeded.
