# Round 5 — `explainer-src-root-self-configures` (PR #295) — coordinator

```yaml
round: 5
fixes_nontrivial: true
subject: explainer-src-root-self-configures
halves:
  codex: ran
  claude: ran
findings:
  - {id: H1, severity: High, aim: instrument, fix_induced: true, component: examined-keys-pin, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: false, component: respawn-message, disposition: filed}
  - {id: L1, severity: Low, aim: instrument, fix_induced: true, component: manifest-comment, disposition: fixed}
  - {id: L2, severity: Low, aim: instrument, fix_induced: false, component: manifest-comment, disposition: fixed}
```

## ⭐ THE HALVES DISAGREED, AND THE DISAGREEING ONE WAS RIGHT — for the fourth time

**Codex: CONVERGED**, with six checks itemised. **Every one of them reproduces** — its work is
correct. The High was simply not where it looked.

**The Claude half: FINDINGS, one new High**, and it said plainly *"I do not reproduce Codex's
CONVERGED."* This repo's memory records the finding-reporter as correct every time the halves have
split; that is now four for four, and it is the argument for **alternating** rather than treating a
single CONVERGED as the gate.

## H1 — the pins added in r2 and r4 were duplicate dict keys → **FIXED**

Both `EXAMINED_KEYS` entries this branch added were a **second occurrence of a key already in the
literal**. A repeated key in a dict literal is not an error — the last silently replaces the first —
so all seven pins were discarded at import.

**Measured on the branch as shipped:**

```
effective explainer-serve.py tuple : no src_root* key at all
effective page_chrome.py tuple     : no repo_root.start, no restart_*
delete repo_root's `start`         -> rc=0, silent
delete src_root_help's `pidfile`   -> rc=0, silent
```

Those two parameters are the **remedies for r1 H1 and r2 High**. The guard was green while the
things it had just been told to protect were unprotected. ⚠ **High, not Blocking:** production
behaviour is correct and independently verified; this defeats the guards, so those two findings were
still open.

⭐ **NOTHING IN THE REPO COULD HAVE CAUGHT IT.** `population_drift` and the population case compare
**name sets**, and a collapsed duplicate leaves the name set identical — the defect is invisible to
everything that *reads* the dict and visible only in the **source**, before Python throws the first
copy away. `_duplicate_ratchet_keys` now parses the three ratchet literals with `ast`: 4 cases,
including a falsifier (a literal written to contain a duplicate) and CANNOT RUN on unparseable
source. Verified by reintroducing the exact defect — the new case goes red naming the key and the
line **while the runtime check stays green**, which is the finding restated as a test.

⚠ **Two corrections to the coordinator's own account**, both made after measuring:

1. *"Master already had duplicates"* — **false.** The grep spanned three different dicts. Master's
   literal has 51 entries and 51 distinct keys. The duplication was entirely this branch's.
2. The first repair pinned `src_root_help.env_value` and `.repo` — **names the r3 redesign had
   already deleted**, copied from a comment written before the signature became `(observed,
   pidfile)`. The guard refused instantly and named them. **A pin copied from prose is a pin about
   the prose.**

⟳ And fixing it exposed a second copy of one number: the drift check hardcoded `!= 60` and *"the
docstring declares 60"* while the docstring said 64 — the same two-copies defect the check exists to
report. It now reads `__doc__`, and a missing declaration is CANNOT RUN rather than a pass.

## L1, L2 — two claims in a comment that were not true → **FIXED**

The reviewer ran the real harness and refuted a reason this coordinator had recorded as *"the
stronger one"*: `expect` matches by exact case-name equality, so a mutation reddening five cases is
admissible. The **shared-anchor** reason was the real and only bar. ⭐ Recorded as a correction
rather than quietly dropped — a reason that sounds better than the true one is how a rule gets
misapplied later.

## M1 — `respawn()`'s failure note asserts an unconditional kill → **FILED**

*"20s after SIGTERM to pid {old_pid}"* prints even when the kill was skipped; measured live as
`SIGTERM to pid None` and `SIGTERM to pid 999999` with no signal sent. **This branch's own class** —
a reason inferred rather than carried — in a function the branch did not otherwise touch, so it is
filed rather than absorbed.

## Q4 — another round owed?

**Yes.** `review-method.md:625` — *stop when a full re-review returns no new Blocking or High.* This
round returned a **new High**, so the branch does not converge here. The fix is small and mechanical;
round 6 should be short.

## Q5 — thrashing?

**No.** H1 is fix-induced but in `examined-keys-pin` — an instrument — and `src-root-help`, the
component the r3 architecture review was about, took **no finding at all** this round for the second
round running. The production shape has been stable since the redesign.

## ⚠ An incident during this round, disclosed rather than buried

The Claude half ran `pkill -f explainer-serve.py` while cleaning up an isolated test server, which
**also killed the user's live docs server on port 7391**. It restarted it immediately and reported
it. Verified by the coordinator afterwards: `HTTP 200` on `/dashboard`, pid 53110. Recorded because
a reviewer reaching outside its sandbox is a hazard of this topology, and `review-method.md`'s
concurrency table already says none of those hazards is mechanically enforced.
