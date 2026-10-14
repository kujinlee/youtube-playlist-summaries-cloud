# `stale-plan-visible-at-session-start` — round 1, CLAUDE half

Subject: branch `stale-plan-visible-at-session-start`, single commit `1506073d` on `origin/master`
(`74a44551`). Mandate: adversarial — refute the commit's nine load-bearing claims.

**Headline.** The two claims the brief said matter most both SURVIVE, and one of them is now measured
rather than asserted: a SessionStart hook's stdout really is the only channel that reaches the
assistant, and a non-zero exit really does suppress it (three arms, green control, §S1). The
session-start partition really is strictly coarser than `decide`'s and reads a strict subset of its
inputs, so "no new discriminator" holds (§S4). What does not survive is the **evidence**: the branch
duplicates two pre-existing mutation anchors, so `check-plan-code.py --mutate .` — the gate
`docs/dev-process.md` records as "what CI runs" — refuses the whole manifest and reports
`NOT MEASURED`, in both the unsharded and the sharded form, where `origin/master` is green under the
identical recipe. The commit records that sweep as NOT RUN, which is exactly why it shipped.

Below that, the new verb's I/O shell is the weak half: `append_step` (pure) has fourteen cases,
`cmd_add` (the verb) has none, and the branch it is defended at most length for — *create a plan when
nothing is armed* — crashes with an unhandled traceback on four of five realistic promise titles and
silently overwrites an existing plan file holding unticked work.

---

## Blocking

### B1 — `--mutate .` goes RED on this branch: two pre-existing anchors are now ambiguous

The commit adds code that duplicates the exact anchor text of two **existing** mutation entries, so
the harness refuses them, and a refused entry voids the whole run.

| anchor (exact line) | file | occurrences on `74a44551` | occurrences on `1506073d` |
|---|---|---|---|
| `    if "paused" in fields:` | `scripts/begin-plan.py` | 1 (`:364`) | 2 — `:411` (`cmd_tick`) and **`:466` (`cmd_add`, new)** |
| `    paused = fields.get("paused")` | `scripts/check-plan-progress.py` | 1 (`:182`) | 2 — `:183` (`decide`) and **`:391` (`session_start_verdict`, new)** |

Counted with `git show <rev>:<file> | grep -cxF '<anchor>'`, so this does not depend on the harness
at all. The owning entries are `--tick stops consulting the pause, so a paused plan advances again
(backlog #99)` in `scripts/mutations/begin-plan.json` and `paused short-circuits to a silent ALLOW
again (backlog #99 restored)` in `scripts/mutations/check-plan-progress.json` — both predate this
commit and neither was touched by it.

The harness's response is not a warning:

```
✗ mutation '--tick stops consulting the pause, …': anchor matches 2 times in scripts/begin-plan.py
  — only the FIRST is replaced, so a 'caught' verdict would not be about the line you named. Tighten it
✗ mutation 'paused short-circuits to a silent ALLOW again (backlog #99 restored)': anchor matches 2 times …
NOT MEASURED — the mutation harness produced no coverage verdict (38 of 40 declared mutation(s)
produced a verdict). Treat this as NOT CHECKED. — measured over the WHOLE manifest
```

**The discriminating pair.** Same recipe (pruned `HARNESS_TREE` copy, two manifests, pruned
`EXPECTED_MUTATIONS`), two trees, opposite verdicts — so the red is caused by this commit and not by
the scoping recipe:

| tree | `--mutate .` | `--shard0 0/2` | `--shard0 1/2` |
|---|---|---|---|
| `74a44551` (base) | **rc=0** — 35 mutations, 35 killed, 35 attributed, 0 survivors | rc=0, 18/18 | rc=0, 17/17 |
| `1506073d` (branch) | **rc=1** — NOT MEASURED, 38 of 40 produced a verdict | rc=1 NOT MEASURED | rc=1 NOT MEASURED |

The sharded row matters because `.github/workflows/ci.yml:723` invokes
`check-plan-code.py --mutate . --shard0 "$SHARD_INDEX/$SHARD_TOTAL"`. `shard_slice` is round-robin,
so the two bad entries land in different shards and **both** shards refuse; there is no shard count
at which this is survivable.

**Why the commit did not see it.** Its evidence line is *"Five mutation entries, pinned counts 17 ->
19 and 18 -> 21 … 0 survivors, 5 of 5 killed through the case each NAMES"* and, separately, *"NOT
RUN: the full `--mutate .` sweep (a CANNOT RUN locally, not a slow pass)"*. The collision is invisible
to a five-entry measurement because the ambiguity is between a NEW line and an OLD entry: you only
see it when the pre-existing entries for the same two files run alongside. My scoped run is a
two-manifest `--mutate .`, which is the smallest run that can see it — about 9 seconds.

