# Code review r2 — `backlog-99-paused-tick` (7d1b8c16) — CLAUDE half

SCOPED to the r1 fold: `git diff 673b4a8b..HEAD`, one commit, 11 files. The r1 base is not
re-reviewed. Method: executed, not read — both suites, all 20 manifest mutations applied to temp
copies with their red-case sets recorded, four hand-built probe mutations for branches the manifest
does not reach, and the shipped scripts driven against throwaway repo roots.

**Verdict: NOT CONVERGED.** 0 Blocking · 1 High · 2 Medium · 8 Low.

---

## What the fold got right (measured, so it is not re-litigated)

**Suites and gates, all green.** `check-plan-progress.py --self-test` **35/35**;
`begin-plan.py --self-test` **47/47**; `check-plan-code.py --self-test` 189/189;
`check-selftest-counts.py` verifies both declared counts by running them;
`check-ratchet-contract.py` at baseline 21; `check-docs.py` OK.

**Cx-M2's written justification is TRUE.** The claim at `check-plan-progress.py:154-169` is that
`paused:` overrides cannot-run *on that path only*, and the non-paused arm still blocks. Driven,
all four arms:

| sentinel | plan | exit | wanted |
|---|---|---|---|
| unpaused | missing | **2** | BLOCK ✅ |
| unpaused | zero checkboxes | **2** | BLOCK ✅ |
| paused | missing | **3** | WARN ✅ |
| paused | zero checkboxes | **3** | WARN ✅ |

The sentence *"Before this branch these paths were allowed SILENTLY"* is also true — on
`origin/master` the paused short-circuit returned `ALLOW, "", None` before either check.

**The H1 disposition (preserve, not clear) holds up, including the questions you asked.** Driven on
a paused, fully-ticked plan with a stale `STATE` of 3:

- three consecutive stops → exit **3** each time, sentinel present, `STATE` unchanged at 3. It nags
  forever and **never blocks** — `block-idle-stop.sh:99` allow-lists 3, so the hook exits 1. There
  is no wedge.
- the anti-nag does not interact: the preserve branch (`:203`) returns before `:249`, with
  `unticked=None`, so `run_decide` writes no `STATE` and unlinks nothing.
- **`--finish` is reachable and works from that state** — `cmd_finish` unlinks unconditionally
  (`begin-plan.py:434-438`); driven, it cleared both sentinel and state and exited 0. The WARN
  message names both escapes at `:212-213`.
- `--resume` then a stop → ALLOW, `unticked == 0`, sentinel cleared. The parked state has two
  exits, both named in the message that announces it.

I recommended the other option in r1 and I think you chose correctly: preserve is the reading that
survives #94's *blocked on in-flight work*, and the r1 escalation clause was the right thing to act
on. **The disposition is not among my findings.**

**L7 is fully closed.** `_armed_plan` now returns a 3-tuple (`begin-plan.py:258`); both call sites
unpack three (`:345`, `:386`) and `grep` finds no two-element unpack of it. (The `armed["plan"]`
uses at `:583`, `:586`, `:594` are a different, dict-valued `armed` in the self-test.)

**L4 and L8 are closed.** The narrowed justification at `:224-226` now names the
`stop_hook_active` conjunct it omitted. `paused = fields.get("paused")` (`:155`) is exactly
equivalent to the conditional it replaced.

**L3's renamed case genuinely reaches its branch.** Measured: `"no command in the
pause->refuse->resume sequence has written the plan"` reddens under both `cmd_tick` write
mutations, which is what its new name claims.

**All 20 manifest mutations are caught via the case they name.** `begin-plan.json` 9/9,
`check-plan-progress.json` 11/11. The two retargeted anchors (`if "paused" in fields:\n` and
`paused = fields.get("paused")\n`) both apply exactly once.

