---
name: skill-upstream-sync
description: Detect and integrate upstream changes to bundled skills that have local modifications. Runs diff review and merges best of both.
version: 1.1.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, skills, maintenance, sync]
    category: hermes
---

# Skill Upstream Sync

Detect bundled skills where you have local modifications AND upstream has published
changes. For each, do an integration pass: read both versions, diff them, merge the
best of both into your local copy, then re-baseline the manifest so future
`hermes update` runs work normally.

Also handles the simpler case where your local copy matches upstream but the
manifest is stale (just re-baseline, no merge needed).

## When to Use

- After `hermes update` when you see `~N user-modified (kept)` in the output
- Periodically, to catch upstream improvements to skills you've customized
- Before a big task where stale skills might cause problems

## Built-in Tools First

Hermes ships commands that handle most of the workflow. Use them before the script:

```bash
# See which bundled skills you've modified
hermes skills list-modified

# See your changes vs the shipped stock version
hermes skills diff <skill-name>

# Re-baseline after integrating (keep your copy, unlock future updates)
hermes skills reset <skill-name>

# Full restore to pristine upstream (discards your changes)
hermes skills reset <skill-name> --restore
```

**What built-in tools don't cover**: detecting whether the LIVE upstream repo
(`~/.hermes/hermes-agent/skills/`) has changed since the stock snapshot. The
`diff` command compares against the frozen shipped version, not the current
upstream HEAD. The detection script fills this gap.

## Procedure

`SKILL_DIR` refers to the directory containing this SKILL.md file
(`~/.hermes/skills/hermes/skill-upstream-sync`).

### Phase 1: Detect

First, use the built-in tool to see what's user-modified:

```bash
hermes skills list-modified
```

Then run the detection script to find skills where upstream ALSO changed:

```bash
python3 SKILL_DIR/scripts/detect_diverged.py
```

The script produces:
- **DIVERGED**: local ≠ upstream AND both differ from origin — needs merge review
- **UPSTREAM_ONLY**: local untouched, upstream changed — `hermes update` will handle
- **MISSING_LOCAL**: platform-specific skills not applicable (e.g., apple-* on Linux) — ignore

Note: STALE_MANIFEST (local == upstream but manifest hash wrong) is possible in
theory but extremely rare — it would require a Hermes bug in manifest writing. If
it appears, just run `hermes skills reset <name>`.

### Phase 2: Integrate True Divergences

For each skill in DIVERGED:

1. **Read both versions** using read_file:
   - Local: `~/.hermes/skills/<category>/<skill>/SKILL.md`
   - Upstream: `~/.hermes/hermes-agent/skills/<category>/<skill>/SKILL.md`

2. **Analyze the diff**: What did upstream change? What did we change? Are they
   in conflict or in different sections? Categories:
   - **Upstream improvements we want**: new commands, fixed docs, better procedures
   - **Our customizations worth keeping**: environment-specific notes, additional
     pitfalls, modified procedures we prefer
   - **Conflicts**: same section changed differently — needs judgment

3. **Merge strategy** (default):
   - Take upstream structural/metadata improvements (YAML frontmatter, new sections)
   - Preserve our environment-specific additions (local paths, machine-specific notes)
   - When same section diverges: prefer the more detailed/correct version
   - Add a `## Local Customizations` section at the bottom to preserve unique
     additions that don't fit cleanly upstream

4. **Write the merged version** using patch or write_file

5. **Re-baseline** so future updates work:
   ```bash
   hermes skills reset <skill-name>
   ```

### Phase 3: Handle Stale Manifests

If STALE_MANIFEST skills appear (local == upstream but manifest hash is old),
just re-baseline — no merge needed, files are already correct:

```bash
hermes skills reset <skill-name>
```

### Phase 4: Report

Summarize what was done:
- Skills merged with upstream
- Skills that were re-baselined (stale manifest only)
- Skills skipped (no upstream changes worth taking)

## Batch Mode for Cron

When running as a cron job, process ALL diverged skills in one pass. The detection
script output is injected as context.

### One-at-a-time mode
When running interactively, process one skill at a time so the user can review.

## Pitfalls

- **Hash algorithm must match Hermes' `_dir_hash`**: Hermes hashes the entire
  skill directory (all files + their relative paths), NOT just SKILL.md. A plain
  `md5sum SKILL.md` gives different results and causes false positives — our
  detection script originally had this bug and reported 60 divergences when only
  5 were real. The fixed script uses `dir_hash()` matching `_dir_hash` exactly
 (hashes all files in the skill directory with their relative paths,
 not just SKILL.md).
- **hermes-agent skill itself**: Heavily customized with environment-specific
  knowledge. Upstream adds new CLI commands and config sections regularly.
  When upstream has moved ahead significantly (version bumps), take upstream
  wholesale via `hermes skills reset --restore` and re-apply specific
  customizations — don't piecemeal-merge dozens of small changes.
- **apple-* and platform-specific skills**: Missing on Linux — expected, not a
  problem. These are macOS/iOS-only skills that don't apply.
- **hermes skills reset without --restore**: Clears the manifest entry but keeps
  your current copy. The NEXT sync re-baselines. This is what you want after a
  merge — never use --restore after doing integration work or you'll lose it.
- **Category mismatch**: If a skill moved categories upstream, the detection
  script may find it under different paths. The manifest tracks by name only,
  so this is handled correctly.
- **Batched resets can be misleading**: `hermes skills reset` always says
  "Cleared manifest entry" even when the skill was already correctly tracked.
  The only way to verify is to re-run the detection script.
- **Skills reappear in list-modified after reset**: After `hermes skills reset`,
  `sync_skills()` re-adds the manifest entry with the current `_dir_hash`. If
  the skill was correctly tracked before (no actual divergence), it disappears
  from `list-modified`. If it was truly diverged and you just re-baselined,
  it may briefly reappear until the next `sync_skills()` pass updates the hash.
  Re-run the detection script to confirm.

## Cron Job Setup

To run this skill automatically on a schedule:

```bash
# Copy the detection script to the cron-accessible location
mkdir -p ~/.hermes/scripts
cp SKILL_DIR/scripts/detect_diverged.py \
   ~/.hermes/scripts/detect_skill_divergence.py
```

Then create the cron job using the `cronjob` tool or `hermes cron create`:

- **Script**: `detect_skill_divergence.py` (runs first, stdout injected as context)
- **Skill**: `skill-upstream-sync`
- **Model**: any strong reasoning model — integration passes benefit from larger context and reasoning capability
- **Schedule**: daily at 9am: `0 9 * * *`
- **Delivery**: `all` for Matrix + other platforms, or `local` for manual review

## Verification
1. Run `hermes skills list-modified` — should show only skills you intentionally
   haven't merged yet
2. Run the detection script again — DIVERGED should be empty or contain only
   skills you explicitly chose to skip
3. Run `hermes skills check` to confirm no hub skill updates pending
4. Spot-check one merged skill to confirm both upstream improvements and local
   customizations are present

## References

- `scripts/detect_diverged.py` — Detection script. Run standalone or as a cron
  pre-script to inject divergence data as context.
