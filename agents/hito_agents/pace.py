"""The pace of the tower, as arithmetic.

A run ends when the swarm outruns the hand. This module says where, for a
given field config and a measured hand: hits the farang need per second
against hits the hand and its lights can supply. It is the yardstick the
balance agents argue against and the judge decides with — a script, so a
test can check it, and so an agent cannot move it by being persuasive.

The defaults are read out of `build/shell_field.py` itself, so this model
cannot quietly drift from the game.
"""
import json
import re
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
SHELL = ROOT / "build" / "shell_field.py"
GAME = ROOT / "scripts" / "hiragana" / "game.json"

# What may be tuned, and how far. The bounds are the referee's, not the
# agents': a proposal outside them is refused before anyone argues.
TUNABLE = {
    "spawnMs":     (2000, 9000),
    "spawnMin":    (1200, 6000),
    "spawnRamp":   (0, 300),
    "hpEvery":     (5, 100),
    "hpMax":       (1, 200),
    "biteEvery":   (5, 100),
    "biteMax":     (1, 6),
    "castCost":    (1, 4),
    "energyPerStroke": (1, 3),
    "hitodamaGain": (1, 3),
}
TOWER_TUNABLE = {"rowWaves": (5, 30), "bossEvery": (5, 30), "bossHp": (0, 5), "bossBite": (0, 3)}


def shell_defaults(path=SHELL):
    """Every `f.get('key', default)` the shell writes into a build, plus the
    tower's defaults, read from the source rather than copied."""
    src = path.read_text(encoding="utf-8")
    out = {}
    for k, v in re.findall(r"f\.get\('([A-Za-z]+)', ([-\d.]+)\)", src):
        out[k] = float(v) if "." in v else int(v)
    m = re.search(r"\*\*\{('rows': [^}]*)\}", src)
    tower = {}
    if m:
        for k, v in re.findall(r"'([A-Za-z]+)': ([-\d.]+)", m.group(1)):
            tower[k] = float(v) if "." in v else int(v)
    out["tower"] = tower
    return out


def current(game=GAME, shell=SHELL):
    """The hiragana game's field config as the build sees it: shell defaults
    under the pack's own field block."""
    cfg = shell_defaults(shell)
    pack = json.loads(Path(game).read_text(encoding="utf-8"))
    field = dict(pack.get("field") or {})
    tower = dict(cfg.get("tower") or {})
    tower.update(field.pop("tower", None) or {})
    cfg.update(field)
    cfg["tower"] = tower
    return cfg


def with_changes(cfg, changes):
    """A copy of cfg with the changes applied; refuses unknown keys and
    values outside the bounds, with a plain reason each."""
    out = dict(cfg)
    out["tower"] = dict(cfg.get("tower") or {})
    refused = {}
    for k, v in (changes or {}).items():
        if k.startswith("tower."):
            tk = k[6:]
            if tk not in TOWER_TUNABLE:
                refused[k] = "not a tunable"
                continue
            lo, hi = TOWER_TUNABLE[tk]
            if not isinstance(v, (int, float)) or not lo <= v <= hi:
                refused[k] = f"outside {lo}..{hi}"
                continue
            out["tower"][tk] = v
        elif k in TUNABLE:
            lo, hi = TUNABLE[k]
            if not isinstance(v, (int, float)) or not lo <= v <= hi:
                refused[k] = f"outside {lo}..{hi}"
                continue
            out[k] = v
        else:
            refused[k] = "not a tunable"
    return out, refused


