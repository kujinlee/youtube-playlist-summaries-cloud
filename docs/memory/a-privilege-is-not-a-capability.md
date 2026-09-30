---
name: a-privilege-is-not-a-capability
description: "FIRES-WHEN: checking a Postgres privilege as evidence an operation will work — has_table_privilege said INSERT was granted and the insert failed — the gap no fingerprint can close, and the finding that ended four rounds of widening one"
metadata: 
  node_type: memory
  type: project
  originSessionId: 92595a72-4e72-4cb8-9e2c-8cddc19a2bb3
  modified: 2026-08-26T14:58:18.993Z
---

⭐ MEASURED 2026-08-26, M4 fork (a) step 5. One role, one identical row, two paths, same container:

```
[RPC]    record_artifact(...)              -> recorded
[DIRECT] insert into video_artifacts ...   -> ERROR: permission denied for function slot_kind
```

`has_table_privilege('service_role','video_artifacts','INSERT')` is **TRUE in both**. The cause:
`art_slot_kind` CHECKs `slot_kind(slot)`, **a CHECK expression runs as the role performing the
write**, and `slot_kind` is granted to nobody.

**Why it mattered more than the bug.** Round 7 proposed fixing this by adding `service_role` to the
digest's function grantees — a FIFTH widening of a 161-object fingerprint that had already been
redefined four times (names → digests → +enforcement → +effective privileges), each correct and each
insufficient. That fix would have **certified a capability that does not exist**.

**How to apply:** when a gate reads a *grant*, ask what would happen if the grant were present and
the operation still failed. If that state is reachable, the gate is measuring the wrong thing —
assert the capability by PERFORMING it (call the RPC as the role, read the row back; attempt the
forbidden path, require 42501). See [[gates-detect-defects-not-design]]: this is the same shape one
layer down — the check was locally correct and the instrument was wrong.

**Second half, same finding.** The spec was **broken in one environment and not the other**: the
direct insert FAILS in a container and SUCCEEDS on production, because Supabase's `alter default
privileges` grants `service_role` EXECUTE at CREATE time. The RPC-only design was enforced by
accident on a laptop and not at all where it matters — see
[[anon-execute-is-the-default-not-a-decision]], which is the same platform behaviour for `anon`.

Recorded as ADR-0012 (every revoke names every principal) and ADR-0013 (structure is fingerprinted,
behaviour is executed). Related: [[a-mechanism-can-be-silently-overridden]],
[[a-test-that-cannot-fail]].
