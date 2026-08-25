#!/usr/bin/env python3
"""Subset the Japanese fonts down to the glyphs the tracer actually draws.

Klee One and Noto Sans JP ship at ~9 MB each because they carry the whole
CJK range. The hiragana build needs 47 characters. Subsetting takes each
font to a few kilobytes of woff2, which is what makes a single-file build
with embedded fonts practical at all.

  Klee One      trace font  — textbook letterforms, hooks kept separate
  Noto Sans JP  print font  — shown small, so the learner sees the shape
                              they'll meet in the wild

Variable fonts are pinned to a single weight first; keeping the variation
axes would carry the whole weight range for no benefit here.

Usage:  make_fonts.py <glyphs.json> <src-dir> <out-dir>

Both fonts are SIL OFL. Their OFL.txt files are copied to the output
directory — the licence has to travel with the font.
"""

import json
import shutil
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

# 人 is not in the gojuon, but it is the project's namesake and the first
# kanji past the kana border — cheap to carry, and the header wants it.
EXTRA = "人"

FONTS = [
    # (source filename, output name, pin variable axes to)
    ("KleeOne-Regular.ttf", "klee-one-kana.woff2", None),
    ("NotoSansJP-var.ttf", "noto-sans-jp-kana.woff2", {"wght": 400}),
]


def build(src, dest, chars, pin):
    font = TTFont(src)

    if pin and "fvar" in font:
        font = instancer.instantiateVariableFont(font, pin, inplace=False)

    opts = subset.Options()
    opts.flavor = "woff2"
    opts.desubroutinize = True
    opts.layout_features = []      # no kerning/ligatures needed for single glyphs
    opts.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14]   # keep licence + family names
    opts.notdef_outline = True
    opts.drop_tables += ["DSIG"]

    subsetter = subset.Subsetter(options=opts)
    subsetter.populate(text=chars)
    subsetter.subset(font)
    font.flavor = "woff2"
    font.save(dest)
    font.close()
    return dest.stat().st_size


def verify(path, chars):
    """Confirm every character we asked for actually made it into the file."""
    font = TTFont(path)
    cmap = font.getBestCmap()
    missing = [c for c in chars if ord(c) not in cmap]
    font.close()
    return missing


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    glyphs_file, src_dir, out_dir = (Path(a) for a in sys.argv[1:])
    out_dir.mkdir(parents=True, exist_ok=True)

    glyphs = json.loads(glyphs_file.read_text(encoding="utf-8"))["glyphs"]
    chars = "".join(g["char"] for g in glyphs) + EXTRA
    print(f"subsetting to {len(chars)} characters "
          f"({len(glyphs)} gojuon + {len(EXTRA)} extra)\n")

    failed = False
    for src_name, out_name, pin in FONTS:
        src, dest = src_dir / src_name, out_dir / out_name
        if not src.exists():
            sys.exit(f"missing source font: {src}")
        before = src.stat().st_size
        after = build(src, dest, chars, pin)

        missing = verify(dest, chars)
        status = "OK" if not missing else f"MISSING {''.join(missing)}"
        if missing:
            failed = True
        print(f"  {out_name:26} {before/1e6:6.1f} MB -> {after/1024:6.1f} KB"
              f"   {before/after:6.0f}x   {status}")

    for ofl in src_dir.glob("*OFL.txt"):
        shutil.copy2(ofl, out_dir / ofl.name)
    print(f"\ncopied {len(list(src_dir.glob('*OFL.txt')))} OFL licence files")

    if failed:
        sys.exit("\nsome characters did not survive subsetting")


if __name__ == "__main__":
    main()
