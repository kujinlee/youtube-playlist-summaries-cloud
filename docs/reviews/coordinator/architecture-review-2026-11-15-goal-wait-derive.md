# Phase 6 architecture review — the prerequisite matcher and the recorded-wait resolver in `scripts/goal-tree.py` (backlog #650, PR #592)

- Subject: `named_prerequisites` and `wait_blockers` (with the part of `owed_reason` they feed), branch
  `goal-wait-derive`, read at `5359735c`.
- Armed by THRASHING: round 2 and round 3 each carried findings caused by the previous round's fix, in the components
  `prerequisite-matcher` and `wait-resolution` (`goal-wait-derive-r2-coordinator.md`, `codex/goal-wait-derive-r3-codex.md`).
- Read first: `CONTEXT.md` (it defines no term for a wait, a prerequisite or the in-flight ledger), `docs/adr/`
  (ADR-0010 and ADR-0014 are the only ones near this path; nothing here re-opens either), the backlog #650 row, the
  six review documents and two coordinator documents of subject `goal-wait-derive`, and `docs/review-method.md` →
  *The stop condition* and *Can a redesign remove it?*.
- No tracked code was changed and nothing was committed. The live ledger was read, never written.
- Every claim is tagged **[M]** (measured here: a command was run and its output read) or **[I]** (inferred from text).

## Recommendation

1. **The thrashing is a mechanism defect.** Both components answer "what does this English sentence say the work
   waits on" with a pattern. A redesign removes the question, so by the method's one test the redesign is owed.
2. **Delete both components. Do not patch round 3's four findings.** Remove `named_prerequisites`, `AFTER_RE`,
   `_CLAUSE_RE`, `_NEGATED_RE`, `_WAIT_JOINERS`, `wait_blockers`, and the `stale` branch of `owed_reason`.
3. **A prerequisite is DECLARED, once, when the item is recorded.** A ledger entry carries `after`, a list of refs
   (`["PR #442", "backlog #394"]`). `session-state.py --add` REQUIRES `--after`, with `none` as a legal value, the same
   way it already requires `--goal` and `--thread`. All listed refs must finish; there is no "or".
4. **The script derives everything that changes afterwards, and nothing else**: each declared ref's live state
   (`open`, `done <date>`, `abandoned`, `not read`, through the unchanged `_blocker`), the alarm, and the idle days.
5. **Prose is shown verbatim and never read for refs**: `what`, `on_done`, a recorded `waits`, and a thread line's
   `· waits on …`. A prose wait stays a live reason whatever it mentions.
6. **The lapse the owner asked about is caught by two things that read no prose**: the required flag at write time,
   and the existing `no reason recorded — idle N days` line at session start.

This is candidate (a) of the brief, plus the write-time requirement, which the brief did not have and which is the
part that answers the owner.

## 1. Is "infer a dependency graph from free prose" the right class?

Yes. I tried to refute it three ways and each attempt failed.

### The record, finding by finding

22 findings over three rounds (13, 5, 4). Seven are in the two armed components. **[M]** counted from the round
documents.

| Round | Finding | Component | Input that broke it | Direction | Caused by |
|---|---|---|---|---|---|
| 1 | Codex 4 | matcher | `on_done="After PR #451 merges, remove the flag"`; `Do not wait until after PR #451` | reads too much | the first build |
| 1 | Claude F1 | resolver | `waits="PR #442"`, PR #442 merged, still "waits for" | reads too little | the first build |
| 2 | N2 | resolver | `(PR #590: r1 Opus, r2 Fable)`; `asked on PR #590` | reads too much | the F1 fix |
| 2 | N4 | matcher | `Wait until after PR #5`; `No rush: start after PR #5`; `no-op flag after PR #5` | reads too little | the Codex 4 fix |
| 3 | Codex 1 | resolver | `after PR #442 and PR #451` keeps only the first | reads too little | the N2 fix |
| 3 | Codex 2 | resolver | `waiting for PR #442`; `blocked on PR #442` never expire | reads too little | the N2 fix |
| 3 | Codex 3 | matcher | `Do not do this: start after PR #451` | reads too much | the N4 fix |
| 3 | Codex 4 | resolver | `PR #442 or PR #451` is read as "both" | wrong meaning | not a fix; same class |

