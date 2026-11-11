<!-- codex-review: model=gpt-6.1-sol -->

1. **P2 — Trailing newlines in alias filenames are still stripped before resolution.**  
   **Location:** `.claude/hooks/check-memory-index-budget.sh:125–130`.

   **Reproduction, executed through the registered launcher in a `mktemp` copy:** Create healthy checkout A and checkout B with a 27,000-character index. Create sibling aliases:
   ```text
   tail          -> A/docs/memory/MEMORY.md
   tail<newline> -> B/docs/memory/MEMORY.md
   ```
   Send the latter path as JSON `tool_input.file_path`. Result: **rc 0, no output**. Command substitution strips the filename’s trailing newline, so the hook resolves `tail` and measures A. B’s direct path emits `OVER BUDGET`.

   **Fix:** Preserve the parsed path with a sentinel, as already done for `root`, or keep parsing and resolution inside Python. Add this sibling-alias integration case.

2. **P2 — Successfully resolved targets without the canonical suffix still select the lexical checkout.**  
   **Location:** `.claude/hooks/check-memory-index-budget.sh:141`.

   **Reproduction, executed in temporary copies:** Point `A/docs/memory/MEMORY.md` at `B/other.md`. Resolution succeeds, but the resolved path fails `is_index_path`, so the `elif` retains A’s path. The unmodified checker reports **root A**, despite the edited file residing in B. Substituting a healthy checker in A produces **rc 0, silence**. Likewise, pointing A’s canonical index at an outside-repository `MEMORY.md` runs A’s checker instead of reporting that no checker contains the resolved file.

   **Fix:** Separate index identification from root selection. Once the lexical or resolved path identifies an index, use the resolved path for the parent walk unconditionally; explicitly handle resolved targets that the selected checker cannot measure.

   This contradicts the new comment at lines **138–140** (“whenever resolution succeeded”) and the containing-file guarantee in the header at lines **12–19**.

Execution results:

- Both round-1 defects and both original round-2 reproductions no longer reproduce. The harness alias warns; lexical directory/file aliases select B; the newline-named checkout selects itself.
- All **34 mutations fail every declared named expectation**, including the retargeted divergent-registration case. Controls pass **45/45**; hook self-tests pass **16/16**.
- Symlink loops, dangling links, spaces, quotes, embedded newlines, relative paths, symlink chains, and ordinary cross-checkout aliases completed at **rc 0 in 168–245 ms**. Loop/dangling paths outside a checkout emitted `NOT MEASURED`; the ordinary aliases selected the correct root.
- These timings establish prompt completion for the tested paths. Line **151** still waits synchronously for the checker; there is no general timeout guarantee.
- CI’s line **535** claim that overflow becomes observed at the next tool write remains too broad given finding 1. Qualify it until alias handling preserves the complete path.

VERDICT: NOT CONVERGED
