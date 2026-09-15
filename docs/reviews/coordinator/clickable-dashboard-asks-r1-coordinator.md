# clickable-dashboard-asks — round 1, coordinator adjudication

**REVIEW GAP: claude** — the Claude half was not run. This session is configured not to
spawn subagents, and a Claude adversarial half requires one. Recorded rather than hidden,
and the same shape as PR #299's rounds 1-10, which each carried a written
`REVIEW GAP: claude` for a structural reason. **What this costs is stated, not waved
past:** a single reviewer has been wrong on this repo before — `dual-review-halves-are-
not-redundant` records a Codex-only round clearing a money guard that the skipped Claude
half caught in one pass. Treat this round's CONVERGED as weaker evidence than a dual one.

In partial compensation the coordinator ran its own adversarial pass BEFORE the review
and filed two corrections from it (`451417d1`); those are author self-review, **not** an
independent half, and are labelled as such below.

* Codex: `docs/reviews/codex/clickable-dashboard-asks-r1-codex.md` (`gpt-5.5`) —
  **0 Blocking, 0 High, 1 Medium. CONVERGED.**
* Verdict: `docs/reviews/verdicts/r1-codex.verdict.json`, `gate_ran: true`,
  `head bb265c08`, `dirty {}`.
  ⚠ The verdict stem is `r1-codex`, not the review document's basename, because `--out`
  pointed at a temp path. Round 2 writes `--out` straight into
  `docs/reviews/codex/` so its verdict carries the matching stem.

## M1 — the chooser was hidden in local-file mode, where the tray still delivers

**ACCEPTED AND FIXED.** `PICK_SCRIPT` returned early on `location.protocol === 'file:'`,
setting `body.nosend`, and CSS hid every `.needs .pick`. The reasoning was "Send does not
work from a bare file, so do not offer a control that cannot deliver".

The reasoning was wrong about the mechanism. The tray **degrades rather than dying**: in
local mode it relabels Send to Copy and puts the composed question on the clipboard.
Codex quoted both the relabel and the clipboard write. So the branch removed a path that
still works — and the page's own mode chip says so in the same breath: *"opened as a file
→ Send copies instead"*. The control contradicted the sentence beside it.

⭐ The general form, which is why this is worth more than its severity: **I asserted what
one delivery mechanism cannot do, where the rule is to assert what the thing DOES.**

**Fixed**: no `file:` branch, no hiding rule. Two cases changed:

* `the choose wiring ships with the page` was bound to `classList.add('nosend')` — an
  incidental line that this very fix deletes. A case anchored to an incidental line dies
  with the line and would have read as *"the wiring is gone"* when only the flag was. Now
  bound to `closest('.pick')`, the handler itself.
* new: `the chooser is not hidden in local-file mode, where the tray falls back to Copy`.
  Control: re-introducing a `body.nosend .needs .pick{display:none}` rule turns it red at
  323/324. Verified.

## What Codex CLEARED, with evidence — three of the coordinator's own attack points

Recorded because a cleared attack is a result, and because the next round should not
re-derive them from scratch:

| attack | verdict |
|---|---|
| the 40ms timer is a race | **Not a race against today's tray**: the tray schedules floater creation at 10ms during the dispatched event, before the 40ms timer is registered. Codex still preferred a poll; the coordinator had already replaced it with a bounded 10×30ms poll in `451417d1` |
| the floater query grabs a heading's button | **Cannot**: heading buttons carry inline `right/top/opacity/transition`, never `position:fixed`; only the floater is positioned that way. Matches the coordinator's live measurement of zero idle `.askbtn` with an inline `fixed` |
| `display:inline` on `h4.q` breaks sibling traversal | **No** — styling only. And it confirmed independently that the composed tray injects into `h2, h3` only, so no redundant h4 ask button appears |

It also confirmed the new cases are not vacuous under deletion, that the collapsed-title
slice matches the emitted shape with no nested braces, and that the manifest anchors are
unique with `expect` names exactly equal to case names (attribution is exact equality).

## ⚠ Two limits of this round, stated

1. **`--mutate .` was NOT completed by the reviewer.** Codex started the sweep and stopped
   at 160/632 while still in unrelated manifests; full attribution is unverified by it.
   CI runs the full gate — and on this branch CI has already caught one survivor that
   local reasoning missed, so that is the instrument, not this round.
2. **The fallback branch is unexecuted.** The button relabelling to *"select the text and
   use ask"* needs a page with no tray, and Chrome automation refuses `file://`. It is a
   degradation path, not a correctness path.

## Coordinator self-review, filed as author work rather than as a review half

* A comment claimed the tray "attaches its own ask button to every H1-H4". Measured false:
  injection is `querySelectorAll('h2, h3')`; `nearestHeading()` matches `H[1-4]`. The `h4`
  choice is better than the comment claimed and for an unstated reason — visible to the
  section resolver, invisible to the button injector. Corrected in `451417d1`.
* A single 40ms shot at the floater was replaced by a bounded poll: *"wait a bit and
  assume"* is the shape `portable-practices.md` §24 was written the same afternoon to
  refuse.

## Verified on this tree

```
gen-dashboard   --self-test  324/324      (323 before M1's fix added a case)
check-plan-code --self-test  128/128
control: re-introducing the hiding rule -> 323/324, red via the case that names it
```

**NOT CONVERGED — round 2 owed.** M1's repair is unreviewed code, and this branch's own
CI gate asks whether the tree that merges was reviewed. Round 2 runs against the current
tree.
