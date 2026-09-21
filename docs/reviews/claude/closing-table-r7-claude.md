# closing-table — round 7 — independent Claude half

**Verdict: NOT CONVERGED.** 2 High, 3 Medium, 2 Low. Nothing here is an incident — the guard is
warn-only and already merged, so every finding is a follow-up PR.

Subject: `scripts/check-closing-table.py` at `master` `371d6fdb`, plus
`.claude/hooks/block-idle-stop.sh` and `scripts/mutations/check-closing-table.json`.
First independent reader: rounds 1–6 were Codex-only; each "claude half" was a coordinator
self-review by the author.

---

## Method — what I actually ran

I replayed the **shipped functions, unmodified** (imported by path) over this project's own
**765 real transcripts** in
`~/.claude/projects/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/*.jsonl`,
simulating a Stop at every turn boundary:
`judged_window(coalesce_injected(windows(records)))` → `closing_acts_of` →
`decide(final_text_of(texts_of(...)))`. Probe scripts are in the session scratchpad
(`probe1.py`–`probe11.py`, `mut.py`); mutation experiments ran on `cp -R scripts` in `mktemp -d`.
Nothing was written in the repo except this file. No git mutation, no Postgres, no schema gates.

**One assumption, stated:** my replay counts one Stop per turn window. Real sessions have at least
one Stop per window (more, when a stop is blocked), so emission counts below are a **lower bound**.

**The baseline nobody has measured in six rounds.** r6's generalisation run ("5,287 unseen Bash
calls … 456 fires, 0 confirmed errors") measured the **trigger** — whether `closing_acts_of` is
right about an act. It did not measure the **verdict**. Here it is:

| measurement (765 transcripts) | value |
|---|---|
| judged turns, total | 1,711 |
| … containing a closing act | 846 (49.4%) |
| … of those, turns that WARN | **821 (97.2%)** |
| distinct turns warned | 744 |
| warning **emissions** (≥1 per stop) | **1,183** — 439 of them repeats of a turn already warned |
| firing rate on turns *after* the rule was written (since 2026-09-04) | **262 / 277 = 94.6%** |

The docstring's justification for warn-only is that "the log is what can later answer *does it
false-alarm?*". The corpus answers it now, and three of the findings below are what it says.

---

## F1 — High — the marker enforces one *rendering* of the rule, and the warning then says something untrue

`has_closing_table` → `_CHECK_CELL` / `_RESULT_CELL` require a header row containing a cell that is
literally `check(s)` and one that is literally `result(s)`.
`docs/process-checklists.md:463-486` states the rule as three properties — *one row per claim*,
*evidence in the row*, *every row could have come back ❌* — and then shows **one example** that
happens to use those headers. Nothing in the three rules mentions a header at all.

Measured, over the 744 distinct warned turns, and restricted to the era in which the convention
existed (since 2026-09-04, 262 warned turns):

| | all 744 | since 2026-09-04 (262) |
|---|---|---|
| closing message contains a rendered table (header + separator + ≥1 row) | 372 (50.0%) | 160 (61.1%) |
| closing message **ends** with one (≤8 lines follow the last table row) | 91 (12.2%) | **54 (20.6%)** |
| closing message contains a **headerless key/value** table | 149 (20.0%) | 60 (22.9%) |

So roughly **one recent firing in five lands on a message that visibly ends in a table**, and the
sentence `decide` prints over it is *"the previous turn completed a commit, a push and **closed with
prose**"*. That sentence is false in those cases. Two verbatim examples from turns that committed
and pushed:

```
| | |
|---|---|
| `master` | `738249d`, clean, CI `verify` passing |
| Prod app | release **v6** (2026-08-11 15:47Z) |
| Prod schema | 25 migrations, `local == remote` |
| Open PRs | none |
```

```
| item | state |
|---|---|
| 14 mutations for `gen-goals-page.py` | written; anchors unique, all matching once, every `expect` names a real case |
| `EXPECTED_MUTATIONS` sum | `524 → 538` |
```

The first shape — **headerless key/value, claim left, evidence right** — is the single most common
table form in this project's closing messages and is *structurally* unrecognisable here: it has no
header row for `_CHECK_CELL` to match. It satisfies all three written rules.

**I am disagreeing with a prior reviewer, and say so.** r1 Codex wrote: *"I would not count
alternate wording like `Evidence | Status` as a defect: `docs/process-checklists.md:459`
specifically names a CHECK / RESULT table."* That is a reasonable reading of the heading — but it
was reasoning from the document alone. With the corpus in hand, the cost of that reading is
measurable: the guard's own cry-wolf doctrine (`backlog #56`: a noisy warn-only gate gets switched
off) is violated by the guard's central judgement, after six rounds spent making the *trigger* side
quiet (segments, quotes, heredocs, vetoes).

