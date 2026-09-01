#!/usr/bin/env python3
"""A page's light palette must cover every token the OS-dark shim supplies.

WHY THIS EXISTS
---------------
MEASURED 2026-09-01, in Chrome, on the real dashboard. With the OS in dark mode and the page
toggled to LIGHT, hovering any page-chrome button made its label vanish: `--ink` #1b2024 on
`--card` #1d1c22 is **1.03:1**, against WCAG AA's 4.5. Both buttons, so it was the class.

No individual colour is wrong. #1d1c22 is a perfectly good dark card. The defect is a SET
DIFFERENCE:

  * `brief-compose.py` supplies 11 tokens on `html` inside `@media (prefers-color-scheme: dark)`.
    That media query keys off the OS, and a page's own `data-theme` toggle cannot override it.
    Its own comment states the intent: the shim "only supplies what nobody supplied."
  * `gen-dashboard.py`'s `light_vars` declares 17 tokens — but 8 of the shim's 11 are not among
    them. For those 8, nobody supplied a light value, so the shim's DARK value stays in force
    while the page is in light mode.

The shim is behaving exactly as documented. It is correctly answering a question the light
palette never asked.

WHY A NEW CHECK, WHEN TWO CONTRAST GUARDS ALREADY EXIST
-------------------------------------------------------
They cannot see this, and that is structural rather than an oversight:

  * `gen-dashboard.py:1290` `LINK_SURFACES = ("--bg", "--panel", "--need-bg", "--err-bg")` — no
    `--card`, so the failing `(--ink, --card)` pair is never enumerated.
  * more fundamentally, `scheme_palettes()` reads the palettes out of gen-dashboard's OWN emitted
    stylesheet, and `--card` is not defined there at all. The reader opens a page composed from
    THREE files; the guard measures one. Adding the pair would not have helped — the token it
    names is invisible at that layer.

So this check deliberately does NOT measure ratios. Contrast is already measured, twice, by
scripts that own a stylesheet. This one measures the only thing neither can: whether the two
palettes COVER the same names. A ratio check needs both colours; the whole failure here is that
one of them silently isn't there.

WHY IT IS A RATCHET AND NOT A FLAT ASSERTION
---------------------------------------------
The 8-token gap exists TODAY and fixing it is backlog #79 — a palette decision, not a mechanical
edit (7 of the 8 are latent: `--good`/`--defect` colour the sparkline bars, `--structure*` the
badges; they render dark-tuned colours on a light page, which reads as slightly-off rather than
broken). Shipping a knowingly-red gate would make CI a thing people learn to ignore. So the
measured gap is pinned in KNOWN_GAP and the check fails in three directions:

  * a NINTH token falls through          -> the class cannot grow
  * a KNOWN_GAP token becomes covered    -> the allowlist must SHRINK as #79 lands; it cannot
                                            sit there stale claiming debt that is already paid
  * KNOWN_GAP names a token the shim no  -> the allowlist cannot go fictional, which is how a
    longer defines                          pinned list quietly stops describing anything

FAILS IF
--------
  * either palette block cannot be parsed -> exit 2, CANNOT RUN. A coverage check that could not
    find a palette has NOT passed; from a green tick the two are indistinguishable.
  * any of the three ratchet directions above trips -> exit 1.

  --self-test  runs 12 cases against synthetic sources, including that each failure mode is
               DETECTED and that a bare mention of a token name does not count as a declaration.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHIM_SRC = ROOT / "scripts" / "brief-compose.py"
PAGE_SRC = ROOT / "scripts" / "gen-dashboard.py"

# MEASURED 2026-09-01 by diffing the two token sets, then confirmed live in Chrome: each of these
# reads byte-identical in both themes on the served page. Backlog #79 removes them; every removal
# must delete a line here, and this check fails if one is fixed and left behind.
# ✅ EMPTY SINCE 2026-09-01 — backlog #79 is CLOSED and all eight were fixed together, so the
# allowlist ratcheted to nothing rather than shrinking one entry at a time. That is the state this
# file was written to reach: from here, ANY shim token the light palette fails to cover is an
# immediate failure with no slack to spend.
#
# ⚠ Do not repopulate this to make a red run green. An entry here is a debt that must name why it
# is owed; the third ratchet direction below (KNOWN_GAP naming a token the shim no longer defines)
# exists because a pinned list that stops describing anything is worse than no list.
#
# ⚠ AND THE ORIGINAL TRIGGER WAS RECORDED WRONG, which is worth keeping: the report said the bug
# needed the OS in dark mode. Measured 2026-09-01 with macOS in LIGHT mode — Chrome still reported
# `prefers-color-scheme: dark` because its own Appearance setting overrides the OS for web content,
# and the defect reproduced at 1.03:1. `prefers-color-scheme` is what the BROWSER says, so this
# check must never be re-scoped to "only matters in dark mode".
KNOWN_GAP: frozenset[str] = frozenset()
KNOWN_GAP_REASON = "backlog #79 — light palette does not cover the OS-dark shim"


def shim_tokens(text: str) -> set[str]:
    """Tokens the OS-dark shim declares on `html`.

    RAISES when the block is absent. Whitespace-tolerant between `@media` and `(` because the
    sibling generators differ there and a harmless reformat must not read as an empty shim — an
    empty shim would make this check pass about nothing.
    """
    m = re.search(
        r"@media\s*\(\s*prefers-color-scheme:\s*dark\s*\)\s*\{\s*html\s*\{(.*?)\}",
        text, re.S)
    if not m:
        raise ValueError("no `@media (prefers-color-scheme: dark) { html { … } }` block found")
    return set(re.findall(r"(--[\w-]+)\s*:", m.group(1)))


def palette_tokens(text: str, name: str) -> set[str]:
    """Tokens declared by a `name = ( … )` palette assignment.

    Matches `--x:` with a colon, so a token merely NAMED in a comment or an f-string lookup is not
    counted as declared. RAISES when the assignment is absent.
    """
    m = re.search(rf"^\s*{re.escape(name)}\s*=\s*\((.*?)\)\s*$", text, re.S | re.M)
    if not m:
        raise ValueError(f"no `{name} = ( … )` assignment found")
    return set(re.findall(r"(--[\w-]+)\s*:", m.group(1)))


def audit(shim: set[str], light: set[str], known_gap: frozenset[str] = KNOWN_GAP) -> list[str]:
    """Three directions. Order is stable so failure output diffs cleanly."""
    problems: list[str] = []

    for tok in sorted((shim - light) - known_gap):
        problems.append(
            f"{tok}: declared by the OS-dark shim, never overridden by the light palette, and not "
            f"in KNOWN_GAP. In light mode this token keeps its DARK value. Give it a light value, "
            f"or add it to KNOWN_GAP with a reason.")

    for tok in sorted(known_gap & light):
        problems.append(
            f"{tok}: now covered by the light palette but still listed in KNOWN_GAP. Delete the "
            f"line — a pinned gap that is already fixed overstates the debt.")

    for tok in sorted(known_gap - shim):
        problems.append(
            f"{tok}: in KNOWN_GAP but the OS-dark shim no longer declares it. Delete the line — "
            f"the allowlist is describing a token that does not exist.")

    return problems


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    for path in (SHIM_SRC, PAGE_SRC):
        if not path.is_file():
            print(f"CANNOT RUN — {path} is missing. Treat this as NOT RUN.", file=sys.stderr)
            return 2

    try:
        shim = shim_tokens(SHIM_SRC.read_text())
        light = palette_tokens(PAGE_SRC.read_text(), "light_vars")
    except ValueError as exc:
        print(f"CANNOT RUN — {exc}. Treat this as NOT RUN.", file=sys.stderr)
        return 2

    problems = audit(shim, light)
    if problems:
        print("theme token coverage — the light palette and the OS-dark shim disagree:\n")
        for p in problems:
            print(f"  ✗ {p}")
        return 1

    print(f"theme tokens: shim declares {len(shim)}, light palette declares {len(light)}, "
          f"{len(KNOWN_GAP)} pinned in KNOWN_GAP ({KNOWN_GAP_REASON}), 0 unexplained")
    return 0


# ── self-test ───────────────────────────────────────────────────────────────────────────────────
_SHIM = """
  @media (prefers-color-scheme: dark) {
    html { --rule: #38353f; --bg: #16151a; --card: #1d1c22; --ink: #eceaf0; }
  }
"""
_LIGHT = """
    light_vars = (
        "--ink:#1b2024;--rule:#d8d6ce;--bg:#f7f8fa;")
"""


def self_test() -> int:
    cases, failures = 0, 0

    # ⚠ THE FAILURE LINE IS A CONTRACT, NOT A STYLE CHOICE. `check-plan-code.py` reads red cases by
    # taking lines that START WITH `[FAIL] ` and splitting on the LAST `": got "`. A prettier `✗`
    # form parses as ZERO red cases, so every mutation against this file would report "expect
    # matched 0 red cases" — which reads as a broken manifest rather than as a guard that works.
    # This project has already paid for that once: 12 mutations reported no red cases over exactly
    # this mismatch, masking three real bugs. Do not reformat.
    def check(label: str, got, want) -> None:
        nonlocal cases, failures
        cases += 1
        if got == want:
            print(f"  ✓ {label}")
        else:
            failures += 1
            print(f"  [FAIL] {label}: got {got!r} want {want!r}")

    def raises(fn) -> bool:
        try:
            fn()
        except ValueError:
            return True
        return False

    # ── parsing ──
    check("shim tokens parsed", shim_tokens(_SHIM), {"--rule", "--bg", "--card", "--ink"})
    check("light tokens parsed", palette_tokens(_LIGHT, "light_vars"),
          {"--ink", "--rule", "--bg"})
    check("`@media(` with no space still parses",
          shim_tokens("@media(prefers-color-scheme:dark){html{--card:#111;}}"), {"--card"})
    check("missing shim block RAISES, never returns empty",
          raises(lambda: shim_tokens("html { --card: #111 }")), True)
    check("missing palette assignment RAISES",
          raises(lambda: palette_tokens("dark_vars = ('--ink:#fff')", "light_vars")), True)
    # A token named in a comment is not a declaration. Counting mentions would let a page "cover"
    # a token by talking about it — the exact shape of a check that measures the wrong thing.
    check("a token mentioned without a colon is not declared",
          palette_tokens('light_vars = (\n  "# --card is handled elsewhere" "--ink:#000;")',
                         "light_vars"), {"--ink"})

    # ── the three ratchet directions ──
    shim = {"--card", "--ink-soft", "--ink", "--bg"}
    light_full = {"--ink", "--bg"}
    gap = frozenset({"--card", "--ink-soft"})

    check("fully explained gap passes", audit(shim, light_full, gap), [])
    check("a NINTH uncovered token fails",
          len(audit(shim | {"--newtok"}, light_full, gap)), 1)
    check("…and it names the token",
          "--newtok" in audit(shim | {"--newtok"}, light_full, gap)[0], True)
    check("a fixed token left in KNOWN_GAP fails",
          len(audit(shim, light_full | {"--card"}, gap)), 1)
    check("KNOWN_GAP naming a token the shim dropped fails",
          len(audit(shim - {"--ink-soft"}, light_full, gap)), 1)
    # The whole point: full coverage with an EMPTY allowlist is the end state #79 is aiming at.
    check("full coverage with an empty allowlist passes",
          audit(shim, shim, frozenset()), [])

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
