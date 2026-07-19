<!-- codex-review: model=gpt-5.5 -->

**Findings**

- **High: `cli_chrome()` can hide CLI errors that occur after the `codex` marker but before `tokens used`, letting an error-only/partial run pass if exit code is 0.**  
  [scripts/codex-review.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:120)  
  `tail` starts at `tokens used`, so any diagnostic in the streamed model region is removed from `chrome`. Then `classify()` only checks `ERROR_LINE`/`AUTH_PROSE` against that stripped chrome. If the plugin/background path reports exit 0 and the body is over 200 chars, `extract_response()` will write the partial response plus error text as a valid review. Concrete shape:
  ```text
  user
  ...
  codex
  partial review text...
  ERROR: {"status":429,...}
  tokens used
  123
  ```
  `cli_chrome()` drops the `ERROR`, `extract_response()` keeps it, and `classify()` can return `OK`.

- **High: marker-missing fallback can certify CLI chrome as a review after a future CLI output reformat.**  
  [scripts/codex-review.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:94), [scripts/codex-review.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:147)  
  If `codex exec` stops printing a bare `codex` line, `extract_response()` returns the whole output. With exit 0 and any long warning/error/banner text not matching the exact `ERROR_LINE` or `AUTH_PROSE` patterns, `len(body) >= 200` becomes enough to pass. This directly reintroduces the “file containing only an error” class, just with a reformatted error like `Error: model requires newer Codex` or pretty-printed JSON.

- **Medium: `extract_response()` uses the last bare `codex` line, so a real review can be truncated or rejected.**  
  [scripts/codex-review.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:95)  
  A review can naturally contain a standalone `codex` line in a quoted transcript, command example, markdown/code block, or when discussing this wrapper. Because the parser slices from the last marker, everything before that line is discarded. If the remaining tail is under 200 chars, a real review is wrongly rejected; if it is over 200, the saved review is silently incomplete.

- **Medium: `ERROR_LINE` is too exact for the failure class it is meant to guard.**  
  [scripts/codex-review.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:57)  
  It only matches a line beginning exactly `ERROR:` with same-line JSON containing numeric `"status"`. Pretty-printed JSON, lowercase `error:`, `ERROR {...}`, status strings, or diagnostics wrapped with a prefix will not match. Combined with the exit-0 plugin path and the 200-char threshold, a long CLI error can still be accepted as a review.

- **Medium: treating every HTTP 429 as account-wide can wrongly reject a possible fallback model.**  
  [scripts/codex-review.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:62), [scripts/codex-review.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:137)  
  Some 429s are genuinely account/project quota, but others can be model-specific rate limits or capacity throttles. The current code aborts immediately and never tries lower-priority candidates. That is fail-closed, but it can wrongly reject a real Codex review that a fallback model could have produced.

- **Low/Medium: `MIN_REVIEW_CHARS = 200` is both too weak and too strong depending on parser state.**  
  [scripts/codex-review.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:52), [scripts/codex-review.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:148)  
  Too weak: a verbose CLI error or warning can exceed 200 chars if markers are missing or error text is in the extracted body. Too strong: a legitimate “no findings” review can be concise, especially if the prompt asks for only blocking findings. Length is useful as a secondary guard, but it is not a reliable review predicate by itself.

**Open Question**

- Is the wrapper expected to accept only reviews with a structured finding format? If yes, the fix should validate content shape, not just character count. A minimal version would require either a finding heading/severity or an explicit “No findings” verdict, and reject outputs containing CLI error signatures anywhere in the extracted body.
