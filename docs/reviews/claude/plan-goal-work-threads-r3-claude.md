# Post-Plan Gate round 3 — Claude half

**Subject:** `docs/superpowers/plans/2026-09-11-goal-work-threads.md` at commit `2958b820`
("Post-Plan Gate round 2: the retraction was incomplete, and my own fix bit back").

**Mandate:** attack the round-2 fixes only. Rounds 1–2 findings (4 Blocking, 6 High) are closed and
are not re-found here.

## Proof of subject

The plan's `pr_fanout` signature line, verbatim from `2958b820`, plan `:485`:

```python
def pr_fanout(histories) -> dict[str, int]:
```

and its call site, plan `:536`:

```python
    fan = pr_fanout(hist_cache.values())
```

Line references below are `plan:N` for the plan document at `2958b820`, and
`gen-goals-page.py:N` for the live script at that same commit.

NOT-CONVERGED

## Method

The plan's six code blocks were transcribed verbatim into a scratch copy of
`scripts/gen-goals-page.py` at the insertion points the plan names, and run against the real repo.
Every line reference in the plan was checked against the live file first: `:160`, `:170`, `:207`,
`:211-218`, `:213`, `:228-300`, `:303`, `:362-369`, `:372-407` all resolve to what the plan says
they do. One does not — see M3.

**While this review was running, Codex's round-3 half landed as `aa40fb0d`** ("one regex, three
rounds, three fixes each narrower than the class"), which edits the plan. Everything below is
reported against the mandated subject `2958b820` **and then re-measured against `aa40fb0d`**, since
this repo's stated pattern is that the next round's Blocking is the previous round's fix. That
re-measurement is where the Blocking is.

---

## Q1 — is `hist_cache` populated when `pr_fanout` is called?

**Yes.** No finding here. Traced through `collect()` as the plan directs the insertions:

| Order | Plan | Resulting statement |
|---|---|---|
| 1 | plan `:509` "insert immediately **before** `out = []` at `:207`" | `hist_cache = {}` and `def history(rel)` |
| 2 | plan `:525` "add **one** key … immediately after `"docs": ds,` (`:213`)" | `"threads": [thread_prs(t, history) for t in pair_documents(ds)],` — **inside** the `for r in registry:` loop at `gen-goals-page.py:208-218` |
| 3 | plan `:533` "after `out.sort(...)` and before `return out`" | `fan = pr_fanout(hist_cache.values())` |

Step 2 is a list comprehension (eager) inside a `for` loop, and `thread_prs` calls
`history(d["rel"])` unconditionally per side (plan `:475`). The loop is exhausted before
`out.sort()` at `gen-goals-page.py:219`, so by step 3 every anchored document that occupies a
`spec` or `plan` slot is in the cache. Measured on the real repo: `fanout` is non-empty and
`fanout["147"] == 22`, which is only reachable if the cache was full.

One gap existed at `2958b820` and is **not** a lazy-population bug: `thread_prs` iterated only
`("spec", "plan")` (plan `:471`), so a collision's *third* document never entered `hist_cache` at
all. Zero collisions exist today so it was latent. **Codex found this independently at r3** and
fixed it by iterating `thread.get("docs")`; verified at `aa40fb0d`, the new case
`"a PR reachable only through a collision's extra document is still found"` passes and dies if the
loop reverts. Closed, no action.

**Side note, positive:** if a future edit reverted the call site to
`pr_fanout([t for a in out for t in a["threads"]])`, `pr_fanout` would raise
`TypeError: string indices must be integers` at build time rather than silently miscounting.
That failure mode is loud. The *other* reversion is not — see H2.

---

## Q2 — built it and ran it

### At `2958b820`: the suite does not finish

```
  ✓ an extra document on a stem is rendered, not silently dropped
Traceback (most recent call last):
  File ".../_r3_scratch_gen_goals.py", line 799, in self_test
    "extra document" in render_threads(
  File ".../_r3_scratch_gen_goals.py", line 456, in render_threads
    f'<a href="/src/{esc(d["rel"])}">{esc(d["name"])}</a></div>')
                         ~^^^^^^^
KeyError: 'rel'
```

### At `aa40fb0d` (Codex's fix applied): **63/65**, two red

