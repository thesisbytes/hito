// What the endpoint will and will not take. Pure, so it is tested offline
// (build/test/server.test.mjs) rather than by deploying and hoping.
//
// Judged per event, not per batch. The Mongo draft this replaces judged the
// batch: one event of a kind it had not heard of — and the client already sent
// three it had not, kindle, cast and word — answered 400 for all forty, and
// since a 400 acknowledges every id so that poison cannot block the queue,
// forty good observations went in the bin beside the one bad one.

export const MAX_BODY = 256 * 1024;   // the whole request
export const MAX_EVENTS = 100;
export const MAX_EVENT = 12 * 1024;   // one event's body; a trace runs 1–3KB
export const WEEK = 7 * 24 * 3600 * 1000;

export const KINDS = new Set([
  'flag', 'attempt',                  // the workshop
  'banish', 'breach', 'kindle', 'cast', 'upgrade',   // the field
  'word',                             // the cards
  'trace',                            // the hand itself
]);

export const isId = s => typeof s === 'string' && /^[a-z0-9-]{8,64}$/.test(s);
export const isDevice = s => typeof s === 'string' && /^d[0-9a-f]{16}$/.test(s);

// The envelope. A request that fails here has nothing in it worth keeping.
export function envelope(body) {
  if (!body || typeof body !== 'object') return 'body must be an object';
  if (!isDevice(body.device)) return 'bad device id';
  if (!Array.isArray(body.events)) return 'events must be an array';
  if (!body.events.length) return 'no events';
  if (body.events.length > MAX_EVENTS) return `too many events (max ${MAX_EVENTS})`;
  return null;
}

// One event. Returns why it is refused, or null.
export function refuse(e, now = Date.now()) {
  if (!e || typeof e !== 'object') return 'event must be an object';
  if (!isId(e.id)) return 'bad event id';
  if (!KINDS.has(e.kind)) return `unknown kind: ${String(e.kind).slice(0, 24)}`;
  if (typeof e.at !== 'string' || Number.isNaN(Date.parse(e.at))) return 'bad timestamp';
  // A client's clock is its own business, but an event claiming to be from
  // 2077 would poison any time-ordered read of the table.
  if (Math.abs(Date.parse(e.at) - now) > WEEK) return 'timestamp too far from now';
  if (e.body != null && (typeof e.body !== 'object' || Array.isArray(e.body))) return 'event body must be an object';
  if (JSON.stringify(e.body ?? {}).length > MAX_EVENT) return 'event body too large';
  return null;
}

// What the row is filed under, so "every つ anyone has drawn" is an index
// lookup and not a scan of JSON. A word's row is filed under the word.
export function glyphOf(e) {
  const b = e.body || {};
  const g = b.glyph ?? b.word;
  return typeof g === 'string' && g.length && g.length <= 32 ? g : null;
}
