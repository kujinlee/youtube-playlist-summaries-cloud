# banner-thread-armed — round 3 — Claude half

Range: `8b871a60..fe08f438` (the fold of round 2). Line numbers refer to `fe08f438`.

**How I tested.** I exported `git archive fe08f438` into a temporary git repo
(`scratchpad/r3c/repo`) with `HOME` redirected. All three self-tests pass there:
`check-banner-armed` 231/231, `gen-work-lines` 48/48, `begin-plan` 120/120. Worktree questions
used real `git worktree add` and `git worktree remove` inside that temp repo. Against the real
repo I ran reads only: `git worktree list`, `scandir`, and `read_plans_noted` imported from the
fold's file. Nothing was written to the real `.claude/`, the worktree or the repo. I did not
run the Stop hook or `begin-plan.py` against the real tree.

## Findings

### F1 — Minor — `scripts/check-banner-armed.py:1329-1362`, docstring `:152`: the thread class still never runs when the journal has no sample, so BLOCK is bypassed on that path

- **Input/state:** the judged turn's banner is `> **Thread:** ⤳ SWITCHED from `dup` → `never-planned-zz``,
  with `THREAD_BLOCK=True`. The session has no journal record for the judged turn. A resumed
  session or a new `session_id` produces this state, as does any earlier stop whose journal write
  failed.
- **What happens (executed):**
  - With no sample, `run_decide` returns **rc=2** and prints only
    `CANNOT RUN: this check judges the PREVIOUS completed turn, and it holds no record of what .claude/executing-plan said…`.
    There is no thread message and no `unknown-thread` log row.
  - The same transcript with a seeded journal returns **rc=4** (BLOCK).
- **Why this matters:** `known_everywhere()` and `decide_thread()` sit inside the
  `else` branch reached only after `sample_for` succeeds and `armed_then is not None`. The
  thread class needs neither value. The fold's docstring says "ALWAYS EVALUATED", and the
  section-5 comment says "ahead of every early return … must not swallow it". On these two paths
  neither statement holds.
- **Is it new?** The placement is unchanged from r1. Only the overclaim is new in this fold.
- **Fix:** compute `t_code…` whenever `judged is not None` and the turn has not already been
  judged, independent of the sample. Add a case where the sample is missing and blocking is on,
  and assert rc 4.

### F2 — Minor — `scripts/gen-work-lines.py:328`, consumed at `check-banner-armed.py` `decide_thread`: one deleted old worktree marks every thread warning as "may be a false alarm"

- **State (real, read-only):** `git worktree list` shows 21 checkouts. One of them is
  `…/62196080-…/scratchpad/wt`, which is `prunable` because its directory is gone.
- **What happens (executed):** `known_everywhere()` against the real repo returns 126 slugs plus
  this note:
  `the checkout …/62196080-…/scratchpad/wt is missing, so its plans were not read`.
  As a result, every thread warning today ends with:
  > `⚠ NOT EVERY CHECKOUT WAS READ, so this may be a false alarm: · the checkout …/62196080…/wt is missing…`
  The page shows the same ⚠ on every rebuild.
- **Why this matters:** a checkout whose directory is gone has no plans left to read. The note
  says "not read" when the truth is "nothing exists". The hedge will sit on every warning until
  someone runs `git worktree prune`. The log the owner counts from is unaffected, because notes
  are not logged. But the warning text that a human reads loses its meaning.
- **Fix:** treat a missing or `prunable` checkout (porcelain marks it) as having no plans.
  Attach the caveat only when git could not answer or a directory exists and cannot be listed.
  The other caveats are real.

### F3 — Minor (needs the owner's awareness) — `scripts/gen-work-lines.py` `plan_dirs` / `read_plans_noted`: removing a worktree silently deletes its lines from the history page

- **Input (executed in the temp repo):**
  1. `git worktree add wt` and arm plan `dup` there with the real `begin-plan.py`.
  2. Run `git worktree remove wt`. It exits rc=0: `.claude/plans/` is gitignored, so git removes
     it without asking.
  3. Call `read_plans_noted(main)`.
- **What happens:** the result is `['dup'] []`. The worktree's plans are gone, with **no note**,
  because the checkout is no longer registered.
- **Why this matters:** the page describes itself as "how did we get here". Under option A, any
  plan armed inside a worktree stays on the page only until that worktree is cleaned up, for
  example by `.claude/commands/clean_gone.md`. Any children of those plans then become "orphans".
  The page's own docstring forbids a page that "silently covers less than it claims". Neither file
  mentions this bound (a grep for `remove`/`prune` finds nothing). The check is not affected: it
  judges one turn later, while the worktree still exists.
