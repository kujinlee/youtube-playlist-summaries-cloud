# Round 4, Claude half — the LLM recall matcher (backlog #191)

**Verdict: NOT CONVERGED.** Two Blocking, two High, five Medium, two Low.

Subject: the round-4 fold, `git diff 077e7f6f..HEAD` — and, where the fold's own written claims
reach further back, the guard it edits.

⭐ **The headline is not any single finding. It is that `unmodelled_quoting` / `structural_lines`'s
soundness claim has now produced a Blocking or High in THREE CONSECUTIVE ROUNDS, and the redesign
test answers YES.** Round 3's B2 said the claim was false for single quotes; round 4's Codex half
said it was false for `<<\EOF`; this half says it is false for `$(…)` and for backticks, and that
the fold's repair introduced a false justification and a new false-refusal in the same edit. **The
arming condition fires.** My independent answer to the arming question is below, and it disagrees
with Codex's — not about the rc-2 enumeration, where I concur, but about what the condition is
asking.

I also confirm **Codex's null on a fifth rc-2 instance**, independently derived by AST over every
`raise Refusal(` and every `return CANNOT_RUN` in the file.

---

## BLOCKING

### B1 · The soundness claim is STILL false: command substitution makes the guard report a code as handled that bash swallows, at exit 0

`scripts/check-rc-contract.py:210` (`structural_lines`'s docstring, round-3 B2's own fix):

```
    ⚠ WHAT IS STILL NOT MODELLED IS NOW REFUSED RATHER THAN DESCRIBED — see `unmodelled_quoting`.
```

