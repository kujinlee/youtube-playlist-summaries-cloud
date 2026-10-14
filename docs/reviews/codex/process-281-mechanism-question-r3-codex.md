<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

**B1 — The “complete” three-way rule still says SAFE when deletion destroys the only content.** `docs/memory/verify-the-other-copy-exists-before-deleting.md:32–50,70–76`.

Measured after green independent-file and hard-link controls:

| Attack | Observed `stat -L` result | Rule says | Actual deletion |
|---|---|---|---|
| Real A; B is a dangling symlink | Different pairs, rc=0 | SAFE | A’s only content is lost |
| Directory A; B symlinks to A | Same pair, `links=3` | SAFE | Recursive deletion destroys the entire tree |
| Directory A; B is inside A | Different pairs | SAFE | Recursive deletion destroys B too |
| Replace A between observations; B symlinks to A | Observed pairs differ; current targets coincide | SAFE | Deleting A destroys the only current content |

The new proof gate makes this worse: line 44 permits the proof **only for same-inode, links==1**. Thus the dangling-link and replacement-race cases receive SAFE and bypass the very proof prescribed to catch unreliable observations. The directory exclusion protects the proof, but does not qualify the table’s SAFE verdicts.

I also changed the link count between individual observations: A reported 2, B subsequently reported 1; deleting A then lost the content. There is no coherent-snapshot requirement or disposition for conflicting counts.

**Fix:** remove unconditional SAFE verdicts from these observations. Require resolving, readable survivors; distinguish files from directory trees; verify the intended content independently; and apply that verification to every proposed deletion. Do not gate verification on the suspicious row alone.

## High

**H1 — “Deleting either DESTROYS it” is false, including in the newly corrected always-delivered row.** `docs/memory/MEMORY.md:12`; topic frontmatter and lines 35,76.

With `alias → real`, both followed stats have the same pair and `links=1`.

- Deleting `real` destroys the content.
- Deleting `alias` leaves `real` and its content intact.

Both directions were exercised. The hardened proof agrees: with A being the symlink and B the real file, it prints **B SURVIVES**, rc=0. The index and body therefore agree on the same false categorical implication, while the executable proof contradicts them.

Likewise, `links>=2` does not establish that **B** names another hard-link entry. I gave A an additional hard link elsewhere and made B reach A through a symlinked parent. Both reported `links=2`; deleting A made B disappear. Content survived through the third name, which is a narrower result than the supposed backup surviving.

**Fix:** make the rule about the particular directory entry being removed and the particular surviving path being verified. Link count counts entries; it does not identify which entry B uses.

**H2 — A failed `cat` still renders CANNOT RUN as a verdict, then returns success.** Topic file line 49.

Native reproduction, satisfying the stated same-pair/links==1 precondition:

1. A is a symlink to B.
2. B’s file mode is `000`.
3. Moving A succeeds.
4. B still exists, but `cat B` fails with permission denied.
5. The block prints **B IS GONE — RESTORE NOW**.
6. Restoration succeeds; the block exits **rc=0**.

A controlled `cat` returning 74 produced the same false verdict. Neither disappearance nor aliasing was established.

**Fix:** establish readability before moving anything, preserve failure diagnostics, and distinguish inaccessible content from a vanished path. An instrument failure must report CANNOT RUN / NOT RUN, not “B IS GONE.”

**H3 — Restoration is neither guaranteed nor protected against overwriting new work.** Topic file lines 45–50.

Two measured failures:

- Making A’s parent read-only after parking A caused the **real final `mv`** to fail. The block exited rc=1, left A parked, and supplied no CANNOT RUN recovery instruction.
- Creating a new A during the intervening read caused final `mv` to overwrite it silently. The new `NEW-PRECIOUS` content disappeared; the block exited rc=0.

The `$$` suffix is not an exclusive reservation. A pre-existing dangling symlink at that exact parking name passed `[ -e "$PARKED" ]` and was overwritten. A regular pre-existing parking file was correctly refused.

**Fix:** reserve parking storage exclusively, prevent destination overwrites, and check restoration explicitly. Handle interruption and restoration failure with an unmistakable NOT RUN result and the surviving parked location. Do not promise that restoration always succeeds.

