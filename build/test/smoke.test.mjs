// Execute the engine's script in a stubbed DOM to catch runtime errors that
// a syntax check cannot see — the temporal dead zone bug was exactly this.
import { readFileSync } from 'fs';
const target = process.argv[2] || 'dist/hiragana-v0.1.6.html';
const html = readFileSync(target,'utf8');
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
let raf=[];
const ctx = new Proxy({}, { get:()=>function(){ return {data:new Uint8ClampedArray(4)}; }, set:()=>true });
const el = () => new Proxy({ style:{}, classList:{add(){},remove(){},contains:()=>false},
  getContext:()=>ctx, getBoundingClientRect:()=>({left:0,top:0,width:400,height:400}),
  querySelectorAll:()=>[], children:[], dataset:{},
  insertBefore(){}, removeChild(){} },
  { get(t,k){
      if (k in t) return t[k];
      if (k==='width'||k==='height'||k==='offsetWidth') return 400;
      if (k==='parentNode') return el();   // a node, so a layer can insert beside it
      if (typeof k==='symbol') return undefined;
      // unknown property: a DOM node is mostly methods, so hand back one
      return new Proxy(function(){ return el(); }, { get:()=>'' });
    }, set(){ return true; } });
globalThis.document = { getElementById:el, createElement:el, body:el(), addEventListener(){},
  documentElement:el(), fonts:{ready:Promise.resolve(), add(){}} };
globalThis.window = globalThis;
globalThis.addEventListener = ()=>{};
globalThis.setTimeout = (f)=>0;
globalThis.setInterval = ()=>0;
globalThis.clearTimeout = ()=>{};
globalThis.URL = { createObjectURL:()=>"" };
globalThis.Blob = class {};
globalThis.localStorage = { getItem:()=>null, setItem(){}, removeItem(){} };
globalThis.requestAnimationFrame = f => { raf.push(f); return raf.length; };
globalThis.performance = { now:()=>0 };
Object.defineProperty(globalThis,"navigator",{value:{vibrate(){}},configurable:true});
globalThis.FontFace = class { load(){ return Promise.resolve(this); } };
globalThis.atob = s => Buffer.from(s,'base64').toString('binary');
globalThis.matchMedia = () => ({matches:false, addEventListener(){}});
globalThis.devicePixelRatio = 1;
// One scope for every block, the way a browser shares the global lexical
// environment between classic scripts. Running them separately hides any
// dependency an appended layer has on the engine's top-level let/const —
// which is most of what a layer is for.

// A classic <script> puts its top-level function declarations on window; a
// new Function body does not. Appended layers wrap those globals (window.load,
// window.conjure), so without this bridge they wrap undefined and the rig
// fails on code that is correct in a browser.
function bridgeFor(src){
  const names = [...src.matchAll(/^function\s+([A-Za-z_$][\w$]*)/gm)].map(m => m[1]);
  return names.length
    ? `\n;${names.map(n => `try{window.${n}=${n};}catch(_){}`).join('')}\n`
    : '';
}
const source = blocks.map((b,i) => b + bridgeFor(b)).join('\n;\n');

let err=null;
try { new Function(source)(); } catch(e){ err=e; }
// drive one animation frame — where the dead-zone bug would have fired
try { for(let i=0;i<3 && raf.length;i++){ const f=raf.shift(); f(0); } } catch(e){ err=err||e; }
if (err) { console.log(`RUNTIME ERROR in ${target}: ${err.message}`); process.exit(1); }
console.log(`${target}: engine executes, animation frames run clean`);
