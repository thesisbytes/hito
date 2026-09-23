#!/usr/bin/env python3
"""The vocab shell: a flashcard above, the sketchbook below.

The hiragana realm teaches the shapes. A class quiz asks for something else:
"college; university" — write it. That is meaning → word → kana, and the
tracer only knows the last step. This shell supplies the first two. A card
shows the prompt (the English by default), a strip of blank slots the length
of the word, and the sketchbook loads the word's kana one at a time. Finish
a kana and its slot lights; finish the word and the reading and meaning
bloom together, which is where attention is highest.

A word is a sequence of glyphs, so no new stroke format is needed — this is
the "layout step" the economy plan always said words would be. The recall
test is honest only as far as the tracer lets it be: on easy the guide draws
the path and so reveals each kana's shape once the pen is down. What the
card measures instead is what happened *before* the pen touched: how long
the hand took to commit (card shown → first pen-down), and whether it
needed help first. The help is graded the way the maintainer described
their own recall — "if I see the first hiragana I'll get most words" — so
the hint is the first kana, the next one is the whole word, and after an
unhinted word the card asks which of the three it was: knew it, needed the
first kana, no idea. A hinted word grades itself. Words not known come
first next round, and slow ones sooner. Real free-recall waits on the
hard-mode scorer, like everything else.

Applied as an appended layer, the way the field is. It reaches the engine
only through globals it already exposes (load, conjure, LETTERS, idx), so
the tracer stays the single authority on what counts as a correct glyph.

Difficulty is the same runtime switch the field has — guided, easy, medium —
and the table below is a copy of the field's. Two copies of one table is a
drift risk and is noted in NOTES.md; folding them into one module means
rebuilding the game, which is a separate change.
"""

