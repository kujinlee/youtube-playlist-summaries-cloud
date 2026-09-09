# Round 1, Claude half — is the mutation check's GREEN verdict FAITHFUL?

Subject: merged `master` of
`/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud`
Reviewer: Claude adversarial half. Everything below is EXECUTED unless labelled UNVERIFIED.

**VERDICT — the green is faithful for what it claims, and narrower than a reader will assume.**
All 23 entries are caught via the mechanism their `expect` names; I reproduced every one by hand
and none is credited by a sibling case. No Blocking. **1 High, 5 Medium, 2 Low** — every one of
them is a rule with *no* manifest entry, not an entry that mismeasures.

---

## PROOF OF SUBJECT (raw output, run first)

```
$ git rev-parse HEAD
3afe62c095a6ec0bab0bdc12e8f73beca0e37512

$ git log --oneline -3
3afe62c0 Retire plan mode — delete the unreachable code (PR 2 of 2) (#271)
4ec7e82a Retire plan mode — refuse the entry points, fence the hole they leave (PR 1 of 2) (#270)
307423f1 Backlog #91 — the coverage verdict becomes a type you cannot read wrongly (#269)

$ git diff --stat 307423f1..HEAD -- scripts/
 scripts/check-plan-code.py                  | 2008 ++++-----------------------
 scripts/check-plan-file-tags.py             |  649 +++++++++
 scripts/check-selftest-counts.py            |    3 +
 scripts/mutations/check-plan-code.json      |  252 +---
 scripts/mutations/check-plan-file-tags.json |  244 ++++
 5 files changed, 1158 insertions(+), 1998 deletions(-)
```

HEAD is `3afe62c0…`; the top two log entries are PR #271 then PR #270. **Matches the brief.**
`docs/reviews/` was not read. Nothing under `docs/` was written. At the end of the review
`git status --porcelain` showed only the *other* half's `docs/reviews/verdicts/…-codex.verdict.json`
— no write of mine, and HEAD unmoved at `3afe62c0…`.

---

## METHOD — what I actually ran

I did not trust `--mutate .`'s own tally. I rebuilt the experiment so I could see, per entry,
*which cases go red*:

1. Staged a copy of `HARNESS_TREE` (`scripts`, `supabase`, `docs`, `node_modules/typescript`)
   into a scratch directory. **The repo's own files were never mutated** (confirmed clean above).
2. Control, run exactly as `run_suite` does (`cwd=stage`, `HOME=stage/.home`):

```
$ cd $STAGE && HOME=$STAGE/.home python3 scripts/check-plan-code.py --self-test
rc=0
78/78 passed
```

3. Per entry: apply its edits to the staged `scripts/check-plan-code.py`, re-run the suite, parse
   the `[FAIL]` lines with the harness's own parser, restore the file. Anchor uniqueness was
   re-checked by my driver independently of the harness — all 23 anchors matched exactly once.
4. Independently re-ran the whole thing end to end:

```
$ cd $STAGE && HOME=$STAGE/.home python3 scripts/check-plan-code.py --mutate .
rc=0
OK — delivered scripts mutated: 33 file(s), 371 mutation(s), 0 survivor(s)
```

5. Cross-check of the counts (three independent statements agree):
   `EXPECTED_MUTATIONS` sum = **371**; manifest entries across 33 files = **371**;
   keys-only-in-one = none; disagreeing per-file counts = none.

Artifacts (scratchpad, not the repo): `drive.py`, `drive-out.txt`, `probe.py`/`probe2.py`/`probe3.py`
and their `-out.txt`, `mutate-full.txt`.

---

## RESULT 1 — all 23 entries reproduce, and every `expect` resolves to exactly one red case

