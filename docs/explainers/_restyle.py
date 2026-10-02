#!/usr/bin/env python3
"""Apply the canonical explainer reading style to every HAND-WRITTEN explainer.

ONE stylesheet (`_explainer-style.css`), N pages, no copies to drift.

⛔ WHY IT SPLICES THE COMPOSED PAGE INSTEAD OF RE-COMPOSING. `brief-compose.py` names its
   output `<today>-<kind>-<slug>.html`, so re-composing a page dated 09-24 creates a NEW
   09-25 file and leaves the original stale. Measured the hard way: a first version passed
   the full filename as `--slug` and produced ten `2026-09-25-brief-2026-09-24-…` duplicates.

⛔ SKIPS THE GENERATED PAGES (dashboard, goals, backlog-table, features). Their palettes are
   local by a recorded decision — `scripts/page_chrome.py`: "MECHANISM SHARED, PALETTE LOCAL …
   emitting one palette would flatten six pages that deliberately look different."

The composed <style> block is ordered [fragment CSS][SHIM][tray CSS]. Only the first part is
replaced; the SHIM and the tray are preserved byte-for-byte, because hand-copying a working
tray between documents is a failure this project has already measured.
"""
import re, sys
from pathlib import Path

D = Path.home()/"explainers"
GENERATED = ("dashboard", "goals", "backlog-table", "features")
SHIM_START = re.compile(r":root\s*\{\s*--verified:\s*var\(--good")
TAGS = ("strong","em","code","p","li","div","td","th","tr","table","h2","h3","h4","pre","span")

css_src = (D/"_explainer-style.css").read_text()
CANON = re.sub(r"^/\*.*?\*/\s*", "", css_src, count=1, flags=re.S).strip()

SCRIPTISH = re.compile(r"<(script|style|pre|textarea)\b.*?</\1>", re.S | re.I)

def unbalanced(body):
    # ⛔ COUNT ONLY WHAT THE PARSER SEES AS MARKUP. A first version counted `<div>` inside the
    #    tray's JavaScript template strings and flagged EVERY composed page -- including one
    #    verified to render correctly. Measuring the wrong population, in the checker.
    body = SCRIPTISH.sub("", body)
    bad = [t for t in TAGS
           if len(re.findall(rf"<{t}(?:\s[^>]*)?>", body)) != len(re.findall(rf"</{t}>", body))]
    d = 0
    for m in re.finditer(r"</?strong>", body):
        d += 1 if m.group(0) == "<strong>" else -1
        if d < 0: bad.append("strong:close-before-open"); d = 0
    if d: bad.append(f"strong:depth{d}")
    return bad

done, skipped, refused = [], [], []
for page in sorted(D.glob("*.html")):
    slug = page.stem
    if slug.startswith(GENERATED) or slug.endswith(".fragment"):
        skipped.append(slug); continue
    t = page.read_text()
    st = re.search(r"<style>(.*?)</style>", t, re.S)
    if not st:                       refused.append((slug, "no <style> block")); continue
    m = SHIM_START.search(st.group(1))
    if not m:                        refused.append((slug, "SHIM boundary not found — refusing to guess where the fragment CSS ends")); continue
    # ⛔ CHECK THE FRAGMENT, NOT THE COMPOSED PAGE. The tray's own markup contributes a
    #    trailing unclosed <div> on EVERY composed page, so checking the page refused all 52
    #    -- a false refusal from measuring a population this script does not own. The fragment
    #    is the part authored here, and it is the part a bad edit breaks.
    frag = D/f"{slug}.fragment.html"
    if frag.exists():
        bad = unbalanced(frag.read_text().split("</style>", 1)[-1])
        if bad:                      refused.append((slug, f"fragment has unbalanced tags {bad}")); continue
    before = st.group(1)
    new_css = CANON + "\n" + before[m.start():]
    out = t[:st.start(1)] + new_css + t[st.end(1):]
    # the tray must survive, byte-for-byte
    for needle in ("#tray", ".askbtn", "#qbox", "#sendbtn"):
        if out.count(needle) < t.count(needle):
            refused.append((slug, f"splice would have dropped {needle} — refused")); break
    else:
        page.write_text(out); done.append(slug)

print(f"✅ restyled {len(done)}")
for s in done: print(f"    {s}")
if skipped: print(f"⏭  skipped {len(skipped)}: {', '.join(skipped)}")
if refused:
    print(f"⛔ refused {len(refused)} — NOT restyled, and NOT silently:")
    for s, why in refused: print(f"    {s}: {why}")
