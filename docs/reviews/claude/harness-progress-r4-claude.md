# Round 4 — Claude adversarial review of `c3d53a70`

**STATUS: COMPLETE.**

## Proof of subject

```
$ git log --oneline origin/master..HEAD
c3d53a70 Round 3: the want was not the only thing deriving from its subject
5e4bd163 Round 2: a guard whose want moves with its subject has no ceiling
b64b4cbc Round 1: inject the reporter, instead of emitting progress
915dfa67 File the review round for the progress change — both halves NOT CONVERGED
7ae516fc The mutation harness says where it is, instead of going silent for minutes

$ git show --stat c3d53a70
commit c3d53a7087a33a4a7ba2476a781895aa010ef3ec
Author: Kujin Lee <kujinlee@gmail.com>
Date:   Fri Sep 11 04:22:07 2026 -0700

    Round 3: the want was not the only thing deriving from its subject

 docs/dashboard-entries.md                          |  28 +-
 docs/reviews/claude/harness-progress-r3-claude.md  | 653 +++++++++++++++++++++
 .../coordinator/harness-progress-r3-codex.md       |  93 +++
 .../harness-progress-r3-codex.verdict.json         |  16 +
 scripts/check-plan-code.py                         | 221 +++++--
 scripts/mutations/check-plan-code.json             | 110 +++-
 6 files changed, 1069 insertions(+), 52 deletions(-)

$ git rev-parse HEAD
c3d53a7087a33a4a7ba2476a781895aa010ef3ec
$ git status --porcelain     # (empty — clean tree)
```

## Method — the control, proved green FIRST

`HARNESS_TREE` staged under a redirected `$HOME` (`scripts` copied; `supabase`, `docs`,
`node_modules/typescript`, `.claude/hooks` symlinked — a scripts-only tree gives a red control):

```
$ cd <staged tree> && HOME=<fakehome> python3 scripts/check-plan-code.py --self-test
121/121 passed                                   # matches the commit's claim
$ python3 scripts/check-plan-code.py --self-test  # in the repo itself
121/121 passed                                    real 0m3.197s
```

**The attribution rule is the shipped one, not a stand-in.** The probe imports
`scripts/check-plan-code.py` and calls its own `run_mutations(tree, muts, known)`, so the anchor
uniqueness check, the suite run, `parse_fail_names`, and the `unnamed` *exactly-one-red-case*
rule (`check-plan-code.py:1124-1125`, `w == f`) are the production code. Every probe run
re-proves the control green first and aborts if it is not:

```
CONTROL scripts/check-plan-code.py: rc=0 green=True tail='121/121 passed'
```

---

## Verdict: **NOT CONVERGED**

One Blocking, one High, two Mediums, four Lows. Every one of them is in subsystem **(b)** — the
diagnostic/evidence machinery. **Subsystem (a), the progress feature, survived every attack I
made on it** (six boundary mutations, all killed via a named case). The detailed answer to the
⭐ question is at the end, and it does **not** simply endorse the author's framing.

---

## ⛔ BLOCKING 1 — `diagnostic_tail`'s split point has no lower bound a case can see, and at one end of the surviving range a REAL suite loses the traceback the function was written to preserve

**`scripts/check-plan-code.py:415`** — `half = window // 2`

The whole content of the H1 fix is the sentence *"each stream is guaranteed half the window."*
Nothing in the suite asserts the *half*. Measured over a green control, mutating only that line:

| `half` | suite | | `half` | suite |
|---|---|---|---|---|
| 0 | **RED** | | 199 | 121/121 **green — survived** |
| 1 | **RED** | | 201 | 121/121 **green — survived** |
| 5 | **RED** | | 250 | 121/121 **green — survived** |
| 10 | **RED** | | 300 | 121/121 **green — survived** |
| 20 | **RED** | | 350 | 121/121 **green — survived** |
| **50** | **121/121 green — survived** | | 399 | **RED** |
| 100 / 133 / 150 | green — survived | | 400 | **RED** |

