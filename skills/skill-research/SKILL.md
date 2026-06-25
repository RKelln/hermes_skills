---
name: skill-research
description: Research existing Hermes skills before building — search all registries, GitHub topics, and awesome lists to find duplicates, adjacent tools, and gaps.
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, skills, research, discovery, pre-build]
    category: hermes
---

# Skill Research

Before building a new Hermes skill, search the ecosystem to avoid reinventing.
This skill searches all known registries, surfaces what already exists, and
identifies whether your idea is novel, adjacent to something, or already solved.

## When to Use

- Before building any new Hermes skill
- When the user says "is there a skill for X?" or "has anyone built Y?"
- When evaluating whether to build vs. install an existing skill

## Discovery Surfaces

Hermes skills live across several registries. Search them all:

| Surface | Command / Location | What it covers |
|---------|-------------------|----------------|
| Browse all | `hermes skills browse` | Unfiltered browse across all sources (~87k skills) |
| All registries | `hermes skills search "<query>"` | skills.sh, clawhub, official, GitHub taps |
| skills.sh | `hermes skills search "<query>" --source skills-sh` | Vercel's public directory (~300 Hermes-compatible skills) |
| ClawHub | `hermes skills search "<query>" --source clawhub` | Community marketplace (~600 skills, some OpenClaw-specific) |
| Official optional | `hermes skills browse --source official` | Shipped with Hermes but not bundled (~100 skills) |
| GitHub topic | `https://github.com/topics/hermes-skills` | Repos tagged by authors on GitHub |
| Awesome list | `https://github.com/0xNyk/awesome-hermes-agent` | Curated list of Hermes tools and skills |
| browse.sh | `hermes skills search "<site>" --source browse-sh` | Site-specific workflows (Airbnb, arXiv, etc.) |

## Procedure

### Phase 0: Check Installed Skills

Before searching the internet, check what's already on disk. You might already
have a skill that does what you need:

```bash
hermes skills list
```

Pay attention to skills in the `hermes` and `devops` categories — maintenance
and meta-skills often live there. Also check `hermes skills browse` for a quick
visual scan across all sources.

### Phase 1: Multi-Query Search

A single query rarely catches everything. Run 3-5 searches with different
phrasings to cover the idea space:

```bash
# Core concept (short, 2-3 words)
hermes skills search "<core idea>"

# Action-oriented (verb + noun)
hermes skills search "<verb> <noun>"  

# Problem-focused (describe what you're solving)
hermes skills search "<problem description>"

# Adjacent terms (synonyms, related domains)
hermes skills search "<synonym or related term>"
```

#### Search Strategy

`hermes skills search` does keyword matching, not semantic search. To get good
results:

- **Start narrow, then broaden**: Begin with your most specific query. If
  nothing, drop words. If too many results, add a distinguishing term.
- **Try both noun and verb forms**: "skill discovery" and "find skills" return
  different results because skills use inconsistent naming conventions.
- **Search by problem, not solution**: "before building check duplicates"
  may find skills that "skill research" misses.
- **Filter by source when results flood**: If a broad query returns 10+
  results, narrow to one source at a time:
  ```bash
  hermes skills search "skill create" --source skills-sh
  hermes skills search "skill create" --source clawhub
  hermes skills search "skill create" --source official
  ```
- **Use `browse` for discovery, `search` for targeting**: `hermes skills browse`
  is good when you're exploring a category. `hermes skills search` is for when
  you have a specific idea.

#### Managing Context

Large search results can flood the agent's context window. To stay lean:

- **Inspect, don't install**: `hermes skills inspect <id>` shows a preview
  without loading the full SKILL.md. Only fetch full content for top candidates.
- **Limit to 2-3 candidates**: You don't need to read every result. Classify
  the top 2-3 most promising, note the rest as "also found, not inspected."
- **Filter by trust level**: Official and trusted sources have fewer, more
  relevant skills. Start there before searching community sources.
