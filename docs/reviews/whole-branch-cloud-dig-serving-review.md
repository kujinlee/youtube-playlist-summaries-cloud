# Whole-Branch Review — feat/cloud-dig-serving

**Range:** `55ce4bf..1988351` (6 code commits) · **Date:** 2026-07-14
**Reviewers:** Codex (gpt-5.5) + Claude (independent) — both scoped to emergent/integration defects the per-task reviews could not see.
**Verdict:** **MERGEABLE — 0 Blocking, 0 High (both reviewers).** One Medium (M1, same finding from both) decided as accept-by-design; 4 Low accepted. This round is the convergence gate.

---

## Convergence

Both reviewers independently verified all four spec §11 risk areas end-to-end against ground-truth source and returned **0 Blocking / 0 High**. They surfaced the **same single Medium** (M1) and nothing else of substance. A full dual re-review round with no Blocking/High = convergence.

### Risk areas — verified sound by both
- **Money invariant (end-to-end):** neither route's dig branch nor `loadDigForServe` nor dig-state reaches `resolveMagazineModel`/`reserve_serve_model`/`resolveAndParse`/`generateDig`/`generateMagazineModel`. The html dig branch returns on every path and cannot fall through into the summary charging flow. `loadSummaryForServe` (reused by loader + dig-state) does not charge. The money unit test is non-vacuous (positive control reaches `rpc('reserve_serve_model')` then `default: throw` before Gemini; negatives are fail-closed `.mockRejectedValue`).
- **Owner isolation (end-to-end):** the list prefix `dig/{base}/` derives `base` from the owner's own validated `mdKey` (never attacker-influenced); `SupabaseBlobStore.list` roots at the authenticated `${p.id}/${p.indexKey}/`, calls `assertLogicalKey` (rejects `/`, `..`, `\0`), strips exactly the owner root. No cross-tenant enumeration.
- **Shared-code safety:** `readOnly=false/nonce=undefined` is byte-identical to pre-branch (`nonceAttr(undefined)===''`; the const→function refactor byte-compared identical); under `readOnly=true` every emitted `<script>`/`<style>` is nonced; partition omits exactly the nav-coupled controls.
- **Version awareness:** loader + dig-state both filter `.r${DIG_GENERATOR_VERSION}.md` off the same shared `base`; cannot disagree on current version. The loader-404 vs dig-state-200-`[]` on zero-dug divergence is intentional and correct (render needs content; state query does not).

---

## M1 (Medium) — dig-state vs serve loader consistency — ACCEPTED BY DESIGN

**Finding (both reviewers):** dig-state derives `sectionIds` from filenames only (`list`+filter); the serve loader opens each blob and skips malformed/vanished ones (behavior 19). For a corrupt/foreign current-version blob, dig-state reports it dug while the serve omits it (and 404s if it was the only one).

**Reviewer split on the fix:** Codex → make dig-state parse too (shared enumerator). Claude → the spec §3 Unit C *deliberately* specifies dig-state as cheap "list-and-filter, no blob read"; document the over-report and keep it (recommended).

**Disposition (accept-by-design, per spec):** §3 Unit C already designs dig-state as filename-authoritative. Making it parse every blob per poll contradicts the approved "cheap state query" contract and adds real cost for a **corruption-only** edge with **no live consumer** (the frontend that reads dig-state is a deferred slice; §9 out-of-scope). Impact is UX-only — no money, no isolation. **Documented** in the spec (§3 Unit C addendum) and in a code comment at `dig-state/route.ts`. If the future frontend needs exact render-parity it validates against the serve response rather than pushing parse cost into the polling endpoint. No code-behavior change.

---

## Low / nits — all accepted (no code change before merge)

- **L1 (test quality):** the behavior-24 byte-identity test proves the new params are a mutual no-op but not identity vs *pre-branch* bytes. Manually verified the const→function refactor is byte-identical; existing `render-dig-deeper.*` substring tests corroborate. Optional future golden snapshot.
- **L2 (type):** `LoadDigResult.language` (`'en'|'ko'`) is a cast of `load.video.language`; a legacy language-less video → runtime `undefined`, absorbed by the renderer's `language='en'` default. Harmless type unsoundness.
- **L3:** version filtering is filename-only (frontmatter `genVersion` not cross-checked against the `.r{V}` suffix). Correct in practice (generation writes both consistently); diverges only under corruption.
- **L4 (known Minor):** `dig/${base}/` + `.r${V}.md` duplicated in loader + dig-state. Behaviorally equivalent; a future dig-key-scheme change must touch both. Cleanliness-only — candidate for a later shared-helper pass.

## Accumulated cross-task deviations — all verified benign by both reviewers
- 3 pre-existing BlobStore mock `list` stubs — none of those suites exercises `list`; mask nothing.
- Money test automock (not `jest.spyOn`, per Next16/SWC gotcha) — guard still fails on a real charge regression (non-vacuous).
- `outputFolder` `.get()`→`.has()` — only change is empty `?outputFolder=` now 400s (intended); matches the pdf route (`.has()` already).
- B14 re-pin (`type=dig-deeper→400` → `type=bogus→400`) — coverage preserved, no regression masked.

**Bottom line:** merge-ready. Full suite 2265/2265, tsc EXIT=0. Push/PR/merge remains the human gate.
