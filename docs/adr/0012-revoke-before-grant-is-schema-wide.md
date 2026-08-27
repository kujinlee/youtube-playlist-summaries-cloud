---
status: accepted 2026-08-26 (fork (a) step 5, M4 review rounds 6-7). Generalises a rule round 6
  applied to relations only. It does NOT re-open ADR-0006/0007/0011 — it records how privileges are
  written, not what the schema means.
  ⚠ ACCEPTED IS NOT IMPLEMENTED, in the same sense as ADR-0011: the rule now holds across all 21
  privilege sites in the M4 spec, and that spec has never run as a migration.
---

> **Anchor:** `stable-blob-addressing` — **ADR:** 0011
> **Goal:** A blob's address stops moving when a title or a serial number changes.

# ADR-0012 — Every privilege site revokes from EVERY principal before granting

## Context

Supabase grants privileges **at CREATE time**, through `pg_default_acl`. A migration that says

```sql
grant execute on function f(...) to service_role;
```

is not describing the resulting ACL. It is adding one grant to a set the platform has already
populated — and on production that set is `anon`, `authenticated` and `service_role` for every new
function, plus `claude_ro` for every new table.

So a spec's grant statements are only half of what the deployed database ends up with, and the other
half is invisible in the migration. Round 6 of the M4 review established the rule for relations:
**revoke from every principal, then grant back exactly what is intended.** It stopped at relations.
Fourteen function sites kept the older shape:

```sql
revoke all on function record_artifact(...) from public, anon, authenticated;
grant  execute on function record_artifact(...) to service_role;
```

which reads as *"only service_role may call this"* and does not say it. `service_role` is absent from
the revoke, so on production its EXECUTE survives from the default ACL — for every function, not just
the one being granted.

### What that cost, measured

The half-applied rule produced two findings in round 7, and they point in opposite directions, which
is the tell that the omission was not stylistic:

- **r7 B1** — the gate could pass over a production write outage, because `service_role`'s function
  EXECUTE was in neither the digest nor any other check.
- **r7 H2** — the spec was **broken in one environment and not the other**. `art_slot_kind` CHECKs
  `slot_kind(slot)`; a CHECK expression runs as the role performing the write; `slot_kind` is granted
  to nobody. MEASURED 2026-08-26, one role, one identical row:

  | environment | `insert into video_artifacts …` as `service_role` |
  |---|---|
  | container, no default privileges | `ERROR: permission denied for function slot_kind` |
  | production-shaped, default ACL present | **succeeds** |

  The RPC-only design was therefore enforced by accident on a laptop and not at all where it matters.

Neither finding is reachable by reading the migration. Both are consequences of a grantee list that
names three roles in a four-role world.

## Decision

**Every `revoke` in this schema names every principal the platform can grant to, and every `grant`
that follows names only what is intended.** For this project that grantee list is
`public, anon, authenticated, service_role`.

The rule applies to relations, functions, and any object class added later. It is a rule about the
*shape of the statement*, not about which principals a given object should end up with — those stay
per-object decisions.

## Consequences

**The migration becomes the whole truth about who can do what.** Before this, reading the spec told
you what was granted and not what was left over. After it, the deployed ACL is a function of the
migration alone, and the two environments agree — which is what makes any environment-invariant check
possible at all.

**⛔ THIS ADR NAMED THE WRONG FALSIFIER FOR ONE COMMIT — ⟳ r8 H3 (codex), and the reviewer proved
it by construction.** The paragraph here originally claimed mutation 19 was the mechanism: *"an M4
applied to a production-shaped database must pass the same checks as a bare container; a regressed
revoke breaks that agreement and the mutation goes red."* **It does not.** Mutation 19 runs only
`check-live-schema.py --expect-present`, and after ADR-0013 that gate carries no privileges at all —
so it cannot see a revoke regression of any kind. MEASURED on a production-shaped scratch with
`service_role` removed from the `slot_kind(text)` revoke:

```
check_live_exit=0            # the named falsifier says nothing
assert_exit=1                # ASSERTION FAILED — service_role wrote video_artifacts DIRECTLY
```

**The real falsifier is the capability assertion**, not the digest — which is ADR-0013's whole point,
and this ADR contradicted it while citing it. A claim about which instrument enforces a rule is
exactly as checkable as the rule itself, and this one was never checked before being written down.

**What actually enforces it, stated as observations that can FAIL:**

| regression | what goes red | verified |
|---|---|---|
| a session role gains write or EXECUTE on an M4 object | `check-anon-exposure.py` RULE 3, gate 11/12 | mutations 10, 17, 22, 23 — each with a control proving the named problem was ABSENT first |
| `service_role` keeps EXECUTE on `slot_kind`, so the direct door opens | `05_assert.sql` SERVICE-ROLE CAPABILITY, gate 8/12 | measured: `assert_exit=1`, "record_artifact is not the only door" |
| `service_role` loses EXECUTE on `record_artifact` | same block, other direction | measured: `assert_exit=1`, "this is a production write outage" |

**⚠ Still a convention where it is not mechanised.** Nothing scans for a revoke that names three
roles instead of four; the rows above catch *consequences on M4 objects*, not the omission itself,
and nothing at all catches a `service_role` omission on a NON-M4 object. If a third instance appears,
that is the signal to write the script rather than the third comment.

## Alternatives considered

**`alter default privileges … revoke` once, globally.** This is backlog #54 half (a), and it is the
better long-term fix: it stops new objects arriving granted at all. It is not this ADR because it
changes production grants for *every* schema and is a deployment decision, not a spec one. The two
compose — this ADR makes each migration self-describing; #54(a) makes the default harmless.

**Leave it, and cover `service_role` in the fingerprint instead.** This was round 7's proposed fix
and it is what ADR-0013 rejects: a digest of a grant cannot tell you the grant *works*.
