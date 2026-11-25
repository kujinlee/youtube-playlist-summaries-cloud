Reviewed head: 8ccc6068d6faeb7875702a3b2e4f519457bbd1b7

# dashboard-retire spec — round 6 — Claude half (adversarial)

Subject: `docs/superpowers/specs/2026-11-24-dashboard-retire-design.md` at `8ccc6068`, the Phase 6 fold (option (b),
one file per ask). This round is past the round cap (`review-method.md` §0 Q4c), so only a BLOCKER changes the spec.
The MAJOR and MINOR findings are ranked honestly and are FILE candidates.

## What I tried to refute, and what held

| Claim | Result | Evidence |
|---|---|---|
| The goal tree can read both sources in S1 | HOLDS | `needs_from_dashboard` is at `scripts/goal-tree.py:1305` and goes through `_sibling("gen-dashboard")`. The source loop at `:1563` is `for key, rel, fn in (("dashboard", DASHBOARD_REL, …), ("backlog", …))` with `(root / rel).read_text`, so a directory source needs a new branch there, as §4.2 says. The NOT READ path for problems is at `:1572`–`:1574`. The `(source, ref)` diff is at `:1165`–`:1168`. The served page builds from a full `git clone --shared` plus checkout of origin/master (`scripts/regen-pages.py:45`–`:48`), so a filesystem read of `docs/asks/` sees the merged tree |
| compaction-state can count both in S1 | HOLDS | `pending_asks` at `scripts/compaction-state.py:473` and `_open_regular` at `:343` (`O_NONBLOCK`, `fstat`, `S_ISREG`, cap) are as cited. `MAX_STORE` is at `:143` (8 MiB; the store is 1.72 MB) |
| `PAGE_SOURCES` directory support already exists | IT DOES NOT — the spec correctly calls it new mechanism | `scripts/explainer-serve.py:243` is files only; `/_stale` takes `max(… for s in sources if (REPO / s).is_file())` at `:2078`–`:2080`; the coverage case at `:3197`–`:3199` asserts every source `is_file()`. The comment at `:252`–`:256` already named directory support as "a real change to this file". `STALE_EXEMPT` (`:270`) and its equality case (`:3203`) are unaffected, because `goal-tree` keeps non-empty sources |
| `check-reference-namespace` misses `docs/asks/` | HOLDS | `SCOPE` at `scripts/check-reference-namespace.py:111` is an allow-list; the store's exemption reason is at `:61` |
| `decisions` / `decision_errors` can run over an ask body | HOLDS, with one unstated argument | `decision_errors(plain, category)` (`scripts/check-dashboard-entry.py:455`) returns `[]` unless `category == "needs-you"`. The §2.4 caller must pass `"needs-you"`, or every warning case passes vacuously. That is plan-level, not a finding |
| L1 fails loudly | THE MISMATCH IS LOUD. ITS DIAGNOSIS AND REPAIR ARE NOT IMPLEMENTABLE AS WRITTEN | M1 |
| The S2 cutover race is "residual" | REFUTED | M1 |

## BLOCKER

### B1 — The fold deleted K7 and K8. The coordinator record says they were kept, and S3's proof still depends on K8.

**Evidence.** At `f63709f3` the Kept table had `| K7 | NO-REVIEW: is still parsed by one definition |` and `| K8 |
nothing still EXECUTES or LINKS a retired thing |` (spec lines 272–273 at that commit). `git diff f63709f3 8ccc6068`
shows both rows removed (`-| K7`, `-| K8`) and no row added back. The table at `8ccc6068` runs A1, F1, L1, C1, K4,
K5, K6 (spec `:290`–`:296`) and stops. Yet:
- the fold record says "Kept with a falsifier each: K4–K8 (… K7, K8 unchanged)"
  (`docs/reviews/coordinator/dashboard-retire-spec-r4-phase6-coordinator.md:71`);
- S2's proof cites "K4–K7" (spec `:409`);
- S3's proof is "K8, including its seeded cases" (spec `:410`);
- §4.3 says "K8 inspects executable loads and links only (§3)" (spec `:397`–`:398`). §3 no longer defines it.

