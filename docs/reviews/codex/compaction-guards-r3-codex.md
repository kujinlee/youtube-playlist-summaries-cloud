<!-- codex-review: model=gpt-6.1-sol -->

Reviewed HEAD `3c282379` against `origin/master`, including all three fold commits. Probes ran in temporary copies; repository contents were not edited.

1. **Major — PostCompact and SessionStart can block indefinitely on session artifacts.** `scripts/compaction-state.py:771–773`, `:877–879`, `:901–903`. **Pre-existing; outside the redesign’s child boundary.**

   **Reproduction:** Create `.remember/compaction/S/snapshot.md` as a FIFO, then invoke `--print` or `--audit` with `{"session_id":"S","compact_summary":"x"}`. Both remained alive at **16 seconds**, exceeding their registered **15-second** timeout. The same occurred with FIFO `receipt.json` in both modes and FIFO `audit.md` in `--print`.

   `_read()` uses unrestricted `read_text()`. The regular-file protection added for dashboard and transcript reads does not cover these parent-side reads. Sparse 256 MiB regular artifacts completed in **0.74–0.91 seconds** here, but no size limit protects them.

   **Fix:** Apply descriptor-based regular-file checks and bounded reads to every artifact reader. Put parsing and auditing under an external deadline too.

2. **Major — The PR namespace fix introduces another quadratic parser outside the killed child.** `scripts/compaction-state.py:703–704`. **FIX-INDUCED by `9d7e32eb`.**

   **Reproduction:** Give the session a valid receipt and snapshot whose only audited item is PR #410. Run PostCompact with:

   ```python
   compact_summary = "backlog #410 " * 100000
   ```

   This **1.2 MB** summary kept PostCompact alive until the test killed it at **16.012 seconds**. For every rejected occurrence, the matcher copies and searches the entire preceding prefix.

   **Fix:** Require explicit PR-qualified references, or inspect bounded local context without rescanning prefixes. Bound the whole audit independently of its parser.

3. **Major — An escaped descendant keeps the live SessionStart hook alive past 60 seconds.** `scripts/session-state.py:126–129`. **Pre-existing failure class; retained by `3c282379`.**

   **Reproduction:** Put a Python `gh` on PATH that forks. Its child calls `setsid()`, retains inherited stdout/stderr, and sleeps 90 seconds; its parent also sleeps. After the 30-second call timeout, group killing removes the parent, but the second, unbounded `p.communicate()` waits for the escaped child’s pipe descriptors.

   The actual `session-state.py` printing invocation remained blocked at **61.006 seconds**, beyond its registered **60-second** timeout. This keeps the hook alive; it does not merely leave a daemon behind.

   The same attack against PreCompact returned in **11.148 seconds**, confirming that its outer child boundary works.

   **Fix:** Bound post-kill pipe draining and close descriptors when that bound expires, or give the live SessionStart capture the same external process boundary.

4. **Major — A valid session ID can select a symlink and write outside the compaction directory.** `scripts/compaction-state.py:489–495`, `:534–538`, `:836–842`. **FIX-INDUCED by `9d7e32eb`’s per-session directory design.**

   **Reproduction:** Make `.remember/compaction/A` a symlink to an existing temporary directory outside `.remember/compaction/`. Invoke PreCompact for session `A`. Both `receipt.json` and `snapshot.md` appear in the external directory.

   The session-ID regex rejects textual traversal, but directory creation and atomic replacement follow ancestor symlinks.

   **Fix:** Resolve storage through directory descriptors, refusing symlink components, and perform creation and replacement relative to the verified directory.

5. **Major — Session identity still does not establish compaction identity.** `scripts/compaction-state.py:877–880`, `:887–903`. **Pre-existing; incompletely addressed by `9d7e32eb`.**

   **Reproduction A:** Within session S, complete capture A, then capture B. Deliver A’s delayed PostCompact payload after B. The audit adopts **B’s nonce and epoch**, audits A’s summary against B’s snapshot, and prints alongside `CAPTURE B` without STALE. With PR #410 in B and “COMPACTION A retained PR #410” as the delayed summary, it reports **“names everything.”**

   **Reproduction B:** Deterministically schedule PreCompact immediately after SessionStart has read the old receipt but before it renders. PreCompact replaces the receipt and deletes the old artifacts; SessionStart still prints its cached `CAPTURE OLD` as current, without STALE.

   Two concurrent PreCompacts completing in reverse order also leave receipt B beside snapshot A. That mismatch is rejected honestly, but publication can overwrite the successful newer capture.

   **Fix:** Serialize publication and reading with bounded locking, and publish only if the receipt still names the capture being completed. Bind PostCompact to an identifiable generation; where the harness supplies insufficient identity, report the association as unverified.