| # | entry | red cases | `expect` → matches | faithful? |
|---|---|---|---|---|
| 0 | a timeout is reported as a plain failure | 1 | 1 | ✅ |
| 1 | a cannot-run is credited as a catch | 2 | 1, 1 (list) | ✅ |
| 2 | an ambiguous anchor is tolerated | 1 | 1 | ✅ |
| 3 | a missing anchor is tolerated | 3 | 1 | ✅ |
| 4 | a mid-line FAIL marker is parsed as a case name | 2 | 1 | ✅ |
| 5 | coverage may shrink silently | 1 | 1 | ✅ |
| 6 | the control BEFORE the sequence is not checked | 2 | 1 | ✅ |
| 7 | the control AFTER the sequence is not checked | 4 | 1 | ✅ |
| 8 | an empty expect list disables the check | 1 | 1 | ✅ |
| 9 | a repeated edit anchor measures nothing twice | 1 | 1 | ✅ |
| 10 | an absent docstring count is silent instead of CANNOT RUN | 1 | 1 | ✅ |
| 11 | count_drift stops reporting a mismatch | 4 | 1 | ✅ |
| 12 | the spawned suite is handed the real HOME again | 3 | 1 | ✅ |
| 13 | a home-escape route in the TARGET is ignored | 1 | 1 | ✅ |
| 14 | a home-escape route in the MUTATION text is ignored | 1 | 1 | ✅ |
| 15 | the exemption marker needs no written reason | 1 | 1 | ✅ |
| 16 | any nonzero exit is credited as a catch | 2 | 1 | ✅ |
| 17 | the exemption marker is taken from any token | 1 | 1 | ✅ |
| 18 | an exemption also covers executable routes | 1 | 1 | ✅ |
| 19 | unparseable source is passed instead of scanned raw | 1 | 1 | ✅ |
| 20 | the after-control stops invalidating the run | 3 | 1 | ✅ |
| 21 | the --mutate REFUSAL leaks a survivor count (r4 B1) | 3 | 1 | ✅ |
| 22 | a control is called green on its EXIT CODE alone (r4 M1) | 2 | 1 | ✅ |

No entry is a case-existence measurement in disguise: in every one, the named case's *assertion*
is broken by the *specific* thing the edit removes. I checked each by hand, e.g.:

- **#2 (ambiguous anchor)** — the fixture anchor `"return 1"` genuinely occurs **twice** in `m.py`
  (`f`'s body and `_self_test`'s failure branch). With `> 99`, the first is replaced, the suite goes
  red normally, `_ok4` becomes `True`, and the case asserting `(False, True)` fails. The case
  distinguishes; it is not merely present.
- **#3 (missing anchor)** — with `and False` the replace is a no-op, the suite stays green, so the
  report says `mutation SURVIVED` instead of `anchor NOT FOUND`. Direct.
- **#11 (count_drift)** — the `!=`→`==` inversion makes 4 cases red, but the named one
  (`count_drift reports a mismatch`) is red because `count_drift` returns `None` on a genuine
  mismatch. Direct, not collateral.

---

## (a) The five entries repaired on 2026-09-09 — all sound, and the mid-line offset is CORRECT

`an ambiguous anchor is tolerated`, `a missing anchor is tolerated`,
`a mid-line FAIL marker is parsed as a case name`, `an empty expect list disables the check`,
`a cannot-run is credited as a catch`. All five reproduce (rows 1–4 and 8 above), and each named
case is red under **its own entry only** among the 23.

**The mid-line offset — COMPUTED by running both readers, not by reading the code:**

```
fixture line   : '> note: mid-line [FAIL] marker'          (check-plan-code.py:1410)
ORIGINAL reader: []                       -> expect matches: 0
MUTATED  reader: ['mid-line [FAIL] marker'] -> expect matches: 1
offset check   : prefix '> note:' is 7 chars; [7:] lands on ' mid-line [FAIL] marker'
VERDICT: falsifiable == True
```

The `[7:]` slice plus the trailing `.strip()` yields exactly the `expect` string under the mutated
reader and nothing under the original. **The entry that shipped unfalsifiable in its first draft is
falsifiable now.** (I also probed `[7:]`→`[6:]`, which *survived* — but that is a **no-op**, not a
gap: `.strip()` absorbs the extra leading space. `[5:]` is the real weakening and **is** caught.
My probe was the error, not the code.)

## (b) Entry 1's LIST expect — legitimate, and not masking

`"a cannot-run is credited as a catch"` names two cases. Under the mutation (`rc == 2` → `rc == 99`)
a timed-out run falls through to `caught = rc == 1`, so:

- `a TIMED-OUT mutation is counted but is NOT a verdict` (`:1685`) goes red because the entry is now
  recorded `measured: True`, so `Measured` **constructs** and `isinstance(_ev8, Measured)` flips
  `False`→`True`. This is the *verdict-type* half.
- `...and it is reported as a cannot-run, not as a catch` (`:1688`) goes red because the report now
  says `mutation SURVIVED` instead of `did NOT COMPLETE`. This is the *report-text* half.

