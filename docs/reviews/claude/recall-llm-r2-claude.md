# The LLM recall matcher (backlog #191) — round 2, Claude adversarial half

**Subject:** `semantic-recall-replication` at `a4a8c0b2`, working tree clean
(`git status --porcelain` empty at the time of every measurement below).
`git diff master...HEAD --stat`: 244 files, +148,182/−3.

**Round 2 is ALTERNATING**, so this half reviews three layers: the original code, the round-1 fold
(`c187d89b`, `636e24d5`, `73d28a5d`, `e64073fe`, `31e87a8a`) and the round-2 fold (`a4a8c0b2`).
Prior documents read first: `claude/recall-llm-r1-claude.md`, `codex/recall-llm-r1-codex.md`,
`codex/recall-llm-r2-codex.md`, `claude/semantic-recall-replication-2026-09-29.md`.

**Verdict: NOT CONVERGED — 1 Blocking, 5 High, 5 Medium, 7 Low.**

Every finding below was reproduced by execution against a built world under
`$SCRATCH/r2/` with `ROOT` and `HOME` redirected; the repository was not modified by any probe.
Where a finding is a code-reading claim rather than a measurement, it says so in its own sentence.

**What ran green, by running it.** `recall-llm.py --self-test` → `171/171`, matching the count
declared at `recall-llm.py:96`. Then **every `python3 scripts/check-*.py` entry point CI runs**, taken
from `.github/workflows/ci.yml` rather than from memory (`docs/CLAUDE.md` rule 1): `check-arch-findings`,
`check-backlog-closure`, `check-docs`, `check-explainer-delivery`, `check-features`,
`check-gate-falsifiability`, `check-group-claims`, `check-plan-file-tags`, `check-plan-task-order`,
`check-python-pin`, `check-review-rounds`, `check-roadmap-consistency`, `check-selftest-counts`,
`check-storage-grant-pin`, `check-theme-token-coverage`, `check-anchors`, `check-ratchet-contract`,
`check-vocabulary-collisions`, `check-dashboard-entry`, `check-memory-link` — all rc=0.
`check-review-rounds.py` was rc=1 (*"recall-llm round 2: only codex"*) until this document existed and
is rc=0 with it. `check-plan-code.py --mutate .` — see *Mutation sweep*.

**What ran RED:** `check-fixture-variation.py` rc=1 — finding H1.

**NOT RUN, so not green:** `check-guard-coverage.py`'s entry point, `check-producer-enumeration.py`,
`check-sentinel-meanings.py`, `check-storage-independence.py`, `check-function-revokes.py` and
`scripts/check-schema-gates.sh` need Postgres/Docker; `check-review-recorded.py`,
`check-merge-ready.py` and `check-test-counts.py --results` need a PR or a test run. Treat all of
those as **unknown on this branch**, never as passing.

---

## BLOCKING

### B1 · Three of the four "a plan IS armed and I cannot use it" states still share rc 2 with the one routine state, and the hook is silent for all of them — B1 of round 1, reproduced inside B1's own fix

**What is wrong.** Round 1's Blocking was: *"nothing fires" and "could not look" are the same
observation at the reader*. The fix invented `UNREADABLE_PLAN = 5` and split it out of rc 2, and the
docstring at `recall-llm.py:78-84` defines rc 5 as **"a plan IS armed and cannot be read"**. But rc 5
is raised at exactly two sites — `prepared_prompt:880` and `do_fire:922` — and both of them raise it
only for a **`plan_verdict` failure**. Every *other* way a plan can be armed and unusable still
raises a bare `Refusal` at rc 2:

| state | raised at | rc | through the hook |
|---|---|---|---|
| sentinel absent — **the routine state rc 2 is FOR** | `recall-llm.py:842` | 2 | silent ✅ correct |
| sentinel present, **names no plan** | `recall-llm.py:847` | 2 | **silent** |
| sentinel names a plan file **that does not exist** | `recall-llm.py:850` | 2 | **silent** |
| sentinel or plan **not valid UTF-8** | `recall-llm.py:844`, `:851` via `read_or_refuse` | 2 | **silent** |
| plan present, `plan_verdict` refuses it | `recall-llm.py:922` | 5 | forwarded ✅ |

