# Hermes Meta-Skills

Skills that make the Hermes Agent ecosystem self-improving:
research before building, build with quality gates, maintain against upstream changes,
and produce professional documents.

## Skills

### `/skill-research` — Research before building

Search all registries + GitHub topics + awesome lists before building a new skill.
Classifies findings as duplicate, adjacent, partial, or none. Avoids reinventing.

### `/skill-builder` — Build with quality gates

Full pipeline from idea to published skill: research existing solutions, mine adjacent
skills for reusable features, author SKILL.md with proper conventions, test end-to-end,
independent subagent review, publish. Includes Phase 1b "Mine Adjacent Skills" —
clone the best existing skills and extract their patterns before writing your own.

### `/skill-upstream-sync` — Maintain against upstream

Detect when customized bundled skills have upstream changes. Runs an LLM-driven
integration pass to merge the best of both, then re-baselines so future updates flow.

### `/typst` — Compile professional documents

A modern alternative to LaTeX. Compile `.typ` markup to PDF, PNG, SVG, or HTML.
Use templates from Typst Universe, generate documents from data, inspect output
programmatically with `typst eval`. Covers agent verification methods (HTML/PNG/pdftotext),
conversion tables for Markdown and LaTeX, and a common-errors quick-reference.

### `/web-content-extraction` — Safe web extraction

One-shot web page → clean markdown via the bundled `webx` script: tirith safety
scan → download (curl with bot-detection fallback to curl-cffi) → extraction
(trafilatura / JSON-LD articleBody / regex) → content scoring → validation.
Handles paywalls (HBR-style JSON-LD), bot-blocked sites, PDFs (pdftotext), and
classifies failure walls (captcha, JS-rendered CSR, video) with targeted hints.
Ships with a 24-case regression suite covering every extraction path:
`webx --selftest` (suite at `scripts/webx-tests.tsv`).

## Install

```bash
hermes skills tap add RKelln/hermes_skills
hermes skills install RKelln/hermes_skills/skill-research
hermes skills install RKelln/hermes_skills/skill-builder
hermes skills install RKelln/hermes_skills/skill-upstream-sync
hermes skills install RKelln/hermes_skills/typst
hermes skills install RKelln/hermes_skills/web-content-extraction
# webx needs to be on PATH — symlink it once:
ln -s ~/.hermes/skills/research/web-content-extraction/scripts/webx ~/.local/bin/webx
webx --selftest   # verify the install
```

## Use

```
/skill-research       # Before building: is there already a skill for this?
/skill-builder        # Build a new skill with research + review pipeline
/skill-upstream-sync  # After hermes update: merge upstream changes into customized skills
/typst               # Create a PDF, CV, letter, paper, or formatted document
webx <URL>           # Extract any web page to clean markdown (one call)
```

## Requirements

- Hermes Agent (any recent version)
- `skill-research` is a prerequisite for `skill-builder` (Phase 1 delegates to it)
- `skill-upstream-sync` works standalone or as a cron job
- `typst` requires the Typst CLI: `brew install typst` or `cargo install --locked typst-cli`
