# Round 2 — `merge-ready-thrash-hold` — coordinator — NOT CONVERGED; both findings fixed

Codex reviewed 3cc76714 (the round-1 fold of backlog #680 part 2): `docs/reviews/codex/merge-ready-thrash-hold-r2-codex.md`
(X1, X2 MAJOR; NOT CONVERGED). Rounds 2+ alternate, so the Claude half did not run this round.

REVIEW GAP: claude — alternation

Severity below uses the header grammar's words: MAJOR is `High`.

- **X1. A second `findings:` key was dropped.** `parse_round` reads only the first `findings:` key, so a header
  with `findings: []` and then a second `findings:` key read as a clean round. A field set twice in one finding was
  dropped the same way: `_scalarise` keeps the LAST value, so `fix_induced: true, fix_induced: false` read as not
  fix-induced. `parse_round` now reports `findings_keys` (the count of every `findings:` key) and
  `findings_dup_fields` (each field set twice in one item, flow or block; `_block_findings` was split so
  `_block_items` returns the raw lines). `thrash_gate` reads a count other than 1, or any duplicate field, as
  unreadable, which is a cannot-judge HOLD under the C3 rule. `parse_header` strips both fields: over the 851
  coordinator docs its output is identical to master's (0 differences, 557 of them parse). A duplicate `round:` key
  is NOT refused, because the gate never reads its value; the round number comes from the doc's filename
  (`last_two_docs`), and a probe with two `round:` lines judged the doc as usual. The corpus has no duplicate
  `findings:` key, `round:` key or item field (0 of 721 headers).
  **fix_induced: false.** At d444dcad, in a full clone, a header with a bare `findings:` and then a second
  `findings:` over a fix-induced block item returned no HOLD (0 reasons) beside a fix-induced r3. The r1 fold did
  not introduce it.
- **X2. Deleting an architecture review cleared an armed HOLD.** `thrash_holds` exempted any `ARCH_REVIEW` path in
  the range, and the range names deletions too (`changed_paths` takes old and new paths from `--name-status`).
  `thrash_holds` now takes `head_paths`, every path in the HEAD tree, as a required argument, and a review counts
  only when it is in the range AND at HEAD. `thrash_gate` passes the `git ls-tree` listing it already reads.
  New cases: a deleted coordinator-dir review and a deleted top-level review each still HOLD (pure, through real git,
  and through `main()` with rc=3), and a review at HEAD but outside the range does not clear the HOLD.
  **fix_induced: false.** Codex called it fix-induced. Measured at d444dcad in a full clone, through `gather` and
  then `thrash_gate`: a PR that deletes `docs/reviews/architecture-review-old.md` has that path in `files`, and
  returns 0 HOLD reasons beside two fix-induced rounds. The top-level bypass was already there in the build. The r1
  fold's C2 only widened its reach to `docs/reviews/coordinator/` (at d444dcad a deleted coordinator-dir review
  still HELD, because that directory did not count yet).

Also in this fold, from CI: `check-fixture-variation` reported 6 parameters never varied (`coordinator_subjects.files`,
`thrash_gate.files/head/read/src`, `thrash_holds.thrashing`). New cases now vary each one: a range of several subjects;
`thrash_gate` at `HEAD~1` against `HEAD` through a recording reader with an explicit `src`; a range with no coordinator
doc that never calls its reader; and a `thrashing` stub that names a component, against one that answers None. The
check now exits 0, with no EXEMPT entry added.

Replay over the 41 master commits that touched coordinator docs: 8 HOLDs (5 armed, 3 cannot-judge), 0 CANNOT RUN
before this fold, and the same after it. 11d0568d (PR #600) still HOLDs. Self-tests: check-merge-ready 448/448,
check-review-decision 123/123. Mutations: check-merge-ready 203 → 207 (one re-bound), check-review-decision 30 → 32.

```yaml
round: 2
fixes_nontrivial: true
subject: merge-ready-thrash-hold
halves:
  codex: ran
  claude: gap
findings:
  - id: X1
    severity: High
    aim: deliverable
    fix_induced: false
    component: check-merge-ready-thrash-gate
    disposition: fixed
  - id: X2
    severity: High
    aim: deliverable
    fix_induced: false
    component: check-merge-ready-thrash-gate
    disposition: fixed
```
