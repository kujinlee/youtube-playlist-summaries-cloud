# Codex Adversarial Review — Stage 1F-c Downloads spec (v1)

**Model:** gpt-5.5 · **Date:** 2026-07-10 · **Verdict:** 1 Blocking, 1 High, 3 Medium, 2 Low. Core money short-circuit verified sound; findings are hardening.

**Blocking**

- **Share MD download bypasses 1F-b’s mandatory final re-check.**  
  Spec §4.2 returns `fileResponse(mdBytes...)` immediately after the blob read, matching [app/s/[token]/route.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/s/[token]/route.ts:37). The existing route only re-checks token liveness/un-promote later at [lines 57-59](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/s/[token]/route.ts:57), after parse/model read.  
  Failure sequence: token is live at `getShareServeContext` line 28, blob read succeeds line 37, owner revokes token or flips artifact away from `promoted`, new MD branch returns bytes before the line 58 re-check. This violates predecessor 1F-b D14/B10b and C11/C16.  
  Fix: every share `200`, including `format=md`, must perform the same pre-response `getShareServeContext` re-check immediately before returning bytes. Add B10b revoke/un-promote tests for `format=md`.

**High**

- **The money import guard will not cover the new shared helper.**  
  Spec D10 says extend B18b/B18c so share MD reaches no charging code, but the current guard scans only `app/s`, `lib/share`, and [lib/html-doc/read-model.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/lib/share/import-guard.test.ts:16). The proposed `lib/html-doc/file-response.ts` is imported by the anonymous share route but would not be scanned.  
  Failure sequence: implementation adds `import { fileResponse } from '@/lib/html-doc/file-response'`; helper later imports a charging-adjacent module or RPC helper; B18b still passes because [tests/lib/share/import-guard.test.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/lib/share/import-guard.test.ts:41) never opens that file.  
  Fix: include `lib/html-doc/file-response.ts` in the guard, or better add a small recursive import graph guard for all share-route runtime imports. Keep helper pure.

**Medium**

- **Spec has contradictory bad-format vs denied-token precedence.**  
  §4.2/C5 says share `format=pdf` is validated before token lookup and returns `400`. C11 says malformed/expired/revoked/unknown token with “any `format`” returns coarse `404`. These cannot both be true.  
  Failure sequence: `/s/short?format=pdf` could reasonably be implemented as either `400` or `404`; tests will encode one and the spec says both.  
  Fix: define precedence explicitly. If bad format wins, amend C11 to “any valid/absent format”.

- **Inline raw Markdown is under-specified for browser safety.**  
  C3/C18 allow `format=md` without `download` to serve raw bytes inline as `text/markdown`, but `fileResponse` does not require `X-Content-Type-Options: nosniff`. Raw MD can contain embedded HTML from source/model content. On the owner route this is same-origin with the app.  
  Fix: require `X-Content-Type-Options: nosniff` on MD and HTML file responses. Consider making MD always `attachment`, or serve inline MD as `text/plain; charset=utf-8` if inline view is necessary.

- **Filename rules are not precise enough to be injection-safe.**  
  §4.3 says `asciiSafe` strips `"`/`;`/path chars, but does not explicitly reject/control CR, LF, other CTLs, backslash, leading dots, or empty fallback. `Video.title` is only `z.string()` with no `.min(1)` in [types/index.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/types/index.ts:47), and share DB rows are not schema-validated.  
  Failure sequence: title/base with CRLF or quoted-string escape edge cases breaks `Content-Disposition`, or empty title yields `filename*=UTF-8''.md`.  
  Fix: specify: strip all `[\x00-\x1f\x7f]`, `"`, `\`, `/`, `;`, collapse whitespace, trim dots/spaces, and if result is empty use a fixed fallback like `summary`. Percent-encode `filename*` from the full final filename.

**Low**

- **“Share title comes for free” is only partly true.**  
  `getShareServeContext` currently selects `data, owner_id` at [lib/share/serve.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/share/serve.ts:37), so title must be extracted from `vid.data.title`; there is no DB constraint requiring it. Existing integration seeds omit `title` in [tests/integration/helpers/seed.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/helpers/seed.ts:36).  
  Fix: return `title?: string` or validate `typeof data.title === 'string' && data.title.trim()`, then fallback to `base`.

- **“Byte-identical responses” is not a testable literal invariant for HTML.**  
  Existing HTML responses include a fresh nonce from [app/api/html/[id]/route.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/api/html/[id]/route.ts:87) and [app/s/[token]/route.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/s/[token]/route.ts:61).  
  Fix: define regression as “same render path, same status, same body modulo nonce, same CSP/cache/referrer headers, and no `Content-Disposition` when `download` is absent.”

Verified: the proposed owner MD insertion after [line 60](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/api/html/[id]/route.ts:60) is before `resolveMagazineModel` at line 75, and the share MD insertion after [line 37](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/s/[token]/route.ts:37) is before `readFreshMagazineModel` at line 54, so the direct money short-circuit is sound if the guard/helper issues above are fixed.
