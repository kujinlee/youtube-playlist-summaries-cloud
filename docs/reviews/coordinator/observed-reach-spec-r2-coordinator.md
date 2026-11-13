# Round 2 — `observed-reach-spec` — coordinator

```yaml
round: 2
fixes_nontrivial: true
subject: observed-reach-spec
halves:
  codex: ran
  claude: gap
findings:
  - {id: R2-X1, severity: High, aim: deliverable, fix_induced: true, component: observed-reach-spec, disposition: fixed}
  - {id: R2-X2, severity: Medium, aim: deliverable, fix_induced: true, component: observed-reach-spec, disposition: fixed}
  - {id: R2-X3, severity: Medium, aim: deliverable, fix_induced: true, component: observed-reach-spec, disposition: fixed}
  - {id: R2-X4, severity: Medium, aim: deliverable, fix_induced: true, component: observed-reach-spec, disposition: fixed}
```

REVIEW GAP: claude — alternation

Codex half: `docs/reviews/codex/observed-reach-spec-r2-codex.md` (R2-X*), on `8ed9c9e7`, NOT CONVERGED. Committed
on its own as `42fc4b05`; the fold is the commit after it.

**Method.** Every finding was checked against `shard_slice`, the shard's `targets` / `control_parts` /
`control_is_green` block in `scripts/check-plan-code.py`, the `concurrency` block and the `mutation-sweep` matrix
in `.github/workflows/ci.yml`, and the spec's own text, never taken from the reviewer. The scratch scorer was
rewritten to apply §3 (session scratchpad, `fold586/opts.py`; the round-1 version kept as `fold586/opts_r1.py`)
and the 30-commit loop re-run.

## Dispositions

All four findings are fix-induced: each is in text the round-1 fold added (option B's probes, the recording
partition, §5's "applies this spec's rules", the 20-PR shadow criterion).

| Finding | Class | Disposition and evidence |
|---|---|---|
| **R2-X1** (High), a modified path seen only by `stat`/`access` picks nothing | FIXED IN SPEC | Verified against the spec's text: §2 Use (a) matched changed paths against `reads` only, and `probed` entered only through (c) for `A`/`D`. A size or mode change is an `M` in `git diff --name-status`. §2 Use 3(a) now matches any changed path, `A`, `M` or `D`, against `reads` OR `probed`; §8.3 cases a size-only and an executable-bit-only modification with an unprobed modification as the negative. The reviewer's fixture is constructed, not run here; the logic holds against the text. Re-scored: the rule adds 0 picks on the spike data, since its probes are failed opens of absent paths |
| **R2-X2** (Medium), the `index mod N` recording owner may run no control for its target | FIXED IN SPEC | Verified: `mutate_delivered` narrows `targets` to `{m["file"] for m in shard_muts}` and runs controls only for those, and `shard_slice` strides over entries, not targets. Re-derived from the 91 manifests (4,505 entries, N=24 from the matrix): **27 of 91** `index mod 24` owners run no control for their target (MEASURED, matches the reviewer). The owner is now the lowest-index shard whose slice holds one of the target's entries, which by construction ran the control; the comparison is per seed against that shard's control; the merge refuses a set whose cross-shard control counts disagree. §8.4 cases both |
| **R2-X3** (Medium), the scorer does not apply §3's eligibility | FIXED IN SPEC, scorer FIXED and re-measured | Verified: `opts.py` judged eligibility by `rc`, `timeout`, `events` and `spawns` only, and took the PR's own diff as the added/deleted set. It now applies ancestry (`git merge-base --is-ancestor R BASE`), the harness hash (blobs of `harness_files` at R and BASE), R..BASE staleness of `reads`/`probed`, R..BASE additions under `listed`, and R..HEAD additions/deletions. **Strict (R = `d206e066`): 0 usable read sets on all 15 non-FULL commits and on the three named PRs, so the saving is 0 (MEASURED)**: 14 commits, PR #545 and PR #543 fail ancestry; `4a6f1577` and this spec's PR fail the harness hash (`check-plan-code.py` changed in `8e052493`). The round-1 figures are reproduced exactly with R = BASE (footprint mode: today 67 (1,014), A 65 (879), D 45 (676), B 40 (637)) and are now labelled as that. New, lag 1 (R = BASE's parent, harness assumed equal): A 65 (988), D 46 (774), B 41 (726); 4 of 15 commits get 0 usable sets, because an addition under `scripts/` over R..BASE stale-marks every traceable set. **Q1's recommendation does not change**: B < D < A < today in both footprint and lag-1 scoring. What changes is the claim: no saving is measured, it is INFERRED, and shadow mode (Q4) is now also where the real saving and fallback rate are measured. Not applicable to the spike: the Python-version and case-count checks (neither was recorded); stated in §5 |
| **R2-X4** (Medium), a missing comparison can count toward the 20 clean PRs | FIXED IN SPEC | Verified: a failed control returns before any mutant runs (`report.append("CANNOT RUN — control run ...")`, then `return False, report, ...`), and `cancel-in-progress` is true for `pull_request`. New §8.5: a PR counts only when every would-skip target has a per-mutant verdict on both sides; a cancelled run, a missing artifact or a CANNOT RUN control makes it INCONCLUSIVE, logged, never a pass; a one-sided control failure is a differing verdict; cased. Q4 now says 20 COMPLETE PRs and states the bound's assumptions (consecutive, independent, each with a would-skip target) |

## Verdict

**NOT CONVERGED.** One High and non-trivial fixes (Q4a). The spec's shape survived again: no finding disputes
target-level skipping on control reads. The new, material fact is X3's: on the spike's data the strict rules save
nothing, and at a lag of one commit 4 of 15 commits save nothing, so the design's saving depends on a fresh
recording at nearly every master commit. That is stated in §5; it does not move the goal.

⚠ **Thrashing watch.** All four round-2 findings came from round 1's fix. If round 3 also carries a fix-induced
finding in this component, that is two consecutive rounds and the Phase 6 arming condition
(`docs/dev-process.md`, *The arming condition is thrashing*) fires.

## Round 3

REVIEW GAP: codex — alternation

Round 3 is ONE half, **Claude**, and it is the LAST round before the cap (`docs/review-method.md` §0 Q4c): from
round 4 any finding is FILED unless it is a BLOCKER. Scope: this fold's delta, namely §2 Record's owner rule and
per-seed / cross-shard counts, §2 Use 3(a)'s `probed` match, §5's three scorings and its lag-1 claim, Q1's and
Q4's revised text, and §8.3-§8.5. The reviewer should be asked to refute the lag-1 reading (that an addition
under `scripts/` stale-marks every traceable set) against §3's listed-directory row, and to say whether that row
is stricter than its own reason requires.
