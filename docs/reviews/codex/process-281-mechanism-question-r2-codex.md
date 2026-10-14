<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established.

**NOT CONVERGED: 4 High, 3 Medium, 2 Low.**

## High

**H1 — Step 2a assumes that thrashing identifies a recurring claim, and supplies no path when it does not.** `.agents/skills/improve-codebase-architecture/SKILL.md:62–92`.

The arming condition establishes fix-induced findings in one component. It does not establish that they refute one identifiable assertion.

Counterexample: a lock-order repair introduces stale reads; its snapshot repair introduces cancellation leaks. Only designing a single-owner queue reveals the hidden ownership assumption connecting them. Before that exploration, an agent can name several plausible claims, but cannot determine which one the mandatory option must stop making. The skill meanwhile postpones interface design until after selection.

The rule also permits a superficial satisfaction: withdraw the disputed assertion while retaining the defective behavior. Conversely, a redesign that makes a required guarantee true preserves that claim and fails the literal “STOPS MAKING” test.

For this incident, r11’s coordinator document already supplies **“Stop attributing: name every heading, claim none.”** Following the new instruction could therefore surface that candidate. That supports an evidence-specific instruction, not the unconditional rule. Require a witnessed assertion and a proposed behavioral change; provide an investigation outcome when their connection remains uncertain.

The list need not become mathematically unbounded: recorded findings are finite. The unresolved problem is choosing and validating the claim, not listing every conceivable option.

**H2 — The correction overstates what candidate 2 proves, then overstates what it excludes.** `SKILL.md:75–86`; `docs/review-method.md:232–246`.

The read-only PR #371 source explicitly says the candidates were **“NOT designed here.”** Candidate 2 proposes one child-verdict module with named states. That establishes a structural refactor being considered; it does not establish that its behavior would dissolve the mechanism defect.

It also does not establish the opposite claim: that the eventual remedy was unavailable through those candidates. A candidate-2 design using observational states and quoted diagnostics, without causal attribution or exhaustive-world assertions, fits its published description and removes the recurring claim.

Of the other candidates, mandatory attribution addresses the empty-failure contradiction; the combiner addresses stream handling; retiring `run_suite` addresses the helper. None explicitly proposes abandoning completeness. But **“not explicitly proposed”** is narrower than **“not among them at all”**, especially for an undesigned verdict module.

The source supports A being chosen after the owner questioned A versus B. It does not support treating B’s mechanism effect, the exclusion of the eventual remedy, or the two-round counterfactual cost as measured facts. Preserve that uncertainty rather than reversing one categorical diagnosis into another.

**H3 — H4 withdraws one deduction but introduces another false discriminator.** `docs/review-method.md:207–209`.

“Finiteness means the pass TERMINATES” requires a terminating enumeration method over a fixed, discoverable population. Finiteness alone does not supply that method.

More substantially, **“a wrong shape generates them, so the pass never terminates”** is false. Consider two fully enumerated states with contradictory ownership requirements. The mechanism is wrong; an exhaustive pass can terminate immediately without discovering another member. A redesign can remove that contradiction.

This is a third case beyond an out-of-scope discovery and a cannot-run pass: **a completed, finite enumeration containing a mechanism defect**. Retain “new members warrant investigation,” but remove the categorical finite/terminating versus wrong-shape/nonterminating distinction.

**H4 — The replacement filesystem command still fails toward a false backup.** `docs/memory/verify-the-other-copy-exists-before-deleting.md:29–52`.

All three tabulated cases reproduced. The direct-symlink case did not:

```text
stat without -L: target and symlink have different device/inode pairs
stat with -L:    both resolve to the same pair
```

In a scratch directory, deleting the target left the supposed alternative path dangling, with no surviving content. Checking the parents did not reveal this direct file symlink.

Sequential observations also lack a stability condition. I measured one path, replaced its target, then measured its alias: the observed pairs differed although both paths subsequently referenced the same new file.

The device/inode comparison is sound for the objects actually observed. It is insufficient as the prescribed deletion check. Follow file symlinks, distinguish link entries from their targets, and verify the surviving content after a reversible move. The frontmatter still emphasizes link count despite the body establishing that it cannot discriminate these cases.

## Medium

**M1 — The new 2/2/1 distribution does not match the five named witnesses.** `docs/review-method.md:214–217`.

| Named witness | Round-document evidence |
|---|---|
| Header-based extraction misses CPython output | r11 Claude H1, including `ExceptionGroup` |
| Any indented run becomes a traceback | r12 Codex H1 |
| ASCII validator drops `Échec` | r12 Codex H1 |
| Identifier validator drops `bad-name` | r13 Codex H1 |
| Three-world enumeration has a fourth producer | r13 Codex H2 |

These selected witnesses distribute **1/2/2**, not **2/2/1**. The earlier redesign commit enumerated a different five-item selection, including another r11 example. The fold changed the examples without updating their distribution.

The three-round bound and r14’s additional forged-attribution witness are supported.

**M2 — The dashboard retains the withdrawn mechanism-first rule and an invalid leading falsifier.** `docs/dashboard-entries.md:14860–14875`.

The skill now requires auditing the candidate list for a removal option. The dashboard still says the **opening question** must be rebuild/patch/accept and that a choice concerning one small piece is already a violation.

