<!-- codex-review: model=gpt-6.1-sol -->

Review of `ledger-cap-safety` at `c3a2b169`, mandate **REFUTE**. Repository unchanged; experiments ran in `/tmp/ledger-review.tYxE0O`.

1. **P1 — A symlinked lock file permits successful concurrent adds to erase a recorded job.**  
   `scripts/session-state.py:175–178,194,217–222`

   Set `inflight.jsonl.lock` to a symlink pointing at `inflight.jsonl`. `_locked()` accepts it, so the lock attaches to the ledger inode that `_write()` replaces.

   Executed three writers against the **same ledger path**, using in-memory pauses to force this interleaving:

   - A holds the original inode’s lock; B opens that inode and waits.
   - A replaces the ledger and finishes.
   - B acquires the old inode’s lock, reads A’s replacement, and pauses before writing.
   - C locks the replacement inode and successfully records C.
   - B writes its snapshot, erasing C.

   Observed:

   ```text
   C finished while B holds lock True
   ids ['old', 'A', 'C']
   results {'A': None, 'C': None, 'B': None}
   FINAL ids ['old', 'A', 'B']
   ```

   Every add succeeded. Reject unsafe lock-file types and ensure all writers lock a stable inode independent of ledger replacement. This inherited lock weakness refutes the branch’s preservation bet.

2. **P2 — A symlinked ledger is accepted and silently detached from its target.**  
   `scripts/session-state.py:204–207,194`

   `_whole()` uses `stat()`, which follows symlinks. An add through a symlink succeeds, then `os.replace()` replaces the symlink itself.

   Executed result:

   ```text
   target ids ['old']
   ledger ids ['old', 'new']
   still symlink False
   ```

   With a writer paused after reading through the link, a concurrent successful add to the target disappeared from the ledger subsequently installed at the link path. Either refuse symlinked ledgers or define consistent target resolution and locking.

3. **P2 — The named `None` regression case never tests explicit null.**  
   `scripts/session-state.py:337–342`

   The `None` iteration omits `statusCheckRollup`; it tests a missing field. I introduced a temporary mutation that renders **explicit null as `NO CHECKS` while preserving missing-field handling**. The suite still reported:

   ```text
   45/45 self-test cases passed
   ```

   Test missing and explicit null separately. The oversized `--done` fixture also contains no recorded target ID; my independent probe covered that missing scenario successfully.

Executed verification:

| Probe | Result |
|---|---|
| Existing ledger exactly 65,536 bytes | Readable; overflowing add refused unchanged; done succeeded |
| Growth to exactly 65,536 bytes | Accepted; both jobs retained |
| 20 concurrent adds near cap | One accepted, 19 refused; existing and accepted jobs retained |
| Huge ID | Refused; ledger unchanged |
| Oversized ledger containing targeted ID | Real CLI add/done exited 2; bytes unchanged |
| Registered shell hook with oversized ledger | Exit 0; warning and complete block printed; bytes unchanged |
| Missing, null, `{}`, `""`, `0`, populated dict | `checks: UNREADABLE` |
| Empty list | `checks: NO CHECKS` |
| Nonempty malformed lists | Unreadable/pending counts; no empty-list claim |
| Self-tests | 45/45 passed |
| Requested mutation command, with dependencies copied | 21/21 killed and attributed; both controls green |

The [PR body](https://github.com/kujinlee/youtube-playlist-summaries-cloud/pull/413), backlog #369, and dashboard correctly report the counts and ordinary cap behavior. Their preservation claims are broader than the executed symlink results support. The PR’s claim that cases cover each bad rollup value also overstates explicit-null coverage. The dashboard’s unconditional “every session” wording retains the disclosed subdirectory-launch limitation.

VERDICT: NOT CONVERGED
