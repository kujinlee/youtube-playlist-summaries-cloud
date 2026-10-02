# Round 5, Claude half — the rc contract guard (backlog #201/#202)

**Verdict: NOT CONVERGED.** One Blocking, two High, three Medium, four Low.

Subject: `scripts/check-rc-contract.py` as it stands on disk on `semantic-recall-replication`
(uncommitted changes included), the hook it observes (`.claude/hooks/surface-recall.sh`), the
matcher whose exit codes are the contract (`scripts/recall-llm.py`) and
`scripts/mutations/check-rc-contract.json`.

⭐ **The headline is that the redesign is sound in TWO of its three rules and the third was never
converted.** R1 and R2 now ask bash, and I could not break either: `defined_codes` is genuinely
`ast`-based, the staged hook is byte-identical to the shipped one, `dead_arms` is exhaustive and
attributes correctly under concurrency, and Codex's H1 is fixed. **R3 is still a hand-written
reader** — not of bash syntax this time, but of an ENGLISH LABEL VOCABULARY two entries long
(`"Detail:", "detail:"`), and of only ONE of the two wrong states around it. The open set moved; it
did not die. B1 and H1 are both instances of that one sentence.

⤳ **Two follow-up leads from the coordinator on `defined_codes` were measured after the first
filing and are M3 and L4.** The "a regex reader survived the redesign" hypothesis is REFUTED —
the function really is `ast` — but a narrower member of the same family is live in it: the two
tuple sides are filtered independently and then zipped positionally. The `bool`-subclasses-`int`
lead is refuted on measurement.

The second theme is narrower and worth as much: **the round-5 fix is wired through an argument
nothing reads.** H2 shows R2 — the entire rule Codex's H1 was about — can be switched off by
deleting one argument at one call site, with the suite at 43/43 and the live run green.

I verified, and do not re-report, the three things the Codex half established: the H1 fix (below,
exhaustively), repo byte-identity across runs, and hostile-payload survival.

---

## BLOCKING

### B1 · The fix the hook's own comment FORBIDS BY NAME passes the guard with zero problems, and the reader gets ZERO BYTES at rc=5

`.claude/hooks/surface-recall.sh:75-77` writes the rule down:

```bash
  # ⛔ AND NOT `[ -n "$OUT" ] && PAYLOAD=…` LIKE ITS SIBLINGS: that makes a deduped rc=5 SILENT,
  # which is the conflation B1 split this code out of rc=2 to end. rc=5 IS NOT SILENCE. So the
  # static sentence always goes, and only the detail is conditional.
```

`scripts/check-rc-contract.py:41-43` writes the SAME rule down, inside R3's own statement:

```
  R3  No arm interpolates `$OUT` into a LABELLED clause without guarding on `[ -n "$OUT" ]`
      first — the #201 shape. An arm may forward unconditionally (rc=5 must never be silent) and
      it may use `$OUT`; what it may not do is promise a detail it might not have.
```

**Nothing checks the parenthetical.** `handled_codes` (`:271`) probes only with a NON-EMPTY payload:

```python
    return {rc for rc in sorted(codes) if observe(hook_src, rc, _PROBE)}
```

and `dangling_detail` (`:283-285`) probes with an empty one but SKIPS a silent code:

```python
        payload = observe(hook_src, rc, "")
        if not payload:
            continue
```

So the state "rc=5 forwards when there is detail and is SILENT when there is not" is seen by
`handled_codes` as handled and by `dangling_detail` as nothing at all.

**Reproduction (run, three variants over the same skeleton, probe range narrowed to 10 for wall
clock only — the verdict column is unaffected):**

```text
RIGHT  (shipped): static sentence always, detail conditional
  handled=[0, 3, 5, 6] dangling=[] -> verdict 0 problem(s)
  reader@rc5 with NO detail  -> 'unreadable.\n'
  reader@rc5 WITH detail     -> 'unreadable. Detail: D\n'

WRONG-A (#201): unconditional Detail: label
  handled=[0, 3, 5, 6] dangling=[5] -> verdict 1 problem(s)
  reader@rc5 with NO detail  -> 'unreadable. Detail: \n'
  reader@rc5 WITH detail     -> 'unreadable. Detail: D\n'

WRONG-B (the fix the hook comment FORBIDS): whole arm guarded -> deduped rc=5 is SILENT
  handled=[0, 3, 5, 6] dangling=[] -> verdict 0 problem(s)
  reader@rc5 with NO detail  -> ''
  reader@rc5 WITH detail     -> 'unreadable. Detail: D\n'
```

WRONG-A is caught. **WRONG-B is not, and WRONG-B is the one the hook's comment predicts someone
will write** — it is the "obvious fix" for #201, it is what the siblings do, and the comment exists
because it was considered. The guard that exists to reconcile this pair reports full agreement over
it.

