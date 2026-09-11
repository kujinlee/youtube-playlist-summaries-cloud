# Backlog #106 — composing is idempotent — round 3, CLAUDE half

**Reviewer:** Claude (adversarial half). **Date:** 2026-09-10.
**Verdict up front: NOT CONVERGED.** One Blocking, and it is the round-2 fix generating the
round-3 defect for the third consecutive round — but with a difference worth stating early: this
time the defect is not in the transform, it is in the **advice**. The tool now tells a user to run
a command that deletes the tray's ask button, and every guard on the branch approves.

---

## PROOF OF SUBJECT

```
$ git status --porcelain
                                    (empty — clean, as you said)
$ git log --oneline origin/master..HEAD
51b0803f Round 2: the marked region is verbatim, and the repair is guarded
d9878eeb Round 1: the marker region goes back to being verbatim
370144b1 Backlog #106: composing a page twice now produces the same page

$ git merge-base origin/master HEAD
050913f6ab1d7d5dc68458b06260c0c9b697a436
```

14 files, +2,418/−47. Tree stayed clean for the whole review — the first round where that was true.

**Pinned:** `scripts/brief-compose.py` md5 `7e4ea15c544e6f6b95472c627a0f4e7b`,
`scripts/mutations/brief-compose.json` md5 `ab5909da97a5bb6eb6f78ef59802f168`, snapshotted
18:37:13. `--self-test` rc=0, **130/130**; docstring declares 130; `check-selftest-counts` rc=0;
manifest 18 entries. I did not run `--mutate .`. Every mutation below was applied to a scratch copy.

---

## BLOCKING

### B1 — The ⚠ instructs the user to run a command that deletes the heading ask path, and all three guards say yes

Measured end to end through `main()`, not reasoned:

```
### fragment legitimately declares a rule identical to a GENUINE tray rule
  tray region : '#tray{a:1}\n#qbox{b:2}\n.askbtn{c:3}'
  fragment    : '.askbtn{c:3}'

  normal run  : ⚠ fired
     "src.html's tray region carries 1 rule(s) this fragment also declares …
      Repair with --remigrate"
  --remigrate : rc=0   (pollution() non-empty ✓   remigration_risk() empty ✓   floor ✓)
  resulting tray: '#tray{a:1}\n#qbox{b:2}'
```

`.askbtn` is gone. That is the rule SHIM's own comment calls load-bearing — *"the tray appends an
ABSOLUTELY positioned `.askbtn` to every heading… 29 of the 33 pages carrying a tray had NO
positioning context; 6 buttons unreachable"* — and it is the exact rule you and I both measured
being dropped in r2 M1, which is why the floor was added.

**Every gate passes:**

| gate | why it approves |
|---|---|
| `pollution()` | the fragment does declare that rule — it cannot tell *"page override"* from *"duplicate of a tray rule"* |
| `remigration_risk()` | nothing in the region is outside the selector regex, so nothing is "lost" |
| the floor | `.askbtn` is not in `TRAY_STRUCTURE = ("#tray", "#qbox")`, and both survive |

**Why this is Blocking rather than the r2 residual restated.** In r2 the byte-identical duplicate was
*passive* — you documented it, and a user would have had to stumble into it. It is now **actionable
advice printed on the normal path**, with a guarded command that approves. A residual a user is
instructed to trigger is not a residual.

**Proposed fix, tested against both arms before proposing it.** A deliberate page override has a
shape, and it is the shape `gen-backlog-page.py:1480` documents — *"two ids win without touching the
lifted code"*. Restrict `pollution()` to rules whose selector is a compound/descendant selector
rooted at a tray part:

```
=== does the candidate still detect the REAL pollution? ===
  shipped pollution(): 3 rule(s)
  candidate          : 3 rule(s)
    ['#tray #qbox', '#tray #qbox::placeholder', '#tray #qbox:focus']

=== does it refuse the BLOCKING case? ===
  shipped   : ['.askbtn{c:3}']   <- fires, advises --remigrate
  candidate : []                 <- quiet, nothing destroyed
```

