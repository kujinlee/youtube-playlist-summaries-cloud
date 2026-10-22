```yaml
round: 5
subject: decision-route-escalation
writer: claude
fixes_nontrivial: false
findings:
  - id: H1
    severity: High
    aim: instrument
    fix_induced: true
    component: unreachable-message-soundness
    disposition: filed
  - id: H2
    severity: High
    aim: instrument
    fix_induced: true
    component: unreachable-message-soundness
    disposition: filed
  - id: M1
    severity: Medium
    aim: instrument
    fix_induced: true
    component: sweep-skip
    disposition: filed
  - id: M2
    severity: Medium
    aim: process
    fix_induced: true
    component: sweep-latency-measurement
    disposition: filed
  - id: L1
    severity: Low
    aim: process
    fix_induced: false
    component: sweep-latency-measurement
    disposition: filed
```

# Claude adversarial review — `decision-route-escalation`, round 5

**Subject, two layers.** (A) `git diff c8c3f226..e72360db`, the r4 fixes. (B) `git diff HEAD` on
`.github/workflows/ci.yml`, `scripts/check-plan-code.py`, `scripts/check-review-decision.py`,
`scripts/mutations/check-review-decision.json`, `docs/backlog.md` rows 330/333 — the coordinator's
corrections to r5 CODEX's three findings, which no review had seen. The 12 modified
`docs/explainers/*.html` files in that diff are a previous session's work and were ignored.
**Everything below was executed.** Nothing in this document is reasoned-only except where labelled
UNVERIFIED.

**Headline.** Layer A holds under every attack I built for it — including the one invariant r4 was
extracted to protect, which I could only break by *reintroducing the second implementation*. The
findings are all in **layer B**: the correction written for CODEX finding 2 is a guard with **no
coverage that can fail**, and it accepts a one-token negation of the very property it exists to
assert. The correction for finding 1 is honest about the hole and then prints the same sentence
whether the hole was crossed or not. The correction for finding 3 is **arithmetically exact — I
reproduced every figure** — and omits the one provenance fact that makes it reproducible.

---

## H1 — High. The FORBIDDEN half of `unreachable_message_sound` has no coverage that can fail: emptying the tuple leaves the suite 102/102 green

**`scripts/check-review-decision.py:287-296`** (the tuple), **`:877-879`** (its only case).

The docstring calls this half load-bearing — *"⭐ SO THE FORBIDDEN HALF IS THE LOAD-BEARING HALF"*
(`:313`) — and `EXPECTED_MUTATIONS` was raised 22 → 23 for it. It has **zero falsifiable coverage**.

Its only case iterates over the set under test:

```python
case("each forbidden phrase alone is enough to reject a message that also names the remedy",
     [unreachable_message_sound(f"{UNREACHABLE_REMEDY} but also {f}")
      for f in UNREACHABLE_FORBIDDEN], [False] * len(UNREACHABLE_FORBIDDEN))
```

