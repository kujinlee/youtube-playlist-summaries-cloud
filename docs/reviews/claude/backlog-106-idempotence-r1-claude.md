# Backlog #106 — composing is idempotent — round 1, CLAUDE half

**Reviewer:** Claude (adversarial half). **Date:** 2026-09-10.
**Verdict up front: NOT CONVERGED.** One Blocking, introduced by the working-tree fix for the
Codex half's Medium, measured on the live corpus.

---

## PROOF OF SUBJECT

```
$ git log --oneline origin/master..HEAD
370144b1 Backlog #106: composing a page twice now produces the same page

$ git diff origin/master...HEAD --stat
 .agents/skills/brief/SKILL.md          |   6 +-
 docs/backlog.md                        |   2 +-
 docs/dashboard-entries.md              |  40 +++++
 scripts/brief-compose.py               | 277 ++++++++++++++++++++++++++++++---
 scripts/check-plan-code.py             | 117 ++++++++++++--
 scripts/check-selftest-counts.py       |   8 +
 scripts/mutations/brief-compose.json   | 106 +++++++++++
 scripts/mutations/check-plan-code.json |  13 ++
 8 files changed, 538 insertions(+), 31 deletions(-)

$ git merge-base origin/master HEAD
050913f6ab1d7d5dc68458b06260c0c9b697a436
```

Base is master `050913f6` exactly, one commit on the branch. No foreign commit is carried.

### ⚠ THE SUBJECT MOVED WHILE I REVIEWED IT, AND THAT CHANGES HOW TO READ THIS DOCUMENT

`git status` was **not** clean:

```
 M scripts/brief-compose.py          # 138 insertions, 13 deletions — UNCOMMITTED
?? docs/reviews/verdicts/backlog-106-idempotence-r1-codex.verdict.json
```

The author was editing `scripts/brief-compose.py` live, in response to the Codex half, throughout
this review. I observed **three distinct contents** of that file:

| md5 | state |
|---|---|
| `7f4e3be4…` | `_selector_scan(style, fragment_css)` — subtraction on the migration path only |
| `a503ca3f…` | `_without_page_rules(css, fragment_css)` — subtraction on **both** paths ← **findings below are against this** |
| (committed) | `370144b1` — no subtraction at all |

Suite size moved `102 → 108 → 109` and the manifest `8 → 10 → 11` while I measured. **Every finding
below names which of the three it is about**, and every measurement I quote was re-taken against
`a503ca3f…` unless stated. A finding against a build the author has already moved past is noise, so
I have marked those explicitly rather than deleting them — two of them are still unfixed.

**Live gate state at `a503ca3f…` (measured, exit codes taken without a pipe):**

| gate | rc | result |
|---|---|---|
| `brief-compose.py --self-test` | 0 | 109/109 passed |
| `check-selftest-counts.py` | **1** | `✗ brief-compose.py: [DRIFT] the docstring declares 102 cases; the suite ran 109` |
| `check-plan-code.py --self-test` | 0 | 93/93 passed |

I did **not** run `--mutate .` (one was already in flight, per the brief). All mutation results
below were produced by copying `scripts/*.py` to a scratch directory, editing the copy, and running
that copy's `--self-test` — never against the repo.

---

## ADDENDUM — the four questions asked after dispatch

Re-measured against the same build (`a503ca3f…`, unchanged since; manifest `a3bf6f8a…`, 11 entries).
Answers first, evidence under each.

| # | question | answer |
|---|---|---|
| Q1 | Is applying the subtraction on the MARKER path safe? | **No** — see B1. But the reachable hazard is *not* the residual you documented |
| Q2 | Can the marked region contain a rule whose selector doesn't match the tray pattern? | **Yes, measured.** `#sendbtn`, `#closebtn`, `.trow` are in the tray's own markup and outside the regex; at-rules are flattened |
| Q3 | Does the `… if kept else css` fallback hide a real failure? | **The premise behind it is correct** — it is genuinely reached through `main()`, verified. But it is silent, and it is the wrong shape for the production caller |
| Q4 | Do the three new mutation entries attribute? | **Yes, all three, cleanly.** One red case each for the named `expect` |

### ⛔ THE ROOT CAUSE OF B1, AND IT IS A POPULATION FACT (§21)