6. **Major — Backlog and issue references still produce a false all-clear.** `scripts/compaction-state.py:691–704`. **Pre-existing; incompletely fixed by `9d7e32eb`.**

   **Reproduction:** With PR #410 as the only snapshot item, audit:

   ```text
   backlog item: #410
   ```

   Result: **“the summary names everything in the snapshot (1 items checked).”**

   `backlog **#410**` also passes. In `issues #410 and #411`, the matcher rejects #410 but counts #411 as a PR.

   **Fix:** Require explicit `PR #N` references. The immediate-preceding-word exclusion does not establish the referent across punctuation, Markdown, or lists.

7. **Major — PR-list truncation never reaches audit completeness accounting.** `scripts/compaction-state.py:580–591`, `:630–638`. **Pre-existing.**

   **Reproduction:** Return exactly `session-state.LIMIT` (**100**) PRs, with an empty readable ledger and zero dashboard asks. The snapshot body warns **MAY BE TRUNCATED**, but the keys retain neither that uncertainty nor an omission marker. A summary naming those 100 numbers yields:

   ```text
   the summary names everything in the snapshot (100 items checked).
   ```

   This contradicts the docstring’s promise that incompletely captured categories produce NOT CHECKED.

   **Fix:** Carry the list-limit uncertainty into the keys and audit. It must prevent an unqualified completeness claim.

8. **Minor — Explicit null provenance flags pass the “absent or literal false” rule.** `scripts/compaction-state.py:274–276`. **Pre-existing validation gap; incompletely fixed by `9d7e32eb`.**

   **Reproduction:** A same-session human-origin prompt carrying `isMeta: null`, `isSidechain: null`, and `isCompactSummary: null` reaches owner words. `_off()` treats null as absence.

   **Fix:** Use `f not in d or d[f] is False`. The docstring and recorded prediction explicitly exclude other values.

9. **Minor — Print headings still claim more than the verified artifacts support.** `scripts/compaction-state.py:782–785`, `:812–831`. **Pre-existing; incompletely fixed by `9d7e32eb`.**

   **Reproduction:** Supply a fresh receipt and snapshot/audit with old nonces. Neither artifact is shown, but the first line still says **“COMPACTION HAPPENED at … items the summary dropped are listed.”** With a matching snapshot and missing audit, the snapshot is displayed despite the docstring’s requirement that all three nonces match.

   **Fix:** Calculate artifact verification before constructing the heading. Either enforce the documented combined gate or describe independently verified pieces accurately.

10. **Minor — The published PR description still contains unfixed round-2 claims.** [PR #425 description](https://github.com/kujinlee/youtube-playlist-summaries-cloud/pull/425), body lines **8, 23, 28, 32–33, 49**. **Pre-existing.**

    **Reproduction:** Read-only `gh pr view 425 --json body` still shows shared artifact paths, “every AskUserQuestion answer,” backlog #363’s rule, 61/57 cases, 22/30 mutations, and **“NO-REVIEW … the dual review is still to run.”**

    **Fix:** Rewrite the description around the final per-session implementation, current validation, bounded answer retention, and actual review state.

Validation:

- **101/101 compaction** and **60/60 session-state** control cases passed.
- Independently applied all **59 + 32 mutations** in temporary copies. **All 91 failed every expected case named by their manifest.**
- `EXPECTED_MUTATIONS` and all manifests agree exactly: **2,427**, with no per-script discrepancies.
- Original round-2 extraction, paste, FIFO-dashboard, cross-session A/B, corrupt-ledger, main-checkout fallback, owner-wait cap, dashboard-omission and missing-origin reproductions now reject their original inputs. Bare ledger words and literal `backlog #410` no longer count.
- The earlier-compaction/no-new-PreCompact reproduction still succeeds, as the new docstring acknowledges. The PR-description reproductions also remain.
- Worktree ledger reading and worktree `--add`/`--done`, garbage-input rc 0, and print bounding held. The oversized print probe produced **9,798 characters**.
- The real **83,065,537-byte** transcript paired **all 40 answers** in **0.564 seconds**.
- A **261,956,000-byte** transcript with a 7.9-second `gh` completed PreCompact in **10.976 seconds**. Failed capture removed the previous snapshot and audit; the previous capture was not retained.

VERDICT: NOT CONVERGED
