# clickable-dashboard-asks — round 2, coordinator adjudication

**REVIEW GAP: claude** — as round 1. This session does not spawn subagents, so the Claude
half was not run. Recorded, not hidden; the cost is stated in the r1 document and is
unchanged.

* Codex: `docs/reviews/codex/clickable-dashboard-asks-r2-codex.md` (`gpt-5.5`) —
  **0 Blocking, 0 High, 1 Medium, 1 Low. CONVERGED** on its own stated criterion.
* Verdict: `docs/reviews/verdicts/clickable-dashboard-asks-r2-codex.verdict.json`,
  `gate_ran: true`. The stem matches the review basename this round, because `--out`
  wrote straight into `docs/reviews/codex/`.

Round 2 existed to review **the r1 fix**, on this repository's measured basis that a fix
generates the next round's defect. It did, and the rule paid for itself twice.

## M1 — `choose` could click a STALE floater and send the wrong option

**ALREADY FIXED in `099bdb74`, and the convergence is the story.** The coordinator
reproduced this in Chrome while r2 was still running; Codex reproduced it independently in
Playwright on the committed artifact. Two instruments, two sessions, one defect, the same
failing shape:

| | coordinator (Chrome) | Codex (Playwright) |
|---|---|---|
| tray opened as | `Project dashboard — "2026-09-14 18:54 · bb265c08 …"` | `What changed — "You tried to answer…"` |
| instead of | the question + the chosen option | the question + the chosen option |

⭐ **Severity disagreement, recorded rather than smoothed.** Codex filed it Medium; the
coordinator filed it **High** and stands by that. The tray does not merely fail — it opens,
accepts the question, and reports **"✓ Sent"** while carrying the previous selection's
context. A reader believes they answered; the session receives something else. Codex's own
sentence agrees with the reasoning even where the label differs: *"worse than a missed
click because the tray is live but carries the previous selection context."*

⭐ **How the coordinator found it: by obeying its own brief.** The r2 prompt instructed the
reviewer to RE-DERIVE r1's cleared attacks rather than inherit them, and the coordinator
ran that instruction against its own code. r1 had cleared the floater selector — correctly,
for the question it was asked (*can it grab a heading's button?* No). The stale-floater
case is a different question about the same line. **Nothing in r1 was wrong; the attack was
simply narrower than the line.**

Fixed by **identity, not delay**: the handler records the floater existing before
`dispatchEvent` and refuses it (`f !== stale`). A longer timeout would have passed and
would have been a timing assumption — the shape `portable-practices.md` §24 was written the
same day to refuse. Verified with the identical reproduction that failed.

## L1 — the r1 regression test was too narrow, and it was a substring assertion AGAIN

**ACCEPTED AND FIXED.** Codex: the case rejected the despaced substring
`".pick{display:none"` only, missing hiding by an ancestor, `visibility:hidden`,
`opacity:0`, or a media-scoped rule.

⛔ **The sharp part is the recurrence, which Codex named:** this branch had *already*
regressed through a page-wide substring assertion (the collapsed-title survivor CI caught),
and the repair written for that regression was **itself a substring assertion**. Fixing the
instance and re-committing the class.

Now every emitted rule whose SELECTOR mentions `.pick` is parsed and its declarations
inspected, so the spelling no longer decides whether the guard can see it. **Measured
against four hiding spellings — the old case caught one, the new case catches all four:**

```
control (unmutated)                                   325/325
A  body.nosend .needs .pick{display:none}   -> RED    (old case: also red)
B  .needs .pick{visibility:hidden}          -> RED    (old case: GREEN — missed)
C  .needs .opts li .pick{opacity:0}         -> RED    (old case: GREEN — missed)
D  @media(...){.needs .opts .pick{display:none}} -> RED (old case: GREEN — missed)
```

Codex also called the adjacent `"closest('.pick')"` assertion incidental. **Partly
conceded and NOT fully fixed:** it is still a text assertion. A behaviour-shaped test needs
a browser, which this suite does not have, and a browser is what found M1. The case exists
so the wiring cannot be silently deleted; it is labelled as weaker in place, the same
trade-off the collapsed-title case records. **Stated as a known limit rather than closed.**

## Codex notes worth carrying, neither filed as a defect

* On `file://` in headless Chromium the tray's clipboard write **rejected** and surfaced
  its error note. So *"opened as a file → Send copies instead"* — which the page's own mode
  chip asserts — is **not proven** by anything on this branch. That is the lifted tray's
  behaviour and a headless-clipboard restriction, not this change's, but the page makes the
  claim, so it is recorded as unproven rather than assumed.
* `check-plan-code --self-test` returned 125/128 in a detached clean worktree purely
  because ignored `node_modules/typescript` was absent. Environment, not defect; 128/128 in
  the real checkout.

## Verified on this tree

```
gen-dashboard   --self-test  325/325
check-plan-code --self-test  128/128
manifest 67 -> 68, declared sum 632 -> 633
control: removing `f !== stale`      -> 324/325, red via the case that names it
control: four hiding spellings A-D   -> all RED via the rule-scanning case
```

**NOT CONVERGED — round 3 owed.** Both repairs above postdate the tree r2 was dispatched
against, so by this branch's own gate the code that merges has not been reviewed. Round 3
is a verification round against the final tree.
