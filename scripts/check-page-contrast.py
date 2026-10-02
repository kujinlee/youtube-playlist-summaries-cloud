#!/usr/bin/env python3
"""Every visible text element on every served page, measured for contrast against the background
it ACTUALLY sits on — in both colour schemes — and held to a baseline that cannot silently worsen.

⛔ WHY THIS EXISTS, AND IT IS A CONFESSION. On 2026-10-02 a one-rule stylesheet was injected into
all 62 explainer pages to soften bold text. It drove 56 elements below WCAG AA and bottomed out at
1.70:1 — invisible — on a page the reader opens regularly. The author had verified the rule on TWO
pages and asserted it of fifty-six. A reviewer found it; nothing mechanical could have, because
NOTHING IN THIS REPOSITORY MEASURED CONTRAST. Backlog #220 is that hole; #221 is the unification
this guard exists to make safe.

⛔ THE ORDER IS THE POINT. This harness is built and BASELINED BEFORE the style change it guards.
Building the change first and measuring second is precisely the sequence that failed, and a gate
authored after the fact is a gate shaped to pass.

RULE AND FETCH ARE SEPARATE, and `separate-the-rule-from-the-fetch` is why: three ratchets in this
repo went eight days untestable because their entry point needed a live service. Everything that
decides anything here — parsing a CSS colour, compositing alpha, the WCAG ratio, the verdict
against a baseline — is PURE and cased below with no browser. Only `measure()` needs Chromium.

⚠ THE PARSER IS THE PART THAT WAS ALREADY WRONG ONCE. Chromium returns `color(srgb 0.78 0.76 0.8)`
for some computed values, whose components are ALREADY NORMALISED 0..1. The first contrast probe
written in this repo divided them by 255 and reported 1.16:1, which read as catastrophe and was
arithmetic. `parse_color` handles both spellings and the cases below pin that difference.

USAGE
    python3 scripts/check-page-contrast.py --self-test        # pure rules, no browser
    python3 scripts/check-page-contrast.py --write-baseline docs/contrast-baseline.json
    python3 scripts/check-page-contrast.py --against docs/contrast-baseline.json
    python3 scripts/check-page-contrast.py --report           # measure and print, no verdict

⛔ NOT A PASS WHEN IT CANNOT RUN. No Chromium, no pages, or a page that fails to load is rc=2 and
says TREAT THIS AS NOT RUN. A contrast gate that goes quiet when it cannot see is worse than none,
because the silence is indistinguishable from "everything is readable".

    python3 scripts/check-page-contrast.py --self-test  # 64 cases
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling modules, e.g. page_chrome
PAGES_DIR = ROOT / "docs" / "explainers"

# WCAG 2.1: 4.5:1 for normal text, 3.0:1 for large text (>=18.66px bold, or >=24px).
AA_NORMAL = 4.5
AA_LARGE = 3.0


class CannotRun(Exception):
    """The measurement could not reach its subject. Never a pass."""


# ── PURE: colour ────────────────────────────────────────────────────────────────────────────────

_RGB_FUNC = re.compile(r"rgba?\(([^)]+)\)")
_SRGB_FUNC = re.compile(r"color\(\s*srgb\s+([^)]+)\)")


def parse_color(css: str) -> tuple[float, float, float, float]:
    """A computed CSS colour -> (r, g, b, a) with r/g/b in 0..255 and a in 0..1.

    ⛔ TWO SPELLINGS, TWO SCALES, AND CONFLATING THEM IS A MEASURED BUG. `rgb(198, 197, 207)`
    carries 0..255 components; `color(srgb 0.776 0.773 0.812)` carries 0..1 components for the
    same colour. Dividing the second by 255 reports near-zero luminance, which looks exactly like
    a contrast catastrophe and is not one.
    """
    s = css.strip()
    m = _SRGB_FUNC.search(s)
    if m:
        parts = [p for p in re.split(r"[\s/]+", m.group(1).strip()) if p]
        vals = [float(x) for x in parts[:3]]
        alpha = float(parts[3]) if len(parts) > 3 else 1.0
        return (vals[0] * 255.0, vals[1] * 255.0, vals[2] * 255.0, alpha)
    m = _RGB_FUNC.search(s)
    if m:
        parts = [p.strip() for p in re.split(r"[,\s/]+", m.group(1).strip()) if p.strip()]
        vals = [float(x) for x in parts[:3]]
        alpha = float(parts[3]) if len(parts) > 3 else 1.0
        return (vals[0], vals[1], vals[2], alpha)
    if s in ("transparent", "rgba(0, 0, 0, 0)"):
        return (0.0, 0.0, 0.0, 0.0)
    raise CannotRun(f"unparseable computed colour {css!r} — the measurement cannot proceed on a "
                    f"colour it does not understand, and guessing one would be a fabricated number")


def composite(fg: tuple[float, float, float, float],
              bg: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    """Source-over: lay a possibly-translucent `fg` on an opaque-enough `bg`.

    ⚠ ALPHA IS WHY THE FIRST PROBE WAS WRONG TWICE. A translucent foreground's CONTRIBUTION is
    what the eye sees, so the ratio must be taken after compositing, never on the declared colour.
    """
    a = fg[3]
    return (fg[0] * a + bg[0] * (1 - a),
            fg[1] * a + bg[1] * (1 - a),
            fg[2] * a + bg[2] * (1 - a),
            1.0)


def _lin(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple[float, float, float, float]) -> float:
    """WCAG relative luminance. Alpha is ignored — composite BEFORE calling this."""
    return 0.2126 * _lin(rgb[0]) + 0.7152 * _lin(rgb[1]) + 0.0722 * _lin(rgb[2])


def contrast(fg: tuple[float, float, float, float],
             bg: tuple[float, float, float, float]) -> float:
    """WCAG contrast ratio, 1.0 .. 21.0. Symmetric by construction."""
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def threshold_for(px: float, weight: float) -> float:
    """WCAG's large-text carve-out: >=24px, or >=18.66px when bold (weight >= 700)."""
    large = px >= 24.0 or (px >= 18.66 and weight >= 700)
    return AA_LARGE if large else AA_NORMAL