**The silence is REACHABLE, not hypothetical.** `scripts/recall-llm.py:1105-1109` (`do_fire`)
deduplicates the sentence of EVERY `Refusal` subclass while keeping the rc:

```python
        msg = str(exc)
        if msg and not nag_once(CACHE_DIR / ".last-said", hashlib.sha256(
                msg.encode("utf-8")).hexdigest()[:16]):
            raise type(exc)("") from exc.__cause__
        raise
```

`UnreadablePlan` is a `Refusal` subclass, so "rc 5 with an empty message" is the normal state from
the second firing onward — which is #201's own measured artefact (409 chars, then 148, then 148,
`check-rc-contract.py:19-20`). Under WRONG-B that becomes 0 bytes, which is #202's artefact
("290 bytes of control against ZERO", `:23`) reproduced on the code #202's sibling split out.

**The repair needs no new machinery, which is why this is Blocking rather than a design argument.**
The guard already computes both halves of the comparison and compares neither: `observe(rc, _PROBE)`
inside `handled_codes` and `observe(rc, "")` inside `dangling_detail`. A fourth rule — *a code
declared must-never-be-silent must forward a non-empty payload when the matcher printed nothing* —
is one predicate over values already in hand. It needs a declared set with written reasons
(rc 5 and rc 6 must not be silent; rc 0 and rc 3 legitimately are, and both say so in the hook),
which is the `DELIBERATELY_UNHANDLED` idiom this file already uses, inverted.

**What would prove this wrong:** a probe showing `verdict()` non-empty for WRONG-B, or a
demonstration that `do_fire`'s dedupe cannot produce an empty message on the rc=5 path — which
`:1105-1109` and the file's own measured 409/148/148 both contradict.

---

## HIGH

### H1 · R3's detector enumerates ENGLISH LABEL SPELLINGS, so #201's exact reader-visible defect survives a one-letter change

`scripts/check-rc-contract.py:286`:

```python
        for label in ("Detail:", "detail:"):
```

This is the same shape as the deleted lexer, one abstraction layer over: the deleted code
enumerated the ways bash can quote a line and every round found one more member; this enumerates
the words a hook might use to promise a detail, and the set of those is not finite either.
`"Details:"` — one added letter, and it CONTAINS `"Detail"` but not `"Detail:"` — defeats it.

**Reproduction, four variants plus a known positive proving the probe can find something:**

| `5)` arm | what the reader gets with no detail | `dangling_detail` |
|---|---|---|
| `PAYLOAD="unreadable. Detail: $OUT"` (control) | `'unreadable. Detail: \n'` | **`[5]`** |
| `PAYLOAD="unreadable. Reason: $OUT"` | `'unreadable. Reason: \n'` | `[]` |
| `PAYLOAD="unreadable. Details: $OUT"` | `'unreadable. Details: \n'` | `[]` |
| `PAYLOAD="unreadable: $OUT"` | `'unreadable: \n'` | `[]` |
| `PAYLOAD="unreadable. Detail: $OUT (end)"` | `'unreadable. Detail:  (end)\n'` | `[]` |

Every one of the last four is #201 as a reader experienced it — a sentence that promises something
and stops — and the guard built to catch #201 by running the hook returns `[]` for all of them. The
control proves the probe works, so the four `[]`s are negatives about the detector and not about my
method.

The fourth row is a second, independent hole in the same function: `partition` + `not tail.strip()`
(`:287-288`) only sees a label at the very END of the payload. The mid-string case is missed even
when the label is spelled exactly right.

**The sound form is derivable, not enumerable** — which is the same move the redesign already made
once. The guard runs each code twice; `pre = observe(rc, _PROBE).partition(_PROBE)[0]` is *the text
the hook itself puts immediately before its detail*, derived from bash rather than guessed. If
`observe(rc, "")` ends with that same text and that text ends in punctuation, the arm promises a
detail it does not have — with no vocabulary anywhere, and the mid-string case included for free.

**What would prove this wrong:** a `dangling_detail` that returns `[5]` for `Reason:`, `Details:`
and the mid-string form; or an argument that R3's subject is the literal word "Detail" rather than
the class of promise — which `:42-43`'s own wording ("promise a detail it might not have")
contradicts.

### H2 · R2 can be switched off by deleting one argument at one call site, and nothing covers it — not a case, not a mutation

`scripts/check-rc-contract.py:329-330`:

```python
def verdict(defined: dict[str, int], handled: set[int], dangling: list[int],
            dead: list[int] | None = None) -> list[str]:
```

`:384`:

```python
    problems = verdict(defined, handled, dangling, dead)
```

`dangling` is positional-required, so dropping IT is a `TypeError`. `dead` has a default, so
dropping it is legal Python and silently disables the whole dead-arm rule — the rule Codex's H1 was
about, and the rule the round-5 diff spent its two new mutation entries on.

**Reproduction, in a sandbox copy, with a control:**

