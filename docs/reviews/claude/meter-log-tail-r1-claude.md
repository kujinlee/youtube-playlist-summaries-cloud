Reviewed head: f645d4bd7589714507703b8930f5b10f8d893f50

# meter-log-tail r1, Claude half (backlog #501, PR #531)

Scope: `git diff 8c5f75a7...HEAD`. Mandate: refute. All experiments ran in a scratch copy made with `git archive HEAD`
(and `git archive 8c5f75a7` for the base). Nothing in the worktree was modified except this file.

`python3 scripts/check-usage-pace.py --self-test`: **361/361 passed** (16 s).

## What I checked that held

- **Window edges.** At the bound the file is read whole and is not cut. One byte over, the read starts at byte 0 and
  the partial first line is dropped. A cut that lands exactly on a line start keeps that line, because the byte
  before it is the newline. A cut that lands mid-line drops the line. All four have cases, and the mutations of
  the seek, the extra byte and the drop each go red.
- **A cut inside a multi-byte UTF-8 character.** Never produces U+FFFD. The partial first line is dropped at the
  byte level before decoding, and 0x0A never occurs inside a multi-byte sequence. Measured for every `limit` from
  1 to 20 over `"é€€€\n{...}\n"`.
- **The file growing or being truncated during the read.** Growth is not read, because `want` is fixed from
  `fstat`. Truncation gives a short read, which yields fewer rows or an empty window: still `cut`, so the line is
  refused rather than wrong.
- **A FIFO.** It is `not a regular file` at once (`O_NONBLOCK`), and that has a case.
- **A slow file.** It goes through the same `_bounded` thread and deadline as before.
- **`read_regular` for its other callers** (lines 691, 737 and 860). Same behaviour: the same box, a 2-tuple on
  the exception and timeout paths (`extra=()`), and the same messages.
- **Wrong start versus refusal.** Under append order, a cut window with no midnight row and no earlier-window row
  is refused, never answered from a later row. A row exactly at midnight counts as `before`, as it does uncut. DST
  is unchanged, since `local_midnight` is untouched.
- **The real log** (`~/.claude/meter/log.jsonl`, read-only): 592 rows from 11-01 02:13 to 11-07 01:51, so about
  100 a day, at about 147 bytes a row. No row is out of order. `resets_at` takes exactly two values with no jitter,
  so the `r < resets` and `r != resets` tests are not disturbed by noise.
- **Mutation manifest.** All 164 anchors occur exactly once in HEAD. Each of the 9 new mutations and the 7
  re-bound ones goes red, and in every case all of its `expect` names are among the failing cases. I ran each one
  against `--self-test` in its own copy.

## Findings

### R1-F1 — High — `check-fixture-variation.py` goes RED on HEAD (green on base): three new parameters are never varied

`scripts/check-usage-pace.py:517` (`read_meter(limit=…, deadline=…)`), `scripts/check-usage-pace.py:398`
(`evaluate(meter_cut=…)`), and the list at `scripts/check-fixture-variation.py:390`.

**Scenario.** CI runs `python3 scripts/check-fixture-variation.py` (`.github/workflows/ci.yml:732`). On HEAD it
exits 1:

```
FAILED — 3 parameter(s) never varied by any case:
  ✗ check-usage-pace.py: `evaluate(meter_cut=…)` is passed the SAME value at every call site in the suite (5x `<omitted, default>`).
  ✗ check-usage-pace.py: `read_meter(deadline=…)` is passed the SAME value at every call site in the suite (2x `<omitted, default>`).
  ✗ check-usage-pace.py: `read_meter(limit=…)` is passed the SAME value at every call site in the suite (2x `<omitted, default>`).
```

On `8c5f75a7` the same command exits 0 with no `✗`. The PR's CI will therefore be red.

**Repro.** `git archive HEAD | tar -x -C $D && cd $D && python3 scripts/check-fixture-variation.py; echo $?` gives 1.
The same against `8c5f75a7` gives 0.

**Fix.** Vary each parameter in a real case rather than exempting it:
- an `evaluate(..., meter=<tail text>, meter_cut=True)` case that asserts the NOT RUN wording;
- a `read_meter(path, limit=<small>)` case on a file over that limit, asserting `cut` is True;
- a deadline case, which R1-F2 needs anyway.

### R1-F2 — Medium — `read_meter`'s failure arity is untested; breaking it crashes `main`, and the launcher then ALLOWS a spawn at the stop

`scripts/check-usage-pace.py:517-521` (`_bounded(..., (False,))`), `:524-539`, and `:865` (the 3-way unpack).

**Scenario.** `read_meter` returns a 3-tuple only because it passes `extra=(False,)` to `_bounded`. Its timeout path
and its reader-exception path are never driven by any case. In the self-test, every call either succeeds or is
answered inside `_read_tail` itself (missing file, FIFO).

