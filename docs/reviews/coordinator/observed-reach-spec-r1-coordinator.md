# Round 1 — `observed-reach-spec` — coordinator

```yaml
round: 1
fixes_nontrivial: true
subject: observed-reach-spec
halves:
  codex: ran
  claude: ran
findings:
  - {id: R1-C1, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-C2, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-C3, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-C4, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-C5, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-C6, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-C7, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-C8, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-C9, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-C10, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-C11, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-C12, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-X1, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-X2, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-X3, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-X4, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-X5, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-X6, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-X7, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-X8, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R1-X9, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
```

Claude half: `docs/reviews/claude/observed-reach-spec-r1-claude.md` (R1-C*), Codex half:
`docs/reviews/codex/observed-reach-spec-r1-codex.md` (R1-X*), both on `5ee0b6d7`, both NOT CONVERGED.
The fold is on the commit after `b43e4945`.

**Method.** Every finding was checked against `select_manifests` (`scripts/check-plan-code.py`), `run_suite_parts`,
`control_parts`, `control_is_green`, `shard_slice`, `red_body` (`scripts/sweep-red-alert.py`) and the
`mutation-sweep` / `mutation-sweep-complete` jobs in `.github/workflows/ci.yml`, never taken from the reviewer. The
spike's raw data (`observed.json` and the per-target event logs) survive in the session scratchpad, so the
selection options were scored with a scratch scorer that imports the real `select_manifests` and `_names_of`
and applies the folded rules to the spike's read sets.

## Dispositions

Duplicates across the halves are merged into one row. The yaml marks every row `fixed`; the CLASS column says
which kind of fix. No finding is REJECTED outright; two sub-claims are refuted in their rows.

