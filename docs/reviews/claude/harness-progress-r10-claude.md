# Adversarial review — `harness-progress-output`, round 10 (Claude half)

**Subject:** `228ea1fc` — *"Round 9: I named the class, then shipped two more of it"*
**Scope:** COVERAGE. Primary subject `scripts/check-fixture-variation.py` and its manifest
`scripts/mutations/check-fixture-variation.json`.

## Verdict: **NOT CONVERGED** — 1 Blocking, 1 High, 1 Medium, 2 Low

But read the **(a)/(b)/(c) judgement** at the end before acting on that verdict. Every finding below
is a **(b) — a variant of a class rounds 1–9 already named.** The instrument is still returning
defects, and it is no longer returning *new kinds* of defect. Those are different facts and the
decision rests on the second one.

---

## Proof of subject

Built from git as the first action, before reading anything:

```
git archive 228ea1fc scripts | tar -x -C <mytree>      # 113 files, matches git ls-tree -r
git rev-parse 228ea1fc:scripts/check-fixture-variation.py  = 56a13bcb9f631d63f5088669bb428e096781f9b9
git hash-object <mytree>/scripts/check-fixture-variation.py = 56a13bcb9f631d63f5088669bb428e096781f9b9   MATCH
git rev-parse 228ea1fc:scripts/mutations/check-fixture-variation.json = 8c859568e608a1209e49915430eba6cfaecd931d  MATCH
git rev-parse 228ea1fc:scripts/check-plan-code.py = dc247919b87df206c27a0505284f8cbfcc508e00  MATCH
```

Every number below comes from that tree, under a redirected `$HOME`, never from the working tree.

## Control, proved green FIRST

```
$ python3 scripts/check-fixture-variation.py --self-test
48/48 passed                                                              rc=0
$ python3 scripts/check-fixture-variation.py
fixture variation OK — 402 parameter(s) examined across 48 file(s);
115 known-unvaried ratcheted, 2 exempt with a written reason              rc=0
```

Every mutation below was applied to a **copy** of that tree and reverted from the pristine blob
between runs.

---

# ⛔ BLOCKING 1 — the pin's DIRECTION is guarded by nothing. Inverting it passes 48/48, passes the manifest, and lets 287 keys be deleted silently

`check-fixture-variation.py:654`:

```python
        pinned = set(EXAMINED_KEYS.get(t.name, ()))
        if t.name in EXAMINED_KEYS:
            for gone_key in sorted(pinned - keys):
```

`EXAMINED_KEYS` is the commit's headline structural claim. Its own comment (`:217-219`) states the
stake precisely:

> *"287 of the 402 keys — 71%, the healthy varied coverage this pin exists to protect — were held by
> nothing but that number."*

**Measured — `pinned - keys` → `keys - pinned` survives the entire suite:**

```
[M1 pinned-keys -> keys-pinned (INVERTS the pin)]   rc=0   48/48 passed
[M2 pinned - keys -> set()      (pin DELETED)]      rc=1   47/48  [FAIL] a file missing a pinned examined key fails
[M3 'if t.name in EXAMINED_KEYS' -> if False]       rc=1   47/48  [FAIL] a file missing a pinned examined key fails
[M8 pinned = ... & keys          (pin VACUOUS)]     rc=1   47/48  [FAIL] a file missing a pinned examined key fails
```

Deletion is killed three ways. **Inversion is killed zero ways.**

⭐ And the sibling line eight lines up — `for lost in sorted(known - keys)` at `:645`, the older
ratchet — **is** direction-anchored: inverting it to `keys - known` fails 4 cases (44/48). Two
adjacent loops, the same operand pair, one protected against transposition and one not. The
difference is not the rule; it is that `:645` accumulated cases over rounds 8 and 9 while `:654`
arrived in this commit with one rc-only case beside it.

**And the harm is live, not theoretical.** `check_file.path` is pinned for
`check-handoff-path.py` and is **not** in `KNOWN_UNVARIED`, so the pin is its only watcher — it is
one of the 287. Privatising that function is r8 B1's own falsifier:

```
# control guard, check_file -> _check_file in scripts/check-handoff-path.py
FAILED — 1 parameter(s) never varied by any case:
  ✗ check-handoff-path.py: `check_file.path` was examined and is NOT any more …        rc=1

# same repo, same edit, with M1 applied to the guard
fixture variation OK — 401 parameter(s) examined across 48 file(s); …                  rc=0
```

Note the headline: **401**, down from 402, and the guard says OK. That is r7 H1's count defect and
r8 B1's "deleting the subject satisfies the ratchet", restored in full through the one line that
replaced them.

**Why no case can see it.** The only case for the pin is `:934`:

```python
            case("a file missing a pinned examined key fails", _rc_fl, 1)
```

It asserts **`rc == 1` and nothing else.** Its fixture writes a two-parameter file named
`check-plan-code.py`, which has 27 pinned keys and produces keys `{g.a, g.b}`. Under the inversion,
`keys - pinned = {g.a, g.b}` → two findings → `rc == 1`, **by the opposite mechanism**, and the case
is satisfied. Every sibling case that touches the pin is likewise rc-only and likewise indifferent:
`:941` (`_rc_nf, 0` — the file is unpinned, both directions give 0), `:1015` (`paid.py` pins exactly
its own key, both directions empty), `:1002` (`lost.py` pins `()`, `keys` is empty, both directions
empty).

**The manifest does not cover it either.** The one entry for this line is a deletion:

```json
{ "name": "the per-file pin stops comparing key sets, …",
  "edits": [["            for gone_key in sorted(pinned - keys):",
             "            for gone_key in []:"]],
  "expect": ["a file missing a pinned examined key fails"] }
```

So `--mutate .` mutates the same line in the same direction the suite already kills.

**Falsifier for the fix.** The case must assert the *message*, not the code — the same repair r9 H1
made one function away, at `:877`:

```python
case("a file missing a pinned examined key fails",
     (_rc_fl, "`check_file.path` was examined and is NOT any more" in _out.getvalue()), (1, True))
```

Under the inversion that string is absent; under the control it is present. A second case should
pin the other arm (a file with an **extra** key beyond its pin must still exit 0), or the direction
is only half-anchored.

---

# H1 — the `*args`/`**kwargs` fix records the right KEYS and its cases never look at the VALUES. Two mutations survive, and the missing case is the one this whole file exists to demand

Round 9's Codex B1 fix, `:504-534`. The keys are produced at `:530` / `:533`; the **values** are
produced at `:516` and `:526`:

```python
            elif vararg:
                extra_pos.append(ast.unparse(arg))          # <- M9
        ...
            elif kwarg:
                extra_kw.append(f"{kw.arg}={ast.unparse(kw.value)}")   # <- M10
```

**Measured — both survive:**

```
[M9  extra_pos.append(...) -> pass]   rc=0   48/48 passed
[M10 extra_kw.append(...)  -> pass]   rc=0   48/48 passed
[M11 'if vararg:'  -> 'if False:']    rc=1   46/48  [FAIL] a *args parameter is examined, not invisible
[M12 'if kwarg:'   -> 'if False:']    rc=1   45/48  [FAIL] a *args parameter is examined, not invisible
```

The key-producing half is killed; the value-producing half is not — and the manifest mirrors the
same blind spot exactly, anchoring `vararg = …`, `kwarg = …` and the `append("(" + …)` line, and
neither `extra_pos.append` nor `extra_kw.append`.

**The harm.** Under M9+M10 a starred parameter can never be seen to vary, so it is reported
unvaried at every call site in the population — a false positive on the axis r9 just added:

```python
def target(*items, **options): ...
def _self_test():
    case("a", target(1, mode="x"), None)
    case("b", target(2, 3, mode="y"), None)      # genuinely varied on BOTH
```
```
control:   keys=['target.items','target.options']  findings=[]
M9+M10:    keys=['target.items','target.options']  findings=['target(items=…)','target(options=…)']
```

**Why no case can see it — and this is the sharp part.** Round 9 added three cases for starred
parameters (`:1078`, `:1084`, `:1097`). In every one of them the starred parameter is passed the
**same source text at every call site**:

- `:1069-1076` — `target(1, mode="x")` at both sites.
- `:1082` — `target(1, 2, mode="x")` at both sites.
- `:1089-1098` — asserts `analyse(...)[1]`, the **key set only**; the findings list is never read.

There is **no case anywhere in the suite in which a `*args` or `**kwargs` parameter is passed
different values at two sites and comes out clean.** That is this file's own docstring rule —
*"FOR EACH PARAMETER OF EACH FUNCTION UNDER TEST, DO AT LEAST TWO CASES PASS DIFFERENT VALUES?"* —
violated by the fixture for the feature that introduced it. The guard cannot report this about
itself, because its subject is a *function's* parameters and `extra_pos` is a local.

**Falsifier for the fix.** Add the positive case (the VARIED block above, expecting `findings == []`)
and two manifest entries anchored on `:516` and `:526`. M9 and M10 then go red via it.

---

# M1 — two of the 48 population members examine ZERO parameters, are pinned at `()`, and are counted in the headline as examined

```
$ files whose analyse() returns an empty key set:
   brief-compose.py, check-docs.py
$ EXAMINED_KEYS entries that are empty tuples:
   'brief-compose.py': (),   'check-docs.py': (),
```

The guard's field of view is **one function deep**: `analyse` reads call sites inside `suite` only
(`:466`, `:486`). Both files route their suite through a module-level private helper, so nothing is
examined:

- `brief-compose.py:969 def self_test()` → `:983 _self_test_body(cases)` → the whole suite lives in
  `brief-compose.py:999 def _self_test_body(...)`, outside the field of view. 18 module-level
  public functions besides `main`/`self_test`/`case`, **0 parameters examined.**
- `check-docs.py:542 def self_test()` drives everything through `_shape` (`:533`) and `_markers`
  (`:537`). Also 18, **0 parameters examined.**

Neither is malice; it is ordinary suite structure. The consequences:

1. **The `()` pin is a pin over nothing.** `pinned - keys` is empty for all time, so no coverage
   regression in either file is detectable — including the regression of deleting their suites
   outright.
2. **The headline overstates.** `fixture variation OK — 402 parameter(s) examined across 48 file(s)`
   reports 48 files examined when 46 were. This is the §21 shape — *a zero over nothing is not a
   finding* — applied at the population level (`:612`) and at the deadness level (`:581`) and
   **not per file**.
3. **Measured size of the blind spot.** Extending the field of view to module-level private helpers
   transitively reachable from the suite (a mechanical change, no new judgement):

```
examined today: 402   with the suite's private helpers followed: 431
   brief-compose.py        0 -> 23
   check-docs.py           0 -> 5
   check-plan-file-tags.py 3 -> 4
```

29 keys, 6.7% of the corpus, outside the instrument — and `check-docs.py` is the documentation gate
`docs/dev-process.md` lists as mechanically enforced.

**Falsifier for the fix.** Either follow module-level private helpers reachable from the suite, or
refuse an empty per-file key set as CANNOT-EXAMINE the way `:581` refuses an empty population. A
pin of `()` must not be spellable without a written reason.

---

# L1 — the stated residual at `:222-227` is not complete: a signature can differ while the key set is byte-identical

```
⚠ RESIDUAL … What is closed is every case where the signature differs, which
  includes plain privatisation, renaming, and parameter changes.
```

The first two halves are true and I confirmed them (privatising `check_file` fires the pin; see
Blocking 1). **"every case where the signature differs" is false.** Measured:

```
def audit(cutoff, docs)      keys=['audit.cutoff','audit.docs']  unvaried=['audit(docs=…)']
def audit(docs, cutoff)      keys=['audit.cutoff','audit.docs']  unvaried=['audit(cutoff=…)']   <- reordered
def audit(cutoff, /, docs)   keys=['audit.cutoff','audit.docs']  unvaried=['audit(docs=…)']
```

A parameter **reorder** is a signature change that leaves the key set identical *and* silently
re-attributes every recorded value to the neighbouring parameter — the mis-attribution class r8 L1
named for `/`, reached from the other side. Adding a `/`, changing defaults and changing annotations
are likewise invisible to the pin.

