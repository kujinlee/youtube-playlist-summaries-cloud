<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established. **Reviewed `7bf8867c`; this round is not clean.**

## High

**H1 — Agreement does not make the cross-check trustworthy, and disagreement does not establish the stated cause.**

This affects the skill `:17`, hook `:76`, guard comment `:77`, process rationale `:371`, memory lesson `:21`, and dashboard `:14860`.

The three requested failures **are detected when all three results are compared**:

| Fixture | Default Git search | Cached search | Filesystem search |
|---|---|---|---|
| `assume-unchanged`, replaced content | Stale indexed match | Stale indexed match | Replacement match |
| `skip-worktree` | Omits subject | Finds indexed subject | Finds disk subject |
| Tracked file deleted from disk | Omits subject | Finds indexed subject | Omits subject |

Each sever had passing controls before and after. But the stronger prescription fails:

- **All three can agree while reading different content.** With indexed `NEEDLE OLD` and disk `NEEDLE replacement` in an `assume-unchanged` file, every `-l` search lists the same paths. Default Git still returns `NEEDLE OLD`.
- **The permitted `rg` alternative can share Git’s omission.** An ignored matching file was missed by default Git, cached Git, and default `rg`; `/usr/bin/grep -rl` found it.
- **Default filesystem traversal can share another omission.** A tracked symlink to an outside matching target was missed by both Git searches and `/usr/bin/grep -rl`; `/usr/bin/grep -RSl` supplied the positive control.
- **Disagreement also occurs without any masked or deleted tracked content.** A committed binary matched both Git searches but not default `rg`. A case-only rename on this case-insensitive filesystem left `git status` empty while Git listed `Subject` and filesystem grep listed `subject`.

Ignored files, `.git` internals, and registered submodules also produced disagreement on otherwise clean tracked trees. An invocation outside a repository returned Git rc=128, requiring error handling rather than result-set comparison. These are selected fixtures, **not a population-wide false-alarm estimate**.

**Repair:** specify traversal, exclusions, path normalization, binary handling, and error handling. Compare content when content matters. Withdraw “two that agree can” as a completeness guarantee.

**H2 — The new hint label is false, and the claimed three-site repair reached only two sites.**

The installed **0.33.0 hook**, executed with isolated homes and projects, produced:

| `data_dir` | Hint |
|---|---|
| `notes` | No |
| `a/b` | Yes |
| `.` | No |
| `./notes` | **Yes** |
| `notes/` | No |
| Absolute immediate child inside project | No |
| Absolute directory outside project | Yes |
| Immediate-child symlink to an outside directory | **No** |
| `..` escaping project | **No** |
| Unset / empty | No / No |

`./notes` is physically an immediate child but prints a hint. `.` and `..` are not immediate children but print none. The implementation compares **lexical strings**: the computed parent `REMEMBER_ROOT` against `PROJECT_DIR`; it does not resolve ancestry.

Moreover, `docs/plugins.md:87` still asserts **“a resolved store root ≠ the project dir ITSELF”**—the exact position this commit retires. `git show 7bf8867c --numstat` confirms the fold did not edit that file. `docs/process-rationale.md:408` also retains the older affirmative “external mode” enumeration.

This supplies a concrete counterexample to the published **“no twelfth”** withdrawal sweep. These are assertions, not quotations recording retirement.

**Repair:** name the actual string comparison and its limitations at every explanatory site.

## Medium

**M1 — The replacement count is correct in the skill but remains unrepaired in the memory lesson.**

Reproduced:

```bash
git grep -l session-start-hook origin/master
```

It returns **six tracked files**: the five original live sites plus `docs/reviews/claude/velocity-177-r5-claude.md`. The sixth genuinely is filed testimony; its `:161` contains the locator.

The skill `:15` now states both units correctly. However, `docs/memory/a-vendored-line-number-has-no-owner.md:21` still says **“all FIVE tracked sites”**, without the live-site qualification or sixth-file explanation. That was the other site explicitly named by r4 M1. The fold edited this same line and retained its count clause.

**M2 — Another memory correction leaves the retired success claim as a bold lesson.**

`docs/memory/a-harness-cannot-read-a-cause-from-a-childs-text.md:7` explicitly says round 13 refuted the repairs described as having worked and that they remain unfinished. At `:21`, the file still leads with:

> **The repairs that worked were all SUBTRACTIVE or NARROWING**

Its enumeration includes the structural-marker and identifier-validator repairs that `:7` identifies as still dropping real exceptions and inventing fake ones. This is an affirmative lesson beside its own correction, not a historical quotation—the recurring incomplete-withdrawal shape.

Rewrite the lead-in and distinguish attempted repairs from established outcomes.

## Low

**L1 — Only one of the two revised locators is a discovery command.** The hook `:81` prints `ls …/remember/*/scripts/session-start-hook.sh`; it finds exactly one installed hook today. The guard comment `:49` contains the bare glob path. Pasting that executes the SessionStart hook instead of discovering its path. In isolated caches, zero matches gave rc=1 for `ls` and rc=127 for the bare path; two matches made `ls` list both, while the bare form executed the first script with the second path as an argument. Prefix the second locator with an explicit discovery command.