This is `docs/memory/a-mutation-anchor-is-unbound-by-any-edit-nearby.md` happening again: the edits
that broke these anchors are *additive* and nowhere near the lines the entries name.

**Fix (a hypothesis, not a verified repair):** tighten both anchors to include a neighbouring line
that is still unique — e.g. the `cmd_tick` one to `    if "paused" in fields:\n        print(f"refusing: this plan is PAUSED`
and the `decide` one to include the following `if plan_text is None:` — then re-run the two-manifest
sweep and require it to print `OK … 40 killed, 40 attributed`.

---

## High

### H1 — `cmd_add` crashes with an unhandled traceback on a promise title containing `/`, `..` or a leading dot

`cmd_add` calls `normalise_slug(title)` directly at `scripts/begin-plan.py:451`, outside any
`try/except`. `cmd_begin` has the handler (`:354-357`), but `cmd_add` computes the slug *before*
delegating, in order to print it. `normalise_slug` **raises** on a path separator, `..`, or a leading
dot — by design, and the docstring says so.

Measured, with nothing armed (the state the commit defends this branch for), five titles:

| `--add "<title>|…"` | rc | armed afterwards | outcome |
|---|---|---|---|
| `Dispatch the r2 Codex half` | 0 | YES | plan created ✅ |
| `Run scripts/check-docs.py` | 1 | NO | **`ValueError` traceback** |
| `Fold rounds 2..3 into the branch` | 1 | NO | **`ValueError` traceback** |
| `Fix .claude/hooks/report-plan-state.sh` | 1 | NO | **`ValueError` traceback** |
| `⤳` | 1 | NO | **`ValueError` traceback** |

```
File ".../scripts/begin-plan.py", line 451, in cmd_add
    slug = normalise_slug(title)
ValueError: refusing the slug 'Run scripts/check-docs.py': it contains a path separator, `..`, or a
leading dot. The plan is written under .claude/plans/ and the name must stay inside it.
```

Three of those four titles are the shape this repository's promises actually take — they name a file
path, or they trail off in an ellipsis typed as `...`. The verb exists so that *"a promise about work
that was not already a step"* has somewhere to go; on this input it has nowhere to go, in the one
state (`armed is None`) the docstring argues hardest for:

> ⛔ IT CREATES A PLAN WHEN NOTHING IS ARMED, RATHER THAN REFUSING — and that is the point.

It is loud (a traceback, rc=1), so it is not silent data loss; it is a total failure of the recording
step. **Fix hypothesis:** catch `ValueError` and fall back to a derived slug that cannot raise
(e.g. `normalise_slug(re.sub(r"[/\\.]+", " ", title))`, or a dated `promise-YYYY-MM-DD-N`), keeping the
full title as the step text — the title is already carried through `step_arg` and never needs to be
the filename.

### H2 — `cmd_add`'s create path silently overwrites an existing plan file, destroying unticked work

`cmd_begin` writes unconditionally (`scripts/begin-plan.py:367`,
`plan_abs.write_text(render_plan(...))`). With `--add`, the slug is derived from free text rather
than typed, so the operator is never aware a filename is being chosen. Measured:

```
before: .claude/plans/dispatch-the-r2-half.md contains "- [ ] **Step 1 of 1** — OLD WORK STILL OUTSTANDING"
$ begin-plan.py --add "Dispatch the r2 half|spawn it|owed"      # rc=0
after : grep -c 'OLD WORK' -> 0      # the file is the new one-step plan; the unticked step is gone
```

`.claude/plans/` is gitignored (`.gitignore:96`), so **there is no other copy** — which is this
repo's most expensive recorded lesson (`docs/memory/verify-the-other-copy-exists-before-deleting.md`).

Reachability is a conjunction and I state it rather than hide it: you need (a) nothing armed, (b) an
existing plan whose slug equals the normalised promise title, (c) that plan to hold unticked work.
(b) arises naturally because review-loop promises *repeat* — "Dispatch the r2 half" is the same
sentence every round — and (c) arises because `--finish` removes the sentinel and leaves the plan
file behind. Note the clobber is pre-existing in `cmd_begin`; what is new is that `--add` reaches it
from free text, automatically, as the documented fallback.

**Fix hypothesis:** in the `armed is None` branch, refuse-or-suffix on an existing path
(`<slug>-2.md`), or arm on the existing file and append to it instead of rewriting it.

