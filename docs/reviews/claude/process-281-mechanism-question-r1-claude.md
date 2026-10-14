# `process-281-mechanism-question` — round 1, Claude half

**Subject:** committed tree `d3324f86`; whole diff `origin/master..d3324f86` — 6 files, 232
insertions, 0 deletions. Commits `46d4c058` (the two process changes) and `d3324f86` (the batch +
dashboard entry).

**Mandate:** adversarial. Everything below is an attempt to refute a claim the branch makes, not to
confirm it. Counts: **1 Blocking, 4 High, 5 Medium, 3 Low.**

**The one finding that matters:** the measured incident the branch cites as its justification does
not say what the branch says it says. The Phase 6 review of 2026-10-13 **did** card a mechanism-level
redesign — it was option **B**, the owner asked why A over B, and B was rejected on a measured width.
So "the mechanism was never put as a decision" is refuted by the document it cites, and the remedy
step 2a prescribes is the thing that already happened. That is B1.

---

## Blocking

### B1 — "The mechanism was never put as a decision" is refuted by the Phase 6 review it cites: the mechanism redesign WAS option B, the owner interrogated it, and it was rejected on a measured width. The prescribed remedy would not have prevented the measured failure.

Both deliverables assert this, as measured fact:

`.agents/skills/improve-codebase-architecture/SKILL.md:64-69`

> **Measured 2026-10-13 — backlog #281, and it cost two review rounds.** A thrashing-armed Phase 6
> review correctly named its root cause in prose […] and then put an **instance-level** A/B choice to
> the owner about one clause of one predicate. **The mechanism was never put as a decision.**

`docs/review-method.md:213-215` (file lines; `:195` is the table row)

> That review named the root cause correctly […] and then put an A/B choice about one clause to the
> owner, **leaving the mechanism as prose.**