**Why BLOCKER.** K8 is the only gate that catches a surviving by-filename load, hook command, workflow `run:` line
or argv naming `gen-dashboard.py`, `check-dashboard-entry.py`, `regen-dashboard.sh` or the old skill. That is the r1
Codex BLOCKER class (§1.2's loader table). K7 is the only falsifier that `NO-REVIEW:` survives the `exemption_reason`
default-marker change in S2. A plan written from this spec has no definition to build either gate from. S2 and S3
would then delete the code these gates protect, with no gate in place. This is a regression the fold introduced,
not a design question.

**Fix.** Restore the two rows verbatim from `f63709f3`. Then update K8's retired-path list so it names
`check-dashboard-entry.py` as retired from S2, after the rename, and the `dashboard` skill as renamed. Under (b),
neither change alters the gate's meaning.

## MAJOR

### M1 — The cutover's L1 window is the normal case, not a residual one. L1's message and restore command cannot be built from a SHA-256 constant.

**Evidence and reasoning.**
1. **Every PR that is open when S2 merges carries an entry.** R1 forces one (`scripts/check-dashboard-entry.py:813`).
   Each such PR's green CI ran under the old workflow. Each one that merges after S2 therefore turns master red, once
   per PR. That is every in-flight PR at cutover time, not "a PR whose last CI ran BEFORE S2" as an edge case
   (spec `:212`). The spec's own prior-art row counts 73 PRs touching the store (`scripts/batch-ci.py:82`).
2. **The pin can be stale at S2's own merge.** The pin is "written … after S2 last merges master in" (spec `:214`).
   Any PR that merges to master between that point and S2's squash adds an entry, because R1 still holds. S2's
   header edit (lines 3–6) does not conflict with an appended entry, so S2 squash-merges cleanly. Master's store then
   differs from the pin the moment S2 lands, and C1 never saw that entry: GitHub does not re-run PR CI when the base
   moves. `check-merge-ready.py` pins the head commit only (`--match-head-commit`). Its `MERGEABLE_STATES`
   (`scripts/check-merge-ready.py:105`) refuses BEHIND, but only if branch protection is strict. The spec does not
   say whether it is. If protection were strict, the stale-CI race in point 1 could not happen either, so the spec
   assumes non-strict protection, and under non-strict protection point 2 is live.
3. **The diagnosis and repair cannot be built as written.** L1 holds only `LEGACY_STORE_SHA256` (spec `:214`). A
   digest cannot print "the bytes that differ from the pinned file" (spec `:212`, `:292`), because the pinned bytes
   are not available to it. The restore command `git checkout <S2 merge commit> -- docs/dashboard-entries.md` has
   two problems. (a) S2 cannot hardcode its own squash SHA. (b) In case 2, that commit's store does not hash to the
   pin, so following the printed repair leaves master red. Finding the right commit at runtime would mean walking
   history for a blob whose SHA-256 matches, and the spec says "no kept check walks history" (spec `:305`).

**What still holds.** No ask is lost silently. The digest mismatch is loud on master and on every later PR. That is
why this is MAJOR and not BLOCKER.

**Fix (three small edits).**
- Pin the git BLOB id as well: `LEGACY_STORE_BLOB = git hash-object` of the frozen bytes, written once in S2. L1 then
  prints `git diff <BLOB> <HEAD's blob>` and the restore command `git cat-file blob <BLOB> > docs/dashboard-entries.md`.
  Both are correct whatever commit S2 lands as, and both work with `fetch-depth: 0`.
- Make the S2 merge step check that master's store has not changed since the pin:
  `git diff <pin-base> origin/master -- docs/dashboard-entries.md` must be empty. Otherwise S2 must re-merge master
  and re-pin before it merges.
- Add a post-merge cutover step: merge master into every PR still open, so its CI re-runs under L1 and it drops its
  entry, instead of letting each one redden master. Restate spec `:212` accordingly.

## MINOR

### m1 — `.gitkeep` is exempt from A1 by name, and F1 covers it.

A1 exempts `.gitkeep` (spec `:290`). F1 covers "a file in `docs/asks/` present at the merge base" (spec `:291`), and
`.gitkeep` is one. Two problems follow:
- Deleting `.gitkeep` when the first real ask lands is refused by F1 ("the file is gone at HEAD").
- An empty base is a prefix of anything, so `.gitkeep` can grow arbitrary text that A1 never reads. A question
  written there is invisible.

**Fix.** F1 applies to files matching the name rule only. A1 requires `.gitkeep` to be empty.

### m2 — The `## Answer` match is not pinned exactly.

"No `## Answer` line outside a code fence" (spec `:174`) does not say:
- whether trailing text is allowed (`## Answer — A`);
- whether leading space is allowed;
- what happens in a four-space indented code block, which the `FENCE` rule (`scripts/check-dashboard-entry.py:143`,
  `{0,3}` indent) does not treat as a fence.

A loose match closes an ask silently: it drops from NEEDS YOU. A strict match leaves an answered ask open, which is
safe.

**Fix.** State the rule as `line.rstrip() == "## Answer"` at column 0, outside a fence. Add cases for
`## Answer — A` (stays OPEN) and an indented `    ## Answer` (stays OPEN). Have the skill teach the exact line.

### m3 — A1 says it "reads HEAD's tree only", but `read_asks(dir)` lists the filesystem.

A1's text (spec `:290`) and `read_asks`'s signature (spec `:180`) disagree. In CI they are the same thing. Locally,
an untracked scratch file in `docs/asks/` fails A1, and an uncommitted deletion passes it. This is the same
working-tree-versus-committed confusion that `docs/CLAUDE.md` rule 3 warns about for the old gate.

**Fix.** Either say A1 reads the working tree, or have A1 list `git ls-tree HEAD docs/asks/` and pass `read_asks`
those names.

VERDICT: NOT CONVERGED