**`strip_field` still round-trips everything `--pause` can now write, within the guard's scope.**
30,000 randomly generated single-line `why` values over `ab: \t#-`*paused:plan:é'` — every one
produced a 3-line sentinel, left `plan:` intact, and round-tripped to byte-identical on
`strip_field(…, "paused")`. **0 failures.** Leading/trailing whitespace is handled by `why.strip()`;
a `key: value`-shaped `why` is safe because `parse_sentinel` splits on the **first** colon, so
`paused: plan: other.md` has key `paused`; a `why` containing `paused:` is likewise inert.

---

## H1 — High: the M3 fix is one character class too narrow. `--pause` still injects a live sentinel field, via U+2028 and seven other separators

`begin-plan.py:412` refuses on `"\n" in why or "\r" in why`. But **both** parsers of this file —
`parse_sentinel` (`check-plan-progress.py:82`) and `strip_field` (`:103`) — use `str.splitlines()`,
which breaks on **eight** characters the guard does not check:

```
VT \x0b · FF \x0c · FS \x1c · GS \x1d · RS \x1e · NEL \x85 · LS   · PS  
```

Measured for each: `refused_by_guard=False`, `len(splitlines())==2`. The guard is exactly
`\n`-and-`\r` wide; the parser is eight characters wider.

**Driven end to end, on the shipped code, with U+2028 in place of the newline r1 used:**

```
$ begin-plan.py --pause $'waiting on review plan: .claude/plans/other.md'
paused: waiting on review<U+2028>plan: .claude/plans/other.md
⚠ WHEN THE WORK RESUMES, run `scripts/begin-plan.py --resume` FIRST. …        [exit 0]

parse_sentinel(sentinel) ->
  {'plan': '.claude/plans/other.md', 'armed': 'x', 'paused': 'waiting on review'}
                ↑ last-wins; the injected line is now THE live plan pointer

$ begin-plan.py --resume
resumed: the Stop guard is armed again and will refuse a stop with steps outstanding.  [exit 0]

$ check-plan-progress.py --status
.claude/plans/other.md: 0/1 steps ticked, 1 remaining      ← supervising a DIFFERENT plan
```

That is byte-for-byte the r1 M3 outcome, reached through a character the fix does not consider.
`strip_field` behaves correctly and cannot help: it removes only the line that **is** the field
(measured — the residue `plan: .claude/plans/other.md\n` survives), which is precisely the design
the fold's own comment at `begin-plan.py:402-411` says `cmd_pause` exists to make safe.

**The coverage is exactly as narrow as the fix, and I measured that too.** The new case at `:641`
and its mutation `"--pause accepts a multi-line reason again"` both exercise `\n` only. I built the
probe the manifest is missing — delete the `or "\r" in why` half — and ran the suite:

```
pause guard checks only \n, not \r   ->  rc=0   RED CASES: 0
```

**Half the guard's stated rule is unguarded by anything**, and no case in either suite mentions any
separator beyond `\n`. This is the recorded *instance-not-class* shape: the fix closes the one
input r1 happened to demonstrate.

**Fix, and it is smaller than the current one:** refuse when the `why` does not survive its own
parser — `if len(why.splitlines()) > 1 or why != why.strip()`, or simply
`if why.splitlines()[:1] != [why]`. Deriving the predicate from `splitlines()` makes it impossible
for the guard and the parser to disagree again, which is the same *one owner for one rule*
principle `strip_field` is built on. Then extend the mutation to a non-`\n` separator, so the case
cannot pass while covering one character.

---

## M1 — Medium: the citation cleanup is instance-not-class, and its count is wrong in two committed documents

The fold declares a policy in the file it cleans (`block-idle-stop.sh:86-92`): *"A cross-file line
number is a citation with a countdown on it."* Measured against the diff and the tree:

**Removed: seven, not ten.** `git diff … | grep '^-'` over the two files yields `:105`, `:109`,
`:113`, `:130`, `:183` (5, in `block-idle-stop.sh`) plus `check-banner-armed.py:499` twice (2, in
`check-plan-progress.py`). Both `docs/dashboard-entries.md` and the `docs/backlog.md` row 99 say
**"ten stale cross-file line citations"**. The "five of them broken by this very commit" half is
correct.

**Four wrong cross-file line citations survive, in the same two files:**

