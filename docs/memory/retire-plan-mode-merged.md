---
name: retire-plan-mode-merged
description: "FIRES-WHEN: citing PR #270, PR #271, or retired plan mode — MERGED 2026-09-09 — PR #270 refused plan mode, PR #271 deleted it. check-plan-code.py 3,607 -> 2,013 lines; the only sanctioned ratchet FALL in the project's history"
metadata:
  node_type: memory
  type: project
---

**BOTH PRs MERGED 2026-09-09.**

| | | |
|---|---|---|
| PR #270 | `4ec7e82a` | the four entry points REFUSE with rc=2 naming the retirement |
| PR #271 | `3afe62c0` | the code behind them DELETED |

`scripts/check-plan-code.py` **3,607 → 2,013 lines**: 7 functions (`extract`, `check`,
`evidence`, `compare_delivered`, `verify_evidence`, `pasted_evidence`, `unsafe_tag`),
7 constants, and 143 cases.

**The refusals STAY and are not vestigial.** Someone who types `--verify-evidence` believed a
subject was being measured; they are owed a sentence saying it no longer is, rather than
argparse's *"unrecognized arguments"*, which reads like a typo instead of a decision.

## ⭐ The only sanctioned ratchet FALL, and how it was justified

    cases                229 -> 78    docstring; `_drift_rc` checks it every run
    EXPECTED_MUTATIONS    44 -> 23    21 anchors stop resolving
    declared sum         392 -> 371

These ratchets rise only. Both falls are recorded **at the site**, naming the count and the
reason — entries are *retired with the code they guarded*, never orphaned. `EXPECTED_MUTATIONS`'
own comment had reserved this: *"the retirement of this entry belongs to the deletion slice,
with the case it serves."*

**23 was confirmed twice, by different methods**: the pre-work inventory attributed anchors by
enclosing line range; the deletion retired them by whether `src.find(anchor)` still resolves.
⚠ Two earlier attempts both answered **0** — the manifest key is `edits[i][0]`, not `anchor`
(`find("") == 0` attributes everything to line 1), and the question is *is the anchor INSIDE a
doomed function*, not *does its text mention one*. See
[[measure-the-population-the-code-actually-sees]].

## What this cost, worth reading before the next deletion

* CI red on the first push — five mutations lost their only red case:
  [[a-mutation-loses-its-binding]]
* the pruner damaged surviving code three times:
  [[a-mechanical-edit-damages-what-it-preserves]]
* `--mutate .` must be run locally for a deletion:
  [[defaults-i-decide-myself]]

## Judgement calls a future reader may reopen

**Two case-groups were deleted as UNFALSIFIABLE rather than dead** — the escaping-tag block
(*"the delivered file is NOT overwritten"*, *"nothing leaked outside the sandbox"*) and the
`evidence()`-requires-`ctx` probe. With their subject gone each asserts an absence that deleting
the subject also satisfies. Keeping them would have kept a green tick over nothing.

**Review:** no dual-adversarial round was run on PR 2. Four rounds ran on PR 1 and stopped by
decision (cause absent, not count); PR 2 is a deletion whose correctness rests on `--mutate .`
and the case count, both measured. Stated so it is a visible choice, not an omission.
