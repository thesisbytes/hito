#!/usr/bin/env python3
"""The title screen: index.html, written from here so it can share code.

    make_index.py [out.html]      (default: index.html at the repo root)

It was a list of links. It is now the first screen of a game: the character
the project is named for, drawn the way the game will ask you to draw, one
thing to press, and who is playing.

Generated rather than hand-kept for one reason: it signs people in, and the
code that does that (`account_layer.CORE`) must be the same code the realms
run. Two hand-kept copies of an auth flow is how one of them ends up wrong.
`run.sh` fails if the committed file is not what this writes.

Same rules as everything else: one file, nothing external, opens from a
double-click. From a file there is no sign-in — see account_layer.py — and the
page says so rather than showing a button that cannot work.
"""

import json
import sys
from pathlib import Path

import account_layer

ROOT = Path(__file__).resolve().parent.parent

REALMS = [
    {"id": "hiragana", "kana": "仮", "name": "hiragana", "file": "dist/hiragana-game.html",
     "blurb": "the farang carry the characters you are forgetting"},
    {"id": "katakana", "kana": "片", "name": "katakana", "file": "dist/katakana-game.html",
     "blurb": "loanwords, one kana at a time"},
    {"id": "vocab", "kana": "語", "name": "vocab", "file": "dist/vocab.html",
     "blurb": "Genki I as flashcards you write"},
]

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="color-scheme" content="dark">
<title>hito 人</title>
<meta name="description" content="A stylus-first tracing game for learning to write. Draw below, the farang come from above.">
<style>
  /* The same lacquer the realms are painted on, so stepping from here into
     one does not feel like changing rooms. Nothing external: this page has to
     open from a double-click like everything else. */
  :root{ --lacquer:#15100d; --lacquer-2:#1d1a16; --gold:#e9c46a; --gold-hot:#fff1b8;
         --teal:#7fd1c4; --ink:#e8e0cc; --line:#57492f; }
  *{ box-sizing:border-box; }
  html{ background:#0c0908; }   /* under the body, or a tall window shows a grey band */
  html,body{ height:100%; margin:0; }
  body{ background:radial-gradient(90% 60% at 50% 34%, #241b14 0%, var(--lacquer) 62%, #0c0908 100%);
        color:var(--ink); font:15px/1.45 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
        display:flex; flex-direction:column; align-items:center; min-height:100dvh; overflow-x:hidden; }
  main{ flex:1; width:min(92vw,440px); display:flex; flex-direction:column; align-items:center;
        justify-content:center; padding:24px 0 8px; text-align:center; }

  /* 人, drawn. Two strokes, the second leaning on the first. */
  .mark{ position:relative; width:min(46vw,190px); aspect-ratio:1; margin-bottom:4px; }
  .mark svg{ width:100%; height:100%; overflow:visible; filter:drop-shadow(0 0 14px rgba(233,196,106,.55)); }
  .mark path{ fill:none; stroke:var(--gold); stroke-width:7; stroke-linecap:round; stroke-linejoin:round;
              stroke-dasharray:1; stroke-dashoffset:1; animation:draw 1.1s cubic-bezier(.5,0,.3,1) forwards; }
  .mark path.core{ stroke:var(--gold-hot); stroke-width:2.2; }
  .mark .s2{ animation-delay:1.05s; }
  @keyframes draw{ to{ stroke-dashoffset:0; } }
  /* ghost lights, the colour of a lit character */
  .wisp{ position:absolute; width:7px; height:7px; border-radius:50%; background:var(--teal);
         box-shadow:0 0 12px 3px rgba(127,209,196,.55); opacity:0; animation:drift 7s ease-in-out infinite; }
  .wisp:nth-child(2){ left:8%;  top:62%; animation-delay:.4s; }
  .wisp:nth-child(3){ left:86%; top:48%; animation-delay:2.6s; animation-duration:8.5s; }
  .wisp:nth-child(4){ left:70%; top:12%; animation-delay:4.4s; animation-duration:6.2s; }
  @keyframes drift{ 0%{ opacity:0; transform:translate(0,8px) scale(.7); } 25%{ opacity:.9; }
                    70%{ opacity:.55; } 100%{ opacity:0; transform:translate(10px,-46px) scale(1.1); } }

  h1{ font-size:clamp(40px,11vw,58px); letter-spacing:.14em; margin:0; color:var(--gold); font-weight:700;
      text-indent:.14em; text-shadow:0 0 26px rgba(233,196,106,.35); opacity:0; animation:rise .9s 1.7s forwards; }
  .tag{ color:rgba(232,224,204,.6); margin:6px 0 26px; font-size:13px; letter-spacing:.04em;
        opacity:0; animation:rise .9s 1.95s forwards; }
  .menu{ width:100%; opacity:0; animation:rise .9s 2.2s forwards; }
  @keyframes rise{ from{ opacity:0; transform:translateY(8px); } to{ opacity:1; transform:none; } }

  .begin{ display:block; width:100%; padding:16px; border-radius:14px; border:0; cursor:pointer; text-decoration:none;
          background:var(--gold); color:var(--lacquer); font:700 18px/1 inherit; letter-spacing:.16em;
          text-transform:uppercase; box-shadow:0 0 0 1px rgba(255,241,184,.4),0 10px 34px rgba(233,196,106,.22);
          animation:breathe 2.8s 3s ease-in-out infinite; }
  .begin small{ display:block; margin-top:7px; font:500 11px/1 inherit; letter-spacing:.08em; text-transform:none; opacity:.72; }
  @keyframes breathe{ 50%{ box-shadow:0 0 0 1px rgba(255,241,184,.6),0 10px 44px rgba(233,196,106,.42); } }

  .realms{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:12px; }
  .realms button{ background:var(--lacquer-2); color:var(--ink); border:1px solid #3d3324; border-radius:12px;
          padding:10px 4px 9px; cursor:pointer; font:inherit; }
  .realms button i{ display:block; font-style:normal; font-size:24px; color:rgba(233,196,106,.75); line-height:1.15; }
  .realms button span{ font-size:12px; letter-spacing:.06em; color:rgba(232,224,204,.7); }
  .realms button[aria-pressed="true"]{ border-color:var(--teal); background:#172422; }
  .realms button[aria-pressed="true"] i{ color:#bdf0e6; }
  .blurb{ min-height:2.9em; margin:10px 0 0; font-size:12.5px; color:rgba(232,224,204,.6); }

  .who{ margin-top:16px; padding-top:14px; border-top:1px solid rgba(87,73,47,.5); font-size:13px;
        color:rgba(232,224,204,.72); }
  .who b{ color:var(--gold); font-weight:600; }
  .who button{ background:transparent; border:1px solid #3d3324; color:rgba(233,196,106,.85); border-radius:9px;
          padding:8px 12px; margin:8px 3px 0; cursor:pointer; font:inherit; font-size:13px; }
  .who button.go{ border-color:var(--teal); color:#bdf0e6; }
  .who small{ display:block; margin-top:7px; font-size:11.5px; color:rgba(232,224,204,.48); }
  .tally{ margin-top:10px; font-size:12px; color:rgba(189,240,230,.78); min-height:1.4em; }

  footer{ width:min(92vw,560px); padding:14px 0 18px; text-align:center; font-size:11px; line-height:1.6;
          color:rgba(232,224,204,.4); }
  footer a{ color:rgba(233,196,106,.6); }
  @media (prefers-reduced-motion:reduce){
    *{ animation:none !important; }
    .mark path{ stroke-dashoffset:0; } h1,.tag,.menu{ opacity:1; } .wisp{ display:none; }
  }
</style>
</head>
<body>
<main>
  <div class="mark" aria-hidden="true">
    <svg viewBox="0 0 100 100">
      <path class="s1" pathLength="1" d="M53 10 C52 38 40 66 11 91"/>
      <path class="s1 core" pathLength="1" d="M53 10 C52 38 40 66 11 91"/>
      <path class="s2" pathLength="1" d="M50 39 C57 62 73 81 92 90"/>
      <path class="s2 core" pathLength="1" d="M50 39 C57 62 73 81 92 90"/>
    </svg>
    <span class="wisp"></span><span class="wisp"></span><span class="wisp"></span>
  </div>
  <h1>HITO</h1>
  <p class="tag">learn to write by writing · draw below, the farang come from above</p>

  <div class="menu">
    <a class="begin" id="begin" href="dist/hiragana-game.html">begin<small id="beginSub">hiragana</small></a>
    <div class="realms" id="realms" role="group" aria-label="realm"></div>
    <p class="blurb" id="blurb"></p>
    <div class="tally" id="tally"></div>
    <div class="who" id="who"></div>
  </div>
</main>
<footer>
  人 is two strokes, and neither stands on its own.<br>
  Stroke order from <a href="https://kanjivg.tagaini.net/">KanjiVG</a> (CC BY-SA 3.0). Klee One and Noto Sans JP under the SIL Open Font License.<br>
  <a href="dist/hiragana.html">the workshop</a> · <a href="https://github.com/thesisbytes/hito">source</a> · every realm is one file that opens offline
</footer>

<script>window.__ACCOUNT_CFG=__ACCOUNT__;</script>
<script>__CORE__</script>
<script>
/* ---- the title screen ---------------------------------------------------- */
(function(){
  const REALMS = __REALMS__;
  const $ = id => document.getElementById(id);
  const get = k => { try { return localStorage.getItem(k); } catch(_){ return null; } };
  const esc = t => String(t).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

  // Begin goes where you were last. A title screen that asks which game you
  // meant, every time, is a menu.
  let realm = REALMS.find(r => r.id === get('hito-realm')) || REALMS[0];
  function pick(id){
    realm = REALMS.find(r => r.id === id) || realm;
    try { localStorage.setItem('hito-realm', realm.id); } catch(_){}
    draw();
  }
  function draw(){
    $('begin').href = realm.file; $('beginSub').textContent = realm.name;
    $('blurb').textContent = realm.blurb;
    $('realms').innerHTML = REALMS.map(r =>
      `<button data-r="${r.id}" aria-pressed="${r === realm}"><i>${r.kana}</i><span>${r.name}</span></button>`).join('');
    for (const b of $('realms').querySelectorAll('button')) b.onclick = () => pick(b.dataset.r);
  }

  // What the hand has done, read straight off the ledger the realms keep.
  function tally(){
    let L = null; try { L = JSON.parse(get('hito-ledger') || 'null'); } catch(_){}
    if (!L || !L.g) { $('tally').textContent = ''; return; }
    const total = Object.values(L.g).reduce((a, e) => a + (e && e.n || 0), 0);
    if (!total) { $('tally').textContent = ''; return; }
    const key = d => d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
    const d = new Date(); let run = 0;
    if (!((L.days || {})[key(d)] || [0])[0]) d.setDate(d.getDate() - 1);
    while (((L.days || {})[key(d)] || [0])[0]){ run++; d.setDate(d.getDate() - 1); }
    $('tally').textContent = `${total} conjured · ${Object.keys(L.g).length} characters`
      + (run > 1 ? ` · ${run} days running` : '');
  }

  function who(){
    const A = window.__account;
    let h;
    if (A && A.user)
      h = `welcome back, <b>${esc(A.user.name)}</b><br><button data-a="out">sign out</button>`
        + `<small>your stats and mastery follow you to any device you sign in on</small>`;
    else if (A && A.state === 'working') h = 'signing in…';
    else if (A && A.can)
      h = `playing as a <b>guest</b><br><button class="go" data-a="in">sign in with Google</button>`
        + `<small>${A.note ? esc(A.note) + ' · ' : ''}a guest keeps everything on this device. signing in keeps it everywhere.</small>`;
    else
      h = `playing as a <b>guest</b><small>everything stays on this device. sign-in is on the web version: a file has nowhere for Google to send you back to.</small>`;
    $('who').innerHTML = h;
    for (const b of $('who').querySelectorAll('button'))
      b.onclick = () => b.dataset.a === 'in' ? A.signIn() : A.signOut();
  }

  draw(); tally(); who();
  if (window.__account) window.__account.onChange(who);
  addEventListener('keydown', e => { if (e.key === 'Enter' && document.activeElement === document.body) $('begin').click(); });
})();
</script>
</body>
</html>
"""


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "index.html"
    pack = json.loads((ROOT / "scripts/hiragana/game.json").read_text(encoding="utf-8"))
    js = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    for r in REALMS:
        if not (ROOT / r["file"]).exists():
            sys.exit(f"title screen links to {r['file']}, which does not exist")
    page = (PAGE.replace("__ACCOUNT__", js(account_layer.values(pack)))
                .replace("__CORE__", account_layer.CORE)
                .replace("__REALMS__", js(REALMS)))
    out.write_text(page, encoding="utf-8")
    print(f"{out}  {len(page.encode('utf-8'))/1024:.0f} KB")


if __name__ == "__main__":
    main()
