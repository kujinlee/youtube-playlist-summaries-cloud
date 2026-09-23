# Claude adversarial review — observer-log-owner, round 2

**Date:** 2026-09-23. **Reviewer:** Claude (Opus 5), adversarial mandate — instructed to REFUTE.
**Subject:** the **WORKING TREE** of `observer-log-owner` — `git diff HEAD` plus `git diff master...HEAD`.
`b360f7cf` is the tip; `scripts/check-banner-armed.py` carries one **uncommitted** change (the M9 fold).

⚠ **THE CODEX HALF OF THIS ROUND REVIEWED THE TREE *BEFORE* THE M9 FOLD.**
`docs/reviews/codex/observer-log-owner-r2-codex.md` reviewed committed `HEAD`. The delegation of
`_log_flush` to `observer_log.append` and the `encoding="utf-8"` on the `WARN_LOG` write were
folded after it ran, so **no Codex pass has seen them.** Everything in §M9 below is single-reviewer.

**Verdict: 2 Blocking, 3 High, 3 Medium, 3 Low.** No category is empty.

---

## What I verified GREEN, by running it

| Check | Result |
|---|---|
| `observer_log --self-test` | **39/39** — matches the docstring's declared 39 |
| `check-banner-armed --self-test` | 159/159 (working tree, with M9) |
| `check-ci-watched --self-test` | 57/57 |
| `check-closing-table --self-test` | 153/153 |
| `check-fixture-variation --self-test` / live | 67/67 · 635 parameters over 58 files, OK |
| `check-ratchet-contract --self-test` / live | 41/41 · 40 guards, OK |
| `check-selftest-counts --self-test` / live | 18/18 · 46 scripts declare a count, all verified |
| `check-plan-code --self-test` | 128/128, including `sum(EXPECTED_MUTATIONS.values()) == 966` at `:3453` |
| `check-docs` / `check-anchors` / `check-vocabulary-collisions` / `check-dashboard-entry` | OK |
| `check-review-rounds` | correctly FAILS on "round 2: only codex" — **this document is that half** |

**Pins, counted off disk, not read off prose:** `check-banner-armed` **47**, `check-ci-watched`
**27**, `check-closing-table` **46**, `observer_log` **15**; 53 manifests summing to **966**, which
equals the pinned sum. Master's counts are 47 / 29 / 47, so the fall is `47→47`, `29→27`, `47→46`.

**Every anchor resolves exactly once against the working tree** — 974 `find` strings over 966
entries, 0 that resolve zero or twice. In particular the M9 edit orphaned nothing: it deleted six
lines from `_log_flush` and no manifest entry was anchored in them.

### H4 — the three `flush_line` anchors are genuine. Verified one at a time.

Applied each mutation to an isolated copy and ran the suite. Control 157/157 (a scripts-only tree
runs two fewer cases than the repo's 159 — the reachability case degrades to NOT CHECKED; that is
the tree, not the mutation).

| Mutation | Result | Failing case |
|---|---|---|
| `counts = (before, after)` → `(1, 2)` | 156/157 | **exactly** `R5-646 flush_line carries BOTH measured counts…` |
| `stamp = when` → `stamp = "T"` | 156/157 | **exactly** `R5-646c …and its TIMESTAMP column…` |
| `record(session, …)` → `record("fl-text", …)` | 156/157 | **exactly** `R5-646b …and its session column too` |

One case each, each the case the entry names, none killed by crash. The three properties are
genuinely independent. **The fix for Codex's Blocking is real.** (What is *not* real is the stated
reason for the code shape it produced — High 1.)

### H5, M7, B2/H3 — verified

- **H5.** `append claims success on a failed write` (`except OSError: return True`) → **38/39**,
  failing only `append returns False on OSError rather than raising`. Clean failure via its named
  case, no crash, no later case hidden.
- **M7.** All four producers call `observer_log.now()`: `check-ci-watched.py:393` and `:435`,
  `check-closing-table.py:931`, `check-banner-armed.py:973` and `:1186`. No `strftime`/`isoformat`
  remains in any producer. **`begin-plan.py:284` is correctly out of scope** — it stamps
  `.claude/executing-plan`, a `key: value` sentinel parsed by `check-plan-progress.parse_sentinel`.
  Different grammar, different consumer, and it *has* a reader, which none of the four logs do.
