<!-- codex-review: model=gpt-5.5 -->

START HEAD: `129b882b5b8958153621a2c87d3b3c5a372aabb9`  
END HEAD: `129b882b5b8958153621a2c87d3b3c5a372aabb9`  
HEAD unchanged.

**Findings**

Blocking / Structural: The committed baseline measures files that are explicitly ignored, and the ratchet silently passes when those files disappear.

Premise: `docs/contrast-baseline.json:6668` reports `"elements": 6664`, `"pages": 60`, `"below_aa": 100`; `.gitignore:147-161` says the standing pages are derived and ignored; `scripts/check-page-contrast.py:187-213` only iterates current samples and never checks for baseline keys missing from the current run.

Measurement: current dirty workspace reproduces `486 -> 100` over `6664` samples. A clean `git archive HEAD` with the same probe and same HEAD scripts gives `418 -> 93` over `6168` samples / `56` pages. The committed baseline contains `496` keys for ignored standing pages (`backlog-table.html`, `dashboard.html`, `features.html`, `goals.html`). In that same clean archive, `python3 scripts/check-page-contrast.py --against docs/contrast-baseline.json` exits 0: “OK — no element crossed below AA...” despite those 496 baseline samples being absent. A pure check also confirms `verdict([], baseline_with_sample) == []`.

Severity: this makes both the headline number and the ratchet population non-reproducible from the branch under review. A selector/corpus change, ignored generated output missing in a checkout, or accidental page disappearance can remove previously baselined failures without any warning.

Proposed fix: store and compare the measured population. Fail or CANNOT-RUN when baseline keys/pages are missing unless explicitly acknowledged in a separate migration. Either commit the standing-page artifacts used by the baseline, regenerate them as part of the measurement, or exclude them from the committed baseline.

Blocking / Structural: `sample_key` plus `collapse` can hide a real crossing regression.

Premise: `scripts/check-page-contrast.py:145-147` claims keeping the worst ratio “can over-report a regression, never hide one”; `scripts/check-page-contrast.py:149` excludes color from identity; `scripts/check-page-contrast.py:167-171` keeps only the minimum ratio for duplicate keys.

Measurement: I collected raw rows under the injected palette. There are `4410` duplicate keys, and `25` keys already mix passing and failing color pairs under the same key. Example: `2026-08-24-findings-slice-a-file-or-not.html|dark|div.in>div.trow>button|13.1|400` has `Copy` at `2.221:1` and `Close` at `5.492:1`. If `Close` regresses to `3.0:1`, the collapsed key remains `2.221`, so `verdict()` sees no worsening even though a passing element crossed below AA.

Severity: this is exactly the ratchet’s core promise, and the failure is not hypothetical. The current corpus already has the mixed-key shape needed to mask a regression.

Proposed fix: keep per-instance identity stable enough to distinguish siblings that can have different color outcomes. Options: include a stable child index among same selector path, include normalized text only as a disambiguator for duplicate-key groups, or store all ratios per key and compare the multiset conservatively.

High / Transitional: The claimed remaining regressions are token-reachable, not page-local literals.

Premise: `scripts/page_chrome.py:65-70` says the pages share a token vocabulary and the palette overrides values; `scripts/page_chrome.py:84-130` defines standard aliases, but not `--ink3`.

Measurement: comparing raw-before to injected-after with the same probe gives `23` worsened already-failing samples, not `14`, all `4.339 -> 4.152` in light mode. The affected pages define `--ink3:#7d766c` and use it for the worsened text, e.g. `docs/explainers/2026-08-12-explanation-sidebar-refresh-after-ingest-49045e5.html:9`, `:120`, `:181`, `:185`; same pattern at `docs/explainers/2026-08-12-explanation-verify-counts-delete-anchor-995d7e4.html:9`, `:99`, `:134`; `docs/explainers/2026-08-13-explanation-m3-1-cloud-e2e-70f7ab1.html:9`, `:141`; `docs/explainers/2026-08-13-explanation-money-guard-review-a45e375.html:9`, `:134`.

Severity: these are still below AA and got worse because the injected palette changes `--bg` while leaving a local faint-ink token in place. That is not unreachable by tokens; it is a missing alias in the unification palette.

Proposed fix: add `--ink3` to the standard palette, or map it intentionally to the corrected faint token. Then rerun the raw-before vs injected-after comparison and make the count part of the report.

Medium / Transitional: The `--fg3` “minimal deviation” claim is false under nearest-RGB measurement.

Premise: `scripts/page_chrome.py:99-107` says `#616c7c` is the smallest legal movement; `scripts/page_chrome.py:118-127` makes the same claim for dark `#8892a2`.

Measurement: against the exact listed grounds, the standard light `#6b7686` fails at min `3.912`; chosen `#616c7c` passes at min `4.523`, distance `17.321`. But `#666a84` is closer, distance `13.153`, and still passes at min `4.505`. Dark standard `#7a8494` fails at min `4.052`; chosen `#8892a2` passes at min `4.872`, distance `24.249`. But `#7d8e95` is much closer, distance `10.488`, and passes at min `4.504`.

Severity: the page remains readable, so this is not a contrast failure, but it refutes the “minimal and imperceptible” justification for deviating from the standard.

Proposed fix: either use the nearest passing values and document the metric, or stop claiming minimality and state the chosen margin policy explicitly.

**Non-Findings / Measurements**

The headline improvement is real only for the current local workspace: `python3 scripts/check-page-contrast.py --raw` reports `486`, default reports `100`, same probe, same `6664` samples. In a clean committed tree it is `418 -> 93`.

The probe-change artifact concern did not reproduce for the raw/default comparison: both numbers above were measured with the same HEAD probe.

CI disclosure is honest: `.github/workflows/ci.yml:385-391` explicitly says CI runs pure rules only and that the live run is local.

Required checks run:
`check-page-contrast.py --self-test` 64/64, `explainer-serve.py --self-test` 211/211, `check-plan-code.py --self-test` 131/131, `check-selftest-counts.py` OK for 51 scripts, `check-ratchet-contract.py` OK.

NOT CONVERGED: 2 Blocking · 1 High · 1 Medium · 0 Low