They measure genuinely different consequences of one edit. **Either alone would suffice** to catch
it, so the list is documentation of both consequences rather than a crutch — the honest form the
`run_mutations` comment at `:951-953` describes. Not masking.

## (c) The four KEPT helpers — three still covered, one is half-dead

| helper | still covered? | evidence |
|---|---|---|
| `control_is_green` (`:288`) | **Yes, and robustly.** | Entry 22 kills it by deletion; I also probed a *weakening* (`and`→`or`) — **CAUGHT**, red via the same case. |
| `run_suite` (`:367`) | **Partly.** | Entry 0 pins the timeout rc; entry 12 pins the `child_env` wiring (and I confirmed the canary lands in the staged home, never the real one). Dropping stderr from the captured output **survives** → F7. |
| `run_mutations` (`:866`) | **Heavily, with two holes.** | 6 of the 23 entries land here. But the `==`-not-substring rule (F1) and the `rsplit(": got ")` rule (F2) both **survive**. |
| `not_measured_line` (`:306`) | **Call site only; the body is half-dead.** | Entry 21 mutates the *print site* at `:2000`. The function's own `subject` clause is unreachable → F4. |

## (d) Did the deletion orphan any OTHER guard's only red case? — **No. Answered by a search and a run.**

Two independent answers, neither from recollection:

1. **Structural bound.** `run_mutations` runs `run_suite(d, fname)` — *only the mutated file's own
   suite* (`:914`). So an entry in `scripts/mutations/<X>.json` can only ever be killed by `X`'s
   own `--self-test`. Plan mode lived in `check-plan-code.py`, so the orphaning class is bounded to
   `check-plan-code.json` by construction. It cannot reach the other 32 manifests.
2. **Measured.** My independent `--mutate .` is `33 file(s), 371 mutation(s), 0 survivor(s)`, rc=0.
   Any orphaned entry anywhere in the 33 would appear there as a survivor.

Residue search: `grep -rn "verify_evidence\|compare_delivered\|pasted_evidence\|unsafe_tag\|def evidence\|extract("`
over `scripts/` and `.github/` finds no live reference to a deleted symbol. The 10 hits are all
**prose in `check-plan-file-tags.py` comments** recounting how its fence rule was calibrated against
`extract()` before that parser was deleted — historically true, and correctly labelled as history.

**So five was the whole class, and CI found all five.** That is a good result for the arming
condition, not luck: the per-file suite boundary is what makes it exhaustive.

---

# FINDINGS

## F1 — HIGH: the rule that makes every other `expect` meaningful has no falsifier

`scripts/check-plan-code.py:975`

```python
unnamed = [(w, [f for f in fails if w == f]) for w in wants]
```

The comment directly above (`:955-960`) records this as a defect measured and fixed in round 6:
*"The round-5 rule was CARDINALITY-ONLY… an `expect` naming a completely unrelated case, or a mere
fragment of a name, still certified the mutation… only equality says that."*

**OBSERVATION THAT MAKES IT FAIL:** revert `==` to `in`. The suite stays at **78/78, rc=0**, and no
manifest entry targets this line.

Consequence, demonstrated by running both variants of `run_mutations` over one fixture whose real
case name is `f returns one` and an `expect` of the mere fragment `returns one`:

```
DELIVERED (equality):  ok=False   -> REFUSES the entry
      report: mutation 'f returns two': `expect` 'returns one' matched 0 red case(s)
              — it was caught by something else: ['f returns one'] …
P5-MUTANT (substring):  ok=True   -> ACCEPTS the entry
```

**Why High.** This is the single line that converts *"the suite went red"* into *"the suite went red
via the case it names"* — for all 371 mutations in all 33 manifests. If it silently reverted, every
entry in the project could be credited by a sibling case and nothing would notice; the recorded
round-5 M1 defect (`expect: "does NOT count"` matching 7 case names) would be live again. It is
**not Blocking**: the rule is intact on this commit and I verified all 23 entries resolve by
equality. What is missing is the *protection*, on the file whose entire purpose is to notice exactly
this.

**Fix shape:** a manifest entry mutating `w == f` → `w in f`, red via a new case that hands
`run_mutations` an `expect` which is a strict substring of a real case name and asserts refusal.

