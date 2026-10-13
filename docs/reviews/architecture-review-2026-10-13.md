# Architecture review — 2026-10-13 · the mutation harness's child-verdict path

> **Anchor:** `review-decides-itself` — the goal ADR-0014 belongs to.
> **Armed by:** THRASHING on `scripts/check-plan-code.py`, answered by the documented test in
> `docs/reviews/coordinator/backlog-249-260-r11-thrashing.md`.
> **Sequenced by:** the owner, 2026-10-13, choosing the review over a twelfth fold.
> **Tree:** `7b88ced8` on `backlog-249-260-fixes` (PR #371). All 8 `mutation-sweep` shards green;
> `verify` red only on the final-tree gate, which only convergence clears.

## The thesis

Eleven review rounds hit one component. Every round's fix was correct and every fix produced the
next finding. This review asked the question a per-task round structurally cannot: **not "is this
correct?" but "is the shape right?"** — and the answer is that one concept has two mechanisms,
**mandatory on one side of zero and optional on the other**, and the optional one admits a FALSE
GREEN.

⚠ **Method, stated because it is what makes the findings usable.** Three read-only `Explore` agents
produced leads; `dev-process.md` requires that agent output be treated as a lead and every
load-bearing claim re-measured by hand. Every finding below carries its verification status, and
**two agent gradings were corrected downward by that re-measurement** (F6, and L2 in the governance
section). That is recorded rather than smoothed over: a review whose leads are published unverified
is the defect it is looking for.

---

## F1 ⭐⭐⭐ — A FALSE GREEN: `attributed: True` recorded over `fails: []`

**Files:** `scripts/check-plan-code.py:2786`, `:2817-2830`, `:2849`
**Verified:** coordinator-reproduced as a 2×2 over the real `run_mutations`.

    A crash, expect NAMED        ok=False caught=True  fails=[]   attributed=False reports=1
    B crash, expect OMITTED      ok=True  caught=True  fails=[]   attributed=True  reports=0  <-- FALSE GREEN
    C real kill, expect OMITTED  ok=True  caught=True  fails=[..] attributed=True  reports=0
    D real kill, expect NAMED    ok=True  caught=True  fails=[..] attributed=True  reports=0

B is byte-identical to D on the verdict fields. A mutation whose suite died before any case ran is
certified as killed. `attributed` is DEFINED at `:2817-2821` as *"red via the case this entry
names"* and the entry names nothing, so the field contradicts its own definition. Flow:
`wants == []` → `unnamed == []` → `attributed = caught and not unnamed` → True; the `if not fails`
branch is unreachable because it sits inside `elif unnamed:`.

**Liveness:** latent — 0 of 1539 live entries omit `expect` (coordinator-measured, all 62
manifests). ⛔ But the route in is BLESSED BY THE TOOL: the empty-list refusal at `:2799-2800` tells
authors *"Name the case(s) that must go red, or omit `expect` entirely"*, and a case asserts *"a
missing expect is no expects, not a crash"*. A guard whose own message invites the hole will meet it.

**Why eleven rounds missed it:** every round examined the `if not fails` branch. In cell B that
branch is never entered.

## F2 ⭐⭐ — one concern, two mechanisms: MANDATORY for `rc == 0`, OPT-IN for `rc == 1`

**Files:** `:376` (`control_is_green`), `:2786` (`caught`), `:2824-2830` (the `expect` clause)
**Verified:** coordinator, by reading both predicates and their docstrings.

`control_is_green(rc, out)` is `rc == 0 and "passed" in out` — two clauses, no opt-out — and its
docstring records the reasoning on **2026-09-03**: *"A script with no `__main__` entrypoint exits 0
and prints nothing, so the exit code alone cannot tell "green" from "never ran""*.

Change one word and that is the red side: `rc == 1` cannot tell *"a case failed"* from *"the
interpreter died"*. The second clause DOES exist there — the `expect` attribution check — but it is
**optional**, and F1 is what the optionality costs.

⚠ My first framing was *"the repair never propagated"*. An agent refuted it and the refutation is
better: it propagated as an **opt-in** clause. "Optional mechanism", not "missing mechanism" — and
that distinction is what makes the remedy one line instead of a redesign.

## F3 ⭐⭐ — `merged_output` fuses the two streams with NO separator, on the ATTRIBUTION path

**Files:** `:603`, `:2758`, `:3047-3070`; `scripts/mutations/check-plan-code.json:772`
**Verified:** coordinator-reproduced with a control.

`:603` is `return (stderr + stdout).strip()`. A child whose stderr lacks a trailing newline fuses its
last stderr line with the first stdout line; if that is the `[FAIL]` line, attribution is lost for a
suite whose printer is correct.

    stderr WITHOUT a trailing newline -> parse_fail_names(merged) == []
    stderr WITH    a trailing newline -> ['the value is one']

⛔ **THE ASYMMETRY IS THE FINDING.** The hazard is named and guarded in the SIBLING combiner:
manifest entry `:772` is literally *"the two kept halves are joined with no separator, fusing the
last stderr line and the first stdout line into one sentence"*, and its edit targets
`diagnostic_tail`'s `"\n".join(...)`. `merged_output`'s two entries are both about ORDER. **So the
separator is guarded on the path a HUMAN reads and unguarded on the path a MACHINE parses.**

**Liveness:** latent — 0 newline-less `stderr.write` calls under `scripts/` (control: 6 that do end
in `\n`), 0 `print(..., file=sys.stderr, end=...)`. ⭐ But the one producer of a newline-less stderr
in the system is **the harness itself** — `run_suite_parts`'s `TimeoutExpired` message — safe only
by two accidents: its stdout is `""` by construction and `rc == 2` `continue`s before attribution.
`subprocess.TimeoutExpired` carries partial output in `.stdout`, so *"show what it printed before it
hung"* would arm this immediately.

## F6 ⭐ — the heading rule reads RAW STDERR ONLY

**Files:** `:2853`
**Verified:** coordinator — **and the agent's grading was corrected downward.**

A child whose exception text reaches stdout lands in world one and is told *"stderr is EMPTY, so the
suite RAN and its PRINTER is the subject"*. The agent graded this LIVE with no trigger needed.
Measured: **latent.** `print_exc`/`format_exc`/`format_exception` sites under `scripts/`: **0**
(control: 969 `print(` calls, 22 files referencing `traceback`), so no traceback text is produced
anywhere. 33 `print()` calls inside `except` handlers do reach stdout (AST-measured); two sampled —
one exits 2 (the harness's correct CANNOT-RUN path), one prints a well-formed `[FAIL]` line.
⚠ BOUND: the traceback-on-stdout shape is airtight-absent; the handled-message shape was checked on
2 of 33 sites.

## F7 ⭐⭐ — the branch has ONE BIT of rule-level coverage, repeated three times

**Verified:** agent-enumerated by AST over `_self_test` (`:3072`–`:6329`), coordinator-reviewed.

Of the cases reaching the `if not fails` branch: **3 assert a PROPERTY, 9 assert a SUBSTRING** of the
report (6 positive, 3 negative) — and all three property assertions are the SAME assertion,
`ok is False`. Counting a fourth that asserts the per-mutation record gives 4/9.

⛔ This is the DENOMINATOR for a claim already written to memory as
`printing-more-evidence-weakens-substring-cases`: three-quarters of this branch's test surface is
substring-based, so every addition of evidence to the report weakens it. That claim was published on
four witnesses; the population is measured now.

## F8 ⭐⭐ — `run_suite` is DEAD IN PRODUCTION, and this session killed it

**Files:** `:609`, `:623-625`; callers at `:3130`, `:3149`, `:3183`
**Verified:** coordinator, AST-measured with `_self_test`'s span separating production from cases.

All four production call sites use `run_suite_parts`. `run_suite`'s only callers are three
self-test cases, so it exists solely to be tested. ⛔ Its docstring at `:609` still says *"the merged
view every other consumer wants"* — **`6b217be9` (this session) made that false and nobody
noticed**, the same shape as the figures withdrawn in r11 Codex L2.

The **deletion test** says delete it: three cases are its only consumers, so removing it removes
complexity rather than concentrating it. ⚠ But `merged_output` is NOT dead (`:2758`), and those
cases are its only coverage — a deletion must not take that with it.

**F8b** — manifest entry `"run_suite drops stderr, so a control's traceback is lost (r1 F7)"`
mutates `merged_output`'s body, and its `expect` also says `run_suite`. A reader chasing
`run_suite`'s coverage finds an entry that never touches it — and that entry mutates the exact line
whose missing separator is **F3**, for ORDER, which is how the separator went unexamined.

---

## The one root cause

**The harness asserts a cause it cannot read from a child's text, and each fix moved the claim
rather than removing it.**

| the claim | made from |
|---|---|
| "a case failed" | `rc == 1` alone |
| "a report-format defect in `<file>`" | `fails == []` alone |
| "the child DIED with `<heading>`" | the last traceback block |

F1 and the r11 Claude H1 premise are **mechanism** defects by `review-method.md:195`'s
discriminator; a redesign dissolves both. The rest are branch-coverage and were fixed as such.

⭐ **And the redesign is not an invention.** `control_is_green` is already the mandatory two-clause
form, with its rationale recorded. The `rc == 1` side needs the same shape.

## Deepening candidates — NOT designed here, per the skill; the owner picks

1. **Make the attribution clause MANDATORY** — `scripts/check-plan-code.py`. *Problem:* F1/F2; the
   second clause is opt-in. *Solution:* `attributed` false whenever `fails` is empty, and/or
   `expect` required. *Leverage:* one invariant removes a state the interface cannot describe;
   *locality:* the contradiction stops being expressible. Tests: the 2×2 becomes four cases.
2. **A deep module over "the child's verdict"** — `run_suite_parts` + `control_is_green` + `caught`.
   *Problem:* `(rc, stdout, stderr)` is a primitive-obsession seam; four sites each reconstruct what
   a child reported. *Solution:* one module with named states. *Trade-off:* it may not be earned if
   candidate 1 suffices — an agent was asked to argue against it and that answer is pending.
3. **One combiner, one separator rule** — `merged_output` / `diagnostic_tail`. *Problem:* F3/F8b.
   *Solution:* the attribution path stops consuming a fused string. *Leverage:* `parse_fail_names`
   gains a stated input contract.
4. **Retire `run_suite`** — F8, with the coverage caveat.

## Decided this milestone and NOT written down

See the governance section of `docs/backlog.md` rows filed with this review. The headline: the venv
requirement and the unignored `.venv` (F4), and the sequencing rule that `review-method.md`
§Iterative Re-Review already owns while four separate places argued it from first principles.

## Corrected BY this review

* `docs/reviews/coordinator/backlog-249-260-r11-thrashing.md` — rewritten: it led with the symptom
  list that `review-method.md:137` says never to lead with, and the symptom cannot discriminate
  because `:495` makes fix-caused findings the expected shape of re-review.
* Two agent gradings (F6 LIVE→latent; the governance contradiction → an unread rule).
* My own framing of F2 ("never propagated" → "propagated as opt-in").

## CANNOT RUN — failures, not passes

* The intermittent shard failure's root cause remains unidentified; it did not recur at `ff5b10f7`
  or `7b88ced8`. **Treat as NOT DIAGNOSED.**
* F6's handled-message shape: 2 of 33 sites inspected. **Not a corpus measurement.**
* The width of F1/F2's class across the other guards was asked of an agent and had not returned
  when this was written. **Treat the class as UNBOUNDED until measured.**

---

## ⟳ Added after the first draft — two answers that arrived late, and one changes the taxonomy

### A THIRD defect category exists and I had been sorting into a two-way split

`review-method.md:217-222` — *"A third outcome the two-way split does not cover: **STALE CROSS-REFERENCE**. A decision changed and some sentences still state the old one."* Its remedy is neither a
redesign nor an exhaustiveness pass:

> **"When a decision is reversed, grep for every place that stated the old one. A rewritten section
> does not rewrite its own cross-references."**

**Applied to this session's own reversals, it found three immediately**, none of them in a review
document (where the old wording is legitimate testimony):

| site | stated the superseded decision |
|---|---|
| `check-plan-code.py:2871` | `exception_heading` — the singular name, renamed hours earlier |
| `check-plan-code.py:609` | *"`run_suite` is the merged view every other consumer wants"* — false since `6b217be9` |
| `docs/adr/0014…:8` | *"The remaining 29 are pinned debt"* — the tool reports 27 |

All three corrected. ⚠ The ADR correction is dated and explicitly **not** a re-litigation: the rule
stands exactly as accepted, and only its population figures moved. ⭐ And the ADR carries a THIRD
disagreeing statement of one fact — its frontmatter says 36/29, the guard's own docstring says
37/10, the tool says 39/12/27. Three statements, all different, which is this category's own shape
applied to the document that defines the rule.

⚠ **So the per-finding table above is a two-way sort where the method has three categories.** Its
MECHANISM and BRANCH-COVERAGE rows were re-checked against `:195`/`:196`/`:217` and stand; what
belongs in the third category are the figure and prose rows (r11 Codex L2, Claude M1, L1–L3), which
the table lumped as "FIX". They are stale cross-references, and their remedy is the grep above —
not a fix at the one site someone noticed.

⚠ **One correction to a datum I nearly used to demote a finding.** I observed that `ok = False` is
set before the `if not fails` branch, so the message's world-selection can never flip a verdict, and
I took that as evidence H1 might be branch-coverage. It is not: `:202-205` asks only whether a
reshaping dissolves the finding and says nothing about harm magnitude, and backlog #136 holds that
*"any stopping rule reading counts or severities is reading noise"*. Harm is severity; severity is
not taxonomy. H1 stays MECHANISM.

### The width question: the class is REPO-WIDE — nine sites, eight guards (backlog #276)

Asked because it gated the owner's A-versus-B choice. ⚠ **It answers H2's class, not F1's** — a
distinction worth keeping, because conflating them would have flipped a decision on the wrong
evidence. H2's class (a world-selection no case asserts) is repo-wide.

⟳ **CORRECTED 2026-10-13 (round 12, Codex M1).** This paragraph said F1's class *"remains UNMEASURED across the other guards"* while the section below reports sweeping **every** `obj.get("literal")` under `scripts/` — 358 sites in 33 files. A repo-wide sweep IS that measurement, so the two statements could not both stand. What was true when this sentence was written is that F1's class was unmeasured *at the time the A-versus-B choice was put*; it was measured later the same day, and the sentence was not revisited. The width section below is the measurement.

Measured by severing each arm against the guard's own `--self-test`, control green either side. The
three with non-cosmetic harm: `check-live-schema.py:891` relabels a LOCAL container read as `--prod`
at 119/119; `check-anon-exposure.py:631` swaps `LOCAL container` for `PRODUCTION (read-only
claude_ro)`; `check-ratchet-contract.py:1152` has `GREW`/`SHRANK` collapsed **and inverted** at
56/56 — and that guard is ADR-0014 COMPLIANT, so compliance with the drivable-main rule does not
reach this class.

⭐ **Coordinator-verified on TWO instances; the other seven are LEADS.**

1. `check-test-counts.py:132` — control 27/27, the two direction literals INVERTED 27/27 **still
   green**, control restored 27/27.
2. `check-live-schema.py:891` — control 119/119, both arms collapsed so a LOCAL CONTAINER READ
   LABELS ITSELF `--prod`, 119/119 **still green**, control restored 119/119.

⚠ The first attempt at (2) returned **CANNOT RUN** (`ModuleNotFoundError: m4_catalog`) because the
guard had been copied out of `scripts/` away from a sibling it imports. Recorded, because a
cannot-run is a failure and not a pass, and because it is the method error this review exists to
catch in others: the re-measurement above staged the whole directory.

**Treat the remaining seven as not independently verified.**

### What the owner chose, and what it did NOT include

Option **A** — make the attribution clause mandatory (#271) — chosen 2026-10-13 after asking why A
over B. ⚠ **A was offered as "~one line" and is four**: fixing `attributed` alone corrects the
recorded field and leaves `ok` wrong, because the `if not fails` block sat INSIDE `elif unnamed:`.
The arm had to be lifted so `expect` cannot disable the refusal. Behaviour is unchanged for all
1,539 live entries, measured rather than argued.

### F1's width — the number that settled A versus B: **2 sites, 2 files**

⟳ **CORRECTED 2026-10-13 by round 12 (Codex M1), and the correction came from THIS DOCUMENT'S OWN NEXT PARAGRAPH.** The figure read **3 sites**. The filter is *does absence answer in the PERMISSIVE direction?* — and six lines below, this document establishes that `gate_ran` answers **conservatively**. A site cannot both fail that filter and be counted among those that survive it. Two survive, not three. ⚠ Nothing about the A-versus-B verdict turns on it: 2 callers is still not a real seam. What is wrong is the arithmetic published to support it, and a figure in a review document is a claim like any other.

Asked after A was chosen, because I had said B was gated on it and would reopen the choice if it
came back large. Method: every `obj.get("literal")` under `scripts/` — 358 sites in 33 files, 21 of
them guard-shaped — swept by severing each to `obj["literal"]` with a control green either side,
then filtered by the condition that matters: **does absence answer in the PERMISSIVE direction?**

**Two** survive that filter, in two files (⟳ *read three until round 12*): `check-plan-code.py:2804` `mut.get("expect")` (fixed by
#271 in this session) and two in `check-review-recorded.py`.

⚠ **AND ONE OF THE TWO IS MIS-GRADED BY THE AGENT THAT FOUND IT — coordinator-measured.**
`rec.get("gate_ran")` was reported as failing OPEN. Through `classify_verdict`: `True` →
`(head, 'usable')`, `False` → `(None, 'skip')`, **ABSENT → `(None, 'skip')`, byte-identical to
False** — i.e. *the gate did not run*, which makes the final-tree gate MORE demanding. That is the
conservative direction, so it is a validation gap, not a false green. The third agent grading
corrected by measurement in this review.

⛔ **So B is not merely unmeasured — it is NOT EARNED.** A shared "child verdict" module over this
class would have **2 callers**, and the remaining two sites are already owned by backlog **#178**.
#178 is amended with today's measurement rather than duplicated.

⟳ **TWO CLAIMS IN THAT PARAGRAPH WERE WRONG, corrected 2026-10-13 by round 12 (Codex M1).**

1. **It read callers as adapters.** The skill's rule is *one ADAPTER = hypothetical seam, two =
   real*; an adapter is a concrete thing satisfying an interface, not a call site. Counting two
   callers and concluding "hypothetical depth by the skill's own rule" cites a rule it does not
   apply. ⚠ B is still not earned — a two-call-site module over a four-line clause carries no
   leverage — but that is an argument, not the skill's rule invoked as authority.
2. **#178's remedy cannot import that validator, because it validates a DIFFERENT RECORD.**
   `check-review-decision.py:265-283` holds `REQUIRED = {"severity", "aim", "fix_induced",
   "disposition"}` plus a `component` check — **finding** fields. A verdict record carries
   `gate_ran`, `dirty`, `schema`, `review`. Measured: calling `_validate` on a well-formed
   verdict raises `has no `severity``. So it is a SHAPE to follow (a required-field table and a
   reader that RAISES), never a function the verdict path can call — and the "2 callers" count,
   which assumed both sides consume one clause, had no basis. Backlog #178's own amendment
   carries the same error and is corrected with it.

⭐ And that validator has propagated to zero of the three — ADR-0014's recorded sentence, for the
third distinct class in one day.