**What I would change** — not "accept any table", which would pass a comparison table in a chatty
message. Either:
  (a) accept a table in the final block whose header has a check-ish column **or** whose header row
      is empty (the key/value form), keeping the separator + ≥1-row requirement; or
  (b) keep the strict marker and **fix the sentence** so it says *"no table headed check/result"*
      rather than *"closed with prose"*, and name the accepted form in the message.
(b) is cheap and makes the guard honest immediately; (a) is the one that matches the written rule.
Which of the two is the user's call, because the marker is a thing they visually scan for.

---

## F2 — High — a teammate `SendMessage` splits a turn exactly like the `<task-notification>` that `coalesce_injected` exists for, and is not folded

`coalesce_injected` folds a window whose opener matches
`_INJECTED = ^\s*<(?:task-notification|system-reminder)\b`. Measured census of every **window
opener** across the 765 transcripts:

| opener head | count | `isMeta` | folded today? |
|---|---|---|---|
| `<task-notification` | 650 | None | ✅ |
| `Another Claude session sent a message` | **332** | None | ❌ **not folded** |
| `<command-name` (slash command) | 94 | None | n/a — a real instruction |
| `<local-command-caveat` | 87 | True | excluded upstream by `_is_turn_boundary` |
| `<local-command-stdout` | 34 | None | n/a |
| `<system-reminder` **as an opener** | **0** | — | ✅ but never exercised by reality |

A teammate message arrives asynchronously mid-turn for exactly the reason a task notification does —
this repo runs agents constantly — and lands in the same place: between the act and the report.
Re-running the identical replay with that one string added to `_INJECTED`:

| variant | judged turns with an act | warning emissions |
|---|---|---|
| shipped | 845 | **821** |
| + `Another Claude session sent a message` folded | 717 | **696** |

**128 judged turns and 125 emissions (15.2% of all firings) are fragments manufactured by a boundary
no person made.** Sampled openers confirm it directly, e.g. a judged window opened by
`Another Claude session sent a message: <teammate-m…` holding the commit, with the report in the
next fragment.

Two things make this worse than a missed case:

* It is the **same defect, in the same function**, that `coalesce_injected`'s docstring says was
  "⛔ FOUND ON THE REAL TRANSCRIPT, not in a fixture" — found again on the same corpus.
* `_INJECTED` is a hand-written **enumeration of two spellings**, one of which never occurs as an
  opener and one of which is the top case; the highest-volume real case is absent. This project
  ships `check-producer-enumeration.py` because membership should come from a defining expression.
  One already exists next door: `check-banner-armed._META_IS_REALLY_A_MESSAGE` names
  `"Another Claude session sent a message"` as a record that is *not the human typing*. The fold
  rule does not consult it.

---

## F3 — Medium — the guard is stateless, has no anti-nag, and re-warns the same turn: 1,183 emissions for 744 turns, worst case 36 for one turn

There is no journal by design ("no journal, no sample, no late-flush"), and `judged_window` returns
*the last judgable window before the live one*. When several windows in a row are opened by
notifications, coalescing folds each into the growing **live** window, so the same previous turn is
selected again at every Stop.

Measured: **1,183 emissions across 744 distinct turns — 439 repeats (37%).** Distribution of
emissions per turn: `1:557, 2:102, 3:38, 4:18, 5:9, 6:9, 7:7, 9:1, 12:1, 31:1, 36:1`.

Worst case, `62196080-8a63-4c8f-a689-80aa431a832f.jsonl`: one turn warned at 36 consecutive window
indices (75→110). The windows in between are a run of `<task-notification>` openers for the same
background task; the judged subject never moves.

This matters for three reasons, in ascending order:
1. repeated identical stderr about a message the reader has already scrolled past is the definition
   of a nag, and the sibling observer `check-plan-progress` carries an explicit anti-nag for
   precisely this;
2. the **log double-counts**. The docstring says the log is how the false-alarm rate "gets measured
   rather than guessed" — at 1.59 lines per turn, `wc -l` on that log is not a turn count;
3. one turn contributing 36 lines will dominate any later reading of it.

`check-banner-armed.py` solved the same problem with a journal keyed on the turn's opener; this
guard has the opener in hand (`judged.opener`) and uses it for nothing.

---

## F4 — Medium — the declared self-test count is a literal, so the external observer is reading a number the script made up

```python
declared = re.search(r"--self-test\s+#\s*(\d+)\s+cases", __doc__ or "")
total = 128
...
print(f"{total}/{total} passed")
```

`total` is a constant compared against the docstring's constant, and the printed ratio is that same
constant. `check-selftest-counts.py` runs the suite as a subprocess and parses the `N/M … passed`
line — so it compares 128 to 128 and is green whatever the suite contains.

