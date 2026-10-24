# backlog-scrub — round 1 — Claude half

**Subject:** branch `docs/backlog-scrub`, commit `486c03ee`, diffed against `origin/master` (`c7c6672f`).
**Mandate:** refute. This is a sampling review of a docs-only commit. I edited nothing in the repo except this file.
**Method:** I parsed every backlog row on both trees with `check-docs.CELL_SPLIT`, the same rule the scripts use (`(?<!\\)\|`), and compared the rows by id. To find the qualifications, I removed the namespace labels from the new text and aligned it against the old row text with `difflib`. This recovered **308** bare-to-qualified rewrites inside pre-existing prose. The report claims 351; the rest are in new text or in duplicated "Previously:" copies. I checked each of these against `gh pr list --state all` (390 PRs) and against the title of backlog row N.

## Findings

### F1 — BLOCKING: backlog #237's closure is wrong. Its own named residue is still live.
The row's old Status lists, as remaining work: *"…and reconciling the prototype page so it stops carrying a private copy."* The new Status closes the row and says *"Not re-checked: whether the prototype page `2026-10-05-topic-why-x-not-y` still carries its private inline copy."* I re-checked it, and the page still carries the copy:
- `docs/explainers/2026-10-05-topic-why-x-not-y.fragment.html:94-101` holds a private `.schemer` stylesheet.
- `:126` holds `<div class="schemer" id="schemer">`.
- `:135-142` holds a private script reading `localStorage 'explainer-scheme'`.
- The composed page has exactly one `id="schemer"`, and it is the private one. The page was never recomposed through `page_chrome.py`.

The implementer applied the PARTLY rule to backlog #218 and #259 ("one stale sentence left, so PARTLY"). That rule applies here as well.
**Fix:** reopen the row with a PARTLY note: shipped in `11c1d5db` (`page_chrome.py:124-129`). What remains is to recompose `2026-10-05-topic-why-x-not-y` from the shared chrome and delete its private copy.

