```yaml
round: 5
subject: decision-route-escalation
writer: coordinator
fixes_nontrivial: true
findings:
  - id: C1
    severity: Medium
    aim: instrument
    fix_induced: true
    component: message-soundness
    disposition: fixed
  - id: C2
    severity: Medium
    aim: instrument
    fix_induced: true
    component: sweep-skip
    disposition: fixed
  - id: C3
    severity: Low
    aim: instrument
    fix_induced: false
    component: shard-balance
    disposition: filed
```

# Adversarial review — `decision-route-escalation` r5 (COORDINATOR half)

**Subject:** the r4 fixes (`c8c3f226..e72360db`) **and** my own uncommitted corrections to the r5
CODEX findings. **Verdict: NOT CONVERGED**, and the justification is below rather than ambient.

**Round topology:** ALTERNATING, not concurrent — CODEX first, then CLAUDE with CODEX's findings and
my responses to them in scope, then this. That ordering is the rule for rounds 2+ precisely because
a concurrent pair never reviews the fixes, and this round is the strongest evidence yet for it:
**every finding in it is against a fix, and five of the eight are against fixes written the same
hour.**

| Finding | Sev | Against | Mine? |
|---|---|---|---|
| CODEX 1 — docs exclusion demonstrably skips changed test inputs | Medium | my r4 "NOT MEASURED" residual | yes |
| CODEX 2 — re-pointed assertions accept the opposite remedy | Medium | my r4 "stricter" claim | yes |
| CODEX 3 — concurrency does not establish ~zero latency | Medium | my r4 docstring + backlog row | yes |
| CLAUDE H1 — the forbidden half has no falsifier; emptying it leaves 102/102 | High | my r5 fix for CODEX 2 | yes |
| CLAUDE H2 — a one-token negation passes; 8 of 8 wrong messages accepted | High | my r5 fix for CODEX 2 | yes |
| CLAUDE M1 — corrected SKIP log is byte-identical either way, self-contradicts | Medium | my r5 fix for CODEX 1 | yes |
| CLAUDE M2 — the latency correction omits its provenance | Medium | my r5 fix for CODEX 3 | yes |
| CLAUDE L1 — "not verified" was verifiable in one command | Low | my r5 caveat | yes |

⛔ **EIGHT FOR EIGHT AGAINST MY OWN WORK, and that is the finding of this round.** It is not
self-flagellation: it is the measured answer to *"is a fix unreviewed code?"* — yes, and at a rate
this branch can now quote rather than assert.

---

## C1 — Medium, FIX-INDUCED: my fix for CODEX 2 was the SAME ERROR ONE LEVEL DEEPER

`scripts/check-review-decision.py`. **Disposition: FIXED, by removing the mechanism rather than
patching it a third time.**

CODEX 2 showed my r4 assertions (`"record" in msg.lower()`, `"DISPOSITION" in msg.upper()`) passed
over a message asserting the opposite. My r5a fix added a FORBIDDEN-phrase list. CLAUDE then broke
that too, twice over:

**H2 — a one-token negation passes.** Verified myself, 4 of 4:

```
True   What reaches convergence is NOT DISPOSITIONING those findings; produce a round with zero…
True   DISPOSITIONING those findings is irrelevant — give me an empty findings list.
True   DISPOSITIONING those findings proves the work is defective.
True   Ignore DISPOSITIONING those findings; DISPOSITIONS are irrelevant.
```

Substring presence cannot distinguish a claim from its negation. My fix was the same class of defect
as the thing it fixed.

**H1 — and the list had no falsifier at all.** Verified over a green control in a staged
`HARNESS_TREE`:

```
CONTROL                                   102/102 passed
UNREACHABLE_FORBIDDEN = ()                102/102 passed
delete one phrase from the tuple          102/102 passed
```

⛔ **The cause is a case that LOOPED OVER THE SET UNDER TEST**, so both sides shrank together and
`[] == []` passed. ⚠ **That is the rule I had written out longhand in `check-plan-code.py` THE SAME
HOUR** — *"AN INDEPENDENT COPY, NOT A LOOP OVER THE SET UNDER TEST"* — for `SWEEP_RELEVANT_ROOTS`,
and then broke in the adjacent file. Knowing a rule and applying it are different acts, which is
this repo's whole argument for putting rules in scripts rather than prose.

**THE FIX IS STRUCTURAL, AND THE REASON IS A RECORDED ONE.** `dual-review-what-it-catches`:
*use review for CLAIMS and design; use a corpus for SURFACES.* A message is an unbounded surface, so
each round finds another evasion and none is the last — three rounds had already gone that way. So
the property is now carried by **TOKENS** (`UNREACHABLE_ABOUT = "record"`,
`UNREACHABLE_REMEDY = "disposition"`), the prose is RENDERED from them, and the suite asserts VALUE
EQUALITY. A token cannot be negated the way a sentence can.

Measured against the two mutations both prose versions survived:

```
CONTROL                                        107/107
remedy token -> "clean-round"                  103/107   (4 cases redden)
about token  -> "work"                         104/107   (3 cases redden)
delete a rendering  ->  [FAIL] every token … HAS a rendering, then a deliberate KeyError
```

