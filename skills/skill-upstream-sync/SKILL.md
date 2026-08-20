---
name: skill-upstream-sync
description: Detect and integrate upstream changes to bundled skills that have local modifications. Runs diff review and merges best of both.
version: 1.3.0
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

## Merge Tiering Policy (Ryan-approved 2026-08-19)

**This cron is the SANCTIONED EXCEPTION to "never modify skills in cron"** (the rule in field-notes / skill-maintenance / cron prompts). The exception is scoped: merges run under this policy, report visibly, and genuine conflicts go to Ryan. Everything is git-tracked and revertable (`hermes skills reset --restore <name>`).

| Tier | When | Action | Visibility |
|------|------|--------|-----------|
| 1 | No conflict — upstream-only change, local-only change, or disjoint sections | Auto-merge per Phase 2 | One-line summary |
| 2 | True divergence in different sections, or same-section where ONE side is clearly richer/correct (upstream fixed a bug; local only added env notes) | Auto-merge per Phase 2 | Diff summary in the report |
| 3 | Same-section conflict where BOTH are defensible, OR the target skill has an open SKILL-PATCH / blocked decision ticket in Ryan's lane | **DO NOT merge** — create a SKILL-PATCH ticket (Ryan's lane, blocked `approval-required:`) with both versions + proposed resolution | Ticket in Ryan's lane |

**Tier determination (per skill, before merging):**
1. Read both versions fully (Phase 2 step 1).
2. Changed sections don't overlap → Tier 1. Overlap with a clear winner → Tier 2. Same section, both defensible (upstream redesign vs local customization) → Tier 3.
3. **Board check before merging:** if the target skill has an open SKILL-PATCH ticket (blocked `approval-required:`) or a blocked decision ticket, it's Tier 3 regardless of diff shape — the pending human-gated change wins. A silent merge would overwrite Ryan's in-flight decision.

**Publish rule (Phase 3):** Tier 1–2 merges publish with the report (safety scan stays). Tier 3 NEVER publishes. If ANY skill is Tier 3, skip publishing entirely that run — never push a partial set with a conflicted skill missing. The ticket's resolution decides the merge.

**Report requirement:** the delivery MUST include, per merged skill: what upstream changed, what we kept, and the diff summary for Tier 2. This is the post-hoc review surface — Ryan reads it after the fact; anything wrong is revertable.

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
- **MISSING_LOCAL**: platform-specific skills not applicable (e.g., apple-* on Linux) — ignore. Also surfaces manifest entries whose live copy is gone (skills pruned to `.archive/`) — same ignore, but a large list means stale manifest entries (t_7ef96bdd).
- **LOCAL_ONLY**: local changed, upstream untouched (e.g. stray `__pycache__` or cache files). No merge needed — check `hermes skills list-modified` and clean junk or keep deliberately.

Note: STALE_MANIFEST (local == upstream but manifest hash wrong) is possible in
theory but extremely rare — it would require a Hermes bug in manifest writing. If
it appears, just run `hermes skills reset <name>`.

### Phase 2: Integrate True Divergences

**Apply the Merge Tiering Policy above.** Tier 1–2 divergences merge here; Tier 3 conflicts are NOT merged — create a SKILL-PATCH ticket (Ryan's lane, blocked `approval-required:`) with both versions and a proposed resolution, per the policy. If any skill is Tier 3, skip the publish phase entirely.

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
script output is injected as context. **Apply the Merge Tiering Policy**: merge
Tier 1–2, ticket Tier 3 (SKILL-PATCH, Ryan's lane, blocked `approval-required:`),
skip publish if any skill is Tier 3, and include the per-skill diff summary in
the report.

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
- **SSH URLs trigger the email regex in `sync_published_skills.sh`**: The safety
  scan's email detection pattern (`[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`)
  matches `<user>@<host>` SSH references (e.g., `<git-user>@github.com`) as
  false-positive email addresses. When adding lines to skills synced to a public
  repo, never use literal SSH URLs — use `<ssh-url>` placeholders or descriptive
  text (e.g., "Verify SSH to GitHub works first" instead of `ssh -T <ssh-url>`).
  Existing lines already in the repo won't trigger this (the regex only checks
  `+`-prefixed diff additions), so only newly-added SSH URLs need this treatment.
- **Hidden-dir shadowing (fixed 2026-08-13)**: `find_skill_skel()` globs match
  dot-directories, so a same-named skill under `.archive/` shadowed a broken
  live skill and misclassified it as UPSTREAM_ONLY (ocr-and-documents incident).
  The function now skips any path component starting with `.`.
- **Silent local-only changes (fixed 2026-08-13)**: a local change with no
  upstream change fell through every branch and was reported nowhere (stray
  `__pycache__` incident). Now surfaced as LOCAL_ONLY.

## Cron Job Setup

To run this skill automatically on a schedule:

```bash
# Cron scripts must live in ~/.hermes/scripts, and the scheduler blocks
# symlinks — so create a thin wrapper that execs the CANONICAL copy in the
# skill dir. Never `cp` the script: a second copy drifts (single-copy rule).
# The wrapper is NOT optional: _run_job_script() rejects scripts that resolve
# outside HERMES_HOME/scripts/ (absolute paths and symlink escapes included),
# and the canonical copy must ship inside the skill dir.
mkdir -p ~/.hermes/scripts
cat > ~/.hermes/scripts/detect_skill_divergence.sh << 'EOF'
#!/usr/bin/env bash
exec python3 "$HOME/.hermes/skills/hermes/skill-upstream-sync/scripts/detect_diverged.py" "$@"
EOF
chmod +x ~/.hermes/scripts/detect_skill_divergence.sh
```

Then create the cron job using the `cronjob` tool or `hermes cron create`:

- **Script**: `detect_skill_divergence.sh` (wrapper — runs first, stdout injected as context)
- **Skill**: `skill-upstream-sync`
- **Model**: any strong reasoning model — integration passes benefit from larger context and reasoning capability
- **Schedule**: daily at 9am: `0 9 * * *`
- **Delivery**: `all` for Matrix + other platforms, or `local` for manual review

After the agent finishes merging, the cron prompt should also sync any
published skills to their GitHub repo. The pattern uses a separate script
that copies local skill dirs to a git clone, scans for PII/hardcoded paths,
and pushes only if safe:

```bash
bash ~/.hermes/scripts/sync_published_skills.sh
```

The script lives outside the skill directory (cron requires `~/.hermes/scripts/`).
It's repo-specific — update the skill list and `REPO_DIR` for your own setup.

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
