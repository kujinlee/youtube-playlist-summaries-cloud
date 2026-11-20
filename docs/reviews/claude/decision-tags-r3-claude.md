Reviewed head: 867e18b7

# decision-tags — round 3, Claude half

Subject: `git diff origin/master...HEAD` — §3a of `.agents/skills/shared/explainer-delivery.md` after the r2 fold
(the copied refusal list replaced by a pointer to the scanner's symbols).

Method: every §3a claim checked against `scripts/brief-compose.py` (`_DecisionScan`, `render_decisions`, the
`_DECISION_*` constants at 1111–1141); two fragments composed outside the repository (scratchpad, style block lifted
from a real fragment) with `brief-compose.py --content <frag> --slug t<x> --title T --out <scratch>/o<x>.html`.

## Gates

- `python3 scripts/check-docs.py` → last line `Documentation integrity OK`, rc=0
- `python3 scripts/check-explainer-delivery.py` → `explainer delivery: 1 shared description, 5 skills cite it, 0 restatements`, rc=0

## Claims that held (tried to refute, could not)

- The three table rows, composed as one fragment (a): `🟨 ✍ DECISION 1 of 3`, `🟩 ✍ DECISION 2 of 3 — ANSWERED: Yes — owner, 11-11`,
  `🟨 ✍ D7 — DECISION 3 of 3`; counter `✍ 3 decisions on this page · 2 remaining · 1 answered` + `next:` link. rc=0.
- Tag as FIRST child: `edits[at + len(text)] = tag` (brief-compose.py:1360) — inserted right after the start tag.
- All-answered counter text `… · 0 remaining · all answered`, no link (brief-compose.py:1373-1374); empty/whitespace
  value is OPEN via `(value or "").strip()` (1285) and `if answer:` (1353); no mark → markup unchanged, no counter (1335-1336).
- Every symbol the pointer names exists: `_DECISION_REFUSE_ON` (1118), `_DECISION_REFUSE_INSIDE` (1128),
  `_DECISION_HIDING_ATTRS` (1130), the `<details>`/`<summary>` rule (`_DETAILS_REFUSAL` 1197, used 1268/1281), the
  id/name collision (`self.ids` from `("id", "name")` at 1247-1249, refused at 1341-1345 only for generated ids 1..N).
- The CSS/misnesting bound matches the `_DecisionScan` docstring (⚠ THE BOUND, CORRECTED r3).
- No other skill doc under `.agents/` or `.claude/commands/` describes decision markup, so nothing contradicts §3a.

## Findings

- **MINOR — .agents/skills/shared/explainer-delivery.md:240-242:** the pointer is still an enumeration, and it omits a
  rule: the parenthesis lists four symbols plus two rules and says "this list is not repeated", but it leaves out
  `_DECISION_REFUSE_FOREIGN` (`svg`, `math`; brief-compose.py:1135, applied at 1269-1270 and 1274-1275). Input b,
  `<svg><text data-decision>Q?</text></svg>` → `CANNOT RUN — … it is on or inside a <svg>, foreign content whose
  visibility this check does not model`. The r1 text named `<svg>`; the r2 rewrite dropped it, so a reader who
  "reads them there" from the listed symbols misses one. Loud, so nothing ships wrong. It is the same drift class r2
  diagnosed (a prose copy of a code list), carried into the list of symbols. Fix: point at ONE thing that cannot go
  stale, for example "the refusals in `_DecisionScan.handle_starttag` and `render_decisions`", not a list of its
  constants; or at minimum add `_DECISION_REFUSE_FOREIGN`. Fix-induced: yes (r2 fold).

VERDICT: NOT CONVERGED
