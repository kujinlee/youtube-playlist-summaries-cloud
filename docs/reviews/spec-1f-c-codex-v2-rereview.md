# Codex Re-Review (round 2) — Stage 1F-c Downloads spec (v2)

**Model:** gpt-5.5 · **Date:** 2026-07-10 · **Verdict:** PART A all fixed/partial; PART B 0 new Blocking, 2 High (content-type propagation, ASCII filename not guaranteed ASCII / undici crash risk). NOT converged.

**PART B — New / Remaining Defects**

No new Blocking findings.

**High**

1. **ASCII fallback still fails for non-ASCII titles, despite claiming Korean/unicode support.**  
   §4.3 defines `name = title?.trim() || base`, then `filename="<asciiSafe(name)>.<ext>"`: [spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md:93). But `asciiSafe` only strips controls and a few separators; it does not replace non-ASCII. For title `건강`, the fallback can become `filename="건강.md"`, contradicting D7/C14’s “ascii base-key fallback”: [spec D7](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md:37), [C14](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md:125). This may also fail header construction in Fetch/undici for code points outside ByteString range. Fix: derive `filename` fallback from sanitized `base` when `title` is not pure printable ASCII, and reserve unicode for `filename*`.

**Medium**

1. **Inline MD content type is internally contradictory.**  
   D11/§4.3/C20 say inline MD must be `text/plain`, but URL Contracts and C3 still say `md=text/markdown` / `200 text/markdown inline`: [spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md:102), [spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md:113). Fix those rows to say inline MD is `text/plain`; download MD is `text/markdown`.

**Low**

1. **`ShareServeContext` double-read latency should be acknowledged but is safe.**  
   The proposed MD branch calls `getShareServeContext` twice. Current implementation is read-only selects plus token hashing/date checks, no writes/RPC/charge: [lib/share/serve.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/share/serve.ts:18). This preserves the one-request-boundary TOCTOU model from 1F-b. Add a note that this is intentionally two DB resolver reads on share MD responses.

2. **Import guard fix is exact-file, not graph-recursive.**  
   Adding `file-response.ts` to `shareSources` works with the current guard because it is an explicit scan list: [tests/lib/share/import-guard.test.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/lib/share/import-guard.test.ts:16). Keep the §7 “pure dependency-free leaf” assertion; otherwise future imports from that helper may escape the intended proof even if they do not directly match forbidden regexes.