def hand_of(runs, version=None, min_runs=5):
    """The measured hand: seconds per trace, strokes per trace (from the
    energy a run could earn — not recorded, so 2.5 is assumed), and how far
    runs go. Medium only, practice left out. With a version and enough runs
    on it, the waves are that version's: a pace is judged by the runs that
    were played at it."""
    real = [r for r in runs if r.get("difficulty") == "medium" and not r.get("practice") and r.get("traced")]
    if version:
        mine = [r for r in real if r.get("v") == version]
        if len(mine) >= min_runs:
            real = mine
    if not real:
        return {"runs": 0, "s_per_trace": 3.6, "strokes_per_trace": 2.5, "wave_p50": None, "wave_max": None, "assumed": True}
    tpt = median((r.get("ms") or 0) / 1000 / r["traced"] for r in real)
    waves = sorted(r.get("wave") or 0 for r in real)
    return {
        "runs": len(real),
        "s_per_trace": round(tpt, 2),
        "strokes_per_trace": 2.5,
        "wave_p50": waves[len(waves) // 2],
        "wave_max": waves[-1],
        "version": version if version and real and real[0].get("v") == version else None,
        "s_p50": round(median((r.get("ms") or 0) / 1000 for r in real)),
        "clean_rate": round(sum(r.get("clean") or 0 for r in real) / max(1, sum(r["traced"] for r in real)), 2),
        "assumed": False,
    }


def model(cfg, hand, waves=range(0, 201, 10)):
    """Need against supply, wave by wave; the wall (the first wave where the
    farang need more hits a second than the hand and its lights give); and
    the end, the wave the ward is predicted to fall on, since a run outlives
    its wall for as long as the ward can absorb what gets through. The end
    is what a run's record measures, so it is what the judge holds in band.
    Calibration: the config before v0.1.63 ends near 25 here against a
    measured median of 27 and a furthest of 43."""
    tpt = hand.get("s_per_trace") or 3.6
    spt = hand.get("strokes_per_trace") or 2.5
    tower = cfg.get("tower") or {}
    gain = cfg.get("hitodamaGain", 1)
    # per trace: the trace is a hit, and it kindles `gain` charges, each a
    # hit if the bag of 気 can pay for it — a stroke fills energyPerStroke,
    # a cast costs castCost
    lights = min(gain, spt * cfg.get("energyPerStroke", 1) / max(1, cfg.get("castCost", 2)))
    supply = (1 + lights) / tpt
    table, wall = [], None
    for w in waves:
        gap = max(cfg["spawnMin"], cfg["spawnMs"] - w * cfg["spawnRamp"]) / 1000
        hp = 1 if not cfg.get("hpEvery") else min(cfg["hpMax"], 1 + w // cfg["hpEvery"])
        boss = tower.get("bossHp", 0) / max(1, tower.get("bossEvery", 10))   # the boss's extra hits, spread over its stretch
        need = (hp + boss) / gap
        held = need <= supply
        if not held and wall is None:
            wall = w
        table.append({"wave": w, "gap_s": round(gap, 2), "hp": hp, "need": round(need, 2), "supply": round(supply, 2), "held": held})
    # the end: farang by farang, what the hand cannot answer in the gap
    # reaches the ward, and bites by the wave's bite
    ward = cfg.get("wardHp", 5) + hand.get("hearts", 0)
    end = None
    for w in range(0, 400):
        gap = max(cfg["spawnMin"], cfg["spawnMs"] - w * cfg["spawnRamp"]) / 1000
        hp = 1 if not cfg.get("hpEvery") else min(cfg["hpMax"], 1 + w // cfg["hpEvery"])
        bite = 1 if not cfg.get("biteEvery") else min(cfg.get("biteMax", 4), 1 + w // cfg["biteEvery"])
        boss = tower.get("bossEvery") and (w + 1) % tower["bossEvery"] == 0
        if boss:
            hp += tower.get("bossHp", 0); bite += tower.get("bossBite", 0)
        short = max(0.0, hp - supply * gap)
        ward -= min(1.0, short / hp) * bite
        if ward <= 0:
            end = w
            break
    return {"supply": round(supply, 2), "wall": wall, "end": end, "table": table}


def end_of(cfg, hand):
    return model(cfg, hand)["end"]


def calibration(cfg, hand):
    """What the model does not know — upgrades, the release, the lanterns a
    hand has bought — as one factor: the measured median wave over the
    model's bare-hand end for the same config. 1 with nothing measured.
    (The model said 78 for a config the maintainer took to wave 230.)"""
    p50 = hand.get("wave_p50")
    e = end_of(cfg, hand)
    if not p50 or not e:
        return 1.0
    return max(0.2, min(10.0, p50 / e))


def predicted(cfg, hand, k=1.0):
    """The end, scaled by the calibration: where a run like the measured
    ones is predicted to end under this config."""
    e = end_of(cfg, hand)
    return None if e is None else round(e * k)


def wall_of(cfg, hand):
    return model(cfg, hand)["wall"]
