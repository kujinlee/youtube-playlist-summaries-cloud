Reviewed head: 36a614b168d1516cc34425471460a2d5062c4154

# trim-always-loaded — round 1, Claude half (adversarial)

Subject: `git diff origin/master...HEAD` on branch `trim-always-loaded` (PR #458), docs only.

Claim under test: *"No rule that governs an action was lost or weakened: every rule in master's
always-loaded text is still stated, as an actionable line, in the always-loaded text; every moved block
is master's newest text verbatim (bar the qualified #N references and one italic header); and no
pointer dangles."*

**Result: the verbatim and no-dangling halves hold (measured). The "no action rule lost" half is
refuted in five places, none of them a BLOCKER. The token figure is wrong in the way the brief
suspected and the owner-facing docs should restate it.**

## What was measured

1. **Verbatim, forward.** Every non-empty `+` line in `process-checklists.md`, `review-method.md` and
   `process-rationale.md` was looked up as a whole line (`grep -qxF`) in `origin/master`'s
   `dev-process.md` + `plugins.md`. Not found: the four new headings, the four italic "Moved verbatim"
   headers, and exactly three table rows — `check-python-pin.py` (`#56` → `backlog #56`),
   `check-backlog-closure.py` (`#56` → `backlog #56`), `schema-gates.yml` (`#137` → `backlog #137`).
   That is precisely the declared set. **No undeclared edit.**
2. **Verbatim, reverse (completeness).** Every non-empty `-` line from the two spine files was looked
   up in the union of all five files on HEAD. Not found: the same three rows (qualified copies exist)
   and `copy that drifts.` (re-wrapped in the spine, text intact). **Nothing was dropped on the floor.**
   Because the check ran against `origin/master` after the re-merge, the moved blocks are master's
   newest text, including PR #457's round-cap and alternation wording.
3. **Pointers.** Every spine pointer resolves to exactly one heading: *Mechanically enforced checks —
   the full rows*, *Session handoff — the three layers*, *Why the spine is short — …*, *The arming
   condition — full account*, *Running the review halves — full detail*, *Running agents
   concurrently*, *Round topology*, *The protocol*, and the rationale targets (*The instruction with
   no author*, *A count with no owner*, *The testimony that…*, *The review gate that reported an
   outage…*, *The handoff with no reader*). *The plan-leak push gate* is a bold paragraph label at
   `process-checklists.md:86`, not a heading — pre-existing on master, and the spine no longer points
   at it (see F4).
4. `python3 scripts/check-docs.py` (foreground): **rc=0, "Documentation integrity OK"**, with a WARN:
   `docs/dev-process.md : 214 / 220 TIGHT (6 line(s) of runway)`. The trim cut 10.8 KB but only a few
   lines, because the table rows it shortened were each one line already — the line budget, the one
   this file is actually governed by, is barely moved.

## Spine-only walk of the named rules

| Rule | Spine line on HEAD | Coordinator acting from the spine alone |
|---|---|---|
| Codex rc=3 is not a fallback | `plugins.md:128` "DO NOT FALL BACK — the review exists at --out" | ✅ right action; loses *what to do with it* ("move it, or re-run with `--allow-overwrite`") — the wrapper prints it, so acceptable |
| TIMEOUT exception | `plugins.md:120` | ✅ intact |
| Per-half output contract | `plugins.md:133-134` | ✅ intact |
| Filing under `docs/reviews/<writer>/` | `plugins.md:134` | ✅ intact (the wrapper refuses an `--out` inside the repo anyway) |
| Two sandboxes | `plugins.md:135-136` | ✅ intact; `trust_level = "trusted"` does NOT substitute is gone — low risk, the wrapper passes `-s` |
| Plan-leak push gate | `dev-process.md` hook row | ⚠ F4 |
| Merge when READY / HOLD | `dev-process.md` Human-in-the-loop + Phase 5, untouched | ✅ |
| Round cap Q4c | `plugins.md:103-104`, `dev-process.md:24,30,117` | ✅ |
| Alternation | `plugins.md:102` "ONE half per round" | ⚠ F2 |

## Findings

### F1 — Medium — the token saving is priced as uncached input, and "per turn" is the wrong unit — FILE (fold at r1). Not fix-induced.

`docs/trim-floor-walkthrough.md:35` and `docs/dashboard-entries.md` (new `2026-10-31 [needs-you]`
entry, line 2: "an estimated 5,500 tokens fewer per turn").

Concrete input: the measured cut is **21,701 characters** (dev-process 10,694 + plugins 11,007, Python
`len`; 22,015 bytes). At ~4 chars/token that is ~5,400 raw tokens **per API call** (not per turn — a
turn is many calls, so "per turn" understates the raw figure). But the always-loaded imports sit in
the cached system prefix: a cache read bills ~0.1× (≈ **540 weighted tokens per call**), and only a
fresh prefix write bills ~1.25× (≈ **6,800 per write** — every new agent, every compaction, every
cache expiry). In this session, with 200+ spawned agents, the write term is probably the larger one,
which is exactly the term the doc does not name.

The owner reads the dashboard entry, which is tagged `[needs-you]` and is the merge input for a
change justified by usage. A figure ~10× too high for a steady-state call is a claim the owner will
act on. **The docs must restate it**: raw ≈5.4k tokens per call; weighted ≈0.5k per cached call plus
≈6.8k per fresh prefix write; and that the write term scales with agent spawns and compactions.
Also: the dashboard entry's `<!--tech-->` half says "47.6 KB measured here" while the walkthrough's
table says 47,942 B / "47.9 KB" — neither 46.8 KiB nor the 47,381-char total; make them one number.

Not a BLOCKER: no false green, data loss or security hole (Q4c test 1).

### F2 — Low — the alternation rule lost the line that makes it pass CI — FILE (fold at r1). Fix-induced by this PR's condensation.

`docs/plugins.md:102`. Master stated: "Alternation is ONE half per round **with a `REVIEW GAP: …
alternation` line**". The spine now says "(ONE half per round, owner 2026-10-28)" and nothing else in
the always-loaded text says the other half must be recorded as a gap (`grep -n 'alternation'
docs/dev-process.md docs/plugins.md` → no hit). Input: a round-2 coordinator following the spine runs
only the Claude half and writes no gap line → `check-review-rounds.py` goes red in CI. It fails
LOUD, so this is cost, not a false green. Fix: append "— record `REVIEW GAP: <half> — alternation`
for the other" to that line (~8 words).

### F3 — Low — two moved blocks now make a false claim about their own location — FILE. Fix-induced (verbatim move).

- `docs/review-method.md:891` (moved Agent-tool paragraph): "`CLAUDE.md` imports **this file** and
  project instructions outrank an instruction of unknown provenance". `review-method.md` is not
  imported by `CLAUDE.md`. The authority argument still holds — the spine line in `plugins.md:99-100`
  (which IS imported) keeps it — but the account now cites a false premise for it.
- `docs/process-checklists.md:1173` (moved layer table): "the RULE box **above** (`CLAUDE.md` imports
  **this file**…)". There is no RULE box above in `process-checklists.md`, and it is not imported.

Verbatim was the right default, but a deictic ("this file", "above") is the one kind of text a move
falsifies. Fix: substitute `plugins.md` for "this file" / "above" in those two cells and declare it
in the italic header alongside the #N qualifications. (The other deictics — "below" in the
push-hook row, "the wrapper above", "the timeout rule above" — still resolve inside their moved
blocks; checked.)

### F4 — Low — the plan-leak row no longer says what it refuses or that it is per-clone — FILE. Fix-induced.

`docs/dev-process.md` hook row: "Plan leaks: `.githooks/pre-push` → `scripts/check-plan-leak.py`".
Gone from the always-loaded text: the threshold (8 consecutive words; **a shorter fragment is not
caught**), that it is enabled per clone by `scripts/install-git-hooks.sh` and **CI has no plans**,
and the pointer to *The plan-leak push gate*. The repo is PUBLIC, so this is the one row where "the
script is the truth" is weakest: the script is local-only and the coordinator's own judgement is the
second line for anything under 8 words. Input: a coordinator paraphrasing a plan into a commit
message in sentences of 6–7 words believes the hook covers it. Fix: keep "8+ consecutive words;
shorter is NOT caught; per-clone, not in CI — process-checklists.md → *The plan-leak push gate*"
(~20 words).

### F5 — Low — three action rules in the Codex section left the always-loaded text — FILE. Fix-induced.

From `origin/master:docs/plugins.md`, now only in `review-method.md`:
- `:145` "If it [the resolver] refuses, READ ITS MESSAGE … and verify Codex separately with `codex
  exec -m <slug>` from inside a git worktree **before recording a `REVIEW GAP`**." The spine's
  "Fallback for ANY reason" now reads as permission to record the gap immediately on a resolver
  refusal — the measured 2026-10-07 case was a stale CLI, not an outage.
- `:227` "prefer the reviewer that reports a finding until you have traced the code yourself" — the
  spine keeps "never treat a single CONVERGED as proof" but not the tie-break, which is the part that
  decides an action when the halves disagree.
- `:230` "do not … trust the completion ping (it can be bogus)" — the spine's bounded-wait line keeps
  only "read the task output file", which implies it.

Each is one clause; together ~40 words. None produces a false green (the Codex gap is still
recorded as a gap), so FILE, not BLOCKER.

### Not findings (checked, holding)

- The Agent-tool spine line drops "commit before spawning is the only protection hazard 2 has"; it
  points to *Running agents concurrently*, which states it, and the spine names that section as the
  bound. Acceptable under the brief's shape.
- `check-schema-gates.sh` row: "THIRTEEN" → "all the schema gates". Removes a count that already
  disagreed with `schema-gates.yml`'s "fifteen"; an improvement.
- Stale line-number citations into `dev-process.md` (walkthrough "push back" list): confirmed
  pre-existing, out of scope, correctly disclosed.

## Summary

| Claim part | Result |
|---|---|
| Moved blocks verbatim (bar declared edits) | ✅ HOLDS — measured both directions |
| No pointer dangles | ✅ HOLDS |
| No action rule lost or weakened | ❌ REFUTED — F2, F4, F5 (and F3 falsifies a premise in moved text) |
| Token saving stated correctly | ❌ F1 — must be restated in walkthrough and dashboard entry |
| `check-docs.py` | rc=0; WARN dev-process 214/220 lines |

No BLOCKER under §0 Q4c (no finding gives a false green, data loss or security hole). All five are
local to files this PR already changes and are cheap to fold at round 1.

VERDICT: NOT CONVERGED
