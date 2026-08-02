# UTF-8 Double-Encoding Artifacts: Troubleshooting Table

When scraped text shows mangled characters like `â€™`, `â€œ`, or `Weâre`, the
root cause is UTF-8 bytes being decoded through a single-byte codec. The
three-byte UTF-8 sequences for curly quotes, dashes, and punctuation all start
with `0xE2 0x80`. The third byte determines the character.

## Byte → Artifact Mapping

| Character | UTF-8 bytes | Latin-1 artifact | cp1252 artifact | Visible as |
|-----------|-------------|-----------------|-----------------|------------|
| `'` U+2018 | E2 80 98 | `â\u0080\u0098` | `â€˜` | left single quote |
| `'` U+2019 | E2 80 99 | `â\u0080\u0099` | `â€™` | right single quote |
| `"` U+201C | E2 80 9C | `â\u0080\u009c` | `â€œ` | left double quote |
| `"` U+201D | E2 80 9D | `â\u0080\u009d` | **UNDEFINED** | right double quote |
| `–` U+2013 | E2 80 93 | `â\u0080\u0093` | `â€"` (U+201C) | en dash |
| `—` U+2014 | E2 80 94 | `â\u0080\u0094` | `â€"` (U+201D) | em dash |
| `…` U+2026 | E2 80 A6 | `â\u0080\u00a6` | `â€¦` | ellipsis |
| `′` U+2032 | E2 80 B2 | `â\u0080\u00b2` | `â€²` | prime |

## Critical: 0x9D is undefined in cp1252

Byte 0x9D (right double quote's third byte) is **undefined in Windows-1252**.
Python's `cp1252` codec raises `UnicodeDecodeError` when it encounters this
byte. This means:

- The cp1252 artifact `â€"` (with U+201D) can ONLY come from the em dash
  path (0xE2 0x80 0x94 → â€" where " is U+201D).
- Right double quote (`"`) artifacts only arrive through the Latin-1 path:
  `\u00e2\u0080\u009d` → `"`.
- When checking the encoding path for an unknown artifact, look at the THIRD
  character. If it's U+201D, it's an em dash, not a quote.

## Partial Artifacts

Sometimes only the first byte survives (`â` by itself where a quote should be).
This happens when the C1 control characters from the Latin-1 path
(U+0080-U+009F) are stripped by intermediate systems. The fix handles this via
the full-sequence replacements — but `â` alone is too ambiguous for safe
single-character replacement (it's a legitimate character in French/Portuguese).

## Diagnosing New Artifacts

1. Find the mangled string in output
2. Check if it starts with `â` (U+00E2)
3. If the second char is `€` (U+20AC) → cp1252 path — check third char
4. If the second char is invisible/U+0080 → Latin-1 path — check third char
5. Work backwards: third char → cp1252 or Latin-1 mapping → original byte → UTF-8 character
6. Add the fix pair to the appropriate list in `_normalize_md()`

## Side-by-Side: cp1252 Byte Mapping (0x80-0x9F)

| Byte | cp1252 char | Unicode | Byte | cp1252 char | Unicode |
|------|------------|---------|------|------------|---------|
| 0x80 | € | U+20AC | 0x90 | (undef) | — |
| 0x82 | ‚ | U+201A | 0x91 | ' | U+2018 |
| 0x83 | ƒ | U+0192 | 0x92 | ' | U+2019 |
| 0x84 | „ | U+201E | 0x93 | " | U+201C |
| 0x85 | … | U+2026 | 0x94 | " | U+201D |
| 0x86 | † | U+2020 | 0x95 | • | U+2022 |
| 0x87 | ‡ | U+2021 | 0x96 | – | U+2013 |
| 0x88 | ˆ | U+02C6 | 0x97 | — | U+2014 |
| 0x89 | ‰ | U+2030 | 0x98 | ˜ | U+02DC |
| 0x8A | Š | U+0160 | 0x99 | ™ | U+2122 |
| 0x8B | ‹ | U+2039 | 0x9A | š | U+0161 |
| 0x8C | Œ | U+0152 | 0x9B | › | U+203A |
| 0x8E | Ž | U+017D | 0x9C | œ | U+0153 |
| | | | 0x9F | Ÿ | U+0178 |

Note: 0x81, 0x8D, 0x8F, 0x90, 0x9D, 0x9E are undefined in cp1252.