# ── PURE: the verdict ───────────────────────────────────────────────────────────────────────────

def sample_key(s: dict) -> str:
    """Stable identity for one measured SITE, so a baseline survives the change it guards.

    ⛔ IT MUST NOT CONTAIN A COLOUR, AND THE FIRST TWO VERSIONS BOTH DID THE WRONG THING. Keyed on
    element TEXT, one page produced 10,626 rows and any content edit invalidated the baseline.
    Keyed on (fg, bg, size, weight) it was compact and stable — until the first real use, a
    palette change, altered every fg and bg, so NO key matched and all 196 affected elements were
    reported as "NEW" instead of compared. **A baseline keyed on the thing under test cannot
    measure a change to that thing.** The key is now page, scheme, selector path, size, weight —
    every component of WHERE the text is, and none of HOW it is coloured.

    ⚠ Two sites can share a key and differ in colour (the same selector path inside a verified
    box and a defect box). `collapse` keeps the WORST ratio for a key, which is conservative in
    the only direction that matters: it can over-report a regression, never hide one.
    """
    return f"{s['page']}|{s['scheme']}|{s['selector']}|{s['px']:.1f}|{int(s['weight'])}"


def collapse(rows: list[dict]) -> list[dict]:
    """PURE. Many measured elements -> one sample per site, carrying its WORST ratio.

    ⛔ WORST, NOT FIRST OR MEAN. Sites sharing a key can differ in colour, and a baseline that
    recorded the first or the average would let the worst of them degrade unseen. Over-reporting
    a regression costs a reader one line; hiding one costs the thing this harness exists for.
    """
    out: dict[str, dict] = {}
    for r in rows:
        k = sample_key(r)
        hit = out.get(k)
        if hit is None:
            out[k] = {**r, "instances": 1}
        else:
            hit["instances"] += 1
            if r["ratio"] < hit["ratio"]:
                hit["ratio"] = r["ratio"]
                hit["text"] = r["text"]
                hit["fg"] = r["fg"]
                hit["bg"] = r["bg"]
    return list(out.values())