```text
# mutation: `verdict(defined, handled, dangling, dead)` -> `verdict(defined, handled, dangling)`
live run        : rc contract OK                                                   rc=0
self-test       : 43/43 self-test cases passed                                     rc=0
# then a real dead arm added to the hook (`7) PAYLOAD="dead arm" ;;`):
mutated guard   : rc contract OK                                                   rc=0
CONTROL, unmutated guard, same dead arm:
                  FAILED — 1 disagreement(s) … the hook ACTS on rc 7 …             rc=1
```

The control is the point: R2 works, and one deleted argument makes it report clean over the very
arm it detects. The two round-5 mutation entries both target `dead_arms`' RANGE
(`probe_max=255` → `15`, `range(probe_max + 1)` → `range(probe_max)`); neither asks whether the
result is READ. This is this repo's recorded "unit coverage does not compose" shape — the gap is
between two tested pieces, at the call site.

**Two fixes, either sufficient:** drop the `= None` default so the mutation becomes a `TypeError`,
or add a mutation entry on `:384`. The default is not load-bearing — `main` is the only caller
(`grep -c "verdict(" scripts/`: all other occurrences are in the suite, which passes `dead`
explicitly at every call).

**What would prove this wrong:** a self-test case or manifest entry that goes red on the `:384`
edit. I applied all ten manifest entries individually (below) and none of them touches that line.

---

## MEDIUM

### M1 · `defined_codes` reads only the ONE tuple that contains all six hardcoded names, so a seventh code assigned separately is invisible to R1 — #202's shape exactly

`:84`:

```python
_RC_NAMES = {"OK", "CANNOT_RUN", "STALE_CACHE", "BAD_RESPONSE", "UNREADABLE_PLAN", "UNANSWERABLE"}
```

`:160`:

```python
        if not _RC_NAMES.issubset(set(names)):
            continue
```

R1 is stated as *"Every rc constant the matcher DEFINES"* (`:36`). As implemented it is *"every
constant in the one tuple assignment that happens to contain these six names"*. Measured:

```text
defined_codes(RC + "SEVENTH = 7\n")            -> {OK:0, CANNOT_RUN:2, … UNANSWERABLE:6}   # 7 unseen
defined_codes(RC + "SEVENTH, EIGHTH = 7, 8\n") -> {OK:0, CANNOT_RUN:2, … UNANSWERABLE:6}   # both unseen
```

A seventh code added that way, with no arm in the hook, leaves the guard printing `rc contract OK`
while the catch-all swallows it — which is #202 verbatim, and it is the instance the docstring at
`:37-38` names as "the obvious next instance". The suite's case at `:432-434` tests only the
tuple-EXTENSION form and so creates the belief that "a new code is picked up without touching this
guard"; that is true of one of the two ways to add one.

⚠ **The obvious fix false-fires, and I checked before proposing it.** "Every module-level
UPPERCASE name bound to an int literal must be in the rc tuple" would flag
`scripts/recall-llm.py:129` (`CALL_TIMEOUT = 600`). Derived by AST over the matcher's module body:
the int-literal uppercase constants are the six rc names and `CALL_TIMEOUT`; `ROOT`/`SENTINEL`/
`CACHE_DIR` are Paths and `TRIGGER_PREFIX`/`NONE`/`MODEL`/`LIVE_*` are strings. So the rule needs a
narrower subject — the constants actually RETURNED as an rc, or an explicit refusal when the
matcher's rc names are not all in one tuple — and I am filing the hole, not a fix I have not tested.

**What would prove this wrong:** a mechanism that refuses a matcher defining an rc outside the
tuple, or a demonstration that the one-tuple layout is enforced somewhere. `grep -rn "_RC_NAMES"
scripts/` returns only this file.

### M2 · A file that EXISTS but cannot be READ exits 1 with a traceback, not 2 — and the docstring promises 2

`:56-61` promises:

```
FAILS IF
  * either file is missing or unparseable -> exit 2, CANNOT RUN, never a pass.
```

`:360-363` establishes existence and not readability (`is_file()` is true of a `chmod 000` file),
and `:365`/`:369` then read outside any handler for `OSError`:

```python
        defined = defined_codes(MATCHER.read_text(encoding="utf-8", errors="replace"))
    except CannotRun as exc:
```

**Measured, in a sandbox copy:**

| world | printed | rc |
|---|---|---|
| matcher missing | `FAILED: scripts/recall-llm.py not found — treat this as NOT RUN.` | **2** |
| hook missing | `FAILED: .claude/hooks/surface-recall.sh not found — treat this as NOT RUN.` | **2** |
| hook `chmod 000` | `PermissionError: [Errno 13] Permission denied: …` + traceback | **1** |
| matcher `chmod 000` | `PermissionError: [Errno 13] Permission denied: …` + traceback | **1** |
| no `bash` on PATH | `FAILED: no \`bash\` on PATH … Treat this as NOT RUN.` | **2** |
| `python3` unreachable to the hook | `FAILED: the hook acted on NONE of the matcher's codes … NOT RUN.` | **2** |

