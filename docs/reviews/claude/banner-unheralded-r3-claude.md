# banner-unheralded — round 3, Claude half (the FIXES)

Subject: `f0b01a3f` on `banner-work-without-banner`; the fold under judgement is `26aa25c7`, plus
`4d2d7f9a` which folded the coordinator's F1/F2/F3.

REVIEW GAP: codex — rounds 2+ ALTERNATE by design; the Codex half ran as round 2 on the same fold

⚠ That is the mirror of round 2's own declaration, and a DESIGN alternation rather than a reviewer
that could not run — `docs/plugins.md`: *"a concurrent pair never reviews the FIXES"*. Round 2 was
Codex-only on `26aa25c7` and returned CONVERGED; this round is the Claude half on the same fold,
scoped to whether round 1's findings are closed.

Read first: round 1's Claude half (`docs/reviews/claude/banner-unheralded-r1-claude.md`, 7
findings), the coordinator half (`docs/reviews/coordinator/banner-unheralded-r1-coordinator.md`,
F1–F4) and round 2's Codex half (`docs/reviews/codex/banner-unheralded-r2-codex.md`, CONVERGED).

**Scope.** I wrote round 1, so this round is scoped to *whether my own findings are closed* plus the
fold treated as fresh code. Everything below was produced by running code. All mutation work was
done on copies of `scripts/` under a scratch dir with `HOME` redirected; every `run_decide` probe
rebinds `ROOT`/`SENTINEL`/`WARN_LOG`/`FLUSH_LOG`/`JOURNAL_DIR` into a fresh `mkdtemp`. No file in
this repo and no live log was written.

**Controls.** `python3 scripts/check-banner-armed.py --self-test` → **140/140**. In the scripts-only
staging tree the harness uses, the control is **138/138** (the reachability cases degrade by design).
Every survivor below is quoted against 138/138, and I proved the harness can go red by replaying all
five of the fold's own manifest entries first — each died through the case it names.

---

## Verdict up front

The four defects round 1 filed as mutations are genuinely dead. **H1, M1, M2, M3, F1, F2, F3 are
CLOSED.** What is not closed is the *class* each of the two Highs belonged to, and this is the
finding of the round:

> Round 1's H2 said *nothing proves the pause is SAMPLED rather than re-read*. The fold pinned
> `paused`. The identical mutation on `armed` — the value H2's own fix comment cites as the
> precedent ("SAMPLED, NOT RE-READ AT JUDGING TIME, **for the same reason `armed` is**") — still
> leaves the suite fully green. Round 1's L2 said the pause key match can be loosened; the fold
> pinned `_paused_from_text` and left `_armed_from_text`, which L2 named in the same sentence.

And one finding is not merely open but **refuted in its premise**: L1 asked whether `prev_paused` is
untested wiring or dead code. Round 2 answered *"no clean run-generated path"*. **It is untested
wiring, it is live, and I drove it.**

**Nine single-edit mutations of the delivered code leave the suite at 138/138.** Six of them are in
one place.

| | mutation | suite | what it does to a user |
|---|---|---|---|
| **H-A1** | `armed` re-read at judging time | **138/138** | warns `unheralded` at a turn that had a plan armed; silences one that did not |
| **H-A2** | `steps` re-read at judging time | **138/138** | the `unbannered` detail and the CANNOT-RUN guard describe the wrong turn |
| **H-B1** | `"prev_paused": …get("paused")` → `False` | **138/138** | false `unheralded` **and** false `unarmed` against a paused turn |
| **H-B2** | the continuation carry of `prev_paused` → `False` | **138/138** | same, on a blocked-stop continuation |
| **H-B3** | the continuation carry reads `paused` not `prev_paused` | **138/138** | the pause sample shifts by one turn |
| **H-B4** | `"prev_armed"` → `False` | **138/138** | false `unheralded` against a turn that had a plan armed |
| **H-B5** | `"prev_steps"` → `None` | **138/138** | spurious **CANNOT RUN** |
| **H-B6** | the continuation test `==` → `!=` | **138/138** | spurious **CANNOT RUN** on both paths |
| **M-A** | `_armed_from_text`'s key match loosened to `startswith` | **138/138** | the two sentinel readers disagree — L2's stated property, undelivered |

---

## Per-finding judgement