def verdict(samples: list[dict], baseline: dict | None) -> list[str]:
    """PURE. -> the problems. A RATCHET, not an absolute bar.

    ⛔ IT RATCHETS BECAUSE AN ABSOLUTE BAR WOULD BE SWITCHED OFF. 303 elements in this corpus are
    already below AA on the day this was written; a gate that fails on all of them fails on every
    commit and gets disabled, which is backlog #56's measured verdict about exactly that. What is
    forbidden is MAKING IT WORSE: an element that passed and now fails, or one that was already
    failing and got worse by more than a rounding wobble.
    """
    problems: list[str] = []
    if baseline is None:
        return problems
    prior = {k: v for k, v in baseline.get("samples", {}).items()}
    for s in samples:
        k = sample_key(s)
        was = prior.get(k)
        if was is None:
            # New element. It must simply meet its own threshold — there is nothing to ratchet
            # against, and admitting new failures silently is how a ratchet rots.
            if s["ratio"] < s["threshold"]:
                problems.append(
                    f"NEW element below AA: {s['ratio']:.2f}:1 (needs {s['threshold']}) "
                    f"[{s['scheme']}] {s['page']} :: {s['text'][:60]!r}")
            continue
        # ⚠ `crossed` AND `worsened` OVERLAP, and the mutation sweep is how I found out.
        # Severing `crossed` does NOT hide the element — `worsened` still catches it, so
        # detection survives and only the MESSAGE changes. This branch is load-bearing for
        # TELLING THE READER WHICH HAPPENED, not for noticing. The manifest entry says so.
        crossed = was >= s["threshold"] > s["ratio"]
        worsened = s["ratio"] < was - 0.05 and s["ratio"] < s["threshold"]
        if crossed:
            problems.append(
                f"CROSSED below AA: {was:.2f} -> {s['ratio']:.2f} (needs {s['threshold']}) "
                f"[{s['scheme']}] {s['page']} :: {s['text'][:60]!r}")
        elif worsened:
            problems.append(
                f"WORSENED while already below AA: {was:.2f} -> {s['ratio']:.2f} "
                f"[{s['scheme']}] {s['page']} :: {s['text'][:60]!r}")
    return problems


def summarise(samples: list[dict]) -> dict:
    """PURE. -> the headline numbers, so a report cannot disagree with its own detail."""
    below = [s for s in samples if s["ratio"] < s["threshold"]]
    return {
        "elements": len(samples),
        "pages": len({s["page"] for s in samples}),
        "below_aa": len(below),
        "worst": min((s["ratio"] for s in samples), default=float("nan")),
    }


# ── FETCH: the only part that needs a browser ───────────────────────────────────────────────────

def measure(pages: list[Path], schemes=("light", "dark"), extra_css: str = "",
            root: Path = ROOT) -> list[dict]:
    """Drive Chromium over every page in both schemes. ⛔ Any failure here is CannotRun.

    ⛔ THROUGH NODE, AND A FALSE POSITIVE IS WHY. The first version imported playwright's Python
    binding, because `python3 -c "import playwright"` printed OK — against an EMPTY NAMESPACE
    PACKAGE whose `__file__` was None and which had no `sync_api`. The import succeeded and the
    capability was absent. `check-paid-caller-arrival` already shells out to a sibling `.mjs` for
    the same reason, so this follows the established route rather than inventing one.

    ⚠ THE PROBE DECIDES NOTHING. It reports computed colour, background, size and weight; every
    threshold and every verdict is pure Python above, cased without a browser.
    """
    probe = root / "scripts" / "page-contrast-probe.mjs"
    if not probe.is_file():
        raise CannotRun(f"{probe.name} is missing, so nothing can be measured. TREAT THIS AS NOT RUN.")
    if not pages:
        raise CannotRun("no pages to measure — an empty corpus is not a clean result, it is a "
                        "measurement that did not happen. TREAT THIS AS NOT RUN.")
    env = dict(os.environ)
    if extra_css:
        env["CONTRAST_EXTRA_CSS"] = extra_css
    samples: list[dict] = []
    for scheme in schemes:
        cmd = ["node", str(probe), scheme, *[str(p.resolve()) for p in pages]]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, cwd=root, env=env,
                                  timeout=900)
        except FileNotFoundError as exc:
            raise CannotRun(f"node is not on PATH ({exc}). TREAT THIS AS NOT RUN.") from exc
        except subprocess.TimeoutExpired as exc:
            raise CannotRun(f"the browser run timed out after 900s. TREAT THIS AS NOT RUN.") from exc
        if proc.returncode != 0:
            tail = (proc.stderr or "").strip().splitlines()[-3:]
            raise CannotRun(f"the {scheme} browser run exited {proc.returncode}: "
                            f"{' / '.join(tail) or 'no stderr'}. TREAT THIS AS NOT RUN.")
        rows = [json.loads(ln) for ln in proc.stdout.splitlines() if ln.strip()]
        if not rows:
            raise CannotRun(f"the {scheme} run produced ZERO elements over {len(pages)} page(s). "
                            f"A zero over a non-empty corpus is a probe that did not work, not a "
                            f"page with no text. TREAT THIS AS NOT RUN.")
        for raw in rows:
            fg = parse_color(raw["color"])
            bg = parse_color(raw["bg"])
            lit = composite(fg, bg) if fg[3] < 1.0 else fg
            samples.append({
                "page": raw["page"],
                "scheme": raw["scheme"],
                "selector": raw["selector"],
                "text": raw["text"],
                "fg": raw["color"],
                "bg": raw["bg"],
                "px": float(raw["px"]),
                "weight": float(raw["weight"]),
                "ratio": round(contrast(lit, bg), 3),
                "threshold": threshold_for(raw["px"], raw["weight"]),
            })
    return collapse(samples)