**Measured, through the real hook** (`surface-recall.sh` copied into the built world, `--fire` run
by the hook exactly as `.claude/settings.json:50-59` runs it):

```
plan file rewritten with invalid UTF-8:
  CLI   -> RC=2  "CANNOT RUN: the plan file at …/w.md is not valid UTF-8, so NOTHING was
                  matched. This is not 'nothing applies' — the file could not be read at all."
  HOOK  -> stdout []                          <- the sentence the reader needed, discarded

plan file deleted while the sentinel still names it:
  CLI   -> RC=2  "CANNOT RUN: the sentinel names .claude/plans/w.md, which is not a readable file."
  HOOK  -> stdout []

sentinel present, names no plan:
  CLI   -> RC=2  "CANNOT RUN: the sentinel names no plan file."
  HOOK  -> stdout []

control — no sentinel at all:
  CLI   -> RC=2  "CANNOT RUN: no plan is armed (… absent) …"      <- correctly silent
```

**The message literally says "This is not 'nothing applies'" and the reader never sees it**, because
it arrives on the one code the hook is right to ignore. That is H1's shape as Codex described it in
round 2 (#2, the undecodable cache), fixed for the *cache* and left open for the *plan and the
sentinel* — which is the pair rc 5 was invented for.

**Reachability is ordinary, not adversarial.** `.claude/plans/` is gitignored (`.gitignore:96`), so
the plan file a live sentinel names is removed by a branch switch, a `git clean -xd`, or simply
renaming the plan — while `.claude/executing-plan` survives. From that moment every
`begin-plan.py` invocation is total silence with a plan still armed, which is the exact state the
fifth exit code was created to make audible.

**Why this is Blocking and not High.** It is not a new class: it is round 1's Blocking sentence,
about the same reader, in the same mode, reproduced by the commit whose message says it closed it.
The fold's own artefact (`UnreadablePlan`'s docstring, `recall-llm.py:146-163`) claims the caller can
now tell the two apart; measured, it can tell them apart in one state out of four.

**What would prove this finding wrong:** a run of `--fire` against a sentinel naming a deleted or
undecodable plan file that exits 5, or a demonstration that the hook forwards rc 2 when a sentinel
exists. Neither holds at `a4a8c0b2`.

---

## HIGH

### H1 · The delivered tree FAILS `check-fixture-variation.py`, which runs in CI — green before the round-2 fold, red at the tip

**What is wrong.** `python3 scripts/check-fixture-variation.py` exits **1** on `a4a8c0b2`:

```
FAILED — 3 parameter(s) never varied by any case:
  ✗ recall-llm.py: `read_or_refuse(path=…)`    is passed the SAME value at every call site (1x `f`)
  ✗ recall-llm.py: `read_or_refuse(refusal=…)` is passed the SAME value at every call site (1x `refusal`)
  ✗ recall-llm.py: `read_or_refuse(what=…)`    is passed the SAME value at every call site (1x 'recall cache')
```

That guard is a **required CI step** at `.github/workflows/ci.yml:347`. This branch cannot go green.

**Attributed to the round-2 fold, by running the CURRENT guard over the PREVIOUS source.** With
`scripts/` copied to a scratch tree and only `recall-llm.py` reverted to `31e87a8a`:

```
CURRENT guard over PRE-round-2 recall-llm.py  -> rc 0, "fixture variation OK — 714 parameter(s)
                                                  examined across 60 file(s)"
CURRENT guard over the tip                    -> rc 1, the three findings above
```

