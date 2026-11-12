Reviewed head: c316d97a3687b6d88abcdac9464e949274213afb

# marketplace-plan — round 2, Claude half (adversarial; the only half this round, alternation)

**Subject:** `docs/superpowers/plans/2026-11-11-marketplace-inventory.md` (1,038 lines) at `c316d97a`, against
`docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md`. The r1 fold is
`docs/reviews/coordinator/marketplace-plan-r1-coordinator.md`.
**Mandate:** refute the claim that the fold closed r1. **Method:** I re-checked every finding marked fixed
against the plan text and against the tree. I extracted the embedded checkpoint code and ran it under
`python3 -I` in the scratchpad (outside the repo), together with its stated mutation. I read
`scripts/explainer-serve.py` for the H7 questions.

**Tally:** 0 BLOCKER, 5 MAJOR, 4 MINOR. All 5 MAJORs were caused by the fold.

---

## MAJOR

### M1. `--status` exits 1 on a free port, so the fold's own step (a) produces a false NO-GO once H7 has done its job (plan:312-323) — fix_induced (CM1)

Step 3(a) now runs `--help` **and `--status`** as the "invocation from elsewhere" check, and Step 5 records NO-GO
when "the installed script cannot be invoked from elsewhere". Here is `status()` (`explainer-serve.py:1621-1629`):

```
    print(f"listening : {'yes' if running else 'NO'} on http://{HOST}:{PORT}")
    ...
    return 0 if running else 1
```

H7 frees 7391, and (a) runs before (b) starts the server. In that world `--status` therefore **always exits 1**.
The fold's evidence for this step was *"`--status` rc 0"*, which the coordinator file attributes to the same
measurement in which `--status` printed `listening : yes on http://127.0.0.1:7391`. So that rc 0 is the owner's
server answering, which is the very leak CM1 is about. The evidence is contaminated, and the expected value is
wrong. Nothing in the plan says rc 1 is the correct `--status` result. The plan-defect escape (plan:327-330) covers
only `ModuleNotFoundError`, so an executor who reads rc≠0 as "cannot be invoked" lands at NO-GO, then H3, and the
plan stops.

**Fix:** use `--help` alone for (a), or state that `--status` is expected to exit 1 with `listening : NO` on the
freed port. Add to the staging escape that a nonzero exit whose output is the script's own documented answer is
not a failure to invoke.

### M2. The GO leak check cannot fail when the owner's server answers, and `start()` exits 0 when it does (plan:314-315, Review Focus 3) — fix_induced (CM1's FAILS IF)

