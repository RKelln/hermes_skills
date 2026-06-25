# Hermes Meta-Skills

Three skills that make the Hermes Agent ecosystem self-improving:
research before building, build with quality gates, maintain against upstream changes.

## Skills

### `/skill-research` — Research before building

Search all registries + GitHub topics + awesome lists before building a new skill.
Classifies findings as duplicate, adjacent, partial, or none. Avoids reinventing.

### `/skill-builder` — Build with quality gates

Full pipeline from idea to published skill: research existing solutions, author
SKILL.md with proper conventions, test end-to-end, independent subagent review, publish.

### `/skill-upstream-sync` — Maintain against upstream

Detect when customized bundled skills have upstream changes. Runs an LLM-driven
integration pass to merge the best of both, then re-baselines so future updates flow.

## Install

```bash
hermes skills tap add RKelln/hermes_skills
hermes skills install RKelln/hermes_skills/skill-research
hermes skills install RKelln/hermes_skills/skill-builder
hermes skills install RKelln/hermes_skills/skill-upstream-sync
```

## Use

```
/skill-research       # Before building: is there already a skill for this?
/skill-builder        # Build a new skill with research + review pipeline
/skill-upstream-sync  # After hermes update: merge upstream changes into customized skills
```

## Requirements

- Hermes Agent (any recent version)
- `skill-research` is a prerequisite for `skill-builder` (Phase 1 delegates to it)
- `skill-upstream-sync` works standalone or as a cron job
