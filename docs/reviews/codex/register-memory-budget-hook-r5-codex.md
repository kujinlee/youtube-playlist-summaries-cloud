<!-- codex-review: model=gpt-6.1-sol -->

1. **P2 — The hard-link boundary is broader than stated.**  
   **Location:** `.claude/hooks/check-memory-index-budget.sh:108`; claims at `:98` and `.github/workflows/ci.yml:536`.

   **Reproduction:** In temporary checkouts A and B, give A a healthy index and B a 29,000-character index. Create `A/hardlink-to-B` with `os.link(B/docs/memory/MEMORY.md, A/hardlink-to-B)`. Invoke:
   ```sh
   printf '%s' "$PAYLOAD" | bash A/.claude/hooks/run-hook.sh check-memory-index-budget.sh
   ```
   where `PAYLOAD` names that hard link.

   **Result:** rc 0, silence. B’s canonical path reports `OVER BUDGET`. The alias is **inside a checkout**, contradicting the claim that in-checkout hard-link aliases are seen. Only A’s index is compared.

   **Fix:** State the actual bound: hard links are detected only when a candidate checkout’s canonical index shares their identity. Links inside unrelated checkouts remain undiscoverable without an additional checkout registry. Add this negative-boundary case.

2. **P2 — Truncation can erase the warning that determines whether anything is emitted.**  
   **Location:** `.claude/hooks/check-memory-index-budget.sh:147–149`.

   **Reproduction:** Replace the checker in a temporary checkout with:
   ```python
   print("x" * 5000)
   print("WARNING overflow")
   ```
   Invoke its canonical index through `run-hook.sh`.

   **Result:** rc 0, no output. The hook truncates before searching for `WARNING`, losing the advisory.

   **Fix:** Determine whether to warn from the complete captured output before truncating the displayed text. Preserve a warning summary when its original line falls beyond the cutoff.

3. **P3 — The header retains a superseded pathname-based bound.**  
   **Location:** `.claude/hooks/check-memory-index-budget.sh:47–49`.

   **Reproduction:** Make `A/docs/memory/MEMORY.md` a symlink to a 29,000-character `B/other.md`, then invoke A’s index through `run-hook.sh`.

   **Result:** rc 0, `OVER BUDGET` from A’s checker. The header promises `NOT MEASURED` because the resolved target lacks the canonical index pathname. The coordinator explicitly superseded that expectation under file identity.

   **Fix:** Rewrite this header paragraph around candidate-index identity and align it with the corrected hard-link bound.

Execution coverage:

- Reran the rounds 1–4 reproductions through `run-hook.sh`, including harness and lexical aliases, newline siblings, case aliases, in-checkout hard links, linked worktrees, checker failures, and undecodable output. Earlier failures are fixed, subject to the documented identity change.
- Loops, dangling links, long chains, spaces, quotes, dot segments, relative paths, unset/odd `PWD`, missing `tool_input`, and malformed payloads caused no unexpected hook failure. The filesystem rejected non-UTF-8 filenames.
- Sleeping checker: **20.150 s**; checker spawning a child: **20.108 s**. Both returned rc 0 with `NOT MEASURED`. These demonstrate synchronous delay, not rejection of the completed tool call.
- Checker crashes and exit 7 produced advisories. Ten MB of output was truncated before emission; capture itself remains unbounded.
- Non-memory edits: **106 ms median, 168 ms maximum**, ten runs.
- Hook self-tests: **24/24**. Command-checker controls: **45/45**. **All 34 mutations failed every declared named case.** Live registration passed; unregistered-hook and stale-exemption controls failed.
- Repository files remained unchanged.

VERDICT: NOT CONVERGED
