# uvx One-Shot CLI: Run Python CLI Tools Without Installation

`uvx` runs any PyPI package's CLI entry point without permanently installing it. Uses `uv`'s fast package resolution (cached after first run). No `pip install`, no venv management, no cleanup.

## Syntax

```bash
uvx <package-name> [subcommand] [options...]
```

First run downloads + caches the package. Subsequent runs are near-instant (uses cached venv).

## When to Use

| Scenario | Example | Use uvx? |
|----------|---------|----------|
| One-off CLI task | `uvx curl-cffi get <url> --impersonate chrome` | ✅ Preferred |
| Script dependency | Tool your Python script imports from | ❌ Use `uv add` or `pip install` |
| Frequent repeated use | Same CLI every session | ❌ Use `uv tool install` (persistent) |
| Testing a tool before deciding | Evaluating a new linter | ✅ Use uvx first, install if it sticks |

## Verified Examples

### curl-cffi — TLS-impersonating web fetcher
```bash
uvx curl-cffi get "https://site-that-blocks.com/page" --impersonate chrome --body -o /tmp/page.html
```

### ruff — Python linter (one-shot)
```bash
uvx ruff check file.py
```

### yamlfix — YAML formatter
```bash
uvx yamlfix config.yaml
```

### typos — Source code spell checker
```bash
uvx typos src/
```

### rich-cli — Syntax highlighting in terminal
```bash
uvx rich-cli code.py --line-numbers
```

## Pitfalls

- **Not all PyPI packages have a CLI entry point.** `uvx` only works if the package defines a `[project.scripts]` entry in pyproject.toml. Test with `uvx <package> --help` to confirm.
- **First run is slow** (download + install). Subsequent runs are cached. Don't judge performance by the first invocation.
- **No isolation guarantees** beyond the cache. If you need strict sandboxing, use Docker or a dedicated venv.
- **Works with `uv` installed** (`which uv`). Check before relying on it.
- **Some CLI tools expect pip-style invocation** (`python -m <package>`). In those cases, `uv run --with <package> python -m <package>` is the equivalent pattern.