**The cause is the shape of the round-2 fix, not an oversight in the cases.** The two cases that
exist to prove `read_or_refuse` honours its class (`recall-llm.py:1828-1831`) both route through one
helper, `_read_or_refuse_label(refusal)` at `:1818-1826`, so in the **source text** there is a single
call site passing three identifiers — `f`, `'recall cache'`, `refusal`. The guard is textual and says
so (`check-fixture-variation.py` header: *"this guard proves a parameter was THOUGHT ABOUT in the
source"*). So the cases are behaviourally fine and the guard is still right to refuse: nothing in the
source distinguishes `read_or_refuse`'s parameters from constants.

⚠ **The mutation sweep cannot see this**, and that matters for how the fold was verified. The sweep
runs each guard's `--self-test`, not its entry point (`separate-the-rule-from-the-fetch`), so
`check-fixture-variation.py` is green as a *rule* and red as a *measurement of this repo* at the same
time. Codex's round-2 "Verified" section ran `--self-test` and `--mutate .` and neither could have
caught it.

**What would prove this finding wrong:** `python3 scripts/check-fixture-variation.py` exiting 0 from
the repository root on a clean checkout of `a4a8c0b2`.

---

### H2 · The MIXED plan still surfaces the WRONG lesson at rc 0 — round 1's B1 named this half, the fold did not close it, and nothing records that decision

**What is wrong.** Round 1's B1 had two halves. The fold closed the all-silent half by calling
`plan_verdict` in `do_fire` (`recall-llm.py:920-922`). The round-1 document said in as many words
that this *"closes the all-silent half but **not** the mixed half"*
(`claude/recall-llm-r1-claude.md:119-124`). Nothing since addresses it: there is no note in
`recall-llm.py`, no `⚠` in `plan_verdict`, no backlog row (the branch adds rows for #191 and #194
only), and no change to `begin-plan.py`'s grammar.

**Measured on the tip.** A plan whose outstanding box uses `begin-plan.py`'s own accepted shape
(`- [ ] **Step 1: …**`, which `begin-plan.py:86` matches and `_BOX_RE` at `recall-llm.py:171` does
not) above a parseable later step:

```
plan_steps      -> [(2, 'a situation')]        # the step the reader is ON has vanished
plan_verdict    -> (0, '')                      # accepted
first_unticked  -> 2                            # points at the LATER step
--fire          -> RC=0
   ⭐ recall — this moment matches a recorded lesson:
      the-entry
      FIRES-WHEN: a situation                   <- the reader is standing at GAMMA, step 1
```

No warning, no divergence note, rc 0. This is the failure the prompt itself names as the most
expensive one it can produce (`recall-llm.py:311-313`: *"A wrong lesson costs more than no lesson"*).

**Why it is still High after being disclosed.** A disclosed defect that is not fixed and not
recorded is indistinguishable, six weeks later, from one nobody noticed. The round-1 document is not
a durable channel; the code and the backlog are.

**What would prove this finding wrong:** a `--fire` on a plan mixing the two step grammars that
either refuses, or prints the situation belonging to the first unticked box under *either* parser.

---

### H3 · `do_arm` still exits **1** with a traceback on an unwritable cache directory — after the paid call, throwing the answer away. H1's fix covered the four READ sites and none of the WRITE sites

**What is wrong.** H1 of round 1 closed four UTF-8/OSError read paths through `decode_verdict` /
`read_or_refuse`. `do_arm`'s three write operations were not covered:
`CACHE_DIR.mkdir(...)` at `recall-llm.py:897`, `tmp.write_text(...)` at `:904` and `tmp.replace(out)`
at `:905`. None is inside a `try`, and `main`'s handler (`:1921-1930`) catches only `Refusal`.

**Measured without any paid call.** The module was imported, `call_model` replaced with a stub
returning a valid reply (`'{"1": "the-entry"}'`), the cache directory `chmod 500`, and `main(["--arm"])`
called:

```
recall-llm: ONE call for 1 step(s) against 1 triggers (1896 chars) …
UNCAUGHT PermissionError -> [Errno 13] Permission denied: '…/.claude/recall-cache/w.json.partial'
=> `main` did NOT convert it; the process would exit 1 with a traceback
```

**Why this is worse than the read paths H1 closed.** The failure happens strictly *after* the 16.1s
paid model call (`recall-llm.py:791` for the figure), so the answer that was bought is discarded
with no path to recover it, and the outcome is an rc the contract at `:56-88` does not define. The
whole thesis of this file is that every outcome is named.

**What would prove this finding wrong:** `--arm` against an unwritable `CACHE_DIR` returning a
defined rc with a named message.

---

### H4 · `LIVE_UNREADABLE` still falls back to the cached trigger, so `--fire` serves a healthy-looking match from an entry `--arm` refuses to load at all

**What is wrong.** Round 2 #1 split `live_trigger_for`'s bare `None` into three statuses
(`recall-llm.py:364-383`) and `do_fire` refuses only `LIVE_NO_TRIGGER` (`:960-963`). For
`LIVE_UNREADABLE` the caller still does `fire_output(entry, live_trigger or cached_trigger)` at
`:964`, and the divergence warning at `:965-968` requires `live_trigger` to be truthy — so an
unreadable entry produces no warning either.

**Measured.** Same world, entry file present but rewritten as invalid UTF-8:

```
--fire         -> RC=0
   ⭐ recall — this moment matches a recorded lesson:
      the-entry
      FIRES-WHEN: a situation          <- read from the CACHE; the live file says nothing readable
      (open the memory file of that name for the detail)   <- the reader cannot open it

--print-prompt -> RC=2
   CANNOT RUN: the memory entry at …/the-entry.md is not valid UTF-8, so NOTHING was matched.
   This is not 'nothing applies' — the file could not be read at all.
```

**The two modes disagree about the same byte, and this file already owns the rule.**
`load_triggers`'s docstring at `recall-llm.py:346-350` states it explicitly — *"A file this cannot
read is a file whose lesson cannot fire, and quietly skipping it shrinks the corpus without saying
so — which is the fail-open shape the whole rc contract above exists to refuse. It raises instead."*
Twelve lines later `live_trigger_for` does the opposite for the same file.

**And the justification for the fall-back is wrong on its own terms.** Mutation #71
(`scripts/mutations/recall-llm.json`) pins this behaviour with the rationale *"one corrupt byte
suppresses a match"*. Under this rc contract a refusal is not suppression — that is the distinction
the contract exists to draw. The alternative is rc 3 with a named sentence, which the hook forwards.

**What would prove this finding wrong:** a `--fire` against an unreadable entry file that either
refuses, or prints the cached wording labelled as cached rather than under a bare `FIRES-WHEN:`.

---

### H5 · The M4 dedupe covers 1 of 8 output paths — the two most reachable stale states re-emit a four-line block into the model's context on **every** invocation, including the rc 5 path this fold created

**What is wrong.** Round 1's M4 found that the useful message was rate-limited while the nag was not,
and the fix added `nag_once` at exactly one branch — the *missing cache file* branch,
`recall-llm.py:934`. Every other non-OK output path is un-deduped:

| path | site | deduped? |
|---|---|---|
| rc 0 match | `:970-981` (`.last-surfaced`) | ✅ |
| rc 3 cache file absent | `:934` (`.last-nagged`) | ✅ |
| rc 3 **fingerprint stale** | `:939-941` | ✗ |
| rc 3 step not in cache | `:942` via `lookup` | ✗ |
| rc 3 entry renamed away | `:944-949` | ✗ |
| rc 3 entry lost its trigger | `:960-963` | ✗ |
| rc 3 cache unreadable/unparseable | `:938` | ✗ |
| rc 5 **unreadable plan** | `:922` | ✗ |

**Measured through the real hook**, three consecutive invocations against one stale-fingerprint
state — the state produced by editing any `Doing:` line after arming:

```
--- call 1 --- {"hookSpecificOutput": {… "additionalContext": "recall-llm: the recall cache for
this plan is absent or stale … Run `python3 scripts/recall-llm.py --arm` … (one model call, ~16s,
covers every step). Detail: STALE CACHE: armed against sha256:… the plan on disk is sha256:… "}}
--- call 2 --- (byte-identical)
--- call 3 --- (byte-identical)
```

Same for rc 5: the unreadable-plan payload is emitted on every invocation, and the fold's own note at
`recall-llm.py:83-86` says **87 committed plans** are in that shape, so arming any one of them
produces a permanently repeating block.

**Why High.** `should_surface`'s docstring (`recall-llm.py:723-733`) states the cost model this
design is built on — *"a hook that printed on every call would be trained away within an hour"*,
measured at 275 firings a session. Two of the states a reader will actually hit do precisely that,
into the model's context rather than the transcript, and one of them was introduced by this fold.

**What would prove this finding wrong:** three consecutive `--fire` calls against an unchanged stale
state producing output once.

---

## MEDIUM

### M1 · `EXPECTED_MUTATIONS`' new comment says **74** beside the **80** it registers — round 1's M1, inside the comment that announces the rule against it

`scripts/check-plan-code.py:1330-1342` carries the fix for round-1 M1, and its own words are:
*"A count in prose has no owner and drifts from the literal below it … So the figure is NOT restated
here."* The next line restates it: *"⟳ 2026-09-30, review round 1 fold: 53 → 74 across B1, H1, H2, H3
and the model-call isolation."* The literal two lines down is `"scripts/recall-llm.py": 80`, and
`json.load(open('scripts/mutations/recall-llm.json'))` is **80** entries.

Nothing can catch this: the suite pins the literal, and the prose beside it is unowned — which is the
finding's own thesis, demonstrated on itself.

**Proves it wrong:** the manifest containing 74 entries.

---

### M2 · `bootstrap-memory.sh` derives the repo path with `pwd` (logical) while the guard and the matcher use `resolve()` (physical) — so under any symlinked path the bootstrap SUCCEEDS, the matcher reads ZERO entries, and the guard reports it as an rc-0 ADVISORY

`bootstrap-memory.sh:23` is `REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"` and feeds that
into `SLUG` at `:25`. `check-memory-link.py:30` is `ROOT = pathlib.Path(__file__).resolve()…`, and
`recall-llm.py:334` is `root = (cwd or ROOT).resolve()`. The `re.sub` rule agrees across all three
copies; the **path fed into it** does not.

**Measured.** A repo at `…/pd/real` reached through a symlink `…/pd/alias`:

```
bash  REPO (pwd)        -> …/pd/alias
py    ROOT (resolve)    -> …/pd/real

$ bash …/pd/alias/scripts/bootstrap-memory.sh
linked: …/projects/…-pd-alias/memory -> …/pd/alias/docs/memory
entries now visible to the harness: 1

$ python3 …/pd/alias/scripts/check-memory-link.py
WARNING: the harness memory path does not exist, so the assistant reads NO corpus here.
Run `./scripts/bootstrap-memory.sh`. (Advisory: this is the normal state of a fresh clone.)
GUARD_RC=0
```

The bootstrap reports success, the guard tells you to run the command you just ran, exits **0**, and
`recall-llm` reads a corpus of zero entries — which is the one failure `check-memory-link.py`'s own
docstring says it exists to catch (*"every recall silently reads a corpus of zero entries"*). The
guard's third implementation is the one that WRITES the link, and its docstring at `check-memory-link.py:37-42` concedes
the shell copy is unmitigated while claiming the mitigation covers "the two Python copies".

Reachable wherever a checkout, a worktree, or `$HOME` sits under a symlink — `/tmp` on macOS is one.

**Proves it wrong:** `pwd` and `Path(__file__).resolve()` agreeing for every path a clone can sit at.

---

### M3 · The CI step "Memory corpus link" cannot fail on a runner — a green check over a subject that does not exist there

`.github/workflows/ci.yml:227-228` (`run:` on `:228`) runs `check-memory-link.py`, and the comment above it at `:219-226`
states the reason it will pass: *"On a CI runner the link is legitimately absent, which the guard
reports as an advisory rc=0."* `main()` at `check-memory-link.py:73-79` returns `MISCONFIGURED` only
when the link **exists** and is wrong. Nothing in CI creates it (no `bootstrap-memory.sh` step; grep
over `.github/workflows/` finds none), so the step reports ✅ on every PR while measuring nothing.

This is the repo's own rule — *"'Cannot run' is a FAILURE, never a pass"* — inverted: the step
reports a pass precisely because it cannot reach its subject. The `--self-test` step beside it
(`ci.yml:230-231`) is the one doing real work.

**Proves it wrong:** a CI run where this step fails, or a step in `ci.yml` that creates the link
first.

---

### M4 · `decode_verdict`'s rc is dead at its only production call site, and its `err is None` branch is unreachable from production — a branch with a case and a mutation that no caller can reach

`read_or_refuse:324` is the only non-test caller and it takes `decode_verdict(...)[1]` — the message
only. So:

* the rc half is never read in production, while the function returns `CANNOT_RUN` unconditionally
  (`:306`) even when its `label` argument makes the sentence say `STALE CACHE`. The two halves of one
  return value contradict each other, and nothing can notice because one of them is dead;
* the `if err is None: return OK, ""` guard at `:299-300` sits inside the only call path, which is
  `except (UnicodeDecodeError, OSError) as exc:` — so `err` is **never** `None` in production. It has
  a case (`:1464`) and a mutation (`recall-llm.json` #60).

This file states the rule it is breaking, twelve functions earlier: *"A branch no input can reach
reads as depth and cannot be falsified by any case, which is worse than not having it"*
(`recall-llm.py:529-532`, on the deliberately-absent `isinstance(obj, dict)` check).

**Proves it wrong:** a production call site that passes `err=None`, or one that reads
`decode_verdict(...)[0]`.

---

### M5 · `read_or_refuse`'s label is decided by `refusal is StaleCache`, so the class→rc rule and the class→label rule live in two places and a third class gets a sentence contradicting its code

`recall-llm.py:320` is `label = "STALE CACHE" if refusal is StaleCache else "CANNOT RUN"`. The rc
comes from the class (`Refusal.rc`, `:128-155`); the label comes from an `is` test against one named
class. They agree today only because exactly two classes are passed (`:344`, `:844`, `:851`, `:938`).

Two ways they part, both by code reading rather than measurement — no caller does either today:

* `read_or_refuse(p, "plan file", UnreadablePlan)` — the obvious fix for B1 above — would produce
  rc 5 under a sentence reading `CANNOT RUN:`, which is the exact defect the parameter was added to
  remove (`:317-319`);
* any subclass of `StaleCache` fails `is` and gets `CANNOT RUN` at rc 3.

The one-place form is a class attribute (`Refusal.label = "CANNOT RUN"`, `StaleCache.label = "STALE
CACHE"`), which makes the rc and the sentence derive from the same fact.

**Proves it wrong:** a demonstration that no third refusal class can ever be passed here.

---

## LOW

**L1 · `LIVE_UNREADABLE` is re-overloaded at the call site, one line after being split.**
`recall-llm.py:959` is `status, live_trigger = live_trigger_for(entry, d) if entry else
(LIVE_UNREADABLE, None)` — so the sentinel now also means "there is no entry at all", a third
meaning, in the caller of the function round 2 #1 split precisely to stop one value meaning two
things. Currently harmless (`fire_output(None, …)` returns `""` at `:760-761`), but the guard the
fold cites for this class, `check-sentinel-meanings.py`, reads columns and cannot see it.

**L2 · `surface-recall.sh` now owns the rc→context rule and has no self-test and no mutation entry.**
H4's fix moved the forwarding decision out of a string literal and into the rc arms at
`surface-recall.sh:59-72`, so the hook is the sole owner of which outcomes reach the model.
Measured: across all mutation manifests there are **59 distinct `"file"` values and not one is under
`.claude/hooks/`**; of 13 hooks only `block-default-branch-push.sh` carries a `--self-test`. Deleting
the `5)` arm leaves `--self-test`, `--mutate .` and every local guard green. The file says this about
itself at `:7-17` for the *caller* requirement; it does not say it about the rc arms it gained.

**L3 · The hook does not verify the command it fired on.** `.claude/settings.json:56` carries
`"if": "Bash(*begin-plan.py*)"`, and `surface-recall.sh` reads nothing from stdin — grep for
`tool_input`/`jq` finds nothing. Both pre-existing `if` hooks in this file re-check the command
themselves (`block-default-branch-push.sh:96` parses `.tool_input.command` from the hook JSON). If
the `if` clause is ever ignored, the matcher runs on every Bash call; the per-step dedupe bounds the
*match* output but **not** the un-deduped paths in H5, which would then repeat ~275 times a session
instead of ~15.

**L4 · Mutation #71's stated consequence is not what its edit does.** Its name says *"one corrupt
byte suppresses a match"*, but the replacement is `raise` inside the `except`, re-raising an
`OSError` that `main` does not catch — an rc-1 traceback, not suppression. Same shape as the H1(e)
entry Codex caught in round 2 #4, one degree milder: the case still kills it for a related reason.

**L5 · `plan_verdict`, `corpus_verdict` and `cache_verdict` return an rc no production caller reads.**
`:880`, `:922` raise `UnreadablePlan` regardless; `:862` raises `Refusal`; `:941` raises `StaleCache`.
Only `cached_entry_verdict` (`:946-949`) branches on its rc. So those functions' rc values are
pinned by cases and mutations while being inert in the shipped path — the same shape as M4, one
notch weaker because the constants happen to agree.

**L6 · The corpus and the questions file are now live-written into the tracked working tree.**
`docs/memory/` is symlinked to the harness's live memory path (`bootstrap-memory.sh:45`) and
`docs/explainers/questions.md` is written by the server, so an ordinary session now dirties tracked
files while unrelated work is in flight. Two of this repo's own rules collide with that: *stage
explicit paths, a live agent's file is not static*, and `check-dashboard-entry.py`'s rule that a
branch changing tracked files must record an entry. Nothing in the branch says how to hold both.

**L7 · `regen-pages.sh:22,25` writes generator logs to a fixed `/tmp/regen-<g>.log`.** Shared,
predictable, outside any scratch directory, and clobbered between concurrent runs — which this repo
does have, since `dispatching-parallel-agents` is in routine use.

---

## Areas I could NOT establish

Every hypothesis I formed and failed to confirm, including the ones that turned out to be wrong.

1. **`parse_trigger` returning an empty string rather than `None`** (the brief's question 1). It
   cannot: `recall-llm.py:281` ends `…split("—", 1)[0].strip() or None`, so an empty trigger is
   `None` and the entry becomes `LIVE_NO_TRIGGER`. Probed with a `description:` of exactly
   `"FIRES-WHEN: — commentary"`; the status was `no-trigger`, not `ok` with `""`. **No finding.**

2. **`UnreadablePlan` reaching `read_or_refuse`.** I looked for a live caller and there is none; M5
   is written as a latent defect for that reason, and is a code-reading claim, not a measurement.

3. **The hook's rc-0 arm forwarding stray stderr.** `surface-recall.sh:45` merges stderr into `OUT`
   and the rc-0 arm forwards it verbatim with no framing, so any interpreter warning at rc 0 would
   arrive as model context that looks like a recall. I could not construct a reachable rc-0-with-
   stderr state from `do_fire` itself, so I could not raise this above speculation.

4. **`--arm` under a concurrent second `--arm`.** `do_arm:903-905` writes to a fixed
   `w.json.partial` before `replace`, so two arms of the same plan race on that name. I did not build
   the race, and with a 16.1s paid call per arm I could not measure it without spending; the
   per-plan-stem naming makes the collision narrow. **Unestablished, not dismissed.**

5. **Whether `--arm` in a real session is contaminated by the repo's hooks.** I did not call the
   model (per the brief). `outside_repo` has four cases and two mutations and the sandbox wiring at
   `:816-823` reads correctly, but the property asserted is "the cwd is outside the tree", not "no
   hook can fire" — which the docstring at `:769-772` already concedes. Same gap Codex recorded.

6. **A self-test case that cannot fail** (the brief's question 4). I read the world-building cases at
   `:1660-1888` and could not find one. `_fire_with_an_unwritable_marker` (`:1728-1768`) genuinely
   exercises the ordering — it is killed by mutation #59 — and `_fire_on_a_trigger_less_entry` is
   killed by #78. The vacuity I did find is one layer along: **cases over functions whose result the
   production path discards** (M4, L5) rather than cases that cannot fail. ⚠ I did not verify all 171
   individually; I traced the 12 added by the round-2 fold and relied on the sweep for the rest.

7. **The nine orphaned-and-repaired anchors.** I confirmed the manifest has 80 entries, no duplicate
   names and no duplicate edit anchors, and that the retargeted entries (#51, #59, #62, #71) name
   their retarget in the entry itself. I did **not** independently verify that each retargeted anchor
   still binds the clause its name is about — only that the sweep resolves and kills it, which is a
   weaker claim (`a-mutation-anchor-is-unbound-by-any-edit-nearby`).

8. **Guards needing Postgres, Docker, a PR or a test run.** Listed in full in the preamble above.
   They were **NOT RUN**, so their status on this branch is unknown, not green — `check-merge-ready.py`
   in particular covers PR-only gates that no local run can reach.

---

## Mutation sweep

`python3 scripts/check-plan-code.py --mutate .`, output redirected to a file and the exit code read
from the file, never from `$?` after a pipe:

```
$ python3 scripts/check-plan-code.py --mutate . > sweep.txt 2>&1; echo "RC=$?" >> sweep.txt
OK — delivered scripts mutated: 55 file(s), 1122 mutation(s), 1122 killed,
     1122 attributed to the case each names, 0 survivor(s)
RC=0
```

`EXPECTED_MUTATIONS` declares `scripts/recall-llm.py: 80` and `scripts/check-memory-link.py: 8`
(`check-plan-code.py:1343-1344`); the manifests hold exactly 80 and 8 entries, counted by
`json.load`. The declared sum pinned at `check-plan-code.py:3768` is 1122.

⚠ **The sweep's green is bounded, and H1 is the demonstration.** It stages `HARNESS_TREE` and runs
each guard's `--self-test`, not its entry point — so `check-fixture-variation.py` was green in the
sweep and red against this repository at the same moment. A perfect sweep score is not a statement
about the tree.

---

## Round-2 bookkeeping

* **Codex half:** `docs/reviews/codex/recall-llm-r2-codex.md`, 2 High + 2 Medium, all four folded in
  `a4a8c0b2`. I re-measured all four: #1 (`live_trigger_for` statuses) is fixed for
  `LIVE_NO_TRIGGER` and **not** for `LIVE_UNREADABLE` → H4. #2 (undecodable cache → rc 3) is fixed
  for the cache and **not** for the plan or sentinel → B1. #3 (`UNREADABLE_PLAN` in every mode) is
  fixed — `--fire` and `--print-prompt` both return 5, measured. #4 (the H1(e) mutation) is fixed —
  the entry now reorders rather than deletes, and a read-only-cache-directory case drives it.
* **This half:** `docs/reviews/claude/recall-llm-r2-claude.md` (this file). No `REVIEW GAP`.
* **Convergence:** not reached. Two of the four round-2 fixes are fixed at one call site and open at
  another, which is the third consecutive round in which a repair closed the instance and left the
  class — the pattern this branch has now paid for five times.
