---
name: skill-builder
description: Build and publish production-ready Hermes skills — research, author, review, ship.
version: 1.1.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, skills, authoring, build, publish, quality]
    category: hermes
    related_skills: [skill-research, requesting-code-review]
---

# Skill Builder

Build production-ready Hermes skills from idea to publication. This skill
orchestrates the full pipeline: research existing solutions, author the
SKILL.md, test it, run an independent review, and publish.

**Prerequisites:** Install `skill-research` first — Phase 1 delegates to it.
Install `requesting-code-review` if you want structured review output.

**How this differs from existing skill-builders:** Most skill-creator skills
(Hermes and otherwise) focus on the authoring step. This one adds pre-build
research (don't reinvent) and independent review (don't ship broken). If you
only need the authoring step, ClawHub's `create-skill` or GitHub's
`re-sianturi/skill-builder-for-hermes` may suffice.

## When to Use

- User says "build a skill for X" or "create a skill that does Y"
- User has an idea for a reusable agent capability
- User wants to publish a skill for others to use

## Hermes Skill Conventions

Before building, know the rules. These are hard-won from shipping skills.

### Portability

- Use `SKILL_DIR` for self-references. Define it early: *"SKILL_DIR refers to
  the directory containing this SKILL.md file."*
- Scripts use `HERMES_HOME` env var (fallback `~/.hermes`), never hardcoded paths
- Cron scripts go in `$HERMES_HOME/scripts/` — copy them there in setup docs

### Structure

- YAML frontmatter: `name`, `description` (brief, one-line), `version`,
  `platforms`, `metadata.hermes.tags`, `metadata.hermes.category`
- Optional frontmatter: `author`, `license`, `metadata.hermes.related_skills`,
  `metadata.hermes.requires_toolsets`, `metadata.hermes.fallback_for_toolsets`,
  `required_environment_variables`
- Sections: When to Use, Quick Reference (if useful), Procedure (phased),
  Pitfalls, Verification

### Safety and Tone

- No PII (usernames, machine names, home paths other than `~/.hermes`)
- No vendor-lock (model names in examples, not requirements)
- No marketing language ("revolutionary", "game-changing", "powerful")
- Instructional tone — tell the agent what to DO

### Scripts

- Prefer Python stdlib when possible (no pip install step for users)
- Read-only detection scripts are safer (no accidental writes)
- If your script hashes files, match Hermes' `_dir_hash` — see the
  implementation in the Pitfalls section below

### Conditional Activation

Skills can declare when they should or shouldn't appear based on available
tools. Consider adding these to frontmatter if your skill is a fallback
for when another tool is unavailable:

```yaml
metadata:
  hermes:
    fallback_for_toolsets: [web]     # Show only when web tools unavailable
    requires_toolsets: [terminal]    # Show only when terminal available
```

## Quick Reference

| Phase | Tool / Command |
|-------|---------------|
| Research | `hermes skills search`, `hermes skills inspect`, GitHub topics |
| Mine | Clone adjacent repos, read sub-files, extract reusable features |
| Author | `write_file` to `~/.hermes/skills/<cat>/<name>/SKILL.md` |
| Test | Load with `/skill <name>`, exercise the procedure |
| Review | `delegate_task` with fresh subagent context |
| Publish | `hermes skills publish <dir> --to github --repo <owner>/<repo>` |

## Procedure

### Phase 1: Research (don't reinvent)

Load the `skill-research` skill (must be installed) and search all registries:

1. Run 3-5 `hermes skills search` queries with different phrasings
2. Check `https://github.com/topics/hermes-skills`
3. Inspect top candidates with `hermes skills inspect <id>`
4. Classify findings: DUPLICATE, ADJACENT, PARTIAL, or NONE

If a DUPLICATE exists: tell the user and offer to install it instead.
If ADJACENT or PARTIAL: proceed to Phase 1b — mine them for reusable features.
If NONE: green light. Proceed to Phase 2.

### Phase 1b: Mine Adjacent Skills (extract reusable features)

Adjacent and partial skills aren't just competitors — they're free research.
Before writing your own skill, pull them down and mine them for value:

1. Clone the repo for the most comprehensive adjacent skill(s):
   ```bash
   cd /tmp && git clone --depth 1 <repo-url> <name>
   ```

2. Read the SKILL.md and all sub-files (look for `references/`, `*.md` siblings,
   `scripts/`, `examples/`). Adjacent skills often have multiple sub-files.

3. Identify what to integrate into your skill:
   - **Features you missed** — sub-commands, flags, workflows not in your plan
   - **Pitfalls they found** — error tables, gotchas, known failure modes
   - **Agent-specific patterns** — how they solve the "agent can't see PDFs"
     problem, verification methods, CLI introspection tricks
   - **Conversion/migration tables** — if the tool interoperates with others

