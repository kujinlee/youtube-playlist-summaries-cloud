# quiet-observers — round 3, Codex half

REVIEW GAP: claude — rounds 2+ ALTERNATE by design; the Claude half ran as round 2, and
this round's subject is that round's FIXES

<!-- codex-review: model=gpt-5.5 -->

Subject: `843bada6` on `quiet-stop-observers-wt`.

**Method.** I read `git show 843bada6`, `git log master..HEAD`, round 2’s Claude review, and round 1’s Codex review. I ran the three fast self-tests in place. For state probes, I imported the scripts and redirected `ROOT`, `SENTINEL`, `PLAN_DIR`, and `STATE` into `tempfile.TemporaryDirectory()`; no repo files under `scripts/` were modified. For the parent comparison, I materialized `0997292d:scripts/begin-plan.py` into a temp directory only.

## Findings

| # | Severity | Finding |
|---|---|---|
| 1 | Medium | An orphan `paused_unticked:` with no `paused:` becomes the baseline for the next real pause, producing a false “work resumed while paused” warning |

### 1 — Orphan `paused_unticked:` becomes a false baseline

A sentinel with `paused_unticked:` but no `paused:` is not paused to the guard. After `--pause`, round 2’s new “keep first baseline” logic preserves that orphan stamp and attaches it to the new pause. That can make the guard fire on work that did not happen.

Current `843bada6` probe:

```sh
python3 - <<'PY'
# temp root; plan has 2 unticked steps
# sentinel before pause:
# plan: .claude/plans/p.md
# armed: now
# paused_unticked: 9
# then cmd_pause("first real pause after stray stamp")
PY
```

Real output:

```text
before_decide= (2, "⛔ DO NOT STOP — 2 of 2 steps are unticked in `.claude/plans/p.md`....
pause_rc= 0
plan: .claude/plans/p.md
armed: now
paused: first real pause after stray stamp
paused_unticked: 9
after_decide= 3 ⏸ PAUSED, BUT 7 STEP(S) WERE TICKED SINCE — the guard has been stood down while the work carried on (backlog #99). None
```

No steps were ticked. The stale `9` was not a pause baseline because there was no `paused:` line. `parse_sentinel` agreed before the pause: the guard treated the sentinel as unpaused and blocked normally.

Parent comparison, same staged input using `0997292d:scripts/begin-plan.py`:

```text
old_begin_plan_from=0997292d
before_decide= 2 ⛔ DO NOT STOP — 2 of 2 steps are unticked in `.claude/plans/p.md`. 2
pause_rc= 0
plan: .claude/plans/p.md
armed: now
paused_unticked: 9
paused: first real pause after stray stamp
paused_unticked: 2
after_decide= 0 <empty> None
```

So this is introduced by the round 2 fix. The fix correctly avoids re-baselining an already-paused plan, but it keys on `paused_unticked` alone. It should only preserve the prior stamp when the prior sentinel is actually paused, or otherwise treat the orphan stamp as stale and recompute/strip it.

## Attacked, and found sound

Fast controls are green:

```text
python3 scripts/check-ci-watched.py --self-test
32/32 self-test cases passed

python3 scripts/check-plan-progress.py --self-test
43/43 self-test cases passed

python3 scripts/begin-plan.py --self-test
58/58 self-test cases passed
```

Normal lifecycle held:

```text
pause1_rc= 0
after_pause1= {'plan': '.claude/plans/p.md', 'armed': 'now', 'paused': 'waiting A', 'paused_unticked': '2'}
resume_rc= 0
after_resume= {'plan': '.claude/plans/p.md', 'armed': 'now'}
pause2_rc= 0
after_pause2= {'plan': '.claude/plans/p.md', 'armed': 'now', 'paused': 'waiting B', 'paused_unticked': '1'}
finish_rc= 0
sentinel_exists_after_finish= False
```

`strip_field` and `parse_sentinel` agree on the pause fields I tried, including doubled fields and colonless `paused`; the new pause path leaves exactly one pair on a normal re-pause:

```text
after_repause_text=
plan: .claude/plans/p.md
armed: now
paused: new reason
paused_unticked: 2
after_double_strip= 'plan: .claude/plans/p.md\narmed: now\n'
```

The CI no-PR wiring reached the intended branch once I isolated the git/gh probes:

```text
no_pr raw= (None, True) run_decide= 0
other_failure raw= (None, False) run_decide= 2
success_pending raw= ('[{"name":"x","state":"PENDING"}]', False) run_decide= 1
```

**VERDICT: NOT CONVERGED**