The accurate claim is narrower and worth writing down as such: **what is closed is every case where
the set of parameter NAMES differs.** This matters because it is the second consecutive round in
which a stated-limit comment claims more than the code delivers, and this file's stated limits are
the only thing standing between "passes" and "safe" (`:45-50`).

---

# L2 — a `*` or `**` at the CALL SITE mis-attributes or erases keys. LATENT: 0 instances in today's corpus

`:512-517` matches positional arguments to parameters **by index**, and an `ast.Starred` node
occupies exactly one index:

```
audit(*P1) / audit(*P2)  ->  keys=['audit.cutoff']            findings=[]     # audit.docs GONE
audit(**K1) / audit(**K2) -> keys=[]                          findings=[]     # function INVISIBLE
```

The second is precisely the shape r9's Codex B1 named for the signature side — *"`def target(*items)`
examined ZERO parameters and the gate passed"* — on the call-site half of the same grammar. This is
the third time this file has been bitten by "the other half of the grammar" (r7 L1 kwonly, r8 L1
positional-only, now the call site).

**Measured over the real corpus: zero call sites inside any of the 48 suites use `*` or `**`
unpacking against a subject function.** So it is latent, exactly as r7 L1 was when it was found and
fixed *"before the population widened into one"* (`:496-497`). I report it at Low on that precedent,
not higher.

---

## Attacks on `EXAMINED_KEYS` that HELD

Run as a battery over `analyse`; all preserve keys *and* findings, i.e. the pin is not fooled:

| Attack | Result |
|---|---|
| decorator applied to the subject | keys and findings unchanged — correct |
| `if TYPE_CHECKING:` decoy with a **different** signature, defined first in source | correct def wins (`ast.walk` is breadth-first; depth 1 beats depth 2) |
| function defined inside a `for` loop at module level | examined normally |
| `functools.wraps` wrapper replacing the real function | the wrapper's signature is what callers use; keys correct |
| subject moved into a class as a method | keys vanish → **pin fires** |
| subject replaced by a re-export alias `audit = _impl` | keys vanish → **pin fires** |
| subject's suite body moved into a module-level private helper | keys vanish → **pin fires** (but see M1 for the two files already at zero) |
| parameter converted to keyword-only (`def f(a, *, b)`) | key vanishes → **pin fires** |

Also verified sound and killed by the suite: the three-way paid/lost/exempt partition
(`known - seen_known - exempted` → r8 B1 restored, killed; dropping `- exempted` → r9 M1 restored,
killed; `known - keys` → `keys - known`, killed), the exemption's file scope, and the
`--mutate .` manifest entry for it.

One note on the file-scope mutation: `f"{path}:{fn}.{param}"` → `f"{fn}.{param}"` kills by raising
`IndexError` out of `_self_test`, not by printing `[FAIL] <case name>`. The file itself warns about
exactly this at `:788-790` — *"a case that dies from its defect attributes nothing; a case that
reports it names the guard."* The manifest's `expect` names a case that never runs. Not filed as a
finding because the mutation IS killed; recorded because the attribution is by crash.

---

## ⭐ THE ROUND'S DELIVERABLE — are these (a), (b) or (c)?

**(b) — variants only. Every finding above is an instance of a class already named in rounds 1–9.
I found no new structural class, and I looked for one deliberately.**

| Finding | Class, and where it was already named |
|---|---|
| **B1** pin direction unguarded | *"an assertion too weak to isolate its subject"* — **r9 H1**, verbatim, one function away. r9 fixed its instance at `:877` and left the identical shape at `:934` |
| **H1** starred values never compared | *"every case passes the SAME value for the parameter that decides it"* — **r6 B1**, this file's own founding defect, reproduced inside r9's fix |
| **M1** two files examine zero parameters | *"a zero over nothing is not a pass"* (§21 / r7 L2 / r8 L2) at a new granularity — per-file rather than per-population; and *"the population is narrower than the rule can already read"* — **r7 H3** |
| **L1** residual claim overstates | *"a comment states as fact something the code does not do"* — **r5 M3, r8 L3, r9 L3** |
| **L2** call-site unpacking | *"the other half of the grammar"* — **r7 L1** (kwonly), **r8 L1** (positional-only), **r9 Codex B1** (signature-side stars) |

