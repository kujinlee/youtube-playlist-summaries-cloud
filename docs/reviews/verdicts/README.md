# Review-gate verdicts

One JSON file per `scripts/codex-review.py` run, named after the review it is about.

**Commit them.** `scripts/check-review-rounds.py` reads this directory in CI, and a verdict that
never gets committed is a verdict nobody reads — which is the failure the mechanism exists to close
(backlog #68(d)). The account is in
[`../../process-rationale.md`](../../process-rationale.md) → *The review gate that wrote over its own evidence*.

## The one field that matters

`gate_ran` — **stated by the wrapper, never derived from `exit_code` by a reader.** Two independent
fields on purpose: re-deriving one from the other would be a second implementation of the wrapper's
rule, and the copies drift.

The check fails when a verdict says the gate did **not** run and a review is filed under its name
anyway. It stays silent when the gate did not run and left nothing behind — that is the documented
Codex-down fallback (`docs/plugins.md`), and punishing it would push people back to silence.

## Why the exit code was not enough

Measured 2026-08-28: a caller wrapped the run as `… ; echo "WRAPPER_RC=$?"`, so the reported status
was the **echo's**. `WRAPPER_RC=1` sat unread while the round was treated as reviewed, and its Codex
half never ran. The same trap reappeared while *verifying this fix* — piping the wrapper into `tail`
made the shell report `rc=0` — and the verdict file still recorded `exit_code: 1, gate_ran: false`.