**Ran it.** On `cp -R scripts` in a temp dir I deleted four `check(...)` calls
(`acts: git status is not an act`, `acts: none`, `final: last non-empty wins`,
`final: empty list -> None`):

| | control | after deleting 4 cases |
|---|---|---|
| `grep -c '    check('` | 128 | **124** |
| printed summary | `128/128 passed` | **`128/128 passed`** |
| exit code | 0 | **0** |

Both sibling guards in the same POPULATION derive it instead —
`check-banner-armed.py:1669` and `check-ci-watched.py:264` both do
`passed = sum(1 for _, ok in cases if ok)` / `len(cases)`. `check-plan-code` does
`count_drift(__doc__, ok, fail)`. `check-selftest-counts.py`'s own docstring says *"a number a
program reports about itself is not evidence"* — this is the newest member of its POPULATION,
pinned in the same commit that created it, and it is the one member where the number is invented.

Fix is two lines: count the `check()` invocations (e.g. increment in `check`) and print the real
ratio.

---

## F5 — Medium — "no way for the two to disagree about a turn" is now false, and the question it dodges was never asked

The docstring, under *WHY THE TRIGGER LIVES IN THE TURN*: *"there is no journal, no sample, no
late-flush, and **no way for the two to disagree about a turn**."* `coalesce_injected` then
re-segments the borrowed windows **for this guard only**. At one Stop, on one transcript,
`check-banner-armed.py` judges window *k* while `check-closing-table.py` judges a window spanning
*k-1..k*. That is a disagreement about the subject, asserted away in the file that introduces it.

`coalesce_injected`'s own docstring defends the composition ("answers a different and narrower
question — *was that boundary a PERSON?*"), and as engineering that is sound: changing the borrowed
rule would silently move the banner guard's subject. What is not sound is that the framing let the
obvious follow-up go unasked in all six rounds: **if a notification-split turn is the wrong subject
here, it is the wrong subject there too.** A fragment cut between a `## ▶ STEP` banner and the work
it announces has the same false-alarm shape the banner guard warns about.

I did not measure the banner guard's exposure (out of subject) — **could not establish** its
magnitude. But 650 task-notification openers and 332 teammate openers exist in the same corpus the
banner guard reads, so the question is owed an answer rather than a composition argument.

Minimum fix: delete or qualify the sentence. Better: file the banner-guard question.

---

## F6 — Low — self-test honesty: three cases that pass with the behaviour they name removed, plus two unfalsifiable guards

Mutation sweep on a temp copy (`mut.py`, 10 targeted mutations, control green first):

