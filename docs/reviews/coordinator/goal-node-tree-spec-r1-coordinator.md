# Round 1 — `goal-node-tree-spec` — coordinator — ⟳ NOT CONVERGED (both halves); 26 fixed, 0 rejected, 3 to the owner (✍)

```yaml
round: 1
fixes_nontrivial: true
subject: goal-node-tree-spec
halves:
  codex: ran
  claude: ran
findings:
  - {id: XB1, severity: Blocking, aim: deliverable, fix_induced: false, component: migration-slices, disposition: fixed}
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: guard, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: false, component: guard, disposition: fixed}
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: false, component: threads-model, disposition: fixed}
  - {id: XM4, severity: Medium, aim: deliverable, fix_induced: false, component: adr, disposition: fixed}
  - {id: Xm1, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: Xm2, severity: Low, aim: deliverable, fix_induced: false, component: renames, disposition: fixed}
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: false, component: threads-model, disposition: fixed}
  - {id: CM2, severity: Medium, aim: deliverable, fix_induced: false, component: migration-slices, disposition: fixed}
  - {id: CM3, severity: Medium, aim: deliverable, fix_induced: false, component: migration-slices, disposition: fixed}
  - {id: CM4, severity: Medium, aim: deliverable, fix_induced: false, component: guard, disposition: fixed}
  - {id: CM5, severity: Medium, aim: deliverable, fix_induced: false, component: guard, disposition: filed}
  - {id: CM6, severity: Medium, aim: deliverable, fix_induced: false, component: threads-model, disposition: filed}
  - {id: CM7, severity: Medium, aim: deliverable, fix_induced: false, component: renames, disposition: fixed}
  - {id: Cm1, severity: Low, aim: deliverable, fix_induced: false, component: mapping, disposition: fixed}
  - {id: Cm2, severity: Low, aim: deliverable, fix_induced: false, component: mapping, disposition: filed}
  - {id: Cm3, severity: Low, aim: deliverable, fix_induced: false, component: history, disposition: fixed}
  - {id: Cm4, severity: Low, aim: deliverable, fix_induced: false, component: guard, disposition: fixed}
  - {id: Cm5, severity: Low, aim: deliverable, fix_induced: false, component: threads-model, disposition: fixed}
  - {id: Cm6, severity: Low, aim: deliverable, fix_induced: false, component: views, disposition: fixed}
  - {id: Cm7, severity: Low, aim: deliverable, fix_induced: false, component: migration-slices, disposition: fixed}
  - {id: Cm8, severity: Low, aim: deliverable, fix_induced: false, component: guard, disposition: fixed}
  - {id: Cm9, severity: Low, aim: deliverable, fix_induced: false, component: guard, disposition: fixed}
  - {id: Cm10, severity: Low, aim: deliverable, fix_induced: false, component: views, disposition: fixed}
  - {id: Cm11, severity: Low, aim: deliverable, fix_induced: false, component: views, disposition: fixed}
  - {id: Cm12, severity: Low, aim: deliverable, fix_induced: false, component: migration-slices, disposition: fixed}
  - {id: Cm13, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: Cm14, severity: Low, aim: deliverable, fix_induced: false, component: views, disposition: fixed}
  - {id: N1, severity: Medium, aim: deliverable, fix_induced: false, component: migration-slices, disposition: fixed}
```

Halves: `docs/reviews/codex/goal-node-tree-spec-r1-codex.md` (1 BLOCKER, 4 Major, 2 Minor) and
`docs/reviews/claude/goal-node-tree-spec-r1-claude.md` (7 Major, 14 Minor). Severity mapped
BLOCKER → Blocking, Major → Medium, Minor → Low. N1 is the coordinator's own, found while verifying.

**`filed` here means ✍ TO THE OWNER, not the backlog.** The three judgment calls the Claude half found
unflagged (CM5, CM6, Cm2) would MOVE an owner decision if fixed, so they are §6 Q11, Q12 and Q13 of the
spec, each with a recommendation; the owner answers them in the walkthrough. CM6 is counted once
below although its G7 half is fixed. XM4's "which tag is primary" part goes to the same Q12.

Every finding was re-derived against the files at `38276f89` before acting; none was taken from either
review's text. The owner's decisions D1–D8 were not reopened; no owner quote was rewritten.

## Findings