and `scripts/check-rc-contract.py:250-253` (`unmodelled_quoting`'s docstring), which is where that
promise is cashed:

```
    `structural_lines` models double and single quotes. It does NOT model
    `$'...'` (ANSI-C quoting, where backslash escapes differ) or heredocs (`<<`, `<<-`), and a
    line inside either could be read as structure. So their PRESENCE is refused outright: the
    guard says "I cannot read this" instead of answering over text it has misparsed.
```

**The enumeration is two forms long and bash has a third.** `$( … )` and backtick command
substitution open a nested quoting context: a `"` inside `$( )` closes the outer string as far as
`structural_lines` is concerned, so a line inside a command substitution is classified as
STRUCTURE. Nothing refuses it — no `$'`, no `<<`, and every arm head is a bare integer, so
`arm_soundness` is clean.

**Reproduced, and adjudicated against real bash.** A hook whose only unmodelled construct is one
multi-line command substitution in its `6)` arm — an idiom the live hook already uses twice
(`.claude/hooks/surface-recall.sh:41` and `:45`), just not yet inside the `case`:

```bash
case "$RC" in
  0) [ -n "$OUT" ] && PAYLOAD="$OUT" ;;
  3) [ -n "$OUT" ] && PAYLOAD="stale. Detail: $OUT" ;;
  6) PAYLOAD="$(echo "no corpus, and the note continues
  5) this line is inside a command substitution and not an arm")"
     [ -n "$OUT" ] && PAYLOAD="$PAYLOAD Detail: $OUT" ;;
  *) : ;;
esac
```

The whole guard, unmodified, over that hook:

```text
rc contract: 6 code(s) defined, 4 handled by an arm, 3 declared unhandled
rc contract OK — every defined code is handled or declared, and no arm promises a detail it might not have
rc=0
```

```text
unmodelled_quoting : []
arm_soundness      : []
handled_codes      : [0, 3, 5, 6]
unguarded_detail   : []
verdict            : []
```

Real bash, same file (`bash -n`: syntax OK):

```text
RC=0 PAYLOAD=[detail text]
RC=3 PAYLOAD=[stale. Detail: detail text]
RC=5 PAYLOAD=[]                                  <-- rc 5 goes to the catch-all
RC=6 PAYLOAD=[no corpus, and the note continues
  5) this line is inside a command substitution and not an arm Detail: detail text]
```

**The guard says rc 5 is handled; bash has no `5)` arm and swallows it silently.** That is backlog
#202 verbatim — the defect this guard exists to catch — produced by the guard, at exit 0.

**Backticks fail identically**, measured on the same shape with `` PAYLOAD="`echo "…" `` :
`unmodelled_quoting []`, `arm_soundness []`, `handled_codes [0, 3, 5, 6]`, `verdict []`.

⚠ **Reachability, stated rather than assumed.** This needs the substitution to SPAN LINES with
arm-shaped text inside it. The live hook already has three multi-line payload strings
(`.claude/hooks/surface-recall.sh:63-65`, `:78-79`, `:85-87`), so the only missing ingredient is a
`$(` or a backtick in one of them. That is the same reachability profile round-3 B2's
single-quoted multi-line payload had, and B2 was Blocking.

**Why this is Blocking rather than the next instance in a series:** the fix for round 3's B2 was to
replace a *described* bound with a *refused* one, and the refusal is an ENUMERATION of forms. An
enumeration of what a hand-rolled lexer does not model cannot be completed by inspection — three
rounds have now each found one more member. The module's own recorded standard
(`scripts/check-rc-contract.py:123-127`) is that such a reader *"CANNOT be made correct. It CAN be
made unable to be silently wrong"*, and an enumeration is exactly the mechanism that cannot deliver
the second half.

**The observation that would prove this finding wrong:** `unmodelled_quoting` returning a problem
for `$(`, `` ` `` and any other construct that opens a nested quoting context — or, better, the
guard refusing any `case` block whose arm bodies are not drawn from a whitelisted set of shapes, so
that the set of *accepted* forms is what is enumerated rather than the set of rejected ones.

### B2 · `DELIBERATELY_UNHANDLED[0]` excuses the absence of the ONE arm that forwards a match, and its written reason asserts that arm exists

`scripts/check-rc-contract.py:87-88`:

```python
    0: "rc 0 IS handled — the `0)` arm forwards a match and stays silent on an empty answer. "
       "Listed only so the table below is total; `handled_codes` finds its arm.",
```

`verdict` consults the table only after the `handled` test (`scripts/check-rc-contract.py:336-345`),
so while the `0)` arm exists the row changes nothing — which is what the reason describes. **The
row's effect is the case the reason does not cover: if the `0)` arm is ever removed, the row
excuses it.** And rc 0 with non-empty output is the entire product: it is the arm that forwards a
matched memory entry to the model.

**Reproduced.** The live hook with `  0) [ -n "$OUT" ] && PAYLOAD="$OUT" ;;` deleted and nothing
else changed, the whole guard unmodified:

```text
rc contract: 6 code(s) defined, 3 handled by an arm, 3 declared unhandled
rc contract OK — every defined code is handled or declared, and no arm promises a detail it might not have
rc=0
```

Note the guard **prints the evidence of the regression — `3 handled by an arm`, where the live tree
prints 4 — and then says OK.** Real bash over that block, with a genuine match in `$OUT`:

```text
rc 0 with a real match -> PAYLOAD=[]
```

So every successful recall is silently dropped and R1 — *"Every rc constant the matcher DEFINES is
either named by a `case` arm in the hook, or is listed here as deliberately unhandled with a written
reason"* (`scripts/check-rc-contract.py:36-38`) — reports OK.

**Nothing can catch it.** Every other row is falsifiable by removal: the suite pops row 4 and
watches the same input flip (`scripts/check-rc-contract.py:611-618`). No case pops row 0, and the
only case that touches it asserts the table's *totality*
(`scripts/check-rc-contract.py:624-625`), not its truth. `grep -n DELIBERATELY_UNHANDLED` returns
six sites and none of them is a check that a row claiming "this code IS handled" is right.

This is the escape-hatch shape this repo has recorded before — **a written reason is a rubber stamp
when nothing tests the sentence** — with the aggravating detail that the sentence here is not merely
unverified but is the *load-bearing premise* for the row being harmless.

**The observation that would prove this finding wrong:** `verdict` refusing a code that is BOTH
absent from `handled` and carries a row asserting it is handled — or row 0 deleted outright, since
`0 in handled` already short-circuits it in every world where the reason is true.

---

## HIGH

### H1 · `arm_soundness`'s indentation freedom is unfalsified, and restoring the old rule silently reopens round-3 M1

`scripts/check-rc-contract.py:130`:

```python
_ARM_SHAPE_RE = re.compile(r"^[ \t]*([^\s#][^)\n]*)\)", re.M)
```

Round 3's M1 fix has two halves: free the arm reader's indentation, and add `arm_soundness` so an
arm shape the module cannot classify becomes a cannot-run rather than a silently missing arm
(`scripts/check-rc-contract.py:123-127`). Round 3's H1 then found the catch-all bound left at two
spaces — *"M1 fixed as an INSTANCE"* — and added a mutation for it. **`_ARM_SHAPE_RE`'s own
indentation freedom got neither a case nor a mutation entry**, so the soundness check itself is
still indentation-fragile with nothing watching.

**Measured.** With `_ARM_SHAPE_RE` reverted to `^\s{2}(...)` — one character class, the same edit
round-3 M1 was filed about — over a hook with a four-space `4|5)` arm:

```text
  at HEAD  -> arm_soundness: 1 problem(s) -> REFUSES (cannot-run)
  MUTATED  -> arm_soundness: 0 problem(s) -> CLEAN  <-- silently missing arm
  MUTATED  -> handled_codes: [0, 3, 6]   (bash handles 4 and 5 via `4|5)`)
```

and the suite stays green: `python3 scripts/check-rc-contract.py --self-test` → **50/50**. The
cases that *look* like they cover this — *"an arm indented FOUR spaces is still an arm"*,
*"a tab-indented arm is an arm"* (`:486-491`) — drive `handled_codes`, never `arm_soundness`.

⭐ **And the wrong answer is worse than a missing arm.** Because `4|5)` is not an `_ARM_RE` mark,
the `3)` arm's span swallows the `4|5)` body, so the mutated verdict is:

```text
["rc 5 (UNREADABLE_PLAN) is defined by the matcher, no `case` arm in the hook names it, …",
 'the `3)` arm interpolates $OUT into a `Detail:` clause with no `[ -n "$OUT" ]` guard …']
```

Real bash on that hook: `RC=4 PAYLOAD=[x. Detail: detail text]`, `RC=5 PAYLOAD=[x. Detail: detail
text]`. So rc 5 is reported unhandled when bash handles it, **and a real #201 defect belonging to
`4|5)` is attributed to the innocent `3)` arm.** A false finding against a named arm is the failure
mode a reader acts on.

**The observation that would prove this wrong:** a case driving `arm_soundness` over a
non-two-space unmodelled arm head, plus a manifest entry reverting `_ARM_SHAPE_RE`'s indentation
that reddens it.

### H2 · `nag_once` degrades to "repeats forever, SILENTLY" — the one rule, written down at its sibling and missing here

`scripts/recall-llm.py:805-809`:

```python
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(current, encoding="utf-8")
    except OSError:
        pass
