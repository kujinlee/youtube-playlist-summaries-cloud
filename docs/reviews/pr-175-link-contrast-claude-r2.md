# PR #175 — dual review, round 2 (Claude half)

**Subject:** `247dc12..b387fff` — the fixes for round 1's three findings, written by the same person
who wrote the original defect. **Codex half:**
[`pr-175-link-contrast-codex-r2.md`](pr-175-link-contrast-codex-r2.md) (`gpt-5.5`).

⚠ **REVIEW GAP at `4b2f2a3`, since CLOSED — see the addendum.** The independent Claude reviewer had
not returned when `4b2f2a3` was committed, so everything above that point is the coordinator's own
verification plus adjudication of Codex's finding. It returned afterwards and found two more, one of
them live. **Read the addendum before trusting the verdict line below**, which describes the state at
`4b2f2a3` and is superseded.

**Verdict at `4b2f2a3`: NOT CONVERGED — one finding, which took two attempts to fix.**
**Verdict after the addendum's fixes: CONVERGED.**

---

## Finding — the round-1 fix measured a model that did not describe the page

**Codex, High, confirmed and reproduced.** `link_contrast_errors` used a flat cross-product of
`LINK_FG × LINK_BG`. It missed `.num a{color:inherit}` — **70 of this page's links**, taking their
colour from `.num` (`--ink-3`), a variable the model never mentioned. Codex's mutation
(`.num{color:var(--ink-3)}` → `var(--line)`, **1.37:1** light / **1.30:1** dark on `--card`)
**survived at 64/64**.

**Codex's proposed fix was wrong and I did not take it.** It suggested adding `--ink-3` to the
measured foregrounds. Measured: `--ink-3` is **4.26:1 on `--ground`** and **4.22:1 on
`--pending-bg`**, both under AA — so that change reddens a *correct* page. `.num a` only ever
renders inside `.item`, whose background is `--card`, where `--ink-3` is 4.60 / 4.57 and passes.

The real defect was the **model**: a cross-product asserts pairs that never co-occur *and* misses
pairs that do. It passed only because `--structural` happens to clear AA everywhere — the model was
wrong and the data hid it. Replaced with explicit `LINK_PAIRS`.

### ⚠ The first fix for this finding was itself insufficient — measured, not reasoned

Modelling `.num a` as `"inherit"` and adding a `link_rule_drift` check over `a`-selectors **did not
catch Codex's mutation**: repointing the *parent* leaves `.num a` untouched, so drift saw nothing
and the contrast check went on measuring `--ink-3`, a variable the links no longer used. Re-ran the
reviewer's exact mutation: **still survived, 69/69.**

Fixed by modelling the inherited colour at its **source** (`LINK_INHERITS`), so the parent's own
declaration is what drift compares. Codex's mutation and a second repoint (`--line-2`) are now
caught; control green at **71/71**, 64 → 71 cases.

This is the fourth consecutive instance in this branch of *"true about the object it names, silent
about the layer around it"* — and the second where the fix for one instance introduced the next.
It was caught only because the reviewer's mutation was re-run against the fix rather than assumed to
close it.

## Verified directly (coordinator, not delegated)

- **Backlog palettes:** the block regex finds exactly **4** — `:root`, dark-media `:root`,
  `:root[data-theme="dark"]`, `:root[data-theme="light"]` — and does **not** match
  `:root[data-theme="dark"] .diff del{…}`. `--panel` and `--pending-bg` both resolve; zero
  "is undefined" rows, so nothing is being silently skipped.
- **Dashboard palettes:** both schemes parse; all **24** measured pairs clear AA, worst
  **5.64:1** (light `--link` on `--err-bg`).
- **The dashboard's cross-product is genuinely complete**, and this is checked rather than assumed:
  `grep -nE "color:inherit" scripts/gen-dashboard.py` returns **nothing**, so no dashboard link
  takes an inherited colour and there is no `.num a` equivalent to miss.
- **Every link-colouring rule on the backlog page enumerated** from the emitted CSS: `a`,
  `.qabody a`, `.rootref a`, `td.mono a` → `--structural`; `.num a` → `inherit`; `.num a:hover` →
  `--ink`; `.depmap a` + `.depmap a:hover .n` → no colour (SVG, fill-based). All nine are modelled.

## Out of scope, reported not fixed

`--ink-3` measures **4.26:1 on `--ground`** and **4.22:1 (light) / 4.40:1 (dark) on `--pending-bg`**
— under AA. It is used for body text there (`h2`, `.cnt`, `.rootref`, `.depmap figcaption`,
`.mmd > summary`). That is a **pre-existing, non-link** contrast issue on the backlog page,
untouched by this branch and not something a link-contrast guard should be widened to cover.
Filing is the user's call.

## Known gap, unchanged from round 1

