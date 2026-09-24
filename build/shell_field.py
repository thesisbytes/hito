#!/usr/bin/env python3
"""The game shell: a battle field above, a stationary sketchbook below.

The workshop screen — gojuon chart, stroke controls, size ladder — is the
instrument this project uses on itself. The game is not that. Here the bottom
third is the sketchbook and never moves, and the top two thirds is the field:
farang advance on a centre you are protecting, each carrying the sign you have
to answer. Finish the glyph and it flies up and hits them.

A finished glyph also *kindles* it: every clean trace of a character lights a
hitodama (人魂, a ghost light) over that character, and a lit character
defends itself. When a monster carrying it appears, a wisp flies on its own
and the charge burns down by one. Trace ぬ three times and the next few ぬ
die without the pen. This is the idle economy's potency stat given teeth
before the economy exists: the hand is pushed toward the characters whose
flame is out, which are exactly the ones that need practice.

The split is what makes real-time movement safe. Monsters can march
continuously because they never share space with the pen: the drawing surface
is a fixed rectangle that does not scroll, scale or reflow while the field
moves above it. "You identify, you do not aim" needs exactly that.

With a deck the farang carry words instead of characters. Katakana loanwords
are English said in a Japanese accent, so the sign is the farang's own word or
its mangled reading, and the answer is the katakana, one kana at a time. A
word monster's `i` is always the kana it is waiting for, so everything that
asks LETTERS[m.i] works unchanged; each finished kana knocks it back a step
and the last one banishes it. The ghost light is kept by the word.

This is applied as an appended layer rather than woven into the engine with
substitutions. It touches the engine only through globals it already exposes
(load, conjure, LETTERS, idx, stage, toast), so the tracer and its scoring
stay the single source of truth for what counts as a correct glyph.
"""

STYLE = """
<style>
  /* The workshop's furniture, hidden. The engine still maintains all of it —
     nothing is torn out, so a pack can switch shells without a rebuild of the
     tracer. */
  body.field .tabs, body.field .count, body.field .meta, body.field .power,
  body.field .only-p, body.field .only-r, body.field #fontRow,
  body.field .grid, body.field .hint { display:none !important; }

  body.field { height:100dvh; overflow:hidden; justify-content:flex-start; }
  body.field header { padding:6px 0 2px; }

  /* Two thirds field, one third sketchbook. The stage loses its square aspect
     ratio here — resize() reads the element's box, so the tracer follows. */
  .field-wrap{ position:relative; width:min(96vw,760px); flex:2 1 0;
               min-height:0; margin-top:4px; }
  .field-wrap canvas{ position:absolute; inset:0; width:100%; height:100%;
    border-radius:18px;
    background:radial-gradient(70% 60% at 50% 70%,rgba(90,160,150,.07),transparent 70%),
               var(--lacquer-2);
    box-shadow:inset 0 0 0 1px rgba(233,196,106,.10),0 18px 50px rgba(0,0,0,.45); }
  /* The sketchbook MUST stay square. norm() in the engine divides x by W and
     y by H independently, so a rectangular stage does not merely stretch the
     glyph — it makes every distance in normalised space anisotropic, and the
     tolerance, coverage radius and travel ratio all stop meaning one thing.
     At 760x250 the pen would be forgiven three times as much sideways as
     vertically. The tracer has always assumed a square; this shell must not
     be the thing that quietly breaks that assumption. */
  body.field .stage{ flex:0 0 auto; aspect-ratio:1;
                     width:min(96vw,34dvh); height:min(96vw,34dvh);
                     margin:8px auto 10px; }
  body.field .field-wrap{ flex:1 1 auto; }
  /* The workshop strip: ink and what it buys. At the top of the field, as far
     from the hand as the screen allows — a button under a resting palm is a
     button that presses itself. */
  .upg{ display:flex; flex-wrap:wrap; gap:6px; align-items:stretch; font:12px ui-sans-serif,system-ui; }
  /* The dashboard: hearts and ink on the seam, where the eyes already are, and
     tabs to duck into while the waves keep coming. The run does not pause for
     a tab; knowing when you can afford to look is the game. */
  /* Four tabs and two bars have to share 374px on a phone: the spacing is
     tight on purpose, and the tabs may not grow (the engine's own button
     rule would have them at 88px each). */
  .dash-bar{ position:absolute; left:8px; right:8px; bottom:6px; z-index:3; display:flex; flex-wrap:wrap; align-items:center; gap:5px;
             padding:5px 6px; border-radius:10px; background:rgba(22,20,17,.88); border:1px solid #3d3324;
             font:12px ui-sans-serif,system-ui; color:#e8e0cc; }
  .dash-bar .bar{ position:relative; flex:1 1 60px; min-width:40px; max-width:150px; height:18px; border-radius:6px; overflow:hidden;
                  background:rgba(232,224,204,.08); border:1px solid #3d3324; }
  .dash-bar .bar i{ position:absolute; left:0; top:0; bottom:0; background:#e9c46a; opacity:.75; transition:width .25s; }
  .dash-bar .bar.energy i{ background:#7fd1c4; }
  .dash-bar .bar b{ position:absolute; left:6px; top:1px; font-size:12px; color:#1a1712; }
  .dash-bar .bar small{ position:absolute; right:5px; top:2px; font-size:10px; color:#e8e0cc; }
  @media (prefers-reduced-motion:reduce){ .dash-bar .bar i{ transition:none; } }
  .dash-bar .n{ font-weight:700; font-size:11px; color:#e9c46a; white-space:nowrap; } .dash-bar .n small{ font-weight:400; color:rgba(232,224,204,.55); }
  /* The tabs (the maintainer: "not so obvious"): the sketchbook's is the
     big one, and each shop wears a mark — a sword to cut, a shield to last,
     a coin to earn, a flame for what lasts. On a phone the tabs take a row
     of their own under the bars rather than fighting them for the width. */
  .dash-bar .dash-tabs{ margin-left:auto; display:flex; gap:4px; align-items:center; }
  .dash-bar .dash-tabs button{ flex:none; min-width:0; font:700 13px ui-sans-serif,system-ui; padding:4px 8px; border-radius:8px; background:transparent;
                          border:1px solid #3d3324; color:#e8e0cc; cursor:pointer; display:inline-flex; align-items:center; gap:4px; line-height:1; }
  .dash-bar .dash-tabs button svg{ width:13px; height:13px; flex:none; opacity:.85; }
  .dash-bar .dash-tabs button[data-tab="trace"]{ font-size:19px; padding:4px 16px; border-width:2px; }
  @media (max-width:560px){ .dash-bar .dash-tabs{ flex:1 0 100%; margin-left:0; justify-content:space-between; } }
  .dash-bar .dash-tabs button.can{ border-color:#7fd1c4; color:#bdf0e6; }
  .dash-bar .dash-tabs button[aria-pressed="true"]{ background:rgba(127,209,196,.14); border-color:#7fd1c4; color:#bdf0e6; box-shadow:0 0 10px rgba(127,209,196,.25); }
  /* The shop stands where the sketchbook stood, and the sketchbook is gone
     while it does: the tracing is a tab like the others (the maintainer:
     "the player has to wait for opportunities to switch out to upgrade").
     It takes the sketchbook's own box, measured as it is hidden, so the
     page does not jump. */
  .panel{ position:relative; flex:0 0 auto; box-sizing:border-box; width:min(96vw,34dvh); height:min(96vw,34dvh); margin:8px auto 10px;
          z-index:2; overflow:auto; border-radius:12px; padding:10px;
          background:rgba(22,20,17,.93); border:1px solid #3d3324; font:12px ui-sans-serif,system-ui; color:#e8e0cc; }
  body.field .stage[hidden]{ display:none; }
  .panel .panel-h{ font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:rgba(232,224,204,.55); margin:0 0 8px; }
  .panel .start-h, .panel .start-row{ margin-top:0; }
  .upg-ink{ display:flex; align-items:center; gap:5px; padding:0 9px; border-radius:9px;
        background:rgba(22,20,17,.82); border:1px solid #3d3324; color:#e9c46a; font-weight:700; }
  .upg-ink i{ font-style:normal; color:rgba(232,224,204,.55); font-weight:400; }
  .upg button{ flex:1 1 44%; min-width:0; text-align:left; padding:6px 8px; border-radius:9px; cursor:pointer;
        background:rgba(22,20,17,.82); border:1px solid #3d3324; color:#e8e0cc; font:inherit; line-height:1.25; }
  .upg button b{ color:#e9c46a; margin-right:5px; display:inline-flex; align-items:center; gap:3px; vertical-align:-3px; }
  .upg button b svg{ width:17px; height:17px; }
  .upg button b i.k{ font-style:normal; font-size:10px; opacity:.6; }
  .upg button small{ display:block; color:rgba(232,224,204,.6); white-space:normal; line-height:1.3; margin-top:2px; }
  .upg button.can{ border-color:#7fd1c4; box-shadow:0 0 10px rgba(127,209,196,.25); }
  .upg button.can small{ color:#bdf0e6; }
  .upg button[disabled]{ opacity:.5; cursor:default; }
  /* At phone width four buttons are 80px each: a cost fits, a sentence does
     not, and half a sentence is worse than none. The title attribute and the
     start page still say what each one does. */
  @media (max-width:560px){ .upg{ gap:4px; } }
  .upg button small i{ font-style:normal; }

  /* The start page. A lacquer sheet over everything, with the two axes the
     game actually has: how much help, and what the sign says. */
  .start{ position:fixed; inset:0; z-index:9998; display:flex; align-items:center;
          justify-content:center; padding:18px;
          background:radial-gradient(60% 50% at 50% 40%,rgba(90,160,150,.10),transparent 70%),
                     rgba(12,10,8,.94); }
  .start[hidden]{ display:none; }
  .start-card{ width:min(94vw,520px); max-height:94dvh; overflow:auto;
               font:14px ui-sans-serif,system-ui; color:#e8e0cc; }
  .start-title{ font-size:34px; font-weight:700; color:#e9c46a; letter-spacing:.02em;
                text-shadow:0 0 24px rgba(233,196,106,.35); }
  .start-title span{ font-size:40px; margin-left:8px; }
  .start-sub{ color:rgba(232,224,204,.55); margin:2px 0 18px; font-size:12px; }
  .start-h{ font-size:11px; letter-spacing:.14em; text-transform:uppercase;
            color:rgba(127,209,196,.8); margin:14px 0 8px; }
  .start-row{ display:grid; grid-template-columns:repeat(auto-fit,minmax(110px,1fr)); gap:8px; }
  .start-row button, .start-row a{ display:block; text-decoration:none; text-align:left; background:#1d1a16; color:#e8e0cc; border:1px solid #57492f;
                     border-radius:10px; padding:10px 12px; cursor:pointer; font:inherit; min-height:74px; }
  .start-row a{ min-height:0; }
  .start-row button b, .start-row a b{ display:block; font-size:15px; color:#e9c46a; margin-bottom:3px; }
  .start-row button b i{ font-style:normal; color:#bdf0e6; margin-right:6px; }
  .start-row button b svg{ width:16px; height:16px; vertical-align:-3px; margin-right:5px; }
  .start-row button small, .start-row a small{ display:block; color:rgba(232,224,204,.7); line-height:1.35; }
  .start-row button[aria-pressed="true"]{ border-color:#7fd1c4; background:#172422;
                     box-shadow:0 0 0 1px rgba(127,209,196,.5), 0 0 22px rgba(127,209,196,.18); }
  .start-row button[disabled]{ opacity:.42; cursor:default; }
  .start-go{ width:100%; margin-top:20px; background:#e9c46a; color:#1d1a16; border:0;
             border-radius:12px; padding:14px; font:700 17px ui-sans-serif,system-ui; cursor:pointer;
             box-shadow:0 0 30px rgba(233,196,106,.25); }
  .over-nums{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; text-align:center; margin:6px 0 10px; }
  .over-nums div{ background:#1d1a16; border:1px solid #3d3324; border-radius:9px; padding:10px 4px; }
  .over-nums b{ display:block; font-size:22px; color:#bdf0e6; }
  .over-nums small{ color:rgba(232,224,204,.6); font-size:11px; }
  .over-line{ margin:0 0 6px; font-size:12.5px; color:rgba(232,224,204,.65); text-align:center; }
  .start-card.over .start-title{ color:#e8a0a0; }
  .start-card.over.won .start-title{ color:#7fd1c4; }
  .over-line.warn{ color:#e8a0a0; } .over-line.warn b{ color:#e9c46a; }
  .over-pay{ margin:2px 0 4px; text-align:center; font-size:20px; font-weight:700; color:#bdf0e6; }
  .over-pay small{ display:block; font-size:11.5px; font-weight:400; color:rgba(232,224,204,.55); }
  .start-row.lantern button.can{ border-color:#7fd1c4; }
  .start-row.lantern{ grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); }
  .start-row.stages{ grid-template-columns:repeat(auto-fill,minmax(54px,1fr)); }
  .start-row.stages button{ text-align:center; padding:8px 2px; }
  .start-row.stages button b{ margin:0; }
  .start-h b.needs{ color:#e8a0a0; font-weight:600; letter-spacing:.04em; }
  .start-foot{ margin-top:12px; font-size:11px; color:rgba(232,224,204,.4); text-align:center; }
  .start-links{ display:flex; gap:8px; margin-top:10px; }
  .start-links button{ flex:1; background:transparent; color:rgba(233,196,106,.75); border:1px solid #3d3324;
                       border-radius:9px; padding:9px; font:13px ui-sans-serif,system-ui; cursor:pointer; }
  .credits p{ line-height:1.55; color:rgba(232,224,204,.85); margin:10px 0; }
  .credits p.lead{ font-size:15px; color:#e8e0cc; }
  .credits p.lead b{ color:#e9c46a; font-size:22px; margin-right:6px; }
  .credits p.small{ font-size:12px; color:rgba(232,224,204,.6); }
  body.field header .brand{ cursor:pointer; }
</style>
"""