```
  ✗ a document record with no rel does not crash the renderer  got False want True
  ✗ and the crash-free path still names the document           got False want True

63/65 self-test cases passed
```

### Real-repo values

| | Measured | Plan says |
|---|---|---|
| build time | **9.7s** (2.4s baseline) | "~10s, about 4.5x" — holds |
| threads (`<details class="thread"`) | **41** | 41 ✓ |
| threads with both halves | **6** | 6 ✓ |
| `>no plan<` | **21** | **35** ✗ — see H1 |
| `>no spec<` | 14 | not stated |
| `>touched code<` / `>docs only<` / `>unknown<` | 72 / 22 / 0 | `>0` / `>=1` ✓ |
| `pr_fanout` output for PR **147** | **`22`** | 22 ✓ |
| threads rendering `on 22 documents` | **22** | 22 ✓ (but see H2) |
| `140 more under docs/superpowers` | ✓ | ✓ |
| threads with `pr_error` / with an extra document | 0 / 0 | — |

Top of the fan-out distribution, measured: `147:22, 133:4, 42:3, 214:3, 176:3, 76:2`.

⚠ **`pr_error` and the extra-document branch are exercised by zero real records.** Both paths exist
only under unit fixtures — and the extra-document branch is the one that is broken (B1).

---

## Q3 — does the anchored `DOC_PATH` miss documentation it should catch?

**At `2958b820`: yes for all four probes — but none of them is a regression, and none is live.**

```python
DOC_PATH = re.compile(
    r"^(docs/|\.remember/|\.agents/|(README(\.md)?|CONTEXT\.md|AGENTS\.md|CLAUDE\.md)$)")
```

| Probe | `DOC_PATH.match` | `files_are_code([p])` |
|---|---|---|
| `worker/CONTEXT.md` | False | **True (code)** |
| `docs` (no slash) | False | True |
| `.remember` (no slash) | False | True |
| `sub/dir/README.md` | False | **True (code)** |

Two qualifications, both measured, both of which cut against calling this a round-2 defect:

1. **Not a regression.** The round-1 regex was `^(…|README|CONTEXT\.md|…)` — also `^`-anchored, so
   `worker/CONTEXT.md` and `sub/dir/README.md` were tagged code *before* round 2 too. Over the last
   400 commits (1,012 distinct paths), the number whose verdict changed between the round-1 and
   round-2 regex is **0**. The `$` fix is purely latent, exactly as the plan's own comment claims.
2. **`docs` and `.remember` without a slash are not reachable.** `git show --name-only` emits files,
   not directories, so no such entry can appear. Correct behaviour on an unreachable input.

**Codex found this independently at r3** and generalised it to `(.*/)?<basename>$`. Verified over a
2,131-path corpus (400 commits + full `git ls-files`): **0 paths** classify differently between r2
and r3 — the fix is again purely latent, and introduces no over-match. The four paths r3 calls
instruction documents outside `docs/`/`.remember/`/`.agents/` are exactly
`AGENTS.md, CLAUDE.md, CONTEXT.md, README.md`. Closed.

**L3 (Low, residual).** `README.txt` / `README.rst` / `README.mdx` at the repo root were
documentation under the round-1 regex and are code under r2 and r3, because only `README` and
`README.md` are enumerated. No such file exists. Not worth a case; worth a word in the comment,
since the comment currently frames the class as "instruction document at ANY depth" and the real
class is "at any depth, from a fixed four-name list, with at most a `.md` extension".

---

## Q4 — can the new round-2 cases fail?

### (a) `"only the three measured tags can be rendered"` — passes, can fail, **but the name over-claims**

`re` **is** in scope: `gen-goals-page.py` imports it at module level and already uses
`re.findall(r"\d{4}", …)` at `:215`. Confirmed by execution, not by reading.

The expected value **does** match emission. For `_h` the renderer produces
`<span class="tag code">touched code</span>` and `<span class="tag docs">docs only</span>`;
`sorted(set(...))` is `["docs only", "touched code"]`. The case passes.

It can fail — mutation, applied to the delivered code:

| Mutation | Result |
|---|---|
| `else "docs only")` → `else "shipped")` | **RED**, via this case *and* "the two PRs are distinguishable" |
| `tag = ("unknown" if …` → `tag = ("shipped" if …` | this case stays **GREEN** |

**M2 (Medium).** plan `:593-595`. The case is named *"only the three measured tags can be
rendered"* and its fixture `_th` renders **two** of the three. A renderer emitting
`<span class="tag unknown">shipped</span>` satisfies it. The third label is caught only by the
separate `>unknown<` case at plan `:627`, by a different mechanism (substring, not set), so the
stated invariant is not the invariant enforced. That is the same shape the round-2 fix was written
to close: the old case `"implement" not in _h` claimed more than it measured.
**Fix:** add a `code: None` PR to `_th` and expect `["docs only", "touched code", "unknown"]` —
one line, and it then kills the `unknown` mutation too.

### (b) the four chained `and` calls — **no, a single failure is not masked**

```python
eq("a code file whose name STARTS with a doc name is still code",
   files_are_code(["README-generator.ts"]) and files_are_code(["CONTEXT.md.bak"])
   and files_are_code(["CLAUDE.md.old"]) and files_are_code(["READMEs.tsx"]), True)
```

`files_are_code` returns `any(...)`, i.e. a real `bool`. `A and B and C and D` is `True` only if all
four are `True`; any single `False` short-circuits to `False` and `got == want` fails. Verified by
mutation: dropping the `$` anchor turns this case **RED**. Two real but minor costs:

- it reports *that* a path class regressed, never *which* — the failure message is `got False`;
- short-circuiting means a second, independent defect in calls 2–4 is invisible while call 1 is red.

Both are diagnosis, not detection. **Codex fixed this at r3** by returning a list of six results and
comparing to `[True] * 6`. Good change; closed. Nothing further.

### (c) `"a document record with no rel does not crash the renderer"` — **BLOCKING, and the round-3 fix does not fix it**

See B1 below. Short answer: at `2958b820` the fixture never reaches the extra-document branch — it
raises `KeyError` on the **spec** branch first. At `aa40fb0d` it reaches the branch and is
**skipped**, so the case still fails.

---

## Q5 — the case-count chain

Counted per task from the plan's own test blocks, over the live baseline of **15** `eq(` calls
(`gen-goals-page.py:6` declares `# 15 cases, pure functions only`; measured 15).

| Task | new `eq(` | running | plan declares | |
|---|---|---|---|---|
| baseline | — | 15 | 15 | ✓ |
| 1 | +10 | 25 | 25 | ✓ |
| 2 | +9 | 34 | 34 | ✓ |
| 3 | +4 | 38 | 38 | ✓ |
| 4 | +7 | 45 | 45 | ✓ |
| 5 | +14 | 59 | 59 | ✓ |
| 6 | +3 | 62 | 62 | ✓ |

**The chain is correct at `2958b820`.** Confirmed end-to-end rather than by arithmetic: the
transcribed module printed `62/62` worth of cases (61 green + 1 red).

Re-checked at `aa40fb0d`, where r3 adds three cases: 15 → 25 → **35** → **39** → **47** → **62** →
**65**, and the plan declares exactly those. The transcribed module reports `63/65`. Correct.

Both supporting claims in the Global Constraints hold: `gen-goals-page.py` is in
`check-selftest-counts.POPULATION` (`scripts/check-selftest-counts.py:134`) and that guard runs at
`.github/workflows/ci.yml:275`.

No finding.

---

# Findings

## ⛔ B1 — BLOCKING. The round-2 "no rel" fix is still broken after the round-3 fix, and now fails twice

**Where:** plan `:690-695` at `2958b820`; plan `:735-741` at `aa40fb0d`. Case at plan `:639-642` /
`:674-686`.

**Round 2 wrote** the case *"a document record with no rel does not crash the renderer"* and the fix
*"`.get` throughout"*. It changed two membership sites and left two render sites:

```python
named = {d.get("rel") for d in (t.get("spec"), t.get("plan")) if d}   # changed
for d in t.get("docs", []):
    if d.get("rel") not in named:                                      # changed
        parts.append(f'… <a href="/src/{esc(d["rel"])}">{esc(d["name"])}</a></div>')  # NOT changed
```

