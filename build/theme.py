#!/usr/bin/env python3
"""Themes: one table, applied to a finished page.

The engine was painted gold on dark lacquer for the Thai tracer, and every
layer since has matched it by hand, so the colours live as literals in six
files and two languages (CSS, and rgba() strings inside canvas code). They
are a small closed set, though — about forty — which makes a theme a mapping
rather than a refactor: build the page, then translate its colours.

`gold` is the identity and stays the Thai realm's, as CLAUDE.md says it
should. `night` is the night-forest the same document asked the shared engine
to lean toward, and what the maintainer asked for by name: dark, blue and
green. Blue takes gold's job (the ink, the path, the thing to press); green
takes teal's (a lit character, a ghost light, whatever is selected). Nothing
changes meaning, so nothing needs re-learning.

What is deliberately NOT translated: the reds of a zap and the orange of ink
that strayed. Those are warnings, and against blue they warn better than ever.

Base64 font data cannot collide with any of this: it contains neither `#` nor
a comma.
"""

import re

NIGHT = {
    # gold -> blue: the ink, the path, the primary action
    "#e9c46a": "#6cb8ff", "233,196,106": "108,184,255",
    "#fff1b8": "#e2f3ff", "255,241,184": "226,243,255",
    "#ffe9a8": "#bfe3ff",
    "240,210,130": "205,234,255",              # the dots along the path: paler than the trail they sit on
    "#f0e3c4": "#d7e9f7", "240,227,196": "215,233,247",
    # teal -> green: lit, selected, alive
    "#7fd1c4": "#5fe3a1", "127,209,196": "95,227,161",
    "#bdf0e6": "#c3f7dc", "189,240,230": "195,247,220",
    "#a8ecdc": "#aef2cf", "#9fd8cc": "#93e0b9", "#e6fffa": "#e6fff2",
    "160,230,215": "150,240,195",
    "#172422": "#10241c", "20,32,32": "16,36,28", "90,160,150": "70,170,120",
    # lacquer browns -> night blues
    "#15100d": "#0a0f15", "#1d1a16": "#101820", "#15120f": "#0c131a", "#0f0d0b": "#080c11",
    "#0c0908": "#06090d", "12,10,8": "6,9,13", "22,20,17": "13,19,26",
    "#2f2a24": "#1b2732", "#241b14": "#101c28",
    "#211812": "#0f1820",                      # --lacquer-2: the panels the field and sketchbook sit on
    "#57492f": "#2a4256", "87,73,47": "42,66,86", "#3d3324": "#1e2f3e", "#8b7b62": "#6b8296",
    # cream text -> cool white
    "#e8e0cc": "#dce8f2", "232,224,204": "220,232,242", "#ece4d8": "#e3edf5",
}
THEMES = {"gold": {}, "night": NIGHT}


def apply(text, name):
    """Translate every colour in a finished page. Unknown theme is an error."""
    if name not in THEMES:
        raise SystemExit(f"unknown theme {name!r}; known: {', '.join(THEMES)}")
    table = THEMES[name]
    if not table:
        return text
    hexes = {k.lower(): v for k, v in table.items() if k.startswith("#")}
    rgbs = {k: v for k, v in table.items() if not k.startswith("#")}
    text = re.sub(r"#[0-9a-fA-F]{6}\b", lambda m: hexes.get(m.group(0).lower(), m.group(0)), text)
    # r,g,b with or without spaces, inside rgb()/rgba() or a bare 'r,g,b' string
    def rgb(m):
        key = f"{m.group(1)},{m.group(2)},{m.group(3)}"
        return rgbs[key] if key in rgbs else m.group(0)
    return re.sub(r"(?<![\d.,])(\d{1,3}),\s?(\d{1,3}),\s?(\d{1,3})(?![\d])(?=\s?[,)'\"`])", rgb, text)


def leftovers(text, name):
    """Source colours of a theme still present in a page: should be none."""
    table = THEMES.get(name) or {}
    low = text.lower()
    return sorted(k for k in table if (k.lower() in low) and k.lower() not in {v.lower() for v in table.values()})
