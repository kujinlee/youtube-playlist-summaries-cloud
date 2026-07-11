# Codex Adversarial Review — Stage 2b Task 2 (createIngest + guardrail matrix)

**Reviewer:** Codex (gpt-5.5). **Diff:** `5136d31..b867dae`. **Date:** 2026-07-11.
**Verdict:** No Blocking. 1 High + 2 Medium + 1 Low.

## Findings
1. **[HIGH] `createIngest` throws raw `TypeError` on 422 with JSON body `null`** (lib/client/api.ts). `res.json().catch(() => ({}))` only handles parse *failures*; a valid JSON `null` (or any non-object) resolves, then `body.limit` dereferences `null` → `TypeError`, bypassing `IngestError`/`ingestErrorMessage`. Defeats the whole guardrail-copy matrix (user gets a raw crash instead of friendly copy). *Fix:* guard `body && typeof body === 'object'` before reading `limit`/`found`.
2. **[MEDIUM] Non-numeric `Retry-After` → `NaN` in copy** (lib/client/api.ts). `h ? Number(h) : 60` yields `NaN` for `Retry-After: later` → "try again in NaNs." *Fix:* `Number.isFinite(n)` fallback to 60.
3. **[MEDIUM] Test gap: 422 fallback not exercised through `createIngest`** (only at `ingestErrorMessage` level) — misses the null-body crash and doesn't assert stringy `{limit:"50",found:"80"}` falls to generic copy.
4. **[LOW] No test for malformed `Retry-After`** — only numeric-present + absent are covered.

Core matrix strings exact for 400/403/422/429/502/503/default; 401 correctly throws `UnauthorizedError`; `import type` from producer is browser-benign; dropping `getJobStatus` from the Task 2 import is benign (Task 3's export). jest 18/18, tsc 0.
