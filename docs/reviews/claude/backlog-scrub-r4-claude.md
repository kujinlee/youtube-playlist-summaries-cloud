# backlog-scrub — round 4 — Claude half

**Subject:** branch `docs/backlog-scrub` at `89a2dbd0`, diffed against `origin/master` (`c7c6672f`):
`docs/backlog.md`, `docs/process-checklists.md`, `docs/dashboard-entries.md`.
**Mandate:** refute (`review-b4-r4.md`). I wrote nothing in the worktree except this file, and ran no git writes.
**Method:** I parsed every backlog row on both trees with `check-docs.CELL_SPLIT` (`(?<!\\)\|`) and compared
them by id. To find the qualifications this branch added, I counted each `backlog|PR|task #N` token in the new
row against the same token in the old row. That gave **397** new qualified occurrences: 313 backlog, 80 PR and
4 task. 321 of them are numbers that exist both as a PR (`gh pr list --state all`) and as a backlog row.

## Findings

### L1 — Low: row 3 credits the quoted code to the wrong commit
Quote: *"`lib/html-doc/render-dig-deeper.ts:289` `▶ (${fmtClock(startSec)})` linking `watch?v=…&t=${startSec}s` (`2fae26a9`)"*.
`2fae26a9` (*"renderDigDeeperDoc merge renderer"*) did add the per-section `watch?v=…&t=${startSec}s` link, but in
a different form: `${sectionTitle} ▶</a>`. `git log -S 'fmtClock(startSec)'` shows the quoted
`▶ (${fmtClock(startSec)})` form arrived in `36e653c5` (*"fix(dig): doc render polish — numeral heading, muted control…"*).
The closure is still correct, because dig-deeper has rendered per-section timestamps since `2fae26a9`. Only the
attribution of the quoted text is imprecise.
**Fix (optional):** cite `36e653c5` for the quoted form, or quote only the link that `2fae26a9` introduced.

### L2 — Low: row 300's re-rate count does not reproduce
Quote: *"re-rated 2026-10-24: 🟠 → 🟡 — the producer is fixed (`page_chrome.py:305` `CHROME_PIN = "position:fixed"`); 59 of 62 tracked pages carry it."*
`page_chrome.py:305` is correct. I counted every tracked non-fragment page under `docs/explainers/*.html` for
`position:fixed` and got **60 of 63**. The three without it are
`2026-08-12-explanation-absence-protection-enforced-5cbedcf.html`,
`2026-08-12-explanation-sidebar-refresh-after-ingest-49045e5.html` and `frag-plan-mode-question.html`. The
residue of 3 is the same either way, so the re-rate reason holds. The denominator differs and is not stated.
**Fix (optional):** write "60 of 63 tracked `docs/explainers/*.html` pages", or name the set the 62 was taken over.

No Blocking or Medium findings.

## Checks that held

**(a) Closures: 5 random, plus 5 more, all hold.**
I drew five with `random.seed(424)` from the 17: **#235, #7, #1, #115, #94**.
- **#1 (MOOT):** `a5066652` is *"refactor: retire deep-dive feature (superseded by dig-deeper) (#51)"*, quoted verbatim. `lib/html-doc/render-deep-dive.ts` is absent.
- **#7:** `render.ts:94` `` `<li>${esc(b.text)}</li>` ``. `git log -S` gives `e68a9794` as its origin, and that subject contains "label-less bullets".
- **#94:** the `check-plan-progress.py:30-31` docstring says "A turn beginning from a background-task notification is a FRESH turn with the flag false". The quote spans a line wrap but is otherwise verbatim. `git log -S` gives `20e343bb` as its origin, and that commit body says "Closes backlog #92, #93, #94". The row paraphrases this without quotation marks, which is the round-2 fold, and the fold holds.
- **#115:** `portable-practices.md:1153` "## 24. Wait on the ARTIFACT, with a deadline". `9503d29f` added it, and its body contains "§24 — the measured form of backlog #115". PR #301's title matches.
- **#235 (MOOT):** I re-ran `gh api …/branches/master/protection --jq .required_status_checks.contexts`, and it returned `["verify","schema-gates","mutation-sweep-complete"]`.

I also re-checked:
- **#41:** `de0622a5` is *"feat(#41): M3.1-B — a prod deploy gate …"* (PR #119). The roadmap `:2803` quote matches.
- **#92/#93:** PR #222's title matches.
- **#128:** `45b65cb7` is "The review testimony names itself — backlog #176 (#343)", quoted verbatim.
- **#236:** the same `gh api` output as #235.
- **#85:** its marker reads `✅ (was 🟠)` while the filing marker was 🟡. The row discloses this ("Marker `was` is the 2026-09-02 re-rate"), so it is correct.

