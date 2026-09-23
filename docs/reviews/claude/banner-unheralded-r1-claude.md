# banner-unheralded — round 1, Claude half (independent)

Subject: `ffc85be8` on `banner-work-without-banner`. Third warning class (`unheralded`) in
`scripts/check-banner-armed.py`.

Read before starting: the Codex half (CONVERGED, no findings) and
`docs/reviews/coordinator/banner-unheralded-r1-coordinator.md` (F1 split-turn, F2 dead `"?"`,
F3 redundant `FileNotFoundError`). **Nothing below restates those three.**

Everything here was produced by running code. Each finding names the command and the behaviour
delta. All mutation work was done on a **copy** of `scripts/` under `$SCRATCH/`, with `HOME`
redirected, and every `run_decide` probe redirects `ROOT`/`SENTINEL`/`WARN_LOG`/`FLUSH_LOG`/
`JOURNAL_DIR` into a fresh `mkdtemp` — no file in this repo and no real log was written.

**Control first.** `python3 scripts/check-banner-armed.py --self-test` → `133/133`. In the
scripts-only staging tree the harness uses, the control is `131/131` (the three reachability cases
degrade to one "NOT CHECKED" case by design). Every survivor below is quoted against that control.

---

## The headline

The delivered code is, as far as I could make it misbehave, **correct**. What is not correct is the
claim that it is *defended*. I found **four single-edit mutations of the delivered code that leave
the suite fully green** — three of them in the exact directions this slice's own commit message
says review caught and fixed. The commit closes with *"A fix is not done when the suite is green;
it is done when something can still kill it."* Applied to itself, the slice is not done.

| | mutation | suite | what it does to a user |
|---|---|---|---|
| **H1** | the class's "no banner" term is dropped | **131/131** | warns `unheralded` on a turn that emitted five banners and finished all five |
| **H2** | the pause is re-read at judging time instead of sampled | **131/131** | warns on a turn that was legitimately stood down |
| **M1** | the log's `detail` hardcodes the threshold | **131/131** | every log entry reports `25 tool calls` whatever the turn did |
| **L2** | `_paused_from_text` matches any `paused*` key | **131/131** | the two sentinel readers disagree about a stand-down |

---

## H1 (High) — the new rule's "no banner" term is unfalsifiable, and the case that claims to cover it passes for an ambient reason

The class is documented as *not armed, not paused, **no banner**, large*. Three of those four terms
are terms of the `if`:

```python
if not armed and not paused and tool_uses >= LARGE_TURN:
```

The fourth — "no banner" — is not written anywhere. It is carried entirely by the statement's
**position** inside `if banner is None:` (`:517`). Nothing in the suite pins the position.

**The mutation.** Hoist the test above `banner = highest_banner(texts)`. One edit, same rule, same
three explicit terms, no case mentions it:

```
$ cd $SCRATCH/sandbox && python3 scripts/check-banner-armed.py --self-test | tail -1
131/131 self-test cases passed
```

**What the mutant does.** Probing `decide()` in both trees, `armed=False, tool_uses=30`:

| texts | delivered | mutant |
|---|---|---|
| `## ▶ STEP 5 of 5 — done` | `rc=0` `reason=''` | **`rc=1` `reason='unheralded'`** |
| `## ▶ STEP 2 of 5 — mid` | `rc=1` `reason='unarmed'` | **`rc=1` `reason='unheralded'`** |
| no banner | `rc=1` `reason='unheralded'` | `rc=1` `reason='unheralded'` |