Each component reversed direction every round: the matcher went too-much, too-little, too-much; the resolver went
too-little, too-much, too-little. That is the signature of a boundary being moved through a space with no boundary
in it, and it is why the count of findings did not fall (2, 2, 4).

### The three refutation attempts

1. **"It is branch coverage: the rule is fine and under-specified."** Refuted. A branch-coverage finding names a case
   the rule does not mention. These name cases the previous fix decided, and decided the other way. Round 2's fold
   wrote down the colon case as acceptable ("never a hidden item"); round 3 showed it hides an idle item. **[M]** from
   `goal-wait-derive-r2-coordinator.md` (*Choices this fold made*) and round 3 finding 3.
2. **"The class is narrower: only negation, or only the `after` form."** Refuted. The eight inputs need at least four
   different pieces of English: which field states a start condition (`on_done`), negation scope, the difference
   between citing and depending (`asked on PR #590`), and conjunction against alternation. Fixing any one leaves
   three.
3. **"Errors are loud, so an imperfect matcher is acceptable."** Refuted, and this was the design's own safety
   argument. A false prerequisite in `what` gives the item a live reason and removes it from the idle list (round 3
   finding 3). A missed prerequisite in a recorded wait leaves `waits for` standing after the PR merged (round 3
   finding 2). Both are silent, and they point opposite ways, so no threshold makes the matcher fail safe.

### What the class is not

The other 15 findings are not this class and did not recur: blocker state (closed is not merged), the idle rule, the
year of a yearless stamp, the exit code, the bounded block. Leave those components alone. `idle_days` shares a
family resemblance (it infers a year the ledger does not store) and carried one fix-caused finding in round 2, but
none in round 3. It has not armed; widening the ledger's `at` to a full stamp would remove it and is not owed here.

### This repository has already made this retreat twice, in the same two files

- `scripts/session-state.py`, above `KIND_WAIT`: *"owner relevance is DECLARED, never inferred … Rounds 1 and 2 each
  found a real phrasing the text matcher missed … because a matcher is a guess about words the next entry will not
  use."* The fix was the `kind` field and `--migrate-kinds`. **[M]** quoted from the file.
- `scripts/goal-tree.py:_ledger_refs`: *"An entry that declares a `thread` names exactly that thread's STRUCTURED refs;
  its prose is not an association (r1 Codex M3)."* **[M]** quoted from the file.

The recommendation is the third application of a rule the code already states.

## 2. Can a redesign remove it, and which one?

| Option | What it is | Removes the class? | Verdict |
|---|---|---|---|
| (a) declared field | `after` on the entry, required at `--add`; prose never parsed | **Yes.** There is no sentence left to misread | **Recommended** |
| (b) one exact form | keep parsing, but only `after PR #N`; everything else verbatim | **No** | Rejected |
| (c1) a wait that IS a ref list | a `; `-part of `waits` that fully matches the refs grammar is structured; no new field | Mostly | Rejected, narrowly |
| (c2) a model reads the prose at page-build time | an LLM call inside `goal-tree.py` | No (moves it, adds cost and nondeterminism) | Rejected |

**Why (b) fails.** (b) is the round-1 design. It is what the branch shipped first: "NARROW on purpose: the word
`after` directly before ONE ref". Narrow search is still search inside a sentence, so context still decides the
meaning. Six of the eight inputs in the table above contain the exact form `after PR #N` or `After PR #N` and are
wrong anyway (`on_done`, `Do not wait until after`, `Wait until after`, `No rush: start after`, `after PR #442 and
PR #451`, `Do not do this: start after`). **[M]** counted from the table. (b) cannot be saved by narrowing further,
because the form is already one word and one ref.