## F2 — MEDIUM: the colon-in-case-name rule is unfalsifiable — no fixture name contains a colon

`scripts/check-plan-code.py:923-924`

```python
fails = [l.strip()[7:].rsplit(": got ", 1)[0].strip()
         for l in out.split("\n") if l.strip().startswith("[FAIL] ")]
```

`:916-919` states the bought lesson: *"split on the LAST ': got ', not the first ':'. A case name may
contain a colon ("collect: a missing git is a could-not-tell"), and splitting on the first one
truncated it to 'collect'."*

**OBSERVATION:** replace `.rsplit(": got ", 1)[0]` with `.split(":", 1)[0]`. **Survives at 78/78.**

**Cause — the project's own recorded shape.** Every case name that reaches this parser in the
fixtures is colon-free: `f returns one`, `value is one`, `mid-line [FAIL] marker`,
`the tree went bad underneath`. With no colon the two splitters agree by construction, so the case
cannot fail via the mechanism it is named after. Computed:

```
"collect: a missing git is a could-not-tell: got 1 want 2"
  rsplit(': got ') -> 'collect: a missing git is a could-not-tell'
  split(':')       -> 'collect'
```

**Fix shape:** give one fixture suite a case name containing a colon, and an `expect` naming it in
full. One character of fixture change closes it.

## F3 — MEDIUM: `EXPECTED_MUTATIONS` is a floor in the GROWTH direction

`scripts/check-plan-code.py:768` (`if got != want:`), rule stated at `:382-384`:
*"EXACT, not a floor: adding a mutation should also be a visible act."*

Entry 5 (`coverage may shrink silently`) mutates `!=` → `>`, which pins the **shrink** direction only.

**OBSERVATION:** replace `!=` with `<`. **Survives at 78/78.** Under that edit a manifest may GROW
silently — an entry added without updating `EXPECTED_MUTATIONS` passes.

**The obvious backstop does not backstop it.** `case("the declared counts are the real ones",
sum(EXPECTED_MUTATIONS.values()), 371)` at `:1857` compares the constant against a literal;
`EXPECTED_MUTATIONS` is *untouched* in this scenario, so the sum still matches. Likewise
`sorted(EXPECTED_MUTATIONS)` at `:1704` pins the key list, which also does not move.

**Fix shape:** a mutation `!=` → `<` with a case that grows a fixture manifest and asserts refusal —
the exact mirror of entry 5's shrink case, which already exists at `:1510` and can be copied.

## F4 — MEDIUM: `not_measured_line`'s `subject` parameter is dead, and its docstring is now false

`scripts/check-plan-code.py:306-333`, sole caller at `:2000`.

```
$ grep -rn "not_measured_line" scripts/*.py
scripts/check-plan-code.py:306:def not_measured_line(nm: NotMeasured, subject: str = "") -> str:
scripts/check-plan-code.py:2000:            print(not_measured_line(verdict))
```

(the three other hits are comment prose). **One caller, and it passes no `subject`.**

**OBSERVATION:** drop `{subject}` from the returned f-string. **Survives at 78/78.**

The docstring still asserts, on this commit:
- *"THREE consumers need it — the `--mutate` printer, the plan-mode printer, and the evidence block"* — two of the three were deleted in PR #271.
- *"two of the three callers pass none, and the third passes `f"{mode}: "`, derived from the command-line flags"* — no caller passes a subject at all.

This is the *inverse* of the orphaned-mutation class the file documents so carefully: not a mutation
whose case died, but a **parameter whose producers died**, leaving a knob no input can turn. The
deletion slice retired 21 entries by anchor location, which correctly caught the mutations — it did
not catch this, because `not_measured_line` was *kept* while its callers went.

**Fix shape:** delete the parameter (and the paragraph describing it), or state in one line that it
is retained for a named future caller. Prefer deletion — an unreachable parameter is a mechanism
with no producer, which is what `check-producer-enumeration.py` exists to notice.

## F5 — MEDIUM: three refusals with neither a case nor a mutation

All three measured as **surviving at 78/78**:

1. **`:703-707` — the duplicate mutation NAME refusal.** Disabling `if nm in seen_names:` survives.
   Entry 9 covers the duplicate *ANCHORS* rule at `:708`, which is a **different** rule: two entries
   can share a `name` while differing in anchors, and the comment at `:696-701` says the name rule
   was bought by a reproduced Codex finding (*"entry 32 swapped for a duplicate of entry 1, still
   green"*). The rule that finding bought is the unguarded one.
2. **`:688-690` — the `json.JSONDecodeError` refusal.** No case ever hands `load_manifests` malformed
   JSON, so swallowing the error survives. The four sibling refusals (`file` disagreement, empty
   manifest, missing target, no manifests at all) each have a case at `:1439-1453`; this one does not.
3. **`:771-773` — the "manifest with no declared count" drift branch.** Disabling
   `for target in sorted(set(counts) - set(EXPECTED_MUTATIONS)):` survives. Nothing else catches a
   NEW manifest file shipped without an `EXPECTED_MUTATIONS` entry (see F3 for why the two
   count-pinning cases do not).

## F6 — MEDIUM: the home-escape TARGET scan is only ever driven with ONE target

`scripts/check-plan-code.py:776` — `for target in sorted(counts):`

**OBSERVATION:** change it to `sorted(counts)[:1]`. **Survives at 78/78.**

Every fixture root built by `_mini` (`:1459`) contains exactly one manifest target
(`scripts/thing.py`), so the loop's *iteration over all targets* is unfalsifiable by construction —
the single-target fixture makes `[:1]` an identity. In the real run there are **33** targets; under
that edit 32 would go unscanned for home-escape routes and `--mutate .` would still print
`0 survivor(s)`. Entry 13 proves `home_escapes` is **called**; nothing proves it is called for more
than the first target.

This is the same class as the `all(t > num for t in owners)` finding recorded at `:551-552` — *"every
fixture symbol had exactly ONE producer, and with one owner `all`/`any` agree"*. Here every fixture
root has exactly one target, so `[:1]` and the full loop agree.

**Fix shape:** a `_mini` variant with two manifest targets, one of them carrying the escape route,
asserting the report names the *second*.

## F7 — LOW: `run_suite` can drop stderr unnoticed

`scripts/check-plan-code.py:377` — `return r.returncode, (r.stdout + r.stderr).strip()`.
Replacing it with `r.stdout.strip()` **survives at 78/78**. Impact is diagnostic quality only:
`control_is_green` needs `"passed"` on stdout, and `[FAIL]` lines are stdout too — but the
`out[-400:]` tails printed inside every `CANNOT RUN` message would silently lose the traceback that
explains *why* a control went red. Worth a line of comment or a case; not urgent.

## F8 — LOW: `count_drift`'s regex anchor is loose and unpinned

`scripts/check-plan-code.py:1007` — `re.search(r"--self-test\s+#\s*(\d+) cases", doc or "")`.
Widening it to `r"(\d+) cases"` **survives at 78/78**. The narrow anchor exists so that a stray
"N cases" elsewhere in a 65-line docstring cannot be mistaken for the declaration; nothing holds it
there. Entries 10 and 11 pin the *absent-count* and *mismatch* branches, not the anchor.

---

# NON-FINDINGS — hypotheses I tested and refuted

Recorded so the next round does not spend a pass re-deriving them.

**N1 — Entry 6's dependence on the word "control". Fails safe, not a false green.**
Entry 6's named case is `(_ok2, any("control" in r.lower() for r in _rep2)) == (False, True)`
(`:1502`). Under the mutation the run is *still* `ok=False` — via the **after**-control — so the
whole discrimination rests on the after-control message at `:846-849` **not** containing the word
"control". I tested that coupling: rewording it to `"the after-control run of {name} is no longer
green"` does turn entry 6's named case green. **But** (i) the same reword turns
`a tree that goes bad DURING the sequence invalidates the run` red, because that case asserts the
literal `"no longer green AFTER the sequence"` — so the wording is independently pinned; and
(ii) even if it were not, `--mutate .` would report entry 6 as `matched 0 red case(s)` and **refuse**,
which is loud. Fragile-looking, structurally safe.

**N2 — The `[7:]` FAIL-parser offset. Adequately pinned; my probe was the error.**
`[7:]`→`[6:]` survives, but computing the parser shows `[6:]` is a **no-op** — the trailing
`.strip()` absorbs the leading space (`[5:]`→`'] value is one'`, `[6:]`→`'value is one'`,
`[7:]`→`'value is one'`, `[8:]`→`'alue is one'`). `[5:]` is a genuine weakening and **is CAUGHT**.

**N3 — `USERPROFILE` (`:146`).** Dropping it survives on macOS by construction — it is the Windows
concept and nothing on this platform reads it. Unkillable here; correctly excluded from the manifest,
the `check-storage-grant-pin` case-5 shape the file already documents at `:461-465`.

**N4 — `ev_survivors.append(name)` in the `rc == 2` branch (`:938`).** Removing it survives. On that
path `measured: False` always makes `Measured` construction raise, so the verdict is `NotMeasured`
and `survivors` can never reach a printed tally (`:1985-2000`). Defensive, not decisive. Correctly
excluded.

**N5 — Entries 7 / 20 / 21 are a subsumption cluster, but they do distinguish.**
Entry 7 (`if not control_is_green(…)` → `if False`) is a superset of entry 20 (drop
`controls_green = False`), and both make entry 21's named case red. Measured overlap:

```
'--mutate mode refuses to print a tally it did not earn'                 red under 3 entries (7, 20, 21)
'...and it is NOT trustworthy, though every declared mutation ran'       red under 2 entries (7, 20)
```

This is **not** the brief's failure mode 4. Each entry's *own* named case is red because of the
*specific* thing that entry removes — entry 7's names the literal `"no longer green AFTER the
sequence"` report emitted only by the block it deletes; entry 20's names the `Measured`-vs-
`NotMeasured` flip that only the `controls_green` assignment causes; entry 21's names the
`"survivor(s)"` token only its own edit introduces. No `expect` string is duplicated across entries.

---

# SUMMARY

**Is the green faithful?** Yes, for the claim it makes. All 23 entries are caught via the mechanism
their `expect` names, verified by execution rather than by reading; the arithmetic (371 = 371 = 371)
is consistent across three independent statements; the five 2026-09-09 repairs are sound and the
mid-line offset is correct when computed rather than read; and the plan-mode deletion orphaned
nothing beyond the five CI caught — which is a *structural* result (per-file suite boundary), not
luck.

**What the green does not mean.** Eight rules in this file have no entry and no case, and each was
bought with a review round or a recorded defect. The sharpest is F1: the `==`-not-`in` rule at
`:975` is the one line on which the faithfulness of all 371 verdicts rests, and it is the one line
nothing measures. The file's own docstring is honest that *"the mutation list is complete"* is not
something it can prove (`:50-54`) — these findings say where that gap currently sits.

| ID | Severity | One line |
|---|---|---|
| F1 | **High** | `expect` must EQUAL a case name (`:975`) — no entry; reverting to substring survives 78/78, and I showed it then accepts a fragment `expect` |
| F2 | Medium | `rsplit(": got ")` (`:923`) unfalsifiable — no fixture case name contains a colon |
| F3 | Medium | `EXPECTED_MUTATIONS` growth direction (`:768`) unguarded; the two count cases do not backstop it |
| F4 | Medium | `not_measured_line`'s `subject` (`:306`) is dead and its docstring names three callers that no longer exist |
| F5 | Medium | Three refusals unguarded: duplicate NAME (`:703`), malformed JSON (`:688`), undeclared-target drift (`:771`) |
| F6 | Medium | Home-escape target loop (`:776`) driven only with ONE target, so `[:1]` is an identity |
| F7 | Low | `run_suite` (`:377`) can drop stderr unnoticed — diagnostics only |
| F8 | Low | `count_drift`'s `--self-test` regex anchor (`:1007`) can be widened unnoticed |

**Recommendation.** F1 is worth an entry before the next slice touches this file — it is cheap (one
mutation plus one case handing `run_mutations` a fragment `expect`) and it protects every other
verdict in the project. F2 is cheaper still (one colon in one fixture name). F3–F6 are ordinary
manifest debt of the kind this project already tracks and pays down. F4 is a five-line deletion.
Nothing here blocks the merged commit.

---

# ADDENDUM — adjudicating the coordinator's entry-11 lead

*Note on the file: sections (a)–(d), F1–F8, the non-findings and the summary above were written at
09:13 and were already complete when this lead arrived. Nothing above has been altered; this section
is additive.*

## The lead: is `count_drift stops reporting a mismatch` broader than the property it names?

**AGREED — and the case is stronger than the one put to me. Rating: Low (two of them, F9 and F10).**
I re-measured on my own staged copy rather than accepting the numbers, and added a third arm the
lead did not run.

`scripts/mutations/check-plan-code.json` entry 11 edits `scripts/check-plan-code.py:1010`:

```python
    if int(m.group(1)) != actual:          # shipped edit rewrites `!=` to `==`
```

```
SHIPPED  (!= -> ==, an INVERSION)              rc=1, 4 red:
    - count_drift is silent when the docstring matches      <- the OPPOSITE property
    - count_drift reports a mismatch                        <- the NAMED case
    - _drift_rc returns 1 when the docstring count has drifted
    - _drift_rc returns 0 when it matches and nothing failed

NARROW   (!= actual and False, disable only)   rc=1, 2 red:
    - count_drift reports a mismatch                        <- the NAMED case still fires
    - _drift_rc returns 1 when the docstring count has drifted

CONTROL  (break ONLY the match branch:                      rc=1, 2 red:
          `return None` -> `return "[DRIFT] spurious"`)
    - count_drift is silent when the docstring matches
    - _drift_rc returns 0 when it matches and nothing failed
    named case 'count_drift reports a mismatch' fires: False
```

The first two arms reproduce the lead's measurement exactly. **The third arm is what settles it:**
`count_drift`'s two directions are *independently breakable*, each with its own pair of cases, and
breaking the match branch alone does **not** fire the named case. So this is not one property with
four symptoms — it is **two separable properties**, and the shipped inversion breaks both under a
name that claims one.

The anchor for the narrow variant is unique (`src.count(...) == 1`, verified), so the weaker edit is
a drop-in.

**The rule is written practice here, not my import.** `docs/dashboard-entries.md:4297` records a past
slice shipping *"five mutations, each the weakest edit that reddens exactly one case, verified on a
temp copy"*, and `:5486` records an entry being *"retargeted to the faithful weakest edit"*. Entry 11
reddens four.

**The counter-argument, stated so it is weighed rather than skipped.** Classical mutation testing
prefers operator replacement (`!=`→`==`) precisely because it models a plausible typo, where
`and False` models nothing anyone would write. That is a real argument for the inversion and it is
why this is **Low, not Medium**: the entry's attribution is *correct* — the named case is red because
the mismatch branch genuinely stopped reporting — and the harness's contract ("red via the case it
NAMES") holds. What is lost is precision of evidence and honesty of the entry's name.

## F9 — LOW: entry 11's edit is an inversion, so its name describes half of what it does

`scripts/mutations/check-plan-code.json` entry 11 · `scripts/check-plan-code.py:1010`

**OBSERVATION that makes it fail:** the strictly weaker edit `!= actual` → `!= actual and False`
fires the same named case while reddening 2 cases instead of 4 (measured above). Under the shipped
inversion you cannot tell from the red set whether the named case is bound to the *mismatch* branch
or merely to `count_drift` being broken at all; under the narrow edit you can.

**Fix shape:** retarget the entry to `!= actual and False`, or rename it to say it inverts
(e.g. *"count_drift's comparison is inverted — it reports a match and hides a mismatch"*). Prefer the
retarget: it makes the entry mean what its name says and leaves the match branch intact for F10.

## F10 — LOW: the match-direction property has no named owner, and is covered by accident

`scripts/check-plan-code.py:1010-1012`

`count_drift is silent when the docstring matches` (`:1229`) guards a **fail-noisy** defect: a
`count_drift` that returned a `[DRIFT]` string on a *matching* count would make `_drift_rc` return 1
and turn every green `--self-test` in the project red. My control arm shows that branch is
independently breakable — and **no manifest entry names it**. It is red under entry 11 only as a
side effect of the inversion.

So the manifest's accounting overstates itself: `EXPECTED_MUTATIONS["scripts/check-plan-code.py"] = 23`
reads as 23 named behaviours, but one entry silently carries two and one behaviour has no owner.
Anyone grepping the manifest to ask *"is the match branch mutation-covered?"* gets **no** — which is
the *"covered elsewhere"* claim this project distrusts on principle (`check-catalog-coverage.py`'s
whole reason for existing, per `check-plan-code.py:430-439`).

**Fix shape:** F9's retarget plus one new entry on the match branch (the control arm above is already
a working mutation), taking the count 23 → 24. That is coverage growing, which the ratchet permits.

