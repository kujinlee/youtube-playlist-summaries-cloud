# Backlog #106 — composing is idempotent — round 2, CLAUDE half

**Reviewer:** Claude (adversarial half). **Date:** 2026-09-10.
**Verdict up front: NOT CONVERGED.** The Blocking I was sent to look for was there, I constructed
it, and you had already fixed it by the time I finished measuring. What remains is that **the repair
this branch depends on has no trigger and no guard** — and the page it exists to repair is still
polluted on disk.

---

## PROOF OF SUBJECT

```
$ git log --oneline origin/master..HEAD
d9878eeb Round 1: the marker region goes back to being verbatim
370144b1 Backlog #106: composing a page twice now produces the same page

$ git merge-base origin/master HEAD
050913f6ab1d7d5dc68458b06260c0c9b697a436

$ git diff origin/master...HEAD --stat
 .agents/skills/brief/SKILL.md                      |   6 +-
 docs/backlog.md                                    |   2 +-
 docs/dashboard-entries.md                          |  40 ++
 .../claude/backlog-106-idempotence-r1-claude.md    | 644 +++++++++++++++++++++
 .../backlog-106-idempotence-r1-codex.md            |  42 ++
 .../backlog-106-idempotence-r1-codex.verdict.json  |  20 +
 scripts/brief-compose.py                           | 501 +++++++++++++++-
 scripts/check-plan-code.py                         | 120 +++-
 scripts/check-selftest-counts.py                   |   8 +
 scripts/mutations/brief-compose.json               | 171 ++++++
 scripts/mutations/check-plan-code.json             |  13 +
 11 files changed, 1530 insertions(+), 37 deletions(-)
```

**`git status --porcelain` was EMPTY when I started**, exactly as you said. It did not stay that way.

### ⚠ THE TREE WENT DIRTY DURING THE REVIEW — AGAIN, AND THIS TIME IT MATTERS MORE

Partway through, `git status` returned `M scripts/brief-compose.py` and a
`backlog-106-idempotence-r2-codex.verdict.json` appeared. `_without_page_rules` — the function I was
reviewing — **was deleted while I was measuring it**. I observed four contents:

| md5 | state |
|---|---|
| `ec1b32d4…` | commit `d9878eeb`: text subtraction on both paths ← **where my Blocking lives** |
| `bf0b28be…` | `_without_page_rules` removed; marker path verbatim; `--remigrate` added |
| `e31fee1d…` | (transient) |
| **`03dfc75a…`** | **everything below is measured against this**, and it is the live working tree as I write |

**Everything in the ATTACK sections is pinned to `03dfc75a2fba03b1ca1b4e505d15b905`**, snapshotted at
16:59:45 to a scratch directory so the measurements are reproducible even as the file moves. The
Blocking is reported against `d9878eeb` — the committed state I was asked to review — and marked
**already fixed**, because the evidence is what validates your fix.

**Gate state at `03dfc75a`:** `--self-test` rc=0, 118/118; docstring declares 118;
`check-selftest-counts` was rc=1 (`declares 115, ran 118`) mid-review and is now consistent.
Manifest 14 entries; `EXPECTED_MUTATIONS["scripts/brief-compose.py"] = 14`. I did not run
`--mutate .`.

---

## BLOCKING — found in `d9878eeb`, ALREADY FIXED in the working tree

### B1 — The text subtraction did not delete rules. It MANGLED them, and fabricated new ones.

You asked me to construct it. Here it is, run through `_without_page_rules` at `d9878eeb`:

```
region  : '#tray{a:1}\n#tray #qbox{color:red}\n#sentnote{c:3}'
fragment: '#qbox{color:red}'
RESULT  : '#tray{a:1}\n#tray #sentnote{c:3}'
```