Row 1 is the guard's **single most important false-alarm mitigation** — the `i >= total` quiet, which
the module docstring spends four paragraphs on (`:36-48`, backlog #96's whole subject). The mutant
warns *"WORK WITHOUT A BANNER — this turn made 30 tool calls … and emitted no `## ▶ STEP i of N`"*
at a turn that emitted five of them. Row 2 relabels **every** `unarmed` entry as `unheralded` —
which is verbatim backlog #97's second defect, the one this slice's `REASON_*` constants exist to
make impossible, arriving through the door the constants do not guard.

**Why no case catches it.** W3 is the case that claims to:

```python
case("W3 a large turn that DID banner is quiet (catches dropping the banner term)",
     decide([B.format(2, 5)], armed=True, tool_uses=_BIG)[0] == QUIET)
```

It passes `armed=True`. With `armed=True` the mutant's `not armed` is already false, so the class
cannot fire wherever it sits — W3 is QUIET in both trees for a reason that has nothing to do with
the banner. W3 *can* fail (deleting `if armed: return QUIET` reddens it), so it is not a dead case;
it is **mislabelled**, and its label is the only place the banner term is claimed to be covered.
This is the recorded shape *a case can pass for an AMBIENT reason* — and the W-block's own opening
comment warns against exactly this ("a case that set both would pass for whichever branch happened
to win"), then commits it three cases later.

**Direction:** cry-wolf, plus log contamination.

**Falsifier to add** (one case, `armed=False` so the banner is the only thing keeping it quiet):

```python
case("W11 a large UNARMED turn that CLOSED its sequence is quiet — the class is defined on "
     "`no banner`, and that term is carried only by where the branch sits",
     decide([B.format(5, 5)], armed=False, tool_uses=_BIG)[0] == QUIET)
```

and a manifest entry anchored on `    banner = highest_banner(texts)\n    if banner is None:`.
Fix W3's label while you are there, or delete it as redundant with "the SAME turn, armed -> quiet".

---

## H2 (High) — `paused` is sampled, journalled and passed, and nothing proves the *sample* is the thing consumed

Two comments carry this slice's most-argued design claim. At `:953`:

> Sampled HERE, beside `armed_now`, so both describe the same turn. A pause read at judging time
> would describe a different moment than the verdict it excuses.

and at `:1050`:

> ⛔ SAMPLED, NOT RE-READ AT JUDGING TIME … resuming a plan between the two stops must not
> retroactively remove the excuse, and pausing between them must not retroactively grant one.

**The mutation.** Make the call site re-read the live sentinel — i.e. do the thing both comments
forbid:

```diff
-                        tool_uses=tool_uses_of(judged.body), paused=paused_then)
+                        tool_uses=tool_uses_of(judged.body), paused=_paused())
```

```
$ cd $SCRATCH/m1tree && python3 scripts/check-banner-armed.py --self-test | tail -1
131/131 self-test cases passed
```

**The scenario it breaks** (`$SCRATCH/m1_demo.py`, run end to end through `run_decide` with every
path redirected). Turn T runs 30 tool calls while the sentinel reads
`paused: waiting on a dispatched review` — backlog #94's meaning of a pause, and the shape of turn
that runs long. During turn T+1 the review lands and the plan is resumed (`paused:` cleared). At
T+1's stop, T is judged:

```
DELIVERED (paused=paused_then, the sample):
  rc=0  warn-log: (no warn-log line)
MUTANT H2 (paused=_paused(), re-read at judging time):
  rc=1  warn-log: ['unheralded', '30 tool calls']
```

A false `unheralded` warning against a turn the project deliberately silenced, plus a contaminating
line in the log that the promote-to-blocking decision reads. The converse is equally reachable:
pausing *during* T+1 retroactively excuses a T that owed a warning — silence in the dangerous
direction.

**Why no case catches it.** P1–P6 are unit calls to `decide()`/`_paused_from_text` with `paused=`
supplied by hand. P7–P9 are unit calls to `sample_for`. P-INT and its control are the only
end-to-end pair, and **they hold the sentinel in one state across both stops** — P-INT leaves it
paused for the seed run and the judging run; the control leaves it absent for both. A scenario in
which the sampled value and the live value *differ* does not exist anywhere in the suite, so
"sampled" and "re-read" are behaviourally identical to every case that exists.

Note the recursion: the commit message's own ⭐ paragraph says the `not paused` fix "was
unfalsifiable until eleven cases and six mutations were written against it." Eleven cases and six
mutations later, the **mechanism that makes it a sample rather than a re-read** is still
unfalsifiable. Four of the fourteen new manifest entries (`sample_for` current slot, `sample_for`
previous slot, `run_decide` stops PASSING, `run_decide` stops SAMPLING) defend a journal round trip
that, under H2, no verdict would consult at all — and the suite would not notice.

**Direction:** both. Cry-wolf on resume-between-stops; silence on pause-between-stops.

**Falsifier to add.** Extend P-INT with a third leg: seed with the sentinel **paused**, then clear
it before the judging run, and assert `QUIET`. Add the mirror (seed unpaused, pause before judging,
assert `WARN`). Anchor a manifest entry on `paused=paused_then)`.

---

## M1 (Medium) — the log's `detail` column cannot be told apart from the constant, because the only integration case drives exactly `LARGE_TURN` calls

```diff
-            detail = f"{tool_uses_of(judged.body) if judged is not None else 0} tool calls"
+            detail = f"{LARGE_TURN} tool calls"
```

```
131/131 self-test cases passed
```

W-INT's assertion is `_logtext().endswith(f"\t{REASON_UNHERALDED}\t{LARGE_TURN} tool calls")` and
its fixture builds `range(LARGE_TURN)` calls — so the logged count and the threshold are the same
number in the only test that reads the log. A guard that always logged `25 tool calls` would look
identical.

This is not cosmetic. The `detail` column is the evidence: `LARGE_TURN` was chosen from a table of
volumes, and the promote-to-blocking decision will be made by reading this log. Under the mutant
every entry sits exactly on the boundary and the observed distribution is manufactured by the
logger — the *a report format is a CONTRACT* / #97 shape, one column over.

The unit case *"...and it reports the COUNT it saw, not a fixed string (catches a hardcoded
message)"* covers `decide()`'s **message**, not the log's **detail**; they are separately derived.

**Fix:** drive `LARGE_TURN + 7` calls in W-INT so the logged number cannot be the constant. Note
this is precisely the hazard the W0 comment already identified ("every other case derives from
`LARGE_TURN` and so moves with it") — the diagnosis was right and was applied to one site.

---

## M2 (Medium) — the pause excuse reaches only the newest of the three classes, and the `unarmed` message states a falsehood during a stand-down

The slice adds `paused` to `decide()` and wires it to exactly one branch. The `unarmed` branch —
**100% of the warn log's 76-entry history**, by this commit's own measurement — is untouched, and
`_armed_from_text` maps a paused plan to `armed=False`. So:

```
$ python3 -c '<import guard>; S="plan: plans/p.md\narmed: t\npaused: waiting on a dispatched review\n"; ...'
  _armed_from_text  -> False
  _paused_from_text -> True
  decide(partway banner, armed=False-because-paused, paused=True) -> rc=1 reason='unarmed'
  says 'names nothing': True
```

The emitted message is *"⚠ BANNER WITHOUT A PLAN — … and `.claude/executing-plan` names
nothing."* The sentinel names `plans/p.md`. The statement is false, and the sibling blocking guard
in the same state says the opposite out loud — `check-plan-progress.py:174` returns
`⏸ PAUSED (<why>) — and …`. `_armed_from_text`'s docstring insists the two guards "must agree about
what 'armed' means"; they agree on the *verdict* and now disagree on the *sentence*.

Backlog **#99** is this symptom — *"the only symptom is a warning that reads like noise"* — and the
information needed to stop it (`paused_then`) is, as of this commit, already computed, journalled
and in scope at the call site. The slice carries the fix past the defect without applying it.

I am flagging this as **pre-existing but newly cheap**: the behaviour is older than the branch, and
it is the branch that makes it a two-token change. Either honour the pause in the `unarmed` branch
too, or amend that message to stop asserting "names nothing" when it cannot know.

**Direction:** cry-wolf, in the class that produces every warning this log has ever held.

---

## M3 (Medium) — `edited` is refuted by this branch's measurement and left in place on the sibling class

The commit's central empirical argument is that backlog #95's proposed `edited` discriminator
**misses half its population**: 52.2% recall, separating 2.48x against turn size's 5.03x. I
re-derived both (below) and they reproduce exactly.

`unbannered` still gates on `edited` (`:519`, `armed and unticked > 0 and edited`), unchanged. So
the refuted discriminator is retired for the new class and retained for the old one, and the state
it misses is the one the docstring calls *"the normal mode, not an edge case"* — a coordinator turn
that dispatches reviewers, edits nothing, and banners nothing, with a plan armed.

**Measured** over the same 2,293 `cli` turns:

| | count |
|---|---|
| large (≥25) bannerless turns | 207 |
| …that edited **nothing** inside the repo | **54 (26%)** |

Those 54, had a plan been armed, are silent in **both** classes: `unheralded` excludes them for
`armed`, `unbannered` excludes them for `not edited`. The branch's own placement comment says the
gap "is entirely in the `not armed` half" — measured, it is not.

I accept the stated reason for not merging the classes (merging moves a live class with its own
falsifiers). This is not a request to merge them; it is a request that the docstring's *what it
cannot see* list say this out loud, since the branch is the thing that establishes it. It pairs
naturally with the coordinator's F1, which asks for the same treatment of the split-turn shape.

**Direction:** under-fire (the less dangerous one).

---

## L1 (Low) — both `prev_paused` carries are unfalsifiable, and the path they feed is never reached end to end

Two survivors, each one edit, each `131/131`:

```diff
-        "prev_paused": (already or {}).get("paused", False),
+        "prev_paused": False,
```
```diff
-        record["prev_paused"] = (already or {}).get("prev_paused", False)
+        record["prev_paused"] = False
```

Instrumenting `sample_for`'s previous-slot branch and running the whole suite prints
`PREV-SLOT-CONSULTED` **once** — from P8, which calls `sample_for` directly on a hand-built dict.
`run_decide` never reaches it in 131 cases.

I tried and failed to construct an input that does. The path `sample_for`'s docstring describes — a
blocked stop re-firing inside the same turn — is preempted by the `last_judged_uuid` dedupe at
`:965`, which returns QUIET before `sample_for` is called. Driven end to end, the continuation stop
is `rc=0` with the warn log unchanged at one line, and it never consults the previous slot.

So this is an honest either/or rather than a defect claim: **either** two lines of new wiring are
untested, **or** `prev_paused` (and, by the same argument, the pre-existing `prev_armed` /
`prev_steps`) is dead. The suite asserts the pure function and settles neither. Worth one
experiment before the next class is added on top of it.

## L2 (Low) — `_paused_from_text`'s key match can be loosened without a case noticing

```diff
-        if line.split(":", 1)[0].strip() == "paused":
+        if line.split(":", 1)[0].strip().startswith("paused"):
```
→ `131/131`. A sentinel key such as `paused_at:` would then read as a stand-down here while
`_armed_from_text`'s `==` keeps the plan armed — the two readers disagreeing about a stand-down,
which is the precise failure both docstrings say the `":" not in line` rule exists to prevent. No
writer emits such a key today, so this is a latent hole rather than a live one, and the identical
hole exists in `_armed_from_text` (pre-existing). P5 covers the *colon* rule and nothing covers the
*key equality* rule.

---

## What I attacked and found sound

Listed so the coverage of this review is visible, and because a review that prints only findings
hides where it looked.

1. **The threshold table reproduces exactly — all four rows, independently derived.** Importing the
   delivered `windows` / `is_judgable` / `tool_uses_of` / `highest_banner` over the 804 live
   transcripts, filtered to `entrypoint == "cli"` (`$SCRATCH/corpus.py`):

   | thr | catches of bannered | fires on unbannered | rate | table says |
   |---|---|---|---|---|
   | ≥20 | 57.2% (115/201) | 284 | 1 per 8.1 | 57.2% / 284 / 8.1 ✅ |
   | ≥25 | **49.8% (100/201)** | **207** | **1 per 11.1** | 49.8% / 207 / 11.1 ✅ |
   | ≥30 | 42.3% (85/201) | 146 | 1 per 15.7 | 42.3% / 146 / 15.7 ✅ |
   | ≥40 | 31.8% (64/201) | 85 | 1 per 27.0 | 31.8% / 85 / 27.0 ✅ |

   Population reproduces too: **2,293 turns, 201 bannered, 2,092 not**. So do the three derived
   figures: `edited` recall **52.2%** (105/201), `edited` separation **2.48x**, size separation
   **5.03x**. I have no correction to offer on any number in this commit.

   One honest note on my own first pass: I initially got **68.2%** for the `edited` recall and was
   about to file it. The difference is `bool(edited_paths_of(...))` versus
   `_edit_inside_repo(edited_paths_of(...), ROOT)` — the commit measured the predicate the guard
   actually uses, and I had measured a looser one. The figure is theirs, correctly.

2. **The population correction is real and the corpus still splits exactly.** 804 files today (803
   at commit + this session): `sdk-py` 732, `cli` 65, `sdk-cli` 7. Zero banners outside `cli`.

3. **The corpus does not produce a split-turn firing window** — I re-derived the coordinator's F1
   independently and agree: 90 message-carrying `isMeta` openers in `cli`, **all**
   `<local-command-caveat>`, **0** judgable, **0** `Another Claude session sent a message`. F1's
   framing ("unexercised, not immune") is the right one and I have nothing to add to it.

4. **Compaction does not manufacture a firing window.** 24 window openers in `cli` carry
   `isCompactSummary`; **all 24** are rejected by `is_judgable` (no assistant record in the
   window). This was a live worry on my list and it is clean.

5. **Adjacency is not a cry-wolf source.** Hypothesis: since the warn log is 100% `unarmed` —
   i.e. the observed habit is bannering *without* arming — a multi-turn job's unbannered turns would
   be `not armed` and fire despite the human having seen banners either side. Measured over the 207
   firing turns: only **12 (6%)** are adjacent to a bannered turn, and **71%** are in sessions that
   used no banner at all. **Hypothesis refuted; the class is aimed at real silence.**

6. **The state battery: every "must not fire" state behaves as documented.** Driven end to end
   through `run_decide` (`$SCRATCH/states.py`), warn-log lines counted:

   | state | rc | log lines |
   |---|---|---|
   | session's first judgable turn (no subject) | 0 | 0 |
   | large unarmed T1 judged at T2's stop *(should fire)* | 1 | 1 |
   | blocked-stop continuation re-fire | 0 | **1 — no double log** |
   | no journal held for the judged turn | 2 (CANNOT RUN) | 0 |
   | sentinel exists but is unreadable | 2 (CANNOT RUN) | 0 |
   | journal from before `paused` existed, plan paused | 1 | 1 |

   The last row is the documented straddle cost: one warning that was not owed, bounded to the turn
   that crosses the upgrade, in the safe direction. It behaves as `sample_for`'s docstring promises.

7. **Manifest hygiene.** All 22 entries' anchors resolve **exactly once** against the delivered
   file; zero duplicate names; `EXPECTED_MUTATIONS["scripts/check-banner-armed.py"] == 22` and
   `sum(EXPECTED_MUTATIONS.values()) == 895` both hold —
   `python3 scripts/check-plan-code.py --self-test` → `128/128 passed`.

8. **Signature changes have no external caller.** `decide()` and `sample_for()` are called only from
   inside this module and its suite; the hook (`.claude/hooks/block-idle-stop.sh:68`) invokes
   `--decide` and reads the exit code, which is unchanged in meaning.

9. **The three `reason` mutations I could think of beyond the manifest's are killed.** Returning a
   non-empty reason on the QUIET path goes red at 129/131 (W8 + W9). `decide()`'s message quoting
   the wrong count is caught. The class-labelling repair itself is genuinely load-bearing.

---

## Summary

| Severity | # | |
|---|---|---|
| Blocking | 0 | |
| High | 2 | H1 the "no banner" term is unfalsifiable and its case passes for an ambient reason; H2 nothing proves the pause is *sampled* rather than re-read |
| Medium | 3 | M1 the log detail is indistinguishable from the threshold; M2 the pause excuse reaches one class of three and the sibling's message is false; M3 `edited` refuted and retained |
| Low | 2 | L1 `prev_paused` wiring never reached end to end; L2 the pause key match can be loosened silently |

No finding says the shipped code computes a wrong verdict. Every High and the first Medium say the
same thing in three places: **this slice's falsifiers stop one layer short of the mechanism they
are about.** H1's rule term lives in a statement's position and no case reads position. H2's design
claim is about sampling and no case varies the sample. M1's evidence column is pinned to a fixture
that makes it equal the constant. Each is one case and one manifest entry away from being defended,
and all three are in the cry-wolf direction backlog #96 and #97 already paid for.

**VERDICT: NOT CONVERGED**
