Reviewed head: e2ac6e41e2975ebbfade2c4b46e8d2c2d60dbeb1

# Comprehensibility suite spec — round 1, Claude half (adversarial)

**Subject:** `docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md` at `e2ac6e41` (branch `spec-384`).
**Mandate:** refute. The owner's answers (§1, §8) are taken as given; the question is whether the spec implements
them faithfully and can be built without guessing. Written independently of the Codex half (not read).

## Re-measured numbers (task (c))

| Spec claim | Re-measured | Result |
|---|---|---|
| 28 feature nodes, 13 with `anchors:` (§9) | `grep -nE '^#{1,4} \|^anchors:' docs/features.md` → 19 `###` + 9 `####` = 28 nodes; 13 `anchors:` lines (24,55,61,71,88,93,99,105,122,138,144,160,166) | **CONFIRMED** |
| `✅` in severity on 117 of 333 rows (§5, §9) | `git show 9ac7c80d:docs/backlog.md` → 333 rows, 117 matching `^\| *N *\| *✅` | **CONFIRMED** (150 today) |
| 422 rows, all with `⟦kind:` | `grep -c '⟦kind:'` = 422; row count = 422 | **CONFIRMED** |
| 3 hand-built backlog hrefs, 1 PR href (§3, §9) | see M1 | **REFUTED — undercounted** |

## Findings

