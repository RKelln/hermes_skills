# GitHub Repo Deep Recon (structure, images, deployment)

When a task needs more than the README — directory layout, subcrate docs, container image contents, deployment bundles — use this verified pipeline (hit 2026-08-02 on block/buzz):

## 1. README + key docs via webx (raw.githubusercontent.com)

```bash
webx https://raw.githubusercontent.com/OWNER/REPO/main/README.md \
     https://raw.githubusercontent.com/OWNER/REPO/main/VISION.md \
     --out /tmp/repo.md
```

Multi-URL in one call, tirith-scanned. Raw URLs beat the GitHub HTML pages (cleaner extraction).

## 2. Directory listings via `gh api` — NOT webx on api.github.com

`webx --json` on `api.github.com/.../contents` returns the JSON payload as an **escaped string** inside webx's own envelope — `json.loads` on the whole output fails silently (empty parse). Use authenticated gh instead (clean JSON, `--jq` filters):

```bash
gh api repos/OWNER/REPO/contents/docs --jq '.[].name'
gh api repos/OWNER/REPO/contents --jq '.[].name'
gh api repos/OWNER/REPO/contents/examples/workflows --jq '.[].name'
```

Then fetch the files that matter (`README.md` of subdirs, `.env.example`, compose bundles) via raw.githubusercontent.com + webx.

## 3. Container image inspection without guessing

Sizes (manifest metadata only, no layer download):

```bash
docker manifest inspect ghcr.io/ORG/IMG:tag --verbose > /tmp/m.json
# parse with a script FILE (never pipe-to-interpreter): entries are a list;
# amd64 entry has layers under 'OCIManifest' or 'SchemaV2Manifest' — sum layer sizes
```

Contents + base OS (pulls the image — fine for small images):

```bash
docker run --rm --entrypoint /bin/sh ghcr.io/ORG/IMG:tag -c \
  'head -3 /etc/os-release; ls -la /usr/local/bin; du -h /usr/local/bin/*'
```

This verified (buzz, 2026-08-02): Debian-12 base, glibc-linked standalone binaries extractable for a no-docker server deploy; image sizes 16–117 MB per service.

## 4. Verify claims against the tree, not coverage

Coverage articles overstate what ships. Check the CLI/README command tables against what you saw in the source (e.g. buzz: "Slack and GitHub in one" — but the shipped CLI has no `issues`/`pr` subcommands). Flag doc-vs-reality gaps explicitly.
