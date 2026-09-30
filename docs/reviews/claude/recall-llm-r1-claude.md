# The LLM recall matcher (backlog #191) — round 1, Claude adversarial half

**Subject:** `semantic-recall-replication` (`git diff master...semantic-recall-replication`,
12 files, +3356).

⚠ **Tree identity, because the branch moved under me.** The brief named 5 commits off `master` at
`446025ab`; while this review was running two more landed (`3e853d05`, `3789d13c`), so the tip is
now `3789d13c` at **7**. `git diff --stat 4d1e7b46..HEAD` is `docs/backlog.md | 1 +` — backlog rows
for #194 only. **Every file under review is byte-identical between the briefed tree and the one I
measured**, and every measurement below was taken against `3789d13c`.

**Verdict: NOT CONVERGED — 1 Blocking, 4 High, 5 Medium, 8 Low.**

The Blocking is the refuted matcher's own H3, reproduced in the replacement, in the only mode the
hook ever runs, on a plan shape this repository has dozens of committed examples of. It was found by
running `--fire`, not by reading it.

Everything below was verified by execution unless a finding says otherwise. Worlds were built under
`$SCRATCH/` with `ROOT` and `HOME` redirected; the repository was not modified.

**What ran green:** `--self-test` 128/128 with the declared count matching (`recall-llm.py:78`);
`check-fixture-variation.py`, `check-selftest-counts.py`, `check-ratchet-contract.py`,
`check-docs.py`, `check-review-rounds.py`, `check-dashboard-entry.py`, `check-anchors.py` all rc=0;
`peer-sites.py --diff master` reports no partially-touched containers across the 4 changed Python
files; `check-review-decision.py` reports `ROUND_OWED  scope=full-loop  rounds=0`, which this
document answers. `check-plan-code.py --mutate .` — see *Mutation sweep* at the end.

---

## BLOCKING

### B1 · `do_fire` never applies `plan_verdict` — a plan it cannot parse is a silent `rc=0`, and a plan it can only PARTLY parse surfaces the wrong lesson

**What is wrong.** The rc contract (`scripts/recall-llm.py:56-73`) states that "a plan with no
recognisable step" is `rc=2 CANNOT RUN`, and `plan_verdict` (`:162-176`) is the pure function that
decides it. **`do_fire` never calls it.** The only thing `do_fire` asks of the plan is
`first_unticked(plan_text)` (`:692`), and that function returns `None` for *two* different worlds:

```
scripts/recall-llm.py:692-694
    step = first_unticked(plan_text)
    if step is None:
        return OK  # every box ticked: also an answer.
```

`first_unticked` (`:179-184`) iterates `_BOX_RE` matches. A plan whose checkboxes do not match
`_BOX_RE` produces **zero** matches, so it returns `None` by the same route as a finished plan, and
`do_fire` reports `OK` in silence. `prepared_prompt` (`:645-657`) does call `plan_verdict`, which is
why `--arm` and `--print-prompt` refuse correctly — but the hook runs **only** `--fire`
(`.claude/hooks/surface-recall.sh:35`).

**The failure scenario, measured.** `_BOX_RE` (`:133`) requires `**Step N of M**`. `begin-plan.py`
generates that shape (`begin-plan.py:174`) but its *own* parser does not require it —
`begin-plan.py:86` is `^- \[( |x)\] (.*)$`, and its comment at `:197` says so out loud: *"A REAL
implementation plan writes `- [ ] **Step 1: Write the tests**`"*. `cmd_plan`
(`begin-plan.py:327-341`) arms any in-repo markdown file with no shape check at all.

So: arm a committed implementation plan, then fire.

```
plan file:  - [ ] **Step 1: Write the tests**
              - **Doing:** writing the failing tests for the parser

--print-prompt  ->  RC=2  "CANNOT RUN: the plan file carries no recognisable
                           `- [ ] **Step N of M**` step, so nothing was matched."
--fire          ->  RC=0  (no output)
```

The hook then discards it: `rc=0` with output not containing `⭐ recall —` falls through
`surface-recall.sh:41` and `[ -n "$PAYLOAD" ] || exit 0` at `:48`. Nothing is said, by anything,
ever. **"nothing fires" and "could not look" are the same observation at the reader** — which is the
sentence at `recall-llm.py:56` and the H3 the replacement exists to remove.

**Reachability is current, not hypothetical.** `docs/superpowers/plans/` holds committed plans in
exactly this shape, e.g. `docs/superpowers/plans/2026-06-18-summary-deepdive-quality.md:49`
(`- [ ] **Step 1: Write the failing tests**`). Every one of them is armable and tickable.

**And the partially-parseable case is worse than silence — it surfaces the WRONG lesson.** The two
parsers disagree on more than the `N of M` form. Measured, one line per row:

| the step line | `begin-plan.py` | `recall-llm.plan_steps` |
|---|---|---|
| `- [ ] **Step 3 of 5** — Title` (generated, em-dash) | ✅ | ✅ |
| `- [ ] **Step 3 of 5** - Title` (plain hyphen) | ✅ | **dropped** |
| `- [ ] **Step 3 of 5** – Title` (en-dash) | ✅ | **dropped** |
| `- [ ] **Step 3 of 5: Title**` | ✅ | **dropped** |
| `- [X] **Step 3 of 5** — Title` (capital tick) | dropped | **dropped** |
| `  - [ ] **Step 3 of 5** — Title` (indented) | dropped | **dropped** |

An em-dash is a deliberate keystroke, so a hand-edited step is more likely than not to carry a
hyphen. When a plan mixes shapes, `first_unticked` **skips the box it cannot see and returns a later
one**, and the cached answer for that later situation is served at the current moment. Measured on a
plan whose outstanding box is `- [ ] **Step 2: the step I am actually on**` (situation GAMMA), with
a parseable `**Step 2 of 2**` (situation BETA) below it:

```
plan_steps      -> [(1, 'situation ALPHA'), (2, 'situation BETA')]   # GAMMA is gone
plan_verdict    -> (0, '')                                           # accepted
first_unticked  -> 2                                                 # points at BETA
--fire          -> RC=0
   ⭐ recall — this moment matches a recorded lesson:
      lesson-for-beta
      FIRES-WHEN: situation BETA          <- the reader is standing at GAMMA
```

That is the design's own most expensive failure, stated in its own prompt at `:311-313`: *"A wrong
lesson costs more than no lesson, because it spends the reader's willingness to look at this channel
at all."*

**Siblings searched.** `grep -n` over `recall-llm.py` for `plan_verdict` call sites: exactly two —
`prepared_prompt:653` and the self-test. `do_arm` reaches it through `prepared_prompt`; `do_fire` is
the only entry point that does not. Same question asked of `corpus_verdict`: reached only from
`read_corpus:639`, which `do_fire` also never calls — but `cached_entry_verdict` (`:705`) covers the
corpus side for `--fire`, so that one is fine. **The plan side has no equivalent.**

**What would prove this finding wrong:** a run of `--fire` against a sentinel naming a plan whose
checkboxes `_BOX_RE` cannot match that exits non-zero; or a demonstration that `begin-plan.py`
refuses to arm such a plan.

**Note on the shape of the fix.** Calling `plan_verdict` in `do_fire` closes the all-silent half but
**not** the mixed half — a mixed plan has a non-empty step list with non-empty situations, so
`plan_verdict` passes it (measured above). The two parsers disagreeing at all is the defect; one of
them has to own the grammar. `begin-plan.py:86` is the looser and the one that arms and ticks, so it
is the natural owner.

---

## HIGH

### H1 · Seven paths exit **1** — a code the rc contract does not define — and the hook swallows all of them; one of them loses a genuine match

**What is wrong.** `parse_cache`'s docstring (`:470-473`) records that the rc contract *"had a
hole"* where a bad cache escaped as a traceback and *"the process exited **1** — a code this file's
docstring does not define, from the one script whose whole thesis is that every outcome is named."*
The hole was closed for **JSON** malformation only. It is open for encoding, for cache shapes below
the top level, and for the filesystem.

Measured, each in its own built world:

| # | input | line | rc | mode |
|---|---|---|---|---|
| a | a memory file whose `description:` is not valid UTF-8 | `:262` `p.read_text(encoding="utf-8")` | **1** | `--arm` / `--print-prompt` |
| b | a cache file that is not valid UTF-8 | `:699` `cache_file.read_text(...)` | **1** | `--fire` |
| c | `"picks": 5` in the cache, fingerprint correct | `:703` → `lookup:496` `key not in picks` | **1** | `--fire` |
| d | `"triggers": ["x"]` in the cache | `:711` `(cache.get("triggers") or {}).get(...)` | **1** | `--fire` |
| e | `.claude/recall-cache/` not writable | `:719-720` `mkdir` / `marker_file.write_text` | **1** | `--fire` |
| f | a plan file that is not valid UTF-8 | `:630` `plan.read_text(...)` | **1** | `--fire` |
| g | a sentinel that is not valid UTF-8 | `:623` `SENTINEL.read_text(...)` | **1** | `--fire` |

`parse_cache` (`:467-483`) validates only that the document is a `dict`; `(c)` and `(d)` are inside
it. All of b–g are reachable through the hook, which routes them to
`surface-recall.sh:45` — `*) : ;;` — and exits 0 with an empty payload.