**So: is it converging, or is it an instrument that always yields one more finding?**

The evidence says **neither, exactly — and the distinction is the useful answer.**

*Against "it always yields one more":* the severity curve is not the only thing that fell, the
**kind** fell. Rounds 8 and 9 found structural faults — a proxy standing in for identity, defeated by
substitution and by name reuse. **Round 10 found no proxy.** I ran eight named attacks at
`EXAMINED_KEYS` (decorators, `if TYPE_CHECKING`, loop definitions, `functools.wraps`, class methods,
re-exports, suite relocation, keyword-only conversion) and **the pin held every one**. Its residual
— name identity — is stated in the code, and I tested the statement: it is *narrower* than written
(L1) but the mechanism is not defeatable by the moves r8 and r9 used. The structural claim is sound.

*Against "it has converged":* what round 10 found is not noise. B1 is a one-token inversion that
restores the exact defect of r7 H1 and r8 B1 over 287 keys, green on 48/48 and green on the
manifest. That is not a Low padded to justify a round.

**The actual pattern, stated as a cause rather than a count:** rounds 6–10 each found the previous
round's *fix* defective, and in every case the defect is in the **case or the manifest entry, not in
the rule.** The rules have converged; the *evidence written alongside each fix* has not, and it fails
the same way each time — the case asserts a return code where it should assert a message, and the
manifest anchors the lines the fix's narrative is about rather than the lines the fix added. Both of
my top two findings are that one cause. That cause is mechanical and does not need another
adversarial round to find; it needs a rule.

**Recommendation.** Fix B1, H1 and M1, and then **stop reviewing this file and write the rule
instead**: *a case that drives `main` asserts a substring of its output, never `rc` alone.* Six cases
in this suite assert `rc` alone (`:882`, `:895`, `:934`, `:941`, `:949`, `:1148`); r9 repaired one of
them by hand and B1 is the next one in the list. That is a grep, not a review round. A round 11 aimed
at *finding* more of this class is not justified by what round 10 returned; a round 11 that reviews
the **rule** against the whole `scripts/` corpus would be.

---

## What I did not measure

- ~~I did not re-run `--mutate .`~~ — **I did, and it reproduces.** Over a staged `HARNESS_TREE`
  (scripts copied from `228ea1fc`, `docs`/`supabase`/`node_modules/typescript`/`.claude/hooks`
  symlinked, redirected `$HOME`):

  ```
  OK — delivered scripts mutated: 39 file(s), 502 mutation(s), 502 killed,
       502 attributed to the case each names, 0 survivor(s)          EXIT=0
  ```

  The claim in the commit is **confirmed**. ⭐ And that is the finding, not a reassurance: the
  harness reports `0 survivors` over 502 mutations **while M1, M9 and M10 survive**, because
  `--mutate .` applies the manifest and the manifest is where those three are missing. `0 survivors`
  is a statement about the manifest's population, never about the file's. That is §21 — *a check has
  a RULE and a POPULATION, and they fail separately* — applied to the mutation harness itself, and
  it is why B1 and H1 are reachable by hand and not by the gate.
- **I did not run the other five gates** (`check-selftest-counts.py`, `check-ratchet-contract.py`,
  etc.). The 48-case count and the docstring's declared 48 agree, which is the part B1 and H1 depend
  on.
- **I did not measure the semantic quality of the 402 pinned keys.** The guard compares *source
  text*; two call sites passing `x` and `y` satisfy it even if both evaluate to the same thing. The
  file says so at `:45-50` and I take it at its word — r5 B1 would still not be caught.
- **I did not attack `KNOWN_UNVARIED`'s growth direction.** Nothing in this file or its manifest
  prevents a regressed parameter from being silenced by adding one line to it, and unlike `EXEMPT`
  it carries no written reason and gets no deadness check. I judged that to be the ordinary meaning
  of a ratchet rather than a defect, and did not file it — but it is the asymmetry a future round
  should decide on deliberately rather than rediscover.
- **I did not verify the two `EXEMPT` reasons are true**, only that they are load-bearing (the
  deadness check does that, and it is killed by three manifest entries).
