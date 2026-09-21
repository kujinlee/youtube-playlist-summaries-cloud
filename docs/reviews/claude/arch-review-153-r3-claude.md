# Claude adversarial review — round 3 — the workflow-readers architecture review

**REVIEW GAP:** codex — not invoked for this round, by design. Rounds 2+ alternate
(`docs/review-method.md`, Round topology), and Codex authored round 2 — the round whose repair this
reviews. A reviewer grading the fix for its own findings is the thing alternation exists to prevent.

**Subject:** the repair commit `b9782ddd` on branch `arch-review-153-workflow-readers` — §5 of
`docs/reviews/architecture-review-2026-09-21-workflow-readers.md` and rows **#155**/**#156** of
`docs/backlog.md`. I am reviewing a repair I did **not** author, of the two Highs Codex filed in
round 2. `git status` clean at `b9782ddd`.

**Reviewer:** Claude half, dual adversarial review, round 3.
**Method:** every load-bearing number re-derived by running the shipped code, from the repository
itself — not from r1's numbers and not from r2's. Transcripts pasted. Anything not run is labelled
UNVERIFIED. No repository file other than this one was modified.

---

## VERDICT: NOT CONVERGED — 0 Blocking, 5 High, 3 Medium, 2 Low

Both of Codex's round-2 Highs are **addressed but not closed**, and the repair introduces two new
defects of its own — including one that is the *same class* as the defect it was written to repair.

| Codex r2 finding | Status |
|---|---|
| **R2-1** — the "no conditional guard invocation" claim is false, #156 under-specified | ⚠ **PARTIAL.** The correction is right and I reproduced it. But the **new justifying sentence is itself false** (R3-2), the binary it mandates does not cover the space (R3-4), and the row's surviving "no job-level `if:`" claim is scoped to a corpus the same row proposes to leave |
| **R2-2** — #155 omits consumer coverage for `check-ratchet-contract.py` | ⚠ **PARTIAL.** Every factual claim in R2-2 checks out exactly. The requirement added, however, **has no seam that can satisfy it**, and the only suite-reachable layer is the implementation trap two rows above it in the same table (R3-1) |

| Severity | Count | Ids |
|---|---:|---|
| Blocking | 0 | — |
| High | 5 | R3-1 … R3-5 |
| Medium | 3 | R3-M1 … R3-M3 |
| Low | 2 | R3-L1, R3-L2 |
| Checked and SOUND | 11 | S1–S11 |

Nothing from r1 or r2 is left NOT FIXED in the sense of *reverted or ignored* — r2 confirmed all
nineteen r1 findings and I spot-checked the load-bearing ones (S1–S4). The five Highs below are
**new or newly-measured**, not re-filings.

---

# Findings

## R3-1 — High. #155's new consumer-coverage requirement has **no seam that can satisfy it**, and the only layer the suite can reach is the implementation trap two rows above it

This is the repair of R2-2. The new §5 row and the matching #155 text demand:

> `check-ratchet-contract.py` needs its **own** new self-test cases **and** mutation entries for the
> wiring — *"`ci.yml` prose no longer satisfies R3"* and the pre-join masking path

Both halves are unachievable as the consumer is shaped today.

**The mask must live in `main()`.** The blob is built at `scripts/check-ratchet-contract.py:868-885`:

```python
    caller_sources: list[Path] = [ci_path]
    caller_sources += sorted((ROOT / "scripts").glob("*.sh"))
    ...
        blob_for[rel] = "\n".join(
            p.read_text(errors="ignore") for p in caller_sources
            if p.is_file() and str(p.relative_to(ROOT)) != rel)
```

`evaluate()` receives `caller_blob_for` already built (`:190`), and `check_caller()` receives one
finished blob (`:167`). So "mask `ci_path.read_text()` before the join" — the trap row's own
instruction — can only be executed inside `main()`.

**(a) A self-test case cannot observe a mask placed there.** `CALLER_CASES` (`:534-551`, seven
cases) drives `check_caller(path, text, caller_blob)` with a *synthetic* blob. Measured, using the
case an implementer would naturally add:

```
A) the case an implementer would add to CALLER_CASES, TODAY (no mask anywhere):
   check_caller -> [] (NO violation — the comment SATISFIES R3)
B) same blob, pre-masked by _structural (what the mask would deliver):
   check_caller -> ['R3_no_caller']
```