I instrumented `extract_tray` to record which path it took against whether the fragment declares any
tray rule, then ran the full 109-case suite:

```
=== extract_tray path x fragment-declares-tray-rules ===
   MARKER  no-own   : 3        <- returns early at `if not own`, subtraction never runs
   scan    no-own   : 9
   scan    own      : 3
   MARKER  own      : 0        <- THE BRANCH THE r1 FIX WAS ADDED FOR
```

**Zero.** The marker-path subtraction — the entire reason `_without_page_rules` was lifted out of
`_selector_scan` and applied to both paths — is executed by **no case in the suite**. A separate
call census agrees: of 17 calls, 13 are no-ops, 3 hit the empty fallback, and exactly **1** performs
a subtraction — and that one is `extract_tray(_legacy_src, css_of(_frag_o))`, a *scan*-path fixture.
All three new mutation entries die on scan-path fixtures too, so the manifest cannot see it either.

The decisive check — revert the r1 fix's central change, i.e. subtract on the scan path only, which
is exactly the behaviour it was written to replace:

```
$ # scratch copy: css = css if <marker path> else _without_page_rules(css, fragment_css)
$ python3 m6/brief-compose.py --self-test
109/109 passed
```

**The change made in response to the Codex Medium is guarded by nothing.** The suite cannot
distinguish it from its own absence. That is why B1 got in: not a reasoning error, a population one.
The rule is right (*"a rule the page declares is not part of the tray"*); the set the cases run it
over does not contain the branch that was added.

### Q1 — the residual you documented is the *less* reachable of the two hazards

Your stated residual is *"a fragment declaring a rule BYTE-IDENTICAL to a real tray rule"*. I agree
with your reachability judgement on it: the overrides that exist use two ids (`#tray #qbox`)
precisely so they do not collide, and the `.fragment.html` sibling written at `brief-compose.py:839`
is the **raw fragment**, not the composed page, so the #88 loop cannot feed a tray rule back in. It
is a fair residual to state and move on from.

The hazard that actually bites needs no byte-identical collision at all — it needs only a tray rule
whose selector is outside the six-token regex, plus *any* fragment override (which the backlog page
always has). That is Q2, and it is B1.

### Q2 — yes, and three such selectors already exist in the tray's markup

```
tray MARKUP ids/classes: ['closebtn', 'in', 'qbox', 'qt', 'sendbtn', 'sentnote', 'tray', 'trow']
selector regex covers:    #tray .askbtn #qbox #qt #sentnote #modechip
```

`#sendbtn`, `#closebtn`, `.trow` are unstyled today. That is the only reason this is latent.

**Your own fixture string demonstrates it in one line.** The new case pins
`_without_page_rules("#tray{a:1}\n  odd  {b:2}", "body{c:3}")` — a fragment with *no* tray rules:

```
own empty     : '#tray{a:1}\n  odd  {b:2}'      <- odd rule preserved  (the case asserts this)
own NON-empty : '#tray{a:1}'                     <- odd rule DELETED    (nothing asserts this)
```

The case proves byte-exactness on the branch where **nothing happens**, and is silent on the branch
where something does. Same fixture, one argument changed.

At-rules are worse than deletion because the rule survives looking correct:
`@media (max-width:40rem){#tray{width:100%}}` comes back as an unconditional `#tray{width:100%}` —
measured, `'@media' still in region: False`.

### Q3 — the fallback's premise is right; its shape is wrong for the production caller

I set out to show `kept == []` was unreachable outside the synthetic case. **It is reachable, and
your justification checks out.** Instrumented census of where the empty fallback is hit:

| site | kind |
|---|---|
| `brief-compose.py:954` | the new synthetic case, `_without_page_rules(css, css)` |
| `brief-compose.py:1407` → `main()` → `extract_tray:677` | **a real `main()` drive** (backlog #88 fixture) |
| `brief-compose.py:1422` → `main()` → `extract_tray:677` | **a real `main()` drive** (backlog #88 fixture) |

So this is not a guard against an unreachable state, and I withdraw the objection I was going to
file. Two things remain:

1. **It is silent.** `kept == []` has two causes that the code cannot tell apart: *"the fragment IS
   the tray"* (benign, the #88 shape) and *"the region has been emptied by something wrong"*. It
   picks the benign reading and says nothing. Given this module's `FAIL LOUD, NEVER SILENT`
   docstring, the fallback should at least print which reading it took.
2. **Same shape as B1.** `subtracted or keep` guards only the endpoint where *everything* would be
   subtracted. The middle of the continuum — a fragment that duplicates *some* genuine tray rules —
   silently yields a partial tray. Measured on the real `goals.html` tray with a fragment
   duplicating three of its rules: `GENUINE TRAY RULES DROPPED: ['.askbtn', '#tray', '#qbox']`,
   `css` non-empty, no refusal.

The comment at `:943-946` — moving the case *before* the #88 fixture so it still runs under its own
mutation — is exactly right, and it is the reason the empty-fallback entry attributes rather than
dying in an abort. That is good work and I want it on the record alongside the criticism.

### Q4 — all three new entries attribute, and none is arbitrary

Each edit applied to a scratch copy; each `expect` checked for **exact** equality against the parsed
`[FAIL]` lines:

| entry | red cases | `expect` matched |
|---|---|---|
| `the fragment's own #tray overrides are lifted into the tray again (r1 Codex Medium)` | 4 | **1** ✓ |
| `the subtraction is allowed to empty the tray, so nothing composes at all` | 2 | **1** ✓ |
| `the no-op path re-normalises a region it was asked to leave alone` | 1 | **1** ✓ |

No `expect` string collides with another entry's, and no anchor is shared. Entry 2 also reddens `the
suite runs to completion without raising` — that is the new wrapper doing its job, and because the
named case was deliberately placed before the abort site it still resolves to one. **Nothing to fix
here.**

What the three cannot do is see B1: all three fixtures take the scan path, so the manifest's
coverage of `_without_page_rules` is coverage of the branch that was already working.

---

## BLOCKING

### B1 — The fix for the Codex Medium makes the MARKER path non-verbatim, and it silently deletes tray CSS

**Subject: working tree `a503ca3f…`. Not present in commit `370144b1`.**

The committed marker path is a verbatim slice (`scripts/brief-compose.py:653` as committed):

```python
css = style[begin + len(TRAY_BEGIN):end].strip()      # the STATED boundary
```

The working tree now routes that slice through `_without_page_rules`, whose body is:

```python
own = set(_tray_rules(fragment_css))
if not own:
    return css                       # nothing to subtract: keep the region byte-for-byte
kept = [rule for rule in _tray_rules(css) if rule not in own]
return "\n".join(kept) if kept else css
```

When `own` is non-empty the region is no longer sliced — it is **re-parsed and re-serialised** by
`_tray_rules`, which keeps only what matches `([^{}]+\{[^{}]*\})` *and* the selector regex
`#tray|\.askbtn|#qbox|#qt\b|#sentnote|#modechip`. Anything else in the region is discarded.

`own` is non-empty for exactly the pages that motivated the fix: `gen-backlog-page.py:1480` emits
`#tray #qbox{…}` into the backlog fragment deliberately. So the re-serialisation is on for
`backlog-table.html` and `dashboard.html` today.

**Two loss classes, both measured against the real tray extracted from `~/explainers/backlog-table.html`:**

```
tray MARKUP ids/classes: ['closebtn', 'in', 'qbox', 'qt', 'sendbtn', 'sentnote', 'tray', 'trow']
selector regex covers:    #tray .askbtn #qbox #qt #sentnote #modechip
```

`#sendbtn`, `#closebtn` and `.trow` are in the tray's own markup and are **not** in the regex. They
are unstyled today, which is the only reason this is latent rather than live.

Six-generation chain, real tray + real markup + a fragment declaring `#tray #qbox` (i.e. the backlog
page's shape):

```
baseline tray (as shipped)   sizes=[14999,14999,14999,14999,14999,14999]  ALL IDENTICAL=True
tray + #sendbtn rule         sizes=[15036,14999,14999,14999,14999,14999]  ALL IDENTICAL=False
tray + @media #tray rule     sizes=[15043,15017,15017,15017,15017,15017]  ALL IDENTICAL=False
```

* **`#sendbtn{background:#369;color:#fff}` is deleted between generation 1 and 2.** `compose` writes
  it into the region; the next `extract_tray` drops it. No error, no refusal — `css` is still
  non-empty, `has_tray()` only checks `id="tray"`, `id="qbox"` and `/questions`, all of which are in
  the markup and script. The page renders with the Send button unstyled.
* **`@media (max-width:40rem){#tray{width:100%}}` is FLATTENED.** Measured: `'@media' still in
  region: False`, and the inner `#tray{width:100%}` survives *unconditionally*. A mobile-only rule
  becomes an all-widths rule. This is worse than deletion because the rule is still there and looks
  correct.

**Why this is Blocking and not Medium.** Three reasons, in order:

1. It defeats the branch's own headline property for a reachable input class. Backlog #106's
   falsifier is *"recompose any page twice from an unchanged fragment and diff the two outputs; if
   they differ, it is open."* For a tray containing either shape above, gen1 ≠ gen2. (Honest bound:
   it stabilises from gen2 — this is a **one-time silent deletion**, not the unbounded growth #106
   closed. I say so rather than letting the reader infer the worse reading.)
2. It is fail-silent in the one module whose docstring is headed `FAIL LOUD, NEVER SILENT` and whose
   stated purpose is that *"the tray is never retyped. It is lifted, verbatim"*. The committed
   marker path could not do this. The fix removed that immunity.
3. The trigger is one CSS rule away. Styling the Send button is an ordinary thing to do, and nothing
   anywhere would tell the person who did it that their rule evaporates on the next recompose.

**Proposed fix — and what would falsify it.** Do not re-serialise on the marker path. The region
contains only what `compose` wrote, so it needs no inference; the pollution the author is chasing
(`backlog-table.html`'s three frozen `#tray #qbox` rules, see H1) is a **one-off caused by one bad
migration run** and should be repaired by one explicit re-migration, not by making every future
extraction lossy. If subtraction on the marker path is kept, it must operate on the region **text**
— remove the matched rule substrings from the verbatim slice — never rebuild the slice from a
filtered rule list.

*Falsifier for my proposal:* add `#sendbtn{background:#369}` to a tray, compose twice from an
unchanged fragment, diff. Byte-identical **and** the rule still present in the marker region. If my
proposal cannot satisfy both, it is wrong and the re-serialisation is doing something I have not
understood.

**⚠ Whatever you choose, the missing case is the same one**, and the Addendum measures why it is
missing: `MARKER × own` is executed **0 times** in the 109-case suite, and reverting the fix's
central change leaves it 109/109 green. Any fix here needs a case that composes a marked page whose
tray carries a rule outside the selector regex (`#sendbtn{…}` is the cheapest), from a fragment that
declares a tray override — then extracts and asserts the rule is still there. Without it the next
change to this function is in the same blind spot.

**One legitimate reading I want to name, because it would change the verdict and I cannot settle
it from the code.** If the marker-path subtraction is intended as a *one-shot repair* of
`backlog-table.html` and nothing more, then a targeted migration — run once, verified by hand,
followed by reverting `extract_tray` to the verbatim slice — is strictly better than a permanent
lossy transform in the hot path, and B1 disappears. The version in the tree pays a forever cost to
fix a one-off. That is a design call, not a defect I can adjudicate; I record it as the alternative
I would take.

---

## HIGH

### H1 — The migration lifts the fragment's own overrides and FREEZES them; verified independently, and it has already happened on a live page

**Subject: commit `370144b1`.** The Codex half filed this as a Medium; I reached it independently
before reading the working tree, and I am recording it as High because I measured the damage on
disk rather than in a fixture.

`_selector_scan` runs over the whole `<style>` block — fragment CSS, SHIM, tray region and chrome
CSS — while the rule it implements is *"the tray's rules"*. That is §21 exactly: the rule is right,
the population is wrong.

Measured over the 40 unmarked pages in `~/explainers` (of 41 tray-bearing pages; `backlog-table.html`
is the only marked one), comparing what the scan lifts against what the legacy tray region actually
contained:

| rule lifted but NOT in the legacy tray region | pages |
|---|---|
| `#tray #qbox{color:var(--ink);background:var(--card);…}` | 32 |
| `#tray #qbox::placeholder{…}` | 32 |
| `#tray #qbox:focus{…}` | 32 |
| `#modechip{…}` — **five distinct historical variants** | 8–15 each |

**It is not hypothetical. It is on disk.** `~/explainers/backlog-table.html` is the one page already
recomposed on this branch, and its permanent marker region now contains those three `#tray #qbox*`
rules plus three conflicting `#modechip` variants:

```
'#tray #qbox{' occurrences at: [6089, 25189]
TRAY_BEGIN at 24876
  before marker (the fragment's own, from gen-backlog-page.py:1480): [6089]
  AFTER marker  (frozen inside the lifted tray)                    : [25189]
```

Equal specificity (0,2,0), later declaration wins → **the frozen copy governs.**
`gen-backlog-page.py:1480` carries this comment:

> *"The tray is LIFTED verbatim by brief-compose.py and spliced AFTER this block, so a plain `#qbox`
> rule here loses the cascade; two ids win without touching the lifted code."*

That mechanism is now dead on that page. Editing those declarations at `gen-backlog-page.py:1480`
has no effect, silently. The values happen to be identical today, so nothing is visibly wrong —
which is why nothing would report it.

**The test gap that let it through.** The commit's case `a fragment's OWN #tray rule is not lifted
into the tray` exercises the **marker** path only (`_o1 = compose(...)`, which writes both markers).
There was no case for the same accumulator on the **scan** path, and on the scan path it fired.

**Status: the author has fixed this in the working tree**, and I verified the fix against the real
corpus rather than the fixture — using each page's own pre-marker CSS as `fragment_css`:

| page | scan output before | after |
|---|---|---|
| `goals.html` | 15 rules incl. the `#tray #qbox` trio + 3 `#modechip` | 10 rules, trio gone, 1 `#modechip` |
| `2026-09-08-brief-comprehensibility-state.html` | same | same |
| `dashboard.html` | same | same |

The surviving `#modechip` is genuinely from inside the legacy tray region. **The fix is correct on
every real page.** It is the marker-path half of it that is B1.

⚠ **The residual the author states is real, and I measured it before they wrote it down.** With the
`7f4e3be4…` all-or-nothing form, a fragment duplicating three genuine tray rules produced:

```
GENUINE TRAY RULES DROPPED: ['.askbtn', '#tray', '#qbox']
css non-empty, so extract_tray does NOT refuse: True
```

`keep = subtracted or keep` guards only the endpoint where *everything* is subtracted; the middle of
the continuum silently yields a broken tray. The current docstring names this residual honestly and
gives a falsifier, which is the right treatment — I am recording the measurement so the residual has
a number attached rather than a "implausible by construction".

---

## MEDIUM

### M1 — A surviving mutant: the END marker is read with `rfind` and nothing pins it

**Subject: both `370144b1` and `a503ca3f…`.** Measured on both.

```
$ # scratch copy, s/style.rfind(TRAY_END)/style.find(TRAY_END)/
$ python3 m4/brief-compose.py --self-test
109/109 passed
```

The begin marker gets a case (`a fragment that quotes the begin marker does not swallow the shim`)
*and* a manifest entry (`the begin marker is read with find…`). The end marker gets neither, though
`rfind` was chosen for both in the same expression:

```python
begin, end = style.rfind(TRAY_BEGIN), style.rfind(TRAY_END)
```

The defect the `rfind` prevents is real and asymmetric to the begin case: a fragment quoting
`TRAY_END` in its stylesheet — the author's own case argues such a page *"is composed roughly every
week"* — makes `end < begin`, so `end > begin` is False and the page **silently falls back to
`_selector_scan` forever**. Measured effect with a realistic fragment (own `#tray #qbox` override +
quoted end marker): `[15100, 15179, 15179, 15179, 15179, 15179]` — a one-time +79 bytes of
re-lifted override, then stable. Bounded, because `_selector_scan` de-duplicates. **Not** a return
of the growth disease, and I state that rather than inflating it.

I verified the four end-marker shapes and found **no defect in the shipped logic** — all round-trip
clean: fragment quotes `TRAY_END`; fragment quotes both; fragment quotes begin-then-end; and a
begin-only legacy page containing a quoted `TRAY_END` correctly takes the scan path (`begin idx
4312, end idx 627 → scan path: True`). The logic is right. It is unguarded.

*Fix:* one case (compose a fragment quoting `TRAY_END`, assert the round-trip) plus one manifest
entry. *Falsifier:* if the entry does not go red via the case it names, my premise that the shapes
are distinguishable is wrong.

### M2 — `.strip()` on the marker slice is the only thing preventing +2 bytes/generation, and it is unmanifested

**Subject: both.** The manifest's own justification is *"Eight entries, one per clause the fix
decides."* This clause is missed:

```python
css = style[begin + len(TRAY_BEGIN):end].strip()
```

`compose` writes `TRAY_BEGIN + "\n" + css + "\n" + TRAY_END`, so without the strip the extracted css
is `"\n" + css + "\n"` — and the next generation is `"\n\n" + css + "\n\n"`. **+2 bytes per
generation, forever**: backlog #106's disease exactly, in the line that closes it.

It attributes cleanly, so an entry is one line — measured on the current tree:

```
$ python3 m5/brief-compose.py --self-test     # .strip() removed
104/109 passed
  [FAIL] re-extracting a composed page returns the tray CSS unchanged
  [FAIL] ⭐ composing twice from an unchanged fragment is BYTE-IDENTICAL
  [FAIL] a fragment's OWN #tray rule is not lifted into the tray
  [FAIL] ...so composing twice is byte-identical for a real fragment too
  [FAIL] a fragment that quotes the begin marker does not swallow the shim
```

`re-extracting a composed page returns the tray CSS unchanged` matches exactly one red case, so it
is a valid `expect`.

### M3 — `check-selftest-counts.py` is RED right now

**Subject: `a503ca3f…`.** `rc=1`, `✗ brief-compose.py: [DRIFT] the docstring declares 102 cases; the
suite ran 109`. `scripts/brief-compose.py:38` still says `# 102 cases`.

This is mid-edit state and the author will very likely fix it before pushing — I record it only
because *"a red check is a STOP"* and a reviewer who saw it and said nothing would be the failure
that rule exists for. It is not evidence of a design problem.

---

## LOW

### L1 — `docs/backlog.md:134` states a mutation total that is never true

The closure note says *"the file joins the mutation manifest with 8 entries (412 → 420)"*. The
commit's own assertion is `case("the declared counts are the real ones", sum(...), 421)` — 8 for
`brief-compose.py` **plus 1** for `check-plan-code.py`'s own new entry. 420 is neither the before
nor the after. At `a503ca3f…` the real numbers are 11 entries and a sum of 424. Given this repo's
history of declared counts drifting undetected, a row that states an intermediate that never existed
is worth one word of repair.

### L2 — §22 asks for a PRODUCER-side case, and only the consumer side was considered

The abandoned pre-flight comment (`check-plan-code.py`, `A PRE-FLIGHT FOR THE FAILURE-LINE CONTRACT
WAS ATTEMPTED HERE, AND ABANDONED`) is **correct, and I would not reinstate it**. I checked its two
claimed false-positive shapes and they hold; a guard that blocks four conforming files is worse than
the time it saves, and *"prose about a rule satisfying a test for the rule"* is the same hazard
`check-plan-file-tags.py` already paid for.

But §22's *How to apply* has two points, and only the second was attacked. Point 1 is:

> *Make the report format an assertion, not a convention. The producer should have a case pinning
> the line it emits, named for the consumer that parses it.*

`scripts/brief-compose.py:1464` prints `[FAIL] {n}` and **no case pins it**. `grep -n FAIL
scripts/brief-compose.py` returns the printer, a docstring, and two prose comments — one of which
quotes the marker, which is precisely the unfalsifiable shape the abandoned pre-flight ran into. A
producer-side case has **no false-positive class at all**: factor the line into a one-line helper
and assert `_line(False, "x").startswith("  [FAIL] ")`. It cannot fire on prose because it calls the
code.

Today the printer is protected only indirectly — if it regresses, all 11 manifest entries go
unattributable and `--mutate .` goes red with the new (good) message. That works. It is
defence-in-depth that is missing, not a hole.

**Credit where it is due:** the working tree's `self_test` wrapper (`:906-922`) is the right shape
and I confirmed it works. Mutating the selector regex to match nothing makes `extract_tray` raise;
the suite still reports:

```
rc=1
  [FAIL] the suite runs to completion without raising
    raised: SystemExit('brief-compose: incomplete tray in source (css=False markup=True script=True)')
```

And the author got there on the sharper half too, without prompting: the exception is on its own
`raised:` line rather than folded into the case name, because `check-plan-code` slices `[7:]` and an
`expect` must equal the name exactly. That is the one detail that would have made the wrapper
useless, and the comment at `:911-913` names it.

That closes a real hazard I was about to file: `caught = rc == 1` (`check-plan-code.py:1002`) cannot
distinguish a red suite from a **crashed** one, so the new report-format message would confidently
misdiagnose a crash as a printer defect. `brief-compose.py` is now immune. It is the only one of the
38 manifested files with such a wrapper — worth knowing, not worth blocking on.

### L3 — `end` means two different things inside `extract_tray`

```python
begin, end = style.rfind(TRAY_BEGIN), style.rfind(TRAY_END)   # a CSS offset
...
end = html.rfind("</script>")                                 # an HTML offset
```

No bug — the first is fully consumed before reassignment. In a function whose entire contract is
"which offsets bound the tray", reusing the name is a defect waiting for a future edit.

---

## VERIFIED AND CLEAN — the attacks that found nothing

I was asked to verify specific claims independently rather than accept them. These held.

**The 1,225 → 341 rule drop is exactly what the author says it is.** My first attempt at this
measurement was wrong in the way §21 warns about: I used a multiset difference, so de-duplication
read as dropping and I "found" four extra dropped selectors that were not dropped at all. Redone as
a presence-set diff over all **41 tray-bearing pages** (40 unmarked → scan path, 1 marked), the
complete list of distinct rules present in the old output and absent from the new is **four**, and
they are the four the author named:

⚠ The corpus is LIVE and moved during the review — the `regen-backlog-page` hook recomposes pages
while this runs. I re-took this diff at the end of the review and it was unchanged (same four rules,
same per-page counts), so the result is not an artefact of when I sampled.

| dropped rule | pages | load-bearing for the tray? |
|---|---|---|
| `.titleline{display:flex;…}` | 33 | **No** — `titleline` appears in neither the tray markup nor the tray script (checked both) |
| `h1,h2,h3{position:relative;}` | 13 | **No** — SHIM supplies it |
| `:where(h1, h2, h3, h4){position:relative;}` | 13 | **No** — this *is* SHIM's own rule, re-added to every page |
| `body{max-width:53rem;…}` | 8 | **No** — a source page's own body width; leaking it into derived pages was the bug |

The two heading rules deserve a sentence, because the change is not purely a deletion. The lifted
`h1,h2,h3{…}` had element specificity (0,0,1) and sat *after* the fragment's CSS; SHIM's
`:where(h1,h2,h3,h4){…}` is (0,0,0). SHIM's comment says the zero specificity is **deliberate** —
*"the shim only supplies what nobody supplied"*. So dropping the accidentally-lifted higher-specificity
copy restores the designed behaviour rather than weakening it. The heading ask-path (`.askbtn`
positioning) still has its positioning context on every composed page.

**De-duplication keeping the LAST copy is always safe, and I could not construct a counterexample.**
The output places each unique rule at its last-occurrence index, in order. Cascade resolution among
equal-specificity rules depends only on each rule's last occurrence, so the surviving order is
order-preserving by construction: `A,B,C,B,A → C,B,A` preserves `A > B > C`. The author's `_order`
fixture is well built — it is the only shape that separates keep-first from keep-last, since
adjacent duplicates resolve identically under both. Mutation 5 and 6 are genuinely distinct and
neither is an equivalent mutant.

**No fragment shape makes `begin >= 0 and end > begin` select a nonsense region.** See M1 for the
four shapes tested. `rfind`/`rfind` is the correct pair.

**`find_source`'s `root` default change is safe and the docstring's reasoning is right.** Callers,
enumerated: `brief-compose.py:806` (`main`) and five self-test sites. Nothing outside this file. I
confirmed the stated reason by construction — with `root: pathlib.Path = ROOT` the default binds at
`def` time, so `globals()["ROOT"] = _r` in the wiring case would not reach it and the case would
scan the reader's real `~/explainers`. `root = ROOT if root is None else root` is required, not
stylistic.

**`globals()["ROOT"] = _r` cannot leak.** Restored in a `finally`. The only escape is an exception
from `main()`, and the `finally` runs first; the working tree's suite wrapper then reports the abort
as a named case.

**The mutation manifest attributes.** I traced all 8 committed entries against the cases they name:
each `expect` resolves to exactly one red case (several mutations legitimately redden more, but no
two entries' `expect` strings collide), no two entries share an edit anchor, and I found no
equivalent mutant. Entries 5 and 6 in particular are a well-designed pair. Three entries on wiring
rather than logic is the right instinct, and `main stops passing exclude` is the one that would have
caught the whole guard being unreachable.

**I did not find** a case that passes for the wrong reason among the committed 16. The author's own
note on `_legacy` — *"THE END MARKER IS REMOVED, or this fixture would take the marker path and the
case would pass without ever running `_selector_scan`"* — is the check I was going to run, already
run, with a case (`the legacy fixture really is unmarked, so the scan is what runs`) pinning it. The
same discipline appears in the working tree's `the fixture is genuinely begin-only`. This is the
strongest part of the branch.

---

## WHAT THE AUTHOR DID NOT MEASURE

Stated plainly, because the brief asked:

1. **The fix was measured on fixtures, not on the corpus it exists for.** The premise check
   (`goals.html` has 867 begin markers, 0 end markers, 315 `#tray #qbox` occurrences) is a check of
   the *input*, not of the *outcome*. Running `_selector_scan` over all 40 unmarked pages with each
   page's own fragment CSS takes about ten lines and is what turns H1 from "a fixture says so" into
   "the trio is gone on all three pages I checked". It also produces B1, because the moment you feed
   a real marked page back through the new code you are re-serialising 1,691 bytes of region that
   the previous version sliced.
2. **The one page that has already been migrated was not re-examined after migrating.**
   `backlog-table.html` was recomposed for real by the `regen-backlog-page` hook; its frozen region
   is on disk and contains the pollution. The working tree's docstring now says so — but it was
   found by the Codex half reasoning about it, not by anyone opening the file. `extract_tray` on
   that path is four lines of Python.
3. **Nothing asked what the tray markup contains that the selector regex does not.** `#sendbtn`,
   `#closebtn`, `.trow` — three of eight ids/classes in the tray's own markup are outside the regex.
   That was harmless while the regex only ever *selected*; B1 is what happens when it starts to
   *delete*.

---

## VERDICT

**NOT CONVERGED.**

**The single most important thing to fix: B1** — restore the marker path to a verbatim slice. The
committed code's central claim is that the boundary is *stated* rather than inferred; routing the
stated region back through the inference is the one change that gives that up, and it does it
silently, in the module whose docstring is `FAIL LOUD, NEVER SILENT`.

This is `portable-practices` §12 in its textbook form: the round-1 fix added a branch, and the
branch it added is where the next defect lives. It is a **branch-coverage** defect, not a mechanism
one — the marker-boundary design is sound and a redesign would not dissolve B1 — so the remedy is a
fix plus an exhaustiveness pass over the two paths, not a design review. The stop-condition counter
stands at **1**.

Ranked: **Blocking ×1** (B1). **High ×1** (H1 — already fixed in the working tree; recorded because
the fix is what produced B1, and because the residual now needs a measured bound). **Medium ×3**
(M1 surviving mutant, M2 unmanifested clause, M3 red gate). **Low ×3**. Nothing found at any level
beyond those, and the four "clean" sections above are things I attacked and failed to break.

**Two surviving mutants in total**, both measured on this build, and they are the shape of the whole
round:

| mutation | suite |
|---|---|
| subtract on the scan path only — i.e. undo the r1 fix's central change | **109/109 passed** |
| `style.rfind(TRAY_END)` → `style.find(TRAY_END)` | **109/109 passed** |

**The three new mutation entries are good and all attribute** (Q4). They guard the branch that was
already working. Adding entries is not the remedy here — adding the *case* for `MARKER × own` is,
and the entries then have something to kill.

⚠ **Re-run this half against whatever is finally committed.** Every finding here is pinned to
`scripts/brief-compose.py` md5 `a503ca3f5ee8d59bb0a095d3e52b4712` and
`scripts/mutations/brief-compose.json` md5 `a3bf6f8af5dd74cf7d308e7521e2e1da`. The file changed
twice during the review and was stable across every measurement in the Addendum.