- **Fix:** either document the bound where `plan_dirs` is defined and on the page, or have
  `begin-plan` write plans to the main checkout's `.claude/plans/` (`git rev-parse
  --git-common-dir`) so that they outlive the worktree. That choice belongs to the owner, since it
  revisits option A's mechanism. It does not change the goal.

### F4 — Minor — `scripts/gen-work-lines.py:385-410`, `:180`/`:451`: a byte-identical copy of a plan in two checkouts counts as two open lines

- **State (real, read-only):** `chrome-r2-fold.md` exists in the main checkout and in
  `…/154b7568…/wt-chrome`. `diff` shows no difference between the two copies.
- **What happens (executed):** both copies are rendered as roots, and both count toward the
  open-line total:
  ```
  chrome-r2-fold @ /Users/kujinlee/code/…/youtube-playlist-summaries-cloud open 5 6
  chrome-r2-fold @ /Users/kujinlee/.claude-tmp/…/wt-chrome open 5 6
  ```
  This is 1 duplicate in 127 real plans.
- **Why this matters:** "never merged" is right when two different plans share a slug. When the
  file was simply copied, it is the same plan shown twice and counted twice.
- **Fix:** collapse copies whose bytes are identical (compare `plan_fingerprint`/sha256) into one
  row that lists both checkouts. Keep the labelled split only for copies that differ.

### F5 — Minor — `scripts/begin-plan.py:326`/`:360`: the `Line:` row says "not in .claude/plans/" when the slug exists in two checkouts, and making a second copy breaks the first copy's banner after the fact (implementer's stated gap, confirmed)

- **Input (executed, temp repo with a real worktree):**
  1. `begin-plan.py dup …` in the worktree prints `> **Line:** _(no objective recorded)_ `dup``.
  2. `begin-plan.py dup …` in main prints
     `> **Line:** _(this plan is not in .claude/plans/, so no line is recorded for it)_`.
  3. `begin-plan.py --banner` back in the worktree now prints the same false line. The file is in
     its own directory.
  4. A child `kid` armed afterwards shows
     `` `dup @ /Users/kujinlee/.claude-tmp/…/r3c/wt` → `kid` ``, with a full absolute path inside
     the banner.
- **Why this matters:** `work_line` looks up `by[slug]`, but `read_plans` now returns labelled
  slugs. The wording "not in .claude/plans/" is also out of date now that every checkout is read.
- **How likely:** low in practice. Real data has 1 duplicate in 127 plans, and that one is a copy.
  When it does happen, the banner states something false.
- **Fix:** in `_banner_line`, resolve `slug` to the label for its OWN checkout (the
  `slug @ <ROOT>` label when that slug is duplicated). Print labels with a short checkout name,
  not the absolute path.

### F6 — Minor — new fold code that no case pins (mutation survivors I constructed myself; the shipped manifest is clean)

I ran the shipped manifests (scoped copy; `EXPECTED_MUTATIONS` pruned to these two files;
`--mutate .`):
`OK — 2 file(s), 110 mutation(s), 110 killed, 110 attributed to the case each names, 0 survivor(s)`.
The new entries' names match the cases that kill them. My own probes, each run against both
self-tests:

| Probe (applied to `fe08f438`) | Result |
|---|---|
| `run_decide` passes `notes=[]` instead of `_notes` (`:1363`) | **survives** (both suites rc 0). The "NOT EVERY CHECKOUT WAS READ" caveat is not wired to any case at the call site. |
| `read_plans_noted`: another checkout's unreadable dir is no longer caught (`except (KeyError,)`) | **survives**. Executed without the mutation, it does work: `chmod 000` on wt2's plans gives rc 0 and a page note. Nothing asserts that. |
| `if not seen_own:` fallback removed (`:385`) | **survives**. Executed: a fixture `repo/sub/.claude/plans` pulls in the main checkout's plans, and labels its own copy `dup @ …/repo/sub/.claude`, which is the `.claude` directory and not a checkout. Cosmetic, and only reachable from a non-root fixture. |
| `known_everywhere` returns `known` when nothing was read; explicit/plan conflict no longer unreadable; `also=` forced to `-`; thread CANNOT RUN no longer forces the code; unlistable dir counted as read | killed |

**Fix:** add one `run_decide` case with a missing checkout, asserting the caveat appears in
stderr. Add one gen-work-lines case with an unlistable other checkout. Pass the checkout root
(`d.parent.parent`), not `d.parent`, in the `seen_own` fallback.

### F7 — Minor (latent) — `scripts/check-banner-armed.py:606`, docstring `:144`/`:599`: any `→ `x`` outranks everything, so a commit id after an arrow becomes the thread

- **Executed:**
  - `` `slice-a` · step 3 of 5 → `abc1234` pushed `` gives `('switched', 'abc1234')`.
  - `` ↳ RESUMED `slice-a` after the ⤳ SWITCHED to `ci-red` detour `` gives `('switched', 'ci-red')`.
- **Why this matters:** the docstring says that "a later commit id, PR number or file name in
  backticks is never the thread". At the top precedence level, an arrow counts anywhere in the
  row, including in a step row that does not switch.
- **Real-world exposure:** zero so far. Across all 559 distinct real Thread rows in the
  transcripts, the old and new `thread_name` disagree on exactly one row, the intended
  `three-review-rounds … ⤳ SWITCHED to `plugins-handoff-citations``. No real row has `→ `x``
  without `SWITCHED`.
- **Fix:** only count `→`/`SWITCHED to` as a destination when the row starts with `⤳`/contains
  `⤳ SWITCHED`. Otherwise, narrow the docstring sentence.
- **Pre-existing, not fold-caused:** the real row
  `` ⤳ SWITCHED from `quiet-stop-observers` (…) → ↳ RESUMED `banner-blind-spot` · 3 of 5 done `` is
  unreadable (None, quiet) both before and after the fold, because `→ ↳` puts no backtick
  directly after the arrow. It errs toward staying quiet, so it is recorded here only.

### Mandate items answered without a finding

- **(a) Stale worktrees and performance:**
  - Real cost: `plan_dirs` over 21 checkouts takes 0.017 s. The whole `read_plans_noted` takes
    0.083 s (127 plans), once per Stop and per plan change. That is acceptable.
  - Plans in old-session worktrees satisfying the check, e.g. `wt-chrome`'s `chrome-bar-fold`,
    is the intended outcome of option A, and they are real plans.
  - A worktree of a different repository cannot appear in `git worktree list`.
  - What does go wrong is covered in F2 and F3.
- **(b) Duplicate slugs:** a child's parent is resolved to the copy in its own checkout, and then
  to main. WT3 checks this, and I confirmed it in the temp repo with `kid`. I found no case where
  a child attaches to the wrong copy, beyond the documented fallback to main when the child is in
  a third checkout. The double-count is F4.
- **(c) Implementer's `begin-plan` gap:** this is F5. It is real, and its likelihood is low:
  1 in 127.
- **(d) The remaining warnings, sampled:**
  - My replay window differs from the implementer's: transcripts modified since 2026-10-10,
    including this session. It gives **41 warns / 108 Thread-row turns** (5 unreadable), across
    **22 distinct slugs**.
  - For every one of the 22, I grepped all transcripts for `begin-plan.py <slug>`. The known
    positive `chrome-bar-fold` matched 1 file. Each of the 22 matched **0**. None of these
    threads was ever armed under that name, so the warnings are genuine by the rule.
  - At least 2 of the 22 slugs (`chrome-bar-reachable`, `process-281`) name work that a plan under
    a *different* name covered (`chrome-bar-fold`; Codex r2 found `afk-two-folds-and-r18`). These
    are naming mismatches, not missing plans.
  - Several others are worktree **branch** names with no plan at all: `marketplace-inventory`,
    `backlog-249-260-fixes`, `plugins-handoff-citations`, `process-281-mechanism-question`. These
    are genuine.
  - Estimate: about 20 of 22 slugs are genuinely planless. This is UNVERIFIED beyond the grep and
    the two named mismatches.
- **(e) Mutations:** 110/110 killed, each attributed to the case its name gives. My extra probes
  are in F6.

## Thrashing or prose floor?

| Finding | Introduced by the r2 fold? | Evidence |
|---|---|---|
| F1 | **No** for the defect, **yes** for the overclaim | The `8b871a60` call site (`:1305`) sits in the same `else` branch after `sample_for`. The fold added the "ALWAYS EVALUATED" text. |
| F2 | **Yes** | `plan_dirs` and its missing-checkout note are new in `fe08f438`. |
| F3 | **Yes** (a consequence of option A) | Before the fold, worktree plans were never read, so nothing could disappear. |
| F4 | **Yes** | The labelled-duplicate logic is new. |
| F5 | **Yes** | `read_plans` now returns labelled slugs, which `work_line` does not handle. |
| F6 | **Yes** | All three survivors are in new code. |
| F7 | **Yes**, but latent | Introduced by the r2 Codex 1 precedence rule, with 0 of 559 real rows affected. |

**Verdict on the question:** the findings are fold-caused and sit in one component (the
every-checkout reader). By count, that matches the arming condition's shape. By character, it is
a **prose/edge floor, not thrashing**:

- Nothing is Blocking or Major.
- None of the findings reopens an r2 finding. The r2 Codex 1/3/4 fixes hold: the
  explicit-destination row now warns, the thread class co-fires with `also=`, and worktree plans
  are found.
- Each finding is an unpinned edge or a bound the owner should see (F3), not a regression of the
  thing r2 fixed.

I do not recommend convening an architecture review over this round.

VERDICT: CONVERGED