and the spec/plan branch above it was never touched at all:

```python
parts.append(f'<div class="prline"><span class="t">{side}</span>'
             f'<a href="/src/{esc(d["rel"])}">{esc(d["name"])}</a></div>')
```

**Measured at `2958b820`:** the fixture's spec is `{"name": "s.md"}`, so the spec branch raises
`KeyError: 'rel'` and the entire `--self-test` **aborts** — no summary line, no exit status a caller
can read as "one case red". Codex reported this at r3 and fixed both render sites.

**Measured at `aa40fb0d`, after that fix: the case still fails, and so does the sibling r3 added.**

```
✗ a document record with no rel does not crash the renderer  got False want True
✗ and the crash-free path still names the document           got False want True
63/65
```

**Root cause, which no round has named.** It is not the render sites. It is the membership set:

```python
named = {d.get("rel") for d in (t.get("spec"), t.get("plan")) if d}
```

With a spec that has no `rel`, `named == {None}`. The extra document also has no `rel`, so
`d.get("rel")` is `None`, so `None not in named` is **False**, and the extra document is
**silently skipped**. The renderer does not crash — it drops the document, which is the *original*
round-1 H1 defect ("the record kept it while the page dropped it") reappearing through the
round-2/round-3 fix for a different symptom. `.get` converted a crash into a silent drop, and the
case that was written to catch the drop is the one that fails.

**Verified fix** — one clause, measured `65/65`:

```python
named = {d.get("rel") for d in (t.get("spec"), t.get("plan")) if d and d.get("rel")}
```

⚠ **Do not fix only the fixture.** Making the fixture's spec carry a `rel` turns both cases green
while leaving the production behaviour — a document with no `rel` vanishes from the page instead of
being flagged — exactly as it is. The defect is in `named`, and the case is right.

**Related, and worth deciding rather than inheriting:** at `aa40fb0d` `thread_prs` now does
`if not d or not d.get("rel"): continue` (plan `:499`). A document the page cannot address is
therefore skipped **without setting `pr_error`**, which contradicts the function's own stated rule
that one unreadable document poisons the thread's verdict. Low, and unreachable in production
(every record built at `gen-goals-page.py:200-205` has a `rel`), but it is a second place where a
missing `rel` means "quietly nothing".

## H1 — HIGH. Task 5's `>no plan<` expectation is 35; measured 21

**Where:** plan `:791` (`2958b820`) / same block at `aa40fb0d`.

```bash
grep -c '>no plan<'              /tmp/goals-check.html    # expect 35 — the PAIRING RATE
```

reinforced at plan `:797`: *"⚠ The `>no plan<` count is round 1 M2 — 35 of 41 threads show one half
absent, and nothing watched it before."*

**Measured on the real corpus, at both commits:**

| | |
|---|---|
| threads | 41 |
| both halves | 6 |
| **`>no plan<`** | **21** |
| `>no spec<` | 14 |

`21 + 14 = 35`. The number 35 is the count of threads with **one side absent** — the sentence in the
plan is correct. The `grep` under it is not: it counts only the missing-plan half. `doc_stem`'s own
docstring (plan `:130`) states this correctly too: *"41 threads of which just 6 have both halves.
35 threads render one side absent."*

**Why this matters more than an off-by-fourteen.** This is a *verification* step in a plan whose
Task 5 step 4 also says *"A FAIL here is a stop."* An implementer who transcribes the plan
faithfully gets 21, reads it as a red on the pairing rule, and goes hunting through `doc_stem` /
`pair_documents` for a bug that is not there. A wrong expected value in a gate is worse than no
gate, because it spends the reader's trust in the direction of a false positive.

**Fix:** two lines, both measured today —

```bash
grep -c '>no plan<'  /tmp/goals-check.html   # expect 21 (measured 2026-09-11)
grep -c '>no spec<'  /tmp/goals-check.html   # expect 14 — 21+14 = 35 of 41 threads one-sided
```

## H2 — HIGH. The retraction's named falsifier cannot tell the fix from the defect

**Where:** plan `:794` and `:798-800`.

```bash
grep -c 'on 22 documents'        /tmp/goals-check.html    # expect 22 — PR #147's fan-out
```

