**REVIEW GAP:** codex — not invoked for this round, by design. Rounds 2+ alternate
(`docs/review-method.md`, Round topology), and Codex authored round 4 — the round whose repair
this reviews.

# backlog #154 — round 5 (Claude half)

Subject: `backlog-154-dash-block-scalar` at `61514c48`, off master `b184bbbc`. PR #331.
Reviewed by reading `scripts/check-python-pin.py` and by running the guard against generated
fixtures whose validity is decided by libyaml (ruby Psych 3.1.0, `/usr/bin/ruby`).

**VERDICT: NOT CONVERGED — 1 Blocking, 1 High, 2 Medium, 1 Low.**

The r4 repair under review is **correct, complete for what it fixes, and properly falsified.** The
refusal now precedes the `pins` computation, every later branch of `verdict()` is behind it, the new
case is a real falsifier that reds by name when the move is reverted, and all five counts re-derive.
I found nothing wrong with it.

The Blocking is the thing round 4 did not look for and this round was asked to: the refusal
**under-fires**. Its predicate is line-local in exactly the way the classifier it protects is
line-local, so a block scalar whose *indicator* sits on a line of its own is invisible to
`_BLOCK_SCALAR` **and** to `_LOOSE_SCALAR`. Twelve valid-YAML spellings, Psych-confirmed, all return
`rc 0 "python pin OK"` over a job with **no `setup-python` step at all** — including the explicit-key
form the refusal was built for, with the indicator pushed one line further down. This is not a
regression from r4; it has been open since the refusal was introduced in r3.

| mandate | answer |
|---|---|
| 1. Is the ordering correct and complete? | **Correct.** Measured: the refusal beats all four later branches. No sibling caller bypasses it — `main()` is the only non-test entry point. One asymmetry found (F3, Medium), not reachable by a schema-valid workflow |
| 2. Is the new case a real falsifier? | **Yes.** Reverted on a temp copy → `99/100`, and the one red is the named case. The mutation kills via that case, though it is a proxy for the move rather than the move (F5, Low) |
| 3. Attack under-firing | **A false green exists, twelve spellings of it** (F1, Blocking) — **and a second, unrelated family my own proposed fix for F1 does not reach** (F2, High) |
| 4. Converged? | **No.** F1 is closable in this PR; F2 is the declared bound coming due and belongs in a row |
| 5. Counts | suite **100**, manifest **47**, `EXPECTED_MUTATIONS` **47**, declared sum **876** over **52** files. Duplicate anchor pair **confirmed inherited** from master, byte-identical anchor |

---

## F1 — Blocking. The refusal cannot see an indicator that is not on the key's line, so the shape it exists to refuse is still a silent false green

