<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head: ba7025ac7c76ea0c90a56d94b422172a3b91b196

Both original suites passed: answerer **123/123**, server **291/291**. Experiments used temporary copies and fake binaries. No real Claude, port 7391, repository edits, or GitHub actions.

## Findings

1. **HIGH — concurrent stops can signal an unrelated process without any watcher starting.** `scripts/ask_answerer.py:915–921`, `scripts/ask_answerer.py:1243`.

   **Ran:** `/tmp/review625_probe.py`: created a stale `answerer.pid` naming an unrelated `sleep 60`; held `ledger.lock`; launched one `stop(root)`, which acquired `watch.lock` and blocked on the ledger; invoked a second `stop(root)`.

   **Measured:** the second stop sent SIGTERM to the unrelated sleep; its exit status was **-15**. Releasing the ledger allowed the first stop to finish.

   This fold makes the death acknowledger look like a live watcher throughout its ledger wait. Unlike #638, this requires **two stops and no start**, and ledger contention can extend the window indefinitely. It violates R4’s isolation intent. **Not BLOCKER:** no reader instruction caused this action, and no page corruption or unbounded spend was demonstrated.

2. **LOW — the documented restart remedy does not answer previously failed questions.** `.agents/skills/shared/explainer-delivery.md:448`, `scripts/ask_answerer.py:923`.

   **Ran:** extended the temporary suite with two pending questions, one session claim, one recorded failure, a stale pid, two stops, a question after the stop, and a restart using the suite’s fake.

   **Measured:** states after restart were:
   ```
   answered, answered, claimed, failed, skipped
   ```
   Exactly two model runs occurred. The failed question stayed failed, although §6b says “the next start answers it.”

   This is a documentation discrepancy concerning R2’s recovery behavior, not a newly introduced execution regression. **Not BLOCKER:** the failure remains visible; explicit retry remains available.

3. **LOW — the new usage case does not protect the log correction.** `scripts/ask_answerer.py:2136`.

   **Ran:** on the temporary copy, changed only the answer log’s `{used}` back to `{run.tokens:,} tokens`, retaining the corrected page stamp.

   **Measured:** the new `r3` case stayed green; no assertion detected the misleading unmeasured log. Both the unchanged temporary suite and this mutant passed **117/118**; their sole failure was the same missing tracked-page fixture because the copy contained scripts only.

   Thus the test permits regression of round-3 finding 4’s log half, weakening verification of R3’s visible accounting. **Not BLOCKER:** this is a test gap; the reviewed production code formats that log correctly.

The adjacent lifecycle inputs held: both pending questions retained **NOT ANSWERED** through stopping and were answered on restart; the session claim survived; the post-stop question was skipped. Repeated stops on a never-started root created no `.ask/`.

A real temporary watcher retained its pid file when `acknowledge_death` encountered its held lock, and `stop` terminated it cleanly. Lock-path inspection found no reverse blocking acquisition or opportunity for the new retry writes to erase a concurrent claim or completed answer. Measured usage retained its token label; forcing every run to say “usage NOT reported” failed the existing stamp and log assertions.

## Loosening answers
LOOSENING-CHECK e723b5dccb0b: not a loosening
LOOSENING-CHECK c0246dcc58a0: not a loosening
VERDICT: NOT CONVERGED