STYLE = """
<style>
  /* The workshop's furniture, hidden. The engine still maintains all of it. */
  body.vocab .tabs, body.vocab .count, body.vocab .meta, body.vocab .power,
  body.vocab .only-p, body.vocab .only-r, body.vocab #fontRow,
  body.vocab .grid, body.vocab .hint { display:none !important; }

  body.vocab { height:100dvh; overflow:hidden; justify-content:flex-start; }
  body.vocab header { padding:6px 0 2px; }
  body.vocab header .brand { cursor:pointer; }

  /* The card takes what is left after the sketchbook. The sketchbook MUST
     stay square: norm() divides x by W and y by H independently, so a
     rectangular stage makes the tolerance anisotropic. Same rule as the
     field, for the same reason. */
  body.vocab .stage{ flex:0 0 auto; aspect-ratio:1;
                     width:min(96vw,46dvh); height:min(96vw,46dvh);
                     margin:6px auto 10px; }

  .vcard{ width:min(96vw,560px); flex:1 1 auto; min-height:0; display:flex;
          flex-direction:column; justify-content:center; align-items:center;
          padding:6px 10px; text-align:center;
          font-family:ui-sans-serif,system-ui,"HT-KleeOne",sans-serif; }
  .vsec{ font-size:11px; letter-spacing:.14em; text-transform:uppercase;
         color:rgba(127,209,196,.8); display:flex; gap:14px; }
  .vsec span{ color:var(--ash); letter-spacing:.06em; text-transform:none;
              font-variant-numeric:tabular-nums; }
  .vprompt{ font-size:clamp(20px,4.6vw,30px); line-height:1.2; color:var(--gold);
            margin:8px 0 6px; text-shadow:0 0 18px rgba(233,196,106,.25); }
  .vprompt.kana{ font-family:"HT-KleeOne",ui-sans-serif,system-ui; font-size:clamp(28px,7vw,40px); }
  .vnote{ font-size:12px; color:var(--ash); min-height:16px; }
  .vstrip{ display:flex; gap:6px; flex-wrap:wrap; justify-content:center; margin:10px 0 6px;
           font-family:"HT-KleeOne",ui-sans-serif,system-ui; }
  .vstrip .slot{ width:clamp(30px,7.5vw,44px); height:clamp(36px,9vw,52px);
    display:flex; align-items:center; justify-content:center;
    font-size:clamp(20px,5.2vw,30px); border-radius:9px;
    border:1px solid rgba(233,196,106,.16); color:rgba(240,227,196,.35); }
  .vstrip .slot.done{ color:var(--gold-hot); border-color:rgba(233,196,106,.5);
    text-shadow:0 0 12px rgba(233,196,106,.8); }
  .vstrip .slot.cur{ border-color:var(--teal); color:#bdf0e6;
    box-shadow:0 0 0 1px rgba(127,209,196,.5), 0 0 18px rgba(127,209,196,.2); }
  .vstrip .slot.cur.blank{ color:rgba(127,209,196,.55); }
  .vstrip .slot.shown{ color:rgba(240,227,196,.8); }
  .vhint{ font-size:15px; color:var(--paper); min-height:20px; opacity:.9; }
  .vhint b{ color:var(--gold-hot); font-weight:600; }
  .vrow{ display:flex; gap:8px; margin-top:8px; width:min(94vw,420px); }
  .vrow button{ padding:9px 8px; font-size:13px; min-width:0; }
  .vrow button.teal{ color:var(--teal); border-color:rgba(127,209,196,.4); }
  .vrow button[hidden]{ display:none; }
  .vcard.bloom .vstrip .slot{ color:var(--gold-hot); border-color:rgba(233,196,106,.5);
    text-shadow:0 0 12px rgba(233,196,106,.8); }
  .vrow.grade button{ flex:1; padding:11px 6px; font-size:13px; line-height:1.25; }
  .vrow.grade button.g2{ color:var(--gold-hot); border-color:rgba(233,196,106,.5); }
  .vrow.grade button.g1{ color:var(--teal); border-color:rgba(127,209,196,.4); }
  .vrow.grade button.g0{ color:#e8a0a0; border-color:rgba(232,160,160,.4); }
  .vtime{ font-size:13px; color:var(--ash); min-height:18px; font-variant-numeric:tabular-nums; }
  .vtime b{ color:var(--paper); font-weight:600; }
  .vsummary{ font-size:15px; line-height:1.7; color:var(--paper); }
  .vsummary b{ color:var(--gold); font-size:22px; }
  .vsummary small{ display:block; font-size:13px; color:var(--ash); line-height:1.5; }
  .vwords{ display:flex; flex-wrap:wrap; gap:5px; justify-content:center; margin:8px 0 4px;
           max-height:22dvh; overflow:auto; width:min(94vw,520px); }
  .vwords span{ font-family:"HT-KleeOne",ui-sans-serif,system-ui; font-size:14px; padding:3px 8px;
                border-radius:7px; border:1px solid rgba(240,227,196,.16); color:rgba(240,227,196,.8);
                font-variant-numeric:tabular-nums; }
  .vwords span small{ font-family:ui-sans-serif,system-ui; color:var(--ash); margin-left:5px; }
  .vwords span.g2{ border-color:rgba(233,196,106,.45); color:var(--gold-hot); }
  .vwords span.g1{ border-color:rgba(127,209,196,.45); color:#bdf0e6; }
  .vwords span.g0{ border-color:rgba(232,160,160,.45); color:#e8a0a0; }

  /* The start page, same sheet as the field's. */
  .start{ position:fixed; inset:0; z-index:9998; display:flex; align-items:center;
          justify-content:center; padding:18px;
          background:radial-gradient(60% 50% at 50% 40%,rgba(90,160,150,.10),transparent 70%),
                     rgba(12,10,8,.94); }
  .start[hidden]{ display:none; }
  .start-card{ width:min(94vw,540px); max-height:94dvh; overflow:auto;
               font:14px ui-sans-serif,system-ui; color:#e8e0cc; }
  .start-title{ font-size:34px; font-weight:700; color:#e9c46a; letter-spacing:.02em;
                text-shadow:0 0 24px rgba(233,196,106,.35); }
  .start-title span{ font-size:40px; margin-left:8px; }
  .start-sub{ color:rgba(232,224,204,.55); margin:2px 0 14px; font-size:12px; }
  .start-h{ font-size:11px; letter-spacing:.14em; text-transform:uppercase;
            color:rgba(127,209,196,.8); margin:14px 0 8px; }
  .start-row{ display:grid; grid-template-columns:repeat(auto-fit,minmax(110px,1fr)); gap:8px; }
  .start-row.secs{ grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); }
  .start-row button, .start-row a{ display:block; text-decoration:none; text-align:left; background:#1d1a16; color:#e8e0cc; border:1px solid #57492f;
                     border-radius:10px; padding:10px 12px; cursor:pointer; font:inherit; min-height:64px; }
  .start-row a{ min-height:0; }
  .start-row button b, .start-row a b{ display:block; font-size:15px; color:#e9c46a; margin-bottom:3px; }
  .start-row button b i{ font-style:normal; color:#bdf0e6; margin-right:6px; }
  .start-row button small, .start-row a small{ display:block; color:rgba(232,224,204,.7); line-height:1.35; }
  .start-row button[aria-pressed="true"]{ border-color:#7fd1c4; background:#172422;
                     box-shadow:0 0 0 1px rgba(127,209,196,.5), 0 0 22px rgba(127,209,196,.18); }
  .start-row button[disabled]{ opacity:.42; cursor:default; }
  .start-go{ width:100%; margin-top:20px; background:#e9c46a; color:#1d1a16; border:0;
             border-radius:12px; padding:14px; font:700 17px ui-sans-serif,system-ui; cursor:pointer;
             box-shadow:0 0 30px rgba(233,196,106,.25); }
  .start-go[disabled]{ opacity:.4; box-shadow:none; cursor:default; }
  .start-foot{ margin-top:12px; font-size:11px; color:rgba(232,224,204,.4); text-align:center; }
  .start-links{ display:flex; gap:8px; margin-top:10px; }
  .start-links button{ flex:1; background:transparent; color:rgba(233,196,106,.75); border:1px solid #3d3324;
                       border-radius:9px; padding:9px; font:13px ui-sans-serif,system-ui; cursor:pointer; }
  .start textarea{ display:block; width:100%; height:90px; margin-top:8px; }
  .credits p{ line-height:1.55; color:rgba(232,224,204,.85); margin:10px 0; }
  .credits p.lead{ font-size:15px; color:#e8e0cc; }
  .credits p.lead b{ color:#e9c46a; font-size:22px; margin-right:6px; }
  .credits p.small{ font-size:12px; color:rgba(232,224,204,.6); }
</style>
"""