The case is a genuine falsifier — **but only if the mask is applied at a layer `check_caller` sees.**
With the mask in `main()`, case A is what the suite gets forever: red, and unfixable except by
moving the mask to the wrong layer.

**(b) The demanded mutation entry cannot be killed.** `check-plan-code.py:498-500` runs only the
mutated file's own suite:

```python
        r = subprocess.run([sys.executable, name, "--self-test"], cwd=d,
                           capture_output=True, text=True, timeout=SUITE_TIMEOUT,
                           env=child_env(d))
```

and `check-ratchet-contract.py:832-833` is `if "--self-test" in argv: return self_test()` — every
line of `main()` after it is unreachable under `--self-test`. A mutation anchored on the mask line
therefore **survives**, which `--mutate .` reports as a failure. This is not speculative: the
existing manifest has **zero** entries anchored in this file's `main()`, and all ten bind to pure
functions or module constants (S5). Other guards do carry `main()`-anchored mutations — 37 across
the tree, e.g. `check-fixture-variation.py` — and every one of those files has a `main()` the suite
**calls in-process** (`check-fixture-variation.py:1249`, `main([])`). `check-ratchet-contract.py`'s
suite never calls `main()`, and `main()` hard-reads `ROOT` (`:40`, `:835`, `:851`), so it cannot.

**(c) The escape route is the documented trap.** The only way to make a `CALLER_CASES` case flip
red→green is to mask inside `check_caller`/`evaluate` — i.e. mask the **joined** blob. That is
exactly what the row two lines above forbids, and the cost is measurable:

```
scripts/check-schema-gates.sh: 264 lines -> 101 survive _structural (163 dropped)
```

163 lines stripped from **one** of the 81 non-workflow sources.

**What is missing from #155.** The consumer needs the same refactor its own `evaluate()` docstring
records making once already (`:190-200`): *"Extracting the function bought coverage of the function;
the wiring inherited the same blind spot."* The blob construction must become a **pure function the
suite can drive** — `caller_blobs(ratchets, sources, ci_text)` or equivalent — before either the
case or the mutation is writable. #155 names neither that refactor nor its cost, and it is not
small: it is the third structural change to a file #155 already changes.

**Requirement:** say in #155 that the blob construction is extracted to a pure, suite-driven
function, and that the case and the mutation bind **there**. Without it the row is satisfiable only
vacuously or wrongly.

---

## R3-2 — High. The sentence the repair uses to justify #156's new design is **false**, and it is false the same way the claim it replaced was

The new §5 text, and #156 verbatim:

> ⭐ **The refutation improves #156 rather than merely correcting it.** *"Reject an invocation inside
> a conditional step"* would **red-line two guards that genuinely run** — and both are PR-only
> gates, the kind whose absence is hardest to notice.

**It would red-line neither.** Both guards have a *second, unconditional* invocation in the same
file:

```
check-dashboard-entry.py: invocations in ci.yml ->
    (411, 'run: python3 scripts/check-dashboard-entry.py --self-test')
    (453, 'python3 scripts/check-dashboard-entry.py \')
  R3 with the two conditional steps DELETED: [] SATISFIED

check-review-recorded.py: invocations in ci.yml ->
    (162, 'run: python3 scripts/check-review-recorded.py --self-test')
    (478, 'python3 scripts/check-review-recorded.py \')
  R3 with the two conditional steps DELETED: [] SATISFIED
```

Method: excised both conditional steps from `ci.yml` by indentation span (447-454 and 472-479), then
ran the shipped `check_caller` against the remainder. Both return **no violation**. The
`--self-test` steps at `:162` and `:411` carry no `if:` and satisfy `invocation_re`
(`(?:python3?\s+|\./|\bbash\s+|\bsh\s+)(?:\S*/)?` + basename, `:142-151`).

**Why this is High and not a nit.** That sentence is the *entire* argument for the statically-false
vs event-scoped distinction #156 now mandates as its design. The stated cost of the simpler
alternative — reject conditional-step invocations — is **zero on today's corpus**, not two
red-lined gates. The distinction may still be the right design; the reason given for it is not a
reason. An implementer reading #156 is told a simpler rule is unsafe, on evidence that does not
support it.

