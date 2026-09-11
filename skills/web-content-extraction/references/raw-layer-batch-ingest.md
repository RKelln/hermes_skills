# Batch landing fetched sources into the raw layer

Companion to `references/lab-research-report-patterns.md` §2.3 (where a single truncated
report's cache file doubles as the raw-source copy). This file covers the **N-URL** case:
a session covering several lab posts at once (a launch week, a policy cluster, a
multi-post response to an incident).

## The waste to avoid

Re-emitting extracted text through `write_file` pays the full body cost a second time for
no benefit. Five OpenAI posts was ~70KB of output that the extraction already produced.
Fetch to disk, then add frontmatter in ONE scripted pass.

## Verified recipe (2026-09-10, five OpenAI posts, hashes round-trip clean)

```bash
mkdir -p .tmp raw/articles
webx "<URL1>" --out .tmp/a.md
webx "<URL2>" --out .tmp/b.md   # one per URL; ~5s each, no tokens
wc -c .tmp/*.md                 # verify: non-trivial, not mid-sentence
```

Then a single python pass that, per file:

1. strips webx's leading `Source: <url>` line — regex `^Source: \S+\n+`
2. prepends raw frontmatter (`title`, `source_url`, `ingested`, `sha256: PENDING`)
3. writes `raw/articles/<date>-<slug>.md`
4. runs `bash ~/.hermes/scripts/raw-sha256.sh <path>` and replaces `PENDING` with the digest
5. asserts the digest matches `[0-9a-f]{64}` before moving on (fail loudly, never store a
   malformed hash)

## Why the hash survives the frontmatter edit

`raw-sha256.sh` hashes only the BODY after the second line-anchored `---` fence, so
patching the `sha256:` field afterwards cannot drift it. Recompute once at the end and
compare against the stored value as a final check. The canonical helper is the single
source of truth — see `content-ingestion-pipeline` → `references/raw-layer-hashing.md`.

## Date discipline

`webx --out` does not always carry the post's date. Where the page has no date line, use
month precision in the filename (`2026-08-openai-<slug>.md`) and mark the date `~` in the
note rather than guessing a day to make the filename look tidy. Same for posts whose date
comes only from third-party coverage — the ledger marks those `~` too.

## Reporting the batch (Ralph's rule)

Reporting all N bodies with their hashes is worthwhile but verbose; if the batch is large, read the files back and
report a compact per-file line (name, char count, 16-hex prefix of the hash) rather than
pasting hashes in full. Verify with one recompute, then report the verification — not just
the fact that the write succeeded.
