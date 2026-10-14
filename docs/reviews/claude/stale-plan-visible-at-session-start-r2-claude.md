<!-- claude-review: round 2, CLAUDE half, subject d4c1c016 (the fold of r2's Blocking) -->

Reviewed `d4c1c016` — the fold of round 2's Codex Blocking — on top of the round-2 brief's nine
claims. Primary subject: the new `check-plan-code.py --self-test` case
*"every manifest anchor binds EXACTLY ONCE on the delivered tree"*, the retargeted
`begin-plan.json` entry, and the locally derived `_repo`.

---

## Blocking

**None.** Stated with what I looked for, because an empty Blocking section is otherwise
indistinguishable from not having attacked.

The fold's own claims about itself all hold under reproduction: both falsification arms red the new
case over a green control (below, S1); the retargeted entry is `attributed` and dies through the
case it names on both interpreters (S2); `_repo` resolves correctly in a staged `HARNESS_TREE` copy
and the case is NOT vacuous there, proved by a known positive (S4); all 1425 anchors bind exactly
once under BOTH the new predicate and `mutate_delivered`'s own (S5). I found no state in which the
delivered tree is wrong today. What I did find is that the instrument the fold installed is blind
to two further shapes of the same class and has no falsifier for its own corpus — H1 and H2 — which
matters especially here, because this is the second repair in this branch to one class and the first
repair caused the second defect.

## High

### H1 — the new case's predicate is NOT the predicate `--mutate` uses, and the gap is the same `anchor NOT FOUND` the Blocking was about

`check-plan-code.py:4971-4983` counts every edit's find-string against the **pristine** file:

    _body = _target.read_text(encoding="utf-8")
    for _find, _ in _e["edits"]:
        _n = _body.count(_find)

`mutate_delivered` -> `run_mutations` (`:1963-1981`) counts each edit against the file **as mutated
so far within that entry**: `src = src.replace(find, repl, 1)` runs between the checks. For an entry
with more than one edit the two predicates answer different questions, and the self-test's answer is
the wrong one.

**Measured, on a `tar` copy, green control first.** I retargeted the second edit of
`check-python-pin.json`'s one 2-edit entry to `"and not is_job]"` — a substring of its own first
edit's find-string, occurring exactly once in the pristine file:

| | result |
|---|---|
| copyA control, `check-plan-code.py --self-test` | **179/179 passed** |
| `check-python-pin.py --self-test` control in the staged tree | **111/111 passed** |
| the new case, over that manifest | **179/179 passed — GREEN** |
| `run_mutations` over the same entry | `ok=False`, **0 verdicts produced**, report: *"anchor NOT FOUND — it was not applied, so its 'caught' verdict would be meaningless"* |
| restore + re-control | 179/179 passed |

That is byte-for-byte the symptom r2's B1 was filed for — `anchor NOT FOUND`, no verdict, a shard
that cannot produce a measured pass — reached through a manifest the new case certifies as clean.
`count != 1` covers 0 and 2+ **on one snapshot of the file**; it cannot see an anchor that is unique
on the pristine tree and absent (or duplicated) by the time its own entry's earlier edit has landed.

**Bound, honestly.** 8 of 1417 entries have more than one edit (`check-banner-armed`,
`check-plan-file-tags` x2, `check-python-pin`, `check-vocabulary-collisions`, `gen-dashboard` x3).
I re-derived all 1425 anchors under the sequential predicate: **zero divergences today**. So this is
a hole in the instrument, not a live defect — which is exactly what *"multiplied relative to master"*
was one round ago.

**Fix:** evaluate the rule the way the consumer does — walk each entry's edits applying `replace(…,1)`
between the counts. It is the same loop plus one line, and it makes the case a statement about
`mutate_delivered` rather than about `str.count`.

### H2 — severing the new case's own corpus leaves the suite GREEN: it has no falsifier for "I measured nothing"

`for _man in sorted((_repo / MANIFEST_DIR).glob("*.json")):` -> `for _man in sorted([]):`

| | result |
|---|---|
| copyA control | 179/179 passed |
| corpus discovery severed | **179/179 passed — still GREEN** |
| re-control | 179/179 passed |

`_orphans` is `[]` over an empty corpus and `[]` is the expected value, so the case reports success
having examined zero anchors. The two neighbouring data cases 19 lines below do NOT cover this: they
read the manifests through `load_manifests`, independently, so severing the new case's own glob
leaves them untouched. This is the repo's own named rule, written in `check-plan-file-tags.py` and
quoted in `CLAUDE.md` — *"an empty corpus is CANNOT RUN, because a zero over nothing is not a
finding"* — and the measured memory *"before you trust a NEGATIVE, check a KNOWN POSITIVE"*.

It matters more than usual because the fold's argument for this case is *"it is now a case rather
than a sweep I remember to run"*. A case that cannot fail when its population vanishes is a sweep
nobody runs, wearing a green tick.

**Fix (cheap, no new read):** assert the population alongside the result, derived rather than typed —
compare the number of anchors examined with `sum(len(e["edits"]) for e in _live_entries)`, which this
same function already computes 19 lines later. Severing the glob then reds.

### H3 — `cmd_add` tracebacks on a long prose title on BOTH interpreters, and `_auto_slug`'s docstring sentence "Never raises" is false on the CI interpreter

Codex filed this as **M4**; I escalate, and the escalation rests on a measurement Codex did not take.
Codex's account — *"Python 3.14 returns that overlong slug instead, leaving the eventual write to
fail"* — reads as though 3.14 is safe. The verb is not safe on either.

Measured, in a redirected `HOME` with a real `.claude/plans`:

| input | 3.12.9 (what CI pins) | 3.14.4 |
|---|---|---|
| `_auto_slug("a"*200)` | ok | ok |
| `_auto_slug("a"*255)` | **OSError [Errno 63] File name too long** | ok |
| `_auto_slug("a"*500)` | **OSError** | ok (returns a 500-char slug) |
| `cmd_add("w "*160)` (320-char prose title) | **OSError** | **OSError** |

So: `_auto_slug`'s own docstring opens *"Never raises; never collides"* and that is false on the
interpreter CI pins; and `cmd_add` — the verb this whole slice exists to make usable — ends in an
unhandled traceback on both. The suite nevertheless contains
`case(f"_auto_slug never raises on a realistic title ({_bad!r})")` over a four-title corpus
(`"Review src/api"`, `"../escape"`, `".dotfile"`, `"Fold r5 + the approved deletion"`) in which no
title is long. That is this repo's measured *"a BOUND enumerates what is WITNESSED"* shape: the case
name generalises over length and the corpus does not contain it.

This is the same defect class as r1 H1/M3 (a prose title reaching a filename validator unguarded),
in a dimension the r1 fix did not consider. Bound the generated stem; keep the full title in the
plan body, which the docstring already says is where the meaning lives.

### H4 — the `cmd_add` create path has no falsifier of EITHER kind

Codex filed this as **M5** on the strength of the suite staying green. The stronger fact is that the
mutation sweep is blind too, so there is no instrument in the repo that would notice.

    -        return cmd_begin(_auto_slug(title), [step_arg])
    +        return cmd_begin(normalise_slug(title), [step_arg])

| | result |
|---|---|
| control | 93/93 passed |
| mutant, Python 3.14 | **93/93 passed — SURVIVES** |
| mutant, Python 3.12 | **93/93 passed — SURVIVES** |
| manifest entries targeting `cmd_add`'s create path (`_auto_slug(` / `cmd_begin(` / `cmd_add`) | **NONE** |
| re-control | 93/93 passed |

And the mutation is not cosmetic — it restores both r1 Highs at once. Exercised through the module:

    _auto_slug("fix the a/b seam")   -> 'added-2026-10-14'
    normalise_slug("fix the a/b seam") -> RAISES ValueError (the r1 H1 traceback)
    _auto_slug("repeat")             -> 'repeat-2'   (existing plan preserved)
    normalise_slug("repeat")         -> 'repeat'     (the r1 H2 overwrite, restored)

`begin-plan.json` has 24 entries and 21/22 cover the two **helpers**; nothing covers the one line
that connects them to the verb. r1 Claude M4 (*"the new verb has no self-test at all; only the pure
helper does"*) is listed in the fold as resolved by the new helper cases. It is not: the branch
`cmd_add` takes when nothing is armed is still reachable only through the verb, and nothing drives it.

### H5 — the session-start CANNOT-RUN message is FALSE in the paused states, and drops the pause reason there

Codex filed this as **M2**; I escalate because the false sentence reinstates r1 Codex H1's exact
damage in a state that fix did not cover, and because the omission Codex did not mention is the worse
half.

`check-plan-progress.py:418` and `:429` say, unconditionally:

> ⛔ And the Stop guard REFUSES EVERY STOP in this state, because a check that cannot run must not
> pass: the session cannot end until this is fixed.

Measured, `decide()` vs `session_start_verdict()` on the same four sentinels:

| state | `decide` rc | session start says "REFUSES EVERY STOP" | pause reason shown |
|---|---|---|---|
| plan missing, not paused | 2 = BLOCK | yes (true) | n/a |
| plan missing, **paused** | **3 = WARN, non-blocking** | **yes (FALSE)** | **no** |
| zero checkboxes, not paused | 2 = BLOCK | yes (true) | n/a |
| zero checkboxes, **paused** | **3 = WARN, non-blocking** | **yes (FALSE)** | **no** |

The paused message is byte-identical in length to the unpaused one (352 and 292 bytes in both rows),
because the NOT_RUN branches return before `paused_reason` is ever read. Meanwhile `decide` prefixes
`⏸ PAUSED (<reason>) — and …`, so the two channels disagree twice: about the consequence, and about
whether a pause exists at all.

And the file itself already settled this, 200 lines away, at `:194-198`:

> ⟳ RECORDED EXPLICITLY at the Codex half's request (code review r1, Cx-M2), which asked whether
> `paused:` is meant to override cannot-run. IT IS, on this path only.

So the new text contradicts a decision recorded in the same file in the previous round's fold. The
damage is r1 Codex H1's: a reader told the session cannot end until the sentinel is fixed, and not
told a pause reason exists, repairs or deletes a sentinel carrying a live waiting reason. Make the
consequence conditional on `paused_reason`, and quote the reason in both NOT_RUN states.

## Medium

### M1 — the retargeted entry's new name cites a finding that is a DIFFERENT entry's subject, and that entry already claims it

The fold renamed entry 18 to *"the of-N total rewrite is skipped on checkbox lines, so the labels
drift **(r1 H2, retargeted r2 B1)**"*. The pre-fold name carried no finding tag at all.

* r1 Claude **H2** = *"`cmd_add`'s create path silently overwrites an existing plan file, destroying
  unticked work"* — which is entry **21**'s subject, and entry 21's name already ends `(r1 H2)`.
* r1 Codex **H2** = *"Runner failures become silent success"* — the hook. Also not this.
* The of-N rewrite's scope was r1 Claude **M1** / r1 Codex **M1**, already claimed by entry **23**.
  The rewrite itself predates round 1 entirely: it was `_TOTAL_RE.sub(..., body)` before the fold.

The manifest is this repo's provenance ledger for which falsifier belongs to which review finding,
and `docs/dev-process.md` requires an id to be qualified rather than bare. Two entries now assert
`r1 H2` and the wrong one is the entry this commit edited. No guard checks finding-id uniqueness, so
nothing will catch it later. The correct tag is `retargeted r2 B1` alone, or
`narrowed by r1 M1, retargeted r2 B1`.

### M2 — "48 guards discovered, 48 RAN, 1 red" is a claim over a population the commit does not define, and there is a second red inside the gap

I ran `--self-test` on every `scripts/*.py` on disk, sequentially, stdin closed:

    69 python files · 67 accept --self-test · 66 green · 1 RED · 2 have no --self-test

The red is **`scripts/subject_status.py` — 16/17**, failing `"the parked schema reports UNSHIPPED,
not SHIPPED"` on BOTH interpreters.

⚠ **This red is PRE-EXISTING and must not be charged to this branch:** `git log 74a44551..d4c1c016 --
scripts/subject_status.py` is empty, and the branch does not touch the schema directory the case
reads. But it is unowned by anything: `grep` finds no reference in `.github/workflows/`,
`scripts/check-schema-gates.sh` or `.claude/hooks/`; there is no mutation manifest for it; it carries
no `NO-CALLER:` line; and `check-ratchet-contract.py`'s population is 44 guards keyed on `check-*.py`,
which excludes it by name.

Four derivations of "the guards" now disagree — 44 (`check-ratchet-contract`), 48 (this commit),
53 (the Codex half), 67 (the filesystem) — and the one the commit used is the only one with no
written definition. `CLAUDE.md` records the lesson verbatim for `check-ratchet-contract.py`:
*"the population is the FILESYSTEM; CI-step discovery saw 14 of 24 and missed all three guards that
nothing ran"*. The fold's line should name its population, or use the filesystem and declare the red.

### M3 — the class the fold claims to have closed has a second equally cheap shape it did not close: an `expect` that names no existing case

The fold's argument is structural: *"it is a pure property of (manifest, file) and needs no mutation
run, so discovering it through a minutes-long sharded sweep was never necessary."* That argument
applies verbatim to `expect`, and `expect` is still sweep-only.

Measured on copyA, entry 18's `expect` replaced with a case name that exists nowhere:

| | result |
|---|---|
| `check-plan-code.py --self-test` | **179/179 passed — GREEN** |
| `begin-plan.py` control in the staged tree | 93/93 passed |
| `run_mutations` over the entry | `ok=False`, `attributed: False`, *"matched 0 red case(s) — it was caught by something else"* |
| re-control | 179/179 passed |

So a one-character typo in an `expect` costs a full sharded sweep to discover, which is the cost the
fold's own reasoning says is unnecessary. It is resolvable without running any mutation: each guard's
`--self-test` prints its case names, so one `--self-test` per distinct manifest target (59 runs,
~60s) yields the set every `expect` must be a member of. That is two orders of magnitude cheaper than
1417 suite runs.

I am filing this as the *class* finding rather than as a second instance, because the commit's
headline is that the predicate was the fix. The predicate was one of three shapes; H1 is the second
and this is the third.

### M4 — backlog #284's proposed remedy already exists, and is structurally blind to #284

Codex filed this as **L1**; I escalate, because #284 is 🔴 OPEN and whoever picks it up will build
something that is already there and already green over the defect.

The row's status cell says: *"The cheap first step is a REFUSAL — a shard whose executed total
differs from `len(shard_slice(...))` must fail, not report OK."* Constructed directly against
`coverage_verdict.Measured`:

    Measured(declared=706, mutations=[605 verdicts], controls_green=True)
      -> VerdictContractError: 605 verdict(s) for 706 declared mutation(s)

    Measured(declared=605, mutations=[605 verdicts], controls_green=True)
      -> CONSTRUCTED. A self-consistent green.

Clause 2 of `Measured.__post_init__` is the proposed refusal, and it already shipped. It cannot see
#284 because `declared = len(shard_muts)` (`check-plan-code.py:1891`) is taken from **the same
population that was narrowed** — so declared and executed agree at 605 and the clause is satisfied.
#284's symptom is a narrowed POPULATION, not a skipped execution, and the two are different claims.

This is the repo's own *"a finding's proposed FIX is a hypothesis"*. The row's `FAILS IF` is fine;
its remedy sentence should be struck and replaced with something that observes the population —
e.g. the shard asserting `len(muts)` against the declared manifest sum before slicing.

I did **not** reproduce the concurrent narrowing itself (see CANNOT RUN) — the brief forbids it and
it is #284's own hazard. `shard_slice` itself is sound: disjoint and exhaustive at N=2, 5 and 8
(709/708, 284/284/283/283/283, 178+177x7 = 1417), and the row's 707/706 figures are consistent with
the 1413 entries the slice commit carried, so they are coherent but unstamped with a commit.

### M5 — fence tracking is still wider than the claim (confirming Codex M2 r2-M1, at its severity)

Reproduced independently on `append_step`, one real checkbox, appending one step. Each row lists only
the PRE-EXISTING lines the call changed:

| shape | pre-existing line rewritten? |
|---|---|
| three-backtick fence | no (protected) |
| **tilde `~~~` fence** | **yes — `**Step 1 of 9**` -> `of 3`** |
| **four-backtick fence containing a three-backtick line** | **yes — the nested example -> `of 3`** |
| **inline literal ON a real checkbox line** | **yes — `real with literal **Step 8 of 9**` -> `**Step 8 of 3**`** |
| unterminated fence | no |
| fence indented inside a list item | no |
| prose outside a fence | no |

`:262` toggles a boolean on any line whose lstrip starts with three backticks: it tracks neither the
fence character nor the delimiter length, and the substitution is still unanchored within an accepted
line. The commit's scope claim is *"scoped to real checkbox lines outside fences"*; the third row
shows the second half of that sentence is not kept even on a line the first half accepts.

### M6 — the hook's failure reporting, with a different diagnosis from the Codex half (confirming r2-M6)

Exercised `.claude/hooks/report-plan-state.sh` against stub readers, 20s cap:

| reader | hook rc | delivered to context |
|---|---|---|
| normal stdout | 0 | the verdict (correct) |
| whitespace only | 0 | CANNOT RUN, "produced 7 bytes" (correct) |
| exit 0, no output | 0 | CANNOT RUN, "produced 0 bytes" (correct) |
| rc=1 with stdout | 0 | CANNOT RUN, "exited 1" (correct) |
| **exit 0, STDERR only (`boom`)** | 0 | **`boom`, delivered as the verdict. No CANNOT RUN** |
| **verdict + one stderr line** | 0 | **`DeprecationWarning: x` FIRST, then the real verdict** |
| **reader hangs** | — | **nothing; still running at 20s** |
| **prints 10 MB** | — | **nothing within 20s** |

`out=$(… 2>&1)` merges before `[ -z "${out//[[:space:]]/}" ]`, so stderr satisfies the emptiness
guard that exists to catch exactly a reader that failed to speak — and when both streams are used,
stderr is ordered ahead of the verdict in the session's context.

⚠ **Where I disagree with Codex's diagnosis of the last row.** Codex attributes the 10 MB stall to
unbounded buffering. It is the wrapper's own emptiness test. Isolated:

| captured bytes | `[ -z "${out//[[:space:]]/}" ]` | `[[ "$out" =~ [^[:space:]] ]]` |
|---|---|---|
| 100 KB | 0s | — |
| 1 MB | 1s | — |
| 4 MB | **16-17s** | **0s** |

The pattern substitution is super-linear, so the guard against an empty verdict is itself what stalls
SessionStart on a large one. The fix is therefore not only a deadline: it is `[[ =~ ]]` (or
`grep -q '[^[:space:]]'`), plus keeping stdout and stderr separate, plus a cap on both. The current
message's own `head -c 400` shows the cap was already understood for one branch and not the other.

⚠ Not reachable from the shipped reader today: `check-plan-progress.py --session-start` emits <= ~450
bytes and the suite asserts it writes nothing to stderr. Both arms need a second defect, or a
Python-level warning, to fire. Filed at Medium on that basis.

## Low

### L1 — `_repo` is now derived twice in the same function, 19 lines apart, with identical expressions

    4971:    _repo = pathlib.Path(__file__).resolve().parent.parent   # added by this fold
    4990:    _repo = pathlib.Path(__file__).resolve().parent.parent   # pre-existing

The commit message justifies the new one at length — *"derived here, LOCALLY, because this module has
no repo-root constant"* — and the derivation it describes was already present, below it, in the block
the new case was inserted in front of. The expression is right (S4 proves it), so this is not a
correctness defect; it is a second copy of one derivation, which is the repo's most-measured
structural shape. Delete the new assignment and move the case below `:4990`, which also gives H2 its
falsifier for free.

### L2 — the commit says the entry's `expect` moved with its name and anchor; `git show` shows `expect` unchanged

`git show d4c1c016 -- scripts/mutations/begin-plan.json` changes exactly two lines, the `name` and
the find/replace pair. The `expect` block is context. The substantive claim behind the sentence is
true and I verified it (S2) — the named case survived r1's fold, so `expect` needed no change — but
"moved together" asserts a mechanical fact the diff refutes, in a commit whose own subject is a
sentence that outran its code.

### L3 — the new case re-reads every target file once per ENTRY: 1417 reads and 212 MB per self-test run

`_body = _target.read_text(...)` sits inside the per-entry loop, and 1417 entries share 59 target
files. Measured on the reviewed tree, median of 5:

| form | time |
|---|---|
| the loop as written | **0.301s** |
| the identical rule, each target read once | **0.069s** |

`check-plan-code.py --self-test` goes from ~5.1s to ~5.7s, and the sweep runs it 106 times (its own
`EXPECTED_MUTATIONS`) plus two controls, so roughly 25 avoidable seconds per full sweep. ⚠ This is
**not** the `8756c623` class ("a test whose COST depends on the mutation it tests"): the cost is flat
and the `run_suite` ceiling is 120s against a 5.7s suite, so no timeout is in reach. Filed as Low on
that basis — one `dict` of file contents removes it.

### L4 — the second conjunct of r1 M1's fix has no manifest entry, though two cases cover it

Entry 23 severs the fence toggle. Nothing severs the checkbox restriction. Measured:

    -        if not in_fence and _BOX_RE.match(line.rstrip("\n")):
    +        if not in_fence:

    control 93/93 -> mutant 91/93, red:
      [FAIL] prose containing `of 9` is NOT rewritten
      [FAIL] …and no `of 9` was turned into `of 2` anywhere
    re-control 93/93

So the behaviour is case-covered and the cases do fire — but the manifest is what pins a case as
load-bearing, and deleting both cases together with the declared count would pass every gate. Half of
r1 Codex M1's fix is manifested and half is not.

## Checked and found SOUND

**S1 — both falsification arms of the new case reproduce, with a green control and a re-control.**
On a `tar` copy of the reviewed tree (`.venv`, `node_modules`, `.git` excluded; dependency symlink
restored), control 179/179 before each arm and after each restore:

| arm | result |
|---|---|
| anchor edited to text present in no file | `[FAIL] every manifest anchor binds EXACTLY ONCE…: got ["check-anchors.json: '…' binds 0 time(s)"]` — **178/179** |
| anchor set to `            else:`, which occurs twice in `check-anchors.py` | `… binds 2 time(s)` — **178/179** |

The commit's claim that the case covers both directions is true as stated.

**S2 — the retargeted entry dies through the case it names, on both interpreters.** Through
`run_mutations` on a staged `HARNESS_TREE`, control and re-control 93/93 each time:

    expect: ['every `of N` total is rewritten — no stale `of 2` survives']
    caught=True  attributed=True  measured=True
    red cases: ['every `of N` total is rewritten — no stale `of 2` survives',
                '…and they all read `of 3`', 'the real checkbox total IS rewritten']

Three reds, so the fold's `90/93` is exact. The mutated statement still runs (`line = line`), and the
behaviour the name claims — every `of N` total on a checkbox line is rewritten — is what fails. The
retarget guards a behaviour, not a spelling.

**S3 — the five named mutations, and 58 more, are killed and attributed; 0 survivors.** I selected
every entry whose name carries an `r1`/`r2` tag — 63 entries across 14 guards, a wider set than this
branch's 7 — and ran them through `run_mutations` on one staged tree:

    14 CONTROLS all green (93, 125, 154, 179, 44, 82, 111, 56, 194, 77, 59, 168, 73, 201)
    ok=True | 63 verdicts | 0 survivors | caught=True and attributed=True on all 63
    14 RE-CONTROLS all green at the same numbers

That includes all four `begin-plan` and all three `check-plan-progress` entries belonging to rounds 1
and 2. **And specifically on the brief's question about the repaired case:** entry 22 (the slug
fallback replaced with `raise`) is `attributed=True` with 5 reds. The `_safe_slug` wrapper catching
the raise does not weaken it — the mutant makes `_auto_slug` raise, `_safe_slug` returns `None`, and
the case's `isinstance(_got, str) and _got != ""` fails on the `None`, which is the behaviour the
case names. The adjacent cases (`strips a path separator`, `falls back to a dated name`) cover the
nearby "fallback present but wrong" mutants, so the kill is not load-bearing on a single assertion.

**S4 — `_repo` is correct under every invocation I could construct, including a staged tree, and the
case is NOT vacuous there.** `Path(__file__).resolve().parent.parent` from `scripts/` is the repo
root; `copytree` yields a copy, not a symlink, so a staged tree resolves to the staged root. Verified
with a known positive rather than a green:

    staged manifests: 59 · manifest targets MISSING in the staged tree: 0
    STAGED CONTROL:        rc=0  179/179 passed
    STAGED KNOWN-POSITIVE: rc=1  [FAIL] every manifest anchor binds EXACTLY ONCE … binds 0 time(s)
    STAGED RE-CONTROL:     rc=0  179/179 passed

All 59 manifest targets lie under `HARNESS_TREE`'s six paths, so the case measures its real subject
inside the harness as well as in the repo.

**S5 — the anchor population and its uniqueness, re-derived two ways.** 59 manifests, 1417 entries,
1425 edit anchors, 59 distinct target files, every one present and inside `HARNESS_TREE`. Under the
new case's predicate: all 1425 bind exactly once. Under `mutate_delivered`'s sequential predicate:
also all 1425. The commit's "1425 anchors, every one binds exactly once" is correct.

**S6 — no anchor binds only in inert text.** Using `tokenize` for comments and `ast` for
module/class/function docstrings: **0** anchors whose single binding lies wholly inside a comment, and
**0** inside a docstring. (28 anchors bind inside string literals; I excluded those deliberately —
they are regex patterns and user-facing message text, i.e. live production data, and mutating them
does change behaviour.) The brief's "binds once in a COMMENT" shape does not occur today.

**S7 — the nonempty-message premise behind the hook's empty-output rule holds.** All six verdict
labels return a nonempty message, including both NOT_RUN states with and without a pause:

    unarmed 300B · cannot-run 352B / 292B (paused and unpaused identical) · live 94B
    parked 187B · parked-done 427B · stale 328B

No state returns an empty message, so "empty output is itself a failure signal" is sound about the
reader. (What the wrapper does with it is M6.)

**S8 — the declared counts all re-derive, on both interpreters.** `check-plan-code` 179/179 (docstring
says 179), `begin-plan` 93/93, `check-plan-progress` 82/82; `EXPECTED_MUTATIONS` entries for
`begin-plan.py` = 24 and `check-plan-progress.py` = 20, matching the manifests on disk; declared sum
1417, matching `len(load_manifests(...)[0])` with zero loader problems. `check-selftest-counts.py`
green.

**S9 — `check-review-rounds` is red for exactly the reason the commit says.** Live invocation:
*"stale-plan-visible-at-session-start round 2: only codex — claude neither ran nor recorded a
`REVIEW GAP:` line"*. That is this round's debt, closed by this file, not a defect.

**S10 — `load_manifests` already refuses the "target file deleted" shape**, so the new case's
`if not _target.is_file(): continue` is not the hole it looks like: `:1493-1496` records a problem
for a manifest whose `scripts/<stem>.py` is absent, `:1547` refuses any entry whose `file` disagrees
with the manifest name, and `:5020` runs that loader over the live tree in the same suite. I probed
for a divergence that matters and found none — which is why H1 is about the *sequential* predicate
and not about this `continue`.

## CANNOT RUN

These are verification failures, not passes. **Treat every item here as NOT RUN.**

* **The full `--mutate .` over all 1417 entries, on this tree.** I ran 63 real entries plus one
  constructed one, each through `run_mutations` on a staged `HARNESS_TREE` with green controls and
  re-controls. That is affirmative evidence for the entries named and says nothing about the other
  1354. The commit also records this as NOT RUN; I am not contradicting it, I am declining to let my
  partial run read as closing it.
* **Backlog #284's concurrent narrowing.** I deliberately did not launch two shards at once — the
  brief forbids it and it is the very hazard #284 describes. Its 707/605 observation is independently
  unverified by me. My M4 is about the row's proposed remedy, which I constructed directly; it is not
  a reproduction of the row's symptom.
* **The real SessionStart delivery path.** I exercised `report-plan-state.sh` with stub readers in a
  temporary tree. I never observed Claude Code itself ingest the hook's stdout, so every claim about
  what reaches a session's context is a claim about the shell wrapper only.
* **`tsc --noEmit`, the unit suite, `test:integration`, `test:e2e`, the schema gates' Postgres, and
  every PR-only gate** (`check-merge-ready.py` and friends). Not attempted; no Docker check made.
* **`check-memory-link.py`** is green in my sweep while reporting its corpus absent. That green is
  not a measurement and I excluded it from S-grade evidence.

## Instruments

Reviewed `d4c1c016` (`git show`, full message and diff), `docs/reviews/codex/…-r2-codex.md`, both
round-1 halves, the round-2 brief, and the `scripts/` and `.claude/hooks/` sources in full where
quoted. Worked in
`/Users/kujinlee/.claude-tmp/claude-501/…/scratchpad/wt-staleplan` at `d4c1c016`.

Interpreters: **Python 3.14.4** and **/usr/local/bin/python3.12 (3.12.9)**, the CI pin. Every guard
invocation closed stdin (`</dev/null` or `stdin=DEVNULL`).

Mutations were applied only to copies, never to the reviewed tree: **copyA**, a `tar` copy excluding
`.venv`, `node_modules` and `.git` with the dependency symlink restored (control 179/179 before any
edit, and a re-control after every restore); **copyB**, a two-file tree for the hook probes; and
per-run staged `HARNESS_TREE` trees under `mkdtemp` for `run_mutations`. No two mutation runs were
launched concurrently (#284). No `git` command touched the main checkout.

Baseline sweep on the reviewed tree: 69 `scripts/*.py`, 67 accepting `--self-test`, run sequentially
— 66 green, 1 red (`subject_status.py`, M2), 2 with no `--self-test`.

⚠ **One tracked file in this worktree is modified and it is not mine:** `docs/available-skills.md`,
regenerated by `scripts/regen-skills-doc.py` at 16:08 (a plugin-version bump, `superpowers` 6.3.0 ->
6.4.1). I did not write it and I left it alone. My own write is this file and nothing else.

## Where I disagree with the Codex half

**Reconciliation of all of r2 Codex's findings, re-measured rather than read.**

| Codex r2 | my verdict |
|---|---|
| B1 — orphaned anchor | **CONFIRMED as correctly folded.** The predicate repair works in both directions (S1) and over the real 1425 (S5). My H1 is that it is still not the predicate `--mutate` uses. |
| M1 — fence protection too wide | **CONFIRMED at Medium**, all three shapes reproduced independently (my M5). |
| M2 — "REFUSES EVERY STOP" false when paused | **CONFIRMED and ESCALATED to High** (my H5). Codex's remedy — make the consequence conditional — is right but incomplete: the paused NOT_RUN message also omits the pause reason entirely, which is the half that reinstates r1 Codex H1's damage. |
| M3 — `PARKED_DONE` is a new wrong answer | **PARTLY DISAGREE — see below.** |
| M4 — `_auto_slug` raises on long titles | **CONFIRMED and ESCALATED to High** (my H3), and Codex's framing understates it: `cmd_add` tracebacks on **both** interpreters, not only 3.12. |
| M5 — no regression test of `cmd_add`'s create path | **CONFIRMED and ESCALATED to High** (my H4): no manifest entry targets that path either, so the sweep is blind too, not just the suite. |
| M6 — wrapper failure reporting | **CONFIRMED at Medium, diagnosis corrected** (my M6): the 10 MB stall is the wrapper's own `${out//[[:space:]]/}`, which is super-linear (4 MB -> 17s, vs 0s for `[[ =~ ]]`), not the buffering. |
| L1 — #284 proposes an existing safeguard | **CONFIRMED and ESCALATED to Medium** (my M4), with the reason the existing clause cannot fire: `declared` comes from the narrowed population. |

### Disagreement 1 — M3 (`PARKED_DONE`) is not clearly a new wrong answer, and the third state Codex proposes is the one already shipped

Codex argues that describing every fully-ticked paused plan as waiting on unseen work is a new false
claim, and asks for a third verdict — *unconfirmed*. Reading the shipped message, that is what it
already is:

> ⚠ every step … is ticked AND the plan is PAUSED … **Whether the job is DONE cannot be read from the
> checkboxes** … Waiting on: <reason> … -> if that has finished: `--finish` … -> if it has not: leave
> the sentinel alone

The sentence Codex objects to (*"a pause means it is waiting on something they cannot see"*) is a
statement about what `paused:` MEANS, not an assertion that the external work is unfinished; the
verdict it reaches is explicitly *cannot be read*, and it offers both branches with the reader
deciding. For Codex's own counterexample — `paused: hand back to human`, every box ticked — a reader
is asked "has the handback finished?", which is the right question to ask someone who has just
started a session. I agree the first clause could be phrased better and that an explicit handoff
state would classify it rather than asking; I do not agree the fold substituted one unjustified
completion claim for another, because the only verdict asserted is "unconfirmed".

Not filed. If the author disagrees with me and folds Codex's M3, the thing to avoid is deleting the
`Waiting on:` line — that line is r1 Codex H1's actual remedy.

### Disagreement 2 — Codex's reproduction of the known-open r1 Claude L4 needs its precondition stated

Codex reports `1 of 4, 1 of 4, 2 of 4, 4 of 4` as confirming that indices are never rewritten. On a
plan `begin-plan.py` itself generated, three successive `--add`s give
`1 of 4, 2 of 4, 3 of 4, 4 of 4` — every index correct, because each appended step is written
`**Step {n} of {n}**`. Codex's figures only appear when the pre-existing labels are **already**
wrong:

    before: - [ ] **Step 1 of 3** — a / **Step 1 of 3** — b / **Step 2 of 3** — c
    after:  - [ ] **Step 1 of 4** — a / **Step 1 of 4** — b / **Step 2 of 4** — c / **Step 4 of 4** — x

So L4 is real and correctly disclosed, but it is reachable only on a hand-edited or hand-written
plan, not as a consequence of appending. That bound belongs in the disclosure; neither half had it.
Not a finding — L4 is on the known-open list.

### Disagreement 3 — the guard population

Codex reports *"53 discovered, 53 RAN, zero nonzero exits"* and treats that as broader coverage of
the commit's 48. My filesystem sweep is 67 and finds a red (`subject_status.py`, 16/17 on both
interpreters). I do not think Codex's run was wrong; I think its discovery rule — *runnable unique
single-line Python commands* — inherits the same defect as the commit's grep: it enumerates
INVOCATIONS, and `CLAUDE.md` records that the population is the FILESYSTEM, measured, after
CI-step discovery saw 14 of 24. Neither half's number should be read as "the guards are green".