**And note the shape.** R2-1's finding was *a plausible inference, stated as measured, propagated
without being re-run.* The repair for it contains a plausible inference, stated as measured, not
re-run — inside the paragraph whose subject is that failure. The commit message says *"agent output
is a lead, not a finding"*; this sentence is the coordinator's own lead, promoted the same way.

**Requirement:** either delete the "would red-line two guards" claim and argue the distinction on
its merits (a statically-false step genuinely never executes; an event-scoped one does — that
argument stands on its own and needs no cost figure), or replace it with a measured cost. If
measured honestly, the cost today is **0 guards**.

---

## R3-3 — High. `check-fixture-variation.py` is a **third** guard #155 changes, it goes red on day one, and no document in this review mentions it

The bookkeeping table enumerates `check-plan-code.EXPECTED_MUTATIONS`, `check-selftest-counts.POPULATION`,
`check-ratchet-contract` discovery, and now consumer coverage. It does not mention
`scripts/check-fixture-variation.py`, which runs **unconditionally in CI**:

```
.github/workflows/ci.yml:333:        run: python3 scripts/check-fixture-variation.py
```

Its population is derived from disk (`:127-139`): every `scripts/*.py` defining a function named in
`SUITE_NAMES = ('_self_test', 'self_test')`. `workflow_structure.py` **must** have a `--self-test`
(r1's H2, now §5's own requirement), so it joins automatically. `population_drift` (`:88-124`) then
fires:

> an ARRIVAL is a FINDING, exit 1, with the line to paste.

So the guard is red until `workflow_structure.py` is pinned in `EXAMINED_KEYS` — with a key set the
file's own comment insists must be **derived by running `analyse()`**, never transcribed, because
*"a written key set goes stale between measuring and pinning"* (`:300-303`).

**And the naming decision #155 never poses determines whether this is a red or a silent hole.**
Measured, by running `analyse()` on both spellings of the extracted library:

```
underscore names kept (_structural / _steps, as §5 names them):
   examined keys: []
   findings: []

renamed public (structural / steps):
   examined keys: ['steps.text', 'structural.lines']
   findings: ["...`steps(text=…)` is passed the SAME value at every call site in the suite...",
              "...`structural(lines=…)` is passed the SAME value at every call site in the suite..."]
```

`analyse()` excludes `_`-prefixed functions (`:736`, `not node.name.startswith("_")`, plus the
transitive `inner` exclusion documented at `:726-734`). So:

* **Keep the underscore names** → the library is pinned with an **empty key set** and
  `check-fixture-variation.py` examines *zero* parameters in the file that now owns this repo's
  most-defect-prone reader. A guard reporting OK over a subject it cannot see.
* **Rename them public** → real findings the library's suite must answer by varying the parameters
  or exempting them with a written reason. That is the correct outcome and it is unbudgeted work.

Corroboration that the underscore rule is live: `check-fixture-variation.py:340-343` pins
`check-python-pin.py`'s key set and it contains **no** underscore names — `_steps` and `_structural`
contribute nothing today, which is also why `check-python-pin.py`'s own pinned set survives the
extraction unchanged (a genuine non-problem, worth stating so the implementer does not hunt for it).

**Requirement:** add a bookkeeping row for `check-fixture-variation.py`, and make the public/private
naming of the extracted functions an explicit decision in #155 with this consequence attached.

---

## R3-4 — High. #156 asserts "there is no job-level `if:`" while its own second half proposes widening to a corpus that has **two**, and the mechanism it specifies is blind to job level

#156 carries both halves in one row, by design (*"same row because it is one mechanism"*):

* **half 1** — reject an invocation under a falsy condition; the stated mechanism is *"resolve the
  **step** owning the invocation, reject it if it carries a falsy `if:`"*;
* **half 2** — R3's corpus is `ci.yml` alone while both siblings read `*.yml` ∪ `*.yaml`.

And it states, as the repair's re-derived fact: *"There is no job-level `if:`."*

That is true of `ci.yml` and false of the corpus half 2 asks for. Measured:

```
=== ALL if: lines in ci.yml ===
448:        if: github.event_name == 'pull_request'
473:        if: github.event_name == 'pull_request'
=== ALL if: in schema-gates.yml ===
183:    if: github.event_name != 'schedule'        <- JOB level (jobs.schema-gates)
239:        if: always()
247:    if: github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'   <- JOB level (jobs.prod-drift)
306:        if: always()
```