> ⚠ **The `on 22 documents` count is the retraction's falsifier in anger**: a zero means
> `pr_fanout` is not discriminating and the page is back to presenting a bulk edit as an
> implementation.

**I expected this to under-report and it does not — the control refuted my premise, and then
refuted the plan's.** Measured: `fanout["147"] == 22` and exactly 22 threads render it, because no
single thread currently has PR #147 on both halves. The plan's number is right.

What is wrong is the claim that the number is a falsifier. I re-enacted the round-2 defect — the
call site passing thread-level PR lists instead of `hist_cache.values()`, which is precisely what
round 2 fixed at plan `:536` — and rendered the page both ways:

| grep | fixed | **round-2 defect re-enacted** |
|---|---|---|
| `on 22 documents` | 22 | **22** |
| `' documents</span>'` | 54 | **51** |

The two `pr_fanout` readings differ on **five** PRs today —
`225: 2 vs 1`, `189: 2 vs 1`, `176: 3 vs 2`, `186: 2 vs 1`, `214: 3 vs 2` — and **every one of them
is invisible to every command the plan runs.** #147 is the one PR where the two readings agree,
and it is the only one the plan checks.

The three unit cases do not cover it either: they test `pr_fanout` as a pure function against
document lists, which the round-2 defect never changed. The defect was the **call site**, and
nothing asserts what the call site passes.

**Fix — one line, and it must name a PR where the two readings disagree:**

```bash
grep -c ' documents</span>'      /tmp/goals-check.html    # expect 54; the thread-level bug gives 51
grep -c 'on 2 documents'         /tmp/goals-check.html    # expect >0 — PR #186 spans both halves
```

`on 2 documents` is the sharper of the two: under the defect PR #186 counts 1, renders no fan-out
span at all, and the grep returns 0.

## M1 — MEDIUM. `pr_fanout`'s de-duplicating `set()` is unfalsifiable, and is a second mechanism for one concern

**Where:** plan `:504`.

```python
        for num in {p["num"] for p in prs}:   # one vote per DOCUMENT, not per commit
```

**Mutation, applied to the delivered code:** replace `{...}` with `[...]`. Result at `aa40fb0d`:
**`65/65` — survives.** No case can see it.

It survives because it cannot fail: `prs_from_log` already dedupes by `num` (plan `:261-263`) and
`annotate_code` preserves that, so a per-document list never contains the same number twice. The
comment presents the `set()` as the mechanism enforcing one-vote-per-document; the mechanism is
actually `prs_from_log`'s `seen` set, one layer up. Two mechanisms for one concern, and the visible
one is the inert one.

Keep the `set()` — defence in depth against a future producer is reasonable — but give it a
falsifier, which is one line:

```python
    eq("a document naming one PR twice still votes once",
       pr_fanout([[{"num": "5"}, {"num": "5"}]]), {"5": 1})
```

## M2 — MEDIUM. "only the three measured tags can be rendered" measures two of three

Full detail under **Q4(a)**. Mutation `tag = ("unknown"` → `("shipped"` leaves this case green;
only the separate `>unknown<` substring case fires. The case name states an invariant over three
labels and the fixture contains two.

## M3 — MEDIUM. Task 6's literal edit still cannot be applied mechanically

**Where:** plan `:882-898` (`2958b820`), unchanged at `aa40fb0d`. This is a **round-1 H2 fix**, not
a round-2 one, so it is outside the narrow mandate — reported because it was measured in passing and
is a stop for the implementer.

The plan says *"`:385` currently reads"* and quotes:

```html
    <strong>{docs}</strong> documents, <strong>{spined}</strong> with a milestone spine.
```

**`gen-goals-page.py:385` does not read that.** The real lines are:

```
385:    survives a rename. <strong>{len(anchors)}</strong> goals, <strong>{docs}</strong> documents,
386:    <strong>{spined}</strong> with a milestone spine.</p>
```

The quoted "one line" is a paraphrase spanning two, and the replacement block ends `</span>` with no
`</p>`. Replacing line 385 alone duplicates `{docs} documents` and orphans line 386; replacing
385-386 deletes `survives a rename.` and the closing `</p>`. Round 1 H2's complaint was *"not an
edit an implementer can apply mechanically"* — it still is not.

