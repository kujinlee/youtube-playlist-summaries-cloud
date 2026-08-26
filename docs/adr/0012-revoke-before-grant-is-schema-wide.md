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

**It does not need a gate, because it has one already.** The environments agreeing is what
`mutate-live-schema-check.sh` mutation 19 asserts: an M4 applied to a *production-shaped* database
(default privileges installed) must pass the same checks as one applied to a bare container. A
regressed revoke breaks that agreement and the mutation goes red.

**⚠ It is a convention where it is not yet mechanised.** Nothing scans for a revoke that names three
roles instead of four. `check-anon-exposure.py` RULE 3 catches the *consequence* for session roles on
M4 objects — an object they can write or execute — which is the part that matters for security. It
does not catch a `service_role` omission on a non-M4 object. If a third instance of this appears,
that is the signal to write the script rather than the third comment.

## Alternatives considered

**`alter default privileges … revoke` once, globally.** This is backlog #54 half (a), and it is the
better long-term fix: it stops new objects arriving granted at all. It is not this ADR because it
changes production grants for *every* schema and is a deployment decision, not a spec one. The two
compose — this ADR makes each migration self-describing; #54(a) makes the default harmless.

**Leave it, and cover `service_role` in the fingerprint instead.** This was round 7's proposed fix
and it is what ADR-0013 rejects: a digest of a grant cannot tell you the grant *works*.
