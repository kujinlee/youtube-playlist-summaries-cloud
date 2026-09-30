# Round 3, Claude half — the LLM recall matcher (backlog #191)

**Verdict: NOT CONVERGED.** Two Blocking, two High.

Subject: the FOLD, `c1b1d810..575fc7a2` (and the round-2 fold beneath it, `446025ab..HEAD`), not the
original. The brief's instruction was *"nine of fourteen findings last round were caused by the
previous fix; find the tenth."* **Both Blockings are that shape**: B1 is round-3 H1's own fix missing
a path the finding it folds explicitly enumerated, and B2 is a written bound inside round-3 M1's fix
that the fix does not have.

---

## BLOCKING

### B1 · The FOURTH instance: `--arm` still exits rc 2 for an unwritable cache, and the fix's own comment says it does not

`scripts/recall-llm.py:1047`:

```python
    return OK if written else CANNOT_RUN
```

`unanswerable_if_armed` is consulted at two boundaries, and both catch **raised** `Refusal`s.
`_arm_body`'s cache-write failure is not a raise. `scripts/recall-llm.py:1036-1040` catches the
`OSError` itself, sets `written = False`, prints the degraded notice, and then **returns** rc 2 — so
`do_arm`'s `except Refusal` at `scripts/recall-llm.py:1004-1005` never sees it.

This is the path the round-3 Codex half named, verbatim, in the finding this fold closes
(`docs/reviews/codex/recall-llm-r3-codex.md`, its `--arm` enumeration): *"cache write failure after
a paid answer: not routine."* It is also the one path the fix's own comment claims by name —
`scripts/recall-llm.py:999-1001`:

```python
    # be armed, so `call_model`'s missing CLI / timeout / non-zero / empty output and the cache
    # write are all rc 6, not the routine rc 2.
```

**The sentence is false about the half of it that is not a raise.** That is the same error the
docstring above it says it is repairing for the third time, at the fourth site.

**Reproduced** — a world valid in every respect except the cache directory, with the model answering
cleanly so the call is paid for and correct:

```
recall-llm: ONE call for 1 step(s) against 1 triggers (1896 chars) …
⚠ the cache could NOT be written ([Errno 20] Not a directory: '/dev/null/cannot-exist'). …
(not written): 1 of 1 step(s) matched an entry
   step 1: e1
do_arm() returned rc = 2
CANNOT_RUN is 2 / UNANSWERABLE is 6
```

**And nothing could have caught it.** `grep` over the suite and the manifest finds no case asserting
this return and no mutation entry whose edit reaches line 1047 — round 2's H3 fix introduced the
`written` flag and the degraded print, and asserted neither. So `--self-test` 196/196,
`check-rc-contract.py` rc=0 and `--mutate .` with 0 survivors are all green over it. This is the
convergence document's own recurring shape — *a case tested the callee while the defect sat at the
call site* — with the call site being a `return` rather than a `raise`.

⚠ **Bound, stated rather than left implied:** this is NOT hook-visible. The hook runs `--fire` only
(`.claude/hooks/surface-recall.sh:45`), so no reader is currently silenced by it, and the message
*is* printed on stdout. What is wrong is the CODE, and the code is the contract: rc 2 means "no plan
armed", the hook's catch-all is built on that meaning, and any future caller of `--arm` — an
arm-on-tick hook is the obvious one — reads a lost paid answer as the routine absence.

**The observation that would prove this finding wrong:** `do_arm` returns 6 (or any non-2 code) when
the cache cannot be written after a successful model call, while still returning 2 for no sentinel.

### B2 · `check-rc-contract.py`'s written bound is FALSE — an unmodelled quoting form produces a WRONG ANSWER, not a cannot-run