- **B2/H3.** The shape cases now assert the literals `"v1"` and `"-"`. I mutated `SEP = "\t"` →
  `"|"` to test the remaining subject-derived reads (`r.split(SEP)`): **36/39**, killed by `col
  strips a TAB` and both `col is not a constant` cases. The `SEP` self-reference is therefore not
  load-bearing. One residual instance survives — Low 1.
- **The docstring's drift evidence is true.** I opened the three generations:
  `banner-warnings.pre-backlog96.log` → `… ⇥ STEP 4 of 5 ⇥ unarmed` (detail, reason);
  `banner-warnings-archived-2026-09-06.log` and the live log → `… ⇥ unarmed ⇥ STEP 3 of 4`
  (reason, detail). The inversion is exactly as `observer_log.py:20-21` states.
- **"Four writers and zero readers" still holds.** `grep` over `*.py *.sh *.yml *.ts *.js` for the
  four log filenames returns only the four `*_LOG` globals and self-test redirections. Nothing parses.
- The four producer signatures listed at `observer_log.py:9-12` all match the live code. `39 cases`
  at `:4` is right. No stdlib name collision from the three new `sys.path.insert(0, scripts/)` lines
  (measured: zero overlap between `scripts/*.py` stems and `sys.stdlib_module_names`), and the idiom
  is already used by 19 scripts here.

**⏳ The full `--mutate .` sweep is running as I write and had reached 289/966 with no survivor.
It is NOT complete, so I do not claim 966/966 — see "What I could not finish".**

---

## Blocking

### B1 — the withdrawal is half a withdrawal: the ratchet's own reason still states the numbers it withdrew

`scripts/check-plan-code.py:571-590`. The fold's stated remedy for Codex's Blocking was *"the false
equivalence is **WITHDRAWN** in `check-plan-code.py`'s comment rather than quietly corrected"*. Two
sentences in that comment were not withdrawn with it, and both are now false:

- **`:571-574`** — *"5 anchors stopped resolving because **THE CODE THEY NAME IS GONE**, moved into
  `scripts/observer_log.py`"*. Only **three** did. For the two withdrawn entries the code they name
  is **not** gone: `flush_line` still exists, and they were retargeted onto it at `:669-671`. The
  header states the pre-withdrawal count as a fact and the withdrawal sits four lines below it.
- **`:589`** — *"Net: **47->45**, 29->27, 47->46, and **+14** for the new owner."* Measured off
  disk: banner is **47** (and `:591` pins 47), observer_log is **15** (and `:602` pins 15). Two of
  the four numbers in the summary line are the numbers this round withdrew. The corrections exist —
  `:581` says `45 -> 47`, `:598` says `14 -> 15` — but the line a reader would size the fall from
  contradicts both, three lines above the dict that refutes it.

