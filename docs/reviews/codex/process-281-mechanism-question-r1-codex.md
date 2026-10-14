<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None found.

## High

**H1 — The new classification rule is false.** `docs/review-method.md:198–203`, repeated in skill step 2a and the dashboard.

Counterexample: a rule governs an existing, finite enum `{ready, failed, cancelled}`. Its first enumeration documents only `ready` and `failed`. An exhaustiveness pass discovers `cancelled`; documenting that branch completes the rule without changing its mechanism. The pass returned a **new member**, yet the finding was genuinely branch coverage.

Finiteness means enumeration *can terminate*, not that enumeration cannot discover anything. The asserted deduction therefore mandates the wrong classification. It also supplies no qualification for an out-of-scope discovery or disposition for a pass that cannot run. Replace automatic reclassification with a scoped investigation of whether redesign removes the recurring defect.

**H2 — Step 2a prescribes a card the repository refuses.** `.agents/skills/improve-codebase-architecture/SKILL.md:73–76`.

I translated its three options into an `AskUserQuestion` payload, retaining its labels and supplying substantive descriptions:

- `python3 scripts/check-selection-card.py`: **rc=2**.
- `bash .claude/hooks/enforce-selection-card.sh`: **rc=2**.

Both rejected the missing recommendation and missing question-shaped final option. A control adding `(Recommended)` to A and `D — I have a question about these` passed, **rc=0**. The template needs those elements.

## Medium

**M1 — “Five rounds” does not match the named rounds.** `docs/review-method.md:198–210`; `docs/dashboard-entries.md:14846`.

Rounds **11, 12, 13 are three numbered rounds**. PR #371’s `ab53945a` repeats “Five consecutive rounds (11, 12, 13),” so copying its assertion does not establish the measurement. Five reviewer passes or five refuted claims could be defensible units, but neither is five numbered rounds. State the unit and enumerate its witnesses.

**M2 — The index additions displace more previously reachable memory.** `docs/memory/MEMORY.md:12,34`.

Measured against `origin/master`:

| Measurement | Before | After | Increase |
|---|---:|---:|---:|
| Bytes | 25,884 | 26,440 | 556 |
| Characters | 25,082 | 25,619 | 537 |

The new rows occur early and remain reachable; existing tail content loses that space. A 25,000-character prefix simulation moves the cutoff from the historical stage links back into “Reservation release.” The defect is this branch’s additional displacement, not the pre-existing overrun. Compact the index enough to pay for these additions.

**M3 — The enforcement caveat falsely claims guards do not read these instructions.** `docs/dashboard-entries.md:14854–14855`; commit `46d4c058`.

`check-docs.py` includes `docs/review-method.md` in `living_docs()` and reads it for structural checks. `check-explainer-delivery.py` reads **every** `*/SKILL.md`, including this skill; I traced that actual read.

Neither guard enforces the new classification or mechanism-first decision. That narrower caveat is supportable. “No automated check reads the review instructions” and “No guard reads the skill” are false.

**M4 — A leading falsifier is constructible.** `docs/dashboard-entries.md:14855–14856`.

The particular #281 predicate involving *next-round findings* is necessarily retrospective. Failure of the new process instruction is not: inspect a completed thrashing-armed Phase 6 review and its first emitted card. An instance-only card, or no mechanism card, already violates step 2a before another round starts. Name that leading observation instead of claiming failure can only be observed later.

**M5 — Step 2a conflicts with the surrounding workflow.** `.agents/skills/improve-codebase-architecture/SKILL.md:48–92`.

Step 2 first unconditionally instructs the agent to present candidates and ask which to explore. Step 2a then says its mechanism card must come first. Step 3 assumes the owner selected a candidate and provides no continuation for “keep narrowing” or “accept and record.”

The skill also does not explain how to establish its arming condition; its offered “tell” is H1’s invalid classifier. Put the conditional branch before the candidate presentation, cite the actual thrashing criterion, and specify each disposition’s continuation.