⚠ **And one more defect of mine, found by the harness rather than by me:** my new cases were written
`unreachable_reason(...)["about"]`, which **crashed the suite** under the `aim`-arm mutation (that
round becomes clean, the function correctly returns None, the subscript raises). A crashing suite
truncates the run, so later cases go unevaluated and *other* mutations lose their attribution —
measured: the aim mutation reported one red, no "passed" line, and `check-plan-code` refused its
`expect`. `(… or {}).get(…)` turns that into a named red. Pyright had flagged those two lines and I
read past it.

---

## C2 — Medium, FIX-INDUCED: the SKIP log, wrong for the THIRD time

`.github/workflows/ci.yml`. **Disposition: FIXED, and now computed rather than asserted.**

- **v1** claimed *"no scripts/ file changed"* on a path where the diff had FAILED (r4's High).
- **v2** — my fix — claimed *"nothing the harness stages changed"* while `docs` **is** staged, and
  asserted *"unchanged suites"* one line above its own warning that a docs change can alter a suite
  result. CLAUDE M1: self-contradicting in adjacent lines, and **byte-identical whether the hole was
  crossed or not**.
- **v3** discriminates, and the discrimination is computed by a new pure
  `check-plan-code.sweep_skipped_hole` — not by a `grep` alternation in YAML, which would be a
  second implementation of `SWEEP_SKIP_ROOTS`.

Executed, all three arms:

```
docs-only  -> changed=false + "these changed paths are STAGED and NOT swept — the measured hole:"
                              docs/backlog.md / docs/roadmap-to-launch.md
app-only   -> changed=false + "nothing in the skipped set either"
diff fails -> changed=true  + two ::warning:: lines
```

⭐ **ALL THREE ERRORS WERE IN THE REPORTING LAYER OF A CORRECTNESS FIX, not in the logic.** That is
the pattern worth carrying: the verdict was right each time and the sentence about it was wrong, and
a log line that asserts more than its step knows is indistinguishable from a working gate.

**AND CODEX 1 CLOSED A RESIDUAL I HAD DECLARED UNMEASURABLE.** My r4 comment said whether a `docs`
content change can flip a verdict was "NOT MEASURED, no claim either way". CODEX measured it:
staged tree, `check-anon-exposure --self-test` 74/74, then `ASSERTION FAILED` → `ASSERTION REMOVED`
in the staged `docs/.../05_*.sql` drives it to exit 1 — while `sweep_needed([that path])` is False.
CLAUDE reproduced it independently (74/74 → 73/74 → restore 74/74). So the safety rationale is
**disproved for `docs`**, the exclusion is a KNOWN MEASURED HOLE retained as a deliberate trade, and
the comment and the CI log now say so. The predicate is unchanged: reverting backlog #173's pinned
decision would redden the case and the mutation entry that guard it.

---

## C3 — Low, filed as backlog #333: the shard imbalance, and the number I could not reproduce

CODEX 3 refuted my *"close to ZERO wall-clock"* claim — an **inference stated as measured**: I
reasoned `needs: null` → concurrent → free, and never measured it. Re-derived over three successive
*successful* runs:

```
                       39359868562  39353987366  39330490473
verify                       3.3m         3.2m         5.2m
slowest shard               26.2m        23.9m        24.3m
verify -> sweep-complete    23.1m        20.9m        19.3m
shard spread               2.15x        1.94x        2.13x
```

And CLAUDE L1 settled the caveat I had left open: `mutation-sweep-complete` **is** a required check
(`gh api .../branches/master/protection` → `["verify","schema-gates","mutation-sweep-complete"]`), so
that is **merge** latency. ⚠ A caveat that could have been a measurement is not a bound, it is an
omission — one command settled it.

⭐ The measurement produced a finding the arithmetic did not: `ci.yml:729` predicts a **1.15×**
round-robin spread, measured wall-clock is **1.94–2.15×**, all eight shards starting within one
second. Since the sweep's critical path IS its slowest shard and the ~153s control floor is paid
twice per shard without dividing by N, **balance is worth more than a larger N**.

⚠ **CLAUDE M2 was right that the row shipped without provenance, and one of its own numbers does not
reproduce.** All three runs are `baseline-surveys` (`23e5a349`, `5e22e9b8`, `e805b88e`) at a
**1,545**-entry manifest against **1,649** here — **1.067×**, derived from git. CLAUDE stated
**1.89×**; that does not reproduce against entry count and is recorded as UNRESOLVED rather than
adopted or dismissed. Its scaled-model result (fastest 0.98–1.06×, slowest 2.06–2.26×, refuting
stale estimates and localising to distribution) is **attributed, not asserted** — I did not
re-derive it, as it needs the per-suite cost table. backlog #333's falsifier now names the branch
and manifest.

---

## Negative results

**N1. CLAUDE's attack on my latency arithmetic held it.** It reports that constant per-job overhead
compresses a ratio and so cannot manufacture a 2.15×, that I did not misread `ci.yml:729`, and that
the comparison is valid in the direction claimed. Recorded because a confirmed method is a result.

**N2. Retaining the docs hole is defensible — CLAUDE declined to file it** after reproducing the
measurement, agreeing the comment is now accurate and the real defect was the non-discriminating log.

**N3. Two of CLAUDE's own runs were non-discriminating and it reported them as such** rather than as
evidence: a forbidden-list mutant whose control was also red (89/102, outside the staged tree), and
a monkey-patched convergence control returning 0 violations because both callers go through
`round_blocker` — which is the extraction's point. Only reintroducing the second implementation
discriminated, and it produced 90. That is the discipline this round was asking for, applied to
itself.

---

## ⛔ `fixes_nontrivial: true` — r6 IS OWED, and I am not pretending otherwise

The r5 fixes are substantial: a prose-matching apparatus deleted and replaced with structured
tokens plus a renderer, a new pure `sweep_skipped_hole`, a restructured `ci.yml` SKIP arm, +11
cases, +5 mutation entries, 2 entries RETIRED WITH THEIR SUBJECT, 1 RE-POINTED, 2 dead mutations
replaced after measuring that they changed no behaviour.

**And eight of eight findings this round were against fixes.** The honest reading is that the
component `message-soundness` has now been fixed three times, which is the thrashing shape — except
that r5's fix **removes the surface** rather than patching it, so the next round should have nothing
of that class to find. That is a prediction, and it is the falsifier: *if r6 finds a ninth evasion of
the convergence diagnostic, the structural fix did not work and the mechanism needs a redesign, not
another round.*

⚠ Separately: `thrashing_component` would not notice any of this, for the reason filed as
backlog #332 — it reads only `rounds[-2] & rounds[-1]`, so each new round disarms the last.

---

## ⛔ THRASHING OR PROSE FLOOR? — the answer this round is obliged to give

`check-review-decision.py` now returns **`ARCHITECTURE_REVIEW — thrashing: 'sweep-skip' carried
fix-induced findings in r4 and r5`**, and filing this half is what armed it. `dev-process.md` says
reaching four rounds OBLIGES ASKING, with per-finding evidence, so:

**IT IS THRASHING BY THE MECHANICAL DEFINITION, AND IT IS THE PROSE FLOOR BY THE EVIDENCE.** Both
are true and the distinction decides whether to convene.

Per finding on `sweep-skip`, every one fix-induced:

| Round | The defect | Layer |
|---|---|---|
| r4 C2 | `RUN` arm printed "scripts/ changed" when the diff had FAILED | the log line |
| r4 C2b | the repair re-implemented `SWEEP_RELEVANT_ROOTS` as a YAML `grep -E` | the log line's evidence |
| r5 C2 | `SKIP` arm claimed "nothing the harness stages changed" while `docs` IS staged | the log line |
| r5 C2b | …and asserted "unchanged suites" one line above its own contradiction | the same log line |

⭐ **FOUR FOR FOUR IN THE REPORTING LAYER. THE VERDICT LOGIC HAS BEEN CORRECT SINCE r4 AND NO ROUND
HAS FOUND A DEFECT IN IT.** `sweep_needed`'s decision, the `None` arm's reachability, and the
`changed=true`/`false` outputs have been re-executed in every round since and held every time —
recorded in r4's N3 and this half's C2. What kept moving is the SENTENCE describing the decision.

`dual-review-what-it-catches` names this exact shape and separates it from regression: *"ALL THREE
BLOCKINGS WERE ABOUT THE EVIDENCE, NEVER ABOUT THE GUARD MISBEHAVING … The severity curve measures
measurement quality improving first, then code quality."* That is cause 2 (coupled falsifiers /
apparatus damage), not cause 1 (new mechanism, new edges). **A redesign cannot remove it, which is
`review-method.md`'s own test for convening** — there will always be a sentence in a CI log, and a
sentence is an unbounded surface.

**So: do not convene on `sweep-skip`. Convene only if the prediction below fails.** What r5 changed
is that the reporting is no longer prose in YAML — `sweep_skipped_hole` is a pure function with 6
cases and 2 mutation entries, so the NEXT instance of this class is caught by a case rather than by
a reviewer. That is the structural move available here, and it is already made.

⛔ **THE FALSIFIER, PRE-COMMITTED SO IT CANNOT BE ARGUED AWAY LATER:** if r6 finds a fifth
fix-induced defect in `sweep-skip`'s reporting, this answer was wrong — the apparatus is not
converging and the step needs a redesign (most likely: no narrative log at all, just the verdict and
the evidence list the module emits). ⚠ And if r6 finds a defect in `sweep_needed`'s LOGIC rather
than its reporting, that is cause 1 and convening is correct regardless of this answer.

⚠ **I am the wrong party to settle this alone and say so plainly:** every finding being against my
own fixes means the party answering "is this thrashing?" is the party whose work armed it. The
answer above is reasoned from recorded evidence and pre-commits its falsifier, which is the best I
can do from here; the owner should know the mechanism said ARCHITECTURE_REVIEW and that I declined
to convene, with this as the reason.