**(e) is the expensive one, and it is an ordering defect, not just a code defect.** The dedupe
marker is written **before** the entry is printed:

```
scripts/recall-llm.py:719-721
    marker_file.parent.mkdir(parents=True, exist_ok=True)
    marker_file.write_text(current, encoding="utf-8")
    print(text)
```

So when the directory is read-only, everything upstream succeeded — cache valid, fingerprint
matched, entry resolved in the live corpus — and the matched lesson is **never printed at all**.
Measured, control first:

```
writable   -> {"hookSpecificOutput": {... "additionalContext": "⭐ recall — ... the-entry ..."}}  HOOK_RC=0
chmod 500  -> (no output)                                                                        HOOK_RC=0
```

The bookkeeping for a message is allowed to destroy the message. Printing first and writing the
marker best-effort inverts that.

**Siblings searched.** Every `read_text` in the file: `:262`, `:623`, `:630`, `:699`, `:716` — and
every one of the five is an unguarded decode. Four are measured above; `:716` (the marker) is
guarded by `is_file()` but not by encoding, and I did not build a world for it because (e) already
covers that line's failure mode. **Class, not instance:** there is no decode-error handling
anywhere in the file, and `Refusal` has no `OSError`/`ValueError` boundary at `main:1291`.

**What would prove this wrong:** any of a–g exiting 0, 2, 3 or 4 instead of 1.

---

### H2 · The trigger TEXT the reader is shown is never re-checked, so `--fire` prints a `FIRES-WHEN:` sentence that no longer exists anywhere

**What is wrong.** `cached_entry_verdict` (`:502-532`) was added precisely because `--fire` "touched
the corpus not at all", and it checks that the named entry still *resolves* — `(d / f"{entry}.md")
.is_file()` at `:706`. It does not look at what that file now says. The trigger the reader sees comes
from the cache (`:711`), and `render`'s own docstring (`:559-564`) says why that string matters:
*"the trigger is the sentence that tells them whether it applies right now."*

**Measured.** Cache armed while `the-entry`'s trigger read *"about to quote a green check as
evidence"*; corpus file then rewritten so its live trigger reads *"restoring a database from a
dump"*; entry name unchanged:

```
--fire -> RC=0
⭐ recall — this moment matches a recorded lesson:
   the-entry
   FIRES-WHEN: about to quote a green check as evidence   <- not in the corpus any more
   (open the memory file of that name for the detail)
```

The reader is handed a sentence that does not exist, for an entry whose real subject is now
unrelated — and is invited to open a file that will not say what the line above it said. That is
strictly worse than the `renamed-away` case `cached_entry_verdict` already refuses, because that one
is at least visibly broken.

**And the cache already carries the fields that would catch the neighbouring cases, unread.**
`cache_document` (`:436-444`) writes `plan`, `corpus_size` and `model`; `cache_verdict` (`:447-464`)
reads **only** `fingerprint` — by design, and the docstring defends the single clause. But that
defence is about an *unreachable* second clause, and these three are not unreachable, they are
simply never consulted. Measured in the same run: a cache whose `plan` is
`.claude/plans/SOME-OTHER-PLAN.md`, whose `model` is `a-model-that-scored-3-of-20` and whose
`corpus_size` is 3 was served at rc=0 without comment. `MODEL` is a module constant (`:103`); change
it and every existing cache is served as though the new model had answered.

This is the repo's own `defined-not-derived-constants` / stored-but-never-read shape: three fields
that look like staleness guards and guard nothing. Either read them or stop writing them.

**Siblings searched.** Every `cache.get(...)` in `do_fire`: `fingerprint` (via `cache_verdict`),
`picks` (via `lookup`), `triggers` (`:711`). `plan`, `corpus_size`, `model` have **zero** readers in
the branch — `grep -n '"model"\|corpus_size\|\["plan"\]' scripts/recall-llm.py` returns only the
writer and self-test assertions about the writer.

**What would prove this wrong:** a `--fire` run whose printed `FIRES-WHEN:` line is re-read from the
corpus file rather than from `cache["triggers"]`.

---

### H3 · Duplicate step numbers: `parse_response` accepts a reply that answered fewer situations than it was asked, and binds one answer to two different moments

**What is wrong.** `parse_response` compares **sets**:

```
scripts/recall-llm.py:387-389
    want = {str(n) for n in step_numbers}
    got = set(obj)
    if got != want:
```

`plan_steps` (`:139-159`) takes the number from the step text and never checks uniqueness;
`plan_verdict` (`:162-176`) refuses only an empty step list and empty situations. So a plan whose
step numbers repeat — the ordinary shape when numbering restarts per task — produces duplicate keys,
and the set comparison collapses them.

**Measured** on a four-step plan numbered `1, 2, 1, 2`:

```
plan_steps   -> [(1,'situation ALPHA'), (2,'situation BETA'), (1,'situation GAMMA'), (2,'situation DELTA')]
plan_verdict -> (0, '')                       # accepted
build_prompt -> sends "1. situation ALPHA" AND "1. situation GAMMA"
parse_response('{"1":"e","2":"NONE"}', [1,2,1,2], ["e"]) -> {1:'e', 2:'NONE'}    # ACCEPTED
cache picks  -> {'1': 'e', '2': 'NONE'}
lookup(doc,1)-> 'e'    first_unticked -> 1
```

Two of the four situations were never answered and nothing said so; the answer chosen for *situation
ALPHA* is now the cached answer for *situation GAMMA*. That is the docstring's own forbidden
behaviour, verbatim (`:363-365`): *"a key missing, or one too many → not 'match up what we can'"*,
and *"A model that answered about different steps than it was asked about did not answer this
question."* The plan fingerprint does not help — it hashes `(n, s)` pairs (`:420`), so it is
perfectly stable across this.

**Reachability.** `begin-plan.py` never generates repeated numbers, and I scanned every file under
`docs/superpowers/plans/` and `.claude/plans/` for repeated `Step N of M` values and found **none**
today. So this needs a hand-written or future plan — but `plan_verdict` is the function whose stated
job is to refuse plans that cannot be matched, and `cmd_plan` arms arbitrary files. Graded High, not
Blocking, on that reachability.

**What would prove this wrong:** a `plan_verdict` or `parse_response` that refuses `[1,2,1,2]`; or a
demonstration that no caller can produce repeated step numbers.

---

### H4 · The hook's forwarding condition duplicates `render`'s leading literal across a file boundary, with zero coverage on either side

**What is wrong.** Whether the model sees anything at all is decided by a string match on the
matcher's stdout:

```
.claude/hooks/surface-recall.sh:41
  0) case "$OUT" in *"⭐ recall —"*) PAYLOAD="$OUT" ;; esac ;;

