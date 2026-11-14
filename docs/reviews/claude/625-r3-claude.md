Reviewed head: b471cb87426b2fbe17859a939a0691eea5519951

# Round 3 — `625` (the Ask answerer) — Claude half — adversarial review of the round-2 fold

Both suites ran on this head: `python3 scripts/ask_answerer.py --self-test` → **120/120**, rc 0;
`python3 scripts/explainer-serve.py --self-test` → **291/291**, rc 0. Every experiment below ran on a copy of
`scripts/ask_answerer.py`, `explainer-serve.py`, `page_chrome.py` and `page_markup.py` in a temp folder outside the
repository, with a temp `EXPLAINER_SERVE_ROOT` and a fake `claude` (a shell script). No real `claude`, no port 7391,
nothing under `.claude/plans/` read, nothing in the worktree changed except this file. The mutation sweep was NOT
re-run (the five new manifest entries were checked by reading their anchors and the cases they name, below).

Scripts (outside the repo): `.../scratchpad/b625r3/x1x4.py`, `x2.py`, `x3race.py`, `x3restart.py`, `x3stale.py`.

## Per round-2 finding: does the fix hold for the adjacent input?

- **X1 (carriage returns) — HOLDS.** MEASURED: the forged-entry text with its `\n` replaced by each of LF, CR,
  CRLF, `\r\r\n`, `\n\r`, VT, FF, FS, GS, RS, NEL (U+0085), LS (U+2028), PS (U+2029) and NUL, formatted by
  `format_question_entry`, written in text mode as the server writes, and read by `read_questions` → **1 question on
  `p.html` every time**. The same 14 separators in `doc` → 1 question each (the page name collapses to one line).
  Why: the read path is `read_text` (universal newlines translate only `\r`, `\r\n`) then `.split("\n")`; nothing
  in it calls `splitlines`. A lone surrogate (`"a\ud800b"`) raises `UnicodeEncodeError` at the server's write:
  nothing is recorded and the handler errors (pre-existing; a reader cannot easily type one; not filed).
- **X2 (no usage → unmeasured) — HOLDS for the ledger.** MEASURED `parse_result`: cache-only usage → 5,000
  measured; negative, string, float, nested, a list as `usage`, cost-but-no-usage → 0 tokens, `unmeasured` True;
  two result objects or a JSON array → not a result, unmeasured. Only `{"input_tokens": true}` counts as 1 measured
  token (Python `bool` is an `int`; the CLI never emits it — not filed). No double count: every path after a `run`
  line writes exactly one `answered`/`failed` event, and `unmeasured` implies `tokens == 0`, so `spent()` adds the
  assumption once per run. `--status` is right (`250,000 of 3,000,000 tokens … ⚠ 1 run(s) ended with NO usage`);
  the page stamp and the log are not — finding 4.
- **X3 (`--stop` after a crash) — fixes Codex's input, breaks two adjacent ones** — findings 1 and 2.
- **X4 (`elsewhere`) — HOLDS.** MEASURED `cross_site` passes the page's own POST as a browser sends it:
  `http://127.0.0.1:7391`, `http://localhost:7391`, `http://[::1]:7391`, Host in upper case, Host with spaces, a
  POST with no `Origin` (curl). Refused: `null`, another port on either local name, an empty Origin, `file://`,
  `127.0.0.2`, `0.0.0.0`, `[::ffff:127.0.0.1]`, a rebound name. A browser cannot set `Origin` or `Host`, and a page
  on another port always sends its own port in `Origin`, so I found no browser-producible shape that passes.
  `https://127.0.0.1:7391` passes, but no other server can hold port 7391. A trailing dot (`localhost.:7391`) is
  refused for the page's own POST too — pre-existing from round 1, a page nobody opens that way; not filed.
- **X5 (403 before the body) — the case can fail**, for the mutant it names (guard moved below the JSON parse →
  foreign `{` gets 400). It cannot see a weaker mutant — finding 5.

## Findings

### 1. MEDIUM — a `--stop` after a crash also skips the questions the page had ALREADY marked NOT ANSWERED

`scripts/ask_answerer.py:1199-1206` (`stop`), with `ensure_baseline` (`:899`) and `page_items`/`panel_lines`
(`:1030`, `:1065-1072`).

**Ran** (`x3restart.py`): a ledger with a baseline; a dead pid file left with no lock held (an unclean end); a
question asked on `p.html`; then `stop(root)` and a start (`watch(..., passes=2)`).
**Observed:**
```
after crash, page panel: ['⚠ <strong>NOT ANSWERED — the Ask answerer stopped unexpectedly.</strong>']
after --stop, page panel: []
after --start: status skipped | runs started False | page panel: []
```
The reader was shown ⚠ NOT ANSWERED with "Start it again"; after the owner's `--stop` + `--start` (the ordinary
restart idiom) the question is skipped, never answered, and **vanishes from the page** — no answer and no
NOT ANSWERED. That contradicts the rule the docstring states at `:52-54`: *"NOT skipped, because the page has said
NOT ANSWERED about each: a question asked after a watcher ended with no clean exit"*. The new case's own name says
the next start skips *"what was asked after it"* (after the stop); its fixture asks only AFTER the stop
(`after_stop`, `:2041`), so it is satisfied by its fixture and never tries the adjacent input — a question asked
between the crash and the stop. The coordinator's round-2 note lists this as a bound, but the bound breaks R2's
"a question with no answer must never look answered" in the weaker form "a failure must be LOUD on the page": a
⚠ the reader saw disappears without an answer. (The terminal message warns the owner; the reader is not told.)
**Violates:** R2 (loud failure on the page), and the script's own stated skip rule.
**Caused by the round-2 fold: yes** — before it, `--stop` on a dead watcher changed nothing, so a later start
answered these questions.
**Suggested direction (inference, untested):** when `stop` clears the record, also mark the questions that are
waiting at that moment as already touched (e.g. one ledger event the baseline honours), so only questions asked
after the stop are skipped — what the case name already claims.

