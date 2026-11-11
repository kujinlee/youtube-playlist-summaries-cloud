<!-- codex-review: model=gpt-6.1-sol -->

Reviewed `fdf15b69` against `origin/master`. Reproductions ran in temporary copies; no repository files were edited.

**The bet is refuted by one retained sentence. No timeout, nonce or owner-provenance failure was reproduced.**

1. **Minor — Pre-existing: `run_capture` still promises the withdrawn survival guarantee.**  
   **File:** `scripts/compaction-state.py:731`

   The docstring says:

   > “nothing it started survives — except a process that called `setsid`.”

   **Reproduction:** Run a child through `run_capture` that forks. Its descendant calls `os.setpgid(0, 0)`, records its PID and sleeps; the original child exits normally. No process calls `setsid`.

   `run_capture` returned `(0, '')` in **0.410 seconds**, while the descendant remained alive. I killed the survivor afterward. The shipped self-test independently confirms this escape.

   This behavior matches the new stated bound, but contradicts this retained docstring and fires the bet’s prose clause.

   **Fix:** Describe cleanup as killing the child’s process group, explicitly excluding descendants that leave it through `setsid` **or `setpgid`**. Remove “nothing it started survives.”

Round-4 reproductions and regressions:

| Check | Result |
|---|---|
| Original 512 MiB streamed payload | PreCompact **0.128 s**, print **0.134 s**; both rc 0 |
| Binary, slow and never-closing stdin | Returned within bounds; slow/empty-open inputs took approximately **2.2 s** |
| Held-open valid stdin plus signal-ignoring capture | PreCompact returned rc 0 in **13.344 s**; capture was gone |
| Signal-ignoring child at real capture timeout | Killed in **11.012 s** |
| FIFO, symlink and oversized receipt/snapshot | Refused in **0.285–0.382 s** |
| Mismatched snapshot nonce | Snapshot sentinel was not printed |
| Large matching print | **9,760 characters**, including closing marker |
| Live SessionStart with escaped stdout holder | Returned rc 0 in **31.156 s**, below its 60 s registration; diagnostic identifies the exited command and held pipe |
| 261,955,584-byte transcript plus 7.9 s `gh` | Returned rc 0 in **11.010 s** |
| Real session transcript | **45 answers paired in 0.490 s**; independent scan also found 45 eligible answers |
| Worktree ledger read/write | Main-checkout reading and real linked-worktree `--add`/`--done` cases passed |
| Structural marking and crash fallbacks | Captured failure-word data stays unmarked; both shell fallbacks carry `NOT CAPTURED` |
| Freshness, single ledger lookup, fixed identity warning | Round-4 regression cases passed |

The audit-only reproductions have no remaining implementation: `--audit` is refused, PostCompact is unregistered, and the hook is deleted. The specified prose surfaces now describe that deferral and corrected paths/counts; the remaining survival sentence above is the exception.

**96/96 compaction cases and 68/68 session-state cases passed. All 94 kept mutations—54 compaction, 40 session-state—were killed by every named expected case.** Retirement reasons are recorded, including audit deletion and the equivalent final-fit mutation. `EXPECTED_MUTATIONS` equals the actual manifest distribution and sum: **2,430**.

VERDICT: NOT CONVERGED