### H3 — the hook fails SILENT on its own breakage, and silence is indistinguishable from a clean run

`.claude/hooks/report-plan-state.sh` is three lines of substance:

```bash
python3 "$REPO_ROOT/scripts/check-plan-progress.py" --session-start </dev/null 2>/dev/null
exit 0
```

`2>/dev/null` discards the only channel a crash has, and `exit 0` discards the only code. Measured,
against a green control (242 bytes of correct verdict text):

| arm | rc | stdout bytes | stderr the reader can see |
|---|---|---|---|
| control (as shipped) | 0 | **242** | — |
| `check-plan-progress.py` has a syntax error | 0 | **0** | 0 |
| `check-plan-progress.py` renamed away | 0 | **0** | 0 |
| `python3` absent from `PATH` | 0 | **0** | 0 (bash's own message; Claude never sees stderr from a hook that exits 0 — §S1) |
| `python3` present but errors on the source | 0 | **0** | 0 |

The reader therefore cannot distinguish *the guard ran* from *the guard did not run* — and
`session_start_verdict` has **no silent branch**: all five labels print (§S2 measured eight states,
all non-empty). So emptiness is unambiguously breakage, which makes the fix cheap and the omission
clean-cut.

This is not covered by the commit's documented deviation. That deviation is argued at the exit-code
level only, and explicitly rests on the text arriving:

> ⚠ That is a DOCUMENTED deviation from "cannot run is a failure, never a pass" at the exit-code
> level only: the CANNOT-RUN text still says TREAT THIS AS NOT RUN, which is the part a reader acts on.

In all four arms there *is no text*. The commit's own verification narrative names the identical
shape one paragraph earlier — *"A first guard sweep printed `red: 0` having run ZERO guards … A
vacuous pass is not a pass"* — and the delivered hook has it.

**Fix hypothesis:** capture stdout, and when it is empty print a CANNOT-RUN line of the hook's own
(still `exit 0`, since §S1 proves a non-zero suppresses it), e.g.
`out=$(python3 … 2>&1); [ -n "$out" ] && printf '%s\n' "$out" || echo "[plan-progress/cannot-run] the plan-state reporter produced no output — TREAT THIS AS NOT RUN"`.
Note this also fixes the `2>/dev/null`: a traceback becomes the evidence instead of being thrown away.

### H4 — `--add` on a paused plan records a promise that nothing in this commit will ever mention again

The commit chooses to append on a paused plan and keep the pause. Measured consequence, end to end
on a copy:

```
$ begin-plan.py --add "Dispatch the r2 half|spawn the agent|a promise is inert"
rc=0  stdout: added step 3 to .claude/plans/demo-paused.md: Dispatch the r2 half
      stderr: ⏸ the plan is still PAUSED … `--resume` re-arms it.
$ check-plan-progress.py --decide                       → rc=0   stdout:[]  stderr:[]
$ check-plan-progress.py --decide --stop-hook-active     → rc=0   stdout:[]  stderr:[]
```

`rc=0`, **both streams empty**, with an unticked promise standing. The path is `decide`'s paused arm
where the outstanding count did not FALL (it grew), which returns `ALLOW, ""` by design — the arm
`scripts/mutations/check-plan-progress.json` already describes as *"paused and the plan GREW -> ALLOW
and silent"*. That arm was written for a hand edit; `--add` makes it a first-class, tool-supported
flow.

**Control, so this is not a general complaint:** the identical append on the same plan after
`--resume` makes the guard refuse the stop — `rc=2`, `⛔ DO NOT STOP — 1 of 3 steps are unticked`. The
verb works; the paused branch is the hole.

So the promise's only notice is the one-shot stderr line at add time — a message at the moment of the
promise, which is precisely the delivery this project has measured six times as not surviving the
turn boundary. And the session-start reporter cannot help: it fires at session boundaries, not at
stops. **This is a third hole, and the commit's stated non-coverage (§claim 9) does not name it.**

**Fix hypothesis (unverified, and it needs a decision first):** either re-baseline the stamp on append
(`paused_unticked` := new outstanding count, so a later tick-without-resume is still detectable), or
record an `added_while_paused:` marker that `decide`'s quiet arm turns into one short WARN line.
Backlog #100 already owns the grammar this needs.

---

## Medium

### M1 — the `of N` rewrite reaches PROSE and FENCED CODE, which refutes the commit's scope claim

The commit says:

> The substitution touches only the total inside the prefix `_STEP_PREFIX_RE` already owns, and the
> preservation cases assert the earlier steps' `Doing:`/`Why:` and titles survive it.

That is false about the scope. `_TOTAL_RE` (`scripts/begin-plan.py:184`) is **unanchored and applied
globally** (`:219`, `.sub` with no count); `_STEP_PREFIX_RE` (`:87`) is anchored with `^` and applied
to the *title text of a parsed checkbox* (`:243`). The two own different sets of lines, and `_TOTAL_RE`
owns the larger one. Measured on a plan that documents its own format:

```
input  : The generated shape is `**Step 1 of 2** — <title>`, which the banner derives.
         ```markdown
         - [ ] **Step 1 of 2** — a worked example from the docs
         ```
after  : The generated shape is `**Step 1 of 4** — <title>`, which the banner derives.
         - [ ] **Step 1 of 4** — a worked example from the docs   (inside the fence)
```

The prose sentence is not a checkbox, so `_STEP_PREFIX_RE` never sees it; `_TOTAL_RE` rewrote it
anyway. The fenced example is additionally *counted as a step* by both parsers (`parse_steps` and
`count_steps` anchor at column 0 and do not track fences) — pre-existing, but `--add` is the first
verb that **writes** on the strength of that count.

The preservation cases are described as "the control for the rewrite above", and they are — for a
`render_plan` output with no prose and no fences. The control is narrower than the claim it controls,
which is this repo's own `a-bound-enumerates-what-is-witnessed` shape.

Blast radius, measured honestly: `.claude/plans/` is gitignored, so in the generated-plan path the
damage is cosmetic and local. But `cmd_plan` (`--plan PATH`) exists to arm on a committed plan — its
`parse_steps` docstring records *"Measured 2026-09-04 by arming on a committed plan"* — and **105
tracked documents under `docs/` carry top-level checkboxes** and are therefore legitimate targets. On
`docs/roadmap-to-launch.md` (181 checkboxes) a single `--add` appends six lines and a
`### Task 182:` heading to the repo's compaction-proof roadmap, with no confirmation and no mention of
the possibility in `cmd_add`'s docstring.

### M2 — the stated non-coverage is wrong about its own first hole: the hook fires more than once

> ⚠ WHAT THIS DOES NOT COVER … session start fires ONCE, so it sees a sentinel stale BEFORE the
> session, never one that goes stale DURING it

`.claude/settings.json` registers the hook with **no `matcher`**, and Claude Code's hooks reference
says an omitted matcher *"fires on every occurrence of the event"*, with SessionStart's own matcher
table listing `startup`, `resume`, `clear`, `compact` (*"Auto or manual compaction"*) and `fork`.

Measured, with a probe hook that logs the `source` field it receives:

```
$ claude -p 'say OK'              → FIRED source= startup
$ claude -p --continue 'say OK'   → FIRED source= resume
```

Two firings, so "fires ONCE" is false as shipped. The `compact` arm I did not force and I am not
claiming it as measured (see CANNOT RUN) — but `clear` and `resume` alone are mid-work boundaries,
and in a repository whose CLAUDE.md is organised around surviving `/compact`, a compaction re-fire is
the common case rather than an edge.

Why this is worth filing rather than welcoming: the commit then proposes design work *for* that hole
(*"The owner's contingent-task idea is the answer to the first"*), on a premise its own configuration
already partly falsifies. A caveat headed "stated rather than implied" that is wrong is worse than
none, because nobody re-examines it.

### M3 — the CANNOT-RUN message drops the consequence that the other two messages state

Measured on the same sentinel (`plan:` naming a missing file):

| path | result |
|---|---|
| `--decide` | **rc=2 = BLOCK.** `.claude/hooks/block-idle-stop.sh:24-25` maps anything outside `{0,3}` to `exit 2`, so **every stop is refused** until the sentinel is fixed |
| `--session-start` | rc=0, `[plan-progress/cannot-run] … TREAT THIS AS NOT RUN — nothing here tells you whether work is outstanding. Fix the path or delete .claude/executing-plan.` |

The session-start text contains **zero** occurrences of "refuse", "block" or "BLOCK" (`grep -c` on
the captured output). Meanwhile the sibling messages do name their consequence — STALE says *"The
Stop guard will not refuse an idle stop while it stands"* (`:418`), PARKED says *"an idle stop will be
allowed"*. So the message set states the consequence in the two states where the guard **allows** and
omits it in the one state where the guard **blocks** — the only one where the reader needs it, and
the only one where not knowing costs a session that cannot end. One clause fixes it.

### M4 — the new verb has no self-test at all; only the pure helper does

All fourteen new `begin-plan` cases exercise `append_step` (pure). `cmd_add` appears in the file
exactly once outside its own definition — at the argparse dispatch, `:1146`. Compare its five
siblings, every one of which has cases inside the existing ROOT-patching harness:
`cmd_tick` (`:794`), `cmd_pause` (`:791`), `cmd_resume` (`:974`), `cmd_finish` (`:1042`),
`cmd_begin` (via the harness block).

Three branches of `cmd_add` are therefore unfalsified: the `armed is None` create path (H1, H2 live
in it), the paused-append path (H4), and the missing-plan CANNOT-RUN path. This is the cause of two
of the three Highs above, and the harness it needs already exists twelve lines away — the
`real = ROOT, PLAN_DIR, SENTINEL, STATE` / `try/finally` block the other verbs use. `append_step`'s
own docstring names this defect class (*"the first version of this branch proved the behaviour in a
THROWAWAY SCRIPT, which leaves the shipped function with no falsifier at all"*) and then stops one
layer short of the verb.

### M5 — the first impure case in a previously pure suite, and the branch it traverses is ambient

`check-plan-progress.py`'s self-test was **entirely pure** before this commit: no ROOT patching
anywhere in the file, and `read_text`/`write_text` reached only from `run_decide`/`run_status`, which
the suite never called. Line `:771` now calls `run_session_start()`, which reads the **live**
`.claude/executing-plan` of whatever tree the suite runs in.

Consequence, measured by construction: `HARNESS_TREE` stages `scripts`, `supabase`, `docs`,
`node_modules/typescript`, `.claude/hooks` and `.github/workflows` — never `.claude/executing-plan`
(which is gitignored besides). So inside the mutation harness and in CI these three cases always
traverse the **UNARMED** branch, while on a developer machine mid-plan they traverse LIVE, PARKED or
STALE. It is benign today because every branch prints and returns 0, so no state can turn the cases
red — but that is also why it reads as coverage it is not: a future mutation of the STALE text could
never be caught through `run_session_start` in the harness world. Patching ROOT for these three cases
costs three lines and makes the traversed branch a choice instead of an accident.

---

## Low

### L1 — the "CHANNEL CASE" comment sits above a case that asserts nothing about the channel

`scripts/check-plan-progress.py:756-761`. The comment reads *"⛔ THE CHANNEL CASE. A Stop hook
reaches its reader via stderr and a non-zero code; a SessionStart hook reaches its reader by putting
stdout into the session's context and exiting 0. Inverting that is the defect this mode repairs, so
it is asserted, not assumed."* The case under it is
`case("every session-start label is distinct — no two states collapse", len({STALE, LIVE, PARKED, UNARMED, NOT_RUN}) == 5)`
— a statement about five module constants that touches neither stream nor exit code. The channel
*is* asserted, by the three cases in the block below it, which carry their own comment. So the
comment is misfiled rather than false, and the risk is a reader (or a future mutation author)
crediting the channel to the wrong case.

### L2 — `"writes the verdict to STDOUT, not stderr"` does not assert the "not stderr" half

`:774`, `_out.strip() != ""`. Measured on a copy:

| mutation of `run_session_start` | suite |
|---|---|
| print to `sys.stderr` only | **64/66** — two cases red ✅ the essential half binds |
| print to **both** stdout and stderr | **66/66** — green, so "not stderr" is unfalsifiable |

The property that matters (it reaches stdout) is genuinely covered, and printing to both is harmless,
so this is a naming defect, not a coverage hole — but the name promises a two-channel assertion the
expression cannot make.

### L3 — two assertions carry a half that cannot independently fail

* `:735` — `label_parked == PARKED and label_parked not in (STALE, LIVE)`. Given the distinctness
  the case at `:760` pins, the second conjunct is implied by the first; no change to the code can
  make it the one that fires.
* `:749` — `session_start_verdict(None, None)[0] != STALE`, two lines after
  `case("no sentinel -> UNARMED", label_un == UNARMED)`, which implies it for the same reason.

Neither is a tautology in the sense the commit's own replaced case was (`v == (UNARMED, v[1])`) — both
*can* fail if the constants collide — but each is satisfied by a sibling case, so neither adds a
falsifier. Worth noting only because this commit's self-report makes "a case that cannot fail" its
own subject.

### L4 — only the totals are rewritten, never the indices, so a self-contradictory label set is still reachable

From the M1 measurement, the four checkbox labels after one `--add` read
`Step 1 of 4`, `Step 1 of 4`, `Step 2 of 4`, `Step 4 of 4`. The case
`"every `of N` total is rewritten — no stale `of 2` survives"` holds; the broader property a reader
will take from the commit message (*"Not doing so leaves `Step 1 of 2` beside `Step 3 of 3`"*) does
not. It is cosmetic for the same reason the commit gives — `render_banner` derives `n of N` from the
parsed checkboxes — and I raise it only to bound the claim: on a generated 1..n plan the indices are
already correct and nothing is wrong; on anything else the rewrite half-repairs the drift it names.

---

## Checked and found SOUND

### S1 — claim 2, the harness premise, is RIGHT, and it is now measured

This is the claim the whole design rests on, so I tested it rather than reading about it. Probe: a
throwaway project with SessionStart hooks, driven by `claude -p --model haiku --output-format json`
asking the model to echo every line in its context containing `PROBE`.

**Arm set 1 — does stdout reach the assistant, and does a leading `[` break it?** (`[` opens a JSON
array, which was my first hypothesis for a defect.)

```
result: SessionStart:startup hook success: [plan-progress/stale] PROBEBRACKET-7F3A — a bracket-led plain line
        SessionStart:startup hook success: plan-progress-stale PROBEPLAIN-9C2B — a plain line with no leading bracket
```

Both arms reached the model; the bracket-free arm is the green control that proves the probe can see
a line at all. **Hypothesis refuted, nothing filed.** The docs confirm the mechanism: *"A JSON array
and a quoted JSON string are plain text by this rule"*, and *"A hook that only adds context can print
it without building JSON, because Claude Code adds a SessionStart hook's plain-text stdout to
Claude's context."*

**Arm set 2 — would a non-zero exit really suppress the text?** Three hooks in one project:

| hook | reached the model's context |
|---|---|
| stdout + `exit 0` | **YES** (control, green) |
| stdout + `exit 1` | **NO** |
| stdout + stderr + `exit 2` | **NO** (neither stream) |

So *"a non-zero would suppress the sentence that reports the failure"* is measured, not assumed, and
the documented deviation from "cannot run is never a pass" at the exit-code level is justified. The
reference agrees: SessionStart's row in the per-event table is *"Can block? No — shows stderr to user
only"*, and *"Claude never sees stderr from a hook that exits 0."*

This also confirms the commit's **diagnosis**: `block-idle-stop.sh:31-32` maps WARN=3 to `exit 1`,
which is a non-blocking error whose notice goes to the human — so the correct WARN genuinely could
not reach the assistant, and routing it to `exit 2` instead (which does reach Claude on a Stop hook)
would block the stop, which is the thing backlog #99/#56 already rejected. The channel framing is the
right one.

### S2 — claim 5, read-only, holds in every state including both CANNOT-RUN paths

Hashed `.claude/executing-plan`, `.claude/executing-plan.state` and `.claude/plans/*` before and after
`--session-start`, in eight states:

| state | label | rc | files unchanged | stderr |
|---|---|---|---|---|
| unarmed | `unarmed` | 0 | YES | 0 B |
| live 0/2 | `live` | 0 | YES | 0 B |
| parked | `parked` | 0 | YES | 0 B |
| ticked, unpaused | `stale` | 0 | YES | 0 B |
| ticked + paused | `stale` | 0 | YES | 0 B |
| sentinel names a missing plan | `cannot-run` | 0 | YES | 0 B |
| plan parses to zero checkboxes | `cannot-run` | 0 | YES | 0 B |
| sentinel with no `plan:` key | `cannot-run` | 0 | YES | 0 B |

`run_session_start` (`:497-509`) contains no `unlink` and no `write_text`, unlike `run_decide`
(`:461-464`). Every state prints a non-empty line — which is what makes H3 a clean finding.

### S3 — claim 6: all six counts re-derive, under both interpreters

| declared | re-derived |
|---|---|
| `begin-plan --self-test` 78 (doc `# 78 cases`) | **78/78**, rc=0, on 3.14.4 and 3.12.9 |
| `check-plan-progress --self-test` 66 (doc `# 66 cases`) | **66/66**, rc=0, both |
| `check-plan-code --self-test` 178 | **178/178**, rc=0 |
| pinned `check-plan-progress.py` 17 → 19 | manifest holds **19** entries, 19 unique names |
| pinned `begin-plan.py` 18 → 21 | manifest holds **21** entries, 21 unique names |
| declared sum 1408 → 1413 | `sum(EXPECTED_MUTATIONS.values())` = **1413** over 59 keys; 1408 + 2 + 3 = 1413 |

Independently, `scripts/check-selftest-counts.py` is green on the branch: *"52 script(s) declare a
count, every one verified by running it"* — so the declarations are machine-checked, not just agreed
with by me. No stale `63`/`43`/`1408` citation survives anywhere outside historical trail comments
(grepped across `*.md`, `*.py`, `*.yml`).

### S4 — claim 1 survives: the session-start partition is strictly COARSER and reads a strict SUBSET

I diffed the two state machines as the brief asked, and the commit's wording holds on the reading that
matters. *Inputs read:* `decide` reads sentinel text, plan text, `paused_unticked`, `STATE` and
`stop_hook_active`; `session_start_verdict` reads **sentinel text and plan text only** — a strict
subset. *Partition:* session-start **merges** cells `decide` separates and splits none that `decide`
merges —

| cell | `decide` | `session_start_verdict` |
|---|---|---|
| ticked + paused | WARN, sentinel KEPT | STALE |
| ticked + unpaused | ALLOW silent, sentinel CLEARED | STALE |
| plan missing, paused / unpaused | WARN / BLOCK | NOT_RUN (merged) |
| zero checkboxes, paused / unpaused | WARN / BLOCK | NOT_RUN (merged) |
| unticked + paused, three stamp arms | WARN / WARN / ALLOW silent | PARKED (merged) |

A coarser partition over fewer inputs cannot be a new discriminator, so *"it adds no new
discriminator"* is literally true. What IS new is the **verdict** on one cell — ticked-and-unpaused is
silent in `decide` and a ⚠ at session start — and that is a channel difference (same state, different
audience, different moment), not a seventh rule. It is also disclosed twice, in the commit message
and at the case (`:725-731`, *"`--decide` treats these two differently on purpose … at session start
both describe a finished job"*), rather than smuggled.

I also checked the collapse is *right*, and I think it is: the ticked-and-unpaused sentinel can only
survive to a session start if no Stop decide ran since the last tick (a crash, a `/clear`), and in
both halves of the collapsed cell the sentence the reader is given — *"The Stop guard will not refuse
an idle stop while it stands"* — is true (ALLOW in one arm, WARN→`exit 1` non-blocking in the other).
The one place the consequence is NOT stated is the cannot-run cell, which is M3.

### S5 — the headline behaviour reproduces exactly, including the adjacent negative

Rebuilt today's state on a copy (2-step plan, both ticked, then `--pause`):

```
sentinel: plan: … / paused: waiting on a dispatched review / paused_unticked: 0
--decide        → rc=3 (WARN) on stderr  ⏸ PAUSED, and every step … is ticked (2/2)
--session-start → rc=0 on stdout  [plan-progress/stale] ⚠ STALE PLAN ARMED — … (2/2) … The Stop
                  guard will not refuse an idle stop while it stands.
                     Its pause reason, which is now historical: waiting on a dispatched review
                     → `scripts/begin-plan.py --finish`, then arm the current job before starting it.
```

Adjacent negative (one box unticked, paused) → `[plan-progress/parked]`, `1 of 3 outstanding`, not
stale. Both halves of the claim hold.

### S6 — the five new mutation entries each die through the case they name

In the two-manifest run, 38 of 40 entries produced a verdict and **no survivor was reported** — the
harness reports only failures, and the only two ✗ lines were the anchor-ambiguity refusals of B1. So
the per-entry half of the commit's claim is right; it is the run that is void, not the entries. The
five new entries are also well-formed in the ways the brief asked about: each `expect` string matches
a case name present in the suite, and the five anchors are each unique in their target file (I counted
all five with `grep -cxF`; the two ambiguous anchors belong to **pre-existing** entries).

### S7 — the new hook owes no `--self-test`, and other population guards are green

`check-ratchet-contract.py`'s guard population is `GUARD_PATH_RE` over `scripts/`, not
`.claude/hooks/` — `discover_guards` (`:160-171`); `.claude/hooks/*` enters only through
`caller_source_paths` as **caller evidence**. So `report-plan-state.sh` is not owed a self-test, and
it does supply R3 caller evidence for `check-plan-progress.py` (which already had
`block-idle-stop.sh`). Green on the branch, run with stdin closed under 3.12:

| guard | rc | |
|---|---|---|
| `check-ratchet-contract.py` | 0 | 44 guards discovered |
| `check-guard-coverage.py` | 0 | every SEQUENCE guard reconciles and is mutation-covered |
| `check-selftest-counts.py` | 0 | 52 declared counts, all verified by running them |
| `check-docs.py` | 0 | documentation integrity OK |
| `check-anchors.py` | 0 | 13 registered, floor 22 held |

### S8 — the `.claude/settings.json` registration is consistent with the repo's eight other hook entries

Relative `bash .claude/hooks/<name>.sh` with a `statusMessage` is the form every other entry uses, so
the new one introduces no new path convention. `SessionStart` accepts `type: "command"`, and the
10,000-character plain-stdout cap is far above the ~250-byte verdict.

---

## CANNOT RUN

⛔ Each of these is a FAILURE to measure, not a pass. **Treat them as NOT RUN.**

* **The full `--mutate .` sweep over all 59 manifests.** I ran **2 of 59** (`begin-plan`,
  `check-plan-progress`) on a pruned `HARNESS_TREE` copy. The other 57 manifests — 1,373 of the 1,413
  declared mutations — are **NOT RUN**; a local 8-shard run is a documented CANNOT RUN on this
  machine (`SUITE_TIMEOUT = 120` versus a control pass that wants ~5 cores by itself). My scoped run
  is authoritative for its own positive red (B1) and says nothing about the rest.
* **The commit's "48 document guards from `ci.yml` discovered, 48 RAN, 0 red".** NOT re-derived — the
  discovery list was ad-hoc and is not in the tree, and `ci.yml` names 32 distinct `scripts/check-*.py`
  invocations, so I cannot reconstruct which 48 steps were counted. I ran six named guards instead
  (§S7 plus `check-review-rounds`). The claim is neither confirmed nor refuted here.
* **The `compact` arm of the SessionStart matcher.** M2 measures `startup` and `resume` only. That
  the hook also fires on `compact` and `clear` is taken from the hooks reference's matcher table, NOT
  measured — M2 does not depend on it, since `resume` alone falsifies "fires ONCE".
* **`scripts/check-test-counts.py`** — no `jest-results.json` in the tree. NOT RUN.
* **The TypeScript, unit, integration and e2e suites** — not run. The branch touches no TS, but that
  is an argument, not a measurement.
* **The PR-only gates.** `check-dashboard-entry.py` is `if: github.event_name == 'pull_request'`
  (`ci.yml:523`) and `check-review-recorded` likewise; run bare, `check-dashboard-entry.py` refuses
  (*7 tracked file(s) changed and no entry*), which is the expected pre-PR state and is **not filed**
  — it is the brief's known-true context. It does mean an entry or a `NO-ENTRY:` reason is owed before
  the PR.
* **`check-review-rounds.py` exits 1** on this tree because a round with one half exists. Expected
  mid-round-1 and not filed; it should go green once both halves are filed under
  `docs/reviews/<writer>/`.

---

## Instruments

* **Worktree reviewed:** `…/scratchpad/wt-staleplan` at `1506073d`. No `git` command was run in the
  main checkout. Nothing in the worktree was modified except this file.
* **Isolation:** every destructive probe ran on a `tar`/`cp -R` copy under my own scratchpad
  (`copy/`, `hookfail/`, `stcase/`, `mut/`, `base/`), with `node_modules` symlinked. The control was
  proved green on each copy before any mutation (78/78 and 66/66 on `copy/`; 242 bytes of verdict on
  `hookfail/`; 35/35 killed on `base/`), and each mutation was reverted immediately after.
* **Interpreters:** `python3` = 3.14.4 and `/usr/local/bin/python3.12` = 3.12.9 (the CI pin). Both
  were used for the self-tests; the two agreed on every count. Guards and scripts were run with stdin
  closed (`</dev/null`) throughout.
* **Exit codes** were read directly from the command, never after a pipe — the first self-test run of
  this review did read `$?` after `| tail`, which reports `tail`'s status; it was re-run.
* **Mutation recipe:** pruned `HARNESS_TREE` copy (the six paths read from the tuple, not guessed),
  all `scripts/mutations/*.json` removed but the two under test, `EXPECTED_MUTATIONS` reduced to the
  two matching keys. ~9 s for 40 entries. The base arm used `git archive 74a44551` plus the same
  pruning with the pre-commit pins (18, 17).
* **Harness probes** used `claude -p --model haiku --output-format json` in throwaway project
  directories, reading the model's own `result` field — so the measurement is what reached the
  model's context, not what the hook printed.
* ⚠ **Independence:** an untracked `docs/reviews/codex/stale-plan-visible-at-session-start-r1-codex.md`
  is present in the tree. I did **not** open it, and no finding above is informed by it. A sibling
  half sitting in the same tree is this repo's recorded *instruction-is-not-isolation* trap.
* **Not done:** I did not re-read the six prior instances of the promise failure or backlog #48/#56/
  #94/#99/#100 beyond the quotations the two scripts carry, so my judgement of H4's fix direction is a
  hypothesis about a decision this project has already litigated once.