**(b) Reference labels: 0 wrong of 70 (0%), every one ambiguous between a PR and a backlog row.**
I drew a stratified sample with `random.seed(4041)`: 55 `backlog` labels and 15 `PR` labels. All were taken from
the 321 newly qualified occurrences whose number exists in both namespaces. Every number that rounds 1–2 listed
was excluded (46, 317, 211, 52, 185, 246–248, 290, 134, 141, 135, 130, 145, 236, 237, 51, 92–94). For each label
I read ±230 characters of context against the backlog row title and the PR title. I checked the unclear cases by
date or by git:
- **PR #149, row 123:** `src_root` first appears in `0536a31c` (#149, 2026-08-24).
- **backlog #70, row 208:** `run_mutations` is first in `da5cd27e`, whose body is "Backlog #70's Phase 1".
- **PR #71 vs backlog #71, row 72:** PR #71 merged on 08-11. The row was filed on 08-30 "while building" the four-renderer seam, which shipped as `0972c55e` (backlog #71).
- **backlog #154/#155, row 160:** the Item says "by backlog #154's round 5", and PR #154 is M4.
- **backlog #206/#207, row 208:** both rows are round-5 findings from 09-30.

Manifest (row@offset:label): 23@5390:b60, 28@227:PR67, 28@518:PR67, 30@195:PR67, 33@3252:b17, 38@179:b37,
40@7710:b56, 54@200/5576/7676:b30, 54@8658/8787:PR165, 56@2567:b40, 72@130:b71, 85@3166:PR206,
86@5407/5512:PR210, 89@4455/4722:b67, 90@1483:b87, 90@5488:b101, 90@5516:b105, 90@12303:b9, 90@13530:PR291,
92@1991:b67, 92@2266:PR222, 101@258/2544:PR235, 109@924:b91, 115@2063:PR301, 123@1630:PR149, 139@7276:PR318,
148@181:b147, 148@537/910:b146, 160@1804/2009/2086:b155, 160@2058:b154, 172@1382:b169, 172@1576:b149,
175@4381:b49, 178@4168:b176, 180@1141:b179, 189@440:b174, 194@3624:b191, 204@3612:b194, 208@2306:b206,
208@5780:b70, 209@2024:b196, 213@4940:b208, 213@7614:b216, 213@8042:b222, 215@1894:b196, 228@3344:b229,
236@826:b235, 236@2396/2420/2538:b137, 252@2374:b249, 252@2430:b342, 253@1629:b255, 256@1185:b250,
256@2025:b257, 260@229:b168, 260@2391:b98, 260@2510:b258, 282@2937/3150:b288, 342@1435:b252.

**(c) State changes, the backlog #344 trap: exactly the 17.**
I extracted master's `scripts` and `docs` with `git archive` into scratch, then ran `gen-backlog-page.py --out`
from both trees with `HOME` redirected. Both pages hold 300 `<article>`s, and open goes from **225 to 208**. The
`data-state` diffs are exactly #1, #3, #5, #6, #7, #41, #85, #89, #92, #93, #94, #115, #128, #228, #235, #236 and
#342. Among open rows, `data-sev` changes on **56** rows, which is exactly the 56 re-rates. The `GROUPS` warning
`[1, 3, 49, 89]` is the disclosed one; on master it is `[49]`. Open by severity, recounted from the Status cells:
🔴 8→3, 🟠 97→63, 🟡 95→106, 🟢 24→35. That matches the dashboard entry. PARTLY notes: 38 rows, which also
matches the dashboard (the brief's "37" predates the reopening of #237).

**The (filed …) form: all 56 re-rates, not just 10.**
- Every `NEW (filed OLD)` has OLD equal to master's leading marker and NEW different from it.
- Every one carries a `re-rated 2026-10-24: OLD → NEW` line whose arrow matches its marker. 0 mismatches.
- Closures: every `✅ (was X)` matches master's marker except #85, which is disclosed above.

I spot-checked the evidence for 10 re-rates not sampled in round 1: #67, #109, #138, #152, #172, #178, #215,
#256, #299 and #300.
- **#178:** `check-review-rounds.py:248` `def schema_of`.
- **#300:** L2 above.

I also screened every re-rated row for round 1's F4 class, where the filer's own words already argued for the
old rating ("why this is X", "not higher", "held at"). The hits were #67, #86, #101 and #103.
- **#67:** the stale warning that was its 🟠 reason is fixed at `mutate-live-schema-check.sh:25-32`.
- **#86:** "held by the weakest layer" is answered by the durable copy, `b3d44f09`.
- **#103:** the false sentence is fixed at `explainer-delivery.md:191`.
- **#101:** its "WHY 🟡 AND NOT 🟠" sentence supports the move to 🟢, not the reverse.

Each of the four cites new evidence rather than the filer's own argument.

**(d) The fold: nothing broke.**
- Cell counts are unchanged on all 98 edited rows, and there are 300 rows on both sides.
- `check-docs.py` exits 0.
- `check-reference-namespace.py --base origin/master`: "OK — no bare `#N` added in 14 reader-facing surface(s)".
- `check-dashboard-entry.py`: ok.
- `git diff --check`: clean.
- **Row 3:** "(PR #51)" is gone.
- **Row 237:** PARTLY, citing `page_chrome.py:124`/`:129`, both verified. The composed prototype page still has exactly one `id="schemer"`, as the note says.
- **Rows 28/30:** now read PR #67.
- **`process-checklists.md`:** the edit (#342 → #252) is consistent with the duplicate closure.

VERDICT: CONVERGED
