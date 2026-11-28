Reviewed head: caf8aa7cda9d097723132eb96764e9b9d5f47e5b

# Round 5, Claude half: `explainer-port-631` (PR #651, backlog #631)

Scope: the two commits that landed after round 4. `95cf4290` makes `--stop` signal only the pid the token proved
(Codex B1). `caf8aa7c` varies `after_fork`'s token and the record's root, and exempts the loopback host. I read both
in the context of `scripts/explainer-serve.py` as a whole. The mandate was to REFUTE. Nothing touched port 7391.

## What was run

- `python3 scripts/explainer-serve.py --self-test` at HEAD: **343/343 passed** (84 s).
- `python3 scripts/check-fixture-variation.py scripts/explainer-serve.py`: rc 0, "fixture variation OK — 89
  parameter(s) examined … 78 exempt with a written reason".
- `scripts/mutations/explainer-serve.json` parses: 146 entries, which equals the pin `EXPECTED_MUTATIONS` = 146. Each
  new anchor occurs exactly once in the script.
- **The two new mutations, by hand.** Each was applied to its own `git archive HEAD scripts` copy in the session
  scratchpad, and the copy's `--self-test` was run.
  - B1 mutant (`if False:` in place of the pid check): 338/343. The extra failure is exactly `r4 Codex B1: --stop
    never signals the recorded pid when the token proved a DIFFERENT pid — exit 3`. The match control (`…and signals
    the recorded pid when the token proved that same pid`) still passes, as it should.
  - after_fork fixed-token mutant: 334/343. The failures include the named case `#631 the parent's OWN token decides,
    at two tokens…`, plus four real-server cases (Z1, control, Y4, X6).
  - Each copy also fails the same 4 repo-dependent cases (the explainer archive files and DIR_SOURCES are absent from
    the copy). Those 4 are ambient: they fail in both mutants alike, so they are not caused by either mutation.
- `python3 scripts/check-plan-code.py --mutate . --only scripts/explainer-serve.py`: **NOT RUN.** It runs 146 mutants,
  and one self-test takes about 84 s, so the run is far beyond the ~270 s call bound. Only the two new mutations were
  checked, by hand, as described above. Treat the full sweep as NOT RUN.

## Refutation attempts on B1 (`stop`, scripts/explainer-serve.py:2638-2683)

1. **Can `--stop` still signal a pid it did not prove?** `classify_listener` returns "ours" only if
   `answer.pid == ident.pid` and the answer's token equals the record's token, where `ident` is the `read_identity`
   taken inside `listener_verdict`. The new guard at :2653 adds `answer.pid == pid`, where `pid` is stop's own first
   pidfile read, the pid that `os.kill` receives at :2673. So the signalled pid equals the pid that a live listener
   answered with this root's current record token. I tried four interleavings: a restart between stop's read and the
   listener query; the answer from A with the record already rewritten to B; the record still A with B answering;
   and A dead and replaced. Each one reaches exit 3 without a signal. **I could not refute the fix.** What remains is
   the window between the proof and `os.kill`, which is pid reuse (B3), and token replay (B2). Both are deferred to
   backlog #748 by the owner's decision, so they are not re-raised here.
2. **The unused `_pid` from `listener_verdict`** is that function's own second pidfile read. Ignoring it is correct,
   because the guard compares against the pid that is actually signalled.
3. **The case's stubs** (:5305-5328) replace `os.kill` and five module globals, and restore them in `finally`. In the
   mismatch case, `forget` is stubbed, so no real record is touched and no real signal can be sent. The case asserts
   both the rc and the sent list, so a variant that exits 3 after signalling would still fail it.

## Refutation attempts on caf8aa7c

- The new after_fork case varies `own` while the answer's token and the record's token are fixed. Its two halves are
  rc 0 and rc 1. The mutant that compares against a fixed token gives (1, 0), so the case is load-bearing, as
  confirmed above. The second half's FAIL path calls `forget_own(..., "tok-B")` on a record carrying
  `tok-of-this-start`, which correctly leaves that record alone.
- `_two_roots` would go red if `tokenfile_for` or `read_identity` ignored `root`. Its expected dict matches what
  `write_identity` and then `read_identity` produce, and the pidfile agrees on 4242.
- The EXEMPT reasons check out. HOST is the 127.0.0.1 constant. `after_fork.pid` callers do vary the answer's pid
  (:5887 passes `_ans(1, …)`). The reason for `after_fork.token` is accurate, because the scan reads `own` as one
  expression.

## Findings

| id | sev | fix_induced | file:line | finding |
|---|---|---|---|---|
| F1 | MINOR | true | scripts/explainer-serve.py:2653-2671 | A B1 refusal prints a false message. **Scenario:** `--stop` reads pid A. Server A exits and B restarts in its place, writing records that name B. The listener answers "ours" with pid B, and the guard turns the verdict into "other-root". By now A is dead, so `forget(ROOT, PORT, A)` returns True. But it removed nothing, because both records name B. The message then says pid A "did not answer as this server — it may be … older code or another program" and "Removed the pidfile … (that pid is gone)". Both statements are false: the listener IS this server (pid B), and the pidfile was kept. The outcome is safe: no signal, no wrong deletion, exit 3, and a re-run stops B. But the text sends the owner looking for a foreign program. Before the B1 fix this race signalled; it now reaches this message. Fix: on this specific path, say "the server restarted as pid B between reads; re-run `--stop`", and report removal from what `forget` actually removed. |
| F2 | NIT | true | scripts/mutations/explainer-serve.json:831 | The new manifest entry lacks the two-space indent its siblings have. The JSON parses, so this is cosmetic. |
| F3 | NIT | false | scripts/explainer-serve.py:5865-5870 | The new two-token case asserts only `[0]` (rc) of each call, while its siblings assert the full tuple (FAIL line, child reaped, record kept). The first call's `record=(…, "tok-B")` has no effect on `after_fork`, which builds `own` from its arguments. The case still kills its mutant, so this costs nothing today. |

There is no BLOCKER. Under the round cap, F1-F3 are for the coordinator to FILE. None needs a fold in this PR.

```yaml
round: 5
subject: explainer-port-631
half: claude
findings:
  - {id: F1, severity: MINOR, aim: deliverable, fix_induced: true, component: explainer-serve}
  - {id: F2, severity: NIT, aim: deliverable, fix_induced: true, component: explainer-serve-mutations}
  - {id: F3, severity: NIT, aim: deliverable, fix_induced: false, component: explainer-serve}
```

VERDICT: CONVERGED