**M6 — The rescued deletion memory contains a false filesystem test.** `docs/memory/verify-the-other-copy-exists-before-deleting.md:29–35`.

“Same inode **or** `links=1`” does not establish that two paths identify one file. I created two independent, byte-identical files: both had `links=1`, their inodes differed, and deleting one left the other intact.

Compare resolved targets and device/inode pairs. Link count alone cannot establish aliasing.

## Low

**L1 — The whole-directory symlink claim is inaccurate.**

`.claude/skills/` is a real directory. Its individual `improve-codebase-architecture` entry is the symlink:

```text
../../.agents/skills/improve-codebase-architecture
```

The substantive “one file, two paths” claim holds for this skill. Correct the directory-level explanation in commit `46d4c058`.

**L2 — One named same-day dashboard section does not exist.** `docs/dashboard-entries.md:14879–14881`.

At the inspected refs, `plugins-handoff-citations` has one `## 2026-10-13` section; `backlog-249-260-fixes` has **zero**. Its supplied worktree also lacks that heading. Keep the merge hazard warning, but correct its claimed witnesses. Put the warning in merge-facing instructions as well; a dashboard entry alone does not guarantee the second merger reads it.

## Checked and found SOUND

- Subject reproduced: **six files, 232 insertions, zero deletions**, HEAD `d3324f86`.
- Round **11** is a supported earliest witness: its Phase 6 artifact already names the root cause. The new document does not claim round 9.
- The skill alias resolves to the edited `.agents/skills/` file; its new relative link resolves.
- Project-local ownership is supported by the tracked file and alias. No duplicate architecture skill was found in installed-plugin paths. The frontmatter itself contains only `name` and `description`, not `projectSettings:`.
- All **three rescued files**, including the complete `MEMORY.md`, are byte-identical to `rescue-two-uncommitted-memories`.
- Dashboard heading count independently reproduced: **306 → 307**.
- Documentation, explainer-delivery and anchor audits passed under Python **3.12.9**.
- The initially timed-out self-test-count audit passed on a pinned-interpreter retry: **52 declared script counts verified**.
- Working tree remained clean. No review file was written.

## CANNOT RUN

**These are failures of verification; treat this as NOT RUN, not a passing suite.**

- `check-test-counts.py --results jest-results.json`: no results file. A Jest generation attempt produced no results before being stopped.
- Full `check-plan-code.py --mutate .`: timed out at **180 seconds during control runs**, before producing a mutation verdict. No population-wide mutation coverage established.
- Exact PR-event/body-file variants of the two PR-only checks: no PR payload exists. Local `--base origin/master` runs were performed instead: dashboard entry passed; review-recorded rejected the unreviewed skill change, as expected.

## Instruments

Read the complete committed diff, both subject commit messages, PR #371’s relevant commits and architecture artifact; compared rescued blobs; measured bytes, characters and heading counts; inspected symlinks and plugin installations; traced guard reads; exercised the selection checker and hook with a green control; reproduced the link-count counterexample.

Executed all **49 distinct single-line `python3 scripts/check-*` commands** extracted from CI. Initially **47 passed**, one lacked Jest results, and one timed out; the latter passed on retry. Commands comprised:

- Audit and self-test: `python-pin`, `test-counts`, `backlog-closure`, `review-rounds`, `anchors`, `memory-link`, `rc-contract`, `surface-recall`, `features`, `plan-file-tags`, `theme-token-coverage`, `selftest-counts`, `fixture-variation`, `main-drivable`, `storage-independence`, `group-claims`, `function-revokes`.
- Self-test only: `review-recorded`, `guard-coverage`, `vocabulary-collisions`, `banner-armed`, `dashboard-entry`, `plan-code`.
- Audit only: `docs`, `arch-findings`, `gate-falsifiability`, `roadmap-consistency`, `ratchet-contract`, `explainer-delivery`, `plan-task-order`, `producer-enumeration`, `storage-grant-pin`.

Names above denote `scripts/check-<name>.py`. The three multiline CI commands were addressed separately as stated under CANNOT RUN.