And the guard at the centre of this entire review is invoked inside **both** conditional jobs:

```
.github/workflows/schema-gates.yml:211:        run: python3 scripts/check-python-pin.py
.github/workflows/schema-gates.yml:281:        run: python3 scripts/check-python-pin.py
```

So the moment half 2 lands, half 1's mechanism — *the **step** that owns the invocation* — is
structurally unable to see the condition that actually governs execution, and the row's own
justification for that blindness has expired. `if: always()` at `:239`/`:306` is a third spelling
the static/event-scoped binary has no rule for.

**The binary is also incomplete on its own terms.** Spellings it does not classify, with the two
that exist in-tree marked LIVE:

| Spelling | Statically false? | Event-scoped? | Present today |
|---|---|---|---|
| `if: false`, `if: ${{ false }}` | yes | — | no |
| `if: github.event_name == 'pull_request'` | no | yes | **LIVE** (ci.yml:448, :473) |
| **job-level** `if: github.event_name != 'schedule'` | no | yes, but at job level | **LIVE** (schema-gates.yml:183, :247) |
| `if: always()` / `failure()` / `cancelled()` | no | **no** — status-scoped, not event-scoped | **LIVE** (schema-gates.yml:239, :306) |
| `if: ${{ vars.X }}`, `secrets.…`, `inputs.…` | undecidable from the text | **no** | no |
| matrix-derived condition | no | no | no |
| `continue-on-error: true` | n/a — the step runs, its verdict is discarded | no | no (grep over both workflows: no match) |
| `if: 'false'` as a quoted string | GitHub expression truthiness makes a non-empty string truthy, so the step **runs** — UNVERIFIED, I cannot execute Actions here | no | no |

**Requirement:** #156 must say (a) job-level and step-level conditions are both in scope once the
corpus widens, (b) what the rule does with a condition that is neither statically false nor
event-scoped — `always()`, `vars.`/`secrets.` — and the safe default is *treat as a caller*, since
the failure direction is a violation rather than a false green, and (c) `continue-on-error` is out
of scope with that stated, not left unsaid.

---

## R3-5 — High. The twelve manifest entries are listed as **`#26–#37`**, which is off by one under the only natural reading — and r2's own evidence said so

#155 and §5 both say:

> transfer **12** anchors (**#26–#37** — ten in the functions, plus `_STEPS_KEY:295` and
> `_BLOCK_SCALAR:298`, whose only consumers they are)

r2's evidence line says the opposite and states its base explicitly: *"I re-bound the manifest and
got entries **27-38 in 1-based enumeration**, twelve total."* The repair kept r1's numbering and
added no base.

I re-derived from the shipped manifest, binding every `edits[*][0]` anchor to a line and resolving
its owning `ast` node:

```
 0based  1based  line  owners
     26      27   264  ['_steps']       the dash line is dropped from the step body...
     27      28   232  ['_steps']       the block-scalar mask is removed from the SPLITTER...
     28      29   298  ['_BLOCK_SCALAR']
     29      30   263  ['_steps']
     30      31   278  ['_steps']
     31      32   349  ['_structural']
     32      33   249  ['_steps']
     33      34   245  ['_steps']
     34      35   254  ['_steps']
     35      36   260  ['_steps']
     36      37   295  ['_STEPS_KEY']
     37      38   244  ['_steps']

count of moving entries: 12      manifest total: 39
any entry with a MIXED owner (partial move)? []
```

Twelve is right, the set is right, and there are no partial moves — the r1 conclusion r2 confirmed.
**The identifiers are 0-based.** A `#N` sigil in this repo means an ordinal (backlog ids, PR
numbers), so the natural reading of `#26–#37` is 1-based, and it picks the wrong twelve:

```
0based 25 / 1based 26  the step is identified by its OPENING LINE again, so a `- name:` step hides its pin (r2 H1…)
    line 384  owner=declared_pins       <-- STAYS in check-python-pin.py
0based 37 / 1based 38  job keys stop being excluded from the depth scan…
    line 244  owner=_steps              <-- MUST MOVE, and the 1-based reading drops it
```

