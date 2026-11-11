<!-- codex-review: model=gpt-6.1-sol -->

**Low — A later budget refusal hides an earlier failing control.** [scripts/check-plan-code.py:2512](scripts/check-plan-code.py:2512) includes failed controls in `control_seconds`; line 2515 then discards the accumulated failure report. Round 1’s control-order fix remains incomplete for multiple targets.

Executed reproduction: invoked `main()` locally with the default 600-second budget and two `--only` targets, substituting suite results and clock readings:

- `check-merge-ready.py`: exit 1, `[FAIL] broken control`, 100 seconds.
- `check-plan-code.py`: exit 0, `1/1 passed`, 0.01 seconds.
- Actual result: exit **2**, empty stdout, only **“REFUSED LOCALLY … 28.4 min”**, naming the **failed** target as costliest. The control-failure diagnostic disappeared.

Preserve control failures ahead of budget refusals, and exclude failed controls from the budget estimate. Add a two-target regression case.

Other executed evidence at HEAD `cbe00ddd`:

- `check-plan-code.py --self-test`: **237/237 passed**.
- `CI=true … check-main-drivable.py --self-test`: **438/438 passed, 52.58 seconds**, confirming the timeout fix.
- All **131** entries’ edit anchors bind exactly once.
- All **18 changed entries**—14 new plus four rebound—executed in memory over a green 237-case control; each exited 1 and failed every exact case it names.
- Real CI-mode `--only scripts/check-merge-ready.py`: **16/16 killed and attributed**, verdict explicitly labeled **DIAGNOSTIC**.
- Real unscoped local invocation: **exit 2**, budget refusal before mutations.
- Whole-manifest checks precede filtering. Documentation broadly matches; the dashboard’s “full 128-entry run” remains stale against 131.

VERDICT: NOT CONVERGED