| finding | verdict | the command that shows it |
|---|---|---|
| r1 **H1** — the `no banner` term is unfalsifiable | **CLOSED** | the hoist now reddens W11+W12 (and W10, and the count case); relocating the branch below `step >= total` reddens 11 cases |
| r1 **H2** — nothing proves `paused` is sampled | **PARTIALLY CLOSED** | `paused=_paused()` reddens H2a+H2b ✅ — but `armed=_armed()` and `steps=steps_now` are **138/138** |
| r1 **M1** — the log detail equals the threshold | **CLOSED** | `detail = f"{LARGE_TURN} tool calls"` reddens the W-INT log case |
| r1 **M2** — the pause reaches one class of three | **CLOSED** (behaviour correct) | withdrawing `or paused` reddens P11; the sibling is loud in every sub-state I could reach |
| r1 **M3** — `edited` refuted and retained | **CLOSED** | the bound is stated in the docstring; **207 / 54 / 26% reproduce exactly** |
| r1 **L1** — `prev_paused` never reached end to end | **NOT CLOSED — and the premise is false** | PREV SLOT CONSULTED, from a clean journal, via `run_decide` only |
| r1 **L2** — the pause key can be loosened | **PARTIALLY CLOSED** | P10 kills `_paused_from_text`; `_armed_from_text` is **138/138** |
| coord **F1** — split-turn bound unstated | **CLOSED** | the docstring's *what it cannot see* list carries it, ending "Do not read the 0 as a property of the rule" |
| coord **F2** — dead `"?"` | **CLOSED** | kept, with "It is a crash barrier, not a branch; that is why no case asserts it" — a stated decline, which is what F2 asked for |
| coord **F3** — redundant `FileNotFoundError` | **CLOSED** | `except (OSError, UnicodeDecodeError)` at `:722`, with the asymmetry against `_armed()` explained |
| coord **F4** — two text bindings, one pre-check | **DEFERRED as filed** | and currently sound: 27 anchors each resolve **exactly once**, 0 duplicate names, **0** `expect[]` naming a case that does not exist |

---

## H-A (High) — the fold pinned `paused` and left `armed` and `steps`, which are the same mechanism

Round 1's H2 was not a finding about the word *paused*. It was a finding about the journal round
trip: *the value the verdict consumes must be the one sampled at the judged turn's stop.* The fold
added `_drive_changing` + H2a/H2b, which are the first cases in the suite where the sampled value
and the live value differ — and they vary **only** `paused`. In both legs `armed_then` is `False`
(`_PAUSED_TXT` is paused, so `_armed_from_text` maps it to False; the other state is an absent
sentinel). So the legs cannot see `armed` being re-read.

**H-A1.** One edit at the call site:

```diff
-                        texts, armed_then, steps=steps_then, edited=edited,
+                        texts, _armed(), steps=steps_then, edited=edited,
```
```
138/138 self-test cases passed        *** SURVIVOR ***
```

**Driven end to end** (`$SCRATCH/a1_demo.py`, every path redirected). Turn T runs 30 tool calls with
a plan armed and no banner. `check-plan-progress.py` unlinks the sentinel when the last box is
ticked — which `run_decide`'s own comment at `:975` cites as the reason this guard runs first — so
by T+1's stop the sentinel is gone. The mirror is the same scenario with the states swapped:

| scenario | delivered | mutant H-A1 |
|---|---|---|
| T ran **armed**, sentinel cleared before judging | `rc=0`, no log line | **`rc=1`, log `unheralded / 30 tool calls`** |
| T ran with **nothing armed**, a plan armed during T+1 | `rc=1`, log `unheralded / 30 tool calls` | **`rc=0`, no log line** |

An exact inversion in both directions: a false *"WORK WITHOUT A BANNER — this turn … armed no
plan"* against a turn that had a plan armed, and silence against one that owed a warning. This is
the mechanism the file calls *"the entire fix"* of backlog #96.

**H-A2.** `steps=steps_then` → `steps=steps_now` is also **138/138**. `steps` feeds both the
`unbannered` detail and the `armed and steps is None` CANNOT-RUN guard, so a re-read makes both
describe the wrong turn.

