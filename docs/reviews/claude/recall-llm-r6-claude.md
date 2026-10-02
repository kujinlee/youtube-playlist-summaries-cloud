# Round 6, Claude half — the rc contract guard, v3 of R3 (backlog #201/#202)

**Verdict: NOT CONVERGED.** One Blocking, two High, two Medium, two Low.

Subject: `scripts/check-rc-contract.py` as it stands **uncommitted** on `semantic-recall-replication`,
the hook it observes (`.claude/hooks/surface-recall.sh`), the matcher whose exit codes are the
contract (`scripts/recall-llm.py`), and `scripts/mutations/check-rc-contract.json`.

⭐ **The headline: v3's "ONE assumption that remains" claim is FALSE, and the open set has moved a
FOURTH time rather than closed.** The remaining assumption is not *"the hook renders the probe
literally"*. It is **that the surrounding text is INVARIANT to the detail** — that the rendered
payload is `prefix + $OUT + suffix` with `prefix`/`suffix` independent of `$OUT`'s content. I
constructed **eight** arms that violate that, and every one presents backlog #201's exact
reader-visible defect — a sentence ending in a label with nothing after it — while
`check-rc-contract.py` exits 0 printing *"no arm promises a detail it might not have"*.
**Four of the eight carry the `[ -n "$OUT" ]` test R3's own rule statement demands.** That is B1.

⤳ **The trail, stated as one sentence per round, because the shape is the finding:**

| round | what R3 enumerated | how it was escaped |
|---|---|---|
| r3 M4 | literal adjacency to `Detail:` | the append idiom one statement away |
| r5 H1 | label SPELLINGS, `("Detail:", "detail:")` | `Reason:`, `Details:`, `detail -`, bare `unreadable:` |
| r6 B1 | the detail's POSITION ("text before the probe") | `Detail: $OUT.`, `[$OUT]`, `got $OUT ok` |
| **r6 (this doc)** | **render-INVARIANCE (an equality between two observations)** | **a transformed detail, or a surround that branches on `$OUT`** |

⭐ **The structural reason this keeps happening, and it is not "the author missed a case".** #201 is a
property of **ONE** observation: *what the hook renders with no detail ends in a promise.* Every
version of R3 so far, v3 included, tests a **relationship between TWO** observations
(`renders(probe) − probe == renders("")`). The arm's author controls both sides independently, so the
relationship is satisfiable while the property is violated. This repo already owns that lesson —
*assert the PROPERTY, not the mechanism*. The honest fix may be to **state R3's bound** (it detects
only the invariant-surround family) rather than to claim there is no vocabulary left, because the
property itself is semantic and recovering it rebuilds the label vocabulary R3 exists to escape.

⚠ **The SHIPPED hook is correct, and I could not break it.** `python3 scripts/check-rc-contract.py`
→ rc=0; `--self-test` → 84/84; the declared count in the docstring agrees with the run. The three
guarded arms (`0)`, `3)`, and the `5)`/`6)` static-sentence-plus-guarded-detail pair) are all
genuinely sound, and v3 classifies each correctly. **Every finding below is about the guard's REACH,
not a live defect in the hook** — which is the same basis on which the round-6 Codex half's B1 was
Blocking.

I verified and do **not** re-report the five things the Codex half established this round: R4
membership, the absence of global leakage from the suite's `globals()` patching, `_read_or_refuse`'s
OSError conversion, and M3/L4's raw-count acceptances and refusals.

---

## BLOCKING

### B1 · v3's remaining assumption is render-INVARIANCE, not literal rendering — eight arms reproduce #201 for the reader while the guard reports clean, four of them carrying the `-n` guard R3 demands

`scripts/check-rc-contract.py:368-372` states the claim this finding refutes:

```
      ⭐ SO THIS NO LONGER ASKS WHERE $OUT SITS. It DELETES the detail from what the hook
      rendered and compares that against what the hook rendered with no detail at all. Equal
      means the surrounding text survived the detail's absence — which IS the promise,
      wherever it sat, on either side, however many times.
```

and `:53-55` states the bound it claims:

```
      The ONE assumption that remains is stated and gated: the hook must render the probe
      LITERALLY, and an arm that transforms `$OUT` fails the `_PROBE not in with_detail` test
      above and is skipped rather than guessed at.
```

The implementation is `scripts/check-rc-contract.py:357-381`:

```python
        with_detail = observe(hook_src, rc, _PROBE)
        if _PROBE not in with_detail:
            continue                      # the arm does not interpolate $OUT: nothing to promise
        deleted = with_detail.replace(_PROBE, "")
        if not deleted.strip():
            continue                      # it forwards the detail ALONE — the `0)` arm's shape
        without = observe(hook_src, rc, "").rstrip()
        if deleted.rstrip() == without:
            bad.append(rc)                # the text around the detail outlived the detail
```

