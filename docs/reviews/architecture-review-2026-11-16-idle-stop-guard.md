# Architecture review (Phase 6) — the idle-stop guard's two ALLOW exceptions

- **Date:** 2026-11-16
- **Subject:** `scripts/check-idle-stop.py` on branch `idle-stop-guard`, head `6d3a2104` (backlog row 663)
- **Armed by:** THRASHING in component `question-exception` — round 2 finding XM1 and round 3 finding Cm2 were each
  caused by the previous round's own fix. Round 3 also found BLOCKER CB1 in the `.claude/paused` pause marker.
- **Scope:** both ALLOW exceptions (the `AskUserQuestion` exception and the pause marker) and how they compose with
  the rest of `decide()`, including `stop_hook_active`. Not the three work signals, except where they bound a claim.
- **Method:** every probe and mutant ran on copies under the session scratchpad (`p6-isg/`); no tracked code was
  edited. The owner's local session transcripts were replayed read-only, as round 3 did.
- **Tags:** **[M]** measured in this review, **[I]** inferred.

## Verdict

**Remove both exceptions. Neither is right in kind, and no narrowing of either survives its own wrong inputs.**

Both exceptions let the agent's own account of the situation stand in for a measurement of it. The guard exists
because that account was wrong at 02:50 ("have you actually started working or just said you are starting"). Every
other ALLOW in `decide()` reads a fact the harness or the filesystem produced; these two read something the stopping
agent wrote or caused. That is the mechanism behind both the thrashing and CB1, and it is removable: each exception
buys exactly one continuation turn on its honest path, which `stop_hook_active` already gives **[M]**.

## 1. Is each exception right in kind? The attempts to refute it

### 1a. What each one buys

On the honest path, each exception saves one nudge and nothing else. The stop is refused once, the agent answers the
refusal, and the continuation is allowed by `stop_hook_active` regardless of either exception.

| Row | World | HEAD | Both removed |
|---|---|---|---|
| I3 | owner said "stop until 02:30", no marker | 2 | 2 |
| I3' | the continuation of I3 (`stop_hook_active`) | 0 | 0 |
| I8 | owner rejected a card, agent replied "What would you like to clarify?" | 0 | 2 |
| I8' | the continuation of I8 | 0 | 0 |

**[M]** `probe.py`, exit codes through `main()`. So the benefit of the question exception is one turn on I8, and the
benefit of the pause marker is one turn per stop while paused. Round 1 declined finding XM5 on exactly this cost:
an honest "nothing is left" stop is refused once by design.

### 1b. How often each one fires

Corpus: 82 transcripts of this project, 3,147 real stops replayed through `last_tool_asked` **[M]**.

| Measure | Value |
|---|---|
| stops where `last_tool_asked` is True | 4 of 3,147 |
| of those, a rejected card that HAS a result | 4 of 4 |
| main-chain `AskUserQuestion` cards, deduplicated per file | 207 |
| answered / rejected by the owner / refused by a hook / **no result ever** | 163 / 7 / 37 / **0** |
| occurrences of the literal `touch .claude/paused` in any transcript | 0 |
| a marker present in the main checkout | no |
| human prompts that tell the session to stop or pause work (regex, see Bound) | 3 of 1,436 |

**[M]** all rows. Two consequences. The "card with no result yet" branch of `last_tool_asked` has never been reachable:
a pending card holds the tool call open, so no stop fires while it waits **[I]** from the zero, **[M]** the zero. And
the pause marker has never been used by anyone; its only reader of record is the block message that advertises it.

### 1c. What each one costs

The question exception fires on 4 stops and owns the whole transcript reader. `tail` is used by `decide()` for
`last_tool_asked` and for nothing else **[M]** (read of the source). Size of what the two exceptions own:

| Measure | Value |
|---|---|
| lines in `_rejected`, `last_tool_asked`, `read_tail`, `paused` | 10 + 39 + 18 + 11 = 78 |
| manifest mutations anchored in those functions, their `decide()` lines, the `main()` tail line | 26 of 99 |
| self-test `case(` statements that reference either exception or the transcript | 29 of 93 |
| cases red when only the two `decide()` lines are switched off | 6 of 93 |

