# Claude adversarial review — banner guard inverse (#95), round 2

**Subject:** `docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md` (v2, 2026-09-04)
**Reviewer:** Claude half, independent. The round-1 files were read as instructed; the Codex half of
round 2 was not read and does not exist at review time.

**Method.** Every quoted line was re-read in the file it names. Four claims were **executed** rather
than reasoned about: (a) v2's own falsifier table was run against today's `decide()`; (b) the §3.5
boundary rule was implemented and run over the 30 most recent transcripts under
`~/.claude/projects/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/`;
(c) the §3.7 adjudication was tested by enumerating every `Edit`/`Write` `file_path` under the repo's
`.claude/` across all **508** transcripts; (d) the §3.3 import posture was run against a missing file.

**Count: 1 Blocking, 4 High, 7 Medium, 3 Low.**

---

## BLOCKING

### B1 — The reorder makes the new warning *reachable* and simultaneously routes its message to the wrong reader in the exact state it targets. v1's defect was moved one layer out, not removed.

**Claim.** §3.1 makes `check-banner-armed.py` execute while a plan is armed with unticked steps. But
that is also precisely the state in which `check-plan-progress.py` returns `BLOCK`, so the hook exits
**2** — and by this repo's own stated contract, exit 2's stderr goes to *Claude*, not to the human.
§1 names the human as the reader whose absence is the whole defect ("**the human, not the harness,
noticed**"). After §3.1 the warning fires and the human still does not see it.

**Evidence.** The contract is stated twice in the file being changed:

```bash
# .claude/hooks/block-idle-stop.sh:15
# Contract: exit 2 blocks the stop and feeds stderr back to Claude; exit 0 allows it.

# .claude/hooks/block-idle-stop.sh:48-49
# WARN-ONLY BY DECISION (user, 2026-09-04). Exit 1 is Claude Code's non-blocking error: stderr is
# shown to the user, the stop proceeds. Exit 2 would block, and is deliberately NOT used here.
```

§3.1's own arithmetic preserves that:

```bash
[[ "$PLAN_RC"   != "0" ]] && exit 2      # blocking still wins
[[ "$BANNER_RC" != "0" || "$CI_RC" != "0" ]] && exit 1
```

Now enumerate where the new predicate fires. It requires `armed ∧ unticked > 0` (§3.4). On the same
on-disk state `check-plan-progress.decide()` returns `BLOCK` at `:133` unless one of exactly two
escapes applies — `paused` (`:100-101`, and §3.2 sets `armed = False` there, so the new branch is
silent) or the anti-nag continuation (`:130-131`). So:

| state the new branch can fire in | `PLAN_RC` | hook exit | who reads the warning |
|---|---|---|---|
| ordinary armed stop, unticked > 0, edited, no banner — **the measured failure of §1** | 2 | **2** | Claude |
| anti-nag continuation (`stop_hook_active` ∧ count did not fall) | 0 | 1 | the human |
| `paused` | 0 | — | §3.2 silences it |

**So the human sees the new warning only on an anti-nag continuation** — one of the two states v1
was rejected for being confined to. v1 fired *only* in the wrong states; v2 fires in the right state
and delivers to the wrong reader there.

Corroborating measurement, and it is a falsifiable prediction: across all 508 transcripts there are
**10** `Stop hook feedback` user records (all exit-2 blocks from this hook), and **0** of them contain
either observer's message text — consistent with the observers never having run on the blocking path.
After §3.1 they will, and their output will land inside that same block-feedback payload.

Second-order: the message the human is not shown says, at `check-banner-armed.py:160`,
`"Nothing is blocked"` — on a stop that is blocked.

**Smallest fix.** Decide which reader the new warning is for, then make the hook say so. Two shapes,
either sufficient: (i) when `PLAN_RC != 0`, suppress the new-class banner warning entirely and let
the blocking guard own that turn — the block message already tells the assistant to keep going; or
(ii) have `check-plan-progress` emit the banner observation as part of *its* block message, so there
is one message on the blocked path rather than two aimed at different audiences. What is not
defensible is emitting a human-addressed, "Nothing is blocked" warning on a channel the spec's own
citation says goes to Claude. Whichever is chosen, F7 must assert the *exit code and destination*,
not merely that the script was invoked.

---

## HIGH

### H2 — §3.1's bash names `$ROOT`, which the hook does not define. Transcribed as written it exits 2 on every stop and the anti-nag cannot clear it.

**Claim.** The snippet is the spec's prescription for the highest-risk change in the document, and it
does not run.

**Evidence.** The hook defines `REPO_ROOT`, never `ROOT`:

```bash
# .claude/hooks/block-idle-stop.sh:23
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
```

The spec uses both, in the same document — `$REPO_ROOT` at `:44` (quoting the current file) and
`$ROOT` at `:92`, `:93`, `:94` (prescribing the replacement). The script has no `set -u`, so `$ROOT`
expands to empty and the invocation becomes `python3 /scripts/check-plan-progress.py`. Measured:

```
$ python3 /nonexistent/scripts/check-plan-progress.py --decide ; echo rc=$?
can't open file ... [Errno 2] No such file or directory
rc=2
```

`PLAN_RC=2` → `exit 2` on **every** stop. And it cannot self-clear: `run_decide` never executes, so
`.claude/executing-plan.state` is never written, so the anti-nag at `:130-131` has no `prev_unticked`
to relax against. That is the wedged session `block-idle-stop.sh:36-38` was explicitly written to
avoid ("*A hook that can trap a session gets disabled, and a disabled hook protects nothing*").

**Smallest fix.** `$ROOT` → `$REPO_ROOT` in all three lines of §3.1.

### H3 — §3.5 over-widens by half. MEASURED: it removes 72 of 142 turn boundaries, and 52 of those 72 begin a genuinely new turn.

**Claim.** "Skip a boundary when `isMeta` is true or `promptSource` is `system`/`sdk`" is not the
repair §3.5 describes. Two of the three record classes it silences are documented turn *starts*.

**Evidence.** I implemented both rules and ran them over the 30 most recent transcripts:

```
OLD rule: 142 windows, 27 contain a banner
NEW rule:  70 windows, 22 contain a banner
boundaries the new rule stops treating as turn starts: 72
```

Classified by what those 72 records actually are:

```
  25  promptSource="sdk"     — the agent's own task prompt ("Review this change for security…")
  27  <task-notification>    — 25 promptSource="system", 2 isMeta=true
   7  skill injection        (isMeta=true)
   7  Stop hook feedback     (isMeta=true, 7/7 — the field name checks out)
   5  <local-command-caveat> (isMeta=true)
   1  other                  (isMeta=true)
```

Only the bottom 20 are same-turn injections. The other 52 are new turns:

- **`<task-notification>` (27).** `check-plan-progress.py:28-36` says so in its own words:
  *"A turn beginning from a background-task notification is a **FRESH turn** with the flag false"* —
  the measured basis of backlog #94. §3.5 declares that record a non-boundary.
- **`promptSource:"sdk"` (25).** These are the *only* real boundary in a subagent session; the
  sampled bodies are the dispatch prompt itself. Skipping them means such a window never resets.

Two consequences, neither stated:

1. **The new predicate under-fires.** A bannerless turn is excused by a banner emitted in a *previous*
   turn that a task-notification separated from it.
2. **The existing banner-without-plan rule over-fires.** A stale `STEP 2 of 5` now survives across a
   task-notification into a turn that announced nothing, with nothing armed → WARN. §3.5's
   "*For text alone this only under-fires*" is true of today's bug and **false of the fix**: widening
   a window can only add banners, and adding banners can only add firings of a rule keyed on their
   presence.

§3.5 is right that the `Stop hook feedback` boundary must be skipped — that one is a genuine
continuation of the same turn. It generalised from that one case to a rule three times its size.

**Smallest fix.** Skip only what is a continuation of the current turn: `isMeta:true`. Leave
`promptSource:"system"` and `"sdk"` as boundaries, or name each with the record class it silences and
say why a new turn should inherit the previous turn's banners. If `<task-notification>` is genuinely
wanted as a non-boundary, that contradicts `check-plan-progress.py:28-36` and needs to be argued, not
absorbed.

### H4 — F4 and F5 are vacuous. EXECUTED. v2 repeats v1's central error inside the table that claims to have fixed it.

**Claim.** §4's first table is headed *"Discriminating — these FAIL against today's code"*. Two of the
seven do not.

**Evidence.** I imported `check-banner-armed.py` and called today's `decide()` with each row's inputs:

```
 F1  expect WARN        today -> QUIET        discriminates
 F2  expect CANNOT RUN  today -> QUIET        discriminates
 F3  expect CANNOT RUN  today -> QUIET        discriminates
 F4  expect QUIET       today -> QUIET        VACUOUS — passes unfixed
 F5  expect QUIET       today -> QUIET        VACUOUS — passes unfixed
```

Both for the reason §4's own opening paragraph names: `:149` returns `QUIET` for any banner-less turn,
before `armed` is consulted. F4 discriminates §3.2 only *given* §3.4 — it falsifies a hypothetical
intermediate build, not today's code, which is what the header asserts. F5's "Expected: QUIET" is
today's answer; the assertion that would discriminate §3.5 is on the **window contents**
(`highest_banner(window_of(fixture)) == (2, 4)`), not on the verdict.

R1–R4 are vacuous too and that is correct — they are labelled regression guards. The defect is
confined to the table that claims otherwise.

**Smallest fix.** Move F4 and F5 to the regression table with their mutations named (`_armed()` stops
reading `paused`; the boundary rule reverts), and restate F5 as an assertion on the window. Then the
discriminating table is F1, F2, F3, F6, F7 — and §4's claim about itself is true.

### H5 — F7 has no harness, and running it as written destroys live state.

**Claim.** F7 is the falsifier v2 rests its Blocking fix on ("*F7 is the one v1 could not have had*").
It is currently aspirational: nothing in this repo executes a shell hook, and the hook cannot be
pointed at a fixture.

**Evidence (negative claim, established by search).** `grep -rn` for hook execution across
`scripts/ tests/ .github/` returns only prose mentions in `check-plan-progress.py:12` and
`gen-dashboard.py:3251,3466`. `ci.yml` references this guard exactly once, and it is a pure self-test:

```yaml
# .github/workflows/ci.yml:195-196
      - name: check-banner-armed self-test
        run: python3 scripts/check-banner-armed.py --self-test
```

Running `block-idle-stop.sh` for real, from a test, would:

- **delete the developer's live sentinel** — `check-plan-progress.run_decide:180-182` calls
  `SENTINEL.unlink()` / `STATE.unlink()` whenever the armed plan happens to be fully ticked;
- **write `.claude/executing-plan.state`** (`:184`), corrupting the anti-nag of the real session;
- **make a live `gh pr view` call** (`check-ci-watched.py:160-161`) — measured at 0.5–0.7 s, 25 s
  timeout;
- **append to the real `.claude/banner-warnings.log`** (`check-banner-armed.py:213-214`), polluting
  the very dataset §3.8 exists to produce.

And it cannot be redirected: `REPO_ROOT` is derived from `${BASH_SOURCE[0]}` (`:23`), and all three
scripts derive their own `ROOT` from `__file__`. There is no `--root` seam. This repo has a measured
memory on exactly this shape — *an instrument that edits the repo corrupts its peers* — and a measured
one on the fix, the `HOME` redirect of PR #181.

**Smallest fix.** Say where F7 lives and how it is isolated. The cheapest shape that is still a hook
test: copy `.claude/hooks/` + `scripts/` into a temp tree, run the hook there with `HOME` redirected
and a stub `gh` earlier on `PATH`, and assert on the exit code and on which scripts were invoked. If
that is judged too much, say F7 is deferred and stop citing it as the fix for Cl B1 in §8 — an
unrunnable falsifier in the disposition column is the "cannot run reported as a pass" shape.

---

## MEDIUM

### M1 — §3.4's hoist has no independent firing set: every input that reaches it already makes the blocking guard emit the same diagnosis, more loudly.

**Claim.** The hoist is presented as making blindness unconditional. In production it is a second copy
of a message `check-plan-progress` already prints.

**Evidence.** The new branch fires iff `armed ∧ steps is None`, i.e. the sentinel names a plan and
that plan is unreadable or parses to zero checkboxes (§3.4's own comment). On the same on-disk state:

```python
# check-plan-progress.py:105-110   plan_text is None -> BLOCK "CANNOT RUN: … does not exist"
# check-plan-progress.py:113-118   total == 0        -> BLOCK "CANNOT RUN: parsed ZERO step checkboxes"
```

There is no path where one fires and the other does not: `paused` sets `armed = False` under §3.2, a
missing sentinel sets `armed = False`, and both `unticked == 0` and the anti-nag relaxation are
reached only *after* `total > 0`. So `PLAN_RC = 2` in 100% of the hoist's firings, the hook exits 2
(B1), and the human sees neither. F2 and F3 therefore test a branch with no independent production
coverage.

This is the shape `scripts/check-vocabulary-collisions.py` exists to catch — one concern, two
mechanisms. It may still be worth keeping for `decide()`'s internal honesty, but the spec should say
that is what it is, rather than presenting it as closing a blindness gap.

### M2 — §3.8 is not a widening, and the part that actually needs specifying is left blank.

**Claim.** The log already has a reason column; what the new class lacks is a value for the *banner*
column, and the spec supplies none.

**Evidence.**

```python
# check-banner-armed.py:173-175
def log_line(step: int, total: int, when: str, session: str) -> str:
    return f"{when}\t{session or '-'}\tSTEP {step} of {total}\tunarmed\n"
```

Column 4 is already the reason, hardcoded. Column 3 is `STEP {step} of {total}` — and the new class
is *defined* by having no banner. §3.8 says "widen `log_line` with a reason column" and never says
what column 3 holds when there is no banner, nor what `step`/`total` become in a signature typed
`int, int`. That was round 1's B3 verbatim ("*there is no shape for a banner-less record, and the
spec never proposes one*"); §8 marks it **Fixed** and the shape is still missing.

**And there is exactly one reader, which the spec did not find.** Negative claim, established by
`grep -rn 'banner-warnings'` over the whole repo: no script parses the file. The only positional
reader is the guard's own self-test:

```python
# check-banner-armed.py:311-313
    case("the log line is tab-separated and states the banner and the state",
         log_line(2, 5, "2026-09-04T07:00:00-07:00", "sess").split("\t")[2:]
         == ["STEP 2 of 5", "unarmed\n"])
```

§3.8 says "any existing reader must be checked" and §6's bookkeeping list — which does remember the
declared self-test count — does not mention that this case must change.

### M3 — The reorder makes `check-ci-watched` run on every blocked stop, and makes the new warning log once per *stop* rather than once per incident.

**Claim.** §3.1 frames "the warnings now print in every case rather than being skipped" as pure gain.
On a continuation chain it is repetition.

**Evidence.** A blocked stop is followed by a continuation, which ends in another stop. Backlog #94,
recorded in `check-plan-progress.py:28-36`, measured **three** blocks in one session where the
anti-nag never engaged. Each of those stops now additionally runs:

- `check-ci-watched.run_decide` — on a non-default branch with an upstream this is a live
  `gh pr view --json statusCheckRollup` (`:160-161`), measured at 0.49/0.53/0.67 s here, 25 s timeout.
  The same "CI IS RUNNING AND NOTHING IS WATCHING" warning repeats on each stop of the chain with no
  per-turn dedupe; its only acknowledgement is the per-SHA sentinel, and HEAD does not move mid-chain.
- `check-banner-armed.run_decide` — which, once §3.8 drops the `if banner:` gate, **appends a log line
  every time**. §3.8's justification is that the log turns "does it false-alarm?" into a number. After
  §3.1 that number counts *stops*, not incidents, and a 3-block chain over one bannerless turn writes
  3 lines. The denominator §3.8 is built to measure is inflated by the fix in §3.1.

**Smallest fix.** Either state that the log's unit is a stop (and say so in the column grammar of
M2), or skip the observers when `stop_hook_active` is set — the hook already extracts that flag at
`:25-34` and already passes it to `check-plan-progress`.

### M4 — The reorder silently flips the existing rule's verdict on the plan-completion stop; §3.1 presents it as position-only.

**Claim.** "*They cannot block, so their position is free*" is true of the exit code and false of the
verdict, because the sentinel is deleted between the two positions.

**Evidence.** §3.1's own ⚠ establishes the mechanism — `run_decide:180-182` unlinks the sentinel when
`unticked == 0`. Today the banner guard runs *after* that unlink and sees `armed = False`; after the
reorder it runs before and sees `armed = True`. So for a turn whose highest banner is `STEP 4 of 5`
on the stop where the fifth box gets ticked (e.g. `--tick` without a final `--banner`):

- today: `armed = False`, `step < total` → **WARN** (`check-banner-armed.py:157`)
- after §3.1: `armed = True` → **QUIET** (`:154-155`)

The new answer is arguably the better one. The defect is that §3.1 claims the reorder changes only
*when* the observers run, and this is a change to *what they conclude* on a state that occurs at the
end of every completed plan.

### M5 — §3.6 draws opposite conclusions from identical evidence, and the stronger one is refuted from inside the same corpus.

**Claim.** `MultiEdit` is rejected because it was measured ×0; `NotebookEdit` is kept despite being
measured ×0 in the same sentence.

**Evidence.** Full-corpus recount over all 508 transcripts (v2 cites the r1 subsample):

```
Edit  2758   key set ('file_path','new_string','old_string','replace_all')  — 2758/2758
Write  813   ('content','file_path') 812   ('content','description','file_path') 1
NotebookEdit 0    MultiEdit 0
```

So §3.6's shape claims hold at 50× the sample (with one `Write` variant it did not see — harmless,
`file_path` is present). But the inference does not: **`NotebookEdit` exists in this runtime** — it is
in the current session's tool roster — and it is also ×0. A ×0 count is evidence of non-*use*, not of
non-*existence*, and this document uses it as both in the same paragraph. This project has a memory
for exactly this — *a ZERO count is the dangerous shape*.

