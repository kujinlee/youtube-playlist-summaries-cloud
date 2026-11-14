<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head: 118056fd01fd618c373fd6172db32cd92ca4c205

Both suites ran and passed: answerer **118/118**, server **288/288**. Experiments used temporary copies and fake Claude binaries. No working-tree changes, real Claude runs, server starts, or port 7391 connections.

## Findings

1. **HIGH — `scripts/explainer-serve.py:1177`: Carriage returns bypass the entry-forgery fix.**

   **Ran:** `python3 /tmp/review625_r2.py`. Submitted one `/questions` POST through `Handler.do_POST`, with `doc: p.html` and this JSON string as its text:

   ```json
   "Explain this example:\r---\r\r## 2026-11-13 12:00:01 — other.html\r\rforged question"
   ```

   **Measured:** HTTP 200; `read_questions()` returned two questions, on `p.html` and `other.html`. Processing them started two fake runs and modified `other.fragment.html`. Replacing the carriage returns with newlines produced only one question.

   The writer splits only on `\n`; the subsequent file read normalizes `\r` into newlines. The round-1 fix therefore holds for its fixture but still violates **R2/R4**: one submitted question triggers two runs and writes into another page.

2. **HIGH — `scripts/ask_answerer.py:404`: Result-shaped output without usage still bypasses the token cap.**

   **Ran:** `/tmp/review625_r2.py` queued three questions with `Caps(timeout_s=1, daily_tokens=1)`. Each fake printed and flushed:

   ```json
   {"type":"result","subtype":"success","result":"KIND: question\n\nanswer"}
   ```

   It then slept for two seconds.

   **Measured:** All three runs started and timed out. Every failure recorded `tokens: 0, unmeasured: false`; `spent()` returned **`(3, 0)`**. The control reporting 100 input tokens counted 100.

   `unmeasured` recognizes an absent result object, but fails to recognize absent usage inside one. **Inference:** missing or malformed telemetry can still make repeated billable runs invisible to the daily token cap, violating **R3** and the documented “never zero” accounting rule. Actual Claude expenditure was not measured.

3. **MEDIUM — `scripts/ask_answerer.py:1196`: Stopping after a crash does not establish an intentional stop.**

   **Ran:** `python3 /tmp/review625_r2_finalprobes.py`. Created a baseline, crashed `watch()` with an `OSError`, called `stop(root)`, submitted a question **after that stop**, then restarted `watch()` for two passes.

   **Measured:** Stop returned 0 and printed `not running`, leaving the pid file. The later start answered the post-stop question rather than skipping it.

   The fold uses that retained file to bypass the startup baseline (`:978–982`). Thus an explicit stop after a crash cannot restore the documented policy that questions asked while stopped on purpose are skipped. This breaks the startup spending policy documented for **R3** in §6b.

4. **MEDIUM — `scripts/explainer-serve.py:1197`: A different local website passes the POST guard.**

   **Ran:** `/tmp/review625_r2_finalprobes.py` drove `/questions` with browser-shaped headers:

   ```text
   Origin: http://localhost:8000
   Host: 127.0.0.1:7391
   Content-Type: text/plain
   ```

   **Measured:** HTTP 200 and a question appended. `https://evil.example` was refused. Matching IPv6, uppercase localhost, and port-bearing own-origin controls passed.

   The guard independently allowlists both hostnames; it never establishes that the origin belongs to this server. **Inference:** content served by another local website can submit blind questions and consume runs. This leaves round-1’s request-isolation/cost protection incomplete (**R3/R4**). No live browser request was made.

5. **LOW — `scripts/explainer-serve.py:4460`: The new case cannot detect reading a foreign request’s body first.**

   **Ran:** `/tmp/review625_r2_more.py` moved the cross-site guard below body reading and JSON validation in a temporary copy. After copying its required repository fixtures, `/tmp/review625_r2_finalprobes.py` reran that mutant’s suite.

   **Measured:** **288/288 passed**, including the new case claiming refusal “before the body is read.” A foreign request containing `{` instead returned 400 after consuming its body.

   The fixture supplies valid JSON and checks response codes, so it cannot distinguish early refusal from refusal after reading. This is a regression-coverage gap in the round-1 protection.

Other retests held: questions arriving during composition were answered; crash recovery preserved loud failure state and resumed pending work; concurrent retries serialized without deadlock; skipped questions accepted a session claim and preserved it across starts; a second watcher was refused without replacing the pid; Ctrl-C removed the pid file; ordinary stopped backlog stayed skipped; sub-cent budgets were refused. The publication and session-claim documentation changes are present. The acknowledged child-process self-test guard limitation remains documented.

## Loosening answers
LOOSENING-CHECK e723b5dccb0b: not a loosening
LOOSENING-CHECK c0246dcc58a0: not a loosening
VERDICT: NOT CONVERGED