`#qbox{color:red}` is a **proper substring** of the region's `#tray #qbox{color:red}`, so
`out.replace(candidate, "", 1)` matched inside it. Two rules are destroyed — `#tray #qbox{color:red}`
entirely, and `#sentnote{c:3}`'s scope — and a **third rule that never existed in either input is
invented**: `#tray #sentnote{c:3}`, the orphaned selector prefix fused to the next rule's block.

Two more shapes, same cause:

```
'#sentnote, #qbox{a:1}\n#tray{b:2}'  +  '#qbox{a:1}'
   -> '#sentnote, #tray{b:2}'                      (selector list; #sentnote silently restyled)

'#tray{a:1}\n@media (max-width:40rem){#tray{width:100%}}'  +  '#tray{width:100%}'
   -> '#tray{a:1}\n@media (max-width:40rem){}'     (mobile-only rule deleted for an unconditional one)
```

**Idempotence:** one-shot, then stable — `gen1 ≠ gen2`, `gen2…gen5` identical. So it fails backlog
#106's own falsifier once and then converges. Bounded, and I say so rather than implying runaway
growth.

**Reachability, honestly:** not reached today. On `~/explainers/backlog-table.html` — the only marked
page — all three fragment rules are whole region rules, **0 proper substrings**. But the shape is
already present: the region holds `#tray #qbox{…}`, `#tray #qbox::placeholder{…}` and
`#tray #qbox:focus{…}`, and each one's tail is itself a tray-regex selector. The route in is the one
`gen-backlog-page.py:1480`'s own comment describes — *"a plain `#qbox` rule here loses the cascade"* —
i.e. somebody writes the plain form with the same declarations.

**Why this was worse than r1's Blocking, which is the part worth keeping:** r1's fix *deleted*
rules; r2's fix *fabricated* them. A deleted rule leaves a page under-styled; a fabricated selector
is a rule nobody wrote, that no grep will find, silently changing what a different rule matches.

⭐ **Your fix is right and I verified it.** At `03dfc75a` the marker path applies nothing at all, and
all three shapes round-trip byte-for-byte:

```
suffix/descendant : region preserved byte-for-byte: True
selector list     : region preserved byte-for-byte: True
inside @media     : region preserved byte-for-byte: True
```

⚠ **Your residual note was wrong about the failure mode, not just its likelihood.** It said a
byte-identical fragment rule *"still drops it from the region"*. Dropping is the **equal** case. The
**proper-substring** case mangles, and the docstring gave a reader no way to know that — so the
residual as written invited accepting something much worse than it described. Worth remembering as a
class: *a residual must state what happens, not only how often.*

---

## HIGH

### H1 — `--remigrate` is r1's Blocking behind a flag, and nothing stops you pointing it at a healthy page

Measured at `03dfc75a`, on a marked page carrying a rule the selector regex cannot see plus an
`@media` wrapper:

```
normal    : #sendbtn kept: True   | @media kept: True
REMIGRATE : #sendbtn kept: False  | @media kept: False
```

`--remigrate` routes a marked page through `_selector_scan`, which is exactly the transform that
produced r1's Blocking: four of the eight ids/classes in the tray's own markup (`sendbtn`,
`closebtn`, `trow`, `in`) are outside the regex, and at-rules are flattened. That is *acceptable for
a page that needs repair* — the alternative is permanent pollution. It is **not** acceptable that
nothing checks whether the page needs repair.

The failure is quiet and one-way: run it on a healthy page and its tray silently loses whatever the
scan cannot see, forever, with a success message. A one-off repair tool that degrades a healthy
artifact is the same class of hazard as the migration that created this backlog row.

*Proposed fix:* refuse unless the marked region actually shows the pollution signature — i.e. it
contains a rule the current fragment also declares. Print what will be dropped either way.
*Falsifier:* it must still repair `backlog-table.html` (1,691 → 1,383 bytes, the `#tray #qbox` trio
gone — I verified `--remigrate` does exactly that today), and it must refuse or warn on a marked page
carrying `#sendbtn{…}`. If a rule cannot satisfy both, my proposal is wrong.