4. **Do NOT** copy their skill wholesale or import their scripts. Extract the
   knowledge and re-express it in your skill's voice and structure.

5. Report to the user: what you found, what you're integrating, what you're
   intentionally leaving out and why. Be specific about omissions — e.g.,
   "left out package publishing (niche), search scripts (require embedded
   data files), and academic specifics (covered by separate skill)." This
   shows you made conscious tradeoffs, not that you missed things.

This step turns 5 existing skills from "competition" into "research budget."
It is not optional — if ADJACENT or PARTIAL skills exist, mine them first.

### Phase 2: Author the SKILL.md

Write the skill to `~/.hermes/skills/<category>/<skill-name>/SKILL.md`.

**Frontmatter template (required fields):**
```yaml
---
name: <kebab-case-name>
description: "<brief one-line description>"
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [<3-8 relevant tags>]
    category: <category>
---
```

**Optional frontmatter fields** (add as needed):
```yaml
author: <name>
license: MIT
metadata:
  hermes:
    related_skills: [<other-skill-names>]
    requires_toolsets: [terminal]
    fallback_for_toolsets: [web]
required_environment_variables:
  - name: API_KEY
    prompt: Description of what this key is for
```

**Body structure:**
1. One-paragraph overview
2. "## When to Use" — trigger conditions
3. "## Quick Reference" — optional, one-table command reference
4. "## Procedure" — numbered phases with exact commands
5. "## Pitfalls" — known failure modes and fixes
6. "## Verification" — how to confirm it worked

For tool-oriented skills (CLI tools, APIs, compilers), add a
"### Common Error Messages" subsection under Pitfalls — a 3-column
table (Error / Cause / Fix) that maps exact error strings to their
causes and fixes. This turns the skill into a self-service debugger.

**Scripts:** Place in `scripts/` subdirectory. Document with exact invocation
commands. If needed for cron, add a "## Cron Job Setup" section.

**References:** Only create `references/` if agents NEED them to operate.
Human-only reference material should be inline or omitted.

### Phase 3: Test the Skill

Before review, load and exercise the skill:

1. Load it: `/skill <name>` in a Hermes session, or use the skill as instructed
2. Walk through the Procedure steps as an agent would
3. Verify every command in the skill actually works
4. Fix any broken commands, missing steps, or unclear instructions

Testing catches things you missed while authoring. Don't skip this.

### Phase 4: Independent Review

Spawn a critical subagent review. This is a Hermes `delegate_task` tool call
(not raw Python — run it directly, not inside a code block):

```
delegate_task(
    goal="Review this skill for publication readiness. Check: PII, hardcoded paths, factual accuracy, completeness, tone, clarity, safety, self-consistency. Be critical.",
    context="Skill at ~/.hermes/skills/<category>/<skill-name>/",
    toolsets=["terminal", "file"]
)
```

Address every finding before proceeding. If the reviewer flags something,
fix it. If you disagree, explain why.

Common issues to catch before the reviewer does:
- `SKILL_DIR` used but not defined
- Hardcoded paths anywhere
- Model name recommendations
- Dead references to non-existent files
- Missing `mkdir -p` in setup commands
- Description too long or self-contradicting advice

### Phase 5: Publish

**Before publishing, run a safety scan** on the staged changes. A quick grep
catches PII, hardcoded paths, and vendor-lock language that reviews can miss:

```bash
git diff --cached | grep -qiE "(api_key|secret|token|password).*=.*['\"][a-zA-Z0-9_-]{20,}" && echo "WARNING: possible secret"
git diff --cached | grep -qE "^\+.*/home/[^/]+/(?!\.hermes)" && echo "WARNING: hardcoded user path"
git diff --cached | grep -qiE "model.*(required|must|should use)" && echo "WARNING: vendor-lock"
```

If any warnings fire, fix before pushing. This is cheap insurance — catching
a leaked credential or environment-specific path before it hits a public repo.

Then publish to GitHub:

**Path A: `hermes skills publish` (preferred, needs fork scope)**

```bash
hermes skills publish <skill-dir> --to github --repo <owner>/<repo>
```

This requires a GitHub token with `repo` and `fork` scopes. Fine-grained
tokens often lack fork permission — if you get "token lacks permission to
fork repos", use Path B.

**Path B: Direct git push (fallback)**

```bash
# Clone the empty repo, copy skills in, push
cd /tmp && gh repo clone <owner>/<repo>
cp -r ~/.hermes/skills/<category>/<skill-name> <repo>/skills/
cd <repo> && git add -A && git commit -m "Add <skill-name>"
git remote set-url origin git@github.com:<owner>/<repo>.git  # use SSH
git push origin main
```

