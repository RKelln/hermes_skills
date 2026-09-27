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
best of both into your local copy, then settle the manifest entry deliberately
(Phase 2 step 5 — a `reset` untracks a merged copy; there is no automatic
re-baseline).

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
| 3 | Same-section conflict where BOTH are defensible, OR the target skill has an open SKILL-PATCH / blocked decision ticket in Ryan's lane | **DO NOT merge** — search all boards (incl. archived) for an existing open SKILL-PATCH or blocked decision ticket on that skill FIRST (method: Tier determination step 3); if one exists, append a dated run-evidence comment only when this run carries a new fact and create nothing. Otherwise create ONE SKILL-PATCH ticket (Ryan's lane, blocked `approval-required:`) with both versions + proposed resolution | Ticket in Ryan's lane |

**Tier determination (per skill, before merging):**
1. Read both versions fully (Phase 2 step 1).
2. Changed sections don't overlap → Tier 1. Overlap with a clear winner → Tier 2. Same section, both defensible (upstream redesign vs local customization) → Tier 3.
3. **Board check before merging:** if the target skill has an open SKILL-PATCH ticket (blocked `approval-required:`) or a blocked decision ticket, it's Tier 3 regardless of diff shape — the pending human-gated change wins. A silent merge would overwrite an in-flight human decision. Search EVERY board, not only `default` (`hermes kanban boards list` enumerates them; a ticket on a non-default board is invisible to a default-board-only search) and include archived tickets — once per board slug:

   ```bash
   hermes kanban boards list
   hermes kanban --board <slug> list --status blocked --json --archived | jq -r '.[] | "<id> | <title>"'
   ```

   `jq` is the unattended-safe filter here (present on this box; verified against a 47-card board). Do NOT use `python3 -c` or `bash -c` for this check: the approval config refuses `-c` script execution in a run with no user present. If `jq` is not enough, write a script file and run it with `python3`.

**Publish rule (Phase 3):** Tier 1–2 merges publish with the report (safety scan stays). Tier 3 NEVER publishes — but the skip is scoped to the CONFLICTED SKILL, never the whole run: if the conflicted skill is in the published set, hold that skill's subtree (never push a partial tree for it) and publish the other ready skills as normal; if the conflicted skill is NOT in the published repo at all, it can never reach the repo under any disposition, so publish the rest as normal. One conflicted skill never holds unrelated reviewed skills. The ticket's resolution decides that one skill's merge.

**Report requirement:** the delivery MUST include, per merged skill: what upstream changed, what we kept, and the diff summary for Tier 2. This is the post-hoc review surface — Ryan reads it after the fact; anything wrong is revertable.

## Built-in Tools First

Hermes ships commands that handle most of the workflow. Use them before the script:

```bash
# See which bundled skills you've modified
hermes skills list-modified

# See your changes vs the shipped stock version
hermes skills diff <skill-name>

# Clears the manifest entry and keeps your copy — for a MERGED copy this ENDS
# TRACKING: nothing puts the entry back (only --restore re-tracks, and that
# discards the merge). Not a post-merge re-baseline; see Phase 2 step 5.
hermes skills reset <skill-name>

# Full restore to pristine upstream (discards your changes)
hermes skills reset <skill-name> --restore
```