### H2 — The repair has no trigger, the page is still polluted, and the window closes silently

Three measured facts that only matter together:

**(a) ✅ CLOSED BY EVENTS AT 17:03, WHILE I WAS WRITING THIS — recording it because the correction
is the finding.** For most of the review `~/explainers/backlog-table.html` had mtime `15:57` and its
marked region still contained all three `#tray #qbox*` rules — 1,691 bytes, 15 rules. Your
verification (*"the three rules are gone, exactly 4 lines removed"*) reproduced exactly as a
**computed** result, while the file on disk still carried them. Re-checked after the mtime moved:

```
region now: 1383 bytes, 12 rules
['#modechip','#modechip','.askbtn','.askbtn:hover','#tray','#tray.on','#tray .in',
 '#qt','#qbox','#sentnote','#sentnote.err','#modechip']
TRIO STILL PRESENT: False        page 1,033,098 bytes, </body> count: 1
```

The page is repaired. Note what that took: the normal path at `03dfc75a` takes the marked region
**verbatim**, so it cannot have removed the trio — the repair necessarily went through
`--remigrate`. Which is the system working, and is also exactly why H1 matters more now, not less:
the flag has been used in anger, on a live page, and the next person to reach for it gets no
warning if they point it somewhere healthy.

The general point stands for the next occurrence: a tick records *that* something was verified,
never *what against*, and for a whole afternoon the verified claim and the artifact disagreed.

**(b) The repair is conditional on the fragment not changing.** The subtraction matches rule text
exactly. I edited one declaration — `outline-offset:1px` → `2px`, the kind of change
`gen-backlog-page.py:1480` invites — and re-ran it:

```
today                      -> region 1383 bytes, trio removed: True
after ONE declaration edit -> region 1457 bytes, #tray #qbox:focus STILL FROZEN
```

**(c) The frozen copy wins.** It sits after the fragment's copy at equal specificity, so once the
window closes, editing `gen-backlog-page.py:1480` has no effect on the rendered page — silently.

So the repair depended on somebody recomposing that page *before* anybody edited that generator, and
nothing anywhere knew either fact. **It happened to be recomposed in time.** That is luck, not a
mechanism — and the same race is now the standing condition for every page that meets the
precondition again. **This is the cost you took on by removing the permanent transform** (see Q2),
and it is the one part of the trade that has not been paid for.

---

## MEDIUM

### M1 — Partial subtraction on the scan path still drops genuine tray rules

Unchanged from r1 and re-measured at `03dfc75a` against the real `goals.html` tray, with a fragment
duplicating three of its rules:

```
genuine tray rules dropped: ['.askbtn', '#tray', '#qbox']
```

`subtracted or keep` guards only the endpoint where *everything* would be subtracted. The middle of
the continuum yields a partial tray, `css` non-empty, no refusal. The three dropped rules are the
container, the textarea and the ask button — the tray's load-bearing three. Still latent (it needs a
byte-identical duplicate), still the only branch with no floor under it.

### M2 — `_report_line` is real defence, but it models only HALF the consumer's parse

**It is not ceremony — I checked.** Changing the format to `❌` takes the suite to 114/115, and the
case calls the function rather than pattern-matching source text, which is what defeated the
abandoned pre-flight. Good.

But the consumer at `check-plan-code.py:986-987` is:

```python
fails = [l.strip()[7:].rsplit(": got ", 1)[0].strip()
         for l in out.split("\n") if l.strip().startswith("[FAIL] ")]
```

and the case asserts only `_report_line("a case", False).strip()[7:] == "a case"`. The
`.rsplit(": got ", 1)[0]` clause is not modelled:

```
name='the width: got the wrong value'
   case model -> 'the width: got the wrong value'
   REAL parse -> 'the width'      *** TRUNCATED — expect could never match ***
```

A case name containing `": got "` is silently truncated by the consumer, so its manifest entry
becomes unattributable — **the exact disease §22 exists for, inside the guard written to prevent
it.** 0 of the 118 live case names contain it, so this is latent.

