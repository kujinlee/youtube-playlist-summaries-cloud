<!-- claude-review: round=18 writer=claude subject=backlog-249-260 head=14867349 -->

NOT CONVERGED — 0 Blocking, 2 High, 3 Medium, 1 Low (new findings only; the Codex half's H1/M1/L1 are
confirmed and not restated).

**The headline is not in `check-plan-code.py`.** Seventeen rounds of attention bought that file a
genuinely hard-to-break diagnostic renderer with two residual holes (below, both Medium). Meanwhile
`scripts/find-claim.py` — added by this branch, +1132 lines, 25 manifest entries — **ships with a RED
`--self-test` on any Python 3.13+ interpreter**, and the guard whose absence makes it red turns the
instrument's one advertised guarantee ("it cannot silently return zero") into a confident false
*absent*. That is the first time this component has been reviewed, and it was found in the first ten
minutes of looking at it.

---

## Instruments and controls (stated first, because every number below depends on them)

All experiments ran on **COPIES** in `…/scratchpad/r18lab/trees/<name>`. Nothing in the worktree was
modified except this review document.

Each tree is a complete `HARNESS_TREE`, derived by `ast` from the source rather than read by eye
(the recipe's own recorded failure mode):

```
('scripts', 'supabase', 'docs', 'node_modules/typescript', '.claude/hooks', '.github/workflows')
```

`$HOME` is redirected into the tree for every run.

| Control | Measured |
|---|---|
| `check-plan-code.py --self-test` | **300/300 passed**, 7.4s |
| `check-plan-code.py --binding` | **1560 anchor(s) across 1552 entries**, each resolving to exactly one site |
| scoped `--mutate .` over `find-claim.json`, **Python 3.12** | **25 mutations, 25 killed, 25 attributed, 0 survivors** |

**Every sever below is stated against that control, with its exact insertion point**, because the
coordinator's first attempt at the Codex half's M1 landed two indent levels off and produced the
opposite verdict.

### Corpus reconciliation (so the sweeps are replayable, not asserted)

`check-plan-code.py` has **296 lexical `case(` call sites**, all inside `_self_test`. One of them,
`scripts/check-plan-code.py:3641`, sits inside a five-iteration `for` loop. 295 + 5 = **300**, which
equals the suite's printed total and the docstring's declared count at `scripts/check-plan-code.py:6`.
The corpus is therefore fully accounted for; no case is hiding in a helper.

---

## Blocking

None. Two candidates were considered and declined, with reasons:

- **The red `find-claim.py --self-test`** (High 1 below) is *not* Blocking, because CI pins the
  interpreter (`.github/workflows/ci.yml:80`, `:701`, `:808` — `python-version: '3.12'`), CI's run of
  that suite at `.github/workflows/ci.yml:179-180` is **green**, and this repository has a written,
  measured policy that a local interpreter mismatch is **advisory** —
  `scripts/check-python-pin.py`'s own output says so. Calling it Blocking would overstate what the
  merge gate sees.
- **The markup bound** (High 2) is not Blocking because `find-claim.py` has no gate caller: its only
  non-self-test invocation is a human following `docs/process-checklists.md:569`.

---

## High

### H-A — `find-claim.py` is RED on Python 3.13+, its ratchet is NOT MEASURED there, and the production guard it loses returns a confident FALSE ABSENT

**Reproduced in the pristine worktree, not only in a lab copy:**

```
$ python3 scripts/find-claim.py --self-test          # python3 == 3.14.4
  [FAIL] ⭐ r3: a classification failure is rc=2, where it used to be an unhandled traceback
         exiting 1 — which this repo reads as 'violation found': got 0 want 2
  [FAIL] ...and it says CANNOT RUN: got False want True
84/86 passed
```

**The cause, measured across three interpreters on this machine:**

| interpreter | `Path.is_file()` on a symlink into a `chmod 000` directory | `find-claim.py --self-test` |
|---|---|---|
| 3.10.x | **raises** `PermissionError` | 86/86 passed |
| **3.12.9 (the CI pin)** | **raises** `PermissionError` | 86/86 passed |
| **3.14.4 (local)** | **returns `False`** | **84/86 passed** |

(`os.stat` still raises on 3.14; it is `pathlib`'s wrapper that now swallows it. The exact boundary —
3.13 vs 3.14 — is **UNVERIFIED**: no 3.13 is installed here. `scripts/check-python-pin.py`'s own
message says "3.13+" for the `ENAMETOOLONG` twin, which corroborates but does not prove it.)

**This is the SECOND instance of a class this repository already built a guard for.**
`scripts/check-python-pin.py` exists because *"`Path.is_file()` raises ENAMETOOLONG on 3.12 and returns
False on 3.13+, which made CI and a dev machine disagree about the same commit"* — its own words, in
its own output. `find-claim.py` depends on the permission-error half of the same wrapper, at
`scripts/find-claim.py:303` (`is_dir, is_file = p.is_dir(), p.is_file()`), and writes the behaviour as
unconditional at `scripts/find-claim.py:730`: *"A symlink pointing into a `chmod 000` directory:
`is_file()` raises"*.

**The substantive half — what a reader actually gets.** The probe at
`scripts/find-claim.py:727-760` searches a corpus where the claim is present, reachable only through a
symlink into the unreadable directory, with `--expect absent`. On 3.12 that is `rc=2` CANNOT RUN. On
3.14 it is **`rc=0`** — the tool's own success wording, *"ok — absent in the searched files, and the
control hit 1 time(s), so the search worked."* The instrument whose docstring property **(c)** is
"⭐ IT CANNOT SILENTLY RETURN ZERO" (`scripts/find-claim.py:43-47`) does exactly that, in the
`--expect absent` mode whose `rc=0` is a **pass** under backlog #257's withdrawal rule.

**And the cost is not just two red cases.** The ratchet goes dark:

```
$ python3 scripts/check-plan-code.py --mutate .      # pruned to find-claim.json; python3 == 3.14.4
[1/1] control scripts/find-claim.py
  ✗ CANNOT RUN — control run of scripts/find-claim.py did not prove the suite works (exit 1)
    BEFORE any mutation was applied. Every verdict below would be an artefact.
NOT MEASURED — the mutation harness produced no coverage verdict. Treat this as NOT CHECKED.
```

Same tree, same 25 entries, **Python 3.12: `25 killed, 25 attributed, 0 survivors`**. So on any 3.13+
developer machine all 25 of this branch's new `find-claim` mutations are unmeasurable, and
`scripts/check-selftest-counts.py` goes **rc=1 on 3.14 and rc=0 on 3.12** off the back of it —
a second gate turned red by the first. That is precisely the shape backlog #56 measured: *a gate red
from birth gets switched off.*

**Remedy.** Not a version bump. The classification site at `scripts/find-claim.py:303` must stop
relying on `pathlib` to raise: call `p.stat()` (or `os.stat`) inside the existing `try`, or
`p.is_file()` followed by an explicit `os.stat` probe when it answers `False`, so the unreadable world
is CANNOT RUN on every interpreter. The probe at `:752` then needs its sentinel repaired (Medium 3).

### H-B — `find-claim.py`'s matcher is markup-literal, the bound is UNSTATED, and the failure direction is a false CLEAN

**First, a correction to the brief.** The coordinator's point 4 states the matcher "is case-sensitive".
**That is refuted.** `scripts/find-claim.py:163` compiles with `re.IGNORECASE` unless
`--case-sensitive` is passed (`:1078-1079`), and `:153-157` records that it *"was case-sensitive
first"* and was deliberately changed. Measured, over a fixture with the claim spelled four ways:

```
$ find-claim.py --pattern "injected before" --control "control token" --report a.md
a.md:2:29: injected before
a.md:3:22: injected BEFORE          <-- the case half of the brief's claim is FOUND
a.md:5:22: injected before   [WRAPPED]
3 occurrence(s)
```

**The markup half stands, and it is the dangerous one.** The tokens are `re.escape`d and rejoined with
`\s+` (`scripts/find-claim.py:34-35`), so emphasis *between* tokens breaks the span. The same fixture:

```
$ find-claim.py --pattern "298 → 300" --control "control token" --expect absent d.md
ok — absent in the searched files, and the control hit 1 time(s), so the search worked.
rc=0
```

…over a file whose line 2 reads `The transition was 298 → **300** cases`. The claim is present, a
reader sees it, and the tool reports **absent with rc=0** — which under `--expect absent` is a pass.
Emphasis at the *edges* of a span (`**298 → 300**`) still matches; it is markup *inside* the span that
is missed, which is the commoner form in this corpus.

**It is not an exotic shape.** Over `docs/**/*.md` — 1,779 files — a mid-claim emphasis opening
(`\w \*\*\w` or `` \w `\w ``) occurs **103,578** times. The tool's prescribed use
(`docs/process-checklists.md:569`, *"Hunt a CLAIM with `find-claim.py`, never a line-based grep"*)
points it at exactly that corpus.

**Why the control cannot save it.** Property (c) catches a *dead search*: the control is a different
phrase and matches fine, so the run is certified working while the claim is missed. This is the
`grep -z` zero the file's own confession was written about (`scripts/find-claim.py:26-29`) — *"⛔ `grep -z` IS THE
TEXTBOOK FIX AND IT RETURNED ZERO. Worth knowing why"* — reproduced one layer up, with a tool instead of a one-liner.

**And nothing states the bound.** A grep over `scripts/find-claim.py` for
`markup|emphasis|asterisk|bold|inline code|backtick` returns **one** hit, `:156`, and it is about
capitalisation, not markup. Property (a) at `:34-36` promises *"a claim found by a reader is found by
this, however the author happened to wrap it"* with no caveat.

**Remedy — and I am deliberately not proposing the obvious one.** Stripping markup before matching
would make `` `before` `` and `before` indistinguishable, which breaks the identifier-hunting use at
`:69`. The minimum honest fix is a **stated bound plus a case**: say in the docstring that the span is
markup-literal, and either (i) warn when the pattern's tokens appear individually in a file while the
span does not — the same shape as the existing "control did not exercise the wrap path" warning at
`:49-55`, which is already a warning-not-refusal by the #56 reasoning; or (ii) offer
`--tolerate-markup` that allows `[*_`]*` between tokens, off by default. Either way the bound must be
written down: an instrument whose limits are unstated is the failure this file exists to end.

---

## Medium

### M-A — the whitespace-stderr count case asserts the WORD "character(s)" and cannot see the NUMBER; a byte count survives at 300/300 and makes the message false

`scripts/check-plan-code.py:3132-3133`:

```python
observed = ("NOTHING to stderr (0 bytes)" if not se else
            f"nothing but WHITESPACE to stderr ({len(se)} character(s))")
```

Its oracle, `scripts/check-plan-code.py:3895-3896`:

```python
case("...counted in CHARACTERS, because `se` is a str and `len` is not a byte count",
     any("character(s)" in r for r in _repws), True)
```

**Sever** — the single occurrence of that f-string fragment, `len(se)` → `len(se.encode())`:

- control **300/300** → severed **300/300 passed, rc=0**. **SURVIVOR.**

**And the message is then false, measured on a constructed input rather than argued.** A child writing
three U+3000 ideographic spaces, reaching the same arm:

```
PRISTINE :  nothing but WHITESPACE to stderr (3 character(s))
SEVERED  :  nothing but WHITESPACE to stderr (9 character(s))
```

That is r12 Claude L1's self-refutation returning with the polarity flipped — the finding whose text
at `scripts/check-plan-code.py:3123-3128` says *"measured, three U+3000 ideographic spaces report
'3 byte(s)' for 9 bytes"*. The comment measured the distinction; **the fixture cannot**. `_repws`'s
child writes `"   " * 200` (`scripts/check-plan-code.py:3879`) — 601 ASCII characters, where
`len(s) == len(s.encode())`, so the only input the case ever sees is one on which the two readings
agree. This is the project's own *"exercise the producer at two DISTINCT inputs"* rule applied to an
encoding axis instead of a count axis.

**Remedy:** one line in the existing fixture — make the whitespace non-ASCII (`"　" * 200`) and
assert the rendered NUMBER, not the word. Cost measured: I wrote the probe that proves it in 15 lines.

### M-B — r17 Claude L2 is confirmed live, and "Low" is no longer the right grade

The brief asks whether the else-arm bound at `scripts/check-plan-code.py:3154-3166` is still unguarded
and whether Low still holds. **Yes to the first, no to the second.**

**Sever** — exact insertion point: the sole production assignment in the `else:` arm, made conditional
so that the bound survives only for a stderr with no colon (the `_w3` fixture) and is dropped for one
with a colon (a real traceback):

```python
said = ("read the "
        "window — ⚠ and note a traceback with NO frames (for example "
        "under `sys.tracebacklimit = 0`) also lands here"
        if ":" not in se else "read the window")
```

- control **300/300** → severed **300/300 passed, rc=0**. **SURVIVOR.**

**Known positive proved, which is what r17 said was missing.** I built the fixture r17 declined to
build — a real `sys.tracebacklimit = 0` child reaching the arm — and ran it against both trees:

| | reaches the else arm | states the no-frame BOUND | raw stderr carries the colon line |
|---|---|---|---|
| pristine | True | **True** | True |
| severed | True | **False** | True |

So the bound is silently removed from the only world it is *about*, and nothing notices.

**Why Low is wrong now.** r17's recorded reason was a cost argument, in its own words: *"this component
is armed for THRASHING and a Low does not justify a third fixture."* That premise is **refuted by
measurement** — the third fixture is 15 lines, it works first time, and it is written out above. A
severity grade resting on a cost estimate must move when the cost is measured. Both siblings in this
same `said` ternary turned out High (the prefix) and Medium (the one-head case); the arm with *no*
falsifier in the direction that matters is not the least of the three.

### M-C — the "no self-granted pass" sentinel in `find-claim.py` validates the chmod, not the failure, so a dead world reports WRONG ANSWERS instead of NOT RUN

Three cases carry the text *"⛔ the chmod-000 world IS buildable here — if THIS fails, the three cases
below were NOT RUN and must not be read as passes"* — `scripts/find-claim.py:910`, `:924`, `:943`. All
three are satisfied by the same precondition shape, `os.access(locked, os.R_OK)` at `:633`, `:709`,
`:752`.

**That precondition checks that the `chmod` took.** It does not check that the operation under test
actually fails. On 3.14 the `chmod` takes (`os.access` → `False`, measured), the sentinel at `:943`
**passes**, and the two cases it guards then report a *wrong answer* (`got 0 want 2`, `got False want
True`) rather than the NOT RUN the sentinel's own text promises. H-A is therefore visible as two
confusing reds instead of one honest CANNOT RUN — and the comment at `:748-752` explicitly says this
sentinel replaced a self-granted pass *so that* this would not happen.

This is the memory lesson *"a BOUND enumerates what is WITNESSED"*: the sentinel witnesses the chmod
and claims the world. **Remedy:** make the sentinel witness the *behaviour* — probe `is_file()` (or
`stat`) on the symlink directly and return the `-1` NOT-RUN sentinel when it does not raise. The other
two probes (`:633`, `:709`) rest on `os.walk(onerror=…)` rather than `pathlib`'s wrapper and were green
on both interpreters, so they are not currently defective — but they share the blind sentinel and
should share the fix.

---

## Low

### L-A — the one comment that would have caught H-A version-qualifies its sibling claim and not itself

`scripts/find-claim.py:359-361` writes: *"under python 3.12, `Path.is_file()` RETURNS FALSE for a path
that no longer [exists]"* — correctly naming the interpreter it was measured on. Twelve lines earlier,
`:353-354` and later `:730` write the sibling behaviour — *"`is_file()` raise[s]"* on a permission
error — with **no version at all**. Both were measured on 3.12; only one says so. This repository's own
rule is *"Record which build a manual check was verified against"* (`CLAUDE.md` → Gates), and this is
the single edit that would have made H-A visible when it was written rather than today.

PROSE FLOOR: a finite correction, two comments, no redesign.

---

## Checked and found SOUND

Each of these is a place I expected to find the Codex half's class and did not. The severs are listed
with both numbers, because a mutation that crashes the suite is a survivor and not a kill.

1. **The extractor's CALL SITE is covered — `lines_after_frame_runs` is genuinely the producer of
   `heads`.** This was my strongest hypothesis (the *"unit coverage does not compose — mutate the CALL
   SITE"* shape: the extractor has its own unit cases at `:4364-4444`, so the report could have been
   reading something else). Sever at the sole production assignment
   `heads = lines_after_frame_runs(se)` → `heads = [l.strip() for l in se.splitlines() if l.strip()][:2]`:
   control 300/300 → **297/300**, three cases red (`#280` no-frame bound, the one-head quote, and the
   exception-naming case). Covered.

2. **The two-head ORDER claim at `:4090` has a real falsifier.** Sever `" · ".join(heads)` →
   `" · ".join(heads[::-1])`: control 300/300 → **299/300**, killed via
   `[FAIL] ...and both lines are there, in the order the child printed them`. My sweep flagged this
   case as ambient (both markers are the fixture's own), and the sever refutes that worry: the quoted
   block precedes `diagnostic_tail` in the report string, so `r.index` resolves against the harness's
   output, not the child's. Nor is it vacuous — `any()` over the empty generator would be `False`
   against `want True`.

3. **The whole repository holds exactly FOUR string constants pinned by an equality oracle, and only
   one of them has H1's shape.** AST sweep over `scripts/*.py`: 4 pinned, **3 with no read-back out of
   a rendered value** — `check-plan-code.py:606 _QUOTED_PREFIX` (occurrences in file: **3** = definition
   + one production use + the oracle; this is the Codex half's H1), `check-review-recorded.py:124
   ABSENT_ENTRY` (5), `check-surface-recall.py:63 FIXTURE_PREFIX` (7). The latter two are **sound for a
   reason worth recording**: each is pinned against an **independent second source** rather than
   against a literal copy of itself — `ABSENT_ENTRY` against `_GIT_DELETION` at `:1799` (with `:1793-1794`
   recording that the earlier version took both sides from the same constant and the mutation moved
   both), and `FIXTURE_PREFIX` against **another module's** `_ratmod.FIXTURE_PREFIX` at `:628`.
   ⭐ **This sharpens H1's remedy:** what the prefix needs is a second independent reader, and
   reading it back out of the rendered report is only one way to get one.

4. **The ambient-satisfaction class is CONCENTRATED, not diffuse — which is itself evidence for the
   thrashing call.** AST sweep across twelve of this branch's guards: **195 literal substring-tests
   over a rendered value**, of which **14** also have that literal in a string constant of the fixture
   that produced the value. **Twelve of the 14 are in `check-plan-code.py`'s diagnostic-report
   component.** The two outside it — `check-main-drivable.py:4957` (`'DEBT'`) and
   `check-surface-recall.py:773` (`'NOT-WHAT-IT-SENDS'`) — are legitimate pass-throughs: the claim *is*
   "the detail the fixture declared reaches the verdict", and there is no second harness path that
   could supply it.
   The discriminator, stated so the sweep can be replayed: a flagged case is defective only when the
   rendered value has a **second harness path** that supplies the literal independently of the
   mechanism the case names. In this report that second path is `diagnostic_tail(so, se)`, concatenated
   into the same string at `scripts/check-plan-code.py:3180`. Of the twelve, `:3458` (both stream
   halves), `:4211`/`:4215` (the window pair, deliberately asserted True/False over the same marker),
   `:4798`/`:4812` (the home-escape report quoting the route the fixture contains), `:5357`/`:5379`,
   `:4703`/`:4870` (the child's message reaching the reader) are all pass-throughs where the fixture
   supplying the literal **is** the property. Only `:4015` is the real thing, and the Codex half has it.

5. **Counts, every one re-derived by running rather than read.** Independent JSON walk over
   `scripts/mutations/`: **62 manifest files, 1552 entries, 1560 edit anchors**. The script's own
   readers, driven directly: `load_manifests` → **1552 entries, 0 problems**; `EXPECTED_MUTATIONS` →
   **62 keys summing to 1552**; entries naming `scripts/check-plan-code.py` → **150**. Suite **300**;
   `--binding` **1560 / 1552**. All five agree.

6. **Every anchor in every manifest binds exactly once in the pristine tree — tested as `count != 1`,
   so the orphan direction is covered.** Independent scan, not `--binding`: **1560 anchors checked,
   ZERO with `count != 1`**. (A count of 0 is the orphan that voided a sibling branch's ratchet for
   days; "multiplied" alone is blind to it.)

7. **Cross-interpreter sweep over every guard with a `--self-test`: 54 guards, run under the CI pin
   (3.12) and locally (3.14), with `markdown-it-py==4.2.0` installed in both venvs. Exactly ONE
   diverges — `find-claim.py`, 86/86 vs 84/86.** Everything else is byte-identical in its verdict,
   including all five guards named in the brief: `check-main-drivable` **438/438**,
   `check-withdrawal` **179/179**, `check-provenance` **155/155**, `codex-frontier-model` **51/51**,
   `check-plan-code` **300/300**. ⚠ My first pass of this sweep mis-reported
   `check-paid-caller-arrival` and `check-storage-independence` as "no count" — that was my output
   regex failing to match their formats, not a CANNOT RUN. Re-run individually they are **32/32** and
   **50/50**. Correcting it here rather than leaving a wrong negative in the record.

8. **`check-withdrawal.py`'s local CANNOT RUN is its dependency, correctly declared and correctly
   wired.** On the system interpreter it refuses with `ParserUnavailable: markdown-it-py is not
   importable … ⛔ Treat this as NOT RUN, not as a pass`. `requirements.txt` pins
   `markdown-it-py==4.2.0`, `.github/workflows/ci.yml:83` and `:704` install it, and with it installed
   the suite is **179/179** on both 3.12 and 3.14. No finding. (This is the right behaviour, and worth
   naming: it refuses rather than guessing "no boundary", which it says is the lenient direction.)

9. **`check-ratchet-contract.py` is green over the branch — 56/56 self-test, `ratchet contract OK`
   over 46 discovered guards — and `find-claim.py` IS covered by it, through the second population.**
   I expected it to fall through the net and it does not. Driven directly: `discover_guards` returns
   **46** and does not include `scripts/find-claim.py` (`GUARD_PATH_RE` keys on the `check-` name),
   but `discover_self_tested_nonguards` (`scripts/check-ratchet-contract.py:433`) returns **22**
   scripts and `scripts/find-claim.py` is one of them — the R4W rule that demands a
   `scripts/mutations/<name>.json` for a self-tested script outside the guard population. It has one,
   with 25 entries. Its CI caller is `.github/workflows/ci.yml:179-180`.
   ⚠ What R4W cannot see is H-A: it asks whether a manifest EXISTS, not whether the control is green
   on the interpreter the reader is running.

---

## CANNOT RUN

- **The full `--mutate .` sweep (1552 entries) and the eight-shard matrix: NOT RUN. Treat as NOT
  CHECKED.** Eight local shards is a measured CANNOT RUN on this hardware, not a slow pass —
  `check-rc-contract.py --self-test` alone wants ~5.3 cores and blows `SUITE_TIMEOUT = 120` during the
  *control* pass. What I ran instead is the scoped pruned-copy run over `find-claim.json` (25 entries,
  6.0s), which exercises staging, `child_env`, subprocess spawn, `parse_fail_names` and exact-`expect`
  attribution — the real instrument, with only the input set changed. **It does not re-prove the
  whole-manifest ratchet. CI does that, and CI is authoritative here.**
- **The exact interpreter boundary for `Path.is_file()`'s permission behaviour is UNVERIFIED.** No
  Python 3.13 is installed on this machine; I measured 3.10, 3.12 and 3.14 only. H-A's finding does not
  depend on the boundary — 3.14 is red, 3.12 is green, and that is enough — but any fix note that says
  "3.13+" is citing `check-python-pin.py`'s prior measurement of a *different* `OSError`, not mine.
- **Not attempted, and not claimed:** `test:integration`, `test:e2e`, real Jest-results validation,
  PR-event guard forms, and anything requiring a live Supabase stack or a browser. The harness is
  structurally browserless — `HARNESS_TREE` stages `node_modules/typescript` only.

---

## Instruments

Four AST sweeps (constant-equality oracles repo-wide; ambient-satisfaction candidates per guard;
case-corpus reconciliation; the literal/fixture cross-reference), four severs over green controls, two
constructed-world probes (`U+3000` whitespace; a real `sys.tracebacklimit = 0` child), one scoped
mutation run at two interpreters, one 54-guard × 2-interpreter self-test matrix, two venvs
(`python3.12` and `python3.14`, both with `markdown-it-py==4.2.0`), and four hand-built corpora for
`find-claim.py`. Sweep scripts are at
`…/scratchpad/r18lab/sweep/sweep{1,2,4,5,6}.py`; the sever driver, which **refuses** unless the target
text occurs exactly once, is at `…/scratchpad/r18lab/sever.py`. Nothing was written to the worktree
but this document.

---

## Thrashing or prose floor

**My verdict: THRASHING in `check-plan-code.py`'s diagnostic-report component — I agree with the Codex
half on the call and on the component. I disagree with its proposed redesign on two specific points,
and I think the round-18 picture changes what a Phase 6 review should look at.**

### The thrashing call, with the mechanism test applied per finding

`docs/dev-process.md:113` requires *two consecutive rounds whose findings came from the previous
round's own fix, in one component*. Satisfied, and not by a count:

| finding | caused by the previous round's fix? | thrashing or prose floor |
|---|---|---|
| Codex H1 (`_QUOTED_PREFIX` pin guards the constant) | **Yes** — r17's own fix added the pin | THRASHING |
| Codex M1 (one-head case accepts zero heads) | **Yes** — r17's own fix added the case | THRASHING |
| **M-A** (character count unasserted) | **Yes** — r12 L1's fix changed the WORD and the case pinned the word | THRASHING |
| **M-B** (else-arm bound) | **Yes** — r17 recorded it as a known gap and declined it on a cost premise that is now refuted | THRASHING |
| Codex L1 (298→300 vs 297→300) | No — arithmetic | PROSE FLOOR |
| **L-A** (missing version qualifier) | No | PROSE FLOOR |
| **H-A, H-B, M-C** (`find-claim.py`) | **No — and this is the important half** | neither: FIRST REVIEW |

Four THRASHING findings across two consecutive rounds in one component. The arming condition is met
and I am not reaching for the four-round count to get there.

**The evidence that it is one component and not a habit:** my cross-guard sweep found **195** literal
substring-tests over rendered values across twelve guards, **14** of them ambient candidates, and
**12 of the 14 are in this one component**. The class is local. The two outside it are sound. That is
what a redesignable component looks like, as opposed to a methodology problem.

**The root cause, named as a mechanism:** the component's only observable is **one flat string** —
`scripts/check-plan-code.py:3167-3180` concatenates harness-owned prose, `said`, and
`diagnostic_tail(so, se)` into a single `report.append(...)` — the tail arrives at `:3180`. Every defect in the sequence follows
from that. Six false wordings passed their own cases (r15, r16, r17) because the marker could arrive
via the child; M1 passes because `ONLY_KILLER` arrives via the tail; H1 passes because the only pure
oracle available was one that never touches the render. A case written against this report **cannot**
distinguish "the harness said it" from "the child said it", so every assertion over it degrades into a
substring test, and the repair for each one creates the next.

### Where I disagree with the Codex half's redesign

Its proposal — *represent quoted lines and raw diagnostic output separately, render through ONE narrow
formatter, and assert that formatter's complete output at explicit zero-, one- and multiple-line
inputs* — is directionally right and **incomplete in two ways I can name with measurements**:

**1. "One narrow formatter" is not sufficient unless its output is OBSERVABLE WITHOUT the child tail.**
If the formatter still *returns* a single joined string, every future case is again a substring test
over a string the child contributes to — the defect rebuilt somewhere prettier. The load-bearing change
is that the harness-owned sentence and the raw tail become **two separately addressable values**
(a two-field structure, or two return values the report joins at the last moment), so a case can assert
over `harness_said` alone and a child can write anything it likes without reaching the oracle. The
Codex half says "separately" about the *representation*; the property that matters is separateness of
the **observable**. State it that way or the redesign under-delivers.

**2. The input axis is wrong. It is not zero-, one- and multiple-LINE; it is the SIX worlds the arms
select on.** Derived from the branch structure at `scripts/check-plan-code.py:3117` (`if not se.strip():`,
with a two-arm `observed` ternary inside it at `:3132`), `:3137` (`elif heads:`) and `:3154` (`else:`):

| world | selected by | fixture today |
|---|---|---|
| empty stderr | `not se.strip()`, `not se` | `_repfmt` |
| whitespace-only stderr | `not se.strip()`, `se` truthy | `_repws` — **ASCII only, which is M-A** |
| one quoted head | `heads` length 1 | `_rep1` — **zero-head hole is Codex M1** |
| two or more quoted heads | `heads` length ≥ 2 | `_repq` |
| prose, no exception line | `else`, no colon | `_w3` |
| **real no-frame traceback** | `else`, with a colon | **NONE — this is M-B** |

Three of the four THRASHING findings are missing *input kinds*, not missing line counts: M-A needs a
non-ASCII whitespace input, M-B needs a `sys.tracebacklimit = 0` child, Codex M1 needs a zero-head
report in the one-head case's world. A redesign that enumerates 0/1/many lines fixes exactly one of
the three. **Enumerate the six worlds, assert the formatter's complete harness-owned output in each,
and the class is closed.** I have working 15-line fixtures for the two that are missing.

### What I think the Phase 6 review must not be scoped to

The verdict arms an architecture review, so the scope matters as much as the call. **If Phase 6 is
pointed only at the diagnostic renderer, it will miss what round 18 actually found.** Seventeen rounds
converged on one component while `find-claim.py` — added by the same branch, with its own suite and its
own manifest — carried a **live red self-test and a lenient false-clean** that no round looked at.
H-A and H-B are not thrashing; they are a first review, and they were cheap to find. The composition
defect is in **where review attention went**, which is exactly the class
`docs/dev-process.md` says per-task review is structurally blind to. I would put two questions in the
Phase 6 brief alongside the renderer:

1. **What makes a guard's interpreter dependence visible before a dev machine finds it?**
   `check-python-pin.py` pins the version and warns that a local green is provisional; nothing
   *measures* a guard at more than one interpreter. The 54 × 2 matrix above took four minutes and found
   the one divergence. That is a candidate gate, not a review finding.
2. **Which of this branch's new guards have a review round at all?** `check-main-drivable.py` (+5130),
   `check-withdrawal.py` (+2120), `check-provenance.py` (+984), `find-claim.py` (+1132) all shipped
   inside a branch whose rounds were spent on `check-plan-code.py`. I measured their suites green and
   swept them for the two classes this round is about, and they are clean on both — but "green and
   clean on two classes" is not a review, and I will not let this document imply otherwise.

**Bottom line.** THRASHING on the diagnostic-quotation component: agreed, armed, with the redesign
amended as above. NOT CONVERGED on the branch, on the strength of H-A and H-B, which are new subjects
rather than another turn of the same screw.
