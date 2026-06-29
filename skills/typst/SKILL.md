---
name: typst
description: Compile Typst documents to PDF/PNG/SVG/HTML, use templates from Typst Universe, and manage packages — a modern LaTeX alternative.
version: 1.1.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [typst, typesetting, pdf, document, template, typst-universe]
    category: productivity
    related_skills: [markdown-publishing, literary-html, nano-pdf]
---

# Typst

Typst is a markup-based typesetting system — a modern alternative to LaTeX
that compiles `.typ` files to PDF, PNG, SVG, or HTML. It has a built-in
scripting language, math typesetting, bibliography management, and a community
package ecosystem at [Typst Universe](https://typst.app/universe/).

This skill covers CLI compilation, template-based project creation, package
management, document verification for agents, and common pitfalls.

## When to Use

- User asks you to create a PDF, formatted report, or typeset document
- User mentions Typst, `.typ` files, `typst.toml`, or Typst Universe
- User wants to generate a CV, paper, letter, invoice, or other structured document
- User wants to use a template from https://typst.app/universe/
- User wants to convert markdown or structured data into a professionally typeset PDF

## Quick Reference

| Task | Command |
|------|---------|
| Compile to PDF | `typst compile file.typ` |
| Compile to PNG | `typst compile file.typ page-{p}.png -f png` |
| Compile to HTML | `typst compile --features html file.typ /dev/stdout -f html 2>/dev/null` |
| Watch and recompile | `typst watch file.typ` |
| Init from template | `typst init @preview/template-name project-dir` |
| Init specific version | `typst init @preview/template-name:1.0.0 project-dir` |
| List available fonts | `typst fonts` |
| Add font path | `typst compile --font-path ./fonts file.typ` |
| Eval expression | `typst eval "1 + 1"` |
| Eval in document | `typst eval --in doc.typ 'query(heading).len()'` |
| Show system info | `typst info` |
| PDF/A standard | `typst compile doc.typ --pdf-standard a-4` |
| Export deps for CI | `typst compile doc.typ --deps deps.json --deps-format json` |

## Procedure

### Phase 1: Installation

Check if Typst is installed:

```bash
typst --version
```

If not, install via the appropriate package manager:

- **Linux (Homebrew)**: `brew install typst`
- **Linux (Cargo)**: `cargo install --locked typst-cli`
- **Linux (Nix)**: `nix-shell -p typst`
- **macOS**: `brew install typst`
- **Windows**: `winget install --id Typst.Typst`

Or download a pre-built binary from https://github.com/typst/typst/releases

### Phase 2: Choose an Approach

There are three ways to produce a document:

1. **From a template** — Best for standard documents (CVs, papers, letters).
   Browse https://typst.app/universe/ to find a template, then init from it.
   
2. **From scratch** — Best for custom layouts. Start with a minimal document
   and iterate.

3. **Convert from markdown** — Manually translate markdown structure to Typst markup
   using the conversion table below. Pandoc does not have a Typst writer.

### Phase 3: Working with Templates

Search for templates on Universe and init a project:

```bash
typst init @preview/charged-ieee paper-project
cd paper-project
typst compile main.typ
```

To find templates, browse https://typst.app/universe/ in the browser (the
`browser_navigate` tool) and search by category. Common template namespaces:

- `@preview/charged-ieee` — IEEE-style papers
- `@preview/modern-cv` — CV/resume
- `@preview/letter` — Formal letters
- `@preview/invoice` — Invoices
- `@preview/touying` — Presentation slides

Local templates can be tested before publication:

```bash
typst init @local/my-template:0.1.0 draft --package-path ./packages
```

### Phase 4: Creating Documents from Scratch

Minimal document:

```typst
#set page(paper: "a4", margin: 2cm)
#set text(size: 12pt)

= Title

Content goes here. Use *bold*, _italic_, `monospace`.

== Section

- Bullet list
- Another item

$E = m c^2$  // inline math

$ sum_(i=1)^n i = (n(n+1)) / 2 $  // display math
```

Key syntax to know:

| Element | Syntax |
|---------|--------|
| Heading levels | `=`, `==`, `===`, `====` |
| Bold / italic | `*bold*`, `_italic_` |
| Code | `` `monospace` `` |
| Line break | `\` at end of line |
| Smart quotes | `'single'` and `"double"` |
| Links | `https://example.com` or `#link("url")[text]` |
| Code block | `` ```typst ... ``` `` |
| Set rules | `#set text(size: 12pt)` |
| Show rules | `#show heading: set text(blue)` |
| Functions | `#heading(level: 1)[Title]` |
| Variables | `#let x = 5` |
| Import package | `#import "@preview/name:1.0.0": function` |
| Label / reference | `<label>` / `@label` |
| Figure with caption | `#figure(image("img.png"), caption: [Text]) <fig:name>` |

#### Generating Tables from Data