**Fix:** quote `:385-386` verbatim as the before-text and give the after-text with `</p>` restored.
(I applied it that way to build the page; the `140 more under docs/superpowers` expectation is
otherwise correct.)

## L1 — LOW. Task 4's Interfaces contradicts Task 4's implementation

plan `:414-415` states *"`collect` returns a second value `fanout: dict[str, int]`"*. Step 3
(plan `:536-538`) attaches it per record and returns `out` unchanged, and Task 5 reads
`a.get("fanout", {})` (plan `:717`). No caller wants a tuple. Delete the sentence or say
"each anchor record gains `fanout`".

## L2 — LOW. Task 5's Files list omits the file Task 5 edits

plan `:559-565` lists `:362-369` and `:228-300`. Task 5's prose at plan `:725-738` also inserts the
`head` block into `collect()` (`:173-224`) and **replaces** the `for a in out: a["fanout"] = fan`
that Task 4 step 3 just wrote. An implementer working the Files list does not know `collect` is in
scope for this task, and the overwrite of a previous task's line is not called out as such.

## L3 — LOW. `README.txt` / `README.rst` at root

See Q3. No such file exists; a word in the `DOC_PATH` comment is enough.

---

## Ran, and clean — recorded so the next round does not re-measure them

**The contrast gate (plan `:766-783`) passes, and I ran it rather than reading it.** All six ratios
clear 4.5:1:

| | light | dark |
|---|---|---|
| `.tag` | 6.24:1 | 6.34:1 |
| `.tag.docs` | 4.58:1 | 7.19:1 |
| `.tag.unknown` | 12.09:1 | 11.18:1 |

`.tag.docs` at 4.58:1 light has 0.08 of headroom — worth knowing before anyone nudges `--pending`.
One quirk in the snippet, harmless today: each token appears **four** times in `CSS`
(light, dark, dark, light), and `{m.group(1): m.group(2) …}` keeps the **last**, which is the light
block. The plan's "Expected: all three PASS in the light block" is therefore what the snippet
actually measures — correct by luck of ordering, not by construction. If a theme block is ever
reordered the snippet silently measures the other theme. Not filed; noted.

Also verified and correct: the `hist_cache` cost estimate (measured **9.7s** against the 2.4s
baseline, plan says "~10s, about 4.5x"); `140 more under docs/superpowers`; the `41` thread count;
`fanout["147"] == 22`; and the `PR_TAIL`/`prs_from_log`/`annotate_code`/`excluded_count` cases,
all of which die under the mutations that target them.

## ⚠ Process — not a plan finding

Commit **`aa40fb0d` swept two of my scratch files into the repo**: `scripts/_r3_getfix.py` and
`scripts/_r3_scratch_gen_goals.py`, transcriptions of this plan I was executing under
`scripts/` so they could resolve `page_chrome`. They are now tracked at HEAD. I have staged their
removal (`git rm --cached`); the working tree is otherwise clean. This is the concurrent-agent
hazard the review-method doc names — a blanket `git add` during another agent's run — and it is
worth a sentence there, since the same commit could as easily have captured a half-written source
file.

---

# Verdict: **NOT-CONVERGED**

1 Blocking, 2 High, 3 Medium, 3 Low.

The Blocking is the fourth consecutive round in which the fix reintroduces the defect it fixes, and
it is the one that must not be waved through: **the round-3 fix at `aa40fb0d` leaves the suite at
63/65**, and the two red cases are the two written to prove the fix. The root cause is `named`
collapsing to `{None}`, not the render sites either round changed. The corrected line is measured at
`65/65`.

H1 and H2 are both *verification* defects rather than code defects, and they share one shape worth
naming for the retrospective: **each states a number that a correct implementation does not
produce (H1), or that a defective one produces just as well (H2).** H2 is the more expensive of the
two — the plan calls `on 22 documents` "the retraction's falsifier in anger", and measured, it reads
22 whether or not the retraction's mechanism is present.

Round 4 should re-run the transcribe-and-execute pass rather than reading the diff. Every finding
above except M3, L1 and L2 came from running the code; none of them is visible by reading it.
