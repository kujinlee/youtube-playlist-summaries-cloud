# merge-ready-thrash-hold — round 1, Claude half

Subject: branch `merge-ready-thrash-hold` at d444dcad, against origin/master 5f32aac8 (backlog #680 part 2).
Method: I tried to refute each claim in the brief with a concrete input. Every experiment ran in a fresh clone at
d444dcad under the session scratchpad (`680b-r1/claude-work/repo`). The worktree was not modified except for this file.

## Claim-by-claim

| # | Claim | Result |
|---|---|---|
| 1 | No thrashing branch without an architecture review gets READY | **REFUTED**: C1 (an inline `findings:` list reads as a clean round) |
| 2 | `parse_header` unchanged for existing callers | **Held**: old and new give identical results or errors on all 850 `docs/reviews/coordinator/*.md`; `check-review-decision.py --self-test` 119/119 |
| 3 | Docs read at HEAD; an unreadable round never yields READY | HEAD read holds (`git ls-tree`/`cat-file` at `head`). "Unreadable never READY" is **refuted** for a round the parser *thinks* it read: C1 |
| 4 | Import failure or a raise in `thrashing_component` is CANNOT RUN | **Held** for both, through `main()` (case 682 and mutation 193). Bound in C4 |
| 5 | The 9 new mutations die under their `expect`; the re-bound #508 (2) mutation binds and dies | **Held** for the 5 I ran by hand in full clones: #109 (re-bound #508, anchor unique, 9 reds incl. its expect), #189, #193, #195, #196, each red on its named case |
| 6 | Self-test 419/419 | **Held**: 419/419 (55 s) |

## Findings

### C1 — MAJOR — a non-empty inline `findings: [...]` list parses as ZERO findings, so a thrashing PR reads READY

`parse_round` finds items only through `_findings_span` / `_block_findings`, and both need the line to match `^findings:\s*$`.
`findings: [a, b]`, `findings: [{id: X, …, fix_induced: true, component: det4, …}]` and `findings:  # two` all give an empty
span. So `declared == 0 == parsed`, the parity check passes, and `findings_key` is True (`^findings:`). The gate takes the
round as **clean**. This is the failure the `findings_key` check was added to stop ("an absent list is not a clean round"),
only quieter, because the key is present and the list is not empty.

Reproducer (ran it; `claude-work/exp1.py`): two commits holding `s-r3`/`s-r4` coordinator docs with the same fix-induced
`det4` finding.
- block list (control): `thrashing armed: s's component 'det4' …` (HOLD)
- `findings: [{id: X, severity: Medium, aim: deliverable, fix_induced: true, component: det4, disposition: fixed}]` in both: `[]` (READY)
- `findings: [a, b]` / `findings: [c]`: `[]` (READY)
- `findings:  # two` followed by the same block items: `[]` (READY; the items are dropped because the trailing comment breaks `^findings:\s*$`)

It happens in the real corpus. 40 coordinator docs carry `findings: [<ids>]`. For 7 subjects BOTH of the last two rounds use
that form, and the gate reads them as clean: `backlog-scrub` r5/r6, `ci-time-limits` r5/r6, `correction-spend-on-failure`
r4/r5, `review-loop-batch1` r3/r4, `trigger3-lost-bet` r6/r7, `work-lines` r3/r4 and `work-lines-always-on` r3/r4
(`claude-work/exp2.py`). Example, `work-lines-r3-coordinator.md`: `findings: [trailing-separator-serving, blank-serving-erases,
… symlink-naming]`. That is 6 findings with no `fix_induced` anywhere in the header. The gate cannot see whether they were
fix-induced, yet it answers "no thrashing" instead of "cannot judge".

`parse_header` has the same blindness on master (claim 2 holds, so this is not new to `parse_header`). This branch makes it
load-bearing for a merge verdict.

Fix direction: treat a `findings:` line with anything after the colon other than `[]` as unreadable. One way is to refuse in
`parse_round` when `^findings:[ \t]*\S` matches and the value is not exactly `[]`. Another is to put the "cannot judge" check
in `thrash_gate` beside the `findings_key` check. Add cases for all three shapes above.

### C2 — MAJOR — architecture reviews filed under `docs/reviews/coordinator/` are not recognised, so the recent Phase 6 PRs would HOLD

`ARCH_REVIEW = ^docs/reviews/architecture-review-[^/]+\.md$` matches the top level only. In the repository, 4 of the 67
`architecture-review-*` docs live in `docs/reviews/coordinator/`, and they are the most recent ones (2026-11-15 ×3,
2026-11-17).

Reproducer (ran it; `claude-work/exp3.py`): run `thrash_gate` over each merge commit's own range, at that commit:
- `9d8d7102` (Marketplace slice C, adds `docs/reviews/coordinator/architecture-review-2026-11-17-hse-slice-c.md`) → `thrashing armed: hse-slice-c's component 'optional-edges' … no docs/reviews/architecture-review-*.md is in this PR's range`
- `84e53b9b` (adds `coordinator/architecture-review-2026-11-15-sweep-liveness.md`) → `thrashing armed: sweep-sample-nightly's component 'docs' …`
- `0340751d` (adds `coordinator/architecture-review-2026-11-15-goal-wait-derive.md`) → 2× `cannot judge`. That message tells the reader to "run the Phase 6 architecture review", which the PR had already done.
- Synthetic: thrashing r3/r4 plus `docs/reviews/coordinator/architecture-review-2026-11-21-s.md` in the range → still HOLDs (`exp4.py`).

These are false HOLDs, so the gate fails safe. But they land on exactly the population the gate targets: PRs that thrashed
and then did the right thing. A guard that refuses the compliant case tends to get waved through, and its HOLD message names
a remedy that is already in the range. Fix: also match `docs/reviews/(coordinator/)?architecture-review-*.md`, or settle the
location and add a case for the coordinator-path form.

### C3 — MINOR — "cannot judge" HOLDs even when thrashing is impossible

`thrash_holds` HOLDs on any unreadable round before it asks whether thrashing could arm. Two cases are false HOLDs:
- **A single round.** `thrashing_component` needs 2 rounds. A subject with only `s-r1-coordinator.md` and no header HOLDs anyway: `cannot judge thrashing for s r1: ValueError: no ```yaml header block` (ran it; `exp4.py`).
- **A clean last round.** `r3` with no header and `r4` with `findings: []` cannot thrash, because the rule needs fix-induced findings in BOTH rounds. It HOLDs on r3 (ran it).

In the current corpus, 22 of 181 subjects fall in "cannot judge". Fix: HOLD as "cannot judge" only when the readable
rounds do not already rule thrashing out, i.e. when there are fewer than 2 rounds or every readable round could still share
an induced component.

### C4 — MINOR — a bug in the sibling's `parse_round` reads as an unreadable doc (HOLD), not CANNOT RUN

`_cross(… crd.parse_round …, error=_RoundUnreadable)` turns every `BaseException` from `parse_round` into a per-round
"cannot judge" HOLD. That includes a `NameError` or `TypeError` from a PR that breaks `check-review-decision.py` itself.
The verdict is still not READY, so nothing fails open. But the message blames the document ("read it, or run the Phase 6
review") for what is a broken rule, and claim 4 says a broken rule is CANNOT RUN. Not run; this is by reading `thrash_gate`.
Fix: narrow the per-round catch to `ValueError`, which is what `parse_round` raises by contract, and let anything else
become `ThrashUnjudgeable`.

### C5 — MINOR — deleting or renaming away the last coordinator docs judges an older pair, or nothing

`coordinator_subjects` includes the subjects of deleted docs, but `last_two_docs` reads the HEAD tree. A PR that deletes
`s-r3`/`s-r4` (both thrashing) reads READY. A PR that deletes only `s-r4` gets judged on r2/r3. This is contrived and needs
a deliberate deletion, so I only note it as a bound. It should be stated beside "last two are the two highest round numbers
in the FILE NAMES". Not run; it follows directly from `last_two_docs(tree, …)` at `head`.

## Checked and not refuted
- The PR adds r(N+1) without touching r(N): the subject is still named, and both rounds are read from the HEAD tree. Correct.
- Thrashing only in a non-final pair (r1/r2 thrash, r3 clean): no HOLD, as the rule says (self-test case; I agree with it).
- The `round:` line disagreeing with the file name: the file-name number is used, as documented.
- A greedy `subject` in `COORD_DOC` (for example `a-r2-r3-coordinator.md` → subject `a-r2`, round 3) is consistent between `coordinator_subjects` and `last_two_docs`.
- PR #600 itself (`11d0568d`) now HOLDs ("cannot judge … r4: header has no `findings:` key"). The headline case is caught.
- `fix_induced: yes`/`True` arm (a truthy string), consistent with the sibling's rule. `fix_induced: no` would also arm, as a false HOLD, but no corpus header uses it.

VERDICT: NOT CONVERGED