### H1 — HIGH — Row 1 (D3, "every merge rebuilds the five pages") is already built
**Spec:** §1 D3 (line 36, no "done" mark, unlike D2), §5 line 120, §6 row 1 (line 125).
**Evidence:** `.claude/hooks/regen-pages.sh` header: *"rebuild EVERY generated page after a Bash command whose TEXT contains `gh pr merge` (owner decision D3, 2026-10-28)"*; registered three times in `.claude/settings.json` (lines 120, 170, 183). `scripts/regen-pages.py:314` asserts `{"goal-tree","dashboard","backlog-table","features","goals"} <= set(regenerable())`. `git log -- scripts/regen-pages.py` → `40291231 2026-10-28 … every generated page is rebuilt on merge … (#433)`. The §5 staleness evidence ("built 10-25, 10-23") predates that merge.
**Fix:** mark D3 done (PR #433) like D2/R8; delete row 1 or rescope it to the measured residual gap (a merge not spelled `gh pr merge` in a session: GitHub UI, another clone) with its own falsifier; re-measure staleness after 10-28 or drop the §5 citation.

### H2 — HIGH — Two mechanisms answer "which rows belong to goal X"; contradicts ADR-0010 and the spec's own §7
**Spec:** §4 line 102 (goal derived "area → its feature node → that node's anchor"), §2 line 70 ("goal → … its open rows").
**Evidence:** `gen-goals-page.py:28` — *"backlog rows <- ROOTS/DEPENDS in gen-backlog-page.py, now keyed by anchor slug"*; rendered as "Backlog hanging off it" (`gen-goals-page.py:~763`). ADR-0010 §Scope: *"The backlog gets no header and no new column. Its anchor mechanism already exists: `ROOTS` … Adding a second would be a duplicate mechanism for one concern."* The spec adds a second (derived) row→goal edge and never mentions ROOTS/DEPENDS, so `/goals` (ROOTS) and `/backlog-table` (derived facet) will give different row sets for one goal — §7's "one question … two different answers". Also: `anchors:` is a LIST field (`check-features.py:25 LIST_FIELDS = ("areas","anchors")`) and a row may carry several areas (§4 line 103), so the derived goal is a SET; the spec says "that node's anchor" (singular). And `areas:` → node is not guaranteed unique.
**Fix:** state that ROOTS/DEPENDS is retired or subsumed (and which page reads what), add an ADR-0010 ⟳ amendment rather than silently overriding its Scope paragraph, define the goal facet as a set, and state the rule when an area is claimed by more than one node.

### H3 — HIGH — The `status` facet collides with an existing closed status vocabulary that already carries `needs-you`
**Spec:** §4 line 105 (status `open, parked, needs-you, done`; registry "this spec"); D1 (two needs-you sources).
**Evidence:** `scripts/check-goal-status.py:109-117` — `STATES = {"✅":"shipped","🟠":"current","⏸":"parked","⛔":"obsolete"}`, `ALIVE_WORDS = ("current","needs-you")`; `gen-goals-page.py:97-111` loads it and renders a status badge per spec/plan. This very spec's header is `🟠 needs-you` (line 6). So: (a) two closed vocabularies named "status" share `parked`/`needs-you` and differ on the rest (`done` vs `shipped`, `open` vs `current`, no `obsolete`) — backlog #385's own FAILS IF ("one concept under two values"); (b) spec/plan headers are a THIRD needs-you surface, shown on `/goals`, that D1's "two sets, each with ONE source" does not account for.
**Fix:** say whether the two vocabularies are one facet (unify values, one registry) or two named facets; say whether a spec header's `needs-you` feeds a D1 set or must stop being rendered as one (and add the row).

### H4 — HIGH — D1 drops a source the goal tree reads today, and loses the decision/ACTION split
**Spec:** §1 D1 line 34, §6 row 5 line 132, §7 line 152.
**Evidence:** `scripts/goal-tree.py:34-40` — NEEDS YOU reads **three** sources: dashboard asks (`needs_from_dashboard`, l.406), ledger (l.422), backlog `NEEDS-OWNER` (l.438), merged by `consolidate` (l.471) on `decision:/action: backlog #N` identities; *"Decisions and ACTIONS only the owner can take are two lists (X4: `NEEDS-OWNER-ACTION`, `WAITS-ON-OWNER: ACTION:`)"*. The dashboard's "What needs you" section (`gen-dashboard.py:1380`) carries the choose/Send tray — the only page where an ask is answered. Row 5 says only "dashboard asks link to the goal tree". Unstated: whether `[needs-you]` dashboard entries still exist; if they do, which of the two sets a readable one belongs to (neither source is the dashboard); whether `needs_from_dashboard`/`consolidate` are deleted; where the owner now *answers*. The four status values have no `ACTION` counterpart, so `NEEDS-OWNER-ACTION` rows have no home.
**Fix:** row 5 must name the fate of dashboard asks (converted to a ledger entry or a row; or kept as a source and D1 says three), of `consolidate`, and of the choose tray; and either add an action value/marker or record that actions leave "needs you".

### H5 — HIGH — Row 3 (status facet) cannot be built without guessing the migration
**Spec:** §4 lines 105-108, §6 row 3 line 129, §8 Q3.
**Evidence:** the backlog header is `| # | Item | Touches | Size | Bundle | Status |` (`docs/backlog.md:30`; a second table at :462 is `| # | Item | Status |`). There is **no severity column** — severity is a glyph prefix inside the Item cell — and there IS a free-text Status column. Classifying the Status cells of all 422 rows by first state keyword: OPEN 212, CLOSED 72, (none) 57, DONE 39, FIXED 22, DECIDED 5, MERGED 4, NEEDS-OWNER 2, SUPERSEDED 2, FILED 2, DEFERRED/IN REVIEW 2, BLOCKED 1, PARKED 1. The spec says nothing about the Status column (if it stays, it is a second home for state — §7 line 151 breaks on day one), gives no mapping for BLOCKED / SUPERSEDED / IN REVIEW / NEEDS-OWNER-ACTION / "pending", and does not say whether `parked` is open or closed for the backlog page's `state` filter (`gen-backlog-page.py:2187-2189`, `data-state` = `r['closed']`).
**Fix:** correct "severity column" to what exists; state the Status column's fate; add a mapping table from today's states to the four values (or add values); state the `open/closed/all` filter's treatment of `parked`.

### M1 — MEDIUM — "3 backlog hrefs, 1 PR href" is undercounted, and row 2 will orphan mutation anchors
**Spec:** §3 lines 92-95, §9 line 181, §7 line 154.
**Evidence:** `git show befd0e6d:scripts/gen-dashboard.py | grep -n '/pull/'` → `967: f'/pull/{n}">…` — a second PR href (`gen-dashboard.py:966-967`), split over two lines so the cited one-line grep cannot see it. `goal-tree.py:415` hand-builds `/dashboard#…` (a §3 "Change" key), which §7's falsifier list omits. `scripts/mutations/goal-tree.json:297-298` anchors on the exact PR-href text, so moving it to `key_link` orphans those mutations silently. Both existing PR sites get the repo from `gh repo view` and return **no link** when it fails (`gen-dashboard.repo_slug` docstring: "a wrong link is worse than no link"); the spec says `git remote get-url origin` and `key_link -> str`, which cannot express "no link".
**Fix:** re-measure with a multi-line search; add `/dashboard#` to the §7 list; name the mutation manifest in row 2; pick one repo source and give `key_link` a `None`/plain-text outcome.

### M2 — MEDIUM — The rationale for `page_markup` is false for the goal tree, which already has `link_keys`
**Spec:** §3 lines 87-91.
**Evidence:** `grep -l page_markup scripts/*.py` lists gen-dashboard, gen-goals-page, gen-backlog-page, gen-features-page, explainer-serve — **not** `goal-tree.py`. `goal-tree.py:680 segments(text, repo)` — *"every `PR #N` and `backlog #N` becomes a link"* — is the existing `link_keys`.
**Fix:** say row 2 moves `goal-tree.segments` into `page_markup` and makes the goal tree import it; drop "every generator imports".

### M3 — MEDIUM — R7 (row 8) has no declaration site and no reader; two subject kinds cannot satisfy it; §8 Q7's check has no row
**Spec:** §2 line 73, §6 row 8 line 137, §7 line 157, §8 Q7 line 171.
**Evidence:** roles page line 371: the explainer question is *"a concept, a change, a set of findings"* — a concept has no row/PR/goal/feature, so §7 "an explainer with no declared subject" fails every concept page. A PR subject's home is GitHub (§3), which cannot link back. Row 8 names neither where the declaration lives (fragment meta? `brief-compose` flag? filename?) nor which generator reads it to draw the back-link. §8 Q7 ("a check reports their unlinked keys") is not among the 12 rows.
**Fix:** name the declaration format and its reader; allow `subject: concept` (or a goal) and state that PR subjects get no back-link; add the Q7 check as a row (or fold it into row 2/8 explicitly).

### M4 — MEDIUM — Two pages already answer questions the spec assigns elsewhere, and no row removes them
**Spec:** §2 lines 68-70, §5 line 118.
**Evidence:** `gen-backlog-page.py:2168-2182` renders "Since your last visit" with a baseline `<select>` (last visit / 7 / 30 days) — a what-changed-since-T answer on `/backlog-table`, while §5 gives since-T to the goal tree. `gen-goals-page.py` renders per-thread PR lists, spec/plan status badges and milestone ◀/✅ rungs — "what is in flight"/"what is built", which §2 says goals must not restate. Its backlog chips are `#{num}` unlinked text (l.~763) and its PR lines `#{num}` — invisible to §7's falsifier, which matches only `backlog #N`/`PR #N`.
**Fix:** either justify each as in-role or add rows to remove/link them; widen the §7 key falsifier to bare `#N` on generated pages (or require the qualified form there).

### M5 — MEDIUM — Row 11 checks a declaration that no row creates
**Spec:** §6 row 11 line 141, §7 line 149.
**Evidence:** no row adds a "declared question" to any page or generator; briefs and explainers are ~69 dated pages (`ls docs/explainers/*.html | grep -v fragment | wc -l` = 69), all sharing one question per type.
**Fix:** say the question is declared per page TYPE (where: each generator, plus brief-compose/explain-* skills) and which row adds it.

### L1 — LOW — Vocabulary and CONTEXT.md drift
**Evidence:** `CONTEXT.md:131` defines **Anchor** only as a mutation's binding text; the spec uses "anchor" for ADR-0010 goal slugs throughout. `CONTEXT.md:100` lists five pages as dashboard, backlog table, goals view, explainer viewer, features tree — not D3's five (which include the goal tree). §9 "seven page producers — MEASURED, backlog #384" — #384's list includes `gen-work-lines`, not the goal tree; the spec's list is a substitution, not that measurement.
**Fix:** add a row (or a line in an existing one) updating CONTEXT.md (goal anchor vs mutation anchor; the page list; "needs you"; the four facets); label the seven-producer list as updated after D2.

### L2 — LOW — The freshness falsifier is not observable
**Spec:** §7 line 158 ("older … by more than one rebuild"), §9 line 188 (D3 "not more than a minute").
**Evidence:** "one rebuild" is not a quantity a check can compare against a stamp; the two lines state different bounds.
**Fix:** one bound, in time (e.g. stamp older than the newest `origin/master` merge by > N minutes).

VERDICT: NOT CONVERGED