def is_served_page(text: str) -> bool:
    """PURE. -> is this a whole served page, or a fragment with no chrome?

    ⛔ THE VIEWPORT META, AND IT IS THE THIRD RULE TRIED. The signal was chosen by MEASURING four
    candidates over all 80 files in the directory, not by picking a plausible one:

        signal          fragments misread as pages   pages misread as fragments
        <html>                      0/20                        1/60
        viewport meta               0/20                        0/60
        :root block                20/20                        0/60
        prefers-color-scheme       19/20                        0/60

    A FILENAME rule was first and missed `frag-plan-mode-question.html` — a second naming
    convention, one file, which promptly turned up as the corpus's worst result at 1.00:1
    because a chromeless fragment has no palette. `<html>` was second and misread
    `2026-08-12-explanation-absence-protection-enforced-5cbedcf.html`, a REAL page authored
    without the tag that browsers imply. ⚠ `:root` looks like the obvious choice for a contrast
    harness and is the WORST of the four — fragments carry their own palettes, which is a large
    part of why this corpus diverged in the first place.
    """
    return 'name="viewport"' in text[:4000]


def corpus(pages_dir: Path = PAGES_DIR) -> list[Path]:
    """The served pages: every `.html` under `pages_dir` that is a whole document."""
    out = []
    for p in sorted(pages_dir.glob("*.html")):
        try:
            if is_served_page(p.read_text(encoding="utf-8", errors="replace")):
                out.append(p)
        except OSError:
            continue
    return out


# ── self-test ───────────────────────────────────────────────────────────────────────────────────