```

Its sibling, thirty lines of the same logic at `scripts/recall-llm.py:1205-1211`, states the rule
this violates (`scripts/recall-llm.py:1201-1204`):

```
    # ⚠ AND THE RECORD IS BEST-EFFORT, DELIBERATELY. If the marker cannot be written the dedupe is
    # lost and this step may be surfaced twice. A duplicate lesson is a far cheaper failure than a
    # lost one, so this must never raise — but it must not be SILENT either, or a permanently
    # unwritable directory degrades to "reprints forever" with nothing saying why.
```

**Measured, both sites, in the same world** — an armed plan, an existing `.claude/recall-cache/`
at `chmod 500`, `--fire` three times:

```text
--- nag_once (the rc 3 NAG), CONTROL: writable cache dir ---
  call 1: rc=3  chars= 113  STALE CACHE: probe.json does not exist — this plan was never armed …
  call 2: rc=3  chars=   0  (nothing said)
  call 3: rc=3  chars=   0  (nothing said)

--- nag_once, UNWRITABLE cache dir ---
  call 1: rc=3  chars= 113  STALE CACHE: probe.json does not exist — this plan was never armed …
  call 2: rc=3  chars= 113  STALE CACHE: probe.json does not exist — this plan was never armed …
  call 3: rc=3  chars= 113  STALE CACHE: probe.json does not exist — this plan was never armed …
```

```text
--- _fire_armed's surface marker, UNWRITABLE cache dir ---
  call 1: … ⭐ recall — this moment matches a recorded lesson: …
        | (recall-llm: the entry above was surfaced, but the dedupe marker could not be written —
        |  [Errno 13] Permission denied: …/.claude/recall-cache/.last-surfaced. This step may be
        |  surfaced again.)
```

The sibling names the errno. `nag_once` says nothing, forever.

**Why this matters more than a missing log line.** rc 3 is the nag, and
`scripts/recall-llm.py:1131-1136` records why: *"`--arm` is a manual, paid step that nothing runs
automatically, so 'never armed' is the DEFAULT state of every plan"*. The hook forwards on
non-empty output, so in this world a four-line block re-enters the model's context on **every**
`begin-plan.py` invocation — which is precisely the failure round-1 M4 and round-2 H5 were filed
about (*"a hook that printed on every call would be trained away within an hour"*, measured at 275
firings a session). The dedupe that exists to prevent it fails open with no signal.

⚠ **Bound.** This needs `.claude/recall-cache/` to exist and be unwritable — `nag_once`'s own
`mkdir(exist_ok=True)` creates it when absent. That is exactly the world round-2's H1(e) was
measured in (`chmod 500`), and the sibling site carries a notice for it, so the world is one this
code already accepts as reachable.

**The observation that would prove this wrong:** `nag_once` printing a notice on a failed write —
or the two bookkeeping sites collapsed into one function, since they are two implementations of one
rule and the loudness clause is the thing that drifted.

---

## MEDIUM

### M1 · The pessimistic `<<` detector refuses a COMMENT, and the likeliest comment to be written is the one documenting the constraint

`scripts/check-rc-contract.py:272`:

```python
    if re.search(r"(?<!<)<<(?!<)", block):
