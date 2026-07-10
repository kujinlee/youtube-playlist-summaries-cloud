# Task 3 review — principal-aware model store (single upsert writer) + `generatorVersion`

**Commit:** `3d14638`
**Gate:** single round Claude + Codex (not a §8 trigger). Execution: SDD.

## Reviews
**Claude task-review — Approved** (no Critical/Important). Verified via direct file reads + own `tsc --noEmit` (clean) + focused `jest` (4 suites/35 tests pass): single upsert writer `writeModelEnvelope` → one `blobStore.put(...)`, **no `putStaged`/`promote` for the model** (Option A integrity); `Principal` param on both fns + all call sites; `rerender.ts` **reuses in-scope `principal`** (F9), `build-doc-html.ts` computes inline (no prior principal in scope — matches brief); `generatorVersion` stamped-on-write from `GENERATOR_VERSION`, returned on read; old envelope lacking `generatorVersion` parses (`.optional()` in a `.strict()` object → unknown-key-only rejection); local behavior unchanged (arg substitution only). Genuine overwrite/upsert test (v2→v3 same key, read v3, `promote` spy never called, no `_staging`). **The two adapted pre-existing tests are byte-for-byte assertion-identical** — only `dir`→`localPrincipal(dir)`, no weakening.

**Codex adversarial — SOUND** (no Critical/Important/Minor). Independently confirmed: Option A integrity, upsert via `upload({upsert:true})`, the overwrite test, pure call-site test adaptations, `tsc` clean, `generatorVersion` stamping + optional-parse. (Codex couldn't run jest — sandbox EPERM on haste-map; Claude ran it.)

## Process note (raised by Claude, now closed)
Per-task `docs/reviews/task-*.md` artifacts were missing (SDD trail lived in the gitignored ledger + scratchpad). Closed: this file + `task-1f-a-1-reserve-rpc.md` + `task-1f-a-2-magazine-caps.md` committed; produced per-task going forward.

## Result
Tests: RED→GREEN, focused 398 pass, `tsc` clean, full suite green. **Task 3 COMPLETE.**