**H4 — Withdrawn categorical claims survive elsewhere in the branch.** `docs/review-method.md:272–279`; `docs/dashboard-entries.md:14843–14858`.

The method narrows the historical claim to **“none explicitly proposed”**, then concludes that a fork **omitted the relevant option**, “which is what happened here.” That restores the stronger conclusion the preceding paragraph withdraws.

The dashboard remains more explicit:

- The eventual rebuild “was not one of the four options.”
- The menu omitted “the only item” that removed the problem.
- “A limited list runs out, a wrong shape keeps producing” cases.

The last statement is the withdrawn finite/terminating discriminator. The method’s own counterexample—two fully enumerated states with contradictory ownership requirements—refutes it.

**Fix:** propagate the narrowed historical claim and withdrawn discriminator through both documents. “Not explicitly proposed” does not establish unavailability, sole-remedy status, or counterfactual cost.

## Medium

**M1 — The new investigation card has no execution continuation.** `.agents/skills/improve-codebase-architecture/SKILL.md:145–166`.

The unnameable-assertion card replaces A with investigation. The routing paragraph still routes only **“A (redesign)”** into redesign grilling, and step 3 unconditionally starts interface design after candidate selection.

Choosing investigation therefore either reaches design prematurely or requires an invented continuation.

**Fix:** route investigation A to its evidence-gathering round, define its stopping condition, and return to the audit before offering a redesign.

**M2 — Scope narrowing can still satisfy the refutation test without repairing the defect.** Skill lines 116–121; `docs/review-method.md:229`.

Changing “complete for all supported inputs” to “complete for this smaller subset” excludes the witnessed counterexamples. The recurring refutation becomes impossible while previously supported behavior remains defective. The method’s unqualified “out of scope” exception supplies the escape.

**Fix:** require disclosure of removed coverage and its replacement contract. An out-of-scope dismissal should use a scope established before the finding, or explicitly record acceptance of the lost coverage.

**M3 — “19 of 19 NAMED invocations” has no reproducible named population.** `b310c470` commit message.

The message names no 19-item set. Its attached review enumerates **15** guard invocations; the predecessor’s message also enumerates 15. Those 15 reproduce green. Both current cards also reproduce green, but adding selected checker/hook runs to construct 19 would be my population definition, not the commit’s.

The message correctly declines to call this the CI suite. The remaining defect is provenance, not a demonstrated CI-equivalence claim.

**Fix:** publish the exact commands, arguments and card payload identities that constitute 19.

**M4 — The dashboard’s repository-wide figures remain stale.** `docs/dashboard-entries.md:14903–14905`.

At `b310c470`, tracked-file searches reproduce:

| Token | Published | Actual |
|---|---:|---:|
| `projectSettings:` | 3 files | **5 files** |
| `description:` | 193 files | **195 files** |

The newer review documents supply the additional members. Pin the measurement revision or define exclusions.

## Low

**L1 — Load-bearing source citations still do not resolve in this tree.** `docs/review-method.md:233–258`; skill lines 83–98.

The architecture artifact and `backlog-249-260` witnesses are absent here. Their relevant content reproduces from pinned commit `9dd9c985`, but readers following the published paths receive no dependency notice. This is separate from the known-true location of #281’s backlog row.

**Fix:** identify the source branch/PR and pinned revision at the first citation.

**L2 — The diagnostic commands still mishandle spaces and produce ambiguous status.** Topic file lines 32–37.

Substituting paths containing spaces into the unquoted `stat` command produced rc=1 and split-path errors. The quoted move proof handled those paths correctly.

Even with quoted arguments, `readlink real alias` printed one unlabelled target and returned rc=1. That does not distinguish which argument supplied the output.

**Fix:** quote every path and print a labelled result for each `readlink` observation.

## Checked and found SOUND

- **Three baseline rows reproduced:** independent files survive deletion of A; genuine A/B hard links survive; deleting the real target of a single-link symlink pair loses content. These witnesses do not establish completeness.
- **Both four-option cards passed the checker and hook**, rc=0, after a substantive green control, under both interpreter environments. Their instantiated actions were distinct:
  - Nameable: remove attribution / add another producer case / accept current errors.
  - Unnameable: investigate shared assumptions / repair cancellation cleanup / accept the leak.