**What built-in tools don't cover**: detecting whether the LIVE upstream repo
(`~/.hermes/hermes-agent/skills/`) has changed since the stock snapshot. The
`diff` command compares against the frozen shipped version, not the current
upstream HEAD. The detection script fills this gap — including skills
`list-modified` cannot see at all because they have no manifest entry (UNTRACKED).

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
- **MISSING_LOCAL**: platform-specific skills not applicable (e.g., apple-* on Linux) — ignore. Also surfaces manifest entries whose live copy is gone (skills pruned to `.archive/`) — same ignore, but a large list means stale manifest entries.
- **LOCAL_ONLY**: local changed, upstream untouched (e.g. stray `__pycache__` or cache files). No merge needed — check `hermes skills list-modified` and clean junk or keep deliberately.
- **UNTRACKED**: no `.bundled_manifest` entry at all, but the name exists BOTH live and upstream (and is not on the script's explicit allowlist). Invisible to `hermes skills list-modified` too — same manifest-keyed mechanism — so it can go stale forever. The live instance is a merged copy whose entry was dropped by a post-merge `reset`. Each needs a deliberate disposition (leave untracked and record it, or accept `--restore` and re-apply the merge); never hand-restore the entry (Phase 2 step 5).

Note: STALE_MANIFEST (local == upstream but manifest hash wrong) is possible in
theory but extremely rare — it would require a Hermes bug in manifest writing. If
it appears, run `hermes skills reset <name>` — this is the ONE case where `reset`
is right, because the on-disk copy is byte-identical to the bundled one (Phase 3).

### Phase 2: Integrate True Divergences

**Apply the Merge Tiering Policy above.** Tier 1–2 divergences merge here; Tier 3 conflicts are NOT merged — create a SKILL-PATCH ticket (Ryan's lane, blocked `approval-required:`) with both versions and a proposed resolution, per the policy. **Before creating a SKILL-PATCH ticket, search every board (including archived) for an existing open SKILL-PATCH or blocked decision ticket on that skill; if one exists, append a dated run-evidence comment only when this run carries a new fact (hash change, upstream movement, or board change) and create nothing.** Publishing skips only the conflicted skill's subtree — see the Phase-3 publish rule; a Tier 3 elsewhere in the run never holds the skills that are ready.

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

5. **Settle the manifest entry — do NOT blindly `reset`.** `hermes skills reset <skill-name>` is not a re-baseline for a merged copy: it clears the entry from `~/.hermes/skills/.bundled_manifest`, and nothing puts it back. Only `hermes skills reset <skill-name> --restore` re-tracks a skill, and it does so by discarding the merge. The operator's choice is one of:
   - **(a) leave the manifest entry in place** — the skill keeps surfacing as diverged until upstream moves (the safe default; if the entry is ever dropped, the UNTRACKED class in Phase 1 catches it), or
   - **(b) accept untracking and record it** — state in the report which skill was untracked, when, and why, so the next run does not read its absence as health.
   Never run `--restore` after integration work: it discards the merge. Never hand-write the entry back either — see the reset pitfall.

### Phase 3: Handle Stale Manifests

If STALE_MANIFEST skills appear (local == upstream but manifest hash is old),
just re-baseline — no merge needed, files are already correct:

```bash
hermes skills reset <skill-name>
```

This is not the same case as untracking a merged copy (Phase 2 step 5): here the
on-disk copy is byte-identical to the bundled version, so Hermes re-tracks it on
the next sync pass — re-tracking happens only for a byte-identical copy. Verify by
re-running the detection script: the entry should come back. If it does not, the
copy is not byte-identical and this is a merge case, not a stale-manifest case.

### Phase 4: Report

Summarize what was done:
- Skills merged with upstream
- Skills that were re-baselined (stale manifest only)
- Skills left untracked (merged copies whose entry was dropped) — with the recorded reason
- UNTRACKED findings and the disposition chosen for each
- Skills skipped (no upstream changes worth taking)

## Batch Mode for Cron

When running as a cron job, process ALL diverged skills in one pass. The detection
script output is injected as context. **Apply the Merge Tiering Policy**: merge
Tier 1–2, ticket Tier 3 (SKILL-PATCH, Ryan's lane, blocked `approval-required:`)
after the board dedup check in Tier determination step 3, hold ONLY the Tier-3
skill's subtree from publishing (the scoped Phase-3 publish rule — a conflict on
one skill never holds the rest), and include the per-skill diff summary in the
report.

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
  your current copy — and for a MERGED copy nothing puts the entry back. Only
  `--restore` re-tracks, and it does so by discarding the merge. So `reset` is NOT
  a post-merge step (Phase 2 step 5). Never use --restore after doing integration
  work or you'll lose it.
- **Category mismatch**: If a skill moved categories upstream, the detection
  script may find it under different paths. The manifest tracks by name only,
  so this is handled correctly.
- **Batched resets can be misleading**: `hermes skills reset` always says
  "Cleared manifest entry" even when the skill was already correctly tracked.
  The only way to verify is to re-run the detection script.
- **A reset copy is NOT re-tracked by `sync_skills()`**: an earlier version of
  this list claimed the manifest entry came back after a reset. That holds only
  when the on-disk copy is byte-identical to the bundled one — Hermes re-tracks in
  `_install_new_skill` / `_recover_renamed_skill` only, and both require a
  byte-identical copy. A MERGED copy stays untracked, so it disappears from BOTH
  `hermes skills list-modified` and this detection script. That is the blind spot
  the UNTRACKED class exists to catch. Only `--restore` re-tracks a merged copy,
  and it discards the merge.
- **Hand-restoring the manifest entry is NOT a general fix**: writing the entry
  back as `<name>:<merged _dir_hash>` makes `_update_existing_skill` treat the copy
  as pristine, so the next upstream change REPLACES it with the bundled version
  and the merge is silently discarded. There is no safe general re-track for a
  merged copy: leave the entry out and let UNTRACKED keep surfacing it.
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
3. Run `hermes skills check` — hub skills (installed from a source rather than bundled)
   have no upstream sync job of their own, so this is the only place their pending
   updates surface. Pending updates are a normal report, not a failure: name them in
   the run report and leave the install as a deliberate, separate call.
4. Spot-check one merged skill to confirm both upstream improvements and local
   customizations are present

## References

- `scripts/detect_diverged.py` — Detection script. Run standalone or as a cron
  pre-script to inject divergence data as context.
