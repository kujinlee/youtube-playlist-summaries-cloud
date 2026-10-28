<!-- codex-review: model=gpt-6.1-sol -->

Reviewed `6c837787` against `origin/master`, reading the architecture decision first. Execution used temporary copies; no repository edits.

The bet is refuted: a registered hook exceeded 15 seconds, and a capture-started process survived without calling `setsid`.

1. **Major — Payload processing remains outside the timeout boundary.**  
   **Pre-existing, retained by `218b9582`.** `scripts/compaction-state.py:215`, `:219`, `:931`.

   **Reproduction:** Feed PostCompact a JSON object with `session_id: "S"` and a `compact_summary` containing 512 MiB of `x` characters. The Python entrypoint returned after **16.440 seconds**. Repeating through `postcompact-audit.sh` confirmed it was alive at **15.004 seconds**, returning rc 0 at **16.317 seconds**.

   Stdin’s deadline bounds collecting bytes, but joining, decoding, JSON parsing, and reserializing the payload happen before the child’s timer starts.

   **Fix:** Cap input bytes before joining or decoding, and include parent processing and child startup in an absolute hook deadline. Add this reproduction alongside the shortened child-timeout cases.

2. **Major — `setpgid` escapes cleanup without using the stated `setsid` exception.**  
   **Pre-existing escape, retained by `218b9582`.** `scripts/compaction-state.py:28`, `:788`, `:952`.

   **Reproduction:** A fake `gh` double-forks; its grandchild executes:

   ```python
   os.setpgid(0, 0)
   pidfile.write_text(str(os.getpid()))
   os.close(1)
   os.close(2)
   time.sleep(90)
   ```

   No survivor calls `setsid`. It remained alive, reparented to PID 1, after normal capture completion at **1.119 seconds**.

   With fake `git` delaying `--git-common-dir` by five seconds and `gh` remaining blocked, it also survived the **real 11-second kill**: the hook returned at **11.026 seconds**, but the grandchild remained alive in its new process group. I killed both probe survivors afterward. An ordinary double-fork without changing groups was killed correctly.

   **Fix:** Cleanup must cover descendant-created groups, or the contract must explicitly withdraw the guarantee for other process-group escapes. Add both normal-return and real-timeout `setpgid` cases; `own_group=False` alone cannot establish the kept property.

3. **Major — Published prose still asserts the withdrawn behavior.**  
   **Pre-existing; the split’s required rewrite remains undone.** [PR #425 body](https://github.com/kujinlee/youtube-playlist-summaries-cloud/pull/425), lines 8–10, 28, 32–33, 47, 49; `.claude/settings.json:165`.

   **Reproduction:** `gh pr view 425 --json body` still reports shared artifact paths, “every AskUserQuestion answer,” `COMPACTION HAPPENED`, paraphrases reported as dropped, obsolete validation counts, and `NO-REVIEW … the dual review is still to run`. The registered status message still says “Auditing what the compaction summary dropped...”.

   **Fix:** Rewrite the PR body from the final implementation, as the decision requires, and change the status message to describe explicit-reference auditing.

4. **Minor — An identifier containing `PR` counts as an explicit PR reference.**  
   **Pre-existing matching permissiveness, retained by `218b9582`.** `scripts/compaction-state.py:799`.

   **Reproduction:** With PR #410 in the snapshot, audit `PR410xyz`. The result lists **PR #410 under “Found explicitly in the summary”**, although the input contains neither the word `PR` nor a standalone PR number. The regex has only a left word boundary and excludes only trailing digits.

   **Fix:** Require boundaries around the PR qualifier and number, with explicit supported separators. Add identifier-prefix/suffix negatives to the named matching case.

5. **Minor — Freshness checks contradict “under 30 min old and not in the future.”**  
   **Pre-existing, retained by `218b9582`.** `scripts/compaction-state.py:895`, `:897`.

   **Reproduction:** Give matching artifacts a receipt epoch of `now + 30`. Print shows the snapshot beneath:

   ```text
   NEWEST CAPTURE … (0 min AFTER this session start)
   ```

   A receipt exactly 1,800 seconds old also passes. The implementation permits 60 seconds of future skew and includes the 30-minute boundary.

   **Fix:** Reject `age < 0` and `age >= STALE_AFTER`, or explicitly revise the kept rule to describe those tolerances.

Round-3 reproduction results:

| Round-3 cases | Round-4 result |
|---|---|
| XR1: FIFO receipt/snapshot/audit | Refused promptly; FIFO, symlink and oversized-artifact probes across all three modes returned rc 0. |
| XR2: repeated `backlog #410` | Linear scan; no explicit PR reference found. |
| XR3: escaped pipe holder in LIVE SessionStart | Hook returned in **31.480 seconds**, rc 0, with its in-flight block. |
| XR4: symlinked storage components | Refused; no external writes. |
| XR5: delayed summary and overlapping captures | **Stated bound**, as intended. Delayed A’s summary can accompany B, with the fixed warning. Reverse-order concurrent publication produced mismatched nonces; print refused the snapshot. |
| XR6 / CR2: backlog punctuation, Markdown and lists | No longer produce a completeness claim; unqualified numbers are excluded. |
| XR7 / Cr8: 100-PR truncation | No “names everything” claim remains. |
| Xr8: null provenance flags | Refused; only absent or literal false passes. |
| Xr9 / Cr4–Cr6: heading, missing audit, nonce/epoch wording | Old compaction-identity and contradictory stale messages are removed. |
| CR1: slow git plus hung gh | Original case passes; the `setpgid` variant above defeats the stronger kept property. |
| Cr7: not-captured vocabulary | Tested lines carry `NOT CAPTURED`; CLAUDE.md names it. |
| Cr9: zero checked items | Vacuous positive sentence removed. |
| Xr10 / CR3 / Cr10: prose | Hook comments updated; published PR body and registered status message remain stale. |

Other regression checks:

- **113/113 compaction** and **62/62 session-state** control cases passed, including worktree ledger reading and `--add`/`--done`.
- The round-3 **83,065,537-byte transcript prefix pairs all 40 answers in 0.609 seconds**. The current transcript has grown to 41 paired answers, extracted in 0.567 seconds.
- Garbage, deeply nested JSON, and large inputs returned rc 0. All modes handled 128 MiB inputs; the larger PostCompact probe exposed finding 1.
- Oversized print output measured **9,788 characters**, including its closing marker.
- The **261,956,000-byte transcript plus 7.9-second gh** probe returned in **11.099 seconds**, publishing a `CANNOT RUN` snapshot.
- After correcting the temporary mutation-copy setup to include hooks, **all 103 mutations—69 compaction and 34 session-state—failed every named expected case**. Anchors resolve uniquely. Retirement reasons are recorded in `scripts/check-plan-code.py:1942`.
- `EXPECTED_MUTATIONS` matches the complete manifest distribution and sum: **2,439**.

Findings 1 and 2 satisfy the decision log’s named failure observation. Its prescribed next route is **DEFER the audit**, shipping the snapshot alone; the surviving boundary defects still require resolution.

VERDICT: NOT CONVERGED