**[M]** all rows (`copy2`, and an anchor resolve of the manifest against the source). Roughly ten of the findings in
rounds 1 to 3 are in the transcript reader or the two exceptions (round 1 XM2/CM1, XM6, XM7; round 2 XM1, XM2, XM3,
Xm6; round 3 CB1, Cm2, Cm3) **[I]** — read by hand from the round documents, not enumerated by a script.

### 1d. Who can trigger each one — the refutation of "safe"

| Row | World | HEAD | Both removed |
|---|---|---|---|
| I0 | the 02:24 idle stop replayed, no marker | 2 | 2 |
| I1 | CB1: a marker 20 h 53 min old, same stop | **0** | 2 |
| I2a | the agent runs `touch .claude/paused` after a block; next turn, +5 min | **0** | 2 |
| I2b | same, +23 h 59 min | **0** | 2 |
| I2c | same, +24 h 1 min | 2 | 2 |
| I5 | card rejected, then "Never mind - starting #657 now." | **0** | 2 |
| I6 | card rejected, the owner's next prompt arrives queued (an `attachment` record), then "Starting now." | **0** | 2 |
| I7 | a card a hook REFUSED (never shown) whose option label contains the rejection phrase | **0** | 2 |
| I9 | an ANSWERED card whose result is the torn last line of the tail | **0** | 2 |
| I10 | a card with no result | **0** | 2 |
| I11 | an answered card, then "Starting now." | 2 | 2 |

**[M]** `probe.py`. Every bold row is the filed incident (an announcement, nothing running) passing in silence.

- **Pause marker.** The file is written with one shell command the agent is allowed to run; the refusal text itself
  names that command (**[M]** the I2 block message contains `.claude/paused`); it lasts 24 h, across every session
  that shares the main checkout; nothing removes it; and the ALLOW is silent. This is a second pause vocabulary
  beside `begin-plan.py --pause`, and backlog row 99 records the same defect class in the first one: a pause that
  "outlived the pause by four steps, a code review and a PR". CB1 is that class, not an instance.
- **Question exception.** The rule is "the last tool call was a question". The claim it stands for is "the turn is
  waiting on the owner". The two differ whenever text follows the card (I5), whenever the owner's reply is not a
  `type: user` record (I6: of 806 `queued_command` attachment records, 133 are human prompts **[M]**), and whenever
  the rejection phrase arrives in text the agent wrote (I7: the real `enforce-selection-card.sh` exits 2 and echoes
  an unlettered label; 48 real error results in the corpus echo an option label **[M]**).

### 1e. Is either one needed?

Tried to refute "not needed" three ways.