LAYER = STYLE + r"""
<script>
/* ---- the field ---------------------------------------------------------
   Monsters advance in polar coordinates around the centre, so the geometry is
   resolution independent and a rotated tablet changes nothing about the game.
   d runs 1 at the edge to 0 at the ward.                                  */
(function(){
  const CFG = window.__FIELD_CFG;
  const $ = id => document.getElementById(id);

  // ---- words
  // A deck turns the roster from characters into words. The word is shared
  // deck data; how far a given farang has been written is on the monster
  // (ci, zaps), and its `i` is kept pointed at the kana it is waiting for.
  const WORDS = CFG.deck ? CFG.deck.words : null;
  if (WORDS) for (const w of WORDS) w.chars = [...w.ja];
  const AT = {};
  LETTERS.forEach((L, i) => { AT[L[0]] = i; });
  // What the hitodama is kept by: always the character. A word farang is
  // waiting on exactly one kana at a time (`i`), and that kana's light is what
  // can answer it. Until v0.1.40 a word kept its own light, whole — right for
  // a flashcard, wrong for a game where the farang grow into sentences: you
  // cannot have traced every sentence, but you can have lit every kana in one.
  const key = m => LETTERS[m.i][0];
  const REALM = WORDS ? CFG.deck.deck : 'hiragana';

  document.body.classList.add('field');
  const wrap = document.createElement('div');
  wrap.className = 'field-wrap';
  const fc = document.createElement('canvas');
  fc.id = 'field';
  wrap.appendChild(fc);
  const stageEl = document.getElementById('stage');
  stageEl.parentNode.insertBefore(wrap, stageEl);

  const cx = () => fc.width / (2*DPRF());
  const cy = () => fc.height / (2*DPRF()) * 1.06;   // ward sits a touch low
  // 2x, not 3x: the field is a phone's width and redrawn every frame, and a
  // 3x phone paints 2.25x the pixels of a 2x one for glows nobody can tell
  // apart. (The maintainer, v0.1.62: "still a touch laggy.")
  function DPRF(){ return Math.min(devicePixelRatio||1, 2); }
  let FW = 0, FH = 0;
  function sizeField(){
    const r = wrap.getBoundingClientRect(), d = DPRF();
    FW = Math.round(r.width); FH = Math.round(r.height);
    fc.width = Math.round(FW*d); fc.height = Math.round(FH*d);
    const g = fc.getContext('2d'); g.setTransform(d,0,0,d,0,0);
  }

  // ---- state
  let monsters = [], shots = [], motes = [];
  let ward = CFG.wardHp, over = false, wave = 0, killed = 0;

  // ---- ink, and what it buys during a run
  // The Tower's loop, with one rule it does not have: nothing here draws for
  // you. Every upgrade multiplies what a trace is worth — how fast the lights
  // you lit are thrown, how many a clean trace lights, how hard a hit shoves —
  // and none of them lights a character the hand has not written. Ink comes
  // from tracing, and mostly from tracing cleanly; a wisp's kill pays a
  // little, so the idle half earns its keep without outearning the pen.
  // All of it belongs to the run and goes when the ward falls.
  // 技: this run's skills, bought with 墨, gone when the ward falls. The theme
  // is intent — the maintainer: "we forge and sharpen our intent to cut
  // through farangs' mindset of sticking to their old ways". Every one
  // multiplies what the hand's strokes are worth; none writes a character.
  // 耐: the same ink, spent on lasting the waves out rather than cutting
  // through them. The farang grow stronger as the waves climb, in health
  // (`hpFor`) and in attack (`biteFor`, a breach costing more of the ward),
  // and this tab is what stands against the second. Persistence: a wall, a
  // life mended, a life back for every stretch of waves held.
  // 志: motivation, which the maintainer pinned to currency: "Motivation tab
  // should be upgrades for currency gain". Every trace pays more ink, every
  // banish pays more ink, and the fall pays more 魂 — 七転び八起き, what you
  // get up with. Three tabs, then, the way a tower is run: 技 cuts, 耐
  // lasts, 志 earns. None of them writes a character.
  // A mark on every upgrade (the maintainer: "since I don't know any kanji
  // it's hard for me to decide what to upgrade"). Inline, in the button's
  // colour, drawn to read at 16px: what it does, not what it is called.
  const svg = d => `<svg viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  const MARK = {
    intent:  svg('<circle cx="8" cy="8" r="6"/><circle cx="8" cy="8" r="2.4"/><path d="M8 2v2M8 12v2M2 8h2M12 8h2"/>'),           // a bullseye: cuts deeper
    quick:   svg('<path d="M9 1.5 4 9h4l-1 5.5L13 7H9z"/>'),                                                                          // a bolt: sooner
    breath:  svg('<path d="M2 5h7a2 2 0 1 0-2-2M2 8.5h10a2 2 0 1 1-2 2M2 12h6a1.8 1.8 0 1 1-1.8 1.8"/>'),                            // wind: fills 気
    shove:   svg('<path d="M2 8h9M8 4l4 4-4 4M14 3v10"/>'),                                                                            // an arrow into a wall: pushes back
    mend:    svg('<path d="M8 14 3.2 9.3A3.1 3.1 0 0 1 8 5.2a3.1 3.1 0 0 1 4.8 4.1z"/><path d="M12.5 1v4M10.5 3h4"/>'),               // a heart and a plus: a life
    wall:    svg('<rect x="2" y="3" width="12" height="10" rx="1"/><path d="M2 6.3h12M2 9.7h12M8 3v3.3M5 6.3v3.4M11 6.3v3.4M8 9.7V13"/>'),  // bricks
    tend:    svg('<circle cx="8" cy="8" r="6"/><path d="M8 5v6M5 8h6"/>'),                                                              // a medic's cross: a life back
    dilig:   svg('<path d="M8 1.5c2.5 3.5 4.5 5.6 4.5 8.3a4.5 4.5 0 0 1-9 0C3.5 7.1 5.5 5 8 1.5z"/><path d="M6 10.5a2 2 0 0 0 2 2"/>'),  // an ink drop: more 墨 per trace
    harvest: svg('<path d="M13 3a7 7 0 0 1-9 9M4 12l-1.5 2.5M13 3l-1 1.5"/>'),                                                          // a sickle: more per banish
    rise:    svg('<path d="M2 13h12M4.5 10.5a3.5 3.5 0 0 1 7 0M8 2v3M3.5 5.5 5 7M12.5 5.5 11 7"/>'),                                  // a sunrise: get up with more
    heart:   svg('<path d="M8 14 2.6 8.8A3.4 3.4 0 0 1 8 4.4a3.4 3.4 0 0 1 5.4 4.4z"/>'),                                             // a heart: the ward starts with one more
    lamp:    svg('<rect x="5" y="4" width="6" height="8" rx="1.5"/><path d="M8 1.5V4M6 14.5h4M8 12v2.5"/>'),                            // a lantern: one more light held
    inkwell: svg('<path d="M3 6h10l-1 7.5H4zM6 6V3h4v3"/>'),                                                                            // an inkwell: ink at the start
    vessel:  svg('<path d="M4.5 5h7l1.5 8.5H3zM6 5V2.5h4V5"/>'),                                                                        // a jar: a bigger bag of 気
  };
  const UPG = {
    // Ceilings raised in v0.1.65 (the maintainer: "we end up maxing out the
    // upgrades so early"), with the pack's ramp steepened: a run should end
    // with things still worth buying, or the tabs stop being a decision.
    intent:{ tab:'skills', kana:'意', name:'intent', blurb:'every light cuts deeper: one more hit per cast', max:5 },
    quick: { tab:'skills', kana:'早', name:'quick',  blurb:'the lights are thrown sooner',                    max:8 },
    breath:{ tab:'skills', kana:'息', name:'breath', blurb:'every stroke fills 気 by one more',                max:5 },
    shove: { tab:'skills', kana:'押', name:'shove',  blurb:'every hit pushes them back',                      max:8 },
    mend:  { tab:'guard',  kana:'守', name:'mend',   blurb:'the ward gains a life',                           max:8 },
    wall:  { tab:'guard',  kana:'壁', name:'wall',   blurb:'a breach costs the ward one less',                max:5 },
    tend:  { tab:'guard',  kana:'癒', name:'tend',   blurb:'a life back for every stretch of waves held',     max:5 },
    dilig: { tab:'drive',  kana:'勤', name:'diligence', blurb:'every trace pays one more 墨',                 max:8 },
    harvest:{tab:'drive',  kana:'収', name:'harvest',blurb:'every farang your lights finish pays one more 墨', max:8 },
    rise:  { tab:'drive',  kana:'起', name:'rise',   blurb:'the fall pays more 魂: get up with more',         max:5 },
  };
  const TABS = { skills:'技', guard:'耐', drive:'志' };
  const freshUpg = () => Object.fromEntries(Object.keys(UPG).map(id => [id, 0]));
  // `sumi`, not `ink`: `ink` is the engine's drawing context, and this layer
  // uses it (guided mode wipes the pen's mark with it). Calling the currency
  // `ink` shadowed it, and guided threw on every repaint in v0.1.39.
  let sumi = 0, upg = freshUpg();
  const costOf = id => Math.round((CFG.upgradeCost[id] || 10) * Math.pow(CFG.upgradeRamp, upg[id]));
  const castMs = () => CFG.castMs * Math.pow(0.82, upg.quick);
  // ---- stages, and the workshop between rounds ------------------------------
  // The maintainer: "make it impossible to advance without unlocking stuff. so
  // there needs to be a currency to use after each round". Stages did that
  // (v0.1.44-v0.1.53): a fixed count of farang, a gate bought with 魂. They
  // became a wall — stage 8 was 33 farang by finger — and every fall was
  // nothing. The tower (below) keeps the currency and the curriculum gate and
  // drops the finish line. Word decks are never staged or towered: a deck is
  // class content with its own order. And the workshop page is never gated,
  // so anything can always be practised.
  const ST = WORDS ? null : CFG.tower;
  const purse = () => { try { return window.__hand && window.__hand.tama; } catch(_){ return null; } };
  const own = id => { const p = purse(); return p ? p.own(id) : 0; };
  const LANTERN = {
    heart:   { kana:'心', name:'heart',   blurb:'the ward starts with one more',        max:5 },
    lamp:    { kana:'灯', name:'lamp',    blurb:'a character can hold one more light',  max:4 },
    inkwell: { kana:'硯', name:'inkwell', blurb:'every run starts with more ink in hand', max:5 },
    vessel:  { kana:'器', name:'vessel',  blurb:'the bag of 気 holds more',                 max:3 },
  };
  const lanternCost = id => Math.round((CFG.lanternCost[id] || 20) * Math.pow(CFG.lanternRamp, own(id)));
  // The tower (the maintainer, 2026-09-24: "there is no completing a level.
  // You just keep going until the swarm consumes you"). The waves do not end;
  // the run ends when the ward falls, and how far it got is the record. The
  // curriculum gate survives, keyed to distance: a row of the chart opens
  // every `rowWaves` waves, counted from the furthest wave this realm has
  // ever reached or the current run's, whichever is further. Every tenth
  // wave (`bossEvery`) carries a boss, and while a boss lives every character
  // traced gets less help — the shape faint, the start dot kept — not only
  // the boss's own ("so throughout round 10, all the characters you stroke
  // are affected by the debuff from the boss"). Guided is practice: it pays
  // nothing and its waves open nothing.
  const bestWave = () => { try { const H = window.__hand; const b = H && H.ledger && H.ledger.best && H.ledger.best[REALM]; return b ? (+b.wave || 0) : 0; } catch(_){ return 0; } };
  const totalRows = () => Math.max(1, Math.max(...LETTERS.map(L => L[6] || 1)));
  const rowsOpen = w => !ST ? Infinity : Math.min(totalRows(), ST.rows + Math.floor(Math.max(bestWave(), w == null ? wave : w) / ST.rowWaves));
  const nextRowAt = () => (!ST || rowsOpen() >= totalRows()) ? Infinity : (rowsOpen() - ST.rows + 1) * ST.rowWaves;
  const RANK = { guided:0, medium:2, hard:3 };
  const needs = () => !ST ? 'guided' : 'medium';
  const bossAlive = () => monsters.some(m => m.boss);
  // Guided draws from every row: it holds nothing and opens nothing, so the
  // gate costs it nothing.
  const roster = () => { if (DIFF[difficulty] && DIFF[difficulty].allRows) return LETTERS.map((_, i) => i);
    const r = rowsOpen(); const a = []; LETTERS.forEach((L, i) => { if ((L[6] || 1) <= r) a.push(i); }); return a.length ? a : LETTERS.map((_, i) => i); };
  function buyLantern(id){
    const p = purse(); if (!p || !LANTERN[id]) return false;
    return p.buy(id, lanternCost(id), LANTERN[id].max);
  }
  const capNow = () => CFG.hitodamaCap + own('lamp');
  const wardMax = () => CFG.wardHp + own('heart') + upg.mend;
  // What this run was, kept as it goes so the end can say it. Observations:
  // how far, how many, how cleanly. Never a score.
  let run = null;
  const newRun = () => ({ at: Date.now(), began: performance.now(), traced: 0, clean: 0, earned: 0, cast: 0, ended: null, pay: 0, q: 0, qn: 0 });
  // ---- 気, the energy for casting
  // One bag. Every stroke the hand completes fills it, whatever is on the
  // field ("the stroke does not depend on which enemy is present. All
  // strokes go into one bag of energy"), and every wisp a lit character
  // throws spends from it. Lights say which characters can answer for
  // themselves; 気 is what they answer with. Nothing fills it but the hand.
  let energy = 0, credited = 0;
  const energyMax = () => CFG.energyMax + own('vessel') * CFG.vesselStep;
  function fill(n){ energy = Math.max(0, Math.min(energyMax(), energy + (+n || 0))); return energy; }   // negative drains; a breach may, one day
  function earn(n){ if (n > 0){ sumi += n; if (run) run.earned += n; renderUpg(); } return sumi; }
  function buy(id){
    if (!UPG[id] || over || upg[id] >= UPG[id].max) return false;
    const c = costOf(id);
    if (sumi < c) return false;
    sumi -= c; upg[id]++;
    if (id === 'mend') ward = Math.min(wardMax(), ward + 1);
    try { window.__sync && window.__sync.record('upgrade', { id, level: upg[id], wave }); } catch(_){}
    renderUpg();
    return true;
  }
  // Farang toughen as the waves climb. A tough one is not answered twice by
  // hand: the trace is the first hit and it lights the character, and the
  // character's own wisps are the rest. One clean trace is worth three hits
  // (itself and two lights), so past three the pen has to come back — or the
  // workshop has to have made a trace worth more. Words are already as tough
  // as they are long, so this is for single characters.
  const hpFor = w => WORDS || !CFG.hpEvery ? 1 : Math.min(CFG.hpMax, 1 + Math.floor(w / CFG.hpEvery));
  // And they bite harder (the maintainer: "every increment in round they get
  // stronger. Both in attack and health"). A breach costs the ward one life
  // at the foot of the tower and one more every `biteEvery` waves; a boss
  // bites `bossBite` more; a wall takes off one per level, never below one.
  // Words bite like anything else: a word that reaches the ward is a word
  // not answered.
  const biteFor = (w, boss) => Math.max(1, (CFG.biteEvery ? Math.min(CFG.biteMax, 1 + Math.floor(w / CFG.biteEvery)) : 1)
                                          + (boss && ST ? ST.bossBite : 0) - upg.wall);
  let spawnAt = 0, tPrev = 0;
  let frames = { n:0, slow:0, jank:0 };
  // The field holds still while the start page is up. Nothing moves, nothing
  // spawns, no wisp flies; the clock resumes from where it stopped.
  let paused = true;

  // ---- difficulty, at runtime
  // The pack bakes in the penalties; the start page chooses between them.
  // The values themselves are read off the engine at boot rather than
  // written here, so a pack that tunes them stays authoritative.
  const BASE = { R_ON0, DRAIN, FIZZ, COVER_MIN, MAX_TRAVEL };
  // guided is not easy with the numbers turned down. The objective is the
  // light: drag it to the end of every stroke and the glyph is yours. So the
  // pen leaves no ink, nothing zaps, the light is big enough to be the thing
  // you are holding, and the only test at the end is that the light got
  // there — coverage and travel are not asked, because the light cannot
  // reach the end without the pen having gone the whole way with it.
  const DIFF = {
    // One size, the largest. Guided teaches the shape and the order; a small
    // glyph tests the hand, and calibrating a hand is not learning hiragana.
    // The light is dragged rather than chased (DRAG_FOLLOW), and nothing is
    // kindled or cast: guided is practice, and the wisps are for the game.
    // The light is easy's light, no bigger: at 2.4x, then 1.5x, it was still
    // 'a giant circle'. And no comet: the looping run to the end of the
    // stroke sets a pace, and the hand starts following its speed instead
    // of dragging the light at its own. The road ahead already shows where
    // to go; guided does not need to be shown how fast.
    guided: { tama:0, kana:'導', blurb:'follow the light. no ink, no zaps, one big size, every row. practice only: nothing here counts toward a stage or 魂.',
              R_ON0: BASE.R_ON0*1.5, DRAIN: 0, FIZZ: Infinity, size: SIZE_MAX,
              COVER_MIN: 0, MAX_TRAVEL: Infinity, dot: 1, ink:false, drag:true, cast:false, reveal:true,
              guide:true, numbers:true, comet:false, shadow:'none', stray:'drop', allRows:true },
    medium: { tama:2, kana:'中', blurb:'the shape only, drawn as wide as you are allowed to stray. where each stroke starts, and in what order, is on you.',
              R_ON0: BASE.R_ON0, DRAIN: BASE.DRAIN, FIZZ: BASE.FIZZ, size: null,
              COVER_MIN: BASE.COVER_MIN, MAX_TRAVEL: BASE.MAX_TRAVEL, dot: 1, ink:true, drag:false, cast:true,
              guide:false, numbers:false, shadow:'strokes', stray:'restart' },
    hard:   { kana:'難', blurb:'nothing shown. this is what a boss asks of you at the end of a stage.',
              locked:true },
  };
  // With words the joke turns around: the loanword is already English in a
  // Japanese accent, so the farang either says it that way (romaji) or says
  // its own word and leaves the accent to you (gaijin).
  const SIGNS = WORDS ? {
    kana:   { blurb:'コーヒー — the word, by copying it' },
    romaji: { blurb:'koohii — the farang\'s accent. you know what it sounds like; write it' },
    gaijin: { blurb:'coffee — the farang\'s own word. the accent is on you' },
  } : {
    kana:   { blurb:'ぬ — the shape, by copying it' },
    romaji: { blurb:'nu — the reading, which is the direction that matters' },
    gaijin: { blurb:'NEW — the way you probably say it' },
  };
  // A word realm remembers its own sign: what "gaijin" means differs.
  const SKEY = WORDS ? 'hito-start-' + CFG.deck.deck : 'hito-start';
  let difficulty = CFG.mode in DIFF && !DIFF[CFG.mode].locked ? CFG.mode : 'medium';
  try {
    const s = JSON.parse(localStorage.getItem(SKEY) || '{}') || {};
    if (s.difficulty in DIFF && !DIFF[s.difficulty].locked) difficulty = s.difficulty;
    if (s.sign in SIGNS) CFG.sign = s.sign;
  } catch(_){}
  function saveStart(){ try { localStorage.setItem(SKEY, JSON.stringify({difficulty, sign:CFG.sign})); } catch(_){} }
  function applyDifficulty(name){
    const d = DIFF[name];
    if (!d || d.locked) return false;
    difficulty = name;
    R_ON0 = d.R_ON0; DRAIN = d.DRAIN; FIZZ = d.FIZZ;
    COVER_MIN = d.COVER_MIN; MAX_TRAVEL = d.MAX_TRAVEL; DOT_SCALE = d.dot; SIZE_PIN = d.size;
    DRAG_FOLLOW = d.drag;
    GUIDE_ON = d.guide; GUIDE_NUMBERS = d.numbers; SHADOW_MODE = d.shadow;
    COMET_ON = d.comet !== false;   // the looping demonstration; guided turns it off
    STRAY_MODE = d.stray || 'drop';   // a stroke that went nowhere: dropped, or the character restarts
    saveStart();
    return true;
  }
  // and the glyph is redrawn under the new rules
  function setDifficulty(name){
    if (!applyDifficulty(name)) return false;
    loading = true; try { _load(idx); } finally { loading = false; }
    return true;
  }
  function setSign(v){ if (!(v in SIGNS)) return false; CFG.sign = v; saveStart(); return true; }
  applyDifficulty(difficulty);

  // ---- hitodama
  // A ghost light per character, keyed by the character itself (a codepoint,
  // never a grid index — words and future scripts write to the same ledger).
  // Tracing kindles it; a monster carrying the character spends it. Kept in
  // localStorage rather than a run, because it is what was learned, and the
  // ward falling does not unlearn anything.
  const HKEY = 'hito-hitodama';
  let HITODAMA = {};
  try { HITODAMA = JSON.parse(localStorage.getItem(HKEY) || '{}') || {}; } catch(_){ HITODAMA = {}; }
  // Lights the word game kept by word before v0.1.40. Nothing can spend them
  // now. Only keys longer than a character go: this store is shared with the
  // other realms on the same origin, and their characters are not ours to bin.
  for (const k of Object.keys(HITODAMA)) if ([...k].length > 1) delete HITODAMA[k];
  function saveH(){ try { localStorage.setItem(HKEY, JSON.stringify(HITODAMA)); } catch(_){} }
  const charge = ch => HITODAMA[ch] || 0;
  function kindle(ch, n){
    HITODAMA[ch] = Math.min(capNow(), charge(ch) + n);
    saveH();
    try { window.__sync && window.__sync.record('kindle', { glyph: ch, charge: HITODAMA[ch] }); } catch(_){}
    return HITODAMA[ch];
  }
  function quench(){ HITODAMA = {}; saveH(); }
  // Zaps during the attempt, so a clean trace can pay more than a scrappy one.
  // conjure() does not say how it went; zap() is the only global that does.
  let zapped = 0;
  const _zap = window.zap;
  window.zap = function(){
    if (DIFF[difficulty] && DIFF[difficulty].ink === false) return;   // guided: the light just stops
    zapped++; return _zap.apply(this, arguments);
  };
  // In guided the pen leaves no mark. redrawInk() is looked up by name on
  // every pointer move, so this wrapper does catch the engine's own calls.
  const _redrawInk = window.redrawInk;
  window.redrawInk = function(){
    if (DIFF[difficulty] && DIFF[difficulty].ink === false){ ink.clearRect(0,0,W,H); return; }
    return _redrawInk.apply(this, arguments);
  };

  // A lit character throws its own wisp. One at a time, on a cooldown, so a
  // swarm of three ぬ is answered visibly rather than vanishing in a frame.
  // Never at the monster the hand is answering right now: that one is yours.
  let castAt = 0;
  function dash(){ return { x: cx(), y: FH - 48 }; }   // above the dashboard
  const casting = () => !DIFF[difficulty] || DIFF[difficulty].cast !== false;
  // A farang the hand is tracing for is left to the hand — the trace lands
  // on it, and a light spent there is a light wasted — unless it is about
  // to walk in. Inside `rescue` of the ward the lights answer whatever they
  // can, whoever is tracing what. (The maintainer: "it targets weirdly,
  // allowing the closer farang to attack it.")
  const leftToHand = m => tracing() && !done && m === bearer(LETTERS[idx][0]) && m.d > CFG.rescue;
  function autocast(now){
    if (!casting()) return null;
    if (now - castAt < castMs()) return null;
    let best = null;
    for (const m of monsters){
      if (charge(key(m)) < 1) continue;
      if (leftToHand(m)) continue;
      if (shots.some(s => s.to === m)) continue;
      if (!best || m.d < best.d) best = m;
    }
    if (!best) return null;
    if (energy < CFG.castCost) return null;   // lit, but nothing to throw it with
    return fire(best, now);
  }
  // The release: a full bag is thrown all at once, every lit character at
  // its nearest bearer, nearest first, until the 気 runs out. It happens
  // when a stroke fills the bag, and when the ward is tapped. This is the
  // moment the hand may look up (the maintainer: "the way our base attacks
  // things is sort of boring"), and it is still nothing but characters the
  // hand has written.
  let flareAt = 0;   // `flare`, not `burst`: the engine owns `burst`
  function release(now){
    if (!casting()) return 0;
    now = now == null ? performance.now() : now;
    let n = 0;
    for (const m of monsters.slice().sort((a, b) => a.d - b.d)){
      if (energy < CFG.castCost) break;
      if (charge(key(m)) < 1 || leftToHand(m) || shots.some(s => s.to === m)) continue;
      fire(m, now); n++;
    }
    if (n){ flareAt = performance.now(); if (navigator.vibrate) navigator.vibrate([30, 40, 30]); }
    return n;
  }
  function fire(best, now){
    energy -= CFG.castCost;
    const ch = key(best);
    HITODAMA[ch] = charge(ch) - 1; saveH();
    // A word is answered one slot at a time, in order: this light writes the
    // kana the farang is waiting on and no other. A dark kana at the front of
    // a word holds up everything lit behind it, which is the right pressure —
    // and it is what keeps writing a word meaning writing it.
    let partial = false;
    if (best.w){
      best.ci++;
      partial = best.ci < best.w.chars.length;
      if (partial) best.i = AT[best.w.chars[best.ci]];
    }
    shots.push({ from: dash(), to: best, t: 0, ch, auto: true, partial });
    castAt = now; if (run) run.cast++;
    // The pen goes to the holes. If that was the word the tracer was pointed
    // at, it is now waiting on a different kana; and if that one is lit too,
    // the hand has no business here and is let go to find a dark one.
    if (best === locked && partial){
      if (charge(key(best)) >= 1) locked = null;
      retarget();
    }
    try { window.__sync && window.__sync.record('cast', { glyph: ch, left: HITODAMA[ch] }); } catch(_){}
    return best;
  }

  // Three ways a monster can ask. kana tests recall of the shape; romaji tests
  // the reading, which is the direction that actually matters; gaijin asks in
  // the learner's own broken accent, which is the same joke as the hero who
  // cannot read — the player is the foreigner here.
  const labelOf = (m, which) => m.w
    ? (which === 'romaji' ? m.w.romaji : which === 'gaijin' ? m.w.en : m.w.ja)
    : which === 'romaji' ? LETTERS[m.i][2] :
      which === 'gaijin' ? (LETTERS[m.i][7] || LETTERS[m.i][2].toUpperCase()) :
      LETTERS[m.i][0];
  const sign = m => labelOf(m, CFG.sign);

  // Mastery says a character was learned; the hand's ledger says whether it
  // still bites. One that does keeps coming back however high its level —
  // conjured six times with a fizzle each time is not a character to skip.
  const shaky = c => { try { return !!(window.__hand && window.__hand.shaky(c)); } catch(_){ return false; } };
  function spawn(){
    // Bias toward glyphs whose flame has gone out: a monster is a character
    // you are forgetting, so the roster is the gojuon and the encounter rate
    // follows what actually needs review.
    let i, w = null, tries = 0;
    if (WORDS){
      // the same rule at word level: a word whose every kana is mastered is
      // usually passed over for one that still has a dark character in it
      do { w = WORDS[Math.floor(Math.random()*WORDS.length)]; tries++; }
      while (tries < 8 && w.chars.every(c => (MASTERY[c]||0) > 2 && !shaky(c)) && Math.random() < 0.7);
      i = AT[w.chars[0]];
    } else {
      const pool = roster();
      // Half the time, a character this hand keeps getting wrong: "I always
      // mess up も ... I feel like that reflection should be used against me".
      // A monster is a character you are forgetting, and the ledger knows which.
      const biting = pool.filter(k => shaky(LETTERS[k][0]));
      if (biting.length && Math.random() < CFG.biteRate){ i = biting[Math.floor(Math.random()*biting.length)]; }
      else do { i = pool[Math.floor(Math.random()*pool.length)]; tries++; }
      while (tries < 8 && (MASTERY[LETTERS[i][0]]||0) > 2 && !shaky(LETTERS[i][0]) && Math.random() < 0.7);
    }
    // The last farang of a stage is its boss: it takes more hits, and its
    // character is traced with less help — the shape faint, the start dot
    // kept. The path is still there under the pen, so the start, the order
    // and the coverage are judged as ever; the eyes get a hint, not a
    // template. (The maintainer, 2026-09-23: "boss fights are when the
    // trace disappears ... perhaps not completely blank, just less help.")
    // Words are not bossed: a word is long enough.
    const boss = !!(ST && !w && (wave + 1) % ST.bossEvery === 0);
    monsters.push({
      i, w, ci: 0, zaps: 0, a: Math.random()*Math.PI*2, d: 1.05, boss,
      speed: CFG.speed * (0.8 + Math.random()*0.5) * (ST ? 1 + ST.speedStep*Math.floor(wave / ST.bossEvery) : 1),
      hp: hpFor(wave) + (boss ? ST.bossHp : 0), wob: Math.random()*6.28, born: performance.now(),
    });
    wave++;
    // 癒 tend: for every `tendEvery` waves held, a life back per level, up to
    // the ward's size. Held, not survived: it is paid when the wave comes,
    // so a ward at one life that lasts the stretch is mended at its end.
    if (upg.tend && CFG.tendEvery && wave % CFG.tendEvery === 0) ward = Math.min(wardMax(), ward + upg.tend);
    applyShadow();   // a boss arriving dims the shape for everyone, retarget or not
    // If the tracer is idle or pointed at a glyph nobody carries, the arrival
    // is what it should be showing.
    if (!locked || !monsters.includes(locked)) retarget();
  }

  // The target is LOCKED once the tracer has loaded its glyph, and stays
  // locked until it dies, reaches the ward, or the player taps another.
  //
  // It used to be recomputed as "whichever is nearest right now", which is
  // wrong the moment anything moves: monsters advance while you trace, so one
  // could overtake yours mid-glyph and conjure() would fire at the newcomer.
  // You drew あ and something carrying ぬ died for it. What you are answering
  // cannot be allowed to change underneath the answer.
  let locked = null;
  // The hand goes where the flame is out. A monster carrying a lit character
  // will be answered by its own wisp, so the tracer is pointed at the nearest
  // one that will not — which is the character that actually needs practice.
  function nearest(){
    let best = null, dark = null;
    for (const m of monsters){
      if (!best || m.d < best.d) best = m;
      if (charge(key(m)) < 1 && (!dark || m.d < dark.d)) dark = m;
    }
    return casting() ? (dark || best) : best;
  }
  function target(){
    if (locked && monsters.includes(locked)) return locked;
    locked = nearest();
    return locked;
  }
  // ---- what the tracer asks for. Its own order, not the farang's.
  // "Too much repeat on the hiragana words. I wrote tsu like four times in a
  // row. Don't base what I trace on what enemies populate." A word realm still
  // walks the word its farang carries; a character realm asks from a queue
  // over the open rows — the characters this hand keeps getting wrong first,
  // then the ones it has not written for longest — and no character comes
  // round again until `noRepeat` others have. What is drawn still hits
  // whichever farang carries it; what nothing carries is kept as a light.
  // A tap on a farang (or a test's ask()) puts its character at the head.
  let asked = null, queue = [], recent = [];
  // The one exception to the queue: a farang at the door (inside `rescue`)
  // whose character is dark. No light can answer it and the queue was going
  // to ask for something else while it walked in — "it targets weirdly,
  // allowing the closer farang to attack it". The pen goes to the hole
  // that is about to become a breach; the queue resumes after.
  function door(){
    let best = null;
    for (const m of monsters){
      if (m.d >= CFG.rescue) continue;
      if (casting() && charge(key(m)) >= 1) continue;
      if (!best || m.d < best.d) best = m;
    }
    return best;
  }
  function nextAsk(){
    if (asked !== null) return asked;
    const d = door(); if (d) return d.i;
    if (!queue.length){
      const pool = roster().filter(i => !recent.includes(i));
      const H = window.__hand;
      const last = i => { try { const e = H && H.ledger && H.ledger.g && H.ledger.g[LETTERS[i][0]]; return (e && +e.last) || 0; } catch(_){ return 0; } };
      queue = (pool.length ? pool : roster()).map(i => ({ i, k: [shaky(LETTERS[i][0]) ? 0 : 1, last(i), Math.random()] }))
        .sort((a, b) => a.k[0] - b.k[0] || a.k[1] - b.k[1] || a.k[2] - b.k[2]).map(o => o.i);
    }
    return queue[0];
  }
  function askDone(i){ if (asked === i) asked = null; if (queue[0] === i) queue.shift(); recent = [i, ...recent.filter(x => x !== i)].slice(0, CFG.noRepeat); }
  function ask(i){ asked = i; }
  function targetIdx(){ if (!WORDS) return nextAsk(); const t = target(); return t ? t.i : null; }

  // Tapping a monster is how you choose what to answer. This is the
  // identification mechanic arriving early: with the guide up the tracer still
  // shows you the shape, but which of them you take is yours.
  function pick(x, y){
    let best = null, bd = 44;
    for (const m of monsters){
      const p = px(m), d = Math.hypot(x-p.x, y-(p.y-14));
      if (d < bd){ bd = d; best = m; }
    }
    if (best && best !== locked){
      locked = best; ask(best.i);
      pendingRetarget = false;
      loading = true; try { _load(best.i); } finally { loading = false; }
      return true;
    }
    return false;
  }

  // ---- drive the tracer from the field
  // Every load() lands on whatever the field is asking for. conjure()'s own
  // delayed load(idx+1) therefore advances to the next target rather than to
  // the next character in the chart.
  const _load = window.load;
  let loading = false;
  window.load = function(i){
    zapped = 0; credited = 0;
    if (loading) return _load.apply(this, arguments);
    const t = targetIdx();
    return _load.call(this, t === null ? i : t);
  };
  // A trace in progress is not to be interrupted. When several monsters land
  // at once the field churns — each arrival clears the lock and retargets —
  // and every one of those reloads wipes whatever the player had drawn. The
  // glyph changing under a working hand is what makes a swarm feel broken
  // rather than hard.
  // `done` matters here. After a conjure prog sits at the end of the last
  // stroke, so without that clause tracing() stayed true forever: the deferred
  // retarget never ran, and when the field emptied and refilled the tracer was
  // left frozen on the celebration of a glyph nothing was carrying any more.
  // "In progress" has to mean what the hand means by it. prog > 0 misses
  // the first stroke before it finds the path, and misses a hand that has
  // just lifted to think — both of which is when a wisp elsewhere would swap
  // the glyph under a pen that is about to come back down. So: ink on the
  // board counts, and so does any contact with the pad in the last holdMs.
  let penAt = -1e9;
  function tracing(){
    return !done && (activeId !== null || prog > 0 || strokes.length > 0 || !!cur
                     || performance.now() - penAt < CFG.holdMs);
  }
  const inkEl = document.getElementById('ink');
  for (const ev of ['pointerdown', 'pointermove', 'pointerup'])
    inkEl.addEventListener(ev, e => {
      if (ev === 'pointermove' && !e.buttons) return;   // a hovering pen is not a hand at work
      penAt = performance.now();
    }, true);

  // Ink that was off the path is a smudge, not an attempt. When the pen
  // lifts the finished stroke is cut down to the runs that were on the path;
  // the orange runs go, with a puff where they were. A stroke that never
  // found the path goes entirely. Keeping the off-path tails of an otherwise
  // good stroke was tried first and it is what let an overdrawn line stay
  // and pile up. Purely cosmetic: travel and coverage are accumulated live
  // in follow(), not read back from the stroke list, so the scribble guard
  // is untouched. Returns how many runs were erased.
  function tidy(){
    if (!CFG.tidyStrays || mode !== 'practice' || !PATH.length || !strokes.length) return 0;
    if (DIFF[difficulty] && DIFF[difficulty].ink === false){ strokes.length = 0; return 0; }
    const s = strokes[strokes.length - 1];
    const keep = [], gone = [];
    let run = [];
    const flush = () => { if (run.length > 1) keep.push(run); run = []; };
    for (const q of s){
      if (q.on) run.push(q);
      else { flush(); gone.push(q); }
    }
    flush();
    if (!gone.length) return 0;
    strokes.pop(); strokes.push(...keep); redrawInk();
    const m = gone[Math.floor(gone.length / 2)];
    for (let k = 0; k < 10; k++){
      const a = Math.random()*6.283, v = .5 + Math.random()*1.5;
      parts.push({x:m.x, y:m.y, vx:Math.cos(a)*v, vy:Math.sin(a)*v, life:.6,
                  r:1 + Math.random()*1.5, c:'200,132,47'});
    }
    loop();
    return gone.length;
  }
  // Registered after the engine's own pointerup, so endStroke has already
  // pushed the stroke by the time this runs.
  inkEl.addEventListener('pointerup', () => tidy());
  inkEl.addEventListener('pointercancel', () => tidy());
  let pendingRetarget = false;
  // While a boss lives, every character is traced with less help: the shape
  // faint, the start dot kept. The full shape is back the moment it falls.
  function applyShadow(){
    const shown = (DIFF[difficulty] && DIFF[difficulty].shadow) || 'none';
    const want = (bossAlive() && shown !== 'none') ? 'faint' : shown;
    if (want !== SHADOW_MODE){ SHADOW_MODE = want; try { drawGuide(); } catch(_){} }
  }
  function retarget(force){
    if (locked && !monsters.includes(locked)) locked = null;
    const t = targetIdx();
    // Already on the right glyph is only a reason to do nothing if the tracer
    // is live on it. After a conjure `done` is set, and if the next target
    // happens to carry the same character the old early return left the
    // tracer sitting in its celebration until the engine's own 1.9s timer
    // fired — a dead spot precisely when two of the same arrive together.
    // A boss gets less help: its shape faint with the start dot kept, and
    // the full shape back for the next farang. Decided from who carries the
    // character, whether or not a reload follows: the farang after a boss
    // can carry the same character, and then nothing reloads.
    applyShadow();
    if (t === null || (t === idx && !done)) { pendingRetarget = false; return; }
    if (!force && tracing()){ pendingRetarget = true; return; }
    pendingRetarget = false;
    zapped = 0;
    loading = true; try { _load(t); } finally { loading = false; }
  }

  // ---- a finished glyph is the attack
  // What was drawn decides what is hit — not which object happened to be
  // locked when the pen came up. "You identify, you do not aim" taken
  // literally: finish ぬ and the nearest ぬ on the field takes it. If the
  // monster you were answering reached the ward mid-glyph, the character is
  // still correct and still finds a mark; if nothing on the field carries it,
  // the shot has nowhere to go and dissipates.
  function bearer(ch){
    // The one the tracer is pointed at, if it is waiting on this. Two words can
    // be waiting on the same kana (ー is in everything), and the nearer one
    // taking a stroke meant for the other is the ぬ-for-あ bug in a new coat.
    if (locked && monsters.includes(locked) && LETTERS[locked.i][0] === ch) return locked;
    let best = null;
    for (const m of monsters)
      if (LETTERS[m.i][0] === ch && (!best || m.d < best.d)) best = m;
    return best;
  }

  // every completed stroke fills 気 as it lands (shine() is the engine's own
  // stroke-complete, and reaches here as a global); a conjure credits any the
  // shine did not, so a trace is worth its strokes however it was scored
  const _shine = window.shine;
  const perStroke = () => CFG.energyPerStroke + upg.breath;
  // A stroke's 気 goes in through topUp, so a bag filled to the brim is
  // released whichever way the stroke was credited — as it shone, or at the
  // conjure for the strokes shine never saw.
  const topUp = n => { fill(n); if (n > 0 && energy >= energyMax()) release(); };
  if (typeof _shine === 'function') window.shine = function(){ topUp(perStroke()); credited++; return _shine.apply(this, arguments); };
  const _conjure = window.conjure;
  window.conjure = function(){
    const drew = LETTERS[idx][0];
    topUp(Math.max(0, Math.max(1, strokes.length) - credited) * perStroke()); credited = 0;
    // A word is only ever advanced by its own next kana, so there is no
    // falling back to the locked monster: a stray character hits nothing.
    const t = bearer(drew);   // a character hits whichever farang carries it, or nothing
    if (!WORDS) askDone(idx);
    let whole = true;   // did this finish what the monster carries
    if (t && t.w){
      // one kana of the word is written; the farang now waits for the next
      t.ci++; t.zaps += zapped;
      whole = t.ci >= t.w.chars.length;
      if (!whole) t.i = AT[t.w.chars[t.ci]];
    }
    if (t){
      shots.push({from:{x:cx(), y:FH-6}, to:t, t:0, ch:drew, partial: !whole});
      if (navigator.vibrate) navigator.vibrate([12,30,40]);
    }
    // And the character is kindled whether or not anything carried it — a
    // trace with nothing to hit is banked, not wasted. Clean pays more.
    // In a word too: every kana written lights that kana, and clean means
    // this kana. The light belongs to the character, whatever it was part of.
    if (casting()){
      const gain = CFG.hitodamaGain + (zapped ? 0 : CFG.cleanBonus);
      kindle(drew, gain);
      const d = dash();
      for (let k=0;k<14;k++)
        motes.push({x:d.x, y:d.y, vx:(Math.random()-.5)*1.8, vy:-Math.random()*2.2,
                    life:1, wisp:true});
    }
    // Ink is paid for the trace, not for the kill: the hand did the work
    // whether or not anything was standing there. A character conjured many
    // times pays a little less, so the run pushes toward the ones that are new.
    const wasClean = !zapped;
    if (run){ run.traced++; if (wasClean) run.clean++; }
    if (casting()) earn(Math.max(1, CFG.inkTrace + (zapped ? 0 : CFG.inkClean) - ((MASTERY[drew] || 0) >= CFG.inkMastered ? 1 : 0)) + upg.dilig);
    const r = _conjure.apply(this, arguments);
    // What this trace is worth when the run ends. The hand has just judged how
    // recognisable it was (the note is taken on the way into the engine): a
    // trace nobody could read pays half, one that could be the book pays half
    // again. With no judgement to go on — a build without the hand — it pays par.
    if (run){
      let q = null; try { const l = window.__hand && window.__hand.last; if (l && l.ok && l.glyph === drew && l.q != null) q = l.q; } catch(_){}
      if (q != null){ run.q += q; run.qn++; }
      run.pay += (wasClean ? CFG.tamaClean : CFG.tamaTrace) * (q == null ? 1 : 0.5 + q);
    }
    // The engine celebrates for 1.9s before advancing, which is dead time in a
    // game with a clock running — a fast hand finishes the next glyph before
    // the next glyph exists. Advance as soon as the shot lands instead.
    //
    // The engine's own delayed load(idx+1) needs no cancelling: load() clears
    // `done`, and that callback is guarded by it, so an early advance disarms
    // the late one. Without that it would fire mid-trace and wipe the strokes.
    // A word half written stays yours: the lock holds until its last kana.
    setTimeout(() => {
      // …unless the kana it now waits on is lit. Then its own light will
      // write it, and the hand is better spent on a farang with a dark one.
      locked = t && t.w && !whole && monsters.includes(t) && !(casting() && charge(key(t)) >= 1) ? t : null;
      retarget(true);
    }, CFG.advanceMs);
    return r;
  };

  let readings = [];
  function strike(m, partial, auto){
    const p0 = px(m);
    if (upg.shove) m.d = Math.min(1, m.d + upg.shove * CFG.shoveStep);
    if (partial){
      // a kana landed: the farang staggers back a step and waits for the next.
      // Only for the hand. A lit arsenal that also shoved would hold a word
      // at the edge for ever, and then there is no clock.
      if (!auto) m.d = Math.min(1, m.d + CFG.knockback);
      for (let k=0;k<8;k++)
        motes.push({x:p0.x, y:p0.y, vx:(Math.random()-.5)*2, vy:(Math.random()-.5)*2, life:.7});
      return;
    }
    m.hp -= 1 + upg.intent;   // intent: every light cuts deeper
    // The sound, attached to the kill. Tracing a shape teaches the shape and
    // nothing else — the hand can learn every stroke of ぬ without the reading
    // ever arriving. Success is the moment attention is highest, so that is
    // where the reading goes.
    // The correct reading, and underneath it the way you probably said it.
    // The joke is the teaching: "SOO" next to "tsu" names the dropped t far
    // better than the correct spelling does on its own, because the learner
    // recognises the wrong one as theirs.
    // A tough one is hit several times. The reading blooms when the hand
    // lands it and when it finally goes — not once per wisp, or it is noise.
    if (CFG.reading !== 'off' && (!auto || m.hp <= 0)){
      const p = px(m);
      let text, sub = null;
      if (m.w){
        // the word blooms with whichever half the sign kept back: after
        // "koohii" the news is "coffee", after "coffee" it is "koohii"
        const flip = CFG.sign === 'romaji';
        text = CFG.reading === 'gaijin' || (CFG.reading === 'both' && flip) ? m.w.en : m.w.romaji;
        if (CFG.reading === 'both') sub = flip ? m.w.romaji : m.w.en;
      } else {
        text = CFG.reading === 'gaijin' ? labelOf(m,'gaijin') : LETTERS[m.i][2];
        sub  = CFG.reading === 'both'   ? labelOf(m,'gaijin') : null;
      }
      readings.push({ x:p.x, y:p.y, life:1, text, sub });
    }
    for (let k=0;k<18;k++)
      motes.push({x:px(m).x, y:px(m).y, vx:(Math.random()-.5)*2.4,
                  vy:(Math.random()-.5)*2.4, life:1});
    if (m.hp <= 0){
      monsters = monsters.filter(x => x !== m);
      if (m === locked) locked = null;
      if (m.boss) applyShadow();
      killed++;
      if (auto) earn(CFG.inkKill + upg.harvest);
      // An observation, not a claim: what was answered and how long it took.
      // Deliberately not a score — the client does not get to assert totals.
      try { window.__sync && window.__sync.record('banish', {
        glyph: LETTERS[m.i][0], level: MASTERY[LETTERS[m.i][0]] || 0,
        word: m.w ? m.w.ja : undefined,
        ms: Math.round(performance.now() - m.born), sign: CFG.sign,
      }); } catch(_){}
      retarget();
    }
  }

  const px = m => ({ x: cx() + Math.cos(m.a)*m.d*FW*0.52,
                     y: cy() + Math.sin(m.a)*m.d*FH*0.52 });

  // ---- the loop
  function step(now){
    if (!tPrev) tPrev = now;
    const raw = (now - tPrev)/1000, dt = Math.min(0.05, raw); tPrev = now;
    if (paused){ draw(); return; }
    // How the phone kept up, counted rather than sampled: frames, the ones
    // over 25 ms (a dropped frame at 60 Hz) and over 50 ms (a stutter a
    // hand feels). Written into the run's record, so the table can say
    // what each device saw — an iPhone was "like butter" and a Pixel 9
    // "a touch laggy" on the same build, and nothing here could tell them apart.
    if (raw > 0 && raw < 2){ frames.n++; if (raw > 0.025) frames.slow++; if (raw > 0.05) frames.jank++; }
    if (!over){
      // Nothing to answer is not a rest, it is a dead screen. Refill at once.
      if (!monsters.length) spawnAt = Math.min(spawnAt, now);
      if (now > spawnAt){
        spawn();
        spawnAt = now + Math.max(CFG.spawnMin, CFG.spawnMs - wave*CFG.spawnRamp);
      }
      for (const m of monsters){
        m.d -= m.speed*dt;
        if (m.d <= 0.06){
          monsters = monsters.filter(x => x !== m);
          if (m === locked) locked = null;
          const bite = biteFor(wave, m.boss);
          ward = Math.max(0, ward - bite);
          try { window.__sync && window.__sync.record('breach', {
            glyph: LETTERS[m.i][0], word: m.w ? m.w.ja : undefined, wardLeft: ward, wave, bite,
          }); } catch(_){}
          retarget();
          if (navigator.vibrate) navigator.vibrate(90);
          if (ward <= 0){ over = true; endRun(); }
        }
      }
      autocast(now);
      for (const s of shots){
        s.t += dt*2.6;
        if (s.t >= 1){ strike(s.to, s.partial, s.auto); }
      }
      shots = shots.filter(s => s.t < 1 && monsters.includes(s.to));
    }
    // Deferred work, once the hand is free: a queued retarget, or a glyph that
    // no monster carries any more — which would otherwise strand the player
    // tracing a character that can no longer hit anything.
    if (!over && !tracing()){
      if (pendingRetarget) retarget();
      else if (!done && monsters.length && !bearer(LETTERS[idx][0])) retarget();
      else if (!done && !WORDS && asked === null){ const d = door(); if (d && d.i !== idx) retarget(); }
    }
    for (const p of motes){ p.x += p.vx; p.y += p.vy; p.life -= dt*1.6; }
    motes = motes.filter(p => p.life > 0);
    for (const r of readings){ r.y -= dt*26; r.life -= dt*0.85; }
    readings = readings.filter(r => r.life > 0);
    draw();
  }
  function fieldLoop(now){ step(now); requestAnimationFrame(fieldLoop); }

  // Glow without shadowBlur. CLAUDE.md's rule is "no per-frame shadow blur",
  // and the field broke it ten times a frame: a blurred shadow is rasterised
  // afresh on every draw, on a canvas a phone wide, sixty times a second.
  // A glow is a radial gradient painted once into a small sprite per colour
  // and stretched to size; the solid shape is drawn over it as before.
  const GLOWS = {};
  function glowAt(g, x, y, rx, ry, color, alpha){
    let sp = GLOWS[color];
    if (!sp){
      sp = document.createElement('canvas'); sp.width = sp.height = 64;
      const c = sp.getContext('2d'), gr = c.createRadialGradient(32, 32, 0, 32, 32, 32);
      if (gr && gr.addColorStop){ gr.addColorStop(0, color); gr.addColorStop(0.3, color); gr.addColorStop(1, 'rgba(0,0,0,0)'); }
      c.fillStyle = gr; c.fillRect(0, 0, 64, 64);
      GLOWS[color] = sp;
    }
    if (alpha != null && alpha !== 1){ g.save(); g.globalAlpha = alpha; }
    g.drawImage(sp, x - rx, y - ry, rx*2, ry*2);
    if (alpha != null && alpha !== 1) g.restore();
  }
  function draw(){
    const g = fc.getContext('2d');
    g.clearRect(0,0,FW,FH);
    const X = cx(), Y = cy();

    // the release: a ring leaving the ward
    const since = (performance.now() - flareAt)/520;
    if (since < 1){
      g.save(); g.globalAlpha = (1 - since) * 0.9; g.strokeStyle = 'rgba(127,209,196,.9)'; g.lineWidth = 2 + 4*(1 - since);
      g.beginPath(); g.arc(cx(), cy(), 20 + since*Math.max(FW, FH)*0.55, 0, 6.284); g.stroke(); g.restore();
    }
    // the ward being protected
    const pulse = 0.6 + 0.4*Math.sin(performance.now()/700);
    glowAt(g, X, Y, 13 + 22*pulse, 13 + 22*pulse, over ? 'rgba(120,60,50,.5)' : 'rgba(233,196,106,.5)', 1);
    g.fillStyle = over ? 'rgba(120,60,50,.9)' : 'rgba(233,196,106,.92)';
    g.beginPath(); g.arc(X, Y, 13, 0, 6.284); g.fill();
    g.strokeStyle = over ? 'rgba(200,90,70,.35)' : 'rgba(233,196,106,.22)';
    g.lineWidth = 1;
    g.beginPath(); g.arc(X, Y, 26 + 5*pulse, 0, 6.284); g.stroke();

    // ward health, as pips under it
    for (let k=0;k<wardMax();k++){
      g.fillStyle = k < ward ? 'rgba(233,196,106,.85)' : 'rgba(233,196,106,.14)';
      g.beginPath(); g.arc(X - (wardMax()-1)*5 + k*10, Y + 34, 3, 0, 6.284); g.fill();
    }

    const tgt = target();
    for (const m of monsters){
      const p = px(m), isT = m === tgt;
      const bob = Math.sin(performance.now()/500 + m.wob)*2.5;

      // the farang: a pale drifting shape, brighter the closer it gets
      const near = 1 - m.d;
      g.save();
      g.globalAlpha = 0.5 + 0.5*near;
      glowAt(g, p.x, p.y+bob, isT ? 17 + 16 : 17 + 8, isT ? 21 + 16 : 21 + 8, isT ? 'rgba(127,209,196,.45)' : 'rgba(150,170,190,.22)', 1);
      g.fillStyle = isT ? 'rgba(127,209,196,.30)' : 'rgba(170,185,200,.20)';
      g.beginPath(); g.ellipse(p.x, p.y+bob, 17, 21, 0, 0, 6.284); g.fill();
      g.restore();

      // the sign it carries — and for a word, a strip under it showing how
      // much of it has been written, blank where it has not
      const label = sign(m);
      g.font = (m.w ? (CFG.sign === 'kana' ? '600 18px' : '600 14px') : CFG.sign === 'romaji' ? '600 15px' : '600 22px')
        + ' ui-sans-serif,system-ui,"Klee One",sans-serif';
      const SP = 15;
      const w = Math.max(g.measureText(label).width, m.w ? m.w.chars.length*SP : 0) + 18;
      const bh = m.w ? 44 : 27;
      const by = p.y + bob - 36 - (bh - 27);
      g.fillStyle = isT ? 'rgba(20,32,32,.92)' : 'rgba(22,24,28,.85)';
      g.strokeStyle = isT ? 'rgba(127,209,196,.65)' : 'rgba(180,195,210,.28)';
      g.lineWidth = 1;
      g.beginPath();
      if (g.roundRect) g.roundRect(p.x-w/2, by-16, w, bh, 8);
      else g.rect(p.x-w/2, by-16, w, bh);
      g.fill(); g.stroke();
      const bb = by - 16 + bh;
      g.beginPath(); g.moveTo(p.x-5, bb); g.lineTo(p.x, bb+7); g.lineTo(p.x+5, bb);
      g.fillStyle = isT ? 'rgba(20,32,32,.92)' : 'rgba(22,24,28,.85)'; g.fill();
      g.fillStyle = isT ? '#bdf0e6' : 'rgba(226,232,240,.8)';
      g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText(label, p.x, by-2);
      if (m.w){
        const n = m.w.chars.length, x0 = p.x - (n-1)*SP/2;
        const reveal = CFG.sign === 'kana' || (DIFF[difficulty] && DIFF[difficulty].reveal);
        g.font = '600 13px ui-sans-serif,system-ui,"Klee One",sans-serif';
        for (let k = 0; k < n; k++){
          const written = k < m.ci, cur = k === m.ci;
          // teal for a slot your own light will write: the word shows, before
          // anything flies, how much of it you already hold and where the holes are
          const held = !written && casting() && charge(m.w.chars[k]) >= 1;
          g.fillStyle = written ? '#ffe9a8' : held ? 'rgba(127,209,196,.95)' : cur ? (isT ? '#bdf0e6' : 'rgba(226,232,240,.8)') : 'rgba(226,232,240,.35)';
          g.fillText(written || reveal ? m.w.chars[k] : '＿', x0 + k*SP, by + 16);
        }
      }
      // a boss says so, above its pips
      if (m.boss){
        g.font = '700 12px ui-sans-serif,system-ui,"Klee One",sans-serif';
        g.fillStyle = isT ? 'rgba(233,196,106,.95)' : 'rgba(233,196,106,.6)';
        g.fillText('将 · less help for all', p.x, by - (m.hp > 1 ? 34 : 24));
      }
      // how much more it takes: one pip per hit still owed, above the bubble
      // (under it is the farang's own head)
      if (m.hp > 1){
        g.fillStyle = isT ? 'rgba(233,196,106,.95)' : 'rgba(233,196,106,.6)';
        for (let k = 0; k < m.hp; k++){
          g.beginPath(); g.arc(p.x - (m.hp-1)*4 + k*8, by - 23, 2.4, 0, 6.284); g.fill();
        }
      }
      // a lit character: its own wisp will answer this one
      if (casting() && charge(key(m)) >= 1){
        glowAt(g, p.x + w/2 + 2, by-14, 11, 11, 'rgba(127,209,196,.6)', 1);
        g.fillStyle = 'rgba(160,230,215,.95)';
        g.beginPath(); g.arc(p.x + w/2 + 2, by-14, 3.2, 0, 6.284); g.fill();
      }
    }

    // the glyph in flight
    for (const s of shots){
      const p = px(s.to);
      const t = s.t, e = t*t*(3-2*t);
      const x = s.from.x + (p.x - s.from.x)*e;
      const y = s.from.y + (p.y - s.from.y)*e - Math.sin(t*Math.PI)*46;
      g.save();
      if (s.auto){
        // the ghost light, cold and trailing, the character faint inside it
        for (let k=3;k>=1;k--){
          const tt = Math.max(0, t - k*0.05), ee = tt*tt*(3-2*tt);
          const tx = s.from.x + (p.x - s.from.x)*ee;
          const ty = s.from.y + (p.y - s.from.y)*ee - Math.sin(tt*Math.PI)*46;
          g.globalAlpha = 0.28 - k*0.07;
          g.fillStyle = 'rgba(127,209,196,1)';
          g.beginPath(); g.arc(tx, ty, 9 - k*1.5, 0, 6.284); g.fill();
        }
        g.globalAlpha = 0.95;
        g.font = '700 15px ui-sans-serif,system-ui,"Klee One",sans-serif';
        const rx = Math.max(11, g.measureText(s.ch).width/2 + 7);   // a word needs a longer light
        glowAt(g, x, y, rx + 18, 13 + 18, 'rgba(127,209,196,.6)', 1);
        g.fillStyle = 'rgba(190,240,228,.9)';
        g.beginPath(); g.ellipse(x, y, rx, 13, 0, 0, 6.284); g.fill();
        g.fillStyle = 'rgba(20,40,40,.9)';
        g.textAlign = 'center'; g.textBaseline = 'middle';
        g.fillText(s.ch, x, y+1);
      } else {
        g.globalAlpha = 0.9;
        glowAt(g, x, y, 26, 26, 'rgba(233,196,106,.55)', 1);
        g.fillStyle = '#ffe9a8';
        g.font = '700 26px ui-sans-serif,system-ui,"Klee One",sans-serif';
        g.textAlign = 'center'; g.textBaseline = 'middle';
        g.fillText(s.ch, x, y);
      }
      g.restore();
    }

    for (const r of readings){
      const a = Math.min(1, r.life*1.6);
      g.save();
      g.globalAlpha = a;
      glowAt(g, r.x, r.y, 30, 22, 'rgba(233,196,106,.45)', 1);
      g.fillStyle = '#ffe9a8';
      g.font = `700 ${Math.round(26 + 10*(1-r.life))}px ui-sans-serif,system-ui`;
      g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText(r.text, r.x, r.y);
      if (r.sub){
        g.globalAlpha = a*0.8;
        g.fillStyle = '#9fd8cc';
        g.font = `600 ${Math.round(15 + 5*(1-r.life))}px ui-sans-serif,system-ui`;
        g.fillText(r.sub, r.x, r.y + 26);
      }
      g.restore();
    }
    for (const p of motes){
      g.globalAlpha = Math.max(0, p.life);
      g.fillStyle = p.wisp ? '#a8ecdc' : '#ffe9a8';
      g.fillRect(p.x, p.y, 2, 2);
    }
    g.globalAlpha = 1;

    // ---- the hitodama dash: the character in the sketchbook and how many
    // ghost lights it holds. Sits on the seam between field and sketchbook,
    // which is where the wisps set out from.
    if (casting()) {
      // for a word: the word so far, blank where it is still to come
      const t = target();
      const ch = t && t.w ? t.w.chars.map((c, k) => k < t.ci ? c : '＿').join('') : LETTERS[idx][0];
      const c = charge(LETTERS[idx][0]), cap = capNow();
      const d = dash();
      g.font = '700 17px ui-sans-serif,system-ui,"Klee One",sans-serif';
      const lw = Math.max(17, g.measureText(ch).width);
      const pipW = 14, w = 41 + lw + cap*pipW;
      const x0 = d.x - w/2;
      g.fillStyle = 'rgba(16,22,24,.78)';
      g.strokeStyle = c >= 1 ? 'rgba(127,209,196,.45)' : 'rgba(233,196,106,.16)';
      g.lineWidth = 1;
      g.beginPath();
      if (g.roundRect) g.roundRect(x0, d.y-13, w, 26, 13); else g.rect(x0, d.y-13, w, 26);
      g.fill(); g.stroke();
      g.textBaseline = 'middle';
      g.fillStyle = c >= 1 ? '#bdf0e6' : 'rgba(226,232,240,.75)';
      g.font = '700 17px ui-sans-serif,system-ui,"Klee One",sans-serif';
      g.textAlign = 'left';
      g.fillText(ch, x0 + 11, d.y + 1);
      g.font = '10px ui-sans-serif,system-ui';
      g.fillStyle = 'rgba(160,190,185,.7)';
      g.fillText('人魂', x0 + 15 + lw, d.y + 1);
      const flick = 0.75 + 0.25*Math.sin(performance.now()/160);
      for (let k=0;k<cap;k++){
        const px = x0 + 41 + lw + k*pipW + 4, lit = k < c;
        if (lit) glowAt(g, px, d.y, 3.4 + 8*flick, 4 + 8*flick, 'rgba(127,209,196,.6)', 1);
        g.fillStyle = lit ? 'rgba(170,236,220,.95)' : 'rgba(127,209,196,.14)';
        g.beginPath(); g.ellipse(px, d.y, 3.4, lit ? 4.6*flick+1 : 3.4, 0, 0, 6.284); g.fill();
      }
    }

    g.fillStyle = 'rgba(233,196,106,.55)';
    g.font = '12px ui-sans-serif,system-ui'; g.textAlign = 'left';
    g.textBaseline = 'alphabetic';
    // Bottom left: the workshop strip has the top, and a tally under buttons
    // is a tally nobody can read. The wave sits with it, because how far a run
    // got is what a run is for.
    g.fillText(`banished ${killed} · wave ${wave}`, 12, FH - 12);
  }

  function restart(){
    if (typeof openTab === 'function') openTab(null);
    monsters = []; shots = []; motes = []; readings = [];
    upg = freshUpg(); run = newRun(); ended = null;
    zapped = 0;   // a new run starts clean: the counter is otherwise only cleared when a glyph loads,
                  // and a run that restarts on the same character does not load one
    sumi = own('inkwell') * CFG.inkwellStep; energy = CFG.energyStart; credited = 0;
    ward = wardMax(); over = false; wave = 0; killed = 0; locked = null; asked = null; queue = []; recent = [];
    spawnAt = 0; tPrev = 0; castAt = 0; paused = false; frames = { n:0, slow:0, jank:0 }; spawn(); retarget();
    // The last banish of a stage leaves the engine celebrating: the whole path
    // lit, `done` set. If the first target of the new run is the character
    // already loaded, retarget() has nothing to change and that lit path is
    // what the player starts on ("an already traced path comes up, typically
    // when I'm progressing to the next round"). A run begins on a clean glyph.
    // ... and a half-traced one is no better: "again" after the ward fell
    // mid-stroke kept the lit half of the character (the maintainer,
    // reproduced once in a session). A run begins on a clean glyph, always.
    if (done || prog > 0 || strokes.length){ loading = true; try { _load(idx); } finally { loading = false; } }
    renderUpg();
  }

  // ---- the end of a run
  // The ward falling used to be a toast and a field that went quiet. A run
  // that ends without saying what it was is a run that did not count, and the
  // player said so: "make it so the game ends when i lose all health and
  // saves that trace experience and all that". So it ends, it says what
  // happened, and it is written down in three places that each do a different
  // job: the hand's ledger (on the device, and in the save that follows a
  // signed-in player), and the events table (an observation, for later).
  let ended = null;
  function endRun(){
    if (!run || ended) return ended;
    const H = window.__hand;
    // What the run leaves behind. Paid for tracing, most of all clean tracing;
    // guided cannot be zapped, so there every trace would count as clean, and
    // it pays less instead. Holding a stage to the end is worth half again.
    const p = purse();
    const pay = !p ? 0 : Math.round((run.pay + Math.floor(wave/CFG.tamaWaves))
                                     * (DIFF[difficulty] && DIFF[difficulty].tama != null ? DIFF[difficulty].tama : 1)
                                     * (1 + upg.rise * CFG.riseStep));   // 起: get up with more
    if (p) p.earn(pay);
    // guided is practice: the hand keeps the run, but not as a furthest wave
    const rec = { at: run.at, realm: REALM, practice: difficulty === 'guided' || undefined, tama: pay,
                  quality: run.qn ? Math.round(100*run.q/run.qn)/100 : undefined, wave, banished: killed, traced: run.traced, clean: run.clean,
                  sumi: run.earned, cast: run.cast, ms: Math.round(performance.now() - run.began),
                  difficulty, sign: CFG.sign, upgrades: {...upg},
                  frames: {...frames}, plat: (navigator.platform || '').slice(0, 24) || undefined,
                  v: typeof APP_VERSION !== 'undefined' ? APP_VERSION : undefined };
    let best = null;
    try { if (H && H.run) best = H.run(rec); } catch(_){}
    try { window.__sync && window.__sync.record('run', rec); } catch(_){}
    ended = { rec, best, since: run.at, pay };
    if (navigator.vibrate) navigator.vibrate([90, 60, 160]);
    // a beat, so the last breach is seen before the page covers it
    setTimeout(() => { if (over && ended) openOver(); }, 700);
    return ended;
  }

  // ---- the workshop strip
  // DOM, not canvas: it is redrawn when something changes rather than every
  // frame, and a button is a button to a screen reader and to a finger.
  const strip = document.createElement('div');
  strip.className = 'upg'; strip.id = 'upg';
  const stripGuard = document.createElement('div');
  stripGuard.className = 'upg'; stripGuard.id = 'upg-guard';
  const stripDrive = document.createElement('div');
  stripDrive.className = 'upg'; stripDrive.id = 'upg-drive';
  let upgMarkup = '', guardMarkup = '', driveMarkup = '';
  const stripHtml = tabName => `<div class="upg-ink" title="ink — earned by tracing, most of all by tracing cleanly">墨 ${sumi}</div>`
      + Object.entries(UPG).filter(([, u]) => u.tab === tabName).map(([id, u]) => {
          const maxed = upg[id] >= u.max, c = costOf(id);
          return `<button data-upg="${id}" title="${u.blurb}" class="${!maxed && sumi >= c ? 'can' : ''}"${maxed ? ' disabled' : ''}>`
            + `<b>${MARK[id] || ''}<i class="k">${u.kana}</i></b>${u.name}${upg[id] ? ' ' + upg[id] : ''}<small>${maxed ? 'max' : '墨 ' + c + '<i> · ' + u.blurb + '</i>'}</small></button>`;
        }).join('');
  function renderUpg(){
    strip.innerHTML = upgMarkup = stripHtml('skills');
    stripGuard.innerHTML = guardMarkup = stripHtml('guard');
    stripDrive.innerHTML = driveMarkup = stripHtml('drive');
    for (const el of [strip, stripGuard, stripDrive]) if (el.querySelectorAll) for (const b of el.querySelectorAll('button[data-upg]')) b.onclick = () => buy(b.dataset.upg);
    if (typeof renderDash === 'function') renderDash();
  }
  // ---- the dashboard, and the tabs behind it
  // `dash-tabs`, not `tabs`: the shell hides the workshop's `.tabs` with an
  // !important rule up top, and a dashboard that borrowed the name shipped
  // three releases (v0.1.55-v0.1.60) with its tab buttons invisible in every
  // real browser. The stub DOM cannot see a stylesheet; a screenshot can.
  const bar = document.createElement('div'); bar.className = 'dash-bar'; bar.id = 'dashbar';
  const panel = document.createElement('div'); panel.className = 'panel'; panel.id = 'panel'; panel.hidden = true;
  const panelSkills = document.createElement('div'); panelSkills.innerHTML = '<p class="panel-h">技 · this run · intent, bought with 墨</p>'; panelSkills.appendChild(strip);
  const panelGuard = document.createElement('div'); panelGuard.innerHTML = '<p class="panel-h">耐 · this run · persistence, bought with 墨</p>'; panelGuard.appendChild(stripGuard);
  const panelDrive = document.createElement('div'); panelDrive.innerHTML = '<p class="panel-h">志 · this run · motivation, bought with 墨</p>'; panelDrive.appendChild(stripDrive);
  const panelLanterns = document.createElement('div');
  panel.appendChild(panelSkills); panel.appendChild(panelGuard); panel.appendChild(panelDrive); panel.appendChild(panelLanterns);
  stageEl.parentNode.insertBefore(panel, stageEl.nextSibling); wrap.appendChild(bar);
  let tab = null, dashMarkup = '';
  // Bars, not hearts (the maintainer: "let's not do hearts. I like bars. For
  // both the life and energy for casting").
  // Marks for the tabs, inline and in the button's own colour so the theme
  // table paints them: a sword, a shield, a five-yen coin, a flame.
  const ICON = {
    sword:  '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M13 3 6 10M3.5 9.5l3 3M2.5 13.5l2-2M12 2l2 2" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
    shield: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.6 13.3 3.6V8c0 3.4-2.3 5.7-5.3 7C5 13.7 2.7 11.4 2.7 8V3.6Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>',
    coin:   '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="5.8" fill="none" stroke="currentColor" stroke-width="1.6"/><circle cx="8" cy="8" r="1.7" fill="none" stroke="currentColor" stroke-width="1.4"/></svg>',
    flame:  '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.8c2 3 3.6 4.4 3.6 7.4a3.6 3.6 0 0 1-7.2 0C4.4 6.2 6 4.8 8 1.8Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>',
  };
  const bar_ = (cls, kana, v, max, title) => `<span class="bar ${cls}" title="${title}"><i style="width:${max > 0 ? Math.round(100*Math.max(0, Math.min(max, v))/max) : 0}%"></i><b>${kana}</b><small>${v}/${max}</small></span>`;
  const canBuyAny = tabName => Object.entries(UPG).some(([id, u]) => u.tab === tabName && upg[id] < u.max && sumi >= costOf(id));
  function renderDash(){
    const p = purse();
    const m = bar_('life', '命', ward, wardMax(), 'the ward: ' + ward + ' of ' + wardMax())
      + bar_('energy', '気', energy, energyMax(), '気 — every stroke fills it, every wisp spends it: ' + energy + ' of ' + energyMax())
      + `<span class="n" title="ink — earned by tracing, spent on this run's skills">墨 ${sumi}</span>`
      + (p ? `<span class="n" title="魂 — earned by runs, spent on what lasts">魂 ${p.balance}</span>` : '')
      + `<span class="n" title="the wave"><small>波</small> ${wave}</span>`
      + `<span class="dash-tabs"><button data-tab="trace" aria-pressed="${tab === null}" title="the sketchbook: write" aria-label="the sketchbook">筆</button>`
      + `<button data-tab="skills" aria-pressed="${tab === 'skills'}" class="${canBuyAny('skills') ? 'can' : ''}" title="技 intent: how you attack" aria-label="intent: attack upgrades">${ICON.sword}技</button>`
      + `<button data-tab="guard" aria-pressed="${tab === 'guard'}" class="${canBuyAny('guard') ? 'can' : ''}" title="耐 persistence: how you defend" aria-label="persistence: defence upgrades">${ICON.shield}耐</button>`
      + `<button data-tab="drive" aria-pressed="${tab === 'drive'}" class="${canBuyAny('drive') ? 'can' : ''}" title="志 motivation: how you earn" aria-label="motivation: currency upgrades">${ICON.coin}志</button>`
      + (p ? `<button data-tab="lanterns" aria-pressed="${tab === 'lanterns'}" title="灯 what lasts, bought with 魂" aria-label="lanterns: what lasts">${ICON.flame}灯</button>` : '') + `</span>`;
    if (m === dashMarkup) return;
    dashMarkup = m; bar.innerHTML = m;
    if (bar.querySelectorAll) for (const b of bar.querySelectorAll('button[data-tab]')) b.onclick = () => openTab(tab === b.dataset.tab || b.dataset.tab === 'trace' ? null : b.dataset.tab);
  }
  function renderLanterns(){ panelLanterns.innerHTML = `<p class="panel-h">灯 · what lasts · bought with 魂</p>` + workshopHtml(); wireWorkshop(renderLanterns, panelLanterns); renderDash(); }
  // A tab does not pause the run. That is the point: the waves keep coming
  // while you shop, and knowing when you can afford to is the game. And the
  // sketchbook is a tab too: while a shop is open there is nothing to trace
  // on, so a lit character's own lights are all that holds the ward. A shop
  // does not open under a pen that is down; lift, and find the gap.
  function openTab(name){
    if (name && name !== 'trace' && tracing()) return tab;
    tab = name && name !== 'trace' ? name : null;
    if (tab && !stageEl.hidden){ const r = stageEl.getBoundingClientRect(); if (r.width > 0){ panel.style.width = r.width + 'px'; panel.style.height = r.height + 'px'; } }
    stageEl.hidden = !!tab;
    panel.hidden = !tab; panelSkills.hidden = tab !== 'skills'; panelGuard.hidden = tab !== 'guard'; panelDrive.hidden = tab !== 'drive'; panelLanterns.hidden = tab !== 'lanterns';
    if (tab === 'lanterns') renderLanterns();
    renderDash();
    return tab;
  }
  renderUpg(); renderDash();

  // ---- the start page
  const start = document.createElement('div');
  start.className = 'start'; start.id = 'start';
  let view = 'start', markup = '';
  const esc = t => String(t).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  function renderCredits(){
    const lines = (CFG.credits || []).map(l => `<p>${esc(l)}</p>`).join('');
    start.innerHTML = markup = `<div class="start-card credits">
      <div class="start-title">hito<span>人</span></div>
      <div class="start-sub">who this leans on</div>
      <p class="lead"><b>人</b>is two strokes, and neither can stand on its own. Take one away and the character falls.</p>
      <p>That is the project. One person records the strokes, another draws the letterforms, testers find the bugs, someone builds it, and every learner leans on all of them.</p>
      ${lines}
      <p class="small">${esc(CFG.credit || '')}</p>
      <p class="small">Single file, opens from a double-click, and needs no network to play. Your progress lives on this device.${window.__sync && window.__sync.enabled ? ' When there is a network, notes on how the tracing went are sent to the workshop under a made-up device name; ✋ hand, up top, turns that off.' : ''}</p>
      <button class="start-go">back</button>
    </div>`;
    const go = start.querySelector('.start-go');
    if (go) go.onclick = () => { view = 'start'; renderStart(); };
  }
  function renderStart(){
    if (view === 'credits') return renderCredits();
    if (view === 'over') return renderOver();
    // Other realms, as links to sibling files. They are other single-file
    // builds beside this one — on Pages or in the same folder offline — so
    // the page is only a hop away and nothing here depends on it loading.
    const realms = () => !(CFG.realms || []).length ? '' :
      `<div class="start-h">other realms</div><div class="start-row">` +
      CFG.realms.map(r => `<a href="${esc(r.file)}"><b>${r.kana ? `<i>${esc(r.kana)}</i>` : ''}${esc(r.label)}</b><small>${esc(r.blurb || '')}</small></a>`).join('') +
      `</div>`;
    // What draws belongs to the hand layer; the page only shows its switch,
    // because on a phone it is the difference between a game and a picture.
    const hand = window.__hand;
    const INPUTS = { pen: { kana:'✎', blurb:'fingers and palms are ignored, so the hand can rest on the glass.' },
                     finger: { kana:'☝', blurb:'anything that touches draws. one finger at a time.' } };
    const row = (k, table, cur) => Object.entries(table).map(([n, d]) =>
      `<button data-k="${k}" data-v="${n}" aria-pressed="${n === cur}"${d.locked ? ' disabled' : ''}>`
      + `<b>${d.kana ? `<i>${d.kana}</i>` : ''}${n}</b><small>${d.blurb}</small></button>`).join('');
    start.innerHTML = markup = `<div class="start-card">
      <div class="start-title">hito<span>人</span></div>
      <div class="start-sub">${esc(REALM)} · v${typeof APP_VERSION !== 'undefined' ? APP_VERSION : ''}</div>
      <div class="start-h">how much help</div>
      <div class="start-row">${row('diff', DIFF, difficulty)}</div>
      <div class="start-h">what the sign says</div>
      <div class="start-row">${row('sign', SIGNS, CFG.sign)}</div>
      ${ST ? `<div class="start-h">the tower · furthest wave ${bestWave()} · ${roster().length} characters on the field${nextRowAt() < Infinity ? ' · next row of the chart at wave ' + nextRowAt() : ' · every row of the chart'}${difficulty === 'guided' ? ' · <b class="needs">practice: nothing counts</b>' : ''}</div>` : ''}
      ${workshopHtml()}
      ${hand ? `<div class="start-h">draw with</div><div class="start-row">${row('input', INPUTS, hand.input)}</div>` : ''}
      ${realms()}
      <button class="start-go">${over ? 'begin again' : 'begin'}</button>
      <div class="start-links">${hand ? '<button class="start-hand">how the hand is doing</button>' : ''}<button class="start-credits">who this leans on</button></div>
      <div class="start-foot">${WORDS ? 'draw below · the farang come from above · write what they are saying, one kana at a time' : 'draw below · the farang come from above · the one you are answering is yours'}</div>
    </div>`;
    const cr = start.querySelector('.start-credits');
    if (cr) cr.onclick = () => { view = 'credits'; renderStart(); };
    const hb = start.querySelector('.start-hand');
    if (hb) hb.onclick = () => hand.show();
    wireWorkshop(renderStart);
    for (const b of start.querySelectorAll('button[data-k]')){
      b.onclick = () => {
        if (b.dataset.k === 'diff') setDifficulty(b.dataset.v);
        else if (b.dataset.k === 'input') hand.setInput(b.dataset.v);
        else if (b.dataset.k === 'stage'){ if (setStage(b.dataset.v) && !over){ monsters = []; wave = 0; killed = 0; locked = null; spawn(); retarget(true); } }
        else setSign(b.dataset.v);
        renderStart();
      };
    }
    const go = start.querySelector('.start-go');
    if (go) go.onclick = begin;
  }
  // The redo button belongs to a run, not to the page over it.
  let redoShown = false;
  function showRedo(v){ redoShown = v; if (typeof redo !== 'undefined') redo.hidden = !v; }
  // The lantern workshop. Shown where a round ends and where one begins.
  function workshopHtml(){
    const p = purse(); if (!p) return '';
    const items = Object.entries(LANTERN).map(([id, u]) => {
      const lv = own(id), maxed = lv >= u.max, c = lanternCost(id);
      return `<button data-lantern="${id}"${maxed || p.balance < c ? ' disabled' : ''} class="${!maxed && p.balance >= c ? 'can' : ''}">`
        + `<b>${MARK[id] || ''}<i>${u.kana}</i>${u.name}${lv ? ' ' + lv : ''}</b><small>${maxed ? 'as far as it goes' : '魂 ' + c + ' · ' + u.blurb}</small></button>`;
    }).join('');
    const gate = '';   // the gate was bought with 魂 until v0.1.54; rows open by distance now
    return `<div class="start-h">the lantern workshop · 魂 ${p.balance}</div><div class="start-row lantern">${items}${gate}</div>`;
  }
  function wireWorkshop(again, root){
    for (const b of (root || start).querySelectorAll('button[data-lantern]')) b.onclick = () => {
      const id = b.dataset.lantern;
      if (buyLantern(id)) again();
    };
  }
  function renderOver(){
    const e = ended; if (!e){ view = 'start'; return renderStart(); }
    const r = e.rec, H = window.__hand;
    const mins = r.ms >= 60000 ? Math.floor(r.ms/60000) + 'm ' + Math.round((r.ms % 60000)/1000) + 's' : Math.round(r.ms/1000) + 's';
    const fresh = e.best && e.best.isBest && e.best.runs > 1;
    // the handwriting of this run, the way the hand's own page draws it
    let hands = '';
    try { if (H && H.thumbs) hands = H.thumbs(e.since, 12, true); } catch(_){}
    start.innerHTML = markup = `<div class="start-card over">
      <div class="start-title">the ward fell</div>
      <div class="start-sub">${esc(REALM)} · wave ${r.wave}${fresh ? ' · <b>your furthest yet</b>' : e.best && e.best.wave > r.wave ? ' · furthest ' + e.best.wave : ''}</div>
      <div class="over-nums">
        <div><b>${r.banished}</b><small>banished</small></div>
        <div><b>${r.traced}</b><small>traced</small></div>
        <div><b>${r.traced ? Math.round(100*r.clean/r.traced) + '%' : '—'}</b><small>clean</small></div>
        <div><b>${mins}</b><small>held</small></div>
      </div>
      <p class="over-line">${r.cast} answered by your own lights${e.best && e.best.total ? ' · ' + e.best.total + ' conjured in all' : ''}</p>
      ${r.practice ? `<p class="over-line">guided is practice: nothing here counts toward the tower or 魂.</p>` : ''}
      ${purse() ? `<p class="over-pay">+ 魂 ${e.pay}<small>${r.quality != null ? Math.round(r.quality*100) + '% recognisable · ' : ''}clean, readable traces pay the most${DIFF[difficulty] && DIFF[difficulty].tama ? ' · ' + difficulty + ' pays ×' + DIFF[difficulty].tama : ''}</small></p>` : ''}
      ${workshopHtml()}
      ${hands ? `<div class="start-h">as you wrote them</div>${hands}` : ''}
      <button class="start-go">again</button>
      <div class="start-links"><button class="start-page">difficulty and the sign</button>${H ? '<button class="start-hand">how the hand is doing</button>' : ''}</div>
      <div class="start-foot">${H && window.__account && window.__account.user ? 'saved to your account' : 'saved on this device'}</div>
    </div>`;
    const go = start.querySelector('.start-go');
    if (go) go.onclick = () => begin();
    wireWorkshop(renderOver);
    const pg = start.querySelector('.start-page'); if (pg) pg.onclick = () => { view = 'start'; renderStart(); };
    const hb = start.querySelector('.start-hand'); if (hb) hb.onclick = () => H.show();
  }
  function openOver(){ openTab(null); paused = true; view = 'over'; renderStart(); start.hidden = false; showRedo(false); }
  function openStart(){ paused = true; view = over && ended ? 'over' : 'start'; renderStart(); start.hidden = false; showRedo(false); }
  function openCredits(){ paused = true; view = 'credits'; renderStart(); start.hidden = false; showRedo(false); }
  function begin(){
    start.hidden = true;
    if (over) restart(); else paused = false;
    // the clock starts when the player does, not when the page loaded
    if (run && !run.started){ run.started = true; run.began = performance.now(); run.at = Date.now(); }
    tPrev = 0;
    showRedo(true);
  }
  addEventListener('DOMContentLoaded', () => {
    document.body.appendChild(start);
    showRedo(!paused);
    // No menu button — it sat under the pen's hand. The name in the header
    // is the way back to the page.
    const brand = document.querySelector && document.querySelector('header .brand');
    if (brand){ brand.title = 'Difficulty and the sign'; brand.onclick = openStart; }
  });
  fc.addEventListener('pointerdown', e => {
    if (over){ openStart(); return; }
    const r = fc.getBoundingClientRect();
    const x = e.clientX - r.left, y = e.clientY - r.top;
    if (!paused && Math.hypot(x - cx(), y - cy()) < 34){ release(); return; }   // the ward itself: throw what you have
    pick(x, y);
  });

  // A handle on the field, for the same reason the tracer has one: a game
  // loop that cannot be inspected can only be tested by playing it.
  window.__field = {
    get monsters(){ return monsters; },
    get shots(){ return shots; },
    get ward(){ return ward; },
    get over(){ return over; },
    get killed(){ return killed; },
    get target(){ return target(); },
    get locked(){ return locked; },
    get pending(){ return pendingRetarget; },
    get readings(){ return readings; },
    get paused(){ return paused; },
    get difficulty(){ return difficulty; },
    get sign(){ return CFG.sign; },
    base: BASE, setDifficulty, setSign, begin, openStart, openCredits, signOf: sign,
    get view(){ return view; }, get startHtml(){ return markup; }, get redoShown(){ return redoShown; },
    get hitodama(){ return HITODAMA; },
    get ink(){ return sumi; }, get bestWave(){ return bestWave(); }, get wave(){ return wave; },
    needs, rowsOpen, nextRowAt, totalRows, bossAlive, roster, buyLantern, lanternCost, capNow, LANTERN, ask, get asked(){ return asked; }, get queue(){ return queue; },
    get run(){ return run; }, get ended(){ return ended; }, get frames(){ return frames; }, endRun, openOver, get upgrades(){ return upg; }, get wardMax(){ return wardMax(); },
    get upgHtml(){ return upgMarkup; }, get guardHtml(){ return guardMarkup; }, get driveHtml(){ return driveMarkup; }, get lanternHtml(){ return panelLanterns.innerHTML; }, get sketchbook(){ return stageEl; }, get dashHtml(){ return dashMarkup; }, openTab, get tab(){ return tab; }, TABS,
    get energy(){ return energy; }, get energyMax(){ return energyMax(); }, fill,
    earn, buy, costOf, hpFor, biteFor, castMs, hit: strike, UPG,
    get words(){ return WORDS; }, at: AT, keyOf: key,
    charge, kindle, quench, autocast, release, tidy, casting, get flare(){ return flareAt; },
    touch(){ penAt = performance.now(); },
    bearer,
    spawn, restart, retarget, pick,
    posOf: px,
    frame(now){ step(now); renderDash(); },
  };

  // A fizzle already clears the ink, but only rewound prog by half — so the
  // player was left with an empty canvas and credit for a path they could no
  // longer see, the guide resuming from the middle of a glyph while the toast
  // said "back to the dot". Under a clock there is no time to work out where
  // that middle is. The attempt now restarts, which is what the message always
  // claimed and what the cleared ink already implied.
  const _fizzle = window.fizzle;
  window.fizzle = function(){
    const r = _fizzle.apply(this, arguments);
    if (CFG.fizzleRestarts) setTimeout(() => {
      if (!done) { loading = true; try { _load(idx); } finally { loading = false; } }
    }, 260);
    return r;
  };

  // And an explicit way out, because auto-restart only fires on a fizzle and a
  // trace can go wrong long before it trips one.
  const redo = document.createElement('button');
  redo.textContent = '↺ redo';
  redo.title = 'Start this glyph again';
  redo.style.cssText = 'position:fixed;right:10px;bottom:10px;z-index:9999;'
    + 'background:#1d1a16;color:#e9c46a;border:1px solid #57492f;border-radius:7px;'
    + 'padding:9px 14px;font:13px ui-sans-serif,system-ui;cursor:pointer;opacity:.9';
  redo.onclick = () => { loading = true; try { _load(idx); } finally { loading = false; } };
  addEventListener('DOMContentLoaded', () => document.body.appendChild(redo));

  addEventListener('resize', sizeField);
  // and watched, for the same reason the stage is: a box that arrives late
  // is not a window resize
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(() => {
    const r = wrap.getBoundingClientRect();
    if (Math.round(r.width) !== FW || Math.round(r.height) !== FH) sizeField();
  }).observe(wrap);
  addEventListener('DOMContentLoaded', () => { sizeField(); resize(); });
  sizeField();
  run = newRun();
  // what lasts is in force from the first run, not the second
  ward = wardMax(); sumi = own('inkwell') * CFG.inkwellStep;
  spawn(); retarget();
  // The title page is the game's start page now ("let's have the game begin
  // from the title page. The practice button can exist on title"): its Begin
  // and Practice open this file with ?go=medium or ?go=guided, and the run
  // starts at once. Without it, the start page as before (the ending's
  // "difficulty and the sign" still opens it).
  let go = null; try { go = new URLSearchParams(location.search).get('go'); } catch(_){}
  if (go && DIFF[go] && !DIFF[go].locked){ setDifficulty(go); try { sizeField(); resize(); } catch(_){} begin(); try { history.replaceState(null, '', location.pathname + location.hash); } catch(_){} }
  else openStart();
  requestAnimationFrame(fieldLoop);
})();
</script>
"""