This does **not** fail open — CI fails either way — so it is Medium and not High. What it does is
state something false: rc 1 is this guard's "the two languages disagree", and the reader is told the
contract is violated when in fact nothing was measured. That is the distinction the whole file
exists to defend, applied to its own exit codes. A permission-denied read is the third shape of
"could not look", alongside missing and unparseable, and the promise names only two.

**What would prove this wrong:** a caller that treats 1 and 2 identically, making the distinction
cosmetic. `ci.yml:239-240` runs the guard as a bare step, so only pass/fail reaches CI — but the
docstring's promise is to a human reader, and it is the human who gets the traceback.

---

### M3 · `defined_codes` filters its two tuple sides INDEPENDENTLY and then zips them POSITIONALLY, so the rc names can bind to the wrong numbers — and the guard then prints `rc contract OK`

`scripts/check-rc-contract.py:159-166`:

```python
        names = [e.id for e in tgt.elts if isinstance(e, ast.Name)]
        vals = [int(v.value) for v in node.value.elts
                if isinstance(v, ast.Constant) and isinstance(v.value, int)]
        if len(names) != len(vals):
            raise CannotRun("the rc tuple assignment has mismatched names and values")
        found.append(dict(zip(names, vals)))
```

The two comprehensions drop elements for unrelated reasons — a non-`ast.Name` target, a non-int
constant value. The length test compares the two FILTERED lists, so when each side drops one
element at a DIFFERENT index the lengths agree and every pairing after the first drop is shifted.
The docstring at `:145-146` names this repo's recorded shape for it — *"a positional read with no
verified shape"* — about the "picks the first of several candidates" risk, and the same sentence
describes `zip` two lines below.

**Reachable, and the strongest form produces the REASSURING answer.** Each row below compares
`defined_codes`' answer against what Python actually assigns, taken by executing the same source:

| source (the six names, plus one extra target) | `defined_codes` returns | reality | misbound |
|---|---|---|---|
| `OK, CANNOT_RUN, …, UNANSWERABLE = 0,2,3,4,5,6` (control) | `{0,2,3,4,5,6}` | same | none |
| `…, mod.X, UNANSWERABLE = 0,2,3,4,5,'s',7` — both drops at the SAME index | `UNANSWERABLE: 7` | same | none |
| `…, UNANSWERABLE, *REST = 0,2,3,4,5,6,'x','y'` — both drops at the tail | `{0,2,3,4,5,6}` | same | none |
| **`OK, mod.X, CANNOT_RUN, …, UNANSWERABLE = 0,2,3,4,5,6,'s'`** | **`{0,2,3,4,5,6}`** | `CANNOT_RUN=3, STALE_CACHE=4, BAD_RESPONSE=5, UNREADABLE_PLAN=6, UNANSWERABLE='s'` | **5 of 6** |
| `D={}` + `OK, D['k'], CANNOT_RUN, …, = 0,2,3,4,5,6,'s'` | `{0,2,3,4,5,6}` | same as above | **5 of 6** |
| `OK, *MID, CANNOT_RUN, …, = 0,1,2,3,'s',5,6` | `CANNOT_RUN=1, STALE_CACHE=2, BAD_RESPONSE=3` | `2, 3, 's'` | **3 of 6** |

Note which answer the bad rows give: **exactly the live, correct-looking `{0,2,3,4,5,6}`**. This is
not a loud wrong number, it is the number a reader is expecting to see.

**End to end, the whole guard over such a matcher and the REAL hook:**

```text
rc contract: 6 code(s) defined, 4 handled by an arm, 2 declared unhandled
rc contract OK — every defined code is handled or declared, and no arm promises a detail it might not have
GUARD rc=0
```

while the same file, imported and read back, actually holds:

```text
{'OK': 0, 'CANNOT_RUN': 3, 'STALE_CACHE': 4, 'BAD_RESPONSE': 5, 'UNREADABLE_PLAN': 6, 'UNANSWERABLE': 's'}
```

The matcher now returns 3 for the ROUTINE "nothing is armed" absence, which the hook's `3)` arm
forwards as "the recall cache … is absent or stale, run `--arm`" on every `begin-plan.py` call; and
`UNANSWERABLE` is a string, so `sys.exit('s')` leaves exit 1, which the catch-all swallows. The
guard reports agreement over all of it.

⚠ **Reachability, stated rather than implied: no plausible refactor produces this shape.** It needs
a non-`Name` target (an attribute, a subscript, or a mid-tuple star) INSIDE the rc tuple together
with a non-int value at a different index. I am filing it anyway for two reasons and would not
without both. First, it is the one place in this function that fails WRONG while the other three
branches (no tuple, two tuples, unparseable) all fail closed — and `:145-146` asserts the opposite.
Second, the repair is free and verified not to false-fire: compare the RAW element counts, not the
filtered ones (`len(tgt.elts) == len(names) == len(node.value.elts) == len(vals)`), so anything the
reader does not fully understand becomes a `CannotRun`. Measured against the real matcher
(`recall-llm.py:116`): `raw targets=6 names=6 raw values=6 ints=6` — a strict reader accepts it
today. **That is the right direction for this function: refusing is cheap because the matcher is a
file in this repo, and a legitimate refactor can be made to satisfy a strict reader.**

