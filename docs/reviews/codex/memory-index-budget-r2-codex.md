<!-- codex-review: model=gpt-6.1-sol -->

**Verdict: REQUEST CHANGES.** The fold still contains a vacuous repaired assertion, unprotected behavior, and an advisory hook that skips relative paths.

Executed successfully:

- Guard: rc 0, **22,078 characters**.
- Suite: **43/43**.
- Actual mutation harness: **16 killed, 16 attributed, zero survivors**, with green control and re-control over a staged `HARNESS_TREE`. Every shipped edit bound once and parsed.
- Six additional behavioral mutants: **all survived 43/43**. No shipped mutant appeared equivalent.

1. **Medium — F2’s repair retains the same suffix defect.**  
   [check-memory-index-budget.py:268](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-memory-index-budget.py:268)

   Change the displayed overage from `{n_chars - limit:,}` to `{n_chars - limit + 1000:,}`. The fixture now reports **1,007 characters** instead of **7**, yet passes: `"7 characters of its tail"` remains a suffix, and the prohibited total `1,241` remains absent. Independently, adding 10,000 to displayed OK headroom also passes because `"990 under"` matches `"10,990 under"`.

   These are executed survivors, not the already-fixed total-versus-difference mutant. Assert complete numeric fields with boundaries or compare structured values.

2. **Medium — replacing the integration case with a predicate case stopped testing dispatch order.**  
   [check-memory-index-budget.py:338](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-memory-index-budget.py:338)

   Insert self-test dispatch immediately before `unknown = unknown_args(argv)`. All **43 cases pass**, although `main(["--self-test", "--bogus"])` now returns success. The predicate remains correct while its caller violates the contract.

   Test `main` with a stubbed `_self_test` that records invocation; this verifies ordering without recursive suite execution.

3. **Medium — the new hook silently ignores a repository-relative index path.**  
   [check-memory-index-budget.sh:27](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/hooks/check-memory-index-budget.sh:27)

   In a throwaway tree with a sentinel guard returning OVER BUDGET, an absolute `file_path` emitted the advisory. `"docs/memory/MEMORY.md"` emitted nothing, at rc 0: the pattern requires a slash before `docs`.

   Normalize relative paths before matching. Invocation from another directory worked with an absolute hook path. Invocation through a symlink resolved the wrong root and reported CANNOT RUN instead of measuring the index. Missing `tool_input`, null input, and malformed JSON all exited quietly at 0. The hook remains unregistered as intended.

4. **Medium — F1 establishes neither Python code points nor newline handling.**  
   [check-memory-index-budget.py:195](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-memory-index-budget.py:195)

   The historical index contains **🔴**, a non-BMP character: **26,930 code points versus 26,931 UTF-16 units**. Both round to the observed 26.3KB. Thus the warning arithmetic cannot distinguish them.

   Executed fixtures expose the difference:

   - `24,984 × "x" + "😀"`: guard counts **24,985**, returns rc 0; UTF-16 length is **24,986**.
   - `9,000 × b"x\r\n"`: guard counts **18,000** because `read_text` normalizes newlines; decoded source length is **27,000**.

   These demonstrate unresolved counting semantics, not proof that the producer uses UTF-16 or preserves CRLF. **A controlled producer boundary experiment was not executed; that verification remains unproven.** The docstring’s claim that the unit is established is stronger than this evidence.

5. **Low — F3 has additional uncovered branches and arithmetic.**

   Three more executed mutants passed **43/43**:

   - `WARN_FRACTION = 0.9004`: changes the live threshold from **22,486 to 22,496**.
   - Replace threshold `int()` with `round()`: differs at fractional boundaries, absent from the fixtures.
   - Remove `UnicodeDecodeError` from the handler: invalid UTF-8 escapes instead of returning CANNOT RUN.

6. **Low — F5’s corrected moved-row measurement is still wrong.**  
   [MEMORY.md:146](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/memory/MEMORY.md:146)

   The **28 original moved rows**, extracted from `dff6a3f0^`, total **4,912 characters excluding line endings**, or **4,940 including one newline per row**—not **4,985**. The current moved rows give the same counts.

   I independently confirmed the historical **26,930 characters / 27,805 bytes / 145 rows / 35 rows over 200 characters / longest row 602** figures. Those checks do not establish the claimed eight-row delivery loss or the producer’s exact counting algorithm.
