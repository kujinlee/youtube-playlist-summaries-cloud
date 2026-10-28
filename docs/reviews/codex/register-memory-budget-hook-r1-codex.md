<!-- codex-review: model=gpt-6.1-sol -->

1. **P1 — Harness-path edits silently bypass the newly registered check.**  
   **Location:** `.claude/settings.json:101`; cause: `.claude/hooks/check-memory-index-budget.sh:109`.

   **Reproduction:** In a `mktemp` checkout, write 26,000 characters to `docs/memory/MEMORY.md`; symlink `harness/projects/slug/memory` to `docs/memory`. Invoke the registered launcher with each path in `tool_input.file_path`:
   - Repo path: exits 0 and emits `OVER BUDGET` in `additionalContext`.
   - Harness symlink path: exits 0 with **no output**.

   The lexical matcher rejects the harness path before resolving its target. Consequently, `.github/workflows/ci.yml:535` overclaims detection “until the next tool write to the index”: a tool write through the normal harness alias remains invisible.

   **Fix:** Resolve symlink aliases before identifying the index and selecting its containing checkout. Add an integration case covering the actual harness directory symlink, and qualify the CI comment until that works.

2. **P2 — Emptying UNREGISTERED breaks a mutation’s named-case attribution.**  
   **Location:** `scripts/check-hook-commands.py:76`; affected expectation: `scripts/mutations/check-hook-commands.json:155`.

   **Reproduction:** In a temporary copy, apply the manifest mutation `main() ignores the root it is given`, then run `--self-test`. Its named case, `main() over a compliant world exits 0`, **passes**: the wrongly selected repository is now also compliant. Two other cases fail, so the mutation is killed, but **not by its declared case**. Of 34 manifest mutations, 33 satisfied every named expectation; this one did not.

   **Fix:** Make the named case discriminate between explicitly constructed roots independently of the live exemption dictionary, or update the manifest attribution to the cases that actually fail.

Other execution results:

- Malformed JSON, missing `file_path`, null inputs, a 10 MB payload, outside-repo paths, a symlinked repo `MEMORY.md`, checker exit 7, and a checker exception all returned 0. Adjacent `.bak` and `OTHER.md` paths stayed silent.
- A real linked worktree correctly reported its own over-budget index.
- Non-memory edits took **64 ms median, 93 ms maximum** across 30 runs here; acceptable locally. The 10 MB payload took approximately 876 ms.
- A substituted checker sleeping for 30 seconds kept the launcher running beyond a measured two-second deadline. Thus advisory exit handling does **not** guarantee prompt completion. This demonstrates synchronous waiting, not reversal or rejection of an already completed tool call. An unmodified checker rejected a FIFO index promptly.
- The live command checker passed; adding an unregistered hook or restoring a stale registered exemption each correctly returned 1. Its control suite passed **45/45**.

VERDICT: NOT CONVERGED
