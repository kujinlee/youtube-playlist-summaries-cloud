Reviewed head: 266ba0b565d1f69ac9fc48aa277e9a66f9a2ebe8

# marketplace-plan — round 1, Claude half (adversarial)

**Subject:** `docs/superpowers/plans/2026-11-11-marketplace-inventory.md` (818 lines) at `266ba0b5`, against the
approved spec `docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md` (1,277 lines).
**Mandate:** refute readiness. **Method:** read the plan in full and spec §1-§2c, §3, §4b, §5 head, §6, §7, §8, §9,
§10. I extracted and ran the embedded code and shell in the scratchpad, never in the repository, and checked every
factual claim a task depends on against the tree at `266ba0b5`. I did not read the Codex half, which sits untracked
in this worktree.

**Tally:** 1 BLOCKER, 8 MAJOR, 9 MINOR.

---

## BLOCKER

### B1. The go/no-go spike packages a script without the two modules it imports, so it gives a false NO-GO and stops the plan at H3 (plan:266-281)

Task 4 Step 1 stages exactly `.agents/skills/explain-topic` and `scripts/explainer-serve.py`. GO requires *"the
installed script performs the operation by its installed path"*. But `explainer-serve.py` imports two siblings at
module load:

```
scripts/explainer-serve.py:99   sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
scripts/explainer-serve.py:101  import page_chrome  # noqa: E402
scripts/explainer-serve.py:102  import page_markup  # noqa: E402
```

**Ran:** I copied `explainer-serve.py` alone into `<scratch>/spike/scripts/` and ran
`HOME=<scratch>/spike/home python3 -I <scratch>/spike/scripts/explainer-serve.py --help` from an unrelated directory.
Result: `ModuleNotFoundError: No module named 'page_chrome'`. Even `--help` fails.

So as written, Step 3 fails. Step 5 records NO-GO, the FAILS IF says *"this is spec §9's D3 falsifier"*, and the plan
*"stop[s] … and go[es] to Human step H3"*. H3 then asks the owner to re-decide D4 because of a staging omission in the
plan, not because of any property of D3. The plan's own justification (*"explainer-serve.py is the script it ends
in"*) never checked the import closure. Task 7's closure validator does check it, but Task 7 runs after the spike.

**Fix:** stage `scripts/page_chrome.py` and `scripts/page_markup.py` with it. I checked that those two have no
further non-stdlib or sibling imports (`page_markup` adds only `bisect`). Separately, state that a NO-GO caused by a
staging omission is a plan defect to fix and re-run, never the D3 falsifier.

---

## MAJOR

### M1. The spike's "start it on a free port" cannot be done, and the preflight refuses on the owner's machine today (plan:201-203, 207-208, 271-272)

- `explainer-serve.py` has no port option. `PORT = 7391` is a module constant (line 104), and `main()` accepts only
  `--stop`, `--status` and `--self-test` (lines 3513-3518). So *"start it on a free port"* (Task 4 Step 3) cannot be
  done without editing the component, which the plan's own *Evaluate, never repair* rule forbids.
- **Measured:** `lsof -nP -iTCP:7391 -sTCP:LISTEN` shows the owner's own `Python` process (pid 30306) listening right
  now. Task 2's preflight is correctly specified to refuse in that case, so the spike cannot start. No task and no
  Human step says who stops the owner's server, or when.
- Without the refusal the result is worse. `start()` (line 1579ff), on finding the port busy, prints
  `already serving on …` and returns, so the stranger's `GET /` would be answered by the **owner's** server, serving
  the owner's `~/explainers`. That is exactly the leak in Review Focus 3.
- The self-test case *"bind a socket in the case, then release it"* (plan:202) will error on the owner's machine,
  because 7391 is already bound there.

**Fix:** decide the port story explicitly. One option is a Human step that has the owner stop their server for the
experiment window. The other is to measure the hard-coded port as a finding: one stranger per machine, and a
collision with any other user of 7391. Rewrite Step 3 as "start on 7391 in a world where preflight confirmed it
free".

### M2. The closure validator can never catch an omitted skill→script dependency, the edge that matters most (plan:355-368)

Task 7's rule is that a reached path resolving outside the installed tree "(CWD-relative …)" is `external`, not a
gap, and its own case says *"a CWD-relative invocation is external, not a gap"*. **Measured:** every skill→script
edge in the five page skills and the shared contracts is CWD-relative:

```
.agents/skills/dashboard/SKILL.md:76             python3 scripts/regen-pages.py
.agents/skills/shared/explainer-delivery.md:165  python3 scripts/brief-compose.py
.agents/skills/shared/explainer-delivery.md:223  python3 scripts/explainer-serve.py
.agents/skills/shared/explainer-delivery.md:300  python3 scripts/explainer-serve.py
```

