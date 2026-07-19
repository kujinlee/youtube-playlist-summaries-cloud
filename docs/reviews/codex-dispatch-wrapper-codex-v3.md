<!-- codex-review: model=gpt-5.5 -->

**Findings**

**High: timeout can still be accepted as a successful review**  
[scripts/codex-review.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:140), [scripts/codex-review.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:149), [scripts/codex-review.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:96)  
On `TimeoutExpired`, `run_codex()` sets `code = 124`, then still reads `msg_path` if it exists. `classify()` checks message length before looking at `exit_code`, so any file content `>= MIN_REVIEW_CHARS` passes even though the wrapper itself says a hung review “must fail the gate.” I reproduced the classifier shape: `classify(124, "[wrapper] timed out...", "partial..." * 20)` returns `("ok", ...)`. If `codex -o` ever creates/writes the file before full process completion, a partial timed-out review can be certified.

**Medium: advisory auth-prose scan can still be spoofed by echoed prompt and skip viable fallback models**  
[scripts/codex-review.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:107), [scripts/codex-review.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:206)  
`AUTH_PROSE` is matched against full stdout, which still includes echoed prompt text. If the prompt contains “usage limit”, “not logged in”, etc., and the current attempt produces no final-message file without a structured `ERROR` line, `classify()` returns `ABORT`; `main()` then breaks instead of trying the next model. This cannot create a false pass, but it can make the Codex gate fail unnecessarily when a later candidate might have succeeded.

**Prior Findings Check**

The old stdout-parser defects are structurally gone in active code. There is no active `split_regions`, `extract_response`, `cli_chrome`, marker slicing, bare `codex` delimiter, or `tokens used` completion check. Success is only `message.strip()` length at [line 96](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:96), and `message is None` fails closed at [line 110](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:110).

On stale files: the `mkstemp` then `unlink` flow at [lines 126-128](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:126) eliminates stale files from previous wrapper runs in normal operation. I do not see a stale-file acceptance bug absent an external same-user race creating that exact random temp path between unlink and CLI open.

Verification run: `python3 scripts/codex-review.py --self-test` passes `12/12`.