⚠ **Both are PRE-EXISTING** — `armed_then, steps_then = sample` is on `master` (`:792`). I am
filing them anyway for the same reason the fold accepted M2, which was also pre-existing: the
branch makes them **cheap**. `_drive_changing` is now in the file and takes a `before`/`after` pair;
closing H-A is two more legs through the helper the fold already wrote, plus two manifest entries.

**Falsifier to add.** Two legs through `_drive_changing`: seed with `plan: plans/p.md\narmed: t`
and judge with the sentinel unlinked (assert QUIET), and the mirror (assert WARN).

---

## H-B (High) — the previous slot is REACHABLE from `run_decide`, and six single edits to it leave the suite green

Round 1's L1 offered an either/or and could not settle it. Round 2 gave a split answer: reachable by
hand-seeding a journal, but *"I do not see a clean run-generated path where it matters before
`last_judged_uuid` or non-judgability makes it irrelevant."* **I found the path, and it is built
out of nothing but this guard's own documented mechanism.**

**Why both earlier attempts missed it.** The prev slot needs, at one stop, `prev_turn_uuid == U`
while `last_judged_uuid != U`. `last_judged_uuid` is set to the judged turn's uuid at every stop
that has one, so the only way to separate them is for the window **U** to be *non-judgable when it
was live* and *judgable one stop later*. Judgability can only change if the transcript grows — which
is backlog #96's late flush, the mechanism `_late_flush` exists to measure and the docstring calls
the normal case. Both earlier passes looked for the path in a transcript written before the first
stop, where it cannot exist by construction.

**The drive** (`$SCRATCH/l1_probe.py` — `run_decide` only, clean journal, nothing hand-seeded;
`sample_for` instrumented to print which slot answered):

```
Stop A   transcript = [user Wa]                       sentinel PAUSED
Stop B   transcript = [user Wa, user Wb]              sentinel cleared (resumed)
Stop C   Wa's assistant record arrives LATE (30 tool calls, no banner) + user Wc + assistant
```
```
      >>> PREV SLOT CONSULTED for Wa
      rcA=0 rcB=0 rcC=0
      journal after C: sampled=Wc prev=Wb prev_paused=False last_judged=Wa
      warn log: (none)
```

The corpus says the precursor shape is ordinary, not exotic: over the 65 `cli` transcripts,
**322 non-judgable windows are not the live one** (`is_judgable` rejects them for holding no
assistant record — the same predicate the coordinator's F1 measured 90 slash-command openers
against).

**Six survivors on that path.** Each is one edit; each leaves **138/138**; each is quoted with the
verdict it changes on the drive above (`$SCRATCH/l1_probe2.py`, which adds a continuation stop):

| # | edit | delivered | mutant |
|---|---|---|---|
| H-B1 | `"prev_paused": (already or {}).get("paused", False)` → `False` | `rc=0` | **`rc=1`, log `unheralded / 30 tool calls`** |
| H-B2 | `record["prev_paused"] = …get("prev_paused", False)` → `False` | `rc=0` | **`rc=1`, log `unheralded / 30 tool calls`** |
| H-B3 | the same line reads `"paused"` instead of `"prev_paused"` | `rc=0` | **`rc=1`, log `unheralded / 30 tool calls`** |
| H-B4 | `"prev_armed": (already or {}).get("armed")` → `False` | `rc=0` | **`rc=1`, log `unheralded / 30 tool calls`** |
| H-B5 | `"prev_steps": (already or {}).get("steps")` → `None` | `rc=0` | **`rc=2` CANNOT RUN** |
| H-B6 | `if live_uuid == (already or {})…` → `!=` | `rc=0` | **`rc=2` CANNOT RUN on both paths** |

H-B6 is the sharpest: inverting the *entire* continuation branch — the branch whose only purpose is
this carry — is invisible to 138 cases, and turns a sound verdict into *"TREAT THAT TURN AS NOT
CHECKED"*. H-B5 does the same through the CANNOT-RUN guard. P8 covers `sample_for`'s prev slot as a
**pure function** on a hand-built dict, which is exactly the shape the W-INT comment warns about
four screens above: *"unit coverage does NOT compose — mutate the CALL SITE"*.

⭐ **This is where M2 lands, and it is the state round 2 did not probe.** The brief asked for a
state `if armed or paused` had not been tried in. It is this one: the fold's behaviour change makes
`prev_paused` load-bearing for the `unarmed` class, which holds **100% of the warn log's 76
entries**. Same drive, with Wa's late record carrying `## ▶ STEP 2 of 5` instead of 30 tool calls
(`$SCRATCH/m2_prev.py`):

