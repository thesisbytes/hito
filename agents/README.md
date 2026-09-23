# hito 人 — the agents

A multi-agent layer over the game's observations. It reads what the tracer
recorded and says what it sees; it scores nothing, changes nothing in a build,
and never runs while anyone is playing. A build opens offline from a
double-click, and nothing here weakens that (see CLAUDE.md).

This is also a class project in multi-agent systems, so each piece maps to a
named idea: a **harness** (Strands' agent loop with the project's own
arithmetic as tools), **hooks** (a ledger of every call and a fence around
writes), **memory** (mem0, as a Strands memory store: injected before a call,
distilled after one), **System 1 / System 2** (Laya labels every trace in one
forward pass; the LLM is for the rows it is unsure about), and **context** (to
come; see the notes for 2026-09-23).

## Setup

```
python3 -m venv agents/.venv
agents/.venv/bin/pip install -e agents          # strands, and hito_agents on the path
```

Then one model provider. Keys go in `.env` at the repo root (or `agents/.env`),
which git ignores and the agents read themselves; the environment wins if both
are set:

| provider | set | notes |
|---|---|---|
| **Bedrock** (default when found) | `AWS_BEARER_TOKEN_BEDROCK`, `AWS_REGION` | a Bedrock API key from the console; `~/.aws` credentials work too. Anthropic models need access enabled once, per region. |
| **OpenRouter** (the class account) | `OPENROUTER_API_KEY` | through Strands' OpenAI-compatible provider; `HITO_LLM_BASE_URL` points it at any other gateway |

`HITO_LLM=bedrock|openrouter` forces one. Memory uses the same provider for
mem0's LLM, and Titan on Bedrock for embeddings; OpenRouter serves no
embeddings, so with it set `GEMINI_API_KEY` (`pip install -e "agents[gemini]"`).
`HITO_MEMORY=0` runs without memory; `HITO_MEMORY_USER` scopes it (default
`maintainer`; a device id scopes what was learned about one hand). `HITO_MODEL` overrides the model id
(`global.anthropic.claude-sonnet-4-6` on Bedrock, `anthropic/claude-sonnet-5`
on OpenRouter). `HITO_MAX_TOKENS` caps output (default 2000: a provider
reserves the whole window against a small balance otherwise).

## Run

```
agents/.venv/bin/python agents/pull.py                      # hito.events -> agents/data/events.jsonl
agents/.venv/bin/python -m hito_agents.analyst "which characters fizzle most?"
agents/.venv/bin/python -m hito_agents.system1              # Laya labels every trace -> agents/out/labels.jsonl
agents/.venv/bin/python -m unittest discover -s agents/test # offline; no key, no model needed
```

Laya (`pip install -e "agents[laya]"`) is a few hundred megabytes of model,
downloaded on first use from Hugging Face and run locally on the CPU. It
never ships in a build.

`pull.py` goes through the Appwrite CLI (`appwrite login` first) and is
read-only. Experiments run against the file on disk, so they can be re-run
offline and the live table only ever sees finished writes.

## Layout

```
agents/
  pull.py                 the table -> a file on disk, one row per line
  hito_agents/
    events.py             arithmetic over a pull: overview, per-character summary, consistency, hardest
    tools.py              what an agent may call: the numbers above, and one write under agents/out
    hooks.py              Ledger (every call, one line each) and Fence (no writes outside agents/out)
    model.py              Bedrock or OpenRouter, from the environment
    memory.py             mem0 as a Strands memory store; `python -m hito_agents.memory` lists everything remembered
    system1.py            geometry per trace, Laya's typed questions, the labels, and the check against the flags
    analyst.py            the first agent: reads the pull and answers questions
  test/test_agents.py     the wiring, offline: a scripted model plays the LLM's part
  data/                   the pull (ignored by git)
  out/                    reports and the ledger (ignored by git)
```

## Rules

- **Observations, never claims.** A trace is a fact about one hand. Nothing
  here ranks anyone, and nothing here will.
- **Geometry in a script, judgment in a model.** `events.py` and
  `system1.py` compute; Laya and the LLM judge what they computed. The
  numbers a report quotes come from code a test can check.
- **Calibration is a claim until checked.** Laya's labels are a hypothesis
  about the traces. The `flag` events are the only human verdicts, and
  `system1.agree()` is the comparison. No flags, no conclusions.
- **Agents write under `agents/out` and nowhere else.** The fence enforces
  it; a refused call goes back to the model as an error so it can say so.
- **Nothing lives only in the terminal.** The ledger is a file.