The mutant `path, deadline, (False,))` → `path, deadline)` **survives the whole self-test** (rc 0, no `[FAIL]`).
With that mutant, a meter log that stalls or whose reader raises makes `read_meter` return a 2-tuple. `main`'s
`meter_text, meter_why, meter_cut = …` then raises `ValueError`, and the guard exits non-zero.
`.claude/hooks/usage-pace-run.sh` turns any non-zero exit into `cannot`. For spawn and wake, `cannot` **allows**
the call ("unknown is not a stop"). So a regression here, which the suite cannot see, would turn a stalled
**meter** read (a guide-only input) into the loss of the **stop** for spawns and wakes.

The code at HEAD is correct; the gap is that nothing would catch it breaking.

**Repro.** Apply the edit above in a scratch copy, then run `python3 scripts/check-usage-pace.py --self-test`. It
prints `361/361` and exits 0.

**Fix.** Add a case modelled on the existing r2 X3 deadline case (line ~1517, which swaps `_read_now` for a slow
reader):
- swap in a `_read_tail` that sleeps;
- assert that `read_meter(p, deadline=0.3)` returns `(None, "... not read within 0.3 s ...", False)`;
- assert that `main(...)` still returns the cache's verdict with the pace line NOT RUN.

Add a second case where the reader raises. Then add a mutation for the dropped `(False,)`. This case also varies
`read_meter.deadline`, which is part of R1-F1.

### R1-F3 — Low — a week reset between local midnight and the tail's first row is refused, though the cut part holds the answer

`scripts/check-usage-pace.py:333-334` (`at <= midnight and r < resets`).

**Scenario.** The log is over its bound and the tail starts after midnight. The tail holds rows of the previous
window written after midnight (the reset came at, say, 02:00), then this window's rows. Read uncut, the start is
this window's first row. Read cut, the line is **refused** with `TAIL_MISSES_MIDNIGHT`: the earlier-window row is
after midnight, so `earlier_window` stays False.

Under the bound the docstring already relies on (rows are appended in time order), **any** earlier-window row in
the tail proves that this window's first row is in the tail too. So `r < resets` alone is sufficient, and the
`at <= midnight` clause only adds false refusals. The mutant that drops `at <= midnight` survives the suite. Its
behaviour is the more correct one, not an equivalent one.

**Repro** (with `now` = local midnight + 10 h):
```
tail = row(mid+60, 99, OLD=mid+100) + row(mid+120, 2, R) + row(mid+180, 3, R)
pace_line(tail, now, R, cut=True)  -> (None, TAIL_MISSES_MIDNIGHT)
pace_line(tail, now, R, cut=False) -> (22.99…, '')
```

**Reachability.** At the measured ~100 rows a day and ~147 bytes a row, a 4 MiB tail spans about 285 days. A
tail that begins after today's midnight needs more than ~28k rows written in one day, so this is a guide-only
false refusal that is practically unreachable.

**Fix.** Make the test `is_number(r) and r < resets` and correct the docstring: "a row of an earlier window
anywhere in the part read". Add this repro as a case so that removing the clause is pinned, not merely survivable.

### R1-F4 — Low — no case cuts inside a multi-byte character, and `errors="replace"` is unpinned

`scripts/check-usage-pace.py:603-638` (`_read_tail`'s decode).

**Scenario.** The brief's multi-byte cut is handled by construction: the byte-level drop of the first line comes
before the decode. I verified it for every cut offset. But no case exercises it. The mutant
`decode("utf-8", errors="replace")` → `decode("utf-8")` survives the suite. With that mutant, one invalid byte
anywhere in the 4 MiB tail raises `UnicodeDecodeError`, and `_bounded` turns it into "could not be read". The
line would then be NOT RUN for every hook until the log rotated past the bad byte.

**Fix.** Add a case with a non-ASCII row, cut one byte inside its multi-byte character, and assert the line still
reads. Add a case with a stray `\xff` in a later row, and assert that row is skipped while the line still reads.

### R1-F5 — Low — at the bound, every hook parses ~28k rows (0.27 s), outside any deadline

`scripts/check-usage-pace.py:324` (`pace_line`'s loop over the whole tail).

**Scenario.** I measured this on a 6 MiB synthetic log in the real row shape. `read_meter` took 0.018 s and
returned 4,194,288 bytes, cut. `pace_line` over that text took **0.272 s**. That cost is paid on every prompt,
every spawn and every wake, and `READ_DEADLINE_S` does not bound it; it bounds only the read.

Before this PR the same cost applied right up to the bound and then stopped, because the read was refused. Now it
is paid permanently. This is not a correctness defect.

**Fix (optional).** Walk the tail's lines newest first and stop at the first row of this window at or before
midnight, or at the first earlier-window row. That is the same answer under the append-order bound already stated.
Alternatively, read a smaller tail first and widen it only on `TAIL_MISSES_MIDNIGHT`.

## Summary

R1-F1 is a CI gate that goes red on this head and green on its base, so the branch cannot merge as is. R1-F2 is a
surviving mutant on the path whose failure drops the stop. Both are cheap to fix, and one deadline case covers
part of each. R1-F3 to R1-F5 are Low.

VERDICT: NOT CONVERGED
