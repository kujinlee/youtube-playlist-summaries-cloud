<!-- codex-review: model=gpt-6.1-sol -->

Reviewed `00fbf3f8..b32a3b28` first, then the final tree at `b32a3b28`. Three findings refute the stated bet; none duplicates C1, C2 or C6.

1. **High — unbounded stdin remains on registered guard paths.**  
   **Where:** `.claude/hooks/enforce-handoff-path.sh:36`, `.claude/hooks/enforce-selection-card.sh:35`, `scripts/check-selection-card.py:581`.  
   **Concrete input:** write `b'{}'` to a child’s stdin pipe and leave the pipe open. Both wrappers remained running at 3 seconds; the direct selection-card guard remained running at 4 seconds. They were killed by the probe. The wrappers block in `cat` before any bounded reader runs.  
   **Fix-induced:** No; unchanged by the SPLIT fold.  
   **Fix:** use `bounded_read.py --stdin` to populate temporary files, preserving bytes and checking its status; use `read_stream` in the selection-card guard. Add held-open and oversized-input child-process cases.

2. **Medium — the Stop hook silently repairs an invalid payload and reports success.**  
   **Where:** `.claude/hooks/block-idle-stop.sh:57`.  
   **Concrete input:** take a valid payload naming a transcript containing one user/assistant window, then insert a literal NUL immediately after its opening `{`. All three direct transcript guards returned **rc 2**, naming invalid JSON. The real hook returned **rc 0, empty stderr**: Bash command substitution discarded the NUL before forwarding the payload.  
   **Fix-induced:** No; reproduced with the pre-fold hook too. This concerns raw payload corruption, distinct from C1’s `session_id` path.  
   **Fix:** retain the bounded payload in a temporary file and redirect that file into each consumer. Add the invalid-NUL payload through the real hook.

3. **Medium — CI guard discards the reader’s refusal and returns OK silently.**  
   **Where:** `scripts/check-ci-watched.py:455–456`.  
   **Concrete input:** run `--decide` in an isolated Git checkout with stdin held open. It returned **rc 0 after 2.38 seconds**, with neither output nor diagnostic. Sending **1,048,577 bytes** also returned silent rc 0. `payload_from` discards `_why` and substitutes an empty payload.  
   **Fix-induced:** No in this fold; the existing policy deliberately preserves the CI verdict while losing the session column. That policy contradicts the stated bet.  
   **Fix:** propagate and name the refusal, returning CANNOT RUN when stdin cannot be read.

Verification:

- Foreground self-tests: **bounded_read 56/56**, **banner-armed 247/247**.
- Foreground mutation slice: **29/29 killed and attributed**, zero survivors.
- FIFO, `/dev/zero`, directory, and symlinks to each: all three transcript guards returned rc 2 naming `NOT_REGULAR`; handoff-path also named the reason.
- Exactly 1 MiB accepted; one byte over refused; 0.5-second-late payload accepted.
- Clean `env -i` plus PATH, from a subdirectory: malformed input returned rc 1. Held-open and oversized hook input also returned rc 1.
- Missing Python returned rc 2. Blocking-check failures likewise take precedence over `INPUT_RC`, return rc 2, and skip the CI observer; C5’s unconditional “every guard / exit 1” claim therefore needs qualification.

No files were changed. No file under `.claude/plans/` was read or quoted.

**NOT CONVERGED.**
