```yaml
round: 6
subject: decision-route-escalation
writer: claude
fixes_nontrivial: false
findings:
  - id: H1
    severity: High
    aim: instrument
    fix_induced: true
    component: unreachable-message-soundness
    disposition: filed
  - id: H2
    severity: High
    aim: process
    fix_induced: true
    component: unreachable-message-soundness
    disposition: filed
  - id: M1
    severity: Medium
    aim: instrument
    fix_induced: true
    component: sweep-skip
    disposition: filed
  - id: M2
    severity: Medium
    aim: process
    fix_induced: true
    component: message-soundness-design
    disposition: filed
  - id: L1
    severity: Low
    aim: instrument
    fix_induced: true
    component: sweep-skip
    disposition: filed
  - id: L2
    severity: Low
    aim: process
    fix_induced: true
    component: message-soundness-design
    disposition: filed
```

# Claude adversarial review — `decision-route-escalation`, round 6

**Subject: `git diff 27d4d003..f6c6dcb3`** — the response to r6 and the architecture review it
convened. `docs/explainers/*` ignored as instructed.

**The headline is one sentence.** The `-z` fix for CODEX finding 2 **holds** — I reproduced the
defect and the fix end-to-end at the real CI seam, over real `git` output, and could not break the
verdict. The identity-case fix for CODEX finding 1 **does not**: it pins `_UNREACHABLE_PROSE`, and
the diagnostic a reader acts on is built from **six** strings of which the table owns three. I
edited the other three and was told *"the implementation on this branch is defective … the code it
delivers is broken and must be rewritten … The only way out is a further round that reports no
findings at all"* at **111/111 green and 27/27 mutations killed**. That is the fifth evasion.

⛔ **And it is not a request for a sixth proxy.** The architecture review's prohibition is on another
proxy *for meaning*; this is the change-detection mechanism it chose, applied to its actual subject.
**ONE case closes it, and I ran the falsifier both ways** (H1, below).

---

## H1 — High. The identity cases' subject is the LOOKUP TABLE, not the diagnostic. Three of the six prose strings `render_unreachable` emits are pinned by nothing, and a transform on its output is pinned by nothing

`scripts/check-review-decision.py:366-371` (the renderer), `:351` (the claim), `:935-951` (the cases).

`render_unreachable` concatenates six strings. Two come from `_UNREACHABLE_PROSE` and are pinned by
this round's new identity cases. **Three are literals in the function body:**

```
366:    return ("no round recorded for this subject is clean, so convergence is "        <- UNPINNED
367:            + _UNREACHABLE_PROSE["about"][reason["about"]]                            <- pinned :935
368:            + ": every recorded round still carries an OPEN Blocking/High finding, an open "
369:              "deliverable-aimed finding, or fixes it declared non-trivial. ⚠ "        <- UNPINNED
370:            + _UNREACHABLE_PROSE["remedy"][reason["remedy"]]                           <- pinned :941
371:            + ". See backlog #329 for why the record, not the work, is what this is about")  <- UNPINNED
```

The docstring at `:351` claims: *"an edit to any rendering below cannot pass unnoticed, because each
string is pinned by an identity case."* Three of them are not "below" — they are above, in the
`return` — and nothing pins them. **That claim is false as written**, and this is the same shape as
[[a-bound-enumerates-what-is-witnessed]]: the bound enumerated what the author had just written,
not what the seam emits.

### Executed — green control, red negative control, then the evasion

`scratchpad/r6-claude/evade.py`. Each run stages a fresh copy of `scripts/` and edits only the
three body literals. "work is defective" and "finds nothing" are deliberately avoided, because
`:927` pins their absence; the `disposition` rendering is left byte-identical, because `:960` pins
it as a substring of what reaches the reader.