So if `brief-compose.py` or `explainer-serve.py` were left out of the comprehensibility package, `--closure` would
report `external: scripts/brief-compose.py` and stay green. Python sibling imports are the only edges it can turn
red. The escape clause *"exists in the repository's version of the package but is missing from the declaration"*
does not rescue this, because "the repository's version of the package" is never defined. Task 5's `map_gaps` only
asks that a file be in **some** component, not in the same **package**, so it cannot catch this either.

**Fix:** resolve every CWD-relative invocation against the package root as well. If the target exists in the
repository and is not in the package, that is a gap, in addition to the detector-2 `cwd-relative` finding. Add the
case *"brief-compose.py dropped from the declaration with its count lowered → closure red"*.

### M3. Task 6 installs the CI layer as a Claude Code plugin, against spec §2c's install channel (plan:316-317, 342-343)

Task 5 defines a `ci-layer` package, and Task 6 *"stage[s] and install[s] all three packages from components.json"*
through `claude plugin install`. Spec §2c, *Install channel for CI pieces*, says these are installed *"as a
**reusable GitHub workflow** (`uses: …@<tag>`) … not through `/plugin marketplace add`"*. It also says C4's
"install" for a CI piece means adding one `uses:` line. A shipping set derived from a plugin-installed tree is the
wrong artifact for that package, and Task 17 then reads routes against it.

**Fix:** derive `ci-layer`'s shipping set from the files a reusable workflow would reference. Or state that effort (2)
gets no installed-tree declaration this milestone, since it is `argued` and has no experiment. Do not install it as
a plugin.

### M4. Detector 4's calibration case asserts "exactly 9" over a file where the specified detector finds more (plan:456-471)

