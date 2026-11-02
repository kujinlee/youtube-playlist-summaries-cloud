<!-- codex-review: model=gpt-6.1-sol -->

Review of `ledger-cap-safety`, PR #413, head `2bd3ff94`, mandate **REFUTE**. Repository unchanged; all experiments ran in `/tmp/ledger-r2.17fzuB` or a temporary Linux-container copy.

1. **P1 — Deleting the lock sidecar restores the three-writer lost-update bug.**  
   `scripts/session-state.py:211–224,240–247`

   Executed this interleaving using real `flock` calls and pauses around reads:

   - A holds the lock; B opens the same lock inode and waits.
   - A writes successfully; B acquires that inode’s lock, reads A’s ledger, and pauses.
   - Delete `inflight.jsonl.lock`.
   - C creates a replacement sidecar and successfully records C.
   - B writes its earlier snapshot, erasing C.

   Results on **macOS and Linux**:

   ```text
   results: A=ok, C=ok, B=ok
   before B writes: ['old', 'A', 'C']
   final:           ['old', 'A', 'B']
   ```

   No adversary edited the ledger’s contents. `O_NOFOLLOW` rejects symlinks but does not establish the promised stable lock identity. This directly refutes the preservation bet.

2. **P1 — Retargeting a symlinked `.claude` lets an update overwrite another ledger’s recorded jobs.**  
   `scripts/session-state.py:159,216,234–237`

   Executed:

   - `.claude` points to directory A, whose ledger records `old-first`.
   - Directory B’s ledger records `old-second`.
   - Pause an add after reading A.
   - Retarget `.claude` to B.
   - Resume the add.

   Observed on **both platforms**:

   ```text
   CLI exit: 0
   visible ledger: ['old-first', 'new']
   ```

   `old-second` disappeared from B’s ledger. The reader’s descriptor pins the file it reads, but subsequent pathname operations resolve the parent again. `O_NOFOLLOW` on the final component does not protect a symlink higher in the path.

3. **P2 — A hard-linked ledger still permits the detached-ledger failure from round 1.**  
   `scripts/session-state.py:165–173,237`

   Created two hard links to one ledger containing `old`. Paused the alias writer after reading; successfully added `target-job` through the other pathname; resumed the alias writer.

   Both platforms produced:

   ```text
   alias writer: success
   alias ledger:  ['old', 'alias-job']
   target ledger: ['old', 'target-job']
   ```

   Both adds succeeded, but the alias ledger excludes the concurrently recorded job. Hard links pass the regular-file check and use different sidecars. The implementation needs an explicit hard-link/identity policy.

   **Control:** hard-linking the *lock sidecar* to the original ledger did preserve serialization: C blocked, and all jobs survived. That variant does not reproduce the symlinked-lock bug.

4. **P2 — The named boundary and Unicode rewrite cases do not establish their stated properties.**  
   `scripts/session-state.py:462–472`

   Two independently executed mutations each left **51/51 tests green**:

   | Temporary mutation | Independent witness |
   |---|---|
   | `_for_update()` returns `([], [])` only when the input is exactly `MAX_LEDGER` | Adding `new` to an exactly-at-cap ledger erased `old`; final IDs were `['new']`. |
   | Serialize with `ensure_ascii=path.exists()` | Removing `x` from a 60,038-byte ledger retaining a CJK job refused because serialization became 120,026 bytes. |

   The boundary case checks that `ledger_done()` raises no exception; it does not check its return value or resulting contents. The Unicode case creates the Unicode entry and then removes that very entry, leaving nothing Unicode to rewrite.

   The official mutation run did report **25 applied, 25 killed, 25 attributed, zero survivors**, with controls green. Those counts are real, but their interpretation needs qualification:

   - The ASCII mutation fails during **creation**, rather than exercising the advertised rewrite.
   - The mutation named “reads past a refusal and rewrites anyway” instead produces `AttributeError` from parsing `None`; the ledger remains unchanged, and a later uncaught exception aborts the suite.

   Consequently, the answer to “do the cases fail for the reasons in their names?” is **not uniformly**.

5. **P3 — The PR body and documentation overstate or misdescribe the evidence.**

   Read the [live PR body](https://github.com/kujinlee/youtube-playlist-summaries-cloud/pull/413) with `gh`: it still says round 1 is running and reports **45 cases / 21 mutations**, while this head has **51 / 25**.

   Backlog #369 correctly describes the ordinary cap refusals, shared reader, direct symlink refusals, and non-list rollup behavior. Its preservation claim is broader than the executed filesystem results support.

   The dashboard still names the removed `_whole()` function and says the ledger “can no longer wipe itself.” Findings 1–2 contradict that wording.

   The backlog’s statement that UTF-8 means a rewrite “cannot re-inflate past the cap” is also too broad. With unmodified code, removing one job from an exactly 65,536-byte compact JSON ledger attempted a 65,925-byte rewrite because serialization adds spaces. It refused unchanged—safe, but still re-inflation.

Executed checks that held:

| Probe | Result |
|---|---|
| Round-1 symlinked-lock three-writer attempt | All three writers refused; original job and symlink survived |
| Round-1 symlinked-ledger paused-writer attempt | Alias writer refused before reaching the pause; target update survived |
| Growth past cap between `fstat` and `read` | CLI exited 2; bytes matched the externally grown ledger |
| `O_NONBLOCK` regular-file read | Returned the complete 54-byte fixture |
| Raw U+2028 and U+0085 | One readable job; `clean()` removed line-breaking effects; exactly one genuine END marker |
| Missing/null/object/string/numeric/boolean rollups | No false `NO CHECKS` |
| Empty versus nonempty rollup lists | Only the empty list printed `NO CHECKS` |
| Self-tests | 51/51 on macOS/Python 3.14.4 and Linux/Python 3.12 |
| Official mutation slice | 25/25 killed and attributed on macOS; full repository sweep not run |

The Linux probes ran on the container’s native filesystem, not a macOS bind mount. Direct final-component symlinks were refused, while the parent-symlink attack succeeded on both systems. These requested platform behaviors are verified.

Additional executed gaps: omitting only `isDraft` produces no missing-field warning; a rollup member with integer `conclusion` raises `AttributeError`. Neither produced a false `NO CHECKS`, so the specific check-list bet held for the tested answers.

VERDICT: NOT CONVERGED