```text
=== control: --self-test rc=0 ['111/111 self-test cases passed']
    decide() verdict: ROUND_OWED
    WHAT THE READER IS TOLD:
      no round recorded for this subject is clean, so convergence is UNREACHABLE from this
      record rather than merely unmet: every recorded round still carries an OPEN Blocking/High
      finding, ... ⚠ What reaches convergence is recording a disposition — `fixed` or `declined`
      — on each of them, ... See backlog #329 for why the record, not the work, is ...

=== evasion: --self-test rc=0 ['111/111 self-test cases passed']
    decide() verdict: ROUND_OWED
    WHAT THE READER IS TOLD:
      the implementation on this branch is defective, so convergence is UNREACHABLE from this
      record rather than merely unmet: the code it delivers is broken and must be rewritten.
      ⚠ What reaches convergence is recording a disposition — `fixed` or `declined` — on each of
      them, ... The only way out is a further round that reports no findings at all

=== negctl: --self-test rc=1
      ['[FAIL] the `record` rendering is pinned — an edit must come HERE',
       '110/111 self-test cases passed']
```

The negative control is the point: editing a **table** rendering goes red at 110/111 through the
case it names, so the identity cases work — **for the table**. Editing the body literals is
invisible. Both forbidden assertions reach the reader through `decide()`.

### The mutation manifest is equally blind

Scoped sweep (`HARNESS_TREE` rsynced, one manifest kept, `EXPECTED_MUTATIONS` reduced), run twice —
once untouched, once with the evasion applied:

```text
# untouched control
OK — delivered scripts mutated: 1 file(s), 27 mutation(s), 27 killed, 27 attributed to the case
each names, 0 survivor(s) — measured over the WHOLE manifest        real 0m6.342s

# EVASION APPLIED to the scoped tree (3 unpinned body literals)
OK — delivered scripts mutated: 1 file(s), 27 mutation(s), 27 killed, 27 attributed to the case
each names, 0 survivor(s) — measured over the WHOLE manifest        real 0m5.925s
```

Byte-for-byte the same verdict over code that misinforms its reader.

### A second, independent evasion in the same gap: a transform on the OUTPUT

The identity cases read the dict. Nothing reads the returned string, so a `.replace()` applied to
the result is also invisible — provided it leaves the `disposition` substring alone:

```text
rc= 0 ['111/111 self-test cases passed'] []
READER IS TOLD:
  no round recorded for this subject is clean, so convergence is UNREACHABLE because the
  delivered implementation is broken: every recorded round still carries an OPEN Blocking/High
  finding, ... See backlog #329 for why the record, not the work, is what this is about
```

⚠ **NEGATIVE RESULT that bounds this.** The same wrapper applied to the **remedy** half *is* caught
— by `:960`, not by an identity case:

```text
### wrapper: .replace() on the rendered OUTPUT: rc=1 ['110/111 self-test cases passed']
    fails=['[FAIL] the ROUND_OWED reason reaches the reader carrying the rendered remedy']
```

So the unguarded surface is precisely: the three body literals + the `about` half of the output.

### The fix, with its falsifier run in both directions

One identity case pinning the whole rendered string for the shipped token pair. **Not a proxy for
meaning** — the same change-detection mechanism, pointed at the sentence instead of the table. The
expected value is derived by *running* the shipped renderer, never typed from memory
([[a-sever-substitutes-todays-value]]):

```python
case("⭐ the SHIPPED diagnostic is pinned WHOLE — the body literals are renderings too",
     render_unreachable({"about": UNREACHABLE_ABOUT, "remedy": UNREACHABLE_REMEDY,
                         "blockers": []}),
     <the 551-character shipped string>)
```

```text
### PROPOSED FIX, control (fix added, code untouched):     rc=0 ['112/112 self-test cases passed']
### PROPOSED FIX, EVASION (fix added, 3 body literals edited): rc=1 ['111/112 ...']
    [FAIL] ⭐ the SHIPPED diagnostic is pinned WHOLE — the body literals are renderings too
```

It also closes the output-transform evasion, since that changes the same returned string.
⚠ The docstring at `:351` must then say *the rendered diagnostic*, not *any rendering below*.

---