The detector is specified as: guard names from all `ls scripts/check-*.py` stems, and doc paths from any repo-relative
`docs/` path the package does not ship. It is not limited to step 1's ground-truth list. **Measured** in
`brief/SKILL.md`, unchanged since `2f5e3f3d` (the `git diff --stat` is empty, so the plan's "re-derive from a
fixture" escape never triggers):

- guard names beyond the four: `check-deploy-freshness.py` (line 78) and `check-selftest-counts.py` (line 167);
- doc path beyond the four: `docs/dev-process.md` (line 31).

So the case *"yields exactly the 9 items of spec §4"* goes red against a correct implementation of the detector as
written. An executor will then either narrow the detector to step 1 (which nothing says to do) or loosen the case.
The FAILS IF says *"fewer than 9"*, which contradicts "exactly". Spec §4's 9 is a count over the ground-truth list,
not over the whole file.

**Fix:** state the population: the calibration is over step 1's list, and the whole-file count is reported
separately with its extras named. Make the case and the FAILS IF agree.

### M5. Detector 4's tool-name derivation confirms against a file that contains none of the tool names (plan:456-458)

Tool names are *"confirm[ed] … against `docs/available-skills.md`"*. **Measured:**
`grep -c 'TaskList\|PushNotification\|AskUserQuestion' docs/available-skills.md` returns `0`. That file lists skills
and commands, not harness tools. The pattern `\b[A-Z][a-z]+[A-Z]\w+\b` over the page skills also matches
`JavaScript`, `SessionStart`, `PreToolUse`, `PostToolUse`, `SendUserFile` and `TaskStop`. Confirmation cannot
separate those, because every one of them is absent. The derivation as specified therefore yields zero tool names,
or all the camel-case words, and the calibration's *"1 tool name (TaskList)"* can only be reached by hand-typing it.

**Fix:** name a source that actually lists harness tools, or declare the tool-name set a hand-written, dated list,
which is a stated deviation from "derived".

### M6. Detector 1's derived vocabulary cannot produce `gemini`, a term the spec names, and its own structural case forbids adding it (plan:413-424)

Spec §5 item 1 lists the vocabulary as *"`supabase`, `gemini`, `fly`, `youtube-playlist`, repo-rooted paths"*.
**Measured:** `package.json` dependencies are `@google/generative-ai`, `@googleapis/youtube`, `@supabase/ssr`,
`@supabase/supabase-js`, … and none of them contains `gemini`. `.env.example` does not exist. So no source in the
plan's derivation produces `gemini`, and the case *"vocabulary contains no hand-typed literal"* forbids adding it.

The same case also contradicts the plan's own derivation, which hand-types the directory list
`supabase/, worker/, app/, lib/, components/`. Choosing which `package.json` keys "name a service SDK" is likewise a
hand judgment.

**Fix:** derive `gemini` from a real source, for example the product's own `lib/gemini.ts` module stem, which
`docs/dev-process.md` names as the mocking boundary. Or narrow the structural case to what it can actually enforce.
Add a case *"`gemini` is in the derived vocabulary"*.

### M7. `row_errors` enforces the grade only on SHIP rows, but spec §4b requires it on every row (plan:663)

Spec §4b: *"**Every component in the inventory carries both fields.** A verdict without a grade is an incomplete
row, and deliverable 5 is not done until every row has one."* The plan refuses only *"a ship row whose grade is
missing"*. A `NEEDS-WORK` or `DON'T-SHIP` row with no grade passes `check-inventory.py`, and Task 20's gate (rc ≠ 1)
is then met over an incomplete inventory.

Two spec §9 falsifiers that are decidable from the data also have no rule:

- *"a component marked `SHIP` that the install experiment cannot run"*. This is decidable by joining a SHIP row's
  scenario with the tier-A record.
- the D11 falsifier's *"named subset that has no shipping set"*. This one is covered only at package level.

**Fix:** require the grade on every row, and add the SHIP-versus-experiment rule (or explain why it cannot be
decided), each with an adjacent negative.

### M8. Slice A puts the D8 corrections in a separate PR, which reverses an owner decision the spec says not to re-open (plan:97-108, 167-168)

Spec §7 item 8: *"⭐ **D8 — A CORRECTION LANDS WITH THE WORK THAT FOUND IT, NOT IN A SEPARATE PR. Decided 2026-10-16
by the owner** … 'yes, fix in here.'"* The spec's bound is that they are PR 1's **first commit**, mergeable alone.
Splitting them into their own PR is named only as the response once the stall risk is live. The plan makes slice A a
standalone PR up front and justifies it by quoting "first commit and mergeable alone". More broadly, it turns the
spec's single "PR 1" into six PRs, so the spec's FAILS IF (*"PR 1 open with ANY OF THE THREE corrections not yet
committed"*) no longer has a subject.

Six PRs may be the better engineering choice, but changing the delivery shape of an owner's decision is the owner's
call, not a default. **Fix:** either keep the corrections as slice B's first commit, or list this as a deviation the
owner must ratify. In either case, restate D8's FAILS IF against the slice structure.

---

## MINOR

- **m1 (plan:239-243), the probe was verified.** I ran the plan's probe verbatim in the scratchpad. `validate`,
  `marketplace add` and `install` each returned rc=0 with no login, and the tree landed at
  `$HOME/.claude/plugins/cache/probe-mkt/probe/0.0.1/`. A second probe confirmed that dot-directories
  (`.agents/skills/shared/x.md`) and `scripts/a.py` (mode kept) survive installation, so Task 3's
  repo-relative layout is installable. This is not a defect. It is recorded so the next round does not redo it.
- **m2 (plan:674-701), the checkpoint code was extracted and run.** The five asserts pass under `python3 -I`, but the
  function as written returns `True` for `next_project_hours = 0` (my probe `_row("1", 1, 0)` returned `True`, and so
  did `_row("1", 0, 0)`). Line 701 says that case is a row error, *"never an automatic fire"*, and the CLI never
  states how its exit codes rank, so rows with errors that also cross the threshold could exit 3 rather than 1.
  **Fix:** state that rc 1 outranks rc 3. Then either guard the function or assert that `row_errors` runs first, with
  a case.
- **m3 (plan:678, 635-636), the recall phase is fixed while recall's status changes.** `checkpoint_fires` always
  counts `1-if-feasible` rows. D11 says that if either condition fails, recall moves to "later". Neither Task 18
  (condition (a) false) nor H1 (not done) updates the rows' `phase`, so recall's four rows can tip a checkpoint whose
  population the spec says excludes them. State which population Task 21 runs on, and have Task 18 write the phase.
- **m4 (plan:301-309), candidates come from every registered hook.** `.claude/settings.json` registers 27 hooks
  through `run-hook.sh` (29 references), most of them governance (`block-default-branch-push`, `check-plan-gate`,
  `usage-pace-*`, …). Their transitive `scripts/*.py` all become candidates that need an exclusion. With `--map` in
  CI (plan:367) **and** the full scan in CI (plan:494-496), every future PR that adds a hook, or renames a component
  file, turns master's CI red until `components.json` or `shipping-sets.json` is hand-edited. The spec asks for CI
  registration of the scan, not a standing whole-repo ratchet. Say that this tax is intended, or start the closure at
  the three efforts' entry points.
- **m5 (plan:345-346), a vacuous gate.** Task 6's FAILS IF *"`declare` opens any path under
  `scripts/check-publishability*`"* cannot fail when it runs, because that script is created in Task 8.
- **m6 (plan:68-70 vs 176-178), spend-log ordering.** Every slice appends a spend-log row, but the file is created in
  Task 2 (slice B), so slice A has nowhere to write. Also, plan:793 opens each slice's PR as a DRAFT at slice start,
  which trips Task 1's FAILS IF (*"slice A's PR still open when slice B's PR opens"*) by the plan's own instruction.
- **m7 (plan:545-550), the skill half has no permission mode.** `claude -p` in a fresh HOME with no settings will
  refuse or prompt for Bash and Write tool use, so the skill half fails on permissions, and that failure would be
  recorded as a **suite** defect. Name the permission flags (`--allowedTools`, or a settings file inside the world)
  as part of the baseline deviation. Also name how a plugin skill is invoked under `-p`.
- **m8 (plan:631-633), Task 18's recall probe also needs the model and `bash`.** `recall-llm.py` shells out to
  `claude -p` (`recall-llm.py:924`), and `surface-recall.sh` starts with `#!/usr/bin/env bash`. Task 18 names
  neither its allow-list (`bash` and `claude` must be on the world's PATH) nor its dependency on H2. Without them the
  probe gives a CANNOT RUN that could be mis-scored as "not useful", which would decide D11 (a).
- **m9 (plan:513-515, 553-555), ground truth exists only for `brief`.** `known-facts.json` covers only `brief`'s
  items, yet Step 4 scores pass condition 2 *"per entry-point"* for `explain-diff`, `explain-findings`,
  `explain-topic` and `dashboard`, none of which has seeded facts. Either seed facts for them or mark condition 2
  `argued` for them.

---

## The 11 defaults the drafter took

| Default | Ruling |
|---|---|
| ADR 0015 in the header | **OK.** `docs/anchors.md:43` registers `harness-ships-elsewhere` with ADR 0015, and the ADR's own anchor line names it. The spec's header reads `ADR: none`. That is harmless but unexplained, so note the difference. |
| Python audit hook as recorder | **OK in kind.** Spec §6 permits "an allow-listed environment". Note that Homebrew Python has its own `sitecustomize.py` (measured: `…/python3.14/lib/python3.14/sitecustomize.py`), and a `PYTHONPATH` one shadows it, so state the shadowing as a baseline deviation. Local Python is 3.14.4 and CI pins 3.12. |
| Login as human step H2 | **OK.** It is the owner's credential, so it is correctly a Human step. See m7 and m8 for what it also gates. |
| Cost unit = agent-hours including one review round | **Acceptable.** The checkpoint is a ratio, so the unit cancels. However, the owner's round cap is r1-r3 with both halves in r1, so "one round" understates the cost. Say so. |
| Tier-B repo `Yeachan-Heo/oh-my-claudecode` | **OK.** It is a spec §6 candidate. Measured: MIT `LICENSE`, and the local copy `is-shallow-repository = true`, so the full-clone instruction is needed and correct. |
| Data under `docs/marketplace/` | **OK.** |
| Spike installs explain-topic + explainer-serve.py | **DEFECT.** See B1 and M1. |
| Scan identity terms | **Partly defective.** See M6: `gemini` cannot be derived. The owner handle in the remote URL is not in the vocabulary. Say whether that is intended. |
| Spec item 7 already done | **Verified.** `docs/anchors.md:43` has the anchor, and `docs/backlog.md:280` shows row 290 as ✅. |
| Three packages | **Defective for `ci-layer`.** See M3. |
| Spend log | **Not in the spec. It is an owner-visible cost the owner did not ask for, though cheap.** See m6 for its ordering defect. |

**Not the owner's to leave defaulted:** M8, the D8 delivery shape. The rest are engineering choices the drafter may
take.

## Checks that pass (stated so a later round does not repeat them)

- Task 1's probe loop, run at `266ba0b5`: `roughly 3x: 1`, `The problem is concentrated in: 1`,
  `10,373 lines across six files: 1`. This matches the plan's "before" values.
- `page_markup.py` contains exactly 2 `supabase` matches (lines 861-862, inside a self-test `case(...)`). This matches
  Task 9's FAILS IF.
- `explainer-delivery.md` contains exactly 3 `python3 scripts/…` invocations. This matches Task 10.
- `brief/SKILL.md` contains each of the 9 named items, and `artifact-design` appears in both `brief` and
  `explain-findings`. This matches Task 11's detector-5 case. See M4 for the over-count.
- `gen-dashboard.py:526` calls `gh` through `subprocess.run`. This matches Task 12.
- `fixture_git.isolated` exists (`scripts/fixture_git.py:86`). The W1-W8 section exists
  (`2026-11-09-observed-reach-selection.md:147`). Every script named in *Before every push* exists, and
  `check-selftest-counts.py --changed` and `check-plan-code.py --only` are real flags.
- `claude` is a native Mach-O binary, so a `PATH` holding only the allow-listed symlink works with no `node`.
- `check-anchors.py`, `check-docs.py` and `check-plan-file-tags.py` all exit `rc=0` at `266ba0b5`.
- No step publishes, pushes, or writes to a third-party repository without a Human step. The H1-H6 table covers
  every outward-facing act.

VERDICT: NOT CONVERGED
