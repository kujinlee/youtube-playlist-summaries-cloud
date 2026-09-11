# harness-progress-output — round 2, Claude half

**Verdict: NOT CONVERGED.** One Blocking, one Medium, two Low. Everything the commit *claims* it
measured, I re-measured independently and it holds — including 48/48 mutations red via the case each
names. The Blocking is a new defect introduced by this commit's own M2 fix, and it is the same
shape as the B1 this commit exists to close.

## Proof of subject

```
$ git rev-parse --abbrev-ref HEAD
harness-progress-output

$ git rev-parse origin/master
f6c03fd87ad652437ef262b3e67e2cc16c92c3d0

$ git log --oneline origin/master..HEAD
b64b4cbc Round 1: inject the reporter, instead of emitting progress
915dfa67 File the review round for the progress change — both halves NOT CONVERGED
7ae516fc The mutation harness says where it is, instead of going silent for minutes

$ git show --stat b64b4cbc
commit b64b4cbcd9d7aeb38af2c2788c74466d83a5fc49
Author: Kujin Lee <kujinlee@gmail.com>
Date:   Fri Sep 11 03:15:25 2026 -0700

    Round 1: inject the reporter, instead of emitting progress
    [full message as committed]

 docs/dashboard-entries.md              |  50 +++++++--
 scripts/check-plan-code.py             | 183 +++++++++++++++++++++++++++++----
 scripts/mutations/check-plan-code.json | 121 +++++++++++++++++++++-
 3 files changed, 320 insertions(+), 34 deletions(-)
```

## The bench, and the control

All measurements below were taken in a staged tree outside the repo, under a redirected `$HOME`,
with the full `HARNESS_TREE` present (`scripts` **copied**; `supabase`, `docs`,
`node_modules/typescript`, `.claude` symlinked from the repo). Nothing in the repo was modified.

**Control, proved green before any mutation:**

```
$ cd <bench>/tree && HOME=<bench>/fakehome python3 scripts/check-plan-code.py --self-test
111/111 passed          rc=0        stderr: 0 bytes
```

The control was re-proved green after every mutation block below.

---

## Blocking

### B1 — `PROGRESS_WIDTH` has no ceiling. Raising it to 200 restores M2's defect in full and the suite stays 111/111.

`scripts/check-plan-code.py:1180` is the whole of M2's fix:

```python
PROGRESS_WIDTH = 79
```

and `:2363-2366` is the case that claims to pin it:

```python
_pl_long = progress_line(164, 434, "x" * 300)
case("a label too long for one row is truncated, and says so",
     (len(_pl_long), _pl_long[-1], _pl_long.startswith("[164/434] ")),
     (PROGRESS_WIDTH, "…", True))
```

**The expected value is derived from the subject.** `len(_pl_long)` is a function of
`PROGRESS_WIDTH`, and the want is `PROGRESS_WIDTH`. Both sides move together, so the case asserts
*"the result is as wide as the constant says"* — which is true for every value of the constant that
truncates at all. It never asserts the property M2 was filed for: **that the line fits one row.**

**Measured, over the green control above,** editing only `PROGRESS_WIDTH = 79`:

| `PROGRESS_WIDTH` | suite |
|---|---|
| **200** | **111/111 passed** |
| **120** | **111/111 passed** |
| **100** | **111/111 passed** |
| **90** | **111/111 passed** |
| **80** | **111/111 passed** |
| 40 | 110/111 passed |
| 20 | 109/111 passed |
| 79 (restored) | 111/111 passed |

The guard has a **floor and no ceiling** — and the ceiling is the entire point. At 200 a progress
line is 200 characters, which is the state r1 M2 measured and filed:

> "at 80 columns one update wrapped to three rows, destroying the one property the feature exists for"

so the defect is restored exactly, with every case green.

