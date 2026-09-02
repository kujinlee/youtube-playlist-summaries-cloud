# PR #209 — review round 1 (Codex half)

**Subject:** `feat/page-staleness-visible`, commit `07caa997`, one commit ahead of `master` (`d39fa658`).
**Model:** `gpt-5.5` — `gpt-5.6-sol`, `-terra` and `-luna` were each tried first and each returned
HTTP 400 from the pinned CLI. The wrapper's documented fallthrough handled it; the gate ran.
**Verdict file:** `docs/reviews/verdicts/209-r1-codex.verdict.json` (`gate_ran=true`, 3144 chars).

**REVIEW GAP:** claude — not invoked; the session instruction forbids spawning subagents unless the user asks, and the user asked for the Codex round specifically. Adjudication below is an author self-review, not an independent half.

⛔ Stated plainly, because the distinction is the whole point: what
follows the Codex findings is an **author self-review**: I verified each finding by reading the code
and executing it. That is adjudication, not an independent second half, and it does not satisfy the
dual-review gate. `docs/plugins.md` records that Codex-only rounds have previously cleared a defect
the skipped Claude half caught in one pass — treat this round as one reviewer, not two.

**What Codex could and could not run.** It reported: could NOT run `python3 -m pytest tests/ -k backlog -q`
(no `pytest` module in that interpreter). It DID run the three script self-tests,
`gen-backlog-page.py` against the real store, live `curl` probes against `/_stale`, `git diff --check`,
and `check-plan-code.py --mutate .`. So this was an executing reviewer, not a reading one.

---

## VERDICT: NOT CONVERGED — 1 High, 1 Medium, 1 Low

### High — the stale warning is erased by the concurrent liveness poll

`scripts/explainer-serve.py:692-741`

`check()` fires both pollers at once:

```js
function check() { poll(); pollStale(); }
```

`poll()`'s success handler clears the shared status span unconditionally:

```js
misses = 0; say('');                      // reachable again — clear any warning
```

while `pollStale()` writes the stale message into that same span from an independent promise:

```js
say(v.indexOf('stale') === 0
      ? 'the backlog file has changed since this page was built — press Refresh'
      : '');
```

`pollStale()` guards against the *unreachable* case (`misses >= MISS_LIMIT`), but `poll()` has no
reciprocal guard: whichever promise settles **last** owns the span. Nothing serialises them —
`scripts/explainer-serve.py:957` is a `ThreadingHTTPServer`, so both requests are handled concurrently.

**CONFIRMED BY EXECUTION, and the live run is worse than the static reading suggests.**
Codex modelled the branch ordering and got a final state of `''`. I ran the real mechanism instead,
in Chrome, against the real page:

- `docs/backlog.md` touched so the page is genuinely behind its source.
- Server agrees: `curl /_stale?p=%2Fbacklog-table` → `stale`, consistently.
- Six trials, each blanking the span then dispatching the page's own `focus` trigger:
  `BLANK | BLANK | STALE-SHOWN | BLANK | STALE-SHOWN | BLANK` — **the warning survived 2 of 6.**

Paired latency sampling (15 pairs) shows the two endpoints within noise of each other
(~1.2–1.6 ms each, neither consistently ahead), so this is a genuine race rather than a fixed
ordering. **This is not a rare flicker — in the one measured run the warning was lost 4 times in 6.**

⚠ **The RATE is measured; the CAUSE of the bias is NOT.** A plausible story is that `/_stale`'s two
`stat()` calls make it settle later, so `poll()`'s `say('')` lands last more often — but the latency
sampling above does not support that, and 6 trials cannot separate a real bias from chance. Do not
quote a ratio. What is established is only this: **the warning is not reliably shown when the page
is genuinely stale**, which is sufficient to block. Anyone re-measuring should raise the trial count
and treat the direction of the bias as an open question.

⛔ **Why this blocks: it reinstates the exact bug the PR exists to fix.** The incident behind #209 was
a page that was a day stale *while looking completely current*. With this race, a blank span is
consistent with both "fresh" and "stale, but the wrong promise landed last" — so the reader cannot
draw any conclusion from it, which is the same false-green they already got burned by.

