# Architecture review — the diagnostic-report component of `check-plan-code.py`

**Armed by THRASHING, not by a round count.** `docs/dev-process.md` arms a Phase 6 review when two
consecutive rounds carry findings caused by the previous round's own fix, in one component. Round 18
of PR #371 produced that, independently from both halves, with the mechanism test applied per
finding rather than a tally.

**Subject:** `scripts/check-plan-code.py`, the report built when a mutated suite goes RED but prints
no parseable `[FAIL] <case>` line. **Branch:** `backlog-249-260-fixes` at `5c42bf55` (PR #371).
**Base:** `master`. **Prior rounds:** 18, both halves each.

⛔ **ADRs are not re-litigated here.** ADR-0014's rule — a case must drive `main()` over a world the
case built — is assumed, and the redesign below must keep satisfying it.

---

## What the two halves agreed, and what I verified by hand

`dev-process.md` says agent output is a lead, not a finding. Both halves returned THRASHING on the
same component. Below, every load-bearing claim is marked with who established it and how.

### F1 · The root cause is ONE FLAT STRING, and it is structural — VERIFIED BY READING

`scripts/check-plan-code.py:3167-3180` is a single `report.append(...)` whose f-string concatenates
three things of different provenance:

1. harness-owned prose (the long "nothing could see the kill" warning),
2. `said` — the harness's own arm-selected sentence, and
3. `diagnostic_tail(so, se)` — **the child's stdout and stderr**.

⭐ Every defect in the sequence follows from that one line. A case written against this report
**cannot distinguish "the harness said it" from "the child said it"**, so every assertion over it
degrades into a substring test that the child can satisfy, and the repair for each one creates the
next. That is not a description of past mistakes; it is a property of the datatype.

### F2 · The class is LOCAL — and my own derivation is STRONGER evidence than the count it replaces

The Claude half reported *"195 substring-tests across twelve guards, 14 ambient candidates, 12 of the
14 in this one component."* ⚠ **I did not reproduce that and do not claim to.** My independent sweep
used a wider definition — any `<str literal> in <rendered-looking value>` test — and found **216
across 24 guard files**, with `check-plan-code.py` holding **75, or 35%**, 3.75× the next file. That
is a superset measure: it neither confirms nor refutes the 14/12 split, because deciding which tests
are *ambient* requires judging each one.

⭐ **So I measured the MECHANISM instead, which is cheaper and decides the question outright.**
Ambient satisfaction is possible exactly when the asserted report contains text the harness does not
own. Derived with `ast` over every `scripts/check-*.py`, matching report-appends whose source segment
embeds `stdout`/`stderr`/`subprocess`/`diagnostic_tail`/`read_text()`:

| guards that splice externally-sourced text into a report their own cases substring-test | sites |
|---|---|
| `check-plan-code.py` | **3** |
| *every other guard in the repository* | **0** |

**One file, three sites, and nothing else in the repository does it at all.** That is what makes this
a redesignable component rather than a methodology problem — and it is the evidence the verdict
should rest on, because it names the channel instead of counting its consequences.

### F3 · The four THRASHING findings, each caused by the previous round's own fix

Established by the two halves; H1 and M1 reproduced independently by me before this record.

| finding | the fix that caused it | how it passes today |
|---|---|---|
| Codex **H1** — `_QUOTED_PREFIX` pin guards the CONSTANT, not the renderer | r17 added the pin | replacing the production use leaves 300/300; after the sever the constant appears **twice** in the file, its definition and its oracle, so nothing reads the rendered prefix |
| Codex **M1** — the one-head case accepts ZERO heads | r17 added the case | `ONLY_KILLER` arrives via the child's traceback, not via the quoting |
| Claude **M-A** — the character count is unasserted | r12 L1 changed the WORD and the case pinned the word | `len(se)` → `len(se.encode())` survives at 300/300; the fixture is ASCII-only |
| Claude **M-B** — the else-arm bound is read by one fixture that reaches it via prose | r17 recorded it as a known gap and declined it on a cost premise | the sever stays 300/300; the real `sys.tracebacklimit = 0` child has no fixture |

Codex L1 (an arithmetic slip, 298→300 vs 297→300) and Claude L-A are **PROSE FLOOR** and are
excluded from the arming, correctly.

### F4 · THE SCOPE FINDING, and it is the one a renderer-only review would miss

⭐ Round 18's largest findings were **not in the thrashing component at all.** `find-claim.py` —
added by this same branch, with its own 86-case suite and its own 25-entry manifest — carried a
**red self-test on 3.13+** and a **lenient false clean**, and no round in eighteen had looked at it.
Verified by me on three interpreters in the pristine tree: 3.10 → 86/86, 3.12 (the CI pin) → 86/86,
3.14 → **84/86**, with the ratchet reporting `NOT MEASURED` on 3.14 against 25/25 on 3.12.

⛔ **So the composition defect is in WHERE REVIEW ATTENTION WENT**, which is precisely the class
`dev-process.md` says per-task review is structurally blind to. Eighteen rounds of a branch that adds
`check-main-drivable.py` (+5,130), `check-withdrawal.py` (+2,120), `find-claim.py` (+1,132) and
`check-provenance.py` (+984) spent themselves on one file. ⚠ Their suites are green and I swept them
for this round's two classes — but "green and clean on two classes" is not a review, and this record
will not imply otherwise.

### F5 · What we decided this milestone that is not written down

The question `dev-process.md` requires, answered:

* **That a guard's local red is acceptable when CI pins a different interpreter.** It is written in
  `check-python-pin.py` as advisory-locally / failing-in-CI, and `scripts/check-python-pin.py:17-18`
  even names this exact `Path.is_file()` divergence — but *nothing measures a guard at more than one
  interpreter*, so the policy is a belief rather than a gate. The 54 × 2 matrix that found the one
  divergence took the reviewer four minutes.
* **That `markdown-it-py` became a HARD dependency** (#267) and therefore that every local guard run
  without a venv is a CANNOT RUN wearing a red. `requirements.txt` says so; nothing surfaces it at
  the moment a developer reads a failure. I misread it myself in this session and nearly filed it as
  a branch defect.

---

## The redesign — Codex's direction, amended on two measured points

Codex proposed: *represent quoted lines and raw diagnostic output separately, render through ONE
narrow formatter, and assert that formatter's complete output at explicit zero-, one- and
multiple-line inputs.* **Approved in direction, amended in two ways, both of which the Claude half
established with measurements and I accept:**

**A1 — "one narrow formatter" is insufficient unless its output is OBSERVABLE WITHOUT the child
tail.** If the formatter still returns one joined string, every future case is again a substring test
over a string the child contributes to: the defect rebuilt somewhere prettier. The load-bearing
change is that the harness-owned sentence and the raw tail become **two separately addressable
values** — two fields, or two return values the report joins at the last moment — so a case can
assert over `harness_said` alone and the child can write anything it likes without reaching the
oracle. Separateness of the **observable**, not of the representation.

**A2 — the input axis is not 0/1/many LINES. It is the SIX WORLDS the arms select on**
(`:3117` `not se.strip()` with a two-arm ternary inside at `:3132`, `:3137` `elif heads:`, `:3154`
`else:`):

| world | selected by | fixture today |
|---|---|---|
| empty stderr | `not se.strip()`, `not se` | `_repfmt` |
| whitespace-only stderr | `not se.strip()`, `se` truthy | `_repws` — ASCII only, which is **M-A** |
| one quoted head | `len(heads) == 1` | `_rep1` — zero-head hole is **Codex M1** |
| two or more quoted heads | `len(heads) >= 2` | `_repq` |
| prose, no exception line | `else`, no colon | `_w3` |
| **real no-frame traceback** | `else`, with a colon | **NONE — this is M-B** |

⭐ Three of the four THRASHING findings are missing **input kinds**, not missing line counts. A
0/1/many-line oracle fixes exactly one of the three. Enumerate the six worlds, assert the formatter's
complete harness-owned output in each, and the class is closed.

**A3 — ADR-0014 still binds.** Each of the six must drive production code over a world the case built.

---

## Verdict

**THRASHING on the diagnostic-report component. The redesign above is APPROVED as the direction, with
amendments A1–A3.** The mechanism test is met per finding, and F2 establishes by mechanism — not by
count — that the class is local and therefore removable.

⛔ **NOT CONVERGED on the branch**, and not because of the renderer: on the strength of H-A and H-B,
which are new subjects rather than another turn of the same screw.

⛔ **This review is NOT scoped to the renderer alone.** F4 and F5 are findings of equal weight, and a
Phase 6 that produced only the renderer verdict would have done per-task review at milestone scale —
the charge round 6 of the sibling branch levelled at its own architecture review, and it was right.

**Findings that become work** — filed in `docs/backlog.md` and the roadmap in this same turn, as
`dev-process.md` requires: **#291** (the renderer redesign, A1–A3), **#292** (a gate that measures
guards at more than one interpreter), **#293** (the unreviewed new guards of this branch).
Already filed earlier today: **#290** (two `find-claim.py` files, add/add conflict).