**And there is no manifest entry for the constant.** `grep -rn PROGRESS_WIDTH` over the repo returns
three hits in code — `:1180` (the definition), `:1209` (`room = PROGRESS_WIDTH - len(head)`), and
`:2366` (the self-referential want) — and **zero** in `scripts/mutations/check-plan-code.json`. The
nine new entries mutate the *shape* of the truncation (the head, the truncating return, the fits
branch) and none of them touches the *number*.

**Why this is Blocking rather than Medium.** It is this commit's own stated tell, applied to this
commit:

> "THE TELL, which is worth more than the fix: the commit added FOUR cases and THREE mutations.
> A case you cannot write a mutation for is usually one that no production edit can reach.
> **COUNT CASES AGAINST ENTRIES.**"

Here the count balances (2 truncation cases, 2 truncation entries) and the defect is one level in:
the entries cover the branch structure, the *threshold* is guarded only by a case that cannot
disagree with it. This is the seventh instance on this line of work of a guard whose existence is
cased and whose content is not — and, per the brief's own fear, it is a Blocking introduced by the
previous round's fix.

**Failing scenario.** Someone widens the constant (a terminal-width tweak, a merge, a "labels get
cut too aggressively" complaint). CI stays green, `--mutate .` goes back to wrapping, and the one
property the feature exists for — a single line that visibly stops advancing — is gone with no
signal anywhere.

**What would fix it.** Assert the property, not the mechanism: a literal (`len(_pl_long) == 79`, or
`PROGRESS_WIDTH <= 79` as its own case) plus a manifest entry that widens the constant and dies via
the named case. The `…` and `startswith` clauses of the existing case are fine and should stay.

---

## Medium

### M1 — H1 was fixed at the emitter, not at the mechanism. Any child stderr still empties the diagnostic, and it also overwrites the recorded tail.

`run_suite:401` returns `(r.stdout + r.stderr).strip()` — **stderr last** — and both CANNOT RUN
messages print `out[-400:]` (`:899` in the before-control loop, `:931` in the after-control loop).
Because stderr is concatenated *after* stdout, any stderr byte from a child suite takes the tail
window first.

The commit removed today's 542 B of progress and I confirm it: the suite's own stderr is now
**0 bytes** (measured above). But nothing changed at `:401`, `:899` or `:931`, and **no case asserts
the property those two diagnostics depend on** — that a suite writes nothing to its own stderr. The
two new silence cases assert it of `mutate_delivered` (`:1877`) and `run_mutations` (`:2404`), which
are call-path assertions about *this* program, not about the child whose output the window shows.

**Measured**, driving `mutate_delivered` against a mini root whose suite is red, with and without a
child that writes 600 B to stderr:

```
--- child stderr = 0 B ---
  [FAIL] visible in the out[-400:] diagnostic: True
  recorded ev tail: '[FAIL] value is one: got 99'
--- child stderr = 600 B ---
  [FAIL] visible in the out[-400:] diagnostic: False
  recorded ev tail: 'NNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN'
```

Two consequences, and the second is not in r1's finding at all:

1. the `out[-400:]` window contains none of the failure — H1's exact harm, reproduced at will;
2. `ev_files[name]["tail"] = out.split("\n")[-1]` (`:893`) records the child's **last stderr line**
   as the file's tail, so the durable evidence object also loses the failure. r1 listed
   `ev_files["tail"]` under *not measured* and the fix did not reach it either.

This is instance-not-class: the emitter that caused it is gone, the converter that makes any future
emitter cause it again is untouched and unguarded. A structural fix is small — order the window
stdout-last, or take the tail of stdout specifically — and it would make the class impossible
rather than the instance absent.

I am filing this Medium, not Blocking: no live emitter exists today, so nothing is currently broken.

---

## Low

### L1 — the flush clause's stated justification is now reachable only from its own test.

`stderr_progress`'s docstring (`:1215-1230`) correctly retracts the false "a pipe buffers this into
oblivion" claim, and the replacement is measured and true:

> "`flush` is what makes this visible BEFORE exit when `sys.stderr` has been **REPLACED** with a
> block-buffered stream […] `redirect_stderr(open(p,"w"))` gives a TextIOWrapper over an 8 KiB
> BufferedWriter […] **That is the case below, and it is why the clause stays.**"

I verified both directions: manifest entry 48 (`flush is dropped from the progress write`) goes red
via `a progress line reaches a block-buffered stream before the process exits`, over a green
control, with **zero** collateral failures. So the case is real and the clause is load-bearing *for
that case*.

The gap is that **nothing in production replaces `sys.stderr`**. `grep -n "redirect_stderr"
scripts/check-plan-code.py` puts every occurrence inside `_self_test`; the real `--mutate` path
writes to the process's own `sys.stderr`, which r1 measured as line-buffered piped or captured. So
the sentence "it is why the clause stays" names a reason that only the test creates. That sits
awkwardly beside the same commit's rule, applied four lines away at `:1203-1205` to justify *not*
adding the no-room branch:

> "a clause no input can reach is a clause no case can kill."

Keeping `flush=True` is right and I would keep it — it costs nothing and is correct defensively. The
fix is one clause of prose: say that no production path in this repo replaces the stream, so the
flush is belt-and-braces rather than a live requirement. The r1 L1 defect was *stating an unmeasured
mechanism as the reason*; the mechanism is now measured, but its relevance to any real caller is
still asserted rather than shown.

### L2 — `:2060` records a grep result that was already false before this commit, and this commit adds a fourth hit.

```
# entry measured). `grep -n 'main(["--mutate"'` returned exactly one hit, and r5 showed
```

Measured on each commit:

| commit | hits of `main(["--mutate"` |
|---|---|
| `f6c03fd8` (master) | 3 |
| `7ae516fc` | 3 |
| `b64b4cbc` | 4 |

Pre-existing — the sentence is past tense and records what r5 found, so it is history rather than a
claim about today, and it is not this commit's defect. But it reads as a present-tense inventory to
the next person, and the new driver at `:1886` is precisely the kind of thing that inventory was
counting. Worth a `⟳` noting the count has moved, in line with the project's own rule that a manual
measurement records which build it was taken against.

---

## What I verified and found NOT to be findings

**All 48 manifest entries for this file kill via the case each names, over a green control.** I did
not use `mutate_delivered` for this — the harness is part of the subject — but re-implemented the
apply/run/parse loop independently and recorded *every* failing case name per mutation
(2m30s, staged tree, redirected `$HOME`). Result: **48/48 KILL-VIA-NAMED, 0 misses, 0 ambiguous
anchors.** That confirms the commit's 9/9 claim and, importantly, that no *pre-existing* entry was
orphaned by the refactor.

**The retarget (entry 39) is honest and tests the same property.** Its anchor moved from
`return f"[{done}/{total}] {label}"` to `head = f"[{done}/{total}] "`, and it still dies via
`a progress line states position, not just motion`. I confirmed the anchor resolves exactly once
(`grep -cF` → 1). It fails 5 other cases collaterally, which the harness permits (`expect` is a
subset requirement, `:1056-1062`) and which is honest here: `progress_line` genuinely feeds all of
them.

**Every one of the six new cases is killed by at least one entry**, so B1's shape does not recur at
the case level:

| new case | killed by entry |
|---|---|
| `every phase of --mutate reports its position when a caller asks` | 41, 43, 44 |
| `...and the whole path is silent when nobody asked` | 42 |
| `--mutate itself supplies the reporter, so a real run is not silent` | 45 |
| `a label too long for one row is truncated, and says so` | 46 |
| `...and a label that already fits is left exactly alone` | 47 |
| `a progress line reaches a block-buffered stream before the process exits` | 48 |
| `...and says NOTHING when no caller asked` (rewritten, was `assert [] == []`) | 40 |

**The H2-one-level-up case is genuinely falsifiable.** Entry 45 applies exactly the deletion the
brief worried about — `mutate_delivered(mroot, progress=stderr_progress)` → `mutate_delivered(mroot)`
at `:2586` — and it dies via `--mutate itself supplies the reporter, so a real run is not silent`
with **zero** collateral failures. That is the cleanest kill in the set: it is the only case that
sees it. It is not the new B1.

**The real user still gets all three phases.** A real CLI `--mutate .` in the staged tree, stderr to
a file: 38 `[n/38] control …` lines during the control phase, then `[n/443]` mutation lines. Progress
is live and stdout stays clean. (Full-run completion is reported at the end of this document.)

**Truncation cannot make two updates report the same line.** The brief asked. Two labels sharing a
72-char prefix *do* truncate identically — I constructed a pair — but the position differs for every
update within a phase (`enumerate(targets, 1)` / per-mutation index), so the full progress line is
always distinct. Across the 443 live manifest names at a fixed position, **0 pairs collide** anyway.
Non-issue; stated so it is not re-asked.

**`max(room - 1, 0)` is right at the boundaries.** Walked with `head = "[1/1] "`, `room = 73`:

| label chars | result chars | bytes | ends |
|---|---|---|---|
| 72 | 78 | 78 | `zzz` |
| 73 | 79 | 79 | `zzz` |
| 74 | 79 | 81 | `zz…` |
| 75 | 79 | 81 | `zz…` |

Monotone, never exceeds 79 characters, the position is always intact. The `…` costs 2 characters of
label at the crossover, which is standard.

**The `…` is multi-byte but that is the right unit.** A truncated line is 79 *characters* / 81
*bytes*. Character count is the correct measure for terminal wrapping, and the file already prints
non-ASCII freely. I checked whether any label contains a **double-width** character, which would
make 79 characters exceed 79 columns: 40 of the 443 names are non-ASCII, but every non-ASCII
character in the corpus is `—` (Ambiguous), `⟳` or `⚠` (Neutral) — **0 names contain a `W`/`F`
character, and 0 live progress lines exceed 79 display columns.** (Instrument sanity-checked:
`east_asian_width` returns `W` for `⭐`, `漢`, `🔥`.) Latent only if someone puts an emoji in a
mutation name, and `—` would count double in a CJK locale. Not filed.

**The declared numbers are all correct.** Verified by reading each commit:

| | master | `7ae516fc` | `b64b4cbc` |
|---|---|---|---|
| `sum(EXPECTED_MUTATIONS.values())` | 431 | 434 | 443 |
| declared self-test cases | 101 | 105 | 111 |

and the live manifests hold exactly **443** entries, `check-plan-code.py` exactly **48** (39 + 9).
Longest name 232 chars; 90 names over 100 (r1 measured 81 of 434 — the 9 new names are all over 100,
so 81 + 9 = 90 is consistent). The dashboard entry's `431 → 443` / `101 → 111` are the correct
whole-branch figures.

**Deleting the "merge #288 first" warning is correct.** `origin/master` is
`f6c03fd8 Backlog #106: composing a page twice now produces the same page (#288)` — #288 is merged,
so the stacking note is spent.

**Neighbouring gates are green on this branch:** `check-selftest-counts` (rc 0, 34 scripts, every
declared count verified by running it), `check-docs` (rc 0), `check-ratchet-contract` (rc 0),
`check-dashboard-entry` (rc 0, entry added), `check-review-rounds` (rc 0), `check-anchors` (rc 0),
`check-selftest-counts --self-test` 18/18.

**The brief's Q5 — does discarding stderr in the two nested drivers hide a diagnostic?** Partly, and
it is not worth filing. `:2047` and `:2075` discard a stream that carries `main`'s CANNOT RUN
sentences (`:2576`, `:2582`, `:2639`). If a nested run ever took one of those paths, the case would
still **fail** — `_no_tally`/`_mut_out` assert on stdout and would not see what they expect — so the
failure is detected; only the explanation is harder to reach. The third driver added by this commit
(`:1885`) captures stderr and asserts on it, which is the better pattern. Suggest `_mutate_output`
keep the buffer and print it on mismatch; not a finding.

**Not findings, positively.** The injection seam is the right design and is the correct reading of
r1's seven findings as one root. Asserting the reporter *sequence* rather than a count (`:1860-1866`)
is the right call and the comment says why. Refusing to add a "no room for the position" branch is
correct. The F6 removal of "~25 minutes" and the L2 "of STDOUT" qualification are both right.

---

## What I did not measure

- **I did not review `7ae516fc`** (round 1's subject) or the r1 findings themselves, per the brief.
- **I did not run `--mutate .` for the other 37 scripts' entries** — I ran all 48 for
  `check-plan-code.py`, which is the only file this commit touches. The full-repo run is reported
  below; I did not independently re-verify the other 395 entries' attribution.
- **I did not test a non-UTF-8 locale.** If `sys.stderr`'s encoding cannot represent `…`,
  `stderr_progress` raises `UnicodeEncodeError`. I did not construct that environment. It is not new
  — the script prints `✗`, `⛔` and `⟳` elsewhere — but the `…` is now on a path that runs 510 times
  per invocation rather than once.
- **I did not measure time-to-first-progress under CI log aggregation**, which is where a reader
  most needs it and where buffering behaviour differs from a terminal.
- **I did not attempt an adversarial search of the other 37 scripts** for stderr writers that would
  trigger M1 in a real `--mutate .` run. M1 is demonstrated with a synthetic child, not with a real
  one, and I say so rather than implying the live tree has such a writer — measured, the live suite
  writes 0 bytes.
- **I did not re-derive r1's 542 B figure**; I measured only that it is now 0.

---

## Full-repo `--mutate .` result

Run to completion in the staged tree under the redirected `$HOME`.

**stdout — one line, the verdict, nothing else:**

```
OK — delivered scripts mutated: 38 file(s), 443 mutation(s), 443 killed,
443 attributed to the case each names, 0 survivor(s)
```

**stderr — 519 progress lines, all three phases, in order:**

| phase | lines | expected |
|---|---|---|
| `[n/38] control …` | 38 | 38 |
| `[n/443] <mutation name>` | 443 | 443 |
| `[n/38] re-control …` | 38 | 38 |
| **total** | **519** | 38 + 443 + 38 = 519 |

first line `[1/38] control scripts/begin-plan.py`, last line
`[38/38] re-control scripts/page_markup.py`.

**The M2 bound holds on the real corpus.** Measured over all 519 emitted lines:

```
max CHARACTERS: 79      max COLUMNS: 79      max BYTES: 83
lines > 79 characters: 0        lines > 79 display columns: 0
truncated (ending in …): 190 of 519
```

(83 bytes at 79 characters is `—` and `…` at 3 bytes each; characters and columns are the units
that decide wrapping, and both are at the bound.) So the feature works end to end for a real user,
and B1 is about the bound's *guard*, not about today's behaviour — which is correct.

⚠ One methodological note on that number: `awk 'length($0)>79'` reports **190** lines over 79,
because macOS `awk` counts bytes. The character and column counts above are the ones that decide
whether a terminal wraps, and they are 0.

**Startup silence, not filed.** `load_manifests`, the drift/home-escape scans and `stage_tree`
(which copies `node_modules/typescript`, 23 MB) all run before the first progress line. The window
is seconds, against the ~5 minutes the feature exists to fill. Worth knowing, not worth a finding.

**This run is also independent confirmation that the refactor orphaned nothing**: 443 declared,
443 killed, 443 attributed, 0 survivors — over a tree whose `scripts/` is a byte copy of the branch.
