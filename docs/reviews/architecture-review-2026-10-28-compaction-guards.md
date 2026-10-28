# Architecture review — 2026-10-28 — the compaction guards (backlog #361, PR #425)

**Convened by THRASHING** (`docs/dev-process.md`): `print` carries findings caused by the previous round's own fix in
round 2 (Cm7, Cm8 — the receipt gate's heading and supersession claims) and round 3 (Cr6 — the stale-audit message
`9d7e32eb` introduced), consecutively, in one component. `check-review-decision.py` returns ARCHITECTURE_REVIEW with
**no lead**: audit, extraction, print and snapshot are tied at three appearances each, so this review covers the subject,
not one component.

## What held, measured, in every round since it shipped

- **The capture boundary (round-2 redesign A).** PreCompact writes the receipt first, runs every capture step in a child
  killed at 11 s, and writes `CANNOT RUN` with every key UNAVAILABLE on expiry. Codex r3: 10.98 s on a 262 MB transcript
  with a 7.9 s `gh`; my own attack: 11.3 s with a slow `gh` and `git`. In-process deadlines failed in rounds 1–2; this has
  not failed once.
- **Owner words, RECORDED not proven.** Same-session binding plus once-only pairing: all 40 real answers pair, in 0.56 s on
  the real 83 MB transcript; every forgery from rounds 1–3 is excluded (one residue: an explicit `null` flag, Xr8).
- **The worktree ledger read and write**, the `WAITS-ON-OWNER:` marker, rc 0 on garbage, and the 10,000-character print bound.

## The wall, named once — and this is the fourth subject in two days to hit it

After `architecture-review-2026-10-27-fixture-guard.md`, `…-27-em-guard.md` and `…-28-import-time-launch.md`: **a check
that asserts a property of ARBITRARY INPUT that the input itself can defeat.** Here there are two such claims, and every
round's findings in `audit` and `print` are one of them:

1. **"The summary NAMES item X."** Whether a `#410` in free prose refers to PR #410 is a question about the WRITER'S
   intent. Round 2 counted `backlog #376` as PR #376; the fix excluded a preceding word; round 3 defeated it with
   `backlog item: #410`, `backlog **#410**` and `backlog #364, #376 and #383` — and the exclusion itself was quadratic
   (XR2). No rule over the text decides the referent; each one moves the outside. Consequence: "names everything" is a
   claim this code cannot make, and every round it was made it was false on SOME input (CM1, CM3, XM5, XR6, XR7, CR2, Cr8).
2. **"This is THE compaction."** The harness gives a `session_id`; it gives no identifier of a compaction. Round 2 bound
   artifacts by session; round 3 showed a delayed PostCompact and a PreCompact racing SessionStart (XR5) bind the wrong
   capture inside one session. Each nonce rule added a message (Cm7, Cm8, Cr6) that claimed an identity the inputs never
   carried. Consequence: "COMPACTION HAPPENED at T … items dropped are listed" is a claim this code cannot make either.

The third claim — "this hook ends in time" — was the same wall for two rounds and was **dissolved by structure** (a child
it can kill), not by more rules. That is the precedent for the decision below.

## Decision (owner's standing AFK rule — not critical)

**SPLIT.** Ship the decidable half; withdraw the two undecidable claims, replacing each with a weaker statement that no
input can make false.

1. **Audit — no completeness claim, ever.** One linear pass collects explicit `PR #N` references (the word `PR` required)
   and ledger ids written as `[id]` or `` `id` ``. Output: *found explicitly* and *not found explicitly*, followed by one
   fixed line: *"Not finding an item here does NOT mean the summary dropped it, and finding one does not mean the summary
   kept it accurately — read the snapshot."* `names everything` and `COULD be checked` are deleted. This dissolves XR2,
   XR6, XR7, CR2, Cr8 and Cr9 by removing the sentence they falsified.
2. **Print — no compaction-identity claim.** The heading becomes *"NEWEST CAPTURE for this session, taken at T (N min before
   this session start)"*. The snapshot shows when its nonce equals the receipt's, the receipt is under 30 min old and not
   in the future; the audit shows only when its nonce equals the snapshot's. Any other combination says which piece is
   missing and shows nothing it cannot match. One fixed line states the remaining bound: *"session identity is not
   compaction identity: a delayed or overlapping compaction in this session can be shown here."* This dissolves XR5 (as a
   stated bound, not a fix), Xr9, Cr4, Cr5 and Cr6.
3. **Accrete the decidable rest, structurally where the class is structural:**
   - **XR1:** PostCompact and SessionStart go behind the SAME external child boundary as PreCompact, and every artifact
     is read by one reader that refuses non-regular files (`O_NONBLOCK` + `fstat`) and caps size.
   - **XR3:** `session-state._run` drains pipes for a bounded time after a kill, then closes them. The LIVE SessionStart
     hook (backlog #362's) can't outlive its timeout on an escaped grandchild.
   - **CR1:** stated as a PROPERTY: after any hook returns, no process the capture started survives, except one that
     calls `setsid` itself (stated, not hidden). The implementer chooses how; one way is for the child to record each
     call's process group and the parent to kill every recorded group. It is tested at the REAL 11 s kill, not only on
     the normal path.
   - **XR4:** refuse a symlink in any component of `.remember/compaction/<sid>/`, and write with `O_NOFOLLOW`.
   - **Xr8:** a provenance flag passes only when it is absent or `is False`.
4. **Prose (Xr10, CR3, Cr7, Cr10):** rewrite the PR body FROM the final code, not by editing the old one. CLAUDE.md
   names ONE shared word for "not captured", which every such line carries.

⚠ **Falsifier for this decision:** an input that makes any sentence the split KEEPS false — an audit line that claims a
kept or dropped item, or a print that shows a capture whose nonce does not match. If round 4 finds one, the claim was not
withdrawn far enough, and the next step is DEFER the audit entirely, with the snapshot alone shipping.

## What did we decide this milestone that isn't written down?

The falsifier for these guards — written by the coordinator at the owner's 04:12 request to test their effectiveness; the owner did not write its criteria — *grade the first REAL compaction after #361 merges against four criteria* — is
held only in the in-flight ledger (`compaction-falsifier`). It belongs in the backlog #361 row, so it survives the ledger
entry being closed.
