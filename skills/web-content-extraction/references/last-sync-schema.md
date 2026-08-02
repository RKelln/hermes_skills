# last_sync.json schema

Written by `--sync` mode after each incremental sync run. A downstream agent can
read this file to act on changes without parsing the markdown report.

```json
{
  "timestamp": "2026-06-23T15:14:29.573063+00:00",
  "summary": {
    "new": 3,
    "changed": 1,
    "removed": 0,
    "unchanged_head": 107,
    "unchanged_hash_verified": 825,
    "downgraded": 0,
    "total_tracked": 936
  },
  "new": [
    {
      "url": "https://www.interaccess.org/events/some-new-event",
      "title": "Some New Event",
      "path": "events/some-new-event.md",
      "full_path": "/data/interaccess/pages/events/some-new-event.md",
      "hash": "2467e67fcba2c176"
    }
  ],
  "changed": [
    {
      "url": "https://www.interaccess.org/exhibitions/wired-together",
      "title": "Who Cares for the Cyborg?: Wired Together",
      "path": "vf26-exhibitions/wired-together.md",
      "full_path": "/data/interaccess/pages/vf26-exhibitions/wired-together.md",
      "hash": "e5f6g7h8a1b2c3d4"
    }
  ],
  "removed": [
    {
      "url": "https://www.interaccess.org/events/old-event",
      "title": "Old Event",
      "path": "events/old-event.md"
    }
  ],
  "errors": [
    {
      "url": "https://www.interaccess.org/broken",
      "error": "HTTP 500"
    }
  ],
  "data_dir": "/data/interaccess",
  "manifest_path": "/data/interaccess/manifest.json",
  "pages_dir": "/data/interaccess/pages"
}
```

## Summary field breakdown

| Field | Meaning |
|-------|---------|
| `new` | URLs in sitemap that weren't in manifest |
| `changed` | Existing URLs whose normalized content hash genuinely differs |
| `removed` | URLs in manifest but missing from current sitemap |
| `unchanged_head` | Skipped via matching HTTP HEAD signal (Last-Modified or ETag) — zero scrape cost |
| `unchanged_hash_verified` | HEAD was inconclusive, but normalized hash matched stored — scraped but confirmed unchanged |
| `downgraded` | Flagged as changed in check phase, but re-check hash matched in write phase — not a real change |
| `total_tracked` | Total URLs in current sitemap (after filtering) |

The `unchanged_head` + `unchanged_hash_verified` + `downgraded` + `changed` + `new` should equal `total_tracked` (minus removals).

## Agent consumption pattern

1. Read `last_sync.json`
2. Check `summary.new` + `summary.changed` — if > 0, there's work to do
3. Iterate `new` + `changed` arrays
4. For each entry, `read_file` the markdown at `full_path`
5. Update wiki/knowledge base with the content
6. For `removed` entries, mark corresponding wiki pages as archived

The `hash` field is a SHA-256 prefix (first 16 chars) of the normalized markdown content.
Compare against previous hashes to detect content drift between sync and wiki update.

## Change detection pipeline

```
sitemap.xml → diff against manifest
  ├─ new URLs → scrape, write, report [NEW]
  ├─ missing URLs → mark removed in manifest, report [REMOVED]
  └─ existing URLs → for each:
       ├─ HEAD Last-Modified/ETag matches manifest? → skip (unchanged_head)
       └─ HEAD inconclusive? → scrape, normalize, hash
            ├─ hash matches stored? → unchanged (hash_verified)
            └─ hash differs? → scrape again in write loop, re-check hash
                 ├─ still differs? → changed (write file, report [CHANGED])
                 └─ now matches? → downgraded (false alarm, no file write)
```