`scripts/check-rc-contract.py:187-189` (`structural_lines`'s docstring):

```
    ⚠ BOUND: it models double quotes only. Single quotes, `$'…'` and heredocs are not tracked — the
    hook uses none of them today, and `arm_soundness` refuses any shape this does not classify, so
    an unmodelled quoting form surfaces as a cannot-run rather than a wrong answer.
```

The second clause does not follow from the first. `arm_soundness` refuses a head it cannot
**classify** (`scripts/check-rc-contract.py:220-221`):

```python
        if head == "*" or head.isdigit():
            continue
```

A bare integer inside a single-quoted string is perfectly classifiable. It is silently accepted as
an arm, so `handled_codes` reports a code the hook does not handle — which is backlog #202's shape,
the exact defect this guard owns.

**Reproduced, and adjudicated by real bash.** A hook whose only unmodelled construct is one
single-quoted multi-line message:

```bash
  3) MSG='the cache is stale.
5) re-arm the plan'
     [ -n "$OUT" ] && PAYLOAD="$MSG Detail: $OUT" ;;
```

```
arm_soundness : CLEAN — no cannot-run
handled       : [0, 3, 5, 6]
unguarded     : []
verdict       : EMPTY -> the guard would exit 0
  bash RC=0: PAYLOAD=[detail text]
  bash RC=3: PAYLOAD=[the cache is stale.
5) re-arm the plan Detail: detail text]
  bash RC=5: PAYLOAD=[]        <-- rc 5 is SILENTLY DROPPED
  bash RC=6: PAYLOAD=[corpus gone]
```

The guard says rc 5 is handled; bash swallows it into the catch-all and the reader hears nothing.
`$'…'` fails the same way (measured: `handled` loses 5 and the guard mis-attributes an unguarded
`Detail:` to arm `3)`), and a heredoc does too once it is not wrapped in the double quotes that
accidentally masked my first attempt.

The failure is not that the reader is incomplete — its own docstring says a hand-rolled reader
"CANNOT be made correct. It CAN be made unable to be silently wrong", and that is the right
standard. The failure is that the **falsifier for that standard is the sentence above, and the
sentence is not true**, so the bound reads as a closed hole and is an open one. A written reason that
is false is worse than an absent one; this repo's record for that is the *stated bound outlives its
hole* shape.

**The observation that would prove this finding wrong:** `structural_lines` tracking single quotes
and `$'…'`, or `arm_soundness` refusing a `case` block that contains any single-quote or heredoc
token at all — either makes the docstring's claim true.

---

## HIGH

### H1 · M1's fix freed the indentation in `_ARM_RE` and left a hard-coded two-space catch-all further down the same module

`scripts/check-rc-contract.py:112` was widened for round-3 M1:

```python
_ARM_RE = re.compile(r"^[ \t]*(\d+)\)", re.M)
```

`scripts/check-rc-contract.py:245`, inside `unguarded_detail_arms`, was not:

```python
    catchall = hook_src.find("\n  *)")
```

The catch-all's position is what terminates the LAST numeric arm's span, so when `*)` is not at
exactly two spaces the last arm's span runs to the end of the block and swallows the catch-all's
text. If the catch-all carries an `[ -n "$OUT" ]` — which is the obvious future improvement for
"never swallow an unknown rc" — the last arm's unguarded `Detail: $OUT` is masked.

**Reproduced. Two hooks identical but for the indentation of `*)`:**

```
[catch-all at TWO spaces (canonical)]
   unguarded    : [6]
   verdict      : ['the `6)` arm interpolates $OUT into a `Detail:` clause with no `[ -n "$OUT" ]` guard …']
[catch-all at FOUR spaces (the only change)]
   unguarded    : []
   verdict      : EMPTY -> exit 0
```

`arm_soundness` reported CLEAN in both. This is M1 fixed as an instance rather than as a class: the
mutation entry added for it ("*the arm reader goes back to two-space indentation only*") targets
`_ARM_RE` and cannot see line 245, which is why the sweep is green over it.