There is a window between preflight and start. In it, the owner, or any concurrent agent in the owner's session,
can restart their server, and every explain-* skill's delivery loop starts that server on 7391. If that happens,
`start()` prints `already serving on …` and **returns 0** (`explainer-serve.py:1581-1585`). `GET /` is then
answered by the owner's server. The fold's guard is *"the response names no path outside the world"*. But
`index_html(root)` (`:1037ff`) renders entries and never prints `root`, so the response names **no** path,
whichever server answers. The CM1 FAILS IF (*"GO is recorded without `GET /` served from the world's
`~/explainers`"*) has no observation that can establish it.

What I verified is safe: `--stop` from the world reads `PIDFILE = ~/explainers/.serve.pid` (`:107`, `:1608-1617`),
and that is the world's `HOME`. So **no agent step can stop the owner's process.** The H7 promise holds. Only the
race and the check are defective.

**Fix:** seed the world's `~/explainers` with a sentinel page before start. GO requires all three of:
(i) start's stdout says `serving <world>/explainers`, not `already serving`;
(ii) the world pidfile's pid is the listener (`lsof -iTCP:7391 -sTCP:LISTEN`);
(iii) `GET /` lists the sentinel.
Apply the same three conditions to Task 14's serve operation (plan:664).

### M3. The fold's CANNOT RUN for an unresolved recall phase has no exit, and it contradicts both the H1 row and D11's "only if" (plan:782-785, 853-866, 901-904, 937-944, 958, 997) — fix_induced (X2 / Cm3)

I extracted plan:840-895 and ran it under `python3 -I`: rc 0, every assert passes. The stated mutation
(`== "1"` → `in ("1","1-if-feasible")`) fails the assert at line 892, so the fold's claim holds. The function is
correct. The **state it creates** is the defect. I probed a realistic inventory: 20 comprehensibility rows, 11 of
them at 3× or more (fires), plus the 4 recall rows unresolved and cheap. The result is
`ValueError: CANNOT RUN: the checkpoint depends on recall's unresolved phase (H1)`, which is rc 2.

That rc 2 then reaches every downstream step, and none of them handles it:

- **Task 20** gates on *"`check-inventory.py` rc 0 or 3"* (plan:941). It cannot proceed, so the live CI caller
  never lands. If the caller lands first and the rows change later, CI goes red on master: *"only rc 1 and 2
  fail"* (plan:943).
- **Task 21** handles only rc 3 (plan:958).
- **Task 22** marks the inventory final *"only if Task 21 did not fire or the owner answered"* (plan:977-978). An
  rc 2 reads as "did not fire", so the inventory can be marked final over an uncomputed checkpoint.
- **The plan contradicts itself.** H1's row says *"If it does not happen … recall moves to 'later'"*
  (plan:997). Task 18 says H1 unanswered → *"stays `1-if-feasible`"* (plan:784).
- **The spec settles it.** D11: *"Recall is in phase 1 **only if** (a) … and (b) our own corpus passes the
  owner's content review"* (spec:145). Spec:1205 expects the corpus row to end the milestone as
  `C5: unanswered`. So H1 unanswered means (b) has not passed, and recall is not phase 1. Recall cannot be a
  third state that the checkpoint must refuse over.

**Fix:**
- Resolve the phase per D11's "only if". Unless both `a is True` and `b == "pass"`, the phase is `"later"`, and
  `"later (pending H1)"` is a note, not a phase.
- Or, if the unresolved state is kept, give rc 2-from-H1 an explicit path in Tasks 20, 21 and 22: not final,
  `[needs-you]`, and the CI caller tolerant of it.
- Either way, reconcile the H1 row with Task 18.

**FAILS IF:** Task 22 can mark the inventory final while `check-inventory.py` exits 2.

### M4. The whole-file calibration case asserts an extra the specified detector cannot produce: `check-deploy-freshness.py` does not exist (plan:572-578, 583-585, 591-592) — fix_induced (CM4)

Guard names are *"derived from `ls scripts/check-*.py` stems"* (plan:553). I ran
`ls scripts/check-deploy-freshness.py`: **No such file**, and `git ls-files | grep deploy-freshness` returns
nothing. `brief/SKILL.md:76-78` names it only as a gate that *"was nearly built as `check-deploy-freshness.py`"*.
The fold counted it with the regex `check-[a-z-]+`, not with the detector's rule. That is the same
measured-the-wrong-population error as r1 M4, one layer in.

A correctly implemented detector yields exactly 2 extras over the whole file (`check-selftest-counts`, which
exists, and `docs/dev-process.md`). The case *"the whole fixture file yields those 9 plus exactly
check-deploy-freshness, check-selftest-counts and docs/dev-process.md"* therefore goes red. So does the FAILS IF
*"the whole-file case does not name all three extras"*. Spec §5 also says *"a historical comment naming a guard is
**not** an invocation"* (spec:842).

The rest of the passage measurement holds. I re-ran the grep at `c316d97a`: the passage gives 8 pattern items plus
`TaskList`, and the file is unchanged since `2f5e3f3d`.

**Fix:** make the whole-file extras exactly `check-selftest-counts` and `docs/dev-process.md`. Add
`check-deploy-freshness` as an adjacent negative: a name with no `scripts/` file, in a historical sentence, is not a
guard-name finding.

### M5. The new closure table makes a missing SHARED CONTRACT `external`, so the fold's headline mutation depends on an unstated staging layout (plan:429-452; Task 3 plan:253-255) — fix_induced (CM2)

Row 4 of the table sends *"a READ of a document (`docs/...`, a `Read`-the-file instruction) not in the installed
tree"* to `external … never a gap`. But the page skills reach the delivery contract by a Read-the-file edge:
`../shared/explainer-delivery.md` appears 8 times across the five skills (measured by grep). Example:
`explain-topic/SKILL.md:68`, *"**Follow `../shared/explainer-delivery.md`**"*. If the package omits
`explainer-delivery.md`, the closure files it under `external` and stays green. That is the CM2 defect moved from
executable edges to read edges.

It also undermines the fold's own case. `brief-compose.py`'s only inbound edge is in `explainer-delivery.md:165`,
so the closure reaches it only if it resolves `../shared/…` to an installed member. Task 3 stages skills at
`<plugin>/skills/<name>` (plan:255), *not* at their repo-relative path. It never says where `.agents/skills/shared/`
lands, and `shared/` has no `SKILL.md` (`ls`: `corpus-search.md`, `explainer-delivery.md`, `handoff-path.md`). If
`shared/` is staged as a file path, at `<plugin>/.agents/skills/shared/`, then `../shared/` from
`<plugin>/skills/brief/` resolves to nothing. In that layout the mandated case *"brief-compose.py dropped →
closure red"* cannot go red.

**Fix:**
- Split row 4. A Read edge under `docs/` is `external`. A Read edge that resolves inside the package's own source
  tree (`../shared/…`, `.agents/skills/…`) is a member, or a gap when absent, exactly like an executable edge.
- State where `shared/` is staged so that `../shared/` resolves from an installed skill.
- Add the case: `explainer-delivery.md dropped → closure red`.

---

## MINOR

- **m1, the SHIP-versus-experiment rule forbids SHIP for every library (plan:816-819; fix_induced, CM7).** The
  rule refuses a SHIP row in a plugin package whose `experiment-tier-a.json` entry has `exercised: false`. But the
  sidecar is the entry-point coverage matrix (plan:657, 687), and spec §4 (`Role` table, spec:480-484) gives a
  `library` an **inherited** C4. Under this rule, `page_chrome.py` and `page_markup.py` can never be `SHIP`, even
  with an inherited grade from a measured scenario. The rule is also silent on a plugin-package row with **no**
  sidecar entry: every `recall` row, which has no tier-A run, and every `data` row. **Fix:** apply the rule to
  `entry-point` rows. For `library`, require the named inheriting scenario's entry-point to pass. State that a
  missing entry is a row error for an entry-point and not applicable to `data`.
- **m2, `channel` has nowhere to live in the Task 5 schema (plan:344-348 vs 366-369; fix_induced, CM3).** The
  Produces contract gives `components.json` only `measured_at`, `components` and `exclusions`. `Component` has
  `package` but no `channel`, and there is no package-level object. Task 6 needs `channel` to decide what to
  install. **Fix:** add `"packages": {name: {"channel": …}}` to the interface.
- **m3, the source of `harness-tools.txt` depends on which session writes it (plan:563-567; fix_induced, CM5).**
  The source is *"the tool list the writing session's harness exposes"*. Under the plan's subagent-driven
  execution, the writer is a subagent. This reviewing subagent's own tool list exposes no `TaskList` or
  `TaskCreate`. A subagent following the rule would omit `TaskList`, and the calibration then goes red, or someone
  hand-adds the one name the calibration checks, which makes the tool-name third of the calibration
  self-fulfilling. The only content check (no date/version header → CANNOT RUN) tests format, not content. Also,
  the plan calls the list *"a STATED deviation from 'derived'"*, but spec §5 item 4 (spec:782-785) does not require
  tool names to be derived (only detector 1's vocabulary, spec:779). So it is not a spec deviation, and **no owner
  decision is needed**. **Fix:** name the source as the coordinator's tool list, or the Claude Code tool
  documentation fetched in the task, and say the calibration's tool-name item is a membership check on that list.
- **m4, H7 makes slice B's stall foreseeable, but the plan names no response that protects D8 (plan:100-108,
  320-323; fix_induced, H7).** An INCOMPLETE or NO-GO spike leaves slice B's PR unmergeable, and the D8
  corrections sit unmerged inside it. Spec:1180-1183: *"PR 1 open with ANY OF THE THREE corrections not yet
  committed … At that point the stall risk the owner accepted is live and the corrections should be split into
  their own PR."* The plan says it *"does not pre-empt"* that. It should name the trigger instead. On Task 4
  INCOMPLETE or NO-GO, Task 1's commit is cherry-picked into its own PR; the spec already authorises this. Also
  state whether slice B merges with an INCOMPLETE or NO-GO spike record.
- *(Wording, no separate finding:)* Task 9's cases need exact-equality semantics. *"the vocabulary matches …
  youtube-playlist"*: the derived vocabulary contains `youtube-playlist-summaries[-cloud]`, not
  `youtube-playlist`. *"source contains none of the four terms as a string literal"*: the `fly` rule must read the
  literal `"fly.toml"`. State "an element equal to" and "a literal equal to", or each case is red under the other
  reading.

---

## Checks of the r1 fixes, one line each

| r1 finding | Holds? | Evidence |
|---|---|---|
| CB1/X1 import closure | **yes** | plan:292-302 stages `page_chrome.py` and `page_markup.py`. `fixture_git` is self-test only (`:1636`). |
| CM1 port / H7 | **partly** | No agent can stop the owner's server (pidfile under the world `HOME`, verified). See M1 (`--status`) and M2 (race + leak check). |
| CM2 CWD edges | **partly** | Executable edges fixed. Read edges moved the defect (M5). |
| CM3 ci-layer channel | **yes** | Not installed. `--closure` prints SKIPPED. The schema gap is m2. |
| CM4 calibration population | **partly** | The passage count is right. The whole-file extra is wrong (M4). |
| CM5 tool names | **yes, with m3** | The `available-skills.md` grep finds none of the four names (r1 measurement accepted). |
| CM6 vocabulary | **yes** | Ran it. The directory predicate yields `app components lib supabase tests types worker` (`docs`, `scripts` excluded). The Mocking-boundaries line names `lib/gemini.ts` and `lib/youtube.ts`. The scopes are `google`, `googleapis`, `supabase`. `fly.toml` is present and `.env.example` absent. |
| CM7 grade on every row | **yes, but over-reaches** | m1 |
| CM8 / D8 placement | **yes** | Task 1 is slice B's first commit (plan:106, 178-186), matching spec:1179-1180. See m4 for the stall path. |
| X2/Cm3 checkpoint | **code yes, state no** | Extracted asserts pass, and the mutation goes red. M3 covers the state. |
| X3 hollow page | **yes** | plan:691-698 |
| X4 practice order | **yes** | plan:937-944 |
| X6 CI caller timing | **yes** | plan:911-918. M3 is the remaining CI-red path. |
| Cm2 rc ranking | **yes** | plan:901-904. `_row("1",1,0)` and `_row("1",0,0)` raise (asserts at 894-895 pass). |
| Cm5, Cm7, Cm8, Cm9 | **yes** | plan:412-415, 233-238 + 667-672, 773-778, 680-684 |

**"Five slice PRs vs the spec's PR 1" — not an owner decision.** The spec uses "PR 1" as the milestone's
deliverable name throughout §7. The only delivery-shape rule it records is D8's *placement* (spec:1147, *"A
CORRECTION LANDS WITH THE WORK THAT FOUND IT, NOT IN A SEPARATE PR"*) and its first-commit bound
(spec:1179-1181). The plan keeps both. Slicing changes no goal, deliverable or falsifier, and `dev-process.md`
makes delivery shape a Phase 2 (autonomous) matter. The one residue is m4.

**Ran clean at `c316d97a`:** `check-docs.py`, `check-anchors.py` and `check-plan-file-tags.py`, each rc 0.

VERDICT: NOT CONVERGED
