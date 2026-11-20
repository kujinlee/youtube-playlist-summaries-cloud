# Round 3 — `hse-slice-e` — coordinator — NOT CONVERGED (Claude half)

Claude (`docs/reviews/claude/hse-slice-e-r3-claude.md`) reviewed `be23de0d`, the round 2 fold (`4873b4bd`) plus the merge of `origin/master`, against plan Tasks 13-15. 1 MAJOR, 5 MINOR, no BLOCKER; none refuted. Every finding was reproduced before it was folded: the four `mkt_seed_repo.py` inputs on copies of the old file in the session scratchpad (each `13/13 self-test cases passed`), and the record findings from the tier-A (`mktA.OPK4`) and tier-B (`mktB.4EXn`) driver `results.jsonl` files the records name. Cm1 and Cm2 are caused by earlier folds in `mkt-seed-repo`: Cm1 by the r2 fold, whose finding (r2 Xm1) was itself caused by the r1 fold — **two consecutive rounds whose findings came from the previous round's fix, in one component: the THRASHING shape that arms Phase 6** (`docs/dev-process.md` → *The arming condition*). Flagged for the coordinator; this fold does not convene it.

REVIEW GAP: codex — alternation (rounds 2+ run one half; round 3 is the Claude half).

```yaml
round: 3
fixes_nontrivial: true
subject: hse-slice-e
halves:
  codex: gap
  claude: ran
findings:
  - {id: CM1, severity: High, aim: deliverable, fix_induced: false, component: experiment-tier-a, disposition: fixed}
  - {id: Cm1, severity: Medium, aim: instrument, fix_induced: true, component: mkt-seed-repo, disposition: fixed}
  - {id: Cm2, severity: Medium, aim: instrument, fix_induced: true, component: mkt-seed-repo, disposition: fixed}
  - {id: Cm3, severity: Medium, aim: instrument, fix_induced: false, component: mkt-seed-repo, disposition: fixed}
  - {id: Cm4, severity: Medium, aim: deliverable, fix_induced: false, component: experiment-tier-a, disposition: fixed}
  - {id: Cm5, severity: Medium, aim: deliverable, fix_induced: false, component: experiment-tier-b, disposition: fixed}
```

| Id | Finding | Fold |
|---|---|---|
| CM1 | condition 4(a) recorded "no, for every component", so 4(b) was a vacuous `pass` — but the driver's own output shows `brief-compose` (`run /explain-diff once first`) and `gen-dashboard` (`Run /explain-diff once to produce one, then re-run`) document a recovery, and the record itself shows following it fails (`explain-diff` produces no Ask tray, S2) | reproduced: a scan of every scripted op's stderr in both `results.jsonl` files finds recovery advice in exactly those two. Regraded STRICTLY: condition 4 `pass` → `fail` for `brief-compose` and `gen-dashboard` in `experiment-tier-a.md` and the `.json` sidecar; the condition-4 paragraph now answers 4(a) per component from the run. Tier B states the same per-component answer (identical messages in its `results.jsonl`). Matrix vs sidecar re-parsed: 33 rows, 0 disagreements on exercised, scenario, `operation_ok`, conditions 1-5. No SHIP verdict changes (both already fail 3) |
| Cm1 | the r2 source check is token membership, so `README.md, not docs/roadmap-to-launch.md`, `cat scripts/check-docs.py` and `grep Deployed: README.md docs/roadmap-to-launch.md` all pass 13/13 | `parsed_from` now holds each typed fact's WHOLE expected source (the verb included for a command item) and the case compares it EXACTLY. All three inputs on a copy of the fixed file: `[FAIL] … got ['roadmap-status']` / `['ratchet-check-docs']` / `['roadmap-deployed']`, 13/14. Mutation `a typed fact's source names the right file among other words` |
| Cm2 | the typed-fact case checks a hand-listed set of 5 ids, so a new typed fact (`roadmap-steps`, wrongly sourced) ships green | an identity clause in the same case: every item that is neither git-derived (an independent literal of the 4 git ids) nor correctly empty must have a parse, and one with none is reported red, never skipped. The `roadmap-steps` input on the fixed file: `[FAIL] … got ['roadmap-steps']`, 13/14. Mutation `a new typed fact has no parse` |
| Cm3 | `ratchets-absent`'s emptiness is never checked against the tree; committing `scripts/check-test-counts.py` leaves 13/13 | new case `every ratchet the seed calls absent is untracked at HEAD` (`git ls-tree -r --name-only HEAD`; the count of 3 paths is an independent literal, so a shrunken source cannot pass vacuously). The input on the fixed file: `got (3, ['scripts/check-test-counts.py'])`, 13/14. Mutation `a ratchet called absent is committed` |
| Cm4 | the scored chat answer is labelled "23:26:59", before world 2 was seeded (23:27:42) | reproduced: world 2's `skill brief` row is `at 23:28:13`, and `at` is the finish stamp (the next run, `explain-diff`, 85 s, is stamped 23:29:53 after a stop at 23:28:14). Label now `23:28:13, finished`; the marks are unchanged |
| Cm5 | tier B says pass conditions differ from tier A only for `skill-explain-diff`, then that condition 2 is `argued` for every page skill — `skill-brief` condition 2 also differs (tier A `fail`) | the sentence now names both differences |

Mutations: manifest `scripts/mutations/mkt_seed_repo.json` 8 → 11, `expected_mutations.py` pin 11. `--mutate . --only scripts/mkt_seed_repo.py` on a scratch worktree: 11 mutations, 11 killed, 11 attributed to the case each names, 0 survivors. Self-test 13 → 14 cases (docstring updated).
