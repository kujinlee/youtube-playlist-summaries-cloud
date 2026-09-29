# Round 6 — `explainer-src-root-self-configures` (PR #295) — coordinator

```yaml
round: 6
fixes_nontrivial: true
subject: explainer-src-root-self-configures
halves:
  codex: ran
  claude: ran
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: false, component: start-restart, disposition: fixed}
  - {id: L1, severity: Low, aim: instrument, fix_induced: true, component: duplicate-key-guard, disposition: fixed}
  - {id: L2, severity: Low, aim: instrument, fix_induced: true, component: duplicate-key-guard, disposition: fixed}
  - {id: L3, severity: Low, aim: instrument, fix_induced: false, component: mutation-manifest, disposition: fixed}
```

⚠ **THIS DOCUMENT WAS WRITTEN LATE, AND THE TOOL IS WHY.** Round 6's halves both ran and its
findings were fixed and pushed, but no coordinator document was filed — the record jumped from 5 to
7. `check-review-decision.py` refused: *"rounds are not gapless: found [1, 2, 3, 4, 5, 7], expected
[1, 2, 3, 4, 5, 6] — refusing to infer adjacency from list position."* That refusal is the whole
point of the header: **the two counters Q4 and Q5 need are adjacency counters**, and a missing round
would have made "two consecutive rounds" unanswerable while looking answerable. Recorded here rather
than silently backfilled, because a round document written after its fixes is weaker evidence than
one written with them, and the reader should know which this is.

## Verdict: FINDINGS — one High, three Lows

**The halves disagreed for the fifth time.** Codex returned CONVERGED on round 5's fix — correctly;
the coordinator re-verified it independently. The Claude half found a race the brief never named.

## H1 — two concurrent restart presses leave the pidfile naming a dead pid → **FIXED**

`_regenerate` has always taken a lock; `_restart` took none. Two presses land as two threads of one
`ThreadingHTTPServer`, both respawners pass `start()`'s `port_busy` pre-check, and the loser's child
dies of `EADDRINUSE` — but its pid is already written, and `port_busy` then answers true about the
**winner's** listener, so it prints `serving … (pid N)` for a corpse.

⭐ **The damage lands exactly on what this branch exists to build:** afterwards `--restart` fails
permanently and `--stop` reports *"not running"* about a running server, then unlinks the last
pointer to it — the fallback commands whose own docstring calls them *"the same one whether the
server is running or dead."*

**Novelty checked, not assumed:** `start()` is byte-identical to master (1016 chars, verified) and
master has no `respawn`, no `--restart`, no `/_restart`, and one caller. The TOCTOU is old; **this
branch creates the reachability** by putting a button on five page types whose design expects
several stale tabs open. Reproduced by the coordinator over a control: pre-fix pidfile named a dead
pid, fixed tree named the live one.

⚠ Fixed in two parts — a `RESTART_LOCK` and `start()` verifying its own child — **both of which
round 7 then found further defects in.** That chain is answered in round 7's Q5.

## L1, L2 — the duplicate-key guard written in round 5 → **FIXED**

It raised `TypeError` on a chained assignment target (`sorted()` over `{None, str}`), and it walked
into **function bodies**, so a future self-test fixture containing a deliberate duplicate — exactly
what its own falsifier writes — would have been reported as a defect in the file. Now `tree.body`
only, which is the correct population: the ratchets are module constants.

## L3 — `restart_control` had no mutation entry → **FIXED**

The one new function in the branch with nothing in the manifest. Added (13 → 14, declared sum
645 → 646) and proved red via the case it names over a green 76/76 control.

## Q4 / Q5 at the time of this round

Another round owed (a High, and unreviewed fixes). Thrashing: **not armed at round 6** — `H1` was an
original defect made reachable by the branch, not a defect introduced by round 5's fix. The chain
that matters begins with this round's own fixes and is assessed in round 7.