The commit message gets this right (*"⚠ NET: of the five original retirements only THREE were
genuine. 47->45 becomes 47->47"*). **The correction landed in the commit message and not in the
file.** `check-plan-code.py`'s comments are the only written justification a ratchet fall has; a
justification that disagrees with its own pins is not a justification. This is the round-1 shape
recurring inside the fix for it — the `#110` pattern this repo has already paid for.

**Fix:** rewrite `:571` to say three, and `:589` to `47->47, 29->27, 47->46, +15`, or delete the
summary line — the per-file comments already carry the numbers and a second copy of a total is what
`:3302` calls "the failure this case exists to catch".

### B2 — the reader-facing record states four things the branch has since falsified, and claims four backlog rows are closed that are still OPEN

`docs/dashboard-entries.md`, the `## 2026-09-23` block (added in `088649a6`, untouched by
`b360f7cf`). This is the artifact a person who was away reads, and it is regenerated into the
dashboard page. Measured against the working tree:

| The entry says | The tree says |
|---|---|
| `964 mutations, 964 killed, 964 attributed … 0 survivors` | the pinned sum is **966** (`check-plan-code.py:3453`) |
| `Ratchet fall 47→45, 29→27, 47→46 with +15` | **47→47**, 29→27, 47→46, +15 |
| `five anchors RETIRED WITH THEIR SUBJECT` | **three**; two were un-retired and retargeted |
| `⚠ NOT CONVERGED — round 2 is owed for M9` | M9 is folded; round 2's Codex half ran and filed a Blocking |
| `Closes #166, #170, #168, #169` | all four rows in `docs/backlog.md` still read 🟡/🟢/🟠 **OPEN** |

The last row is a merge-gate violation on its own terms: `docs/dev-process.md` Phase 5 — *"Write the
merge tick BEFORE opening the PR"*, *"Roadmap/backlog status ticks ride in the **same PR** as the
work they describe"*. `check-backlog-closure.py` is warn-only and reads **merged** subjects, so
nothing will catch this before merge — which is precisely backlog #98's finding ("five shipped that
way, none caught by a machine"). The other four rows are the same class as B1: a second copy of a
number, in the place a human actually reads, left behind when the number moved.

**Fix:** update the entry to 966 / 47→47 / three, replace the NOT-CONVERGED paragraph with round 2's
outcome, and tick #166, #168, #169, #170 in `docs/backlog.md` in this branch.

---

## High

### H1 — `stamp = when` exists to satisfy a harness rule the harness does not have. I measured it.

`scripts/check-banner-armed.py:663-668` justifies splitting `flush_line` into three statements:

> *"Each line now carries one property, so each can be mutated independently."*

and the fold document states the premise outright
(`docs/reviews/codex/observer-log-owner-r2-codex.md:46-47`): *"the harness refuses two entries that
share one [anchor]"*. `scripts/observer_log.py:84-87` makes the identical claim about `col`:

> *"Folded into one line they share an anchor, and the mutation harness refuses two entries with the
> same anchor because the second measures nothing new."*

**The harness refuses two entries with the same anchor TUPLE, not two anchors on the same line.**
`load_manifests` at `check-plan-code.py:1166` computes `anchors = tuple(f for f, _ in e["edits"])`
and refuses only an exact repeat. I built a fixture with three entries anchored on three different
substrings of one line — `record(session,` / `before, after` / `when=when` — and ran `load_manifests`
on it:

```
entries accepted: 3
problems: []
```

`check-plan-code.py:1172-1176` says so in its own words, 500 lines below the code being justified:
*"Two entries aimed at the SAME behaviour clear this rule simply by shortening one anchor to a
different substring of the same line, which is exactly what r11's repair did (legitimately)."*

So `stamp = when` — a pure alias that ships in a guard — was written for a constraint that does not
exist. The single-expression form could have carried all three anchors. This is not cosmetic: it is
a **comment asserting a property the code lacks**, which `check-plan-code.py:1191-1194` itself names
as *"this branch's signature defect"*, and it is now written in three places including a committed
review document.

**Fix:** correct all three sentences to say what the rule is (identical anchor tuples are refused),
and state the real reason for the split if one is wanted — *readability of the anchors* is a
defensible reason; *the harness requires it* is not. Whether to collapse `stamp = when` back is a
judgment call; the mutations bind by text and would need retargeting either way.

### H2 — `VERSION` is a marker with no reader and no bump trigger; the docstring calls it "the load-bearing part"

`scripts/observer_log.py:25-26`: *"That is why `VERSION` below is the load-bearing part of this
module and the sanitiser is the cheap part."* `:35-36`: *"a per-record token makes backlog #170's
own falsifier **trivial** — concatenate two generations and the boundary is visible on EVERY line."*

What ships does less than that:

1. **Nothing reads it.** The module says so honestly at `:44` (*"It does not parse"*), so the marker
   cannot itself detect anything today.
2. **Nothing makes it move.** `:53-54` is a comment — *"⛔ BUMP THIS ONLY WHEN THE COLUMN MEANINGS
   CHANGE"* — with no guard behind it. There is no recorded declaration of what v1's columns *mean*,
   so no check can compare an adapter's emitted order against one. A deliberate reorder of any
   adapter's payload leaves `VERSION` at `"v1"` and produces exactly #170's defect inside one version.
3. **It only separates pre-v1 from v1.** The two generations that actually inverted are *both*
   pre-v1 and both unmarked; `:38-40` handles that by declaring them incomparable, which is honest
   but is a different thing from the falsifier at `:35-36`.

**What actually catches a column reorder on this branch is the adapters' own self-test cases, not
`VERSION`.** Measured: swapping `reason` and `detail` in `check-banner-armed.log_line` kills **7 of
157** cases. That is the real mechanism, and the docstring credits the wrong one.

I am not arguing the marker should go — a per-record token is the right shape and it is cheap. The
finding is that the module's headline claim is stronger than what it delivers, in the one paragraph
a future maintainer will use to decide whether the marker can be trusted.

**Fix:** either demote the claim to what is true (*"it makes a FUTURE reader able to refuse a record
it does not understand; nothing bumps it today"*) or file the missing half — a declared column
vocabulary per adapter plus a guard that reds when the emitted order disagrees with it.

### H3 — M9 was fixed as an instance; the class is still open, and two hand-rolled writes remain

M9's defect was *a hand-rolled write drifting from the shared one* (`FLUSH_LOG.open("a")` with no
`encoding=`). The fold delegated `_log_flush` to `observer_log.append` and hand-added
`encoding="utf-8"` to the other write. **Two hand-rolled writes are still in the tree**, each with
its own `mkdir(parents=True, exist_ok=True)` + `open("a", encoding="utf-8")`:

- `scripts/check-banner-armed.py:1191-1193`
- `scripts/check-ci-watched.py:415-417`

Both keep their own write for the same stated and correct reason: they interpolate `{e}` into the
warning text (`:1195-1197`, `:419-424`), and `observer_log.append` returns a bool that discards it.
So the module's API is what forces the duplication. Nothing prevents the next such write from
omitting `encoding=` again, and nothing would notice — which is M9 verbatim.

**Fix:** have `append` return `OSError | None` (or add `append_or_raise`). All four sites then
delegate, `mkdir` exists once, and the two callers that want the exception text get it. The
"deliberately keeps its own write" comments become unnecessary rather than carefully argued.

---

## Medium

### M1 — a third `check-ci-watched` entry was removed, the account says five removals, and six were removed

Diffing manifest entry names master→branch: **6 removed, 3 added** (banner 2 of each — renames with
retargeted anchors; ci 3 removed / 1 added; closing 1 removed). `check-plan-code.py:575-585` lists
**five** retirements. The sixth is `check-ci-watched`'s *"the log line drops its SESSION column, so
entries stop being attributable to a session"*, replaced by *"the log line drops a PAYLOAD column"*
and folded into `:586-588`'s *"THREE were RETARGETED … ci log_line's column count"*.

Calling that a retarget is loose. The removed entry's property was *this adapter passes `session`
through*; the new entry's is *this adapter emits its payload fields*. Those are different, and the
difference is **exactly what Codex's Blocking established** — the adapter owns passing its own
arguments through, and that property has its own owner. Having accepted that for `flush_line`, the
same search was not run over the siblings: **neither `check-ci-watched.log_line` nor
`check-closing-table.log_line` now has a manifest entry for session-passthrough or
timestamp-passthrough.**

The properties are not *uncovered* — I mutated all four and the suites catch them:

| Mutation | Suite result |
|---|---|
| ci `log_line` freezes session | 49/57 |
| ci `log_line` freezes `when` | 56/57 |
| closing `log_line` freezes session | FAIL `log: an empty session degrades to '-'…` |
| closing `log_line` freezes `when` | FAIL `log: the timestamp is the SECOND field…` |

So this is a ratchet/bookkeeping finding, not a coverage hole. But the ratchet is what proves the
cases can fail, and the written account of the fall is off by one entry and mislabels the one it
does mention. Same root as B1.

**Fix:** say six, and describe the ci change as a *replacement* with the reason ("session is now the
shared module's positional 3, so the adapter's remaining property is its payload"). Optionally add
the two session-passthrough entries for the siblings, which would make the class fix complete.

### M2 — the #168 remedy is an untested sentence

`scripts/check-dashboard-entry.py:851-854` adds the instruction *"you must then PUSH something — CI
reads the body from the frozen event payload"*. `:846-848` argues this is where the remedy belongs
*"because the reader actually sees it"*, and the `ci.yml` comment (`:447` block) explicitly calls
itself "the cheap half".

There is **no self-test case asserting that sentence and no mutation entry for it**; the pin stayed
at 43 (`check-plan-code.py:760`) and the suite is 148/148 either way. The load-bearing half of #168
is the half nothing measures, so a later message rewrite deletes it silently. This repo's own rule
for it is at `check-plan-code.py:555-560` — *"the new entry guards the OBSERVATION LINE'S CONTENT,
not whether a line appeared"* — written about this same class one manifest over.

Also worth stating: #168 is a different backlog item from the observer-log slice, folded into this
branch. That is defensible batching, but it means the branch's one untested behaviour is the one
whose subject nobody was reviewing.

**Fix:** one case asserting the push clause is present in the refusal, one mutation deleting it,
pin 43 → 44.

### M3 — the two backlog rows filed on this branch quote a live count the same branch moved

`docs/backlog.md` rows **#173** and **#174** (added in `088649a6`) say *"measured over the **964**
live mutations"* and *"carry **488 of 964** mutations (51%)"*. `b360f7cf`, on this branch, moved the
total to **966**. Row **#170**, three rows up and written the same day, warns: *"⚠ Live counts move
under you … do not quote a live count without re-measuring it."*

The percentages barely move and neither row's argument changes. It is Medium because of where it
sits — a backlog row is the input to a future sizing decision, and this is the third instance on
this branch of a number left behind by its own subject (B1, B2, this).

**Fix:** re-derive from `sum(EXPECTED_MUTATIONS.values())` at the moment the PR opens, or say
"≈960" and cite the run id.

---

## Low

### L1 — one assertion still derives its expected value from the subject, two lines under the comment condemning it

`scripts/observer_log.py:226-227`:

```python
case("record defaults `when` to a real stamp when omitted, not to the sentinel",
     record("s", "f").split(SEP)[1] not in ("", EMPTY, "T1"), True)
```

`EMPTY` is the constant under test, and `EMPTY = ""` is mutation 9 in this file's own manifest. It
is **benign**: the mutation is killed at `:210` (`an empty session becomes the sentinel`, literal
`"-"`), and under the single-mutation model the tuple degrading to `("", "", "T1")` cannot hide
anything. But this is the exact class B2/H3 were filed for, the ⛔ comment at `:221-222` condemns it,
and the case was written *by* that fix. Write `"-"`.

### L2 — only one of the three adapters pins the literal `"v1"`

- `check-ci-watched` does: `== ["v1", "T1", "s1", …]` (`:590-594`).
- `check-closing-table`'s case is *named* `log: the record carries a version cell plus FOUR payload
  fields` but asserts `len(split("\t")[1:]) == 4` — it asserts a fifth cell exists, not that it is a
  version cell. A record that dropped `v1` and gained a payload field passes it. The name also calls
  `when` and `session` "payload", which the module's own vocabulary does not.
- `check-banner-armed` has no version assertion at all; `:1334` was silently reindexed `[1:]` →
  `[2:]` with no comment, while the equivalent closing-table reindex got a three-line paragraph
  explaining itself (`:1356-1358`). Inconsistent treatment of the same edit.

Nothing is wrong today — `observer_log`'s own suite pins the literal in two cases. It is a Low
because the round's headline lesson was *assert at the layer that owns the property*.

### L3 — the M9 fold is uncommitted

`git status` shows `scripts/check-banner-armed.py` modified. The committed tip `b360f7cf` still has
the old `_log_flush` with `FLUSH_LOG.open("a")` and no encoding. Everything in this review's M9
section describes the **working tree**. If the PR is opened from the tip as it stands, the fix this
round exists to review is not in it.

---

## What I could not finish

**The full `--mutate .` sweep did not complete inside this review.** I started
`python3 scripts/check-plan-code.py --mutate .` in the background; it had passed 289 of 966 with no
survivor when I finished writing. Per backlog #173 it takes 8m12s in CI and considerably longer
locally. **Treat "966/966 killed" as NOT RE-VERIFIED BY ME** — what I did verify by hand is that all
974 anchors resolve exactly once against the working tree, that the four pins and the declared sum
match the manifests on disk, and that the three `flush_line` mutations and the `append` mutation
each kill via exactly the case they name. The commit message's `966/966/966/0` claim is unaudited by
this half.

I also did not attempt an end-to-end run of the Stop hooks against a live transcript; all producer
behaviour above was exercised through the suites and through direct calls.