## H2 — High. backlog #335 is CLOSED and roadmap-ticked, and its own written FALSIFIER fires

`docs/backlog.md:319`; `docs/roadmap-to-launch.md` (the `[x] backlog #335` bullet).

Row 335's falsifier, verbatim: *"**FALSIFIER:** editing any shipped rendering must redden a NAMED
case; and the docstring must not reacquire a soundness claim."* The three body literals are shipped
renderings — they appear in **every** diagnostic this tool emits, not in a rejected branch — and
editing them reddens nothing (H1). The status cell reads `✅ **CLOSED 2026-10-21** — narrowed,
pinned, mutation-covered, 27/27 killed and attributed`; the 27/27 is accurate and, as H1 shows, not
evidence for the sentence it is attached to.

Shares H1's evidence; filed separately because the remedy is different — a status reversal, not
code. ⛔ **This is the one that outlives the round.** H1 is a missing case; H2 is the *record* saying
a property is guaranteed when it is not, and the record is what the next reader acts on. Reopen 335
(or re-close it on the completed guard), and untick the roadmap bullet.

---

## M1 — Medium. `ci.yml`'s RUN arm now asserts "a staged path changed" on a path where it does not know that, and where it can be false — the third state the shell cannot express

`.github/workflows/ci.yml:956` (the RUN arm), `:876` (`-z`), `:900` (`changed_from_nul`).

The shell has two RUN branches: `DIFF_TAKEN=0` → *"the diff could not be taken"*, else *"a staged
path changed, so the sweep runs:"* + `$MATCHED`. `changed_from_nul` introduces a **third** state —
the diff was taken (`DIFF_TAKEN=1`) but the paths were refused, so `changed is None`. The module
prints evidence only `if need and changed is not None`, so `MATCHED` is empty and the arm claims a
staged path changed. **It does not know that, and in the docs-only case it is false.**

### Reachable on TODAY's workflow, with `-z` in place

A file at the repository root whose name begins with `"`. Real repo, real `git`, the step extracted
from `ci.yml` with `require("js-yaml")` and run for real:

```text
$ git diff --name-only -z HEAD^ HEAD | od -c
0000000    "   w   e   i   r   d   .   p   y  \0

### quoteroot / fixed  rc=0  (-z present: 1)
--- GITHUB_OUTPUT: changed=true
--- log:
    a staged path changed, so the sweep runs:
                                                 <- empty
```

### And it is the shape the arm's own comment says it closed

`:950-955` records: *"THE REASON IS REPORTED, NOT ASSUMED. This arm used to print 'scripts/ changed'
unconditionally, so on the undetermined-diff path it asserted a changed file set it had just failed
to read… A log line must never claim to know something this step could not determine."* The new
refusal path is exactly an undetermined-diff path, and it lands in the arm that asserts.

Worse on the `-z`-dropped future the fix is designed for — the composition works, the log does not:

```text
### docsonly / nozflag  rc=0  (-z present: 0)
--- GITHUB_OUTPUT: changed=true
--- log:
    a staged path changed, so the sweep runs:
                                                 <- no staged-relevant path changed at all
```

