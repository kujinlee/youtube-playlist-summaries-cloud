---
name: a-declaration-is-not-the-act
description: "FIRES-WHEN: about to push, or about to run a command that RECORDS that something is being watched/checked/done — ⛔ `check-ci-watched.py --watching` only records a CLAIM. Arm the real Monitor in the SAME action, or the ledger says watched while nothing is. Measured 2026-10-06: 43 minutes blind on a red CI."
metadata:
  type: feedback
---

**Measured 2026-10-06, PR #366.** CI went red at 13:49:18 and I noticed at 14:32:44 — **43m 26s**,
and only because the user asked about an unrelated background task.

```
13:41:54  pushed 56eafeef
13:43:21  checked CI once — all 10 pending
13:49:18  CI finished RED        <- the failure existed from here
14:32:44  noticed, incidentally
```

**The cause was not slowness. I never watched.** For every earlier push that day I armed a `Monitor`
on `gh pr checks`, which notifies within seconds. For this one I ran
`python3 scripts/check-ci-watched.py --watching` — which **only records a claim that a watcher
exists** — and then did not watch.

⛔ **THAT IS WORSE THAN NOT DECLARING AT ALL.** The repo's guard exists to warn *"CI IS RUNNING AND
NOTHING IS WATCHING"*. Recording the claim without the act turns a visible gap into an invisible one
and stops anyone asking. The guard's own docstring admits it cannot verify the act — *"a hook cannot
create a harness background task"* — so the declaration is an honesty ledger, and I made it lie.

⚠ **The adoption itself caused it.** I started running `--watching` that morning *because* the user
showed me the warning; in adopting the declaration I dropped the behaviour it declares. Substituting
the symbol for the thing is the same defect this PR kept finding in my code comments, relocated into
my process.

**How to apply — one action, never two:**

> **After any push: arm the `Monitor` FIRST, then run `--watching`.** The declaration is the receipt
> for the watch, not a replacement for it. If only one of the two happens, it must be the Monitor.

- Give the monitor a `date`-stamped output line so the notification itself carries when it fired —
  see [[waiting-lines-carry-a-timestamp]].
- The monitor must emit on **failure and completion**, not only on success:
  silence must not be indistinguishable from green. [[a-check-result-is-not-the-claim]].
- ⚠ Generalise past CI: any command whose name sounds like a query but whose effect is a RECORD
  (`--watching`, `--tick`, `--arm`, `--decide`) is a declaration. Ask what act it is the receipt
  for, and whether that act happened. Related: [[a-test-that-cannot-fail]],
  [[a-gates-channel-can-be-weaker-than-the-gate]].