def _self_test() -> int:
    ok = fail = 0

    def case(name: str, got, want) -> None:
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            print(f"[FAIL] {name}\n       expected {want!r}\n       got      {got!r}")
            fail += 1

    def close(name: str, got: float, want: float, tol: float = 0.01) -> None:
        nonlocal ok, fail
        if got is not None and abs(got - want) <= tol:
            ok += 1
        else:
            print(f"[FAIL] {name}\n       expected {want} +/- {tol}\n       got      {got}")
            fail += 1

    def refuses(name: str, fn) -> None:
        nonlocal ok, fail
        try:
            fn()
        except CannotRun:
            ok += 1
            return
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {name} — raised {exc.__class__.__name__}, not CannotRun")
            fail += 1
            return
        print(f"[FAIL] {name} — returned instead of refusing")
        fail += 1

    # ── parse_color: the two scales, which is the bug this file was written after ──
    case("rgb() parses 0..255 components", parse_color("rgb(198, 197, 207)"), (198.0, 197.0, 207.0, 1.0))
    case("rgba() carries its alpha", parse_color("rgba(0, 0, 0, 0.5)"), (0.0, 0.0, 0.0, 0.5))
    # ⛔ THE MEASURED BUG: these two spellings are the SAME colour on different scales.
    close("color(srgb ...) is NORMALISED and scales UP, not down",
          parse_color("color(srgb 0.776471 0.772549 0.811765)")[0], 198.0, tol=0.5)
    case("...and the two spellings agree once parsed",
         [round(x) for x in parse_color("color(srgb 0.776471 0.772549 0.811765)")[:3]],
         [round(x) for x in parse_color("rgb(198, 197, 207)")[:3]])
    close("color(srgb ...) alpha after a slash", parse_color("color(srgb 0 0 0 / 0.25)")[3], 0.25)
    case("transparent is zero-alpha black", parse_color("transparent"), (0.0, 0.0, 0.0, 0.0))
    case("the fully-transparent rgba spelling too", parse_color("rgba(0, 0, 0, 0)"), (0.0, 0.0, 0.0, 0.0))
    refuses("an unparseable colour REFUSES rather than guessing", lambda: parse_color("chartreuse"))
    refuses("...and so does an empty string", lambda: parse_color(""))

    # ── luminance + contrast, against values anyone can check by hand ──
    close("black luminance is 0", luminance((0, 0, 0, 1)), 0.0)
    close("white luminance is 1", luminance((255, 255, 255, 1)), 1.0)
    close("black on white is 21:1", contrast((0, 0, 0, 1), (255, 255, 255, 1)), 21.0)
    close("white on black is also 21:1 — the ratio is symmetric",
          contrast((255, 255, 255, 1), (0, 0, 0, 1)), 21.0)
    close("a colour against itself is 1:1", contrast((120, 120, 120, 1), (120, 120, 120, 1)), 1.0)
    # The real pair from the 2026-10-02 failure, so the harness is pinned to the defect it exists for.
    close("the #220 failure reproduces: #c8c5cf on #ffffff",
          contrast((200, 197, 207, 1), (255, 255, 255, 1)), 1.70, tol=0.02)
    close("...and what that text WAS before: #151b23 on #ffffff",
          contrast((21, 27, 35, 1), (255, 255, 255, 1)), 17.31, tol=0.05)

    # ── compositing ──
    case("a fully opaque foreground is unchanged by compositing",
         composite((10, 20, 30, 1.0), (255, 255, 255, 1.0)), (10.0, 20.0, 30.0, 1.0))
    case("a fully transparent foreground becomes the background",
         composite((10, 20, 30, 0.0), (200, 100, 50, 1.0)), (200.0, 100.0, 50.0, 1.0))
    case("half alpha lands halfway", composite((0, 0, 0, 0.5), (200, 200, 200, 1.0)),
         (100.0, 100.0, 100.0, 1.0))
    # ⛔ THE WHOLE REASON COMPOSITING IS HERE: the ratio differs before and after.
    case("compositing CHANGES the verdict, which is why it is not optional",
         round(contrast((0, 0, 0, 0.3), (255, 255, 255, 1)), 1)
         != round(contrast(composite((0, 0, 0, 0.3), (255, 255, 255, 1)), (255, 255, 255, 1)), 1),
         True)

    # ── the large-text carve-out ──
    case("16px normal weight needs 4.5", threshold_for(16, 400), AA_NORMAL)
    case("24px needs only 3.0", threshold_for(24, 400), AA_LARGE)
    case("18.66px BOLD needs only 3.0", threshold_for(18.66, 700), AA_LARGE)
    case("18.66px at 400 still needs 4.5 — weight is half the rule", threshold_for(18.66, 400), AA_NORMAL)
    case("23.9px at 400 still needs 4.5 — the boundary is not rounded", threshold_for(23.9, 400), AA_NORMAL)

    # ── the verdict ratchet ──
    def s(ratio, page="p.html", scheme="light", text="hello", thr=AA_NORMAL,
          fg="rgb(0, 0, 0)", bg="rgb(255, 255, 255)", px=16.0, weight=400.0, selector="body>p"):
        return {"page": page, "scheme": scheme, "selector": selector, "text": text,
                "fg": fg, "bg": bg, "px": px, "weight": weight,
                "ratio": ratio, "threshold": thr}

    # ── collapse: the element -> style-combination step ──
    # ⛔ WHY IT EXISTS: keyed on element text, the backlog page alone produced 10,626 rows and the
    # baseline was invalidated by adding one table row. Contrast is a property of a combination.
    case("identical style combinations collapse to ONE sample",
         len(collapse([s(5.0, text="a"), s(5.0, text="b"), s(5.0, text="c")])), 1)
    case("...and the survivor counts how many it stands for",
         collapse([s(5.0, text="a"), s(5.0, text="b")])[0]["instances"], 2)
    case("...keeping the FIRST text as the exemplar, so a message can name real words",
         collapse([s(5.0, text="first"), s(5.0, text="second")])[0]["text"], "first")
    # ⛔ COLOUR IS NOT PART OF IDENTITY — this is the property the palette change required, and
    # the version that lacked it reported all 196 affected elements as NEW instead of comparing.
    case("a different FOREGROUND is the SAME site, so a palette change can be compared",
         len(collapse([s(5.0), s(4.0, fg="rgb(1, 1, 1)")])), 1)
    case("...and the survivor carries the WORST ratio, never the first",
         collapse([s(5.0), s(4.0, fg="rgb(1, 1, 1)")])[0]["ratio"], 4.0)
    case("...in either order, so it is a minimum and not a last-write",
         collapse([s(4.0, fg="rgb(1, 1, 1)"), s(5.0)])[0]["ratio"], 4.0)
    case("a different SELECTOR is a different site",
         len(collapse([s(5.0), s(5.0, selector="body>h1")])), 2)
    case("a different SIZE is a different combination — it changes the threshold",
         len(collapse([s(5.0, px=16.0), s(5.0, px=24.0)])), 2)
    case("a different WEIGHT is too, for the same reason",
         len(collapse([s(5.0, weight=400), s(5.0, weight=700)])), 2)
    case("the same combination on a different PAGE stays separate",
         len(collapse([s(5.0), s(5.0, page="q.html")])), 2)
    case("...and in a different SCHEME",
         len(collapse([s(5.0), s(5.0, scheme="dark")])), 2)
    # ⚠ THE PROPERTY THE WHOLE REDESIGN RESTS ON: changing only the TEXT must not change identity.
    case("the key is independent of the TEXT, so a content edit does not invalidate a baseline",
         sample_key(s(5.0, text="before")), sample_key(s(5.0, text="after a content edit")))
    case("the key is independent of COLOUR, so a PALETTE change can be compared at all",
         sample_key(s(5.0, fg="rgb(0,0,0)", bg="rgb(255,255,255)")),
         sample_key(s(5.0, fg="rgb(9,9,9)", bg="rgb(250,250,250)")))

    base = {"samples": {sample_key(s(8.0)): 8.0}}
    case("unchanged is silent", verdict([s(8.0)], base), [])
    case("improving is silent", verdict([s(12.0)], base), [])
    case("a small wobble while still PASSING is silent", verdict([s(7.9)], base), [])
    got = verdict([s(3.0)], base)
    case("crossing below AA is reported", len(got), 1)
    case("...and the message says CROSSED", "CROSSED" in (got[0] if got else ""), True)
    low = {"samples": {sample_key(s(2.0)): 2.0}}
    case("already-failing and unchanged is SILENT — this ratchets, it does not bar",
         verdict([s(2.0)], low), [])
    got2 = verdict([s(1.2)], low)
    case("...but already-failing and WORSE is reported", len(got2), 1)
    case("...and says WORSENED, not CROSSED", "WORSENED" in (got2[0] if got2 else ""), True)
    case("an already-failing element that IMPROVES is silent", verdict([s(2.6)], low), [])
    # ⚠ NOVELTY IS A STYLE, NOT A WORD. The first version of these two cases used
    # `text="brand new"` and failed once the key stopped depending on text — correctly, and the
    # red is the evidence that the redesign took effect. A new COMBINATION is a new colour.
    got3 = verdict([s(2.0, selector="body>aside")], base)
    case("a NEW failing combination is reported rather than admitted silently", len(got3), 1)
    case("...and says NEW", "NEW" in (got3[0] if got3 else ""), True)
    case("a NEW passing combination is silent", verdict([s(9.0, selector="body>aside")], base), [])
    # ⚠ A key built from the index would renumber on any edit; this one must not.
    case("the sample key is independent of ORDER",
         sample_key(s(8.0)) == sample_key(s(3.0)), True)
    case("...but distinguishes the colour scheme",
         sample_key(s(8.0, scheme="light")) != sample_key(s(8.0, scheme="dark")), True)
    case("no baseline means no verdict — a first run cannot fail", verdict([s(1.0)], None), [])

    # ── is_served_page: the corpus rule, and it took three attempts ──
    case("a page declaring a viewport is a served page",
         is_served_page('<meta name="viewport" content="width=device-width"><body>x'), True)
    case("a chromeless fragment is NOT", is_served_page("<section><p>hello</p></section>"), False)
    case("...and that is the real file the FILENAME rule missed",
         is_served_page("<style>b{color:red}</style><div>0 of 92</div>"), False)
    # ⛔ THE CASE THE SECOND RULE FAILED: a real page authored with no <html> tag.
    case("a real page with NO <html> tag is still a page, which `<html>` got wrong",
         is_served_page('<meta name="viewport" content="width=device-width"><div>real</div>'), True)
    # ⚠ AND THE ONE THAT MAKES `:root` WRONG: fragments carry palettes too.
    case("a fragment that carries its own :root palette is still a fragment",
         is_served_page("<style>:root{--fg:#000;--bg:#fff}</style><p>x</p>"), False)
    case("an empty file is not a page", is_served_page(""), False)
    case("a viewport mentioned deep in prose does not promote a fragment",
         is_served_page("<p>x</p>" + ("y" * 5000) + 'name="viewport"'), False)

    # ── summarise ──
    # ⚠ TWO DISTINCT INPUTS, because `check-fixture-variation` refused the first version of this
    # for passing `samples` one value at the only call site — a `summarise` that ignored its
    # argument would have passed. The repo's `exercise-the-producer-at-two-distinct-inputs`.
    case("summarise counts what is below ITS OWN threshold",
         summarise([s(3.0), s(9.0, text="b"), s(3.2, text="c", thr=AA_LARGE)])["below_aa"], 1)
    case("...and a different corpus gives a different answer",
         summarise([s(1.0), s(1.1, text="b")])["below_aa"], 2)
    case("...and it reports the WORST, not the first",
         summarise([s(9.0), s(1.4, text="b"), s(5.0, text="c")])["worst"], 1.4)
    case("...and counts distinct pages, not elements",
         summarise([s(9.0), s(8.0, text="b"), s(7.0, page="q.html", text="c")])["pages"], 2)

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