```typst
#let data = ((name: "Alice", score: 95), (name: "Bob", score: 82))

#table(
  columns: 2,
  table.header([*Name*], [*Score*]),
  ..data.map(row => (row.name, str(row.score))).flatten(),
)
```

For CSV data, `csv("data.csv")` returns string arrays. For JSON data,
`json("data.json")` preserves types — wrap in `str()` for table cells.

Common table patterns: zebra stripes with `fill: (_, y) => if calc.odd(y) { luma(240) }`,
bold headers with `#show table.cell.where(y: 0): strong`, full-width with
`columns: (1fr,) * n`. Use `grid()` instead of `table()` for borderless layout.

### Phase 5: Compilation and Output

```bash
# Basic PDF compilation
typst compile document.typ

# Explicit output path
typst compile document.typ output.pdf

# Non-PDF formats
typst compile document.typ page-{p}.png -f png    # one PNG per page; {0p} pads, {t} = total
typst compile document.typ output.svg -f svg       # SVG output
typst compile --features html document.typ output.html -f html     # HTML output

# PDF standards (accessibility, archival)
typst compile document.typ output.pdf --pdf-standard a-4       # PDF/A-4
typst compile document.typ output.pdf --pdf-standard a-4,ua-1  # PDF/A-4 + PDF/UA-1

# CI / reproducible builds
typst compile doc.typ out.pdf --root . \
  --creation-timestamp "$SOURCE_DATE_EPOCH" \
  --package-cache-path ./.typst-cache \
  --deps deps.json --deps-format json

# Set project root (for absolute imports)
typst compile src/main.typ --root .

# Watch mode (auto-recompile on save)
typst watch document.typ
```

Multi-page PNG/SVG outputs require a page-number template like `page-{p}.png`.
`--pages` uses one-indexed physical page numbers, not the document's printed
page counter.

### Phase 6: Package Management

Packages are imported in Typst source:

```typst
#import "@preview/cetz:0.3.2": canvas, draw
```

Packages are auto-downloaded on first use and cached in `~/.cache/typst/packages/`.
No separate install step is needed.

To locate package storage:
```bash
typst info | grep -i package
```

Local packages can be placed in `~/.local/share/typst/packages/local/{name}/{version}/`
and imported via `#import "@local/{name}:{version}": *`.

### Phase 7: CLI Introspection with `typst eval`

`typst eval --in` lets agents inspect document structure without opening a PDF.
This is Typst's killer feature for programmatic document verification.

```bash
# Count headings
typst eval --in doc.typ 'query(heading).len()'

# Count figures
typst eval --in doc.typ 'query(figure).len()'

# Filter by level/kind
typst eval --in doc.typ 'query(heading.where(level: 1)).len()'
typst eval --in doc.typ 'query(figure.where(kind: image)).len()'
```

#### Metadata Export Pattern

Embed metadata in Typst docs, extract it from the CLI:

```typst
// In doc.typ:
#metadata((title: "Report", version: "2.1.0", status: "draft")) <doc-info>
```

```bash
typst eval --in doc.typ 'query(<doc-info>).first().value' --pretty
# -> {"title": "Report", "version": "2.1.0", "status": "draft"}
```

#### Document Statistics

```bash
# Pages
typst eval --in doc.typ 'counter(page).final().first()'

# Full stats dump
typst eval --in doc.typ '(
  headings: query(heading).len(),
  figures: query(figure).len(),
  pages: counter(page).final().first(),
)' --pretty
```

#### Multi-Pass Compilation

Query in pass 1, feed back via `--input` in pass 2 (e.g., "Page X of N"):

```bash
PAGES=$(typst eval --in main.typ 'query(<page-count>).first().value')
typst compile main.typ --input "total-pages=$PAGES"
```

### Phase 8: Agent Verification

Agents cannot preview PDFs directly. Use these three methods to verify output:

**1. HTML export — best for text, structure, and content checks:**

```bash
typst compile --features html document.typ /dev/stdout -f html 2>/dev/null
typst compile --features html document.typ /dev/stdout -f html 2>/dev/null | grep -i "expected text"
```

Outputs semantic HTML (headings → `<h2>`, tables → `<table>`). Ignores
page-specific features (headers, footers, page numbers).

**2. PNG export — for visual layout verification:**

```bash
typst compile document.typ "page-{p}.png" -f png
# Then read the PNG file(s) to visually inspect the rendered output.
```

Use `--ppi 288` for higher resolution. Requires a multimodal model for visual
inspection. Best when alignment, spacing, font rendering, or page breaks matter.

**3. pdftotext — fallback for quick page-count/content checks:**

```bash
typst compile document.typ && pdftotext document.pdf -
```

### Phase 9: Markdown / LaTeX Conversion

#### Markdown → Typst Quick Map

| Effect | Markdown | Typst |
|--------|----------|-------|
| Bold | `**text**` | `*text*` |
| Italic | `*text*` | `_text_` |
| Code | `` `code` `` | `` `code` `` |
| Link | `[text](url)` | `#link("url")[text]` |
| Heading | `# Title` | `= Title` |
| Bullet list | `- item` | `- item` |
| Numbered list | `1. item` | `+ item` |

