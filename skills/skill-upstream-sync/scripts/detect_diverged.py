#!/usr/bin/env python3
"""
Detect bundled skills where local has diverged from upstream.

Three categories:
  TRUE_DIVERGENCE: local != upstream AND both differ from origin
    → User has custom changes, upstream has new changes. Needs merge review.
  MANIFEST_STALE: local == upstream but both differ from origin  
    → Upstream was updated and local was synced but manifest not re-baselined.
    → Fix with: hermes skills reset <name> (no --restore)
  UPSTREAM_ONLY: local == origin, upstream != origin
    → Upstream changed but local untouched. hermes update should handle this.
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
            if skel.parent.name == skill_name:
                return skel
    return None


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

    if missing:
        print(f"MISSING_LOCAL ({len(missing)}): {', '.join(missing)}")

    # Machine-readable report
    report = {
        "true_divergence": true_divergence,
        "true_divergence_count": len(true_divergence),
        "manifest_stale": manifest_stale,
        "manifest_stale_count": len(manifest_stale),
        "upstream_only": upstream_only,
        "upstream_only_count": len(upstream_only),
        "missing": missing,
    }

    print("---REPORT---")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