### 2. LOW — a `--stop` racing a `--start` deletes the LIVE watcher's pid file; that watcher can then not be stopped

`scripts/ask_answerer.py:1199-1202` — `watcher_died(root)` is checked, then the pid file is unlinked, with no lock
held between the two.

**Ran** (`x3race.py`): a dead pid file; `stop(root)` with `watcher_died` wrapped so that, after it returns True and
before the unlink, a REAL `ask_answerer.py --watch` (temp root, fake claude) starts and writes its pid.
**Observed:**
```
after: child alive True | watcher_running True | pid file exists False | watcher_pid 0 | watcher_died False
second --stop rc 0 said: ask-answerer: not running
child still alive after the second --stop: True
status first line: ask-answerer: not running
--start rc 1 … DID NOT START (exit 3)
```
A running watcher that `--status` reports as not running, that `--stop` cannot stop, and that blocks `--start`.
Spend stays inside the daily caps. The window is two statements wide and needs `--stop` and `--start` issued at the
same moment, so it is not normal use: LOW. Fix: unlink only while holding `watch.lock` exclusively (LOCK_EX|LOCK_NB;
if that fails, a watcher is alive — do not unlink).
**Violates:** R6 in spirit (a watcher that cannot be turned off with the documented command).
**Caused by the round-2 fold: yes** — the unlink is new; before it, `stop` deleted nothing.
(Measured with a forced interleaving; the natural frequency is inferred to be very low.)

### 3. LOW — `--stop` can SIGTERM the stale pid while a new watcher is starting

`scripts/ask_answerer.py:888-890` with `:980-981` and `:1209`. A starting watcher holds the lock BEFORE it
replaces the dead pid file, so in that window `watcher_pid()` returns the DEAD watcher's pid and `stop` signals it.
**Ran** (`x3stale.py`): a pid file naming an unrelated `sleep 30` (a reused pid), the lock held as a starting
watcher holds it, then `stop(root)`. **Observed:** the unrelated process got signal 15; `stop` printed
`pid … did not stop within 10 s`, rc 1. Window of a few statements; pid reuse needed for harm.
**Violates:** R4 in spirit (a process outside the answerer is signalled). **Caused by the round-2 fold: no** — the
pid file left by an unclean end dates from round 1.

### 4. LOW — an answered run with no usage still says "0 tokens" on the page and in the log

`scripts/ask_answerer.py:777` (page stamp) and `:790-791` (log line).
**Ran** (`x2.py`): a fake `claude` that prints a `success` result with `usage: {}`; `answer_one` end to end.
**Observed:** ledger `tokens 0, unmeasured True`; `--status` `250,000 of 3,000,000 tokens … ⚠ 1 run(s) ended with
NO usage reported`; but the answer block's stamp reads `Headless sonnet, Read tool only: 2 turns, 0 tokens, $0.12`
and the log `… · 2 turns, 0 tokens`. R3 asks the cost to be visible; the page shows a measured-looking zero for a
run whose spend is unknown. The real CLI reports usage on success, so this is a display bound.
**Caused by the round-2 fold: no** — the stamp predates it; the fold made this state reachable as `answered` but did
not carry it to the stamp.

### 5. LOW — the new 403-before-body case cannot see a guard that reads the body first

`scripts/explainer-serve.py:4491`. The case name says the refusal comes *before the body*; it compares only status
codes (foreign `{` → 403, own `{` → 400). A mutant that reads `self.rfile.read(length)` into a variable before the
`cross_site` check, and parses after it, gives the same two codes. So does a guard moved below the
`Content-Length` checks for any length the case sends. **Inferred from the code, not run.** Nothing is recorded
either way, so no requirement is at risk; the case name overstates what it proves.
**Caused by the round-2 fold: yes** (the case is new in it).

## Tried and could not break

- X1: 14 separators in the text and in `doc`, and a lone surrogate — no forged entry (above).
- X2: 10 malformed `usage` shapes, several result objects, double counting in `spent` — only a `bool` token count,
  not real.
- X4: 20 Origin/Host shapes — no browser-producible cross-site shape passes; the page's own POSTs pass.
- The five new manifest entries: each anchor occurs once in the file; each named case goes red under its edit by
  reading (the r1 cases use `\n` only, so the CR mutation is killed by the r2 case; `if False:` makes the stop case
  answer `after_stop`; `silent = False` and the `== "failed"` edit each flip a value the r2 X2 case pins). Not
  re-swept.
- Documents: §6b's caps (10 turns, $0.75, 240 s; 40 questions, 3,000,000 tokens), the docstring's 120 cases, the
  server's 291 cases, backlog row 625's "+9 cases, +11 mutations" (282→291, 112→123 against `origin/master`) all
  match the code.

## Measured vs inferred

Measured: every "Ran/Observed" above, and both suite counts. Inferred: finding 2's real-world frequency, finding 5
in full, and the suggested fixes.

VERDICT: NOT CONVERGED
