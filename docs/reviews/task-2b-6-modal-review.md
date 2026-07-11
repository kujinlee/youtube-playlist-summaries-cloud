# Claude Task Review — Stage 2b Task 6 (NewPlaylistModal, §13)

**Reviewer:** Claude (independent subagent). **Diff:** `8946cb3..96c7e0e`. **Date:** 2026-07-11.

## Verdict (round 1)
- **Spec compliance:** ✅ — all 4 dismissal paths gated by `submitting` (guardedClose + disabled on ✕/Cancel); playlistId===null stays open + exact message + no onSuccess + reset; onSuccess only on non-null; 401→router.replace('/login') no post-nav setState; IngestError→role=alert+reset, generic otherwise; focus trap symmetric (forward + reverse in code); inside-dialog click stopPropagation. Traced + confirmed the DOM-only icon deviation (⚠ → aria-hidden span) is needed for RTL getNodeText exact-match and is state-machine/copy/role-neutral.
- **Code quality:** Approved. Real tokens only. Tests non-vacuous (submitting-guard exercises all 4 paths against a real pending promise; focus-trap asserts activeElement moved via the component's own trap logic since jsdom has no native Tab).

## Severity disagreement vs. Codex (controller adjudication)
Claude rated double-submit re-entrancy **informational** (Enter + click both route through the single `<form onSubmit>`; React flushes state between discrete events so `disabled={submitting}` suppresses a second real dispatch — "no realistic UI path"). Codex rated it **High** (no synchronous ref lock → two same-window submits fire createIngest twice). **Controller decision:** this is a spend/velocity-guardrail-adjacent path; a synchronous `submittingRef` mutex is ~3 lines and unambiguously correct — applied (fix commit) rather than resting on "no realistic path." Also closed Codex's 3 test-strength Lows: double-submit test, Shift+Tab reverse-wrap test, re-enable-after-reset assertions.

## Claude Minors (non-blocking, noted)
1. `submitting` not reset after successful onSuccess — relies on parent unmounting (intended). 2. `focusables()` `:not([disabled])` applied only to button/input selectors — harmless (no href/textarea/select in this modal), latent if extended. 3. Shift+Tab test gap (inherited from brief) — closed by the fix.

Re-review both per iterative re-review (the guard is a behavior change). See `-codex.md` + `-v2-rereview.md`.