A list can contain both a narrow repair and an explicit claim-removal candidate. Its ordering or introductory question does not establish omission. Inspecting whether the declared removal candidate exists is leading; judging whether it actually removes the recurring cause requires evidence beyond the card’s shape.

The “convened by this signal” qualification protects ordinary milestone reviews when their arming is recorded correctly. The false-positive problem remains for compliant thrashing reviews.

**M3 — The candidate audit still appears after the instruction to present and ask.** `SKILL.md:49–60,90–92`.

Step 2 tells the agent to present candidates and ask the owner which to explore. Step 2a then requires adding the missing option **before carding anything**.

Calling this an audit removes the old disagreement about which card takes precedence, but does not repair the execution order. Move the audit before step 2’s presentation instruction, or explicitly make completing 2a a prerequisite to that presentation. The answer continuations themselves are now stated.

## Low

**L1 — M4’s search scope is still misstated.** `docs/dashboard-entries.md:14889–14891`; fold commit message.

The committed tree contains `projectSettings:` in **three tracked files**, including the corrected dashboard paragraph itself. The same tracked-repository search finds `description:` in **190 files**.

The claimed **0/21** result reproduces over tracked `.agents/skills` files. It supports absence of the alleged frontmatter key, but is not a repo-wide measurement. State that scope.

**L2 — “21 of 21 … as a suite” has no reproducible CI denominator.** Fold commit message.

The specified CI instrument contains **49 distinct single-line commands**: 26 audits and 23 self-tests, plus three multiline checks. One inline command occurs twice.

No invocation set is supplied that derives 21 as this suite’s denominator. The separately declared NOT RUN checks do not reconcile it. Name the measured invocation set rather than publishing “21 of 21” as evidence of the required suite.

## Checked and found SOUND

- **Card replacement:** a substantive green control passed first. The instantiated A/B/C/D template then passed both `check-selection-card.py` and `enforce-selection-card.sh`, **rc=0**. The checker’s self-test passed **59/59**. My A removed attribution, B added another exception case, and C retained behavior while recording acceptance: three distinct actions. Generic placeholders alone do not establish distinctness.
- **Memory accounting:** master **25,884 B**, pre-fold **26,440 B**, fold **25,591 B**. Additions **556 B**; compaction **849 B**; net reduction **293 B**. The three old rows measured **602/413/445 characters**. Every index Markdown target exists. The removed operational details remain in the three linked topic files; the revised descriptions retain usable situations.
- **Guard caveat:** both claimed reads are real. Neither implements the new semantic process rules. Both impose structural constraints: a missing documentation link is refused, and an added delivery-command fence in this skill is refused. These were exercised in scratch copies after green controls.
- **Filesystem controls:** independent files gave `links=1,1` and different pairs; hard links gave `links=2,2` and equal pairs; symlinked parents gave `links=1,1` and equal pairs. An APFS clone had a different inode and survived deletion of its source.
- **Remaining corrections:** `.claude/skills` is a real directory with **21 child symlinks**; the edited skill paths identify the same file. The skill has zero `&lt;`/`&gt;` occurrences. `backlog-249-260-fixes` has zero exact `## 2026-10-13` headings. The arming definition and A/B/C continuations are present.
- **Dashboard:** heading counts reproduce **306 → 307**. The live path resolves into the main checkout; `.gitignore:154` ignores it, and it is untracked. Its content includes the correction. Regeneration to scratch produced **307 entries** and left this worktree clean.
- **Pinned suite:** after retrying the timed-out count audit, **49 distinct commands green**; the expected review-coverage red is not filed as a defect. The count audit verified **52 scripts by running their self-tests**.

## CANNOT RUN

**These are verification failures; treat each as NOT RUN.**

- `check-test-counts.py --results jest-results.json`: results file absent.
- Full `check-plan-code.py --mutate .`: timed out at **180 seconds**, under both interpreter sweeps, without a coverage verdict.
- Exact PR-event/body-payload variants: no PR payload exists. Local base forms were run.
- Default-interpreter parity: `python3` initially resolved to **3.14.4**. Its results were provisional. The suite was subsequently repeated with **3.12.9**, including a `python3` PATH shim for subprocesses.
- The original Phase 6 card was not directly observed; its content is bounded by the architecture document’s record.
- Bind-mount and firmlink cases were not exercised. The direct-symlink, replacement-race and APFS-clone measurements do not establish those cases.
- The historical assertion that regeneration changed no Git state lacks a before/after record available here. Current ignored/untracked status and clean scratch regeneration were verified.

## Instruments

Read both required commit messages first, both round-1 reviews, the fold and whole-branch diffs, and PR #371’s source documents read-only.

Executed all **50 inline CI invocations, representing 49 distinct commands**, plus local forms of the two PR-only checks and the mutation invocation: **53 invocations / 52 distinct commands**. Retried the self-test-count audit successfully. No listed command was silently skipped; unresolved checks are identified above.

Used controlled card payloads, scratch filesystem cases, production guard functions, tracked-blob byte measurements, scoped searches with known positives, and scratch dashboard generation. Searches distinguish tracked skill scope from repository scope.

**HEAD remained `e3a6aad8`; worktree clean. No review file was written.**