```
DELIVERED             rc=0  log=(none)
MUT prev_paused=False rc=1  log=['unarmed', 'STEP 2 of 5']
```

So M2 itself is correct — and it widened the blast radius of the one piece of wiring nothing drives.

**Direction:** cry-wolf on four of the six, and *"cannot run"* on the other two, which this project's
own rule says must never be read as a pass.

**Falsifier to add.** The nine-line fixture above, as one `_drive_*` helper plus two cases (assert
QUIET with the pause in the prev slot; assert WARN with the control), and manifest entries anchored
on `"prev_paused": (already or {}).get("paused", False),` and on the continuation `if live_uuid ==`.

⚠ **And the shipped prose now says the opposite.** `docs/dashboard-entries.md:11325` — a
reader-facing page — states as fact: *"`prev_paused`'s path is never reached end to end."* Round 1
hedged (*"I tried and failed to construct an input that does"*); the fold hardened the hedge into an
assertion. That is this project's recorded *an inference stated as MEASURED*. The sentence needs
correcting whatever happens to the code.

---

## M-A (Medium) — L2's fix pinned one of the two readers, and the property it claims needs both

P10 is a good case and it kills the mutation it names. But L2's finding named two functions in one
sentence — *"the identical hole exists in `_armed_from_text` (pre-existing)"* — and the fold's own
comment states the property being defended: *"a key like `paused_at:` would … stand this reader down
while `_armed_from_text`'s `==` keeps the plan armed — the two readers disagreeing about a
stand-down."* Loosening the **other** reader produces that same disagreement, from the other side:

```diff
-        if key == "paused":
+        if key.startswith("paused"):
```
```
138/138 self-test cases passed        *** SURVIVOR ***
```

On `plan: plans/p.md\narmed: t\npaused_at: 2026-09-22\n`:

| | `_armed_from_text` | `_paused_from_text` | `decide(..., tool_uses=30)` reason |
|---|---|---|---|
| delivered | `True` | `False` | `''` (quiet) |
| mutant | **`False`** | `False` | **`unheralded`** |

A false *"WORK WITHOUT A BANNER … armed no plan"* against a turn with a plan armed. Pre-existing, one
line, and one case (the mirror of P10) closes it. This is the repo's recorded *a shim fails BOTH
ways* — fixing the half you were shown is instance-not-class.

---

## L-A (Low) — `_drive_changing` is a second implementation of `_drive`'s protocol

`_drive_changing` (`:1938`) duplicates `_drive` (`:1588`) line for line — clear the journal, write
the subject, stop, append a `later` turn, stop — and differs only by the two sentinel writes. If the
drive protocol ever changes in one, the other silently describes a different world, and the cases
that depend on it stay green. It is a three-line change to give `_drive` optional `before`/`after`
parameters and delete the copy. Offered, not pressed.

Two adjacent notes, both cheap and both in F4's territory (bindings by literal text):

* the suite has **140 PASS lines and 139 distinct case names** — `"...and it says TREAT THIS AS NOT
  RUN"` appears twice. **Pre-existing** (master: 96 cases, 95 names), no manifest entry names it, so
  nothing is mis-attributed today — but `expect[]` matches by name, so a duplicate name is an
  attribution ambiguity waiting for its first entry.
* the fold's **P12** is named *"...and the SAME turn unpaused still warns, so the excuse is doing the
  work"*, and the pre-existing **P2** is *"...and the SAME turn unpaused still WARNS, so the excuse
  is doing the work"*. The two differ in one word's capitalisation. Both are currently bound
  correctly; a future tidy-up of either would rebind silently.

---

## What I attacked and found sound

Recorded because a review that prints only findings hides where it looked.

1. **All five of the fold's new manifest entries die through the case they name**, replayed
   independently on staged copies: hoist → W11 + W12 (+W10, +the count case); re-read → H2a + H2b;
   hardcoded detail → the W-INT log case; withdraw `or paused` → P11; prefix key → P10.
