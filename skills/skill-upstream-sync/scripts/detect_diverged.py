#!/usr/bin/env python3
"""
Detect bundled skills where local has diverged from upstream.

Five categories:
  TRUE_DIVERGENCE: local != upstream AND both differ from origin
    → User has custom changes, upstream has new changes. Needs merge review.
  MANIFEST_STALE: local == upstream but both differ from origin
    → Upstream was updated and local was synced but manifest not re-baselined.
    → Fix with: hermes skills reset <name> (no --restore)
  UPSTREAM_ONLY: local == origin, upstream != origin
    → Upstream changed but local untouched. hermes update should handle this.
  LOCAL_ONLY: local != origin, upstream == origin
    → Local changed but upstream untouched (e.g. stray cache files). No merge
    needed; check `hermes skills list-modified` and clean or keep deliberately.
  UNTRACKED: no .bundled_manifest entry at all, yet the name exists BOTH live
    and upstream, and is not in the explicit allowlist below.
    → Invisible to the manifest-keyed classes above AND to `hermes skills
    list-modified` (same manifest-keyed mechanism), so it can go stale
    forever. A merged copy whose entry was dropped by `hermes skills reset`
    lands here; so does any older case of the same shape. Each entry needs a
    deliberate disposition: for a merged copy there is no safe automatic
    re-baseline (see skill-upstream-sync SKILL.md, Phase 2 step 5).
"""

import hashlib
import json
import os
import sys
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
SKILLS_DIR = HERMES_HOME / "skills"
UPSTREAM_SKILLS_DIR = HERMES_HOME / "hermes-agent" / "skills"
MANIFEST_PATH = SKILLS_DIR / ".bundled_manifest"

# Explicit allowlist for the UNTRACKED class: local skill dirs that exist under
# upstream too but have NO manifest entry, and are deliberately left that way.
# One-line reason per name, so the class cannot become permanent daily noise.
# Every name here is a user-owned local variant:
# it was never a manifest-tracked bundled copy on this box (verified 2026-09-26:
# absent from .bundled_manifest, and `hermes skills list-modified` cannot see
# it), so there is no bundled baseline for this pipeline to merge FROM.
# Removing a name re-surfaces it as an UNTRACKED finding.
UNTRACKED_ALLOWLIST = {
    # user-owned research variant; installed outside hermes update, no baseline
    "arxiv": "user-owned local variant, never manifest-tracked on this box",
    # user-owned creative variant; not a tracked bundled copy
    "claude-design": "user-owned local variant, never manifest-tracked on this box",
    # user-owned knowledge-base variant; not a tracked bundled copy
    "llm-wiki": "user-owned local variant, never manifest-tracked on this box",
    # user-owned note-taking variant; not a tracked bundled copy
    "obsidian": "user-owned local variant, never manifest-tracked on this box",
    # user-owned agent-CLI variant; not a tracked bundled copy
    "opencode": "user-owned local variant, never manifest-tracked on this box",
    # user-owned media variant; not a tracked bundled copy
    "youtube-content": "user-owned local variant, never manifest-tracked on this box",
}

# Deliberately NOT allowlisted: `grounded-citations`. It is the live instance of
# this defect — merged from upstream + local fix 2026-09-12, then untracked by a
# post-merge `hermes skills reset`, so nothing re-adds the entry (only
# `--restore` re-tracks, and that discards the merge). It must keep surfacing
# here until an operator records a disposition for it.


def dir_hash(directory: Path) -> str:
    """Match Hermes' _dir_hash: hash all files with their relative paths."""
    hasher = hashlib.md5()
    for fpath in sorted(directory.rglob("*")):
        if fpath.is_file():
            rel = fpath.relative_to(directory)
            hasher.update(str(rel).encode("utf-8"))
            hasher.update(fpath.read_bytes())
    return hasher.hexdigest()


def find_skill_skel(skills_root: Path, skill_name: str) -> Path | None:
    if not skills_root.is_dir():
        return None
    for depth in range(1, 4):
        pattern = "/".join(["*"] * depth) + "/SKILL.md"
        for skel in skills_root.glob(pattern):
            # Hidden dirs (e.g. .archive/) must not shadow a live skill: a
            # same-named archived copy would be hashed instead, misclassifying
            # the live skill (2026-08-13: ocr-and-documents reported
            # upstream_only while its live copy was broken).
            rel_parts = skel.relative_to(skills_root).parts[:-1]
            if any(p.startswith(".") for p in rel_parts):
                continue
            if skel.parent.name == skill_name:
                return skel
    return None