1. *A pending card is an owner wait the guard cannot otherwise see.* It never produces a stop: 0 of 207 **[M]**.
2. *A rejected card leaves the agent with nothing it may do.* It may say so; the continuation passes (I8') **[M]**.
3. *The owner must be able to pause the guard.* The owner's words are already sufficient: the agent quotes them and
   the continuation passes (I3') **[M]**. What the marker adds is making that pass silent and durable, which is the
   part CB1 objects to.

No input was found where removing both changes the final outcome of an honest stop; it changes only whether one
refusal is printed first.

## 2. Design problem or witness problem? Can a redesign remove it?

Design. The thrashing rounds each fixed their instance correctly, and each fix added a branch to a parser of
agent-influenced text, which the next round then found a new input for. A parser cannot be made total over text
its subject writes. The options, each with the inputs it gets wrong:

| Option | What it is | Inputs it still gets wrong |
|---|---|---|
| A | keep both; fold CB1 (shorter age cap), Cm2, Cm3 | I2a, I5, I6, I7, I9, I10 all still 0 **[M]** at HEAD; a cap of any length keeps I2a |
| B1 | pause marker carries its own end time, capped | owner 21:00 "stop until 02:30", cron wake 01:57, idle stop 01:58 → ALLOW; agent writes "until now + 12 h" → ALLOW **[M]** `probe2.py` |
| B2 | pause marker counts only if newer than the last prompt | needs the transcript reader; a queued prompt is not a `user` record → ALLOW; the agent touches the marker after the wake → ALLOW **[M]** `probe2.py` |
| B3 | question exception narrowed: rejected-only, phrase anchored, attachments reset it | I5 still ALLOW **[I]** (the rejected card is still the last tool call); the reader and its 26 mutations stay |
| C1 | remove the pause marker, keep the question exception | I5, I6, I7, I9, I10; thrashing component untouched |
| C2 | remove the question exception, keep the pause marker | I1, I2a, I2b; CB1 untouched |
| **D** | **remove both** | honest stops I3 and I8 cost one refusal (2 then 0) **[M]**; declined as XM5 in round 1 |

B1 and B2 are the strongest narrowings and both fail on the real chronology of the filed incident: the pause was
legitimate when written and wrong by the time the wake arrived. B2 is also equivalent to something the agent already
has, a one-turn self-declared pass, bought at the price of keeping the reader **[I]**.

Option D removes the component that thrashed and the class CB1 belongs to. It does not make the guard unforgeable:

| Row | World | HEAD | Both removed |
|---|---|---|---|
| W0 | an old quiet builder worktree | 2 | 2 |
| W1 | the agent touched one file in it 5 s ago | 0 | 0 |
| W2 | same at 9 min 59 s / 10 min 1 s | 0 / 2 | 0 / 2 |

**[M]** `probe.py`. That residual is in the worktree signal, outside this scope, and differs in kind: it expires in
ten minutes and requires faking work rather than declaring a wait. It is proposed as a backlog row below.

## 3. Recommendation

**Option D, inside the round 3 fold, then stop.**

1. Delete `_rejected`, `last_tool_asked`, `read_tail`, `paused`; the constants `PAUSE_MAX_S`, `PAUSE_FILE`,
   `REJECTED_MARK`, `TAIL_BYTES`; the `tail` parameter of `decide()`; the line in `main()` that reads the tail; and the
   pause and question lines of `decide()`. `main()` no longer opens `transcript_path` at all.
2. `decide()` order after the fold: not an object → NOT CHECKED; `stop_hook_active` → ALLOW; `agent_id` → ALLOW;
   usage stop → ALLOW; signals (a), (b), (c); else BLOCK. Every ALLOW now reads harness or filesystem state.
3. Rewrite the block message. It names no file to write and no tool to call. It names two outs: start the next job
   in this turn; or, if the owner told you to stop or only the owner can act, say so in one line quoting them and
   end the turn. It does not describe the guard's mechanics.
4. Fold round 3 finding Cm1 (the unpinned `__typename` shape check) as one case and one mutation. Cm2, Cm3 and CB1
   have no code left to apply to; the round document records them as dissolved by removal, not as fixed.
5. Same change, other files: `scripts/mutations/check-idle-stop.json` (drop the 26 tied entries, add the new ones);
   the count pin in `scripts/expected_mutations.py`; the docstring's case count and exception list; `.gitignore`
   (the three `.claude/paused` lines); backlog row 663's list of exceptions; the dashboard entry if it names them.

### Cases that must exist after the fold

1. **Marker identity.** With a `.claude/paused` file in the main checkout at each of an independent literal list of
   ages (fresh, 5 min, 20 h 53 min, 25 h), the 02:24 replay through `main()` exits 2, identical to no marker.
2. **Rejected card.** A transcript ending in a rejected card and a closing reply → BLOCK; the same payload with
   `stop_hook_active` true → ALLOW.
3. **Rejected card, then an announcement** (I5) → BLOCK.
4. **Transcript is never opened.** For each of a literal list of `transcript_path` worlds (missing, a directory, a
   FIFO, unreadable, a record nested 200,000 deep, a torn last line) the verdict equals the verdict with no
   `transcript_path`, and the call returns without reading it. The FIFO row is the one that fails by hanging.
5. **Block message.** It contains none of `.claude/paused`, `touch`, `AskUserQuestion`; it names both outs.
6. **Self-report class, identity.** For each of marker, rejected card, unanswered card, hook-refused card whose
   label holds the rejection phrase: verdict equals the no-state verdict. The list is a literal in the case, not
   derived from the code.
7. **Cm1.** A CI answer whose `__typename` shape is malformed → unread → BLOCK.
8. **Order.** `stop_hook_active`, `agent_id` and a usage stop each still ALLOW with nothing running.

Mutations to bind them: re-adding a marker read to `decide()` goes red on case 1; re-adding any transcript open to
`main()` goes red on case 4; restoring the old block message goes red on case 5.

**Stop condition.** The round this fold closes is round 4, under the round cap: findings are FILED unless a BLOCKER.
Two kinds of finding are expected and are not blockers: "an honest stop costs one refusal" (declined as XM5; cite
it), and "a work signal can be forged" (file under the backlog row proposed below). A BLOCKER would be an input,
reachable without the agent forging a work signal, where an announcement-only stop exits 0 on its first attempt.

**What would make this recommendation wrong:** a harness path where a stop fires while a card is pending (the corpus
has 0 of 207; a harness change could add one), or evidence that a refusal after a rejected card makes the agent
start work the owner just declined. Neither was observed; the second was not tested.

## Proposed backlog rows (not written to `docs/backlog.md` by this review)

1. **`check-idle-stop.py`: the worktree signal accepts a `touch`.** W1 above: one file touched in a builder worktree
   allows a stop for ten minutes. Falsifier: W1 exits 0. A fix would need the signal to read something a builder
   produces and an idle orchestrator does not; no design is proposed here.
2. **`check-idle-stop.py`: the usage-stop ALLOW reads a cache file the agent can write.** **[I]**, not probed in this
   review. Same class as row 1; may be one row.
3. **An owner pause, if one is wanted, must be a fact the agent cannot author.** The owner paused or stopped work in
   3 of 1,436 prompts. If a silent multi-turn pause is ever asked for, it belongs with `begin-plan.py --pause`
   (one vocabulary, never silent, per backlog row 99), not in a second marker. A decision for the owner, not work.
4. **What record does a cron-fired wake produce?** Not determined here (see Bound). Any future rule keyed on "the
   last prompt" depends on it, and 133 human prompts already arrive as attachments.

## What was decided this milestone and is not written down

- **An ALLOW in this guard reads only state the stopping agent did not author.** This is the rule option D applies.
  It is an instance of the repository's existing practice (a harness cannot read a cause from a child's text) and
  needs a pointer in the script's docstring, not a new rule.
- **"One nudge, not a lock" is the pause mechanism.** The owner's instruction to stop is honoured by the agent
  stating it on the continuation. No document says the continuation is the intended out.
- **`stop_hook_active` is set by any Stop hook's refusal**, so when the sibling `block-idle-stop.sh` (registered
  first) refuses, this guard does not judge that turn **[I]** from the hook contract; not probed with both hooks.

