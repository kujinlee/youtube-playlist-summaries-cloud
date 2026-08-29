# PR #175 — dual review, round 2 (Claude half)

**Subject:** `247dc12..b387fff` — the fixes for round 1's three findings, written by the same person
who wrote the original defect. **Codex half:**
[`pr-175-link-contrast-codex-r2.md`](pr-175-link-contrast-codex-r2.md) (`gpt-5.5`).

⚠ **REVIEW GAP: the independent Claude reviewer dispatched for this round had not returned at
commit time.** This half is the coordinator's own verification plus adjudication of Codex's finding.
It is weaker than round 1's independent pass and is recorded as such. Round 3 should re-run it.

**Verdict: NOT CONVERGED at round 2. One finding, which took two attempts to fix.**

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
