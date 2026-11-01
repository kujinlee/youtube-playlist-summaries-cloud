# Trimming the always-loaded docs — walkthrough

**What this is.** A DRAFT pull request that shrinks the text re-sent to the model on every turn,
without deleting any rule. Every paragraph that left an always-loaded file was MOVED, verbatim, into
an on-demand doc, and a one-line rule plus a pointer stayed behind. This page is for the owner's
walk-through before merge.

## What is loaded on every turn

`CLAUDE.md` imports three files with `@` lines, and nothing nests further (none of the three has an
`@` line of its own):

```
CLAUDE.md
├─ @AGENTS.md
├─ @docs/dev-process.md
└─ @docs/plugins.md
```

Also loaded every turn, and NOT touched here: the global `~/.claude/CLAUDE.md` (6,688 bytes) and the
memory index `MEMORY.md` (out of scope).

## Before and after

Measured on this branch against `origin/master` (bytes as `wc -c`; characters as Python `len`).

| File | Before | After | Change |
|---|---:|---:|---:|
| `CLAUDE.md` | 1,044 B | 1,044 B | — |
| `AGENTS.md` | 327 B | 327 B | — |
| `docs/dev-process.md` | 25,453 B | 14,607 B (214 lines) | −10,846 B |
| `docs/plugins.md` | 21,118 B | 9,949 B (164 lines) | −11,169 B |
| **Always-loaded total** | **47,942 B** | **25,927 B** | **−22,015 B (−46%)** |

**Expected per-turn saving: about 22 KB, roughly 5,500 tokens.** ⚠ The token figure is an ESTIMATE
at about 4 characters per token; no tokenizer was run. ⚠ The 10-30 usage study put this chain at
about 162 KB. The four files measure 47.9 KB on `origin/master` today, so that figure and this one are
not measuring the same thing, and the study's "about 15% of each call" should be re-derived before
anyone quotes a saving as a percentage of a call.

The on-demand docs grew by the moved text: `process-checklists.md` +17,073 B, `review-method.md`
+14,423 B, `process-rationale.md` +930 B. They load only when a task reads them.

## Where each section went

| Section (was) | Where it went | Why it is safe to load on demand |
|---|---|---|
| `dev-process.md` → *What is mechanically enforced*: the 29-row table, about 14 KB, with every row's measurements, ⟳ dates, case counts and history | Spine keeps ONE line per row (name + what it enforces). Full rows moved verbatim to `process-checklists.md` → *Mechanically enforced checks — the full rows* | The script is the truth and runs whether or not the row is read. What a turn needs is *that* the check exists and what it refuses; the measurements matter only when someone works on that guard, which is exactly when the checklists doc is read |
| `dev-process.md` → *Phases*: the thrashing arming-condition paragraph (the 4→5→4 measurement, the 10-20 ranking note) | Spine keeps the rule: two consecutive fix-caused rounds in one component; four rounds obliges asking, does not fire; rank by total appearances. Full paragraph moved to `review-method.md` → *The arming condition — full account* | The rule is what must hold on every turn; the evidence for it is needed only when a review round is deciding whether it is thrashing — and `review-method.md` is the file read when a round starts |
| `dev-process.md` → *Keeping this file short*: the 576-line history and the 09-20 eviction-queue note | Spine keeps the "ask whether it can be a script" rule and the budget pointer. History moved to `process-rationale.md` → *Why the spine is short — history moved out of the always-loaded files* | History is rationale; it changes no action |
| `plugins.md` → *Session Handoff*: the "locally modified" note, the three-layer table, layer 2's falsifier, what layer 2 does not do, the `.claude/commands/` note | The RULE box stays untouched. A five-line summary (authority / leading gate / convenience; re-author commands, never patch vendored copies) stays. Full text moved to `process-checklists.md` → *Session handoff — the three layers* | The rule that decides where a handoff is written is still always loaded, and the hook still blocks a wrong path before anything is written. The layer table matters only when someone edits the skill or the guard |
| `plugins.md` → *Code Review*: the 2.5 KB Agent-tool paragraph, the Codex-model measurement, the rc=3 and output-contract boxes, the backtick incident, the two-sandbox note, the fail-open list, the bounded-wait note, about 12 KB in all | Spine keeps one line per rule: Claude half pre-authorised (and bounded by *Running agents concurrently*), round topology pointer, resolve the frontier model and never accept a hidden one, the fallback rule including the TIMEOUT exception, the `codex-review.py` command with all four exit codes (rc=3 is NOT a fallback), the per-half output contract, filing under `docs/reviews/<writer>/`, two sandboxes, fail-open, bounded wait. Full text moved verbatim to `review-method.md` → *Running the review halves — full detail* | Every rule a coordinator acts on mid-turn is still in the spine. The measurements behind them are needed when a review round is being run, and `review-method.md` is the file whose read-trigger is "a review round is starting" |

**Kept as they were** (they are rules, the merge/HOLD house rule and the security constraints):
*Human-in-the-Loop Policy*, *Session Resume*, *Roadmap & Task List*, the Phases table, Phase 3 and
Phase 5 rules, the architecture-review paragraph, *Not yet in CI*, the "anything longer than a line
goes in a FILE" rule, *Tools*, *Project-Specific*, and every plugin table in `plugins.md`.

## Two small text changes made during the move

- Three bare references in the moved table were qualified, because the reference-namespace guard
  checks added lines: `#56` → `backlog #56` (twice) and `#137` → `backlog #137`. Both were checked
  against `docs/backlog.md` and the merge log.
- Each moved block opens with one italic line saying it was moved, from where, and that the rule
  still stands in the spine.

## What the owner might push back on

- **The condensed lines restate rules that the moved text also states.** That is the shape the brief
  asked for (keep the rule, move the account), but it is two copies. Each moved block's header says
  the spine line is the rule and the block is its account. A guard does not enforce that.
- **Stale line-number citations into `dev-process.md` already existed and are NOT fixed here**
  (`check-roadmap-consistency.py` prints `dev-process.md:102`, which on `origin/master` is already a
  table separator; `check-rc-contract.py`, `check-plan-code.py` and `check-schema-gates.sh` cite
  `:108` and `:142` in comments). Fixing them touches `scripts/`, which this docs-only PR avoids.

## Suggestions for the global `~/.claude/CLAUDE.md` (not edited)

It is 6,688 bytes and loaded every turn in every project. Candidates to move to an on-demand file:

- The banner section's history: the "settled 2026-10-16 after three variants" and "re-derived it
  wrongly on 2026-10-19" notes, and the whole "A SCRIPT CANNOT DO THIS FOR YOU" paragraph — keep its
  one-line rule (the banner must be in the assistant's own visible text).
- The thread-line paragraph's origin story ("added 2026-09-04 at the user's request…") — keep the two
  glyph examples.
- The "This one is convention, not a machine" note under *Open every session*.
