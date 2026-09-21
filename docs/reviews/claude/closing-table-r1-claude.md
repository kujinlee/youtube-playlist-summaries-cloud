# closing-table — round 1, Claude half

**REVIEW GAP: the independent Claude half could not be dispatched.** This session runs under an
instruction not to invoke the Agent tool unless the user asks for it, so the usual fresh-subagent
adversarial reviewer was unavailable. What follows is a **coordinator self-review** — the author
attacking their own code — and it is **weaker than an independent half by construction**: it cannot
find what the author did not think to look for, which is precisely what the second half exists for.
`docs/plugins.md` records the measured cost of a skipped half: a Codex-only round cleared a money
guard that the Claude half caught in one pass. **Re-attempt this half before merge if a subagent
becomes available.** The Codex half DID run (`docs/reviews/coordinator/closing-table-r1-codex.md`,
`gate_ran: true`) and produced 1 Blocking, 2 High, 3 Medium, 1 Low, all folded.

## What the self-review found, before Codex returned

Five defects, all found by **running probes rather than reading the code** — which is the only
reason a self-review found anything at all.

| # | Grade | Finding | Status |
|---|---|---|---|
| S1 | High | `\|-\|-\|` is valid GFM and `_SEPARATOR` demanded `-{2,}`, so a correctly-written table was reported MISSING. A warn-only observer's false alarms are what get it switched off. | fixed, case `table: single-dash separator is valid markdown` |
| S2 | High | The trigger matched anywhere in the command string, so `grep -n 'git push' file` and `echo 'git push'` both fired. That grep is a command this session runs routinely. | fixed by command-segment anchoring |
| S3 | Medium | `git commit --dry-run` counted as a commit. | fixed, `_REHEARSAL` |
| S4 | Medium | `git -C /repo push` was MISSED — global options sit between `git` and the subcommand. | fixed |
| S5 | Medium | `python3 scripts/begin-plan.py --tick` was missed once the trigger became `^`-anchored: the segment starts with `python3`. Introduced BY the S2 fix and caught only by the suite. | fixed |

⚠ **S5 is the notable one**: it was *created by the fix for S2*, in the same edit. That is this
repo's recorded *each round's fix causes the next round's finding* shape, compressed into a single
round — and nothing but the self-test would have caught it, because reading the new regex it looks
obviously correct.

## An incident, recorded because it cost real diagnosis time

While this branch was being written, `check-plan-code.py --mutate .` was left running in the
background **against the live checkout**. It applies one mutation at a time to the DELIVERED script,
so the working tree transiently carried `judged = banner.windows(records)[-1]` — verbatim one of
this branch's own mutation entries. Three self-test failures were then measured against a corrupted
file and diagnosed as logic bugs before `git diff` showed what had happened.

**The commit was clean** (checked: `git show` carried `judged_window(...)`), so nothing shipped. Two
things follow, and both are now acted on rather than merely noted:

* ⛔ **Do not run `--mutate .` while editing the files it mutates.** The harness's own documentation
  says it stages a tree; whatever the mechanism, the working copy was observed to change.
* The per-manifest verification used for this branch runs against a `copytree` into a temp root and
  never touches the checkout. That is the *an instrument that edits the repo corrupts its peers*
  memory, paid for a second time.

## Verification performed

| check | result |
|---|---|
| Self-test | ✅ 73/73, control GREEN before any mutation |
| Mutations kill via the case each NAMES | ✅ **19/19**, 0 survivors, 0 unattributable, 0 orphaned |
| Failure-line contract (`  [FAIL] {name}: got X want Y`) | ✅ byte-identical to `check-merge-ready.py` |
| `check-ratchet-contract` | ✅ rc=0, discovers the guard (39 total) |
| `check-selftest-counts` | ✅ rc=0, 44 scripts declare a count, all verified by running |
| `check-fixture-variation` | ✅ rc=0, 6 keys pinned, derived by running `analyse()` |
| `check-docs` | ✅ rc=0 |
| Hook syntax | ✅ `bash -n` clean |
| An independent Claude reviewer ran | ❌ **NO** — see REVIEW GAP above |