§22 asks for *"the consumer's own parser over the producer's real output, copied verbatim rather
than reimplemented"*, and this is a re-typed partial copy — the *second implementation drifts*
failure, already drifted on day one. *Fix:* extract those two lines into a named function in
`check-plan-code.py` and have both `run_mutations` and this case call it. That also fixes L1.

---

## LOW

### L1 — `check-plan-code.attribute` does not exist

Named as the consumer in `brief-compose.py:919` and in `check-plan-code.py:1062` and `:2159`.
`grep -n "def attribute" scripts/check-plan-code.py` returns nothing; the parse is inline at
`:986-987`. A reader sent to a function that is not there. Extracting it (M2) makes the name true.

### L2 — Two manifest entries have identical kill sets

Running all 14 entries, every `expect` resolves to exactly one red case and there are no survivors
and no missing anchors. But two entries produce a byte-identical set of 8 red cases:

- `compose stops writing the end marker, so the tray boundary is inferred again`
- `the marked region is re-derived by scanning instead of taken verbatim`

They are different clauses with different real-world failures (*the marker is not written* vs *the
marker is not honoured*), so neither is an equivalent mutant in the strict sense — but **no case in
the suite distinguishes them**, which is what an identical kill set means. One case asserting
`TRAY_END in compose(...)` directly would separate them and make the second entry's coverage real.

### L3 — The END-marker anchor is over-specified, and it orphaned during this review

The entry's anchor spans two lines:

```
'    begin, marked_end = style.rfind(TRAY_BEGIN), style.rfind(TRAY_END)\n    if begin >= 0 and marked_end > begin:'
```

The second line is identical in `FROM` and `TO` — it is not being mutated, only pinned. When
`--remigrate` added `not remigrate and` to that `if`, the anchor stopped matching and the entry went
**orphaned**; I caught it in my snapshot, and you have since re-coupled it to the new text. It will
break again on the next edit to that line. This is the repo's own *"a refactor ORPHANS the mutation
guarding it"* lesson, live. Anchor on the `rfind` line alone.

---

## ANSWERS TO THE SIX QUESTIONS

**Q1 — text subtraction idempotent in every case?** No. See B1: three constructed shapes, one of
which fabricates a rule. It *is* idempotent from generation 2 (measured, 5-generation chain), so the
damage is one-shot. Closed by the `03dfc75a` fix.

**Q2 — is subtraction on the MARKER path justified? Argue the other side.**

The honest case **for** keeping it, which is stronger than it looks:

1. **It self-heals.** Any page polluted by any past *or future* wrong migration is repaired on its
   next recompose, with nobody needing to know. `--remigrate` requires an operator who knows.
2. **The condition is not a one-off.** A fragment declaring `#tray …` is deliberate and permanent
   (`gen-backlog-page.py:1480`), so pages keep meeting the precondition that produced the pollution.
3. **The population is not actually bounded.** I argued in r1 that the damage was one page. That was
   true of *that* migration. It is not a property of the design.

The case **against**, which wins:

4. Two independent Blockings, in two consecutive rounds, both caused by inferring over a region whose
   whole contract is *verbatim*. That is not bad luck; it is the shape telling you something.
5. The marker region contains only what `compose` wrote. Inference there has no input it does not
   already have exactly.

**You are right and I was right, and the reason is (1): the transform's real virtue was that it
needed no trigger, and removing it means you now owe a trigger.** `--remigrate` is the correct
mechanism; it is currently a mechanism with nothing pointing at it (H2) and no safety catch (H1).
Add the detector and the trade is strictly better than the transform ever was.

**Q3 — the new cases: do they reach their branch?** Yes. I instrumented `extract_tray` and ran the
full suite:

```
=== extract_tray: path x fragment-declares-tray-rules ===
   MARKER  no-own : 4      scan  no-own : 9
   MARKER  own    : 2      scan  own    : 3
```