`deleted.rstrip() == without` is an **equality between two independent observations**. It detects
#201 only when the surround is byte-identical (mod trailing whitespace) across both. There are two
ways to break that, and both are live.

**Family (a) — the detail is TRANSFORMED, so the documented gate SKIPS the arm.** The gate is not a
refusal; it is `continue`, and `dangling_detail` then returns `[]`, which `verdict` reads as "no
problem". *"Skipped rather than guessed at"* describes a silent pass.

**Family (b) — the SURROUND branches on `$OUT`, so `deleted != without` for a reason other than the
detail,** and the comparison reports the arm fine. R3's written rule is *"No arm interpolates `$OUT`
AFTER ANY OTHER TEXT without guarding on `[ -n "$OUT" ]` first"* (`:41-42`) — these arms **do**
guard, and the reader still gets `Detail:` with nothing after it.

**Reproduction.** Control first, per method: the known positive is caught and the shipped shape is
not, so the probe discriminates before any negative is trusted.

```
label                                          R3 verdict  R4 verdict   what the READER sees at empty $OUT
CONTROL +ve  5) PAYLOAD="unreadable. Detail: $OUT"      [5]      []     'unreadable. Detail: \n'   ← caught
CONTROL -ve  shipped: static sentence + guarded detail  []       []     'unreadable.\n'            ← correct

(a) TRANSFORMED DETAIL — skipped by `_PROBE not in with_detail`
  Detail: ${OUT:0:10}                                   []       []     'unreadable. Detail: \n'
  Detail: $(printf %s "$OUT" | tr -d -)                 []       []     'unreadable. Detail: \n'
  Detail: $OUT (${#OUT} chars)                          []       []     'unreadable. Detail:  (0 chars)\n'

(b) SURROUND BRANCHES ON $OUT — `deleted != without` for a non-detail reason
  if [ -n "$OUT" ]; then PAYLOAD="unreadable. Detail: $OUT (end)"
                   else PAYLOAD="unreadable. Detail:"; fi    []   []    'unreadable. Detail:\n'
  PAYLOAD="unreadable."; if [ -n "$OUT" ]; then PAYLOAD="$PAYLOAD Detail: $OUT"
                         else PAYLOAD="$PAYLOAD  Detail:"; fi []   []   'unreadable.  Detail:\n'
  if [ -n "$OUT" ]; then PAYLOAD="unreadable.  Detail: $OUT"
                   else PAYLOAD="unreadable. Detail:"; fi     []   []   'unreadable. Detail:\n'
  PAYLOAD="unreadable. Reason:"
  [ -n "$OUT" ] && PAYLOAD="unreadable. Reason: $OUT Detail:" []  []    'unreadable. Reason:\n'
  5) PAYLOAD="PROBE-DETAIL-TEXT: $OUT"                        []  []    'PROBE-DETAIL-TEXT: \n'   (see L2)
```