*Falsifier:* it must keep repairing the real `backlog-table` pollution (3 rules, verified above) and
must be quiet when a fragment merely duplicates a bare tray rule. If some real override is *not*
rooted-descendant shaped, my premise is wrong and the rule needs widening — I checked all three live
ones and all three are.

---

## HIGH

### H1 — You asked me to find the fourth guard covered by nothing. There are THREE, and they cluster

I mutated every clause added in r2/r3 against the pinned snapshot. Ten candidates, three survivors:

```
[killed(3)  ] [NOT in manifest] pollution: compares against the WRONG direction
[killed(2)  ] [NOT in manifest] pollution: always finds nothing
[killed(1)  ] [NOT in manifest] remigration_risk: loses the at-rule clause
[killed(3)  ] [NOT in manifest] remigration_risk: never reports an unselected rule
[killed(3)  ] [NOT in manifest] remigration_risk: uses _tray_rules, blind to what the scan misses
[killed(3)  ] [in manifest    ] floor: always passes
[SURVIVED   ] [in manifest    ] floor: any() instead of all()          <<<<
[killed(3)  ] [in manifest    ] floor: fallback ignored
[SURVIVED   ] [NOT in manifest] _all_rules: drops the comment strip    <<<<
[SURVIVED   ] [NOT in manifest] TRAY_STRUCTURE loses #qbox             <<<<
```

**All three survivors are the floor's CONTENT, or the normalisation feeding the guard that protects
it.** The floor got a case, and the case pins that the floor *exists*. Nothing pins what it
*requires*:

* **`all()` → `any()` survives**, and the anchor is already in the manifest — the existing entry
  kills `= True` but not the weaker mutation. Both floor cases use fixtures where `all` and `any`
  agree (`".askbtn"` contains neither token; `"#tray #qbox"` contains both), so neither can
  distinguish them.
* **`TRAY_STRUCTURE = ("#tray",)` survives.** The constant can be halved and the suite is green.
* **`_all_rules`' comment strip removed survives** — and it is a *false-positive* source, which is
  the worst kind for a guard that refuses:

  ```
  region: '/* the ask button */\n.askbtn{a:1}\n#tray{b:2}\n#qbox{c:3}'
  remigration_risk (SHIPPED): []
  remigration_risk (MUTANT) : ['/* the ask button */\n.askbtn{a:1}']
  => --remigrate refuses a page it could repair, naming a rule the scan keeps fine
  ```

### H2 — The floor is a substring test over CONCATENATED selectors, so one override rule satisfies it

```python
selectors = " ".join(rule.partition("{")[0] for rule in subtracted)
structure_survives = all(token in selectors for token in TRAY_STRUCTURE)
```

`"#tray #qbox"` contains both `#tray` and `#qbox`. So a subtraction that leaves **one page-override
rule and nothing else** passes the floor. Measured against the real `goals.html` tray, with a
fragment duplicating everything except the two tokens:

```
survived: ['#tray #qbox', '#tray #qbox::placeholder', '#tray #qbox:focus',
           '#tray', '#tray.on', '#tray .in', '#qbox']
DROPPED : ['#modechip', '#modechip', '.askbtn', '.askbtn:hover', '#qt',
           '#sentnote', '#sentnote.err', '#modechip']
=> floor passed; .askbtn, #qt and #sentnote are gone, no refusal
```

**Answering Q3 directly: no, `.askbtn` is not equally protected, and it should be.** It is the
heading ask path. So are `#qt` (the quoted-section header) and `#sentnote` (the only feedback the
reader gets that a question was sent). The floor's token list is the *narrowest* possible reading of
"is this still a tray".

*Fix:* make the floor a whole-selector test over a token set derived from the tray markup plus
`.askbtn`. Derived, so it cannot drift. *Falsifier:* it must still permit the real `backlog-table`
repair (which removes only `#tray #qbox*` and leaves every other selector styled).

