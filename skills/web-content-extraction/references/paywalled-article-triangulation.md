# Paywalled / Blocked Article Triangulation

**Problem**: Primary source (NYT, WSJ, Bloomberg, etc.) is fully blocked by DataDome/Cloudflare/paywall. Browser returns captcha. Curl returns captcha. Google cache returns captcha. Jina.ai returns "SecurityCompromiseError".

**Approach**: Don't keep hammering the primary source. Reconstruct key facts from secondary coverage, organizational press pages, and reporter social posts.

## Multi-source triangulation workflow

When the primary URL is blocked:

### 1. Check aggregator summaries

Search the article title + date on search engines. Many aggregators (Benton Institute, MSN, Apple News) provide 2-3 paragraph summaries of each article they syndicate:

```
web_search(query='"Big Companies Aim to Ease A.I. Transition" "Lydia DePillis"')
```

Aggregator snippets often include the lede, key stats, and main argument — enough to reconstruct 60% of the article's substance.

### 2. Search for the reporter's own social posts

Reporters often post links to their own articles with a 1-2 sentence summary on LinkedIn/X:

```
Search for the reporter's name + article title on LinkedIn/X.
LinkedIn news stories often carry the WSJ/NYT article with the reporter's own commentary.
```

LinkedIn was particularly useful in this session — Lydia DePillis's LinkedIn post paraphrased the article lede: "Job loss fears have soured many Americans on AI, while Congress and the White House do nothing to cushion the impact."

### 3. Find secondary coverage of the same news event

When a major announcement launches (e.g., a new nonprofit), multiple outlets cover it. Find outlets with less restrictive paywalls:

- TNW (The Next Web) — often open access, thorough detail
- Politico — may have 3-5 free articles/month
- Yahoo Finance / Business Wire — press releases are always open
- Regional papers (Inquirer, etc.) — may syndicate the NYT article with free preview
- Tech-focused outlets (TechCrunch, The Verge, Wired)

For this session: TNW had a comprehensive standalone story with full detail on RAISE US's budget, state pilots, quotes, and strategic analysis — arguably more useful than the NYT original.

### 4. Go to the source organization's press page

Every new initiative has a press page. Find it:

```
web_search(query='"RAISE US" press' OR 'raiseus.ai/press')
```

The press page lists all coverage with one-line summaries, plus the organization's own press release with full quotes, donor lists, and strategic framing. For this session: RAISE US's About page had leadership bios, full board/advisory lists, and a complete set of founding partner quotes.

### 5. Search for the official press release

New nonprofits, policy initiatives, and coalition launches issue press releases via Business Wire/PR Newswire, often syndicated on Yahoo Finance:

```
web_search(query='launch RAISE US Raimondo "Business Wire"')
```

Press releases are always open-access and provide the organization's own framing, full quote blocks, and complete partner/board lists.

### 6. Check for republishing sites

Some sites auto-republish NYT content via RSS or API (e.g., `theengineeringofconsciousexperience.com`). These are usually just the first 100 words + "Source link" — not useful for depth, but confirm the article exists and shows the byline/dateline.

### 7. Assemble the reconstruction

From all sources, extract and deduplicate:

| Fact type | Primary source | Triangulated source |
|-----------|---------------|-------------------|
| Lede/argument | Aggregator snippets, reporter social | 1-2 sentences |
| Key stats ($500M, $1B target) | TNW, press release | Exact numbers |
| Quote blocks | Press release | Full, verified quotes |
| Partner/board lists | Press page, Business Wire | Complete lists |
| Strategic framing/analysis | TNW, aggregator context | Context for significance |
| Congressional/WH political context | Aggregator snippets, TNW | Political vacuum framing |

### 8. Add HFF-specific strategic analysis

For HFF-relevant articles, the final step is mapping the news to HFF's mission:
- Does this validate HFF's premise (infrastructure gap)?
- Does it open institutional partnership opportunities?
- Does it align with HFF programs (RAISE, AI Tinkerers, Policy Lab)?
- Does the leadership have relevant background (AI Safety Institute, open source positions)?
- Who on HFF's network might have connections to this organization?

This was the pattern for the HFF KB update — the NYT article was a data point, not the deliverable. The deliverable was the strategic significance analysis appended to the HFF knowledge base.

## Concrete example: NYT "Big Companies Aim to Ease A.I. Transition..." (June 25, 2026)

| Attempt | Result |
|---------|--------|
| `browser_navigate(NYT URL)` | DataDome captcha |
| `browser_navigate(AMP version)` | DataDome captcha |
| `curl -H "User-Agent: ..."` | DataDome captcha |
| `r.jina.ai/` proxy | "SecurityCompromiseError" |
| Google cache | Google captcha ("unusual traffic") |
| Wayback Machine | No recent snapshot |
| **Philadelphia Inquirer** (syndicated) | Paywall — got lede only |
| **Benton Institute aggregator** | Summary snippet |
| **TNW** (thenextweb.com) | **Full article, open access** |
| **RAISE US press page** | Full quotes, partner list |
| **RAISE US About page** | Full bios, advisor quotes |
| **LinkedIn (Lydia DePillis)** | Reporter's own summary |
| **Yahoo Finance press release** | Organizational framing |

**Time spent**: ~8 browser navigations + 4 searches over 2-3 turns. The blocked primary source was never needed — all key facts were available from secondary sources.

## Pitfalls

- **Do not cycle on the blocked primary source.** Three failed attempts is enough. Each attempt costs a turn and adds nothing. After attempt 3, switch to the triangulation workflow.
- **The Wayback Machine won't have today's article.** Recent-breaking stories get cached within 24-48 hours at best. Don't waste the call.
- **Syndicated versions often have the same paywall.** Check for free preview (lede paragraph visible before the gate) but assume it's behind the same wall.
- **Republishing sites only have 100 words.** Sites like `theengineeringofconsciousexperience.com` auto-pull the first paragraph from RSS. Don't deep-inspect them.
- **Jina.ai blocks domains with previous abuse.** If NYT blocked Jina.ai for DDoS, it will keep blocking. No point retrying with different URL formats.
- **Save extracted content immediately.** Triangulation involves navigating 5+ pages. Browser_console returns raw text once — `write_file` it before navigating away.