`window // 2` is 200. **The suite pins it to the open range 20 < half < 399.** A seventeen-fold
band, and the declared value is not distinguishable from any other point in it.

### That is not a theoretical gap — one end of the band IS the defect r1 F7 and r3 H1 exist to fix

Driven against a **real** suite, not a fixture: `scripts/check-paid-caller-arrival.py` (the one the
commit message itself cites at 16,701 B of stdout — **confirmed, measured: 16,701 B, stderr 0 B on a
green run**), patched to crash after printing, exactly the 28-of-38 shape the fix is for:

```
rc 1   stdout 16,701 B   stderr 450 B
stderr tail: "...RuntimeError: the tree went bad underneath: node_modules/typescript vanished mid-run"

  half= 50  err_keep= 50  out_keep=350   RuntimeError named in tail: False   message in tail: False
  half=100  err_keep=100  out_keep=300   RuntimeError named in tail: True    message in tail: True
  half=200  err_keep=200  out_keep=200   RuntimeError named in tail: True    message in tail: True
  half=350  err_keep=350  out_keep= 50   stdout gets 50 chars: ' RUN, not dormant\n\n32 of 32 self-test cases passed'
```

At `half = 50` — **a value the suite passes 121/121 at** — the CANNOT RUN report for a real control
crash shows 50 characters of stack frames and **neither the exception type nor its message**. That is
verbatim the harm the r2→r3 argument was about, reachable by a one-token edit, with zero cases able
to fail for it. At `half = 350` — also green — stdout is cut to 50 characters, which is shorter than
most `[FAIL] <case name>` lines in this repo, i.e. the *other* half of the same harm.

### Why the guarding case cannot see it — and this is the SAME class as r3 B1, in the code that fixed r3 B1

`check-plan-code.py:2521-2531`, the case written for exactly this hazard:

```python
(_wdp / "late.py").write_text( ... 'print("S" * 800)\n'
    '    raise RuntimeError("the tree went bad underneath")\n' ... )
_ltail = diagnostic_tail(_lso, _lse)
case("a suite that crashes AFTER 800 B of stdout still shows its traceback",
     (_lrc, "the tree went bad underneath" in _ltail), (1, True))
```

The fixture's exception line is `RuntimeError: the tree went bad underneath` — **41 characters**.
A real one is **84**. So the case proves `half ≳ 41` and the real corpus needs `half ≳ 84`. The
input is not at the boundary; it is an order of magnitude inside it, on the safe side.

r3's own commit message states the lesson it did not then apply to its own new function:

> *"A want that cannot disagree and an input that cannot locate the edge are two different ways for
> a case to assert nothing. Cases now sit AT the boundary."*

They sit at the boundary **for `progress_line`** — where the fix was — and nowhere near it for
`diagnostic_tail`, which is the code that fix introduced. **Fourth consecutive round whose Blocking
is the previous round's fix, and the ninth instance of the class.**

### What would fix it

A case at the boundary, with a literal want, on the thing the parameter decides: assert
`len(diagnostic_tail("S"*5000, "E"*5000).split("\n")[0]) == 200` (the stderr half is exactly
`window // 2` when both streams flood) — a literal, no `half` on the right-hand side, killed by
every value in the band above. Plus a manifest entry naming it.

*(Measured, for the `half = 350` end: across all 1,589 `case(...)` names in `scripts/*.py`, the bare
`  [FAIL] <name>: got ` prefix alone has a median of 63 characters and exceeds 50 in **1,164 of
1,589** cases. A 50-character stdout budget cannot show one.)*

---

## ⚠ HIGH 1 — the AFTER-control diagnostic got the fix and neither a case nor a manifest entry; the identical BEFORE-control site got both

**`scripts/check-plan-code.py:993`** vs **`:960`**. This commit changed `out[-400:]` →
`diagnostic_tail(so, se)` at **two** sites. It added a case and a manifest entry for the first:

```
entry: "the before-control diagnostic goes back to slicing one merged string…"
       anchor: 30-space-indented  f"CHECKED.\n    {diagnostic_tail(so, se)}")
       expect: ["a CANNOT RUN report says WHY the control died, not just that it did"]
```