An implementer who trusts the list moves a `declared_pins` anchor into a library that has no
`declared_pins` (unbindable anchor) and leaves a `_steps` anchor in a file that no longer has
`_steps` (unbindable anchor) — **two simultaneous `--mutate .` failures**, which is verbatim the
consequence r1 graded B1 Blocking. The list exists precisely so the implementer does not re-derive;
in its current form, re-deriving is the only safe action.

**Requirement:** write **1-based `#27–#38`**, or state the base. Cheapest correct form is to drop
the indices and list the twelve anchor lines (`:232`, `:244`, `:245`, `:249`, `:254`, `:260`,
`:263`, `:264`, `:278`, `:295`, `:298`, `:349`) — indices shift when anything is inserted, line
anchors do not.

---

## R3-M1 — Medium. #155 pins three numbers against today's tree while mandating a predecessor that moves them

#155 says *"OPEN — blocked behind #154"* and #154 says *"must land BEFORE #155"*. #155 then pins:
`EXPECTED_MUTATIONS` **39 → 27**, new key **= 12**, entry indices, and *"declared count falls from
**84**"*.

All four are measurements of the pre-#154 tree. Verified today:

```
scripts/check-plan-code.py:813:    "scripts/check-python-pin.py": 39,
check-python-pin.py docstring:  --self-test  # 84 cases
suite:                          84/84 passed
```

#154's fix is to `_BLOCK_SCALAR` (`:298`) — **one of the twelve moving anchors** — and #154 itself
records that the existing case at `:880-882` *"passes for an ambient reason… add the `uses:` line
and the case inverts*". So #154 necessarily adds at least one self-test case: **84 is wrong the
moment #154 merges.** If #154 also adds a mutation entry (this repo's invariable pattern — the
manifest names cite `r2 H1`, `r6 codex High`, and so on) anchored in `_BLOCK_SCALAR` or `_steps`,
then 39, 27, 12 and every index shift too.

Not graded High because the failure is loud and self-explaining (`check-plan-code.py:1212-1218`
prints the drift with both numbers). But the row's stated purpose is to spare the implementer the
derivation, and as written it spares them a derivation they must redo anyway.

**Requirement:** one clause — *"re-derive all four figures after #154 lands; the values below are
measured on `b9782ddd`, which #154 changes by construction."*

---

## R3-M2 — Medium. The new row demands self-test cases and mutation entries for `check-ratchet-contract.py` and omits the bookkeeping that both require

The table's own neighbouring rows insist on this for `check-python-pin.py` — declared count,
`POPULATION`, `EXPECTED_MUTATIONS`. The new consumer-coverage row demands the same two kinds of
artefact for a second file and names none of the bookkeeping:

```
scripts/check-plan-code.py:703:    "scripts/check-ratchet-contract.py": 10,
```

and `check-ratchet-contract.py` is pinned in `check-selftest-counts.POPULATION`
(`scripts/check-selftest-counts.py`, bare name, alongside `check-python-pin.py`), so its declared
count is externally verified. Adding cases without re-declaring, or mutations without raising `10`,
is a drift failure on each.

r1 graded the analogous omission (H2) **High** because it was most of what made #154 an M. This one
is two lines of bookkeeping on one file, so Medium — stated so the grading is not mistaken for
inconsistency.

---

## R3-M3 — Medium. `ci.yml:447` and `:472` are the step's opening dash lines — neither the `if:` nor the invocation

#156 reads *"`check-dashboard-entry.py` (`ci.yml:447`) and `check-review-recorded.py`
(`ci.yml:472`)"*, which parses as *the guard is invoked at line 447*. Measured:

```
447   - name: dashboard entry ratchet          <- cited
448     if: github.event_name == 'pull_request'
453       python3 scripts/check-dashboard-entry.py \    <- the invocation

472   - name: check-review-recorded (PR only)   <- cited
473     if: github.event_name == 'pull_request'
478       python3 scripts/check-review-recorded.py \    <- the invocation
```

The numbers came from r2's script, which printed the dash line as the *step's* identity — correct
in its own frame, ambiguous once lifted into prose next to a guard name. Given this round is about
a citation that was never re-run, the citations should point at what they name.

---

## R3-L1 — Low. The §5 transcript is a reformatting of r2's output, presented as a transcript

§5's new fenced block reads:

```
  steps with BOTH an if: and a guard invocation: 2
    line 447: if=[...]  guards=['check-dashboard-entry.py']
```