LAYER = STYLE + r"""
<script>
/* ---- the vocab shell ------------------------------------------------------
   A word is a sequence of glyphs. The card above the sketchbook asks for the
   word; the sketchbook is pointed at its kana one at a time.              */
(function(){
  const CFG = window.__VOCAB_CFG;
  const DECK = CFG.deck;
  const $ = id => document.getElementById(id);
  const esc = t => String(t).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

  document.body.classList.add('vocab');

  // character → index in the engine's list, so a word can be walked
  const AT = {};
  LETTERS.forEach((L, i) => { AT[L[0]] = i; });

  // ---- the card, inserted above the sketchbook
  const card = document.createElement('div');
  card.className = 'vcard';
  const stageEl = $('stage');
  stageEl.parentNode.insertBefore(card, stageEl);

  // ---- difficulty, at runtime (a copy of the field's table — see the docstring)
  const BASE = { R_ON0, DRAIN, FIZZ, COVER_MIN, MAX_TRAVEL };
  const DIFF = {
    guided: { kana:'導', blurb:'follow the light. no ink, no zaps, one big size, and the kana are shown — practice.',
              R_ON0: BASE.R_ON0*1.5, DRAIN: 0, FIZZ: Infinity, size: SIZE_MAX,
              COVER_MIN: 0, MAX_TRAVEL: Infinity, dot: 1, ink:false, drag:true, reveal:true,
              guide:true, numbers:true, comet:false, shadow:'none', stray:'drop' },
    medium: { kana:'中', blurb:'the shape only, as wide as you may stray. where each stroke starts, and in what order, is on you.',
              R_ON0: BASE.R_ON0, DRAIN: BASE.DRAIN, FIZZ: BASE.FIZZ, size: null,
              COVER_MIN: BASE.COVER_MIN, MAX_TRAVEL: BASE.MAX_TRAVEL, dot: 1, ink:true, drag:false, reveal:false,
              guide:false, numbers:false, shadow:'strokes', stray:'restart' },
    hard:   { kana:'難', blurb:'nothing shown. the scribe has not written this page yet.',
              locked:true },
  };
  // What the card asks with. English is the quiz; romaji is the reading;
  // kana is copying, which is handwriting practice rather than vocabulary.
  const PROMPTS = {
    en:     { blurb:'"college; university" — the meaning. this is what the quiz asks.' },
    romaji: { blurb:'"daigaku" — the reading. spelling without the meaning.' },
    kana:   { blurb:'"だいがく" — copy it. handwriting, not recall.' },
  };
  const SKEY = 'hito-vocab-start';
  let difficulty = CFG.mode in DIFF && !DIFF[CFG.mode].locked ? CFG.mode : 'medium';
  let prompt = CFG.prompt in PROMPTS ? CFG.prompt : 'en';
  let chosen = new Set(DECK.sections.map(s => s.id));
  try {
    const s = JSON.parse(localStorage.getItem(SKEY) || '{}') || {};
    if (s.difficulty in DIFF && !DIFF[s.difficulty].locked) difficulty = s.difficulty;
    if (s.prompt in PROMPTS) prompt = s.prompt;
    if (Array.isArray(s.sections)){
      const ok = s.sections.filter(id => DECK.sections.some(x => x.id === id));
      if (ok.length) chosen = new Set(ok);
    }
  } catch(_){}
  function saveStart(){
    try { localStorage.setItem(SKEY, JSON.stringify({difficulty, prompt, sections:[...chosen]})); } catch(_){}
  }
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
  function setDifficulty(name){
    if (!applyDifficulty(name)) return false;
    if (word) reload();
    render();
    return true;
  }
  function setPrompt(v){ if (!(v in PROMPTS)) return false; prompt = v; saveStart(); render(); return true; }
  function toggleSection(id){
    if (!DECK.sections.some(s => s.id === id)) return false;
    if (chosen.has(id)) chosen.delete(id); else chosen.add(id);
    saveStart();
    return true;
  }
  applyDifficulty(difficulty);

  // ---- the ledger: one entry per word, keyed by the word itself
  // n: times completed. clean: completed with no hint, no skip, no zap.
  // peek: times the hand needed help (first kana, whole word, or skip).
  // g: the last few grades, newest last — 2 knew it, 1 needed the first
  //    kana, 0 no idea. rt: the last few recall times in ms, card shown to
  //    first pen-down, kept only for words graded 2 (a hinted word was not
  //    recalled, so its time is not a recall time).
  const LKEY = 'hito-vocab', KEEP = 8;
  let LEDGER = {};
  try { LEDGER = JSON.parse(localStorage.getItem(LKEY) || '{}') || {}; } catch(_){ LEDGER = {}; }
  function saveLedger(){ try { localStorage.setItem(LKEY, JSON.stringify(LEDGER)); } catch(_){} }
  const entry = ja => LEDGER[ja] || { n:0, clean:0, peek:0, last:0, g:[], rt:[] };
  const median = a => { if (!a || !a.length) return null; const s = [...a].sort((x, y) => x - y);
                        return s.length % 2 ? s[(s.length-1)/2] : (s[s.length/2-1] + s[s.length/2]) / 2; };
  const known = e => !!(e && e.g && e.g.length && e.g[e.g.length-1] === 2);
  const recall = e => e && e.rt ? median(e.rt) : null;
  const secs = ms => ms == null ? '' : (ms/1000).toFixed(ms < 9950 ? 1 : 0) + ' s';
  const GRADE = { 2:'knew it', 1:'needed the first kana', 0:'no idea' };

  // ---- the queue: every chosen word once, the shaky ones first
  // Weight favours words never seen, words not known last time, and words
  // recalled slowly. A word is never left out of a round; the order is
  // what the ledger changes.
  function weight(w){
    const e = LEDGER[w.ja];
    if (!e || !e.n) return 2.5;
    let k = 1;
    if (e.g && e.g.length){
      const g = e.g.slice(-3);
      k += 2 - g.reduce((a, b) => a + b, 0) / g.length;        // 0 (all knew) .. 2 (all no idea)
    } else k += 2*(e.peek/(e.n + e.peek)) + (e.clean === 0 ? 0.8 : 0);   // a ledger from before grades
    const r = recall(e);
    if (r) k += Math.min(1, r / 8000);                           // eight seconds of thinking weighs like a miss
    return k;
  }
  function weightedShuffle(words){
    const pool = words.map(w => ({ w, k: weight(w) }));
    const out = [];
    while (pool.length){
      let total = 0; for (const p of pool) total += p.k;
      let r = Math.random()*total, i = 0;
      for (; i < pool.length - 1; i++){ r -= pool[i].k; if (r <= 0) break; }
      out.push(pool.splice(i, 1)[0].w);
    }
    return out;
  }
  // A word the book prints on two pages (p.59 repeats six from pp.39-40)
  // is in the deck twice, so a quiz on either page alone still asks it.
  // A round over both asks it once, from the first page it appears on.
  function selected(){
    const out = [], seen = new Set();
    for (const s of DECK.sections)
      if (chosen.has(s.id)) for (const w of s.words){
        if (seen.has(w.ja)) continue;
        seen.add(w.ja); out.push({ ...w, sec: s.title, secId: s.id });
      }
    return out;
  }

  // ---- state
  let queue = [], qi = -1, word = null, chars = [], ci = 0;
  let peek = 0, zapped = 0, skipped = false, wordAt = 0;
  let firstAct = null;   // ms from card shown to the first pen-down or hint tap
  let phase = 'start';   // start | word | bloom | summary
  let cmarkup = '';      // what the card shows, kept so a test can read it
  const newRound = () => ({ words:0, clean:0, peeked:0, skipped:0, knew:0, first:0, none:0, list:[] });
  let round = newRound();
  let timers = [];
  function later(fn, ms){ timers.push(setTimeout(fn, ms)); }
  function cancelTimers(){ for (const t of timers) clearTimeout(t); timers = []; }

  function startRound(){
    cancelTimers();
    queue = weightedShuffle(selected());
    qi = -1; round = newRound();
    nextWord();
  }
  function nextWord(){
    qi++;
    if (qi >= queue.length){ word = null; chars = []; phase = 'summary'; render(); return; }
    word = queue[qi]; chars = [...word.ja]; ci = 0;
    peek = 0; zapped = 0; skipped = false; wordAt = performance.now(); firstAct = null; graded = false;
    phase = 'word';
    render();
    loadChar();
  }
  const _load = window.load;
  let loading = false;
  // Reload what the card is asking for — not idx, which a stray conjure of
  // some other glyph could have left pointing elsewhere.
  function reload(){
    if (phase === 'word' && word) return loadChar();
    loading = true; try { _load(idx); } finally { loading = false; }
  }
  function loadChar(){
    const i = AT[chars[ci]];
    if (i === undefined){ toast(`no strokes for ${chars[ci]}`); return; }
    loading = true; try { _load(i); } finally { loading = false; }
  }
  // Every load the engine initiates on its own — conjure()'s delayed
  // load(idx+1), the arrow keys, the clear button — lands on the kana the
  // card is asking for. While the word blooms or the round is summarised,
  // there is nothing to ask for, and the engine's late advance is swallowed
  // rather than reloading a finished glyph out from under its celebration.
  window.load = function(i){
    if (loading) return _load.apply(this, arguments);
    if (phase === 'word' && word){
      // A finished kana is waiting on the shell's own advance. The engine's
      // 1.9s timer from an *earlier* kana can land in that wait when the
      // hand is quick, and redirecting it would reload the finished glyph
      // out from under its celebration. Nothing else needs a load while
      // that kana is done — the shell is about to do one. A stray glyph
      // that finished is a different matter: it comes back to the card.
      const t = AT[chars[ci]];
      if (done && idx === t) return;
      return _load.call(this, t === undefined ? i : t);
    }
    if (phase === 'bloom' || phase === 'summary') return;
    return _load.apply(this, arguments);
  };

  // ---- a finished kana lights its slot; a finished word blooms
  const _conjure = window.conjure;
  window.conjure = function(){
    const r = _conjure.apply(this, arguments);
    if (phase !== 'word' || !word) return r;
    const drew = LETTERS[idx][0];
    if (drew !== chars[ci]) return r;      // a stray conjure is not this word's
    later(() => {
      if (phase !== 'word') return;
      ci++;
      if (ci < chars.length){ render(); loadChar(); }
      else wordDone();
    }, CFG.advanceMs);
    return r;
  };
  // The word is written. A hinted word has graded itself — the first kana
  // is grade 1, the whole word grade 0 — and blooms for wordPauseMs. An
  // unhinted word blooms until the hand says which it was, because the
  // guide drew every shape once the pen was down and only the hand knows
  // whether it needed that.
  function wordDone(){
    phase = 'bloom';
    render();
    if (navigator.vibrate) navigator.vibrate([20,40,60]);
    if (peek >= 1){ grade(peek >= 2 ? 0 : 1); later(nextWord, CFG.wordPauseMs); }
  }
  let graded = false;
  function grade(g){
    if (phase !== 'bloom' || !word || graded) return false;
    g = Math.max(0, Math.min(2, g|0));
    if (peek >= 2 && g > 0) g = 0;            // the word was shown: nothing was recalled
    if (peek === 1 && g > 1) g = 1;           // the first kana was given
    graded = true;
    const e = entry(word.ja);
    const clean = !peek && !zapped && !skipped;
    e.n++; if (clean) e.clean++; if (peek) e.peek++; e.last = Date.now();
    e.g = (e.g || []).concat(g).slice(-KEEP);
    e.rt = e.rt || [];
    const think = firstAct == null ? null : Math.round(firstAct);
    if (g === 2 && think != null) e.rt = e.rt.concat(think).slice(-KEEP);
    LEDGER[word.ja] = e; saveLedger();
    round.words++; if (clean) round.clean++; if (peek) round.peeked++;
    round[['none', 'first', 'knew'][g]]++;
    round.list.push({ ja: word.ja, en: word.en, g, ms: think });
    try { window.__sync && window.__sync.record('word', {
      word: word.ja, deck: DECK.deck, section: word.secId, prompt, difficulty,
      peek, grade: g, zaps: zapped, thinkMs: think, ms: Math.round(performance.now() - wordAt),
    }); } catch(_){}
    render();
    return true;
  }
  function gradeAndGo(g){ if (grade(g)){ cancelTimers(); nextWord(); } }
  // The clock stops at the first thing the hand does: a pen-down on the
  // sketchbook, or a hint. Only the first counts; a redo does not restart it.
  function touched(){ if (phase === 'word' && word && firstAct == null) firstAct = performance.now() - wordAt; }
  // Help, and it counts. The first kana lights its slot; the whole word
  // fills every slot and shows the reading; skip gives up on the word,
  // which goes to the back of the queue once.
  function showFirst(){ if (phase !== 'word') return; touched(); peek = Math.max(peek, 1); render(); }
  function showKana(){ if (phase !== 'word') return; touched(); peek = 2; render(); }
  function skip(){
    if (phase !== 'word' || !word) return;
    touched();
    const e = entry(word.ja); e.peek++; e.last = Date.now();
    e.g = (e.g || []).concat(0).slice(-KEEP); e.rt = e.rt || [];
    LEDGER[word.ja] = e; saveLedger();
    round.skipped++;
    if (!word.requeued){ queue.push({ ...word, requeued:true }); }
    cancelTimers();
    nextWord();
  }

  // ---- ink and zaps, as the field does them
  const _zap = window.zap;
  window.zap = function(){
    if (DIFF[difficulty] && DIFF[difficulty].ink === false) return;
    zapped++; return _zap.apply(this, arguments);
  };
  const _redrawInk = window.redrawInk;
  window.redrawInk = function(){
    if (DIFF[difficulty] && DIFF[difficulty].ink === false){ ink.clearRect(0,0,W,H); return; }
    return _redrawInk.apply(this, arguments);
  };
  // Off-path runs are cut out of a finished stroke when the pen lifts.
  // Cosmetic: travel and coverage accumulate live in follow().
  function tidy(){
    if (!CFG.tidyStrays || mode !== 'practice' || !PATH.length || !strokes.length) return 0;
    if (DIFF[difficulty] && DIFF[difficulty].ink === false){ strokes.length = 0; return 0; }
    const s = strokes[strokes.length - 1];
    const keep = [], gone = [];
    let run = [];
    const flush = () => { if (run.length > 1) keep.push(run); run = []; };
    for (const q of s){ if (q.on) run.push(q); else { flush(); gone.push(q); } }
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
  const inkEl = $('ink');
  inkEl.addEventListener('pointerdown', () => touched());
  inkEl.addEventListener('pointerup', () => tidy());
  inkEl.addEventListener('pointercancel', () => tidy());
  const _fizzle = window.fizzle;
  window.fizzle = function(){
    const r = _fizzle.apply(this, arguments);
    if (CFG.fizzleRestarts) later(() => { if (!done && phase === 'word') reload(); }, 260);
    return r;
  };

  // ---- the card
  function slotText(i){
    const d = DIFF[difficulty] || {};
    const show = phase === 'bloom' || peek >= 2 || (peek >= 1 && i === 0) || prompt === 'kana' || d.reveal || i < ci;
    return show ? chars[i] : '＿';
  }
  function render(){
    if (phase === 'summary'){
      card.className = 'vcard';
      const rts = round.list.filter(x => x.g === 2 && x.ms != null).map(x => x.ms);
      const med = median(rts);
      const slow = rts.length ? Math.max(...rts) : null;
      const order = [...round.list].sort((a, b) => a.g - b.g || (b.ms || 0) - (a.ms || 0));
      const chips = order.map(x => `<span class="g${x.g}" title="${esc(x.en)} · ${GRADE[x.g]}">${esc(x.ja)}`
        + `<small>${x.g === 2 && x.ms != null ? secs(x.ms) : x.g === 1 ? '1st' : '✗'}</small></span>`).join('');
      card.innerHTML = cmarkup = `<div class="vsec">round done</div>
        <div class="vsummary"><b>${round.words}</b> words · <b>${round.knew}</b> knew ·
        <b>${round.first}</b> first kana · <b>${round.none}</b> no idea${round.skipped ? ` · <b>${round.skipped}</b> skipped` : ''}
        <small>${med != null ? `recalled in <b>${secs(med)}</b> typically, <b>${secs(slow)}</b> at the slowest` : 'nothing recalled unhinted this round'}</small></div>
        <div class="vwords">${chips}</div>
        <div class="vnote">the ones you did not know come first next time, and the slow ones sooner</div>
        <div class="vrow"><button class="primary" id="vAgain">again</button><button id="vMenu">menu</button></div>`;
      $('vAgain').onclick = startRound;
      $('vMenu').onclick = openStart;
      return;
    }
    if (!word){ card.className = 'vcard'; card.innerHTML = cmarkup = ''; return; }
    card.className = 'vcard' + (phase === 'bloom' ? ' bloom' : '');
    const p = prompt === 'romaji' ? word.romaji : prompt === 'kana' ? word.ja : word.en;
    const slots = chars.map((c, i) => {
      const cls = ['slot'];
      if (i < ci || phase === 'bloom') cls.push('done');
      else if (i === ci){ cls.push('cur'); if (slotText(i) === '＿') cls.push('blank'); }
      else if (slotText(i) !== '＿') cls.push('shown');
      return `<span class="${cls.join(' ')}">${esc(slotText(i))}</span>`;
    }).join('');
    let hint = '';
    if (phase === 'bloom') hint = `<b>${esc(word.romaji)}</b> · ${esc(word.en)}`;
    else if (peek >= 2 && prompt !== 'romaji') hint = `<b>${esc(word.romaji)}</b>`;
    // the clock: what the hand did first, and when
    let time = '';
    if (firstAct != null){
      const t = secs(firstAct);
      time = peek >= 2 ? `shown after <b>${t}</b>` : peek === 1 ? `first kana after <b>${t}</b>` : `pen down after <b>${t}</b>`;
    }
    // after the word: a hinted one has graded itself; an unhinted one asks
    let row;
    if (phase === 'bloom' && !graded)
      row = `<div class="vrow grade">
        <button class="g2" data-g="2">knew it</button>
        <button class="g1" data-g="1">needed the first kana</button>
        <button class="g0" data-g="0">no idea</button></div>`;
    else if (phase === 'bloom'){
      const g = round.list.length ? round.list[round.list.length-1].g : 0;
      row = `<div class="vrow grade"><button class="g${g}" disabled>${GRADE[g]}</button></div>`;
    } else
      row = `<div class="vrow">
        <button class="teal" id="vFirst"${peek >= 1 || prompt === 'kana' ? ' disabled' : ''}>first kana</button>
        <button class="teal" id="vKana"${peek >= 2 || prompt === 'kana' ? ' disabled' : ''}>show word</button>
        <button id="vSkip">skip ›</button>
      </div>`;
    card.innerHTML = cmarkup = `<div class="vsec">${esc(word.sec)}<span>${qi+1} / ${queue.length}</span></div>
      <div class="vprompt${prompt === 'kana' ? ' kana' : ''}">${esc(p)}</div>
      <div class="vnote">${esc(word.note || '')}</div>
      <div class="vstrip">${slots}</div>
      <div class="vhint">${hint}</div>
      <div class="vtime">${time}</div>
      ${row}`;
    if (phase === 'bloom'){
      for (const b of card.querySelectorAll('button[data-g]')) b.onclick = () => gradeAndGo(Number(b.dataset.g));
    } else {
      $('vFirst').onclick = showFirst;
      $('vKana').onclick = showKana;
      $('vSkip').onclick = skip;
    }
  }

  // ---- the start page
  const start = document.createElement('div');
  start.className = 'start'; start.id = 'start';
  let view = 'start', markup = '';
  function renderCredits(){
    const lines = (CFG.credits || []).map(l => `<p>${esc(l)}</p>`).join('');
    start.innerHTML = markup = `<div class="start-card credits">
      <div class="start-title">hito<span>人</span></div>
      <div class="start-sub">who this leans on</div>
      <p class="lead"><b>人</b>is two strokes, and neither can stand on its own. Take one away and the character falls.</p>
      <p>That is the project. One person records the strokes, another draws the letterforms, testers find the bugs, someone builds it, and every learner leans on all of them.</p>
      ${lines}
      <p class="small">${esc(CFG.credit || '')}</p>
      <p class="small">Single file, opens from a double-click, and needs no network to play. Your progress lives on this device — export it below to keep it.${window.__sync && window.__sync.enabled ? ' When there is a network, notes on how the tracing went are sent to the workshop under a made-up device name; ✋ hand, up top, turns that off.' : ''}</p>
      <div class="start-links"><button id="vExport">export progress</button><button id="vImport">import</button></div>
      <textarea id="vIO" spellcheck="false" hidden placeholder="Paste exported progress here, then tap import again."></textarea>
      <button class="start-go">back</button>
    </div>`;
    start.querySelector('.start-go').onclick = () => { view = 'start'; renderStart(); };
    $('vExport').onclick = exportProgress;
    $('vImport').onclick = importProgress;
  }
  function renderStart(){
    if (view === 'credits') return renderCredits();
    // Other realms, as links to sibling files. They are other single-file
    // builds beside this one — on Pages or in the same folder offline — so
    // the page is only a hop away and nothing here depends on it loading.
    const realms = () => !(CFG.realms || []).length ? '' :
      `<div class="start-h">other realms</div><div class="start-row">` +
      CFG.realms.map(r => `<a href="${esc(r.file)}"><b>${r.kana ? `<i>${esc(r.kana)}</i>` : ''}${esc(r.label)}</b><small>${esc(r.blurb || '')}</small></a>`).join('') +
      `</div>`;
    const row = (k, table, cur) => Object.entries(table).map(([n, d]) =>
      `<button data-k="${k}" data-v="${n}" aria-pressed="${n === cur}"${d.locked ? ' disabled' : ''}>`
      + `<b>${d.kana ? `<i>${d.kana}</i>` : ''}${n}</b><small>${d.blurb}</small></button>`).join('');
    const secs = DECK.sections.map(s => {
      const knew = s.words.filter(w => known(LEDGER[w.ja])).length;
      const med = median(s.words.map(w => recall(LEDGER[w.ja])).filter(x => x != null));
      return `<button data-k="sec" data-v="${esc(s.id)}" aria-pressed="${chosen.has(s.id)}">`
        + `<b>${esc(s.title)}</b><small>${s.words.length} words · ${knew} known${med != null ? ` · ${secs(med)}` : ''}</small></button>`;
    }).join('');
    const n = selected().length;
    start.innerHTML = markup = `<div class="start-card">
      <div class="start-title">hito<span>人</span></div>
      <div class="start-sub">${esc(DECK.deck)} · v${typeof APP_VERSION !== 'undefined' ? APP_VERSION : ''}</div>
      <div class="start-h">what to review</div>
      <div class="start-row secs">${secs}</div>
      <div class="start-h">how much help</div>
      <div class="start-row">${row('diff', DIFF, difficulty)}</div>
      <div class="start-h">what the card asks with</div>
      <div class="start-row">${row('prompt', PROMPTS, prompt)}</div>
      ${realms()}
      <button class="start-go"${n ? '' : ' disabled'}>${n ? `begin · ${n} words` : 'pick a section'}</button>
      <div class="start-links"><button class="start-credits">who this leans on · export</button></div>
      <div class="start-foot">read the card · write the word below, one kana at a time · peeking counts</div>
    </div>`;
    start.querySelector('.start-credits').onclick = () => { view = 'credits'; renderStart(); };
    for (const b of start.querySelectorAll('button[data-k]')){
      b.onclick = () => {
        if (b.dataset.k === 'diff') setDifficulty(b.dataset.v);
        else if (b.dataset.k === 'prompt') setPrompt(b.dataset.v);
        else toggleSection(b.dataset.v);
        renderStart();
      };
    }
    start.querySelector('.start-go').onclick = begin;
  }
  let redoShown = false;
  function showRedo(v){ redoShown = v; redo.hidden = !v; }
  function openStart(){ view = 'start'; renderStart(); start.hidden = false; showRedo(false); }
  function openCredits(){ view = 'credits'; renderStart(); start.hidden = false; showRedo(false); }
  function begin(){
    if (!selected().length) return false;
    start.hidden = true;
    showRedo(true);
    startRound();
    return true;
  }

  // ---- progress travels: nothing lives only in browser storage
  function exportProgress(){
    const o = { hito:'vocab', deck: DECK.deck, exported: new Date().toISOString(),
                ledger: LEDGER, mastery: MASTERY };
    const txt = JSON.stringify(o);
    const ta = $('vIO'); if (ta){ ta.hidden = false; ta.value = txt; ta.select(); }
    try { navigator.clipboard && navigator.clipboard.writeText(txt); } catch(_){}
    try {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([txt], {type:'application/json'}));
      a.download = 'hito-vocab-progress.json'; a.click();
    } catch(_){}
    toast(`exported ${Object.keys(LEDGER).length} words`);
  }
  function importProgress(text){
    const ta = $('vIO');
    const src = typeof text === 'string' ? text : (ta ? ta.value : '');
    if (!src){ if (ta){ ta.hidden = false; ta.value = ''; ta.focus(); } return false; }
    try {
      const o = JSON.parse(src);
      if (!o || o.hito !== 'vocab' || typeof o.ledger !== 'object') throw 0;
      // merge, never replace: a count only ever goes up, and the grade and
      // recall history come from whichever side wrote last
      for (const ja in o.ledger){
        const a = entry(ja), b = o.ledger[ja] || {};
        // (a millisecond timestamp does not survive |0 — that dropped every
        // imported `last` to zero until the grade history depended on it)
        const bl = Number(b.last) || 0;
        const newer = bl > (Number(a.last) || 0) ? b : a;
        LEDGER[ja] = { n: Math.max(a.n, b.n|0), clean: Math.max(a.clean, b.clean|0),
                       peek: Math.max(a.peek, b.peek|0), last: Math.max(a.last, bl),
                       g: Array.isArray(newer.g) ? newer.g.slice(-KEEP) : [],
                       rt: Array.isArray(newer.rt) ? newer.rt.slice(-KEEP) : [] };
      }
      saveLedger();
      if (o.mastery) { for (const k in o.mastery) MASTERY[k] = Math.max(MASTERY[k]||0, o.mastery[k]|0); persistM(); }
      toast('imported ✓');
      if (view === 'credits') renderCredits();
      return true;
    } catch(_){ toast('that did not look like exported progress'); return false; }
  }

  // ---- the redo button, for a trace that goes wrong before it fizzles
  const redo = document.createElement('button');
  redo.textContent = '↺ redo';
  redo.title = 'Start this kana again';
  redo.style.cssText = 'position:fixed;right:10px;bottom:10px;z-index:9999;'
    + 'background:#1d1a16;color:#e9c46a;border:1px solid #57492f;border-radius:7px;'
    + 'padding:9px 14px;font:13px ui-sans-serif,system-ui;cursor:pointer;opacity:.9';
  redo.onclick = () => { if (phase === 'word') reload(); };
  redo.hidden = true;

  addEventListener('DOMContentLoaded', () => {
    document.body.appendChild(start);
    document.body.appendChild(redo);
    const brand = document.querySelector && document.querySelector('header .brand');
    if (brand){ brand.title = 'Sections, difficulty and the prompt'; brand.onclick = openStart; }
    resize();
  });

  // A handle, for the same reason the field has one: a loop that cannot be
  // inspected can only be tested by playing it.
  window.__vocab = {
    get deck(){ return DECK; },
    get queue(){ return queue; }, get qi(){ return qi; },
    get word(){ return word; }, get chars(){ return chars; }, get ci(){ return ci; },
    get phase(){ return phase; }, get peek(){ return peek; }, get zapped(){ return zapped; },
    get firstAct(){ return firstAct; }, get graded(){ return graded; },
    get round(){ return round; }, get ledger(){ return LEDGER; },
    get difficulty(){ return difficulty; }, get prompt(){ return prompt; },
    get sections(){ return [...chosen]; },
    get view(){ return view; }, get startHtml(){ return markup; }, get cardHtml(){ return cmarkup; },
    get redoShown(){ return redoShown; },
    base: BASE, at: AT,
    setDifficulty, setPrompt, toggleSection, begin, openStart, openCredits,
    startRound, nextWord, skip, showFirst, showKana, touched, grade: gradeAndGo, tidy,
    median, recall, known,
    exportProgress, importProgress,
    weight, selected,
    clearLedger(){ LEDGER = {}; saveLedger(); },
  };

  openStart();
})();
</script>
"""