**L2 — The fragment fix did not fix the fragment.** The skill’s former `:17`, now `:19`, still reads “THREE things print it, not one. **the store directory…**”; the list lacks an introduction. The hook preserves “THREE things print it: …”. Bold formatting did not restore the skill’s grammar.

**L3 — “14/14 green” has no reproducible invocation set.** The commit names neither fourteen commands nor their arguments. The filed r4 review describes a different, 52-invocation sweep. A closed-stdin bare selection-card invocation returns rc=2, whereas its `--self-test` passes. Publish the exact set; the historical ratio cannot be independently replayed as stated.

**L4 — The live skill retains the unversioned GNU claim.** The three provenance passages correctly restore **3.12**, but `.agents/skills/handoff/SKILL.md:17` still asserts “GNU grep has no `-S`” without that bound. A later release adding `-S` would invalidate this instruction’s account. Apply the version qualification here too.

## Checked and found SOUND

- **Layer-2 shell falsifier:** copied-tree control guard/hook rc=0; removing every `.remember/remember.md` occurrence produced guard rc=1 and hook rc=2. The hook emitted empty stdout and stderr containing `Write the handoff to:  .remember/remember.md`. An unrelated skill remained silent and allowed. Restoration returned both controls to rc=0. Actual host/UI delivery remains NOT RUN below.
- `python3.12 scripts/check-handoff-path.py --self-test </dev/null` passed **10/10**: seven text cases and three file cases.
- All five mutation anchors bind once. Each mutation was also executed under Python 3.12: control rc=0 → mutant rc=1 with its expected named failure → restored control rc=0.
- `docs/plugins.md` has **260 lines** at both base and reviewed commit; its budget is 260. Dashboard `^## ` headings reproduce **306 → 307**.
- Installed hook measurements reproduce **2,027 lines**, **two** `REMEMBER_HANDOFF=` matches, and **23** bare-token matches.
- GNU grep **3.12**’s downloaded source has no uppercase `S` in `short_options`. The three restored provenance qualifications are correct and remain valid as historical claims if a later release adds it. [GNU 3.12 source archive](https://ftp.gnu.org/gnu/grep/grep-3.12.tar.xz)
- Python **3.12.9** is available; the named guard set below was run with it. The pin guard confirms the interpreter matches the CI major/minor pin.
- The longer count-audit rerun completed successfully: **52 declaring scripts, every count verified by execution**. The initial 120-second timeout was a harness limit.
- Remaining “eighth,” “ninth and tenth,” “prescribe none,” and “ONE INSTRUMENT” occurrences identified in the withdrawal passages are explicitly historical or retired quotations; they are not filed merely for matching those phrases.
- Shell syntax passes. Tracked worktree remains clean. No review file written.

## CANNOT RUN

**These are failures to validate; treat this as NOT RUN wherever listed.**

- **Actual Claude host/UI delivery of the refusal.** Shell execution proves stderr and exit status, not what the user sees. Official documentation establishes that PreToolUse exit-2 stderr reaches Claude as a tool error; that does not substitute for observing the installed UI. [Claude hook output contract](https://code.claude.com/docs/en/hooks#exit-code-2)
- `check-test-counts.py --results jest-results.json`: rc=1 because the results file is absent.
- Bare `check-selection-card.py` with closed stdin: rc=2 because no card payload exists. Its separate self-test passed **59/59**.
- Full `check-plan-code.py --mutate .` shard matrix and actual PR-event forms of the PR-only guards.
- GNU binary replay, pre-0.33.0 historical installation/growth, historical configuration correctness, and complete cross-branch harness experiments.

The expected `check-review-recorded` red is **not filed as a defect**.

## Instruments

Required commit messages read in order: `7bf8867c`, `2ad7038a`, `f6d240a5`; r1–r4 review records; committed fold and whole-branch diffs; position-based prose/comment sweeps; Git 2.49.0 fixtures; normalized filename comparisons; real isolated hook executions; copied-tree enforcement; controlled mutations; glob zero/one/several probes; GNU source inspection.

The explicitly selected guard set used `python3.12 scripts/…`, with stdin closed:

```text
check-docs.py
check-anchors.py
check-memory-link.py
check-review-rounds.py
check-handoff-path.py
check-handoff-path.py --self-test
check-selection-card.py
check-dashboard-entry.py --base origin/master
check-plan-file-tags.py
check-explainer-delivery.py
check-plan-task-order.py
check-selftest-counts.py
check-python-pin.py
check-plan-code.py --self-test
```

Thirteen completed rc=0; bare selection-card was NOT RUN. Additional invocations: selection-card `--self-test`, test-counts `--results jest-results.json`, and review-recorded `--base origin/master`. This selected set is **not represented as the unidentified historical “14/14.”**
