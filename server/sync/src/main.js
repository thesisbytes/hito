// The write endpoint. Public URL, so it is written as one.
//
// Everything a client sends is an OBSERVATION — "this happened here" — never
// an assertion of state. There is no path from this endpoint to "my score is
// 9000", because the moment a client can claim a total, the leaderboard means
// nothing and the idle economy is editable by anyone with devtools. Totals are
// derived server-side, from events, later.
//
// No dependencies on purpose: no install step, nothing to go stale, and the
// REST API is three calls. The key is the one Appwrite mints per execution
// (scopes: rows.read, rows.write), so there is no secret to keep or leak.

import { createHash } from 'node:crypto';
import { MAX_BODY, envelope, refuse, glyphOf } from './validate.js';

const DB = 'hito', TABLE = 'events';
const WINDOW_MS = 60_000;
const MAX_PER_WINDOW = 240;      // a fast player lands maybe 40 events a minute

const CORS = {
  'access-control-allow-origin': '*',
  'access-control-allow-headers': 'content-type',
  'access-control-allow-methods': 'POST, OPTIONS',
  'access-control-max-age': '86400',
};

// Idempotent: the same device and event id always land on the same row, so a
// batch retried after a dropped response overwrites itself instead of
// doubling. Hashed because a row id is 36 characters and these two are 35
// today, which is one client change away from not fitting.
const rowId = (device, id) =>
  createHash('sha256').update(`${device}:${id}`).digest('hex').slice(0, 36);

export default async ({ req, res, error }) => {
  const reply = (status, body) => res.json(body, status, CORS);
  if (req.method === 'OPTIONS') return res.text('', 204, CORS);
  if (req.method !== 'POST') return reply(405, { error: 'POST only' });

  const raw = req.bodyText ?? '';
  if (raw.length > MAX_BODY) return reply(413, { error: 'body too large' });
  let body;
  try { body = JSON.parse(raw); } catch { return reply(400, { error: 'bad json', accepted: [] }); }

  // 400 and not 429/500: a malformed request will never become well-formed,
  // so the client must drop it rather than retry it forever. The outbox treats
  // an accepted id as done, which is what stops poison blocking a queue.
  const bad = envelope(body);
  if (bad) return reply(400, { error: bad, accepted: (Array.isArray(body?.events) ? body.events : []).map(e => e?.id) });

  const api = process.env.APPWRITE_FUNCTION_API_ENDPOINT;
  const headers = {
    'content-type': 'application/json',
    'x-appwrite-project': process.env.APPWRITE_FUNCTION_PROJECT_ID,
    'x-appwrite-key': req.headers['x-appwrite-key'] ?? '',
  };
  const rowsUrl = `${api}/tablesdb/${DB}/tables/${TABLE}/rows`;

  const now = Date.now();
  const refused = {}, rows = [];
  for (const e of body.events) {
    const why = refuse(e, now);
    if (why) { refused[e?.id ?? '?'] = why; continue; }
    rows.push({
      $id: rowId(body.device, e.id),
      device: body.device,
      kind: e.kind,
      at: new Date(e.at).toISOString(),
      glyph: glyphOf(e),
      body: JSON.stringify(e.body ?? {}),
    });
  }
  // Refused events are acknowledged with the rest: they are as done as they
  // will ever be. The reasons go back so a debug build can say what it lost.
  const accepted = body.events.map(e => e?.id);
  if (!rows.length) return reply(200, { ok: true, accepted, stored: 0, refused });

  try {
    // Rate limit per device, counted in the table rather than in memory:
    // executions do not share memory, so an in-process counter is theatre.
    const q = [
      { method: 'equal', attribute: 'device', values: [body.device] },
      { method: 'greaterThan', attribute: '$createdAt', values: [new Date(now - WINDOW_MS).toISOString()] },
      { method: 'limit', values: [1] },
    ].map(o => 'queries[]=' + encodeURIComponent(JSON.stringify(o))).join('&');
    const seen = await fetch(`${rowsUrl}?${q}`, { headers });
    if (!seen.ok) throw new Error(`count ${seen.status}: ${(await seen.text()).slice(0, 200)}`);
    if ((await seen.json()).total > MAX_PER_WINDOW) return reply(429, { error: 'slow down' });

    const put = await fetch(rowsUrl, { method: 'PUT', headers, body: JSON.stringify({ rows }) });
    if (!put.ok) throw new Error(`upsert ${put.status}: ${(await put.text()).slice(0, 200)}`);
    return reply(200, { ok: true, accepted, stored: rows.length, refused });
  } catch (err) {
    // Retryable: the client keeps the events and tries again with backoff.
    error(String(err?.message ?? err));
    return reply(503, { error: 'store unavailable' });
  }
};
