Reviewed head: 8b602d55b5059f972fb057eb141ecb12b09b4197

# spawn-line-500 — round 1, Claude half (adversarial)

Subject: `git diff origin/master...HEAD` on branch `spawn-line-500` (backlog #500, draft PR #500).
Files: `scripts/check-usage-pace.py`, `scripts/mutations/check-usage-pace.json`, `scripts/check-plan-code.py`,
`.claude/hooks/usage-pace-{spawn,wake}.sh`, `docs/{backlog,dashboard-entries,goal-threads}.md`.

Mandate: refute. Everything below was EXECUTED unless it is labelled UNVERIFIED.

## What I ran

- `python3 scripts/check-usage-pace.py --self-test` → `291/291 self-test cases passed` (10.9 s wall).
- The 11 new `#500:` mutations, each applied to a `git archive HEAD` copy in a temp dir, the self-test run,
  and the named `expect` cases checked for `[FAIL] <name>:` → **all 11 KILLED by their named cases.**
- 7 reviewer mutations of my own in the same temp copy (results in the findings).
- Hostile meter content through `pace_line()` and `evaluate()` (in-process, TZ fixed to PST8PDT).
- `local_midnight()` brute-forced every 10 min over 2025-2026 in 9 zones with DST or midnight
  transitions (America/Los_Angeles, Havana, Santiago, Asuncion, Sao_Paulo; Asia/Beirut, Tehran;
  Africa/Cairo; Australia/Lord_Howe) → 0 instants where midnight > now or now − midnight > 25 h.
- `main()` against a FIFO meter, a 4.2 MB meter (over the bound) and a 3.8 MB valid meter.
- The live checker, read-only (`python3 scripts/check-usage-pace.py`, no `--hook`): `WARN … weekly usage is
  89% (… at 95.2% new spawns and agent wake-ups are refused) … The stop is today's pace line (95.2%)`.
  The live meter (`~/.claude/meter/log.jsonl`, 46,829 bytes, 318 rows since 10-31) holds a single
  `resets_at` (1793959200) across every row, so the exact-equality window filter matches in practice.

## What held (refutation attempts that failed)

1. **The stop.** `refuse_at` = `max(90, min(97, line))`; `line` is either None or finite because every operand
   passes `is_number` and `days > 0` (`resets > now >= midnight`, the DST brute force above). No meter content
   I constructed put the stop below 90 or above 97. `≥ 97` is always refused without an override (the cap
   case at 97 REFUSES; `p=150` row three days out → stop 97.0).
   An unreadable line → 90 and says so: FIFO meter → `REFUSE … at 90% … Today's pace line cannot be read
   (the meter log is missing or unreadable), so the stop is the 90% floor.` in 0.08 s; the 4.2 MB meter →
   the same text.
2. **Hostile rows.** `true`, `NaN`, `10**400` (→ inf), a 100,000-deep `[[[…]]]`, a string `at`, a list row, a
   string row, `seven_day: null`, `rate_limits: [1]`, NUL bytes, a `resets_at` off by 0.5 s, a duplicate `at`
   key of 1e300 → each skipped; with no other row each gives `(None, "the meter log has no reading of this
   week's window")` and `evaluate(cache(91))` REFUSES. No exception escaped. `RecursionError` is mapped to
   `ValueError` inside `parse_json` (line 236), which `pace_line` catches.
3. **Bounded read.** The meter goes through `read_regular` (line 694), the same daemon-thread reader with the
   1 s deadline as the cache, with its own 4 MiB bound.
4. **Test isolation.** `HOME` is replaced at line 755 before the first case and restored in `finally`; the
   in-process `main()`/`drive()` cases, the FIFO and slow-read children (`subprocess.run` with no `env`, so
   they inherit the fake `HOME`) and the run-hook cases (`hook_env` sets `HOME=<tmp>/home`) all resolve the
   default meter under a temp directory. By inspection no case reads the owner's `~/.claude`. (But see C2: the
   redirect has no falsifier.)
5. **Old mutations after 95 → 98.5.** In the meter-less paths (`ev()` passes `meter=False`; `drive()` and the
   run-hook cases see an empty fake `HOME`) the stop is 90 whatever the value, so a 95 and a 98.5 case
   distinguish the same mutants. The two old anchors that were rewritten (`weekly >= stop`,
   `REFUSED (at {pct(stop)})`) still name cases that use the 90 stop (`weekly 90 is REFUSE-SPAWN`). I did not
   re-run the 102 old mutations myself; CI's `mutation-sweep` shards for this head were PENDING when I wrote
   this (UNVERIFIED here).

## Findings

### C1 — MAJOR — the production wiring of the meter has no falsifier: the default path can break with the suite green

`scripts/check-usage-pace.py:167` (`METER_LOG`) and `:694` (`os.path.expanduser(args.meter)`).

Every case that reads a meter passes it explicitly: `evm(…, m)` in-process, and `main(["--cache", cp,
"--meter", mp, …])` at lines 846-848. The hooks never pass `--meter`, so in production the line comes from the
DEFAULT, and no case exercises the default. Executed in a temp copy:

| mutation | self-test |
|---|---|
| `METER_LOG = …"log.jsonl"` → `…"log.json"` | **rc 0, 0 fails** |
| `read_regular(os.path.expanduser(args.meter), …)` → `read_regular(args.meter, …)` | **rc 0, 0 fails** |

