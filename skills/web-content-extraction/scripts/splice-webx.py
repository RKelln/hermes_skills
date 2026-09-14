#!/usr/bin/env python3
"""splice-webx.py — replace webx's embedded JSONLD_EXTRACT_HELPER constant with a
reference to the standalone jsonld_extract.py file.

Done as a script rather than a text patch because the constant is a 53-line
triple-quoted string full of escaped regex — reproducing it byte-exactly in a patch
old_string is how you corrupt a file. Anchors on the two constant names instead.

Writes webx.new and leaves the original untouched; the caller verifies syntax and
moves it into place.
"""
import os
import re
import sys

# webx sits beside this script; realpath matters because the scripts dir is normally
# reached through a symlink (webx is exposed as ~/.local/bin/webx).
WEBX = os.path.join(os.path.dirname(os.path.realpath(__file__)), "webx")

NEW = '''# JSON-LD / __NEXT_DATA__ extraction lives in jsonld_extract.py beside this script.
# It used to be an embedded 53-line string constant; it is a file now because it is
# testable on its own (python3 jsonld_extract.py page.html) and it is the piece most
# likely to need fixing. realpath matters: webx is normally invoked through a symlink
# in ~/.local/bin, so __file__ alone would point at the wrong directory.
JSONLD_HELPER_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "jsonld_extract.py"
)


'''

src = open(WEBX, encoding="utf-8").read()

start = src.index("JSONLD_EXTRACT_HELPER = textwrap.dedent(")
end = src.index("REGEX_EXTRACT_HELPER = textwrap.dedent(")

# sanity: the removed region must be the helper only
removed = src[start:end]
assert "articleBody" in removed and "REGEX" not in removed, "anchor check failed"
assert removed.count("textwrap.dedent") == 1, "unexpected extra dedent in region"

out = src[:start] + NEW + src[end:]

# the constant must no longer be referenced anywhere
leftover = re.findall(r"JSONLD_EXTRACT_HELPER", out)
if leftover:
    print(f"WARNING: {len(leftover)} stale reference(s) to JSONLD_EXTRACT_HELPER remain",
          file=sys.stderr)

open(WEBX + ".new", "w", encoding="utf-8").write(out)
print(f"spliced: removed {len(removed)} chars, added {len(NEW)}, "
      f"file {len(src)} -> {len(out)} chars")