**Smallest fix.** Reject `MultiEdit` on the evidence that exists ("never used in 508 transcripts; if
the runtime ever exposes it, this guard is blind to it") and put it in §7 with the other stated blind
spots, rather than asserting it does not exist.

### M6 — The pure/shell seam is not specified, and R3 is not expressible against the interface §3.6 states.

**Claim.** Three names are in play for two functions, and the tool-use extractor and path predicate
are unnamed.

**Evidence.** §3.5 mandates a change to **`records_since_last_user`** — a function that does not exist;
the file has `assistant_texts_since_last_user` (`:73`), returning `list[str]`. §3.4's snippet still
calls `highest_banner(texts)`. §3.6 declares the new inputs as `steps: tuple|None` and
`edited: bool`. If `edited` arrives at `decide()` as a bool, then:

- **R3** ("armed · unticked > 0 · edit path **outside** the repo → QUIET, catches *a missing path
  scope*") cannot exercise the path scope at all — it is `decide(..., edited=False)`, identical to R1.
  The mutation it names lives in a helper the spec never names.
- §3.7's `Path(p).resolve().is_relative_to(ROOT)` and the `.git/` exclusion have no owner, no
  signature, and no falsifier.

Round 1's Codex half asked for exactly this ("*write the path predicate as a separate pure helper with
self-tests*"); §8 marks it **Fixed, §3.7**, and §3.7 specifies the rule but still not the seam.

### M7 — §3.3's "catch `ImportError`" does not catch the failure it is written for.

**Claim.** The rename/deletion case raises `FileNotFoundError`, which is an `OSError`, not an
`ImportError`.

**Evidence.** `begin-plan.py:98-111` is the cited precedent, and it raises `ImportError` only for
*missing names* (`:107-110`). For a missing *file*, `spec_from_file_location` succeeds and
`exec_module` raises. Measured:

```
spec: ModuleSpec(name='_x', loader=<SourceFileLoader>, origin='/tmp/definitely-not-here-xyz.py')
NOT an ImportError -> FileNotFoundError: [Errno 2] No such file or directory
is OSError: True   is ImportError: False
```

So §3.3's stated posture covers "someone renamed `count_steps`" and misses "someone renamed or moved
`check-plan-progress.py`" — a traceback out of a Stop hook, which is the outcome §3.3 exists to
prevent. **Smallest fix:** `except (ImportError, OSError)`.

---

## LOW

**L1 — §5's citation is two lines short, and §8 claims citation defects were "Fixed throughout".**
§5 cites `check-ci-watched.py:93-94` for the per-SHA acknowledgement. Those lines are
`if not pending: / return QUIET, ""`; the acknowledgement is `:95-96`. The error is inherited verbatim
from round 1's M4, i.e. it was carried across the fold without re-verification — the one thing §8's
last row asserts did not happen.

**L2 — §5 calls `check-plan-progress` an observer, contradicting §3.1.** "*none of the **three**
Stop-hook observers*" — §3.1 correctly calls only two of the three warn-only observers; the third is
the blocking guard the whole document is about. The underlying claim is **verified**: `scripts/mutations/`
holds seven manifests and none is for the three Stop-hook scripts.

**L3 — one round-1 finding is neither fixed nor rowed in §8.** The Codex Low ("*measured claims about
transcript tool fields are unsupported in the repo … move the claim into executable fixtures, or cite
the exact transcript paths*") has no row in §8's table, and §3.6 still cites neither a path nor a
fixture. It matters more in v2 than in v1, because §3.6's measurement is now the *sole* basis for
rejecting `MultiEdit` (see M5). The header's arithmetic is otherwise right: 5 Blocking / 7 High /
8 Medium / 6 Low is exactly the round-1 total across both halves.

---

## Claims I verified as CORRECT

Recorded so round 3 does not re-litigate them.

- **§3.7's adjudication survives a real search, and this was the finding I most expected to overturn.**
  Across all 508 transcripts, the complete set of `Edit`/`Write` targets under the repo's `.claude/`
  is: `hooks/block-idle-stop.sh` ×4, `hooks/check-schema-gates.sh` ×2, `hooks/suggest-explainer.sh` ×2,
  `settings.json` ×2, `hooks/block-default-branch-push.sh` ×2, and five more hooks/commands ×1 each.
  **Every one is tracked** (`git check-ignore` returns non-zero for all of them). **Zero** writes to
  `.claude/plans/`, `.claude/executing-plan`, `.claude/ci-watching`, `.claude/banner-warnings.log` or
  `.claude/settings.local.json`. The 12 hits on `.claude/plans/…` in the corpus are under
  `~/.claude/plans/`, i.e. outside `ROOT`. The conclusion holds. One caveat, unverified and offered
  as a residual rather than a finding: the *reason* given ("written by scripts through Python") is not
  what makes it true for `.claude/settings.local.json`, which is gitignored (`.gitignore:62`) and is
  the documented target of a skill that edits files — it has simply never been edited here.
- **Exit-code precedence is genuinely preserved.** Enumerated all combinations: `PLAN_RC ∈ {0, non-0}`
  × `BANNER_RC ∈ {0,1,2}` × `CI_RC ∈ {0,1,2}` maps to exactly the same exit code as today in every
  cell. The trailing-`[[ ]]`-status hazard does not bite either: the explicit `exit 0` at `:98` means
  a false final test cannot leak status 1.
- **§7's subagent claim.** `"isSidechain":true` occurs **0** times across all 508 transcripts;
  all 118,522 occurrences are `false`.
- **§6.1's bookkeeping is accurate.** `check-banner-armed.py --self-test` prints `25/25`, the docstring
  at `:47` declares `# 25 cases`, and `check-selftest-counts.py:88` is literally `"check-banner-armed.py"`.
- **§5's rename argument.** `ci.yml:195-196` references the script by name; `check-selftest-counts`
  pins it. (`check-ci-watched.py` has **no** CI reference — true today and not a v2 defect, but worth
  knowing before §6.5 claims the reorder repairs it.)
- **§2's diagnosis of why v1 was unviable** is correct in every line number I re-read: `:39-41`,
  `:54`, `:55`, `:97-98`, `:100-101`, `:121-125`, `:130-131`, `:180-182`.
- **§1, §3.2, §3.3's quotations** all match: `check-banner-armed.py:149`, `:180-188`;
  `check-plan-progress.py:113-118`; `check-anchors.py:61` is `HEAD_LINES = 10`.
- **§3.5's field names are real.** `isMeta` and `promptSource` both exist; the observed
  `promptSource` values are `typed` (25), `sdk` (21), `system` (8), `queued` (7),
  `suggestion_accepted` (3) plus unset. `Stop hook feedback` records carry `isMeta: true` in 7 of 7 —
  §3.5's premise about *that* record class is exactly right. It is the generalisation that is wrong (H3).

---

## What would change my verdict

B1 is the finding that makes the rest matter, and it has the fold's signature on it: v1 was rejected
for a warning that could not run, and v2's fix produces a warning that runs and is delivered to the
wrong reader in the majority state — the same class, one layer out, introduced by the fix. H3 and H4
are the second signature: the window rule and the falsifier table are both new machinery in v2, and
both are wrong in the direction of looking repaired. A v3 that (i) resolves who reads the warning on a
blocked stop, (ii) narrows §3.5 to `isMeta`, (iii) demotes F4/F5 and restates F5 on the window, and
(iv) either gives F7 a harness or stops citing it as a closed disposition, would be defensible.
Nothing here argues against the goal.

VERDICT: NOT CONVERGED