### H3 — `pollution()` sees SELF-pollution only; INHERITED pollution is invisible *and* unrepairable

This is Q1's answer, and it is the mechanism the whole branch exists to stop.

```
page A's region carries A's fragment override:  #tray #qbox{color:var(--ink)}
page C is composed from A; C's fragment declares nothing about it

pollution() on C's region : []          <- silent
_selector_scan for C      : keeps '#tray #qbox{color:var(--ink)}'
--remigrate on C          : refuses — "carries none of this fragment's own rules"
```

`pollution(region, fragment_css)` compares the region against **this** page's fragment. Propagation
is precisely how the pollution spreads — a verbatim region is inherited by every descendant — and at
the first inheritance step the rule stops being "a rule this fragment declares", so both the detector
and the repair go blind in the same instant.

So: **a polluted region can still be created by a route nothing detects.** Not by the transform any
more — by inheritance. The r2/r3 machinery repairs generation 0 and cannot see generation 1.

⚠ Live exposure today is one page (`backlog-table.html`, already repaired) and 40 unmarked pages that
clean themselves on first regeneration, so nothing is currently inheriting. The gap is structural,
not active.

---

## MEDIUM

### M1 — A byte-level near-miss silences the detector, and the detector shares its matching rule with the repair

```
region contains: #tray #qbox{color:var(--ink)}
  exact match        : ['#tray #qbox{color:var(--ink)}']
  one space in block : []          # "color: var(--ink)"
  newline in block   : []
```

Your ⚠ text already warns the user about this window — *"the match is on exact rule text, so do it
BEFORE editing those declarations"* — which is exactly right and is my r2 H2b written into the
product. But the warning can only be printed while the match still works. **The detector and the
repair both key on `_tray_rules` exact equality, so they expire together**, and the thing that would
have told you the window closed is the thing that closed. §21's sharpest form: the expectation and
the subject share a source, so the check cannot see that source's omissions.

*Fix:* compare on a whitespace-normalised block for **detection** (keep exact text for removal). The
detector then keeps warning after the window shuts, which is when the warning matters most.

### M2 — The deadlock: ⚠ fires forever naming a repair that refuses forever

```
region is polluted AND carries a rule the scan cannot see (#sendbtn{…}):
  normal run  : ⚠  "… Repair with --remigrate"
  --remigrate : REFUSED — "re-deriving this region would ALSO lose what the scan cannot see"
```

Both guards are individually correct. Together they produce a page that warns on every generation
and names a repair that can never run. Backlog #112's own rule — *a warning that fires every run is
decoration* — then applies to exactly the pages that need attention. The trigger you added in r2 H2
degrades to noise precisely where it is load-bearing.

Reachable the moment anyone styles `#sendbtn`, which this branch's own docstring calls *"one ordinary
CSS rule away"*. *Fix:* when both conditions hold, say so in one message and name the hand repair —
not the command that will refuse.

---

## LOW

### L1 — `_all_rules` is a second copy of the selector-normalise rule

`_all_rules` and `_tray_rules` both do
`re.sub(r"/\*.*?\*/", "", selector, flags=re.S).strip() + "{" + block`. The two must agree or
`remigration_risk`'s set difference is nonsense — which is exactly what H1's third survivor
demonstrates. One helper, called twice.

---

## ANSWERS TO THE SIX QUESTIONS

**Q1 — verbatim path still wrong anywhere? Can a polluted region be created undetected?** The path
itself is correct: I re-ran r1's and r2's counterexamples (`#sendbtn`, `@media`, suffix, selector
list, dangling `#tray `) and all round-trip byte-for-byte. But **yes** — H3: by inheritance.

**Q2 — can pollution hide?** Whitespace and near-miss declarations: **yes** (M1). Inside `@media`:
**no** — `_tray_rules` flattens, so it is detected; but then `remigration_risk` refuses it, which is
M2. `remigration_risk` misses no loss class I could construct: it catches both unselected rules (via
`_all_rules`) and at-rule wrappers, and four mutations against it all died.

