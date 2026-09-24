"""Two agents that argue over the tower's pace, and a judge that is arithmetic.

The maintainer: "wouldn't it be cool to have an agent to buff and one agent
to nerf?" 仏 hotoke is the learner's advocate and wants the tower to be
climbed; 鬼 oni is the farang's advocate and wants it to bite. Each reads
the same pull of the events table, runs the same pace model, and proposes
changes to the same short list of tunables. Neither can write the game:
the verdict is a file under agents/out, and a human applies it.

The judge is `pace.py`, not a third model. It refuses anything outside the
bounds, takes each side's proposal only as far as the modelled wall stays
inside the target band, and prefers the smaller move when both would do.
An agent can be as persuasive as it likes; the wall is where the arithmetic
says it is.

    agents/.venv/bin/python -m hito_agents.balance            # argue, judge, write agents/out/balance-<date>.json
    agents/.venv/bin/python -m hito_agents.balance --apply agents/out/balance-<date>.json   # a human applies it
"""
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from strands import Agent, tool

from . import events, pace
from .hooks import OUT, Fence, Ledger

# The band the judge holds the predicted end in, for a bare hand with no
# lanterns. 100 is the next level: the hand and its lights should get near
# it, and the lanterns should be what gets a run past it. Below 55 and the
# chart's later rows are never seen; past 120 and nothing bites.
BAND = (55, 120)

_rows = None
_proposals = {}


def rows():
    global _rows
    if _rows is None:
        _rows = events.load()
    return _rows


def use(rows_):
    global _rows, _proposals
    _rows = rows_
    _proposals = {}


def runs():
    return [r["body"] for r in rows() if r.get("kind") == "run"]


@tool
def state_of_play() -> dict:
    """The runs in the pull and the measured hand: how many, how far they
    got (median, furthest), how long they lasted, seconds per trace, the
    clean rate, which upgrades were bought, and how the phones kept up
    (frames over 25 and 50 ms) where a run recorded it. Start here."""
    rs = runs()
    hand = pace.hand_of(rs)
    bought = {}
    for r in rs:
        for k, v in (r.get("upgrades") or {}).items():
            if v:
                bought[k] = bought.get(k, 0) + 1
    frames = [r["frames"] for r in rs if isinstance(r.get("frames"), dict) and r["frames"].get("n")]
    perf = None
    if frames:
        n = sum(f["n"] for f in frames)
        perf = {"runs": len(frames), "slow": round(sum(f.get("slow", 0) for f in frames) / n, 3), "jank": round(sum(f.get("jank", 0) for f in frames) / n, 3)}
    return {"runs": len(rs), "hand": hand, "upgrades_bought": bought, "frames": perf,
            "by_version": Counter(r.get("v") or "?" for r in rs).most_common(5)}


@tool
def current_config() -> dict:
    """The hiragana game's pace config as the build sees it, and which keys
    may be proposed (with their bounds)."""
    cfg = pace.current()
    return {"config": {k: cfg[k] for k in pace.TUNABLE if k in cfg}, "tower": cfg.get("tower"),
            "tunable": pace.TUNABLE, "tower_tunable": {"tower." + k: v for k, v in pace.TOWER_TUNABLE.items()}}


@tool
def pace_model(changes: dict = None) -> dict:
    """Where a run is predicted to end for the measured hand (and where the
    wall is: the first wave the farang need more hits a second than the hand
    and its lights supply) for the current config with these changes applied. Keys as current_config lists them ('tower.bossHp' for
    the tower's). Refused keys come back with a reason and are ignored."""
    cfg, refused = pace.with_changes(pace.current(), changes or {})
    m = pace.model(cfg, pace.hand_of(runs()))
    m["table"] = [row for row in m["table"] if row["wave"] in (0, 10, 30, 60, 100, 140, 200)]
    if refused:
        m["refused"] = refused
    return m


def proposer(side):
    @tool
    def propose(changes: dict, because: str) -> dict:
        """Your proposal: the changes (keys as current_config lists them) and
        one plain sentence of why, quoting the numbers you saw. Out-of-bounds
        or unknown keys are refused and the rest kept. Call it once; a second
        call replaces the first."""
        cfg, refused = pace.with_changes(pace.current(), changes or {})
        kept = {k: v for k, v in (changes or {}).items() if k not in refused}
        _proposals[side] = {"changes": kept, "because": because, "refused": refused,
                            "wall": pace.wall_of(cfg, pace.hand_of(runs())), "end": pace.end_of(cfg, pace.hand_of(runs()))}
        return _proposals[side]
    return propose


SYSTEM = """You are {kana} {name}, one of two advocates arguing over the pace of the tower in hito 人,
a script-tracing game: farang (monsters) carrying characters advance on a ward, the player traces a
character to hit the one carrying it, and a traced character stays lit and throws its own light at
later farang. Waves never end; a run ends when the ward falls, and the next level opens at wave 100.
{stance}
Rules:
- Call state_of_play, then current_config, then pace_model with your idea, then propose. Once each.
- Quote the numbers the tools gave you. Never invent one.
- Propose at most three changes, each with a reason from the data. The judge is arithmetic and will
  refuse anything outside the bounds or that moves the predicted end out of {band}; be precise, not loud.
- Two sentences at the end: what you proposed and why. The project's tone is affectionate and a bit silly."""

