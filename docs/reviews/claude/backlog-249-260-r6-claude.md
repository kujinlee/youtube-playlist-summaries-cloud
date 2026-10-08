# Round 6, Claude half — `backlog-249-260-fixes` @ `e70aa551`

Subject: `git diff 6e829059..e70aa551 -- scripts/` — verified as **7 files, 422 insertions, 94
deletions** (`git diff --shortstat`). Two commits: `aee7dd8e` (round 5's Claude fold) and
`e70aa551` (round 6's Codex fold). Mandate: refute. Hypothesis under test: **round 6 is clean.**

**Verdict: the hypothesis breaks, but not where the brief expected.** Round 6's *own* fold —
the opener truncation, the `tomllib` readback, the HEAD refutation, the three new manifest entries —
**holds under every attack I could build**, including a differential test against two independent
CommonMark parsers over 411,110 inputs. The High below is in `aee7dd8e`, the other commit in the
subject range: `masked_of`'s cache key is unsound and the docstring sentence defending it is false.

Everything was run under `python3.12` (3.12.9). Every exit code was taken from a redirected file or
captured into `rc=$?` on its own line, never after a pipe. Nothing under `scripts/` was edited; every
mutation was applied to an in-memory copy of the delivered source.

**The instrument, and why it is better than r5's.** r5 got cmark + markdown-it-py and read span
boundaries *out of* the shipped function with a probe string, which is the move that found r5's H1.
That probe can only see an in-span position by masking a whitespace character there, so it has two
blind spots r5 recorded as stated bounds: a span whose content is all backticks/backslashes is
invisible, and a span whose content *starts or ends* with backticks/backslashes gets snapped to the
wrong bounds. **Both blind spots produce false findings, and I hit them:** r5's harness, re-run on
this fold, reported 12 "disagreements" and **all 12 were the snapping artifact** — e.g. ``​`\``a` ``,
where the function masks `(1,5)` correctly and the probe can only see position 4.

So this round the **delivered function is instrumented instead**: two inserted lines record the
`(content_start, content_end)` pair it is about to mask. No decision logic is touched, no CommonMark
rule is reimplemented, and both of r5's bounds disappear. Harness:
`…/scratchpad/r6/work/fuzz2.py`, driver `work/drive2.py`.

**Control before result, every time.** Each measurement below was first run against a deliberately
broken subject, and is reported only because the broken version moved:

| instrument | control | control result | real result |
|---|---|---|---|
| span fuzz | `open_start = s` (r6 M1 reverted) | **227** disagreeing inputs / 126 shapes | **37** inputs / 29 shapes, all one class |
| live verdict reach | fragment mask (r5 H2 reverted) | **124** changes, **124/124** false suppressions | **0** changes |
| live verdict reach | `BLANK_LINE` severed (r5 Codex H1) | **385** changes, **379** false suppressions | — |
| `write_config` readback | 3 manifest entries | all 3 killed **and attributed** | 9 further candidates: 6 killed, 2 no-ops, 1 real survivor |

r5 measured the fragment mask at 205 changes over 75,076 windows; I get 124 over 49,319, because my
window construction enumerates `NUMBER_RE` occurrences rather than r5's superset. **The figure differs
and the finding does not** — 124 of 124 in the same direction, so the instrument is the one that found
a real defect, pointed at this fold.

---

## Blocking

None. Both findings leave `check-withdrawal.py` able to return a wrong answer, but the guard is
warn-only unless `--strict` (#56), and neither can fire in a single live invocation of `main()`.

---

## High

### H1 — `masked_of` keys its cache on `id(text)`, and the sentence that says this is safe is false. 18 of 33 cache hits returned the WRONG document's mask across 40 real `main()` runs. INTRODUCED IN THE SUBJECT RANGE (`aee7dd8e`).

`scripts/check-withdrawal.py:235-250`:

```python
_MASKED_DOCS: dict = {}


def masked_of(text: str) -> str:
    """`mask_inline_code(text)` for a whole document, memoised by identity. r5 Claude H2.

    Every hit in one document shares one mask, and masking a large file per-hit would turn a cheap
    guard into a slow one. Keyed on `id(text)` AND length so a recycled id cannot serve the wrong
    document; the blobs are held for the whole run by the caller, so the ids are stable.
    """
    key = (id(text), len(text))
```

**The load-bearing sentence is wrong, and it is wrong in the one way that matters.** *"Keyed on
`id(text)` AND length so a recycled id cannot serve the wrong document"* — the length is exactly
what a collision has in common. `id()` in CPython is the object's address, the allocator reuses an
address for an object **of the same size**, and `len(text)` is part of that size. So the second
component of the key is not an independent discriminator; it is implied by the first. Direct probe,
400 trials over same-length/different-content document pairs:

```
trials=400  id reused=399  masked_of returned the WRONG mask=399
```

**The second half of the sentence is true but does not cover the hazard.** `main()` does hold every
document for the whole run — `blobs: list[tuple[Path, str]]` is built at `:1283` before the loop, so
within one invocation all ids are live and distinct, and I confirmed no collision is possible there.
But `_MASKED_DOCS` is **module-global and never cleared**, while `main()` is called many times per
process. The suite alone calls it through `_drive_live`, `_drive_rewrap`, `_drive_span_window` and
their siblings; after `--self-test` the cache still holds **7 entries**, so entries do outlive the
`blobs` list that justified them.

**Failure scenario, measured on the real entry point.** Two documents of equal length, one with a
leading code span and one without, driven through `main()` alternately 40 times in one process, with
`masked_of` instrumented to recompute and compare on every hit:

```
40 main() runs:  masked_of misses=7  hits=33  WRONG=18     cache size at end: 7
```

**18 of 33 hits served a mask computed from a different document.** Seven misses for forty runs is
the tell on its own: the cache is answering almost every run from another run's entry. The verdict
did not flip in this particular pair (rc=1 both arms), so the suite is green for a real reason today
— but the mask is the input to every sentence boundary in `sentence_around`, so what stands between
this and an arbitrary verdict is only that no current case's answer depends on the difference. The
length guard added to `sentence_around` this round cannot catch it: a stale mask from a same-length
document has exactly the right length and the wrong content, which is the one case the guard passes.

**Why this is worse than a wrong answer in a guard.** CI's `mutation-sweep` spawns this suite
thousands of times. A mutation's kill or survival would be decidable by allocator behaviour, which
varies with Python build and allocation history — a non-deterministic mutation harness, which is the
one property that makes every other measurement in this branch unreadable.

**Fix, verified.** `key = text`. Same file, same line. Measured both ways over the same 40 runs:

```
SHIPPED  key=(id(text), len(text)): miss=7  hit=33  WRONG=18  cache=7  6.9s   --self-test 114/114
FIXED    key=text:                 miss=2  hit=38  WRONG=0   cache=2  7.2s   --self-test 114/114
```

No wall-clock cost (str hashes are cached after first use, and masking is already O(n)), **more**
cache hits rather than fewer, and the cache collapses the two identical fixture documents to one
entry, which the id key could not. `len(text)` becomes dead and should go with it.

**Which mutations a class fix could hollow out: none.** I grepped every manifest — exactly one entry
mentions `masked_of`, and it anchors the **call site**
(`masked_win = window_around(masked_of(text), start, start + len(hit.text))`), not the function's
internals. Nothing anchors inside `masked_of`, so changing the key moves no anchor and voids no kill.

**What I ran:** the 400-trial probe; the instrumented 40-run `main()` audit; the instrumented
`--self-test` audit (2 hits, 0 wrong, 7 entries retained); the fix comparison above;
`grep -c 'masked_of\|_MASKED_DOCS' scripts/mutations/*.json`.

---

## Medium

### M1 — `mask_inline_code` pairs backticks across a markdown LIST-ITEM start, erasing the very boundary `SENTENCE_SPLIT` adds for it. Both parsers refute all 17 live instances. NOT fold-induced.

The fuzz found **37 disagreeing inputs in 29 distinct shapes** that are not fences, not indented
code and not raw HTML — and **every one of the 29 contains `\n* `**. The function's only block-level
rule is a blank line:

```python
BLANK_LINE = re.compile(r"\n[ \t]*\n")
...
        # A code span cannot contain a blank line — a paragraph break ends it.
        if BLANK_LINE.search(text[e:cs]):
```

A blank line is one of several things that end a paragraph. A list-item start is another, and
`SENTENCE_SPLIT` **already says so** — its fifth alternative exists for exactly this:

```python
    r"|\n(?=\s*(?:[|#>]|[*+-]\s|\d+[.)]\s))"      # a markdown block start; `1)` too
```

So the two rules contradict each other: `SENTENCE_SPLIT` declares `\n* ` a boundary, and
`mask_inline_code` whitens that `\n` before `SENTENCE_SPLIT` ever sees it.

**Minimal witness, a verdict flip in the lenient direction:**

```
- the `--mutate run was wrong
- it holds 1,414 anchors` today
```

```
SHIPPED (BLANK_LINE only)    masked='- the `--mutatexrunxwasxwrongx-xitxholdsx1,414xanchors` today\n'
                             history_marker -> 'was '  => SUPPRESSED as history
with a list-item rule        masked='- the `--mutate run was wrong\n- it holds 1,414 anchors` today\n'
                             history_marker -> ''      => SURVIVOR
oracles on the same text:    cmark []   markdown-it-py []
```

Neither parser finds a code span at all — two list items are two paragraphs. The shipped mask pairs
them, swallows the boundary, and the `was` in item 1 reaches the figure in item 2: **a live stale
figure reported as history**, which this function's own docstring calls "the expensive direction".

**Live reach, and the honest limit of it.** Over the 393 files `docs_files()` returns:

* **17 subject spans cross a list-item start, across 6 files** — and **17 of 17** are refuted by
  *both* parsers (checked per span against the enclosing block; 0 oracle splits, 0 agreements).
  Files include `docs/superpowers/plans/2026-06-25-dig-slide-selectivity.md` (3 spans, one of them
  103 characters of prose numbered `1.`…`7.`) and `2026-07-07-stage-1e-b-worker-summary-handler.md`.
* **559 mask bytes differ** across 10 files once the rule is added.
* **0 verdict changes.** None of the 17 lands on a figure's sentence. Compare the blank-line sibling
  at **379** false suppressions — this is the same mechanism with two orders of magnitude less live
  reach, which is why it is Medium and not High.

**Why it is Medium and not Low.** The docstring is headed **"⚠ THREE BOUNDS, STATED RATHER THAN
HIDDEN — and the third was MISSING from this list until r4 Claude L1, which is the failure mode a
caveat headed *stated rather than hidden* has"**. That heading makes a completeness claim, the list
names `A SPAN CANNOT CONTAIN A BLANK LINE` as its block-level entry, and a reader finishes it
believing block boundaries are handled. They are handled for one of at least three. An unstated bound
in a list whose own heading is about unstated bounds is the defect that list exists to prevent — and
this is the fourth consecutive round in which a hand-derived markdown rule turned out partial, which
is evidence *for* #262 rather than another rule to add.

**What I ran:** `work/drive2.py` (exhaustive over 10 tokens to length 5 + 300,000 random, 411,110
inputs) against the real function and against the r6-reverted control; the per-span oracle check over
all 393 files; `work/livereach.py` with both known positives; the witness above.

**Suggested shape of the fix**, since adding a fourth hand-derived rule is what #262 says to stop
doing: reject a candidate pair when `SENTENCE_SPLIT`'s own block-start alternative matches between
the opener and the closer — one expression, lifted from the regex that already owns the rule, rather
than a second implementation of it. ⚠ **Do not include `>` in that rule.** I tried it and it is
wrong: a `> ` line inside a blockquote is a lazy paragraph continuation, so cmark keeps the span.
That over-reach is what produced my first (false) 10-file count, caught only by opening
`docs/memory/running-codex.md:69` by hand.

### M2 — PR #371's body misstates six measured figures, and its own correction note claims they were already fixed.

Read live at 2026-10-08T14:34Z: `updatedAt=2026-10-08T13:57:36Z`, `head=e70aa551` — so this body was
written for round 6, not left over from round 5.

| PR body says | measured at `e70aa551` |
|---|---|
| L14 `--binding` — **1,534 anchors across 1,526 entries** | **1,537 anchors across 1,529 entries** |
| L48 **86 / 112 / 152 / 237 / 51** cases | **86 / 114 / 155 / 237 / 51** |
| L48 **1,526 mutations** | **1,529** |
| L50 `EXPECTED_MUTATIONS` 1408 → **1,526** at both pinning sites | 1408 → **1,529** |
| L62 **1,526** mutations over 62 manifests | **1,529** |
| L63 `--binding` reports **1,534 anchors across 1,526 entries** | **1,537 / 1,529** |

Four distinct stale figures over six occurrences. Line 60 of the body reads *"This body was written
after round 3 and stated `1,453 mutations`, `1408 → 1453`, and …"* — i.e. the body was corrected once,
to **round 5's** numbers, and round 6's fold moved all four again. The brief's item 5 states "the PR
body's three stale figures corrected"; on the live PR they are not.

This is the artifact a human merges on, and it is the only place on this branch where stated counts
have no gate: `check-withdrawal.py` and `check-provenance.py` scan `docs/`, and a PR body is not in
`docs_files()`. The guard built on this branch to catch a corrected figure still standing elsewhere
cannot see the document describing it. That observation is worth a backlog row on its own.

**What I ran:** `gh pr view 371 --json body,updatedAt,headRefOid`; the five `--self-test` runs;
`--binding`; the `EXPECTED_MUTATIONS` reconciliation.

---

## Low

### L1 — `BLANK_LINE` does not recognise a CR line ending, so a CR-written paragraph break is not a blank line. Zero live reach.

`BLANK_LINE = re.compile(r"\n[ \t]*\n")`. A second fuzz over an alphabet including `\t`, `\r` and
`\r\n` produced **8 shapes in the carriage-return class**, shortest `` `\n\r` ``: both parsers treat
`\n\r` as two line endings and report no span; `\n[ \t]*\n` does not match it, so the subject masks
across a paragraph break. Same mechanism and same lenient direction as r5 Codex H1's blank-line
witness.

**Live reach is zero and I checked rather than assumed: 0 of the 393 corpus files contain a CR at
all, and 0 subject spans contain one.** So this is a stated-bound item, not work: one clause
(`\r\n?` in the alternation) or one line in the bounds list. I note it because a CRLF file reaching
`docs/` is a Windows checkout away, and the symptom would be a silent false suppression.

### L2 — `scratchpad/r6/attrib.py` applies a weaker rule than the harness it proxies: "at least one matching red case" where `check-plan-code` requires "exactly one".

This is the soundness answer to ask (a); the verdict on the whole checker is in **SOUND** below.
`attrib.py:88`:

```python
        missing = [w for w in want if w not in names]
```

`check-plan-code.py:2688-2690` is the rule it stands in for:

```python
        unnamed = [(w, [f for f in fails if w == f]) for w in wants]
        unnamed = [(w, m) for w, m in unnamed if len(m) != 1]
```

Equality matches — that half is right, and it is the half r6 of the harness itself had to fix. What
differs is **cardinality**: an `expect` matching *two* red cases is a problem to the harness ("an
expect must name EXACTLY ONE, or it cannot show which case is the guard") and a pass to `attrib.py`.
That is the **unsafe direction** for a pre-push proxy — it reports clean where CI will go red.

Three smaller divergences, same direction or noisier:

* `rc == 0` is SURVIVED and **any** non-zero is caught; the harness requires `rc == 1` and treats
  `rc == 2` as CANNOT RUN. All four touched suites return `1 if failures else 0`, so no divergence
  today, but a suite that learned to return 2 would read as a kill here and a cannot-run there.
* `spec_from_file_location(modname, str(src_path))` sets `__file__` to the **unmutated** path while
  the mutated source is `exec`'d, so a case that reads its own source, or shells out to the real
  script, sees unmutated code and the entry reads as SURVIVED. Noisy direction, and no false survivor
  appeared in the 97-entry run.
* `tempfile.mkdtemp` per entry is never removed (1,529 leaked `attrib-home-*` directories on a full
  run), and `HOME` is restored to `""` rather than unset when it was absent.

⚠ **Stated bound: I did not establish a live instance of the cardinality gap.** Seven `expect`
strings occur more than once in their target source, but the one I opened
(`check-handoff-path.py:81,101,103`) is a single case name plus two comment mentions, so the
duplicate count is an upper bound on candidates, not evidence of one.

### L3 — `_drive_span_window`'s `trailing_span` parameter now has one live value, so its `False` branch is unexercised.

`scripts/check-withdrawal.py:1079`, with both call sites at `:1120` and `:1123` passing
`trailing_span=True`. The docstring explains why: `trailing_span=False` *was* the control, it proved
nothing, and `suppressed=True` replaced it. That replacement is right. But the parameter stayed, so
the branch it selects (`tail = " today."`) is now dead, and `check-fixture-variation` — which reads
argument *expressions* — sees one value for it. Either drop the parameter or give the `False` arm a
case that asserts something; a dead branch in a probe is how a future reader concludes the control
still exists.

---

## Checked and found SOUND

**The arithmetic table — all six claims reproduce.** Nine of the brief's figures having failed
before, I rebuilt each:

| claim | measured | ✓ |
|---|---|---|
| `EXPECTED_MUTATIONS` sums to 1,529 over 62 manifests, every per-file count matching disk | `declared sum: 1529  manifests: 62  json files on disk: 62  total entries: 1529  PER-FILE MISMATCHES: none` | ✓ |
| suites 86 / 114 / 155 / 237 / 51 | `86/86`, `114/114`, `155/155`, `237/237`, `51/51`, all rc=0 | ✓ |
| `--binding` rc=0 over 1,537 anchors / 1,529 entries | rc=0, *"1537 anchor(s) across 1529 entries"* | ✓ |
| attribution 97 entries, 0 problems over the four touched files | `attribution: 97 entr(ies) applied, 0 problem(s)`, rc=0, 42.7s | ✓ |
| CI at `aee7dd8e`: 7 of 8 shards passed; shard 6 + sweep-complete failed | `failure verify`, shards 1-5,7,8 `success`, `failure mutation-sweep (6)`, `failure mutation-sweep-complete` | ✓ |
| 422 insertions / 94 deletions over 7 files | `7 files changed, 422 insertions(+), 94 deletions(-)` | ✓ |

Both `EXPECTED_MUTATIONS` pinning sites agree at 1,529 (the dict sum and the `case(...)` literal at
`:5592`), and the per-file comment arithmetic checks out: `28 + 2 - 1 + 1 = 30` for
`check-withdrawal.py` and `18 + 1 + 2 = 21` for `codex-frontier-model.py`, both matching disk.

**CI at HEAD is BETTER than at `aee7dd8e`, and the r6 fix is why.** Run `37788537409` on `e70aa551`:
all eight `mutation-sweep` shards **and** `mutation-sweep-complete` are `success`. The unattributed
kill is genuinely gone, not moved. `verify` is still red, and **for a different reason than r5's** —
`check-review-recorded` has gone green and the failing step is now `check-review-rounds`:
*"✗ backlog-249-260 round 6: only codex — claude neither ran nor recorded a `REVIEW GAP:` line"*.
This file closes it. ⚠ "the sweep is green" still must not be read as "CI is green".

**R6 M1 — the opener-truncation loop holds.** 411,110 inputs, exhaustive over
`` ` ``/`` `` ``/`\`/`a`/space/newline/`<`/`>`/`*`/`[` to length 5 plus 300,000 random of length 6-12,
compared against cmark **and** markdown-it-py with disagreement counted only where the two oracles
agree with each other. Outside the three deferral classes (fences, indented code, raw-HTML/autolink
precedence) the only disagreements were M1's list-item class. The control, `open_start = s`, produced
227 inputs in 126 shapes including the exact r6 witness (`\``a` → subject none, oracles `['a']`), so
the instrument was demonstrably able to see this defect class and did not see a new one.
The r6 comment's own stated parser result reproduces exactly:
`the count was \``v1:\n2` and 1,414 today` → cmark `['v1: 2']`, markdown-it-py `['v1: 2']`,
subject span `(17,22)` = `'v1: 2'`.

**R6's HEAD refutation is correct — this is the answer to ask (b).** Running `git rev-parse --verify
<span>^{commit}` on `m.group(0)` over 126 token/base combinations:

* `at HEAD~?` → span `HEAD~` → rc **0**; `at HEAD~!` → span `HEAD~` → rc **0**. The `?`/`!` are
  outside the match. **The refutation stands and the previous round's Low was not a defect.**
* **18 tokens** are where the typed-token oracle and the matched-span oracle disagree — and all 18
  are punctuation the regex never matched. That is the trap, reproduced, three times larger than the
  three instances the comment names.
* **7 spans the regex accepts are not commit-ish in this repo** — `HEAD^2`, `HEAD~^2`, `HEAD~1^2`,
  `HEAD^^2`, `HEAD^1^2`, `HEAD~99999`, `HEAD^99999`. Every one is **syntactically valid rev syntax
  that does not resolve here** (HEAD has no second parent; the repo has fewer than 99,999 commits),
  which is the limitation the comment already states for `HEAD^2`. Not a finding, and importantly not
  a fourth instance of the wrong-oracle shape: the oracle is right and the *repo* is the limit.
* `HEAD@{1}` is refused, rc=0 on the token — exactly as r5 L3's pinned STATED BOUND case says.
* Bare `HEAD` is unmatched by the suffixed arm, so the r2 Claude HIGH mutation's subject is intact.

**`attrib.py` is sound in the respect it was built for — ask (a).** It applies each entry to the
delivered source, refuses an anchor that does not resolve exactly once, `compile()`s before running
so a SyntaxError is distinguished from a kill, wraps the suite in `except BaseException` so a crash
is reported as *"the suite died, so NOTHING COULD SEE THE KILL"* rather than counted as a pass, and
redirects `HOME` to a temp dir to match `child_env`. It **imports** `parse_fail_names` from the
harness instead of re-deriving the `[FAIL]` contract, and it uses the same equality rule. That is
precisely the class `--binding` cannot see — a stale *replacement* rather than a stale anchor — and
the checker catches it. The string-vs-list `want` coercion is correct and the comment explaining why
(iterating a string yields characters) records a real self-inflicted wound. Divergences are L2.

**The `tomllib` readback kills more than the brief claims, and the two survivors are no-ops.** I
applied twelve candidate `write_config` defects to the delivered source and ran the file's own
`_self_test()` on each, checking separately what bytes each one actually writes over the `keep`
fixture:

* the three manifest entries (discard-everything, block-after-existing, block-written-twice) are all
  **killed and attributed to the case they name**;
* **killed, and not covered by any manifest entry:** dropping `re.DOTALL` from the strip; removing
  the strip entirely; losing the `BEGIN` marker; losing the trailing newline after `END`; dropping
  `exist_ok=True`; renaming the `model` key;
* **two apparent survivors are NO-OPs** — making the strip regex greedy, and removing
  `existing.lstrip("\n")` — both write byte-identical output to the control over this fixture, so
  they measure nothing. (The brief's own trap, caught by checking the bytes rather than the verdict.)
* **one real survivor, cosmetic:** deleting the `# Do NOT hand-edit the slug` comment from the
  managed block. The readback asserts the parsed document, so a lost comment is invisible. Worth a
  sentence in the arm's docstring as its stated bound; not work.

So the answer to "what could a wrong `write_config` still do that all three miss" is: write a
correct TOML document with the wrong *prose* in it. The parse-don't-grep change is right, and the
`keep` fixture's shape (`[profile]` first) is what makes clause 2 catch the ordering defect — note
that an existing file of top-level keys with no table would hide that shape.

**`main()`'s `blobs` really is held for the whole run** (`:1283-1288`, built before the loop), so H1
cannot fire in a single live invocation. I verified this rather than taking the docstring's word for
it, and it is the reason H1 is High and not Blocking.

**Sibling guards are green, both as suites and against the tree.** `--self-test`:
`check-fixture-variation` 67/67, `check-selftest-counts` 18/18, `check-ratchet-contract` 56/56,
`check-producer-enumeration` 11/11, `check-docs` 22/22, `check-anchors` 15/15,
`check-review-rounds` 77/77. Live: `check-fixture-variation` rc=0 (*914 parameters across 67 files*),
`check-selftest-counts` rc=0 (*55 scripts declare a count, every one verified by running it*),
`check-docs` rc=0, `check-anchors` rc=0 (*floor 22 held*). The three-signature `masked=` threading
broke no sibling.

**Backlog #265 is filed** (`docs/backlog.md:280`), states its own FAILS-IF, and marks its proposed
fix UNVERIFIED — including the sharper note that reversing the sort is a second instance rather than
a fix. Nothing to add.

---

## CANNOT RUN

* **`--mutate .` locally — NOT MEASURED, and deliberately not attempted.** Local shards time out, so
  a run would produce NOT MEASURED dressed as a result. CI covers it and is **green at HEAD on all
  eight shards plus `mutation-sweep-complete`**, which is the stronger evidence anyway. My
  `attrib.py` runs are a *proxy* for attribution only, not a substitute for the sweep.
* **The full-repo attribution sweep did not finish inside this review.** `python3.12 attrib.py .`
  over all 1,529 entries was still running after 32 minutes of CPU (1.4 GB RSS, in-process module
  accumulation) when I stopped measuring. **So the brief's question "is any OTHER entry in the repo
  unattributable for the same reason?" is UNANSWERED by me — treat it as NOT RUN, not as a clean
  sheet.** What *is* answered: the four touched files are clean (97/97), and CI's real sweep is green
  at HEAD across every shard, which covers the whole population by the authoritative instrument. The
  honest residual is that nothing local has confirmed it per-entry.
* **The docstring's 597 span-level disagreements across 121 files (fence deferral) did not
  reproduce, and I am NOT reporting that as a defect.** My instrument counts a different unit:
  subject spans lying inside a fenced block (1,834 across 106 files, with a crude fence-state
  detector that ignores info strings, tilde fences and indentation), whereas r5's figure counts
  differing entries in an ordered content-sequence comparison. Two different quantities, so mine is
  not a refutation of theirs. Re-measuring it would need the fence state done properly, which is
  #262's job.
* **`test:integration` and `test:e2e`** — need a live Supabase stack; not run, per
  `docs/dev-process.md`.
* **The 14 retargeted manifest entries were not re-verified individually by hand.** `--binding` rc=0
  proves all 1,537 anchors resolve to exactly one site (the *binding* half) and `attrib.py` proves
  the four touched files' 97 entries kill via the case they name (the *killing* half for those
  files). The round-6 replacement fix is confirmed by CI shard 6 going from `failure` to `success`.

---

**Round 6's own fold: no Blocking, no High.** The one High is in `aee7dd8e`, the other half of the
subject range, and it is a false sentence in a docstring guarding a cache key — not a markdown rule
re-derived by hand, which is the pattern that produced the previous seven. M1 is the fourth partial
hand-derived markdown rule and belongs to #262 rather than to a fifth rule. If H1's one-line fix and
M2's body edit land, I would expect round 7 to be the second clean round.