**Why (c1) loses to (a).** (c1) is honest structure: a full match on a whole part has no context to negate, and
`PR #442 or PR #451` falls out as prose. It is also the smallest diff. It loses on the owner's question. Nothing
asks the writer anything, so whether the ref gets written in the exact form is a convention again, and the first
`--waits "waiting for PR #442"` is round 3 finding 2 once more. It also hides structure inside a prose field,
split on `"; "`.

**Why (a) and what it costs.** The meaning of the owner's sentence is still extracted, by the agent that records
the entry and can read English, once, at the moment it types `--add`. The script stops guessing at read time. Cost:
two scripts change (`session-state.py` gains the flag and a setter; `goal-tree.py` loses about 60 lines of matcher),
and 32 of the 446 mutations in `scripts/mutations/goal-tree.json` touch the deleted text and must be retired or
rebound. **[M]** counted by pattern over the manifest; treat 32 as an upper bound, the pattern includes the word
`stale`.

## 3. Does it still meet what the owner asked?

The owner's words, read from the session transcript (2026-11-14 21:33 and 21:37 local) **[M]**:

> "It would be better to mention what they are currently waiting for"
>
> "I see you manually updated goal-thread. Will you be doing it for all Owed items in the future too? I meant if some
> itens are waiting for something, show the reason to the reader (X is waiting for Y...)"

The words "derive it" are not there. The owner asked for two things: every Owed item shows its reason, and that
this does not depend on someone remembering a manual edit. "Derived by the script, never typed by hand" is the
backlog #650 row's reading of the second.

| What was asked | Prose derivation (the branch today) | Declared `after` (recommended) |
|---|---|---|
| The page says "X is waiting for Y" | Yes, when the sentence happens to parse | Yes, for every declared ref, with its live state |
| It does not rest on remembering | Rests on writing the one phrasing the matcher reads | `--add` refuses without `--after`; nothing to remember |
| An item with no reason is visible | `no reason recorded — idle N days` | The same line, unchanged |
| A finished prerequisite is an alarm | Yes, when the sentence parsed | Yes, always, for a declared ref |
| A wrong answer is possible | Yes, silently, in both directions | Only if the writer declares the wrong ref |

**It does not change what the owner asked for. It does change the backlog #650 row**, whose title says "never typed
by hand" and whose fix (1) says "DERIVE the wait from what the item already names". The row must be reworded: the
ref is typed once, by the tool's demand; its state, date and idle time are derived. The row's falsifier survives
unchanged with "named" read as "declared": a declared prerequisite that merged renders `blocker done`; an item with
nothing declared and nothing recorded renders `idle N days`.

The motivating case, replayed under the redesign **[I]**: backlog #511 is recorded with `START ONLY AFTER PR #442` in
its `what`. `--add` refuses until `--after "PR #442"` is given. From then the row reads `waits for: PR #442 (open)`,
and on 10-30 it reads `blocker done 10-30 (PR #442), not started` and is listed at session start. Two weeks of
"not recorded" cannot happen.

## 4. Migration

The main checkout's `.claude/inflight.jsonl` holds 9 entries. **[M]** read 2026-11-15 06:56; the current branch code
was also run over it, and it derives exactly the two below.

| Entry | Names a prerequisite in prose | Where | Gets |
|---|---|---|---|
| `subdivide-tooling` | **PR #442** | `what`: "START ONLY AFTER PR #442 (#394 kinds …) merges"; its `waits` repeats it as done | `after: ["PR #442"]` |
| `memory-hygiene` | **backlog #511** | `waits`: "queued after backlog #511 in the 11-15 budget" | `after: ["backlog #511"]` |
| `fable-compare-week` | none; it CITES PR #590 in its wait | `waits`: "(PR #590: r1 Opus, r2 Fable)" | `after: []` (optional) |
| the other 6 | none | | nothing |

**Two entries are affected.** A third cites a ref that is not a prerequisite, and is the entry round 2's N2 was
found on.

How they get the field:

- An entry with no `after` key reads as "none declared". That is the same fail-toward-showing rule `kind` has: with
  no recorded wait it shows as idle. So the six untouched entries need no edit.
