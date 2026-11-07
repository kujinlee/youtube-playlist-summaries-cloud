Reviewed head: 4f334faeb8937b81e7b7bab1b70df38e0feb7e05

# pace-stop-message (backlog #525): round 5, Claude half (adversarial, under the round cap)

Subject: the commits after the round-4 record `f10719d9`. They are `166a0f9b`, a merge of `origin/master` at `1d618a6f`, and
`4f334fae`, which renames one `expect` in `scripts/mutations/check-usage-pace.json`. The merge brings in master's backlog #507
work (`session-state.py`, its manifest, its reviews) and keeps this branch's dashboard entry at the end of the file. Since the
`e9fa101f` tree that round 4 confirmed, `git diff e9fa101f 4f334fae -- scripts/check-usage-pace.py .claude/hooks` is empty, so
the subject's code is unchanged. The only new guarded change from this branch is the one-line `expect` rename.

Why this round exists: CI `verify` on PR #524 (job 128022557596) failed at `check-review-recorded.py`:
"5 round(s) ran and guarded code was committed after every one of them. The closest
(pace-stop-message-r3-claude.verdict.json) never saw: scripts/mutations/check-usage-pace.json".

**Summary.** The rename is correct. It points the entry back at the case the build renamed. That case is still as strong as
before, and the mutation kills it deterministically. No BLOCKER, no MAJOR, no MINOR.

## 1. The mutation goes red through the case it now names, deterministically

Entry: `#510: a rising stop is described as the 97% cap (owner 2026-11-05)`. The edit changes `if stop == STOP_CAP` to
`if stop >= STOP_CAP` in the WARN note.

I ran it on a `git archive HEAD` copy in the scratchpad, with `HOME` redirected to an empty directory. I applied the entry's
edit with an exact-once replacement and ran `scripts/check-usage-pace.py --self-test` three times:

| run | rc | result | named case `[FAIL]`? | attributed by the harness's `parse_fail_names`? |
|---|---|---|---|---|
| 1 | 1 | 338/347 | yes | yes (9 names parsed) |
| 2 | 1 | 338/347 | yes | yes (9 names parsed) |
| 3 | 1 | 338/347 | yes | yes (9 names parsed) |

All three runs failed the same nine cases. The first is the named one,
`#510: the message says the stop is rising, its value now, and when its NEXT stop comes (backlog #525: the hard limit at the last night)`.
The other eight are backlog #525's M1, r1-fold and r2-fold cases. That fits the mutation: every rising-stop note now reads
"The stop is the 97% cap". For attribution I used the harness's own consumer, `parse_fail_names` from
`scripts/check-plan-code.py`, and did not match by eye. The name has a `#525:` colon but no `: got `, so the consumer does not
truncate it (that case is pinned in `check-plan-code.py`'s self-test: "a case name containing ': got ' is TRUNCATED").
Unmutated baseline in the worktree: `347/347 self-test cases passed`.

## 2. Why the old name was not red, and whether the rename hid a weakened case

The old `expect`, `#510: the message says the stop is rising, its value now, and when it reaches 99`, could not be red under
any mutation because that case no longer exists. `grep -c "when it reaches 99" scripts/check-usage-pace.py` returns 0. The
build commit `59936267` renamed the case, and `git log -S"when it reaches 99"` shows only that commit and `4f334fae`. So
from `59936267` through round 4, the entry named a case that did not exist. The mutation was still killed, by the
renamed case and the other eight above. That is why the sweep's shard 13 reported a kill attributed to a different case,
not a survivor.

Was the case weakened? I compared it before and after (`git diff origin/master...HEAD -- scripts/check-usage-pace.py`):

- before: `"The stop rises over the last day, 98% now and 99% from Sat 01-16 01:00 PST: what is left under it is lost at the reset." in evm(cache(97.5, week_reset=_sat2, at=NOW + 12.5 * 3600), m85, NOW + 12.5 * 3600)[1]`
- after: `"The stop rises over the last day, 98% now and 100% (the hard limit) from Fri 01-15 18:00 PST: what is left under it is lost at the reset." in` the same call.

The input, the call and the shape are the same: an exact substring that pins the value now, the next stop and its time.
Only the expected text changed, because backlog #525 changed the behaviour. Under a Sat 02:00 reset the last night starts
Fri 18:00, before the rise's 99% end at Sat 01:00, so the 99% stop never comes. The case is as strong as before. The 99%
branch it used to cover still has its own case: `…while BEFORE a rise end that precedes the last night, the 99% IS the next
stop (the other branch stays reachable)`. That case is among the nine this mutation reddens. **The rename was right.**

## 3. Other checks

- **The merge brought no subject change.** The paths that differ between `f10719d9` and `4f334fae` are master's #507 work,
  the `check-plan-code.py` pin line from master, and this one `expect`. `scripts/check-usage-pace.py` and both usage-pace
  hooks are byte-identical to `e9fa101f`.
- **The other CI message is not a failure.** The log line
  `✗ docs/superpowers/plans/2026-01-01-x.md: no **Status:** line ... and armed-anchor is armed` is the expected output of a
  passing negative case in `scripts/check-goal-status.py --self-test` (lines 394-407: a `TemporaryDirectory` fixture, case
  "...and exits 1 once an armed document declares nothing"). That step ended `34/34 self-test cases passed`. The file is in
  neither `HEAD` nor `origin/master`, and this branch does not touch `check-goal-status.py`. The job's only non-zero exit was
  `check-review-recorded.py`, the reason for this round.
- **Not a finding, an observation.** No check at rest catches an `expect` that names a case that does not exist. This one
  lived through four review rounds and was found only when a sweep shard ran the entry. A naive literal check finds 27 such
  `expect`s across `check-usage-pace.json`, but most are case names built at runtime (f-strings, loops), so that count is not
  a defect count. I did not file it from this round.

Self-test at the reviewed head: `python3 scripts/check-usage-pace.py --self-test` → `347/347 self-test cases passed`.

VERDICT: CONVERGED
