# hito sync

A write-only endpoint for play observations. Not deployed — this is the code
and the steps; the credentials are yours and do not belong in this repo.

## Why there is a server at all

MongoDB's Atlas Data API and HTTPS Endpoints reached end-of-life on
**30 September 2025**, along with App Services auth, Device Sync and GraphQL.
A static page can no longer reach Atlas directly, so a small function has to
hold the connection string. That is the whole reason this directory exists.

## The rule everything follows

A client sends **observations**, never **totals**.

`{"kind":"banish","body":{"glyph":"ぬ","ms":4200}}` is a thing that happened.
`{"score":9000}` is a claim, and a claim from a client is worth nothing —
anyone with devtools can send it. Totals get derived here, from events.

That is not caution for its own sake. It is what makes the two unbuilt
features possible later:

| feature | why it needs this |
|---|---|
| leaderboards | a board built on client-reported scores ranks whoever edited hardest |
| the idle economy | "I earned 400 while away" is unverifiable; elapsed time computed server-side is not |

## Merge rules, decided now

Writing these down before the code exists, because each field wants different
treatment and getting it wrong is discovered late:

| data | rule | why |
|---|---|---|
| telemetry (`flag`, `banish`, `breach`) | append-only, dedupe by `_id` | events are facts; two devices never disagree about one |
| mastery | `max()` per glyph | a counter that only rises is conflict-free, so a device offline for a week merges without asking anyone |
| economy | server-authoritative | the client never asserts a balance; the server holds `lastTick` and computes forward |

Mastery is the interesting one: because `max()` merges cleanly, the client can
keep owning it and stay fully playable offline. That is not true of the
economy, which is why the economy is last.

## Deploy

1. **Atlas**: create a free **M0** cluster. It is free forever and will hold
   far more than this project can generate — the $50 of credits are not what
   makes this work, and picking a paid tier to spend them would be backwards.
2. **Database user**: one user, `readWrite` on the `hito` database only.
3. **Network access**: serverless functions have no stable egress IP on a free
   plan, so this needs `0.0.0.0/0`. That makes the database password the only
   thing standing between the internet and the data — generate a long random
   one and never commit it.
4. **Deploy** `server/` to Vercel (`vercel --prod` from this directory).
5. **Env var**: set `MONGODB_URI` in the Vercel project. Optionally `SYNC_DB`.
6. **Index**, once, in the Atlas shell — the rate limiter counts recent events
   per device on every request and is a collection scan without it:

   ```js
   db.events.createIndex({ device: 1, received: -1 })
   db.events.createIndex({ received: -1 })
   ```

7. Point a build at it: set `sync.endpoint` in `scripts/hiragana/game.json` to
   the deployed URL (`https://…/api/sync`) and rebuild. It must be `https` —
   `stitch.py` refuses anything else, because a mixed-content POST from the
   GitHub Pages page fails silently, which is the worst way for this to break.

## What the endpoint refuses

Public URL, treated as one: batch and body size caps, a fixed set of event
kinds, event-id and device-id shape checks, timestamps more than a week from
now, and a per-device rate limit counted **in the database** rather than in
process memory — serverless instances do not share memory, so an in-process
counter would be theatre.

Writes are idempotent: `_id` is `device:eventId`, so a retried batch is a
no-op rather than a duplicate.

Malformed events are answered `400` **with their ids in `accepted`**. That is
deliberate. The outbox drops whatever the server accepts, so a permanently
invalid event has to be acknowledged or it blocks the queue behind it forever.
Only genuinely retryable failures (`503`, network) leave events queued.

## Not built yet

Accounts and device linking, the mastery merge, the economy tick, and
leaderboards. The client half is done: `window.__sync.record(kind, body)`
queues offline and flushes when it can.
