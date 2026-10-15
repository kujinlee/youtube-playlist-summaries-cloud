<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established. **Reviewed `dd595394`; NOT CONVERGED.**

**Thrashing, not prose floor. The architecture-review condition is met.**

| Finding | Evidence that the preceding fix caused it |
|---|---|
| r4 Claude H1 | `2ad7038a` replaced “reads the index” with “reads working-tree content”; index-masked fixtures refuted the replacement. |
| r4 Claude H2 | That fold substituted another store-position label instead of the requested comparison; its own `data_dir=notes` control contradicted it. |
| r4 Claude H3 | The fold edited the memory paragraph while retaining its retired “ONE INSTRUMENT” headline. |
| r5 Codex H1 | `7bf8867c` added “two that agree can”; matching filenames concealed different indexed and disk content. |
| r5 Codex H2 | That fold introduced the immediate-child label, refuted by `./notes` and `..`, and left `plugins.md` unrepaired. |
| r5 Claude H1 | `1a2cc8de` withdrew the false label by deleting the true linked-worktree clause, reopening r4 M3. |

**Can a redesign remove it? Yes:** one canonical operational description, with citations from the other sites, removes independently maintained copies drifting or losing clauses during a withdrawal. It does not establish that the canonical description correctly interprets the vendor; behavioral controls remain necessary. That remaining risk is different from six-copy disagreement.

A guard can mechanically require the canonical statement and its citations, and reject restatements. Alternatively, generated or exactly delimited excerpts can be compared mechanically. Arbitrary paraphrases cannot be checked for semantic agreement reliably. `scripts/check-explainer-delivery.py:45` already demonstrates the structural approach. **Architecture review is owed; no redesign was implemented here.**

## High

**H1 — The restored worktree explanation overgeneralizes the resolver’s conditional redirect.**

Affected: `.agents/skills/handoff/SKILL.md:19`, `.claude/hooks/enforce-handoff-path.sh:108`, `docs/plugins.md:87`.

The ordinary main/worktree result reproduces **3/3**, with `=== REMEMBER ===` present on every execution. The broader assertion does not survive all requested cases:

| Case | Controlled result |
|---|---|
| Main checkout, default configuration | No hint |
| Ordinary linked worktree | Hint to main checkout |
| Worktree created from another worktree | Hint to original main checkout |
| Subdirectory of linked worktree | Hint to main checkout |
| Main checkout moved, then `git worktree repair` | Hint to moved main checkout |
| Bare-repository worktree, default configuration | **No hint; store remains local** |
| Ordinary submodule | No hint; store remains in submodule |
| Linked worktree, relative `data_dir=notes` | Hint to `<main>/notes/remember.md` |
| Linked worktree, absolute `data_dir=<worktree>/localnotes` | **No hint; store remains in worktree** |

Moving the disposable main checkout **without repair** also produced a completing hook with a local store and no hint; that demonstrates the fallback when Git metadata cannot resolve the main checkout.

The vendor checks common-dir versus git-dir, then verifies a candidate main checkout. A `.git` **file alone is insufficient**—the submodule control demonstrates that. Absolute `data_dir` also bypasses the main-relative placement.

The restored clause is correct for ordinary, resolvable linked worktrees with default configuration. Presented as the general mechanism, it becomes another overbroad prediction. Preserve the measured case and state the redirect’s conditions and configuration boundary.

## Medium

**M1 — The hook still emits the withdrawn biconditional and incomplete derivation.**

`.claude/hooks/enforce-handoff-path.sh:101` still omits the `/` stripping guard, root case, empty-parent fallback, and no-slash fallback. At `:103` it still says:

> “the hint fires iff that string differs from PROJECT_DIR”

At `:114`, the same refusal says that claim is withdrawn. A copied-tree sever produced the actual refusal containing **both statements**, with guard rc=1, hook rc=2, and empty stdout.

Controlled `per_session` executions printed hints while the strings were equal. The skill’s corrected derivation and narrowing therefore did **not** reach the hook, contrary to the fold’s L1/L2 closure claims.

**M2 — The committed-tree search figures and untracked-file explanation do not reproduce.**

With needle `session-start-hook`, explicit `.` for filesystem searches, and stdin closed:

| Invocation | `dd595394` result |
|---|---:|
| `git grep -l session-start-hook` | **14** |
| `/usr/bin/grep -rl session-start-hook .` | 14 |
| `rg -l session-start-hook .` | 12 |
| `rg --hidden -l session-start-hook .` | 14 |

All filesystem matches correspond to tracked matches after path normalization. `git grep` against **both `dd137dbb` and `dd595394` returns 14**; the r5 Claude review is committed already.

Thus **13/14/12/14** and “the +1 is the untracked review file” cannot be replayed at the reviewed committed tree. This does not prove the earlier measurement never occurred; it requires its actual snapshot to be identified.

**M3 — The GNU runtime-provenance withdrawal still retains an affirmative contradiction.**

`scripts/check-handoff-path.py:68` correctly says the GNU evidence came from **3.12’s source option table**, not a runtime probe. At `:73`, it still asserts:

> “Each version was checked against the binaries the author happened to have”

`docs/process-rationale.md:371` retains the equivalent assertion beside its source-only qualification. This is the previously identified withdrawal left incomplete, rather than a newly established fourteenth instance.

## Low