- **Skip clearly wrong-scope results**: A "research paper" skill isn't relevant
  to "skill research." Use the one-line descriptions to triage quickly.

Example for a "skill upstream sync" idea (these may return nothing — and that's
useful information; it means the idea space is open):
```bash
hermes skills search "skill sync upstream merge"
hermes skills search "bundled skill update maintain"  
hermes skills search "hermes maintenance divergence"
```
If all return nothing, try broader queries before concluding the idea is novel.

### Phase 2: GitHub Topic Scan

Check the `hermes-skills` topic for repos that don't appear in registry searches:

```bash
# Use web_search or browser to check:
# https://github.com/topics/hermes-skills
```

The topic has ~13 repos. Some are tools (not installer skills) but many contain
skills directories. Read the README of any repo whose description overlaps.

### Phase 3: Inspect Candidates

For each promising result from Phase 1 or 2, inspect before concluding:

```bash
hermes skills inspect <identifier>
```

Read the SKILL.md to understand scope — `inspect` shows a preview, but the full
content may need to be fetched. For skills.sh identifiers (e.g.
`skills-sh/vercel-labs/agent-skills/skill-creator`), the SKILL.md lives at
`https://raw.githubusercontent.com/<owner>/<repo>/main/skills/<name>/SKILL.md`.
For ClawHub skills, use `hermes skills inspect` which fetches the full content.
Many skills have misleading names or descriptions — the actual content tells
you whether it solves your problem.

### Phase 4: Classify and Report

For each candidate found, classify:

- **DUPLICATE**: Does exactly what you planned to build. Install it instead.
- **ADJACENT**: Solves a related but different problem. Note what it does and
  where your idea differs — this helps position your skill for discovery.
- **PARTIAL**: Covers some of your use case. Could extend it via PR or build
  a companion skill that references it.
- **NONE**: Nothing found. Green light to build.

Report format:
```
SKILL RESEARCH: <your idea>

Duplicates (install instead): [list or "none"]
Adjacent (different scope): [skill name — what it does, how yours differs]
Partial (could extend): [skill name — what's covered, what's missing]
Gaps (green light): [aspects with no existing solution]
```

### Phase 5: Position Your Skill

If building new, use the research to position it for discovery:
- Choose a name that won't collide with adjacent skills
- Write a description that makes the scope difference clear
- Add relevant tags (`hermes-skills` GitHub topic, `hermes` tag in frontmatter)
- Mention adjacent skills in your skill's description ("unlike X which does Y,
  this skill does Z")

## GitHub Topic Tagging

When you publish a skill repo, add the `hermes-skills` topic so it appears in
the topic listing. In the repo's "About" section, click the gear icon and add
the topic. This is the primary discovery mechanism on GitHub for Hermes skills.

Also tag with: `hermes-agent`, `agentskills`, and any domain-specific topics.

## Pitfalls

- **Single-query blindness**: Running one search and concluding "nothing exists"
  is the most common mistake. Skills use inconsistent naming — your exact
  query may miss a skill that does exactly what you want under a different name.
- **ClawHub noise**: ClawHub results often contain OpenClaw/Clawdbot-specific
  skills that aren't directly usable in Hermes. Check the description and source
  before assuming compatibility.
- **skills.sh lag**: The skills.sh index may be hours to days behind the latest
  GitHub commits. A skill published yesterday may not appear yet.
- **Awesome list staleness**: The awesome-hermes-agent list is manually curated.
  It may not include recent or niche skills.
- **False negatives from name mismatch**: A skill called "auto-maintain" might
  do exactly what you're searching for as "upstream sync". Search by problem
  description, not just feature name.
- **Desktop/tool repos masquerading as skills**: Some repos tagged `hermes-skills`
  are Hermes-related tools or desktop apps, not installable skills. Read the
  README to distinguish.

## Verification

After completing research:
1. Can you name the closest existing skill and explain how yours differs?
2. Have you searched at least 3 different query phrasings?
3. Have you checked the GitHub topic page?
4. Have you inspected (not just listed) the top 2-3 candidates?
