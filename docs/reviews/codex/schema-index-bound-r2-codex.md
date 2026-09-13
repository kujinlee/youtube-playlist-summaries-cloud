# Adversarial review — `schema-index-bound-stale`, round 2 (Codex)

**Both halves ran.** The Claude half is `docs/reviews/claude/schema-index-bound-r2-claude.md`
(CONVERGED, 2 Low, both fixed before this run — so Codex reviewed the FINAL state, including the
r2 fixes, which were deliberately left uncommitted until it had seen them).

**Dispatched with** `scripts/codex-review.py --prompt-file … --out …/schema-index-bound-r2-codex.md`;
model `gpt-5.5`; `gate_ran=true`. ⟳ The first dispatch was killed at 10 minutes by the caller's own
foreground limit — NOT a hang: it had already spawned the harness. Re-dispatched in the background
with `--timeout 1500`. The orphaned harness child was reaped and the scratch databases verified gone
(`select count(*) … like 'm4_gate_mut%'` → 0) before re-running, so this review did not share a
database with a zombie. ⟳ `--out` is named after the subject this time, so the verdict JSON lands at
the matching basename without a rename — the r1 lesson.

**Verdict: NO FINDINGS.**

---

<!-- codex-review: model=gpt-5.5 -->

No findings.

I reviewed the current `git diff HEAD` plus `git diff master...HEAD`, with focus on `scripts/mutate-live-schema-check.sh:probe_kind`.

Checks against the attack points:

- `residue` is only written at `scripts/mutate-live-schema-check.sh:345`, `:364`, and `:382`; the normal path reaches `:382` with `r=pass`, so it does not spuriously poison the next probe.
- The two observe-only `gate` reads can mark residue for an unrelated `check-live-schema.py` failure, but both are already red paths: mutation DID NOT LAND sets `fail=1` at `scripts/mutate-live-schema-check.sh:337`, and “never observed as drift” follows `report` at `:352`, whose failure behavior is defined at `:148-149`. Cascading NOT RUN after that does not hide a green run.
- No caller reads `probe_kind`’s return value. All four call sites are bare commands at `scripts/mutate-live-schema-check.sh:389`, `:393`, `:397`, and `:421`.
- `set -uo pipefail` is in force at `scripts/mutate-live-schema-check.sh:61`; there is no `-e`. `local out mrc seen` at `:325` has no assignment to mask status, and `mrc=$?` at `:334` immediately follows the mutation `db` call at `:331-333`.
- The rewritten comment at `scripts/mutate-live-schema-check.sh:375-381` matches the code: the three writers are `:345`, `:364`, and `:382`; later probes read at `:326`; the FOREIGN bound reads at `:446`.

Measurements reproduced:

- `M4_PHASE=post scripts/mutate-live-schema-check.sh`: `56 ✓ / 0 ✗`, exit `0`.
- POLICY undo desynced in scratch copy: one POLICY undo `✗`, CONSTRAINT/TRIGGER/INDEX and FOREIGN bound `NOT RUN`, exit `1`.
- Neutered `unexpected()` plus POLICY desync in scratch copy: POLICY undo `NOT RUN`, CONSTRAINT/TRIGGER/INDEX and FOREIGN bound `NOT RUN`, exit `1`.
- Partial land plus desynced undo in scratch copy: `POLICY mutation DID NOT LAND`, then sibling probes and FOREIGN bound `NOT RUN`, exit `1`.
- Neutered `check-live-schema.py --self-test`: `104/119`, exit `1`.
- `M4_PHASE=post scripts/check-schema-gates.sh`: `73 ✓ / 0 ✗`, exit `0`, all `15/15` gates green.

Clean from this round.

---

## Coordinator note

Two things worth recording rather than leaving implicit.

**It reproduced the load-bearing measurement independently.** Every claim about the NOT-RUN paths
rests on the neutered `unexpected()` actually being neutered; Codex ran that copy's own `--self-test`
and got **104/119**, the same figure the Claude half and I each measured separately. Three
independent reproductions of the sabotage, not one asserted once.

**It checked the comment against the code, which is what this branch is about.** `:375-381` claims
three writers and two classes of reader; Codex enumerated `:345`, `:364`, `:382` as the writers and
`:326` (later probes) plus `:446` (the FOREIGN bound) as the readers, and reported them as matching.
That is the finding r2 raised against the previous comment, checked rather than re-asserted.

⚠ **Independence, stated as before:** round 1 was filed on the branch, so a reviewer reading the diff
learns r1's verdict. Round 2's Claude half disclosed this. For round 2 the Codex half ran against a
tree containing r1's committed reviews and the r2 Claude review, so its independence is bounded the
same way. The fix remains: dispatch both halves before either is committed.