**Verdict is correct and fail-safe in every case above** (`changed=true`), so this is reporting, not
logic — the fourth false statement about the world this one step has produced (v1 *"no scripts/ file
changed"*, v2 *"unchanged suites"*, the RUN arm's *"scripts/ changed"*, now this). Fix: let the
module print the reason it refused (a third evidence line, or `RUN-UNDETERMINED`), so the shell
keeps owning no copy of the rule. ⚠ A `run:` block has no case and no mutation entry, which is why
this class keeps recurring here and why the discrimination belongs in the module.

---

## M2 — Medium. The architecture review attributes all four failures to "an untestable property", and two of the four are ordinary guard-construction defects — which is why the fifth survived

`docs/reviews/architecture-review-2026-10-21-message-soundness.md` F1.

F1's core claim is sound and worth keeping: *"this refusal is a statement about the RECORD, not
about the work"* is a claim about what an English sentence means, no test can assert it, and it
should have been dropped rounds ago. **The over-reach is the word "four".** Taking the review's own
table:

| Design | How it fell | Class |
|---|---|---|
| r4 — the token `RECORDED` | a message asserting the opposite contains it | genuine proxy-for-meaning failure |
| r5a — phrase + forbidden list | a one-token negation contains the phrase | genuine proxy-for-meaning failure |
| r5a — the forbidden list itself | emptying it left 102/102; the case **looped over the set under test** | ordinary guard construction |
| r5b — `_UNREACHABLE_PROSE` | editing a rendering left 107/107 | ordinary guard construction |

The last two are not consequences of an unestablishable goal. The third is this repo's own named
class, [[a-class-fix-needs-an-independent-copy-and-an-identity-case]], written out longhand in
`check-plan-code.py` the same hour — the review says so itself. The fourth is closed by a mechanical
pin, which the review *then prescribes*. **The proof is in H1:** my fifth evasion is closed by one
identity case over the rendered string, with no reasoning about meaning anywhere in it. A defect
that a mechanical change-detection case kills was never evidence that the property was untestable.

### The cost of the over-reach is visible, not hypothetical

F1 concludes *"⛔ NOT PROPOSED: a fifth cleverer proxy. Four have failed; the next would too."*
Correct about proxies — but applied to a round whose actual fix was change detection, it licensed
**closing #335 without re-attacking the new mechanism**, and that is where evasion five lived. The
generalisation absorbed two construction defects, and absorbing them meant nobody asked whether the
construction was complete. Honest framing: *two* designs died of an untestable goal, *two* died of a
guard whose subject was narrower than the property's surface, and the second class is still open.

⚠ **UNVERIFIED (reasoning, not measurement):** that stating it the narrower way at r6 would have
caught H1. I can only show the broad framing was present and H1 shipped under it.

⟳ Two of F1's figures I did verify, and both hold: `~12 cases` (10 in the token/negation/identity
block + the 2 value-equality cases) and `5 mutation entries` (manifest entries 22, 23, 24, 26, 27).

---

## L1 — Low. A non-UTF-8 filename makes the step crash rather than parse, and `changed_from_nul`'s stated bound does not mention it

`scripts/check-plan-code.py:307` (`raw: str`), `:327` (*"WHAT IS NOT CLAIMED"*).

With `-z`, `git` emits the path's **raw bytes**. A filename that is not valid UTF-8 cannot be read
by `pathlib.Path.read_text()`. Built with `git update-index --add --cacheinfo`, through the real
extracted step:

```text
$ git diff --name-only -z HEAD^ HEAD | od -c
0000000    s   c   r   i   p   t   s   / 351   .   p   y  \0

--- GITHUB_OUTPUT: changed=true
--- log:
    ::warning::could not decide whether the sweep is needed (ERROR) —
    ::warning::running it rather than skipping a gate on an unanswered question
--- stderr: UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in position 8
```

**Fail-safe, and the warning is a true statement** — `|| echo "ERROR"` plus the `*)` arm catch it.
Low because the gate runs. But the subject is bytes and the parameter is `str`, so the function
cannot handle it by construction, and the paragraph that enumerates what is *not* claimed names the
newline and NUL cases and not this one. Either take `bytes` (`os.fsdecode` per entry) or add the
encoding case to that paragraph. ⚠ I did not test a non-UTF-8 locale; under one, a *valid* UTF-8
non-ASCII path would take the same crash-then-RUN route — also fail-safe. **UNVERIFIED.**

---

## L2 — Low. The architecture review calls F3 "the pattern"; backlog #334 correctly calls it n=1

Architecture review `:134`: *"became a reviewable decision with a falsifier attached, **and that is
now the pattern rather than a one-off**."* backlog #334 says the opposite, twice, and is right to:
*"measured over one live instance"* and *"⚠ Deliberately NOT scripted yet: n=1, and a guard built on
one instance is the shape backlog #56 warns about."* The row is honest and correctly sized (🟢, S);
the review's sentence is the one to correct. [[a-signal-needs-its-base-rate]].

