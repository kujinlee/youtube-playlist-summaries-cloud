# Round 1 — `spec-586-redesign` (PR #552, backlog #586) — coordinator — both halves NOT CONVERGED; folded

```yaml
round: 1
fixes_nontrivial: true
subject: spec-586-redesign
halves:
  codex: ran
  claude: ran
findings:
  - {id: X-F1, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: X-F2, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: X-F3, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: X-F4, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: X-F5, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: X-F6, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: X-F7, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: C-F1, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: C-F2, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: C-F3, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: C-F4, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: C-F5, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: C-F6, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: C-F7, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: C-F8, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: C-F9, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: C-F10, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: C-F11, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: C-F12, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: C-F13, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
```

Subject: `docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md` at `dcf8bb20`, the spec as the
owner approved it, with the round-3 redesign (one dedicated `record-reads` job) and the owner's `strace -f`
recorder that no round of `observed-reach-spec` saw (`observed-reach-spec-r3-coordinator.md`, REDESIGNED line).

- Codex half: `docs/reviews/codex/spec-586-redesign-r1-codex.md` (F1-F7, recorded here as X-F1..X-F7), 7 High,
  NOT CONVERGED.
- Claude half: `docs/reviews/claude/spec-586-redesign-r1-claude.md` (F1-F13, recorded here as C-F1..C-F13),
  3 High, 5 Medium (F4-F8), 5 Low (F9-F13), by the half's own headings. NOT CONVERGED. (The fold's brief said
  6 Medium and 4 Low; the headings are what this table records.)

Both review files and their verdicts were committed on their own before this fold. None of the twenty is
fix-induced: this is the first round on the redesigned text.

**Scope of the fold.** The owner approved the direction and every decision in §7 (Q1 B, Q2 superseded, Q3
today's rule where tracing fails, Q4 shadow for 20 complete PRs, Q5 the accepted bound, Q6 before backlog #560,
the `strace -f` recorder, goal `dev-speed-first`). Every finding is folded as a MECHANISM change inside those
decisions. Each fix keeps the fail-closed property: any doubt gives today's selection or more, never fewer. Where
a fix replaces a fallback to today's rule with a PICK (`Δ`, `git_membership`), the pick is the stronger side.

**Method.** The harness facts each disposition rests on were checked by hand at this head, never taken from a
reviewer: `stage_tree` copies with `shutil.copytree`'s default (`scripts/check-plan-code.py`, `stage_tree`),
21 tracked symlinks (`git ls-files -s`, mode `120000`), `child_env` sets `PYTHONDONTWRITEBYTECODE`, the staged
tree is a temp directory holding `HARNESS_TREE` only (no `.git`), and `_importers` is today's import closure.
The §5 scorer (`r3f_opts.py`, session scratchpad `fold586/`) was read to answer C-F13 and C-F8: its 3(c) helper
`literal` includes `_importers`, and its 3(b) test is `anc(p) & listed`, the any-ancestor reading.

## Dispositions

