# Spec review — dashboard collapsed cards, round 2, Claude half

**Target:** `docs/superpowers/specs/2026-08-31-dashboard-collapsed-cards-design.md` v2 (`f147c3fd`)
**Scope:** the machinery round 1 ADDED — §2f, §3a's two couplings, the rebuilt §4, §2a/§2b/§2c/§6.
**Date:** 2026-08-31 · **Verdict: NOT CONVERGED** — 0 Blocking, 1 High, 2 Medium, 1 Low.

⚠ **Coordinator-run, not a dispatched subagent** (session constraint). Treat as the weaker half; the
Codex half at `spec-dashboard-collapsed-cards-r2-codex.md` executed three suites.

Every finding below was produced by calling the delivered functions. Probe output quoted inline.

---

## High

### H1 — §2f suppresses the fold and takes the tech block with it *(NEW-IN-V2; independently found by Codex r2 H1 — I reproduced it, and propose a smaller fix)*

**Reproduced:**

```
entry: "## 2026-08-31\nSame title.\n<!--tech-->\nraw unique detail\n"
  title            : 'Same title.'
  prose stripped   : 'Same title.'
  tech             : 'raw unique detail'
  prose == title?    True
  -> v2 §2f would SUPPRESS the fold and take the tech with it: True
```

§2f says suppress when the body is empty **or** its tag-stripped text equals the title's. For a
one-sentence entry carrying a `<!--tech-->` block, the second clause fires, the fold vanishes, and
`{eid}-tech` — the only route to the raw detail — vanishes with it. That contradicts §2d and makes F4
unsatisfiable for this input.

**Codex's fix is to widen the comparison to the whole hidden payload. I recommend the narrower one:
delete the comparison.** `_prose`'s tail (`:265-271`) keeps the repetition *deliberately*, and its
comment states the premise:

> `# else: the headline is the entire entry. Keep it — an empty fold is worse than a repeated`
> `# sentence, and there is nothing else to show.`

**§2f overturns that premise.** With no fold, an empty fold is not the alternative — a plain row is.
So let that branch pop the paragraph unconditionally. **Measured**, simulating the pop:

```
single sentence  -> paras after drop: []
sentence + para  -> paras after drop: ['Second paragraph.']
no terminator    -> paras after drop: []
markup only      -> paras after drop: []
```

The prose comes back **genuinely empty** in every shape that previously repeated. §2f then reduces to
one exact test with no string comparison:

> **Suppress the fold iff the rendered prose is empty AND the entry has no tech block.**

This is strictly better than widening: a tag-stripped equality needs normalisation rules for
whitespace, punctuation and inline markup that v2 never gave (see M1), and every one of them is a
place to be wrong. Emptiness has no such rules.

**⚠ COUPLING 3, and it must be named in §3a.** That `else` branch's comment is load-bearing
documentation of a decision this slice reverses. Changing the behaviour without rewriting the comment
leaves the file arguing against its own code — the shape this project keeps paying for.

---

## Medium

### M1 — §2f's tag-stripped equality was never specifiable *(NEW-IN-V2)*

v2 says "its tag-stripped text equals the row title's tag-stripped text" without saying how either
side is normalised. The two sides are **not** produced alike: the title goes through `_inline`, the
prose through `_prose`, which wraps in `<p class="lede">` and re-joins whitespace with
`" ".join(paras[0].split())` (`:251`). Whether `Same  title.` matches `Same title.`, or a title
carrying `**bold**` matches a prose copy of the same words, is undefined.

H1's fix dissolves this finding rather than answering it. **If H1 is rejected, M1 becomes Blocking** —
an undefined comparison in the rule that decides whether content is reachable.

### M2 — v2 does not say what the fold contains when the prose is empty but tech exists *(NEW-IN-V2)*

After H1, an entry with no plain body and a tech block keeps its fold. v2 is silent on whether an
empty `<div class="prose"></div>` is emitted inside it. It should not be: an empty prose div is
invisible, but it is also the kind of thing a later falsifier counts.

**Fix:** state that the prose div is omitted when the rendered prose is empty, and the fold then
contains the nested tech fold alone.

---

## Low

### L1 — §6 still says five `orphaned_delimiters` cases; §3a says four *(NEW-IN-V2; same as Codex r2 L1)*

`grep`: line 356 reads "loses `orphaned_delimiters` and its 5 cases". §3a and §5 were corrected to 4
in v2; §6 was missed. The actual count is 4 (`page_markup.py:436-439`). An implementer following §6
hunts for a fifth deletion.

---

## Checked and correct — round 1's other fixes hold

- **§2c's CSS.** `flex:1; min-width:0` is genuinely required; the corrected selector
  `.entry details[open] .title` matches the emitted nesting. Not observed in a browser by either half
  — **Phase 4 must**, and §6 already says so.
- **§2b's anchor claim.** Verified independently of Codex: tray hrefs are `#{_slug(e["id"])}`
  (`:877-880`) and the article keeps that id.
- **§3a coupling 1.** `_prose` does still pass `cap=len(first)` (`:252`); the `TypeError` is real.
- **§3a coupling 2.** The title and the dropped span both derive from `_first_sentence`, so they cannot
  disagree — including the abbreviation and `TITLE_FLOOR` paths.
- **§3a's cascade.** `_close_orphan_markup` → `_orphaned_delimiters` → `page_markup.orphaned_delimiters`
  is the whole chain; nothing else calls any of them.

## What I did not verify

- Browser behaviour of the flex ellipsis and the un-clip on open. Neither half has run this. Phase 4.
- `--mutate .` after the change (it cannot be run before the change exists). Codex confirmed the
  pre-change baseline at 120 mutations / 0 survivors.
