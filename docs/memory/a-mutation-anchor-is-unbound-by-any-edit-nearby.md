---
name: a-mutation-anchor-is-unbound-by-any-edit-nearby
description: "FIRES-WHEN: editing (or merging, or resolving a conflict in) a script or manifest that mutation anchors bind to, on ANY branch in flight. Run the harness's own all-manifest resolve; merge manifests per entry"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e8d4fa1c-667d-4d08-bd64-55931cd5a12f
  modified: 2026-09-23T00:31:37.819Z
---

**The rule: after ANY edit to a manifested script — a comment, a rename, a merge resolution — on EVERY branch in flight, run the all-manifest resolve before pushing: for each `scripts/mutations/*.json` entry, `src.count(anchor) == 1`, plus the harness's own `expect` rule (exact equality against the case names that went RED, exactly one match). It needs no suite and takes seconds.**

**How to apply:**
- **Use the HARNESS's own rule, never a broader re-typed one** — mine reproduced recorded bugs (`expect` is sometimes a bare string, so iterating it yields one "orphan" per character; a duplicate rule stricter than the harness's invents failures). Cite the rule in `check-plan-code.py` by symbol. See [[a-second-implementation-of-one-rule-drifts]].
- **Derive the population: glob `scripts/mutations/*.json`, never pick.** A run over 2 of 4 manifests is how a Blocking got past me.
- **Anchor on CODE, not comments** — prefer the statement plus the next section's header; comment lines are what gets rewritten.
- **A manifest MERGE is per entry, three-way:** ours-changed & theirs-unchanged → ours; then assert EVERY anchor occurs in its file. Never "master's list + my new entries".
- ⛔ **Every per-round gate (anchors, decision log, review rounds) runs on every branch with a review round**, not just the one I am thinking about.

**Why:** anchors bind by TEXT; any edit that changes, splits or moves the span unbinds it, and nothing says so until the manifest is applied — often in CI.

## History (condensed)

- **2026-09-22, PRs #332/#333:** seven bindings orphaned by unrelated edits — a comment inserted into a two-line anchor and a case rename (found by a 35-minute sweep, `NOT MEASURED`); a comment rewrite across a 3-comment-line anchor (found by a review round as a **Blocking** red CI step); four from restructuring (found by the 15-second check).
- **2026-10-25, PR #400:** re-resolved anchors after every fold on `merge-when-ready-rule` but never on `local-sweep-guard`, which orphaned FOUR entries; the review found it. Same night, same branch: `check-decision-scheme` failed in CI — 4 rounds with no decision-log row (a retroactive row was the honest repair).
- **11-06 03:00, PR #516:** resolved a `goal-tree.json` conflict as "master's list + my NEW entries", silently taking master's copy of 4 entries I had re-bound → 12 shards red in 30 s, "anchor NOT FOUND". Codex r3 and my spot check both looked only at new entries.

See [[a-mutation-loses-its-binding]] (the earlier, narrower instance), [[a-measurement-is-only-as-good-as-its-corpus]], [[a-check-result-is-not-the-claim]].