`unreadable_scalar_openers` (`scripts/check-python-pin.py:499-517`) refuses a line that
`_LOOSE_SCALAR` matches and `_BLOCK_SCALAR` does not. `_LOOSE_SCALAR` (`:362`) is

    ^\s*(?:-\s+)*[^\n]*?:\s*(?:[&!]\S+\s*)*[|>][-+0-9]*\s*(#.*)?$

— **it requires a colon on the same line as the indicator.** YAML does not. A block scalar header
is a node, and a node may begin on the line after its key:

```yaml
      - name: write a fake workflow
        run:
          |
          uses: actions/setup-python@v5
          with:
            python-version: '9.9'
      - name: real work
        run: python3 --version
```

Psych, on that file:

```text
PSYCH OK
2
"uses: actions/setup-python@v5\nwith:\n  python-version: '9.9'\n"
["name", "run"]
```

Two steps; `run` is a **String**; there is no `setup-python` step anywhere in the job. The guard, on
the same file:

```text
declared_pins: ['9.9']
unreadable_scalar_openers: []
unreadable_jobs: 0
job_names: ['build']
unpinned_jobs: []
VERDICT rc 0
⚠ ADVISORY — this machine runs Python 3.12; CI runs 9.9.
```

`rc 0`, zero refusals, and the "pin" is a line of shell script. This is verbatim the defect the
branch exists to end — `declared_pins` reading a block scalar's body as YAML structure — arriving
through the one door the refusal does not watch.

### It is a class, not a spelling — 12 members, all valid, all false green

Generated differential, Psych as the oracle. Every fixture is the workflow above with the opener
spelling varied; `real_setup_python=false` is Psych's own verdict that the job has no such step.

```text
ctrl  run: |          psych[real_setup_python=false ] refusals=0 pins=[]       -> AGREE (masked)
ctrl  run: >          psych[real_setup_python=false ] refusals=0 pins=[]       -> AGREE (masked)
ctrl  ? run / : |     psych[real_setup_python=false ] refusals=1 pins=['9.9']  -> REFUSED rc=2
N1    run: / |        psych[real_setup_python=false ] refusals=0 pins=['9.9']  -> FALSE GREEN
N2    run: / >-       psych[real_setup_python=false ] refusals=0 pins=['9.9']  -> FALSE GREEN
N3    run: / |+       psych[real_setup_python=false ] refusals=0 pins=['9.9']  -> FALSE GREEN
N4    run: / |2       psych[real_setup_python=false ] refusals=0 pins=['9.9']  -> FALSE GREEN
N5    run: / &a |     psych[real_setup_python=false ] refusals=0 pins=['9.9']  -> FALSE GREEN
N6    run: / !!str |  psych[real_setup_python=false ] refusals=0 pins=['9.9']  -> FALSE GREEN
N7    "run": / |      psych[real_setup_python=false ] refusals=0 pins=['9.9']  -> FALSE GREEN
N8    run: # c / |    psych[real_setup_python=false ] refusals=0 pins=['9.9']  -> FALSE GREEN
N9    ? run / : / |   psych[real_setup_python=false ] refusals=0 pins=['9.9']  -> FALSE GREEN
N10   run: &a / |     psych[real_setup_python=false ] refusals=0 pins=['9.9']  -> FALSE GREEN
N11   run: / | # c    psych[real_setup_python=false ] refusals=0 pins=['9.9']  -> FALSE GREEN
N12   deeper content  psych[real_setup_python=false ] refusals=0 pins=['9.9']  -> FALSE GREEN
```

⭐ **N9 is the one that settles the argument.** The refusal was added *for* the explicit-key form,
and the code's comment at `:341-350` presents that form as the boundary case a line-local matcher
cannot reach. `? run` / `: |` is refused (the `ctrl` row). Write the same thing as `? run` / `:` /
`|` — the value node on the line after the colon, which is what the explicit-key form's own logic
permits — and the refusal is gone. The repair reached one *spelling* of the boundary case, not the
boundary.

### The docstring states the bound in the safe direction only

`:512-514`:

> ⚠ ITS BOUND, stated rather than discovered later: it is line-local too, so a block indicator
> inside a quoted string on one line could trip it. That direction is SAFE — it refuses, and a
> refusal is visible — which is the whole reason this shape of check is allowed to be crude.

Being line-local has **two** consequences and this names only the harmless one. The other is F1: a
line-local predicate cannot see an indicator the key does not share a line with, and that direction
is a silent pass. The file is unusually careful about stating bounds (`_structural:390-394`,
`_steps:212-215`); this is the one place where the bound written down is the one that does not
matter.

### Reachability, stated honestly

`grep -nE '^\s*(\|[-+0-9]*|>[-+0-9]*)\s*(#.*)?$' .github/workflows/*.yml` finds nothing — **no
workflow in this repository uses the shape today, and the live guard returns `rc 0` correctly.** That
is the same sentence backlog #154's own row uses about the dash short form (*"Latent today … and that
is precisely why it is urgent"*), and it resolved the same way: the corpus never asked the question,
so the guard was never right about it. The filed row also names why latency is not safety here —
**#155 promotes this reader into other guards** (see F4).

⚠ **What I verified and what I did not, because "valid workflow" is two claims.** VERIFIED: the
fixtures are valid YAML (Psych loads them) and the value GitHub's schema requires for `run` — a
string — is what Psych produces, for all twelve. **UNVERIFIED: I did not submit any of them to
GitHub Actions.** The guard's contract is about YAML, so the YAML result is the load-bearing one,
but a reader should not take "GitHub would accept this" from me as measured.

### Proposed fix — a hypothesis, but a measured one

A block-scalar opener either carries its key on the indicator's line or it does not, so the keyless
half is one rule rather than another spelling — **and this closes F1 only; see F2 for what it does
not close:**

```python
_BARE_SCALAR = re.compile(r"^\s*(?:-\s+)*(?:[&!]\S+\s*)*[|>][-+0-9]*\s*(#.*)?$")
```

refused when it matches and `_BLOCK_SCALAR` does not. Measured on a temp copy:

```text
closed 12/12
yaml files scanned 18; NEW refusals introduced by the widening: 0
workflows dir only: 0
```

⚠ **Label this transitional.** When I first wrote this paragraph it claimed the enumeration was
*closed* — "after the mask, a line either carries its key or it does not". **I then tested that
claim and it is false**; F2 is the counter-example, and it is a family no indicator-based predicate
reaches at all. The zero-over-fire figure *is* measured, over all 18 YAML files rather than the
workflow dir alone; the completeness claim is withdrawn.

---

## F2 — High. A multi-line QUOTED scalar is read as structure too, and no block-indicator rule can see it

This is the family that decides the convergence question, so it is reported separately from F1 even
though the symptom is identical. A YAML scalar does not need a block indicator to span lines — a
quoted scalar does it with no indicator at all, and may contain colons:

```yaml
      - name: x
        run: "echo hi
          uses: actions/setup-python@v5
          with:
            python-version: 9.9"
      - name: real
        run: python3 --version
```

```text
P2 multi-line DOUBLE-QUOTED scalar
   psych=VALID real_setup_python=false
   pins=['9.9'] live_refusals=0 proposed_refusals=0 rc=0

P3 multi-line SINGLE-QUOTED scalar
   psych=VALID real_setup_python=false
   pins=['9.9'] live_refusals=0 proposed_refusals=0 rc=0
```

`proposed_refusals=0` is the important column: **my own F1 fix does not touch this.** There is no
indicator to match. The control is worth stating — the *unquoted* multi-line form, `P1`, is
correctly rejected by Psych (`mapping values are not allowed in this context`), so the family is
exactly the two quoted spellings, not three.

`_structural`'s docstring already declares this (`:390-394`):

> ⚠ WHAT THIS STILL CANNOT DO, stated rather than implied: it is not a YAML parser. A flow
> mapping (`with: {python-version: '9.9'}`) or a quoted string containing a newline escape is
> still read as text.

So it is a **declared** bound, not a hidden one, and that is why it is High rather than Blocking.
But a declared bound that produces `rc 0 "python pin OK"` over a job with no interpreter pinned is
still a false green, and the file's own standard is that this is the direction the guard must never
fail in. A declaration is not a mitigation.

**A crude predicate does reach it**, and I measured it rather than asserting it: refuse any
structural line that leaves a quote open (quote-to-quote scan, `''` and `\"` handled, stop at an
unquoted `#`). It refuses both P2 and P3, fires **zero** times in `.github/workflows/`, and fires 24
times across the repository — all in `.playwright-mcp/` page snapshots the guard never opens, which
is the same corpus and the same shape as the existing refusal's three quiet hits. I am **not**
recommending it be landed in this PR: it would false-refuse on an apostrophe in prose after an
inline `#`-free value, it is the fourteenth line-local rule on this file, and choosing it over
parsing is precisely the decision backlog #153 asked to be made once instead of per-round.
**Recommendation: file it**, with the measurement above, and let #155's "parse or refuse" answer it.

---

## F3 — Medium. The refusal is computed over the FILE; the pin that decides `unpinned_jobs` is read from the BLOCK, and the two can disagree

`verdict()` computes `unreadable_scalar_openers(text)` per **file** (`:654-656`), but
`unpinned_jobs` → `job_blocks` → `declared_pins(block)` reads a **slice**, `lines[start+1:end]`
(`:572`) — the job's body with its **key line removed**. A block scalar opened *on the job key line*
is therefore masked when the refusal looks and absent when the pin is read:

```yaml
jobs:
  ok:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
  bad: |
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
```

```text
PSYCH VALID; jobs.bad is a String
unreadable openers: []
file declared_pins: ['3.12']
unpinned_jobs: []
rc 0 | python pin OK — every job pins 3.12, and this interpreter is 3.12
```

`bad` is a **string**, not a job, and it reads as pinned.

**Severity is Medium, not Blocking, and the reason is a bound rather than an argument:** the only
line `job_blocks` drops is the job key, and a job key that opens a block scalar makes the job a
string, which GitHub's schema rejects. I could not construct a schema-valid instance and I looked
for one. What it demonstrates is the structural point mandate 1 asked about — **a refusal computed
at one granularity does not protect a read performed at another** — and that is worth recording
before #155 moves these functions apart. Either compute the refusal over the same text the consumer
reads, or state in `unreadable_scalar_openers`' docstring that it speaks for whole files only.

---

## F4 — Medium. #155's transfer inventory predates the refusal, and the refusal imposes a caller obligation nobody has written down

`docs/backlog.md:183` enumerates the twelve anchors #155 must transfer — `:232, :244, :245, :249,
:254, :260, :263, :264, :278, :295, :298, :349` — and names the movers as `_structural()`,
`_steps()`, `Step`, `_STEPS_KEY`, `_BLOCK_SCALAR`. **`_LOOSE_SCALAR` (`:362`) and
`unreadable_scalar_openers` (`:499`) appear nowhere in it.** The row says its figures are measured
on `b9782ddd` and must be re-derived after #154 lands, so this is a known-stale count rather than a
missed one — but the *omission of the refusal as a concept* is not a count, and re-deriving numbers
will not surface it.

The substantive half: **the refusal is only half a mechanism.** The predicate is a pure function;
the safety comes from `verdict()`'s decision to return `rc 2` before computing anything derived from
`_structural`. That obligation is recorded in a comment inside `verdict()` (`:644-653`) and nowhere
a consumer would read. `check-ratchet-contract.py`'s R3 will import `_structural` to mask `ci.yml`
(`:835-837`); if it imports the mask without the refusal, it inherits F1's exact shape in its own
currency — a guard invocation quoted inside an unmasked heredoc counts as a real caller, and a guard
that nothing runs reads as called. That is the fail-open direction, in the guard whose job is to
find fail-opens.

**Ask #155 to carry the rule, not just the regexes:** *a consumer of `_structural` must call
`unreadable_scalar_openers` on the same text and refuse before deriving anything from the mask.*
And per the row's own most-repeated lesson — **mutate the call site**, or the library's coverage
proves nothing about whether the caller called it.

---

## F5 — Low. The new mutation is a proxy for the move, not the move

`scripts/mutations/check-python-pin.json`, the entry named *"the unreadable-scalar refusal is
demoted below the `pins` computation…"*, edits:

```json
["        for ln in unreadable_scalar_openers(text))\n    if unreadable_openers:",
 "        for ln in unreadable_scalar_openers(text))\n    if unreadable_openers and len({q for tx in workflows.values() for q in declared_pins(tx)}) <= 1:"]
```

It does not relocate the refusal; it adds a guard clause that suppresses it when the pins disagree.
That reproduces r4's **symptom** faithfully and kills via the named case, so coverage is real — and
I verified separately (mandate 2 below) that the **literal** move is also killed by the same case.
Recording it because the entry's `name` asserts a relocation the `edits` do not perform, and the
next reader will take the name at face value. Either reword the name to what the edit does, or make
the edit move the block.

---

## Checked SOUND

### The ordering is right, not merely righter (mandate 1)

`verdict()` runs: `not workflows` → **refusal** → `pins = …` → `not pins` → `len(pins) > 1` →
`jobless` → `unpinned_jobs` → the in-CI provenance chain. Measured — four corpora, each pairing an
unreadable opener with the branch it might be preempted by:

```text
refusal vs `not pins`   (no real pin anywhere)             rc=2  CANNOT RUN — a line opens a block scalar…
refusal vs len(pins)>1  (r4's original case)               rc=2  CANNOT RUN — a line opens a block scalar…
refusal vs jobless      (unreadable job too)               rc=2  CANNOT RUN — a line opens a block scalar…
refusal vs unpinned_jobs(a genuinely unpinned sibling)     rc=2  CANNOT RUN — a line opens a block scalar…
```

- **The empty-workflows `rc 2` correctly precedes it.** With no files there is nothing to be
  unreadable, so it cannot mask a refusal; both are `CANNOT RUN` and the empty-corpus message is the
  more specific of the two.
- **The `not pins` `rc 2` correctly follows it**, and did not before — that is r4's finding
  generalised properly rather than patched: with an unreadable opener present, an empty `pins` is
  just as untrustworthy as a disagreeing one, and the r4 repair gets that right by moving ahead of
  the computation rather than ahead of one branch.

### No sibling consumer bypasses the refusal

Every non-test caller of `declared_pins` / `_structural` / `unpinned_jobs` / `job_blocks` /
`unreadable_jobs` is reached from `verdict()`, and `verdict()` has exactly one non-test caller:

```python
# :1273-1275
rc, msg = verdict(_read_workflows(), running_version(sys.version_info[:2]),
                  asserts_here(dict(os.environ)), None,
                  sys.executable, os.environ.get("pythonLocation"))
```

A grep across `scripts/`, `.github/` for the symbol names returns only `EXPECTED_MUTATIONS` /
`check-selftest-counts` / `check-fixture-variation` bookkeeping and four `run: python3
scripts/check-python-pin.py` invocation lines (`ci.yml:107,110`, `schema-gates.yml:211,281`). **There
is no second entry point.** ⚠ I checked the one that looks like a caller:
`check-fixture-variation.py:340-343` names `declared_pins.text`, `job_blocks.text`,
`job_names.text` — it parses the guard with `ast` (`:65`, `:986`) and never calls it, so it is a
population pin and not a consumer. The `EXEMPT_JOBS` interaction is also behind the refusal — it is read at
`:640` but first *used* at `:583`, inside `unpinned_jobs`, four branches later.

### The new case is a real falsifier, and it is the named one (mandate 2)

Reverted on a temp copy by moving the refusal block bodily to after `len(pins) > 1`:

```text
  [FAIL] an unreadable scalar refuses even when it makes the pins DISAGREE: got 1 want 2

99/100 passed
```

Exactly one case reds, it is the case the manifest entry names, and it reds for the right reason
(`got 1 want 2` — the disagreement r4 reported, not an unrelated break). Nothing else moved.

### Counts re-derived by running (mandate 5)

```text
100/100 passed                                   # check-python-pin.py --self-test
manifest entries 47                              # scripts/mutations/check-python-pin.json
files 52 sum 876 check-python-pin 47             # EXPECTED_MUTATIONS in check-plan-code.py
```

`python3 scripts/check-plan-code.py --mutate .`, run to completion on this working tree:

```text
OK — delivered scripts mutated: 52 file(s), 876 mutation(s), 876 killed, 876 attributed to the case each names, 0 survivor(s)
rc=0
```

Duplicate anchor pair — **confirmed inherited, not introduced**, and the anchor text is identical on
both sides:

```text
HEAD 61514c48 entries 47 duplicate old-anchors 1
   x2  '        if (opens_steps and len(opens_steps.group(1)) == job_steps_indent\n    '
master b184bbbc entries 39 duplicate old-anchors 1
   x2  '        if (opens_steps and len(opens_steps.group(1)) == job_steps_indent\n    '
```

### The refusal does not over-fire

The live predicate returns **zero** refusals across all 18 YAML files in the repository, not only
the two workflows it reads. The guard against the real corpus:

```text
⚠ ADVISORY — this machine runs Python 3.14; CI runs 3.12.
rc=0
```

Correct: this machine is 3.14, CI pins 3.12, local mismatch is advisory by backlog #56.

### r4's L1 is fixed and the replacement is accurate

`docs/backlog.md:182` now reads *"group 1 ends at the key; the dash prefix repeats; the key may be
quoted or bare"*, which is what `_BLOCK_SCALAR` (`:331-333`) does — `(?:-\s+)*` repeatable inside
group 1, a quote-to-quote or bare-key alternation, node properties allowed after the colon. Stated
as the rule rather than as a revision of one, which is what the finding asked for.

---

## Standing question — is this converged? (mandate 4)

**No — and the two open items split, which is the decisive part of this answer.**

- **F1 is closable in this PR and should be closed here.** It is a false green in the exact family
  the branch was opened to close, sitting in the predicate this PR's own repair is about; measured,
  one rule closes all twelve members with zero over-fire. Filing it would ship a guard that reports
  `python pin OK` over a job with no interpreter pinned at all, which is the sentence #137 and #317
  exist to prevent.
- **F2 should be filed, not fixed here**, and it is why *"one more widening"* is not the answer to
  this file in general. It is a declared bound (`_structural:390-394`) that is nonetheless a false
  green; it needs a predicate of a different kind; and choosing crude-line-local over parsing is
  exactly the decision #153 asked to be made once. A row carrying the P2/P3 fixtures and the
  measured quote-balance option is worth more than a fourteenth regex landed in a hurry.

⭐ **The shape of this round is itself the finding.** Round 4 attacked over-firing and found
nothing. Round 5 was pointed at under-firing and found two families in an afternoon — one of which
I discovered only by testing my own completeness claim from an hour earlier. That is not evidence
the reviews are failing; it is evidence that **the subject is a surface, and review is the wrong
instrument for a surface** (`dual-review-what-it-catches`). The differential-against-libyaml harness
r3 built is the right instrument, and it is the one thing this branch has that should outlive it:
F1's twelve members came out of it in one run. If F1 is fixed here, **extend that harness to
generate openers rather than only bodies** — that is what would make the next family fall out
mechanically instead of waiting for a reviewer to think of it.

**Thrashing or prose floor? — Neither, and this is round 5, so the question is answered rather than
deferred.** `docs/dev-process.md` arms Phase 6 on *two consecutive rounds whose findings came from
the previous round's fix, in one component*. Per finding:

| round | finding | caused by the previous round's fix? |
|---|---|---|
| r3 | B2, explicit-key silently dropped | no — original class |
| r4 | High, refusal preempted by disagreeing pins | **yes** — by r3's placement of the refusal |
| r5 | F1, refusal blind to a keyless indicator | **no** — a gap r3's fix never closed, open since the refusal was written, found only because this round was asked to attack under-firing |
| r5 | F2, multi-line quoted scalar | **no** — a bound declared before this branch opened, and older than the refusal |

One consecutive round, not two. **The arming condition does not fire**, and the architecture answer
for this file already exists and is scheduled: backlog #153's verdict, tracked as #155.

**What a future reader should NOT re-open:**

- **The ordering inside `verdict()`.** Measured four ways this round. A refusal must precede the
  computation it distrusts; it now does, and every branch that consumes `pins`, `job_names` or
  `declared_pins` sits behind it.
- **Whether a sibling caller escapes the refusal.** `main()` is the only non-test entry point, by
  grep over the whole of `scripts/` and `.github/`.
- **Whether the refusal over-fires.** Round 4 attacked this and found nothing; I re-measured over
  all 18 YAML files and the candidate widening adds zero. The open direction is under-firing only.
- **Whether the multi-line *plain* scalar is a third family.** It is not — Psych rejects it
  (`mapping values are not allowed in this context`), so F2 is exactly the two quoted spellings.
- **The duplicate anchor pair.** Inherited from PR #317, byte-identical on master. Leave it.
- **Whether `_BLOCK_SCALAR` needs another alternative.** It does not, and that was r3's correct
  conclusion. F1 is not an argument for a thirteenth spelling in the *classifier* — it is a gap in
  the *refusal*, where the error direction is visible by construction.

**What #155 must carry across, beyond the twelve anchors:** the refusal (`_LOOSE_SCALAR`,
`unreadable_scalar_openers`, plus whatever closes F1) and, written down for the first time, the
obligation it places on a consumer — *refuse before deriving anything from the mask*. See F4.
