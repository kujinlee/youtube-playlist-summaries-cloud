# Claude Re-Review (round 3) — Stage 1F-c Downloads spec (v3) — CONVERGED

**Reviewer:** Claude (opus) · **Date:** 2026-07-10.
**Verdict:** PART A — all 5 round-2 findings (2 High + 1 Med + 2 Low) genuinely FIXED, verified across every cross-reference. PART B — **0 new Blocking, 0 new High** (convergence signal); 2 cosmetic Low nits only.

## PART A — round-2 findings
- **B-H1 (inline-md text/plain propagation) → FIXED.** D11, §4.3, §5 (both rows), C3, C20 all agree: inline md=`text/plain`, download md=`text/markdown`, html=`text/html`. Download rows C2/C8 correctly `text/markdown`. No remaining "text/markdown inline". The sniffing-XSS closure holds because the behaviors table (test contract) now ships `text/plain`.
- **B-H2 (ASCII filename + undici crash) → FIXED.** §4.3 `filename="<asciiSafe(base)>"` (always base key, never title) + `filename*=encodeRFC5987(title||base)`; `asciiSafe` now collapses `[^\x20-\x7e]` → provably printable-ASCII, structurally eliminating the undici Latin-1 throw. D7/C13/C14/§4.3 now one rule. Confirmed `asciiSafe` is idempotent/lossless on the already-ASCII base key.
- **B-M1 (guard leaf) → FIXED.** §7 states the guard is a flat non-recursive grep; the plan MUST add the explicit leaf assertion (`file-response.ts` has no `import … from '@/…'`) + the `.filter(existsSync)` TDD-order note. The guarantee is anchored to the leaf assertion, not the append.
- **B-L1 (regex range) → FIXED.** §4.3 warns to place `-` at a class edge so `+-.` isn't a range admitting `,`.
- **B-L2 (precedence) → FIXED.** §4.2 pins `format` before `TOKEN_RE` + lookup → `/s/<malformed>?format=pdf` = 400; C11 limited to valid/absent format.

## PART B — new
No new Blocking/High/Medium. Cross-checks clean: `filename*` RFC-5987-valid (trailing `.ext` chars are all attr-char); no header-injection surface; Referrer-Policy asymmetry preserved (owner none, share no-referrer); `nosniff` on every response; D12 mid-request re-check intact + read-only.

### Low (cosmetic, non-blocking)
- Base-key-is-ASCII is an assumption but `asciiSafe` handles it defensively (degrades a hypothetical unicode slug to `_` safely; `filename*` carries the real name). Worth one clause in the plan so an implementer doesn't flag the degraded path as a bug.
- C13 wording was generic `<ascii>` vs D7/C14's base-key — tightened in v4.

## Convergence
**Converged.** Round 3 returned 0 new Blocking/High/Medium — this round is the gate. Recommend user spec-approval → `writing-plans`.
