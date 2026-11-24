# Round 4 — `decision-buttons` (PR #628) — coordinator — NOT CONVERGED (Codex half); BLOCKER answered by a REDESIGN

```yaml
round: 4
fixes_nontrivial: true
subject: decision-buttons
halves:
  codex: ran
  claude: gap
findings:
  - {id: B1, severity: Blocking, aim: deliverable, fix_induced: false, component: sent-state, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: sent-state, disposition: fixed}
```

REVIEW GAP: claude — alternation (round 4 is the Codex half)

Codex (`docs/reviews/codex/decision-buttons-r4-codex.md`, model gpt-6.1-terra: NOT CONVERGED, one BLOCKER and one
Minor) reviewed head `48bc031f`, the round 3 fold. In the header, severities use the vocabulary
`check-review-decision.py` validates (BLOCKER → Blocking, Minor → Medium). The Minor is fix-induced: the r3 fold
added the forget-at-load loop to a script that was still only emitted while a decision was open.

## The round-cap answer — thrashing, answered by a redesign

From round 4, findings are FILED unless they are BLOCKERs (`docs/review-method.md` §0 Q4c). B1 is a BLOCKER, so it
is folded. The question the cap asks, *thrashing or the prose floor?*, has this answer: **thrashing.** Three
consecutive rounds found a way for one of two identical decisions to show the other's *sent* state, and each one
was found against the previous round's own patch to the occurrence-order suffix:

| Round | Finding | What it broke |
|---|---|---|
| r2 | Codex C1 | two identical decisions shared one key; r2 added an occurrence suffix |
| r3 | Claude F1 | recording twin A made B the first OPEN occurrence, so B took A's key; r3 counted done tags too |
| r4 | Codex B1 | REMOVING twin A makes B the first occurrence, so B takes A's key; counting cannot see a removal |

Patching the ordinal a third time would leave the class open (any edit that reorders twins moves the state). The
redesign removes the class instead: **a twin is an authoring error.** It is also ambiguous to the session reading
`questions.md`, which cannot tell which of two identical sections an answer belongs to, so it is not a case worth
supporting.

| Finding | Disposition | Evidence |
|---|---|---|
| **B1** (BLOCKER): removing one of two identical decisions makes its twin inherit the *sent* state | **fixed (redesigned)** | `render_decisions` now REFUSES (CANNOT RUN) two `data-decision` tags whose base key is equal: the same label (whitespace folded) and the same question. The question is the marked element's text as the card's script reads it: entities decoded, whitespace folded, a `<button>`'s text left out (`_DecisionScan._text`, which collects text per marked element on the scanner's existing stack, so an implicitly closed `<p>` stops collecting where the browser closes it). The message names both decisions with their lines and tells the author to give one a distinct `data-decision-label`. In `DECISION_JS`, the occurrence suffix (`SEEN` and its counting) is removed, and `key()` is just the base key. The done-tail stripping in `baseKey` stays, because forget-at-load needs a done tag to compute the same key it had when it was open. **Measured before the change:** each of the 37 `docs/explainers/*.fragment.html` was run through the new `render_decisions`. 3 have decisions (13 + 28 + 4 = 45), with 45 distinct base keys, and none is refused, which matches r3's count. |
| **M1** (Minor, fix-induced by r3 F2): `DECISION_JS` was not emitted on an all-done page, so forget-at-load never ran there | **fixed** | The composer now emits it whenever the page has any decision (`if decisions:`), done ones included. On an all-done page it offers no buttons (there is no `.ex-decision-open`), but it forgets each done decision's key. |

**Bound, stated:** the refusal compares the question as a Python HTML scan reads it, and the card hashes it as the
browser's DOM reads it. Where the two disagree (misnested markup, or an element other than `<p>` closed
implicitly, the same bound `_DecisionScan` already states), a twin could pass the refusal. Every such shape is
hostile markup that no real fragment has. Nested decisions are read by the scan without the inner tag's text, so
in that case the scan errs toward refusing.

## Cases and mutations

- **Replaced:** the r3 twin case ("recording one of two identical decisions does not hand its 'sent' to the other"),
  and S6's twin pair. S6's decision 2 now asks its own question, and its case is renamed "…not another unlabelled
  one…".
- **New:** "decision twins: two identical decisions are REFUSED, naming both; a distinct label or question is
  accepted (r4)". It covers an entity-encoded twin that hides behind a `<button>`, a done twin of an open one, a
  distinct label accepted, and a distinct question accepted.
- **New:** "buttons: on a page with no twins each card's key is its BASE key…". Under node, it builds a page with
  one question under two labels plus a done decision. It asserts each tag's `exKey`, and the stored keys, against
  keys computed independently in Python (page, label less ordinal, FNV-1a over the question's UTF-16 code units).
- **Rewritten:** the emission case is now "the pick script ships with any decision, all answered included, and not
  with none (r4)".
- **Mutations** (`scripts/mutations/brief-compose.json`). Retired: "identical decisions are no longer told apart by
  occurrence" and "occurrences are counted over OPEN decisions only again". Both targeted the suffix, which no longer
  exists. Retargeted: the 400-character mutation now points at the renamed S6 case, and the "ANSWERED tail left in
  the key" mutation now points at the forget-at-load case. Added: the refusal disabled; a `<button>`'s text read into
  the question; a suffix put back on the key; the script shipped only while a decision is open. Pin 102 → 104.

## Decision log

One `redesign` row was appended to `docs/reviews/decision-scheme/decision-log.jsonl` (not retroactive, `outcome:
null`). Its bet is that no later round finds a composed page on which one card shows a sent state another card
sent. Its stated risk is the Python-scan / DOM disagreement above.

## Gates (worktree, after the fold)

- `python3 scripts/brief-compose.py --self-test`: 251/251. Two twin cases were replaced by the refusal case and the base-key case, and the emission case was rewritten. The docstring count is now 251.
- `python3 scripts/ask_answerer.py --self-test`: 125/125.
- `check-ratchet-contract`, `check-selftest-counts` (97 scripts verified), `check-docs`, `check-review-rounds`, `check-decision-scheme`, `check-explainer-delivery`: all rc 0. The first `check-decision-scheme` run refused a `redesign` row that did not record skipping `accrete`, so the row now declares `skipped: [accrete]` with its reason.
- `python3 scripts/check-plan-code.py --mutate . --only scripts/brief-compose.py`, run in a scratch copy of this tree (a detached git repo): 104 mutations, 104 killed, 104 attributed to the case each names, 0 survivors, re-control passed (rc 0). This was measured over ONLY scripts/brief-compose.py, a diagnostic slice, not the full sweep.
- `check-review-decision.py`: ROUND_OWED. This fold's fixes are non-trivial, so round 5 (the Claude half, under the alternation) is owed.