```

`unmodelled_quoting` reads the RAW block. `structural_lines` — thirty lines up, in the same module
— does not, and says why (`scripts/check-rc-contract.py:233-237`): *"⛔ A COMMENT IS NOT CODE, AND
SCANNING ONE OPENED A PHANTOM STRING."* The module now holds both positions.

**Measured — every probe refuses, i.e. drives the whole guard to rc 2, CANNOT RUN:**

```text
  REFUSED  | a COMMENT mentioning a heredoc (documenting the guard's own constraint)
  REFUSED  | an arithmetic left-shift in an arm body   ($(( 1 << 2 )))
  REFUSED  | `<<` inside a double-quoted PAYLOAD string
  REFUSED  | `<<` in an arrow-ish comment              (# rc 0 <<-- the common case)
```

The first is the one that matters, and it is a loop: the natural way to record the new constraint
inside the hook is a comment such as `# NEVER use a heredoc (<<EOF) here: check-rc-contract.py
refuses the block` — and writing it makes the guard permanently red with a message that says the
block *contains a heredoc* when it contains none. **A false sentence in a cannot-run message is
worse than a spurious red**, because the reader is told a specific untrue thing about their file
and this repo's measured verdict on a gate red from birth (backlog #56) is that it gets switched
off.

I accept the fold's asymmetry argument — loud beats silent — and it is the right direction. The
finding is its SCOPE: the pessimism is over the raw text where the module already has a
comment-aware reading, and narrowing it to comments costs nothing (a `<<` inside a comment cannot
open a heredoc in bash either). Not HIGH because it costs a red gate and a confused look, never a
wrong answer.

**Proved wrong by:** `unmodelled_quoting` skipping `#`-comment text the way `structural_lines` does,
while still refusing every `<<` on a structural line — or a written reason explaining why a comment
is deliberately included, since the sibling function documents the opposite choice.

### M2 · The fold's justification for the look-behind is FALSE — the live `case` block contains no `<<` at all

`scripts/check-rc-contract.py:267-271`:

```
    # missed one is silent and costs a wrong answer. `(?!<)` excludes `<<<`, bash's herestring,
    # which the live hook does use (outside the `case` block) and which has no unmodelled body.
    # ⚠ THE LOOK-BEHIND IS REQUIRED, and my own adjacent negative caught its absence: `<<(?!<)`
    # still matches `<<<` at OFFSET 1, where the lookahead sees the quote rather than a third `<`.
    # So a herestring would have been refused and this guard would be red on the real repo.
```

and the case at `scripts/check-rc-contract.py:560-561`:

```
    # ⚠ THE ADJACENT NEGATIVE, and it is load-bearing: `<<<` is a HERESTRING, which the live hook
    # uses. Refusing it would make this guard red on the real repo forever.
```

**The parenthetical in the first quote refutes the sentence after it.** `unmodelled_quoting` is
only ever called on `case_block(hook_src)` (`scripts/check-rc-contract.py:377-382`), and the hook's
herestring is at `.claude/hooks/surface-recall.sh:94`, outside the block.

Measured over the live tree:

```text
raw `<<` occurrences inside the live case block : []
`(?<!<)<<(?!<)` on the live block               : False
`<<(?!<)`       on the live block               : False   <-- the look-behind changes nothing here
`<<(?!<)`       on the WHOLE hook file          : True  at offset 6774 -> '<<"$PAYLOAD"'
```

And the guard with the look-behind **removed**, run against the real hook:

```text
rc contract: 6 code(s) defined, 4 handled by an arm, 3 declared unhandled
rc contract OK — …
rc=0
```

So both written claims are false. The look-behind is still *correct* — a herestring genuinely is
not a heredoc — but its stated reason is not, and the manifest entry's name asserts the same false
thing: *"the herestring look-behind is dropped, so `<<<` is refused and the guard reddens on the
real repo"* (`scripts/mutations/check-rc-contract.json`). That entry is killed by a **synthetic**
fixture, not by the real repo.

⚠ **The mechanism, and it is the useful half:** the suite contains **no case that reads
`.claude/hooks/surface-recall.sh`**. The cases named for the live shape — *"the live shape uses
neither, so it is not refused"* (`:564-565`), *"...and the canonical block is sound"* (`:497`) —
run over `HOOK_OK`, a synthetic fixture. The real hook is reached only by `main()`. That is
defensible as a design (CI runs `main()`), but it is why a belief about the real hook's contents
could be written into three places in one fold and checked by nothing.

**Proved wrong by:** a `<<`-bearing construct existing inside the live `case` block, or the
comments rescoped to say the look-behind protects a future hook rather than the current one.

### M3 · The rc-4 row's repair for one stale citation is SIX new citations, and nothing owns them

`scripts/check-rc-contract.py:102-114` re-derives **TRUE** at HEAD. I verified it by AST rather
than accepting it:

```text
  :580  in no_duplicate_keys
  :612  in parse_response
  :618  in parse_response
  :633  in parse_response
  :639  in parse_response
  :642  in parse_response

  parse_response    cited [612, 618, 633, 639, 642] actual [612, 618, 633, 639, 642] MATCH
  no_duplicate_keys cited [580]                     actual [580]                     MATCH
  json.loads at :616 in parse_response kwargs=['object_pairs_hook']
  json.loads at :718 in parse_cache    kwargs=[]
  parse_response production callers: [(1013, '_arm_body')]
```

So Codex's "the three reasons re-derive as true" holds for row 4, and the conclusion holds for the
stated reason.

**The finding is the mechanism, not the claim.** Round 3's M1 was caused by a line citation that had
drifted and been copied forward; the repair was to write six more line numbers into a different
file, where nothing verifies them. `check-selftest-counts.py` verifies a script's own declared
count by running it and has no row for a count one script asserts about another;
`check-anchors.py`, `check-producer-enumeration.py` and `check-docs.py` do not read
`DELIBERATELY_UNHANDLED`. Measured by absence: `grep -rln DELIBERATELY_UNHANDLED scripts/
.github/` returns only `check-rc-contract.py` itself. Any insertion in `recall-llm.py` above line
580 makes all six stale, silently — the *document-inside-the-corpus-it-measures* shape, now at 6×
the surface it had when it was filed.

**Proved wrong by:** the row naming `no_duplicate_keys`, `parse_response` and the
`object_pairs_hook` relation by SYMBOL with no line numbers (which is what makes the claim survive
a rename), or a case that re-derives the six sites by AST and reddens when they move.

### M4 · `DELIBERATELY_UNHANDLED.pop(4)` sits OUTSIDE the `try` added to protect it, so a renumbered row truncates the cases below it

`scripts/check-rc-contract.py:611-616`:

```python
    _saved = DELIBERATELY_UNHANDLED.pop(4)
    try:
        case("a defined code with NO arm and NO row is refused (rc 4, row removed)",
             len(verdict(D, {0, 3, 5, 6}, [])), 1)
    finally:
        DELIBERATELY_UNHANDLED[4] = _saved
```

Twelve lines above it, the fold that produced this suite documents exactly this hazard
(`scripts/check-rc-contract.py:598-604`): *"⛔ NO UNGUARDED `[0]`, AND ITS ABSENCE TRUNCATED THIS
SUITE … a CASE that can raise hides every case after it."* The `try` was placed around the
`case()` call and not around the `pop` that sets it up.

**Measured.** The plausible edit — renumbering the rc-4 row, which is what happens when a code is
renumbered:

```text
[FAIL] the live shape agrees …
[FAIL] a defined code with no arm and no written reason is refused — #202's shape …
Traceback (most recent call last):
  File ".../check-rc-contract.py", line 611, in _self_test
    _saved = DELIBERATELY_UNHANDLED.pop(4)
KeyError: 4
rc=1
```

**Four cases below that line never execute** (`:617`, `:619`, `:620`, `:624`), the
`50/50` counter line is never printed, and the two `[FAIL]`s that do print belong to different
cases than the one whose setup raised — so a harness attributing a mutation by the case it names
sees the same misattribution the earlier instance produced.

⚠ It is red rather than green, so this is a reporting defect, not a false pass. Medium for that
reason.

**Proved wrong by:** the `pop` moved inside the `try` (or replaced by a dict copy), so that a
missing row fails one case instead of ending the run.

### M5 · Two of the 50 cases cannot fail

**Case `:463`** — *"the catch-all is not a code"*:

```python
    case("the catch-all is not a code", 42 in handled_codes(HOOK_OK), False)
```

`handled_codes` returns `{int(m.group(1)) for m in _ARM_RE.finditer(...)}`, so every member's digits
come from the fixture. Measured, every digit run in `HOOK_OK`:

```text
  ['0', '3', '5', '6']
```

There is no `42` anywhere in the fixture, so **no change to `_ARM_RE` or `structural_lines` can put
42 in that set** — the assertion is satisfied by a constant the fixture does not supply, which is
this repo's named shape for a case that cannot fail. The property the name claims — `*)` is not read
as a code — is already asserted by `:462`, which pins the set to exactly `{0, 3, 5, 6}` and
therefore excludes any extra member including 42.

**Case `:472`** — *"...and it names only the offending arm"*:

```python
    case("...and it names only the offending arm", unguarded_detail_arms(BAD) == [5, 6], False)
```

`:470` already asserts the same call `== [5]`. A list equal to `[5]` is never `[5, 6]`, so `:472`
is green whenever `:470` is green. And under a mutation that breaks the function it stays green
while `:470` reddens — measured, with `_NONEMPTY_GUARD` made to match nothing:

```text
    mutated result = [3, 5, 6]
    case :470 ('== [5]')     -> RED
    case :472 ('!= [5, 6]')  -> PASS  <-- adds nothing
```

Zero independent discriminating power in either direction.

⚠ **No guard owns this.** `check-gate-falsifiability.py` inspects gate DESCRIPTIONS in documents
("Every unticked gate item must name what would make it FAIL") and says so in its own docstring; it
does not look at self-test cases. `check-fixture-variation.py` ratchets unvaried *parameters*, not
unfalsifiable *assertions*. So a declared-and-verified count of 50 includes two cases that carry no
information, and the count is the only thing checked.

**Proved wrong by:** a mutation entry that reddens `:463` via the rule it names, or either case
rewritten as a positive assertion (`handled_codes(HOOK_OK) == {0,3,5,6}` is already `:462`;
`:472`'s intent is delivered by `:470`).

---

## LOW

### L1 · `DELIBERATELY_UNHANDLED[2]`'s middle shape is narrower than the code it excuses

`scripts/check-rc-contract.py:89-91` names *"no mode flag at all (`main`)"*. The code is
`if len(chosen) != 1` (`scripts/recall-llm.py:2486`), which also covers **two or more** modes.
Re-measured at HEAD, every invocation form:

| invocation | rc | first line of stderr |
|---|---|---|
| `--fire` | 0 | — |
| `--print-prompt` | 0 | — |
| *(none)* | 2 | `CANNOT RUN: name exactly one of --arm / --fire / --print-prompt …` |
| `--again` | 2 | same |
| `--arm --fire` | **2** | same — **two** modes, not none |
| `--print-prompt --arm` | **2** | same — **two** modes, not none |
| `--fier` | 2 | `usage: recall-llm.py …` (argparse) |
| `--fire --extra` | 2 | `usage: recall-llm.py …` (argparse) |

The row's count of three shapes is right and its verdict is right; one of the three is described by
a phrase that excludes half its cases. This row has now been corrected twice for narrow wording, and
its own text says so.

**Proved wrong by:** the phrase reading *"not exactly one mode flag"*.

### L2 · Three production clauses are unfalsified — the suite stays 50/50 with each one removed

Measured by applying 37 single-edit mutations to the production code and running the suite each
time. Three survived green:

| edit | what it removes |
|---|---|
| `_OUT_LABEL` → `re.compile(r"Detail:")` | the lowercase `detail:` alternative (`:135`). No fixture uses it |
| `_RC_NAMES` loses `"UNANSWERABLE"` (`:81`) | the recognition key's completeness — a 5-name assignment would then be accepted as the rc tuple |
| `defined_codes`' `raise CannotRun("… mismatched names and values")` → `pass` (`:168`) | a reachable cannot-run branch (`A, …, F = 0, 2, 3, 4, 5, 6, 7`) with no case |

Two further survivals are semantically inert rather than defects (`_ARM_RE` losing its `^` anchor,
`_ARM_SHAPE_RE` admitting a `#` head) and I could not turn either into a wrong answer, so they are
listed here rather than filed.

**Proved wrong by:** a case or manifest entry for each, or a written reason that the clause is
defensive.

---

## The judgement you asked for: ~650 lines guarding a 90-line hook

**Measured first, because the framing is off in both directions.**

| | lines | non-blank, non-comment |
|---|---|---|
| `scripts/check-rc-contract.py` | 632 | 471 |
| … the suite (`_self_test`) | 223 (`:406-628`) | — |
| … the nine production functions | — | **209** |
| `.claude/hooks/surface-recall.sh` | 95 | 23 |
| … the `case` block (the subject) | 41 | **14** |

So the honest ratio is not 650:90. It is **209 lines of production guard over 14 lines of
executable `case` block** — worse than the framing suggests on one axis, and much better on
another, because the hook is only *half* the subject: the other half is `recall-llm.py`'s six rc
constants and their reachability, and that file is 2,508 lines. A guard whose subject is an
AGREEMENT has no single denominator, which the docstring already says
(`scripts/check-rc-contract.py:45-47`).

**Now split the 209 by what it does, because that is where the judgement actually lives:**

| role | functions | non-comment lines |
|---|---|---|
| read the PYTHON side | `defined_codes` | 30 |
| **re-implement BASH's lexer** | `case_block`, `structural_lines`, `unmodelled_quoting`, `arm_soundness` | **91** |
| the actual rules R1/R2/R3 | `handled_codes`, `unguarded_detail_arms`, `verdict` | 49 |
| reporting + cannot-run plumbing | `main` | 39 |

**The rules are 49 lines and they have produced no Blocking in any round. The bash reader is 91
lines — nearly twice the rules — and it is where round 3's B2, round 4's Codex H1, and this half's
B1, M1 and M2 all live.** That is the size argument, quantified: the expense is not the guard, it
is the *reader*, and the reader is the part that keeps being wrong.

**Deletion test, applied honestly.** I found one true pass-through and one thing worse than a
pass-through:

- `DELIBERATELY_UNHANDLED[0]` is not a pass-through, it is **B2** — deleting it makes the guard
  strictly stronger, because `0 in handled` already short-circuits it in every world where its own
  reason is true.
- `_OUT_LABEL`'s lowercase `detail:` alternative (L2) is a genuine pass-through: no fixture, no
  mutation, and the hook never spells it that way.
- `handled_codes`' four lines look like a pass-through and are not — they are the composition of
  `_ARM_RE` with `structural_lines`, which is the whole point of R1 reading structure rather than
  text.
- `main`'s 39 lines are five distinct cannot-run exits with distinct messages. That is this repo's
  own standard ("cannot run is a FAILURE, never a pass") and I would not cut it.

**Verdict: the ratio is defensible for the rules and not for the reader.** The guard earns its
existence outright — its subject produced two live defects (#201, #202) that every other gate in
the repo was structurally blind to, and 14 lines of bash dispatch controlling whether a memory
entry reaches the model is exactly the kind of small, high-blast-radius code this project says to
guard. What is not defensible is spending 91 lines re-deriving bash's lexical rules by hand and
then guarding the result with an ENUMERATION of the forms that were not derived. Replacing those
91 lines with a whitelist refusal — *this block's arms must be `N)` or `*)` with bodies drawn from
these shapes, or the guard cannot run* — would be shorter, would dissolve B1 and M1 together, and
would make the module's own stated standard ("unable to be silently wrong") true by construction
rather than by enumeration. **That is the same redesign the arming answer below owes, arrived at
from the size question instead of the finding count, which is why I think it is the right one.**

---

## The arming question — my independent answer

**It fires. `docs/dev-process.md:113` is met, and the component is
`unmodelled_quoting` / `structural_lines`'s soundness claim.**

First, the part where I **agree with Codex**: there is **no fifth live rc-2 instance in
`recall-llm.py`**. I derived it independently by AST rather than by reading the same enumeration.
Every production site that can produce rc 2:

| site | reached from | inside a boundary? |
|---|---|---|
| `raise Refusal` `recall-llm.py:941` (no sentinel) | all three modes | **deliberately outside** — the routine absence, correct |
| `raise Refusal` `recall-llm.py:960`, `:964` (`read_corpus`) | `prepared_prompt` | yes → rc 6 |
| `raise Refusal` `recall-llm.py:908`, `:915`, `:917`, `:920`, `:923` (`call_model`) | `_arm_body` | yes, `do_arm` → rc 6 |
| `return CANNOT_RUN` `recall-llm.py:2489` (`main`) | usage | not an armed-scope exit |
| `return CANNOT_RUN, …` `:393` `decode_verdict` | pure; rc **discarded**, caller raises a classed refusal | n/a |
| `return CANNOT_RUN, …` `:489`, `:492` `corpus_verdict` | `read_corpus` → boundary | yes → rc 6 |
| `return CANNOT_RUN, …` `:776` `cached_entry_verdict` | `_fire_armed` raises `Unanswerable` explicitly | yes → rc 6 |

No `sys.exit`/`os._exit` outside the `__main__` guard. And I confirm Codex's specific claim about
the marker paths: `nag_once`'s two swallows (`:799-802`, `:808-809`) and `_fire_armed`'s two
(`:1189-1192`, `:1208-1210`) all yield rc 0 or a printed nag, never rc 2 — and rc 0 is the right
answer at each, since the entry was either printed or deliberately suppressed. **H2 is a defect in
what those swallows SAY, not in the code they return.** `should_surface` is pure and
`fire_output` returns a string; neither can exit.

**Now the disagreement.** Codex answered *"is there a fifth instance of the rc-2 conjunction?"*.
That is not what `docs/dev-process.md:113-118` asks. It asks whether **two consecutive rounds carry
findings caused by the previous round's own fix, in one component** — and it explicitly warns that
*"Reaching four rounds OBLIGES ASKING, and does not fire"*, requiring *thrashing or prose floor?*
answered per finding. Here is that inventory for rounds 3 and 4.

| round | finding | component | caused by the previous round's fix? |
|---|---|---|---|
| 3 | B2 — the soundness claim is false (single quotes) | **the soundness claim** | ✅ the claim was introduced by the round-3-input fold |
| 3 | B1 — `_arm_body` returns rc 2 | the rc contract (`recall-llm.py`) | ✅ round 2's H3 fix |
| 3 | H1 — the catch-all bound left at two spaces | the arm reader | ✅ round 3 M1's fix |
| 3 | H2, M1 | the `DELIBERATELY_UNHANDLED` reasons | ✗ original to the guard |
| 3 | M3, M4, L1 | mixed | ✗ / ✅ |
| **4** | **codex H1 — `<<\EOF` slips past the detector** | **the soundness claim** | ✅ **round 3 B2's fix** |
| **4** | **claude B1 — `$(…)` and backticks give a wrong answer** | **the soundness claim** | ✅ **round 3 B2's fix** |
| **4** | **claude M1 — the pessimistic detector now refuses a comment** | **the soundness claim** | ✅ **round 4 codex H1's fix, same round** |
| **4** | **claude M2 — the look-behind's justification is false** | **the soundness claim** | ✅ **round 4's own fold** |
| 4 | claude H1 — `arm_soundness`'s indentation unfalsified | the arm reader | ✅ round 3 M1/H1's fix |
| 4 | claude B2 — row 0 excuses the `0)` arm | the escape table | ✗ original to the guard |
| 4 | claude H2 — `nag_once` silent | the dedupe (`recall-llm.py`) | ✅ round 2 H5 + H1(e) fixes |
| 4 | claude M4 — the unprotected `pop` | the suite | ✅ round 3's own truncation fix |
| 4 | claude M3, M5, L1, L2 | mixed | ✗ / ✅ |

**Rounds 3 and 4 are consecutive, both are predominantly fix-caused, and ONE COMPONENT is re-opened
in both: the soundness claim.** That is the half of the condition round 2's and round 3's
convergence documents each correctly found unmet — *"no component has been re-opened twice"*. It is
met now, at the third round in a row, in the same pair of functions —
`structural_lines` + `unmodelled_quoting`, 58 non-comment lines between them.

**And the test is not the symptom list.** `docs/review-method.md:200` — *"Can a redesign remove
it?"*:

> **Yes, decisively.** All three findings in this component are instances of one sentence: *my
> hand-rolled bash lexer differs from bash's.* A different shape dissolves the class rather than
> the instance — refuse any `case` block whose arms are not drawn from a WHITELIST of shapes (so
> the enumeration is of what is ACCEPTED, which is finite and knowable, instead of what is
> rejected, which is not), or adjudicate by running bash itself rather than re-implementing its
> lexer. Under either shape, single quotes, `$'…'`, heredocs, escaped heredoc delimiters,
> command substitution and backticks all stop being separate findings.

By `review-method.md`'s table this is a **mechanism** defect (*"the rule cannot be satisfied"* — the
module's own standard is *"unable to be silently wrong"*, and an enumeration of unmodelled forms
cannot deliver it), not branch-coverage and not a stale cross-reference. **Prose floor: no.** Every
finding in this half was reproduced before it was reported, three of them adjudicated against real
bash, and none is a wording preference — M2 is the only one about a sentence, and it is about a
sentence that is factually false against a measurement.

⚠ **What I am NOT claiming.** The other components are not thrashing: `recall-llm.py`'s rc contract
produced B1 in round 3 and nothing Blocking here (my H2 is the dedupe, a different mechanism), and
Codex's rc-2 enumeration and mine agree that it has converged on the question it was re-opened for.
**The redesign that is owed is scoped to `check-rc-contract.py`'s bash reader, not to the matcher.**

---

## Areas I could NOT establish

- **A fifth rc-2 instance.** Measured null, by AST over every `raise Refusal(` and `return
  CANNOT_RUN` plus a boundary audit — reported above as a positive agreement with Codex, not as a
  skipped check. ⚠ Bound: AST sees *syntactic* raise sites. A rc-2 exit constructed dynamically
  (`raise type(exc)("")` at `scripts/recall-llm.py:1097`) is not one of them; I checked that site
  by hand — for a bare
  `Refusal` it is only reachable from the no-sentinel path, which is outside every boundary by
  design.
- **Whether `_ARM_RE`'s `^` anchor and `_ARM_SHAPE_RE`'s `#` exclusion are load-bearing.** Both
  mutations left the suite green; I could not build a hook where either changes the answer, so they
  are in L2 as inert-or-unfalsified rather than filed as defects. Someone who can build one has a
  finding I do not.
- **`;;&` / `;&` fall-through**, which round 3 also could not turn into a silent miss. My probes
  reproduced its loud-false-positive behaviour and nothing quieter.
- **The hook as sole caller against live state.** Not run: it consumes the live `.last-said` and
  `.last-surfaced` markers, and my brief forbids mutating the repo. Every bash adjudication in B1,
  B2 and H1 runs the `case` block in isolation instead, which answers the same question about arm
  dispatch; H2's measurement ran against a temp `ROOT`/`CACHE_DIR`/`HOME` with the globals swapped
  back in a `finally`.
- **Whether refusing on an arithmetic `$(( 1 << 2 ))` has ever been intended.** I treated it as a
  false refusal in M1 because no arm uses arithmetic today, so I cannot distinguish "not thought
  about" from "accepted cost".

---

## Verified

Every command run, with its output. Each of the coordinator's claimed gates is checked, not
accepted.

| command | output | claim |
|---|---|---|
| `python3 scripts/recall-llm.py --self-test` | `199/199 self-test cases passed`, rc=0 | **matches** |
| `python3 scripts/check-rc-contract.py` | `rc contract: 6 code(s) defined, 4 handled by an arm, 3 declared unhandled` / `rc contract OK …`, rc=0 | **matches** |
| `python3 scripts/check-rc-contract.py --self-test` | `50/50 self-test cases passed`, rc=0 | **matches** |
| `python3 scripts/check-ratchet-contract.py` | `guards discovered (42)` / `ratchet contract OK`, rc=0 | **matches** |
| `python3 scripts/check-fixture-variation.py` | `729 parameter(s) examined across 61 file(s); 117 known-unvaried ratcheted, 7 exempt`, rc=0 | **matches** |
| `python3 scripts/check-selftest-counts.py` | `49 script(s) declare a count, every one verified by running it`, rc=0 | **matches** |
| `python3 scripts/check-docs.py` | `Documentation integrity OK`, rc=0 | **matches** |
| `python3 scripts/check-plan-code.py --self-test` | `131/131 passed`, rc=0 | **matches** |
| `python3 scripts/check-plan-code.py --mutate .` | see the line below | — |
| `python3 scripts/check-gate-falsifiability.py` | `gate falsifiability OK — every unticked gate item names what would fail it`, rc=0 | not claimed; run to test whether it owns M5 — it does not |
| manifest count vs `EXPECTED_MUTATIONS` | `scripts/mutations/check-rc-contract.json` **16** entries; `check-plan-code.py:1352` declares **16** | agree |
| `<<` occurrences in the live `case` block | `[]`; `(?<!<)<<(?!<)` → False; `<<(?!<)` → False; whole file → True at offset 6774 (`<<"$PAYLOAD"`) | **M2** |
| the guard with the look-behind REMOVED, vs the real hook | `rc contract OK`, rc=0 | **M2 — the "red on the real repo" claim is false** |
| whole guard vs a hook with a multi-line `$( … )` in its `6)` arm | `rc contract OK`, rc=0; `handled [0,3,5,6]`; bash `RC=5 PAYLOAD=[]` | **B1** |
| same with backticks | `unmodelled_quoting []`, `arm_soundness []`, `handled [0,3,5,6]`, `verdict []` | **B1** |
| whole guard vs the live hook with the `0)` arm deleted | `3 handled by an arm` / `rc contract OK`, rc=0; bash forwards nothing | **B2** |
| `arm_soundness` over a four-space `4\|5)` arm, HEAD vs `_ARM_SHAPE_RE` at two spaces | `1 problem` → `0 problems`, suite still **50/50**; mutated verdict blames the `3)` arm | **H1** |
| `--fire` ×3, writable vs `chmod 500` cache dir | `113/0/0` vs `113/113/113`, no notice | **H2** |
| `_fire_armed`'s marker write, same world | prints `(recall-llm: … the dedupe marker could not be written — [Errno 13] …)` | **H2's asymmetry** |
| `unmodelled_quoting` over 5 legitimate `<<` constructs | **5 of 5 REFUSED** (comment, `$(( 1 << 2 ))`, quoted payload, `<< EOF`, arrow comment) | **M1** |
| AST: `ResponseRejected` raise sites + enclosing function, at HEAD | `:580 no_duplicate_keys`; `:612 :618 :633 :639 :642 parse_response` — **exact match to the row's citation** | **M3** — row 4 is TRUE |
| AST: `json.loads` kwargs | `:616 parse_response object_pairs_hook`; `:718 parse_cache` none | **M3** — the conclusion holds |
| AST: `parse_response` production callers | `[(1013, '_arm_body')]` | **M3** |
| `grep -rln DELIBERATELY_UNHANDLED scripts/ .github/` | only `scripts/check-rc-contract.py` | **M3** — nothing owns the six citations |
| suite with the rc-4 row renumbered | `KeyError: 4` at `:611`, **4 cases below never execute**, no counter line | **M4** |
| digit runs in the `HOOK_OK` fixture | `['0', '3', '5', '6']` — no `42` | **M5** |
| `unguarded_detail_arms(BAD)` with `_NONEMPTY_GUARD` neutered | `[3, 5, 6]` — `:470` RED, `:472` **PASS** | **M5** |
| rc census over 8 invocation forms | `0 / 0 / 2 / 2 / 2 / 2 / 2 / 2` — see L1's table | **L1** |
| AST: every `raise Refusal(` and `return CANNOT_RUN` + enclosing function | 8 production sites, table in the arming section | arming |
| falsifiability sweep: 37 single-edit mutations of the production code, suite run each time | 3 survived green (L2), 2 semantically inert, 1 killed via a different case; 32 killed | **L2, H1** |

**`--mutate .`:** see the line recorded at the end of this document. ⚠ **And it is green over B1,
B2 and H1 by construction** — no manifest entry's edit reaches `DELIBERATELY_UNHANDLED[0]`,
`_ARM_SHAPE_RE`'s indentation, or a `$(…)`-bearing fixture, so `0 survivors` says nothing about
any of the three. That is the same caveat round 3 attached to its own sweep, and it is why the
falsifiability sweep above was run instead of trusting it.

⚠ `check-review-recorded.py` rc=1 is by design per the brief (guarded code committed after the last
completed round) and I did not treat it as a finding.

**`python3 scripts/check-plan-code.py --mutate .`** — `OK — delivered scripts mutated: 56 file(s),
1154 mutation(s), 1154 killed, 1154 attributed to the case each names, 0 survivor(s)`, rc=0 —
**matches the coordinator's claim in every term.** (Run to completion; the verdict line above is
the run's own last line, not a recollection of the claim.)