| Finding | Severity | Disposition | Spec section changed |
|---|---|---|---|
| **X-F1** a PR undoing master's R..BASE addition nets `R..HEAD` to empty | High | FIXED. Rule 3 reads `Δ = (R..BASE) ∪ (BASE..HEAD)`, both name-status lists unioned as (path, status) pairs, never netted; Codex's `docs/activated` case is a §8.3 PICK | §2 *The comparison set*, Use 3; §3 table; §8.3 |
| **X-F2** the plain pass warms a cache the traced pass then reads instead of the repo file | High | FIXED. The traced run is FIRST, cold, in a fresh copy of the staged tree with an empty `CHILD_HOME`; the plain control runs second in another fresh copy | §2 Record (steps 1-2); §8.4 |
| **X-F3** `readlink`, `openat2`, `rename`/`unlink`, `execve`'s executable not extracted | High | FIXED. Tracing by strace class (`%file`, `%process`), every `%file` path at least `probed`, successful `execve` and `readlink` are `reads`; unsupported calls (`io_uring_setup`, `unshare`, unreadable `clone` flags) are INCOMPLETE | §2 recorder, *What makes a trace INCOMPLETE*; §8.4 |
| **X-F4** the blanket `.git` drop loses `git -C "$GITHUB_WORKSPACE" ls-files` | High | FIXED. Three cases by component: a fixture's `.git` dropped; the real checkout's working tree mapped and counted; the real checkout's `.git` sets `git_membership`, and rule 3(d) picks on ANY change in `Δ` | §2 *`.git` reads, exactly*; Use 3(d); §5 git-only spawners; §8.3, §8.4 |
| **X-F5** `stage_tree` dereferences repo symlinks, erasing provenance | High | FIXED. A staging provenance map (staged path to repo link and resolved target, through every link); a read records all of them; a link leaving the roots is INCOMPLETE | §2 normalisation, *staging provenance*; §8.4 |
| **X-F6** copy-on-clone cwd is wrong under `CLONE_FS` | High | FIXED. One cwd per shared filesystem context, split only without `CLONE_FS`; `unshare(CLONE_FS)` and unreadable flags INCOMPLETE; `AT_FDCWD`'s `-yy` label, where present, is the authority | §2 normalisation, *the working directory*; §8.4 |
| **X-F7** pending comparisons fall out of the window; final-push-only counting | High | FIXED. `shadow-compare` is stateless over a fixed shadow start date (pending retried every run), uploads a ledger artifact that keeps decided rows; misses are over EVERY push, against each push's own base, and latch | §2 *Shadow mode's data and its comparator*; §8.1; §8.6 |
| **C-F1** a master add/delete of a `probed`/`reads` path over R..BASE neither stales nor picks | High | FIXED by the same `Δ`: the probe flip and the deletion twin are both in `Δ`, so 3(a) picks. The old staleness row ("MODIFIED over R..BASE → today's rule") is REPLACED by a pick, which is today's selection or more | §2 Use 3(a); §3 table; §8.3 |
| **C-F2** a symlink outside the tree pointing in, deleted before parsing, drops reads as `complete` | High | FIXED. A successful open takes its path from the kernel's `-yy` fd label; failed and path-only calls resolve through a link table of links created during the trace (`symlink*`/`link*`/`rename*` traced); an unresolvable link that could name a staged path is INCOMPLETE. The `_cli` fixture is a §8.4 case | §2 normalisation; §8.4 |
| **C-F3** shadow mode has no data source | High | FIXED. Three named components: `verdicts-<run_id>-<attempt>-<shard>` (`verdicts.jsonl`, per mutant and control, with a `complete` line), `selection-<run_id>-<attempt>`, both `retention-days: 90`, and `scripts/shadow-compare.py` run by a daily `shadow-compare` job | §2 shadow mode; §8.1 |
| **C-F4** the hand-written syscall list is incomplete (`clone3`, `openat2`, `readlinkat`, `CLONE_FS`, `io_uring_setup`) | Medium | FIXED with X-F3 and X-F6: strace classes, `io_uring_setup` INCOMPLETE, `CLONE_FS` modelled, build step 1 MEASURES the calls | §2 recorder; §4.2 |
| **C-F5** warm state and laundered cross-suite flows | Medium | FIXED. Traced run first and cold (X-F2); `wrote` is recorded; a target reading or probing any path another target's run wrote is INCOMPLETE (`cross-run flow`). `PYTHONDONTWRITEBYTECODE` (already set) keeps bytecode out of it; the refusal count is UNMEASURED and build step 1 counts it | §2 *Cross-run flows*; record `wrote`; §4.3; §8.4 |
| **C-F6** one unseeded recording is one draw | Medium | FIXED. Every recording runs under the same two fixed `PYTHONHASHSEED`s; the sets are unioned, a difference marked `seed_dependent` | §2 Record; record fields; §8.5 |
| **C-F7** the recording env is not the shard's; image, strace, Node unkeyed | Medium | FIXED. One YAML anchor supplies the `mutation-sweep` step env to both jobs, with a PR shard's values and PR `GITHUB_*` event values set by the recorder; the VALIDITY KEY adds strace version, Node minor and runner image; a mismatch at `sweep-select` is today's rule. A shard on a different image than `sweep-select` cannot re-select without breaking the one-list stride, so it is LOGGED and counted as drift (§4.4), stated rather than hidden | §2 *The shard's environment*, Store, Resolve; §3 table; §4.4 |
| **C-F8** "under a listed directory" undefined | Medium | FIXED. The deepest ancestor of P that existed at R must be in `listed`. §5 now says the figures were scored with the wider any-ancestor reading, so 3(b)'s share is an upper bound | §2 Use 3(b); §5; §8.3 |
| **C-F9** `.git` prefix vs component; the "must count" side | Low | FIXED with X-F4: decided by component; `.github/workflows/ci.yml` and `.githooks/pre-push` are §8.4 negatives that DO count; the staged tree has no `.git`; `GIT_DIR`/`GIT_WORK_TREE` set refuses every target. ⚠ The half said "no `.git` read must count"; X-F4 shows one (the real checkout reached by `$GITHUB_WORKSPACE`), so the fold follows X-F4 there | §2 `.git`; §3 table; §8.4 |
| **C-F10** traced timeout unspecified | Low | FIXED. `SUITE_TIMEOUT` × `TRACE_FACTOR`, measured in build step 1; a timeout is INCOMPLETE; refusals tallied by reason | §2 Record, build step 1 |
| **C-F11** `/proc/self/fd/N` needs an fd table | Low | FIXED. Resolved only through the same line's kernel fd label; any other `/proc` fd/cwd/root path is INCOMPLETE | §2 normalisation |
| **C-F12** shadow definitions: push, flake, the 6-day figure | Low | FIXED. Every push, not the final one (with X-F7); a differing mutant is re-run 3 times on each tree, flaky → INCONCLUSIVE, stable → a miss; "about 6 days" restated as a PREDICTION with the two red master runs and the every-push rule as reasons it is optimistic, checked by the ledger | §2 *A MISS, precisely*; §7 Q4 row (prediction only; the decision is unchanged); §8.6 |
| **C-F13** rule 3(c) dropped today's import closure | Low | FIXED. 3(c) keeps `_importers`; §5 states the figures were scored with it (verified in `r3f_opts.py`) | §2 Use 3(c); §5; §8.3 |

**Not re-scored, and said so in §5.** Two fold changes move §5's figures in opposite directions: `Δ` picks where
a stale set used to fall back (more picks, lag columns only), and the deepest-existing-ancestor rule narrows 3(b)
(fewer). The net is UNMEASURED; shadow mode measures it.

## NEEDS THE OWNER

None. No finding needed a decision changed: every fix is a mechanism inside §7, and none moves the goal. The one
place a fix touched a decision's TEXT is Q4's row, where "about 6 days" is restated as a prediction; the decision
(shadow mode for 20 complete PRs) is unchanged.

## Verdict

**Codex: NOT CONVERGED. Claude: NOT CONVERGED.** Twenty findings, all fixed in the spec; the fixes are
non-trivial (new recorder rules, a new comparison set, three new CI components), so a further round is owed.

**Next: round 2, ONE half, Codex** (rounds 2+ alternate, `docs/review-method.md` → *Round topology*), on the
fold commit, with `REVIEW GAP: claude — alternation` in the round-2 coordinator. Its brief should ask it to
refute the fold's new rules in particular: `Δ`, the cross-run rule, the `CLONE_FS` model, the link table and
staging provenance, `git_membership`, and the comparator's stateless re-scan.