Both sides are derived from `UNREACHABLE_FORBIDDEN`, so shrinking the tuple shrinks the comparison
rather than reddening it — `[] == []`. **Failure scenario:** someone trims a phrase from the list
while tidying (or deletes the tuple's contents in a merge), the abolished demand it forbade becomes
accepted again, and every gate stays green.

Measured in a staged `HARNESS_TREE` tree, **control proved green first**:

```
=== CONTROL in staged tree ===
102/102 self-test cases passed

=== MUTANT M-A: UNREACHABLE_FORBIDDEN = ()  (gut the load-bearing half entirely) ===
102/102 self-test cases passed

--- MUTANT: deleted forbidden entry "finding-free", ---        102/102 self-test cases passed
--- MUTANT: deleted forbidden entry "DISPOSITION is irrelevant", --- 102/102 self-test cases passed
--- MUTANT: deleted forbidden entry "WORK is defective", ---    102/102 self-test cases passed
```

⚠ **My first run of this was non-discriminating and I discarded it.** Run from the scratch directory
the copy scored `89/102` — and so did the *unmutated* control, because 13 cases resolve the repo root
from `__file__`. The figures above are from a tree staged over all seven `HARNESS_TREE` paths, where
the control is green.

**And the starred case does not cover it either.** The case labelled *"⭐ ...and the message that
defeated the old assertions is REJECTED by the new one"* (`:874`) is insensitive to the forbidden
half — CODEX's counterexample lacks `UNREACHABLE_REMEDY`, so the **positive** half already rejects it:

```
C3 is the counterexample rejected by the FORBIDDEN half, or only by the POSITIVE half?
   positive half alone (remedy present?): False
   -> so with UNREACHABLE_FORBIDDEN = (), the counterexample case still returns: False
```

The mutation entry's own name concedes this (*"ATTRIBUTED TO THE 'each forbidden phrase alone' CASE,
NOT to the counterexample case"*) — so the manifest points at the one case that is structurally
unable to fail, and the harness cannot see that, because `--mutate .` measures the entries that
exist, not the ways a guard can die with no entry. I confirmed the shipped entry itself is fine:
scoped run, **23/23 killed, 23 attributed, 0 survivors, 5.3s**.

This is `a-class-fix-needs-an-independent-copy-and-an-identity-case` exactly: the fix needs an
**independent literal copy** of each forbidden phrase in the case, plus an identity case asserting
`len(UNREACHABLE_FORBIDDEN) == 5` (or the phrases themselves), so the set cannot shrink silently.

## H2 — High. The check accepts a one-token NEGATION of the remedy, and two rewordings of the abolished demand: 8 of 8 adjacent wrong messages pass

**`scripts/check-review-decision.py:298-320`.**

The stated guarantee is *"What it now guarantees is that the three specific demands backlog #329
abolished cannot come back, and that the remedy is named as a remedy"* (`:318`). **Both halves of
that are false by measurement.** `True` below means the unsound message PASSED:

```
=== ATTACKS: True means the unsound message PASSED the soundness check ===
True  | A1 one-token NEGATION of the remedy
True  | A2 abolished demand, reworded ('zero findings')
True  | A3 abolished demand, reworded ('empty findings list')
True  | A4 blames the work, lowercase ('work is defective')
True  | A5 negates disposition, pluralised ('DISPOSITIONS are irrelevant')
True  | A6 CODEX counterexample + remedy phrase bolted on (what an author 'fixing' it would write)
True  | A7 instructs the reader to DELETE the findings
True  | A8 tells the reader to stop reviewing

=== CONTROLS ===
True  | C1 the shipped runtime message (expect True)
False | C2 CODEX verbatim counterexample (expect False)
```

**Paired**: the check does discriminate on the two inputs it was built from (C1/C2). It fails on
every input adjacent to them.

**A1 is the finding.** Its text is:

> *"UNREACHABLE from this record. What reaches convergence is **NOT** DISPOSITIONING those findings;
> produce a round with zero findings instead."*

`"DISPOSITIONING those findings" in msg` is satisfied **by the negation**, because the negation
contains the phrase. That is verbatim the defect the fix was written to close — the docstring's own
words, `:311`: *"Substring PRESENCE cannot tell a claim from its negation."* The new check has the
same property; prefixing `NOT` is not creative rewording.

**A2/A3 refute the "three demands cannot come back" guarantee**: `zero findings` and `empty findings
list` are the demand backlog #329 abolished, in words the five-phrase list does not contain.
**A4/A5 refute the other two forbidden entries** by case (`work is defective` vs the
case-sensitive `"WORK is defective"`) and by number (`DISPOSITIONS are irrelevant`).

**Failure scenario, concrete:** a future round rewrites this diagnostic to *"...produce a round with
zero findings"* — the demand measured as unsatisfiable over 48 rounds — the suite passes 102/102, the
mutation manifest reports 23/23, and the reader is told to make an artifact the workflow does not
produce. That is the exact r4 harm this guard was added to prevent, restated in `round_blocker`'s own
docstring at `:256`.

⚠ **The docstring does declare a bound** (`:316`, *"still prose matching and a sufficiently creative
rewording could pass it"*). The bound is **weaker than the reality it covers**, which is the
`a-bound-enumerates-what-is-witnessed` shape — a caveat headed *"stated rather than hidden"* that is
wrong is worse than none. A one-token negation and a two-word synonym are not "sufficiently creative".

⭐ **And the check is wrong in BOTH directions, which is the design signal.** The author records that
the *previous, correct* message was rejected by the new check because it recited the abolished demand
in order to refute it (`:350-355`), and resolved that by rewriting the message. So the predicate
cannot distinguish **mention from use** either way: it rejects correct mention (measured — the old
message) and accepts incorrect use (measured — A1-A8). `a-shim-can-fail-in-both-directions`. A phrase
list cannot carry this property; what can is making the *remedy* machine-checkable — e.g. assert the
message names the literal dispositions `round_blocker` accepts (`"fixed"`, `"declined"`) and the one
it rejects (`"filed"`), derived from that function rather than retyped, and drop the negative list.

## M1 — Medium. The corrected SKIP log is byte-identical whether the measured hole was crossed or not, and still asserts "unchanged suites" one line above its own refutation

**`.github/workflows/ci.yml:902-915`** (the `SKIP` arm of step `mutated_code`).

I extracted the real `run:` block with `js-yaml`, substituted the two `${{ }}` expressions, and drove
it with a `git` shim on `PATH` that resolves `rev-parse` and emits a controlled changed-file list:

```
────────── changed = [README.md] ──────────
no path under check-plan-code.SWEEP_RELEVANT_ROOTS changed against HEAD^,
so the sweep would mutate unchanged code against unchanged suites.
⚠ KNOWN HOLE: docs/ is staged but deliberately NOT in that set (backlog #173's
pinned decision), and a docs change CAN alter a suite result — backlog #330.
  [GITHUB_OUTPUT] changed=false
────────── changed = [docs/.../schema/05_assert.sql] ──────────
no path under check-plan-code.SWEEP_RELEVANT_ROOTS changed against HEAD^,
so the sweep would mutate unchanged code against unchanged suites.
⚠ KNOWN HOLE: docs/ is staged but deliberately NOT in that set (backlog #173's
pinned decision), and a docs change CAN alter a suite result — backlog #330.
  [GITHUB_OUTPUT] changed=false
```

**Two defects, both in the fix.**

**(a) Zero discriminating power, from information the step already holds.** `/tmp/changed.txt` is in
hand; the step knows whether any `docs/` path changed. It prints the same four lines either way. So a
PR touching only `README.md` is warned about a docs hole it never went near, and the PR that changes
`docs/.../05_assert.sql` — the file I proved flips a suite — gets a warning indistinguishable from
noise. **Failure scenario:** the reader learns the line is boilerplate (it appears on every skip),
and the one case it was written for is the case it cannot mark. The `RUN` arm, two lines below,
already does the right thing: it branches on `DIFF_TAKEN` and prints the matched paths.

**(b) It still asserts the refuted claim, above the refutation.** Line 2 — *"so the sweep would
mutate unchanged code against unchanged suites"* — is the sentence the measurement disproved: when a
`docs/` file changes, a suite **input** changed, so the suites are not unchanged. Lines 3-4 then say
so. A reader who skims reads line 2. The comment above it states the intent correctly (*"It now says
what was actually tested"*), and line 2 is not what was tested.

**(c) UNVERIFIED (channel).** The hole notice is a plain `echo`, while this same step uses
`::warning::` on both of its other non-obvious arms. A plain echo inside a collapsed log step is the
weaker channel (`a-gates-channel-can-be-weaker-than-the-gate`); I did not measure GitHub's rendering,
so this is reasoned only.

**Minimal fix:** branch the arm on whether any changed path starts with `docs/` — print the hole
notice as a `::warning::` only then, and only then name the paths; otherwise say the skip is clean.
That also removes (b), because line 2 becomes true in the branch that prints it.

**Retaining the hole itself is defensible and I am not filing it.** Including `docs` reverts backlog
#173 for the population it was filed for, and would redden the case and the mutation entry that pin
the decision — the `a-guard-can-mandate-the-duplication-it-audits` trap, which this comment names.
The trade is stated at the strength it was measured and `#330` owns the fix that dissolves it.

## M2 — Medium. The latency correction is arithmetically exact and omits the provenance that makes it reproducible: all three runs are `baseline-surveys`, at 1.89x this branch's manifest

**`scripts/check-plan-code.py:1795-1820`** (the `sweep_needed` docstring) and **`docs/backlog.md`
row 333**.

**Every figure reproduces. I re-derived them from `gh api` rather than taking them:**

```
         run  verify  fastest  slowest  spread  agg_end-verify_end  shard_start_spread
 39359868562     3.3     12.2     26.2    2.15x                23.1                   1s
 39353987366     3.2     12.3     23.9    1.94x                20.9                   1s
 39330490473     5.2     11.4     24.3    2.13x                19.3                   0s
```

All three `conclusion=success`, same branch, inside five hours. `verify` 3.3/3.2/5.2, slowest shard
26.2/23.9/24.3, `verify`→`mutation-sweep-complete` 23.1/20.9/19.3, spread 2.15/1.94/2.13 — the
docstring and row 333 are correct to the decimal.

**The method survives the attack I built for it.** `completed_at − started_at` per job includes
per-job constant overhead (checkout, `npm ci`) that the model excludes — but a *constant* added to
both ends **compresses** a ratio toward 1. Measured spread is 2.15x, *larger* than the predicted
1.15x, so the confound cannot manufacture this finding; if anything it understates it. And all eight
shards start within one second, so queueing is excluded by measurement, as the row says.

**The defect is what is missing.** The three runs are on **`baseline-surveys`**, whose
`EXPECTED_MUTATIONS` sums **3,114 over 64 files** against this branch's **1,645 over 65**. Neither
document records this. The model at `ci.yml:729` was fitted on **1,193 entries over 57 files** and
predicts **325-374s per shard**. So row 333's own falsifier — *"per-shard wall-clock on a successful
run must agree with the model's predicted spread"* — sends a reader to compare 325-374s against
11-26 min and conclude the model is off by **4x on magnitude as well as spread**. It is not:

```
per-entry cost from the fit      : 1.346s
MODEL predicts per shard, N=8    : 697s = 11.6 min   (scaled to 3,114 entries / 64 files)

39359868562: fastest 12.2 min = 1.05x model | slowest 26.2 min = 2.26x model
39353987366: fastest 12.3 min = 1.06x model | slowest 23.9 min = 2.06x model
39330490473: fastest 11.4 min = 0.98x model | slowest 24.3 min = 2.09x model
```

⭐ **This strengthens the finding and removes one of its four candidate causes.** Scaled to the
manifest it was measured against, the model predicts the **fastest** shard within **0.98-1.06x** and
the slowest at **2.06-2.26x**. So the per-suite cost estimates are **not** globally stale — row 333's
first candidate cause is refuted by its own data — and the anomaly is purely in **distribution**: one
or more shards carry ~2x the modelled work. That points at the remaining candidates (cost correlating
with index through `muts[i-1::N]`, or a few entries whose suites far exceed their file's average),
and it means the fix is balancing by **measured cost**, which is the row's own stated Work item.

**Fix:** record the branch and manifest size beside the measurement in both documents, and restate
the falsifier against a model prediction scaled to the manifest measured — otherwise the next reader
re-derives the wrong conclusion from the right numbers (`a-retrospective-number-needs-provenance`).

## L1 — Low. Both documents declare `mutation-sweep-complete`'s branch-protection status "not verified". One API call settles it, and the answer strengthens them

**`docs/backlog.md`** rows 330 and 333: *"⚠ Whether `mutation-sweep-complete` is REQUIRED by branch
protection is **not verified** — that is a repo setting, and it decides whether this is merge latency
or only workflow latency."*

```
$ gh api repos/kujinlee/youtube-playlist-summaries-cloud/branches/master/protection \
    --jq '.required_status_checks'
{"contexts":["verify","schema-gates","mutation-sweep-complete"], ... "strict":false}
```

**It IS required.** So the 19-23 minute `verify`→aggregator gap is **merge** latency, not merely
workflow latency, and the correction's conclusion (*"the sweep IS the critical path"*, *"backlog
#173's cheap half is worth more than my correction claimed"*) is stronger than the rows claim. Filed
Low because it is an unclosed caveat rather than a wrong statement — but a declared-unverified item
with a one-command answer is the cheapest kind of debt to leave standing.

---

## NEGATIVE RESULTS — attacks that held

These are the result, not filler. Each is paired.

**1. CODEX finding 1 reproduces independently — the docs hole is real.** Staged tree, control first:

```
=== CONTROL: check-anon-exposure in staged tree ===      74/74 passed   rc=0
=== MUTANT: docs-only content change ===                 73/74 passed   rc=1
=== restored; re-control ===                             74/74 passed
```

`sed 's/ASSERTION FAILED/ASSERTION REMOVED/'` on
`docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/05_assert.sql` (101 occurrences),
no `scripts/` change. And `sweep_needed(["docs/.../05_assert.sql"]) == False`. The corrected comment
at `check-plan-code.py:282-296` is accurate; the hole is measured, not asserted.

**2. The r4 convergence invariant holds, and my generator is PROVEN sensitive.** 732 generated states
(severity × aim × disposition × 1-3 rounds × both scopes), `converged() is True ⟹
convergence_unreachable() is None`:

```
shipped (round_blocker extracted)                         calls=732 violations=0
pre-r4 shape (convergence_unreachable owns a 2nd copy)    calls=732 violations=90
```

⚠ **My first negative control returned 0 and I rejected the run.** Monkey-patching
`m.round_blocker` cannot break the invariant, because **both** callers go through it — which is the
extraction's whole point. The only control that discriminates reintroduces the second implementation
inside `convergence_unreachable`. That is a structural guarantee, not a tested one, and it is the
strongest thing in this diff.

A wider sweep (25,664 states, including malformed severities, `aim: 0`, `disposition: False`, a
missing `findings` key, and both `scope` values) also produced 0 violations and **0** reachable
reasons that mention `UNREACHABLE` and fail `unreachable_message_sound` — but that run shares the
blind control above, so I report it as non-discriminating rather than as evidence.

**3. No other producer of the abolished demand survives.** AST scan over every string literal in
`check-review-decision.py`: 7 contain a forbidden phrase, and all 7 are docstrings, the
`UNREACHABLE_FORBIDDEN` tuple itself, or the negative test case. No reader-facing runtime message
besides the one rewritten recites it. The r4 class is closed in that direction.

**4. The rewritten runtime message is still actionable.** It names the remedy, the two dispositions
that count (`fixed`, `declined`), the one that does not (`filed`), and why. It drops the base-rate
figures the old text carried (*"48 rounds, 1 clean, 0 of 12 subjects converging"*), which were the
evidence for the claim — noted, not filed, since `backlog #329` is cited in their place.

**5. `SWEEP_RELEVANT_ROOTS` boundary probes all behave.** `scriptsfoo/x.py` → False,
`.agents/skillsother/y.md` → False, `node_modules/typescriptx/x.js` → False,
`node_modules/typescript/lib/x.js` → True, `.agents/skills/shared/handoff-path.md` → True,
`.claude/hooks/...` → True, `.github/workflows/ci.yml` → True, `supabase/migrations/...` → True,
`.claude/settings.json` → False (not staged), `None` → True, `[]` → False.
⚠ **UNVERIFIED:** `./scripts/x.py` → **False** and a bare `scripts` → **False**. I did not find a
way to make `git diff --name-only` emit either form, so I am recording the near-miss rather than
filing it; the prefix test is `str.startswith` against trailing-slash roots and a `./` prefix would
defeat it if any caller ever produced one.

**6. The new mutation entry reddens through the case it names, over a green control.** Staged tree,
all manifests but `check-review-decision.json` deleted, `EXPECTED_MUTATIONS` reduced to that one key:
`23 mutation(s), 23 killed, 23 attributed to the case each names, 0 survivor(s)` in **5.3s**.
`EXPECTED_MUTATIONS` 22→23 and the declared sum 1644→1645 both match the real population (65 files,
sum 1,645, verified by import).

**7. `backlog #332` is not worsened.** `thrashing_component` is untouched by layer B; the
`round_blocker` extraction moved the clean-round rule only, and `thrashing_component` does not call
it. Not re-filed.

---

## Verdict

**NOT CONVERGED.**

The named finding is **H1**: the half of `unreachable_message_sound` that its own docstring calls
load-bearing can be deleted entirely — tuple emptied, or any single phrase removed — with the suite
at **102/102** and the mutation manifest at **23/23 attributed**. A guard with no coverage that can
fail is not a guard, and this one was added *this round* to close a defect CODEX had just measured.
**H2** is the same function failing on its own terms: a one-token negation of the remedy passes, and
the three abolished demands the docstring says "cannot come back" come back under two synonyms.

**What would change the answer.** H1 closed by an independent literal copy of each forbidden phrase
plus an identity case pinning the tuple's membership; H2 closed by deriving the remedy assertion from
`round_blocker`'s accepted dispositions instead of matching prose, or — if the phrase list is kept —
by replacing the guarantee in the docstring with the bound I measured above. M1 and M2 are both
one-edit fixes (branch the SKIP arm on a `docs/` path; record the measurement's branch and manifest
size). None of layer A is implicated: the convergence extraction, the `ci.yml` failure paths, the
`SWEEP_RELEVANT_ROOTS` derivation and the hook fix all held under execution, and the one invariant
I could not break required reintroducing the defect to break it.
