# closing-table — round 8 — independent Claude half (fix verification)

**Verdict: F2 fixed in behaviour, F4 CLOSED, F5 CLOSED — but the branch carries a BLOCKING defect
in its own mutation evidence and should not merge as it stands.** 1 Blocking, 1 Medium, 3 Low.

Subject: branch `fix/closing-table-r7-findings` (PR #327) — `0538027a`, `4f1a3b66` — on top of
`master` `365f8d75`. I read the diff myself (`git diff master...fix/closing-table-r7-findings`).
Out of scope, already filed with r7's measurements: #145 (F1), #148, #149 (F3+F7), #151 (F6).

Constraints honoured: read-only git; every experiment in `mktemp -d`; this file is the only write
in the repo; `check-plan-code.py --mutate .` was **not** run against the working tree — I imported
`run_mutations` and ran only the three new entries against a copy.

⚠ Working-tree note for anyone replaying this: the tree is **checked out on the branch**, so
`scripts/check-closing-table.py` on disk is the FIXED file. `master`'s version has to come from
`git show master:…` — my first replay compared the fixed file with itself and produced two
identical columns before I caught it.

---

## R8-1 — Blocking — two of the three new mutation entries fail the harness: one SURVIVES, one is UNATTRIBUTABLE

Run through the **real** `run_mutations` from the branch's own `check-plan-code.py`, on a copy of
`scripts/` in a temp dir, with only the three new entries:

```
ok = False
survivors = ['the fold widens to a SUBSTRING match, so a person quoting the phrase has their turn swallowed']

REPORT: mutation SURVIVED — the fold widens to a SUBSTRING match …: the suite stayed green,
        so no case can fail for what it names
REPORT: mutation 'the self-test count stops being derived …': `expect` 'declared self-test count'
        matched 0 red case(s) — it was caught by something else:
        ['declared self-test count 132 != 0 — the docstring is the pinned declaration read by
          check-selftest-counts.py']. An expect must name EXACTLY ONE …

entry caught=True  attributed=True   the teammate-message fold is reverted …
entry caught=False attributed=False  the fold widens to a SUBSTRING match …
entry caught=True  attributed=False  the self-test count stops being derived …
```

`EXPECTED_MUTATIONS["scripts/check-closing-table.py"]` is 40 and the file holds 40, so the *count*
gate is satisfied; it is the **run** that is red. CI's `check-plan-code.py --mutate .` should be
failing on this branch right now.

### (a) `_INJECTED.match` → `_INJECTED.search` is an EQUIVALENT MUTANT

The pattern is `^`-anchored and compiled without `re.MULTILINE`, so `search` can only ever match at
position 0 — which is what `match` does. Measured directly:

| input | `.match` | `.search` |
|---|---|---|
| `why did Another Claude session sent a message appear?` | False | **False** |
| `Another Claude session sent a message: hi` | True | True |
| `  Another Claude session sent a message` | True | True |
| `x\nAnother Claude session sent a message` | False | **False** |

So the new case **`"coalesce: the phrase QUOTED mid-message is still a real turn"` has no mutation
that can kill it** — it is precisely the shape you asked me to hunt, arriving in the fix for the
review that named the shape. The case itself is *correct and worth keeping*; what is missing is any
demonstration that the behaviour it names is load-bearing.

Two repairs, either works:
* drop `^\s*` from `_INJECTED` and keep `.match` (the anchor is redundant under `match` except for
  leading whitespace, which `\s*` handles) — then `.match` → `.search` becomes a real mutation and
  the quoted-phrase case kills it; or
* retarget the entry to a mutation that does change behaviour. **Measured, two candidates, both
  kill via a named case:** truncating the phrase to `Another Claude session` → red via
  `coalesce: a near-miss spelling is NOT folded`; widening to `Another Claude` → same case.

### (b) `expect: "declared self-test count"` is a FRAGMENT, and `run_mutations` requires EQUALITY

`check-plan-code.py`, in `run_mutations`:

```python
unnamed = [(w, [f for f in fails if w == f]) for w in wants]
```

with the comment two lines up: *"⚠ EXACT case names, not substrings (round 6). The round-5 rule was
CARDINALITY-ONLY … only equality says that."* The fragment matches zero red cases and the entry is
scored red-but-unattributable.

**And it cannot be fixed by pasting the whole sentence**, because the sentence embeds live numbers
(`132 != 0`) — it would break again the next time a case is added, which is the exact drift the F4
fix exists to end. The structural repair is to make the drift failure obey the canonical failure
grammar that `parse_fail_names` reads:

```python
failures.append(f"declared self-test count: got {declared_or_'MISSING'} want {total} — …")
```

`parse_fail_names` truncates at the LAST `": got "`, so the attributed name becomes the stable
string `declared self-test count`, and the existing `expect` starts matching by equality.

---

## R8-2 — Medium — the fix removes 17% of warned TURNS but 0.6% of the warnings a reader receives, and it makes the repeat concentration worse

Replay of both versions over the same **767** transcripts, coalescing recomputed at **every stop**
(what the hook actually does — `coalesce_injected(windows(records))` on the transcript as it stands
at that moment):

| | master | fix branch | delta |
|---|---|---|---|
| distinct turns with a closing act | 771 | 642 | −129 |
| distinct turns WARNED | 744 | **619** | **−125** — exactly r7's prediction |
| warning **EMISSIONS** (what stderr shows) | 1,183 | **1,176** | **−7 (−0.6%)** |
| repeat emissions (a turn warned again) | 439 | **557** | **+118 (+27%)** |
| worst single turn | 36× | **71×** | +35 |

Mechanism: folding a teammate window into the **live** window means the live window absorbs more
records without the subject advancing, so `judged_window` returns the *same* previous turn at more
consecutive stops. Fewer turns warn; the ones that do warn more often.

This is the interaction with #149, not a re-report of it: the fix **enlarges** the quantity #149
measures, so #149's cost estimate taken from r7 is now low by about a quarter.

**A correction I owe on r7.** The r7 method table labelled `821` and `696` as "warnings"; those were
emissions computed with coalescing applied once and then prefixed, which under-counts repeats. The
figure that survives re-measurement is the **turn** count — 744 → 619, and the 125 delta is exactly
what F2 predicted. The 15.2% claim should be read as *15.2% of warned turns*, not of emissions.

---

## R8-3 — Low — 42 turns warn after the fix that did not before; 40 are correct, 2 are a new false alarm of the wrong-subject kind

Set difference on turn identity (opener uuid), master vs branch: **167 turns stop warning, 42
start.**

* **40 of 42** were "not a judged subject before": pre-fix their closing acts sat in the teammate
  fragment while the turn proper had none, so the turn was invisible. Post-fix the acts and the
  report belong to one turn and it warns. That is the rule working, not a defect.
* **2 of 42** were **QUIET before and WARN now** — the wrong-subject hazard you asked about,
  concretely. Example `12fc2cc2-f073-4ca3-b682-fe9869deae0d.jsonl`, acts
  `['a plan tick','a commit','a push','a merge']`: on master the judged turn's final text carried a
  table (QUIET); on the branch the merged window's final text is the *later* fragment's message,
  ending `…**The comprehensibility bundle is unblocked** … Say "go" for **#78**, or name a
  different row.` — no table, so it warns. Second instance in
  `6b5778a9-a088-47b5-94ac-4c3380ae80cd.jsonl`.

`final_text_of` takes the last text block of the merged window, so when a fold joins two fragments
that each closed something, the *later* report is judged against the *union* of acts. The hazard is
inherent to coalescing and already existed for `<task-notification>`; what changed is that the
opener population it applies to grew by 332. It is not stated in the docstring's
*WHAT THIS CANNOT SEE* list, and it belongs there — one line, next to
*"A close split across text blocks"*.

Rate: 2 in 767 transcripts. I am not asking for a behaviour change.

---

## R8-4 — Low — the new case "the teammate fragment's records join the interrupted turn" cannot see the opener it names

Mutation on a copy: `list(prev.body) + [opener] + list(window.body)` → `list(prev.body) +
list(window.body)`. Result: **132/132 passed, rc=0 — SURVIVED.**

The case asserts `[x for x in _tm[0].body if isinstance(x, str)] == ["A", "B"]`, and the opener is a
`dict`, so the filter removes exactly the record whose joining is in the case's own name. This is
r7 F6(e) (#151) reproduced in a case written for the F2 fix. Held to the standard you asked for, it
is a case that passes with part of the behaviour it names removed.

Fix: add `check("coalesce: the injected opener itself joins the body", len(_tm[0].body), 3)`.

Harmless today — nothing reads the opener out of the body — which is why it should be asserted
rather than argued: `_errored_tool_ids` and `paired_outputs` both iterate the whole body, so a
future injected record carrying a `tool_result` would make it load-bearing silently.

---

## R8-5 — Low — the literal now lives in two guards, and nothing fails if the harness rewords it

`"Another Claude session sent a message"` is now hardcoded in
`check-closing-table._INJECTED` **and** in `check-banner-armed._META_IS_REALLY_A_MESSAGE`. If the
harness ever rewords that injection, both stop matching, every self-test stays green, and the 332
openers silently revert to splitting turns. No standing check observes the string against a real
transcript.

Not asking for a fix in this PR — naming the falsifier so it is a decision rather than an oversight.
The cheapest honest version is a comment in both places pointing at the other, which is what the
`_INJECTED` comment nearly does already.

---

## The argument you struck — you are right, and here is the code

Concede, both halves.

```python
# scripts/check-banner-armed.py:175-181
def _is_turn_boundary(rec: dict) -> bool:
    if rec.get("type") != "user":
        return False
    if _is_tool_result(rec):
        return False
    if rec.get("isMeta") is True and not _meta_carries_a_message(rec):
        return False
    return True
```

1. **Inverted, exactly as you read it.** `_meta_carries_a_message(rec) == True` makes the
   `return False` branch not fire, so the record **stays a boundary**. The tuple names records that
   ARE a real new instruction. Citing it as a defining expression for *"not the human typing"*
   argues for preserving the split F2 wanted folded. My r7 wording was wrong, not merely loose.
2. **Unreachable for these records anyway.** The branch is gated on `isMeta is True`, and all 332
   teammate records carry `isMeta: None` (re-measured this round). `_meta_carries_a_message` is
   never called for them.

The residual worth keeping is much smaller than what I claimed, and it is R8-5 above: the two files
now share a literal with no observer. Resting the fold on `coalesce_injected`'s own predicate —
*was that boundary a PERSON?* — is the correct warrant, and the code comment records the struck
reasoning better than a deleted sentence would have.

---

## Verdict, per finding

| finding | verdict | evidence |
|---|---|---|
| **F2** — teammate fold | **CLOSED in behaviour, but the PR is NOT MERGEABLE as it stands** | 744 → 619 warned turns over 767 transcripts, exactly the predicted −125; fold reverted → red via the case it names. ⛔ Blocked by **R8-1(a)**: its second mutation is an equivalent mutant, so one of the four new cases has no falsifier |
| **F4** — derived self-test count | **CLOSED** | `cases += 1` in `check()`; 132 static calls = 132 counted; deleting `cases += 1` → red. ⛔ Its mutation entry is **UNATTRIBUTABLE** — R8-1(b) |
| **F5** — docstring + the open half | **CLOSED** | the false sentence is gone, replaced by an accurate account of the disagreement; the unmeasured half is backlog **#148** with an explicit *"do not apply this fold there on suspicion"*. Verified #146/#147/#150 are ticked ✅ and #145/#148/#149/#151 stand open |
| new defects from the fixes | **3** | R8-2 (Medium, emission-level benefit is 0.6% and repeats rise 27%), R8-3 (Low, 2 new wrong-subject warnings), R8-4 (Low, new vacuous case) |
| mutation gate on the branch | ❌ **RED** | `run_mutations` returns `ok = False` on the three new entries |
| self-test on the branch | ✅ | 132/132, rc=0 |
| repo left untouched apart from this file | ✅ | read-only git, temp copies, no `--mutate .` against the tree |

**The one thing to change before merge:** R8-1. Retarget the substring mutation to the phrase
truncation (measured to kill via `coalesce: a near-miss spelling is NOT folded`), and give the
count-drift failure the canonical `": got "` grammar so its `expect` can match by equality. Both are
small, and until they land the branch's mutation evidence says the opposite of what the commit
message claims.

**REVIEW GAP: codex — not run for round 8.** This is the independent Claude half only.