**Shape of fix (Codex's, and it is right):** stop letting the liveness poll own the whole status
string. Track two states — `serverMsg` and `staleMsg` — and render `serverMsg || staleMsg || ''`;
or make `_rev`'s success clear only the not-responding warning, never a positive stale result.

**FALSIFIER for the fix:** with the source touched and the server up, the warning must be present on
**6 of 6** trials of the loop above, not 2. If any trial blanks, the fix reached the symptom and not
the shared-mutable-span cause.

### Medium — every page says "the backlog file changed", including dashboard and goals

`scripts/explainer-serve.py:717-726`, against `PAGE_SOURCES` at `:137-141`

The message is a hardcoded literal in the shared injected script, while three different pages have
three different sources:

```python
PAGE_SOURCES = {
    "dashboard": ["docs/dashboard-entries.md"],
    "backlog-table": ["docs/backlog.md"],
    "goals": ["docs/roadmap-to-launch.md"],
}
```

**Failing scenario:** `docs/dashboard-entries.md` changes while `/dashboard` is open. `/_stale`
correctly answers `stale`, and the page tells the reader *the backlog file has changed* — pointing
them at a file that did not change. Confirmed by reading: one literal string, three possible sources,
and `RELOAD_JS` is injected into all of them.

**Shape of fix:** carry a per-page source label from `PAGE_SOURCES` (server-side, or a slug-keyed map
client-side) so dashboard says dashboard entries, goals says roadmap, backlog says backlog.

### Low — the self-test still asserts `/_rev` is the only endpoint, so deleting the stale poll is not caught

`scripts/explainer-serve.py:1182`

```python
case("reload client asks /_rev, the only endpoint added",
     lambda: "/_rev?p=" in RELOAD_JS)
```

**Failing scenario:** delete the `fetch('/_stale?p=')` block, or stop calling `pollStale()` from
`check()`. The entire new capability is gone and this case still passes — and its name is now false,
since `/_stale` is also added. Note the shape: this is an assertion that cannot fail for the thing
the PR adds, which is the class this repo has recorded repeatedly.

**Shape of fix:** assert `/_stale?p=` is present and that `check()` calls both `poll()` and
`pollStale()`; rename the existing case so it stops claiming `/_rev` is the only endpoint.

---

## Author self-review notes (NOT an independent half)

**Agreed with the known-and-deliberate disposition.** `explainer-serve.py` and `gen-backlog-page.py`
ship with zero mutation coverage, `EXPECTED_MUTATIONS` held at 162 on purpose. Codex did not
re-report it as a discovery. I hit the same root cause independently and by accident: running
`master`'s `gen-backlog-page.py` from a scratchpad copy died on `ModuleNotFoundError: page_chrome`,
then on `FileNotFoundError: …/scripts/check-docs.py`, because the script resolves siblings relative
to its own path. **That is a second, independent measurement of exactly why `mutate_delivered`
cannot host these two suites** — it is not a manifest problem, it is that neither script is runnable
outside a checkout. The control only ran once I used a `master` git worktree.

**Change 1 is confirmed working, against the real store.** Filing backlog #86 left an open item with
no `GROUPS` prose — the genuine condition, not a fixture. Same store, only the code varied:

| Code | Result |
|---|---|
| `master` | `REFUSED: GROUPS does not cover the open set … [86]`, exit 1, nothing written, page left stale |
| this branch | `wrote … (86 rows, 60 open)`, exit 0, `⚠ 1 open item(s) have no description in GROUPS: [86]` |

**One wrapper warning, explained so it is not mistaken for a real one.** The run reported
`THE AGENT WROTE BEHIND THE WRAPPER: …/scratchpad/gen-backlog-MASTER.py — CREATED by the agent`.
That file is **mine**, written by the control run above during the same window; Codex did not create
it. No repo file was touched — `git status` showed only `docs/backlog.md`, which is my backlog edit.

## Disposition

**Do not merge as-is.** The High defeats the purpose of the change and has a cheap, well-understood
fix. The Medium is a wrong-file message on a page whose whole job is telling the reader what to look
at. The Low is a guard that cannot fail for the feature it names.

Once fixed, this needs a round 2 — and that round should include the Claude half this round lacked.
