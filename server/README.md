# hito sync

A write-only endpoint for play observations, on Appwrite: one function
(`server/sync/`) in front of one table (`hito.events`). Deployed at
`https://hito-sync.sfo.appwrite.run`. The schema and the function's settings
are in `appwrite.config.json` at the repo root, so a fresh clone can see what
exists and `appwrite push` can recreate it.

This directory used to hold a Vercel function over MongoDB Atlas. It was never
deployed; git history has it. Appwrite replaced it because the project already
hosts there and it removed the one secret the old design needed — see below.

## The rule everything follows

A client sends **observations**, never **totals**.

`{"kind":"banish","body":{"glyph":"ぬ","ms":4200}}` is a thing that happened.
`{"score":9000}` is a claim, and a claim from a client is worth nothing —
anyone with devtools can send it. Totals get derived here, from events.

| feature | why it needs this |
|---|---|
| leaderboards | a board built on client-reported scores ranks whoever edited hardest |
| the idle economy | "I earned 400 while away" is unverifiable; elapsed time computed server-side is not |

## What is stored

One row per event in `hito.events`:

| column | |
|---|---|
| `$id` | sha256 of `device:eventId`, so a retried batch overwrites itself |
| `device` | the random per-browser id the outbox makes up. Not an account, not a name. |
| `kind` | `trace`, `banish`, `breach`, `kindle`, `cast`, `word`, `flag`, `attempt` |
| `at` | when the client says it happened |
| `glyph` | the character (or word) the row is about, so "every つ anyone drew" is an index lookup |
| `body` | the event, as JSON text |

The table has no permissions at all: nothing reads or writes it except the
function, through the key Appwrite mints for each execution (scopes
`rows.read`, `rows.write`). **There is no secret in this repo or in the
function's variables**, which is the improvement over a Mongo connection
string behind `0.0.0.0/0`.

A `trace` is the handwriting: see `scripts/PACK.md`, "The hand".

## Accounts

Google sign-in, through Appwrite's OAuth, from `build/account_layer.py`.
Optional in every sense: guest is the default and is the whole game.

- **Web platforms** registered on the project: `hito.appwrite.network`,
  `thesisbytes.github.io`, `nira-hito.tech`. A host that is not on that list
  cannot sign anyone in. `localhost` is always allowed.
- **`hito.saves`**: one row per player, id = the user id, `data` (the ledger
  and mastery, as JSON) and `devices` (the device ids that have signed in as
  them, which is what will let the events table be read per player later).
  Row security is on, the table only lets signed-in users create, and each
  row is created readable, writable and deletable by `user:<id>` alone. A
  stranger asking for a row gets 404 and an empty list.
- The Google client ID was saved in the console with `https://` in front of
  it, and Google answers that with `Error 401: invalid_client`. Fixed
  2026-09-20. If sign-in ever dies at Google's page, look there first:
  `appwrite project get-o-auth-2-provider --provider-id google`.
- To test everything after Google without Google: `appwrite users create`,
  then `appwrite users create-token --show-secrets`, and open a build at
  `?userId=…&secret=…` — that is exactly what the provider's redirect carries.

## Merge rules, decided now

| data | rule | why |
|---|---|---|
| telemetry and traces | append-only, dedupe by `$id` | events are facts; two devices never disagree about one |
| mastery | `max()` per glyph | a counter that only rises is conflict-free, so a device offline for a week merges without asking anyone |
| economy | server-authoritative | the client never asserts a balance; the server holds `lastTick` and computes forward |

## What the endpoint refuses

Public URL, treated as one: request and per-event size caps, a fixed set of
kinds, event-id and device-id shape checks, timestamps more than a week from
now, and a per-device rate limit counted **in the table** rather than in
memory — executions do not share memory, so an in-process counter would be
theatre.

**Refusal is per event.** A refused event is dropped and the rest of the batch
is stored. Every id comes back in `accepted` either way, because the outbox
drops what is accepted and a permanently invalid event must not block the
queue behind it; the reasons come back in `refused`. Only genuinely retryable
failures (`503`, `429`, network) leave events queued.

`build/test/server.test.mjs` checks all of that offline, and also that every
kind the client records is a kind the server keeps.

## Deploy

```
appwrite login
appwrite push function --function-id sync --activate --force
```

No install step and no dependencies: the function is three REST calls.
`appwrite push table` applies schema changes made in `appwrite.config.json`.

## Reading the data

```
appwrite tablesdb list-rows --database-id hito --table-id events \
  --filter kind=trace --filter glyph=つ --limit 100 --json
```

## Not built yet

Accounts and device linking, the mastery merge, the economy tick, and
leaderboards. Appwrite has auth, and it is deliberately not switched on here:
a device id asks nothing of the player, and the first thing that genuinely
needs an account is merging two devices. Until then an account would be a
login screen in front of a game that opens from a double-click.