**L1 — The list copies still diverge.** `.agents/skills/handoff/SKILL.md:19` uses ①②③; the hook at `:98`, `:116`, and `:118` uses `(1)(2)(3)`. The colon and noun-phrase repair landed, but marker agreement and the `.handoff_mode` gloss remain inconsistent. The guard’s repaired locator sentence at `scripts/check-handoff-path.py:48` is grammatical.

**L2 — The new memory entry’s 294/297 and 297/297 figures lack an invocation.** `docs/memory/an-instrument-that-edits-the-repo-corrupts-its-peers.md:106` identifies tree contents but names no script, arguments, interpreter, or measured ref. The figures cannot be independently replayed as stated.

A partial copy demonstrably gives rc=2 controls for the handoff, explainer-delivery, and surface-recall guards. That confirms the hazard, **not the unidentified 297-case measurement**.

## Checked and found SOUND

- **The named 29-command set returns rc=0 under both Python 3.14.4 and 3.12.9.** Both count audits completed: 52 declaring scripts checked by execution. `check-memory-link`’s advisory rc=0 remains no measurement of an absent corpus.
- **All five derivation branches:** direct execution of the vendor’s parameter-expansion/case block confirmed trailing-slash stripping, preservation of `/`, the root case, empty-parent fallback to `/`, and no-slash fallback to `.`. The skill describes these correctly.
- **Fourteen `data_dir` rows:** thirteen had positive controls. Hint results were: `notes` no; `a/b` yes; `.` no; `./notes` yes; `notes/` no; `a//b` yes; absolute child no; absolute outside yes; child symlink outside no; `..` no; unset no; empty no; `~` yes. `/` is excluded below.
- **Three-way emission condition:** all eight truth-table combinations of the actual emission block behaved as the disjunction requires. Full-hook single, per-session, and degraded executions had positive controls. No fourth trigger or suppression on a completing controlled row was established.
- **Six-site search-limit agreement:** all carry the same four-limit set—content agreement proves nothing; disagreement has innocent causes; traversal is tool-specific; outside-repository Git errors require handling. `.git` is now included in the dashboard. Wording differs; the **set agrees**. The dashboard remains a dated retrospective.
- **Ripgrep attacks:** controlled fixtures confirmed hidden-path, ignore-rule, and binary omissions. Further omissions came from **symlinked directories** and `RIPGREP_CONFIG_PATH` supplying exclusions and `--max-filesize`. `--no-config` recovered the configuration omissions; `--hidden --no-ignore -a -L` recovered the fixture population. CRLF, missing final newline, and the selected Unicode/`--no-unicode` probe retained their matches. These additional omissions fit the existing tool-specific-reach caveat.
- **Deleted-clause audit:** examined removed clauses in `7bf8867c..dd595394`, rather than only retired phrases. The worktree clause is restored; the true nested-store, per-session, degraded-mode, and locator information remains represented. **No new deleted-true-clause withdrawal established.** That does not certify withdrawal completeness; M1/M3 remain.
- **Copy-only enforcement:** control 0/0 → sever 1/2 → restored 0/0. Source skill hash unchanged. All five handoff mutations bound once and were killed through their named failures under Python 3.12, over green controls.
- **Memory persistence:** the new entry exists in the `dd595394` blob and is byte-identical to the read-only live-store file. SHA-256: `f26f31ced609231e82ea1be150fc30f3395d69402f524e1302076b672e455879`. A disposable Git repository reproduced `checkout --` discarding an uncommitted edit.
- `plugins.md`: **260/260** at base and reviewed commit. Dashboard: **307** `^## ` headings. `bash -n .claude/hooks/enforce-handoff-path.sh`: rc=0, syntax only. Worktree explanation present at all three sites.
- Reviewed worktree remains clean. **No review file written.**

## CANNOT RUN

**These are validation failures; treat this as NOT RUN.**

- `/` `data_dir` row: rc=127, missing `=== REMEMBER ===`, source-loading error. Its absent hint is **not** a negative behavioral result.
- Actual Claude host/UI delivery of the refusal.
- `check-test-counts.py --results jest-results.json`: results file absent.
- Full `--mutate .` shard matrix and actual PR-event forms.
- Exact historical four-edit loss and unidentified 294/297 experiment. Mechanism replay and file persistence do not reconstruct those historical measurements.

The expected review-recorded red and absent withdrawal guard are not filed as defects.

## Instruments

Required commit messages read first, in order: `dd595394`, `dd137dbb`, `1a2cc8de`, `d80b12f9`. Reviewed fold/range diffs, r1–r5 records, process rules, installed 0.33.0 resolver/context/emission source, disposable Git/search fixtures, isolated hook executions, copied-tree refusal, and controlled mutations.

**Every grep measurement used `/usr/bin/grep` explicitly.** No Git command ran in the forbidden main checkout. Guard subprocesses used closed stdin.

Exact 29-invocation set, under **each** interpreter; `+self-test` means both bare and `--self-test`:

```text
check-docs
check-anchors +self-test
check-arch-findings
check-backlog-closure +self-test
check-explainer-delivery
check-features +self-test
check-gate-falsifiability
check-handoff-path +self-test
check-main-drivable
check-memory-link
check-plan-file-tags +self-test
check-plan-task-order
check-producer-enumeration
check-python-pin +self-test
check-rc-contract +self-test
check-review-rounds
check-roadmap-consistency
check-selftest-counts +self-test
check-selection-card --self-test
check-surface-recall +self-test
```

Invocation form: `python3 scripts/<name>.py </dev/null`, repeated with `python3.12`. Additionally ran `check-review-rounds --self-test` under both interpreters. **This selected set is not the CI suite.**
