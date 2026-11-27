<!-- codex-review: model=gpt-6.1-terra -->

No findings in the checks completed, but the review is **incomplete**. I cannot establish that F1–F5 are closed or that the fold broke nothing.

The fold’s self-tests cover the write-day and leap-day rules, malformed stored dates, the same-text live and undated wait cases, the thread-line wait, and the passed `--print` leaf. I inspected the write-time date handling and confirmed that `--set-until` uses the day it runs. I did **not** independently rerun every round-1 input, construct all four requested F4 shapes, or diff the no-`until` snapshot and `--print` output against `4ef6dfea`.

The mutation manifests contain **554 goal-tree** and **172 session-state** entries, matching the stated pins; every edit anchor resolves exactly once. Three hand-applied goal-tree mutations—for retirement by text, preservation of a live dated wait, and the passed `--print` leaf—each failed its named case. I did not establish whether every unchanged session-state mutation remains effective after the fold; unique anchors alone do not prove that.

The requested commands finished with these last lines:

- `python3 scripts/session-state.py --self-test`: `172/172 self-test cases passed`
- `python3 scripts/goal-tree.py --self-test`: `623/623 self-test cases passed`
- `python3 scripts/check-docs.py`: `Documentation integrity OK`

The three flagged changes preserve the existing checks: the first adds a stray-flag refusal, the second adds a condition for an existing diagnostic, and the third passes the new optional argument without removing the existing arguments.

## Loosening answers
LOOSENING-CHECK 9f6e419f062f: not a loosening
LOOSENING-CHECK 019597abdc70: not a loosening
LOOSENING-CHECK 2a714f9dba72: not a loosening
VERDICT: NOT CONVERGED
