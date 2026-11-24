# Round 3 — `goal-node-tree-spec` — coordinator — Claude half CONVERGED (6 Minor); THRASHING armed Phase 6; 6 fixed, 0 rejected

REVIEW GAP: codex — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

Subject: the round-2 fold (`0723378e`) of `docs/superpowers/specs/2026-11-23-goal-node-tree-design.md` and
`docs/adr/0016-names-live-in-one-node-tree.md`, reviewed by Claude in
`docs/reviews/claude/goal-node-tree-spec-r3-claude.md` (0 BLOCKER, 0 Major, 6 Minor; CONVERGED).

```yaml
round: 3
fixes_nontrivial: true
subject: goal-node-tree-spec
halves:
  claude: ran
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: F1, severity: Low, aim: deliverable, fix_induced: false, component: migration-slices, disposition: fixed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: true, component: migration-slices, disposition: fixed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: true, component: migration-slices, disposition: fixed}
  - {id: F4, severity: Low, aim: deliverable, fix_induced: true, component: migration-slices, disposition: fixed}
  - {id: F5, severity: Low, aim: deliverable, fix_induced: false, component: migration-slices, disposition: fixed}
  - {id: F6, severity: Low, aim: deliverable, fix_induced: true, component: migration-slices, disposition: fixed}
```

Severity mapped Minor → Low. `fix_induced` is the reviewer's column, re-checked: §5.1.1, its note, the
dispatcher test and the S3 routing all came in with the round-2 fold (`0723378e`). The owner's decisions D1–D8
and the ✍ questions Q11–Q13 were not touched; no owner quote was rewritten; no new ✍ question was added.

## Thrashing or prose floor? — THRASHING, and Phase 6 ran

Round 2 carried fix-induced findings in `migration-slices` (XM1, N2); round 3 carries four more (F2, F3, F4,
F6). Two consecutive rounds, one component: the arming condition is met, and the answer is not "prose floor"
although every round 3 finding is Minor. Per finding:

| Finding | Same defect as | Why it is not a wording floor |
|---|---|---|
| F2 | r1 XB1 (5 of 21 readers), r1 CM3, r2 XM1 | a list claimed complete, gating a slice, with a member missing |
| F3 | the same | a sentence listing one generator's reads, two missing |
| F4 | the same | a sentence listing the hook edits, one hook and one slice missing |
| F6 | follows from the r2 routing fix | a consequence of adding a trigger the design did not owe |

The test is *can a redesign remove it?* It can, and did:
`docs/reviews/architecture-review-2026-11-23-goal-node-tree-migration.md`. Its two changes: (1) the design
adds NO page trigger, because every page is built from `origin/master` and a merge rebuilds every page
(backlog #408), so the trigger inventory and its two-dispatcher test are deleted; (2) a slice that retires a
name is gated by a search of the whole tracked tree, not by a reader list. The reviewer's own suggestion
(narrow the completeness claim) was option A of that review and is rejected there: S2 would still gate on
"any file in the S2 reader list".

## Findings

| id | Verified? — evidence | Action |
|---|---|---|
| F1 | YES. `scripts/check-features.py:297` assigns `declared`, `:306` passes it to `kind_problems`, `:316` prints its length, `:461` asserts the old message; `scripts/gen-backlog-page.py:4424` raises on `parent_errors(rows, registry_anchors())`, `:4097` and `:3019` are self-test cases | FIXED. S2's first cell now states the replacement once: every former consumer of the registry's slug set takes the tree's CURRENT slugs (G3), naming `kind_problems`, `parent_errors`, the count and the self-test messages. The line numbers are not enumerated as a gate: the S2 search prints 5 of the 7 cited lines, and the other 2 use the local assigned at a printed line (architecture review §4) |
| F2 | The FACTS are true (`regen-backlog-page.sh:88-89` fires on 2 files; `regen-dashboard.sh:35-36` exists). The HARM is not: `scripts/regen-pages.py` builds every page from a fresh `origin/master` (`fresh()`, `:431`), so a `docs/features.md` edit cannot reach `/backlog-table` before it merges, and the merge rebuilds every page (`pages_for`, `:594`). A stranded `epic:` parent fails `check-features.py` (G3) in CI before any merge | FIXED by removing what was incomplete: §5.1.1's table, its "every trigger" claim and the "one edit dispatcher per page" rule are gone; §5.1.1 now states why no trigger is owed. Neither proposed fix (a `/backlog-table` row; a new `case` arm) was taken |
| F3 | YES. `collect()` (`scripts/gen-goals-page.py:433-459`) also calls `parse_roots(gen_text)` (`:444`) and reads the git log | FIXED: the sentence is deleted with the inventory; the spec no longer lists a generator's reads |
| F4 | YES. S2 edited two hooks and S4 one again; the dispatcher test had no named suite | FIXED: the dispatcher test is deleted (nothing left for it to test); S4 edits no hook; the closing paragraph names both hooks S2 edits and says the S2 search checks the removal |
| F5 | PARTLY. No slice said when trunks get slugs — true. But S2's `dev-speed` does not need one: a node's parent is its heading position (`parse_features`, `scripts/check-features.py:41-55`, `trunk = line[3:]`), not a named slug | FIXED: S3 adds the three trunk slugs, where the goal `product` lands on its trunk, conditional on the owner's ✍ row 4.1; S3 says S2's lift is positional. The reviewer's "S1 or S2" was not taken: S1 moves no name, and a trunk slug before ✍ 4.1 would pre-empt the owner |
| F6 | YES (`.claude/settings.json:175`), and only because S3 routed `docs/features.md` to `/goal-tree` | FIXED by removing the cause: S3 adds no route, so the message stays true. `.claude/settings.json` is not touched |

## Same-class search

One search of the tracked tree for the retired file name and the four registry symbols, minus the history set
(architecture review §4; raw output kept in the session scratch directory). Found, beyond round 3:
`docs/backlog.md` names the registry in 9 rows and was in neither S2 list — now in the history set by name;
`regen-pages.py` was listed as an S2 file and names no anchor — removed from the list. A second search for
the bare word `anchors` as a path part in `scripts`, `.claude` and `.agents` found only the `anchors:` field
name (3 lines), so no reader spells the path another way today.

Filed, not fixed: backlog #710 — the edit hooks' `case` lists and `PAGE_SOURCES` are hand-kept copies of what
each generator reads, and since backlog #408 an edit hook cannot show the edit.

## Count

6 findings (Claude): **6 fixed, 0 rejected, 0 to the owner.** 1 backlog row filed (#710).

The fold is non-trivial (a Phase 6 redesign of §5.1 and §5.1.1). Round 4 falls under the round cap
(`docs/review-method.md` §0 Q4c): its findings are FILED unless a BLOCKER.

VERDICT: CONVERGED (Claude half, round 3) — Phase 6 redesign applied in the fold.