| mutation | result | what it means |
|---|---|---|
| `_SEGMENT_SPLIT` drops `\|` | **SURVIVED** | the case `"acts: a real pipe still splits"` (`git push 2>&1 \| tee log`) still yields `["a push"]` without pipe-splitting, because the segment still *starts* with `git push`. The case does not test what its label claims, and the manifest has no mutation for it |
| backslash escapes **inside single quotes** too | **SURVIVED** | the documented POSIX rule (*"a backslash escapes inside double quotes and NOT inside single quotes"*, `mask_quotes`) has no falsifier. `"acts: a single-quoted span has no escapes"` uses `echo 'a; git push'`, which contains no backslash. A real input that would break under the mutation: `sed -e 's/a\\//' f && git push` — the `\` would swallow the closing quote and mask the later real push, i.e. a **miss** |
| `_cells`: `len(s) < 3` → `< 1` | SURVIVED | guard is unreachable — any shorter line fails the header match anyway |
| `has_closing_table`: `len(cells) < 2` → `not cells` | SURVIVED | same; a 1-cell row cannot carry both a check and a result cell |
| `coalesce_injected`: drop `[opener]` from the merged body | SURVIVED | the case `"coalesce: its records join the turn it interrupted"` asserts `[x for x in body if isinstance(x, str)] == ["A","B"]`, which **filters the opener out by construction**. Harmless today (the opener is never read), but the behaviour is asserted in the docstring and tested by nothing |

Also, by reading: `"log display: a repo-relative path is unchanged by the redirect guard"` is
mislabelled and duplicates the case above it — `WARN_LOG` is `/tmp/elsewhere/x.log` at that point,
so nothing repo-relative is under test; both cases assert the same `/tmp/elsewhere` behaviour.
That is `process-checklists.md`'s own *mislabelled row* trap, inside the suite for the guard that
enforces it.

Controls: the same sweep killed `log-display-never-relative`, `dedupe-removed`,
`final-text-first-not-last` and `rehearsal-only-dryrun` via the case each names, so the harness and
my method were working.

---

## F7 — Low — the log line cannot identify the turn it is about

`log_line` writes `{when}\t{session}\t{acts}` — e.g. `2026-09-20T…	s	a commit+a push`. The sibling
`check-banner-armed.log_line` writes a **fingerprint of the judged turn** (`unarmed	STEP 3 of 5`),
and `TurnWindow`'s docstring says carrying the opener exists partly for *"the log line — which turn
a verdict is about, now that it is not the live one"*. Here the opener is available and unused.

With a 94.6% firing rate and 1.59 emissions per turn, a log of `a commit+a push` lines cannot
answer the question the docstring assigns it. Adding the opener's uuid (or the first 40 chars of the
closing message) makes each line adjudicable.

---

## Answers to the five questions the brief asked

**1. Should the rule exist in this shape?** Yes as a mechanism, with one reservation and one
correction.
* Blindness to work that closes nothing is real but small in the right direction: 49.4% of judged
  turns contain a closing act, so the guard sees half of all turns and misses the memory-file /
  docs-only class named in the docstring. Under-firing on a warn-only observer is the safe side.
* One turn of latency is **not** the problem the brief suspected — `final_text` in an earlier block
  of the same turn costs only 7 false alarms in 821 (0.9%), and turns with no text at all
  (`decide(None, acts)`, the r1 High) fired **0 times in 765 transcripts**. The r1 High is a real
  hole and an empirically empty one.
* The reservation is F1 + F3 together: at today's compliance the guard emits ~1.6 warnings per
  closing turn on ~95% of closing turns, and ~20% of those land on a message that ends in a table.
  That is the profile of a gate that gets switched off, and the log as currently written cannot
  prove otherwise.

**2. The marker.** It enforces one rendering, not the rule — see F1, with the measurement r1 did not
have.

**3. What a reader SEES, and can they act?** Two channels, and one is silent about it:
* ordinary stop → the wrapper folds `TABLE_RC` into **exit 1**, stderr goes to the **human**, one
  turn after the message they already read. Nothing is actionable; the value is pattern-noticing,
  which is what the log is for — and F7 says the log cannot support it.
* a stop **blocked** by `check-plan-progress` → the whole hook exits **2** and stderr goes to
  **Claude**, not the human. Claude cannot amend a sent message; the only available response is to
  emit a table in the *next* close, attaching the artifact to a different subject. The warning is
  still logged, so it counts in the record while nobody who could act on it saw it. The r1 Medium
  fix (moving the observer ahead of the blocking check) made the verdict *exist* on that path; it
  did not make it *reach a reader*.

**4. Self-test honesty.** F4 (the count is fabricated) and F6 (three cases and two guards with no
falsifier). The 37-entry mutation manifest is otherwise in good order: every entry names a real
case, and the anchors I checked resolve.

**5. Interaction with `check-banner-armed.py`.** `coalesce_injected` is sound as composition — it
does not mutate the borrowed rule, and the semantic probe in `_load_banner_guard` (a drifted fake
module → `CANNOT RUN`) is the strongest thing in this file; I mutated it and it refuses correctly.
But it does make the two guards disagree about turn boundaries (F5), and it does not prevent the
same turn being judged at 36 consecutive stops (F3). The banner guard's own exposure to the split is
unmeasured.

---

## Verdict

| check | result |
|---|---|
| Replay over 765 real transcripts, shipped code unmodified | ✅ 1,711 judged turns, 846 with an act, 821 warnings |
| Marker vs the written rule | ❌ **F1 High** — 54 / 262 recent warnings land on a message ending in a table |
| Injected-boundary census | ❌ **F2 High** — 332 unfolded teammate openers, 125 emissions (15.2%) |
| Repeat-warning rate | ❌ **F3 Medium** — 439 repeats / 1,183 emissions; worst turn 36× |
| Declared self-test count | ❌ **F4 Medium** — 124 cases still print `128/128 passed`, rc=0 |
| Two-guard disagreement claim in the docstring | ❌ **F5 Medium** — false since `coalesce_injected` |
| Mutation sweep for vacuous cases | ❌ **F6 Low** — 5 survivors on a temp copy, 4 controls killed correctly |
| Log adjudicability | ❌ **F7 Low** — no turn identity |
| Borrowed-rule semantic probe | ✅ refuses a drifted module, verified by mutation |
| Veto / heredoc / quote machinery from r1–r6 | ✅ no regression found; I did not re-report fixed items |
| Repo left untouched apart from this file | ✅ no git mutation, no Postgres, temp copies only |

**NOT CONVERGED.**

**The single most important change:** make the marker recognise the closing-table shapes this
project actually writes — or, if the strict `check`/`result` header is deliberate, change the
warning to say *"no table headed check/result"* instead of *"closed with prose"*. Everything else
here is a bounded repair; this one decides whether a 95% firing rate is a signal the user will act
on or noise they will turn off.

**REVIEW GAP: none for this half.** This is the first independent Claude half the subject has had;
the Codex half for r7 is the coordinator's to dispatch.
