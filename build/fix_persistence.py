#!/usr/bin/env python3
"""Give a build's persistence layer a real implementation.

The engine calls an ambient `window.storage` that it never defines. Every call
sits behind an `if (window.storage)` guard, so in an ordinary browser saving
and loading are silent no-ops — while saveCurrent() reports "saved ✓"
regardless, because persist() is fire-and-forget with no error path.

That is how two recording sessions were lost. This applies the fix to a build
that already exists, without touching anything else in it.

    fix_persistence.py <in.html> <out.html> <new-version>
"""

import re
import sys
from pathlib import Path

SHIM = """<script>
// The engine calls window.storage but never defines it, so every save and
// load was a silent no-op. This is that implementation. set() returns false
// when the write genuinely failed (quota, private browsing) so the UI can
// tell the truth about it.
window.storage=window.storage||{
  async get(k){ try{ const v=localStorage.getItem(k); return v==null?null:{value:v}; }catch(_){ return null; } },
  async set(k,v){ try{ localStorage.setItem(k,v); return true; }catch(_){ return false; } }
};
</script>
"""


def sub(text, what, pattern, repl, count=1, flags=0):
    new, n = re.subn(pattern, lambda _: repl, text, count=count, flags=flags)
    if n != count:
        sys.exit(f"'{what}' matched {n} time(s), expected {count} — "
                 f"the build has changed shape; fix the anchor.")
    print(f"  · {what}")
    return new


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    src, dest, version = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    s = src.read_text(encoding="utf-8")

    if "window.storage=window.storage||" in s:
        sys.exit(f"{src.name} already has the fix.")

    s = sub(s, "storage shim", r"<body>", "<body>\n" + SHIM)
    s = sub(s, "persist returns a result",
            r"async function persist\(\)\{[^\n]*?\}\n",
            "async function persist(){ try{ if(!window.storage) return false;\n"
            "  return await window.storage.set('nirathai-teacher-strokes',"
            "JSON.stringify(TEACHER),false);\n"
            "}catch(_){ return false; } }\n")
    s = sub(s, "save reports failure honestly",
            r"persist\(\); toast\('saved ✓'\);",
            "persist().then(ok=>toast(ok?'saved ✓':"
            "'SAVE FAILED — export before you close this tab'));")

    # The header badge read 0.9.0 while the title and toast said 0.9.3.
    s = sub(s, "version stamp: APP_VERSION",
            r"const APP_VERSION='[^']*';", f"const APP_VERSION='{version}';")
    # Note: sub() replaces via a lambda, so backreferences do not expand —
    # build the whole replacement string here instead.
    title = re.search(r"<title>([^<]*?)v[\d.]+</title>", s)
    if not title:
        sys.exit("could not find a versioned <title>")
    s = sub(s, "version stamp: title",
            r"<title>[^<]*</title>", f"<title>{title.group(1)}v{version}</title>")
    s = sub(s, "version stamp: boot toast",
            r"toast\('build v[^']*'\)", f"toast('build v{version}')")

    dest.write_text(s, encoding="utf-8")
    print(f"\n{dest}  {dest.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()
