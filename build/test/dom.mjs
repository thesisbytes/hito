/**
 * A stubbed DOM that boots a build the way a browser would: every <script>
 * block in one scope, function declarations bridged onto window, and a
 * sketchbook that keeps its pointer listeners in order so a test can put a
 * pen down and have the engine, the hand and the shell hear it in turn.
 *
 * Shared by the tests that drive a pen (hand, stray). `heard` is the
 * listener table, for a test that needs to fire only some of them.
 */
import { readFileSync } from 'fs';

export function boot(file, { stored = {}, touchPoints = 0, fine = false, coarse = false, screen = {width:1280, height:800} } = {}){
  const html = readFileSync(file, 'utf8');
  const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
  let T = 0;
  const store = {...stored};
  const ctx = new Proxy({}, { get: () => function(){ return {data:new Uint8ClampedArray(4)}; }, set: () => true });
  const el = () => new Proxy({ style:{}, classList:{add(){},remove(){},contains:()=>false},
    getContext:()=>ctx, getBoundingClientRect:()=>({left:0,top:0,width:400,height:400}),
    querySelectorAll:()=>[], children:[], dataset:{}, insertBefore(){}, removeChild(){},
    append(){}, appendChild(){}, addEventListener(){}, setAttribute(){} },
    { get(t,k){
        if (k in t) return t[k];
        if (k==='width'||k==='height'||k==='offsetWidth') return 400;
        if (k==='parentNode') return el();
        if (typeof k==='symbol') return undefined;
        return new Proxy(function(){ return el(); }, { get:()=>'' });
      }, set(t,k,v){ t[k]=v; return true; } });
  const g = globalThis;
  // The sketchbook keeps its listeners, in the order they were added, so a
  // test can put a pen down on it and have the engine, the hand and the shell
  // each hear about it in turn — which is the only way to test what one of
  // them does to the ink before the next one looks.
  const heard = {};
  const inkEl = el(); inkEl.addEventListener = (ev, f) => { (heard[ev] = heard[ev] || []).push(f); };
  const fire = (type, x, y, pt = 'touch', id = 1) => {
    const e = { type, pointerId:id, pointerType:pt, clientX:x, clientY:y, buttons:1, pressure:.5, preventDefault(){}, getCoalescedEvents(){ return [e]; } };
    for (const f of heard[type] || []) f(e);
  };
  g.document = { getElementById: id => id === 'ink' ? inkEl : el(), createElement:el, body:el(), addEventListener(){},
    documentElement:el(), fonts:{ready:Promise.resolve(), add(){}} };
  g.window = g;
  g.addEventListener = () => {};
  g.setTimeout = () => 0; g.setInterval = () => 0; g.clearTimeout = () => {};
  g.URL = { createObjectURL:()=>"" }; g.Blob = class {};
  g.localStorage = { getItem:k => (k in store ? store[k] : null), setItem:(k,v) => { store[k] = String(v); }, removeItem:k => { delete store[k]; } };
  g.requestAnimationFrame = () => 0;
  g.performance = { now:()=>T };
  Object.defineProperty(g, 'navigator', {value:{vibrate(){}, maxTouchPoints:touchPoints, onLine:false}, configurable:true});
  g.screen = screen;
  g.FontFace = class { load(){ return Promise.resolve(this); } };
  g.atob = s => Buffer.from(s,'base64').toString('binary');
  g.matchMedia = q => ({matches: q.includes('fine') ? fine : q.includes('coarse') ? coarse : false, addEventListener(){}});
  g.devicePixelRatio = 1;
  g.fetch = () => Promise.reject(new Error('the test is offline'));
  for (const k of ['__hand','__sync','__field','__vocab','__probe']) delete g[k];

  const bridgeFor = src => {
    const names = [...src.matchAll(/^function\s+([A-Za-z_$][\w$]*)/gm)].map(m => m[1]);
    return names.length ? `\n;${names.map(n => `try{window.${n}=${n};}catch(_){}`).join('')}\n` : '';
  };
  const probe = `\nwindow.__probe = { get penOnly(){ return penOnly; }, get done(){ return done; }, get idx(){ return idx; },
    get LETTERS(){ return LETTERS; }, get strokes(){ return strokes; }, get BASE_F(){ return BASE_F; },
    get ease(){ return HAND_EASE; }, get SIZE_MAX(){ return SIZE_MAX; }, get SIZE_MIN(){ return SIZE_MIN; },
    get TEACHER(){ return TEACHER; }, setStrokes(v){ strokes = v; }, setSize(f){ curF = f; curS = f/BASE_F; }, get W(){ return W; }, get H(){ return H; },
    get prog(){ return prog; }, get segIdx(){ return segIdx; }, get awaitLift(){ return awaitLift; }, get PATH(){ return PATH; },
    get SEGS(){ return SEGS; }, denorm(p){ return denorm(p); }, get stray(){ return STRAY_MODE; }, set stray(v){ STRAY_MODE = v; },
    get strayed(){ return strayed; }, get R(){ return R_ON(); }, get SEGLEN(){ return SEGLEN; }, get DRAG(){ return DRAG_FOLLOW; },
    get moving(){ return moving; }, get mv(){ return [mvx, mvy]; }, get lastN(){ return lastN; } };`;
  new Function(blocks.map(b => b + bridgeFor(b)).join('\n;\n') + probe)();
  g.resize();
  if (g.__field) g.__field.begin();
  return { H: g.__hand, P: g.__probe, S: g.__sync, store, g, fire, heard, tick: ms => { T += ms; } };
}
