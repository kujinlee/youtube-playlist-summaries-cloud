<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head: 9860643393579d48c952b5e76b53a2616c47a982

**BLOCKER B1 — A final observation freezes evidence that absorb discarded.**

Locations: plan Task 7.3 `absorb_epoch`, lines 1502–1503; Task 7.2 `final_runs` and `settled`.

Concrete failing input:

1. The active ledger holds PR #600, push h1/b1, run 55, attempt 1, with a stable miss on `x.py`.
2. A legal attempt 2 adds a stable miss on `y.py`. Its report contains both misses.
3. GitHub’s repository-response `Date` is `2027-02-02T07:00:00Z`; run 55 was created `2027-01-01T10:00:00Z` and is completed at attempt 2. `final_runs` correctly records attempt 2.
4. Absorb retains the attempt-1 row because the existing row is already `miss`. It nevertheless absorbs the report’s identity and final observation. **The ledger never records the `y.py` miss.**
5. An owner reset archives that ledger verbatim. With run 55 absent from the capped listing, `settled` returns `True` using the attempt-2 observation against the attempt-1 row.

The new epoch never receives `y.py`; the absorbed report is skipped thereafter. This contradicts the promise that a reset clears exactly the evidence archived, and that evidence no archive holds latches.

**Executed result:** the guard accepts this absorb with `absorb_errors(...) == []`; `held_by_archive(..., row=attempt_2_row)` is `False`; after reset, `settled(...)` is `True`.

**Control:** removing the final observation makes `settled` false. Re-comparison then latches the `y.py` miss into the new epoch.

The repair must preserve additional miss evidence before recording an observation that permits omission. Replacing only non-miss rows is insufficient.

**BLOCKER B2 — The report listing has the same 1,000-run cap, but truncation can hide tightening evidence.**

Locations: plan’s shared `list_reports`, line 808; `runs_from_listing`, line 1094; `absorb_errors`, line 1524.

Concrete failing input:

- The filtered `shadow-compare.yml` listing has 1,001 runs within 120 days.
- BASE already absorbed the newest 1,000 runs and has fresh evidence satisfying the opening clauses.
- The omitted oldest run has an unabsorbed attempt containing a trusted miss—for example, a late rerun published after the newer runs were absorbed.
- GitHub returns ten pages containing 1,000 runs, with `total_count: 1001`.

`runs_from_listing` discards `total_count`. The specified fetch loop skips the 1,000 absorbed identities and returns no reports. The guard accepts the unchanged ledger, and gate clause 9 sees no unabsorbed miss. Pagination does not recover results beyond the endpoint’s cap.

This differs from backlog #595: truncating the **CI listing** forces re-comparison; truncating the **report listing** silently omits the evidence that should close the switch.

**Executed result:** the extracted parser and guard, with a small model of the prose-only fetch/skip loop, return `listed == []` and `absorb_errors(...) == []`.

**Control:** supplying the omitted run returns its miss report; the guard refuses its omission, and absorb latches it.

The listing must prove completeness or refuse; partitioning the creation window is another possible repair.

Task 7.2/7.3 blocks were extracted unchanged into `$TMPDIR` and executed under `python3 -I`: **25 assertions passed**, including both failing constructions and controls. [Reproduction script](/var/folders/tg/tmf6bl6s2n95zxh08fqgwv6w0000gn/T/plan586-r8-sn70h05c/repro.py).

The clock controls held: malformed headers, excessive runner skew, the exact +31-day boundary, and in-progress runs do not establish finality. The rebuild rejected inserted, removed, and altered observations. Explicit partial-call failures are specified to publish nothing; B2 is successful-but-incomplete input.

No additional MAJOR/MINOR findings. Repository files were unchanged; no GitHub calls were made.

VERDICT: NOT CONVERGED
