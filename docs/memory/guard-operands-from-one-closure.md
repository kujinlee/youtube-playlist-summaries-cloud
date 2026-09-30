---
name: guard-operands-from-one-closure
description: "FIRES-WHEN: writing a guard that compares two values captured in the same closure — A guard comparing two values captured in the SAME stale closure can never fire; mutation testing reports it as \\\"untested\\\", never as \\\"broken\\\""
metadata: 
  node_type: memory
  type: project
  originSessionId: d573bf68-cbd6-4516-aa70-ff7d565b1278
  modified: 2026-08-13T05:00:44.804Z
---

Measured 2026-08-12, PR #91 (backlog #37), round 4 of adversarial review.

An account guard in `PlaylistSidebar` read:

```
const requestedFor = userId;          // captured when the load starts
...
if (requestedFor !== userId) return null;   // "is this still the same account?"
```

`loadPlaylists` is a **closure recreated each render**. The refresh effect held the version from the
render where `userId === 'a'`, so after a switch to `'b'` **both operands still read `'a'`**. The
condition could never be true. It read like a check and was a no-op. Fix: a ref reassigned on every
render (`currentUserIdRef.current = userId`), so one operand is genuinely live.

**Why:** neither instrument caught it alone, and that is the transferable part.

- **The mutation run said "untested"** — deleting the guard broke nothing, which is the *same signal*
  a merely-uncovered guard produces. "No test fails when I remove it" does not distinguish
  *unprotected* from *not actually doing anything*.
- **Reading the guard said "protected"** — the comparison names the right two concepts.

Only a test that genuinely **reached the code path** separated them. The first version of that test
didn't: it resolved the stale load *after* a newer one had applied, so the sequence guard caught it
and the account branch never ran. It passed with the guard deleted.

**How to apply:** when a mutation survives, do not conclude "needs a test" and stop — first ask
whether the guard can fire *at all*. For any guard inside an async continuation, name where each
operand was captured; if both came from the same closure, it is decoration. Then check the test
reaches the branch you think it does, not merely the outcome you expect — an earlier guard
short-circuiting the path is indistinguishable from the later guard working.

Same family as [[a-test-that-cannot-fail]] (a criterion that could only ever
pass) and [[test-harness-can-launder-failures]] (a negative test that passes on typos). Related:
[[dual-review-what-it-catches]] — four rounds, and every High came from the previous
round's own fix.
