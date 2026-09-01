# Spec review — dashboard collapsed cards, round 1, Claude half

**Target:** `docs/superpowers/specs/2026-08-31-dashboard-collapsed-cards-design.md` v1 (`a96b510c`)
**Date:** 2026-08-31 · **Verdict: NOT CONVERGED** — 2 Blocking, 2 High, 2 Medium, 1 Low.

⚠ **This half was run by the COORDINATOR, not a dispatched subagent.** The previous session measured
that the dispatched half out-found the coordinator in all three of its rounds, so treat this half as
the weaker instrument of the two and weight the Codex half accordingly. The reason is a session
constraint, not a judgement: subagent dispatch was not available without the user asking for it.

Every finding below was produced by **calling the delivered functions**, not by reading them. The
probe output is quoted inline.

---

## Blocking

### B1 — The triangle can promise content and deliver the sentence just read

**Measured.** An entry whose body is a single sentence:

```
entry: "## 2026-08-31\nThe page can no longer contradict itself.\n"
  title: 'The page can no longer contradict itself.'
  prose: '<p class="lede">The page can no longer contradict itself.</p>'
  tech : None
```

`_prose(…, drop_headline=True)` **deliberately keeps** the repetition here: the drop is guarded by
`elif len(paras) > 1` (`:250-265`), whose comment says the fold must not open empty because *"the
reader is worse off than with the repetition"*. That reasoning was sound while the fold sat open-able
beside a fully visible title. Under this spec the fold becomes the card's only affordance, so the
triangle advertises hidden content and reveals a verbatim repeat.

**Failure scenario.** Any entry with one sentence and no `<!--tech-->` block. The reader clicks and
gets back the row they were already reading. Several entries in the live store are this shape.

**Smallest fix.** Compute the fold body **before** choosing the markup. If it is empty, or its text
content equals the title's text, emit the row with **no `<details>` and no triangle** — a plain,
non-interactive line. §2 must say this, and §4 needs a falsifier: *a single-sentence entry with no
tech block renders no `<details>`*.

### B2 — Deleting the cap turns a bounded duplication into an unbounded one, and §3 does not mention it

**Measured**, with the cap simulated away:

```
para = 159 chars, no '.', '?' or '!'
  capped title  : 'this first paragraph has no full stop at all and runs on…'   (110 + …)
  UNcapped title: 'this first paragraph has no full stop at all and runs on for a very long way indeed…'
  prose still contains the paragraph?  True
```

`drop_headline` **refuses to drop** when the first paragraph has no sentence terminator — the guard at
`:250-258`, whose case at `:2087-2091` states the reason explicitly: dropping it *"while the title
showed only TITLE_CAP characters"* deleted text the reader never saw. So the paragraph renders **twice**:
once as the title, once as the lede.

Today the cap bounds the damage to 110 characters. Uncapped, an entry whose first paragraph is 2,000
characters with no full stop renders 2,000 characters twice.

**The guard's own stated premise is the cap.** Removing the cap voids it: with an uncapped title the
whole paragraph is always displayed, so dropping it from the fold loses nothing.

**Smallest fix.** Drop unconditionally once the cap is gone — delete the no-terminator refusal and its
case — and let B1's empty-fold suppression handle the entry that then has nothing behind the triangle.

⚠ **This is a COUPLED change and the spec must label it.** The `:2087` guard and the cap deletion have
to land in the **same commit**. Shipping the cap deletion alone duplicates text on the page; shipping
the guard relaxation alone re-opens the §1c content loss the spec exists to fix.

---

## High

### H1 — `<p>` inside `<summary>` is not conforming, and §2 never names the element

The delivered markup is a `<h3>` (date + id + badge) followed by a sibling `<p class="title">`:

```html
<article class="entry" id="2026-08-31-1"><h3>2026-08-31 <span class="eid">2026-08-31/1</span></h3>
<p class="title">A thing happened here today.</p><details id="2026-08-31-1-plain">…
```