| Finding | Class | Disposition and evidence |
|---|---|---|
| **R1-C1** (High), added/deleted naming union gives the saving back; §5 does not apply §3 | FIXED IN SPEC + OWNER QUESTION (Q1) | Verified. The cause is `between` starting AT the staged root (`lo = len(root.split("/"))`), so every `docs/` path picks every `'docs'` quoter: one new `docs/zzz.md` picks 51 of 91 (MEASURED). Scored: §3 as written picks 65 on PR #543 and 61 on this spec's PR, against today's 68 and 64; over the 15 non-FULL commits of the last 30 on master the median is 67 today, 65 under §3 as written (A), 45 (D) and 40 (B). Options A-D and their numbers are now §7 Q1, recommendation B; §5 applies the rules per option. The reviewer's third candidate, "naming only for added paths under a directory some suite listed", is MEASURED degenerate: `check-canonical-source` lists every directory, so it equals option A (65 / 61) |
| **R1-C2** = **R1-X4** (High), the recording launcher wraps the real control | FIXED IN SPEC | Verified: `run_suite_parts` runs `[sys.executable, name, "--self-test"]`, and the control gates `control_is_green` and prices `control_seconds`. Now a SEPARATE pass after the verdicts, feeding neither, with argv/`sys.path[0]`/cwd/env parity, once per seed and united (`control_parts` runs every seed), accepted only when green by `control_is_green` with the real control's case count. X4's sub-claim that the spike's launcher did not reproduce `sys.path[0]` is refuted: `audit_wrap.py` sets `sys.path[0]` and `sys.argv` explicitly. `sys.modules["__main__"]` still differs under `runpy`, so the parity contract stands |
| **R1-C3** = **R1-X5** (High), per-shard restore, no ancestry filter | FIXED IN SPEC | Verified: each shard computes its own selection, and `shard_slice` strides over it. A new `sweep-select` job resolves once (API listing, ancestor filter, exact-key restore, payload validation) and passes the list to every shard; §8.4 fails a shard that runs another list |
| **R1-C4** (High), staleness ignores `listed` | FIXED IN SPEC | Verified against §3's table. New row: an R..BASE addition or deletion under a listed directory makes the set stale. Cased with the adjacent negative in §8.3 |
| **R1-X1** (High), a master addition after R activates an unseen dependency | FIXED IN SPEC | The reproduction is a constructed fixture; its logic holds against the spec's text. Added and deleted paths are now taken over R..HEAD. Cased in §8.3 |
| **R1-X2** (High), control read sets do not meet backlog #560's contract | FIXED IN SPEC | Verified against backlog #560's row ("everything that mutant run read"). §6 now claims only the infrastructure; per-mutant recording is backlog #560's own. Q6's answer is unchanged, its reason restated |
| **R1-X3** = **R1-C11** first bullet (Medium/Low), own-manifest does not run ALL | FIXED IN SPEC | Verified: `MANIFEST_PATH.fullmatch` adds its target; only an orphan manifest is FULL. §2 Use now lists the real FULL rules, including `SHARED_FULL_FRACTION`, and makes own-source/own-manifest mandatory |
| **R1-C7** = **R1-X6** (High), shadow criterion cannot fire; §8.1 has no data source | FIXED IN SPEC; data artifacts DEFERRED to the build plan | Verified: `red_body` carries the sweep result, event, sha and run URL, no targets. Q4 now uses the PR's own sweep against its base's full sweep, per-mutant verdicts on the would-skip set, 20 PRs, bound stated (0 in 20 is below 14%, 95%). §8.1 names the data: a parseable `WOULD-SKIP:`/`SKIPPED:` line, a per-shard structured results artifact, PR attribution from the squash subject. Building those artifacts is the plan's |
| **R1-C8** = **R1-X7** (Medium), §8.2 passes a degenerate selector | FIXED IN SPEC | §8.2 asserts the EXACT set for PR #545 (33 spawners + `check-canonical-source`, `check-dashboard-entry`, `check-features`, re-derived by the scorer), plus mandatory positives and adjacent negatives. §8.4 checks exact shard and target coverage before a save |
| **R1-X8** (Medium), `--name-only` cannot give A/M/D | FIXED IN SPEC | Verified at the sweep step: `git diff --name-only -z --no-renames`. §2 now specifies `--name-status -z --no-renames`; an unparseable list is FULL |
| **R1-X9** + **R1-C10** (Medium/Low), estimates and counts | FIXED IN SPEC; historical replay DEFERRED | Verified in `observed.json`: 47 spawners (one, `push-command`, also failed), 43 traceable. So "46 spawn and 1 failed" was wrong and Q3 (ex-Q1) is 50, not 49. "MEASURED estimate" is now INFERRED. The `GITHUB_*` drift is §4.4. A replay against historical-base read sets is impossible (none were recorded), so shadow mode is that measurement |
| R1-C1's "25 of the last 30 commits add or delete" | re-measured | 26 of the 30 first-parent commits ending at `4a6f1577` (MEASURED, `git diff --name-status --no-renames` per commit); the spec states the window |
| **R1-C5** (Medium), failed opens are dropped | FIXED IN SPEC (option B) | Verified in `analyze.py`: opens not in `repo_files.txt` go to `junk`. `probed` records them; Q1 B adds wrapped `stat`/`lstat`/`access` |
| **R1-C6** (Medium), "spawned" by argv kinds | FIXED IN SPEC | §2 lists every process-creation audit event; §8.3 cases `os.fork` and `os.system` |
| **R1-C9** (Medium), cost of a miss understated | FIXED IN SPEC | Verified: backlog #560's row reads "10 survivors = 3 distinct defects, each red 1-3 days". Quoted, with the masking under one open issue |
| **R1-C11** remaining bullets (Low) | FIXED IN SPEC | The launcher is a top-level import of `check-plan-code.py`, so `harness_files` covers it; recording excludes `batch/**` (fail-fast shards) and PRs. BASE is refined from the reviewer's "the `origin/$BASE_REF` tip" to `git merge-base origin/$BASE_REF HEAD`, which is what the three-dot diff uses |
| **R1-C12** (Low), Q3 is engineering; F1's trade is missing | FIXED IN SPEC | Master-only recording left §7 as a stated decision; the added-path trade is Q1 |

## Verdict

**NOT CONVERGED.** Seven Highs in the deliverable and non-trivial fixes (Q4a). The spec's shape survived:
neither half disputed that control reads are a sound basis for target-level skipping on modify-only paths,
and PR #545's 36 was re-derived exactly. Every High was a gap around it, now closed in the text. Q1 is new and
is the owner's.

## Round 2

REVIEW GAP: claude — alternation

Round 2 is ONE half, **Codex**, scoped to this fold's delta to the spec: §2 (the separate recording pass, the
`sweep-select` job, the status-bearing diff), §3's two new staleness rows, §7 Q1's options and numbers, and §8's
exact-set and shadow falsifiers. Reproduction is Codex's strength, and the new rules are reproducible. Per the
round cap (`docs/review-method.md` §0 Q4c), round 3 is Claude if round 2 does not converge, and from round 4 any
finding is FILED unless it is a BLOCKER.
