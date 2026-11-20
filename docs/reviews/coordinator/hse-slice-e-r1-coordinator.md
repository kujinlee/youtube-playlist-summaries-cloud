# Round 1 — `hse-slice-e` — coordinator — NOT CONVERGED (both halves)

Codex (`docs/reviews/codex/hse-slice-e-r1-codex.md`) and Claude (`docs/reviews/claude/hse-slice-e-r1-claude.md`) reviewed `d3819724` (plan Tasks 13-15: `scripts/mkt_seed_repo.py`, `docs/marketplace/experiment-tier-a.{md,json}`, `experiment-tier-b.md`, the Phase 6 re-pin). Codex: 1 MAJOR, 2 MINOR; Claude: 4 MAJOR, 3 MINOR; no BLOCKER. XM1 and CM2 are the same finding (`ask-answerer` counted as a working useful operation that was not run). Every regrade below uses only evidence already in the record or the tier-B driver's `results.jsonl`; no measurement was invented.

```yaml
round: 1
fixes_nontrivial: true
subject: hse-slice-e
halves:
  codex: ran
  claude: ran
findings:
  - {id: CM1, severity: High, aim: deliverable, fix_induced: false, component: experiment-tier-a, disposition: fixed}
  - {id: CM2, severity: High, aim: deliverable, fix_induced: false, component: experiment-tier-a, disposition: fixed}
  - {id: CM3, severity: High, aim: deliverable, fix_induced: false, component: mkt-seed-repo, disposition: fixed}
  - {id: CM4, severity: High, aim: instrument, fix_induced: false, component: experiment-tier-a, disposition: filed}
  - {id: Cm1, severity: Medium, aim: deliverable, fix_induced: false, component: experiment-tier-a, disposition: fixed}
  - {id: Cm2, severity: Medium, aim: deliverable, fix_induced: false, component: mkt-seed-repo, disposition: fixed}
  - {id: Cm3, severity: Medium, aim: deliverable, fix_induced: false, component: experiment-tier-b, disposition: fixed}
  - {id: XM1, severity: High, aim: deliverable, fix_induced: false, component: experiment-tier-a, disposition: fixed}
  - {id: Xm1, severity: Medium, aim: deliverable, fix_induced: false, component: experiment-tier-a, disposition: fixed}
  - {id: Xm2, severity: Medium, aim: deliverable, fix_induced: false, component: experiment-tier-a, disposition: fixed}
```

| Id | Finding | Fold |
|---|---|---|
| CM1 | `explainer-serve` condition 1 `pass`, though spec §6 condition 1 requires a page the reader can ask a question INSIDE, and the page served was the experiment's sentinel | regraded strictly: condition 1 `fail` in the matrix and the sidecar, with the reason in the row (the endpoint accepting a POST is not an askable page; S2). `operation_ok` stays `yes`: plan Task 14 defines the serve's `operation_ok` by Task 4 Step 3 (b)'s three conditions, which the row records as held |
| CM2 | `ask-answerer.operation_ok: true` for a useful operation (`--once`) the row says was not run | `operation_ok` → `no` in both, the row saying it is NOT RUN, not failed (the plan's sidecar field is a bool; `false` is the direction that cannot back SHIP under Task 19's `row_errors`) |
| XM1 | the headline counts `ask_answerer --status` as a successful useful operation | same fold as CM2: the headline now reads 7 fail, 1 completes (`explainer-serve`), 1 not measured (`ask_answerer`) |
| CM3 | the 4 typed facts of `known_facts` are never checked against the files the seed commits; `ROADMAP.splitlines()[2]` → `[3]` and `backlog-open` → `"#1 x"` both left 12/12 green | new case `every typed fact is what the committed file it names says`: an independent parse of `git show HEAD:` for the roadmap and backlog, and a run of the committed `check-docs.py`, checking roadmap-status, roadmap-deployed, decision-waiting, backlog-open and ratchet-check-docs. Test-after, red shown by control: on copies outside the repository all 5 typed-fact mutations (the reviewer's 2, plus the deployed line, the decision text, the ratchet rc) go red on this case alone (12/13). The reviewer's 2 are added to `scripts/mutations/mkt_seed_repo.json` (5 → 7, `expected_mutations.py` updated): `check-plan-code.py --mutate . --only scripts/mkt_seed_repo.py` → 7 killed, 7 attributed, 0 survivors |
| CM4 | isolation defect I1 and the `exec_edges` over-report are found defects of this project's tooling, described only, with no backlog row | FILED: backlog #674 (`preflight` passes a world whose root lies under the real `HOME`; its `claude` loaded the author's `~/.claude/CLAUDE.md`) and #675 (`exec_edges`). Verifying #675 corrected the record's cause: the edge does NOT come from a string naming the file (rewording the `source` label left it), but from the self-test's interpreter argv `[sys.executable, str(Path(a.repo) / "scripts/check-docs.py")]` — the reader drops the base by its documented rule, and the base here names the seeded tree (removing the argv removes the edge). The record now says so. Not added to the roadmap: both rows are tooling defects with no milestone step |
| Cm1 | `skill-explain-diff` condition 3 `pass`, though I2 records its server ran from the STAGED marketplace, not the installed paths condition 3 names | regraded `argued` in both, the row naming I2 |
| Cm2 | the seed's docstring says "one per command or file that step names", which `brief` Step 1 refutes (`git diff --stat`, `docs/reviews/`, `docs/superpowers/` have no item; the absent ratchets share one) | docstring states the population as the 12 CHOSEN items and names what has no item |
| Cm3 | tier-B "all 11 scripted and serve runs" enumerates no population | enumerated from the driver's `results.jsonl` (`$(getconf DARWIN_USER_TEMP_DIR)/mktB.4EXn`): 16 runs carry a `RunRecord` — 8 scripted, 3 serve (`--status`, start, `--stop`), 5 post-skill `--stop`; the GETs and POST are the driver's HTTP requests. The record names them |
| Xm1 | "Two causes explain all of it" — `explain-findings` and `dashboard` failed on S3/S4 | reworded: S1 and S2 account for the 7 script failures and both tray-less pages; the 3 skills that produced no page failed on S3 (and `dashboard` also S4), as the matrix rows already say |
| Xm2 | "The ground-truth half of `brief` works for a stranger" overstates a chat answer missing the ahead count and 2 of 5 subjects | reworded to the measured marks: partial ground truth (no ahead count, 3 of 5 subjects without SHAs) and no page half |

Agreement after the fold: all 33 matrix rows parsed against the sidecar (`exercised`, `scenario`, `operation_ok`, conditions 1-5) — 0 disagreements. `check-shipping-sets.py --self-test` 140/140 after the seed edit (the pinned 347-edge set is unchanged: the new argv yields the same edge). Codex's loosening answer (the 347-edge set passes where master's pin required 344) is the documented re-pin both halves reproduced: 0 lost, 3 gained, all from this diff; not a finding.