## Is any OTHER entry broader than the property it names? — **No. One outlier, answered from the data.**

I classified all 23 edits by shape and cross-referenced the red-set sizes rather than judging by
impression. A "genuine inversion" is detected mechanically: the edit is exactly `find` with one
comparison operator replaced by its complement.

```
 # red shape                                        entry
 0   1 REWRITE                                      a timeout is reported as a plain failure
 1   2 NEUTRALISE via unreachable constant          a cannot-run is credited as a catch
 2   1 NEUTRALISE via unreachable constant          an ambiguous anchor is tolerated
 3   3 DISABLE via `and False` (explicit weakest)   a missing anchor is tolerated
 4   2 REWRITE                                      a mid-line FAIL marker is parsed as a case name
 5   1 REWRITE                                      coverage may shrink silently
 6   2 DISABLE via `if False:`                      the control BEFORE the sequence is not checked
 7   4 DISABLE via `if False:`                      the control AFTER the sequence is not checked
 8   1 DISABLE via `and False` (explicit weakest)   an empty expect list disables the check
 9   1 DISABLE via `and False` (explicit weakest)   a repeated edit anchor measures nothing twice
10   1 FAIL-OPEN return                             an absent docstring count is silent instead of …
11   4 ⚠ INVERT the predicate                       count_drift stops reporting a mismatch
12   3 REWRITE                                      the spawned suite is handed the real HOME again
13   1 NEUTRALISE via empty input                   a home-escape route in the TARGET is ignored
14   1 NEUTRALISE via empty input                   a home-escape route in the MUTATION text is ignored
15   1 REWRITE                                      the exemption marker needs no written reason
16   2 REWRITE                                      any nonzero exit is credited as a catch
17   1 REWRITE                                      the exemption marker is taken from any token, …
18   1 REWRITE                                      an exemption also covers executable routes
19   1 REWRITE                                      unparseable source is passed instead of scanned raw
20   3 DELETE (weakest: remove the line/clause)     the after-control stops invalidating the run, …
21   3 REWRITE                                      the --mutate REFUSAL leaks a survivor count (r4 B1)
22   2 DELETE (weakest: remove the line/clause)     a control is called green on its EXIT CODE alone

GENUINE PREDICATE INVERSIONS: [11]
entries whose red set is >2: [3, 7, 11, 12, 20, 21]
```