Either mutant makes the live guard read no meter, so the stop is the 90 floor forever: exactly the behaviour
backlog #500 replaces, and the owner would see it only as the generic "cannot be read" note at WARN or above.
It fails safe (toward the stricter stop), which is why this is MAJOR and not a BLOCKER, but the feature can be
dead in production while 291/291 is green. The run-hook cases already build a fake `HOME`
(`<tmp>/home/.claude/`); writing a `meter/log.jsonl` there with rows matching the cache's `resets_at` (the
fixture uses `t + 86400` with `t = time.time()`, so the row must carry the same float) and asserting the
spawn hook ALLOWS a weekly value between 90 and the line would kill both mutants through the shipped hook.

### C2 — MINOR — the HOME redirect itself is unfalsified

`scripts/check-usage-pace.py:755`. Replacing `os.environ["HOME"] = fake_home` with `pass` → **rc 0, 0 fails**
(executed). The property it guards ("no case reads the live meter") is real today only because the live
meter's `resets_at` never equals the fixtures' synthetic ones; a fixture that ever used a real-looking
reset, or a live log with a matching row, would flip a verdict silently. A case that asserts
`os.path.expanduser(METER_LOG)` starts with the suite's temp directory (or that `main()` with no `--meter`
reports the line as missing even when the owner's file exists) would pin it.

### C3 — MINOR — a meter row's `used_percentage` is not range-checked the way the cache's is

`scripts/check-usage-pace.py:283`. The cache's `window()` refuses a negative `used_percentage`; `pace_line`
accepts any finite number. Executed: a single row of this window at `NOW-60` with `used_percentage: 150`,
reset 3 days out → `pace_line` = `(97.0, '')`, and `evaluate(cache(91))` = **WARN** (stop 97), where a
readable sane row gives 92.5 and an unreadable one 90. A row of `-1000` → line `-450.0`, and the note reads
"Today's pace line is -450%"; on the last day the same row → 97.0. Mutating the check away
(`is_number(at) and is_number(r)`, dropping `is_number(p)`) → **rc 0, 0 fails**, so even the finite check on
`p` has no case. Low likelihood (the statusline writes the same values the cache has), but the fallback rule
"unreadable → 90" does not cover "readable nonsense → up to 97". Treat `p < 0` (and arguably `p > 100`) as an
unreadable row, and add a case with a bad `p`.

### C4 — MINOR — the meter read adds a THIRD deadline to the hook; the stated worst case and a timing case's margin are stale

`scripts/check-usage-pace.py:420` still says "With the cache read, the hook's worst case is two deadlines".
`main()` now reads the cache, then the meter, then (wake/prompt paths) stdin, each bounded by 1 s, so the worst
case is three. The meter is read unconditionally, including when the cache was unreadable (where the line
cannot matter) and on every OK prompt. Measured: the self-test's stalled-read child (line 1113, "EXITS within
the 1 s deadline + 1.5 s") now takes **2.05 / 2.05 / 2.06 s** over three runs (both reads stall), against a
2.5 s bound: the margin fell from ~1.5 s to ~0.45 s, which is a flake risk on a loaded CI runner, and the case
name no longer describes what it measures. Reading the meter only when `weekly >= WARN_AT` (after the cache
parses) would restore both the margin and the docstring, and take the parse off the common path (a 3.8 MB
valid meter took 0.35 s wall per run).

### C5 — MINOR — the meter's 4 MiB bound is reachable in normal use, and the reason is discarded

`scripts/check-usage-pace.py:168` and `:694` (`meter_text, _ = …`). The live log grows ~100 rows/day at
~147 bytes/row (318 rows, 46,829 bytes since 10-31), so it crosses 4 MiB in roughly 9 months (INFERRED
from that rate). From then on the line is permanently the 90 floor, and the message says only "missing or
unreadable", because `read_regular`'s reason ("over the … bound") is dropped. Nothing rotates the log. Lowering
the bound to 64 KiB → **rc 0, 0 fails** (executed), so the bound is unpinned too. Either read the tail of the
file (only today's and this window's rows matter) or carry the reason into the note.

### C6 — MINOR — docstring claims beyond the code

`pace_line`'s docstring says "the last day before the reset is 97". Executed: on the last day (reset 20 h
after midnight) a start of 110 → line 92.0, and of 200 → 20.0 (stop 90). The comment at the return says
"at days <= 1 the formula is >= 150 - start/2 >= 100", which holds only for `start <= 100`. Harmless while
weekly is above the start (the verdict refuses anyway), but the claim should state its precondition or C3's
range check should make it true.

## Stale text (item 5)

No remaining description of the stop as a fixed 90% or a fixed 97% in the diff's files: the module header
(line 20), the FAILS-IF line (129), both hook headers, the backlog row and the dashboard entry all say
max(90, line) capped at 97. The only stale text found is C4's "two deadlines" (line 420) and the line-1113 case
name.

## Summary

The rule is sound: I could not move the stop outside [90, 97], make it crash, hang or let ≥ 97 through, and the
11 new mutations are each killed by their named case. C1 blocks convergence: the production path the hooks
actually use (the default meter location) is unwitnessed, and two one-token mutants of it survive.

VERDICT: NOT CONVERGED