# ── entry point ─────────────────────────────────────────────────────────────────────────────────

def main(argv: list[str], root: Path = ROOT) -> int:
    """⛔ `root` IS DEFAULTED SO A CASE CAN DRIVE THIS OVER A WORLD IT BUILT — ADR-0014."""
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--write-baseline", metavar="PATH")
    ap.add_argument("--against", metavar="PATH")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--extra-css", metavar="PATH",
                    help="inject this stylesheet INSTEAD of the standard palette — how a "
                         "proposed change is measured BEFORE it ships")
    ap.add_argument("--raw", action="store_true",
                    help="measure the files as they sit on disk, WITHOUT the standard palette. "
                         "What a saved copy looks like, not what a reader sees")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()

    try:
        pages = corpus(root / "docs" / "explainers")
        # ⛔ THE STANDARD PALETTE BY DEFAULT, BECAUSE THAT IS WHAT A READER SEES. The pages on
        # disk do not carry it — `explainer-serve` injects it at send time, so a harness that
        # measured the bare files would be measuring a view nobody has. Backlog #221.
        # ⚠ This was NOT the first design, and the first design was wrong in the usual
        # direction: it measured the artefact rather than the rendering, which is the same
        # mistake as verifying a rule on two pages and asserting it of sixty.
        if args.extra_css:
            extra = Path(args.extra_css).read_text(encoding="utf-8")
        elif args.raw:
            extra = ""
        else:
            import page_chrome
            extra = re.sub(r"</?style>", "", page_chrome.standard_palette_css())
        samples = measure(pages, extra_css=extra)
    except CannotRun as exc:
        print(f"FAILED: {exc}")
        return 2

    sm = summarise(samples)
    print(f"contrast: {sm['elements']} text element(s) across {sm['pages']} page(s), both schemes")
    print(f"  below AA: {sm['below_aa']}   worst: {sm['worst']:.2f}:1")

    if args.write_baseline:
        out = {"samples": {sample_key(s): s["ratio"] for s in samples}, "summary": sm}
        Path(args.write_baseline).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n",
                                             encoding="utf-8")
        print(f"  baseline written: {args.write_baseline} ({len(out['samples'])} keys)")
        return 0

    if args.against:
        try:
            base = json.loads(Path(args.against).read_text(encoding="utf-8"))
        except OSError as exc:
            print(f"FAILED: baseline {args.against} cannot be read ({exc.__class__.__name__}). "
                  f"TREAT THIS AS NOT RUN.")
            return 2
        problems = verdict(samples, base)
        if problems:
            print(f"\nFAILED — {len(problems)} contrast regression(s):")
            for p in problems[:40]:
                print(f"  ✗ {p}")
            if len(problems) > 40:
                print(f"  … and {len(problems) - 40} more")
            return 1
        print("  OK — no element crossed below AA and none already failing got worse")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