- Do NOT re-run `--add` to migrate. Re-adding an id replaces the entry and stamps `at` with now, which resets the
  idle clock (`subdivide-tooling` would lose its `11-05 13:42`). **[M]** read from `ledger_add`.
- Add one small mode, `session-state.py --set-after ID REFS`, that rewrites that one key under the existing lock and
  keeps every other key. It is needed outside the migration too: a prerequisite discovered later must not reset the
  age. The migration is then two commands, run once in the main checkout after merge. No `--migrate-after` proposal
  mode is worth building for two entries.

`docs/goal-threads.md` needs no migration: 6 thread lines carry `· waits on …` and none names a ref (owner
walkthroughs, days of data, a weekly reset, product work resuming). **[M]** `grep -n "waits on"`.

## 5. The stop condition — what keeps this from thrashing again

1. **The thrashing code is deleted, not adjusted.** A finding of the form "this sentence is misread" has no code to
   land on. That is the difference from every previous fold.
2. **The contract is written where a reviewer reads it.** One docstring on the new reader: *prose is never read for
   prerequisites; a prose wait never expires; a counterexample that depends on what a sentence means is outside the
   contract.* The round-4 prompt quotes it.
3. **One property case replaces the phrasing cases**: prose-invariance. Take every adversarial input from the table
   in §1 (an independent literal list in the test, not built from the code), place each in `what`, `on_done`, `waits`
   and the thread line of an entry with `after: []`, and assert that no blocker is derived for any; then set `after:
   ["PR #442"]` on the same entries and assert exactly that one blocker for all. The derived blockers move with the
   field and with nothing else. One mutation: re-reading any prose field for refs turns it red.
4. **The untouched components stay untouched.** `_blocker`, `idle_days`, `_finished`, the bounded block and the hook
   are not edited, so the fold cannot cause a finding in them.
5. **The round cap governs the next round.** It is round 4: findings are FILED unless a BLOCKER
   (`review-method.md` §0 Q4c).
6. **A retreat, committed in advance.** If round 4 reports a fix-caused finding in the new `after` reader, the
   retreat is to drop the read-time validation of a hand-edited `after` and treat any element that is not exactly
   `PR #N` or `backlog #N` as `state not read`. No third parser.

This fails if: after the change, `grep -n "AFTER_RE\|named_prerequisites\|_NEGATED_RE\|_WAIT_JOINERS" scripts/goal-tree.py`
prints a line, or the prose-invariance case passes with `after` ignored.

## Implementation outline

Build test-first, in this order. Steps 1 to 3 are `session-state.py`; 4 to 8 are `goal-tree.py`.

1. **`ledger_add` takes `after`.** A list of `(kind, n)`, stored as `"after": ["PR #442", "backlog #394"]`, always
   written, `[]` for none. Refuse (ValueError) a ref that repeats, and a ref that is one of the entry's own thread
   refs.
2. **`--after REFS` on the CLI, required with `--add`.** The value is `none` or a string that fully matches the
   grammar `goal-tree.py:REFS_RE` already owns: `PR #N` or `backlog #N`, joined by `, `. Anything else is CANNOT RUN,
   exit 2, with a message naming both legal forms. `--after` outside `--add` joins the existing stray-flag list.
   Extend `ADD_NEEDS_GOAL`'s message, or add a sibling, so a missing `--after` says: "does this work wait on a PR or a
   backlog row to finish? `--after 'PR #N'`, or `--after none`".
3. **`--set-after ID REFS`.** Rewrites the one key under `_locked`, keeps every other key including `at`; an unknown
   id is exit 1 with nothing written. One case with two inputs proves `at` is unchanged.
4. **One reader in `goal-tree.py`: `declared_prerequisites(entry) -> list`.** Returns the `(kind, n)` pairs of
   `entry["after"]`. An absent key is `[]`. A value that is not a list, or an element that does not fully match one
   ref, yields a blocker `{"ref": <cleaned text>, "state": "unread"}`, so a damaged declaration shows as
   `state not read` and is never dropped.
