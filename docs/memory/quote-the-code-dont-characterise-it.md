---
name: quote-the-code-dont-characterise-it
description: "FIRES-WHEN: about to state what existing code does — A design premise about existing code must PASTE the lines with a file:line, or be labelled unverified — \\\"worker_id is stable config\\\" was written from memory, was false, and cost two review rounds"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 85db654d-d23e-47f5-b2ea-89104f89cb42
  modified: 2026-08-11T01:32:45.576Z
---

**Measured 2026-08-08 (round 10, PR #59).** I built an ownership mechanism on the premise that
`worker_id` was stable config. `worker/main.ts:69` says:

```ts
const workerId = `${os.hostname()}-${process.pid}-${randomUUID().slice(0, 8)}`;
```

A fresh uuid and the pid at **process start** — exactly as volatile as the token it replaced. The
other half of the premise (*"job_id is recoverable by querying jobs for locked_by = me and
status = 'active'"*) was false too: `sweep_expired_leases` nulls `locked_by` and moves the job off
`active`, so that query returns nothing precisely when recovery is needed.

**Why nothing caught it.** Every instrument in that effort — assertions, mutations, guard coverage,
SQL probes — points at the SCHEMA. The fatal claim was about code **outside** the artifact under
review, so the whole apparatus was blind to it, and the claim sat in a table next to measured facts,
in the same voice, indistinguishable.

> **QUOTE THE CODE YOU RELY ON; DO NOT CHARACTERISE IT.** Quoting forces a read; characterising lets
> you write from memory. If a premise genuinely cannot be verified, label it **unverified in the same
> sentence** — the unrecoverable move is a premise presented in the register of a fact.

**The sibling rule, same round:** ask **"what caller reaches this state?"** of every measured defect.
A rolled-back probe can construct any state you can type, including unreachable ones. Round 8
measured a doubly-lost worker being refused and graded it Blocking; rounds 8 and 9 designed against
it; round 10 established the state cannot occur (a crashed process lost the bytes with the token, and
`worker-runner` ABORTS the handler on lease loss). *"Is this refused?"* ≠ *"can a caller BE here?"*,
and only the second decides whether a fix is needed.

Both are now in `docs/review-method.md`. The outcome was the third option nobody proposed: **delete
the mechanism**. See [[a-fence-wrong-both-ways-asks-the-wrong-credential]] (the round it corrects),
[[unsatisfiable-ordering-is-the-tell]], [[blob-addressing-spec-state]].

---

## The sharpening, measured 2026-08-10 — quoting is not enough

Three times in one session I **did** quote code, and was still wrong, because I quoted the wrong end
of the mechanism:

| I cited | I concluded | Reality |
|---|---|---|
| `sourceMdHash` is written (`serve-doc.ts:124`), schema'd, commented | freshness compares it | `isFresh` (`read-model.ts:20-24`) compares titles + `generatorVersion` only. Its sole readers are on the sync path, and `companion.ts:43` says so |
| the refund rule at `serve-doc.ts:130-132` is untouched | refunds still happen | bounding the settle RPC means a release-path timeout never applies the refund |
| postgrest exposes `.abortSignal()` | an abort throws | `shouldThrowOnError=false` by default; the abort is caught and **returned** as `{error}` |

Each cited artifact was real. Each said nothing about the behaviour claimed.

> **CITE THE CODE THAT PERFORMS THE BEHAVIOUR, NEVER THE CODE THAT PREPARES IT.** A written field, a
> preserved rule, an exposed API — none of them *do* anything. Cite the **reader**, the **executor**,
> the **consumer**. "X is written" is not evidence about who reads it; "the rule is unchanged" is not
> evidence that it still runs.

The tell is a sentence whose subject is a *preparation* ("is written", "is unchanged", "is supported")
carrying a conclusion about an *outcome*. When you catch one, go find the consumer and quote that.

Twice the refutation was already in the repo, in a comment written by whoever last worked that seam.
See [[postgrest-abort-returns-not-throws]], [[serve-path-bounding-merged]].
