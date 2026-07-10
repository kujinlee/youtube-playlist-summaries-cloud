# Task 5 review — nonce + dig + print-listener in shared render (§8 shared-code trigger)

**Commits:** `39bf16d` (impl) → `5e6533c` (test hardening: click-causes-print + listener-form regex)
**Gate:** §8 iterative dual-adversarial re-review (shared already-merged render code). Execution: SDD.
(The implementer's own in-loop self-review docs are `docs/reviews/task-5-render-nonce-{review,codex}.md`; its self-run Codex hung — the known subagent-sandbox issue — so it self-reviewed with Claude. This file records the authoritative **coordinator-run** dual gate.)

## Dual gate — both CONVERGE (no Blocking/High/Medium)
**Codex (coordinator, gpt-5.5) — CONVERGES.** Verified: `render-dig-deeper.ts` imports/calls the new function exports, passes no nonce, wires `printListenerScript()` (`:479`); removed shared const imports gone from `lib`/`tests`; local callers unchanged (`generate.ts:58`, `rerender.ts:71` — no nonce, dig default true); `buildSummaryCsp` matches D7 directives, no `unsafe-*`; nonce = `randomBytes(16)` base64; for `{nonce, dig:false}` all inline `<script>`/`<style>` nonced; `[\s\S]*` rewrite correct; tsc clean.

**Claude (coordinator, opus) — CONVERGES.** Independently ran tsc (exit 0) + 9 focused suites (217 tests). Confirmed: second consumer correctly updated + jsdom parity test drives the click and asserts print fires for BOTH docs with per-script try/catch isolation (can't false-green the print path); test consumers **strengthened** not loosened (`render.test.ts` asserts `not.toContain('onclick=...')` AND `toContain('window.print()')`; `theme.test.ts` asserts no inline onclick + `addEventListener('click'` + `window.print()`); `NAV_SCRIPT` now module-private, no other importer); CSP exactly D7, nonce 128-bit base64 distinct per call, `render-nonce.test.ts` sweeps every `<script>` tag for the nonce; local parity (`showDig = opts.dig ?? true`), navScript `.replace` mechanical/exact.

## Low findings — FIXED (`5e6533c`, both reviewers)
- Print-parity test could false-green if an inline script called `print()` at load → now asserts `printSpy` 0 before click, exactly 1 after, for both summary + dig-deeper.
- Nonce listener regex had a weak `|window.print()` fallback → now requires `addEventListener('click'...)[\s\S]*window.print()` (the real D11 form).

## Carry-forward → Task 7 (both reviewers agree: Task-7 WIRING concerns, NOT Task 5 defects — buildSummaryCsp is test-only in this diff, no route wires it yet)
- Scope `buildSummaryCsp` to the summary view + `dig:false` on cloud (D12 dig-suppressed).
- Add `connect-src` if the cloud page makes any fetch (currently omitted — a footgun once wired).
- `#t=` deep-link scroll behavior under `dig:false` (dropped in the dig-suppressed path).

## Result
Tests: RED→GREEN, focused 350→357 pass, full suite 1722 pass, `tsc` clean; second consumer compiles + prints; local behavior-identical. **Task 5 COMPLETE — §8 converged.**
