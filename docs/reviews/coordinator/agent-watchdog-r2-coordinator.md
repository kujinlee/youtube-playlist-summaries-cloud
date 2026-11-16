# Round 2 — `agent-watchdog` — coordinator — ⟳ NOT CONVERGED (Codex half); every finding FIXED by a redesign

The Codex half reviewed the round 1 fold `b61d0e5a` (PR #596, backlog #657): `gpt-6.1-sol`,
`docs/reviews/codex/agent-watchdog-r2-codex.md`. NOT CONVERGED: 4 MAJOR, 1 MINOR.

REVIEW GAP: claude — alternation

```yaml
round: 2
fixes_nontrivial: true
subject: agent-watchdog
halves:
  codex: ran
  claude: gap
findings:
  - {id: R2M1, severity: Major, aim: deliverable, fix_induced: true, component: quiet-window, disposition: fixed}
  - {id: R2M2, severity: Major, aim: deliverable, fix_induced: true, component: quiet-window, disposition: fixed}
  - {id: R2M3, severity: Major, aim: deliverable, fix_induced: true, component: gitdir, disposition: fixed}
  - {id: R2M4, severity: Major, aim: deliverable, fix_induced: false, component: isolation, disposition: fixed}
  - {id: R2m5, severity: Minor, aim: deliverable, fix_induced: false, component: quiet-window, disposition: fixed}
```

**Three of the five findings were caused by the round 1 fold** (R2M1 and R2M2 in `quiet-window`, R2M3 in `gitdir`).
That is ONE round of fix-induced findings in each component. A round 3 finding caused by THIS fold in the same
component would be the second consecutive one, which is the arming condition of an architecture review.

## The design changed, not the symptoms

Round 1 judged activity by *"the newest modification time changed"*. Codex showed that signal is wrong in kind: a
maximum hides every write below it and every deletion, so repairing one input (the future stamp) made another one
false. The fold replaces the signal:

- **Activity is ANY change in a fingerprint of the observation.** `observe` returns one `(kind, name, mtime_ns,
  size)` per worktree file and directory, per git file (`HEAD`, `index`, `logs/HEAD`) and for the transcript;
  `fingerprint` hashes them sorted. No modification time is compared with a clock or with another time.
- **Elapsed quiet time is `time.monotonic`.** The wall clock (`wall=time.time`) only dates the report.
- **`.git` is opened once, non-blocking, and judged by `fstat` on the descriptor.** No path check precedes the open.
- **`main` turns any `OSError` or `ValueError` raised while observing ONE builder into CANNOT RUN for that
  builder**, beside the named `CannotRun` refusals, so the others are judged in the same poll.

Every fix was test-first. Eight cases were added to the suite and run against the unfixed code: `60/68`, all eight
red (quoted below). After the redesign the suite is `73/73`: the eight, three more that need the new seams (a
wall-clock step, the report's date, an `OSError` no rule anticipated), the fingerprint's order-independence, and
one split of an activity case. The activity cases were rewritten from *"which time is newest"* to *"did the
fingerprint change"*.

| Finding | Disposition | Fix and evidence |
|---|---|---|
| **R2M1** — activity below a retained maximum, and every deletion, is unseen | FIXED (design) | The fingerprint above. Red before, all `got (1, 10)`: *ordinary writes BELOW a retained future stamp are activity: written each minute to 7, woken at minute 17*; *a file whose time moves BACKWARDS at minute 4*; *a DELETION at minute 4 … even with its directory's time put back*; *a file that changes SIZE at minute 4 with its time put back* (each `want (1, 14)` but the first). Mutations: only the newest time compared again; an entry's size left out; an entry's time left out; the fingerprint made order-dependent. Retired with its code: *an mtime is compared with now again*. |
| **R2M2** — a wall-clock step shortens or extends the window | FIXED | `main(clock=time.monotonic, …, wall=time.time)`. Case *a wall clock that steps an HOUR forward or back at minute 1 changes nothing* (the suite's world now has two clocks that start 4 billion apart); case *the report is DATED by the wall clock*. Mutations: elapsed time read from the wall clock in the loop; the report dated by the elapsed clock. |
| **R2M3** — `.git` is checked, then opened: a FIFO swapped in between blocks every builder | FIXED | `os.open(dot, O_RDONLY \| O_NONBLOCK)`, then `fstat` decides directory / regular file / refused. Red before: *a .git that became a FIFO AFTER a path check* (`BLOCKED: gitdir_of trusted a path check`; staged by making every path check answer "regular file") and *a FIFO .git that delivers a valid gitdir line is still refused* (`BLOCKED: gitdir_of read a FIFO .git to its end`). Both are bounded by a thread, so a regression fails and never hangs. Mutations: the open made blocking again; the `fstat` verdict dropped; a `.git` that cannot be opened taken as the git directory. |
| **R2M4** — a `gitdir:` pointer holding a NUL raises `ValueError` and ends the poll for every builder | FIXED (design) | The `except (OSError, ValueError)` in `main`'s per-builder loop. Red before: `raised ValueError: stat: embedded null character in path`; now `CANNOT RUN b:` and `active a:` in one report, with the broken builder listed FIRST. A second case stages an `OSError` no rule anticipated (`os.walk` itself raising). Two mutations, one per exception type. |
| **R2m5** — the default production clock is untested | FIXED | Case *the DEFAULT clock is time.monotonic … and the default sleep is time.sleep* (red before: `(False, True)`). Mutations: the default clock is the wall clock again; the default clock never advances (Codex's own `lambda: 0`). |

**Manifest:** 53 → 63 mutations. One retired, eleven added, thirteen re-anchored or re-attributed to the renamed code and cases with the same
intent. Not mutated, and said so in the pin comment: `GITFILE_MAX` (a read bound no case can observe) and the
walk's vanished-file `continue`.

**Bounds this design has, now in the docstring:** a rewrite that leaves a file's name, time and size all the same
is not seen, and neither is a change made and exactly undone between two polls. The race case stages the swap by
substituting the path checks, since two real processes cannot be scheduled deterministically; it would fail for
any implementation that lets a path check decide.

## Gates, on the fold commit

- `python3 scripts/agent-watchdog.py --self-test` → `73/73 self-test cases passed`
- `python3 scripts/check-plan-code.py --mutate . --only scripts/agent-watchdog.py` → `OK — delivered scripts mutated: 1 file(s), 63 mutation(s), 63 killed, 63 attributed to the case each names, 0 survivor(s)`
- `check-ratchet-contract.py` → `ratchet contract OK`; `check-selftest-counts.py --only agent-watchdog.py` → verified;
  `check-fixture-variation.py` → `fixture variation OK`; `check-docs.py`, `check-reference-namespace.py` → OK.

Round 3 owes the Claude half (alternation).
