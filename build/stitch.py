#!/usr/bin/env python3
"""Stitch the engine and one script pack into a single self-contained HTML.

Takes the tracer engine from an existing build, swaps in a script pack's
glyph list, stroke book and fonts, and writes a new versioned file to dist/.

    stitch.py <engine.html> <pack-dir> <out.html>

Every substitution is checked: if an anchor stops matching because the engine
moved on, the build fails loudly rather than quietly emitting a file with the
old script still in it. That failure mode has already cost this project real
work — a save button that reported success while writing nothing.

Fixes applied to the engine on the way through:

  * window.storage is given a real localStorage-backed implementation. The
    engine calls it behind `if(window.storage)` guards but never defines it,
    so in an ordinary browser every save and load silently did nothing.
  * A failed save now says so instead of toasting "saved ✓" regardless.
  * restore() merges over the baked-in stroke book instead of replacing it,
    so recording one glyph no longer discards the defaults for the other 45.
"""

import base64
import json
import re
import sys
from pathlib import Path

VOWELS = "aiueo"          # gojuon column order
GRID_COLS = 5


class Stitch:
    """Applies anchored substitutions and refuses to lose one silently."""

    def __init__(self, text):
        self.text = text
        self.log = []

    def sub(self, what, pattern, repl, count=1, flags=0):
        new, n = re.subn(pattern, lambda _: repl, self.text, count=count, flags=flags)
        if n != count:
            raise SystemExit(
                f"stitch failed: '{what}' matched {n} time(s), expected {count}.\n"
                f"  pattern: {pattern[:90]}\n"
                f"  The engine has probably changed shape — fix the anchor."
            )
        self.text = new
        self.log.append(what)


def js_string(obj):
    """Compact JSON safe to drop straight into a <script> block."""
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            .replace("</", "<\\/"))