**What would prove this wrong:** a `defined_codes` that raises `CannotRun` on the three bad rows
above, or a demonstration that a non-`Name` element cannot appear in that tuple — which the A3/A6
sources refute, since both are valid Python that executes.

---

## LOW

### L1 · A forwarding `*)` catch-all makes R1 vacuous, and the failure arrives as 250 uncapped lines that name the wrong thing

Measured, over a hook with a forwarding catch-all:

```text
forwarding catch-all, NO arms at all : handled=[0, 2, 3, 4, 5, 6]  dead=250 (1..255)  verdict=250
full arms + forwarding catch-all     : handled=[0, 2, 3, 4, 5, 6]  dead=250            verdict=250
catch-all echoing $OUT               : handled=[0, 2, 3, 4, 5, 6]  dead=250
```

A hook with **no arms at all** produces ZERO R1 problems — every code reads as handled — and
`main`'s summary line says `6 handled by an arm`, which is a false sentence read as reassurance.
The run does fail, loudly, but only via R2, and the 250 messages all say "dead arm" when the defect
is "the catch-all forwards". `verdict` has no cap, so the one thing a reader needs is not in the
output at all. Not a fail-open; a diagnosis that points away from the cause.

### L2 · The contract has a THIRD direction and nothing reconciles it, while the docstring's "what it does not check" list omits it

`:36-43` covers defined→handled (R1) and arm→defined (R2). Nothing covers **emitted→defined**: a
code the matcher produces that no constant names. `scripts/recall-llm.py:2530-2546` catches only
`Refusal`, so any other escaping exception exits 1; a missing `python3` exits 127. Both land in the
hook's catch-all as silence, and the guard never asks, because neither is "defined".

