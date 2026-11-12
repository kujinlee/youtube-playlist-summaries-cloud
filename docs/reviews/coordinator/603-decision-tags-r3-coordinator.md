# Round 3 — `603-decision-tags` (PR #563, backlog #603) — coordinator — NOT CONVERGED (Claude), closed at the round cap

Claude half: `docs/reviews/claude/603-decision-tags-r3-claude.md`, reviewed `f22cf182` (the r2 fold).

REVIEW GAP: codex — alternation (rounds 2+ run ONE half; round 3 is Claude's).

```yaml
round: 3
fixes_nontrivial: true
subject: 603-decision-tags
halves:
  codex: skipped
  claude: ran
findings:
  - {id: F1, severity: Low, aim: deliverable, fix_induced: true, component: decision-scan, disposition: fixed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: false, component: decision-scan, disposition: filed}
  - {id: F3, severity: Low, aim: instrument, fix_induced: true, component: self-test, disposition: fixed}
```

Severity mapping: a review's MAJOR is `High`, MINOR is `Low`. **F1 and F3 were caused by the r2 fold** (F3's
instrument is decision-scan's own self-test). F2 is pre-existing: all five shapes were silent counts under the r1
composer too. The r2 fold only restated the false claim in the docstring.

## THRASHING — ARMED, filed, not run

Round 2 (X1–X3, caused by the r1 `<details>` auto-open and the new ancestor stack) and round 3 (F1, F3, caused by
the r2 implicit-`</p>` closing) both carry findings caused by the previous round's own fold, in ONE component:
`decision-scan` (`_DecisionScan` in `scripts/brief-compose.py`). That is the arming condition
(`docs/dev-process.md`; `docs/review-method.md` → *The arming condition — full account*). Phase 6 is **ARMED**.

It is **not run tonight** (usage wind-down). It is filed as **backlog #616**, *Phase 6 architecture review of
`brief-compose` decision-scan: a hand-written HTML visibility model thrashed r2→r3*. The row asks the Phase 6
question, *can a redesign remove the class?* It names two candidates: refuse every mark that is not a direct
descendant of an allowlisted visible-container chain, or verify visibility with a real parser or browser at build
time. F2 is its first evidence.

Decision log (`docs/reviews/decision-scheme/decision-log.jsonl`): the r2 ACCRETE bet is scored `continued` (lost on
its named observation). A DEFER row closes the unit at round 3, skipping `redesign` and `split` with a stated reason:
no round 4 can score either bet, and the redesign is #616's question. `check-decision-scheme.py` exits 0.

## What changed — and what this fold deliberately did NOT do

- **F1: a mark ON or INSIDE `<svg>`/`<math>` is REFUSED** (`_DECISION_REFUSE_FOREIGN`). The message is *"it is on or
  inside a <svg>, foreign content whose visibility this check does not model — move the mark outside the <svg>"*.
  `svg` and `math` are also added to `_P_SCOPE`. Stopping at the foreign ROOT is a superset of stopping at
  `foreignObject`/`desc`/`mi`/`mtext`/…, so a hidden `<p>` stays open across them, and keeping a p can only refuse.
  That second half matters after the `</svg>`. In `<p hidden>x<svg><foreignObject><div>d</div></foreignObject></svg><span
  data-decision>` the span is still inside the hidden p, and refusing marks inside `<svg>` alone would have counted it.
  The scanner was NOT taught the foreign-content scope rules. A grep of the 34 fragments finds no mark in an `<svg>`
  or `<math>`.
- **F2: the docstring now states the REAL bound, and nothing was fixed.** It no longer claims that a stale stack "can
  only cause a refusal, never a silent count". It now says that an explicit end tag pops with no scope check and no
  re-opening of formatting elements. As a result, misnested hidden markup can be counted and not seen. It names the
  reviewer's shapes and points to the Phase 6 row. No re-opening logic was built, because that is a third patch to
  the component that is thrashing.
- **F3: the survivors are pinned in both directions.** A new case covers each of these: only a HIDDEN formatting
  element keeps the p (`<p hidden>a<b>c<div data-decision>` COUNTS); `li`, `hr` and `h2` close the p (each COUNTS);
  `object` is a scope stop (`<p hidden>x<object><div data-decision>` REFUSES). A second case covers the reviewer's
  four SVG/MathML shapes, a mark ON `<svg>`, a mark inside `<svg>`/`<math>` that names the foreign refusal, a hidden
  p that stays open across `</svg>`, and a mark after a closed `<svg>` that still counts.

Self-test 224 → 226 on Python 3.12 and 3.14. Manifest 86 → 94, with the pin changed in
`scripts/mutations/expected_mutations.py`. The 8 new mutations cover: the formatting check ignoring `hidden`;
`object`, `li`, `hr` and `h2` removed from their sets; `svg`/`math` removed from `_P_SCOPE`; and the ON-foreign and
INSIDE-foreign refusals disabled. They were run with `check-plan-code.py --mutate . --only scripts/brief-compose.py`
on the worktree. That is a full tree, `docs/` included: a staged copy of only `scripts/` + `docs/` was refused
CANNOT RUN (no `node_modules`, `.claude/hooks`, …). That refusal is the harness guarding against the
missing-`docs/` artefact the reviewer hit.

All 34 fragments were re-composed on both interpreters. The 33 decision-free pages are byte-identical to master's
composer once the generation stamp is normalised. The walkthrough reads 13 / 2 remaining / 11 answered.

## Not done

- **F2 is not fixed.** Misnested hidden markup (`<p>a<b hidden>c</p><div data-decision>`,
  `<div><b hidden>x</div><p data-decision>`, `<p hidden>x<object></p><div data-decision>`, an end tag crossing a
  table cell) is still counted and not seen. It is hostile misnesting, and no real fragment has it. Filed as #616's
  first evidence.
- **Phase 6 is armed and not run** (backlog #616).
- **No check makes a fragment mark EVERY owner decision**: backlog #615, unchanged.

Review closed at the round cap: round 4 would only FILE.