r2's actual output was `447 ["if: github.event_name == 'pull_request'"] ['python3 scripts/check-dashboard-entry.py \\']`
with the headers `job_level_if_lines []` / `step_level_if_with_guard:`. The conclusion is identical
and I reproduced it independently, so nothing is wrong — but a fence in a review document reads as
captured output. Either paste the real capture or label it a summary.

## R3-L2 — Low. §5 now makes five claims in one paragraph and the weakest is the one carrying the design

Noting the structural cause of R3-2: the new §5 text runs correction → transcript → design
recommendation → limit statement without separating *what was measured* from *what follows from
it*. The measured part (two conditional steps exist) is sound; the inferred part ("would red-line
two guards") is not; and they sit in one paragraph under one ⭐. Splitting measured from inferred
would have made R3-2 visible to its author.

---

# Checked and SOUND

**S1 — Every factual claim in Codex's R2-2 is exact.** `scripts/mutations/check-ratchet-contract.json`
holds **10** entries. Re-dumped all ten with their anchors: entries 1–5 concern the widened
population and debt drift, 6–7 the `NO-MUTATIONS`/`NO-CALLER` escape regexes, 8 the debt-PAID arm,
9–10 R4's docstring scoping and its could-not-parse path. **None reads `ci.yml`**; none touches R3's
caller blob. Confirmed.

**S2 — The suite genuinely lacks a comment/block-scalar case.** `CALLER_CASES` (`:534-551`) is seven
cases: a CI-step caller, a shell-gate caller, nothing-executes-it, the `NO-CALLER` escape, a bare
escape, a bare escape adopting the next line, and a docs-table mention. The nearest neighbour —
*"a guard mentioned ONLY in prose docs has no caller"* — is a markdown table row, not a YAML comment,
and it passes because `invocation_re` requires an invocation prefix, not because anything is masked.
Confirmed: no case exercises a `#`-prefixed line or a block scalar.

**S3 — The conditional-step population is exactly two, and there is no job-level `if:` in `ci.yml`.**
Re-derived independently of r2's script: `grep -nE '^\s*if:'` over `ci.yml` returns exactly two
lines, `448` and `473`, both at 8-space (step) indentation inside steps whose bodies invoke
`check-dashboard-entry.py` and `check-review-recorded.py`. No other `if` token in the file appears
outside a comment. The count **2** is right and the guards named are right. (What the repair infers
*from* it is R3-2; the scope of "no job-level `if:`" is R3-4.)

**S4 — The twelve-anchor transfer is right as a set.** See R3-5's table: exactly 12 entries bind
into `Step` (`:86-103`), `_steps` (`:106-282`), `_STEPS_KEY` (`:295`), `_BLOCK_SCALAR` (`:298`) and
`_structural` (`:301-357`), with no entry straddling the boundary. `39 → 27` plus a new key `= 12`
preserves the sum, so the *transfer, not a ratchet fall* framing holds. Only the identifiers (R3-5)
and their durability across #154 (R3-M1) are defective.

**S5 — The manifest's discipline corroborates R3-1's mechanism.** All ten `check-ratchet-contract.py`
entries anchor in pure functions or module constants — none in `main()`. Across the whole tree, 37
of 740 manifest entries anchor after their target's `def main(`, and every such file's suite drives
`main()` in-process. `check-ratchet-contract.py`'s does not. The absence is a design consequence,
not an oversight, and it is what makes the new requirement unwritable without a refactor.

**S6 — `check-docs.py` is green and no table was broken.** `rc=0`; *"backlog items (unique): 158 /
backlog rows, shape OK: 158 / Documentation integrity OK"*. Independently re-counted cells honouring
`\|` escapes: rows 153–158 all have **6**; §5's table rows 244–253 all have **3**, including the new
consumer-coverage row at `:252`. (The run also WARNs that `docs/plugins.md` is at 260/260 and
`docs/dev-process.md` at 212/220 — both pre-existing, neither caused by this branch, which touches
neither.)

**S7 — The branch changes no scripts.** `git diff --stat master...HEAD`: `CONTEXT.md`,
`docs/backlog.md`, `docs/dashboard-entries.md`, the review document, four review/verdict files, and
`docs/roadmap-to-launch.md`. No file under `scripts/`, so `EXPECTED_MUTATIONS` and every manifest
are untouched and the full `--mutate .` harness has nothing new to measure. Not run, per the brief —
and there is nothing for it to find on this diff.

**S8 — Baselines green over the tree I measured.** `check-ratchet-contract.py --self-test` →
`41/41 passed`; `check-python-pin.py --self-test` → `84/84 passed` (matching its declared `# 84
cases`); `check-selftest-counts.py` → *"45 script(s) declare a count, every one verified by running
it"*; `check-fixture-variation.py scripts/check-python-pin.py` → *"fixture variation OK — 16
parameter(s) examined"*.

**S9 — The "executes vs gates" residue #156 gestures at is latent, not live.** §5's sharpened limit
— *a structure reader answers "does this text survive masking?", never "does this guard execute?"* —
is correct and well put. I looked for the live instance one level deeper: a guard whose **only**
invocation anywhere is a `--self-test` run would satisfy R3 while nothing gates on it. Swept all 40
guards against the full 82-source caller corpus: **0**. The only two guards with no invocation at
all are `check-merge-ready.py` and `check-review-decision.py`, both of which hold `NO-CALLER:`
escapes — matching r1's S5 exactly. Reported as a negative result: the gap is real and nothing is
standing in it today.

**S10 — `workflow_structure.py` would pass `check-ratchet-contract.py`'s own rules.** `GUARD_PATH_RE`
is `scripts/check-[\w.-]+\.py` applied with `fullmatch` (`:113`, `:164`), so R1–R3 never see a
library — r1's S10, re-confirmed. R4 reaches it via `discover_self_tested_nonguards` (`:402-409`)
the moment it has a `--self-test`; shipping a 12-entry manifest satisfies R4 and keeps it correctly
out of `WIDENED_MANIFEST_DEBT`. No change needed there, and §5's Discovery row (as corrected in r1's
M2) says the right thing.

