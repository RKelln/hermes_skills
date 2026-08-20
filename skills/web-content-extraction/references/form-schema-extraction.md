# Form Schema Extraction — Tally.so and similar client-rendered forms

Extract the questions, specs, and terms from an application/registration form WITHOUT rendering it.

## When to use

- A call page says "submit your application here" but withholds technical specs, and you need to know what the form actually asks
- You need the exact question list / field types of a Tally.so form (increasingly common for art/festival/venue open calls)
- Conclusion-guard: **read the form itself before concluding "no specs published"** — the form is the authoritative spec source, not the marketing page

## Technique (verified 2026-08-17 on tally.so/r/D4x9qZ — MAPP MTL MINUTE_MAPP call form)

Tally is client-rendered (React), but the FULL form schema ships in the static HTML — no browser or Kitesurf needed:

```bash
curl -sL "https://tally.so/r/<FORM_ID>" -o /tmp/form.html   # ~100KB for a typical form
```

Then grep the embedded JSON:

```bash
# Human-readable labels / question text (strip the [[ and trailing quote):
grep -oE '"safeHTMLSchema":\[\["[^"]{3,400}"' /tmp/form.html | sed 's/.*\[\["//; s/"$//' | sort -u

# Field types (tells you the form shape at a glance):
grep -oE '"groupType":"[A-Z_]+"' /tmp/form.html | sort | uniq -c
# INPUT_TEXT / INPUT_EMAIL / TEXTAREA / MULTIPLE_CHOICE / QUESTION / PAGE_BREAK / DIVIDER ...

# Prose blocks (call text, terms, "non-compliant" clauses) are TEXT groupTypes in the same JSON
```

## What it answered in practice

The MAPP MTL form: language choice, personal info (name/email/city/country), background + projection-mapping experience, "have you participated before?", "how did you hear?", newsletter opt-in. Field types showed **no FILE/VIDEO upload field** → the application is interest-only; the video + format compliance come post-shortlist. The form also carried the clause "MAPP_MTL reserves the right to refuse or remove any non-compliant video, even after acceptance" — proof specs are enforced later, not published upfront.

## Pitfalls

- **Choice-option labels use a different key than `label`** — `"label"` hits UI strings ("Choisir | Choose", "Continuer"). Multiple-choice OPTION text lives in the `options` array; grep it separately.
- `safeHTMLSchema` values are JSON arrays of style-tagged runs — the first string in each nested array is the visible text; strip the `[[` wrapper and trailing `"` as shown.
- Labels may be truncated by the `{3,400}` window — widen it for long paragraphs.
- The page has `oembedUrl` + form config in the same JSON; don't confuse form field JSON with the site chrome.
- Page breaks mean multi-step forms: question labels appear on separate `PAGE_BREAK` groupTypes — the sort -u output IS the full question list across steps.
