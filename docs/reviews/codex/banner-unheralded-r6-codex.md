# banner-unheralded — round 6, Codex half

REVIEW GAP: claude — rounds 2+ ALTERNATE by design; the Claude half ran as round 5, and
this round's subject is that round's FOLD

<!-- codex-review: model=gpt-5.5 -->

Subject: `a8bd13af` on `banner-work-without-banner`.

**Method.** I reviewed `a8bd13af`, `02218390`, and `docs/reviews/claude/banner-unheralded-r5-claude.md`; ran the fast controls first; then attacked the fold’s specific claims with generated probes in temp copies. I did not modify `scripts/` and ran no mutating `git` command.

Control:

```text
$ python3 scripts/check-banner-armed.py --self-test
159/159 self-test cases passed

$ python3 scripts/check-fixture-variation.py
fixture variation OK — 618 parameter(s) examined across 57 file(s); 121 known-unvaried ratcheted, 7 exempt with a written reason
```

Mechanical delivered-code interpolation enumeration used AST over `scripts/check-banner-armed.py` before `_self_test`. It found the same contract-bearing population round 5 described: `unticked`, message `tool_uses`, banner `step/total`, `all N steps`, `log_line` columns, `flush_line` columns, late-flush counts, warning-log banner detail, warning-log tool count, and warning-log unticked detail. The non-contract/plumbing f-strings were session temp paths, import error text, journal/log error paths, and exception text.

Targeted manifest run, in a temp copy with redirected `$HOME`:

```text
control rc= 0 summary= 159/159 self-test cases passed
entries checked=47 all_attributed=True
all 47 anchors applied exactly once; each expect matched exactly one red case
```

I did not run `check-plan-code.py --mutate .`; I accept the recorded full sweep (`920 mutations, 920 killed, 920 attributed, 0 survivors`) as sufficient because the narrower question here was whether the 47 banner entries bind and attribute correctly after the fold. I did run the harness self-test:

```text
$ python3 scripts/check-plan-code.py --self-test | tail -n 5
128/128 passed
```

`pad` replay, in a temp copy, confirmed the helper changes only the intended late-flush sizes while preserving the warning class and banner:

```text
{"pad": 0, "rc2": 1, "first_sampled_text_len": 1, "prev_text_len_after_second": 1, "judged_text_count_before_second": 2, "highest_banner_before_second": [2, 3], "tool_count_before_second": 0, "flush_tail": "...	s0	1	2", "warn_tail": "...	s0	unarmed	STEP 2 of 3"}
{"pad": 2, "rc2": 1, "first_sampled_text_len": 3, "prev_text_len_after_second": 3, "judged_text_count_before_second": 6, "highest_banner_before_second": [2, 3], "tool_count_before_second": 0, "flush_tail": "...	s2	3	6", "warn_tail": "...	s2	unarmed	STEP 2 of 3"}
```

Fixture-variation ratchet claim held. Directly calling its analyser produced:

```text
examined keys containing log_line/flush_line:
flush_line.after
flush_line.before
flush_line.session
flush_line.when
log_line.detail
log_line.reason
log_line.session
log_line.when
findings containing log_line/flush_line:
check-banner-armed.py: `log_line(reason=…)` is passed the SAME value at every call site...
known for check-banner-armed: ('log_line.reason',)
```

The three deleted suppressions (`log_line.detail`, `log_line.session`, `log_line.when`) are paid off; `log_line.reason` remains pinned.

For the bytes branch of `_sentinel`, I enumerated call sites in HEAD and in `02218390`:

```text
HEAD sentinel calls= 4
  (1742, 'Name:before')
  (1745, 'Name:after')
  (2252, 'Name:before')
  (2255, 'Name:mid')
02218390 sentinel calls= 4
  (1689, 'Name:before')
  (1692, 'Name:after')
  (2125, 'Name:before')
  (2128, 'Name:mid')
```

The helper still has the same four call sites; existing `_UNTOUCHED`, `None`, and string states follow their prior branches. The new bytes value exists to make the judging stop unreadable for `R5-1111`. Its falsifier observation is concrete: dropping `and judged is None` must turn the named quiet scenario red, and the targeted manifest run confirmed that exact case is the one that fails.

## Findings

| # | Severity | Finding | Introduced by round 5's fold? |
|---|---|---|---|
| - | - | No new findings. | - |

## Attacked, and found sound

**VERDICT: CONVERGED**