**The observation that would prove this wrong:** `unguarded_detail_arms` locating the catch-all with
the same indentation-free rule `_ARM_RE` uses (or `_ARM_SHAPE_RE`'s `*` head), and a mutation entry
that reverts THAT line reddening a case.

### H2 · `DELIBERATELY_UNHANDLED[2]`'s written reason is false in two further ways, one of which the matcher cannot control

`scripts/check-rc-contract.py:89-93` is the escape hatch that makes R1 green over rc 2:

```
    2: "CANNOT RUN is the ROUTINE absence — no plan armed. …
```

Measured, every invocation form:

| invocation | rc | what rc 2 means there |
|---|---|---|
| `--fire` | 0 | — |
| `--arm --fire` | **2** | `main`'s own usage refusal (`recall-llm.py:2396-2398`) |
| *(no flag)* | **2** | same |
| `--fier` | **2** | **argparse's** usage-error convention — not this file's code at all |
| `--fire --extra` | **2** | same |
| `--print-prompt` | 0 | — |

So rc 2 carries at least three meanings before B1 is counted: the routine absence, a usage error the
matcher chooses, and a usage error **argparse hardcodes and the matcher cannot renumber**. The
hook's catch-all is built on the single meaning, so a hook edited to pass a flag the installed
matcher does not yet have — a stale worktree, a partial checkout, a flag added to the caller first —
makes the matcher permanently inert with nothing said. That is B1's sentence in the only mode the
hook runs.

The reason's own last line is the test it fails: *"If you find yourself widening this sentence again,
split the code instead."*

**The observation that would prove this wrong:** `main` returning a code other than 2 for a usage
error (argparse's can be overridden by catching `SystemExit` around `parse_args`), or the rc-2 reason
enumerating the usage paths and explaining why a caller may treat them as routine.

---

## MEDIUM

### M1 · `DELIBERATELY_UNHANDLED[4]`'s reason misstates its own evidence, and it inherited the error from F7

`scripts/check-rc-contract.py:94-97`:

```
    4: "RESPONSE REJECTED can only arise on the `--arm` path (every `ResponseRejected` raise site "
       "is inside `parse_response`, which only `--arm` calls), and this hook runs `--fire` only. "
```

Enumerated by AST over the current tree — the raise sites and their enclosing functions:

```
  line 612  in parse_response
  line 633  in parse_response
  line 580  in no_duplicate_keys      <-- not parse_response
  line 618  in parse_response
  line 639  in parse_response
  line 642  in parse_response
```

**The conclusion survives; the stated evidence does not.** `no_duplicate_keys` has exactly one
caller, `scripts/recall-llm.py:616`, as `json.loads`'s `object_pairs_hook` inside `parse_response`,
and `--fire`'s own JSON read (`parse_cache`, `scripts/recall-llm.py:718`) passes no hook. So rc 4
still cannot reach `--fire`. But a reader re-deriving the reason by grepping raise sites finds the
sentence false and cannot tell whether the conclusion holds without rebuilding the call graph — and
the reason exists precisely so that re-derivation is unnecessary.

⭐ **The sentence was copied from a document where it was ALREADY false.**
`docs/reviews/architecture-review-2026-09-30-recall-matcher.md:255-257` says *"every
`ResponseRejected` raise site (`recall-llm.py:520,552,558,573,579,582`) sits inside
`parse_response`"* — and at the reviewed tree `d26c79d6`, line **520** is in `no_duplicate_keys`
(verified by AST against `git show d26c79d6:scripts/recall-llm.py`). The review cited the line number
that refutes it. That is *quote-the-code-don't-characterise-it* failing in the direction it is
usually safe in: the quote was right and the characterisation of it was wrong.

**Proved wrong by:** the reason naming `no_duplicate_keys` and its single call site, or a case
asserting `parse_cache` passes no `object_pairs_hook`.

### M2 · The `⟳` correction to the architecture review landed at ONE site; the same corrected-away claim still stands in F7 and F6

The newest fold's only edit to that document inserts a `⟳` after the primary verdict
(`:57-63`), conceding that *"nothing reconciles"* is now *"a reconciliation guard exists"*. F7
repeats the claim as a **measured table** and was not touched. Re-measured:

| F7 row | F7 says | measured now |
|---|---|---|
| mutation manifests targeting the hook | none | **none** ✓ still true |
| scripts or workflows reading the hook | **none** | `scripts/check-rc-contract.py`, `.github/workflows/ci.yml` |
| self-test cases driving the hook end to end | 0 | **0** ✓ still true |

F7's prose *"Nothing reconciles the two halves of the rc contract: the matcher can emit `{0,2,3,4,5}`
and the hook distinguishes `0`, `3`, `5`, with `2` and `4` falling into a catch-all"* is stale twice
over — the set is `{0,2,3,4,5,6}` and the hook distinguishes `0,3,5,6`. F6's *"Run live: `guards
discovered (41)`"* (`:222`) now measures **42**, the difference being `check-rc-contract.py` itself;
F6's load-bearing half, *"`recall-llm.py` appears 0 times"*, is still true.

This is the *after-fixing-search-for-the-class* shape applied to a document: one sentence corrected,
three copies of it left. The reviewed-tree figures I checked all reproduce and need no correction —
2204 lines, 78-line hook, 1024-line `begin-plan.py`, 22 commits, `--self-test` 185/185, 93 loose-only
of 96 plans, and F8's finding table (2 Blocking, 14 High, 16 total, verified by counting headings in
all four r1/r2 documents) — so the defect is specifically the un-annotated staleness, not the
measurements.

**Proved wrong by:** F7 and F6 carrying the same `⟳` scoping the document as a pre-guard snapshot,
which the primary verdict now has and they do not.

### M3 · The one rule has a boundary at two of the THREE places the armed scope opens

`prepared_prompt` and `do_arm` consult `unanswerable_if_armed` at a boundary. `_fire` opens an armed
scope at exactly the same point — the line after `read_armed_plan()` returns
(`scripts/recall-llm.py:1078`) — and has no boundary. `do_fire` wraps `_fire` only for the dedupe
(`scripts/recall-llm.py:1068-1074`) and re-raises the original class.

Today nothing under `_fire` raises a bare `Refusal`: every refusal is a subclass, `read_or_refuse` is
passed `StaleCache` at `scripts/recall-llm.py:1100`, and `live_trigger_for` swallows its own
`OSError` (`scripts/recall-llm.py:475-476`). So this is **latent, not live**, and it is protected by
exactly the per-site discipline that `unanswerable_if_armed`'s own docstring says produced the next
round's findings:

```
    ⭐ ONE RULE, CONSULTED AT THE TWO BOUNDARIES WHERE THE ARMED SCOPE OPENS — not a class change
    at each raise site.
```

`read_or_refuse`'s default parameter is `refusal: type = Refusal` (`scripts/recall-llm.py:397`), so
one new call on the `--fire` path that omits the class argument is rc 2 in the one mode the hook runs.

**Proved wrong by:** a boundary in `_fire` after `read_armed_plan()` (or `read_or_refuse` losing its
default so every caller must name a class), plus a case driving it.

### M4 · The `Detail:` detector is literal-adjacent, and the hook's own append idiom evades it one statement away

`scripts/check-rc-contract.py:115`:

```python
_OUT_IN_LABEL = re.compile(r"(?:Detail|detail):\s*\$OUT")
```

The live `5)` and `6)` arms build their detail by appending — `PAYLOAD="$PAYLOAD Detail: $OUT"`. Split
that one append into two and the regex sees nothing:

```bash
  6) PAYLOAD="corpus gone"
     PAYLOAD="$PAYLOAD Detail:"
     PAYLOAD="$PAYLOAD $OUT" ;;