`MARKER × own` was **0** in r1 and is now **2** — the population hole that let r1's Blocking through
is closed. The production edit for each new case, verified by running it: reinstating the parsed-list
rebuild reddens `the marked region is re-derived by scanning instead of taken verbatim`; dropping
`--remigrate` from `main` reddens `main --remigrate re-derives the region…`; `❌` in the printer
reddens `the failure line is exactly what check-plan-code parses`. All bite.

**Q4 — 14 entries: equivalent mutants? arbitrary expects?** No survivors, no missing anchors in the
live repo, and **every `expect` resolves to exactly one red case**. One identical-kill-set pair (L2).
One transient orphan (L3).

**Q5 — `_report_line`: defence or ceremony?** Defence — mutating the format takes the suite to
114/115. Half-modelled (M2).

**Q6 — what you still did not measure.**

1. **The artifact.** Every check of the repair was of a computed result; for the whole afternoon the
   verified claim and the file on disk disagreed. The page was recomposed at 17:03 and is now clean
   — but that closed by action taken, not by the verification, which would have read the same either
   way.
2. **The repair's expiry.** That it depends on the fragment declaring byte-identical rules, and that
   one edit to `gen-backlog-page.py:1480` closes the window permanently and silently, is not measured
   anywhere and not written down.
3. **`--remigrate` on a page that does not need it.** It was measured on the one page it repairs.
   The interesting run is the other one.
4. **The consumer's parse, in full.** M2 — the half-clause you did not copy is the one that bites.

The through-line: **three of these four are the same omission — measuring the thing you built rather
than the thing it acts on.** r1's version of this answer was *"the fix was measured on fixtures, not
on the corpus it exists for."* It is the same sentence one level up: the fix is now measured on the
case that needs it, but not on the case that does not, and not on the artifact it is supposed to
change.

---

## VERDICT

**NOT CONVERGED.**

**The single most important thing to fix: give the repair a trigger** — a check that a marked region
contains a rule the page's own fragment also declares. It is cheap, it has no false-positive class
(both sets are already computed), and it closes the remaining findings at once: it fires before the
repair window closes (H2b/c), and it is exactly the precondition `--remigrate` should refuse without
(H1). Without it, removing the permanent transform traded a defect you could see for one you cannot.

⚠ `backlog-table.html` was repaired at 17:03, mid-review, so the one page that needed it is clean —
but it was repaired by someone who already knew. The trigger is what makes that repeatable.

The Blocking is fixed and the fix is verified. `MARKER × own` went from 0 to 2 executions, all 14
mutation entries attribute, and `_report_line` is real. The remaining work is not in the transform —
it is that nothing in the system knows a page needs repairing.

**Stop-condition counter: 2.** Round 1's fix produced round 2's Blocking, and round 2's fix produced
H1 (`--remigrate`'s missing guard) — two consecutive rounds of fix-induced findings, which is the
documented trigger. **I do not think it should fire, and here is the test applied rather than the
symptom list:** *can a redesign remove them?* No. Both are **branch-coverage** defects in a design
that is now demonstrably right — the marker region is verbatim, inference is confined to the legacy
scan and to an explicit opt-in flag. A different shape would not dissolve H1; it would still need to
decide when repair is warranted. The remedy is a guard and a trigger, not a design review.

*Override falsifier, per `review-method.md`:* this fires to REDESIGN if round 3 produces a fix-induced
finding in `extract_tray`'s path selection that is a **mechanism** defect — e.g. if the detector
cannot be written without re-introducing inference into the marker region.

⚠ Pinned to `scripts/brief-compose.py` md5 `03dfc75a2fba03b1ca1b4e505d15b905` and
`scripts/mutations/brief-compose.json` md5 `bb82a48fc86125b4c4299ee9092c6a84`. The file changed four
times during this review; `03dfc75a` is the live working tree as I write, and every ATTACK-section
measurement was taken against a scratch snapshot of it.
