# backlog-354-ts-gates — round 1, Claude half

Subject: `git diff origin/master...HEAD` on `backlog-354-ts-gates` (PR #402). Mandate: refute.

## What I ran

- `python3 scripts/check-merge-ready.py --self-test` in the worktree: **206/206, rc=0**.
- The 10 mutation entries this branch adds or re-binds (7 new + 3 re-bound anchors), each applied to a
  copy of the tracked tree and the suite run there: **every one goes red, and every `expect` case it
  names is among the `[FAIL]` lines** (4/4, 2/2, and 1/1 for the other eight). So the new cases do not
  pass for an ambient reason, and the three re-bound anchors (`fail.search` window, `fail =` gate
  skip, the `check-*` GATE_CODE narrowing) still test what their names say.
- The 40-PR replay (`replay5.py`, worktree checker): **11 of 40**, matching the claim.
- A probe harness calling `hold_reasons` on crafted diffs, plus three real git repositories built
  from copies of the repo's own TS/JS gates. Everything was under the scratchpad (`r354/`); nothing
  in the worktree was edited except this file.

## Findings

### M1 (Medium): block-commenting the #354 gate's own failure path still reads READY
`scripts/check-merge-ready.py:617` (`is_comment` only knows `#`) and `:659-688` (only removed lines are
read). Real git, copy of `scripts/check-service-confinement.ts`: put `/*` above and `*/` below the
`if (violators.length) { … process.exit(1); }` block. The diff has **only `+` lines and no removals**,
and `hold_reasons` returns `[]`, so the PR reads **READY**. This is the same gate and the same effect
(the gate exits 0 whatever it finds) as the backlog row's measured case. In JavaScript a `/* */` around
a block is the usual way to switch something off for a while, not an evasion. (The `//`-per-line form
does hold: `// return 1;` in `check-deployed-bundle.ts` was held, measured.) The module header's
stated bound covers "a failure line re-added inside dead code", but here nothing is removed or re-added.
It also makes the dashboard entry overclaim (`docs/dashboard-entries.md:17591-17593`, "one of them could
be switched to always pass … It now holds that change"). Possible fix: in a Node gate, any ADDED
line that opens or closes a block comment (`/*`, `*/`) within `FAIL_WINDOW` of a failure-path line on
the old side should hold. Or narrow the prose to "rewriting an exit".

### M2 (Medium): removing the TS gate's CI invocation reads READY
`scripts/check-merge-ready.py:521-523`. The TS gates run through npm, not by path. `ci.yml:256-257`
is `run: npm run check:confinement`, and `package.json:19` maps that name to the `.ts` file.
- Removing or rewriting the `ci.yml` line gives `hold_reasons` = `[]`. `GATE_REF`
  (`scripts/check-|\.claude/hooks/|--self-test|--mutate`) does not match `npm run check:confinement`.
- Changing `package.json`'s `"check:confinement"` to `"true"` gives `[]`, because `package.json` is
  not in `GATE_CALLER`.

Both were probed through `hold_reasons`. For Python gates the invocation half was closed in r1 CLAUDE M1
(a removed `scripts/check-…` call holds). This branch makes TS gates "gate code" but leaves their only
invocation path unseen. So the rule's direct analog of backlog #354 is still a false READY with
distance zero. Possible fix: add `package.json` to `GATE_CALLER`, and add `npm run check:` (or any
`package.json` script that names a `scripts/check-*` file) to `GATE_REF`.

### L1 (Low): in Node files, `//` and `/* */` comments are treated as code, so the docstring is false for them and comment edits can be held
`scripts/check-merge-ready.py:617-619` ("Python, shell and YAML all use `#`") and `:663` ("A comment
line neither counts nor anchors"). Both are now applied to TS/JS unchanged. Probed:
- In `scripts/cloud-sync.ts` (not a gate), rewording `// retry the upload twice` next to a `throw` is **HELD**.
- Rewording a JSDoc line `* Uploads a file.` next to a `throw` is **HELD**.
- A comment `// on failure we process.exit(1) below` anchors a hold on an unrelated `const n = 3` → `4`.

All of these fail closed, so they are false holds, never a false READY. The fix is a Node comment
rule in `is_comment` chosen by `NODE_SRC`, or at least a correction to the two prose lines.

### L2 (Low): the Node idioms miss common failure forms, including the repo's own JS self-test tally
`scripts/check-merge-ready.py:513-514`. Each of these reads READY next to an `if (bad) {` hunk:
- `reject(err)` → `resolve()`
- `return Promise.reject(new Error(…))` → `Promise.resolve()`
- `process.exitCode ||= 1` removed

In a real git repository, dropping `bad++` from `scripts/ts-comment-spans.mjs:70` (the `✗` branch,
the only thing that makes `process.exit(bad)` at `:95` non-zero) reads **READY**. The Python analog,
`failures += 1`, is matched by `\bfailures?\b`. These sit within the stated bound ("a gate whose failure
path uses none of FAIL_PATH's idioms is unseen"). They are listed so the bound is a decision rather
than an accident. `✗` and `\bbad\+\+` cost nothing to add. Its oracle is not run directly in CI, so
this stays Low.

### L3 (Low): the replay's "before and after" has no TS/JS edits in its population
Backlog row #354 (`docs/backlog.md:336`) and `docs/dashboard-entries.md:17593,17599` say 11/40 before
and after. That is true (re-run: 11 of 40). But per `git log --first-parent origin/master`, **0 of the
last 40, and 0 of the last 200, merged PRs touched a `scripts/*.{ts,mts,cts,js,mjs,cjs}` file** (13 of
the last 400 did). So the replay could only measure the scoping decision (#397). It cannot measure what
the TS half costs. I measured that half: over those 13 PRs, comparing the `origin/master` checker with
this branch's, one PR (`df00f101`, PR #2) newly gets TS holds (`audit-timestamps.ts`,
`rerender-html.ts`). It was already held for other reasons, so the hold count is unchanged. The cost
looks small, but the prose should say the 40-PR population contains no subject files and quote the
13-PR figure instead.

## Checked and not a finding
- `process.exit( 1 )`, `process.exit(code)`, `process.exit(1)` without a semicolon, `process.exitCode=1`
  without spaces: all held. `process.exit(0)`, `process.exit()`, `exitCode = 0` removed: not held. The
  lookahead behaves as the mutations say.
- `.ts`/`.mjs` under `scripts/ci/` and `.claude/hooks/`: held, and they get `NODE_FAIL_PATH` through the
  extension. `scripts/lib/x.ts` is not gate code, but no `scripts/` subdirectory holds TS today
  (`ci/ fixtures/ mutations/` only). `.tsx` is unseen, and none exist.
- Wrapping `process.exit(1)` in `if (false)` on the same line, and changing `if (violators.length)` to
  `if (false)`: both held.
- Python gates are unaffected (`page_chrome.py`'s stub `throw` is not a failure path; that case
  reddens under the "every gate" mutation).
- Case count 199 → 206 = 6 synthetic + 1 real-git case. The pin is 75 → 82, the total 2105 → 2112, and
  three anchors were re-bound, all consistent with the diff.

VERDICT: NOT CONVERGED
