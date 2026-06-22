# Adversarial Review — Gemini `responseSchema` Reliability Fix

**Date:** 2026-06-21
**Reviewer:** Claude adversarial (general-purpose subagent) — **Codex fallback**

> ⚠️ **Codex gap.** The Codex adversarial pass (`codex:codex-rescue`, `--fresh`) failed with
> `API Error: 529 Overloaded` (0 tokens, 0 tool uses). Per `docs/plugins.md` (Codex-fallback rule:
> *unavailable for ANY reason → do not block; run a Claude adversarial review in its place*), a
> Claude adversarial review was run instead and satisfies the gate. **Re-attempt the Codex-specific
> pass before merge if access returns.**

## Verdict: YES-WITH-FIXES → all blocking-class fixes applied

Change is safe in the narrow sense (compiles, additive, Zod+retry preserved). Three fidelity gaps
were flagged that would re-create the "fail Zod → retry identical prompt" loop for value-level
errors. All three addressed.

## Findings & resolution

| # | Sev | Finding | Resolution |
|---|-----|---------|------------|
| H1 | High | Magazine `sections` missing `minItems:1` (Zod has `.min(1)`) | **Fixed** — added `minItems: 1` (`lib/gemini.ts`). |
| H2 | High | `videoType`/`audience` dropped enum constraint though SDK supports `format:"enum"` | **Fixed** — `{type:STRING, format:'enum', enum:[...VideoTypeSchema.options]}` / `AudienceSchema.options` (drift-free, derived from Zod). |
| M1 | Med | Ratings integers unbounded (1–5 not expressible in SDK subset) | **Documented** — in-code comment now names integer-range as a Zod-only constraint. Not fixable downstream. |
| M2 | Med | `.strict()` no-extra-keys not expressible in API schema | **Documented** — comment notes responseSchema does not subsume strict mode; Zod remains the net. |
| M3 | Med | New test verified plumbing only; couldn't catch H1/H2/M1 drift, didn't lock required/optional split | **Fixed** — test now uses exact `required` (`toEqual`), asserts `minItems:1` on sections, asserts enum `format`+values on videoType/audience, and takeaways min/max. |
| L1 | Low | Root-cause framing: responseSchema is a strong bias, not an absolute guarantee; only fixes the structural class | **Adopted** — commit message will claim only the structural/trailing-comma class, not "all invalid-JSON." |
| L2 | Low | Mock spread `...jest.requireActual` correct & consistent across all 6 files | No action. |
| L3 | Low | `label`/`text` `.min(1)` not expressible | Left to Zod. No action. |

## Verification after fixes
- `tests/lib/gemini-response-schema.test.ts`: 3/3 pass.
- Full jest suite: **907/907** pass.
- `tsc --noEmit`: only the 2 pre-existing unrelated `tests/lib/html-doc/theme.test.ts` errors; none introduced.