**Entry 11 is the only inversion.** The other five large red sets are all *one minimal edit with
several downstream consequences*, which is a different thing and in two cases a strength:

- **#3** (`and False`) — the explicit weakest form. Its 2 extra reds are the shortfall cases, which
  exist because that path *deliberately* uses absent anchors; disabling the refusal removes the skip,
  so the shortfall never forms. A consequence, not a broader edit.
- **#7** (`if False:`) — disables the whole after-control block, which is exactly what
  *"the control AFTER the sequence is not checked"* says. **Entry 20 is its narrow companion**
  (deleting only `controls_green = False`), so the pair is deliberately coarse-plus-fine, not
  redundant. See N5.
- **#12** — removing `env=child_env(d)` is the minimal edit for *"handed the real HOME again"*; the
  3 reds are the canary chain asserting one property in three steps.
- **#20** — deletes one line. Cannot be weaker.
- **#21** — restores the r4 B1 defect, and its 3 reds are the **three different refusal paths**
  (after-control, before-control, total shortfall) all proven by one edit. That is the shape you
  want: narrow edit, broad evidence.

## Revised finding tally

| ID | Severity | One line |
|---|---|---|
| F1 | **High** | `expect` must EQUAL a case name (`:975`) — no entry; reverting to substring survives 78/78 |
| F2–F6 | Medium | as above (`:923` colon rule, `:768` growth direction, `:306` dead `subject`, `:703`/`:688`/`:771` refusals, `:776` single-target loop) |
| F7–F8 | Low | `run_suite` stderr (`:377`); `count_drift` regex anchor (`:1007`) |
| **F9** | **Low** | entry 11's edit is the manifest's only predicate INVERSION; its name describes half of it, and a unique-anchor weaker edit fires the same case with 2 reds instead of 4 |
| **F10** | **Low** | `count_drift`'s match branch is independently breakable, has no named entry, and is covered only as a side effect of F9's inversion |

F9 and F10 are one change: retarget entry 11 to `and False`, add an entry for the match branch,
`EXPECTED_MUTATIONS` 23 → 24. Neither affects the merged commit's green.
