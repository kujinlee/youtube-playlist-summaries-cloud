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
    python3 scripts/check-page-contrast.py --write-baseline docs/contrast-baseline.json.gz
    python3 scripts/check-page-contrast.py --against docs/contrast-baseline.json.gz
    python3 scripts/check-page-contrast.py --raw        # the files on disk, no palette
    node scripts/page-contrast-probe.mjs --self-test    # the probe's own pure predicate
    python3 scripts/check-page-contrast.py --report           # measure and print, no verdict

⚠ THE LIVE GATE IS NOT WIRED TO ANYTHING. CI runs `--self-test` only (no browser on the runner).
Nothing runs `--against` automatically — not CI, not a hook, not a script. It is a command a human
types. Round 1 M1 found an earlier comment claiming it was "listed with the other two in
docs/dev-process.md"; THERE IS NO SUCH ENTRY and the claim was invented. Until something runs it,
this guard protects nothing on its own, and saying so is the only honest state.

⛔ NOT A PASS WHEN IT CANNOT RUN. No Chromium, no pages, or a page that fails to load is rc=2 and
says TREAT THIS AS NOT RUN. A contrast gate that goes quiet when it cannot see is worse than none,
because the silence is indistinguishable from "everything is readable".

    python3 scripts/check-page-contrast.py --self-test  # 94 cases
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import subprocess
import tempfile
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

    ⛔ IT MUST NOT CONTAIN A COLOUR, and two earlier versions got this wrong in opposite ways.
    Keyed on element TEXT, one page produced 10,626 rows and any content edit invalidated the
    baseline. Keyed on (fg, bg, size, weight) it was compact and stable — until the first real
    use, a palette change, altered every fg and bg so NO key matched and 196 affected sites were
    reported as "NEW" instead of compared. A baseline keyed on the thing under test cannot
    measure a change to that thing.

    ⛔⛔ AND IT MUST DISTINGUISH SIBLINGS, which is round 1's H1 and was Blocking. Page + scheme
    + selector path + size + weight collapsed `Copy` (2.221:1) and `Close` (5.492:1) — two
    buttons with the same ancestry — onto ONE key. `collapse` kept the worse, so `Close` could
    crash from passing to 3.0:1 and the verdict would see no change at all. Measured: 4,410
    duplicate keys in this corpus and 25 of them already mix a passing and a failing site, so
    the masking surface was real and not hypothetical.
    ⤳ `ordinal` is the site's index among its duplicate-key siblings, assigned in document
    order by `collapse`. It is stable under a palette change (which is the point), and under a
    content edit it shifts only for siblings AFTER an insertion — a far smaller blast radius
    than keying on text, which the first version paid for.
    """
    return (f"{s['page']}|{s['scheme']}|{s['selector']}|{s['px']:.1f}|{int(s['weight'])}"
            f"|{s.get('ordinal', 0)}")


def collapse(rows: list[dict]) -> list[dict]:
    """PURE. Measured elements -> one sample per SITE, siblings kept apart by ordinal.

    ⛔ THE PREVIOUS VERSION'S DOCSTRING CLAIMED it "can over-report a regression, never hide
    one". That was FALSE and round 1 refuted it with a real pair from this corpus. Siblings
    sharing a selector path were merged and only the worst ratio survived, so a passing sibling
    could cross below AA invisibly behind a failing one.

    Now each element gets an `ordinal` within its (page, scheme, selector, px, weight) group, so
    siblings stay distinct and the earlier guarantee is finally true — because nothing is merged
    away. `instances` stays 1 and is kept for message compatibility.
    """
    counter: dict[str, int] = {}
    out: list[dict] = []
    for r in rows:
        base = f"{r['page']}|{r['scheme']}|{r['selector']}|{r['px']:.1f}|{int(r['weight'])}"
        n = counter.get(base, 0)
        counter[base] = n + 1
        out.append({**r, "ordinal": n, "instances": 1})
    return out


def coverage(samples: list[dict], baseline: dict | None) -> tuple[int, int, list[str]]:
    """PURE. -> (baselined sites measured this run, baselined sites total, the ones missed).

    ⛔ ONE COMPUTATION, TWO READERS — round 3 HIGH 1. The advisory and the success line are
    statements about the same population, and before this they derived it separately: the
    advisory counted what vanished and the verdict line counted nothing at all, so a green
    verdict sat directly beneath "29,950 sites were not measured" and read as whole-corpus.
    A second derivation of the same set is the shape this repository has measured drifting
    seventeen times; here the two did not even disagree, because only one of them existed.
    """
    if baseline is None:
        return (0, 0, [])
    seen = {sample_key(s) for s in samples}
    total = set(baseline.get("samples", {}))
    missed = sorted(total - seen)
    return (len(total & seen), len(total), missed)


def population_notes(samples: list[dict], baseline: dict | None) -> list[str]:
    """PURE. -> ADVISORY notes about the measured population. Never fatal.

    ⛔ SEPARATED FROM `verdict` BECAUSE THE COMMENT CLAIMED IT ALREADY WAS. Round 2's B1: the
    VANISHED check was appended to the same list `main()` fails on, while a comment beside it
    said "deliberately not fatal on its own… The caller decides". There was no such mechanism,
    and the consequence was measured — on a clean `git archive` the gate reported 29,950
    vanished sites and exited 1. The gate was RED ON EVERY CLEAN CLONE.
    ⚠ Four of the 60 served pages are DERIVED and gitignored (`backlog-table`, `dashboard`,
    `features`, `goals`), and after the sibling-split they are 45.7% of the baseline. A fresh
    clone legitimately lacks them. Failing on that is not rigour, it is a gate nobody can keep
    green — which `docs/backlog.md` #56 measured getting switched off.
    """
    if baseline is None:
        return []
    _measured, _total, vanished = coverage(samples, baseline)
    if not vanished:
        return []
    by_page: dict[str, int] = {}
    for k in vanished:
        by_page[k.split("|")[0]] = by_page.get(k.split("|")[0], 0) + 1
    where = ", ".join(f"{p} x{n}" for p, n in sorted(by_page.items(), key=lambda kv: -kv[1])[:5])
    return [f"{len(vanished)} baselined site(s) were not measured this run ({where}). "
            f"A site that is gone is not a site that improved — but a derived page absent from "
            f"a fresh clone is not a regression either, so this is ADVISORY."]


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
    # ⚠ THE VANISHED CHECK LIVES IN `population_notes`, NOT HERE — round 2's B1. It is
    # advisory, and putting it in this list made the gate red on every clean clone.
    # ⛔ BUT A SITE THAT STOPPED BEING SCORED IS NOT ADVISORY, and that is round 2's H1: the
    # gradient exclusion removed such sites from `samples` entirely, so a baselined site at
    # 8.0 crashing to 2.0 reported CROSSED while the same site with an image background
    # reported NOTHING. It did not vanish — it left the verdict. Reported here.
    unscored = [s for s in samples if s.get("bg_uncertain") and sample_key(s) in prior]
    for s in unscored:
        problems.append(
            f"NO LONGER SCORED: {s['page']} [{s['scheme']}] {s['text'][:50]!r} was baselined at "
            f"{prior[sample_key(s)]:.2f} and now sits on a gradient or image, so no ratio can be "
            f"computed. A site leaving the verdict is not a site that improved.")
    samples = [s for s in samples if not s.get("bg_uncertain")]
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


def baseline_payload(samples: list[dict], summary: dict) -> dict:
    """PURE. -> what gets written as a baseline.

    ⛔ EXTRACTED SO A CASE CAN DRIVE THE REAL RULE. The first case for the gradient exclusion
    asserted a dict comprehension written inside the case itself — a copy — so severing the
    shipped one left the suite green and the mutation SURVIVED. Second time in one day that a
    test exercised a duplicate of the thing it was named for.
    """
    return {"samples": {sample_key(s): s["ratio"]
                        for s in samples if not s.get("bg_uncertain")},
            "summary": summary}


def load_baseline(path: Path) -> dict:
    """Read a baseline, gzipped or plain. PURE apart from the one read.

    ⛔ GZIPPED BECAUSE THE HONEST BASELINE IS BIG. Round 1's H1 fix stopped merging siblings, so
    the corpus went from 6,664 collapsed groups to 65,508 individual sites — 5.16 MB of JSON,
    rewritten on every style change. Gzip takes that to **0.20 MB with no fidelity lost**, which
    is why there is no threshold here: the alternative considered was keeping only sites below
    some ratio, and that is a judgement about how far a future change might move a colour. A
    26x win needs no such guess.
    """
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))


def dump_baseline(obj: dict, path: Path) -> int:
    """Write a baseline gzipped. -> bytes written."""
    blob = gzip.compress(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode(), 9)
    path.write_bytes(blob)
    return len(blob)


def summarise(samples: list[dict]) -> dict:
    """PURE. -> the headline numbers, so a report cannot disagree with its own detail.

    ⛔ GRADIENT-BACKED SITES ARE COUNTED BUT NOT SCORED — round 1 H2. Their ratio is computed
    against whatever opaque colour lies beneath an image, which is not what a reader sees; the
    old published `worst: 1.107` was one such site. Reporting them as unmeasurable is honest;
    folding them into `worst` was not.
    """
    scored = [s for s in samples if not s.get("bg_uncertain")]
    below = [s for s in scored if s["ratio"] < s["threshold"]]
    return {
        "elements": len(samples),
        "scored": len(scored),
        "unmeasurable": len(samples) - len(scored),
        "pages": len({s["page"] for s in samples}),
        "below_aa": len(below),
        "worst": min((s["ratio"] for s in scored), default=float("nan")),
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

    ⚠ THE PROBE HOLDS DECISION RULES — what is visible, what counts as opaque, which ancestor
    supplies the background, how deep a selector path goes, what a gradient means. Round 1 (H3)
    counted seven and round 2 (B2) found this SECOND copy of the false claim still standing
    after the first was corrected: fixing one site of a repeated sentence is the instance, not
    the class. What is true: every threshold and every VERDICT is pure Python above, cased
    without a browser, and the probe's `opaque` predicate is single-source and self-tested.
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
                # ⛔ round 1 H2: text over a gradient or image has NO single background colour.
                # The ratio above is computed against whatever opaque colour sits beneath, which
                # is not what a reader sees — the corpus's old `worst: 1.107` was exactly that.
                "bg_uncertain": bool(raw.get("bgImage")),
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

    # a gradient-backed variant of the same site — its ratio is not a fact about what a
    # reader sees, so it must never be scored, and must never be a hiding place either.
    def g(ratio, **kw):
        d = s(ratio, **kw); d["bg_uncertain"] = True; return d

    # ── collapse: elements -> sites, siblings kept APART ──
    # ⛔ ROUND 1 H1 WAS BLOCKING AND THIS IS THE REPAIR. The previous version merged siblings
    # sharing a selector path and kept the worst ratio, so a PASSING sibling could cross below
    # AA invisibly behind a failing one. Real pair from this corpus:
    #     …|dark|div.in>div.trow>button|13.1|400  ->  'Copy' 2.221  and  'Close' 5.492
    case("siblings sharing a selector path stay DISTINCT, they are not merged",
         len(collapse([s(5.0, text="a"), s(5.0, text="b"), s(5.0, text="c")])), 3)
    case("...and are numbered in document order, so the numbering is reproducible",
         [r["ordinal"] for r in collapse([s(5.0), s(5.0), s(5.0)])], [0, 1, 2])
    # ⭐ THE MASKING CASE ITSELF, with the measured pair. Before the fix these collapsed to one
    # sample at 2.221 and `Close` could crash to 3.0 unseen.
    _mask = collapse([s(2.221, text="Copy"), s(5.492, text="Close")])
    case("the Copy/Close pair that proved the masking now yields TWO samples", len(_mask), 2)
    case("...and the passing sibling keeps its own ratio rather than the worse one",
         sorted(r["ratio"] for r in _mask), [2.221, 5.492])
    case("...so their keys differ and a regression on either is visible",
         sample_key(_mask[0]) != sample_key(_mask[1]), True)
    # ⛔ AND THE PROPERTY THE ORDINAL MUST NOT BREAK: a palette change alters every colour, and
    # the keys must still line up or the baseline cannot compare anything. Same sites, new
    # colours, same key sequence.
    _before = collapse([s(5.0, fg="rgb(0,0,0)"), s(6.0, fg="rgb(0,0,0)", text="b")])
    _after = collapse([s(4.4, fg="rgb(9,9,9)"), s(5.1, fg="rgb(9,9,9)", text="b")])
    case("a palette change leaves every key unchanged, which is what makes a baseline work",
         [sample_key(r) for r in _before], [sample_key(r) for r in _after])
    case("a different SELECTOR is a different site",
         len({sample_key(r) for r in collapse([s(5.0), s(5.0, selector="body>h1")])}), 2)
    case("the same site on a different PAGE stays separate",
         len({sample_key(r) for r in collapse([s(5.0), s(5.0, page="q.html")])}), 2)
    case("...and in a different SCHEME",
         len({sample_key(r) for r in collapse([s(5.0), s(5.0, scheme="dark")])}), 2)
    case("the key is independent of the TEXT, so a content edit does not invalidate a baseline",
         sample_key(s(5.0, text="before")), sample_key(s(5.0, text="after a content edit")))
    case("the key is independent of COLOUR, so a PALETTE change can be compared at all",
         sample_key(s(5.0, fg="rgb(0,0,0)", bg="rgb(255,255,255)")),
         sample_key(s(5.0, fg="rgb(9,9,9)", bg="rgb(250,250,250)")))

    # ── the VERDICT's own cases ──
    # ⛔ THIS WHOLE BLOCK WAS DELETED BY A CARELESS SPLICE while fixing H1, and the suite then
    # reported "47/47 passed" over a gate whose entire verdict logic had become untested. The
    # only thing that noticed was the declared-count mismatch. Restored, and recorded here
    # because "the tests still pass" was true and worthless at that moment.
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
    case("an already-failing site that IMPROVES is silent", verdict([s(2.6)], low), [])
    # ⚠ THE BASELINED SITE IS KEPT IN EACH RUN BELOW — omit it and the run no longer measures
    # it, which is now correctly reported as VANISHED.
    got3 = verdict([s(8.0), s(2.0, selector="body>aside")], base)
    case("a NEW failing site is reported rather than admitted silently", len(got3), 1)
    case("...and says NEW", "NEW" in (got3[0] if got3 else ""), True)
    case("a NEW passing site is silent", verdict([s(8.0), s(9.0, selector="body>aside")], base), [])
    case("no baseline means no verdict — a first run cannot fail", verdict([s(1.0)], None), [])

    # ── the baseline's own encoding ──
    # ⛔ A ROUND TRIP IS NOT A DETAIL HERE: the baseline IS the gate's memory, and a lossy or
    # unreadable one fails silently as "everything improved". 5.16 MB plain -> 0.20 MB gzipped.
    import tempfile as _tf
    with _tf.TemporaryDirectory() as _td:
        _obj = {"samples": {"a|light|body>p|16.0|400|0": 4.321}, "summary": {"below_aa": 1}}
        _gz = Path(_td) / "b.json.gz"
        dump_baseline(_obj, _gz)
        case("a gzipped baseline round-trips EXACTLY — ratios included", load_baseline(_gz), _obj)
        case("...and is actually compressed, not just renamed", _gz.read_bytes()[:2], b"\x1f\x8b")
        # ⚠ PLAIN JSON MUST STILL READ. A baseline written before this change, or by hand, is
        # not a reason to report that every site vanished.
        _plain = Path(_td) / "b.json"
        _plain.write_text(json.dumps(_obj), encoding="utf-8")
        case("a PLAIN json baseline still reads, so an older one is not silently empty",
             load_baseline(_plain), _obj)
        # ⛔ A SECOND, DISTINCT OBJECT AND PATH — `check-fixture-variation` refused the first
        # version for passing `dump_baseline` one object at one path, so a `dump_baseline` that
        # ignored both arguments and wrote a constant would have passed. Third time this guard
        # has caught that shape in one day.
        _obj2 = {"samples": {"z|dark|body>h1|24.0|700|3": 19.9}, "summary": {"below_aa": 0}}
        _gz2 = Path(_td) / "other.json.gz"
        dump_baseline(_obj2, _gz2)
        case("a DIFFERENT baseline round-trips to its own content, not the first one's",
             load_baseline(_gz2), _obj2)
        case("...and lands at the path it was given, not a remembered one",
             (_gz2.exists(), load_baseline(_gz) == _obj), (True, True))

    # ── a key that VANISHES — ADVISORY, and round 2's B1 is why it is not fatal ──
    # ⛔ Measured before the split: on a clean `git archive` the gate reported 29,950 vanished
    # sites and exited 1 — RED ON EVERY CLEAN CLONE — while a comment beside it claimed the
    # check was "deliberately not fatal… The caller decides". There was no such mechanism.
    # Four of the 60 pages are derived and gitignored, and after the sibling split they are
    # 45.7% of the baseline; a fresh clone legitimately lacks them.
    gone = population_notes([], base)
    case("a baselined site NOT measured this run is reported", len(gone), 1)
    case("...and names the page, so a derived artefact is distinguishable from a deletion",
         "p.html" in (gone[0] if gone else ""), True)
    case("...and says ADVISORY, because a fresh clone legitimately lacks derived pages",
         "ADVISORY" in (gone[0] if gone else ""), True)
    case("...while a run that measures everything says nothing",
         population_notes([s(8.0)], base), [])
    case("no baseline means no population note either", population_notes([], None), [])
    # ⛔⛔ AND THE PART THAT IS **NOT** ADVISORY — round 2's H1. The gradient exclusion removed
    # baselined sites from the verdict entirely, so one crashing 8.0 -> 2.0 reported NOTHING
    # while an identical non-gradient site reported CROSSED. Leaving the verdict is not
    # improving, and `verdict` — not `population_notes` — must say so.
    _left = verdict([g(2.0)], base)
    case("a BASELINED site that becomes gradient-backed is reported, not silently dropped",
         len(_left), 1)
    case("...and says NO LONGER SCORED", "NO LONGER SCORED" in (_left[0] if _left else ""), True)
    case("...and quotes the ratio it used to have, so the reader can judge",
         "8.00" in (_left[0] if _left else ""), True)
    # ⚠ A gradient-backed site that was NEVER baselined is not a finding — just unscorable.
    case("an UNBASELINED gradient-backed site is silent",
         verdict([s(8.0), g(1.0, selector="body>aside")], base), [])
    # ⛔ AND THAT IS WHY THEY ARE NEVER BASELINED. Writing a gradient-backed site into the
    # baseline makes it permanently "baselined and now unscored" — measured on a clean clone,
    # 103 sites reporting NO LONGER SCORED while nothing about them had changed.
    case("...so re-running over the same corpus reports nothing about it",
         verdict([s(8.0), g(1.1, selector="body>figure")],
                 baseline_payload([s(8.0), g(1.1, selector="body>figure")], {})), [])

    # ── is_served_page: the corpus rule, and it took three attempts ──
    # ⛔ THIS BLOCK WAS DELETED BY THE SAME CARELESS SPLICE that ate the verdict cases, and
    # unlike those it was not noticed until a MUTATION SURVIVED — `is_served_page -> True` left
    # the suite green because nothing cased it any more. Two blocks lost to one bad slice; I
    # restored the first and never checked for a second.
    case("a page declaring a viewport is a served page",
         is_served_page('<meta name="viewport" content="width=device-width"><body>x'), True)
    case("a chromeless fragment is NOT", is_served_page("<section><p>hello</p></section>"), False)
    case("...and that is the real file the FILENAME rule missed",
         is_served_page("<style>b{color:red}</style><div>0 of 92</div>"), False)
    case("a real page with NO <html> tag is still a page, which `<html>` got wrong",
         is_served_page('<meta name="viewport" content="width=device-width"><div>real</div>'), True)
    case("a fragment that carries its own :root palette is still a fragment",
         is_served_page("<style>:root{--fg:#000;--bg:#fff}</style><p>x</p>"), False)
    case("an empty file is not a page", is_served_page(""), False)
    case("a viewport mentioned deep in prose does not promote a fragment",
         is_served_page("<p>x</p>" + ("y" * 5000) + 'name="viewport"'), False)

    # ── the baseline payload, driven as the REAL function ──
    _pay = baseline_payload([s(8.0), g(1.1, selector="body>figure")], {"below_aa": 0})
    case("a gradient-backed site is NOT written into the baseline", len(_pay["samples"]), 1)
    case("...and the scored one IS", sample_key(s(8.0)) in _pay["samples"], True)
    case("...and the summary rides along", _pay["summary"], {"below_aa": 0})
    # ⚠ A SECOND, DISTINCT SAMPLE SET — `check-fixture-variation` refused the first version for
    # passing `baseline_payload` one list at both call sites, so a version ignoring its argument
    # would have passed. FOURTH time this guard has caught that exact shape today, each time in
    # a function written minutes earlier. The blind spot is "one call site", not any one rule.
    _pay2 = baseline_payload([g(2.2), g(3.3, selector="body>aside")], {"below_aa": 7})
    case("a set of ONLY gradient-backed sites yields an empty baseline", _pay2["samples"], {})
    case("...and still carries its own summary, not the other call's",
         _pay2["summary"], {"below_aa": 7})

    # ── summarise ──
    # ⚠ TWO DISTINCT INPUTS, because `check-fixture-variation` refused the first version of this
    # for passing `samples` one value at the only call site — a `summarise` that ignored its
    # argument would have passed. The repo's `exercise-the-producer-at-two-distinct-inputs`.
    # ⛔ GRADIENT-BACKED SITES ARE COUNTED BUT NOT SCORED — round 1 H2, and the mutation that
    # reverts this SURVIVED until these cases existed. The corpus's old `worst: 1.107` was one
    # such site: text on a `repeating-linear-gradient`, scored against the cream beneath it.
    case("a gradient-backed site is not counted as below AA, however bad its nominal ratio",
         summarise([g(1.1), s(9.0, selector="body>h1")])["below_aa"], 0)
    case("...and is excluded from WORST, which is where the fiction used to surface",
         summarise([g(1.1), s(9.0, selector="body>h1")])["worst"], 9.0)
    case("...but is still COUNTED, and reported as unmeasurable rather than hidden",
         (summarise([g(1.1), s(9.0)])["elements"], summarise([g(1.1), s(9.0)])["unmeasurable"]),
         (2, 1))
    case("...and an ordinary site is still scored normally beside it",
         summarise([g(1.1), s(3.0, selector="body>h1")])["below_aa"], 1)
    # ⚠ AND IT MUST NOT BECOME A HIDING PLACE: a baselined site that turns up gradient-backed
    # still counts as MEASURED, so it cannot be used to make a key vanish quietly.
    _b = {"samples": {sample_key(s(8.0)): 8.0}}
    case("a site that becomes gradient-backed does NOT read as vanished",
         any("VANISHED" in x for x in verdict([g(8.0)], _b)), False)

    case("summarise counts what is below ITS OWN threshold",
         summarise([s(3.0), s(9.0, text="b"), s(3.2, text="c", thr=AA_LARGE)])["below_aa"], 1)
    case("...and a different corpus gives a different answer",
         summarise([s(1.0), s(1.1, text="b")])["below_aa"], 2)
    case("...and it reports the WORST, not the first",
         summarise([s(9.0), s(1.4, text="b"), s(5.0, text="c")])["worst"], 1.4)
    case("...and counts distinct pages, not elements",
         summarise([s(9.0), s(8.0, text="b"), s(7.0, page="q.html", text="c")])["pages"], 2)

    # ─── coverage(): the denominator the verdict line was missing (round 3 HIGH 1) ──────
    # ⚠ `samples` AND `root` BOTH VARY ACROSS CALL SITES. `check-fixture-variation` refused the
    # first draft: five calls passing one `_s` make the parameter indistinguishable from a
    # constant, so no case could tell a clause that READS it from one that ignores it. It
    # caught the same mistake twice in one session, which is the point of having it.
    _s1 = [{"page": "a.html", "scheme": "light", "selector": "p", "px": 16.0, "weight": 400,
            "text": "x", "ratio": 9.0, "threshold": 4.5}]
    _s2 = [{"page": "b.html", "scheme": "dark", "selector": "h2", "px": 24.0, "weight": 700,
            "text": "y", "ratio": 7.1, "threshold": 3.0}]
    _k1, _k2 = sample_key(_s1[0]), sample_key(_s2[0])

    case("coverage with no baseline measures nothing and claims nothing",
         coverage(_s1, None), (0, 0, []))
    case("a baseline whose every site was measured reports full coverage",
         coverage(_s2, {"samples": {_k2: {}}})[:2], (1, 1))
    case("...and names nothing as missed",
         coverage(_s1, {"samples": {_k1: {}}})[2], [])
    # ⭐ THE CASE THAT WOULD HAVE CAUGHT THE DEFECT: a baseline holding sites this run did not
    # measure must report PARTIAL coverage and name them. The old code reported neither.
    case("a baseline with unmeasured sites reports partial coverage",
         coverage(_s2, {"samples": {_k2: {}, "gone.html|light|y": {}}})[:2], (1, 2))
    case("...and names exactly the ones missed",
         coverage(_s1, {"samples": {_k1: {}, "gone.html|light|y": {}}})[2], ["gone.html|light|y"])
    # a DIFFERENT samples list against the SAME baseline must change the answer — the pair is
    # what proves the parameter is read rather than ignored.
    case("a run that measured none of the baseline reports zero coverage",
         coverage(_s2, {"samples": {_k1: {}}})[:2], (0, 1))
    case("population_notes agrees with coverage about how many were missed",
         ("2 baselined site(s)" in (population_notes(
             _s1, {"samples": {_k1: {}, "g1|light|y": {}, "g2|light|z": {}}}) or [""])[0]), True)

    # ─── ADR-0014 rule D2: a case DRIVES main() over a world it built ───────────────────
    # ⛔ THIS CASE REFUTES A PIN ADDED AN HOUR EARLIER. `check-page-contrast.py` was put in
    # `MAIN_DEBT` on the reasoning that driving `main()` needs node and a browser. Round 3
    # refuted it by RUNNING it: over an empty constructed world `main()` returns 2 — the file's
    # own CANNOT-RUN contract, an advertised outcome — with no node and no browser.
    with tempfile.TemporaryDirectory() as _tdA, tempfile.TemporaryDirectory() as _tdB:
        _rootA, _rootB = Path(_tdA), Path(_tdB)
        for _r in (_rootA, _rootB):
            (_r / "docs" / "explainers").mkdir(parents=True)
            (_r / "scripts").mkdir()
        case("main() over an EMPTY constructed world refuses with the CANNOT-RUN code",
             main([], root=_rootA), 2)
        # a SECOND, distinct world — so `root` is not a constant to the suite either, and the
        # refusal is shown to be about the world rather than about one particular path.
        case("...and --raw over a DIFFERENT empty world refuses identically",
             main(["--raw"], root=_rootB), 2)

    print(f"\n{ok}/{ok + fail} self-test cases passed")

    return 1 if fail else 0


# ── entry point ─────────────────────────────────────────────────────────────────────────────────

def main(argv: list[str], root: Path = ROOT) -> int:
    """⛔ `root` IS DEFAULTED SO A CASE CAN DRIVE THIS OVER A WORLD IT BUILT — ADR-0014."""
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--write-baseline", metavar="PATH")
    ap.add_argument("--against", metavar="PATH")
    ap.add_argument("--report", action="store_true",
                    help="also list the worst sites, so a human can see WHICH text is failing "
                         "rather than only how many do")
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
    # ⚠ "sites", not "elements x schemes" — round 1 L1. Each sample is ONE (page, scheme, site)
    # triple, so "6,664 across 60 pages, both schemes" read as 13,328 to a reasonable reader.
    print(f"contrast: {sm['elements']} measured site(s) (page x scheme x element) "
          f"across {sm['pages']} page(s)")
    print(f"  below AA: {sm['below_aa']} of {sm['scored']} scored   worst: {sm['worst']:.2f}:1"
          + (f"   ⚠ {sm['unmeasurable']} NOT SCORED (text over a gradient or image — no single "
             f"background colour exists, so any ratio would be fiction)"
             if sm["unmeasurable"] else ""))

    if args.write_baseline:
        # ⛔ GRADIENT-BACKED SITES ARE NOT BASELINED, and leaving them in made round 2's H1 fix
        # fire on all 103 of them forever. Their stored ratio is the fiction H2 removed from the
        # verdict; baselining it means every such site is permanently "baselined and now
        # unscored". Only a site that LATER becomes gradient-backed is the thing H1 guards.
        # ⚠ Found by running the gate on a clean `git archive`, not by reading the fix.
        out = baseline_payload(samples, sm)
        n = dump_baseline(out, Path(args.write_baseline))
        print(f"  baseline written: {args.write_baseline} "
              f"({len(out['samples'])} keys, {n/1048576:.2f} MB gzipped)")
        return 0

    if args.against:
        try:
            base = load_baseline(Path(args.against))
        except OSError as exc:
            print(f"FAILED: baseline {args.against} cannot be read ({exc.__class__.__name__}). "
                  f"TREAT THIS AS NOT RUN.")
            return 2
        for note in population_notes(samples, base):
            print(f"  ⚠ ADVISORY — {note}")
        problems = verdict(samples, base)
        if problems:
            print(f"\nFAILED — {len(problems)} contrast regression(s):")
            for p in problems[:40]:
                print(f"  ✗ {p}")
            if len(problems) > 40:
                print(f"  … and {len(problems) - 40} more")
            return 1
        # ⛔ THE SUCCESS LINE CARRIES ITS OWN COVERAGE — round 3 HIGH 1. It used to say only
        # "no element crossed below AA", printed directly beneath an ADVISORY reporting that
        # 29,950 of 66,732 baselined sites were not measured. MEASURED: that green covered
        # 55.1% of its own baseline, and regenerating the four gitignored derived pages made
        # the identical command exit 1 with ten NEW below-AA sites.
        # ⚠ A verdict that omits its denominator is read as whole-corpus by every reader
        # INCLUDING THE ONE WHO WROTE IT: the coordinator quoted this line as proof that a fold
        # was verified while the advisory sat two lines above it in the same output. The
        # docstring of `population_notes` even states the derived pages are 45.7% of the
        # baseline — the number was known and simply never reached the verdict.
        _measured, _total, _missed = coverage(samples, base)
        _cov = (f"{_measured / _total * 100:.1f}% of baseline ({_measured} of {_total} site(s))"
                if _total else "no baseline")
        print(f"  OK over {_cov} — no element crossed below AA and none already failing got worse")
        if _missed:
            print(f"  \u26a0 NOT A WHOLE-CORPUS PASS: {len(_missed)} baselined site(s) were not "
                  f"measured (see the ADVISORY above). Regenerate the derived pages and re-run.")
        return 0

    # ⚠ `--report` WAS A DECLARED NO-OP — round 1 L2. The flag was documented in the usage block
    # and parsed, and did nothing at all; a reader who passed it got the summary they would have
    # got anyway. A documented switch that does nothing is a false claim with a help string.
    if args.report:
        # ⚠ SCORED SITES ONLY — round 2's M1. The first version sorted ALL samples, so its top
        # line was `1.11 … 'create'`, the gradient-backed fiction H2 had just excluded, printed
        # two lines under a `worst: 2.06` that correctly excluded it. A report contradicting its
        # own summary teaches the reader to trust neither.
        worst = sorted((x for x in samples if not x.get("bg_uncertain")),
                       key=lambda s: s["ratio"])[:25]
        print("\n  worst sites (ratio, threshold, scheme, page, text):")
        for s in worst:
            flag = "✗" if s["ratio"] < s["threshold"] else " "
            print(f"  {flag} {s['ratio']:>6.2f} / {s['threshold']:<4} [{s['scheme']:<5}] "
                  f"{s['page'][:46]:<48} {s['text'][:42]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