def find_live_skels() -> dict[str, Path]:
    """Every live skill skeleton under SKILLS_DIR, keyed by skill name.

    Hidden path components (.archive/, .trash/, dotfiles) are skipped for the
    same reason find_skill_skel() skips them.
    """
    found: dict[str, Path] = {}
    if not SKILLS_DIR.is_dir():
        return found
    for depth in range(1, 4):
        pattern = "/".join(["*"] * depth) + "/SKILL.md"
        for skel in SKILLS_DIR.glob(pattern):
            rel_parts = skel.relative_to(SKILLS_DIR).parts[:-1]
            if any(p.startswith(".") for p in rel_parts):
                continue
            found.setdefault(skel.parent.name, skel)
    return found


def scan_untracked(manifest: dict[str, str]) -> list[dict]:
    """Live skills with no manifest entry whose name also exists upstream.

    Being absent from the manifest is not by itself interesting: most local
    skills are purely local (never bundled). The class is the intersection —
    absent from the manifest AND present in the upstream checkout — which is
    exactly the set the manifest-keyed detection cannot see.
    """
    untracked = []
    for skill_name, local_skel in sorted(find_live_skels().items()):
        if skill_name in manifest or skill_name in UNTRACKED_ALLOWLIST:
            continue
        upstream_skel = find_skill_skel(UPSTREAM_SKILLS_DIR, skill_name)
        if upstream_skel is None:
            continue  # purely local skill — nothing to diverge from
        category = str(local_skel.parent.parent.relative_to(SKILLS_DIR))
        untracked.append({
            "skill": skill_name,
            "category": category,
            "local_path": str(local_skel),
            "upstream_path": str(upstream_skel),
        })
    return untracked


def parse_manifest() -> dict[str, str]:
    if not MANIFEST_PATH.is_file():
        print(json.dumps({"error": "no manifest"}))
        sys.exit(1)
    manifest = {}
    for line in MANIFEST_PATH.read_text().strip().splitlines():
        line = line.strip()
        if not line:
            continue
        name, _, h = line.partition(":")
        manifest[name] = h
    return manifest


def main():
    manifest = parse_manifest()

    true_divergence = []
    manifest_stale = []
    upstream_only = []
    local_only = []
    missing = []

    for skill_name, origin_hash in sorted(manifest.items()):
        local_skel = find_skill_skel(SKILLS_DIR, skill_name)
        upstream_skel = find_skill_skel(UPSTREAM_SKILLS_DIR, skill_name)

        if not local_skel:
            missing.append(skill_name)
            continue
        if not upstream_skel:
            continue  # skill removed upstream, ignore

        local_hash = dir_hash(local_skel.parent)
        upstream_hash = dir_hash(upstream_skel.parent)

        local_changed = local_hash != origin_hash
        upstream_changed = upstream_hash != origin_hash

        if not local_changed and not upstream_changed:
            continue  # nothing changed

        if local_changed and upstream_changed:
            if local_hash == upstream_hash:
                manifest_stale.append(skill_name)
            else:
                category = str(local_skel.parent.parent.relative_to(SKILLS_DIR))
                true_divergence.append({
                    "skill": skill_name,
                    "category": category,
                    "local_path": str(local_skel),
                    "upstream_path": str(upstream_skel),
                    "origin_hash": origin_hash,
                    "local_hash": local_hash,
                    "upstream_hash": upstream_hash,
                })
        elif upstream_changed and not local_changed:
            upstream_only.append(skill_name)
        elif local_changed and not upstream_changed:
            local_only.append(skill_name)

    untracked = scan_untracked(manifest)

    # Human-readable summary
    if true_divergence:
        names = ", ".join(d["skill"] for d in true_divergence)
        print(f"DIVERGED ({len(true_divergence)}): {names}")
    else:
        print("OK: no true divergences")

    if manifest_stale:
        names = ", ".join(manifest_stale)
        print(f"STALE_MANIFEST ({len(manifest_stale)}): {names}")

    if upstream_only:
        names = ", ".join(upstream_only)
        print(f"UPSTREAM_ONLY ({len(upstream_only)}): {names}")

    if local_only:
        names = ", ".join(local_only)
        print(f"LOCAL_ONLY ({len(local_only)}): {names}")

    if missing:
        print(f"MISSING_LOCAL ({len(missing)}): {', '.join(missing)}")

    if untracked:
        names = ", ".join(d["skill"] for d in untracked)
        print(f"UNTRACKED ({len(untracked)}): {names}")

    # Machine-readable report
    report = {
        "true_divergence": true_divergence,
        "true_divergence_count": len(true_divergence),
        "manifest_stale": manifest_stale,
        "manifest_stale_count": len(manifest_stale),
        "upstream_only": upstream_only,
        "upstream_only_count": len(upstream_only),
        "local_only": local_only,
        "local_only_count": len(local_only),
        "missing": missing,
        "untracked": untracked,
        "untracked_count": len(untracked),
        "untracked_allowlisted_count": len(UNTRACKED_ALLOWLIST),
    }

    print("---REPORT---")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