scripts/recall-llm.py:565
    return (f"⭐ recall — this moment matches a recorded lesson:\n"
```

One rule, two files, nothing reconciling them. All 53 mutation entries target
`scripts/recall-llm.py` (`"file"` is that path in every entry), the hook has no `--self-test`, and
no case asserts the hook's pattern.

**Measured.** I changed only `render`'s first line, `⭐ recall —` to `⭐ recall:` — the shape of an
ordinary wording tweak — in a copied tree:

```
--self-test              -> 128/128 self-test cases passed
--fire                   -> RC=0, prints the entry correctly
surface-recall.sh        -> (no output)   HOOK_RC=0
```

Control, same world unmutated: the hook emits the full `hookSpecificOutput` JSON. **The mechanism is
switched off, silently, and every gate in the repository stays green.** This is the repo's
`a-second-implementation-of-one-rule-drifts` shape at a producer/consumer boundary.

**Siblings searched.** `grep -rn "⭐ recall"` over the whole tree excluding `docs/reviews/`: exactly
two sites, the two above. Then the class: `grep -l` over `.claude/hooks/*.sh` for hooks that
pattern-match a script's stdout returns `block-default-branch-push.sh` and `surface-recall.sh`; a
third, `block-implementation-before-plan-gate.sh:56`, matches on `$VERDICT` — but **its producer is
the inline `python -c` in the same file** (`:48-53`), so the literal cannot drift across files.
`surface-recall.sh` is the only cross-file instance. Not a class defect; one site, unguarded.

**What would prove this wrong:** a case or mutation anywhere in the branch that goes red when
`render`'s leading literal changes.

---

## MEDIUM

### M1 · The `EXPECTED_MUTATIONS` comment says **41** twice, beside the **53** it registers

```
scripts/check-plan-code.py:1330-1336
    # ... 41 entries over a file whose CENTRAL mechanism — a model call — cannot be
    # mutated at all ...
    # SIX of the 41 mutate the PROMPT TEXT rather than code ...
    "scripts/recall-llm.py": 53,
```

The manifest holds 53 entries (verified: `len(json.load(...))` = 53), and 6 of them do anchor inside
the `PROMPT` literal (verified by substring containment), so the "SIX" is right about the numerator
and wrong about the denominator. This is the table whose entire purpose is that a count cannot move
without someone deciding it should, and the only prose explaining *why* this count is what it is
names a different count. `check-selftest-counts.py` cannot see it — it verifies docstring counts
against suites, not comments against literals.

**Disposition per Q3:** inside the delta, no new mechanism — FIX.
**Falsifier:** the manifest turns out to hold 41 entries.

### M2 · `surface-recall.sh:5` cites a guard that does not cover this file

> *"A matcher nothing invokes is the inert field this design spent a day arguing about, and
> `check-ratchet-contract.py` refuses one."*

It does not. `evaluate` applies `check_caller` (R3) only over `discover_guards()`
(`check-ratchet-contract.py:202-204`), whose population is `GUARD_PATH_RE.fullmatch` — `check-*.py`
(`:153-163`). Non-guards get R4 **only**, and the code says so at `:210-214`: *"Only R4 is applied:
R1-R3 were never asked of these files."* Confirmed by running it: `guards discovered (40)` lists
every `check-*.py` and not `recall-llm.py`.

So deleting the hook and the `.claude/settings.json` entry would leave `check-ratchet-contract.py`
green. The thing the hook is offered as protection against is unprotected. This is the
*quote-the-code-don't-characterise-it* premise rule applied to a comment rather than a design doc,
and the cost is that a reader trusts a guard that is not there.

**Disposition:** FIX the sentence (it is a claim about a guard, not a design change).
**Falsifier:** a run of `check-ratchet-contract.py` that reports R3 against `scripts/recall-llm.py`.

### M3 · **The fourth instrument error** — "the eight that sank" is a list of seven, and the arithmetic needs eight

The measurement record, `docs/reviews/claude/semantic-recall-replication-2026-09-29.md:170-172`:

> *"Eight of the twenty correct entries rank at 66, 82, 94, 95, 106, 107 and 108"*

That is **seven** ranks. The committed fixture agrees with the document and disagrees with itself —
`scripts/fixtures/recall-replication-2026-09-29.json` →
`mechanism_measurements_same_day.lexical_recall_at_k._ranks_of_the_eight_that_sank` is
`[66, 82, 94, 95, 106, 107, 108]`, seven elements under a key that says eight. The same table gives
`at_20: "12/20"`, which **requires** eight entries ranked beyond 20. `scripts/recall-llm.py:16-17`
carries the count a third time: *"eight correct entries rank 66th to 108th"*.

So one measured rank is missing from the experimental record, in the one artefact that is supposed
to make the measurement re-derivable. The *decision* does not move — `recall@20 = 12/20` is what
kills the hybrid, and it is unaffected — but the record cannot now reconstruct which eight.

This is the fourth instrument error the brief asked for. **It is the same shape as one the document
already owns**: `:79-87` says *"Lexical's 7 false fires of 60 are all pure token collisions"* and
then tabulates **four**, with nothing saying the table is partial (filed separately as L7).

**Disposition:** FILE or FIX — it needs the original ranking run re-read, not a text edit.
**Falsifier:** the eighth rank turns up in the run's raw output and both files are amended; or
`at_20` is re-derived as 13/20.

### M4 · The `rc=3` "run `--arm`" nag is not deduped, while the useful message is

`should_surface` (`:540-555`) exists because, in the author's own words at `:543-546`,
*"`begin-plan.py` is run for `--status` and `--banner` as well as `--tick`, so the same step can be
re-surfaced several times without the situation having changed at all"*, and a hook that printed
every time *"would be trained away within an hour."*

The dedupe is consulted at `:717`, which is reached **only after** `fire_output` returned non-empty
(`:711-713`). Every refusal — including the `StaleCache` at `:697` for "this plan was never armed" —
raises before it. So the branch that fires on a *correctly matched, armed* plan is rate-limited, and
the branch that fires when the plan is **not armed** is not. Since `--arm` is a manual, paid step
that nothing runs automatically, "not armed" is the default state of every plan, and the nag is
therefore the common case.

Measured: the hook emits the full 340-character `additionalContext` block on every invocation with
no cache present; repeated invocations are byte-identical. The frequency of `begin-plan.py` calls is
not measured on this branch — the `~15/day` figure is for step *transitions*, and
`should_surface`'s own docstring asserts the invocation count is higher.

**Disposition:** FIX (the marker mechanism already exists; the nag needs its own key, e.g.
`plan_stem:unarmed`).
**Falsifier:** a measurement showing `begin-plan.py` is invoked at roughly the step-transition rate,
so the un-deduped nag costs ~1 line per transition.

### M5 · The measurement record still states the model call at 6.41s; the code says that figure is not about this call

`call_model`'s docstring corrects it explicitly (`:590-594`):

> *"MEASURED 2026-09-29, this script's own first real call: 16.1s for a 15,336-character prompt …
> The 6.41s in the addendum measurement is a TRIVIAL prompt on `--model haiku` — a floor for CLI
> startup, not a figure for this call."*

The record was not updated. `semantic-recall-replication-2026-09-29.md:191` still heads the section
*"A model call costs 6.41s"* and `:194-195` derives *"29 minutes per session"* from it; the fixture
records `model_call_latency.latency_s: 6.41` with `_verdict: "~51x the old hook; 29 min/session"`.
At the real 16.1s the same arithmetic is 275 × 16.1 = **74 minutes**, and `~51×` is `~129×`.

The conclusion is unchanged and stronger, which is exactly why this is Medium rather than High — but
the record is the artefact a future reader re-derives from, and it now carries a number the shipped
code documents as wrong for the thing it is a number about. The script's own top docstring
(`:23-25`) reuses 6.41s for the 29-minute figure too, though it at least labels it *"a trivial
prompt"*.

**Disposition:** FIX (one heading, one sentence, one fixture value, with the 6.41s kept as the
labelled CLI-startup floor).
**Falsifier:** the 16.1s figure turns out to be the outlier and 6.41s the representative one.

---

## LOW

**L1 · The `ALREADY DOING` rubric clause has two cases and no mutation, unlike all six others.**
`recall-llm.py:287-293` says *"Five clauses are load-bearing and each has a self-test case asserting
it is still here plus a mutation entry that deletes it."* I checked all seven pinned clause literals
against the manifest: six have a deleting mutation; `"ALREADY DOING what the lesson advises"` —
added 2026-09-30 and described in the addendum as *"stated in the shipped prompt, with two cases
pinning it"* — has **none**. So its two cases (`:1095`, `:1098`) are unfalsified by the sweep.
`:1098` is additionally a near-duplicate of `:952` (both assert `thematically adjacent` is present),
and the mutation that names `:952` would not distinguish them. *Falsifier:* a manifest entry whose
`new` drops that clause.

**L2 · The cache and the dedupe marker are keyed on `plan.stem` alone.** `cache_path` (`:424-426`)
and `surface_marker` (`:535-537`) both use the stem, so `.claude/plans/w.md` and `docs/plans/w.md`
share one cache file and one marker. Measured: arming the first and pointing the sentinel at the
second yields `rc=3` with the message *"Its situations have been edited since"* — false; they are
different plans, and the cache's own unread `plan` field says which. Fails closed, so Low; but
alternating between two same-stem plans destroys each other's cache and buys a paid call per switch,
and the marker (`w:1`, verified on disk) lets a surface on one plan suppress the same step number on
the other. *Falsifier:* `cache_verdict` comparing `cache["plan"]`.

**L3 · `parse_response` accepts duplicate JSON keys, last-wins.** `json.loads` without
`object_pairs_hook` cannot see them (`:380`). Measured: `parse_response('{"2":"a","2":"b"}',[2],…)`
→ `{2: 'b'}`, no rejection. The first answer is silently dropped, which is the one thing the
docstring at `:360-368` says every branch refuses. Cheap to close with `object_pairs_hook`.
*Falsifier:* a reply with a repeated key being rejected.

**L4 · The fence rule takes the FIRST fenced block, not the last.** `:373-375`. A reply that
restates the requested format in a fence and then answers in a second fence is rejected as answering
the wrong steps — measured: `ResponseRejected: missing ['2'], unexpected ['1']`. Fails closed, so
Low, but it costs a whole re-arm (16.1s and money) for a common model formatting habit, and the
answer is conventionally the *last* fence. The case at `:987` pins fence-over-prose, not
first-over-last. *Falsifier:* a measurement that the model never emits two fences.

**L5 · A hand-edited cache can name an entry with path separators.** `:706` resolves
`(d / f"{entry}.md")`, so `"../../../../secret"` satisfies `entry_present` from outside the corpus
and `render` prints that string to the model — measured, rc=0, `FIRES-WHEN: a trigger` and a
traversal path as the entry name. The cache is gitignored and local, so the threat model is a hand
edit or a corrupt file rather than an attacker; the fix is one `"/" not in entry` check where names
are already validated. *Falsifier:* `parse_response`'s `valid_names` being the only producer of
cached names — it is not, because `parse_cache` reads whatever is on disk.

**L6 · Concurrent `--arm` for the same plan stem share a fixed temp path.** `:678`
`tmp = out.with_suffix(".json.partial")`. The comment at `:674-677` claims atomicity via
`os.replace`, which is true for *interruption* and not for *concurrency*: two `--arm` runs for one
plan both truncate and write the same sibling before renaming it. `--arm` is manual and not
hook-driven, so this is Low. `tempfile.mkstemp(dir=...)` removes it. *Falsifier:* a lock, or a
demonstration that two `--arm` runs cannot overlap.

**L7 · The dashboard entry's commit count was wrong when it was written.**
`docs/dashboard-entries.md`, the 2026-09-30 tech block: *"`semantic-recall-replication`, 4 commits,
unmerged, off `master` at `446025ab`"*. `git log -S` places that line in commit `4d1e7b46`, which
was the branch's **fifth**. Trivially wrong, and inherently stale — but the same class as M3 and L8:
a count written beside the thing it counts, and not derived from it. Recorded so the next entry
either derives it or omits it. *Falsifier:* `git log --oneline master..` at `4d1e7b46` showing four.
Same block's *"16.1s"* is correct and is the figure M5 says the review doc is missing.

**L8 · The record's false-fire table enumerates 4 of the stated 7.**
`semantic-recall-replication-2026-09-29.md:79-87` — *"Lexical's 7 false fires of 60 are all pure
token collisions"* followed by a four-row table with no note that it is a sample. Same shape as M3;
graded Low because the count itself is corroborated by the fixture
(`results.lexical_top1_paraphrased.hard_negatives_60` = *"53/60 silent, 7 false fires = 11.7%"*, and
7/60 = 11.67%). *Falsifier:* a caption saying the table is illustrative.

---

## Areas I could NOT establish

Hypotheses I formed and failed to confirm. Each was tested, not merely considered.

1. **That the `hookSpecificOutput` shape is wrong for `PostToolUse`, or that an `rc=3` payload can
   break the JSON.** Both refuted by running the hook end to end. `surface-recall.sh:50` pipes the
   payload through `json.dumps`, so a `Doing:` line containing `"quoted"`, backslashes, literal
   `\n`, `}{` and an embedded `"additionalContext":"INJECTED"` came out correctly escaped; the
   output parses and carries exactly `{hookSpecificOutput: {hookEventName, additionalContext}}` with
   `hookEventName: "PostToolUse"`. I could not construct an input that produced malformed JSON.

2. **That the hook can block or fail a Bash call.** Not established. `set -uo pipefail` without
   `-e`, `RC=$?` taken from an assignment (correct for a command substitution), `exit 0` on every
   path including `[ -f "$MATCHER" ] || exit 0`. Every crash I engineered (H1 a–e) still gave
   `HOOK_RC=0`. I did not test a *hang*: `.claude/settings.json` sets no `timeout` on this hook and
   `--fire` has no internal deadline, so a stalled filesystem would block on the default. I could
   not construct that stall, so I am not filing it.

3. **That two armed worktrees collide.** Refuted. `ROOT = Path(__file__).resolve().parent.parent`
   (`:95`), so `SENTINEL`, `CACHE_DIR` and the marker are all per-checkout, and `memory_dir` derives
   the slug from the resolved root (`:242-245`), giving each worktree its own corpus path. The
   stem-collision problem (L2) is *within* one tree, not across two.

4. **That a plan file replaced by a copy defeats the fingerprint.** Refuted by construction: the
   fingerprint is content-derived from `(step number, situation)` pairs (`:420`), not mtime, and the
   docstring's claim about mtime being wrong in the other direction is correct.

5. **That some of the 53 mutations are vacuous.** I could not find one. Checked mechanically: every
   `old` anchor occurs exactly once in the source; no anchor is reused across entries; every
   `expect` string exists verbatim as a case label; no anchor is comment-only. The four
   *overlapping*-anchor pairs (lines 420, 537, 555, 717 — including the retargeted pair the brief
   asks about at 537) each mutate genuinely different behaviour and each names a case that only that
   mutation fails; I traced all eight by hand against their cases. One mutation
   (`plan_fingerprint hashes the plan's bytes`) would also fail `:1015` as well as its named
   `:1004`, which is over- rather than under-attribution. The `expect` reused twice
   (*"do_fire is SILENT on the second call for the SAME step"*) belongs to two distinct mutations of
   different lines. **The sweep's own attribution is the authority here, not my reading** — see
   *Mutation sweep* below.

6. **That the `141` / `144` / `142` trigger counts disagree.** They do not. Measured against the
   live corpus: 144 entry files (excluding `MEMORY.md`), 144 carrying a `FIRES-WHEN:` trigger, 142
   of those carrying an em-dash — exactly `parse_trigger`'s claim at `:226-228`. The record's `141`
   is correct as of 2026-09-29 and `cached_entry_verdict:515` records the 141→144 growth itself.

7. **That the `~15/day` derivation is wrong.** It checks out. The record says 45 plan files, 195
   steps, 4.3 steps/plan; measured today, `.claude/plans/` holds 46 files and 199 `Step N of M`
   boxes — one plan (this branch's own, 4 steps) added since. 199/46 = 4.33. 28/8 = 3.5 plans/day,
   3.5 × 4.3 = 15.1. The only quibble is that `steps/plan` comes from a 45-plan denominator and
   `plans/day` from a 28-plan one, which is not enough to file.

8. **That the `252-char clause` and `93,781-char prompt` figures are invented.** The clause is
   exactly 252 characters, verified by measuring the literal in `PROMPT`. I could **not** verify the
   93,781 figure — it requires the 1000-entry padded corpus, which is not committed (only the 80-item
   fixture is), so the one-variable control at `:304-312` is not re-derivable from this branch. I am
   recording that as a limit of the artefact, not as a finding: the document states the control's
   method and result, and nothing in the committed material contradicts it.

9. **That `parse_response` guesses on a near-miss name.** It does not. `"Running-Codex"`, a name not
   in `valid_names`, and a name differing by whitespace are all rejected; non-string, null and
   nested values are rejected with the type named; a bare list is rejected; a key `" 2"` or `"2.0"`
   is rejected. The only acceptance hole I found is the duplicate key (L3) and the set-collapse
   (H3).

10. **That `--arm` spends money on a paused plan.** It does — `do_arm` (`:660-685`) never calls
    `paused()`, which only `do_fire:690` does. I did not file it: `--arm` is a deliberate manual act
    and arming a parked thread ahead of resuming it is a reasonable thing to want. Recorded so the
    next reviewer does not spend the same probe on it.

11. **That the `_DOING_RE` block scan bleeds past the last step.** For the final box,
    `end = len(plan_text)` (`:155`), so trailing prose containing a `- **Doing:**` line would be
    read as the last step's situation. I could not find a real plan with that shape, and
    `begin-plan.py` never writes one, so I did not file it.

12. **That the docstring's own execution checklist overstates what was run.** It does not — I
    re-ran all seven rows of `recall-llm.py:44-46` plus the correction at `:48-54`, in a rebuilt
    world: no sentinel → **2**, no cache → **3**, edited situation → **3**, tick-only edit →
    **not staled**, paused → **silent 0**, zero triggers → **2**, and `--fire` under a redirected
    `HOME` → **2** with `NOTHING WAS SURFACED`. Every one reproduces. One phrasing nuance, not a
    defect: *"tick-only edit → served"* reproduced as *the cache was not invalidated* — in my world
    the newly-current step's pick was `NONE`, so nothing printed. The three self-reported instrument
    errors in the measurement record and the docstring are, as far as I could check them,
    **described accurately**; M3 and M5 are additional ones, not restatements.

13. **That a manually edited or garbage `.last-surfaced` misbehaves.** Refuted. Any value that is
    not the current `stem:step` token makes `should_surface` return True (`:555`), so a corrupt
    marker surfaces rather than suppresses; a marker naming a vanished plan likewise. The only
    degradation is a marker hand-set to the current token, which suppresses exactly one surface.
    Fails safe.

---

## Mutation sweep

`python3 scripts/check-plan-code.py --mutate .` was started at the top of this review and its real
exit code read from the redirected file, never from `$?` after a pipe.

```
OK — delivered scripts mutated: 54 file(s), 1087 mutation(s), 1087 killed,
     1087 attributed to the case each names, 0 survivor(s)
SWEEP_RC=0
```

`scripts/recall-llm.py` is in the population (control at `[54/54]`, re-control at `[54/54]`), its 53
entries are inside the 1087, the declared sum in `check-plan-code.py:3760` is 1087, and the pre- and
post-controls both passed — so this is a measurement and not a `NotMeasured`. **No mutation
survived and none was attributed to a case other than the one it names**, which answers the
vacuity question the brief asks about the 53 more authoritatively than my hand-tracing in
*Areas I could NOT establish* §5.

⚠ **What it does not cover, and this is the point of B1, H1 and H4.** The sweep stages
`HARNESS_TREE` and mutates `scripts/`. `.claude/hooks/surface-recall.sh` is not in it, so every
finding that lives at the script↔hook boundary is outside its reach by construction; and a green
sweep says nothing about a decision that is *absent* from the code (`do_fire` not calling
`plan_verdict`) — you cannot mutate a call that is not there. **1087/1087 is exactly the shape of
evidence the repo's own `unit-coverage-does-not-compose` records: correct about every piece it
measured, silent about the composition.**

---

## Round-1 bookkeeping

- **Q1 (scope):** full loop — the diff touches `scripts/`, `.claude/hooks/`, `.claude/settings.json`
  and `.gitignore`. `check-review-decision.py` agrees: `scope=full-loop rounds=0`.
- **Q4(a) (convergence):** **CONTINUE.** One Blocking and four High.
- **Q5 (thrashing):** not applicable at round 1 — no previous round's fix exists to have caused
  anything.
- **Aim of the findings:** B1, H1, H2 and H3 are all in the **deliverable**, not the instrument.
  M1, M3, M5 and L7 are instrument/record findings. That split is itself a signal that the
  deliverable has not converged.

REVIEW GAP: none for this half — this document is the Claude half; the Codex half ran concurrently
and files separately.
