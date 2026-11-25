Reviewed head: 1fdbd53c560f3424921112d8e22c79fa064c3b32

# goal-node-tree S2 (Tasks 5–11) — round 1, CLAUDE half

**Subject:** `git diff origin/master...HEAD` on branch `goal-node-tree-s2` (PR #637). `docs/anchors.md` is deleted, its
names become nodes in `docs/features.md`, and every reader moves to the tree. ADR-0016 is accepted.
**Mandate:** refute it. The spec is approved and is not re-argued here.

## What I tried to break, and what happened

| # | Attempt | Result |
|---|---|---|
| 1 | **Card set.** I ran `gen-goals-page.collect` on a master copy and on the branch and diffed the card ids. | Both have **15 cards** and the same set. The one difference is that `g-dev-speed-first` becomes `g-dev-speed`. Each card's documents, ADRs and backlog rows are equal. Only the order differs: the sort key is `(touched, len(docs))` at `scripts/gen-goals-page.py:538`, and touched dates move with the branch. |
| 2 | **Armed set.** I compared master's hand-kept list with the branch's derived `armed(anchored_slugs) − UNARMED`. | They are **equal, 13 slugs each**. |
| 3 | **Second header reader (T9).** `check-goal-status.living_documents` keeps its own `ANCHOR_LINE` (`scripts/check-goal-status.py:137`, unanchored, `HEAD_LINES = 18`). `check-anchors.anchored_slugs` reads at most 10 lines with a `^>` anchor. I diffed their (document, slug) sets over the living tree. | **Identical** on the 66 documents, with nothing on either side alone. See MINOR-4. |
| 4 | **An unknown slug in a probe copy:** `Anchor: \`no-such-node\``. | check-anchors exits 1 with the right message. check-goal-status also exits 1, but its message is the wrong one (MINOR-2). |
| 5 | **An Anchor on a `was:` slug** (`dev-speed-first`). | Exits 1. The message names the current slug `dev-speed`. |
| 6 | **Renaming a node and recording `was:`.** | check-anchors exits 1 on the 2 documents that still name the old slug. check-goal-status exits 1 with a stale exemption. check-features exits 0, which is correct. |
| 7 | **A stale UNARMED entry**, i.e. a slug that is not a current node. | Exits 1 via `stale_exemptions` (`scripts/check-goal-status.py:115`). |
| 8 | **Task 11 Step 2 searches** (both `git grep` commands, using the plan's exclusions). | Both print nothing (rc 1). No reader of `anchors.md`, `parse_registry`, `registry_anchors`, `ANCHORS_MD` or `anchor_slugs` remains. |
| 9 | **Task 11 Step 3, the retired-slug search.** | Every line falls in an allowed class: `was:` (`docs/features.md:165`), quoted request lines, the goal-tree fixture (`scripts/goal-tree.py:5018`), and exactly one `## GOAL dev-speed-first` (`docs/goal-threads.md:161`, the S2 exception). |
| 10 | **Mutation anchors, all manifests.** I resolved every `edits[i][0]` against its file. | **6755 edits. Each is found exactly once, so none is unbound or ambiguous.** |
| 11 | **Mutation sweeps**, run in a scratch copy of the tree with `node_modules` linked. | check-anchors 12/12 killed. check-goal-status 10/10. gen-goals-page 32/32. gen-features-page 61/61. check-features 59/59. Every kill is attributed to the case it names, with 0 survivors. **gen-backlog-page: NOT RUN.** The harness refused it locally (about 45.9 min against a 10 min local budget, 84 mutations) and measured nothing. That one is left to the PR's CI shards. |
| 12 | **Repo checks on the branch.** | All seven exit 0: check-docs, check-fixture-variation (2587 params), check-hook-commands, check-vocabulary-collisions, check-ratchet-contract, check-guard-coverage, check-doc-citations. The self-tests of the six touched scripts pass. check-shipping-sets `--self-test` passes 170/170, but took longer than 270 s, so I ran it in the background. |

**The builder's deviations, judged:**
- **T7, the hermetic probe** (gen-features-page builds a world by symlinking the real adr, backlog and features files): sound. It reads the real corpus without writing to it.
- **T8, `anchored_slugs` as the one reader** (plan choice C10): sound. Four consumers now share it.
- **T9, the kept `ANCHOR_LINE`:** not a defect today, because the two readers agree. It is a latent second implementation (MINOR-4).
- **T10, the goals hook arm that was dropped:** a real gap, but a small one (MINOR-1).

## Findings

**No BLOCKER. No MAJOR.**

### MINOR-1 — the goals regen hook has no `docs/features.md` arm, and its header prose still describes the registry

The goals page now takes each card's purpose, ADRs and names from `docs/features.md`. However, `.claude/hooks/regen-goals-page.sh:35-38` fires only on `docs/adr/*.md`, `specs/*.md`, `plans/*.md` and `gen-backlog-page.py`. So an edit to `docs/features.md` alone, such as renaming a node, adding `adrs:` or rewording a purpose, does not rebuild `/goals` until some other trigger fires.

The harm is limited, because `regen-pages.sh` rebuilds every page on each `gh pr merge`. Until that merge, though, the page is stale.

The header comment is also out of date:
- `regen-goals-page.sh:13` still lists "five — the registry, …".
- `regen-goals-page.sh:18` still lists "an anchor claimed by no document, a ROOTS key outside the registry". The first of those failures is rule R4, which this slice dropped.

**Fix:** add a `*/docs/features.md|docs/features.md) ;;` arm, and rewrite lines 13–18 to say: the tree, every spec/plan/ADR header, the milestone spines, and ROOTS/DEPENDS.

### MINOR-2 — check-goal-status arms an unknown slug and asks for the wrong repair

`armed()` (`scripts/check-goal-status.py:110`) returns every slug that a document names, unfiltered. A typo such as `Anchor: \`no-such-node\`` therefore becomes an armed goal. The check then fails with "declare a Status", when the real defect is "that is not a node". The gate's overall verdict is still correct, because check-anchors G1 exits 1 on the same input. Only the diagnosis is wrong.

**Fix:** have `armed()` take `current_slugs(nodes)` and filter `slug in slugs`, since `main` already reads `nodes` at line 292. Add a case where an unknown slug is not armed.

### MINOR-3 — `globals()["armed"]` works around a parameter that shadows its own function

At `scripts/check-goal-status.py:301`, `main(..., armed=None)` shadows the module function `armed`, so the function is reached through `globals()`. This is fragile: renaming either one breaks it without warning, and readers trip over it.

**Fix:** rename the parameter (for example `armed_override`) or the function (`derive_armed`), then call it directly.

### MINOR-4 — `living_documents` keeps a second header reader (T9)

`scripts/check-goal-status.py:137-138` reads the header with `ANCHOR_LINE = r"\*\*Anchor:\*\*\s*`…`"`, unanchored, over 18 lines. `check-anchors.ANCHOR` (`scripts/check-anchors.py:76`) is `^>`-anchored with the full `— **ADR:**` shape, over 10 lines. The two agree on all 66 documents today (attempt 3). They will disagree on a document that has an `Anchor:` on line 11–18 or one not in blockquote form. In that case check-goal-status would arm a slug that check-anchors never saw.

**Fix:** have `living_documents` take each document's anchor from `anchored_slugs` (inverted to rel → slug), and delete `ANCHOR_LINE`. Alternatively, record why two readers are intended, and add a case where the two must agree.

### MINOR-5 — leftover registry vocabulary and an ADR index row that contradicts its ADR

- **The ADR index row.** `docs/adr/README.md:34` still shows ADR-0010 as **PROPOSED**. This branch sets ADR-0010's own status to `accepted 2026-11-24`. **Fix:** update the row to ACCEPTED, partly superseded by ADR-0016.
- **gen-goals-page prose.** Comments at lines 203, 450, 487 and 516 still say "the registry". The local at line 469 is still named `registry`. **Fix:** say "the tree's goal nodes", and rename the local to `goal_rows`.
- **ADR-0010's body** (for example lines 25, 30, 36, 127–129) still speaks of a registry. This is acceptable as history, since ADR-0016 supersedes those parts and the ADRs are not to be re-argued. No change is needed.
- **`docs/marketplace/inventory.json`** (lines 586, 783, 1639) still mentions `docs/anchors.md`. These are point-in-time measurement records, which the plan's own search excludes. No change is needed.

## NOT RUN

- **The gen-backlog-page mutation sweep.** The harness refused it locally and measured nothing. CI must carry it.
- **`test:integration` and `test:e2e`.** They are out of scope, since this slice changes no app code.

VERDICT: CONVERGED
