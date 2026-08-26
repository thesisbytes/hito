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

    # ---- the shadow: draw it from the stroke data, not the font
    #
    # The guide comes from KanjiVG, whose centrelines describe KanjiVG's
    # letterforms. Overlaid on Klee One only 66% of the path fell inside the
    # glyph's ink — and that is the ceiling across every possible scale and
    # offset, so it is a shape difference, not a misalignment. Hooks diverge
    # most, which is exactly where two textbook designs disagree.
    #
    # Thai never hit this: its recordings were captured by tracing the
    # rendered glyph. Deriving the target from the same data as the guide is
    # what makes the two agree by construction.
    if pack.get("shadow", "none") != "font":
        # sub() replaces literally — backreferences do not expand — so read
        # the value out first and write the whole replacement.
        m = re.search(r"const BASE_F=([\d.]+);", s.text)
        if not m:
            sys.exit("cannot find BASE_F to anchor the shadow scale on.")
        s.sub("shadow mode", r"const BASE_F=[\d.]+;",
              f"const BASE_F={m.group(1)};"
              f"const SHADOW_SCALE={pack.get('shadowScale', 2.4)};"
              f"let SHADOW_MODE='{pack.get('shadow', 'none')}';")
        s.sub("shadow from strokes",
              r"g\.save\(\); g\.font=glyphFont\(size\); g\.textAlign='center'; "
              r"g\.textBaseline='middle';\s*\n\s*const rec=mode==='practice'&&teacherStrokes\(\);"
              r"\s*\n\s*g\.fillStyle=[^\n]*\n\s*"
              r"if\(done\)\{g\.shadowColor='rgba\(233,196,106,\.9\)';g\.shadowBlur=40;\}\s*\n\s*"
              r"g\.fillText\(L,W/2,H/2\+size\*\.06\); g\.restore\(\);",
              "const rec=mode==='practice'&&teacherStrokes();\n"
              "  if(rec&&PATH.length&&SHADOW_MODE!=='font'){\n"
              "    // 'none' leaves only the trail: road ahead, dots, and the\n"
              "    // stroke already made. A thick shadow bulges on the outside\n"
              "    // of curves, so the thin trail down its centreline cannot\n"
              "    // cover it, and the stacked glows read as blur.\n"
              "    if(SHADOW_MODE==='strokes'||done){\n"
              "      paintPath(g,0,PATH.length-1,{alpha:done?.5:.13,blur:done?28:7,"
              "scale:SHADOW_SCALE,nocore:true,"
              "color:done?'rgba(255,241,184,.95)':'#e9c46a'});\n"
              "    }\n"
              "  } else {\n"
              "    g.save(); g.font=glyphFont(size); g.textAlign='center'; "
              "g.textBaseline='middle';\n"
              "    g.fillStyle=done?'rgba(255,241,184,.9)':(mode==='record'?"
              "'rgba(127,209,196,.13)':'rgba(233,196,106,.16)');\n"
              "    if(done){g.shadowColor='rgba(233,196,106,.9)';g.shadowBlur=40;}\n"
              "    g.fillText(L,W/2,H/2+size*.06); g.restore();\n"
              "  }", flags=re.S)

    # ---- strict following: no skipped strokes, no free boundary crossing
    #
    # The original follow() searched prog..prog+LOOK and kept any jump
    # (prog = max(prog, best)), so one lucky touch 24 points ahead skipped
    # everything between. Enough leaps reached the end without tracing the
    # middle, and the dot teleported on the way. SEGEND also auto-advanced,
    # so a single unbroken line satisfied a four-stroke glyph — which defeats
    # the hook problem the whole hiragana pack exists for.
    #
    # Three changes: the search is clamped to the current stroke, every path
    # point the pen actually passes near is recorded, and completion needs
    # real coverage rather than merely arriving at the last index.
    if pack.get("strictFollow"):
        s.sub("strict state",
              r"let PATH=\[\],SEGEND=new Set\(\),prog=0,offCount=0;",
              "let PATH=[],SEGEND=new Set(),prog=0,offCount=0;\n"
              "let SEGS=[],segIdx=0,hit=null,awaitLift=false,travel=0,lastN=null,PATHLEN=0;"
              f"const COVER_MIN={pack.get('coverThreshold', 0.85)},END_SLACK=4,"
              f"MAX_TRAVEL={pack.get('maxTravel', 2.5)},TRAVEL_EPS=0.006;")

        s.sub("build segments",
              r"if\(rec\)\{ rec\.forEach\(st=>\{ const R=resample\(st,"
              r"Math\.max\(6,Math\.round\(\(resample\(st\)\.len\|\|\.05\)/0\.008\)\)\);"
              r" PATH\.push\(\.\.\.R\); SEGEND\.add\(PATH\.length-1\); \}\); \}",
              "SEGS=[];segIdx=0;awaitLift=false;\n"
              "  if(rec){ rec.forEach(st=>{ const a=PATH.length;"
              " const R=resample(st,Math.max(6,Math.round((resample(st).len||.05)/0.008)));"
              " PATH.push(...R); SEGEND.add(PATH.length-1); SEGS.push([a,PATH.length-1]); }); }\n"
              "  hit=new Uint8Array(PATH.length); travel=0; lastN=null;\n"
              "  PATHLEN=0; for(const g of SEGS) for(let i=g[0];i<g[1];i++)\n"
              "    PATHLEN+=Math.hypot(PATH[i+1].x-PATH[i].x,PATH[i+1].y-PATH[i].y);")

        s.sub("strict follow",
              r"function follow\(q,down\)\{ const n=norm\(q\); let best=-1,bd=R_ON\(\);\n"
              r"  for\(let i=prog;i<=Math\.min\(PATH\.length-1,prog\+LOOK\);i\+\+\)"
              r"\{ const d=Math\.hypot\(n\.x-PATH\[i\]\.x,n\.y-PATH\[i\]\.y\);"
              r" if\(d<bd\)\{bd=d;best=i;\} \}\n"
              r"  if\(best>=0\)\{ q\.on=true; prog=Math\.max\(prog,best\); offCount=0;"
              r" smudge=Math\.max\(0,smudge-2\); spark\(q\.x,q\.y,q\.p\);\n"
              r"    if\(SEGEND\.has\(prog\)&&prog<PATH\.length-1\) prog\+\+;\n"
              r"    runeUI\(\); drawGuide\(\); if\(prog>=PATH\.length-2\) conjure\(\); return; \}",
              "function covered(){ if(!hit) return 0; let c=0;"
              " for(let i=0;i<hit.length;i++) c+=hit[i]; return c/hit.length; }\n"
              "function follow(q,down){ const n=norm(q); const seg=SEGS[segIdx];\n"
              "  if(!seg) return;\n"
              "  // How far the pen has actually travelled. A correct trace runs\n"
              "  // about the length of the path; a scribble runs many times it,\n"
              "  // and that is the one thing a scribble cannot disguise. Single\n"
              "  // stroke glyphs have no lift barrier, so without this they let\n"
              "  // a dense scribble through on coverage alone.\n"
              "  if(down) lastN=null;\n"
              "  if(!lastN){ lastN={x:n.x,y:n.y}; }\n"
              "  else { const step=Math.hypot(n.x-lastN.x,n.y-lastN.y);\n"
              "    // Sub-threshold movement is digitizer noise, not travel.\n"
              "    // Summing every raw sample would let a jittery pen inflate\n"
              "    // the ratio and fail an honest trace.\n"
              "    if(step>=TRAVEL_EPS){ travel+=step; lastN={x:n.x,y:n.y}; } }\n"
              "  if(awaitLift){   // stroke finished — the pen must come up first\n"
              "    // Overshooting the end slightly is just finishing the stroke,\n"
              "    // not an error. Only complain once the pen leaves the end and\n"
              "    // keeps going, which is what running two strokes together\n"
              "    // actually looks like.\n"
              "    const e=PATH[seg[1]];\n"
              "    if(Math.hypot(n.x-e.x,n.y-e.y)<R_ON()*1.6){ q.on=true; return; }\n"
              "    q.on=false; offCount++;\n"
              "    if(offCount===1) toast('lift the pen — the next stroke is separate');\n"
              "    if(offCount%14===1) zap(q); return; }\n"
              "  const R=R_ON(), lo=Math.max(prog,seg[0]), hi=Math.min(seg[1],prog+LOOK);\n"
              "  // Coverage and progress answer different questions and must not\n"
              "  // share a window. Progress is ordering, so it only looks ahead.\n"
              "  // Coverage is 'did the pen actually go here', so it sweeps the\n"
              "  // whole stroke — otherwise a hook that curls back within LOOK\n"
              "  // lets prog leap and leaves the skipped points unmarked.\n"
              "  for(let i=seg[0];i<=seg[1];i++)\n"
              "    if(Math.hypot(n.x-PATH[i].x,n.y-PATH[i].y)<R) hit[i]=1;\n"
              "  let best=-1,bd=R;\n"
              "  for(let i=lo;i<=hi;i++){ const d=Math.hypot(n.x-PATH[i].x,n.y-PATH[i].y);\n"
              "    if(d<bd){bd=d;best=i;} }\n"
              "  if(best>=0){ q.on=true; prog=Math.max(prog,best); offCount=0;"
              " smudge=Math.max(0,smudge-2); spark(q.x,q.y,q.p);\n"
              "    // Near the end counts as the end: requiring the exact final\n"
              "    // index makes completion depend on where samples happen to\n"
              "    // land, and a sparse sample can stop one point short.\n"
              "    if(prog>=seg[1]-END_SLACK){ for(let i=prog;i<=seg[1];i++) hit[i]=1; prog=seg[1];\n"
              "      if(segIdx>=SEGS.length-1){\n"
              "        const cov=covered(), eff=PATHLEN?travel/PATHLEN:1;\n"
              "        if(cov>=COVER_MIN&&eff<=MAX_TRAVEL){"
              " runeUI(); drawGuide(); conjure(); return; }\n"
              "        toast(cov<COVER_MIN\n"
              "          ? `missed ${Math.round((1-cov)*100)}% of the path — trace all of it`\n"
              "          : 'too much wandering — follow the stroke, do not scrub');\n"
              "        fizzle(); return;\n"
              "      }\n"
              "      awaitLift=true;   // hooks are separate strokes, so prove it\n"
              "    }\n"
              "    runeUI(); drawGuide(); return; }")
        s.sub("advance on pen down",
              r"if\(PATH\.length&&mode==='practice'\)\{ const q=pos\(e\);"
              r" if\(PATH\.length\) follow\(q,true\); \}",
              "if(PATH.length&&mode==='practice'){\n"
              "    // A lift is what separates one stroke from the next, so the\n"
              "    // pen coming down is what advances to it.\n"
              "    if(awaitLift&&segIdx<SEGS.length-1){"
              " segIdx++; prog=SEGS[segIdx][0]; awaitLift=false; offCount=0; }\n"
              "    follow(pos(e),true); }")

        # fizzle rewinds prog; the segment cursor and coverage have to follow it
        # back or the two disagree and the glyph becomes untraceable.
        s.sub("fizzle resets strict state",
              r"function fizzle\(\)\{ smudge=0; offCount=0;"
              r" prog=Math\.max\(0,Math\.round\(prog\*0\.5\)\);",
              "function fizzle(){ smudge=0; offCount=0;"
              " prog=Math.max(0,Math.round(prog*0.5));\n"
              "  segIdx=0; while(segIdx<SEGS.length-1&&prog>SEGS[segIdx][1]) segIdx++;\n"
              "  awaitLift=false; if(hit) for(let i=prog;i<hit.length;i++) hit[i]=0;")

    # ---- difficulty curve
    #
    # Mastery shrank the glyph 12% a level AND tightened tolerance in the same
    # proportion. Those compound: a smaller target is already harder to hit,
    # and a hand's precision does not shrink with it — finger contact stays the
    # same size while the glyph halves, and by level 4 the finger covers what
    # it is meant to trace. Tolerance now falls with the square root of the
    # scale, so difficulty still rises but stops outrunning the hand.
    if pack.get("difficulty"):
        d = pack["difficulty"]
        s.sub("shrink rate",
              r"const glyphF=le=>Math\.max\(\.28,BASE_F\*Math\.pow\(\.88,MASTERY\[le\]\|\|0\)\);",
              f"const glyphF=le=>Math.max({d.get('minGlyph', 0.32)},"
              f"BASE_F*Math.pow({d.get('shrinkPerLevel', 0.93)},MASTERY[le]||0));")
        s.sub("tolerance curve",
              r"const R_ON=\(\)=>Math\.max\(\.03,R_ON0\*curS\);",
              f"const R_ON=()=>Math.max({d.get('minTolerance', 0.045)},"
              "R_ON0*Math.sqrt(curS));")

    # ---- sequential reveal (requires strictFollow for SEGS/segIdx)
    #
    # Showing the whole glyph at once tells the learner the answer before they
    # have made a mark. One stroke at a time turns the character into a
    # sequence they earn: strokes already made stay lit, the current one is
    # drawn by the pen, and the ones after it have not caught light yet.
    if pack.get("sequentialReveal") and pack.get("strictFollow"):
        s.sub("trail: current stroke only",
              r"  paintPath\(tr,prog,PATH\.length-1,"
              r"\{alpha:\.38,blur:10,nocore:true,scale:\.75\}\);[^\n]*\n"
              r"  for\(let i=prog;i<PATH\.length;i\+=4\)\{ const q=denorm\(PATH\[i\]\);[^\n]*\n",
              "  const _si=(awaitLift&&segIdx<SEGS.length-1)?segIdx+1:segIdx;\n"
              "  const _sg=SEGS[_si]||[0,PATH.length-1];\n"
              "  const _ss=Math.max(prog,_sg[0]), _se=_sg[1];\n"
              "  paintPath(tr,_ss,_se,{alpha:.38,blur:10,nocore:true,scale:.75});"
              "   // road, this stroke only\n"
              "  for(let i=_ss;i<=_se;i+=4){ const q=denorm(PATH[i]);\n")

        s.sub("ghost demonstrates this stroke",
              r"  const rem=PATH\.length-1-prog, dur=2200\+rem\*17,"
              r" now=performance\.now\(\), ph=\(\(now-ghostAnim\.t\)%dur\)/dur,"
              r" end=PATH\.length-1;",
              "  // The comet shows the stroke you are on, not a lap of the whole\n"
              "  // glyph — the later strokes have not been revealed yet. Once a\n"
              "  // stroke is finished it shows the next one instead, so lifting\n"
              "  // the pen is answered by an invitation rather than a repeat.\n"
              "  const _g=SEGS[_gi]||[0,PATH.length-1], _a=_g[0], end=_g[1];\n"
              "  const rem=end-_a, dur=1500+rem*17, now=performance.now(),"
              " ph=((now-ghostAnim.t)%dur)/dur;")
        s.sub("ghost comet range",
              r"  const n=prog\+Math\.max\(2,Math\.floor\(ph\*\(end-prog\)\)\);"
              r" paintPath\(fx,Math\.max\(prog,n-16\),n,\{alpha:\.9,blur:18,scale:\.8\}\);",
              "  const n=_a+Math.max(2,Math.floor(ph*(end-_a)));"
              " paintPath(fx,Math.max(_a,n-16),n,{alpha:.9,blur:18,scale:.8});")
        s.sub("start dot marks where the pen goes next",
              r"const s0=denorm\(PATH\[prog\]\), pulse=",
              "const s0=denorm(PATH[(awaitLift&&segIdx<SEGS.length-1)"
              "?SEGS[segIdx+1][0]:prog]), pulse=")
        s.sub("ghost keeps running between strokes",
              r"if\(!PATH\.length\|\|done\|\|prog>=PATH\.length-1\)"
              r"\{fx\.clearRect\(0,0,W,H\);return;\}",
              "if(!PATH.length||done){fx.clearRect(0,0,W,H);return;}")

        # the shine: a finished stroke throws light along its whole length
        s.sub("trail cache tracks the segment too",
              r"  if\(trailProg!==prog\) renderTrail\(\);",
              "  // Declared here because the cache check below is the first use;\n"
              "  // declaring it further down put it in the temporal dead zone.\n"
              "  const _gi=(awaitLift&&segIdx<SEGS.length-1)?segIdx+1:segIdx;\n"
              "  if(trailProg!==prog||trailSeg!==_gi) { trailSeg=_gi; renderTrail(); }")
        s.sub("trail cache state", r"let SEGS=\[\],segIdx=0,",
              "let trailSeg=-1;\nlet SEGS=[],segIdx=0,")

        s.sub("shine on stroke completion",
              r"function fizzle\(\)\{",
              "function shine(a,b){ const step=Math.max(1,Math.round((b-a)/16));\n"
              "  for(let i=a;i<=b;i+=step){ const q=denorm(PATH[i]);\n"
              "    for(let k=0;k<3;k++){ const ang=Math.random()*6.28, v=.3+Math.random()*1.4;\n"
              "      parts.push({x:q.x,y:q.y,vx:Math.cos(ang)*v,vy:Math.sin(ang)*v,\n"
              "        life:1,r:1+Math.random()*2,c:'255,241,184'}); } }\n"
              "  if(navigator.vibrate) navigator.vibrate(12);\n"
              "  loop(); }\n"
              "function fizzle(){")
        s.sub("call shine",
              r"      awaitLift=true;   // hooks are separate strokes, so prove it",
              "      shine(seg[0],seg[1]);\n"
              "      awaitLift=true;   // hooks are separate strokes, so prove it")

    # ---- difficulty modes
    #
    # easy    the path, the dots, the comet, and a numbered badge on the
    #         stroke you are about to draw
    # medium  the shape only — you know what the character looks like but not
    #         where to start or in what order
    # hard    nothing. Reserved: free draw needs a different scorer, since
    #         path-following cannot judge a glyph drawn from memory.
    if pack.get("mode"):
        m = {"easy":   ("'none'",    "true",  "true"),
             "medium": ("'strokes'", "false", "false"),
             "hard":   ("'none'",    "false", "false")}[pack["mode"]]
        s.sub("mode state", r"let SHADOW_MODE='[a-z]+';",
              f"let SHADOW_MODE={m[0]};let GUIDE_ON={m[1]},GUIDE_NUMBERS={m[2]};")

        # the trail, comet and start dot are the guide; the shape is not
        s.sub("guide can be hidden",
              r"  fx\.save\(\); fx\.globalAlpha=\.85\+\.15\*Math\.sin\(now/600\);"
              r" fx\.drawImage\(trail,0,0,W,H\); fx\.restore\(\);\n"
              r"  const n=_a\+Math\.max\(2,Math\.floor\(ph\*\(end-_a\)\)\);"
              r" paintPath\(fx,Math\.max\(_a,n-16\),n,\{alpha:\.9,blur:18,scale:\.8\}\);[^\n]*\n"
              r"  const s0=denorm\(PATH\[\(awaitLift&&segIdx<SEGS\.length-1\)"
              r"\?SEGS\[segIdx\+1\]\[0\]:prog\]\), pulse=\.5\+\.5\*Math\.sin\(now/260\);"
              r" fx\.save\(\); fx\.fillStyle=`rgba\(255,241,184,\$\{\.5\+\.4\*pulse\}\)`;"
              r" fx\.shadowColor='#fff1b8'; fx\.shadowBlur=16\+10\*pulse;\n"
              r"  fx\.beginPath\(\); fx\.arc\(s0\.x,s0\.y,4\+3\*pulse,0,7\); fx\.fill\(\); fx\.restore\(\);",
              "  if(GUIDE_ON){\n"
              "    fx.save(); fx.globalAlpha=.85+.15*Math.sin(now/600);"
              " fx.drawImage(trail,0,0,W,H); fx.restore();\n"
              "    const n=_a+Math.max(2,Math.floor(ph*(end-_a)));"
              " paintPath(fx,Math.max(_a,n-16),n,{alpha:.9,blur:18,scale:.8}); // comet\n"
              "    const s0=denorm(PATH[(awaitLift&&segIdx<SEGS.length-1)"
              "?SEGS[segIdx+1][0]:prog]), pulse=.5+.5*Math.sin(now/260);\n"
              "    fx.save(); fx.fillStyle=`rgba(255,241,184,${.5+.4*pulse})`;"
              " fx.shadowColor='#fff1b8'; fx.shadowBlur=16+10*pulse;\n"
              "    fx.beginPath(); fx.arc(s0.x,s0.y,4+3*pulse,0,7); fx.fill(); fx.restore();\n"
              "  }")

        # label() drew numbered badges but only ever in record mode. Stroke
        # order is the thing a learner is actually trying to recall, so on
        # easy the number of the stroke you are about to draw is shown.
        s.sub("stroke numbers on the guide",
              r"  if\(rec&&!done&&prog>1\) paintPath\(g,0,prog,\{alpha:\.9\}\);",
              "  if(rec&&!done&&prog>1) paintPath(g,0,prog,{alpha:.9});\n"
              "  if(GUIDE_NUMBERS&&rec&&!done&&SEGS.length>1){\n"
              "    const _ni=(awaitLift&&segIdx<SEGS.length-1)?segIdx+1:segIdx;\n"
              "    const _ns=SEGS[_ni];\n"
              "    if(_ns) label(g,denorm(PATH[_ns[0]]),_ni+1);\n"
              "  }")

    # ---- practice grid
    #
    # Paper practice sheets put the character in a square with a cross through
    # it, and that frame is what makes length and position judgeable — a
    # stroke floating in empty space gives nothing to measure against.
    #
    # It marks the glyph's own box, derived from the same transform the stroke
    # data was baked with, so "starts just left of centre, ends on the lower
    # line" means the same thing every time. It shrinks with mastery like
    # everything else.
    #
    # Deliberately independent of difficulty: a grid says where the box is,
    # never what to draw, so it can stay on in medium and hard.
    if pack.get("grid", "none") != "none":
        s.sub("grid state", r"let SHADOW_MODE=",
              f"let GRID_MODE='{pack.get('grid')}';let SHADOW_MODE=")
        s.sub("draw the grid",
              r"function drawGuide\(\)\{\n"
              r"  g\.clearRect\(0,0,W,H\); if\(!guideOn&&mode==='practice'&&!done\) return;",
              "function gridBox(){\n"
              "  const A=(typeof DEFAULT_BOOK!=='undefined'&&DEFAULT_BOOK.alignment)"
              "||{glyphCy:0.44};\n"
              "  const cy=A.glyphCy;\n"
              "  return {x0:(0.5-curF/2)*W, x1:(0.5+curF/2)*W,\n"
              "          y0:(0.5-curF*cy)*H, y1:(0.5+curF*(1-cy))*H}; }\n"
              "function drawGrid(){\n"
              "  if(GRID_MODE==='none') return;\n"
              "  const b=gridBox();\n"
              "  g.save(); g.lineWidth=1;\n"
              "  g.strokeStyle='rgba(233,196,106,.16)';\n"
              "  g.strokeRect(b.x0,b.y0,b.x1-b.x0,b.y1-b.y0);\n"
              "  const mx=(b.x0+b.x1)/2, my=(b.y0+b.y1)/2;\n"
              "  g.setLineDash([5,7]); g.strokeStyle='rgba(233,196,106,.13)';\n"
              "  g.beginPath(); g.moveTo(mx,b.y0); g.lineTo(mx,b.y1);\n"
              "  g.moveTo(b.x0,my); g.lineTo(b.x1,my); g.stroke();\n"
              "  if(GRID_MODE==='quarters'){\n"
              "    g.strokeStyle='rgba(233,196,106,.07)'; g.beginPath();\n"
              "    for(const f of [0.25,0.75]){\n"
              "      g.moveTo(b.x0+(b.x1-b.x0)*f,b.y0); g.lineTo(b.x0+(b.x1-b.x0)*f,b.y1);\n"
              "      g.moveTo(b.x0,b.y0+(b.y1-b.y0)*f); g.lineTo(b.x1,b.y0+(b.y1-b.y0)*f); }\n"
              "    g.stroke(); }\n"
              "  g.restore(); }\n"
              "function drawGuide(){\n"
              "  g.clearRect(0,0,W,H); if(!guideOn&&mode==='practice'&&!done) return;\n"
              "  drawGrid();")

    # ---- metadata line: 'a-row', not 'a-row class'
    s.sub("class label", r"\$\('cls'\)\.textContent=cls\+' class'\+",
          "$('cls').textContent=cls+")

    # ---- the baked stroke book, and a restore() that doesn't clobber it
    # Carry the alignment metadata through: tooling that re-derives guide
    # coordinates needs to know what transform was already baked in.
    default_book = {"fonts": book["fonts"]}
    if "alignment" in book:
        default_book["alignment"] = book["alignment"]
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
