/**
 * What the endpoint refuses, checked without deploying it.
 *
 * The rule being defended: a client sends observations, never totals. And the
 * one learned writing this version: refusal is per event. The draft before it
 * refused per batch, did not know three of the kinds the client was already
 * sending, and would have binned every batch that contained one.
 *
 *   node build/test/server.test.mjs
 */
import { readFileSync, readdirSync } from 'fs';
import { envelope, refuse, glyphOf, KINDS, MAX_EVENT } from '../../server/sync/src/validate.js';

let fail = 0;
const ok = (c, m) => { if (!c) { console.log(`  FAIL: ${m}`); fail++; } };
const now = Date.parse('2026-09-20T12:00:00Z');
const ev = (o = {}) => ({id:'mfx1abcd-0123abcd', kind:'trace', at:'2026-09-20T11:59:00Z', body:{glyph:'つ'}, ...o});

ok(envelope({device:'d0123456789abcdef', events:[ev()]}) === null, 'a well-formed request was refused');
ok(envelope({device:'d00000000000test1', events:[ev()]}), 'a device id that is not hex was accepted');
ok(envelope({device:'d0123456789abcdef', events:[]}), 'an empty batch was accepted');
ok(envelope({device:'d0123456789abcdef', events:Array(101).fill(ev())}), 'a batch of 101 was accepted');
ok(envelope(null) && envelope('x') && envelope({device:'d0123456789abcdef'}), 'a body with no events was accepted');

ok(refuse(ev(), now) === null, 'a good event was refused');
ok(refuse(ev({kind:'score', body:{score:9000}}), now), 'a client was allowed to assert a total');
ok(refuse(ev({at:'2077-01-01T00:00:00Z'}), now), 'an event from 2077 was accepted');
ok(refuse(ev({at:'soon'}), now), 'an unparseable timestamp was accepted');
ok(refuse(ev({id:'x'}), now) && refuse(ev({id:'../../etc'}), now), 'a bad event id was accepted');
ok(refuse(ev({body:[1,2,3]}), now) && refuse(ev({body:'hello'}), now), 'a body that is not an object was accepted');
ok(refuse(ev({body:{s:'x'.repeat(MAX_EVENT)}}), now), 'an oversized body was accepted');
ok(refuse(ev({body:undefined}), now) === null, 'an event with no body was refused');
ok(refuse(null, now) && refuse(7, now), 'a non-object event was accepted');

ok(glyphOf(ev()) === 'つ', 'a trace is not filed under its glyph');
ok(glyphOf(ev({kind:'word', body:{word:'コーヒー'}})) === 'コーヒー', 'a word is not filed under the word');
ok(glyphOf(ev({body:{glyph:'x'.repeat(40)}})) === null, 'a glyph too long for the column was passed through');
ok(glyphOf(ev({body:{glyph:{$ne:1}}})) === null, 'a non-string glyph was passed through');

// Every kind the client records has to be one the server keeps. This is the
// check that would have caught kindle, cast and word going nowhere.
const sent = new Set();
for (const f of readdirSync('build').filter(f => f.endsWith('.py')))
  for (const m of readFileSync(`build/${f}`, 'utf8').matchAll(/__sync\.record\('([a-z]+)'/g)) sent.add(m[1]);
ok(sent.size >= 5, `only found ${sent.size} recorded kinds in build/ — the scan is broken`);
for (const k of sent) ok(KINDS.has(k), `the client records '${k}' and the server would refuse it`);

if (fail) { console.log(`  ${fail} server check(s) failed`); process.exit(1); }
console.log(`  observations only, refusal is per event, and all ${sent.size} kinds the client records are kinds the server keeps`);