**Answering the brief directly: no, #334 is not n=1 dressed as a pattern** — the *row* discloses
n=1 prominently. One sentence in the review does overstate it.

---

## NEGATIVE RESULTS — what I attacked and could not break

### 1. The `-z` fix: reproduced the defect, verified the fix, at the real CI seam

Not the pure function — the actual `mutated_code` step, extracted with `require("js-yaml")` and run
against real `git` in real repositories (`scratchpad/r6-claude/run_step.sh`). ⚠ My first run had a
**RED CONTROL** and was discarded: copying only `check-plan-code.py` gave
`ModuleNotFoundError: No module named 'coverage_verdict'`, so every arm fell to `*)`. All results
below are from a tree with the whole of `scripts/`.

| Scenario | pre-fix (no `-z`, `splitlines`) | shipped (`-z` + `changed_from_nul`) |
|---|---|---|
| only `scripts/é.py` changed | **`changed=false`** + *"nothing under SWEEP_RELEVANT_ROOTS changed"* | **`changed=true`**, `scripts/é.py` listed |
| only `docs/base.md` changed | `changed=false` + the hole message | `changed=false` + the hole message |
| nothing changed | `changed=false`, no hole | `changed=false`, no hole |

The first row is CODEX finding 2 reproduced as a **verdict** defect with the false log line attached,
and the fix closing it. Rows 2–3 are the negative controls that matter: backlog #173's docs-only
saving is **not** regressed, and the hole/no-hole discrimination still discriminates.

**The composition claim holds.** Dropping `-z` and keeping the parser:

```text
### nonascii / nozflag  changed=true      ### docsonly / nozflag  changed=true
### nothing  / nozflag  changed=false     (correct — an empty diff is [] in both worlds)
```

### 2. Real `git` output shapes — nothing I could construct produced a wrong verdict

```text
$ git diff --name-only -z HEAD~1 HEAD | od -c     # git 2.49.0
scripts/"quoted.py\0scripts/back\slash.py\0scripts/new\nline.py\0
scripts/with space.py\0scripts/é.py\0

$ changed_from_nul(<that>)  -> ['scripts/"quoted.py', 'scripts/back\\slash.py',
                                'scripts/new\nline.py', 'scripts/with space.py', 'scripts/é.py']
$ sweep_needed(...)         -> True
```

- **a literal newline under `-z`**: parses to one path, verdict RUN. The docstring's claim holds.
- **whitespace in a path**: `MATCHED`/`HOLE` are only ever expanded as `printf '%s\n' "$HOLE"`, so
  there is **no word-splitting hazard**. Verified live: `scripts/with space.py` → RUN, printed whole.
- **a rename** (`git mv docs/base.md docs/renamed.md`) → SKIP + hole, correct.
- **`core.quotePath=false` does not rescue the old code.** It unquotes the non-ASCII path and still
  quotes `"`, `\` and newline — 3 of 5 shapes:
  ```text
  "scripts/\"quoted.py"\n"scripts/back\\slash.py"\n"scripts/new\nline.py"\n
  scripts/with space.py\nscripts/é.py\n
  ```
  So refusing *all* newline-delimited input, rather than un-quoting it, is the right call.
- **a real file whose name starts with `"`** → refused → RUN. Over-conservative and safe (such a
  path cannot be under a staged root). Its only cost is M1's log line.

### 3. A7 — all four new mutation entries redden through the case each names, over proved-green controls

`check-plan-code`'s manifest cannot be scoped (its suite pins the manifest sum), so its entries were
applied individually to staged `HARNESS_TREE` copies:

```text
### CONTROL check-plan-code: rc=0 ['206/206 passed'] fails=[]
  newline-delimited output is TRUSTED instead of refused
    rc=1 ['205/206 passed']  reddened via named case: True
    [FAIL] ⛔ NEWLINE-delimited output is REFUSED …: got ['scripts/a.py\n'] want None
  a C-quoted path that arrives despite `-z` is passed through
    rc=1 ['205/206 passed']  reddened via named case: True
    [FAIL] ⛔ a C-quoted path that arrives anyway is REFUSED …: got ['"scripts/\\303\\251.py"'] want None

### CONTROL check-review-decision: rc=0 ['111/111 self-test cases passed'] fails=[]
  the `record` rendering is edited to blame the IMPLEMENTATION
    rc=1 ['110/111 …']  reddened via named case: True
  the `disposition` rendering is replaced by the demand backlog #329 abolished
    rc=1 ['110/111 …']  reddened via named case: True
```

Each kills **exactly one** case, so none is behaviour-neutral and none is over-caught by a sibling —
the two failure modes this round's brief flagged. Declared manifest sum verified against the files:
`declared sum: 1653  real sum: 1653, per-file mismatches: none`.

### 4. backlog #336's claims about `check-gate-falsifiability.py` — all accurate

- *"Its population is gate checklist items under `docs/`"* — `GATE_SCOPES` is exactly
  `{"docs/m1.4-finishup-checklist.md": None, "docs/roadmap-to-launch.md": ["## M1","## M2","## M3"]}`.
  No docstring is in its subject. **Accurate** (and narrower than the row implies, which only
  strengthens the row).
- both quoted passages (*"the guard is a SENTENCE…"* and *"It CANNOT tell whether an instrument can
  observe its subject"*) — **verbatim**.
- *"ran green throughout (`gate falsifiability OK`)"* — `rc=0`,
  `gate falsifiability OK — every unticked gate item names what would fail it`; `19/19` self-test.
- *"60+ guards carry property prose today"* — **75** of 75 `scripts/*.py` have a module docstring
  (50 of 50 `check-*.py`); `discover_guards`' population is ~98 files. True and conservative.

### 5. Attacks that found nothing

- **Adding a key to `_UNREACHABLE_PROSE`, or flipping a token constant.** Caught: `:911-916` pin
  both constants *and* the exact key sets, by independent literals.
- **Mutating the table at import time** (a statement after the literal). Caught — the identity cases
  read the live dict, not the source.
- **A transform on the remedy half of the output.** Caught at `:960` (quoted under H1).
- **The deliberate loop-over-the-set at `:960`** (`_UNREACHABLE_PROSE[...] in decide(...)`) — both
  sides move together, so it cannot see a reworded remedy. That is documented as intentional (its
  subject is the *escape path*) and it is now backed by the `:941` identity case. Not a defect.
- **`sweep_needed`'s derivation** — I did not re-attack A5; r6 CODEX found no current failure and I
  have nothing to add.

---

## The pre-committed falsifier, answered

**The structural fix did NOT close the class — and the architecture review's own design correction
is also not yet achieved.** Evasion five needs no cleverness: three of the six strings in the
rendered diagnostic were never in the guard's subject. The honest statement of where this stands:

- the *soundness* claim is correctly abandoned, and the docstring is right to abandon it;
- the *change-detection* claim that replaced it is **not true of the diagnostic**, only of the
  lookup table — and that is a mechanical gap with a one-case fix whose falsifier I ran both ways;
- so `message-soundness` remains open, and the thing to stop doing is **closing the row before
  re-attacking the new mechanism**, not "trying another proxy".

⚠ **`sweep-skip` has now carried fix-induced findings in r4, r5 and r6** (M1 is this round's).
`sweep_needed`'s *logic* is undented for a fourth round and the `-z` fix is the first finding on this
component I could not break. The pattern is not a thrashing predicate — it is a `run:` block with no
case and no mutation entry, three times over.

# NOT CONVERGED

**The finding: H1** — `render_unreachable:366-371` emits three prose strings that no identity case
pins, so a reader can be told the work is defective and that a finding-free round is the remedy at
111/111 green and 27/27 mutations killed. **H2 follows from it:** backlog #335 is closed and
roadmap-ticked against a falsifier that fires.