**S11 — `check-python-pin.py`'s own pinned fixture-variation key set survives the extraction.**
`check-fixture-variation.py:340-343` pins ten keys, all on public functions (`declared_pins.text`,
`job_blocks.text`, `job_names.text`, `running_version.version_info`, `unpinned_jobs.*`, `verdict.*`).
`_steps` and `_structural` contribute none, because `analyse()` excludes `_`-prefixed functions
(`:736`). So removing them does **not** trigger the departure path (`population_drift`'s CANNOT RUN).
Worth stating explicitly so the implementer does not go looking — the problem is on the arrival
side, not the departure side (R3-3).

---

# What I would require before this converges

1. **R3-2** — delete or replace the "would red-line two guards that genuinely run" claim. Measured
   cost today is 0 guards. *(The one I would fix first: it is a false statement in a document whose
   subject is a false statement.)*
2. **R3-1** — #155 must name the extraction of `check-ratchet-contract.py`'s blob construction into
   a suite-driven pure function, or its consumer-coverage requirement cannot be met except vacuously
   or by the trap it sits beside.
3. **R3-5** — `#27–#38`, or state the base, or list the twelve anchor lines instead.
4. **R3-3** — add a `check-fixture-variation.py` bookkeeping row and make the public/private naming
   of the extracted functions an explicit decision.
5. **R3-4** — #156 must cover job-level conditions and say what happens to `always()` and to
   `vars.`/`secrets.`-derived conditions.

R3-M1 and R3-M2 are one clause each and should be fixed in place rather than filed. R3-M3, R3-L1 and
R3-L2 are improvements, not gates.

**On convergence, plainly:** two rounds have now found defects in the *recommendation* rather than
the prose, and this round found three more there (R3-1, R3-3, R3-4) plus two in the repair itself
(R3-2, R3-5). That is not thrashing by this repo's definition — R3-2 and R3-5 come from the previous
round's fix, but R3-1, R3-3 and R3-4 are independent subjects the earlier rounds never opened
(`check-fixture-variation.py` and the consumer's test seam had not been looked at by anyone). The
document is still improving, and improving is the instruction to keep going. But R3-1, R3-3 and
R3-4 are all the same *question* — **what does §5's recommendation actually cost to implement?** —
and it keeps returning a larger answer. If a fourth round finds a fourth unbudgeted consumer, the
honest move is not another round on the document: it is to size #155 by attempting it.