SSH push bypasses token scope issues. Verify SSH works first:
`ssh -T git@github.com`

**Path C: Add to existing taps repo (most common)**

When you already have a taps repo and are adding a new skill (or updating
existing ones), clone, copy, update the README, and push:

```bash
cd /tmp && gh repo clone <owner>/<repo>
cp -r ~/.hermes/skills/<category>/<skill-name> <repo>/skills/
```

Also copy any meta-skills you updated during the build (skill-builder,
skill-research, etc.) — they live in the same taps repo:

```bash
cp -r ~/.hermes/skills/hermes/skill-builder <repo>/skills/
```

Then update the README to list the new skill with a one-paragraph description
matching the format of existing entries. Add install instructions if this is
a prerequisite for other skills. Finally:

```bash
cd <repo> && git add -A && git commit -m "Add <skill-name>; update meta-skills"
git push origin main
```

This is the typical pattern: you're maintaining a growing collection, not
creating a fresh repo per skill.

**Post-publish (all paths):**
- Add `hermes-skills` topic to the GitHub repo (Settings → Topics in web UI)
- Also tag: `hermes-agent`, `agentskills`
- Verify the skill appears in `hermes skills search` within 24 hours

## Skill Directory Layout

```
<skill-name>/
├── SKILL.md              # Required — main skill document
├── scripts/              # Optional — Python/Bash scripts
│   └── <script>.py
└── references/           # Optional — only if agents need them
    └── <doc>.md
```

Keep it minimal. Every file adds context cost. A great skill is a single
SKILL.md with no scripts and no references.

## What NOT to Include

- **Session notes or draft comments** — clean these before publishing
- **"Publishing This Skill" sections** — meta-noise for end users
- **Personal anecdotes** ("we learned this when...")
- **GitHub issue response drafts**
- **TODO comments or work-in-progress markers**

## Pitfalls

- **SKILL_DIR undefined**: The most common publication blocker. Define it at the
  top of your Procedure section.
- **md5sum vs _dir_hash**: If your skill hashes files, match Hermes' `_dir_hash`
  — it hashes ALL files in the skill directory with their relative paths, not
  just SKILL.md. Here's the exact implementation from `skills_sync.py`:
  ```python
  import hashlib
  from pathlib import Path

  def dir_hash(directory: Path) -> str:
      hasher = hashlib.md5()
      for fpath in sorted(directory.rglob("*")):
          if fpath.is_file():
              rel = fpath.relative_to(directory)
              hasher.update(str(rel).encode("utf-8"))
              hasher.update(fpath.read_bytes())
      return hasher.hexdigest()
  ```
  A plain `md5sum` on one file gives different results and causes false positives.
- **Manifest blindness**: The `.bundled_manifest` tracks content hashes.
  `hermes skills diff` compares against the FROZEN stock, not live upstream.
  If your skill depends on detecting upstream changes, you need a custom script.
- **Cron script paths**: Cron jobs require scripts in `$HERMES_HOME/scripts/`,
  not inside the skill directory. Always add `cp` + `mkdir -p` instructions.
- **Category confusion**: Categories are subdirectories in `~/.hermes/skills/`.
  Valid categories include `hermes`, `devops`, `creative`, `github`, `research`,
  `productivity`, `software-development`, `autonomous-ai-agents`, `mlops`,
  `media`, `note-taking`, and others. Choose a category that matches your
  skill's domain.
- **Over-polishing**: Skills improve with use. Ship v1.0.0 with the core
  procedure, then patch as pitfalls emerge. Don't add features you haven't
  tested in practice.
- **Publish token permissions**: `hermes skills publish` needs a GitHub token
  with `repo` AND `fork` scopes. Fine-grained tokens and some OAuth tokens
  lack fork permission. Fallback: clone the empty repo, copy skills in
  manually, and push via SSH (`git@github.com:<owner>/<repo>.git`).
  SSH push bypasses all token scope issues.
- **Reviewers need the CLI, not just the file**: When the skill covers a CLI
  tool, include the tool's binary path and version in the reviewer's context
  (e.g., "Typst 0.15.0 is installed at /path/to/typst"). A reviewer who can
  only read the SKILL.md can catch PII and tone issues but not broken commands.
  Give them `toolsets=["terminal","file"]` so they can actually run commands.

## Verification

After building:
1. Does it use `SKILL_DIR` for all self-references?
2. Is the description brief and one-line (fits in a list view)?
3. Does it have a Pitfalls section with at least 3 real gotchas?
4. Does it have a Verification section with specific checks?
5. Would a new user understand the Procedure from start to finish?
6. Did you test the skill end-to-end before review?
7. Did an independent reviewer approve it?
