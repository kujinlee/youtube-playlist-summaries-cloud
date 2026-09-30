---
name: a-mechanism-can-be-silently-overridden
description: "FIRES-WHEN: about to claim a mechanism, flag or setting is in effect — MEASURED 2026-08-19 building the prod smoke — two defects, one shape: a mechanism that APPEARS to be in effect and is silently discarded. Neither was visible by reading; both surfaced in the first 30 seconds of running it"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a00a513a-4135-416e-bbf4-48c0416ca19d
  modified: 2026-08-20T04:02:56.983Z
---

**A mechanism can be present, accepted by the API, and doing nothing.** Both defects in the M3.1-B
prod smoke (PR #119) had this shape, and neither was findable by reading the code.

## 1. `sslmode=require` in the URL overrode the `ssl` object beside it — *and was non-verifying*

`pg`'s connection-string parsing builds its own `ssl` config from `sslmode=` and **overrides** the
`ssl` object passed in the same client options. So the pinned CA was supplied, accepted, and
**silently ignored** — the connection failed with the identical error it had before the fix.

Worse, and the part worth carrying: **pg 8 maps `sslmode=require` to a NON-VERIFYING connection.**
Its own deprecation warning says pg 9 will adopt libpq semantics and start verifying. So
`CLAUDE_RO_DATABASE_URL` had been carrying a database credential over TLS that never checked who was
on the other end — and the parameter that made it so *reads* like the security-conscious choice.

The fix was to strip `sslmode=` and pin Supabase's private root
(`Supabase Root 2021 CA`, self-signed by design — Node is right to reject it), downloaded over
**public** TLS so trust is anchored in the web PKI rather than in whatever the pooler presented
first. Trust-on-first-use from the chain being verified would have been circular.

⚠ **The first fix written was `rejectUnauthorized: false`, and it was WRONG** — it accepts any
certificate at all on a credential-bearing connection. A security hook caught it. The right move
was to *inspect the actual chain* (three lines of `tls.connect`) rather than reach for the bypass.

## 2. `describe.serial` converted "3 could not run" into "5 told you nothing"

Copied from the A-suite without asking whether its reason applied. `.serial` aborts every remaining
test after the first failure — so when the session-bearing check reported NOT RUN, Playwright
abandoned the three checks that need **no** session, in exactly the situation the suite is most
useful. The A-suite's rungs share ordering; these build their own contexts and do not.

## The rule

**Ask of any guard, option or ordering primitive: what would I observe if it were silently doing
nothing?** If the answer is "the same thing I observe now", it is not yet evidence. Run it.

Same family as [[guard-operands-from-one-closure]] and
[[test-harness-can-launder-failures]]; the running-it-beats-reading-it half is
[[a-convention-catches-what-you-read]]. Related: [[check-the-assumption-not-just-the-code]],
[[separate-the-rule-from-the-fetch]].
