# Claude Re-Review (round 2) — Stage 1F-c Downloads spec (v2)

**Reviewer:** Claude (opus) · **Date:** 2026-07-10.
**Verdict:** PART A — all 8 v1 findings genuinely FIXED (the Blocking re-check faithfully mirrors `s/route.ts:57-59`, verified read-only/no-double-charge). PART B — **0 new Blocking, 2 new High + 1 Medium + 3 Low**, all reconciliation defects from the v2 rewrites. NOT converged.

## PART B — new
### High
- **B-H1 — inline-MD `text/plain` fix not propagated: C3 (line 113) + §5 URL contracts (lines 102-103) still say `text/markdown` inline.** The behaviors table is the test contract; following C3 ships `text/markdown` inline → reopens the sniffing-XSS the D11/C20 fix closes. **Fix:** C3 → `text/plain` inline; split §5 md cells into inline=`text/plain` / download=`text/markdown`.
- **B-H2 — ASCII filename fallback self-contradiction + crash risk.** D7/C14 say the ASCII `filename=` half is the base key; but §4.3 `name = title?.trim() || base` uses the title for BOTH halves, and `asciiSafe` strips `[\x00-\x1f\x7f]"\/;` only — NOT `0x80-0xFF` — so `asciiSafe("건강")="건강"` → `filename="건강.md"` (not ASCII, violates RFC 6266, fails C14). Codex adds: a non-Latin1 `filename=` value **throws in undici/Fetch** (header ByteString range) — a runtime crash, not just a contradiction. **Fix:** ASCII half = `asciiSafe(base)` always (per D7); `filename*` = `encodeRFC5987(title?.trim() || base)`; and make `asciiSafe` also collapse `[^\x20-\x7e]` so the ASCII half is provably printable-ASCII. Reconcile D7/C13/C14/§4.3.

### Medium
- **B-M1 — the reused import guard is a flat non-recursive grep;** adding `file-response.ts` to `shareSources` catches only forbidden imports written *in that file*, not transitive ones. The "cannot smuggle in charging code" guarantee rests on the **pure-leaf assertion** (§7), which isn't in the shown guard. **Fix:** the plan MUST add an explicit leaf assertion (`file-response.ts` has no `import … from '@/…'`), not merely append the path; note `shareSources` uses `.filter(existsSync)` (TDD-order: file must exist when the guard runs).

### Low
- **B-L1 — `encodeRFC5987` allowlist content is RFC-5987-correct** (exact `attr-char`), but a literal regex class `[!#$&+-.^_\`|~]` makes `+-.` a **range** admitting `,`. Order `-` literal.
- **B-L2 — share `format` vs syntactic `TOKEN_RE` precedence unpinned** (`/s/<malformed>?format=pdf` → 400 or 404?). Security-neutral (both token-content-independent); pin it (validate `format` first → 400).
- **B-L3 — MD path calls `getShareServeContext` twice** — verified benign (SELECT-only, no double-charge, cost = the HTML path's existing 2 lookups; TOCTOU bounded to the accepted one-request boundary). No action.

## Convergence
Not converged — 2 new High (both cheap reconciliation fixes: propagate `text/plain` to C3/§5; make the ASCII filename half provably ASCII). Round 3 need only re-verify (a) C3/§5/C20 agree on inline=text/plain, and (b) D7/C13/C14/§4.3 agree on one filename rule with a provably-ASCII `filename=`.