- **The step-2 ordering fix works for established thrashing:** line 49 precedes presentation at line 54. An unarmed milestone review legitimately skips the audit; that permitted path is not a defect.
- **The H3 pointer repair works:** the withdrawal is scoped to the paragraph; the instruction points BELOW to “Can a redesign remove it?” at line 283, rather than to the symptom table.
- **The known-cases list no longer claims completeness.** A correctly scoped, fixed enum whose pass discovers an omitted `cancelled` member remains a branch-coverage case outside the listed exceptions. The open wording accommodates it.
- **Memory accounting reproduces exactly:** master **25,884 B**, subject **25,847 B**—37 B smaller. Every index Markdown target resolves. The deletion row retains a recognisable cleanup situation, although its test remains false as described above.
- **APFS clone:** different inode; content survived source deletion.
- **Firmlink exercised:** `/private/.../a` and `/System/Volumes/Data/private/.../a` reported the same pair and `links=1`; neither file entry was a symlink. Parking one made the other disappear; restoration recovered it. The deletion prediction held, but “everything else is a symlink” did not.
- **Proof controls:** directory pairs, B inside directory A, an initially read-only parent, missing A, and an existing regular parking file were refused with rc=2. Direct symlink chains and quoted space-containing paths restored correctly.
- **Binary/large reads:** a readable 16 MiB binary and 1 GiB sparse file produced B SURVIVES and restored successfully.
- **Historical witnesses:** pinned source documents reproduce the four candidates, A chosen after questioning A versus B, and the five selected claims distributed **1/2/2**.
- **Dashboard count:** **306 → 307** headings.
- **CI population:** 50 inline invocations, **49 distinct commands = 26 audits + 23 self-tests**.
- **Review gates:** `check-review-rounds` is green. The expected `check-review-recorded` red is not filed.

## CANNOT RUN

**These are verification failures—treat each as NOT RUN, never as a pass.**

- **Full CI suite:** 33 distinct inline CI commands were not invoked. Of the 16 invoked inline commands, `check-test-counts --results jest-results.json` could not perform its comparison.
- **Jest count comparison:** missing `jest-results.json`; rc=1, explicitly NOT RUN.
- **Full `check-plan-code.py --mutate .`:** not attempted; no mutation-coverage verdict for this tree.
- **PR-event forms / merge-ready:** no PR payload; NOT RUN.
- **Bind mounts:** not exercised; NOT RUN. Firmlinks were exercised separately.
- **Cross-filesystem hard-link experiment:** attempted APFS-to-`/dev` creation failed with EPERM before testing the cross-device restriction. Treat that experiment as NOT RUN. It did not produce the requested fixture.
- **Original owner-facing Phase 6 card:** unavailable directly; historical conclusions remain bounded by the pinned architecture record.
- **Dashboard regeneration:** the generated page is absent here; only its tracked source was verified.
- **Actual memory delivery:** `check-memory-link` returned rc=0 with its missing-harness-path warning. That is not evidence that this worktree’s corpus was delivered.

## Instruments

Reviewed **HEAD `b310c470`**, its commit message first, both required earlier commits, all four prior reviews, the fold, and the whole-branch changes. Historical source reads used pinned Git blobs at `9dd9c985`.

Repeated the following named set under **Python 3.14.4** and **3.12.9**, with a `python3` PATH shim covering subprocesses:

`check-docs`; `check-anchors`; `check-anchors --self-test`; `check-arch-findings`; `check-backlog-closure`; `check-explainer-delivery`; `check-features`; `check-gate-falsifiability`; `check-plan-file-tags`; `check-rc-contract`; `check-rc-contract --self-test`; `check-roadmap-consistency`; `check-surface-recall`; `check-memory-link`; `check-selection-card --self-test`.

All returned rc=0 in both environments. Additionally ran `check-review-rounds` (0), `check-review-recorded` (expected 1), and `check-test-counts --results jest-results.json` (CANNOT RUN, 1). Guards used closed stdin; card checker/hook runs used payload files. Results matched across interpreters.

Filesystem experiments used disposable scratch content outside the repository. Native failures and injected failures are distinguished above. Known-positive controls preceded card and filesystem negatives; source searches used verified positive controls.

**NOT CONVERGED: 1 Blocking, 4 High, 4 Medium, 2 Low. Worktree unchanged. No review file written.**
