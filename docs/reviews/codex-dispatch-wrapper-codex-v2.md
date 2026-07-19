<!-- codex-review: model=gpt-5.5 -->

> **TRUNCATED ARTEFACT — this file is evidence of a bug, not a normal review.**
> The original was 308,229 bytes because the then-current wrapper extracted everything after
> the first `codex` marker in stdout, which swallowed the entire tool-call transcript
> (file dumps and all) into the 'review'. That is one of the defects this round reported.
> Switching to `codex exec -o/--output-last-message` fixed it structurally; later rounds
> (v3/v4/v5) are a clean ~2 KB each. The final findings are preserved below.

---

TTP 429) — no model will succeed)
  [PASS] timeout: got=try_next (codex exited 124)
  [PASS] codex missing: got=try_next (codex exited 127)
  [PASS] REGRESSION: prompt mentioning 429/unauthorized: got=try_next (CLI reported HTTP 400 — model unusable with this CLI)
  [PASS] REGRESSION: real review ABOUT auth code: got=ok (551 chars)
  [PASS] H1: error AFTER reply began, exit 0: got=try_next (no `tokens used` completion marker — the turn did not finish (or the CLI output format changed); failing closed rather than certifying a partial run)
  [PASS] H2: CLI reformat — no markers at all, exit 0: got=try_next (no `tokens used` completion marker — the turn did not finish (or the CLI output format changed); failing closed rather than certifying a partial run)
  [PASS] M1: review containing a bare `codex` line is not truncated: got=ok (359 chars)

12/12 passed

codex
The self-test passes, but I found two parser ambiguities the tests don’t cover: the echoed prompt is not delimited from the real `codex` marker, and `tokens used` is accepted from anywhere in the output. I’m validating whether those are exploitable with small classifier fixtures before calling them findings.
exec
/bin/bash -lc "python3 - <<'PY'
import importlib.util
spec=importlib.util.spec_from_file_location('cr','scripts/codex-review.py')
cr=importlib.util.module_from_spec(spec); spec.loader.exec_module(cr)
out=(\"OpenAI Codex v0.142.5\\n--------\\nmodel: gpt-5.5\\n--------\\nuser\\n\"
     \"Prompt includes a fixture line:\\ntokens used\\n1,234\\n\"
     \"codex\\n\" + (\"Partial review text after a stream cut. \"*20) +
     '\\nERROR: {\"type\":\"error\",\"status\":500,\"error\":{\"message\":\"stream interrupted\"}}\\n')
print(cr.classify(0,out))
print('completed/body_len', cr.split_regions(out)[2], len(cr.split_regions(out)[1]))
PY" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
exec
/bin/bash -lc "python3 - <<'PY'
import importlib.util
spec=importlib.util.spec_from_file_location('cr','scripts/codex-review.py')
cr=importlib.util.module_from_spec(spec); spec.loader.exec_module(cr)
out=(\"OpenAI Codex v0.142.5\\n--------\\nmodel: gpt-5.5\\n--------\\nuser\\nReview parser\\ncodex\\n\"
     + (\"Opening analysis before quoted trailer. \"*8)
     + \"\\n"'```'"\\ntokens used\\n4,456\\n"'```'"\\n\"
     + (\"Finding after the quoted token marker that should survive extraction. \"*6)
     + \"\\ntokens used\\n9,999\\n\")
print(cr.classify(0,out))
print('---extracted---')
print(cr.extract_response(out))
PY" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
exec
/bin/bash -lc "python3 - <<'PY'
import importlib.util
spec=importlib.util.spec_from_file_location('cr','scripts/codex-review.py')
cr=importlib.util.module_from_spec(spec); spec.loader.exec_module(cr)
out=(\"OpenAI Codex v0.142.5\\n--------\\nmodel: gpt-5.5\\n--------\\nuser\\n\"
     \"Please review this transcript:\\n"'```'"\\nuser\\nhello\\ncodex\\nhi\\n"'```'"\\n\"
     \"codex\\n\" + (\"Real finding text. \"*20) + \"\\ntokens used\\n1,234\\n\")
print(cr.classify(0,out))
print('---extracted---')
print(cr.extract_response(out)[:300])
PY" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
('ok', '392 chars')
---extracted---
hi
```
codex
Real finding text. Real finding text. Real finding text. Real finding text. Real finding text. Real finding text. Real finding text. Real finding text. Real finding text. Real finding text. Real finding text. Real finding text. Real finding text. Real finding text. Real finding text. Re

 succeeded in 0ms:
('ok', '324 chars')
---extracted---
Opening analysis before quoted trailer. Opening analysis before quoted trailer. Opening analysis before quoted trailer. Opening analysis before quoted trailer. Opening analysis before quoted trailer. Opening analysis before quoted trailer. Opening analysis before quoted trailer. Opening analysis before quoted trailer. 
```

 succeeded in 0ms:
('ok', '878 chars')
completed/body_len True 878

codex
Findings:

**H1 - `tokens used` completion can be spoofed by echoed prompt text**  
[scripts/codex-review.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:106), [classify check](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:161)  
`completed = bool(TOKENS_USED.search(output))` scans the entire combined output, including the echoed prompt. If the review prompt contains a fixture with a bare `tokens used` line, an exit-0 run that dies mid-stream after `codex` but before the real trailer is accepted as complete. I reproduced this with a partial review plus trailing `ERROR: ... status 500`; `classify(0, out)` returned `ok`. This means the positive completion requirement is real in name, but not anchored to the CLI trailer.

**H1 - A bare `codex` line in the echoed prompt can certify prompt text as the review**  
[scripts/codex-review.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:111) through [line 120](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:120)  
`split_regions()` takes the first bare `codex` after `user`, but the region after `user` starts with the echoed prompt. A prompt that quotes a transcript containing a bare `codex` line is misparsed as the model marker. The extracted review then starts inside the prompt and can exceed `MIN_REVIEW_CHARS` even if the actual model reply is empty/banner-only. This fixes M1 for model replies, but introduces the same ambiguity on the prompt side.

**M1 - Reviews quoting a bare `tokens used` line are truncated**  
[scripts/codex-review.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/codex-review.py:119)  
After finding the reply start, the parser cuts at the first `tokens used` line in `rest`. A legitimate review can quote a Codex transcript containing:

```text