Measured — the same reversion applied to the **after**-control site (`:993`, 20-space indent, so the
anchors do not collide):

```
caught=False attributed=False  C1 the AFTER-control diagnostic goes back to slicing one merged string
    red cases: []
REPORT: mutation SURVIVED — C1 …: the suite stayed green, so no case can fail for what it names
```

**The branch is already driven.** `:2104-2119` builds a `thing.py` that poisons itself on its third
run so only the after-control goes red, and the case asserts only the head sentence
(`"no longer green AFTER the sequence" in r`) — never the diagnostic the commit just rewrote. The
fixture already prints to stdout, so the fix is one added clause on an existing case plus one entry;
no new fixture is needed.

This is the repo's own recurring shape — *after fixing, SEARCH for the class*. The class here is two
lines, in the same function, in the same diff hunk.

---

## ⚠ MEDIUM 1 — the ceiling case has a character of slack, and the separator rides in it

**`scripts/check-plan-code.py:418-419`**, and the case at `:2543-2545`:

```python
case("...and the window never exceeds its budget, however much is offered",
     len(diagnostic_tail("S" * 5000, "E" * 5000)) <= 401, True)
```

`401` is `window` + 1 for the join. With `"\n".join` → `""` the result is exactly 400, which
satisfies `<= 401`, and nothing else looks at the separator:

```
caught=False attributed=False  D5 the two kept halves are joined with no separator, fusing two lines into one
```

Harm: the last line of the stderr tail and the first line of the stdout tail are fused into one
line in every CANNOT RUN report. On the real fixture above that reads
`…vanished mid-run  ✓ an empty ledger is CANNOT RUN…` — two different streams presented as one
sentence, in the report a reader consults precisely when they cannot trust anything.

The `<=` is also the shape r3's own B1 objected to: an inequality with slack asserts a half-space,
not a value. `== 401` for the both-flooded input is a literal and is exactly as easy to write.

---

## ⚠ MEDIUM 2 — `.strip()` on the two streams is unpinned

**`scripts/check-plan-code.py:414`** — `out, err = stdout.strip(), stderr.strip()`. Measured:

```
caught=False attributed=False  D4 the streams are no longer stripped   (out, err = stdout, stderr)
```

It survives because every case's fixture is either stripped-equivalent or long enough that the
trailing newline is inside the window anyway. The live effect is that trailing whitespace is charged
against a 400-character budget and the `if p` filter stops discarding a whitespace-only stream — a
stderr of `"\n"` becomes a blank first line. Small, but it is a behaviour this commit chose, with
no case that can fail for it.

---

## LOW 1 — two clauses whose branches are observationally identical for every input

**`scripts/check-plan-code.py:418-419`** — `err[-err_keep:] if err_keep else ""`, and the same for
`out_keep`. Both survive:

```
caught=False attributed=False  D2 the err_keep==0 guard is removed
caught=False attributed=False  D3 the out_keep==0 guard is removed
```

They survive because they cannot matter. `err_keep == 0` requires `len(err) == 0` (the other factor
is `max(half, …) ≥ half = 200 > 0`), and `err[-0:]` over an empty string is `""` either way; `out_keep == 0`
likewise requires `len(out) == 0`. The guards protect against the `s[-0:] == s` footgun in a world
where the keep count can be zero while the string is not — which this arithmetic cannot produce.

