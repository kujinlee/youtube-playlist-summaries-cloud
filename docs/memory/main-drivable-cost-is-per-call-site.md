---
name: main-drivable-cost-is-per-call-site
description: "FIRES-WHEN: adding main([...]) calls to a long _self_test, or check-main-drivable's suite got slow / timed out in CI"
metadata:
  type: project
---

`check-main-drivable.py --self-test` analyses EVERY `main()` call site against its ENCLOSING function, so a
`main([...])` call placed inside a long `_self_test` is expensive: PR #400 added five and took that suite from
50s to 209s — past the 120s `SUITE_TIMEOUT` — which made EVERY CI mutation shard's control fail (183 of its
mutations spread over all 12 shards). Measured fixes, same machine: a reviewer's guessed cause (the
`globals()` rebind) changed nothing (209s); ONE call site in a table loop → 84s; that one call moved into a
small module-level helper (`_budget_wiring`) → **52s**, master 50s.

**Why:** a guessed mechanism read as a fix; only the ATTRIBUTION (replace the calls with constants → fast) was
measured, and it was right. **How to apply:** drive `main()` from a small helper outside `_self_test`, one call
site; re-time `CI=true python3 scripts/check-main-drivable.py --self-test` against master on a QUIET machine
(a concurrent Codex run made one timing read 3m45s). See [[a-check-result-is-not-the-claim]].
