# backlog-scrub — round 6 — Claude half

**Subject:** branch `docs/backlog-scrub` at `dd003167`, against merge base `c7c6672f` (`origin/master` is now
`9f673be7`; the r5 Codex half already attributed the #310/#340 differences to master advancing).
Files: `docs/backlog.md`, `docs/process-checklists.md`, `docs/dashboard-entries.md`.
**Mandate:** refute (`review-b4-r6.md`), final-tree check. I wrote only this file and ran no git writes.
I ran every generator and checker with `HOME` redirected to scratch.
**Method:** I parsed rows on both trees with `check-docs.CELL_SPLIT` (`(?<!\\)\|`) and keyed them by id. For
bare references I imported `check-reference-namespace.violations` and ran it, rather than writing my own
version of the rule.

## Findings

### L1 — Low (a stated number that does not reproduce, and was not updated by the fold): dashboard reference count
**Where:** `docs/dashboard-entries.md`, the 2026-10-24 entry, tech section.
**Quote:** *"That came to 351 references: 307 marked backlog, 40 PR and 4 task."*
**What is wrong:** I could not reproduce this figure under either reading of "references qualified":
- **Bare references that had to be qualified.** I ran the guard's own `violations()` over the master text
  of the 98 edited rows and got **311** (it is **0** on the branch).
- **Qualified tokens added.** The net increase in `backlog|PR|task #N` over the same 98 rows is **396**: 312
  backlog, 80 PR and 4 task. At the original commit `486c03ee` it was **397**: 321 backlog, 72 PR and 4 task.
  Round 4 reported 397 (313/80/4).

The breakdown is stale in any case. Fold F2 (`3b162d32`) moved seven labels from backlog to PR (six to PR #67
and one to PR #317). That diff carries the "351" line as unchanged context, so the per-namespace split predates
the fold that changed it. The claim next to it, *"Every bare `#N` in the 98 edited rows was qualified"*, is
TRUE: the guard reports 0 on the branch. So this is a count, not a correctness defect.
**Fix:** restate it with its method, e.g. "the 311 bare references that `check-reference-namespace.py` fires
on in master's text of these rows are all qualified". Or drop the breakdown. Do not re-derive 351.

### L2 — Low (wording; the claim is true): row 23's two sentences list different remainders
**Quote:** *"re-rated 2026-10-24: 🟠 → 🟡 — slice A shipped; all remaining work is filed as backlog #60, backlog
#61, backlog #62, backlog #63."* is followed by *"PARTLY — … Remains: nothing in this row; slices B and C are
backlog #60 and backlog #61, and the failure-path leak is backlog #62."*
- The second sentence drops backlog #63, which the first one names and which the row's own 08-24 note files.
- "PARTLY" next to "Remains: nothing in this row" also reads oddly. Leaving the row open as an umbrella is a
  defensible choice, so I am not calling it a missed closure. But a reader cannot tell why a row with nothing
  remaining is still counted among the 208 open rows.

**Fix:** add "and the raw validator string is backlog #63". Optionally, say why the row stays open (for example,
"kept open as the umbrella until #60–#63 close"), or close it as split.

No Blocking or Medium findings.

## Checks that held

**(a) Closures: all 17 citations opened, none wrong.**
- **#5, #6, #7:** `e68a9794` (2026-06-19, *"lighter lead + label-less bullets + palette dedup"*). Its diff
  changes `.lead` from `font-weight:600` to `400`, keeping `color:var(--gold)`. `render.ts:39` and `:94`
  (`<li>${esc(b.text)}</li>`) are verbatim. `theme.ts:9-26` holds `BASE_PALETTE_*`, which `git log -S` traces
  to `e68a9794`.
- **#1, #3:** `render-deep-dive.ts` is absent. `a5066652`'s subject is quoted verbatim. `render-dig-deeper.ts:289`
  is `▶ (${fmtClock(startSec)})` with the `watch?v=…&t=${startSec}s` href, and the r4 attribution
  (`2fae26a9`/`36e653c5`) holds.
- **#41:** `de0622a5` (PR #119), subject verbatim.
- **#85:** `7a99fb2e` (PR #211). `check-dashboard-entry.py:202` is `def fence_closes`.
- **#89:** `882f0b1f` (PR #266) and `a06a0ada` (PR #267). `explainer-delivery.md:22` is "## 0. WHO RUNS THIS".
  `check-explainer-delivery.py` gives "1 shared description, 5 skills cite it, 0 restatements".
- **#92, #93, #94:** the `20e343bb` body begins "Closes backlog #92, #93, #94". #93's row describes a trap
  around plan-mode printer gates, and plan mode's code was deleted (PR 2 of 2, 2026-09-09, per `dev-process.md`).
- **#115:** `portable-practices.md:1153` is verbatim, from `9503d29f` (PR #301).
- **#128:** `codex-review.py:490` is `f"{review_id}.verdict.json"`, from `45b65cb7`.
- **#228:** `codex-frontier-model.py:53` is verbatim. The `plugins.md` quote "NEVER loosen the resolver to accept
  a hidden model" spans a line wrap at `:141`, with bold markers dropped. That is acceptable.
- **#235, #236:** I re-ran `gh api …/branches/master/protection` and it returned
  `["verify","schema-gates","mutation-sweep-complete"]`.
- **#342:** the duplicate pointer is consistent with `process-checklists.md:121`, which now cites backlog #252.

**(b) Reference labels: 0 wrong of 62 (0%).** I drew a fresh sample with `random.seed(60624)`.
- **Population:** newly added `backlog|PR|task #N` tokens in edited rows whose number exists BOTH as a PR
  (`gh pr list --state all`, 390 PRs) and as a backlog row. I excluded every number named in r1 or in r4's
  manifest. That left 144 candidates (138 backlog, 6 PR, 0 task); I took 56 backlog and all 6 PR.
- **Method:** for each label I read ±200 characters of context against both titles.
- **Ambiguous cases, resolved by date or git:**
  - **backlog #96 "F11" (row 89):** the backlog #96 slice is `d7e96cbd` (2026-09-06), and its banner-guard
    review rounds exist. PR #96 is an 08-13 e2e test.
  - **backlog #214 (row 213):** both rows were filed 2026-10-01 in the same session. PR #214 is unrelated.
  - **backlog #217 (rows 174, 189, 228, 235, 236):** PR #366's title ends "(backlog #217)".
  - **PR #322 (row 139):** this is the `fly.toml` sentence deletion. The PR title matches.
  - **PR #331 / backlog #154 (row 155):** the PR title ends "(backlog #154)".
  - **backlog #36 (row 40):** the 🔴 non-ASCII title row was filed before the 08-13 note. PR #36 is dev-login.
  - **backlog #88 → PR #224 (row 89):** consistent.

Manifest (row@offset:label): 17@3093:b19, 17@3251:b22, 23@8914/9109:b62, 23@9067:b61, 30@3168:b54,
33@2993/4010:b54, 33@3225:b19, 40@6704:b36, 41@1719:PR119, 61@1692:b23, 89@2883/4335/8881:b88, 89@9210:b96,
90@866/1405:b79, 90@1314:b50, 90@1353:b75, 90@1366:b76, 90@1379:b77, 90@1418:b80, 90@1444:b82, 90@1457:b83,
90@1509/1576:b89, 90@1692:b39, 90@1820:b53, 90@2163:b28, 90@5474:b100, 90@5502:b104, 90@5530:b107,
101@1669:b78, 105@1484/1806:b102, 115@2123:b115, 120@2262:b260, 134@2453:b131, 139@6116/6507:PR322,
148@1823:PR332, 149@2684:PR328, 155@5622:PR331, 172@1030:b170, 174@2694:b173, 174@2756:b217,
189@7227/7312/7492:b217, 192@4045:b137, 213@5010:b214, 228@3382:b217, 235@5775:b217, 236@512/2566:b230,
236@2420:b137, 236@2552:b217, 252@2402:b251, 258@2650:b256, 289@3682/4821:b282.

**(c) State changes, the backlog #344 trap: exactly the 17.** I extracted master's `scripts` and `docs` with
`git archive c7c6672f` and ran `gen-backlog-page.py --out` on both trees.
- Both pages hold 300 `<article>`s, and open goes from **225 to 208**.
- The `data-state` diffs are exactly #1, #3, #5, #6, #7, #41, #85, #89, #92, #93, #94, #115, #128, #228, #235,
  #236 and #342.
- Among open rows, `data-sev` changes on **56** rows. Open by severity is crit 8→3, high 97→63, med 95→106 and
  low 24→35, which matches the dashboard. The crit rows are exactly i139, i251 and i312, as the prose says.
- The `GROUPS` warning is `[1, 3, 49, 89]` against master's `[49]`, as disclosed.
- `check-backlog-closure.py` warns on #117 and #159. Neither row was touched, and both closing subjects (PR #304
  and PR #330) are docs-only filing PRs, so these are known false positives and not misses of this scrub.

**(d) The fold and cross-copy numbers.**
- All 98 edited rows keep their cell count, and there are 300 rows on both sides.
- These checks pass: `check-docs.py` (rc=0), `check-reference-namespace.py --base origin/master` (OK, 0 bare),
  `check-dashboard-entry.py` (ok) and `git diff --check` (clean).
- **The scrub's own counts agree with the tree:**
  - 17 `CLOSED 2026-10-24`.
  - 56 `(filed X)` markers, which equals 56 `re-rated 2026-10-24` lines.
  - 38 `2026-10-24: PARTLY` notes.
  - NEEDS-OWNER is exactly #8, #26, #27, #28, #53 and #144.
  - None of the nine "not touched" rows (#62, #63, #231, #306, #310, #318, #339, #340, #343) is edited.
  - Row 300 reads "60 of 63" and "3 of 63", which now agree. That was the r5 class, and I re-checked it by grep.
- The one number that disagrees is L1.

VERDICT: NOT CONVERGED
