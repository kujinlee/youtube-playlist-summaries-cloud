# Round 7 — Claude adversarial half · `shard-mutation-sweep` (PR #366) at `6416e212`

Subject: `git diff d95908c0..6416e212` — the whitespace fold (`SHARD_SPEC.fullmatch(spec)`, no
`.strip()`), plus its case, its mutation entry, the three count bumps and the dashboard entry.
Wider view read: `git diff 68f6d7ea..6416e212`.

Mandate: **REFUTE**.

**Headline — two findings, and the second is the one that matters.**

The whitespace fold itself is correct and I could not break it: 88 constructed inputs, 87 refused,
one accepted, and the one accepted is `1/8`. `$` does nothing surprising inside `fullmatch`.

But the brief's framing — *"one small rule has now been fixed five times, assume it is still
wrong"* — turned out to be aimed one notch too narrow. **The rule is fine; its two seams are not.**

1. **H1 — `--self-test --shard0 <anything>` exits 0 and prints `169/169 passed`.** This is round
   1's Codex Medium, verbatim, reopened by round 6's own M1 fold. `shard_mode_refusal` is called as
   `shard_mode_refusal(a.shard, a.mutate)` at `:4539` — the new flag was never passed to it. The
   control, `--self-test --shard 0/8`, correctly exits 2. A shard-shaped invocation reporting
   success over a subject no shard touched is the single failure this script exists to prevent, and
   it is reachable by one word on the documented CLI.