SIDES = {
    "hotoke": {"kana": "仏", "name": "hotoke, the learner's advocate",
               "stance": "You want the tower to be climbable: a learner tracing at the measured pace, with the lights they have kindled, should be able to reach the later rows of the chart and see wave 100. You loosen: slower spawns, gentler health and bite ramps, cheaper casts."},
    "oni":    {"kana": "鬼", "name": "oni, the farang's advocate",
               "stance": "You want the tower to bite: a run that never ends is not a tower, the record must be earned, and the lanterns must matter. You tighten: quicker spawns, sooner health and bite, dearer casts. But a wall the hand cannot pass whatever it learns is a wall, not a game, and you know it."},
}


def build(side, model=None, hooks=None, **kw):
    if model is None:
        from .model import pick
        model = pick()
    if hooks is None:
        hooks = [Ledger(), Fence()]
    sp = SYSTEM.format(band=f"{BAND[0]}..{BAND[1]}", **SIDES[side])
    return Agent(model=model, tools=[state_of_play, current_config, pace_model, proposer(side)],
                 system_prompt=sp, name=side, hooks=hooks, **kw)


def judge(current_cfg, hand, proposals, band=BAND):
    """Arithmetic decides. Start from the current config; for each key either
    side proposed, try the sides' values (the smaller move first) and keep the
    one that leaves the predicted end inside the band, closest to its middle.
    A key nobody's value can keep in band stays as it is."""
    cfg = current_cfg
    before = pace.end_of(cfg, hand)
    mid = sum(band) / 2
    keys = []
    for side in ("hotoke", "oni"):
        for k in (proposals.get(side) or {}).get("changes", {}):
            if k not in keys:
                keys.append(k)
    chosen, why = {}, {}
    def cur(k):
        return cfg["tower"].get(k[6:]) if k.startswith("tower.") else cfg.get(k)
    def dist(w):
        return abs((w if w is not None else 999) - mid)
    for k in keys:
        options = []
        for side in ("hotoke", "oni"):
            ch = (proposals.get(side) or {}).get("changes", {})
            if k in ch:
                options.append((abs(ch[k] - (cur(k) or 0)), side, ch[k]))
        options.sort()
        base = dist(pace.end_of(cfg, hand))
        best = None
        for move, side, v in options:
            trial, refused = pace.with_changes(cfg, {k: v})
            if refused:
                continue
            w = pace.end_of(trial, hand)
            if w is not None and band[0] <= w <= band[1] and (best is None or dist(w) < best[0]):
                best = (dist(w), side, v, w, trial)
        if best and best[0] <= base + 1e-9:
            _, side, v, w, trial = best
            cfg = trial
            chosen[k] = v
            why[k] = f"{side}'s {v}: predicted end {w}"
        else:
            why[k] = "kept: no proposed value holds the predicted end in band, or none improves on it"
    after = pace.end_of(cfg, hand)
    return {"changes": chosen, "why": why, "end_before": before, "end_after": after, "band": list(band)}


def argue(model=None, out_dir=OUT, hooks=None, quiet=False):
    """Both sides speak, the judge decides, the verdict is a file."""
    global _proposals
    _proposals = {}
    said = {}
    for side in ("hotoke", "oni"):
        agent = build(side, model=model, hooks=hooks, callback_handler=None if quiet else None)
        said[side] = str(agent("Read the state of play and make your proposal."))
    hand = pace.hand_of(runs())
    verdict = judge(pace.current(), hand, _proposals)
    record = {"date": date.today().isoformat(), "hand": hand, "current": {k: v for k, v in pace.current().items() if k in pace.TUNABLE or k == "tower"},
              "hotoke": {**_proposals.get("hotoke", {}), "said": said["hotoke"]},
              "oni": {**_proposals.get("oni", {}), "said": said["oni"]},
              "verdict": verdict}
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"balance-{record['date']}.json"
    p.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    record["file"] = str(p)
    return record


def apply(verdict_file, game=pace.GAME):
    """A human's command, not an agent's tool: write a verdict's changes into
    the hiragana game pack's field block. The build and the tests follow."""
    rec = json.loads(Path(verdict_file).read_text(encoding="utf-8"))
    changes = rec["verdict"]["changes"]
    pack = json.loads(Path(game).read_text(encoding="utf-8"))
    field = pack.setdefault("field", {})
    for k, v in changes.items():
        if k.startswith("tower."):
            field.setdefault("tower", {})[k[6:]] = v
        else:
            field[k] = v
    Path(game).write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changes


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--apply"]:
        print("applied", apply(argv[1]))
        return
    rec = argue()
    print()
    print("── 仏 hotoke ──", rec["hotoke"].get("changes"), "·", rec["hotoke"].get("because"))
    print("── 鬼 oni ──", rec["oni"].get("changes"), "·", rec["oni"].get("because"))
    v = rec["verdict"]
    print("── the judge ──", v["changes"], f"predicted end {v['end_before']} -> {v['end_after']} (band {v['band']})")
    for k, w in v["why"].items():
        print("  ", k, ":", w)
    print("written to", rec["file"], "· apply with: python -m hito_agents.balance --apply", rec["file"])


if __name__ == "__main__":
    main()