5. **Feed `blockers` from it at the three sites** that call `named_prerequisites` today: `_ledger_owed`, and
   `derive_thread` (the entries naming the thread; the thread line's own `what` contributes nothing). Delete the
   `own=` filter with the matcher; step 1 refuses a self-reference at write time.
6. **Delete** `named_prerequisites`, `AFTER_RE`, `_CLAUSE_RE`, `_NEGATED_RE`, `_WAIT_JOINERS`, `wait_blockers`, every
   `wait_blockers` key (`_ledger_owed`, `derive_thread`, `_owed_keys`, `_fold_item`, the agenda digest), and in
   `owed_reason` the `by_wait` and `stale` lines. The idle rule becomes: no declared prerequisite open or unread, and
   no recorded wait. That is the round-1 Codex 5 rule with the stale clause removed, so its case still holds.
7. **Cases.** Add the prose-invariance case of §5.3 and one case per `declared_prerequisites` outcome (absent, `[]`,
   one ref, two refs in order, damaged). Keep the blocker-state, idle-days, session-block and hook cases as they are,
   re-pointing their fixtures from an `after PR #N` sentence to an `after` field. Retire the cases that assert a
   phrasing (round 1 Codex 4, round 1 Claude F1's nine spellings, round 2 N2 and N4).
8. **Mutations.** Retire the entries anchored in deleted text (at most 32), add at least one for each new rule
   (absent key read as a prerequisite; a damaged element dropped; prose re-read), update the pin in
   `scripts/mutations/expected_mutations.py`, and run the all-manifest anchor resolve. `session-state.py`'s manifest
   gains entries for steps 1 to 3.
9. **Callers and docs.** `.claude/commands/goal-tree.md` and the `--add` usage line in both scripts gain `--after`.
   Reword the backlog #650 row as §3 says. Regenerate the backlog page and run its `--self-test`.
10. **After merge, in the main checkout**: the two `--set-after` commands of §4.

## Deliberately out, and what to file

- **A dated wait.** 3 of the 8 recorded waits are a date (`the 11-20 weekly reset`, `the weekly reset (Fri 11-06
  02:00)` twice), and the 11-06 one is nine days past and still reads as a live reason. **[M]** No option here reads
  it. File one row: a declared `--until <mm-dd>` that goes stale on its own date.
- **A thread line that waits on a ref and has no ledger entry.** Its `· waits on PR #442` is prose and never
  expires. This is round 1 Claude F1's second repro, and the redesign leaves it as a stated bound. None exists today
  (0 of 6). File one row with that count as its trigger; the remedy when one appears is a ledger entry with `after`.
- **Alternatives ("or").** Not expressible. Declare both and the alarm waits for both, or write it as prose.
- **`idle_days` and the yearless `at`.** See §1; not armed.

## What we decided on this branch that is not written down

- "A prose wait is a live reason forever" was true before this branch, was made false by round 1's F1 fix, and
  becomes true again here. It should be one sentence in `docs/goal-threads.md` next to the line that defines
  `· waits on`.
- `CONTEXT.md` has no entry for *prerequisite*, *wait* or *Owed*. Three rounds argued over those words without a
  definition. Not an ADR (it is easy to reverse); a glossary entry.

## Bound of this review

| Claim | Basis |
|---|---|
| 22 findings, 7 in the two components, direction reversed each round | **[M]** counted from the six round documents |
| The current code derives a prerequisite for exactly 2 of 9 live entries | **[M]** ran `named_prerequisites` and the `wait_blockers` rule over the live ledger at `5359735c` |
| The owner's words | **[M]** read from the session transcript; the 21:37 message also appears in the backlog row, shortened |
| 32 mutations touch the deleted text | **[M]** pattern count, an upper bound |
| The redesign's behaviour on the motivating case, and that round 4 will not find a fix-caused finding | **[I]** not built, not run |
| The self-test was not re-run in this review | NOT RUN; round 3 reports 541/541 at `d3b1e5a4` |