```

Measured: `unguarded []`, `verdict EMPTY -> exit 0`, while bash emits a sentence ending `Detail:`
with nothing after it for a deduped rc 6 — backlog #201 exactly, in the arm #202 added.

Related and in the same function: `unguarded_detail_arms` runs `_ARM_RE` over its raw argument and
does **not** pass it through `structural_lines`, unlike `handled_codes`
(`scripts/check-rc-contract.py:230-233`). The two readers of the same block disagree about what a
line is, which is `CONTEXT.md`'s structural-line distinction applied inconsistently inside one
module. I could not build a silent miss from that asymmetry alone (my attempts produced loud false
positives), so it is reported here rather than as its own finding.

**Proved wrong by:** a detector that asks whether an arm's span writes a `Detail:` label and
interpolates `$OUT` anywhere within it, rather than adjacently.

---

## LOW

### L1 · `check-rc-contract.py`'s docstring declares two of the matcher's numbers, both now stale, and no guard owns them

`scripts/check-rc-contract.py:27`:

```
`recall-llm.py` has 188 self-test cases and 91 mutation entries; every one of them lives on the
```

Measured: `scripts/recall-llm.py:102` declares **196** and `scripts/mutations/recall-llm.json` holds
**94**. `check-selftest-counts.py` verifies a script's own declared count by running it — it has no
row for a count one script asserts about another, and reported rc=0 over this. The
*document-inside-the-corpus-it-measures* shape, in a guard's prose.

---

## Areas I could NOT establish

- **Item 6 — the next ambient-reason case. I looked and found none; this is a measured null result,
  not a skipped check.** Two probes, one hooking `pathlib.Path`'s ten syscall-facing methods and one
  hooking `builtins.open` plus `os.listdir/scandir/stat/mkdir/makedirs`, recorded every access under
  the live `.claude/` or `~/.claude/projects/` during a full 196-case run. Total: **2** accesses, both
  `os.stat`/`is_dir` on `~/.claude/projects/-private-var-folders-…-T-tmpXXXX-repo/memory` — a slug
  derived from the case's own temp `ROOT`, so deterministically absent rather than ambient. The suite
  is 196/196 both at baseline and with `HOME` redirected to an empty directory. ⚠ **Bound:** the
  probes see Python-level filesystem calls only, and I did not empty the live
  `.claude/recall-cache/` (that would mutate the repo, which my brief forbids) — the `HOME`
  redirection and the access census are what stand in for it.
- **The `;;&` / `;&` fall-through semantics.** `unguarded_detail_arms`' span model treats arms as
  independent, which bash's fall-through terminators break. My probe still produced a loud finding
  rather than a silent miss, so I could not turn it into a defect and did not file one.
- **The hook as sole caller against live state.** Not run: it consumes the live `.last-said` and
  `.last-surfaced` markers. The bash adjudication in B1/B2/H1/M4 runs the `case` block in isolation
  instead, which answers the same question about arm dispatch.
- **Whether the `2204`/`78`/`1024` sizes in the architecture review's header should carry a `⟳`.**
  They reproduce exactly at `d26c79d6` and the document names that tree, so I treated them as
  correctly scoped rather than stale. A reader who takes the header as current would be wrong by
  213 lines on the matcher; that is a judgement about document convention, not a measurement.

---

## Verified

Every command run, with its output.

| command | output |
|---|---|
| `python3 scripts/recall-llm.py --self-test` | `196/196 self-test cases passed` — matches the claim |
| `HOME=<empty dir> python3 scripts/recall-llm.py --self-test` | `196/196 self-test cases passed` |
| `python3 scripts/check-rc-contract.py` | `6 code(s) defined, 4 handled by an arm, 3 declared unhandled` / `rc contract OK` · rc=0 — matches |
| `python3 scripts/check-rc-contract.py --self-test` | `35/35 self-test cases passed` — matches |
| `python3 scripts/check-ratchet-contract.py` | rc=0; `guards discovered (42)` — matches rc, refutes F6's `41` |
| `python3 scripts/check-fixture-variation.py` | `728 parameter(s) … 61 file(s); 117 known-unvaried ratcheted, 7 exempt` · rc=0 — matches |
| `python3 scripts/check-selftest-counts.py` | `49 script(s) declare a count, every one verified by running it` · rc=0 — matches |
| `python3 scripts/check-plan-code.py --self-test` | `131/131 passed` — matches |
| `python3 scripts/check-plan-code.py --mutate .` | see the line below |
| `python3 scripts/recall-llm.py` with `--fire` / `--arm --fire` / *(none)* / `--fier` / `--fire --extra` / `--print-prompt` | rc `0 / 2 / 2 / 2 / 2 / 0` — H2's table |
| `do_fire` rc census over five isolated worlds | no sentinel `2` · armed/no cache `3` · armed/no cache/unwritable cache dir `3` · sentinel names nothing `5` · undecodable plan `5` — **`--fire`'s rc 2 is confined to the no-sentinel case**, so the conjunction is closed on that side |
| AST enumeration of `ResponseRejected` raise sites, HEAD and `d26c79d6` | 5 in `parse_response`, **1 in `no_duplicate_keys`**, at both trees — M1 |
| AST enumeration of `parse_response` callers | one production caller, `_arm_body:1013`; the rest are `_self_test` — M1's conclusion holds |
| `Refusal` subclass rc audit | `Refusal` 2 · `StaleCache` 3 · `ResponseRejected` 4 · `UnreadablePlan` 5 · `Unanswerable` 6; `__init__(message)` only, no rc parameter — item 3 below |
| `do_arm` / `prepared_prompt` over four isolated worlds | no sentinel `2/2` · readable plan, no corpus `6/6` · unreadable plan `5/5` · all present `0/0` — item 2 below |
| `grep -rl surface-recall scripts/mutations/` | nothing — F7 row 1 still true |
| `grep -rln surface-recall scripts/ .github/` | `scripts/check-rc-contract.py`, `.github/workflows/ci.yml` — F7 row 2 refuted |
| `_BOX_RE`/`_LOOSE_BOX_RE` over `docs/superpowers/plans/*.md` | `total 96 \| strict-readable 0 \| loose-only 93 \| no checkboxes 3` — F2 reproduces |
| heading counts over the four r1/r2 review documents | 2 Blocking, 14 High, 16 total — F8 reproduces |
| `EXPECTED_MUTATIONS` vs manifests | `recall-llm.py` 94/94 · `check-rc-contract.py` 9/9 · `check-memory-link.py` 8/8 — agree |
| `git rev-list --count 446025ab..d26c79d6`; reviewed-tree `wc -l` | 22; 2204 / 78 / 1024; `--self-test # 185 cases` — the header reproduces |

**`--mutate .`:** `OK — delivered scripts mutated: 56 file(s), 1145 mutation(s), 1145 killed, 1145 attributed to the case each names, 0 survivor(s)`, rc=0 — **matches the claim in every term**. ⚠ And it is green over B1: no manifest entry's edit reaches `recall-llm.py:1047`, so 0 survivors says nothing about that line. I also checked that all seven mutation anchors added in this fold bind EXACTLY ONCE in the delivered files (the *anchor unbound by any nearby edit* class) — all seven do.

### The three things the brief asked me to VERIFY rather than attack, and their answers

1. **Item 2 — is the boundary placed correctly, or does it over-convert?** *Correctly, and it does
   not.* `do_arm` wrapping `_arm_body` and not `prepared_prompt()` is load-bearing: over the four
   worlds above, "no sentinel" stays rc 2 in both modes. And `--print-prompt` agrees with `--arm` on
   all four, which it does because it returns from inside `prepared_prompt`, on the far side of that
   function's own boundary.
2. **Item 3 — is dropping `type(exc) is Refusal` safe?** *Yes, and the new rule is strictly more
   correct.* No subclass carries rc 2 (audit above), and `Refusal.__init__` accepts a message only —
   there is no rc parameter, so no path constructs a bare `Refusal` with a non-default code. An
   instance's `rc` can be reassigned in principle, and nothing in the file does it. A future rc-2
   subclass now converts, which the old predicate would have silently refused.
3. **The `check()`-truncation class the brief named.** Closed: `scripts/recall-llm.py:1272-1277`
   evaluates the thunk inside its own `try` and turns a raise into a named `[FAIL]` line, so a
   mutation that makes a case raise cannot truncate the cases below it. The new round-3 helpers
   (`_prepared_with`, `_arm_body_failing`) restore their globals in a `finally`, so a raise inside
   one cannot leak a stub into a later case either.

---

## What this round says about arming

**The architecture review still does not arm, and B1 is why it does not rather than why it should.**
`docs/dev-process.md:113` (the round-2 convergence document cites this rule as `:108`; it has since moved) requires two consecutive rounds whose findings came from the previous
round's fix, in ONE component. Round 3 is unambiguously fix-caused — B1 and B2 both are, and so is
H1 — which makes round 2 and round 3 a consecutive pair. But the second half of the condition is not
met, and the distinction is the same one round 2's convergence document drew: **no component has been
re-opened twice.** B1 is a new site in the rc contract (a `return`, where every prior instance was a
`raise`); B2 and H1 are in a guard that did not exist at round 2; M1 and M2 are documents. The
component that keeps producing findings is *the rc contract as a whole*, and a redesign can still
remove each instance — which is `review-method.md`'s test, answered yes.

⭐ **The shape worth carrying into round 4 is narrower than "boundary relocation".** Three times now
the rule has been moved to a boundary and the boundary has been placed on the RAISE path only:
`do_fire`'s per-site `Unanswerable` in #202, and now `do_arm`'s. **A `return` is an exit from the
armed scope too**, and nothing in this file's design treats it as one.