def config(pack, deck):
    """The shell's tuning and the deck itself, written into the page."""
    import json
    v = pack.get("vocab") or {}
    prompt = v.get("prompt", "en")
    if prompt not in ("en", "romaji", "kana"):
        raise SystemExit(f"vocab.prompt must be en, romaji or kana, not {prompt!r}")
    slim = {
        "deck": deck.get("deck", "vocab"),
        "sections": [
            {"id": s["id"], "title": s["title"],
             "words": [{k: w[k] for k in ("ja", "romaji", "en", "note") if k in w}
                       for w in s["words"]]}
            for s in deck["sections"]
        ],
    }
    js = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return (
        "<script>window.__VOCAB_CFG={"
        f"deck:{js(slim)},"
        f"prompt:{json.dumps(prompt)},"
        f"mode:{json.dumps(pack.get('mode', 'medium'))},"
        f"credit:{json.dumps(pack.get('credit', ''), ensure_ascii=False)},"
        f"credits:{json.dumps(list(pack.get('credits', [])), ensure_ascii=False)},"
        f"realms:{json.dumps(list(pack.get('realms', [])), ensure_ascii=False)},"
        f"advanceMs:{int(v.get('advanceMs', 420))},"
        f"wordPauseMs:{int(v.get('wordPauseMs', 1200))},"
        f"fizzleRestarts:{'true' if v.get('fizzleRestarts', True) else 'false'},"
        f"tidyStrays:{'true' if v.get('tidyStrays', True) else 'false'}"
        "};</script>"
    )
