<!-- codex-review: model=gpt-5.5 -->

START HEAD: `30e5b1b98f83b03efa77c1b03309c84d62e79bc1`  
END HEAD: `30e5b1b98f83b03efa77c1b03309c84d62e79bc1`

**Findings**

Blocking / Structural: `VANISHED` turns a clean clone into a red gate for benign, intentionally ignored pages.

Premise: `.gitignore:147-161` says `dashboard.html`, `goals.html`, `backlog-table.html`, and `features.html` are derived pages that “MUST NOT BE TRACKED.” But `scripts/check-page-contrast.py:215-224` appends a `VANISHED` problem for every baselined key absent from the current run, and `scripts/check-page-contrast.py:712-718` exits `1` on any problem.

Measurement: those four ignored files are absent from `git ls-files` and show as ignored (`!!`). The committed `docs/contrast-baseline.json.gz` contains `29,950` keys from them: `backlog-table.html x21252`, `dashboard.html x5678`, `goals.html x1602`, `features.html x1418`. Simulating a clean clone by removing only those baselined keys from the current sample set produces exactly one problem: `VANISHED — 29950 baselined site(s) were not measured this run (...)`, which the gate treats as failure.

Severity reasoning: round 1 B2’s silent pass was real, but the fold traded it for an unusable local gate on the repo’s own tracked population. A fresh clone legitimately lacks these files by policy, yet cannot pass `--against docs/contrast-baseline.json.gz`.

Fix: do not baseline ignored derived pages, or regenerate them before measuring. If derived pages are intentionally optional, classify their absence separately from tracked-page vanishings and return `CANNOT RUN` or an explicit partial verdict, not a regression failure.

Blocking / Structural: gradient exclusion can hide a regression by removing a baselined site from scoring while keeping it “seen.”

Premise: `scripts/check-page-contrast.py:213-215` computes `seen` before filtering `bg_uncertain`; then `scripts/check-page-contrast.py:214` removes those samples before the crossed/worsened loop at `scripts/check-page-contrast.py:225`. The comment at `scripts/check-page-contrast.py:210-212` claims this means “excluding it cannot be used to make a baselined site disappear quietly.”

Measurement: pure reproducer with the same key before and after:

`baseline: p.html|light|body>p|16.0|400|0 = 8.0`  
`current: same key, ratio 1.0, bg_uncertain=True`  
`verdict([current], baseline) == []`

`summarise([current])` reports `elements=1`, `scored=0`, `unmeasurable=1`, `below_aa=0`.

Severity reasoning: a passing baselined text site can acquire a gradient/image background and leave the ratchet without `VANISHED`, `CROSSED`, or `WORSENED`. That is a fail-open in the exact area H2 changed.

Fix: compare scored/unscored status against the baseline. If a previously scored baselined key becomes unscored, report it as `UNMEASURABLE` and fail or `CANNOT RUN` until rebaselined deliberately.

Medium / Structural: the probe header claims selector-builder coverage that does not exist.

Premise: `scripts/page-contrast-probe.mjs:19-20` says `--self-test` exercises “opaque, the selector builder.” The self-test at `scripts/page-contrast-probe.mjs:143-153` contains ten `isOpaque(...)` cases and no selector case.

Measurement: `node scripts/page-contrast-probe.mjs --self-test` passes `10/10`; `.github/workflows/ci.yml:396-399` does run it in CI. The problem is the coverage claim, not CI wiring.

Severity reasoning: selector depth is part of `sample_key`, so this is not cosmetic. The fold says H3 is discharged, but one of the probe’s identity rules is still untested while the header says otherwise.

Fix: export/lift the selector builder and add real cases for class selection and depth, or remove the claim and state that only opacity is covered.

Low / Transitional: `--report` still scores gradient-backed samples that the summary says are not scored.

Premise: `scripts/check-page-contrast.py:279-292` excludes `bg_uncertain` samples from `below_aa` and `worst`; `scripts/check-page-contrast.py:725-731` sorts all samples by `ratio` and marks `ratio < threshold` with `✗`.

Measurement: `python3 scripts/check-page-contrast.py --report` prints summary `below AA: 211 of 65370 scored worst: 2.06:1 ⚠ 138 NOT SCORED`, then lists `✗ 1.11 / 4.5 ... 'create'` as the first worst site. That is the old gradient-backed fiction reappearing in the detail view.

Severity reasoning: the gate summary is fixed, but the human-facing report contradicts the new scoring contract.

Fix: filter `bg_uncertain` out of the worst list, or list it in a separate “unscored” section without a failure mark.

Low / Transitional: added review markdown fails whitespace check.

Premise: `docs/reviews/codex/unify-explainer-style-r1-codex.md:3-4` contain trailing spaces.

Measurement: `git diff --check 129b882b..HEAD` exits `2` and reports those two lines.

Severity reasoning: not behavioral, but it is a committed hygiene failure in the fold.

Fix: remove trailing spaces.

**Measurements That Survived**

The new headline is sound for this workspace: `--raw` gives `4,192` below AA over `65,508` measured sites; default gives `211` over the same `65,508`. Key sets match exactly, base populations match, and ordinal sets have zero differences. A repeat default run also produced identical keys and values.

Required checks run: `check-page-contrast.py --self-test` `75/75`; `explainer-serve.py --self-test` `215/215`; `page-contrast-probe.mjs --self-test` `10/10`; `check-plan-code.py --self-test` `131/131`; `check-selftest-counts.py`, `check-ratchet-contract.py`, and `check-fixture-variation.py` all passed.

NOT CONVERGED: 2 Blocking · 0 High · 1 Medium · 2 Low
