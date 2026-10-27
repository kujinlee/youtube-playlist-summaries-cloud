# backlog-multi-tag — round 1, Claude half (adversarial)

Subject: branch `backlog-multi-tag`, PR #421, HEAD `f8743a97`, against `origin/master` `9ac7c80d`.
Mandate: refute the four claims in the brief. Everything below was executed in mktemp dirs, with
`HOME` redirected for every page render and every mutation run.

## What I tried to refute and could not

| Claim | Probe | Result |
|---|---|---|
| (1) every pre-existing cell parses to its old tags | old `bundle_tags` (from `origin/master`) vs new, over EVERY row of master's `docs/backlog.md` | 333 rows, **0 differ**, 0 malformed, 0 multi-group cells on master |
| (2) multi-tag row under every node and filter tag; the pages agree | `match_rows` over the real tree; `backlog_areas` vs `parse`+`cell_tags` tag sets | tag sets identical (334 item lines both ways); **0 tagged rows unplaced**; untagged rows are #9, #10, #11, #302, all closed |
| nearest at several depths | `nearest_claim("a / b / c / d", ["a","a / b / c","a / b"])` → `a / b / c`; `("a / b", ["a","a / b / c"])` → `a` | correct |
| adversarial cells | `((a))`, `(a),`, `(a) (b`, `(a) (b) x`, `**(tooling)**`, `*(a)*` → flagged malformed, one tag each. `(a)(b)`, `(a)\t(b)`, `(a) ,, (b)` → two tags. `( )`, `()`, `(/)`, `( / )`, `(—) (x)` → sentinel dropped (same as the pre-#381 rule). NBSP collapses; `(a/b/)`, `(a //b)` → `a / b`; `(A) (a)` → one tag | no silent mis-read I could find except finding 5 |
| check-features catches a duplicate claim | two spellings on one node, and one tag on two nodes | both red |
| pages render | `gen-backlog-page.py` (2.97 MB written to temp HOME); `gen-features-page.py --fragment-only` (123 KB). The full features page REFUSES in an empty HOME for want of an Ask tray, which is expected and not this branch's | render |
| mutations | `check-plan-code.py --mutate . --only <f> --allow-long-local` per file | check-features 27/27, gen-features-page 15/15, gen-backlog-page 15/15, **every one attributed to the case it names** |
| EXPECTED_MUTATIONS 2266 | summed the dict literal and counted every entry in `scripts/mutations/*.json` | 2266 = 2266, no per-file mismatch; `check-plan-code --self-test` 246/246 |
| self-tests | all three | 179/179, 18/18, 39/39; `check-features.py` live run rc 0 |
| (4) no closed row changed | bundle diff, master → HEAD, closed rows | **0**; the retag commit changes exactly the 32 ledger rows, old and new cells match the ledger character for character |
| explainer page (c) | recomputed its Bundle figures on `9ac7c80d` | 333 rows, 23 raw values, 22 filter tags, `(tooling)` 176, `(comprehensibility)` 38, ✅ 117, 21 `areas:` entries. All correct for the commit it states it was measured at. Its "features page (raw exact match)" and "explainer-pages claims no tag" are true of that commit and are dated, so I don't count them as false |

## Findings

### 1. Major: the stale-alias check now passes an area that places no row at all

`scripts/check-features.py:221`

```python
if not any(nearest(u, [area]) for u in areas_in_use):
```

This asks whether *some* in-use tag sits at or below `area`. It does not ask whether `area` is the
NEAREST claimant of any tag, which is the rule `match_rows` uses to place rows. So a family area
whose every leaf is claimed by a deeper area passes the gate and shows an empty band. That is the
exact case the message names: "a stale alias looks like coverage".

Reproduction (executed):

```
tree: ### cloud  areas: (cloud)    ### spend  areas: (cloud/money)
in use: {"cloud / money"}
check_cross(...)          -> []                      # green
match_rows(...)           -> {'cloud': [], 'spend': [1]}
```

On master this tree is red, because `(cloud)` was compared raw and no row wrote it. So the branch
**loosens** a gate. The mutation `the stale-alias test wants an exact match, so a family area over
its leaves reads as stale` (`scripts/mutations/check-features.json:289`) and the case at `:411`
pin the loosened form, but neither one separates "family over unclaimed leaves" (should pass)
from "family whose leaves are all claimed deeper" (should fail).

It is not live today. I computed, for every real area, whether it is the nearest claimant of some
in-use tag, and all 22 are. So the fix below does not turn the live tree red.

**Fix:** collect `area_claims` first, then call an area stale when
`area not in {nearest(u, area_claims) for u in areas_in_use}`. Add a case using the tree above
(it must come out red), keep the `:411` case (it must stay green), and add a mutation that reverts
to the any-descendant form, killed by the new case.

### 2. Minor: the shared-chrome rows were retagged as explainer-only, so they dropped off status-pages

Rows #300, #303, #304, #349 and #352 went from `(comprehensibility)` (or untagged, for #303) to
`(comprehensibility/explainers)` alone. Their subject is `scripts/page_chrome.py` or
`brief-compose`, and the status pages render through both: `gen-goals-page.py:801` and `:826`
(`chrome_bar`, `chrome_script`), `gen-work-lines.py:216` and `:530`, and `brief-compose.py`, which
composes the dashboard. #300 itself says the bars sit in the last 30 px "OF EVERY PAGE", and #303
is the `.chrome-slot` reserve that every chrome-bearing page carries. Under nearest-claim these
rows now appear only under `explainer-pages`. The status-pages band under-reports the defects
that affect it, which works against what the retag is for. The suite-wide distinct count is not
affected.

**Fix:** give these five rows `(comprehensibility)` beside `(comprehensibility/explainers)`, which
`status-pages` claims. Or, if shared chrome deserves its own node, give it `(comprehensibility/page-chrome)`.

### 3. Minor: #288 was left out while its twin #259 was put in

#259 ("THE EXPLAINER CONTRACT SAYS PAGES LIVE OUTSIDE THE REPOSITORY…") gained
`(comprehensibility/explainers)`. #288 ("THE EXPLAINER DELIVERY PROCEDURE IS GUARDED ONLY INSIDE A
`SKILL.md`…", touching `.agents/skills/shared/explainer-delivery.md`) was "judged a guard row and
left out". Both are about the same delivery contract, and #123, #129 and #130, which are guard and
coverage rows on `explainer-serve.py`, were also tagged. Whichever rule the retag uses, it applies
to these two rows in opposite directions.

**Fix:** tag #288 `(tooling) (comprehensibility/explainers)`, or untag #259 and write the rule
down in the ledger.

### 4. Minor: the published suite counts include #381 as open, but #381 is closed on the same branch

The #381 status cell (`docs/backlog.md:362`) and the dashboard entry
(`docs/dashboard-entries.md:17897`) say **30** open suite rows, status-pages **10**
(🟠3 🟡6 🟢1) and feature-map **3** (🟠1 🟡2). At HEAD, `match_rows` over the real files gives
**29**, status-pages **9** and feature-map **2**. The difference is #381 itself. It carries
`(comprehensibility) (comprehensibility/feature-map)` and its marker is now ✅, so the figures
were taken before the row closed.

**Fix:** restate the numbers as 29 / 9 / 2, with the severities recounted, or say that they
exclude #381.

### 5. Minor, pre-existing: a tag containing `\|` gets a filter option that matches nothing

`scripts/gen-backlog-page.py:1425` joins `data-tags` with `|`, and the filter at `:2081` does
`split('|')`. `cell_tags` accepts an escaped pipe inside a group. With the row
`| 999 | … | (a \| b) (tooling) | open |`, I get `bundle_tags` → `['a \\| b', 'tooling']` and
`bundle_options` lists `a \| b`, but the JS sees the tags `a \` and ` b`, so choosing that option
shows nothing. No real row has an escaped pipe in this cell, and the old rule had the same flaw.
I list it because #381 now owns this grammar for three readers.

**Fix:** treat a `|` inside a group as malformed in `cell_tags`, so the row gets flagged.

### Not a finding (noted)

The retag commit also edits prose outside the Bundle cell in rows #58, #129, #130, #143, #225 and
#303: bare `#N` becomes `PR #N` or `backlog #N`. I checked each one: `(#322)`, `(#321)`, `(#318)`,
`(#155)` and `(#150)` are squash-commit PR suffixes, and #122 is a backlog row. The ledger doesn't
mention these edits, but they are correct and no closed row is touched.

## Verdict

Claims (1), (2) and the closed-row half of (4) survived every probe. Claim (3) fails on finding 1:
the gate now accepts an area that claims nothing. Claim (4)'s judgement half has two
inconsistencies (findings 2 and 3).

VERDICT: NOT CONVERGED
