# PR #364 round 4 — coordinator: THRASHING, and the evidence per finding

**Verdict: THRASHING. Folding stops here; a scoped Phase 6 architecture review is armed instead.**
Decided 2026-10-06 by the repository owner from a selection card, which is what
`docs/dev-process.md` requires — *"Reaching four rounds OBLIGES ASKING, and does not fire. Answer
thrashing or prose floor? in the round document, with per-finding evidence."* This is that answer.

## The arming condition, against this branch

> It fires when **two consecutive rounds carry findings caused by the previous round's own fix, in
> one component**.

Both halves of round 4 ran. Codex: no deliverable findings, one Low. Claude: 2 High (both
deliverable), 4 Medium, 2 Low. The question is not the count — it is where the findings came from.

| round | finding | caused by | component |
|---|---|---|---|
| 3 | MEDIUM 2 — the `MAIN_DEBT` pin is refuted | **the coordinator's merge fold**, ~1h earlier | contrast guard wiring |
| 4 | HIGH 1 — the coverage fold has no falsifier | **round 3's fold** | contrast guard |
| 4 | HIGH 2 — the un-pin case cannot fail in CI | **round 3's fold** (the un-pin) | contrast guard wiring |
| 4 | MEDIUM 2 — a wrong number labelled MEASURED | **round 3's fold comment** | contrast guard |
| 4 | MEDIUM 3 — the #238 amendment is false | **round 3's filing** | contrast measurement |
| 4 | MEDIUM 4 — "FILED, NOT FOLDED" was false | **round 3's fold commit** | process record |

**Five of round 4's six Medium-or-above findings are defects in round 3's fixes, and round 3's own
Medium 2 was a defect in the merge fold before it. One component throughout.** That is the shape,
not a count of rounds.

## Why "prose floor" is REFUSED as the answer

A prose floor would mean the findings are converging on documentation quality while the code is
settled. Two facts refuse it:

1. **HIGH 2 is not prose.** Severing `root → ROOT` and running the suite in four worlds gives
   control+browser 94/94 rc=0, severed+browser 92/94 rc=1, control+no-node 94/94 rc=0, and
   **severed+no-node 94/94 rc=0 — survived.** A guard was un-pinned from `MAIN_DEBT` on a case that
   cannot fail in the only environment where the suite runs as a gate. That is a live false green.
2. **HIGH 1 is not prose either.** The fix for a silent verdict is itself untested: reverting the
   sentence leaves 94/94 rc=0, emptying the warning leaves 94/94 rc=0, and no mutation entry names
   either line.

## What the repairs would have cost, which is the other half of the decision

Round 4 **refuted the obvious repair for HIGH 2 before it was attempted**: threading `root` into
`measure()` — round 3's still-open Medium 1 — makes the case bind *less*, because the probe refusal
then fires before the corpus path. So the fifth fold would have started from a repair that round 4
had already shown to be wrong, which is the definition of the loop reviewing its own repairs.

## What Phase 6 is asked to answer

Scoped to `scripts/check-page-contrast.py`, its probe, and its wiring into `page_chrome.py`:

1. Can this guard's `main()` be driven over a constructed world by a case that **binds without a
   browser**? If not, is `MAIN_DEBT` the honest state and the un-pin simply wrong?
2. Is a verdict line a testable surface here at all, or does the design need the verdict to be a
   value a case can read rather than a string a human reads?
3. "One layer decides the common look and feel" is this PR's thesis, and a served page bypassed it
   with a private `--st-*` vocabulary. Measured: **58 served pages declare 91 token names outside
   the standard 40, and every page declares at least one.** Is the standard-palette-injection design
   right, or does unification need a different mechanism?

⛔ ADRs must not be re-litigated. Agent output is a LEAD; every load-bearing claim is verified by
hand. Findings that become work go to `docs/backlog.md` and the roadmap in the same turn.

## Filed from rounds 3 and 4 — and filed LATE, which is itself a finding

`#239` root half-threaded · `#240` the un-pin case cannot fail in CI · `#241` the coverage fold has
no falsifier · `#242` an unusable baseline passes at 0% coverage · `#243` four prose claims the code
does not satisfy. ⚠ Round 3's fold commit claimed *"FILED, NOT FOLDED"* for seven deferrals and
filed **none** of them; round 4's Medium 4 caught it. The rows above are that claim being made true
after the fact.

## Corrected in place rather than filed, because they are factual errors in this session's own work

- the fold comment stated **66,732 / 55.1%** as MEASURED; the baseline holds **65,370** keys and the
  code computes **54.2%**. Corrected, with the cause recorded at the site.
- `#238` claimed the 58/91-vs-59/95 gap was unreproducible. It is deterministic: 58/91 is the
  guard's own `corpus()`, 59/95 is a filename rule the coordinator hand-rolled, and the delta is
  exactly `frag-plan-mode-question.html`. The row now carries the guard's figures.
- a `check-main-drivable.py` docstring still said "27 of the 37" / "one of the 10"; the guard prints
  38 and 11. Corrected, and the class searched for other sites (none).