| location | claim | actual | status |
|---|---|---|---|
| `block-idle-stop.sh:11` | `check-banner-armed.py (:48)` | invoked at `:65` | wrong |
| `block-idle-stop.sh:11` | `check-plan-progress.py (:56)` | invoked at `:105` | wrong |
| `block-idle-stop.sh:12` | `check-ci-watched.py (:67)` | invoked at `:118` | wrong |
| `block-idle-stop.sh:124` | `check-banner-armed.py:70` = "their CANNOT-RUN code" | `:70` is prose about #96 | wrong (pre-existing on `origin/master` too) |

The first three are the ones I flagged in r1 as *"already wrong before this branch … but it is now
wronger"*, and this commit moved them a further three lines. They now sit **74 lines above** the
paragraph declaring that line numbers expire. The two that remain correct are
`check-ci-watched.py:43` (`:125`) and `check-banner-armed.py:924` (`check-plan-progress.py:358`) —
both verified by `sed`.

Either finish the sweep or say in the comment that the header's three are knowingly left; what is
not defensible is a policy paragraph with four counter-examples in the same file and a count in two
documents that does not match the diff.

## M2 — Medium: the new preserve WARN's `--finish` guidance has no mutation — the r1 L1 defect, reproduced in the code written to fix it

r1 L1 measured that the outstanding-WARN's `--resume` guidance reddened only under a 7-case
blunderbuss. The fold closed that correctly: the new entry *"the paused WARN stops naming
--resume"* reddens **exactly one** case. Good.

But the preserve WARN written in the same commit ends with the only two exits a parked plan has
(`check-plan-progress.py:212-213`), and `--finish` is the one that is otherwise undiscoverable —
`--resume` is named in four other places, `--finish` in none of them. I built the missing probe:

```
WARN drops the --finish guidance in the preserve message
   rc=1  RED CASES (1): ['...and it names --finish, the explicit way to clear a parked plan']
```

An isolating mutation exists, reddens exactly the case that names it, and is not in the manifest.
One entry closes it. The shape is worth naming because it is the fold's own r1 finding recurring
inside the fold: the class was *a guard's message that names the only escape is unguarded*, and the
fix addressed the instance.

---

## Low

**L1 — the new "isolating" mutation does not isolate, and the L3 rename makes isolation
impossible.** Measured for *"the refusal path writes to the plan before returning REFUSED"*:

```
RED CASES (2): ['the refused tick leaves the plan BYTE-IDENTICAL on disk',
                'no command in the pause->refuse->resume sequence has written the plan']
```

It narrows the co-red set from 3 to 2 but is not isolating. It cannot be: the L3 rename made the
second case a **superset assertion by construction** — "no command in the sequence has written the
plan" is red whenever any write happens anywhere in that sequence — so no mutation can ever make
`byte-identical` the sole red while both cases exist. r1 L2 is therefore narrowed, not closed, and
the fold's own L3 fix is what closes the route. Not a defect in the code; a correction to the
coverage claim.

**L2 — two newly borrowed cross-file symbols are outside the loader's asserted-names list.** The
fold's new begin-plan cases use `pp.decide` (`:650`) and `pp.WARN` (`:654`), but
`_load_plan_progress`'s list is still `("count_steps", "next_pending_task", "parse_sentinel",
"strip_field")` (`:106`). That list exists precisely so a rename in the owning file *"fails LOUDLY
here"* (`:93-100`). Measured, renaming each in a temp copy:

```
rename WARN   -> begin-plan suite rc=1, AttributeError: module '_plan_progress' has no attribute 'WARN'
rename decide -> begin-plan suite rc=1, AttributeError: module '_plan_progress' has no attribute 'decide'
```

Still loud — not fail-open — but it is a bare `AttributeError` mid-suite instead of the explanatory
ImportError the loader was built to raise. Two strings.

**L3 — `cmd_tick()` at `begin-plan.py:648` is a no-op, and its comment says otherwise.** The
comment reads `# 2 of 2 -> fully ticked`, but the preceding case at `:636` already ticked to 2/2.
Measured by counting the suite's own output: `"nothing to tick — every step … is already done."`
appears **once**, and `"ticked step"` appears exactly twice (steps 1 and 2), both before this line.
The three H1 cases that follow get the right state only as a side effect of an earlier case. You
already found one mutation surviving via a re-ticked box; this is the same line, still a no-op, with
a comment asserting an action that does not happen.