| id | half | Verified? — evidence | Action |
|---|---|---|---|
| XB1 | codex | YES. `scripts/gen-features-page.py:286` reads `docs/anchors.md` (`anchor_adrs`) and `:745` lists it as an input; S2 deleted the file and did not touch the script. A full `git grep -c -F anchors.md` found 21 living readers, of which S2 named 5 | FIXED: §5.1 S2 now lists every living reader, by file and line (scripts, both hooks, `explainer-serve.py`, `regen-pages.py`, `check-fixture-variation.py`, `check-publishability.py` fixtures, 10 prose files), and the history files left alone. S2 FAILS IF a listed file still names the registry |
| XM1 | codex | YES. `docs/goal-tree-answers.json` `_doc` keys answers `goal:<slug>`; `scripts/goal-tree.py:2880-2882` matches on them; an unmatched key falls to "Older questions". 0 answers today | FIXED: G2 validates `goal:<slug>` keys; the key is LIVING, so a rename moves it in the same pull request; §5.2 names the test (an answer on a renamed node stays on it) |
| XM2 | codex | YES. G5 said "does not resolve", and `resolve()` resolves `was:` slugs, so `--goal dev-speed-first` would pass | FIXED: G1–G5 check new values against CURRENT slugs; `resolve()` is for reading history only (§2.4, G5, ADR-0016 FAILS IF). G5's collision with backlog #514 is CM5's ✍ |
| XM3 | codex | YES. The 4 cross-goal refs are distinct records: PR #421 `bookkeeping` (l.51) vs `fix` (l.63); PR #422 (l.46, 64); PR #557 (l.57, 208); backlog #384 three lines, one with a `waits` (l.66, 170, 227). And the line-229 "duplicate" was a typo (CM1) | FIXED: §2.3 keeps every line as a work record; counting is by distinct REF (D5's item); `also` is only for a single future record; no §4 merge lands two of these under one node; §5.2 FAILS IF is 144 lines in, 144 out |
| XM4 | codex | PARTLY. ADR-0010 *Scope* does say "no second mechanism". But `epic:` is not new in this spec — backlog #394 shipped it, 2 rows use it — and it is MEMBERSHIP, while `ROOTS`/`DEPENDS` is ORDERING (`gen-backlog-page.py:617-645`) | FIXED: ADR-0016 gains decision 3, recording that `epic:` superseded that ADR-0010 sentence and that the two relations differ; §Prior art row says the same; G3 covers `epic:`, `ROOTS` keys and `DEPENDS` roots. Primary for a multi-tag row → ✍ Q12 (with CM6) |
| Xm1 | codex | YES. "renames two, retires six more" vs 5 `was:` slugs in §4.4 | FIXED: §2.4 says 2 renames + 3 retired = 5, subject to ✍ 4.24, 4.30, 4.33 |
| Xm2 | codex | YES. `docs/goal-threads.md:35, 86, 150, 169` quote `dev-speed-first` and `token-usage-first` inside one owner request | FIXED: §2.4 — a quote is never rewritten nor checked; S3 re-points `## GOAL` headings only; ADR-0016 says the same |
| CM1 | claude | YES. `gh pr view 613` = "Marketplace Task 16: the publishability scan predicts…", merge `36deefc9`; PR #376 = the inventory spec (`d18167ce`), already at l.226; `git log -S` puts the duplicate in `36deefc9`. Page build in a scratch clone: BEFORE rc 1 `MALFORMED — line 229: thread fix · PR #376 is declared twice`; AFTER rc 0, page written (142494 bytes) | FIXED: `docs/goal-threads.md:229` now names PR #613 (on this branch, per the coordinator's brief, not a separate PR); §1 diagnosis corrected; §5.3's "fixed in S3, not before" deleted. `origin/master` still carries the typo until this branch merges |
| CM2 | claude | YES. `Anchor: dev-speed-first` on the observed-reach spec and plan; no `dev-speed-first` node until S3 | FIXED: S2 creates the 4.24 node `dev-speed` (`was: dev-speed-first, harness-speed`) and re-points both headers; the `## GOAL` heading still moves in S3 (no guard reads it before then). S2 FAILS IF names it |
| CM3 | claude | YES. `explainer-serve.py:257` (`PAGE_SOURCES["features"]` holds `docs/anchors.md`, :264 goal-tree lacks `features.md`), hooks `regen-goals-page.sh:36` / `regen-features-page.sh:61`, `regen-pages.py:952-954` routes `goal-threads.md` to goal-tree only. All 14 named scripts have a mutation manifest (checked `scripts/mutations/*.json`) | FIXED: S2 and S4 list each; S4 adds `features.md` and `goal-threads.md` to the page sources; FAILS IF tested through `pages_for`, one case per source |
| CM4 | claude | YES. `check-anchors.py`: `SUBDIRS` is the two `superpowers` dirs, `DATED` never matches `0016-…`; R2 checks every header regardless of date. 6 ADRs carry a header (0011–0016; measured with the `ANCHOR` regex) | FIXED: G1 = every header in specs, plans AND `docs/adr`, any date; ADR-0016 FAILS IF the same |
| CM5 | claude | YES. `session-state.py:377-381` `ADD_NEEDS_GOAL` (backlog #514, owner 2026-11-05): the agent proposes, the owner picks; `goal-tree.py:350` shows an unknown goal as a problem | ✍ OWNER — §2.7 "How a name is born" + §6 Q11. Recommendation: a `proposed:` node field |
| CM6 | claude | YES. `docs/features.md:15-17` shows a multi-tag row under each claimant; 27 rows multi-tag, 23 open (re-measured with `gen-backlog-page.parse` + `cell_tags`) | G7 FIXED (second clause: primary counts sum to distinct open rows). Which tag is primary → ✍ OWNER §6 Q12; recommendation: `epic:` else first tag |
| CM7 | claude | YES (same as Xm2) | FIXED with Xm2; §1 recounts 6 lines as 2 headings + 4 quoted-request lines |
| Cm1 | claude | YES. §2.2 cited 4.20 (that is `cloud-blob-key-encoding`); 4.38–4.41 all at `#####` | FIXED: → 4.38; 4.38 marked ✍; "the one branch" |
| Cm2 | claude | YES. 4.27, 4.41 have no state; 4.3, 4.18 given `built` unflagged | ✍ OWNER §6 Q13; 4.3/4.18 rows flag `built` as the author's claim; §4.4 says 9 nodes with no state |
| Cm3 | claude | MOSTLY. `.claude/agenda-log.jsonl` (main checkout, read-only): 54 records, no slug field; slugs only in free step text (`harness-ships-elsewhere` ×32, `memory-hygiene` ×1) | FIXED: §5.2 row now says "no slug field; prose; not parsed" |
| Cm4 | claude | YES (same as XM1) | FIXED with XM1 |
| Cm5 | claude | YES. 3 request quotes repeat under more than one goal, one ×4 (`sort | uniq -c` of `> 20…` lines) | FIXED: §2.2 accepts and states the repetition — a request is the owner's words, not a counted item |
| Cm6 | claude | YES. `page_markup.py:978-979`, `key_link("feature", …)` → `/features#<slug>`; `check-page-links.py` exists | FIXED: §3.5 / G8 fold both kinds into one with `view`; §3.5 FAILS IF via `check-page-links.py`; S4 lists it |
| Cm7 | claude | YES. Branch `features-tree-index` is not on `origin/master`; `render_index` on `group_tree` (`gen-features-page.py:184-195`) | FIXED: "D8 merged" is §5.1's entry condition; S1 lists `render_index` and the 27-entry pin |
| Cm8 | claude | YES | FIXED: G4 = `ARMED_ANCHORS` exists (if Q6 is taken), else its strings are current slugs; "any tuple of slugs" dropped as undetectable |
| Cm9 | claude | YES — G9 checked shape only | FIXED: G9 requires the `done:` date-time and words to equal a request line under that node; bound stated (recorded, not proven who said it) |
| Cm10 | claude | YES. `docs/goal-threads.md:12-13` numbers by first request | FIXED: §2.2 — a node with no request is numbered after every requested node, in tree order |
| Cm11 | claude | YES. `gen-goals-page.py:498` renders the ROOTS/DEPENDS band | FIXED: §3 table — the band stays on `/goals` (ordering, not gap counts) |
| Cm12 | claude | YES. `batch-ci.py:95-101` resolves `goal-threads.md` only | FIXED: S3 adds a `docs/features.md` resolver to `batch-ci.py` |
| Cm13 | claude | YES. 9 occurrences on 8 lines; 10 on 6 | FIXED: §1, §5.2, Q4 say lines |
| Cm14 | claude | YES. `token-usage` claims no area (Q5 defers) | FIXED: §3.2 — such a node shows "claims no area — gaps not counted" |
| N1 | coordinator | NEW. Removing `anchors:` breaks `check-features.py:141-144` (a `built` node needs ≥1 fragment = areas + anchors): `share-and-download`, `cloud-sync`, `serve-path-bounding`, `cloud-blob-key-encoding` have no `areas:`, and `status-visibility` loses its only area to 4.36. `gen-features-page.py:312` attaches documents via `n.anchors` | FIXED: §2.2 `anchors:` row and S1 — a fragment is `areas:`, `adrs:` or an anchored document; documents attach by the node's own slug |

## Also done in this fold

- **The slug-source enumeration the brief asked for** is §2.5.1 of the spec: the `git grep -c -F`
  command per changing slug, the per-file result, each hit classified, and the table of structured
  sources (field → today's count → which G-rule reads it), with its bound.
- **The page build, not only `--print`**: `python3 scripts/goal-tree.py --snapshot --page --out <file>`
  in a scratch `git clone --shared` of this worktree — rc 1 `MALFORMED` on line 229 before, rc 0 and a
  written page after. It is now a per-slice FAILS IF.

## Count

29 findings (7 Codex + 21 Claude + 1 coordinator): **26 fixed, 0 rejected, 3 ✍ to the owner**
(CM5 → Q11, CM6 → Q12, Cm2 → Q13). XM4 is counted as fixed for its ADR half; its primary-tag question
rides on Q12. Duplicates across halves (XM1/Cm4, Xm2/CM7) are counted on each row.

VERDICT: NOT CONVERGED — round 2 owed (alternation: one half).
