---
name: separate-the-rule-from-the-fetch
description: "FIRES-WHEN: writing a guard whose entry point needs a live service — MEASURED 2026-08-19 — three ratchets went eight days untestable because their only ENTRY POINT needed docker, which read as the LOGIC needing a database; splitting fetch from rule made all three self-testable in minutes"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a00a513a-4135-416e-bbf4-48c0416ca19d
  modified: 2026-08-20T01:24:30.972Z
---

**A dependency at the ENTRY POINT is not a dependency of the LOGIC** — and confusing the two is how
work gets priced out of existence.

`check-ratchet-contract.py` had named four scripts as missing a `--self-test` since 2026-08-11, with
`BASELINE = 4`. Three of them read the catalog through `docker exec … psql`, so their only entry
point needed a live Postgres. *"Give it a self-test"* therefore read as *"stand up a database"*, and
nobody did — for eight days, with the debt written down the whole time.

**The fix was not a database.** Each script's `main()` was one fetch followed by one pure decision.
Splitting `evaluate()` out — catalog rows in, problems out — made all three testable in milliseconds
with fixtures. 56 cases across the four, mutation-tested 16/16, in one sitting. PR #117.

**Ask of any "we can't test this": what exactly needs the expensive thing — the decision, or the
input to it?** Usually only the input.

## The sharper half: a proxy that measures the wrong property

The follow-on (PR #118) added a banner telling readers what a gate's subject IS before its verdict,
because `exit 1` looked identical whether you had broken something or were meeting nine-day-old
expected drift. It shipped with two defects, **both caught by its own self-test within minutes**:

1. It counted references to the **caller's scan list** — which includes shipped tables like `jobs`
   and `spend_ledger` — and printed *"SHIPPED — 100 runtime file(s)"* for a schema nothing deploys.
   **The number was true and the sentence it supported was false.**
2. ⭐ It compared the subject's last commit date against the **script's** and concluded *"reconciled"*
   when the script was newer. False by construction — the script had been edited hours earlier to add
   a `--self-test`, which reconciled nothing. **A file's commit date is not evidence about its
   contents' meaning.**

Fix for (2) was to reach **no verdict at all**: the findings already ARE the reconciliation signal
(a `STALE` entry *is* the drift). What a reader cannot get from them is *when* the subject moved, so
that is the only thing the banner reports — an attribution, not a conclusion.

Same shape as [[a-positional-read-needs-a-verified-shape]] one day earlier: a cheap derived signal
standing in for the property actually wanted. Deriving it is necessary and **not sufficient** — ask
what the derived thing is evidence *of*.

Related: [[a-convention-catches-what-you-read]], [[hardcode-only-what-fails-loudly]],
[[test-harness-can-launder-failures]], [[gates-detect-defects-not-design]].