def config(pack, deck=None):
    """The field's tuning, as a JS object literal written into the page.

    With a deck the roster is its words, flattened and deduplicated (a word
    printed on two pages is one monster), and the sign axis speaks for words.
    """
    import json
    f = pack.get("field") or {}
    js = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    deck_js = "null"
    if deck is not None:
        words, seen = [], set()
        for sec in deck["sections"]:
            for w in sec["words"]:
                if w["ja"] in seen:
                    continue
                seen.add(w["ja"])
                words.append({k: w[k] for k in ("ja", "romaji", "en")})
        deck_js = js({"deck": deck.get("deck", "words"), "words": words})
    sign = f.get("sign", "kana")
    if sign not in ("kana", "romaji", "gaijin"):
        raise SystemExit(f"field.sign must be kana, romaji or gaijin, not {sign!r}")
    reading = f.get("reading", "both")
    if reading not in ("romaji", "gaijin", "both", "off"):
        raise SystemExit(f"field.reading must be romaji, gaijin, both or off, not {reading!r}")
    return (
        "<script>window.__FIELD_CFG={"
        f"deck:{deck_js},"
        f"knockback:{float(f.get('knockback', 0.07))},"
        f"sign:{json.dumps(sign)},"
        f"mode:{json.dumps(pack.get('mode', 'medium'))},"
        f"credit:{json.dumps(pack.get('credit', ''), ensure_ascii=False)},"
        f"credits:{json.dumps(list(pack.get('credits', [])), ensure_ascii=False)},"
        f"realms:{json.dumps(list(pack.get('realms', [])), ensure_ascii=False)},"
        f"speed:{f.get('speed', 0.055)},"
        f"wardHp:{int(f.get('wardHp', 5))},"
        f"tower:{js({**{'rows': 2, 'rowWaves': 10, 'bossEvery': 10, 'bossHp': 2, 'bossBite': 1, 'speedStep': 0.03}, **(f.get('tower', f.get('stages')) or {})}) if f.get('tower', f.get('stages', True)) else 'null'},"
        f"tamaClean:{int(f.get('tamaClean', 2))},"
        f"tamaTrace:{int(f.get('tamaTrace', 1))},"
        f"tamaWaves:{int(f.get('tamaWaves', 3))},"
        f"inkwellStep:{int(f.get('inkwellStep', 6))},"
        f"lanternRamp:{float(f.get('lanternRamp', 1.6))},"
        f"lanternCost:{js({**{'heart': 20, 'lamp': 30, 'inkwell': 15, 'vessel': 25}, **(f.get('lanternCost') or {})})},"
        f"hpEvery:{int(f.get('hpEvery', 10))},"
        f"biteRate:{float(f.get('biteRate', 0.5))},"
        f"noRepeat:{int(f.get('noRepeat', 4))},"
        f"hpMax:{int(f.get('hpMax', 5))},"
        f"biteEvery:{int(f.get('biteEvery', 20))},"
        f"biteMax:{int(f.get('biteMax', 4))},"
        f"tendEvery:{int(f.get('tendEvery', 10))},"
        f"riseStep:{float(f.get('riseStep', 0.2))},"
        f"inkTrace:{int(f.get('inkTrace', 2))},"
        f"inkClean:{int(f.get('inkClean', 2))},"
        f"inkKill:{int(f.get('inkKill', 1))},"
        f"inkMastered:{int(f.get('inkMastered', 6))},"
        f"shoveStep:{float(f.get('shoveStep', 0.025))},"
        f"upgradeRamp:{float(f.get('upgradeRamp', 1.6))},"
        f"upgradeCost:{js({**{'intent': 12, 'quick': 8, 'breath': 9, 'shove': 6, 'mend': 10, 'wall': 10, 'tend': 9, 'dilig': 8, 'harvest': 7, 'rise': 14}, **(f.get('upgradeCost') or {})})},"
        f"spawnMs:{int(f.get('spawnMs', 5200))},"
        f"spawnRamp:{int(f.get('spawnRamp', 140))},"
        f"spawnMin:{int(f.get('spawnMin', 1800))},"
        f"advanceMs:{int(f.get('advanceMs', 460))},"
        f"reading:{json.dumps(reading)},"
        f"fizzleRestarts:{'true' if f.get('fizzleRestarts', True) else 'false'},"
        f"hitodamaGain:{int(f.get('hitodamaGain', 1))},"
        f"cleanBonus:{int(f.get('cleanBonus', 1))},"
        f"hitodamaCap:{int(f.get('hitodamaCap', 6))},"
        f"castMs:{int(f.get('castMs', 900))},"
        f"rescue:{float(f.get('rescue', 0.3))},"
        f"energyMax:{int(f.get('energyMax', 24))},energyStart:{int(f.get('energyStart', 6))},"
        f"energyPerStroke:{int(f.get('energyPerStroke', 1))},castCost:{int(f.get('castCost', 2))},vesselStep:{int(f.get('vesselStep', 6))},"
        f"holdMs:{int(f.get('holdMs', 1500))},"
        f"tidyStrays:{'true' if f.get('tidyStrays', True) else 'false'}"
        "};</script>"
    )
