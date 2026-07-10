# Codex Re-Review (round 3) — Stage 1F-c Downloads spec (v3) — CONVERGED

**Model:** gpt-5.5 · **Date:** 2026-07-10 · all 5 round-2 findings FIXED; 0 new Blocking/High/Medium.

- **B-H1 content-type propagation: FIXED.** D11, §4.1, §4.3, §5, C3, and C20 now agree: inline MD is `text/plain; charset=utf-8`; MD download is `text/markdown`; HTML is `text/html`. I found no remaining `text/markdown inline` wording. Evidence: [spec lines 41, 57, 91, 102-103, 113, 131](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md:41).

- **B-H2 ASCII filename fallback: FIXED.** D7 says ASCII fallback is sanitized base key and `filename*` carries Unicode title; §4.3 now specifies `filename="<asciiSafe(base)>.<ext>"` and `filename*=...<encodeRFC5987(title?.trim() || base)>...`; C13/C14 match. `asciiSafe` now replaces controls and `[^\x20-\x7e]`, so the `filename=` half is provably printable ASCII. Evidence: [spec lines 37, 93-95, 124-125](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md:37).

- **B-M1 guard leaf: FIXED.** §7 now explicitly says the guard is a flat non-recursive grep, adds the required leaf assertion that `file-response.ts` contains no `import … from '@/…'`, and notes `.filter(existsSync)` means the file must exist before the guard runs. Evidence: [spec line 139](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md:139).

- **B-L1 regex range: FIXED.** §4.3 now explicitly warns to put `-` at a regex-class edge so `+-.` is not parsed as a range admitting comma. Evidence: [spec line 95](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md:95).

- **B-L2 precedence: FIXED.** §4.2 pins share-route precedence: validate `format` before `TOKEN_RE` and lookup, so `/s/<malformed>?format=pdf` returns 400. C11 remains limited to valid/absent format. Evidence: [spec lines 65, 115, 121](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md:65).

**PART B**

No new **Blocking** or **High** findings. Convergence signal: the v3 reconciliation edits close the prior round’s security-relevant contradictions.

No new Medium findings.

Low: one wording nit remains in §7: “empty / all-non-ASCII title → `summary`/base fallback” is a little imprecise now that ASCII `filename=` always comes from `base`, never title. The authoritative rules in §4.3/C13/C14 are consistent, so this is not a behavioral contradiction; it would just be clearer as “empty title falls back to base for `filename*`; ASCII `filename=` always uses sanitized base, or `summary` only if base sanitizes empty.” Evidence: [spec lines 93-96, 136](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md:93).

Confirmations: the ASCII filename is now truly always ASCII; collapsing `[^\x20-\x7e]` in `asciiSafe` does not break the base key because `{serial}_{slug}` is already ASCII; inline MD as `text/plain` is still the right call for non-executable same-origin rendering; C13/C14/D7/§4.3 now agree on one filename rule.
tokens used
27,407
**PART A**

- **B-H1 content-type propagation: FIXED.** D11, §4.1, §4.3, §5, C3, and C20 now agree: inline MD is `text/plain; charset=utf-8`; MD download is `text/markdown`; HTML is `text/html`. I found no remaining `text/markdown inline` wording. Evidence: [spec lines 41, 57, 91, 102-103, 113, 131](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md:41).

- **B-H2 ASCII filename fallback: FIXED.** D7 says ASCII fallback is sanitized base key and `filename*` carries Unicode title; §4.3 now specifies `filename="<asciiSafe(base)>.<ext>"` and `filename*=...<encodeRFC5987(title?.trim() || base)>...`; C13/C14 match. `asciiSafe` now replaces controls and `[^\x20-\x7e]`, so the `filename=` half is provably printable ASCII. Evidence: [spec lines 37, 93-95, 124-125](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md:37).

- **B-M1 guard leaf: FIXED.** §7 now explicitly says the guard is a flat non-recursive grep, adds the required leaf assertion that `file-response.ts` contains no `import … from '@/…'`, and notes `.filter(existsSync)` means the file must exist before the guard runs. Evidence: [spec line 139](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md:139).

- **B-L1 regex range: FIXED.** §4.3 now explicitly warns to put `-` at a regex-class edge so `+-.` is not parsed as a range admitting comma. Evidence: [spec line 95](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md:95).

- **B-L2 precedence: FIXED.** §4.2 pins share-route precedence: validate `format` before `TOKEN_RE` and lookup, so `/s/<malformed>?format=pdf` returns 400. C11 remains limited to valid/absent format. Evidence: [spec lines 65, 115, 121](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md:65).

**PART B**

No new **Blocking** or **High** findings. Convergence signal: the v3 reconciliation edits close the prior round’s security-relevant contradictions.

No new Medium findings.