**L4 — the control case has no manifest mutation.** *"an UNPAUSED fully-ticked plan still clears —
the pause is what changes it"* (`:407-408`) is the right control and it is load-bearing: dropping
the `paused is not None` conjunct from `:203` reddens it (measured, RED = that case plus the
pre-existing *"all steps ticked -> allow and clear"*). Because a sibling also reddens, severity is
Low — but the "fix went too far" direction is the one direction the manifest does not probe.

**L5 — `_print_state` promises a clear the preserve branch will not honour.** `begin-plan.py:291`
prints *"✅ every step in … is ticked. The Stop guard will allow the turn to end and clear
.claude/executing-plan."* It is true when printed (`--tick` refuses on a paused plan), but it is the
message the actor sees immediately before the `--pause "waiting on CI"` that creates the parked
state — which is exactly the H1 entry sequence. After that pause, the sentinel is deliberately not
cleared.

**L6 — the `--tick` refusal points at the wrong escape when the plan is fully ticked.** Driven from
the parked state: `refusing: this plan is PAUSED … If the work has resumed, run --resume first.`
For a fully-ticked parked plan the correct next command is `--finish`; the preserve WARN gets this
right by naming both, the tick refusal does not.

**L7 — three of the fold's new begin-plan cases are structurally unreachable by the mutation
harness.** `"a fully-ticked PAUSED plan does not report 'clear the sentinel'"` and its two siblings
(`:652-657`) assert `check-plan-progress` behaviour from `begin-plan`'s suite. They are **not
vacuous** — measured, mutating `:203` to `if False:` and running *begin-plan's* suite reddens all
three. But `check-plan-code.run_suite(d, fname)` runs only the mutated file's own suite, so no
manifest entry can ever exercise them. Their protection rests entirely on CI running both suites,
which it does (`ci.yml:198` directly for begin-plan; `check-plan-progress` via
`check-selftest-counts.py` at `:217`, as `block-idle-stop.sh:20-22` documents). Informational, but
worth recording so the coverage is not over-read.

**L8 — the `strip_field` docstring's new sentence separates its subject from its verb by 40
words.** `check-plan-progress.py:94-98`: *"`check-banner-armed._armed_from_text`'s docstring — cited
by SYMBOL, because … a citation with a countdown on it — records the near-miss…"*. The symbol
citation is correct (`check-banner-armed.py:490`, and its docstring does carry the `":" not in
line` near-miss). The sentence is the thing PR #231's comprehensibility pass was about.

---

## Full mutation run — RUN, and it confirms the claimed figure

`python3 scripts/check-plan-code.py --mutate .`, run to completion (~25 min wall clock):

```
OK — delivered scripts mutated: 10 file(s), 206 mutation(s), 0 survivor(s)
exit 0
```

So the branch's *"206 mutations / 0 survivors"* is verified, not taken on report. Note what that
figure does and does not say: it certifies that every declared mutation dies via the case it names.
It says nothing about the branches no mutation targets — which is where H1's `\r` half, M2's
`--finish` guidance and L4's control all sit. Each of those was found by building the probe the
manifest is missing, and each went red immediately.

---

## Dispositions requested

- **H1** — derive the refusal predicate from `splitlines()` rather than from a two-character list,
  and point the mutation at a non-`\n` separator. This is the one item I would not merge without.
- **M1** — finish the sweep in `block-idle-stop.sh` (four citations), and correct "ten" to seven in
  the dashboard entry and backlog row 99.
- **M2** — one manifest entry; the probe above is the entry.
- **L1–L8** — record dispositions; none blocks on its own. L2 and L3 are one-line each.

**NOT CONVERGED.**