**Two of these are not merely reader-visible — they are #201's original symptom verbatim**: the
rendered string is `unreadable. Detail:`, a sentence whose last token is a label. That is the exact
text `.claude/hooks/surface-recall.sh:70-74` records as the measured defect (*"the reader got a
sentence ending 'Detail:' with nothing after it — forever, because the marker persists"*).

**The adjacent negative that proves the comparison is doing work, not nothing:** the same
else-branch arm with a *trailing-whitespace-only* difference IS caught —

```
  if [ -n "$OUT" ]; then PAYLOAD="unreadable. Detail: $OUT"
                   else PAYLOAD="unreadable. Detail:"; fi     [5]      []
```

— because `rstrip()` erases that one difference. So the evasion is specifically about the surround
differing, and the margin is a single interior character.

⤳ **This answers the `rstrip`/`strip`/interior question directly: the combination is right at both
ENDS and wrong in the MIDDLE.** `rstrip()` on both sides correctly absorbs the herestring's trailing
newline and any trailing space; leading whitespace is preserved on both sides and so cancels (I
confirmed `"$OUT — unreadable."` is caught, leading space and all). **Nothing normalises the
interior**, so one extra space anywhere inside the surround defeats the comparison — and because that
surround is whatever the `else` branch chose to write, the author of a hollow fallback controls it.

**End-to-end through `main`, over a staged tree, not just the function:**

```
--- canonical tree + 5) PAYLOAD="unreadable. Detail: ${OUT:0:10}" ---
rc = 0
rc contract: 6 code(s) defined, 4 handled by an arm, 2 declared unhandled
rc contract OK — every defined code is handled or declared, no arm promises a detail it
might not have, and no code that must speak is silent
```

The guard's success sentence asserts the negation of what the tree does.

**The boundary is the guard's own sentinel length, which is the sharpest evidence that family (a) is
ambient rather than principled.** `_PROBE = "PROBE-DETAIL-TEXT"` (`:335`), `len == 17`:

```
  Detail: ${OUT:0:15}   R3=[]    with='… Detail: PROBE-DETAIL-TE'
  Detail: ${OUT:0:16}   R3=[]    with='… Detail: PROBE-DETAIL-TEX'
  Detail: ${OUT:0:17}   R3=[5]   with='… Detail: PROBE-DETAIL-TEXT'
  Detail: ${OUT:0:18}   R3=[5]   with='… Detail: PROBE-DETAIL-TEXT'
```

Whether R3 sees a truncating arm is decided by an implementation constant of the **guard**, not by
any property of the **hook**. A cap of 16 is invisible; a cap of 17 is caught. Truncating a detail
for a one-line hook notice is an ordinary thing to write.

⤳ **A ninth arm belongs to family (a) and is filed as H1 because its primary defect is different:**
`5) PAYLOAD="unreadable. Detail: $(jqq -r . <<<"$OUT")"` — a misspelled or absent tool — renders
`unreadable. Detail: ` at **every** firing and reaches the same skip. It is the most plausible member
of family (a) I found, and it needs no unusual bash.

**What would refute B1:** `dangling_detail` returning `[5]` for any of the eight arms above; or R3's
docstring being narrowed to state the invariance bound explicitly, in which case these become
*declared* gaps rather than a false claim. Arguing the shapes implausible would NOT refute it —
`${OUT:0:N}` truncation, an `else` branch and a missing tool are all ordinary bash. ⚠ I am not
claiming the three previous members were *judged* implausible; that would be an inference about
their authors. What the record shows is that each fix was written as closed and was escaped by the
next round, three times, which is the base rate this finding should be weighed against.

**Proposed direction — UNVERIFIED CODE, I ran none of it.** Two options, and I think the first is
right: (1) **state the bound** in R3 and in the `continue` comments — R3 detects an unguarded
interpolation *whose surround is invariant to the detail*, and a transforming or branching arm is
NOT examined — then file the residue. That is honest and costs nothing. (2) If a mechanical check is
wanted, the property is about ONE render, so probe `renders("")` directly and refuse a payload whose
final non-space character is `:` or `-`, plus a trailing-bracket check — but that **is** a label
vocabulary, which is the thing this redesign exists to escape, so it trades a false claim for a
reopened open set. Choosing (1) and saying so in the round document seems to me the better trade.

---

## HIGH

### H1 · `observe` reads a bash FATAL ERROR as silence, and its documented refusal is unreachable by construction for the one hook it exists to observe

`scripts/check-rc-contract.py:309-311` states the contract:

```python
    The empty string means the hook stayed silent. ⛔ A non-zero bash exit or unparseable output is
    a CANNOT-RUN and never an empty answer: silence and "I could not look" must not be the same
    observation, which is the contract this guard exists to police.
```

The mechanism is `:321-323`:

```python
        if proc.returncode != 0:
            raise CannotRun(f"the hook exited {proc.returncode} at rc={rc}, which it documents it "
                            f"never does ('NEVER BLOCKS, NEVER FAILS THE CALL')")
```

**That predicate cannot fire for the subject.** `.claude/hooks/surface-recall.sh:39` is
`set -uo pipefail` — **no `-e`** — and `:92`/`:95` are `[ -n "$PAYLOAD" ] || exit 0` and `exit 0`.
The hook's own header (`:31`) states the property as a design commitment: *"NEVER BLOCKS, NEVER
FAILS THE CALL. `exit 0` unconditionally."* So **every** bash-level failure inside a `case` arm
arrives at `observe` as `returncode == 0` with empty stdout — and `capture_output=True` collects
stderr and discards it.

**Reproduction — a missing command, which is version-independent and the worst case.** An arm that
pipes `$OUT` through a tool that is absent or misspelled:

```
arm:  5) PAYLOAD="unreadable. Detail: $(jqq -r . <<<"$OUT")" ;;

raw bash:  returncode 0
           stdout  '{"hookSpecificOutput": {… "additionalContext": "unreadable. Detail: \n"}}'
           stderr  '…/surface-recall.sh: line 8: jqq: command not found'      ← DISCARDED
observe(h, 5, _PROBE) : 'unreadable. Detail: \n'
observe(h, 5, "")     : 'unreadable. Detail: \n'
handled_codes(h,{0,5}): {0, 5}     ← rc 5 reads as fully handled
dangling_detail       : []         ← skipped: the probe did not survive
silent_codes          : []         ← not silent, so R4 has nothing to say
```

**This arm is hollow at EVERY firing, not merely from the second** — the reader gets
`unreadable. Detail: ` whether or not the matcher produced a detail, forever — and all four rules
report agreement. End-to-end over a staged tree:

```
--- canonical tree with 5) PAYLOAD="unreadable. Detail: $(jqq -r . <<<"$OUT")" ---
rc = 0
rc contract: 6 code(s) defined, 4 handled by an arm, 2 declared unhandled
rc contract OK — every defined code is handled or declared, no arm promises a detail it
might not have, and no code that must speak is silent
```

⚠ **A second shape, narrower, recorded because it fails differently.** A bash-4 expansion on this
machine's bash 3.2 (`GNU bash, version 3.2.57(1)-release`, the macOS default) kills the arm outright:

```
arm:  5) PAYLOAD="unreadable. Detail: ${OUT,,}" ;;
raw bash:  returncode 0, stdout '', stderr '… bad substitution'
observe(): ''                     ← read as "the hook stayed silent"
handled_codes(h, {0,5}): {0}      ← read as "rc 5 has no arm"
```

Here R4 *does* redden (rc 5 is in `MUST_NOT_BE_SILENT`), but R1's diagnosis is wrong — it reports
*"no `case` arm in the hook names it"* about an arm that is right there. Move the same breakage to a
code with a `DELIBERATELY_UNHANDLED` row and even that is lost: canonical tree plus
`4) PAYLOAD="rejected. Detail: ${OUT,,}"` → rc=0, `rc contract OK`. ⚠ This second shape depends on
the bash version; the `jqq` shape above does not, and a CI runner on bash 5 would reproduce it
identically.

An arm that exists, is reached, and fails is reported as agreement. This is the repo's own standing
rule inverted — *"Cannot run" is a FAILURE, never a pass* — in the file whose entire job is refusing
that conflation, and the refusal it wrote for the purpose is keyed on a signal its subject is
documented never to emit.

**Severity reasoning:** High rather than Blocking because both shapes need an arm that is *already
broken* at the bash level, so the guard is failing to catch a second defect rather than blessing a
well-formed one — but High rather than Medium because the `jqq` shape ships a payload that is hollow
on **every** firing while all four rules say clean, and because the guard's single stated protection
against confusing silence with "I could not look" is dead by construction for its own subject. ⤳ It
also compounds B1: the two findings share the `_PROBE not in with_detail` skip, so a transforming arm
and a failing one are indistinguishable to R3 and both pass.

**Fix direction — UNVERIFIED, not run:** `observe` already has `proc.stderr`; refusing when stderr is
non-empty (or when it matches bash's own diagnostic prefix) would reach this, and the shipped hook
produces empty stderr at all six codes, so a control exists. I did not implement or measure it.

**What would refute H1:** `observe` raising `CannotRun` for the `${OUT,,}` arm; or a demonstration
that the hook can exit non-zero, which would make the existing predicate live.

### H2 · The gate the docstring calls "gated… rather than guessed at" has NO case exercising its real subject, and its one mutation entry tests the opposite direction

B1 family (a) rests on `if _PROBE not in with_detail: continue` (`:358`). The docstring (`:53-55`)
presents that clause as the thing that makes the remaining assumption safe. **Nothing tests it
against a transforming arm.**

Measured over the suite (lines 567-936, the whole of `_self_test`):

```
$ sed -n '567,936p' scripts/check-rc-contract.py | grep -n '${OUT\|OUT:0:\|OUT//\|OUT,,\|#OUT\|OUT:-\|tr \|head -1'
  (no output)  — no case stages an arm that transforms $OUT
```

Every fixture interpolates `$OUT` **literally**. The clause is therefore reached only by arms that
do not interpolate at all (a code with no arm, where `with_detail == ""`), which is a different
branch of its meaning.

Its one mutation entry inverts the gate, and the case named to kill it does not involve a transform:

```json
{ "name": "the $OUT-interpolation gate inverts, so only arms that DO NOT use $OUT are examined",
  "edits": [["if _PROBE not in with_detail:", "if _PROBE in with_detail:"]],
  "expect": "an unguarded detail is refused whatever the label ('detail -')" }
```

Inverting the gate is killed by any arm that interpolates literally. **Deleting the gate entirely, or
narrowing it, is a different mutation and there is none** — and the direction that matters (an arm
whose probe does not survive) has no case, so no mutation of this clause can be attributed to it.
This is the repo's recorded *a test that cannot fail* shape: the clause's load-bearing behaviour is
asserted in prose and exercised by nothing.

**What would refute H2:** a case in the 84 whose fixture transforms `$OUT` (substring, substitution,
pipe, `tr`, `${#OUT}`), or a mutation entry whose `expect` names such a case.

---

## MEDIUM

### M1 · A `DELIBERATELY_UNHANDLED` row's premise is never falsified when the hook STARTS acting on that code — round 4 B2 in the mirror direction, and the summary line prints a count that cannot be right

`verdict` (`:447-450`) short-circuits on handledness **before** it ever consults the row:

```python
    for name, code in sorted(defined.items(), key=lambda kv: kv[1]):
        if code in handled:
            continue
        if code in DELIBERATELY_UNHANDLED:
            continue
```

So a row saying *"the hook deliberately does not act on this code"* is checked only in the world
where the hook does not act on it. Round 4 B2 killed the rc-0 row for the symmetric reason —
`:124-129` records it: *"A row whose premise is 'this is already handled' is a row that stops
checking whether it is."* The surviving rows assert the opposite premise and are unchecked in exactly
the same way.

`DELIBERATELY_UNHANDLED[4]` (`:145`) asserts: *"RESPONSE REJECTED can only arise on the `--arm`
path, and this hook runs `--fire` only."* Add an arm and the row becomes false, silently:

```
--- canonical tree + 4) PAYLOAD="response rejected." ---
rc = 0
rc contract: 6 code(s) defined, 5 handled by an arm, 2 declared unhandled
rc contract OK — …
handled set: {0, 3, 4, 5, 6}
```

⚠ **The printed summary is self-refuting and nobody reads it**: `5 handled` + `2 declared unhandled`
= 7 over `6 code(s) defined`. The arithmetic is visible in the guard's own success output and no rule
asserts it.

**Severity:** Medium, not High — the consequence is a stale *reason*, not a swallowed code, and rc 4
cannot be emitted on the `--fire` path today (the row's verdict survives even though its falsifier
does not, as `:154-157` already concedes about a different property). It earns a row because it is
the one defect class this file has already paid for once, in the other direction.

**Fix direction — UNVERIFIED:** one line in `verdict` — a code that is both `handled` and in
`DELIBERATELY_UNHANDLED` is a contradiction between the hook and the row, and should be a problem.
That also makes `len(handled) + len(DELIBERATELY_UNHANDLED) <= len(defined)` an invariant worth
asserting. I did not write or run either.

**What would refute M1:** any existing rule that reddens on the staged tree above.

### M2 · The `EXPECTED_MUTATIONS` provenance trail does not reconcile with the file — it accounts for 24 entries and a sum of 1162, while the file holds 25 and 1163, and its last two steps both start from 1162

`scripts/check-plan-code.py:1362` is `"scripts/check-rc-contract.py": 25` and `:3828` pins
`sum(EXPECTED_MUTATIONS.values()) == 1163`. Both are **correct**: I derived the table sum as 1163
over 56 entries, and the manifest holds exactly 25 entries. The defect is in the narrative that is
the only record of *why* the number moved.

Reading the trail at `:3792-3826` as consecutive deltas:

| trail line | stated delta | implied manifest count |
|---|---|---|
| `:3794` round 5 | `1148 -> 1160`, "+12 … going 10 -> 22" | 22 |
| `:3802` fixture-variation | `1160 -> 1162`, "+2" | 24 |
| `:3809` after the red sweep | `1162 -> 1161`, "-1 … coverage rises 10 -> 23" | 23 |
| `:3824` round 6's Blocking | **`1162 -> 1163`**, "+1" | 24 |

The last row's *from* value is 1162 while the preceding row left it at **1161**; and the trail's
terminal count is **24** against a file holding **25**. One entry's provenance is unrecorded, and
`case("the declared counts are the real ones", …)` cannot see it — it compares the table to the pin,
both of which were updated together, and neither to the narrative.

This is the repo's declared-count-drift class with the roles swapped: the counts are right and the
**explanation** has drifted. It matters because `check-plan-code.py:3809`'s whole point is that a
FALL needs a written reason, and the written reasons no longer add up to the file.

**What would refute M2:** a reading of those four comment blocks under which the deltas chain and
terminate at 25/1163 — e.g. if `1148` or `1161` refers to a different baseline than I assumed. I
read them as consecutive edits to the one pin, which is how they are formatted.

---

## LOW

### L1 · The size figures this fold's deferrals rest on count docstring PROSE as code, and are now stale — the executable ratio is 10.3x, not 16.6x

`docs/backlog.md:234` (#206) and `:235` (#207) each carry, identically:

> *"Derived properly: 904 total = 546 production (382 code) + 359 suite (267 code), against a hook of
> 96 lines / 23 code / 5 case-arm lines. **The defensible ratio is production CODE to hook CODE:
> 382/23 = 16.6x.**"*

⚠ **In scope, not pre-existing:** `git diff docs/backlog.md` shows 3 insertions and **both**
occurrences of `382/23 = 16.6x` are among them, so this figure is part of the uncommitted fold under
review rather than an inherited row.

That correction (from a wrong 61x) was the right move and is still imprecise in the same direction.
Derived at the current tree, with the method stated:

| metric | value | how |
|---|---|---|
| total lines | **936** (rows say 904) | `wc -l` |
| suite marker | line **567** | the `# ─… the suite` line |
| production incl. comments | **566** (rows say 546) | lines 1..566 |
| suite incl. marker | **370** (rows say 359) | 936 − 566 |
| production, non-blank, non-`#` | **390** (rows say 382) | ← **this is the rows' "382"** |
| production, non-blank, non-comment, **non-docstring** | **238** | `tokenize` + `ast.get_docstring` spans |
| hook, non-blank non-comment | **23** | agrees with the rows and with Codex |

So the rows' "382 code" is *non-blank non-comment lines counting docstring text as code* — and this
file's docstrings are ~152 lines of prose arguing about the design. The **executable** production
code is **238 lines → 238/23 = 10.3x**, while the whole file against the hook is **936/23 = 40.7x**.

Three statements, each true of a different metric, and the one that bears on *"the guard earns its
existence; its reader does not earn 91 lines"* is the executable one. 10.3x is materially less
damning than 16.6x; 40.7x is materially more. The rows should carry the definition alongside the
number, and both are now stale by the v3 fix (+32 total, +8 production non-comment).

**What would refute L1:** a line-counting definition under which the production half yields 382
executable lines at this tree. I could not construct one.

### L2 · `_PROBE` is an unreserved sentinel, and `replace` deletes the hook's own occurrences of it too

`deleted = with_detail.replace(_PROBE, "")` (`:374`) removes **every** occurrence. If the hook's own
static text contains `PROBE-DETAIL-TEXT`, the surround is deleted along with the detail:

```
  5) PAYLOAD="PROBE-DETAIL-TEXT: $OUT"
     with    = 'PROBE-DETAIL-TEXT: PROBE-DETAIL-TEXT\n'
     deleted = ': \n'
     without = 'PROBE-DETAIL-TEXT: \n'    ← what the reader sees: a dangling label
     R3 = []   R4 = []
  5) PAYLOAD="PROBE-DETAIL-TEXT $OUT"
     deleted = ' \n'  → `not deleted.strip()` → SKIPPED entirely
```

Low because the shipped hook does not contain the string and no plausible wording would introduce it
— but it is the second of the two `continue` skips reached while a promise stands, and the docstring
at `:368-373` claims `replace`'s non-positionality as a strength (*"two interpolations come free"*)
without noting that it is also non-discriminating. Worth one sentence, or a sentinel unlikely to
collide by construction.

**What would refute L2:** `dangling_detail` returning `[5]` for either arm above.

---

## Is v3's "only one assumption" claim true? Is there a fourth member?

**No, and yes.** Quoting the claim exactly (`:53-55`): *"The ONE assumption that remains is stated
and gated: the hook must render the probe LITERALLY."*

**There are two assumptions, and the undeclared one is the load-bearing one.**

1. *Declared:* the probe renders literally. **Real, and the gate is a SILENT PASS, not a refusal** —
   B1 family (a), H2. Its reach is set by `len(_PROBE) == 17`, measured at the boundary.
2. *Undeclared:* **the surround is INVARIANT to the detail.** `deleted.rstrip() == without` is an
   equality between two renders the arm's author controls separately. Any arm that branches on
   `$OUT` breaks it — B1 family (b) — and four such arms satisfy R3's written `-n`-guard rule while
   the reader gets `unreadable. Detail:`.

**The fourth member of the moving set is therefore an INVARIANCE vocabulary**, exactly parallel to its
three predecessors: r3 M4 enumerated *adjacency*, r5 H1 enumerated *label spellings*, r6 B1 enumerated
*position*, and v3 enumerates *the ways a render can differ* — implicitly, by assuming there is only
one (the detail). The reviewer's sentence the coordinator asked me to carry forward holds with one
word changed: **R3 no longer has a label vocabulary or a position vocabulary left to be incomplete,
and it still has an incomplete render-invariance vocabulary.**

⭐ **The thing worth saying beyond "here is member four":** every member has been found by asking
*what does this compare?* rather than *what does this enumerate?* v3 compares two observations; #201
is a property of one. **While R3 is phrased as a comparison, there will be a fifth member**, because
the set of reasons two renders can differ is not finite in any useful sense — which is the same
sentence the round-3 redesign note (`:264-265`) wrote about bash quoting, applied to its own
successor. The argument for **stating the bound instead of widening the detector** is that the
property is semantic: deciding whether `renders("")` ends in a promise requires reading English.
R3's deliberate strictness note (`:56-63`) already accepts refusing harmless unlabelled
interpolations rather than judging what "looks like a label" — the same reasoning says the honest
move now is to declare what R3 does not reach, not to add a fifth comparison.

---

## Could Not Establish

- **`python3 scripts/check-plan-code.py --mutate .` — NOT RUN**, by instruction (in flight
  elsewhere). Treat this document as saying nothing about the repo-wide sweep — in particular nothing
  about the OTHER 1,138 pinned mutations, or about whether this fold orphaned an anchor in another
  file. I ran this guard's own 25 entries individually against a staged copy instead: **25/25 killed,
  25/25 attributed, 0 survivors**, detailed in *Verified* below.
- **Whether any of B1's eight shapes would be written by a human.** Plausibility is a judgement, not
  a measurement. What I measured is the reader-visible render and the guard's verdict. I note that
  `${OUT:0:N}` truncation, an `else` branch and a misspelled tool are ordinary bash, and that each of
  the three previous versions of R3 was written as closed and escaped by the next round.
- **Whether H1's stderr-based repair false-fires.** I did not implement or run it. I did measure the
  control it would need: the shipped hook over all 6 codes × {probe, empty} is 12/12 `returncode=0`
  with `stderr=''`, so such a rule would not false-fire on the hook as it stands today — that is
  evidence about the control, not about the repair.
- **The design split question (R3/R4 to a hook-owned suite).** Answered below as an opinion with its
  reasoning, not as a measurement — I did not build either arrangement.
- **`observe`'s behaviour under a hook that writes to stderr legitimately.** The shipped hook does
  not, so I have no live example to reason from.

---

## The design question — would a hook-owned suite have caught this earlier?

**Partly, and the honest answer is that it would have caught B1 and NOT the class.** The round-6
Codex half proposed R1/R2 in the cross-file guard with R3/R4 as hook fixtures. I think that is right,
for a reason neither half has stated: **R3 and R4 are not cross-file rules at all.** R1 and R2
genuinely need both languages — one reads python constants, the other reconciles arms against them.
R3 and R4 read **only** the hook, through `observe`, and the matcher enters only as the source of the
`codes` set. They are a hook test wearing a contract guard's clothes, and that is why they are where
every finding in four rounds has landed.

Would it have caught round 6 B1 earlier? **The fixture-per-shape arrangement would have, because the
cost of adding a shape would have been one fixture line rather than a round trip through a
cross-language observer** — and B1's four shapes (`$OUT.`, `[$OUT]`, `got $OUT ok`, two interpolations)
are exactly the kind of table a fixture suite invites and a rule-shaped guard does not. It would
**not** have caught my B1: a fixture suite enumerates shapes the author thinks of, and family (b)
is not a shape, it is a *property of the comparison*. Nothing about file layout fixes that.

⚠ **The size argument should be made on the corrected numbers (L1), and it is weaker than the rows
say.** 238 executable production lines against 23 hook code lines is 10.3x — substantial, but the
bulk of this file is **not** code: ~152 lines of production docstring and a 370-line suite. Backlog
#196's real finding stands undisturbed and is the one I would act on: the hook has **no** self-test,
**no** mutation entry, and — verified — `grep -rl surface-recall scripts/ .github/` returns only
`scripts/check-rc-contract.py` and `.github/workflows/ci.yml`, and no file in `scripts/mutations/`
names it. Both live defects of this fold were on the one side of the seam nothing drives. Moving R3/R4
to a hook-owned suite is the same work as giving the hook its first mutation entry, which is why I
would do it.

---

## Verified

| What I ran | Result | Bearing |
|---|---|---|
| `python3 scripts/check-rc-contract.py` | `rc contract OK`, rc=0 | live run green |
| `--self-test` | `84/84 self-test cases passed`, rc=0 | declared count at `:99` agrees with the run |
| the shipped hook's four arms through `dangling_detail` + `silent_codes` | `[]` and `[]` | **no live defect in the hook** |
| known-positive control before every negative | `Detail: $OUT` → `[5]`; shipped → `[]` | the probe discriminates |
| 8 constructed arms (B1) | `R3=[]`, `R4=[]`, reader sees a hollow promise | **B1** |
| `${OUT:0:N}` at N = 15/16/17/18 | `[] [] [5] [5]` | **B1** — the boundary is `len(_PROBE)` |
| `main()` over a staged tree with the truncating arm | rc=0, "no arm promises a detail it might not have" | **B1**, wired |
| `5) … $(jqq -r . <<<"$OUT")` arm (missing command), raw bash | rc **0**, payload `'unreadable. Detail: \n'`, stderr `jqq: command not found` discarded | **H1** — version-independent |
| that arm through all four rules | `handled={0,5}`, `dangling=[]`, `silent=[]` | **H1** — hollow at every firing, reported clean |
| `main()` over a staged tree with that arm | rc=**0**, `rc contract OK` | **H1**, wired |
| `${OUT,,}` arm on bash 3.2, raw bash | rc **0**, stdout `''`, stderr `bad substitution` | **H1** — second shape, version-dependent |
| `main()` over a staged tree with a broken `4)` arm | rc=**0**, `rc contract OK` | **H1** |
| `main()` over a staged tree with a working `4)` arm | rc=0, `5 handled` + `2 declared` over `6 defined` | **M1** |
| grep for a transforming fixture in lines 567-936 | **zero** | **H2** |
| the gate's one mutation entry vs its `expect` | inverts the gate; killed by a literal-interpolation case | **H2** |
| `tokenize`+`ast` line counts, both halves | 936 / 566 / 370 / 390 / **238**; hook 23 | **L1** |
| probe-collision arms | `R3=[]` via the comparison and via the `deleted.strip()` skip | **L2** |
| the four new SHAPE cases at `{0,5}` **and** at full `CODES` | `[5]` in all eight runs | **attack 5 REFUTED** — the narrowing is not why they pass |
| `case "$OUT" in ?*)` guard and `! [ -z "$OUT" ]` guard | `R3=[]`, `R4=[]` — correctly passed | **a real strength**: v3 accepts guards no `-n` parser would |
| `Detail: ${OUT:-none}` (reader sees `Detail: none`) | `R3=[]` — correctly passed | **a real strength**: a label-vocabulary detector would false-fire |
| an `else` branch giving real text (`No detail given.`) | `R3=[]` — correctly passed | **a real strength**, and the adjacent negative for B1 family (b) |
| 3 arms emitting the probe string with NO `$OUT` interpolation | `R3=[]`, `R4=[]` | **no false positive** from a coincidental sentinel (the prompt's candidate, refuted) |
| probe at the START of the payload (`"$OUT — unreadable."`) | `[5]` | the leading-space worry does not materialise |
| 3 MULTI-LINE payload shapes (detail then a newline then text; label and detail on separate lines; a newline after the detail) | `[5]` in all three | **a real strength**, and it matters: the shipped `5)`/`6)` arms ARE multi-line |
| the SHIPPED hook read from disk, all three rules at full `CODES` | `dangling=[]`, `silent=[]`, `handled={0,3,5,6}` | **no live defect**; reproduces `main`'s own output |
| the shipped hook at 6 codes × {probe, empty}, raw bash | **12/12** `returncode=0`, `stderr=''` | H1's two halves: the exit code carries no signal, and a stderr rule has a clean control |
| `silent_codes` vs `dangling_detail` over my own arms, plus the suite's `_FORBIDDEN` fixture (passing) | complementary at every arm I built: an arm silent-when-empty is R4's, an arm with a surviving surround is R3's | **attack 4**: no reachable disagreement. `silent_codes` returns only `codes & set(MUST_NOT_BE_SILENT)`, so `why is None` at `:484` cannot be reached from `main` — it is the mutation-attribution sentence it says it is, and it is correct |
| 25 manifest anchors vs the delivered file | **25/25 bind exactly once**, 0 orphans, 0 duplicate names | manifest sound |
| 25 `expect` values vs harvested case names | **25/25 resolve** (70 literal + 4 f-string templates) | manifest sound |
| **each of the 25 entries applied individually to a staged copy, suite run per entry** | **25/25 rc=1, 25/25 killed VIA THE EXACT CASE ITS `expect` NAMES, 0 survivors, 0 unattributed** — over a control proved green at 84/84 first | **attack 6 REFUTED** — including the three RE-ANCHORED entries |
| manifest count vs `check-plan-code.py:1362` | 25 vs 25 | agree |
| `sum(EXPECTED_MUTATIONS.values())` vs the pin at `:3828` | 1163 vs 1163 | agree |
| the four provenance comments at `:3792-3826`, read as consecutive deltas | terminate at 24 / 1162 | **M2** |
| `grep -rn check-rc-contract .github/` | `ci.yml:240` (run), `:243` (self-test) | the guard has a caller |
| `grep -rl surface-recall scripts/ .github/` + `scripts/mutations/*.json` | guard + ci.yml only; **no** manifest names the hook | #196 unchanged |

⚠ **I modified no tracked file and ran no writing `git` command.** Every experiment ran against
copies staged under my own scratchpad directory
(`…/scratchpad/r6/`), and against in-memory hook fixtures passed to `observe`. The staged tree's
unmutated baseline reproduced the live verdict (`84/84`, rc=0) before any edit and was restored
after the last. `git status --short` is unchanged apart from this review document.

NOT CONVERGED
