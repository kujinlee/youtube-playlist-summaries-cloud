# Plan review — dashboard collapsed cards, round 1, Claude half

**Target:** `docs/superpowers/plans/2026-08-31-dashboard-collapsed-cards.md` (`e99eca73`)
**Date:** 2026-08-31 · **Verdict: NOT CONVERGED** — 1 Blocking, 0 High, 1 Medium, 0 Low.

⚠ Coordinator-run, not a dispatched subagent (session constraint). The Codex half ran in parallel with
an explicit mandate to execute every code block in a temp tree.

**A plan review has code to run, and that is the whole point.** Findings below come from executing the
plan's fixtures against the delivered generator.

---

## Blocking

### B1 — An existing case asserts the exact property this slice REVERSES, and the plan does not mention it

`scripts/gen-dashboard.py:1861-1862`:

```python
    case("the title is rendered outside the fold",
         '<p class="title">Decide the thing.</p>' in anchored, True)
```

Task 3 moves the title **into** the fold as its `<summary>` and drops the `<p class="title">` element.
So this case goes red — and not incidentally: **its name states the property being reversed.** The
plan's Task 3 step 4 says only "Expected: PASS", and its self-review claimed the surviving cases were
accounted for. An implementer following the plan hits a red suite with no instruction, which is the
definition of a Blocking plan defect.

**How I found it, and the near-miss worth recording.** My first grep required the pattern and `case(`
on the *same line*, and reported "none" for all four old-markup strings — because this case spans two
lines. That is the same defect class as the repo's *"measure the population the CODE sees"* scar. The
corrected grep, over the whole file with the emission site excluded, found three hits: two comments
(`:143`, `:2364`) and this live assertion.

**Smallest fix.** Do not patch the string. **Replace the case with its successor and keep the history**,
because the old case was itself a round-3 survivor — the title had to remain visible while the fold was
shut. The collapse preserves that property by different means: the summary *is* the visible line.

```python
    # ⟳ 2026-08-31. WAS "the title is rendered outside the fold", asserting
    # `<p class="title">…</p>`. That case was a round-3 survivor and its property —
    # the title is legible without opening anything — still holds; it is now
    # delivered by the title BEING the summary rather than by sitting outside a
    # fold. Asserting the old MARKUP would now be asserting the mechanism this
    # slice replaced, so the case moves with the property.
    case("the title is the fold's own summary, so it is legible while shut",
         ('<summary><h3 class="row"' in anchored,
          "Decide the thing." in anchored[anchored.index("<summary>"):
                                          anchored.index("</summary>")],
          '<p class="title">' in anchored),
         (True, True, False))
```

---

## Medium

### M1 — Task 6's `expect` for the CSS mutation names a case the plan never writes

Task 6 mutation 1 (`the collapsed title stops clipping…`) has **expect:** "a new case asserting the
emitted CSS contains `white-space:nowrap` inside `.entry .title` — add it in Task 5's step 3 region if
absent." That is a conditional instruction, not a step. A mutation whose named case does not exist
crashes the harness rather than reddening anything, which `--mutate .` refuses — correctly, and by no
named guard, per the spec's own §4 note.

**Smallest fix.** Make it an explicit Task 5 step:

```python
    _css = _B([], bucket_days([], [], 2, "2026-08-31"))
    case("the collapsed title clips rather than wrapping",
         ("white-space:nowrap" in _css, "text-overflow:ellipsis" in _css,
          "min-width:0" in _css),
         (True, True, True))
```

⚠ This asserts the *stylesheet text*, which is weaker than asserting the rendered effect — a browser
is the only instrument for that, and Task 7 step 2 owns it. Recording the weakness rather than
implying the case proves the behaviour.

---

## Verified by execution — the plan's fixture assumptions hold

- `_slug("2026-08-31/1")` → `'2026-08-31-1'`, so every `_fragment(..., "2026-08-31-1")` lookup in
  Tasks 3 and 4 addresses a real id.
- The emitted article tag is exactly `<article class="entry" id="2026-08-31-1">`, matching
  `_fragment`'s `index()` string including attribute order and spacing.
- **F9's fixture is not vacuous.** The `[needs-you]` ask fixture produces two tray hrefs —
  `{'day-2026-08-31', '2026-08-31-1'}` — and both resolve to emitted ids
  (`2026-08-31-1`, `2026-08-31-1-plain`, `day-2026-08-31`). The non-vacuity assertion on `_trayrefs`
  therefore passes for a real reason, not by accident.
- No `case()` anywhere references `-plain` or `class="eid"`, so Task 3's id change breaks nothing
  beyond B1.

## What I did not verify

- I did **not** apply the plan's patches to a temp tree and run the full suite; the Codex half was
  given that mandate explicitly. Until its report lands, the claim "Tasks 1–5 leave a green suite" is
  **UNVERIFIED** by this half.
- The CSS `content:"\\25B8"` escaping through both the f-string and the CSS parser is unverified by
  this half — also delegated to Codex.

---

## Addendum — the CLASS, enumerated after both halves reported

My B1 and the Codex half's Blocking 3 are **the same defect class**: an existing case that asserts the
property this slice reverses. Two instances found by two reviewers is a signal to stop finding
instances and measure the population — *"after fixing, SEARCH for the class"*.

**Method.** Parsed all **242** `case()` blocks out of `_self_test` by **paren balance**, not by line
grep — a line grep is what hid my B1 in the first place, because that case spans two lines — then
filtered for blocks touching the three behaviours this slice changes.

**Result: four members, and provably no fifth.** Each verified by simulating the new `_prose`:

| case | line | after the change | disposition |
|---|---|---|---|
| `the title is rendered outside the fold` | `:1861` | **RED** | replace (my B1) |
| `a paragraph with no sentence end is never dropped from the fold` | `:2090` | **RED** | delete — coupling 2 |
| `...but the headline is KEPT when it is the entire entry` | `:2203` | **RED** | replace (Codex B3) |
| `a first sentence longer than the displayed cap is STILL dropped` | `:2210` | **PASSES** | **rename** |

**`:2210` is the one neither half found**, and it is the most interesting, because it does not go red.
It keeps passing while its *name* asserts a "displayed cap" the slice deletes — a guard documenting a
mechanism that no longer exists. Nothing would ever have flagged it; a future reader would take it as
evidence a cap exists. Renamed to assert the property (`a long first sentence is STILL dropped from
the fold`) rather than the mechanism.

The other seven `_first_sentence` cases were checked and are unaffected except the two cap cases
already on Task 1's deletion list.

## Correction to this half's own conduct

I edited the plan file **while the Codex half was reviewing it**. It was pointed at `e99eca73` but
reads the working tree, so its report may mix versions — *an instrument that edits the repo corrupts
its peers*, in mirror image. I re-verified each of its findings against the current file before acting;
all eight held, and its three Blockings were reproduced from its own executed output, not taken on
trust. Its step-number citations (`:291`, `:376-378`) refer to the pre-edit file.