2. **L1 — the fifth way in does exist, and it is the LENGTH of the digit run, not its alphabet.**
   `SHARD_SPEC.fullmatch("1"*4301 + "/8")` matches, then `int()` raises
   `ValueError: Exceeds the limit (4300 digits)`. The comment introduced one fold ago at `:1551`
   says, verbatim: *"An explicit byte class makes both impossible: every string that matches is one
   `int()` accepts."* **That sentence is false**, and it is false about the exact symptom the same
   paragraph names two lines earlier (*"`int()` RAISES — a traceback, which this function's own
   docstring forbids"*).

Both are in the **deliverable**. Verdict: **NOT CONVERGED**, and this is **not** a clean round — the
quiet counter stays at zero, as it did after rounds 5 and 6.

---

## 1. Verification

`HEAD` = `6416e21252236380072ea137cd0bbe2a0656910d`, confirmed before and after.

**No tracked file was modified.** `git status --short` reads `M docs/explainers/questions.md` only
(the deliberately-dirty file the brief told me to ignore), at the start and at the end. Every probe
ran out of the session scratchpad; the one YAML extraction wrote to the scratchpad, never the repo.
I applied **no** mutations to any file on disk.

### 1.1 Commands run, with real output

| # | command | rc | result |
|---|---|---|---|
| 1 | `check-plan-code.py --self-test` | 0 | `169/169 passed` |
| 2 | `check-merge-ready.py --pr 366` | 0 | `READY` — relayed verbatim in §Q6 |
| 3 | `check-docs.py` | 0 | `Documentation integrity OK` |
| 4 | `check-selftest-counts.py` | 0 | `50 script(s) declare a count, every one verified by running it` |
| 5 | `check-python-pin.py` | 0 | pass |
| 6 | `check-features.py` | 0 | `26 nodes (24 built, 2 declared absent)` |
| 7 | `check-anchors.py` | 0 | `13 registered, all claimed` |
| 8 | `check-vocabulary-collisions.py` | 0 | `✅ no unjustified duplicate mechanism` |
| 9 | `check-ratchet-contract.py` | 0 | `ratchet contract OK` |
| 10 | `check-backlog-closure.py` | 0 | `WARN — 2 row(s) may be stale, 0 orphaned` (#117, #159 — **both pre-existing, neither this branch's**) |
| 11 | `check-review-rounds.py` | 0 | pass |
| 12 | `check-test-counts.py` | 0 | `2,892 unit / 278 suites` |
| 13 | `check-guard-coverage.py` | 0 | pass |
| 14 | `check-dashboard-entry.py` | 0 | `ok — an entry block was added` |
| 15 | `--mutate . --shard0 4/8` | — | shard 5 of 8 — verbatim verdict in §Q5. ⚠ It ran under `nohup`, so I read the **verdict line**, not an exit code; the line's `OK —` prefix is the success path and `0 survivor(s)` is the assertion |

### 1.2 Attack 1 — the accept set, 88 constructed inputs

I built the corpus from code points rather than typing escapes: 18 invisible or control characters
(`CR FF VT NUL BEL ZWSP ZWNJ RLO RLE LRM NBSP LS PS NEL BOM U+0301 U+3000 U+180E`) in **three**
positions each — leading, trailing and infix — plus 34 structural and numeric-notation forms.

```
ATTACK 1 — accept set (88 inputs)
  canonical          '1/8'                      -> ACCEPT (1, 8)

ACCEPTED (should be only the canonical form):
   '1/8' (canonical) -> (1, 8)
RAISED: []
TOTAL refused: 87 of 88
```

**`$` inside `fullmatch` does not misbehave**, which the brief flagged as worth checking and which
is worth writing down because the reasoning is not obvious:

```
  '1/8'          match=True  fullmatch=True
  '1/8\n'        match=True  fullmatch=False
  '1/8\n\n'      match=False fullmatch=False
  pattern: ^(0|[1-9][0-9]*)/(0|[1-9][0-9]*)$   flags: 32
```

`$` *does* still assert at position 3 of `"1/8\n"` — it is zero-width and matches before a final
newline exactly as before. What refuses the string is `fullmatch`'s own requirement that the match
*end* at `len(s)`: the assertion succeeds and the match is rejected anyway. So the `^`/`$` anchors
are now redundant rather than load-bearing, and leaving them in is harmless.

**Non-`str` input raises `TypeError`** (`None`, `int`, `bytes`, `list`, `float` — all five). Not a
finding: argparse yields `str` or `None`, and both call sites are guarded by `is not None`, so no
caller can supply one. Recorded because the brief asked.

### 1.3 Attack 2 — does `--shard0` *select* the slice it claims? Run, on the real manifest

Over all **1,204** real manifest entries, at N = 1, 2, 3, 7, 8, 16, for **every** valid `i`:
`shard_slice` under `--shard0 i/N` is identical to `shard_slice` under `--shard (i+1)/N`, both for
the id list and for the real mutation objects.

```
N = 8
  --shard0 0/8 == --shard 1/8  -> 151 entries
  --shard0 1/8 == --shard 2/8  -> 151 entries
  --shard0 2/8 == --shard 3/8  -> 151 entries
  --shard0 3/8 == --shard 4/8  -> 151 entries
  --shard0 4/8 == --shard 5/8  -> 150 entries
  --shard0 5/8 == --shard 6/8  -> 150 entries
  --shard0 6/8 == --shard 7/8  -> 150 entries
  --shard0 7/8 == --shard 8/8  -> 150 entries
  union: 1204 / 1204   duplicates: 0   missing: none
```

Union-complete and pairwise-disjoint at **every** N tested (`PARTITION OK`). Boundary:
`--shard0 8/8`, `-1/8` and `0/0` all refuse with the right sentence; the empty-shard refusal fires
at `N = count+1` and not at `N = count`.

### 1.4 Attack 3 — the CI seam, extracted by a YAML parser and run

⚠ **`pyyaml` is not installed** on this machine and PEP 668 blocks `pip install`. Rather than
hand-roll an extractor — which would be a second implementation of a parser, the thing backlog #227
is open about — I extracted the block with **ruby's psych**, a real YAML implementation:
`YAML.load_file(".github/workflows/ci.yml")`, then wrote `step["run"]` byte-exact to a file.
**No `textwrap.dedent`, no re-indentation, no retyping.** 1,218 bytes.

The leading-space profile of the delivered block is 0 spaces on lines 1–15 and 2 spaces on line 16
(the `\`-continuation), and **the block contains no inline Python** — it is one `python3 … \` call.
So the `IndentationError` class the brief warned about is not reachable here, and I am saying that
because I checked the shape rather than because I assume it.

Run under `bash` with 18 hostile environments:

| I | N | outcome |
|---|---|---|
| `0` | `8` | sweep started (timed out at 30 s mid-control — the correct behaviour) |
| `''` | `8` | **rc=2** `--shard0 '/8' is not of the form I/N` |
| `0` | `''` | **rc=2** `--shard0 '0/'` |
| `''` | `''` | **rc=2** `--shard0 '/'` |
| `abc` | `8` | **rc=2** |
| `18446744073709551616` | `8` | **rc=2** `names a shard that does not exist` (the r5 overflow, no longer wrapping) |
| `٠` | `8` | **rc=2** (the r6 L1 Unicode route) |
| `0\n` | `8` | **rc=2** (the r6 Codex route) |
| ` 0` | `8` | **rc=2** |
| `0` | `8\n` | **rc=2** |
| `00` | `8` | **rc=2** |
| `8` | `8` | **rc=2** out of range |
| `-1` | `8` | **rc=2** |
| `0;echo PWNED` | `8` | **rc=2** — see note below |
| `0 1` | `8` | **rc=2** |
| `0` | `8 -x` | **rc=2** |
| `0` | `0` | **rc=2** |
| **`1`×4301** | `8` | **rc=1 — `ValueError` traceback.** §F-L1 |

A non-zero rc makes the **step** fail: `bash` exits with the last command's status and that command
is the `python3` call. Verified by observation — the harness read rc=2 back from `bash`, not from
`python3` directly.

> ⚠ **One false alarm in my own probe, stated rather than buried.** My detector flagged `PWNED` for
> the `0;echo PWNED` case. It is **not** an injection: the string is inside double quotes, bash
> passes it as one argv word, and the token appears only because the refusal sentence *echoes the
> spec back* — `--shard0 '0;echo PWNED/8' is not of the form I/N`. The quoting is correct.

### 1.5 Attack 5 — the four declared counts, re-derived independently

Every one agrees with the tree. I derived each from a different source than the one that declares
it, because a count that agrees with itself is this repo's recurring defect.

| declared | where | my independent derivation | agrees? |
|---|---|---|---|
| self-test **169** | docstring `:6` | `ast` walk of `_self_test`: **164** static `case(` sites + **1** site inside a 5-iteration `for` at `:2455` = **169** | ✅ |
| manifest **99** | `EXPECTED_MUTATIONS` | `json.load` of `check-plan-code.json`, count of entries with `file == scripts/check-plan-code.py`: **99** | ✅ |
| declared sum **1204** | `sum(EXPECTED_MUTATIONS.values())` | all 57 manifest JSONs, total entries: **1204**; and `load_manifests(".")`: **1204**, 0 problems | ✅ |
| anchors **1,212** | dashboard entry | sum of `len(e["edits"])` over all manifests: **1212** | ✅ |

**Anchor resolution, derived rather than trusted:** every one of the 1,212 find-strings was counted
against its delivered target file. **0 unresolved** (zero occurrences) and **0 ambiguous** (more
than one occurrence). Per-file `EXPECTED_MUTATIONS` vs actual: **no disagreements** across all 57.

Duplicate refusals: **0** duplicate names and **0** duplicate anchor-tuples within any manifest.
⚠ I initially measured duplicates *across* manifests and across *individual* edits and found some —
both are out of scope by design, and correctly so: `seen_names`/`seen_anchors` reset per manifest
(and `e["file"]` must equal the manifest's target, so a cross-manifest name collision is two
different scripts), and the anchor rule keys on the **tuple**, which `:1504-1524` already documents
honestly as weaker than its message. I could not find a case where the code is weaker than that
comment.

### 1.6 What I could NOT run — **NOT MEASURED**

- **`pyyaml` is unavailable** (PEP 668). Worked around with ruby psych, above; the extraction itself
  **is** measured. What is not measured is whether GitHub Actions' own YAML dialect delivers the
  same bytes psych does — no runner was available to me.
- **No CI run at `6416e212` under my own eyes.** `check-merge-ready` reports 12 green checks for the
  PR head (§Q6); I did not re-trigger or watch a run.
- **`--mutate .` unsharded** — forbidden by the brief (~29 min). I ran one shard.
- **Shards 1, 2, 3, 4** — already measured by the coordinator; re-running them would reconfirm, not
  refute, so I ran **shard 5** instead (§1.5 row 15, result in §Q5 table).

---

## 2. Findings

Findings and fixes are stated **separately**. Every fix below is **UNVERIFIED** — I applied none of
them, to any file.

---

### H1 (High · deliverable · **caused by a previous fold — round 6's M1**)

## `--self-test --shard0 <anything>` exits **0** and prints `169/169 passed`

This is round 1's Codex Medium, reopened. That finding's own repair, `shard_mode_refusal`, carries
this docstring:

> *"The defect this closes was an ORDER defect: `--self-test` returned BEFORE the shard was
> validated, so `--self-test --shard garbage` exited 0 and printed a clean suite result — a
> shard-shaped invocation reporting success over a subject no shard ever touched."*

Round 6's M1 added `--shard0` and did not pass it to that predicate.
`scripts/check-plan-code.py:4539`:

```python
    _mode_why = shard_mode_refusal(a.shard, a.mutate)
```

**Exhibiting inputs, measured, with the control that proves the asymmetry is real:**

```
  --self-test --shard0 garbage       rc=0 | 169/169 passed
  --self-test --shard0 0/8           rc=0 | 169/169 passed
  --self-test --shard0 99/8          rc=0 | 169/169 passed
  --self-test --shard0 ''            rc=0 | 169/169 passed
  --self-test --shard 0/8            rc=2 | CANNOT RUN — --shard 0/8 only means something with --mutate ROOT
```

**Four of four `--shard0` forms report success. The `--shard` control refuses.** Note the second
row especially: `0/8` is a *perfectly valid* shard spec, so the invocation reads to its author like
"self-test shard 1 of 8 — passed", and no such thing was done.

**Why no gate saw it, which is the part worth more than the defect.** Three self-test cases cover
`shard_mode_refusal` (`:3869-3876`) and **all three call the predicate directly** with positional
arguments — `shard_mode_refusal("2/8", None)`, `("garbage", None)`, `("0/0", None)`, `("2/8", ".")`,
`(None, None)`, `(None, ".")`. None goes through `main`, and none mentions `--shard0`. The suite
therefore proves the predicate is *right* and never that the **call site** passes it everything it
must. The one mutation entry at the call site is named *"main stops obeying the shard mode refusal,
so `--self-test --shard` rides through"* — it severs the call and is killed, which proves `--shard`
is wired and says nothing about `--shard0`.

That is this repository's recorded lesson *unit coverage does not compose — mutate the CALL SITE*,
and its sibling *a shim fails both ways*: the repair of round 1's finding keyed on the one flag
name that existed when it was written.

**Blast radius, stated honestly:** CI is **not** exposed. `ci.yml:495` runs
`check-plan-code.py --self-test` bare, with no shard flag. The exposure is a human at the documented
CLI, which is the same reachability class as round 1's original and as rounds 5 L2 and 6 L1 — all of
which this branch judged worth fixing.

**Severity, and why I am going above round 1's Medium — disagree with the number, not a hidden
judgement.** Round 1's Codex half rated the `--shard` instance **Medium**. I rate this **High** for
three reasons the original did not have: (a) the outcome is **rc=0**, a false green, and this script
exists to make rc=0-over-nothing impossible; (b) it is a **regression** — a closed finding reopened,
not a new hole; (c) the fold that reopened it is the fold under review, and its stated purpose was
to move this rule into code that a suite can see.

**Fix — UNVERIFIED.** Pass both flags, and derive rather than enumerate so a third base cannot
repeat this:

```python
    _mode_why = shard_mode_refusal(a.shard if a.shard is not None else a.shard0, a.mutate)
```

⚠ **That one-liner is the instance fix and I do not recommend it alone** — it is exactly the shape
that produced this finding. The class fix is a case that goes through `main`, which the predicate's
own docstring says it avoided (`main(["--self-test", …])` would re-enter the running suite). The
escape it already uses elsewhere in this file is `_main_rc` in a subprocess (`:2455`'s loop does
this for the retired flags). A case built that way would have caught this; a direct-call case
structurally could not. Any repair should also carry a mutation entry that severs `a.shard0`
specifically, or the next flag added repeats this a third time.

---

### L1 (Low · deliverable · **the claim is caused by the previous fold; the defect predates it**)

## The fifth way in is the digit run's LENGTH, and `:1551` says it is impossible

`SHARD_SPEC` matches an unbounded `[0-9]*`. Python caps `int()`↔`str` conversion at
`sys.get_int_max_str_digits()` = **4300** (3.11+, and CI pins **3.12**, so this is not a local-only
artifact). So the regex accepts strings `int()` refuses.

```
  sys.get_int_max_str_digits() = 4300
  I= 4299 digits  regex=True  -> returned shard=None why='CANNOT RUN — --shard 111111111'
  I= 4300 digits  regex=True  -> returned shard=None why='CANNOT RUN — --shard 111111111'
  I= 4301 digits  regex=True  -> *** RAISED ValueError: Exceeds the limit (4300 digits) ...
  I=10000 digits  regex=True  -> *** RAISED ValueError: Exceeds the limit (4300 digits) ...
```

Both operands, both flags, and from the CLI:

```
$ python3 scripts/check-plan-code.py --mutate . --shard "$(python3 -c "print('1'*4301)")/8"
  File ".../scripts/check-plan-code.py", line 1587, in parse_shard
    index, total = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
ValueError: Exceeds the limit (4300 digits) for integer string conversion
rc=1
```

`--shard0` is identical. `1/<4301 digits>` is identical.

**What makes this a finding rather than a curiosity is the comment, not the traceback.** `:1546-1555`
reads:

> *"⛔ `[0-9]`, NOT `\d` — ROUND 6 L2. … 128 further code points (`²`, `፩`) pass `\d`/`isdigit()`
> while `int()` RAISES — **a traceback, which this function's own docstring forbids**. … An explicit
> byte class makes **both impossible**: **every string that matches is one `int()` accepts**."*

The final sentence is false. The byte class closed the *alphabet* route and left the *length* route
open, and the paragraph asserts the whole class is shut. `parse_shard`'s docstring then says
*"⛔ A SENTENCE AND A CANNOT RUN, NEVER A TRACEBACK"*. I confirmed the 128 figure independently
(`128` code points are `isdigit()` and not `isdecimal()`, and `int()` raises on all 128), so the
paragraph is right about everything except its own conclusion.

**Consequence is bounded and I will not inflate it.** rc=**1**, not 0 — a loud failure, no false
green. It is **unreachable from CI** (`strategy.job-index` is a small GitHub integer). What it costs
is the refusal *kind*: rc=1 is this script's "a mutation survived" code, so the one malformed-spec
path that does not say `CANNOT RUN` reports the wrong failure — and `main`'s own comment
(`:4611-4616`) gives exactly that reasoning for why the empty-shard refusal was hoisted: *"rc 1 from
an empty shard reads as 'a mutation survived' when the truth is that nothing ran."*

**Provenance, for Q5 — I checked rather than assumed.** `int(m.group(1))` is present at
`68f6d7ea^`, before the byte-class fold, under `SHARD_SPEC = r"^(\d+)/(\d+)$"`. So:

- the **defect** dates to `parse_shard`'s birth and is **not** caused by any previous fold;
- the **false claim that it cannot happen** was written by `d95908c0` — one fold ago, as the repair
  for round 6's L2.

**Fix — UNVERIFIED.** Bound the digit run in the pattern, which also removes the need to trust
`int()`'s limit:

```python
SHARD_SPEC = re.compile(r"^(0|[1-9][0-9]{0,8})/(0|[1-9][0-9]{0,8})$")
```

9 digits caps N at 999,999,999 — far beyond any matrix, and `shard_refusal` already refuses anything
exceeding the manifest. ⚠ **Two cautions.** (1) Do not "fix" this by raising
`sys.set_int_max_str_digits()`: that moves the boundary and keeps the hole, and the honest statement
is that the *regex* should bound the value, which is `:1546`'s own argument. (2) If the fix lands,
the sentence at `:1551-1552` must change too — a bound of 9 digits makes "every string that matches
is one `int()` accepts" true for the first time, and leaving the sentence as-is would mean it was
correct only by accident.

---

### L2 (Low · instrument · not caused by any fold)

## Attack 4: nine other sites still spell "a decimal integer" their own way, and one is in this same file

The brief asked whether the class is still live elsewhere. **It is**, and the sharpest instance is
440 lines below `SHARD_SPEC` in the same deliverable file.

`grep` over `scripts/ .github/ .claude/hooks/` for `isdigit|isnumeric|isdecimal` and bare `\d`:

| site | guard | measured |
|---|---|---|
| `check-gate-falsifiability.py:327-330` | `--current-release=` from **argv** | **RAISES** (below) |
| `peer-sites.py:551,560` | `site` positional, `FILE:LINE` from **argv** | **RAISES** (below) |
| `check-plan-progress.py:276` | `paused_unticked` from a hand-edited sentinel | **RAISES** (below) |
| `check-plan-code.py:2025` | `count_drift`'s own `r"(\d+) cases"` | fails safe on Unicode; **raises** at 4301 digits |
| `check-plan-progress.py:356` | state file | same shape, not separately exercised |
| `check-paid-caller-arrival.py:427` | `psql` count output | shape only — not attacker-reachable |
| `check-gate-falsifiability.py:220` | `fly releases --json` | shape only |
| `gen-backlog-page.py:654,664` | backlog row text | shape only |
| `verify-exclusion-reasons.py:363` | in-file labels | shape only |
| `check-merge-ready.py:406` | `gh` output | shape only |

**Three measured, each with its adjacent control** — the control is what makes these findings rather
than observations, because it shows the author *intended* a refusal sentence and one input slips past
it:

```
$ python3 scripts/check-gate-falsifiability.py --staleness --current-release=²
  File ".../check-gate-falsifiability.py", line 330, in main
    current_release = int(raw)
ValueError: invalid literal for int() with base 10: '²'                          rc=1
$ python3 scripts/check-gate-falsifiability.py --staleness --current-release=abc
FAILED: --current-release must be a version number like v6, got 'abc'.           rc=1
```

```
$ python3 scripts/peer-sites.py "scripts/peer-sites.py:²"
  File ".../peer-sites.py", line 560, in main
    for line in report(src, {int(ln)}) or [...]
ValueError: invalid literal for int() with base 10: '²'                          rc=1
$ python3 scripts/peer-sites.py "scripts/peer-sites.py:abc"
CANNOT RUN — expected FILE:LINE, got 'scripts/peer-sites.py:abc'.                rc=2
```

`peer-sites.py` is the worst of the three: the control earns **rc=2 (CANNOT RUN)** and `²` earns
**rc=1**, so the one bad input gets the one exit code that means something else. The 4301-digit route
raises there too.

`check-plan-progress.decide()` with a sentinel carrying `paused_unticked: ²` raises
`ValueError`. Its own comment two lines above says *"⚠ THREE STATES, AND THE THIRD IS WHY THIS IS
NOT JUST AN ANTI-NAG… 'cannot tell' must not read as 'nothing happened'"* — a traceback is a fourth
state nobody declared, in a guard that runs from a Stop hook.

**The structural observation, which is what I would actually file.** The fold's own comment says the
rule is now spelled in **one** place: *"the same rule is spelled in `.github/workflows/ci.yml`, and
spelling it a second way is what produced three disagreeing definitions … so the workflow no longer
spells it at all."* That consolidated **two** of the spellings. There is still **no shared canonical
definition** in this repo — `SHARD_SPEC` is a private module-level constant — and `count_drift`,
440 lines below it in the same file, uses a bare `\d`. `check-vocabulary-collisions.py` passes, so
nothing sees this as a duplicate mechanism.

**Fix — UNVERIFIED, and deliberately not a code change.** This is a backlog row, not a fold:
promote a canonical `DECIMAL = re.compile(r"(0|[1-9][0-9]{0,8})")` (or a `parse_decimal()` returning
`(value, why)` in `parse_shard`'s shape) to a shared module, and convert the three argv/file-reachable
sites. ⛔ **Do not take this inside PR #366** — its subject is the sharding, and nine call sites
across eight guards is a slice. The two in-file ones (`SHARD_SPEC` + `count_drift`) are arguably in
scope; the other eight are not.

---

### L3 (Low · merge artifact · not caused by any fold)

## The PR #366 body's `NO-REVIEW:` waiver states a scope the diff contradicts, and its counts are 4–9 behind the tree

The brief's Q6 asks whether a reader of the backlog, roadmap or dashboard would be misled.
**Those three are clean** (§Q6). The **PR body** is not, and it is what the merger reads.

The body's only `NO-REVIEW:` waiver says:

> *"NO-REVIEW: the commits after round 2's fold change one `expect` string in
> `scripts/mutations/check-plan-code.json` and nothing else — **no delivered code, no test, no
> workflow**."*

Measured, `git diff --stat b1d059e9..HEAD` — the waiver's own stated baseline:

```
 .github/workflows/ci.yml            |  25 +-      <- workflow
 scripts/check-plan-code.py          | 138 ++++-   <- delivered code AND tests
 scripts/check-rc-contract.py        |  66 ++-     <- delivered code
 scripts/check-surface-recall.py     |  68 ++-     <- delivered code
 scripts/mutations/*.json (3 files)  | 184 ++--
```

Three delivered scripts, the workflow, and three manifests. Nine commits. **All three of the
waiver's named exclusions are false.**

Also stale in the same body: manifest `77 → 95` (actual **99**); declared sum `1178 → 1196` (actual
**1204**); self-test `131 → 160` (actual **169**); *"the real 1,193-entry manifest"* (actual
**1,204**); *"shard 1 of 8 | 353 s, 150/150 killed"* (the coordinator now measures **151/151**); and
the "What changed" list names only `--shard I/N`, never `--shard0`. Rounds **3–6 are absent
entirely** — the body ends at round 2.

Worst of the stale lines, because it describes the *defect* as the design:

> *"`N` comes from `strategy.job-total` and `I` from `strategy.job-index + 1`"*

The workflow carries no `+ 1`. Removing it **is** round 6's M1 — the entire point of `--shard0`.

**Not currently load-bearing, and I checked rather than assumed.** `check-merge-ready` reports
`review recorded rc=0 — ok — review recorded in this range: docs/reviews/claude/shard-mutation-sweep-r1-claude.m…`,
i.e. the gate took the **review-present** path, not the waiver path. So no gate is being bypassed
today. The risk is that the waiver is *standing testimony* with a false scope: if the review-present
path ever stopped matching, the fallback is a sentence that is no longer true.

**Fix — UNVERIFIED.** Before merge: delete the `NO-REVIEW:` waiver (it describes a commit range that
no longer exists and rounds 3–7 are recorded), refresh the four counts to 99 / 1204 / 169 / 1204,
drop the `strategy.job-index + 1` sentence, and add `--shard0` to "What changed". ⚠ The repo's own
rule is that a merge tick is written **before** the PR and not chased afterwards — that rule is about
not chasing a *squash SHA*, not a licence for the body's factual claims to drift nine commits.

---

### Observation (not a finding) — the backlog row's round count

`docs/backlog.md:245` (#217) says *"Five review rounds; r2-r4 were spent on a bytecode race."*
Rounds 6 and 7 exist. Per `dev-process.md` Phase 5 the tick is written before the merge, so a
count written then is expected to lag; I am recording it rather than filing it because the row's
substantive claims — the fix, the measurement, the remaining human action — are all accurate, and
the thing a reader needs from it is right.

---

## 3. Answers to the six questions

**Q1 · The accept set.** Airtight, with one exception. 88 constructed inputs across 18 invisible
code points in three positions each plus 34 structural forms: **87 refuse, 1 accepts, and the one
is `1/8`**. `$` inside `fullmatch` is redundant, not dangerous — the assertion still succeeds on
`"1/8\n"` and `fullmatch`'s end-position requirement rejects the match anyway. Non-`str` raises
`TypeError` but no caller can supply one. **The one exception is length, not alphabet: `L1`.**

**Q2 · Does `--shard0` select the slice it claims?** Yes — run, not reasoned. `--shard0 i/N` ≡
`--shard (i+1)/N` for every valid `i` at N = 1, 2, 3, 7, 8, 16, over the real 1,204-entry manifest
and over the mutation objects themselves. Union-complete, zero duplicates, zero missing, at every N.
Boundaries and the empty-shard refusal behave. **No finding.**

**Q3 · The CI seam end to end.** Extracted with ruby psych (pyyaml unavailable), byte-exact, no
dedent — and the block contains no inline Python, so `IndentationError` is not a reachable class
here. 18 hostile environments: **16 refuse with rc=2 and a sentence**, the real values start a real
sweep, and **one — the 4301-digit spec — gives rc=1 and a traceback**. A refusal does fail the step:
bash exits with the `python3` call's status. The `0;echo PWNED` case is **not** an injection; my own
detector false-alarmed on the refusal echoing the spec, and I have said so above rather than let it
stand.

**Q4 · Is anything else spelling "a decimal integer" its own way?** **Yes — nine other sites**,
three of them reachable from argv or a hand-edited file and **measured raising**, and one of them
(`count_drift`, bare `\d`) is 440 lines below `SHARD_SPEC` **in the same deliverable file**. No
shared canonical definition exists; the fold consolidated two spellings and left ten. `L2`, filed as
a backlog row rather than a fold.

**Q5 · Counts and anchors.** All four re-derived independently and **all four agree**: self-test
**169** (164 static `case(` sites + 5 loop iterations, by `ast`), manifest **99**, declared sum
**1204** (= 1,204 JSON entries = `load_manifests`), anchors **1,212** with **0 unresolved and 0
ambiguous**. Zero per-file disagreements across 57 manifests; zero duplicate names or anchor-tuples.
**No finding.** Shard 5 of 8 — deliberately *not* one of the four already measured, so this is a new
measurement rather than a reconfirmation — verbatim:

```
OK — delivered scripts mutated: 54 file(s), 150 mutation(s), 150 killed, 150 attributed to the case
each names, 0 survivor(s) — measured over shard 5 of 8 (round-robin)
```

⚠ **150, not 151, and that is correct rather than a shortfall** — shards 1–4 each hold 151 and
shards 5–8 each hold 150 (§1.3, `1204 = 4×151 + 4×150`). I am saying so explicitly because "151"
appears in the brief and in the dashboard entry, and a reader comparing numbers would otherwise read
this as one entry missing. The verdict line also names its own slice (`shard 5 of 8 (round-robin)`),
which is `shard_label` doing the job it was added for.

**Q6 · Merge readiness, verbatim:**

```
pull request           : #366
base                   : origin/master
pull-request-only steps: 2 derived from ci.yml — dashboard entry ratchet, check-review-recorded (PR only)

  ok  dashboard entry    rc=0  ok — an entry block was added
  ok  review recorded    rc=0  ok — review recorded in this range: docs/reviews/claude/shard-mutation-sweep-r1-claude.m
  ok  review rounds      rc=0  ⚠ verdict corpus: 221 read — 29 meaningfully checked below, 192 PRE-CUTOVER (schema < 3:
  ok  mergeability       rc=0  open, not draft, based on master, head 6416e212, CLEAN
  ok  CI                 rc=0  12 check(s) green

READY — every gate CI will run has been run here, including the PR-only ones
```
rc=0.

**And the question no gate asks.** Backlog, roadmap and dashboard are **clean and consistent**:
`backlog.md:245` ticks #217 `✅ FIXED 2026-10-06 — PR #366` with the remaining human action named;
`roadmap-to-launch.md:2227` carries `- [x] #217`; and the 2026-10-06 dashboard entry's counts row
(`169`, `99`, `1204`, `1,212`) matches my independent derivation **exactly**. `check-backlog-closure`'s
two WARN rows (#117, #159) are pre-existing and belong to other PRs. **The misleading artifact is the
PR body — `L3`.**

---

## 4. What I tried to refute and could not

The brief said a rigorous demonstration that there is no sixth hole is the second-best outcome. I
found two seam defects, so this section is not that — but these are the attacks that failed, and
they are where a future round should **not** spend effort.

1. **Whitespace and invisible characters — the actual subject of the fold.** 18 code points × 3
   positions = 54 inputs, every one refused. I specifically tried the ones a `strip()`-shaped fix
   tends to miss: `NBSP` (U+00A0), `U+3000` ideographic space and `U+180E`, none of which
   `str.strip()` removes in all Python versions and all of which the regex refuses anyway because it
   never calls `strip()`. **The decision to delete `.strip()` rather than widen it is why this
   held** — a widened `strip()` would have been the sixth version.
2. **`$` inside `fullmatch`.** The brief flagged it, I expected a hole, and there is none. I checked
   the mechanism rather than the outcome: `$` still asserts at position 3 of `"1/8\n"`, and the
   match is rejected by `fullmatch`'s end-position requirement instead. A reader who "fixes" the
   redundant anchors away will not break it, and a reader who swaps `fullmatch` back to `match`
   will — which is exactly the mutation entry the fold added.
3. **The partition.** I tried to make `--shard0` and `--shard` disagree at N=1, at N=16, at the
   first and last index, on the real objects rather than ids, and on the union. 1,204 entries,
   six values of N, zero disagreements. The `+1` living inside `parse_shard` rather than the
   workflow is doing what round 6's M1 claimed.
4. **A mutation appearing in no shard or two.** Union-complete and duplicate-free at every N. I also
   checked the thing a count cannot see: the *identity* of each entry per shard, not just how many.
5. **The declared counts.** I expected one of the four to be stale — this repo's most-repeated
   defect, and three of the four moved in the commit under review. All four agree, and I derived
   each from a different source than the one declaring it.
6. **Anchor resolution.** 1,212 find-strings counted against their delivered targets; I was looking
   for a zero-match (orphaned by the fold's own comment rewrite, which is how two were orphaned one
   round ago) or a multi-match (ambiguous, so the mutation might land twice). **0 and 0.**
7. **A shell injection at the seam.** `0;echo PWNED`, `0 1`, `8 -x`. The quoting is correct; my
   detector false-alarmed and I ran the case down rather than reporting it.
8. **The duplicate-entry refusals being weaker than their messages.** `:1504-1524` already says so,
   at length and accurately. I tried to find a case where the *code* is weaker than that *comment*
   and could not.
9. **The bytecode scrub** — not attacked, per the brief (rounds 4, 5, 6 found nothing).

---

## 5. Findings table

| # | severity | aim | caused by a previous fold? |
|---|---|---|---|
| **H1** | High | **deliverable** — `check-plan-code.py:4539` | **YES — round 6's M1.** It added `--shard0` and did not pass it to `shard_mode_refusal`, reopening round 1's Codex Medium |
| **L1** | Low | **deliverable** — `check-plan-code.py:1556,1587` + the comment at `:1551` | **PARTLY.** The *defect* predates `parse_shard`'s first regex (`int(m.group)` is present at `68f6d7ea^`). The *claim that it is impossible* was written one fold ago, by `d95908c0`, as round 6 L2's repair |
| **L2** | Low | instrument — 9 sites across 8 guards, one of them in `check-plan-code.py:2025` | No. Pre-existing; surfaced by asking the brief's Q4 |
| **L3** | Low | merge artifact — the PR #366 body | No. Drift across nine commits; the waiver was true when written at `b1d059e9` |

Blocking: **0**. High: **1**. Medium: **0**. Low: **3**.

**Q5 of the method · thrashing?** Per-finding, as the method requires:

- **H1 — yes, caused by the previous round's fix**, and this is now the **second consecutive round**
  in which a finding was caused by the immediately preceding fold (round 6 L2's byte-class fix
  produced the false claim in `L1`; round 6 M1's `--shard0` produced `H1`). That is the surface
  condition for the thrashing clause.
- ⛔ **But the single test — *can a redesign remove it?* — says NO, and I do not convene an
  architecture review.** Both defects are in the **same function's two seams**, not spread across a
  component, and both have a bounded mechanical repair: pass one more argument, bound one quantifier.
  The accept-set rule itself has now been stable for two rounds and survived 88 adversarial inputs.
  What is thrashing is not the design; it is that **each repair has been scoped to the instance the
  reviewer exhibited** — `L2` is the same pattern a third time. The right response is a class fix
  (a shared decimal parser, and a case that goes through `main` rather than calling the predicate),
  which is a slice, not a redesign.
- Round 4's clean round was quiet 1; rounds 5, 6 and **7** each reset it. Four rounds was passed two
  rounds ago, and the brief's own table records that reaching four **obliges asking** — asked and
  answered here, with evidence, as *prose floor is not the issue; instance-scoped repair is*.

---

## 6. Verdict

# NOT CONVERGED

`review-method.md:110` stops only on **two consecutive** rounds with no Blocking, no High, no
finding in the deliverable, and no non-trivial fixes. This round has **one High and two findings in
the deliverable**, so:

**This is not a clean round at all — not the first of two, not the second. The quiet counter is
reset to zero**, as it was after rounds 5 and 6. Round 4 remains the only clean round on this
branch, and it is no longer consecutive with anything.

`fixes_nontrivial` will be **true** for whatever fold answers H1, because a correct answer is not
the one-line argument change — it is a case that reaches the wiring through `main`, plus a mutation
entry that severs `a.shard0` by name. A fold that takes only the one-liner should expect round 8 to
find the third instance of the same shape.

⛔ **Do not merge on this round.** H1 is a documented-CLI invocation that prints `169/169 passed` and
exits 0 while validating nothing — the one outcome `scripts/check-plan-code.py` exists to make
impossible.
