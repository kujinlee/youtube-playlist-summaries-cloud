Reviewed head: 3719d9e1dd3adf246394eacd18f976f6e85f6b22

# Marketplace Task 20, round 1, Claude half

Branch `marketplace-task20`, PR #619. Subject: `git diff origin/master..HEAD`. It holds 34 effort (3) rows in
`docs/marketplace/inventory.json`, practices 27 and 28 in `docs/portable-practices.md`, the live
`check-inventory.py` step in `.github/workflows/ci.yml`, and a dashboard entry.

## What was run

- `python3 scripts/check-inventory.py` printed `CHECKPOINT: the D1 checkpoint FIRED over 34 phase-1 rows`, with rc=3.
- Ratios were recomputed from the rows. 31 of the 34 phase-1 rows have public_bar / next_project >= 3. The three
  below 3 are page-chrome, page-markup and fixture-git, each 2.0. Dropping the two DON'T-SHIP orphans gives 29 of 32,
  so the fire is robust to C5 below.
- The CI step's shell was run verbatim under `bash --noprofile --norc -eo pipefail`, which is GitHub's default shell,
  with a stub guard. Results: rc 0→0, 1→1, 2→2, 3→0; an uncaught exception →1; SIGKILL →137; a missing script →2. The
  real guard with `experiment-tier-a.json` removed (`--root` copy) returned rc 2. **The CI caller is correct. No
  finding.**
- I read all 34 rows' verdicts, grades, criteria, routes and bases. I sampled in full: skill-brief, skill-explain-diff,
  brief-compose, explainer-serve, gen-backlog-page, ask-answerer, hook-regen-dashboard, hook-dispatcher,
  contract-explainer-delivery, contract-handoff-path, contract-corpus-search, page-chrome, page-markup, fixture-git,
  session-state, agent-watchdog, check-docs and check-dashboard-entry. The sample includes both DON'T-SHIP rows. There
  are no SHIP rows.
- I checked these against `scan-2026-11-17.json`, `experiment-tier-a.json`, `experiment-tier-a.md`,
  `experiment-tier-b.md`, `shipping-sets.json`, `components.json` and the source lines the notes cite.

## Findings

### C1 — MAJOR — `fix_induced: false` — the route kinds misdescribe the work: 23 of the 26 `decouple-config` rows are path-resolution fixes, which is the option spec §4 rejected

**Where:** every effort (3) row whose `route.kind` is `decouple-config`, except skill-brief (whose basis does move
values into a config file) and, in part, skill-dashboard and check-dashboard-entry (S4 store creation). Also the
`portable-core` rows page-chrome, page-markup and fixture-git.

**Evidence:** these are the `Basis:` lines, extracted per row:
- contract-explainer-delivery: "six invocations to ${CLAUDE_PLUGIN_ROOT}".
- hook-regen-* (all five): "declaring the hook in the package's hooks/hooks.json through ${CLAUDE_PLUGIN_ROOT}".
- gen-backlog-page, gen-features-page, gen-work-lines, check-goal-status, check-features, check-anchors and
  session-state: "project root from the caller" or "the root from the caller".
- hook-dispatcher: "resolve package hooks from ${CLAUDE_PLUGIN_ROOT}".
- explainer-serve: "a packaged fixture".

D10's route reads *"decouple it behind a config file"*. Spec §4's option table names *"a user-configurable path"*
for exactly this defect class and marks it **rejected — more surface, same class**. It names
`${CLAUDE_PLUGIN_ROOT}` as *"the fix. No new name, no user configuration"*. So these rows record the rejected
option's label on the accepted option's work.

The `portable-core` rows say "no code change; one importer scenario re-run". D10's portable core is *"ship only its
portable core, leaving the project-specific part behind"*, and nothing is left behind there.

The tell: on every one of these rows `route.cost_hours == cost.public_bar_hours`. The "route" is simply the public
bar's work, filed under whichever D10 label was nearest. The guard passes this because `[route]` and `[shape]` read
only that the kind is in `ROUTE_KINDS`, never what the basis does.