**Q3 — is `.askbtn` equally load-bearing?** Yes, and it is unprotected — H2. So are `#qt` and
`#sentnote`. The floor can also be satisfied by a single `#tray #qbox` rule.

**Q4 — can the ⚠ fire spuriously?** Yes, and that is B1. Not merely spurious: acting on it destroys a
genuine rule with every guard approving.

**Q5 — `tally_line` / `attributed` wrong on a cannot-run, control failure, or partial run? No, and
this is the best-engineered thing on the branch.** I tried to construct all three and could not,
because `Measured.__post_init__` (`scripts/coverage_verdict.py:138-158`) makes them
**unrepresentable**:

```
  cannot-run present: REFUSED — mutation(s) at index [1] are not measured — a cannot-run is not a verdict
  control NOT green : REFUSED — controls were not green — a mutation cannot be 'caught' by a suite …
  partial run       : REFUSED — 1 verdict(s) for 2 declared mutation(s) — a mutation that never ran …
```

`killed = mutations - survivors` is therefore exactly right on every verdict that can reach
`tally_line`, and the docstring's *"a cannot-run cannot be present (clause 3)"* is a type invariant
rather than a claim. This is the correct answer to *"can this number be wrong?"* — not *check it*,
but *make the wrong state unconstructible*. The affirmative-numbers change is right for the same
reason it was needed: `0 survivors` was the complement of the question.

**Q6 — the fourth guard covered by nothing.** Three, not one — H1. And the pattern behind all six
now (the r1 branch, the M1 floor, `attributed`, plus these three) is worth naming: **every one was a
guard whose EXISTENCE was cased and whose CONTENT was not.** The floor has two cases and neither
distinguishes `all` from `any`; `TRAY_STRUCTURE` has no case at all. A case that runs the guard is
not the same as a case that would fail if the guard's rule changed. The mechanical form of that
question is the sweep above, and it costs about twenty minutes.

---

## VERDICT

**NOT CONVERGED.**

**The single most important thing to fix: B1** — `pollution()` must not report a rule the fragment
merely duplicates. Everything downstream trusts it: the ⚠ tells the reader to act on it, and
`--remigrate` deletes on it. The rooted-descendant test is one predicate, it is the shape
`gen-backlog-page.py:1480` already documents, and I verified it keeps all three real detections while
going quiet on the destructive case.

**Stop-condition counter: 3**, and for the first time I think the override needs more than a
sentence. Applying the test rather than the symptom list — *can a redesign remove it?*

* B1, H2, M1, M2: **no.** They live in a detector/repair pair whose job is inherently heuristic —
  *"is this rule the page's or the tray's?"* — and every shape of the feature needs that judgement.
  Branch-coverage and threshold defects; a redesign relocates them.
* **H3 is different, and it is the one to watch.** Inheritance makes pollution undetectable by
  construction, because the fragment that declared the rule is not the fragment being asked. No
  tuning of `pollution()` fixes that; it needs a different anchor — a *known-good tray*, rather than
  "whatever this page's fragment does not claim". That is a mechanism defect in the small.

It does not fire yet, because H3's exposure is currently zero (one repaired page; 40 unmarked pages
that self-clean). **Override falsifier:** this fires to REDESIGN if round 4 produces a finding that
requires knowing which rules are canonically the tray's — i.e. if any fix for B1, H2 or H3 needs a
trusted reference tray. At that point the answer is to *state* the tray once (a checked-in canonical
tray file) instead of inferring it from whichever page happens to be newest, and `_selector_scan`,
`pollution()` and the floor all collapse into reading it.

**What is now solid, and I attacked all of it:** the verbatim marker path survived every
counterexample from both previous rounds; `remigration_risk` killed four mutations; `pollution`
killed two; the `Measured` invariants make Q5's three failure modes unconstructible; 18 manifest
entries; 130 cases; counts green.

⚠ Pinned to `brief-compose.py` md5 `7e4ea15c…` and manifest md5 `ab5909da…`.