2. **H1 is genuinely pinned, and I tried to get round it.** Relocating the branch below
   `if step >= total` — which keeps all three explicit terms and is the nearest thing to the
   original mutation — reddens **11** cases including W12. W3's new label (*"the ARMED term, which
   is what this case actually exercises"*) matches what it tests: it reaches the `armed or paused`
   return, and deleting that line reddens it. It is mislabelled no longer, and not dead.
3. **H2a/H2b do not pass for an ambient reason.** In H2a the only thing keeping the verdict quiet is
   `paused_then`: `armed_then` is `False` in both legs and the mutant's `_paused()` returns `False`,
   so it warns. The two legs are the only place in the suite where the sampled and live values
   differ, as the comment claims.
4. **M2's behaviour is right and the sibling really is the loud channel.** Beyond round 2's three
   probes I checked the state it did not: `paused:` with **no `plan:` line**. `check-plan-progress`
   is still loud there — `plan_text is None` with `paused is not None` returns
   `WARN, "⏸ PAUSED (<why>) — and CANNOT RUN …"` (`:173`). So does `total == 0` (`:182`). The
   verdicts agree and the sentences no longer contradict each other.
5. **M3's numbers reproduce exactly.** Re-derived against today's corpus with the delivered
   predicates: **207** large bannerless `cli` turns, **54** editing nothing inside the repo, **26%**.
   (My population reads 2,297 turns / 202 bannered against the docstring's 2,293 / 201 — this
   session's own turns, drifting in the direction it should.)
6. **Manifest hygiene is clean, including the binding F4 was filed about.** 27 entries, 0 duplicate
   names, every `edits[].find` resolves **exactly once** against the delivered file, and every
   `expect[]` names a case the suite actually runs — the `expect` half is the one that had no
   pre-check and cost the 40-minute round trip. `check-plan-code.py --self-test` → `128/128`;
   `EXPECTED_MUTATIONS["scripts/check-banner-armed.py"] == 27` and the declared sum `900` both hold.
7. **The declared counts are honest.** The module docstring says `# 140 cases` and the suite runs
   140.
8. **Eight more mutations die correctly**, listed so the shape of the coverage is visible: counting
   `tool_uses` from the live window instead of the judged one (4 red), the same for the log detail
   (1 red), `step >= total` → `>` (9 red), the threshold off by one (6 red), `sample_for`'s current
   slot reading `prev_paused` (3 red) and its prev slot reading `paused` (1 red), the journalled
   pause ANDed with `armed` (2 red), the dedupe removed (1 red), the `unarmed` branch returning the
   `unheralded` reason (5 red), and `steps` not carried to the log block (1 red).
9. **Repo gates all green on the branch:** `check-docs.py`, `check-selftest-counts.py` (45 scripts,
   every declared count verified by running it), `check-review-rounds.py`, `check-dashboard-entry.py`,
   `check-ratchet-contract.py`, `check-anchors.py`.

---

## Summary

| Severity | # | |
|---|---|---|
| Blocking | 0 | |
| High | 2 | **H-A** `armed`/`steps` re-read at judging time — H2's mechanism, one value over, 2 survivors · **H-B** the previous slot is reachable and undefended — 6 survivors, incl. a wholly inverted branch |
| Medium | 1 | **M-A** `_armed_from_text`'s key match — L2's other half, named in L2 and not fixed |
| Low | 1 | **L-A** `_drive_changing` duplicates `_drive`; two name-binding hazards |
| Correction | 1 | the shipped dashboard entry asserts *"`prev_paused`'s path is never reached end to end"* — measured false |

No finding says the delivered code computes a wrong verdict; as in round 1, every one says the
falsifiers stop short of the mechanism. But the shape has changed, and that is what makes this round
worth a fourth. Round 1 found four undefended mechanisms. The fold defended **exactly the four
instances named** and left the sibling value in two of them — `armed` beside `paused`,
`_armed_from_text` beside `_paused_from_text` — each time inside a comment that names the sibling as
the precedent. That is this repo's recorded *after fixing, SEARCH for the class*, and it is the one
correction a green suite can never prompt.

The previous-slot finding is different in kind: it is not a fix that stopped short but a conclusion
that was wrong. Two reviewers and one fold agreed the path was unreachable, wrote that agreement
into a reader-facing page, and used it to justify leaving six live edits undefended. The path is the
guard's own late-flush mechanism, applied to judgability instead of to text length — the one race
this file instruments and then assumes away.

**VERDICT: NOT CONVERGED**