§2a moves the title into the `<summary>` without saying what element carries it. `<summary>`'s content
model is **phrasing content, or a single heading element** — a `<p>` is neither. Keeping the `<p>`
emits non-conforming HTML in the one page whose whole job is to be read.

**Smallest fix.** Make the summary's entire content **one `<h3 class="row">`** holding id, badge, title
and triangle. That is conforming (a single heading element is explicitly allowed), and it resolves the
accessibility question in the same stroke — see H2.

### H2 — The heading outline changes, and the spec is silent about it

There are 29 `<h3>`s on the page today, one per entry, each reading `2026-08-31 2026-08-31/1` — id and
date only. A screen-reader user navigating by heading gets a list of dates.

Whatever §2 does to the title, it **changes that outline**, and silence reads as a decision nobody took.

H1's fix makes this an improvement rather than a regression: the `<h3>` survives, and it now contains
the entry's actual title, so heading navigation goes from a list of dates to a list of what happened.
**State it in the spec** rather than leaving it as a side effect.

---

## Medium

### M1 — F2 cannot be implemented as written; it would fail spuriously

**Measured** on one rendered card:

```
occurrences of '2026-08-31' in ONE card's markup: 5
   id: day-2026-08-31
   id: 2026-08-31-1
   id: 2026-08-31-1-plain
```

F2 says the falsifier fails when *"the rendered row contains the date twice"*. The date is in the day
anchor, the article id and the fold id **by design**, and those are not going away. As written the case
fails on a correct implementation.

**Smallest fix.** Bind F2 to the summary's **visible text with tags stripped**, not to markup.

### M2 — F1 is vacuous for any title containing markup

F1 asserts the full sentence is *"a substring of the rendered card"*. `_inline` renders `**bold**` to
`<strong>bold</strong>`, so for any marked-up sentence the raw string is **not** a substring. Written
naively the case fails on correct output; written with a markup-free fixture it passes while proving
nothing about the path that actually broke in §1c's sibling defect.

**Smallest fix.** Compare tag-stripped text, and include one fixture whose first sentence carries both
a `**` span and a backtick span — the two delimiters the deleted `_close_orphan_markup` handled.

---

## Low

### L1 — The un-clip selector in §2b cannot match

§2b gives `details[open] .entry .title`. `.entry` is the `<article>`, which is an **ancestor** of the
`<details>`, not a descendant, so the selector matches nothing and titles never un-clip on open.

**Smallest fix.** `.entry details[open] .title`, or drop `.entry` from the un-clip rule.

---

## Confirmed, not a finding

- `{eid}-card` is free: `grep -n '\-card"' scripts/gen-dashboard.py` returns nothing, so F8's
  replacement id is available as §4 claims.
- `entry["title"]` has exactly one delivered reader (`:999`); every other hit is a self-test.
  `grep -rn 'class="entry' scripts/` returns only `gen-dashboard.py`. §6's blast radius holds.
- `_close_orphan_markup` has one caller (`:157`, inside `_first_sentence`). The deletion leaves no
  live caller.

## What I did not verify

- ~~Whether `check-plan-code.py` accepts a decrease in `EXPECTED_MUTATIONS` at all.~~
  **RESOLVED during this review, by reading the comparison.** It is an **exact equality**, not a
  floor: `if got != want:` (`:109`), and the drift message at `:543` requires the pin to move *"in the
  SAME commit"*. The rule the codebase states is that coverage cannot shrink **unnoticed** (`:547`),
  not that it cannot shrink. **§3a is therefore sufficient as written** — a decrease passes iff the
  pin is edited alongside the manifest. Still not run: `--mutate .` itself (~3m30s), which is an
  implementation-time gate, not a spec-time one.
- Browser behaviour of `text-overflow: ellipsis` inside a flex `<summary>`, and whether Cmd-F reaches
  clipped text. Asserted from the spec, not observed in Chrome. Phase 4 must drive it.
