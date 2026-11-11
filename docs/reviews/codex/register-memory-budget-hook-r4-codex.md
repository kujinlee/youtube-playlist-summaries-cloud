<!-- codex-review: model=gpt-6.1-sol -->

1. **P2 — Case aliases silently bypass the check on this case-insensitive filesystem.**  
   **Location:** `.claude/hooks/check-memory-index-budget.sh:62`, `:90`.

   **Reproduction:** In a temporary checkout B, write 29,000 characters through `B/docs/memory/memory.md`. Confirm that the canonical `MEMORY.md` now contains those characters. Send the lowercase path as `tool_input.file_path` through `run-hook.sh check-memory-index-budget.sh`.

   Result: **rc 0, no output**. Sending the canonical path reports **OVER BUDGET**. `B/DOCS/MEMORY/MEMORY.md` also silently bypasses detection. `realpath()` preserves these spellings, while `is_index()` requires exact component strings.

   **Fix:** Identify the canonical index using filesystem identity on filesystems supporting case aliases. Avoid globally lowercasing paths, which would misidentify distinct files on case-sensitive filesystems.

2. **P2 — Hard-link edits change the index without triggering detection.**  
   **Location:** `.claude/hooks/check-memory-index-budget.sh:90`.

   **Reproduction:** Create a hard link named `hardlink` to B’s canonical index. Write 28,000 characters through it; verify the canonical index changed. Invoke the registered launcher with the hard-link path.

   Result: **rc 0, no output**. The canonical path reports **OVER BUDGET**. Symlink resolution cannot discover another hard-link name.

   **Fix:** Compare edited files against candidate canonical indexes using `os.path.samefile()`. Explicitly document any remaining boundary for hard links outside discoverable checkouts.

   Findings 1–2 also refute the unconditional “until the next tool write to the index” statement at `.github/workflows/ci.yml:535`. The stated bound covers resolved non-index targets, but these aliases never reach its `NOT MEASURED` arm.

3. **P2 — Undecodable checker output makes the advisory hook fail.**  
   **Location:** `.claude/hooks/check-memory-index-budget.sh:120–125`.

   **Reproduction:** Replace the checker in a temporary checkout with:
   ```python
   import os
   os.write(1, b"\xff")
   ```
   Invoke its canonical index through `run-hook.sh`.

   Result: **rc 1, traceback, no structured advisory**. `text=True` raises `UnicodeDecodeError`, which neither exception handler catches.

   **Fix:** Capture bytes and decode with replacement, or specify `errors="replace"`. Preserve an advisory `NOT MEASURED` response for decoding failures. The header’s “always exits 0” and CI’s corresponding assertion currently overclaim. This demonstrates hook failure; it does not demonstrate rejection of an already completed tool call.

All reported defects from rounds 1–3 were rerun in temporary copies. Their original reproductions now behave as intended, including harness aliases, lexical aliases, newline checkout and filename siblings, and non-index resolved targets.

Other execution results:

- Hook self-tests: **20/20**. Command-checker controls: **45/45**. All **34 mutations fail every declared named case**.
- Live registration passes; an unregistered hook and a stale exemption each fail.
- Checker exceptions, exit 7, and signal termination produce advisories at rc 0.
- A sleeping checker times out after **20.095 s**, reporting `NOT MEASURED`. A checker spawning a child also returned after approximately 20 seconds.
- A checker printing 10 MB completes at rc 0 but forwards approximately **10 MB of additionalContext**; output has no size cap.
- Missing `tool_input`, malformed payloads, relative paths, symlink chains, loops, dangling links, FIFO indexes, and a real linked worktree behaved without an unexpected hook failure.
- Non-memory edits: **78 ms median, 105 ms maximum**, 30 runs.
- The filesystem rejected non-UTF-8 filenames, limiting that attack’s coverage.

Repository files were unchanged.

VERDICT: NOT CONVERGED