**Why it matters:** Task 22 renders this, and the H4 selection card reads "what could be published at a known price"
off it (D10's three lists). A reader sees 26 components needing "config decoupling", which is a different and larger
kind of work than a path fix.

**Fix:** D10's vocabulary has no entry for "fix the defect in place and ship as a plugin". That is a spec gap, not a
mechanical choice. Either:
- (a) record such rows honestly: no D10 route is cheaper than the public bar itself. Note this in the row, and file
  the vocabulary gap as a backlog row against spec D10 / `ROUTE_KINDS`; or
- (b) take it to the owner, because adding a route kind moves D10.

Either way, relabel the three `portable-core` "no code change" rows, or say why that label fits them.

### C2 — MAJOR — `fix_induced: false` — "cheapest route" is unsupported: `template-repository` is never priced or ruled out in any of the 34 rows

**Where:** all non-SHIP effort (3) rows (D10: *"the inventory records its cheapest route"*).

**Evidence:** I searched the 34 notes for "template". There are **0 hits**, and the only "cheap" hit is
contract-handoff-path.

Every row also carries the same sentence: *"next_project_hours prices copying the component into the owner's next
repository as files, where the install directory IS the project … so S1, S2 and S3 do not bite."* A template
repository is that same situation for a stranger: the files live in their repository, so `REPO = SCRIPTS.parent` is
the project (S1 gone), CWD-relative names resolve (S3 gone), and the template carries `.claude/settings.json`, so the
hooks are registered (S5 gone). Only S2 still bites, because a stranger's `~/explainers` has no tray page, and so do
the C2 project values. So, by the rows' own reasoning:

| row | priced route | a template-repository route would cost about |
|---|---|---|
| gen-backlog-page | 8 h | next_project 2 h |
| gen-features-page, gen-goals-page, regen-pages | 5–6 h | about 1 h |
| hook-regen-* (×5) | 2 h each | 0.5 h each |
| goal-tree | 10 h | 2 h |

No row says why the route is unsuitable. It plausibly suits only new projects, and that is a real limit, but it is
not stated anywhere.

**Fix:** for each non-SHIP row, either price `template-repository` or state in one line why it does not apply (for
example "a template serves only new repositories, and D1 targets installing into an existing one"). Then name the
cheaper of the two as the route. It may not change the checkpoint, which reads public_bar against next_project, but
it changes the H4 card's answer to "at what price".

### C3 — MAJOR — `fix_induced: false` — session-state is graded `none` on a false attribution: goal-tree's measured failure is raised in session-state's code

**Where:** row `session-state`. The note says: *"Imported by goal-tree and regen-pages, both exercised and failing on
S1 in their own code (spec 4: attributed elsewhere → grade none)"*.

**Evidence:**
- `experiment-tier-a.md:82` records goal-tree's failure as `rc 2 CANNOT RUN — … git rev-parse --git-common-dir gave
  no usable path`.
- That string is produced in exactly one place: `scripts/session-state.py:799`, in `_common_dir`
  (`grep -n "gave no usable path" scripts/*.py` → only that line).
- goal-tree reaches it through `_SS.main_checkout(root, run)` at `scripts/goal-tree.py:1542` (`_SS =
  _sibling("session-state")`, line 264).

Spec §4's all-fail row says: *"a failure attributed to code in this library makes it a measured failing component,
graded `measured` with that defect named"*, where attribution means *"the entry-point's failure trace reaches it"*.
The trace reaches it: the failing message is session-state's. The wrong root originates in goal-tree's `ROOT =
SCRIPTS.parent`, so this is at least a judgement call. But the row states the opposite as fact, and grade `none`
means "nothing was established", which this measured failure contradicts.

**Fix:** grade session-state `measured`, with `scenario: "goal-tree: A-script-goal-tree-print, failed in
main_checkout/_common_dir (session-state.py:799)"` and the S1 defect (line 91 / 1990) named. Alternatively, keep
`none` and state the attribution judgement explicitly, as contract-explainer-delivery's note does. Also check
regen-pages: its own `git rev-parse --git-common-dir` at `regen-pages.py:222/423` would make its failure its own, but
`regen-pages.py:1574` also loads session-state.

### C4 — MAJOR — `fix_induced: false` — C4 is recorded `pass` on rows where nothing established C4, so NEEDS-WORK sits beside five passes

**Where:**
- page-chrome, page-markup and fixture-git: `criteria` all `pass`, grade `none`, verdict NEEDS-WORK.
- contract-handoff-path and contract-corpus-search: all `pass`, grade `none`, verdict DON'T-SHIP.
- agent-watchdog: C4 `pass`, grade `none`.

**Evidence:**
- page-chrome's own note: *"the C4 its role inherits (spec 4) cannot be established until an importer passes"*.
- The two contracts have *"no importer in this package"*, so spec §4 says *"no inheritance is possible — grade
  `none`"*. That is no C4 evidence of any kind.
- §4b defines `none` as *"nothing was established"*.
- `CRITERION_VALUES` includes `unanswered` (`check-inventory.py`), so an honest value exists.

As recorded, the rendered row reads "C4 pass" for a library whose C4 the row itself says is unknown. It is an
inference displayed as a result. For page-chrome and its two siblings, it also leaves the NEEDS-WORK verdict with no
failing criterion to point at. No rule refuses it, because no rule relates C4 to the grade.

**Fix:** set C4 to `unanswered` on these six rows, or `struck` if the owner rules that an orphan's C4 is outside the
question, but not `pass`. Optionally add a `[shape]`/rule case: a `library` at grade `none` with C4 `pass` is refused.

### C5 — MINOR — `fix_induced: false` — the two DON'T-SHIP orphans are still in the phase-1 shipping set, and they count in the checkpoint

**Where:** contract-handoff-path and contract-corpus-search. `shipping-sets.json` lists both under
`packages.comprehensibility.components` (both present, 34 components). `components.json` gives both `phase: "1"`.

**Evidence:** both rows invoke spec §4's *"an orphan library is also a scope question: ask why it is shipping at
all"*. They answer with DON'T-SHIP, yet they remain in the set Task 22 names as "the phase-1 subset … and shipping
set", and they are 2 of the 34 rows the checkpoint counted (ratio 4.0 each). A DON'T-SHIP member of a shipping set
contradicts itself.

**Fix:** state in the rows, and carry into Task 22, that they leave the comprehensibility shipping set. Map and
shipping-set changes are Task 5's files, so filing them is acceptable. The checkpoint still fires at 29 of 32, so the
H4 stop is unaffected.

### C6 — MINOR — `fix_induced: false` — the three "no way to assess it" rows will file Task 22 backlog rows for files with no defect, the phantom spec §4 says the role table exists to prevent

**Where:** page-chrome, page-markup and fixture-git (NEEDS-WORK, grade `none`, *"a limit of this run, not a code
defect"*).

**Evidence:** spec §4, *Why the role exists at all*: *"the original text forced `NEEDS-WORK` with defect 'no way to
assess it', and §7 turns every `NEEDS-WORK` into a backlog row — a filed defect for a file that has none."* Task 22:
*"`docs/backlog.md` (one row per `NEEDS-WORK` component with its named defect)"*.

Under the rules NEEDS-WORK is the only verdict available here: SHIP needs a passing importer scenario, and DON'T-SHIP
has no reason. So the verdict is defensible. The downstream effect is not.

**Fix:** have the rows' notes, and Task 22, file these three as ONE work item ("re-run an importer scenario once an
importer's route lands"), not three defects. Or raise the gap: spec §4b's *"we have not assessed it yet"* row has no
backlog shape distinct from a defect.

### C7 — MINOR — `fix_induced: false` — skill-brief's note says tier B reproduced its S3 failure, but tier B's brief found brief-compose and failed on S2

**Where:** row `skill-brief`. Its note says: *"tier B reproduced it in a real repository (the skill 'was written for a
different repo')"*.

**Evidence:** `experiment-tier-b.md:39` says: *"`brief` | … | Found `brief-compose.py` in the staged package this
time; it refused (no Ask-tray page — S2)"*. The CWD-relative miss (S3) was not reproduced. The record's own I2 bound
(`experiment-tier-a.md`, I2) also says path behaviour in both tiers is *"the staging's, not a stranger's"*. This
matters beyond the one row: contract-explainer-delivery's `measured` grade rests on skill-brief's S3 failure, and
that failure is a single tier-A observation.

**Fix:** correct the sentence to "tier B: brief-compose was found, then refused on S2". Add the I2 bound to
contract-explainer-delivery's attribution.

### C8 — MINOR — `fix_induced: false` — practice 27 misquotes its source and presents an unrun remedy as part of the measured practice

**Where:** `docs/portable-practices.md`, §27, under *The measured runs that produced it* and *The distinction that
makes this actionable*.

**Evidence:**
- §27 says *"Two defects account for every script failure, and they are the same mistake made in opposite
  directions"*, and names S3 and S1. The source says otherwise: `experiment-tier-a.md:12` reads *"Suite defects S1
  and S2 … account for the 7 script failures"*. S3 is the cause of three **skill** failures (`brief`,
  `explain-findings`, `dashboard`, line 13), and brief-compose's script failure is S2.
- The remedy table prescribes `${CLAUDE_PLUGIN_ROOT}/…` in skills and `CLAUDE_PROJECT_DIR` for user files. Neither
  was run in either experiment, and every route that would use them is graded `argued`. Spec §4c says a practice
  entry carries *"the measurement that earned it"*.

**Fix:**
- Reword to "two defects account for every *path* failure: S3 in the skills, S1 in the scripts". This is true per the
  record.
- Mark the remedy column as argued: the convention observed in `openai/codex-plugin-cc` and `oh-my-claudecode` (spec
  §4), not run here.

Practice 28 checks out against the sidecar (`brief-compose` and `gen-dashboard` condition 4 `fail`) and against
tier B (0 of 5 trays). No finding there.

### C9 — MINOR — `fix_induced: false` — shared fixes are priced in more than one row

**Where:**
- skill-explain-diff: *"the work left here is the delivery invocations through ${CLAUDE_PLUGIN_ROOT}"*.
- skill-explain-topic and skill-explain-findings say the same.
- skill-brief: *"and the delivery invocations to ${CLAUDE_PLUGIN_ROOT}"*.
- contract-explainer-delivery prices those same six invocations (`:2:1`–`:2:6`) at 3 h.
- The five hook-regen rows each price 2 h for entries in one `hooks/hooks.json`.

**Evidence:** these are the basis lines quoted above. Per-component ratios are unaffected, but any total read off the
cost record at H4 counts the same work up to five times.

**Fix:** price each shared fix in one row, and have the dependents say "priced in <row>", as the S2 tray already
does.

### C10 — NIT — `fix_induced: false` — check-inventory's docstring still says CI runs `--self-test` only

**Where:** `scripts/check-inventory.py:80`. It reads *"Caller: the `check-inventory self-test` step … runs
`--self-test` ONLY. The live run joins CI in plan Task 20 …"*.

**Fix:** name both steps, the self-test and the live run, which passes rc 3.

### C11 — NIT — `fix_induced: false` — the CI step prints the rc 3 stop as a plain log line

**Where:** `.github/workflows/ci.yml`, step `check-inventory (live)`.

**Evidence:** `echo "check-inventory rc 3: …"` lands in a log nobody opens on a green job. It meets the plan
("printed"), but the channel is weaker than the stop it carries.

**Fix:** `echo "::warning::check-inventory rc 3: …"`, so it surfaces as an annotation on the PR.

## Questions the brief asked, answered

1. **Verdicts versus evidence.** The NEEDS-WORK verdicts follow for every exercised entry point. Each sidecar entry
   has a `fail`, and each cited finding id exists for its own component (sampled ids are quoted above). The
   misdescriptions are C3 and C7. C4 is a criterion that contradicts its own note.
2. **Grades.** No estimate is graded `measured`: all 68 cost grades and 34 route grades are `argued`. Every row has a
   `Basis:` line. Some name no finding (brief-compose, page-chrome), and say why. The hours include review in words
   only. They are a uniform boilerplate sentence, uncalibrated against any recorded slice duration, but honestly
   graded `argued`.
3. **Library inheritance.** No library is graded `inherited`. contract-explainer-delivery is graded `measured` by
   attribution and says it is a judgement. session-state is the misapplication (C3). No CANNOT RUN importer
   contributes. ask-answerer's `--status`-only run is correctly `argued`.
4. **Cheapest route.** It is not established (C1, C2).
5. **Practice entries.** Both headings exist exactly (`[practice]` passes, and I checked by eye). The issue is C8.
6. **CI caller.** It is correct, as verified above.
7. **The guard.** rc 3 is honest about the checkpoint. Rows pass only because the guard does not read route kind
   against basis (C1), C4 against grade (C4), or verdict against shipping set (C5). The spec places the first two in
   the reviewer's judgement.

VERDICT: NOT CONVERGED
