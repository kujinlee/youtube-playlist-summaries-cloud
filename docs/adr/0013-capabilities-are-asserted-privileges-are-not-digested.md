---
status: accepted 2026-08-26 (fork (a), user decision 2026-08-25; Phase 6 #2 question 1). Records
  what the M4 verification instrument may and may not contain, after four redefinitions across
  rounds 4-7 that were each correct and each insufficient. Supersedes nothing; it BOUNDS
  `scripts/m4_catalog.py`, which had no stated bound before.
  ⚠ ACCEPTED IS NOT IMPLEMENTED for the assertion half in production: the capability assertions run
  against a live schema (measured), but `0027` does not exist, so they have never run against
  production.
---

> **Anchor:** `stable-blob-addressing` — **ADR:** 0011, 0012
> **Goal:** A blob's address stops moving when a title or a serial number changes.

# ADR-0013 — Capabilities are asserted by executing them; privileges are not fingerprinted

## Context

M4's live-catalog gate compares a deployed database against a 161-object manifest of
`kind:name@digest` strings. Between rounds 4 and 7 the digest was redefined four times, and **each
redefinition was correct and insufficient**:

| round | the fix | what it caused |
|---|---|---|
| 4 | names → digests | r5: absent mode needed the *opposite* change; "defined" ≠ "in force" |
| 5 | digest enforcement state, incl. raw ACLs | r6: the ACLs made `--prod --expect-present` **unsatisfiable** |
| 6 | effective access + revoke-before-grant | r7: four written exclusion reasons were false; the function revokes were not extended |
| 7 | *(proposed)* add `service_role`, add TRUNCATE | — |

The architecture review of 2026-08-25b found that **nine findings across four rounds were one
choice**, and named the constraint the fingerprint could not satisfy: a fingerprint must both
*enumerate* everything worth comparing **and** be *comparable across environments*. Privileges fail
the second requirement by construction, because production carries `alter default privileges` and a
`claude_ro` grantee no developer machine has (r6 B1, measured against production).

Round 7 then produced the finding that settles it. `service_role` holds `INSERT` on
`video_artifacts` **and cannot use it** — `art_slot_kind` CHECKs `slot_kind(slot)`, a CHECK runs as
the writing role, and `slot_kind` is granted to nobody. MEASURED 2026-08-26, one role, one identical
row, two paths in the same container:

```
[RPC]    record_artifact(...)              -> recorded
[DIRECT] insert into video_artifacts ...   -> ERROR: permission denied for function slot_kind
```

`has_table_privilege('service_role','video_artifacts','INSERT')` is **TRUE in both cases**. A digest
of that grant would have certified a capability that does not exist.

## Decision

**The manifest digest contains structure. It contains no privileges.**

Facts about *who may do what* live in one of two places, chosen by whether the fact is
environment-dependent:

| fact | home | runs |
|---|---|---|
| session roles (`public`, `anon`, `authenticated`) on M4 relations and functions | `check-anon-exposure.py` RULE 3 | gate 11/12, every run |
| `service_role`'s ability to do its job | `05_assert.sql` — SERVICE-ROLE CAPABILITY | gate 8/12, `M4_PHASE=post` |

**A capability is asserted by performing it**, not by reading a catalog: call the RPC as the role and
read the row back; attempt the forbidden path as the role and require `42501`.

## Consequences

**The gate is deliberately blind to a class of change, and that is the trade.** Granting `anon`
INSERT on `video_artifacts` now leaves `check-live-schema.py --expect-present` at exit 0. That is
correct, and the mutation harness asserts it: mutations 10, 17, 22 and 23 each require **both** that
the digest passes and that the new home fails. One assertion could not distinguish *coverage moved*
from *coverage deleted*.

**Coverage moved only because something runs the new home.** `check-anon-exposure.py` was named in the
roadmap and twice in the plan and invoked by nothing; it is now gate 11/12, and its self-test asserts
the wiring at both ends. This project has shipped a gate with no caller three times.

**The assertion half is weaker in one specific way: it needs the schema to exist.** Pre-`0027` the
capability assertions are skipped (`M4_PHASE=pre` says so out loud rather than passing), and RULE 3
reports `0/8 relations present`. Nothing is being checked because nothing is there — but a reader must
be able to see that, which is why both print counts instead of verdicts.

**It ends the redefinition cycle, or it does not, and round 8 is where that is tested.** The
falsifier: if the next review round produces findings about the *instrument* rather than the
*schema*, the instrument has stopped paying for itself and M4 should proceed to `0027` with the
assertions as its only guard.

## Alternatives considered

**Widen the fingerprint again** — add `service_role` to the function grantees, add `TRUNCATE` to
`REL_PRIVS`. This was round 7's proposal and it is exactly the move rounds 4, 5, 6 and 7 each made.
It also cannot work here: it would have digested a grant that does not confer the capability.

**Drop the fingerprint entirely and assert everything.** Rejected. Assertions cannot see what is
*absent* — a dropped index, a missing constraint, a policy that was never created leave no behaviour
to execute. The two instruments answer different questions and the split is along that line:
**structure is fingerprinted, behaviour is executed.**

**Keep privileges in the digest but only for environment-invariant principals.** This is what step 3
did as a staging decision, holding `service_role` back with a date on it. It was a way to avoid a
coverage gap for two commits, not a stable design — and r7 H2 is the argument against making it one.
