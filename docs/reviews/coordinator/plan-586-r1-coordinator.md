# Round 1 — `plan-586` (backlog #586 implementation plan) — coordinator — both halves NOT CONVERGED; folded

```yaml
round: 1
fixes_nontrivial: true
subject: plan-586
halves:
  codex: ran
  claude: ran
findings:
  - {id: X-F1, severity: Blocking, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: X-F2, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: X-F3, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: X-F4, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: X-F5, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: X-F6, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: X-F7, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: X-F8, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: X-F9, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F1, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F2, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F3, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F4, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F5, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F6, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F7, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F8, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F9, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F10, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F11, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F12, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F13, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F14, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F15, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F16, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F17, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F18, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F19, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F20, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
  - {id: C-F21, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-plan, disposition: fixed}
```

Subject: `docs/superpowers/plans/2026-11-09-observed-reach-selection.md` at `20aa6e1b`, the first draft of the
plan for the approved spec `docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md` (PR #552). The
spec is NOT changed by this fold; every fix is a change to how the plan delivers it.

- Codex half: `docs/reviews/codex/plan-586-r1-codex.md` (F1-F9, recorded here as X-F1..X-F9): 1 BLOCKER (F1),
  5 High (F2-F6), 3 Medium (F7-F9). NOT CONVERGED.
- Claude half: `docs/reviews/claude/plan-586-r1-claude.md` (F1-F21, recorded here as C-F1..C-F21): 3 High
  (F1-F3), 10 Medium (F4-F13), 8 Low (F14-F21), by the half's own headings. NOT CONVERGED.

Both review files were committed on their own (`ff7c9264`) before this fold. None of the thirty is fix-induced:
this is round 1.

**Overlaps, folded once.** X-F3 = C-F3 (Q1 probe provenance); X-F6 = C-F13 (the post-switch detector's job and
write permission); X-F8 = C-F14 (registrations for a MODIFIED self-tested script); X-F9 = C-F16 (image drift).
Each pair has one fix, cited under both ids below.

**Method.** Every repo fact a disposition rests on was checked by hand at this head, never taken from a reviewer:
- `parse_seeds` (`scripts/check-plan-code.py`) returns CANNOT RUN for one seed: "it takes two or more" (X-F4).
- `scripts/mutations/expected_mutations.py`: "⛔ backlog #359: THERE IS NO TYPED TOTAL. `declared_total()` derives
  it" (X-F7a). `check-fixture-variation.py`'s `main` prints only `fixture variation OK — N parameter(s) examined`,
  never the key set; `analyse(source, path)[1]` is the set. The W6 command the fold writes was RUN on
  `scripts/sweep-red-alert.py` and printed its five keys (X-F7b).
- `select_manifests` unions own-source, own-manifest and namer hits into one `hit` per path, so its return value
  cannot say why a target was picked (C-F8).
- `GUARD_PATH_RE = re.compile(r"scripts/check-[\w.-]+\.py")` in `check-ratchet-contract.py` (C-F15).
- `ci.yml`: `mutation-sweep` has no job-level `if:`; `mutation-sweep-complete` is `needs: mutation-sweep`,
  `if: always()`, fails any `needs.mutation-sweep.result` but `success`, and holds `issues: write` for
  `scripts/sweep-red-alert.py` (X-F1, X-F6).
- `check-merge-ready.py`'s `hold_reasons`: the only HOLDs are pinned-baseline edits, falling pins or case counts,
  failure-path lines, dropped gate invocations, scope exits, migrations, `NO-REVIEW:`, and app code without tests.
  No PR-body marker forces a HOLD (C-F2).
- Commit `d206e066` exists in this clone, so today's selection at the spike's commit can be computed (C-F7).
- Spec §2's `trace` list spells "strace's own exit"; the fold's reason is `strace exit` to match (C-F10).

## Dispositions

| Finding | Severity | Disposition | Plan section changed |
|---|---|---|---|
| **X-F1** `mutation-sweep needs: sweep-select` while `sweep-select` is PR-only: GitHub skips the dependent job, so master, the schedule and a PR whose selector failed run NO sweep | Blocking | FIXED. Verified: no job-level `if:` on `mutation-sweep`, and `mutation-sweep-complete` fails a `skipped` result. `mutation-sweep` gets `if: ${{ !cancelled() }}` with its `needs:`; a pure `shard_targets(event, select_result, output)` decides, honouring a list only on `pull_request` + `success` + a parseable non-empty list. WORKFLOW-level cases named: master push (skipped → FULL), schedule (skipped → FULL), selector failure, selector skipped and cancelled on a PR, empty/truncated/`full:` output, a list on a push event ignored; a `ci.yml` read pins the `if:` text and the passed result. Plus a live check on the PR and the first master push after merge. A Global Constraint and Review Focus 3 now say the sweep never stops because selection did | Global Constraints; Review Focus 3; Task 8.1 |
| **X-F2** `merge_seeds` returns `a` on equal sets even if `b` was refused; a seed-B-only write disappears | High | FIXED. Either seed's refusal propagates; equal sets → `wrote`/`all_named`/`all_listed` unioned, `probed_stat_only` intersected. Cases: complete A + refused B with equal sets → refused (and the mirror); a write under seed B only refuses its reader | Task 3.2 |
| **X-F3** = **C-F3** `q1_probe_delta` cannot be computed from an undifferentiated `probed` | High | FIXED once. `Record.probed_stat_only` ⊆ `probed`: paths whose ONLY calls were the stat/access family; carried through `readsets.json`; `q1_probe_delta` replaces `probed` with `probed - probed_stat_only`. Cases: stat-only vs stat + failed open vs access + `execve`; the delta 1 vs 0 on a two-target fixture | Tasks 3.2, 4.1, 6.1 |
| **X-F4** replay's `--seeds <s>` is rejected by `parse_seeds` | High | FIXED. Verified the refusal. `parse_seeds(spec, minimum=2)`; only `--mutant` passes `minimum=1` (its seed is fixed by the comparator, not a sample). Spec §2's spelling `--seeds <s>` kept. Cases: replay under seed 5 prints one `verdict=` line; a SWEEP with one seed still CANNOT RUN; a repeated seed refused | Task 7.1 |
| **X-F5** the comparator has no persistence contract: ledger upload, newest-ledger download, latched rows | High | FIXED. The `shadow-compare` job's steps written out; a ledger schema (`prs`, `counts` incl. `clean_consecutive_from_start`, `miss`, `drift_events`, `post_switch_events`, `q1_probe_delta`); upload `if: success()`. Fail closed: a FAILED listing/download uploads nothing (an empty ledger would erase a latched miss); only a truly empty first listing starts empty. Cases: a later run after input expiry keeps a `miss`; a failed listing writes nothing; the newest of two ledgers is read | Task 7.2 |
| **X-F6** = **C-F13** the post-switch detector is not wired and needs `issues: write` the plan forbids | High | FIXED once. It runs as a step of the EXISTING `mutation-sweep-complete` (which already holds `issues: write`, backlog #330) on a red non-PR sweep; the job gains only `actions: read`. Output contract: a Markdown report file; `sweep-red-alert.py` appends it via `POST_SWITCH_REPORT` and stays the one writer of the issue. A missing file is `NOT CHECKED`. The Global Constraint states the exception. The detector also LATCHES (`post_switch_events` in the ledger closes `switch_gate`), which is spec §8.1's "stops the switch" | Global Constraints; Task 8.2 |
| **X-F7** W3 asks for a TOTAL comment the file forbids; W6's command does not print the keys | Medium | FIXED. Both verified. W3: a per-file pin and dated comment, never a sum. W6: an executable `analyse()` one-liner, run once by this fold to check it | W3, W6 |
| **X-F8** = **C-F14** tasks that MODIFY a self-tested script carry no count/manifest/keys pins | Medium | FIXED once. A new "WM" paragraph names W1, W2/W3, W6 for every modifying task (`check-plan-code.py` in 4.1, 4.2, 5.2, 6.1, 6.2, 7.1, 8.1; `strace_reads.py`; `reach_select.py`; `shadow-compare.py`; `sweep-red-alert.py`, registered in all three, verified), and the tasks cite "WM pins" | W-list; Tasks 4.1, 4.2, 5.2, 5.3, 6.1, 6.2, 7.1, 8.1, 8.2 |
| **X-F9** = **C-F16** spec §2's image-drift count is not planned | Medium | FIXED once. `ImageVersion` in each `verdicts-*` header and the `selection-*` artifact; `compare_push` returns a drift flag (images differ, or either null); the ledger counts `drift_events`; never a verdict change. Cases with adjacent equal images | Tasks 6.1, 6.2, 7.2 |
| **C-F1** cross-run compares absolute paths from two different copies, so it never fires in-tree | High | FIXED. ONE normal form `norm`: `copy:<relative>` at or under the run's copy (`.home` included), else absolute (spec §2: "Paths under a run's copy are compared relative to that copy"). Case: two records built by `record_from_log` from logs with DIFFERENT copy roots | Task 3.2 |
| **C-F2** slice 8's preconditions are prose, and the house rule merges on READY | High | FIXED, mechanically and at RUN time: `reach_select.switch_gate` runs on every PR inside `sweep-select` and leaves the selection at today's rule while #590's row at BASE lacks ✅ (read at BASE, so a PR cannot tick its own way in), the ledger is absent, holds a latched miss or post-switch event, has < 20 consecutive complete clean PRs, or Q1 is undecided. Merging slice 8 early is therefore inert. **Declined sub-suggestion, with evidence:** "a `LOOSENING-CHECK`-style declaration so `check-merge-ready` HOLDs it" cannot work: `hold_reasons` has no PR-body-driven HOLD except `NO-REVIEW:` (a waiver), and a `LOOSENING-CHECK` answer only CLEARS a proxy-detected line; it cannot create a HOLD. The runtime gate makes a HOLD unnecessary | Global Constraints; slice map; slice 8 preamble; Task 8.1 |
| **C-F4** "allowlist ⊆ measured set" is a tautology against a constant in the same module | Medium | FIXED. A case LOADS the committed measurement JSON and asserts `MEASURED_SYSCALLS`/`MEASURED_IOCTLS`/`STRACE_VERSION` EQUAL it; slice 3's merge gate is that case, no reviewer diff | Task 3.1; slice map row 3; Task 4.3 |
| **C-F5** no rule for a measured name the spec's lists do not name | Medium | FIXED. Such a name goes to WRITES (spec §2: "a call is a WRITE unless the table names it READ-ONLY"); PROCESS only for the spec's process names or a name whose line shape takes no fd and no path, each with a reason. Case: an unlisted measured name → write | Task 3.1 |
| **C-F6** slice 1 keeps no raw log lines for slice 2's fixtures | Medium | FIXED. The driver keeps two whole logs per shard and one sampled line per (name, return shape) plus signal/exit/clone shapes; committed under `scripts/fixtures/strace-lines/`; slice 2 copies every fixture line from there and parses each whole log end to end | Tasks 1.1, 1.2, 2.1 |
| **C-F7** §8.2's expected set depends on today's live sources | Medium | FIXED. Task 1.0 Step 1b computes today's rule at `d206e066` (its own `select_manifests`, one path at a time) into the fixture; Task 5.2's case INJECTS it (`reasons=`), never recomputed live. The count 33 is the spec's and is checked, not adjusted | Tasks 1.0, 5.2 |
| **C-F8** rule 2 cannot be separated from rule 4 through `select_manifests`' return value | Medium | FIXED. Verified the union. `select_reasons` is split out of `select_manifests` (same body, records the clause per target); `select_manifests` becomes a wrapper with byte-identical output, cased over three recorded diffs. Rule 3 replaces only rule-4 reasons; a case pins an own-source pick surviving a usable set | Task 5.2; slice map row 5 |
| **C-F9** the import direction between `reach_select` and `check-plan-code` is unspecified | Medium | FIXED. `reach_select` loads `check-plan-code` once via `importlib` and owns `--select-only`; `check-plan-code` never imports `reach_select`. Stated consequence: `reach_select` is not in the recording's harness hash, correctly, since it takes no part in recording | Tasks 5.1, 6.1 |
| **C-F10** four §8.3 refusal reasons have no case | Medium | FIXED. `strace missing`, `ptrace denied`, `strace exit` (told apart from a red suite by strace's stderr), `timeout`, each via the injected runner with an adjacent green; slice 1 records strace's stderr and the timeout | Tasks 1.1, 4.1 |
| **C-F11** (a) `record-reads`' timeout from one shard; (b) parse timing vs the copy's removal | Medium | FIXED. (a) the SUM of six shards × 1.5, with slice 1 recording the sum; (b) the traced log is parsed before the copy is removed and before the plain run, with an ordering case through the fake runner | Tasks 1.2, 4.1, 4.2 |
| **C-F12** `sweep-select` lacks `setup-node`, full fetch; ancestry logic in YAML | Medium | FIXED. Steps listed (fetch-depth 0, Node 22, Python 3.12 + pin); `pick_cache` is a pure `reach_select` function with cases (nearest ancestor, nearer non-ancestor skipped, API failure) | Tasks 5.3, 6.2 |
| **C-F14** | Low | = X-F8, folded there | — |
| **C-F15** W7's stated reason is vacuous for these names | Low | FIXED. Verified `GUARD_PATH_RE`. W7 now cites the `ci.yml` step as the caller evidence and says `check-ratchet-contract` does not see these names | W7 |
| **C-F16** | Low | = X-F9, folded there | — |
| **C-F17** slice 4's merge gate lists post-merge observations | Low | FIXED. Task 4.3 is POST-MERGE and blocks slice 6, not slice 4's merge; the slice map says so | Slice map; Task 4.3 |
| **C-F18** #590's "rename or replace" half-cased | Low | FIXED. Either side of a `rename*` that is a pre-existing external path refuses; cases for a replace (`rename(tmp, L)`), a source removal, and a negative between two created paths | Task 2.2 |
| **C-F19** the cache key has no producer step | Low | FIXED. `--record-reads` writes `key=` to `$GITHUB_OUTPUT`; the save reads `steps.rec.outputs.key`; the same-sha schedule collision stated harmless, with `continue-on-error` if the action fails on a duplicate (UNVERIFIED, as the half said) | Tasks 4.1, 4.2 |
| **C-F20** slices 2 and 5 in parallel edit the same registries | Low | FIXED. Merge slice 2 first; slice 5 merges `origin/master` in (not a rebase) and re-derives its pins | Slice map |
| **C-F21** `shadow-compare`'s replay needs the sweep's setup | Low | FIXED with X-F5: Node 22, `npm ci`, Python 3.12 + pin listed | Task 7.2 |

**Codex's closing note** (not a numbered finding): the slice map's "Changes selection?" was literally inaccurate for
slices that edit the harness (their own PR runs ALL). Folded as wording: the column is now "Skips a target?", with
a sentence saying those PRs run MORE.

## Rejected

None outright. One SUB-SUGGESTION of C-F2 is declined with evidence (above): a PR-body declaration cannot make
`check-merge-ready.py` HOLD. The finding itself is folded by a stronger mechanism.

## NEEDS THE OWNER

None. Every fix is a mechanism inside the approved spec; none changes a §7 decision or the goal. The switch gate
implements, at run time, preconditions the spec already states (§2 "backlog #590 must close before any skip takes
effect"; §7 Q4's 20 complete PRs; §2's Q1 fallback; §8.1's "stops the switch").

## Verdict

**Codex: NOT CONVERGED. Claude: NOT CONVERGED.** Thirty findings (one BLOCKER), all folded; the fixes are
non-trivial (a run-time switch gate, a workflow `if:` with workflow-level cases, a ledger persistence contract, a
`select_reasons` split of the harness, a path normal form for the cross-run check), so a further round is owed.

**Next: round 2, ONE half, Codex** (rounds 2+ alternate, `docs/review-method.md` → *Round topology*), on the fold
commit, with `REVIEW GAP: claude — alternation` in the round-2 coordinator. Its brief should ask it to refute the
fold's new mechanisms in particular: `switch_gate` (reads BASE, its ledger dependency, and whether any path lets
a skip take effect with #590 open), `mutation-sweep`'s `if: ${{ !cancelled() }}` and `shard_targets`, the ledger's
fail-closed download, `select_reasons`' byte-identical claim, the `norm` path form, and `merge_seeds`.