**The cited document says otherwise.** `docs/reviews/architecture-review-2026-10-13.md:158-172`
(read in the PR #371 worktree, branch `backlog-249-260-fixes`) is headed *"Deepening candidates — NOT
designed here, per the skill; the owner picks"* and lists **four**, of which the second is a
mechanism-level redesign:

```
2. **A deep module over "the child's verdict"** — `run_suite_parts` + `control_is_green` + `caught`.
   *Problem:* `(rc, stdout, stderr)` is a primitive-obsession seam; four sites each reconstruct what
   a child reported. *Solution:* one module with named states. *Trade-off:* it may not be earned if
   candidate 1 suffices — an agent was asked to argue against it and that answer is pending.
```

And the same document's `### What the owner chose, and what it did NOT include` (`:264-266`) records
that this was carded as **B** and interrogated:

```
Option **A** — make the attribution clause mandatory (#271) — chosen 2026-10-13 after asking why A
over B.
```

with the answer measured rather than asserted (`:272`, `:296-298`):

```
### F1's width — the number that settled A versus B: **2 sites, 2 files**
…
⛔ **So B is not merely unmeasured — it is NOT EARNED.** A shared "child verdict" module over this
class would have **2 callers**…
```

So the sequence actually recorded is: root cause named → a mechanism redesign carded as B → the owner
asked why A over B → B measured at 2 callers → B rejected as not earned → A taken. That is not
"leaving the mechanism as prose"; it is a mechanism option offered, costed and declined.

**Why this is Blocking and not a wording nit.** Step 2a's prescription is *"the first thing you card
is not a candidate list"* but rather *redesign / keep narrowing / accept and record*. Against this
very incident that instruction changes nothing: a redesign option was already on the card, in a
candidate list, with its trade-off stated. The deliverable therefore prescribes a remedy whose own
measured justification shows the remedy was already satisfied — and the failure it is named after
happened anyway. Whatever did go wrong at Phase 6, **this is not it**, and a future agent reading
step 2a is told to guard against a failure mode the cited evidence does not contain.

**What the evidence does support**, and what the honest version of the claim would be: the redesign
that actually resolved the thrashing was neither A nor B. It was *stop claiming the enumeration is
complete* — named at round 11 in `docs/reviews/coordinator/backlog-249-260-r11-thrashing.md:24`
(*"Stop attributing: name every heading, claim none"*), filed at round 13 as #279/#280, and landed by
`ab53945a` *"#279/#280 CLOSED by removing the claims: nothing decides what a line means any more"*.
That redesign was **not among the four candidates**. The defensible finding is *the carded candidates
did not include the redesign the review's own root-cause table implied* — which is a narrower and
genuinely useful lesson, and it is not the one written.

**How I measured it:** read `docs/reviews/architecture-review-2026-10-13.md` and
`docs/reviews/coordinator/backlog-249-260-r11-thrashing.md` in the read-only PR #371 worktree
`…/fdb027d3-…/scratchpad/wt-backlog`; cross-read `git log --oneline -14` on that branch for the
commit that landed the redesign.

⚠ **Stated rather than hidden:** I could not observe the `AskUserQuestion` card itself. I inferred
its A/B content from the review document's own candidate list plus its `What the owner chose` section,
which name A and B explicitly and describe B as a shared module. If the card put to the owner differed
from what that document records, this finding weakens — but then the document is wrong instead, and it
is the source both deliverables cite.

---

## High

### H1 — The card step 2a tells future agents to emit is REFUSED by this repo's own PreToolUse hook. Measured: rc=2, two violations, over a green control.

`.agents/skills/improve-codebase-architecture/SKILL.md:73-76` templates the card:

```
> The root cause is **&lt;the cause, in one sentence&gt;**. Do we
> **A — redesign** (name what the redesign removes), **B — keep narrowing** (name what the next
> narrowing costs, and that the previous N each produced the following round's finding), or
> **C — accept and record** (name what ships)?
```

This repo enforces option-list shape at the point of use —
`.claude/hooks/enforce-selection-card.sh` is a `PreToolUse` hook on `AskUserQuestion`
(`.claude/settings.json:45`) delegating to `scripts/check-selection-card.py`.

**Instrument controls first.** `python3 scripts/check-selection-card.py --self-test` → **59/59
passed, rc=0**. A §19-compliant four-option card I wrote by hand → **rc=0** (silent, as designed). The
instrument works and a known positive passes.

**The subject.** I encoded the template faithfully as an `AskUserQuestion` payload (A/B/C, each with
the parenthetical as its description) and ran the checker:

```
✗ question 1 ('Mechanism'): nothing is marked (Recommended). §19: withholding a recommendation is
  not neutrality, it is handing over an unfinished analysis.
✗ question 1 ('Mechanism'): the last option is 'C — accept and record', not a question-shaped exit.
  §19: add 'D — I have a question about these'. A form with no way to ask turns every clarification
  into a rejected choice.
subject rc=2
```

End-to-end through the hook, wrapped as `{"tool_name":"AskUserQuestion", …}`:

```
╔══════════════════════════════════════════════════════════════════════════╗
║  ⛔ BLOCKED — this selection card does not follow portable-practices §19  ║
╚══════════════════════════════════════════════════════════════════════════╝
HOOK rc=2
```

So a skill instructing a future agent to put this card first is instructing it to emit a card the
repo's own hook blocks. The agent then has to rediscover §19 mid-task, at the moment step 2a says is
the most important card in the review.

**This is the exact failure `check-selection-card.py` was written for**, which is why it is High and
not Medium. That file's own docstring records the measurement:

```
card 1 (which slice to pick)   recommendation ✓   letters ✗   question-exit ✗
card 2 (two decisions)         recommendation ✗   letters ✗   question-exit ✗
card 3 (after two corrections) recommendation ✓   letters ✓   question-exit ✓

The rule was not missing. It was in §19, and restated in two memory files, the whole time — and it
was reconstructed from recall at the moment of use instead of read.
```

A template that omits both missing clauses is a *written* instruction to reproduce cards 1 and 2.
The fix is small: mark one option `(Recommended)` and place it first, and add `D — I have a question
about these`. Step 2a should also cite §19 rather than restate a card shape, which is this repo's
one-rule-one-place rule.

### H2 — "MEASURED … OVER FIVE ROUNDS" contradicts the body beneath it and silently drops the honest bound #281 filed the same day.

`docs/review-method.md:198`:

> ⛔⛔ **AND THE EXHAUSTIVENESS PASS IS ITSELF A TEST — MEASURED 2026-10-13 OVER FIVE ROUNDS, backlog
> #281.**

Four lines later, `:204-211`:

> **What it cost, measured:** PR #371 rounds 11, 12 and 13. One harness message-and-parser produced a
> refuted completeness claim **in each** — [five items listed].

Three problems, in increasing order of seriousness.

1. **The arithmetic does not close.** Three rounds cannot each produce one claim and yield five.
   "in each" is wrong for a list of five over a population of three.

2. **"Five rounds" is a figure the #281 row had already superseded.** The looser count comes from
   `5dacbf59`'s commit body on PR #371 — *"This is the FIFTH consecutive round in which an
   enumeration or a stated bound in this one message-and-parser is refuted"* — i.e. rounds 9–13. But
   the #281 backlog row, filed the same day, corrects exactly that:

   > ⚠ **Honest bound: not round 9.** Round 13's own review established that rounds 9–10 concern
   > withdrawal and parser problems, so the pattern is **WITNESSED from round 11** — which is also
   > when the arming fired.

   I verified the exclusion independently: rounds 7–10 of PR #371 are about the markdown paragraph
   predicate (`BLANK_OR_BLOCK`, `paragraph_ends_between`, cmark divergence — r7 B1, r8 H1, r9 B1, r10
   H1), a different component from the r11–r13 harness message-and-parser (`exception_heading`, the
   three-world chain, `diagnostic_tail`). Measured by reading the `###` finding headings of
   `docs/reviews/claude/backlog-249-260-r{7..13}-claude.md`.

   So the deliverable published the **pre-correction** figure and left the correction behind in the
   backlog row — on a different branch, where a reader of `review-method.md` will never see it.

3. **The bound is the part that travels.** `review-method.md` is a permanent method document; the
   backlog row is not. Moving a measurement into the method document without its bound is how a
   bound stops existing. This repo's own recorded lesson is *a BOUND enumerates what is WITNESSED*.

**The defensible sentence** is *measured over three rounds — 11, 12 and 13 — in which five
completeness claims in one harness message-and-parser were refuted; rounds 9–10 are a different
component and are excluded.* That is both shorter and true.

### H3 — "Every round graded it branch-coverage" is false for round 11, and one witnessed member refutes it — which is the branch's own new rule applied to the branch's own claim.

`docs/review-method.md:208-210`:

> **Every round graded it branch-coverage, fixed the instance, and ran the pass; every pass returned
> another member.**

Round 11's own coordinator document grades the central findings the other way.
`docs/reviews/coordinator/backlog-249-260-r11-thrashing.md:22-27`, verbatim:

```
| finding | kind | can a redesign remove it? | verdict |
|---|---|---|---|
| **r11 Claude H1** — `exception_heading` named the LAST traceback block as the killer; … |
  **MECHANISM** — the rule's premise is untrue, so no amount of case-covering satisfies it |
  **YES.** Stop attributing: name every heading, claim none … | REDESIGN |
| **Phase 6 F1** — `attributed: True` recorded over `fails: []` … |
  **MECHANISM** — two requirements contradict | **YES.** … | REDESIGN |
| **r11 Codex H1** — … | branch-coverage … | NO … | FIX + exhaustiveness |
| **r11 Claude H2** — two of three worlds asserted by no case | branch-coverage … | NO … |
  FIX + exhaustiveness (done: a case and a mutation per world) |
```

Round 11 graded two findings **MECHANISM** and prescribed **REDESIGN** for both, and the same document
names the root cause at `:39` (*"the harness asserts a cause it cannot read from a child's text"*) and
reaches the verdict *"ARCHITECTURE REVIEW is owed, on the MECHANISM findings only"* (`:30`).

So the grading at round 11 was **right**, not wrong. The failure at round 11 was not mis-grading, and
the paragraph attributes the wrong failure to it. This also makes H2's problem concrete: with round 11
excluded from "every round graded it branch-coverage", the population for that sentence is rounds 12
and 13 — two.

⭐ **And this is self-undermining in a specific way.** The new rule two paragraphs above says a
completeness claim refuted by one new member *"was graded wrong"* and that this is a deduction, not a
heuristic. "Every round" is a completeness claim. Round 11 is a member that refutes it. By the
branch's own rule, the claim is wrong rather than approximately right.

### H4 — "That is not a heuristic; it is what the two rows mean" is an invalid deduction, and this repository already records the distinction it erases.

`docs/review-method.md:198-202`:

> **If that pass comes back with a NEW MEMBER, the finding was MECHANISM and was graded wrong.** That
> is not a heuristic; it is what the two rows mean. A shape that is merely under-specified has a
> FINITE set of unsaid cases, so the pass terminates. A shape that is wrong generates them, so the
> pass does not.

The deduction conflates *the pass terminates* (a property of the limit) with *the first pass returns
nothing new* (a property of one step). A finite set of size N > 1 yields a new member on the first
pass **and** terminates. Nothing in the premises rules that out, so the conclusion does not follow,
and it is asserted as a deduction — one counter-example is enough.

**Counter-example 1, in this repository, with the distinction already written down.**
`scripts/check-main-drivable.py:186`:

```
# removal WAS available there: `ast` enumerates the grammar, so `_expr_children` descends through
```

That comment is the whole point: `_expr_children`'s member list is **finite and externally
enumerable** (the `ast` grammar), so a sloppy first enumeration can miss a node type, an
exhaustiveness pass returns that node type, the pass then terminates, and the shape was fine — a
textbook branch-coverage defect. Backlog #224 states the contrast explicitly: *"`_expr_children`
could delete ITS list because `ast` enumerates the grammar; **nothing enumerates stdlib expressions
that read ambient process state**"*. The new rule would grade the first of those MECHANISM and demand
a redesign.

**Counter-example 2, measured just now.** `python3 scripts/check-rc-contract.py` →

```
rc contract: 6 code(s) defined, 4 handled by an arm, 2 declared unhandled
```

The population is six rc codes, derived from the source. A rule that handled five of six would yield
one new member on an exhaustiveness pass and then terminate. Shape fine; rule under-specified.

**The property that actually discriminates** is not *finite* but *externally enumerable* — can the
member set be derived from something outside the rule (a grammar, a catalog, an enum), or does the
rule's own prose define it? The repo has that distinction and the new sentence replaces it with a
weaker one. That is the fix: say *if the pass returns a new member AND the member set is not
externally enumerable, the finding was MECHANISM.*

**Two cases the rule does not answer at all**, both of which this repo's standards require it to:

- **An out-of-scope member.** The pass returns something the rule does not govern. Under the text as
  written that is still "a NEW MEMBER" and forces a MECHANISM re-grade. No clause excludes it.
- **The pass cannot be run.** `docs/dev-process.md`'s standard is that *"cannot run" is a FAILURE,
  never a pass*. The rule is silent, so a pass that could not be run reads as a pass that returned
  nothing, which is the benign direction — fails toward good news.

---

## Medium

### M1 — "NOTHING ENFORCES EITHER OF THESE … No guard reads the skill" is false. A CI guard reads this SKILL.md's full text, and a second guard reads the branch's changed paths and demands a round.

Commit `46d4c058`:

> ⚠ STATED RATHER THAN HIDDEN — NOTHING ENFORCES EITHER OF THESE. **No guard reads the skill**, and
> #281's own `FAILS IF` is lagging by construction…

and `docs/dashboard-entries.md`:

> Neither change is enforced by anything, which is worth saying plainly. **No automated check reads
> the review instructions**…

Two guards contradict the literal claim.

1. `scripts/check-explainer-delivery.py:83-84` reads **every** skill's body:

   ```python
   # Restatement can appear in ANY skill, not only the three.
   for f in sorted(skills_dir.glob("*/SKILL.md")):
       text = f.read_text()
   ```

   It then checks each fenced block for a delivery command and for `Monitor({`. This runs in CI —
   `.github/workflows/ci.yml:299`, `python3 scripts/check-explainer-delivery.py` — and I ran it
   against the branch tree: `rc=0`, *"explainer delivery: 1 shared description, 5 skills cite it, 0
   restatements"*. So `improve-codebase-architecture/SKILL.md` is **inside a CI guard's population**.
   Step 2a's new content is prose and passes, but the file is read, and a later edit adding a fenced
   block to 2a would fire it.

2. `scripts/check-review-decision.py` reads the branch's changed paths and refuses the branch. Run
   against the branch tree:

   ```
   ROUND_OWED — no round recorded; a full-loop change needs at least one
     branch=process-281-mechanism-question  scope=full-loop  rounds=0  tree_reviewed=False
   ```

   And `scripts/check-docs.py:285-318` reads `.agents/skills/` against `.claude/skills/` for symlink
   reachability — so the skill's *path* is guarded too.

The honest statement is narrower and still worth making: *no guard reads the CONTENT of either rule,
so neither can be falsified mechanically; the review obligation for changing them is enforced
(`check-review-decision.py`), and the files are inside two guards' populations for unrelated rules.*

Why Medium rather than Low: this repo's own recorded lesson is *a caveat headed "stated rather than
hidden" that is wrong is worse than none*, because a reader stops looking. Here the caveat is the
place a reader would go to learn what guards exist, and it says none do.

### M2 — "#281's `FAILS IF` is lagging by construction" — a leading falsifier is constructible, and the claim that it is not was not tested.

Commit `46d4c058` and the dashboard entry both assert the lagging shape is forced:

> #281's own `FAILS IF` is lagging by construction: *a Phase 6 review names a root cause and the next
> round's findings share that cause, with no decision card having been put* is only observable after
> the next round.

The lagging *form* of #281's `FAILS IF` is indeed lagging. But "by construction" is a claim that no
leading form exists, and a leading form is available at the moment the review document is written:

> **FAILS IF** a review document in `docs/reviews/` that records a THRASHING arming contains no
> decision card offering a redesign option.

That is observable the instant the review is committed — no next round required. It is also
mechanically checkable, and the instrument class already exists in this repo:
`scripts/check-review-decision.py` and `scripts/check-gate-falsifiability.py` both read review and
gate documents today, and `check-gate-falsifiability.py` is green on this tree (*"every unticked gate
item names what would fail it"*).

The repo's standard is that a gate must name the observation that makes it FAIL, and that a decision
wearing a checkbox should be renamed rather than ticked. Declaring a leading falsifier impossible,
when one is constructible with a guard pattern already in use, is the finding — the branch may well
decide not to build it, but *not attempted* and *impossible by construction* are different claims and
only the first is true.

### M3 — The two `MEMORY.md` rows push ten more memory-file names off the delivered end of the index. Measured from this session's own context.

`docs/memory/MEMORY.md` is the file the harness loads: same inode as the live path.

```
158338009 links=1 /Users/kujinlee/.claude/projects/-Users-…-cloud/memory/MEMORY.md
158338009 links=1 /Users/kujinlee/code/…/docs/memory/MEMORY.md
```

Sizes:

```
origin/master     25884 bytes
d3324f86          26440 bytes   (+556)
  added row  350 bytes  - [⭐⭐ Verify the OTHER copy exists before deleting](…)
  added row  206 bytes  - [⭐⭐ Printing MORE evidence weakens substring cases](…)
```

**The truncation is real, and I can witness its cut point rather than assume it.** The live file is
26,498 bytes and ends at line 167; the copy delivered into this session's context stops after the
`[Blob addressing]` line (line 160), and the loader appended *"MEMORY.md is 25.1KB (limit: 24.4KB) …
Only part of it was loaded."* Computing the prefix that ends at that line:

```
live file bytes            : 26498
delivered prefix bytes     : 25728 (25.1 KiB)   <-- matches the warning's "25.1KB" exactly
DROPPED bytes              : 770
DROPPED lines              : 7
memory files named only in the dropped tail: 15
```

So delivery is a byte-bounded **tail** truncation, and the budget is witnessed at 25,728 bytes.
Applying that same budget to both versions of the committed file:

```
origin/master    delivered 164 lines   DROPPED  2 lines /  5 memory-file names
d3324f86         delivered 161 lines   DROPPED  7 lines / 15 memory-file names
```

The branch's 556 bytes sit near the top of the index, so they displace 556 bytes of tail. **Five
memory-file names become ten more**: the lines pushed off name `worker-vs-sync-fencing-gap`,
`serial-coherence-slice-state`, `reservation-release-slice-state`,
`summary-section-timestamp-guarantee-state`, `cloud-dig-deeper-frontend-state`,
`cloud-dig-serving-branch-state`, `playlist-sidebar-ux-branch-state`, `cloud-summary-pdf-slice-state`,
`frontend-subproject-design-state` and `stage-2-batch-autonomy-plan`.

Net effect on discoverability: **+2 rows visible, −10 rows invisible.** The index exists so a memory
can be found; adding to it past the delivery budget removes more findability than it adds. The two
rescued memory *files* are unaffected and worth committing — this finding is only about the two index
rows, and the available repairs are to shorten existing rows by ≥556 bytes in the same commit (the
file's own header asks for ~200 chars per row and both new rows are over), or to land the files now
and the rows with a shortening pass.

⚠ **Bound, stated rather than hidden:** 25,728 bytes is one observation, from this session. The
allocator may vary with other context, so the exact boundary rows could differ. The direction cannot:
the truncation is at the tail and the additions are above it.

### M4 — `(projectSettings:)` names a frontmatter key that does not exist in the file or anywhere in the repo. The substantive claim holds; its cited evidence does not.

Commit `46d4c058`:

> ⭐ Unlike the handoff skill, this one is PROJECT-LOCAL (`projectSettings:`), not vendored, so a
> plugin update will not revert it

The file's complete frontmatter is two keys:

```yaml
---
name: improve-codebase-architecture
description: Find deepening opportunities in a codebase, informed by the domain language in CONTEXT.md and the decisions in docs/adr/. Use when the user wants to improve architecture, …
---
```

`grep -rn 'projectSettings' --include='*.md' --include='*.json' --include='*.sh' --include='*.py'
--include='*.yml' .` (node_modules excluded) returns **zero hits**. Instrument control: the same
invocation for `improve-codebase-architecture` returns 7 hits across `.agents/`, `docs/dev-process.md`,
`docs/available-skills.md` and `docs/backlog.md`, so the search works.

**The conclusion is true**: the skill is tracked in this repo (41 files under `.agents/skills/` in
`git ls-files`), I found no plugin-installed copy (`find /Users/kujinlee/.claude -type d -name
improve-codebase-architecture` → nothing; no plugin `SKILL.md` mentions it), and my own session lists
the skill with no plugin prefix. So a plugin update would not revert it. Only the parenthetical
evidence is invented — a backtick-quoted token presented as readable from the file.

This is the repo's own *"an inference stated as MEASURED"* class, and the cost here is specific: a
future reader checking the claim opens the frontmatter, finds no such key, and has no way to tell
whether the conclusion survives. The fix is to drop the parenthetical or replace it with the evidence
that does exist — *tracked in this repo under `.agents/skills/`, with no plugin copy installed*.

### M5 — Step 2a's precondition cannot be determined from the skill: it never defines THRASHING and never says where the arming condition lives.

`SKILL.md:62` — *"**2a.** If this review was ARMED BY THRASHING…"* — and `:71` — *"So when the arming
condition was THRASHING…"*. `grep -rn -i 'thrash|arming|armed'` over the whole skill directory returns
only the four lines inside step 2a itself. Nothing in the skill defines the condition, states who
armed the review, or points at where the definition lives.

The definition is in `docs/dev-process.md` (*"on THRASHING: two consecutive rounds whose findings came
from the previous round's fix"*) and elaborated in `docs/review-method.md`. Step 2a's only outbound
link (`:83-84`) goes to `review-method.md` for a different thing — the exhaustiveness tell.

Consequence: an agent that enters this skill through its normal trigger (the description is *"Use when
the user wants to improve architecture, find refactoring opportunities…"* — no mention of rounds or
arming) arrives at step 2a unable to evaluate the `if`. The safe default is to skip it, which makes
the step inert exactly when it is needed. One sentence fixes it — *"armed by thrashing" is defined in
`docs/dev-process.md`'s Phase 6 row; if you were not told which arming convened this review, ask.*

---

## Low

### L1 — "`.claude/skills/` is a SYMLINK to `.agents/skills/`" is not what is on disk. The conclusion survives; the stated check does not.

Commit `46d4c058`: *"⚠ The edit targets `.agents/skills/…` because `.claude/skills/` is a SYMLINK to
it — one file, two paths."* The dashboard entry repeats it: *"⚠ edited via `.claude/skills/…`, which
is a symlink to `.agents/…`"*.

Measured:

```
$ readlink .claude/skills            # empty — not a symlink
$ ls -ld .claude/skills
drwxr-xr-x@ 23 kujinlee staff 736 Oct 13 16:16 .claude/skills
```

`.claude/skills` is a **real directory holding 21 per-skill symlinks**:

```
lrwxr-xr-x@ 1 … improve-codebase-architecture -> ../../.agents/skills/improve-codebase-architecture
```

`git ls-files -s` confirms: 21 entries at mode `120000` under `.claude/skills/`, against 41 regular
files under `.agents/skills/` — so the two trees are not even the same population.

The conclusion is right for the edited file — `stat -f '%i links=%l'` gives inode `179304860` for
both paths, one file — and the edit landed on `.agents/…`, the real file. So this is Low.

It is worth correcting anyway because of what the branch pairs it with: the memory file this same
commit rescues says *"⛔ `readlink` the parents. Do not reason about it."* Here `readlink` on the path
as described returns empty, and only `readlink` on the *child* shows the link. A reader applying the
rescued note's own check to the claim as written would conclude there is no symlink.

### L2 — The fusion warning is well placed but has no mechanical half, and `check-dashboard-entry.py` green is specifically not evidence against fusion.

The header count re-derives correctly: `grep -c '^## '` is **306** on `origin/master` and **307** on
`d3324f86`. And `python3 scripts/check-dashboard-entry.py` → `rc=0`, *"ok — an entry block was
added"*.

The warning is at the end of the new section inside `docs/dashboard-entries.md` itself, which is the
right file — a keep-both conflict resolver working that hunk will have it on screen. That is better
placement than a PR body (there is no PR).

What is missing is any mechanical half. `check-dashboard-entry.py` asks whether an entry was *added*;
it does not count `^## ` and cannot see two same-day sections fused under one header. So its green is
compatible with the fusion. This is the third occurrence of a hazard `docs/memory/MEMORY.md`'s own
index records as paid for twice (*"⛔ keep-both FUSES two entries when headers match (hit AGAIN
2026-10-07) — `grep -c '^## '` must RISE"*), and the branch correctly warns while adding nothing that
would catch it. Low because the warning is where it needs to be and the obligation is stated; the
observation is that a twice-paid hazard is still carried by prose.

### L3 — The template's placeholder is HTML-escaped in a file agents read as raw text, and 2a restates a card shape that lives in §19.

`SKILL.md:73`: `> The root cause is **&lt;the cause, in one sentence&gt;**. Do we`

An agent reads SKILL.md as raw markdown, so it reads the literal characters `&lt;` and `&gt;`. Line 73
is the only line in the file carrying those entities (`grep -n 'lt;\|gt;'` → one hit). The surrounding
blockquote is never HTML-rendered for its actual consumer. Use `<the cause, in one sentence>` or
backticks.

Related and the same size: step 2a restates an option-list shape that `docs/portable-practices.md` §19
owns, which is how the two copies in H1 came to disagree. The repo's rule is one rule, one place —
cite §19.

Also checked and clean: the relative link `[review-method.md](../../../docs/review-method.md)`
resolves from **both** paths (`.agents/skills/improve-codebase-architecture/` and
`.claude/skills/improve-codebase-architecture/`), verified with `test -f`.

---

## Checked and found SOUND

- **Byte-identity of the three batched files** (claim 12). `git show
  rescue-two-uncommitted-memories:<path>` vs `git show d3324f86:<path>`, `shasum` on each — **3 of 3
  identical**, index rows included:
  `verify-the-other-copy-exists-before-deleting.md` `6adddeb5…`, `printing-more-evidence-weakens-substring-cases.md` `df885397…`, `MEMORY.md` `afe20e0a…`.
  The conclusion that `rescue-two-uncommitted-memories` must not be opened as its own PR is therefore
  safe on the evidence given.
- **Dashboard header count 306 → 307** (claim 11). Re-derived above.
- **`review-method.md` is not line-budgeted.** `scripts/check-docs.py:191-194`: `LINE_BUDGETS` holds
  exactly `docs/dev-process.md: 220` and `docs/plugins.md: 260`. `review-method.md` is 742 lines and
  unbudgeted. `check-docs.py` → rc=0.
- **`dev-process.md` is at 219/220** — `wc -l` confirms 219, so the "one line of runway" statement and
  the decision to leave the Phase 6 row alone are accurate.
- **The 2a insertion breaks no cross-reference** (claim 9, second half). Heading sequence is
  `### 1. Explore` (:33), `### 2. Present candidates` (:47), `### ⛔ 2a.` (:62), `### 3. Grilling
  loop` (:89) — well-formed. The only "Step 2"/"Step 1" references in the skill directory are
  `INTERFACE-DESIGN.md:17` and `:23`, which number that file's own steps, not SKILL.md's. Nothing
  refers to SKILL.md's step 3 by number.
- **"Project-local, not vendored"** (claim 8, substance). 41 tracked files under `.agents/skills/`; no
  plugin copy found; the skill lists without a plugin prefix. Only the `projectSettings:` citation
  fails — M4.
- **"The redesign was available at round 11"** (claim 3). Supported.
  `docs/reviews/coordinator/backlog-249-260-r11-thrashing.md:24` names the redesign that was
  eventually taken (*"Stop attributing: name every heading, claim none"*) and `:39` names the root
  cause, both at round 11. The redesign landed at `ab53945a`, 16:14 on the same day.
  ⚠ But the words used for it in `review-method.md:209-210` — *"delete the validator"* — name an
  artifact that did not exist as a subject at round 11; the validator enters at rounds 12–13. The
  *shape* was available at 11; that specific sentence was not.
- **"Each of those rounds took a couple of hours"** (claim 13). Derived from commit timestamps on
  `backlog-249-260-fixes`: round 12 spans `100d1f1a` 11:29 → `d56a00ae` 13:56 ≈ **2h27m**; round 13
  spans 13:56 → `cb1de6d9` 15:11 ≈ **1h15m**; Phase 6 (`940fb21c` 10:56) to the redesign landing
  (`ab53945a` 16:14) ≈ **5h18m**. "A couple of hours" is right for round 12 and the upper end for
  round 13. Defensible as written.
- **Document guard suite.** Extracted every `python3 scripts/check-*.py …` invocation from
  `.github/workflows/ci.yml` (52 invocations) and ran all of them against the branch tree: **49
  green**. The three non-green are instrument or in-flight states, not branch defects — see CANNOT
  RUN.

---

## CANNOT RUN — failures, not passes

⛔ **Treat each of these as NOT RUN.**

1. **The mutation harness was not run on this branch.** `python3 scripts/check-plan-code.py` (bare)
   exits **rc=2** by design — *"CANNOT RUN — nothing to do. The modes are `--mutate ROOT` … Plan mode
   was RETIRED on 2026-09-08"*. CI runs `--mutate .`; I did **not** run it. The branch touches no
   guard source, so I judged the cost unjustified for round 1 — but that is a judgement, not a
   measurement, and the mutation evidence for this tree does not exist. `--self-test` alone is green
   (178/178).
2. **`check-test-counts.py --results jest-results.json` → rc=1**: no `jest-results.json` in the
   worktree. The roadmap-vs-suite count comparison was **not measured**. `--self-test` green.
3. **`check-review-recorded.py` → rc=1** on both runs: no review recorded for this branch and no
   `NO-REVIEW:` reason. Expected for an unreviewed branch and it is what this document starts to fix;
   it measures the review ledger, not the deliverable.
4. **`check-review-rounds.py` gave two different answers 40 minutes apart** — `rc=0` in my first
   (backgrounded) sweep, then `rc=1`: *"process-281-mechanism-question round 1: only codex — claude
   neither ran nor recorded a `REVIEW GAP:` line"*. The Codex half's verdict landed between the two
   runs. Neither reading is a branch defect; both are states of an in-flight round, and it should go
   green once this file is committed. Recorded because a reader seeing only the first run would draw
   the wrong conclusion.
5. **I could not observe the Phase 6 `AskUserQuestion` card itself** (B1). Its A/B content is inferred
   from `architecture-review-2026-10-13.md`'s own candidate list and `What the owner chose` section.
   If the real card differed, B1 weakens — see the caveat under B1.
6. **The MEMORY.md delivery budget is one observation** (M3), witnessed from this session's context at
   25,728 bytes. I did not find or read the loader's allocator, so the exact boundary rows may shift;
   the direction (tail truncation, additions above it) is measured.
7. **`check-memory-link.py` emits a WARNING in the worktree** — *"the harness memory path does not
   exist, so the assistant reads NO corpus here"* — and still exits 0, as designed for a fresh clone.
   The link exists for the main checkout, which is how M3 was measured; the worktree is not the
   subject of that guard's claim.

---

## Instruments

Everything below was run inside the worktree
`…/cc324e78-…/scratchpad/wt-281` at `HEAD = d3324f86`. **No `git` command was run in the main
checkout.** The read-only cross-reads of PR #371 used `…/fdb027d3-…/scratchpad/wt-backlog` (branch
`backlog-249-260-fixes`) with `git log`/`git show`/`sed` only — nothing written, nothing modified.

| what | how | result |
|---|---|---|
| selection-card control | `python3 scripts/check-selection-card.py --self-test` | 59/59, rc=0 |
| selection-card known positive | a hand-written §19-compliant 4-option card on stdin | rc=0, silent |
| **H1 subject** | the step 2a template as an `AskUserQuestion` payload on stdin | **rc=2, 2 violations** |
| **H1 end-to-end** | same payload with `tool_name`, through `.claude/hooks/enforce-selection-card.sh` | **rc=2, BLOCKED panel** |
| CI document suite | every `python3 scripts/check-*.py …` in `ci.yml` (52 invocations), 300s cap each | 49 green, 3 not-run |
| symlink shape | `readlink`, `ls -l`, `git ls-files -s`, `stat -f '%i links=%l %N'` | real dir + 21 child symlinks; edited file one inode |
| `projectSettings` | `grep -rn` over `*.md *.json *.sh *.py *.yml`, with a known-positive control | 0 hits / 7 control hits |
| MEMORY.md sizes | `git show <ref>:docs/memory/MEMORY.md | wc -c` | 25884 → 26440 (+556) |
| MEMORY.md delivery | prefix of the live file ending at this session's witnessed cut line | 25,728 B delivered, 770 B / 15 names dropped |
| MEMORY.md displacement | same budget applied to both committed versions | 5 → 15 dropped names |
| dashboard count | `git show <ref>:docs/dashboard-entries.md | grep -c '^## '` | 306 → 307 |
| byte identity | `git show rescue-two-uncommitted-memories:<p>` vs `d3324f86:<p>`, `shasum` | 3/3 identical |
| blast-radius class | `check-review-recorded.is_prose` imported and called per changed path | 5 prose, SKILL.md **not** prose |
| review scope | `python3 scripts/check-review-decision.py` | `scope=full-loop rounds=0 ROUND_OWED` |
| round timings | `git log -1 --format=%ci` on r11–r14 commits | r12 ≈ 2h27m, r13 ≈ 1h15m |
| round attribution | `###` headings of `backlog-249-260-r{7..13}-claude.md` | r7–r10 a different component |
| line budgets | `scripts/check-docs.py:191-194` + `wc -l` | only dev-process (219/220) and plugins |

⚠ **Harness note, per the method rules:** my first sweep was backgrounded and buffered, so its output
file was 0 bytes for its whole run. That is the wrapper buffering, not 52 hung guards — I re-ran the
document guards in incremental batches to confirm each result independently before reporting any of
them.

**Worktree left clean.** I modified no file in the worktree; the only writes were this review and
JSON payloads under the session scratchpad. `git status --porcelain` shows this review file as the
sole addition.

---

## Verdict

**NOT CONVERGED.** 1 Blocking, 4 High, 5 Medium, 3 Low.

The branch's instinct is right and its two changes are cheap and well placed. What round 1 found is
that the *measurements* supporting them do not hold: the Blocking is that the incident cited as the
reason for step 2a records a mechanism redesign being carded, interrogated and declined, which is the
opposite of the failure the step guards against. H1 is the sharpest cheap fix — the card this skill
tells agents to emit is refused by this repo's own hook, measured end-to-end. H2/H3/H4 are all the
same shape as each other and as the rule the branch is adding: a completeness claim published without
the bound that was already known.

⭐ Worth stating plainly, because it is the cleanest evidence for the branch's own thesis: three of my
four High findings are completeness claims refuted by a single witnessed member, found in the document
that introduces the rule *"if the pass returns a new member, the claim was graded wrong"*. The rule is
useful. It was not applied to the paragraph that states it.