#### LaTeX → Typst Package Equivalents

Typst is "batteries included" — most LaTeX packages are built in:

| LaTeX | Typst |
|-------|-------|
| `graphicx`, `svg` | `image()` function |
| `tabularx` | `table()`, `grid()` |
| `amsmath`, `amssymb` | Built into math mode |
| `hyperref` | `link()` function |
| `biblatex` | `cite()`, `bibliography()` |
| `geometry`, `fancyhdr` | `#set page(margin: ..., header: ...)` |
| `xcolor` | `#set text(fill: rgb("..."))`, `luma()` |
| `enumitem` | `list()`, `enum()`, `terms()` parameters |
| `csquotes` | Smart quotes auto-active |
| `\newcommand{\foo}{...}` | `#let foo = ...` |
| `\textbf{x}` (style-only) | `#text(weight: "bold")[x]` or `*x*` |
| `\label{foo}` / `\ref{foo}` | `<foo>` / `@foo` |

#### Using Pandoc

Pandoc can use Typst as a PDF engine (reads Typst markup, outputs PDF):

```bash
pandoc input.md -o output.pdf --pdf-engine=typst         # Markdown → PDF via Typst
```

Pandoc has a Typst *reader* but no Typst *writer* — you cannot convert
Markdown/LaTeX *to* Typst source with Pandoc. For those cases, manually
translate using the mapping tables above.

#### For LaTeX Math

Use the mitex package if you need to embed raw LaTeX math:

```typst
#import "@preview/mitex:0.2.6": mitex, mi
#mitex(`\frac{\partial f}{\partial x}`)
```

## Ecosystem Tools

- **tinymist** — Language server for editor integration (autocomplete, preview)
- **typstyle** — Code formatter: `cargo install typstyle && typstyle -i *.typ`
- **tytanic** (`tt`) — Visual regression testing for packages (PNG diffs)
- **typst-package-check** — Validator before submitting to Typst Universe

## Pitfalls

- **Multi-letter identifiers in code**: In `#` expressions and code blocks,
  bare multi-letter words are treated as variable references, not text.
  Use `[content blocks]` for literal text in function arguments (e.g.,
  `[Books]` works correctly). In markup paragraphs outside `#`, this
  doesn't apply — bare words display as-is.

- **Font availability varies**: `typst fonts` lists available fonts. Don't
  assume system fonts like "Times New Roman" are present — check first or
  bundle fonts with `--font-path ./fonts`.

- **Package versions are required**: Unlike npm, `#import "@preview/name"` with
  no version doesn't work. Always include the version: `@preview/name:1.0.0`.

- **typst init may fail on some templates**: Not all packages are init-able
  templates. If `typst init @preview/pkg` fails, manually create a `.typ` file
  and `#import` the package instead.

- **Single-pass compilation**: Typst uses single-pass incremental compilation
  for reference resolution (unlike LaTeX's multi-pass approach). Forward
  references work through this incremental system, but complex
  cross-referencing may need explicit `#label()` and `#ref()`. Multi-pass
  workflows (e.g., "Page X of N") require `typst eval` extraction followed
  by `--input` recompilation.

- **HTML export is incomplete**: As of 0.15, HTML export may lack some layout
  features present in PDF output. For production, prefer PDF. HTML is best
  used for agent-side content verification.

- **No stdin piping for templates**: You can pipe complete Typst source via
  stdin (`typst compile - output.pdf`), but there is no `--template` flag
  to pipe content into a named template. To use a template, `typst init` it
  first, then edit the generated files.

### Common Error Messages

| Error | Cause | Fix |
|-------|-------|-----|
| "unknown variable" | Undefined identifier | Check spelling; ensure `#let` before use |
| "expected X, found Y" | Type mismatch | Check function signature in docs |
| "file not found" | Bad import path | Paths resolve relative to current file |
| "unknown font" | Font not installed | Use system fonts or `--font-path` |
| "maximum function call depth exceeded" | Deep recursion | Use iteration instead |
| "can only be used when context is known" | Missing `context` wrapper | Wrap in `context { ... }` |
| "unexpected argument" | `=` instead of `:` for named args | Named args use `:`: `func(name: value)` |
| "expected content, found string" | Content/string type mismatch | Use `[#str-var]` to embed string in content |
| set/show rule has no effect | Rule placed after content | Place set/show rules before the content they target |

## Verification

After creating a document:

1. Does `typst compile file.typ` exit 0?
2. Is the output file non-empty? (`wc -c < output.pdf` > 1000)
3. Does `file output.pdf` report "PDF document"?
4. Can you verify content via HTML export? (`typst compile --features html file.typ /dev/stdout -f html 2>/dev/null`)
5. For templates: does `typst compile main.typ` work from the init'd directory?
6. Are all referenced fonts available? (`typst fonts | grep FontName`)
