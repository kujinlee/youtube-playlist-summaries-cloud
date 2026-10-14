<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established.

## High

**H1 — The replacement inventory prescription overstates its coverage and misstates what it reads.** `.agents/skills/handoff/SKILL.md:15`, `.claude/hooks/enforce-handoff-path.sh:68–69`, and `docs/memory/a-vendored-line-number-has-no-owner.md:21` prescribe default `git grep` to find “every site” and explain that it reads the index.

Concrete fixtures refute both claims:

| Fixture | Default `git grep -l session-start-hook` |
|---|---|
| Untracked matching file | Missed |
| Gitignored matching file | Missed |
| Nested checkout containing a matching file and bare `*` ignore | Missed |
| Initialized, registered submodule | Missed; `--recurse-submodules` found it |
| Matching content staged, then removed from working copy | Missed; `--cached` found it |
| Tracked symlink whose untracked target contains the match | Missed |

Default searches read tracked **working-tree content**, not staged content. Searching a commit explicitly reads that committed tree. The handoff skill is found through its tracked `.agents` file; Git does not follow its `.claude` alias.

The cited round-3 Claude H1 expressly bounded its claim to tracked content and disclosed the untracked limitation. The fold dropped that bound from the actionable instructions. Its new “instrument that cannot have the problem” lesson therefore replaces an implementation-specific prescription with an incomplete inventory prescription.

**Repair:** specify the corpus and content version being inventoried, and separately inspect ignored files, nested repositories, submodules, and vendored dependencies where applicable.

## Medium

**M1 — The GNU-grep provenance withdrawal remains incomplete.** `docs/process-rationale.md:372` and `scripts/check-handoff-path.py:58–61` still say round 3 “measured” the GNU behavior and that each prescription was verified against available binaries. The filed Codex review explicitly says the GNU binary could not be built; its evidence was the source option table. The new memory paragraph now discloses that distinction, but these two sites—including the least-protected code comments—retain the stronger account. This establishes another incomplete withdrawal. Qualify both sites consistently; the underlying option-table finding need not be withdrawn.

**M2 — Two sites retain the lesson this commit says it retired.** `docs/process-rationale.md:372` still concludes “The repair is to prescribe none” and recommends checking tool-specific symlink behavior. `scripts/check-handoff-path.py:54–66` likewise says no search command is prescribed and calls prescribing no flag the repair. Meanwhile, the rewritten skill and memory prescribe `git grep` for the same missed inventory. Rewrite the explanation around the two distinct corpora: repository inventory and vendored-plugin lookup.

**M3 — The first hint-trigger label remains incompletely repaired.** `.agents/skills/handoff/SKILL.md:17` still describes only “External mode (the store is outside the project),” omitting the linked-worktree case added elsewhere. Furthermore, `.claude/hooks/enforce-handoff-path.sh:77–78` and `docs/plugins.md:87` still label the condition as a store outside the project.

An isolated execution of the installed hook with `data_dir=a/b`, default single mode, and a valid session ID printed a hint pointing to `<project>/a/b/remember.md`: the store remained inside the project. The corresponding `data_dir=notes` control printed no hint. Round-2 Claude M2 already documented this nested-relative case.

Name the actual comparison—`REMEMBER_ROOT != PROJECT_DIR`—and explain its causes consistently across the sites.

## Low

**L1 — The refusal fixes wrapping by dropping the hook locator’s suffix.** Rendered output now contains only:

```text
~/.claude/plugins/cache/claude-plugins-official/
```

The path is unbroken, but it identifies the cache directory rather than `remember/<version>/scripts/session-start-hook.sh`. The one-line `git grep` command locates repository references, not the installed plugin assignment. Restore a complete hook locator or provide an executable discovery command.

## Checked and found SOUND

- **Inventory counts re-derived:** `git grep -l session-start-hook origin/master` finds **6** files; the same query against `f6d240a5` finds **10**. Excluding `docs/reviews` gives **5** and **6** respectively. The added sixth non-review site is this branch’s memory lesson. Five original live stale-citation sites is correct; five raw-query matches is not.
- A filesystem walk following symlinks independently found **10 distinct physical matching files** at this commit. No additional live stale-locator site established.
- In both this worktree and the main checkout, `.claude/.git` and `.claude/.gitignore` are absent. Root `git grep` finds `.claude/hooks/enforce-handoff-path.sh`; `ls` confirms the handoff skill alias. The remembered nested-checkout configuration is not the current filesystem state.
- A tracked fixture marked `export-ignore -diff` in `.gitattributes` remained discoverable.
- Against the installed 0.33.0 hook, these commands returned **2** and **23** respectively:

  ```bash
  /usr/bin/grep -c 'REMEMBER_HANDOFF=' "$hook"
  /usr/bin/grep -c 'REMEMBER_HANDOFF' "$hook"
  ```

  The assignments are at 1168 and 1171; the bare token spans three variable names.
- `REMEMBER_HANDOFF_STATE` exists with the cited spelling and identifies the delivery-record mechanism. It is unique as a variable identity, **not** as a textual occurrence: nine lines contain the exact token; thirteen contain the substring including the legacy variable. Its references reach the record read at 1660, write at 1698, and cleanup at 1703. The symbol citation avoids the retired range’s under-bounding.
- Anchors **1159**, **1163**, and **1185** match the stale sentence, comment-block end, and correcting sentence. They are current version-specific measurements; vendor growth can move them. The two passages also retain the distance phrase “22 to 26.”
- **Real falsifier works on a copy:** control guard rc=0; removing every `.remember/remember.md` occurrence gives guard rc=1 and hook rc=2 with the correct destination in stderr; restoration returns rc=0. Self-test passes **10/10**.
- Stub refusal rendering gives rc=2, empty stdout, one unbroken command line, and no sentinel expansion. `bash -n` passes.
- All five handoff mutations were caught, with green controls before and after each mutation.
- CI extraction found **53 `python3 scripts/check-*` occurrences**. **52 were attempted:** 50 completed rc=0, `check-review-recorded` returned the expected rc=1, and the results-dependent count check could not run. The initially timed-out count audit was rerun successfully: **52 declared script counts verified**. `check-plan-code.py --self-test` passes **178/178**; `check-review-rounds.py` and `check-docs.py` pass.
- HEAD remains `f6d240a5`; worktree remains clean. No review file written.

## CANNOT RUN

**These are validation failures; treat this as NOT RUN wherever listed.**

- `check-test-counts.py --results jest-results.json`: rc=1 because the results file is absent. The unit suite was not run.
- Full `check-plan-code.py --mutate .` CI shard matrix was **not run**. The five handoff mutation checks do not substitute for that whole-manifest execution.
- PR-only checks were exercised with `--base origin/master`, without an actual PR event/body. Their event-dependent behavior is **NOT RUN**. The expected `check-review-recorded` red is not filed as a branch defect.
- Historical installation behavior, “always has” configuration claims, pre-0.33.0 hook growth, and complete cross-branch harness experiments were not replayed.
- Local guards ran on Python 3.14; CI pins 3.12. Exact CI interpreter parity is **NOT RUN**.

## Instruments

Commit message read first; committed fold and whole-branch diffs; all six prior reviews; cited historical-review context; Git and filesystem inventories; isolated index/worktree, ignored-file, nested-checkout, symlink, attributes, and registered-submodule fixtures; installed-hook inspection and store probes; copied-tree falsifier and refusal rendering; five controlled handoff mutations; CI-derived guard sweep and successful count-audit rerun.

**Reviewed `f6d240a5`: 0 Blocking / 1 High / 3 Medium / 1 Low. Round is not clean.**