### F2 — Namespace errors: 8 wrong labels, and the evidence for each
| Row | Now reads | Should read | Evidence |
|---|---|---|---|
| 28 (4×: "review of", "Before", "After", "accepted for") | `backlog #46` | the serve-path-bounding slice, `0aac16de` / PR #67 (or leave it unresolved, the way row 289 does for #290) | Backlog row #46 is *"Normalize the title with NFKC before `slugify`"*, filed **2026-08-17**. That is a week **after** the "2026-08-10 whole-branch review of #46" the sentence describes. At `0aac16de` (`fix(#46): bound the serve path's work…(#67)`, 2026-08-11) the backlog had **no row 46 at all**. PR #46 is unrelated (`test(integration): apply pending migrations…`). The roadmap (`roadmap-to-launch.md:126`) calls it "**#46 serve-path bounding** (PR #67)". |
| 30 (2×: "round-4 review of", "the #46 settle-witness") | `backlog #46` | same as above | same slice: reserve RPC, migrations `0024`/`0025` |
| 192 | `a known CODE PR (backlog #317, 28 files, .github/workflows/ci.yml present)` | `PR #317` | The sentence calls it a PR. PR #317 is *"The interpreter every guard runs on was never declared (follow-up to #137)"*, a code PR that touches `ci.yml`. Backlog #317 is a row, not a PR, and has no file count. |
| 85 (new Status text) | `` `Backlog #85 … One fence rule now. (backlog #211)` `` | `` (#211) `` verbatim, or `PR #211` outside the quote | The actual subject of `7a99fb2e` ends `(#211)`, which is the squash PR number. The qualifier rewrote **inside** a quoted commit subject. The report says commit-subject quotes were put in inline code "so the quotes stay verbatim", and this one did not. |

Rows 90 (`backlog #46 and backlog #50 were once marked closed`) are **correct**. The backlog header records that exact incident for rows 46 and 50.

**Error rate.**
- **Systematic sample:** all 32 `PR`/`task` labels, plus every 4th `backlog` label (69 of 276), so 101 in total. **2 wrong (2.0%)**: the two #46 entries that fell in the sample. 0 of 32 PR/task labels were wrong.
- **Full screen** (all 276 `backlog` labels, flagged by context words, then read by hand): **7 wrong of 308 aligned rewrites (2.3%)**, plus 1 in new text (row 85). That is below the ~3% threshold, but close to it, and every one of the 7 is a `backlog` label that should not be one. This is the error direction the report itself predicted.

**Not counted as errors.** The original author's own reference does not match any row, and no label would be right:
- row 90 `#52` ("*tick B5 in the checklist after PR #69 merges*"). Backlog #52 is the sub-playlist row, and no row mentions B5.
- row 226 `#185` ("the page-chrome seam across five producers"). Backlog #185 is the `check-review-decision.py` seam.
- row 259 `#246/#247/#248`. These rows exist only on the unmerged PR #364 branch, as row 249 itself records.

Each of these deserves the same "could not tell" treatment row 289 got. They are not classifier errors.

### F3 — Low (cosmetic): doubled nouns where a plural prefix was kept
- `tasks task #134/#141 → task #135` (row 23)
- `tasks task #130 / task #145` (row 23)
- `PRs PR #134 + PR #135` (row 23)
- `PRs PR #236 and PR #237` (row 101)

The namespaces are right; only the prose is garbled. **Fix:** remove the plural (`tasks #134/…` is not accepted by the checker, so write `task #134/#141 → task #135` and `PR #134 + PR #135`).

### F4 — Low: two re-rates cite evidence the filer had already weighed against them
- **#139 🔴→🟠** quotes *"EXPOSURE today is ZERO — 0 jobs in 30 days"*. The same sentence opens **"Severity held at 🔴: the defect did not get smaller."** The filer considered exposure and rejected it as a reason to downgrade. A better-evidenced reason is in the row: the residual is *"narrow: … orphaned garbage, invisible to readers"*. Cite that instead, or keep the 🔴.
- **#253 🟠→🟡** quotes *"the hook is non-blocking, so a traceback here is noise"*. The filer's sentence continues *"— which is why this is 🟠 and not higher"*. The same fact was used to set the rating at 🟠, so it cannot also justify 🟡 without new evidence.

### F5 — Low: two date conventions in one commit
Every new note is stamped **2026-10-24** (122 occurrences, e.g. "✅ CLOSED 2026-10-24"). The commit is dated `Fri Oct 23 23:33 2026 -0700`. Rows 149, 235 and 236 say "on **2026-10-23**", and backlog #149 says "the 2026-10-23 scrub" while backlog #289 says "the 2026-10-24 scrub". That is the same scrub with two dates. Pick one.

## Checks that held

**Closures, 17 of 18 confirmed** against the cited commit or line:
- **#1:** `render-deep-dive.ts` is gone.
- **#3:** `render-dig-deeper.ts:289` has the `▶ (${fmtClock(startSec)})` link.
- **#5:** `theme.ts:9-26` `BASE_PALETTE_*`.
- **#6:** `render.ts:39` `font-weight:400`.
- **#7:** `render.ts:94` `<li>${esc(b.text)}</li>`.
- **#41:** roadmap `:2803` "Step 3b 6/6, VERIFIED AGAINST: release v11", and Step 3b is the prod smoke (`deploy.md:81`). The old row's only residue was the session capture, which 6/6 implies.
- **#85:** fixed; only the quote is wrong (F2).
- **#89:** `explainer-delivery.md:22` "## 0. WHO RUNS THIS", the `a06a0ada` body runs T0/T3/T4, and all four skills cite the shared file.
- **#92/#93/#94:** the "Closes backlog #92, #93, #94" line is in the `20e343bb` **commit** body, not the PR body as written, but it is still true. `check-plan-progress.py:31` "FRESH turn".
- **#115:** `portable-practices.md:1153` §24, which is the snippet option the row offered.
- **#128:** `codex-review.py:490` `{review_id}.verdict.json`.
- **#228:** `codex-frontier-model.py:53` policy text, and `plugins.md` "NEVER loosen". MOOT is a fair reading.
- **#235/#236:** I re-ran `gh api …/protection --jq .required_status_checks.contexts` and it returned `["verify","schema-gates","mutation-sweep-complete"]`.
- **#342:** backlog #252 covers the same eager pre-check, and is older and fuller.

**Re-rates, 12 sampled, 10 evidenced:**
- **#19:** "*not paid blobs … re-converges*" is present.
- **#22:** `summary-handler-promote-divergence.test.ts:148` `it.failing(…)`.
- **#40:** "NOT launch-blocking".
- **#131/#132:** no `peer-sites` reference under `.claude/` or `.github/`.
- **#182:** 49 of 49 coordinator docs carrying a YAML `GAP:` also carry a `REVIEW GAP:` line, and `check-review-rounds.py` exits 0.
- **#196:** "PARTLY CLOSED 2026-10-01 — the HOOK half is done".
- **#205:** "NOT URGENT".
- **#207:** `surface-recall.sh:107` `*) : ;;`.
- **#259:** `explainer-delivery.md:249` still says `~/explainers/` is outside the repository, so the PARTLY note is right.
- **#311:** "advisory and UNREGISTERED".
- **#332:** "latent, not a missed gate".

The two that failed, #139 and #253, are covered in F4.

**The `🟢 (filed 🟡)` form.** I ran `gen-backlog-page.py --out <tmp>`, which wrote 300 rows with 207 open. I then compared every one of the 300 rendered `<article>`s' `data-sev`/`data-state` against the row's leading marker and its Status-cell ✅. There were **0 mismatches**. No `<h3>` title contains "(filed". The `GROUPS` warning for [1, 3, 49, 89] is expected and was disclosed.

**State changes (the #344 trap).** Exactly 18 rows changed open/closed state, and they are exactly the 18 intended closures. No PARTLY note or re-rate put a ✅ into an open row's Status cell. Cell counts are unchanged on all 98 edited rows.

**Gates.** `check-reference-namespace.py --base origin/master` printed "OK — no bare `#N` added in 14 reader-facing surface(s)". `check-docs.py` exited 0. `check-dashboard-entry.py` exited 0. The `process-checklists.md` edit (#342 → #252) is consistent with the duplicate closure.

## Required to converge
1. **F1:** reopen backlog #237 as PARTLY.
2. **F2:** relabel the 6 `backlog #46` references in rows 28/30 and the `backlog #317` reference in row 192, and restore `(#211)` verbatim in row 85.
3. **F3–F5:** optional, but cheap.

VERDICT: NOT CONVERGED
