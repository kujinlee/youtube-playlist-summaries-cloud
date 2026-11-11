# session-state — round 3, Claude half (adversarial, mandate: REFUTE)

Subject: PR #410, branch `session-state`, head `d24832e6`, `git diff origin/master...HEAD`.
Bet under test (decision-log, last `session-state` row): *no state in which the block is falsely
reassuring or attributes one PR's state to another, and no way to forge a line or the END marker.*

Every experiment below was run in a fresh `mktemp -d` world. Nothing in any checkout was edited.

## What held (executed)

- `python3 scripts/session-state.py --self-test`: **38/38**.
- `python3 scripts/check-plan-code.py --mutate . --only scripts/session-state.py`, run in a `git archive HEAD`
  copy with `node_modules/typescript`: **19 mutations, 19 killed, 19 attributed to the named case, 0 survivors**.
- **Line forgery:** `clean("a"+chr(cp)+"b")` over every code point except surrogates (0..0x10FFFF).
  `splitlines()` gives exactly one line for **all** of them. The only C/Z categories that survive are Cn and Co
  (unassigned and private use), and neither is a line break. Fullwidth `＝` (and U+207C, U+208C, U+FE66, all NFKC
  `=`) survives: `clean("x ＝＝＝ END IN FLIGHT ＝＝＝")` → `'x ＝＝＝ END IN FLIGHT ＝＝＝'`. Because it cannot start a
  line, it always sits after a `latest commit:`/`[id]` prefix. I count it as inert: informational, not a finding.
- **Budget, end to end:** I ran the real hook with a fake `git` on PATH whose `fetch` sleeps 100 s, and a fake `gh`
  that backgrounds `sleep 100` (a grandchild holding stdout) and then prints a PR. Elapsed was **40 s**. Output was
  `fetch failed … STALE` plus `OPEN PRS: CANNOT RUN`, which is honest, and the block ended with its END marker.
- **Same-named fork and ref drift:** the fork is not read, and drift shows only the note (cases plus mutations 13 and 14).
- **Real run** (blobless clone of origin, real `gh`): 7 PRs in 1.9 s. Every line is consistent with `gh pr list`.

## Findings

### F1 — P1 (the bet's named failure): another PR's commit subject and review files are shown as this PR's when the branch is STACKED or has MERGED ANOTHER FEATURE BRANCH
`scripts/session-state.py:287-288` (range `origin/master..{head}` / `origin/master...{head}`), and `:252-253`
(`baseRefName` is not requested).

Executed world: `w` has `master` and `parent` (a commit "PARENT PR: r1 recorded, next is fold" plus a review file).
`child` is branched from `parent` with no commits of its own, as a stacked PR. `mixer2` makes its own commit
"MIXER2 own: next is run Codex r3", then `parent` gains "PARENT PR: r2 fold, next is merge", then `mixer2` merges
`parent`. A clone `c` has a fake `gh` listing them as PRs #1, #2 and #3, and runs the real script:

```
  PR #2 `child` head f4ac76b8 · CLEAN · checks: NO CHECKS
      latest commit: PARENT PR: r1 recorded, next is fold
      review files added by this PR: 1
  PR #3 `mixer2` head 6ee55f35 · CLEAN · checks: NO CHECKS
      latest commit: PARENT PR: r2 fold, next is merge
      review files added by this PR: 1
```

Both lines carry PR #1's state, its step and its review file, as their own, and nothing flags it. The docstring
(`:14-15`, "the branch's OWN commits … never reported as this PR's") and the PR body say it cannot happen. The range
excludes only master. Commits merged in from any other branch, or inherited from a stacked base, are inside it.

Fix:
- (a) Add `--first-parent` to the `git log` (executed: it returns `MIXER2 own: next is run Codex r3`, which is correct).
- (b) Request `baseRefName` and use `origin/<base>` as the range base for both calls. If `origin/<base>` is missing,
  print NOT READ.
- (c) Count added review files only along the first-parent, non-merge commits, so files arriving through a merge
  are not counted:
  `git log --first-parent --no-merges --diff-filter=A --name-only --format= origin/<base>..<head> -- docs/reviews/`.
- (d) Add a case for each world: stacked with no own commits, and a feature branch merged in.

### F2 — P2: after a failed `git fetch`, a MASTER commit (another PR's merge) is shown as the PR's latest commit; the warning says "STALE", not "may be another PR's"
`scripts/session-state.py:203-204` and `:287`.

Executed: the clone's `origin/master` is at "master base". `sm3` makes its own commit "SM3 own: next is CI", then
merges a newer master that holds "MASTER: PR #1000 landed (someone else's)". Only `origin/sm3` is fetched, and the
URL is then broken so the script's fetch fails:

```
⚠ `git fetch` failed: branch facts below may be STALE.
  PR #5 `sm3` head cf46290c · CLEAN · checks: NO CHECKS
      latest commit: MASTER: PR #1000 landed (someone else's)
```

"Stale" tells the reader the value is old. Here it is wrong: it belongs to a different PR. This needs an
`origin/<b>` fresher than `origin/master`, for example a single-branch fetch, an "Update branch" on GitHub followed
by `git fetch origin <b>`, or a partial fetch. That makes it narrower than F1, but it is the same mis-attribution.

Fix: F1(a), `--first-parent`, removes it (executed: `SM3 own: next is CI`). Alternatively, when the fetch failed,
do not print subjects at all.

### F3 — P3: the mid-PR deadline branch is untested; one case's name claims more than its clock can show
`scripts/session-state.py:289-293`, `:246`, and case `:452`.

- Executed mutation: replacing `if r1 is None or r2 is None:` with `if False:` gives **38/38 green**. That path then
  indexes `None[0]` and crashes. The hook prints a traceback plus `CANNOT RUN` (not reassuring), but the branch and
  its `not_read -= 1` accounting are never reached. Executed: `not_read -= 1` → `pass` also gives 38/38. The fake
  clock ticks 15 s, so the deadline always lands on `rev-parse`, never between `rev-parse` and `log`.
- Executed mutation: `if left < 1:` → `if left <= 0:` gives 38/38. The case named "none is started with under a
  second left" cannot tell `<1` from `<=0`, because its clock never lands in (0, 1).

Fix: add a clock whose budget runs out between `r0` and `r1`, and assert the note plus the `not_read` count. Add a
tick that leaves 0.5 s, and assert no launch.

### F4 — P3: the ledger's size is unbounded and its read is outside the budget
`scripts/session-state.py:143` and `:230-232`, `:302`.

Executed: a 139 MB ledger (1.5 M lines) took **35.4 s**, all outside the 40 s budget, and printed **120 MB** into
the block. Added to a slow `gh`, this passes the hook's 60 s kill, and then no block appears at all. The ledger is
written by hand, so this is unlikely, but the r2 FIFO finding was of the same kind.

Fix: cap the rendered entries (for example 50, then "N more NOT SHOWN"), and refuse a ledger over a size bound
with a NOT READ note.

### F5 — P3: an empty id is accepted by `--add`, is then unreadable forever, and `--done ""` prints the block instead
`scripts/session-state.py:182`, `:148`, `:486`.

Executed: `--add "" w d` prints `ledger: added `. That line is then reported as "unreadable (no id) — kept, NOT
SHOWN" and is written back on every later write. `--done ""` is falsy, so it falls through to printing the whole
block, and the job cannot be removed.

Fix: reject an empty or whitespace ID in `main()` with rc 2. Test `args.done is not None`.

### F6 — P3: a timeout's CANNOT RUN reason is truncated away
`scripts/session-state.py:101`, `:258`.

Executed (the budget world): `gh exited 127: Command '['gh', 'pr', 'list', … 'statusChe`. The `[:160]` cut lands
inside the echoed command, so the words "timed out after N seconds" never show. It is honest, but it does not tell
the reader why.

Fix: on `TimeoutExpired`, return `f"timed out after {exc.timeout:.0f}s"`.

### F7 — P3 (usefulness, and a count that over-states): "review files added" counts verdict JSONs, misses renames, and says nothing about what is next; failing checks are not named
`scripts/session-state.py:288`, `:299`, `:215`.

Executed: a real run shows PR #410 with "review files added by this PR: 7". Those are 3 reviews, 2 coordinator
records and **2** `verdicts/*.json`. A review moved into `docs/reviews/` (as #92 did) is `R`, not `A`, so it is not
counted. `checks: 1 fail · 12 pending` does not say WHICH check failed, and that is the first thing a resuming
model needs. The commit subjects in the real run say what was DONE, and in practice rarely what is next.

Fix: restrict the count to `*.md`, or label it "files under docs/reviews/". Append the names of failing checks,
cleaned and capped at 3.

### F8 — P3: PR body numbers and claims
- The body says "never reported as the PR's" (master commits merged in). F1 and F2 refute it.
- The body says "6 open PRs"; the run today shows 7. That is a snapshot, so it is trivial; date it or drop it.
- The backlog #362 row, the #366 row and the dashboard entry match the code. The #362 row's *Proposal* still says
  "latest review record per branch", but the status cell records the redesign, so this is acceptable.

## Disposition
F1 is the bet's named failure ("attributes one PR's state to another"). It was executed against the real script,
and it is fixed in four short lines plus two cases. F2 has the same cause and is fixed by the same `--first-parent`.
Everything else is P3. The forgery half of the bet held under an exhaustive code-point sweep. The budget half held
end to end.

VERDICT: NOT CONVERGED