Silence is probably the RIGHT response (both are "the matcher never got to look", which is
`DELIBERATELY_UNHANDLED[2]`'s own argument) — but rows 2 and 4 exist precisely so that a code the
hook ignores has a written reason, and these have none. `:49-54`'s "WHAT IT DOES NOT CHECK" lists
the *opposite* asymmetry (defined-but-unreachable) and not this one. I could not construct a
reachable rc=1 against the current matcher: `read_or_refuse` (`:409-413`) catches `OSError` and
`UnicodeDecodeError`, and `live_trigger_for` (`:473-476`) catches both too. So this is a gap in the
DECLARED contract, not a live defect.

### L3 · Three refusal paths have no self-test case and no mutation entry

- `observe`'s `TimeoutExpired` → `CannotRun` (`:245-246`). No case. I exercised it: a hook that
  backgrounds `sleep 45` → `CannotRun after 30.0s: the hook did not finish within 30s at rc=0`.
- `observe`'s `FileNotFoundError` → `CannotRun` (`:243-244`). No case. Exercised: rc=2, correct.
- all four of `main`'s refusal branches (`:362`, `:367`, `:378`, `:381`). No case. All four
  exercised by hand in M2's table; all four behave correctly except the one M2 reports.

⚠ One measured nuance about the timeout, worth recording because the exception text overstates it:
`subprocess.run(capture_output=True)` returns on **pipe EOF**, not on the hook exiting. A hook that
backgrounds a process holding stdout blocks `observe` for the grandchild's lifetime — measured, a
hook that runs `sleep 8 &` and exits immediately returned after **8.0s** with `''`. The 30s ceiling
does hold (measured above), so this is a latency note and not a hang; the message "the hook did not
finish within 30s" names an event the code does not measure.

### L4 · A duplicate rc value is absorbed by set arithmetic, and the guard either says OK with a false count or blames the hook for the matcher's defect

`verdict` iterates `defined.items()` and tests `code in handled` (`:333-336`); `main` builds
`codes = set(defined.values())` (`:373`) and prints `len(defined)` (`:385`). A dict with six names
and five distinct values therefore reports "6 code(s) defined" over five codes, and two names
sharing a value cannot be told from one.

Measured, three duplicate variants against the real hook:

| matcher's rc tuple | the guard | the matcher's own suite |
|---|---|---|
| `0,2,3,4,5,5` (`UNANSWERABLE` = `UNREADABLE_PLAN`) | rc=1, but the message is **`the hook ACTS on rc 6 and no matcher constant has that value — a dead arm`** | `[FAIL] CANNOT ANSWER and UNREADABLE PLAN are different codes: got 5 want 6` |
| `0,2,3,4,5,0` (`UNANSWERABLE` = `OK`) | rc=1, same false "dead arm at 6" message | same `[FAIL]` |
| **`0,2,3,2,5,6`** (`BAD_RESPONSE` = `CANNOT_RUN`, a code with no arm) | **`rc contract OK`, rc=0**, printing "6 code(s) defined, 4 handled" over 5 distinct codes | same `[FAIL]` |

`verdict` in isolation over the first variant with `handled={0,3,5,6}` returns **0 problems** — the
collision is absorbed exactly as predicted; the live run only went red because the vanished value
happened to be one the hook has an arm for, which then read as dead.

Two things make this Low rather than Medium. The trigger is plausible — `5, 5` for `5, 6` is one
character — but the property IS enforced, cross-file, by the matcher's own suite at
`scripts/recall-llm.py:2261-2262`, whose comment states the reason in the right words: *"a shared
value would re-create the conjunction one code along"*. So the defect cannot ship. What remains is
that the reconciliation guard's output is actively misleading in two of three variants — it blames
a live hook arm for a matcher-side collision — and vacuously green in the third.

**This closes with M3's repair, not a separate one:** requiring `len(set(vals)) == len(vals)` in
`defined_codes` is the same two-line strictness increase, and the real matcher already satisfies it
(`distinct=6` of 6, measured).

---

## Redesign soundness — is the central claim true as implemented?

**The claim: a closed set of six codes, every parsing question delegated to bash. Two-thirds true.**

| rule | reader | verified how | sound? |
|---|---|---|---|
| R1 defined→handled | `ast` over the matcher + bash over the hook | constructed matchers; constructed hooks | ✅ except M1 |
| R2 arm→defined | bash, exhaustive over 0..255 | 9 scattered arms incl. 255 | ✅ (but H2: the result is read through a defaultable arg) |
| R3 no unfulfilled promise | **a hardcoded two-word English vocabulary, in Python** | 4 label variants + control | ❌ **H1**, and only one of the two wrong states — **B1** |

What I confirmed is genuinely delegated:

- **`defined_codes` is `ast`, not a substring reader** — the lead's prime hypothesis, refuted by
  construction rather than by reading. The same tuple text inside a comment (`"# " + RC`) and
  inside a string literal (`"DOC = '''" + RC + "'''"`) both produce `CannotRun`, and a real tuple
  with a docstring decoy above it returns the six correctly. A regex over `= 0, 2, 3, 4, 5, 6`
  would have answered on all three.
- **The staged hook is the SHIPPED bytes.** `sha256` of `.claude/hooks/surface-recall.sh` on disk,
  of `read_text(errors="replace").encode()`, and of the file `_stub_tree` writes into the temp
  tree: all three `4f9de73bed079bb3…`, length 6858. The `errors="replace"` read is lossless here,
  and the staged tree contains exactly two files. The hook resolves `REPO_ROOT` from
  `BASH_SOURCE`, reads no env var and no cwd, and production invokes it as
  `bash .claude/hooks/surface-recall.sh` (`.claude/settings.json:57`) — the same interpreter the
  guard uses.
- **Codex's H1 is FIXED, and fixed in kind rather than in degree.** `dead_arms(probe_max=255)`
  catches an arm at 16 (the reviewer's own case), and the domain really is finite: the suite's
  `:541-543` case observes `exit 300` arriving at the `44)` arm, so an arm above 255 is unreachable
  by construction. The two new manifest entries pin both the bound and its inclusivity.
- **The concurrency is correctly attributed.** `dead_arms` over a hook with arms at
  `[1, 17, 63, 64, 99, 128, 200, 254, 255]` returned exactly `[1, 17, 63, 64, 99, 128, 200, 254,
  255]` in 3.7s. Each probe builds its own `TemporaryDirectory` and `pool.map` preserves input
  order, so the `zip(codes, pool.map(...))` pairing at `:323` cannot cross-attribute. 250 probes
  cost 6.1s wall against the docstring's claimed ~20s serial.
- **`handled_codes` does not search for a sentinel** — it tests the truthiness of the forwarded
  payload (`:271`). Both shim directions behave: an arm that acts but forwards nothing reads as
  NOT handled (documented at `:267-269`, and the safe direction), and a catch-all that forwards
  makes codes read as handled, which L1 covers.
- **`isinstance(v.value, int)` accepting `bool` is NOT a defect, and I checked rather than
  assumed.** `bool` does subclass `int`, so a `True` in the value tuple passes the filter and
  `int(True)` is 1 — but 1 is also the number the shell actually sees: measured,
  `python3 -c 'import sys; sys.exit(True)'` leaves `$?` = **1** and `sys.exit(False)` leaves **0**.
  So the reader's answer equals the matcher's real exit status, and widening the `isinstance` test
  to reject `bool` would make the guard disagree with the shell. The `False` case is caught
  separately: it collides with `OK`, which is L4.
- **The ten manifest entries all bind, and all kill via the case each names.** Anchor uniqueness:
  10/10 occur exactly once in the redesigned file. Applied individually to a sandbox copy over a
  green control (43/43), every one went rc=1 with its named case among the failures. The declared
  count at `check-plan-code.py:1362` is 10 and the manifest holds 10.

**The honest summary of the redesign:** it converted the two rules whose readers had produced every
Blocking and High, and left the third rule's reader alone — and R3 is where #201, the defect that
started this, actually lives. The arming condition's question *can a redesign remove it?* was
answered YES for bash quoting and never asked about label vocabulary. B1 and H1 together say the
answer is YES there too, and that the material for it (`observe` called twice per code) is already
in the file.

---

## Could Not Establish

- **The repo-wide mutation sweep.** Not run, by instruction — `check-plan-code.py --mutate .` was
  in flight in another process. I ran `--self-test` (131/131) and verified this file's ten entries
  individually instead, which is a statement about ten mutations and not about 1,147.
- **Whether B1's WRONG-B has ever been written by anyone.** I can show the state is reachable and
  the guard green over it; I cannot show it has occurred. The hook comment's existence says it was
  considered and rejected by a human, which is the opposite of evidence that a machine would catch
  it.
- **A reachable rc=1 from the live matcher** (L2). Both IO sites I traced catch `OSError` and
  `UnicodeDecodeError`. Someone who can construct one turns L2 from a declaration gap into a live
  defect.
- **Whether `_PROBE`'s literal value matters.** `"PROBE-DETAIL-TEXT"` contains the word "DETAIL";
  I checked that `dangling_detail` probes with `""` and not `_PROBE` (`:283`), so the probe text
  cannot satisfy its own label test — but I did not build a hook that greps its own `$OUT` for a
  substring, which would let a hook recognise the probe and behave differently under observation.
  That is the one class of hook the observer approach is structurally blind to, and it is not
  listed in `:49-54`.
- **The hook as sole caller against live state.** Not run: it consumes the live `.last-said` and
  `.last-surfaced` markers and my brief forbids mutating the repo. Every adjudication above uses
  `observe`'s stub tree, which runs the shipped hook bytes against a stub matcher.

---

## Verified

Every command run, with its output.

| command | output | claim |
|---|---|---|
| `python3 scripts/check-rc-contract.py` | `6 code(s) defined, 4 handled by an arm, 2 declared unhandled` / `rc contract OK …`, 7.3s | rc=0 — **matches** |
| `python3 scripts/check-rc-contract.py --self-test` | `43/43 self-test cases passed`, 19.1s | rc=0 — **matches**, and `:65` declares 43 |
| `python3 scripts/recall-llm.py --self-test` | `201/201 self-test cases passed` | rc=0 — matches |
| `python3 scripts/check-ratchet-contract.py` | `guards discovered (42)` / `ratchet contract OK` | rc=0 — matches |
| `python3 scripts/check-selftest-counts.py` | `49 script(s) declare a count, every one verified by running it` | rc=0 — matches |
| `python3 scripts/check-fixture-variation.py` | `735 parameter(s) examined across 61 file(s); 117 known-unvaried ratcheted, 7 exempt` | rc=0 — matches |
| `python3 scripts/check-docs.py` | `Documentation integrity OK` | rc=0 — matches |
| `python3 scripts/check-plan-code.py --self-test` | `131/131 passed` | rc=0 — matches |
| `defined_codes` over the tuple in a COMMENT | `CannotRun: expected exactly one rc tuple assignment …` | redesign — AST, not substring |
| `defined_codes` over the tuple in a STRING | `CannotRun` | redesign — AST, not substring |
| `defined_codes` over a real tuple + docstring decoy | the six, correctly | redesign |
| `defined_codes(RC + "SEVENTH = 7")` | the six — **7 unseen** | **M1** |
| `defined_codes(RC + "SEVENTH, EIGHTH = 7, 8")` | the six — **both unseen** | **M1** |
| AST census of the matcher's module-level UPPERCASE int constants | the six rc names + `CALL_TIMEOUT` (`:129`) | **M1's fix would false-fire** |
| `sha256` shipped hook / `errors="replace"` round trip / staged in stub tree | `4f9de73bed079bb3…` × 3, len 6858 | redesign — **shipped bytes observed** |
| staged tree contents | `['.claude/hooks/surface-recall.sh', 'scripts/recall-llm.py']` | redesign |
| `dangling_detail` with `Detail: $OUT` at end (control) | `[5]`, reader sees `'unreadable. Detail: \n'` | **H1 control — the probe works** |
| … with `Reason: $OUT` | `[]`, reader sees `'unreadable. Reason: \n'` | **H1** |
| … with `Details: $OUT` | `[]`, reader sees `'unreadable. Details: \n'` | **H1** |
| … with `unreadable: $OUT` | `[]`, reader sees `'unreadable: \n'` | **H1** |
| … with `Detail: $OUT (end)` | `[]`, reader sees `'unreadable. Detail:  (end)\n'` | **H1, second hole** |
| whole `verdict` over WRONG-B (`5) [ -n "$OUT" ] && …`) | `handled=[0,3,5,6] dangling=[] -> 0 problem(s)`; reader at rc5 with no detail = `''` | **B1** |
| same over WRONG-A and the shipped RIGHT form | `dangling=[5] -> 1 problem` / `0 problems` | **B1** — only one of two states caught |
| `do_fire`'s dedupe applies to every `Refusal` subclass | `recall-llm.py:1105-1109`, `raise type(exc)("")` | **B1** — the silence is reachable |
| `main` with `verdict(defined, handled, dangling)` — live | `rc contract OK`, rc=0 | **H2** |
| … same mutation — suite | `43/43 self-test cases passed`, rc=0 | **H2** |
| … same mutation, hook given a real `7)` arm | `rc contract OK`, rc=0 | **H2** |
| CONTROL: unmutated guard, same `7)` arm | `FAILED — 1 disagreement(s) … the hook ACTS on rc 7 …`, rc=1 | **H2's control** |
| matcher missing / hook missing | `… not found — treat this as NOT RUN.`, rc=2 | correct |
| hook `chmod 000` / matcher `chmod 000` | `PermissionError` traceback, **rc=1** | **M2** |
| no `bash` on PATH (python3 still reachable) | `FAILED: no \`bash\` on PATH …`, rc=2 | correct |
| `python3` unreachable to the hook | `FAILED: the hook acted on NONE of the matcher's codes …`, rc=2 | correct — `:380` is load-bearing |
| hook backgrounding `sleep 45`, then exiting | `CannotRun after 30.0s: the hook did not finish within 30s` | **L3** — the ceiling holds |
| hook backgrounding `sleep 8`, then exiting | `observe` returned `''` after **8.0s** | **L3** — bounded by pipe EOF, not by the hook |
| forwarding `*)` catch-all, no arms | `handled=[0,2,3,4,5,6]`, `dead=250 (1..255)`, `verdict=250`, 6.1s | **L1** |
| forwarding `*)` + all real arms | same | **L1** |
| `*) [ -n "$OUT" ] && PAYLOAD="$OUT"` | `handled` includes 2 and 4 | **L1** |
| an arm for 4 that acts and forwards nothing | `4 in handled = False` | documented at `:267-269` |
| `dead_arms` over arms at `[1,17,63,64,99,128,200,254,255]` | returned exactly that list, 3.7s | redesign — **exact attribution** |
| `defined_codes` vs executed source, 6 constructed tuples | 3 bind correctly; 3 misbind (5, 5 and 3 of 6 names) | **M3** |
| whole guard over the A3-shaped matcher + the real hook | `rc contract OK`, rc=0, while the file holds `CANNOT_RUN=3 … UNANSWERABLE='s'` | **M3** |
| strict reader (raw elts counts + distinct values) vs `recall-llm.py:116` | `raw targets=6 names=6 raw values=6 ints=6 distinct=6` → accepts | **M3's fix does not false-fire** |
| `sys.exit(True)` / `sys.exit(False)` through the shell | `$?` = 1 / 0; `int(True)`=1 | **Lead B refuted — the reader agrees with the shell** |
| matcher rc tuple `0,2,3,4,5,5` — guard / matcher suite | rc=1 with a FALSE "dead arm at 6" / `[FAIL] … got 5 want 6` | **L4** |
| matcher rc tuple `0,2,3,4,5,0` — guard / matcher suite | rc=1, same false message / same `[FAIL]` | **L4** |
| matcher rc tuple `0,2,3,2,5,6` — guard / matcher suite | **`rc contract OK`, rc=0**, "6 defined" over 5 / same `[FAIL]` | **L4** |
| `verdict(dup_defined, {0,3,5,6}, [], [])` | `0 problem(s)` — the collision is absorbed | **L4** |
| manifest anchor uniqueness, 10 entries vs the file | 10/10 **BOUND(unique)**, 0 orphans | manifest sound |
| each manifest entry applied individually, suite run | 10/10 rc=1, 10/10 **via the case it names**, over a green 43/43 control | manifest sound |
| manifest count vs `check-plan-code.py:1362` | 10 vs 10 | agree |
| `grep -rn check-rc-contract .github/` | `ci.yml:240` (run) and `:243` (self-test) | the guard has a caller |

⚠ **I modified no tracked file.** Every mutation above was applied to a copy of the three subject
files staged under my own scratchpad directory, whose unmutated baseline reproduced the live verdict
(`rc contract OK`, rc=0) before any edit and again after each restore. No `git` command that writes
was run.

**`python3 scripts/check-plan-code.py --mutate .`** — NOT RUN, by instruction (in flight elsewhere).
Treat this document as saying nothing about the repo-wide sweep.

NOT CONVERGED