Worth stating only because the file argues the rule against itself, two hundred lines away
(`progress_line`'s docstring, `:1268`): *"a clause no input can reach is a clause no case can kill."*

## LOW 2 — one of the eight new cases has no manifest entry, and it is the one holding the upper bound

New cases: **8**. New manifest entries for this file: **7** (50 → 57). The unmatched one is
**"a flooded stderr cannot evict stdout's failure from the window"** (`:2536-2538`) — no entry's
`expect` names it. It is the only case that fails when `half` is pushed toward `window`
(measured: `half = 399` and `half = 400` are the two RED rows in the Blocking's table), so the single
bound the suite *does* place on that parameter is held by a case that nothing in CI mutates. It is
protected only by the self-test count ratchet, which — in this file's own words — *"sees the number
move rather than the coverage leave."*

## LOW 3 — `merged_output`'s order is a contract only one of its three callers needs

Measured, both survive:

```
caught=False attributed=False  C3 run_suite merges its halves in the wrong order at the CALL SITE
        (`:461`  return rc, merged_output(out, err)  ->  merged_output(err, out))
caught=False attributed=False  C4 the re-control loop stops merging stderr in
        (`:983`  out = merged_output(so, se)  ->  out = so.strip())
```

Neither is a live harm and I am not asking for a fix: `run_suite`'s merged string is consumed only
by `parse_fail_names` (splits every line) and `control_is_green` (`"passed" in out`), both
order-blind, and the after-control's `out` only feeds `control_is_green`. The point is diagnostic:
`merged_output`'s docstring says *"the order decides exactly one live thing: `ev_files[name]['tail']`"*
— and the measurement agrees, which means the one entry pinning that order is killed through
`mutate_delivered`'s call site (`:953`) and says nothing about the other two callers. The
call-site swap at `:953` **is** caught (`C2`, attributed to *"…and the recorded tail is the failure,
not the noise"*), so the live contract is held. This is a shared function carrying a contract that
belongs to one of its callers.

---

## ✅ What I attacked and could NOT break — the progress feature

Every boundary mutation I could construct around `progress_line` dies **via a named case**:

```
caught=True attributed=True  P1 truncation keeps one char too many (max(room-1,0) -> max(room,0))
caught=True attributed=True  P2 truncation drops one char too many (-> max(room-2,0))
caught=True attributed=True  P3 room computed one wider (PROGRESS_WIDTH - len(head) + 1)
caught=True attributed=True  P4 PROGRESS_WIDTH 79 -> 80
caught=True attributed=True  P5 PROGRESS_WIDTH 79 -> 78
caught=True                  P6 the head gains a second space   (killed by 6 cases)
```

The brief asked whether the r3 B1 fix is the ninth instance — whether there is a **third** way those
cases fail to constrain. **I could not find one.** The two new cases sit at `room` and `room + 1`
with literal wants, and they, not the old `"x" * 300` case, are what kills P1–P5. B1's fix is sound.
The ninth instance is real, but it is in `diagnostic_tail`, not here.

### And the design itself survived — this is a coverage defect, not an arithmetic one

I tried to break `diagnostic_tail`'s arithmetic over 250 combinations (`len(stdout)`, `len(stderr)` ∈
{0, 1, 2, 199, 200, 201, 399, 400, 401, 5000} × `window` ∈ {400, 401, 1, 2, 3}), asserting three
properties: *never longer than `window` + 1*, *never empty when either stream has content*, and
*neither stream evicted when both fit in their own half*.

```
violations: []   total 0
stderr exactly 199 -> err part 199, total 401
stderr exactly 200 -> err part 200, total 401
stderr exactly 201 -> err part 200, total 401   (capped at half, as designed)
```

So the answers to the brief's item 2 are: it **cannot** return more than `window + 1`; it **cannot**
return nothing when there is output; `.strip()` loses nothing that mattered (see MEDIUM 2 for what it
*does* decide). **Every finding above is about what the suite can see, not about what the code does.**
That distinction is what decides the ⭐ question below.

## ✅ Brief item 4 — the monkeypatch repoint is sound. Verified by measurement, not by reading

The concern was that `_real_run_suite` now stubs `run_suite_parts` and returns a 3-tuple, so the
timeout path might be bypassed rather than exercised. It is not. Over a green control:

```
caught=True  attributed=True   T1 the stub times out the BEFORE-control instead of the mutation
    red: ['a TIMED-OUT mutation is counted but is NOT a verdict',
          '...and it is reported as a cannot-run, not as a catch']
caught=True  attributed=False  T2 the stub times out the AFTER-control instead of the mutation
    red: ['...and it is reported as a cannot-run, not as a catch']
caught=True  attributed=True   T3 run_mutations stops recognising rc 2 as a cannot-run (`:1079` rc==2 -> rc==99)
    red: ['a TIMED-OUT mutation is counted but is NOT a verdict',
          '...and it is reported as a cannot-run, not as a catch']
```

T3 is the decisive one: the production `if rc == 2` branch at `:1079` is genuinely reached through
the repointed stub, so the path is exercised, not routed around. The call index is also still
located — moving the timeout to either neighbouring phase goes red.

*One honest detail:* under T2 the case **named** for the mutation phase stays green; it is the
sibling (*"…and it is reported as a cannot-run, not as a catch"*) that fails. So the pair locates the
phase and neither case does alone. Not a finding — the pair is what the manifest entry for this
behaviour relies on — but worth recording, because it is the same *shape* as BLOCKING 1 and it is
benign here only by luck of a second case existing.

A fourth probe, the stub returning its message on stdout rather than stderr, **survives** — correctly:
`merged_output` concatenates both, so the two are the same string. Not a finding.

## ✅ Other things I checked and did not file

- **`ev_files[...]["tail"]` is genuinely read from production now** (r3 H2's fix holds). Swapping the
  merge arguments at the real call site (`:953`, `merged_output(so, se)` → `merged_output(se, so)`)
  is **caught and attributed** to *"…and the recorded tail is the failure, not the noise"*. That case
  reads `_evT.files["scripts/thing.py"]["tail"]`, not a recomputation. r3 H2 is properly fixed.
- **The `merged_output` consolidation is real.** `grep` finds no fourth copy of the merge rule;
  `run_suite` (`:461`), the before-control (`:953`) and the re-control (`:983`) are the three callers,
  all going through it.
- **Case/entry accounting is consistent.** Extracted `case(...)` literals: base `5e4bd163` = 109,
  head = 116 (some cases are built in loops, hence 121 at runtime); 8 added, 1 removed, +7 → 114 → 121 ✓.
  Manifest for this file: 50 → 57 = +7 ✓. `sum(EXPECTED_MUTATIONS.values())` = 452 ✓.
  The 8-added / 7-entry gap is LOW 2 above.
- **The commit's cited corpus number is true.** `scripts/check-paid-caller-arrival.py --self-test`
  on a green run: **stdout 16,701 B, stderr 0 B** — measured, matches the commit message exactly.
- **Brief item 5, recomputation.** Six of this commit's cases call `diagnostic_tail` themselves
  rather than reading a production string (`:2509`, `:2529`, and the pure quartet at
  `:2538`, `:2541`, `:2545`, `:2549`). That is legitimate for a pure function — but it means the
  *production* diagnostic is
  asserted by exactly one case, for one of its two call sites. That is HIGH 1, filed there rather
  than twice.

## LOW 4 — a comment states the merge order backwards and names a code path this commit deleted

**`scripts/check-plan-code.py:1912-1914`**, inside the block explaining the reporter seam:

```
        #   * `run_suite` returns `(stdout + stderr)`, and every CANNOT RUN message prints
        #     `out[-400:]`. 542 B of progress pushes the `[FAIL]` line out of that window
```

Both clauses are now false, and **this commit is what falsified them**. `run_suite` returns
`merged_output(out, err)` = `(stderr + stdout).strip()` (`:439`, `:461`) — the opposite order — and
no CANNOT RUN message prints `out[-400:]` any more; both were changed to `diagnostic_tail(so, se)`
at `:960` and `:993`. The surrounding prose is historical ("`mutate_delivered` USED to call…"), but
these two clauses are in the present tense and read as a description of the code as it stands.

Filed as Low because it costs a reader, not a run — and because the file argues this rule against
itself at `:326-329`: *"a docstring that names dead callers sends the next reader looking for them."*

---

# ⭐ THE SUBSYSTEM QUESTION

> *"My reading is that (a) has been correct since round 1 and every Blocking has been in (b). Say
> whether the evidence supports that."*

**Half of it is supported and half of it is not, and the half that is wrong is the half that would
decide Phase 6.** Enumerated from the four rounds' own filed findings, not from recollection:

| Round | Finding | Subsystem | Behaviour or coverage? |
|---|---|---|---|
| r1 B1 | the nested-run guard cannot fail | **(a)** the `progress=` seam | coverage |
| r1 H1 | the control-failure diagnostic contains none of the failure | **(b)** | behaviour, *caused by* (a) |
| r1 H2 | the two control-loop call sites have no case and no mutation | **(a)** | coverage |
| r1 M1 | label text enters the stream whose substring decides green | (a)→(b) seam | behaviour, latent |
| r1 M2 | the label is unbounded | **(a)** `progress_line` | behaviour |
| r2 B1 | `PROGRESS_WIDTH` has no ceiling; the want moves with its subject | **(a)** `progress_line` | coverage |
| r2 M1 | any child stderr still empties the diagnostic | **(b)** | behaviour |
| r3 B1 | the fits/truncate threshold has no case at its edge | **(a)** `progress_line` | coverage |
| r3 H1 | the stream-order swap re-creates r1 F7 for 28 of 38 suites | **(b)** | behaviour |
| r3 H2 | three cases assert on recomputed copies | **(b)** | coverage |
| **r4 B1** | `half` has no case at its edge | **(b)** `diagnostic_tail` | **coverage** |
| **r4 H1** | the after-control diagnostic has no case and no entry | **(b)** | **coverage** |

**1 — "Every Blocking has been in (b)" is false. Three of the four Blockings are in (a).**
r1 B1, r2 B1 and r3 B1 are all about subsystem (a): the seam's guard, `progress_line`'s want, and
`progress_line`'s threshold. Only mine is in (b). The commit message asserts the opposite
(*"The feature has been correct since round 1; what keeps bleeding is the diagnostic-window
machinery underneath it"*), and the finding table does not support it.

**2 — But the sentence *underneath* that claim is true, and it is a different sentence.** (a)'s
shipped **behaviour** has been correct since r1 M2 was fixed, and I confirm it independently: six
boundary mutations on `progress_line`, every one killed via a named case, plus the live evidence in
the `--mutate .` run going on beside this review — `[1/452] … [452/452]`, every line one row. What
kept failing in (a) was its **coverage**. The right sentence is *"(a)'s behaviour has been right
throughout; three Blockings were its guards failing to be able to say so."*

**3 — "(b) predates this branch" is now false, and this matters most.** My Blocking and my High are
both about `diagnostic_tail` and its two call sites — **code this branch created two commits ago, in
`c3d53a70` itself.** The genuinely pre-existing machinery (`out[-400:]`, the single-concatenation
merge) is *gone*: r3 deleted the first and consolidated the second into `merged_output`, and I could
not break either. So "stop patching the old machinery" no longer describes the situation. The
machinery under review **is this branch's own work**, seventy lines old, and its *arithmetic* is
sound (250-combination boundary sweep, zero violations).

## Would I keep patching (b), or redesign it?

**Keep patching — and the patch is cases, not code.** I am applying this project's own test
(`docs/review-method.md:66`, *"Can a redesign remove it?"*):

| Finding | Would a different shape dissolve it? |
|---|---|
| B1 `half` unpinned | **No.** Every budget-splitting design has a split point, and every one needs a case at its edge. Reshape it — interleave the streams, print both tails unbounded, tag each line with its stream — and the same finding reappears against whatever constant the new shape has |
| H1 after-control uncovered | **No.** Two call sites, one covered. That is arithmetic about cases, not about structure |
| M1, M2, L1–L4 | **No.** All of them are "this line has no case that can fail for it" |

By `review-method.md:248`, the **thrashing** tell is present — each round's findings are introduced
by the previous round's fix, four times running, and the stop condition at `:45` says two consecutive
rounds escalates to REDESIGN. **I am arguing against firing it here, and here is the evidence:**

> **The defect follows the author, not the module.** r2 B1, r3 B1 and r4 B1 are the *same* defect in
> *three different functions* — a guard whose fixture sits far inside the boundary it claims to pin.
> Two of those functions are in (a) and one is in (b). A component-level redesign of (b) cannot
> remove a defect that has already appeared in two components; it would relocate it into the third.

That is a **method** defect, and Phase 6 (architecture review) is not the instrument for it. What is:

1. **Fix the six items.** Roughly five cases and three manifest entries. None touches production
   logic except LOW 4's comment.
2. **Run an exhaustiveness pass over the branch's numeric edges** — the "FIX, plus an exhaustiveness
   pass" arm of `review-method.md:62`. It is a seven-row table and I have filled it in:

   | Constant / comparison introduced or touched by this branch | Case at its boundary, literal want? |
   |---|---|
   | `PROGRESS_WIDTH = 79` (`:1242`) | ✅ two, at `room` and `room + 1` |
   | `if len(label) <= room` (`:1272`) | ✅ both sides, literal wants |
   | `label[:max(room - 1, 0)]` (`:1274`) | ✅ killed by the `len == 79` wants |
   | `DIAGNOSTIC_WINDOW = 400` (`:391`) | ✅ the `== 400` and `<= 401` cases |
   | `max(half, …)` floor (`:416`) | ✅ manifest entry, `max(half,…)` → `max(0,…)` |
   | **`half = window // 2` (`:415`)** | ❌ **BLOCKING 1** — no case in the band 20 < half < 399 |
   | `min(len(err), …)` upper cap (`:416`) | ⚠ one case, and **no manifest entry** — LOW 2 |

3. If a mechanical answer is wanted later, note that `--mutate .` cannot find this class by
   construction: the manifest only ever holds mutations someone thought to write. A generic "±1 and
   ×2 on every integer literal in a pure function" sweep would have caught B1, D1 and D7 in one pass.
   That is a backlog item, not this branch's work, and I am not asking for it here.

**Record of the call, per `review-method.md:280`:** I judge this **thrashing by tell and
branch-coverage by cause.** The count says convene Phase 6; the cause says the shape is fine and
under-specified, and the per-finding evidence for that is the "Would a redesign dissolve it?" table
above. My recommendation is a fifth round scoped to *coverage only*, not an architecture review.
⚠ This is a recommendation, not a decision — arming Phase 6 is the human's call, and the raw trigger
condition (four rounds, no convergence) **is** met.

---

# Brief item 6 — the full `--mutate .`, re-run. The claim is TRUE

```
$ time python3 scripts/check-plan-code.py --mutate .
[1/38] control scripts/brief-compose.py
 …
[452/452] page_markup: a <details> block is emitted without its wrapper
[1/38] re-control scripts/brief-compose.py
 …
OK — delivered scripts mutated: 38 file(s), 452 mutation(s), 452 killed,
     452 attributed to the case each names, 0 survivor(s)

real 6m50.936s    user 4m25.236s    sys 1m59.090s    EXIT=0
```

**452 / 452 / 452 / 0, confirmed independently.** (The commit's `real ~370 s` vs my 411 s is machine
load; `progress_line`'s own docstring is right that a duration in prose is not a stable number, and I
am not filing it.)

## …and the feature itself, measured on that real run

Every progress line from the run above, parsed out of the captured stderr:

```
progress lines: 528                      (= 452 mutations + 38 controls + 38 re-controls)
max length: 79 characters / 79 columns   lines over 79: 0
exactly 79 and truncated (ends "…"): 199
exactly 79 and NOT truncated:          4   <- the r3 B1 threshold, exercised every run
all three phases report: control, mutation, re-control
```

Independent confirmation of the shipped behaviour on live data, and of the claim that the boundary
B1 is about is crossed on a real run. **Subsystem (a) works.**

---

# What the AUTHOR did not measure (brief item 7)

1. **The value of `half`.** The commit measured which *order* was the worse trade (28 of 38, 2 of 38
   — both numbers confirmed) and then chose a split point with no measurement behind it and no case
   able to see it. BLOCKING 1.
2. **Whether a real traceback fits in the budget it was given.** The fixture's exception line is 41
   characters; the one I produced from a real repo suite is 84. Nothing in the round checked a real
   one against the window.
3. **The second call site.** `diagnostic_tail` was put at `:960` and `:993`; only `:960` was covered.
4. **Whether the new cases' *inputs* locate the edges** — which is the r3 B1 lesson, applied to
   `progress_line` and not to the function the same commit created. The two boundary cases the
   commit is proudest of are exactly right; the four written next to them are the old shape.
5. **The `<= 401` slack.** An inequality was chosen where the equality was available and is strictly
   stronger; the separator mutation lives in the one character of difference.

---

# What I did not measure

- **I did not re-run the other 37 files' suites individually.** The full `--mutate .` covers them and
  came back 452/452, but my targeted probes only ever ran `check-plan-code.py`'s own suite; a
  mutation with a cross-file effect would not show up in them.
- **The nested self-test stderr claim (`0 B`) — NOT CHECKED.** The commit asserts it; I did not
  reproduce it. Treat that specific number as unverified by this review.
- **I did not test under a non-UTF-8 stderr** (r3's deliberately-unfixed LOW about `PYTHONIOENCODING=ascii`
  turning `…` into 6 columns). My 79-column measurement above is under the default UTF-8 environment.
- **I did not exercise the `SUITE_TIMEOUT` path against a genuinely hung child** — only through the
  stub. A real 120 s hang was out of budget.
- **My `half` sweep is 15 points, not all 401.** The band edges (20/50 and 350/399) are bracketed to
  within a factor of ~2.5, not to the exact integer. The finding does not depend on the exact edge.
- **Contention caveat, stated rather than hidden:** the four monkeypatch probes (T1–T4) ran while the
  full `--mutate .` was executing. `SUITE_TIMEOUT` is 120 s against a ~3 s suite, so a contention-induced
  timeout is implausible, and all four results are deterministic logic outcomes rather than timings —
  but by this project's own rule a red measured beside a shared load is contamination until re-measured
  alone, so: T1–T4 were **not** re-measured alone. The `half` sweep and the 17-mutation probe both ran
  **before** the full run started.
- **I did not read the Codex half of round 4** — it was not available when I wrote this.

---

# Summary

| # | Severity | Subsystem | Finding | File:line |
|---|---|---|---|---|
| B1 | **Blocking** | (b) | `half` is unpinned across 20 < half < 399; at `half = 50` a real suite's traceback is lost entirely | `check-plan-code.py:415` |
| H1 | **High** | (b) | the after-control diagnostic has neither a case nor a manifest entry; its twin has both | `:993` vs `:960` |
| M1 | Medium | (b) | the ceiling case's `<= 401` slack hides the `"\n"` → `""` separator mutation | `:418-419`, case `:2545` |
| M2 | Medium | (b) | `.strip()` on both streams is unpinned | `:414` |
| L1 | Low | (b) | two clauses whose branches are identical for every reachable input | `:418-419` |
| L2 | Low | (b) | 8 new cases, 7 new entries; the unmatched one holds the only upper bound on `half` | case `:2538` |
| L3 | Low | (b) | `merged_output` carries an order contract only one of its three callers needs | `:461`, `:983` |
| L4 | Low | (b) | a comment states the merge order backwards and names a path this commit deleted | `:1912-1914` |

**Verdict: NOT CONVERGED.** Subsystem (a) is done — I attacked it and could not break it, and the
live run confirms it. Everything outstanding is subsystem (b), all of it coverage rather than
behaviour, and the arithmetic under it survived a 250-combination boundary sweep. The fix is
roughly five cases and three manifest entries.

**Recommendation:** a fifth round scoped to coverage, not a Phase 6 architecture review — reasoning
and the per-finding "would a redesign dissolve it?" evidence recorded above. The raw four-round
trigger **is** met, so arming Phase 6 anyway is a legitimate call and it is the human's to make.