## Bound of this review

| Claim | Basis |
|---|---|
| probe rows I0 to I11, W0 to W2 | **[M]** `probe.py` through `main()` on a `git archive` copy of the head; the copy's self-test is 93/93 |
| "both removed" column | **[M]** a two-line patch to `decide()` on a second copy, not the full deletion; the reader still runs there |
| 3,147 stops, 4 True, 207 cards, 0 without a result | **[M]** 82 transcripts of this project only; card counts differ from round 2's because ids are deduplicated per file |
| 0 uses of the marker | **[M]** a literal-string search; a paraphrased command would be missed |
| 3 of 1,436 pause prompts | **[M]** one regex over string-content `user` records; a floor, not a count |
| B1, B2 wrong inputs | **[M]** on prototypes of the rule (`probe2.py`), not on a patched guard |
| B3 still allows I5 | **[I]** not prototyped |
| ten findings in the two exceptions and the reader | **[I]** hand count from the round documents |
| 26 of 99 mutations, 29 of 93 cases | **[M]** first-edit anchor resolved against the source; case count by a regex over `case(` statements |
| usage cache is agent-writable | **[I]** not probed |
| record shape of a cron-fired wake | NOT DETERMINED: the records found were compaction carry-overs, not firings |

Not examined: the three work signals beyond W0 to W2, the launcher's exit-code mapping, and the interaction with the
sibling Stop hook on a live session. The eight cases above were not written or run; the option D column was measured
on a patch, so the fold's own self-test and mutation sweep are its first real gate.
