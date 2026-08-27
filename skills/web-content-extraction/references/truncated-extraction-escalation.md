# Truncated extraction → webx CLI escalation (head-only returns)

## The failure mode

`web_extract` can return **plausible-but-head-truncated** content on bot-guarded
or progressive-render pages: output that looks like a normal short page (title,
lede, clean markdown, no error) but is only the first ~800 tokens of a long
article. This is distinct from the failure modes already in SKILL.md (0 bytes,
<200 chars, wrong content) because it **passes the plausible-content check** —
the head reads like the real article.

## Verified case (2026-08-27)

- URL: `https://www.meta.com/thefutureisforeveryone/` (Zuckerberg essay, 6,500 words)
- `web_extract` (both as the chat URL attachment and with `char_limit=40000`)
  returned only the ~800-token lede, ending mid-sentence at "Early AI could
  answer questio..."
- Wayback Machine via `web_extract` failed separately (tooling missing) — do not
  reach for archive mirrors before trying the CLI
- `webx <URL> --out file` (CLI, no special flags) extracted the **full 41K
  chars** via trafilatura in one call, HTTP 200, safety 0/100

## The rule

If `web_extract` output is suspiciously short for a known content-rich page, or
ends mid-article with no error:

1. Rerun through the **webx CLI** with `--out` to a file — the CLI's
   curl-cffi rescue + full trafilatura/JSON-LD/regex pipeline often gets what
   the plugin path truncated. This is also the step Ryan expects ("use
   web_extract / webx to get web pages") before any browser attempt.
2. Verify the file's char count (`wc -c`) and that it does NOT end
   mid-sentence, then read it.
3. Only if the CLI also fails (<200 chars, 0 bytes, captcha hint) fall through
   to targeted extraction or the browser tool per the SKILL.md decision flow.

## Companion pattern (worked same session)

Batch multi-URL extraction with per-file `--out` and explicit exit echoes so a
single bad URL doesn't mask the others:

```bash
webx <URL1> --out /tmp/a.md; echo "e1=$?"; webx <URL2> --out /tmp/b.md; echo "e2=$?"
wc -c /tmp/a.md /tmp/b.md
```

Distinguish tool failure (non-zero exit) from extraction failure (exit 0 but
tiny/truncated output) — both need different next steps.
