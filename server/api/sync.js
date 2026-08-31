// The write endpoint. Public URL, so it is written as one.
//
// Everything a client sends is an OBSERVATION — "this happened here" — never
// an assertion of state. There is no path from this endpoint to "my score is
// 9000", because the moment a client can claim a total, the leaderboard means
// nothing and the idle economy is editable by anyone with devtools. Totals are
// derived server-side, from events, later.
//
// Env: MONGODB_URI, and optionally SYNC_DB (default "hito").

import { MongoClient } from 'mongodb';

const MAX_BODY = 256 * 1024;     // a batch of 40 events is ~8KB; this is slack
const MAX_EVENTS = 100;
const KINDS = new Set(['flag', 'banish', 'breach', 'attempt']);
const WINDOW_MS = 60_000;
const MAX_PER_WINDOW = 240;      // a fast player banishes maybe 20/min

// Serverless reuses the process between invocations; a client per invocation
// exhausts the connection pool under any real load.
let clientPromise = null;
function db() {
  if (!clientPromise) {
    const uri = process.env.MONGODB_URI;
    if (!uri) throw new Error('MONGODB_URI is not set');
    clientPromise = new MongoClient(uri, { maxPoolSize: 4 }).connect();
  }
  return clientPromise.then(c => c.db(process.env.SYNC_DB || 'hito'));
}

const isId = s => typeof s === 'string' && /^[a-z0-9-]{8,64}$/.test(s);
const isDevice = s => typeof s === 'string' && /^d[0-9a-f]{16}$/.test(s);

function validate(body) {
  if (!body || typeof body !== 'object') return 'body must be an object';
  if (!isDevice(body.device)) return 'bad device id';
  if (!Array.isArray(body.events)) return 'events must be an array';
  if (!body.events.length) return 'no events';
  if (body.events.length > MAX_EVENTS) return `too many events (max ${MAX_EVENTS})`;
  for (const e of body.events) {
    if (!e || typeof e !== 'object') return 'event must be an object';
    if (!isId(e.id)) return `bad event id: ${JSON.stringify(e.id)}`;
    if (!KINDS.has(e.kind)) return `unknown kind: ${JSON.stringify(e.kind)}`;
    if (typeof e.at !== 'string' || Number.isNaN(Date.parse(e.at))) return 'bad timestamp';
    if (e.body && typeof e.body !== 'object') return 'event body must be an object';
    // A client's clock is its own business, but an event claiming to be from
    // 2077 would poison any time-ordered read of this collection.
    const skew = Math.abs(Date.parse(e.at) - Date.now());
    if (skew > 7 * 24 * 3600 * 1000) return 'timestamp too far from now';
  }
  return null;
}

export default async function handler(req, res) {
  res.setHeader('access-control-allow-origin', '*');
  res.setHeader('access-control-allow-headers', 'content-type');
  res.setHeader('access-control-allow-methods', 'POST, OPTIONS');
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({error: 'POST only'});

  const raw = typeof req.body === 'string' ? req.body : JSON.stringify(req.body ?? '');
  if (raw.length > MAX_BODY) return res.status(413).json({error: 'body too large'});

  let body;
  try { body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body; }
  catch { return res.status(400).json({error: 'bad json'}); }

  const bad = validate(body);
  // 400 and not 429/500: a malformed event will never become well-formed, so
  // the client must drop it rather than retry it forever. The outbox treats an
  // accepted id as done, so this is what stops a poison event blocking a queue.
  if (bad) return res.status(400).json({error: bad, accepted: (body?.events || []).map(e => e?.id)});

  try {
    const d = await db();

    // Rate limit per device, in the database rather than in memory, because
    // serverless instances do not share memory and an in-process counter is
    // security theatre.
    const since = new Date(Date.now() - WINDOW_MS);
    const recent = await d.collection('events')
      .countDocuments({device: body.device, received: {$gte: since}}, {limit: MAX_PER_WINDOW + 1});
    if (recent > MAX_PER_WINDOW)
      return res.status(429).json({error: 'slow down'});

    const now = new Date();
    const docs = body.events.map(e => ({
      _id: `${body.device}:${e.id}`,      // idempotent: a retried batch is a no-op
      device: body.device,
      kind: e.kind,
      at: new Date(e.at),
      received: now,
      body: e.body ?? {},
    }));

    // Unordered so one duplicate does not abort the rest of the batch.
    try {
      await d.collection('events').insertMany(docs, {ordered: false});
    } catch (err) {
      // 11000 is a duplicate key, which means we already have it — success.
      const onlyDupes = err?.writeErrors?.every(w => w.err?.code === 11000)
        ?? err?.code === 11000;
      if (!onlyDupes) throw err;
    }

    return res.status(200).json({ok: true, accepted: body.events.map(e => e.id)});
  } catch (err) {
    // Retryable: the client keeps the events and tries again with backoff.
    return res.status(503).json({error: 'store unavailable'});
  }
}