The plan's **43-mutation manifest still does not cover the new cases**. `--compare .
--verify-evidence` passes at 2 files / 43 mutations / 0 survivors, and Codex independently makes the
point that this is **not** evidence the new guards are mutation-covered — the survivor it found sat
outside the manifest entirely. Backlog #70 retargets it.

## Gates

`gen-dashboard.py` 111/111 · `gen-backlog-page.py` **71/71** · `check-dashboard-entry.py` 46/46 +
5/5 · `check-plan-code.py` 121/121 · `check-docs.py` · `check-anchors.py` ·
`check-review-rounds.py` · `check-plan-code.py --compare . --verify-evidence` OK.
`gen-backlog-page.py` is not mirrored in the plan, so this round needed no plan edit.

**Not run:** `test:integration`, `test:e2e` — no TypeScript changed.

---

# ADDENDUM — the independent Claude half, received after `4b2f2a3`

**The REVIEW GAP above is now CLOSED.** The dispatched reviewer returned; it had reviewed
`b387fff`, i.e. the state *before* the round-2 fix. Its findings re-measured against `4b2f2a3`:

| Its finding | On `b387fff` | On `4b2f2a3` | Disposition |
|---|---|---|---|
| **IMPORTANT 1** — `--ink-3` (70 of 166 anchors) unmeasured; `#7a8494`→`#5a6472` = 2.88:1 | survived 64/64 | **caught** | already closed by the pair model |
| **IMPORTANT 2** — `LINK_MIN = 4.5 → 0.0` | survived | **caught** | caught only **incidentally** — now pinned explicitly |
| **IMPORTANT 2** — `CONTRAST_MIN = 4.5 → 0.0` | survived | **SURVIVED** | **real and live. Fixed here.** |
| **MINOR 1** — `@media(` vs `@media (`; raise arrives as an uncaught traceback | — | confirmed | fixed here |

**Convergent finding, independently.** It reached the same conclusion I did about `--ink-3`, by the
same route: its first pass measured against `--ground`/`--pending-bg`, got 4.26 / 4.22 / 4.40, and
it says it *"nearly filed this with wrong numbers"* before checking `.item`'s actual background and
withdrawing all three. That is exactly the correction I made when declining Codex's proposed fix.
Two reviewers and the coordinator independently walked into and out of the same trap.

## Fixed in this round

1. **`CONTRAST_MIN` had no falsifier** — a one-token edit neutered the headline assertion while the
   suite stayed green at 111/111. Now pinned, along with the sweep sets themselves, so narrowing
   `LINK_FOREGROUNDS` or `LINK_SURFACES` also fails. Backlog #69's class, fresh instance.
2. **`LINK_MIN` pinned explicitly.** It was already caught, but by a positive-assertion case that
   happens to need a non-empty result. Luck is not a guard.
3. **`scheme_palettes` is now whitespace-tolerant** (`@media\s*\(\s*…`). It previously demanded the
   exact spelling one generator emits while the sibling emits the other, so a harmless reformat
   raised. It now fails on the palette being **absent**, never on its formatting.
4. **`_safe()` wraps the eager `case` argument.** `contrast_failures` raising inside argument
   evaluation aborted the whole suite with a traceback, silently skipping every later case. A raise
   is now one failed case carrying the exception text.

## Re-measured after the fixes (control green first: 113/113 and 73/73)

`CONTRAST_MIN→0.0` **caught** · `LINK_MIN→0.0` **caught** · drop `--link-visited` from the sweep
**caught** · drop `--err-bg` from the sweep **caught** · drop the `--ink-3` pair **caught** ·
`--ink-3`→2.88:1 **caught** · genuinely deleting the dark palette block **caught cleanly** (112/113,
not a traceback) · `@media(`→`@media (` **passes**, which is now the correct outcome.

## Accepted without change

- Block regex finds exactly 4 palettes, rejects `:root[data-theme="dark"] .diff del{…}` — the
  reviewer verified this independently and reached my number.
- `--panel` **is** a real link surface on the backlog page (`.qabody`'s `p`, 17 anchors) — I had
  listed it without checking that; the reviewer confirmed it. `--line-2` is painted but carries no
  anchor today.
- Dark-overrides-light is the correct cascade model, and is *strictly better* than the count-of-2 it
  replaced: deleting the dark `--link` is now caught for the right reason (light `#1f5d8c` fails on
  the dark `--bg`) rather than by an arithmetic coincidence.
- `_raises` discards which exception fired, so a wrong-type failure reports only `got False`. Real
  but minor; left.

## Still open

**The manifest gap is now quantified: 43 mutations before, 43 after, against 17 new cases (8
dashboard, 9 backlog) — zero new mutations.** Both reviewers make the point independently:
`--verify-evidence` passing says the recorded evidence equals what the tool emits, and says nothing
about whether the contrast guards are mutation-covered. The manifest's coverage has *narrowed
relative to the suite*. Belongs on backlog #70, which already owns the coupling.

**Verdict: round 2 CONVERGED after these fixes.** Every mutation either reviewer produced is caught,
and both halves ran with a green control. A round 3 would be the first with no outstanding finding.