def build_letters(glyphs):
    """[char, row-label, romaji, note, row-name, column, row] per glyph.

    The engine destructures the first five; the trailing two drive explicit
    grid placement so the ya and wa rows keep their gaps instead of closing
    up into a dense block.
    """
    rows, heads, letters = [], {}, []
    for g in glyphs:
        if g["row"] not in rows:
            rows.append(g["row"])
            heads[g["row"]] = g["char"]   # first glyph of a row names the row
    for g in glyphs:
        rom = g["romaji"]
        standalone = rom == "n"           # ん belongs to no column
        col = 1 if standalone else VOWELS.index(rom[-1]) + 1
        row = len(rows) + 1 if standalone else rows.index(g["row"]) + 1
        letters.append([
            g["char"],
            "" if standalone else heads[g["row"]] + "行",
            rom,
            g.get("hookNote", ""),
            "" if standalone else f"{g['row']}-row",
            col,
            row,
        ])
    return letters, len(rows) + 1


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    engine_path, pack_dir, out_path = (Path(a) for a in sys.argv[1:])

    engine = engine_path.read_text(encoding="utf-8")
    pack = json.loads((pack_dir / "pack.json").read_text(encoding="utf-8"))
    glyphs = json.loads((pack_dir / "glyphs.json").read_text(encoding="utf-8"))["glyphs"]
    book = json.loads((pack_dir / "strokes.json").read_text(encoding="utf-8"))

    letters, grid_rows = build_letters(glyphs)
    version = pack["version"]

    # ---- fonts: base64 the woff2 files the pack names
    embedded, font_defs = {}, []
    for f in pack["fonts"]:
        data = (Path(pack["fontDir"]) / f["file"]).read_bytes()
        if data[:4] != b"wOF2":
            sys.exit(f"{f['file']} is not woff2 (got {data[:4]!r})")
        embedded[f["key"]] = base64.b64encode(data).decode("ascii")
        font_defs.append({"id": f["id"], "label": f["label"],
                          "family": f["family"], "b64": f["key"]})

    s = Stitch(engine)

    s.sub("title", r"<title>[^<]*</title>", f"<title>{pack['title']}</title>")
    s.sub("brand", r'<div class="brand">.*?</div>',
          f'<div class="brand">{pack["brand"]} <span id="ver"></span></div>',
          flags=re.S)
    s.sub("app version", r"const APP_VERSION='[^']*';",
          f"const APP_VERSION='{version}';")
    s.sub("boot toast", r"toast\('build v[^']*'\)", f"toast('build v{version}')")
    s.sub("header count", r'<div class="count" id="count">[^<]*</div>',
          f'<div class="count" id="count">1 / {len(letters)}</div>')

    s.sub("embedded fonts", r"EMBEDDED_FONTS=\{.*?\};",
          f"EMBEDDED_FONTS={js_string(embedded)};", flags=re.S)
    s.sub("font list", r"const FONTS=\[.*?\];",
          f"const FONTS={js_string(font_defs)};", flags=re.S)
    s.sub("default font", r"let fontId='[^']*';",
          f"let fontId='{font_defs[0]['id']}';")

    s.sub("letters", r"const LETTERS=\[.*?\];", f"const LETTERS={js_string(letters)};",
          flags=re.S)

    # ---- grid: explicit placement, so empty cells stay empty
    s.sub("grid columns", r"grid-template-columns:repeat\(\d+,1fr\)",
          f"grid-template-columns:repeat({GRID_COLS},1fr)")
    s.sub("grid render",
          r"LETTERS\.forEach\(\(L,i\)=>\{const b=document\.createElement\('button'\);"
          r"b\.textContent=L\[0\];b\.className=\(fontBook\(\)\.letters\[L\[0\]\]\?'rec':''\)"
          r"\+\(i===idx\?' cur':''\);b\.onclick=\(\)=>load\(i\);gr\.appendChild\(b\);\}\);",
          "LETTERS.forEach((L,i)=>{const b=document.createElement('button');"
          "b.textContent=L[0];b.className=(fontBook().letters[L[0]]?'rec':'')"
          "+(i===idx?' cur':'');"
          "if(L[5]){b.style.gridColumn=L[5];b.style.gridRow=L[6];}"
          "b.onclick=()=>load(i);gr.appendChild(b);});")

    # ---- metadata line: 'a-row', not 'a-row class'
    s.sub("class label", r"\$\('cls'\)\.textContent=cls\+' class'\+",
          "$('cls').textContent=cls+")

    # ---- the baked stroke book, and a restore() that doesn't clobber it
    default_book = {"fonts": book["fonts"]}
    s.sub("teacher init",
          r"let TEACHER=\{version:2,activeFont:'[^']*',fonts:\{\},customFonts:\[\]\};",
          f"const DEFAULT_BOOK={js_string(default_book)};\n"
          f"let TEACHER={{version:2,activeFont:'{font_defs[0]['id']}',"
          "fonts:JSON.parse(JSON.stringify(DEFAULT_BOOK.fonts)),customFonts:[]};")

    s.sub("restore merge",
          r"async function restore\(\)\{[^\n]*?\}\n",
          "async function restore(){ try{ if(!window.storage) return;\n"
          "  const r=await window.storage.get('hito-teacher-strokes',false);\n"
          "  if(!r||!r.value) return; const saved=JSON.parse(r.value);\n"
          "  if(saved.activeFont) TEACHER.activeFont=saved.activeFont;\n"
          "  if(saved.customFonts) TEACHER.customFonts=saved.customFonts;\n"
          "  for(const fid in (saved.fonts||{})){\n"
          "    TEACHER.fonts[fid]=TEACHER.fonts[fid]||{letters:{}};\n"
          "    Object.assign(TEACHER.fonts[fid].letters, saved.fonts[fid].letters||{});\n"
          "  }\n"
          "}catch(_){} }\n")

    # ---- persistence that actually persists, and reports when it can't
    s.sub("persist", r"async function persist\(\)\{[^\n]*?\}\n",
          "async function persist(){ try{ if(!window.storage) return false;\n"
          "  return await window.storage.set('hito-teacher-strokes',"
          "JSON.stringify(TEACHER),false);\n"
          "}catch(_){ return false; } }\n")

    s.sub("save honesty",
          r"persist\(\); toast\('saved ✓'\);",
          "persist().then(ok=>toast(ok?'saved ✓':"
          "'SAVE FAILED — export before you close this tab'));")

    s.sub("storage keys", r"'nirathai-mastery'", "'hito-mastery'", count=2)

    # The font-loaded probe measures glyphs that must exist in the pack's
    # fonts. It shipped measuring Thai characters, which a kana-only subset
    # does not contain — so both measurements matched and every font was
    # reported as blocked.
    s.sub("font probe", r"measureText\('[^']*'\)",
          f"measureText('{pack['probeChars']}')", count=2)

    s.sub("export filename", r"a\.download='[^']*';",
          f"a.download='{pack['exportName']}';")

    shim = (
        "<script>\n"
        "// The engine calls window.storage but never defined it, so every save\n"
        "// and load was a silent no-op in an ordinary browser. This is that\n"
        "// implementation. set() returns false when the write genuinely failed\n"
        "// (quota, private browsing) so the UI can tell the truth about it.\n"
        "window.storage=window.storage||{\n"
        "  async get(k){ try{ const v=localStorage.getItem(k);"
        " return v==null?null:{value:v}; }catch(_){ return null; } },\n"
        "  async set(k,v){ try{ localStorage.setItem(k,v); return true; }"
        "catch(_){ return false; } }\n"
        "};\n"
        "</script>\n"
    )
    s.sub("storage shim", r"<body>", "<body>\n" + shim, count=1)

    s.sub("credit", r"</body>",
          f'<div class="credit">{pack["credit"]}</div>\n</body>')
    s.sub("credit style", r"</style>",
          ".credit{max-width:min(92vw,520px);margin:0 auto 26px;font-size:11px;"
          "line-height:1.5;color:var(--ash);opacity:.65;text-align:center}\n</style>")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(s.text, encoding="utf-8")

    print(f"applied {len(s.log)} substitutions:")
    for entry in s.log:
        print(f"  · {entry}")
    print(f"\n{out_path}  {out_path.stat().st_size/1024:.0f} KB  "
          f"({len(letters)} glyphs, {grid_rows} grid rows, {len(font_defs)} fonts)")


if __name__ == "__main__":
    main()
