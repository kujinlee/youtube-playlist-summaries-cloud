# quiet-stop-observers — round 1, Codex half

Subject: `84131ec0` on `quiet-stop-observers-wt`. Model: gpt-5.5 via `scripts/codex-review.py`.

REVIEW GAP: claude — round 1 ran one half; the Claude half follows as round 2 on the fixes

<!-- codex-review: model=gpt-5.5 -->

Medium, [scripts/check-plan-progress.py](/Users/kujinlee/code/agentic-ai-docs/yps-quiet-observers/scripts/check-plan-progress.py:266): `paused_unticked` stores only the outstanding count, so “same outstanding count” is treated as “nothing changed.” That misses a paused plan edited by hand where work did resume but the net count stayed flat, e.g. one old step was ticked and one new unticked step was added. Concrete input:

```text
sentinel:
plan: .claude/plans/p.md
armed: now
paused: waiting
paused_unticked: 2

plan:
- [x] old done
- [x] old ticked while paused
- [ ] old still open
- [ ] new work added while paused
```

Measured:

```sh
python3 - <<'PY'
import importlib.util
from pathlib import Path
root = Path.cwd()
spec = importlib.util.spec_from_file_location('pp', root / 'scripts/check-plan-progress.py')
pp = importlib.util.module_from_spec(spec); spec.loader.exec_module(pp)
sentinel = 'plan: .claude/plans/p.md\narmed: now\npaused: waiting\npaused_unticked: 2\n'
plan = '''### Task 1: A

- [x] old done
- [x] old ticked while paused
- [ ] old still open
- [ ] new work added while paused
'''
print(pp.count_steps(plan))
print(pp.decide(sentinel, plan, None, False))
PY
```

Output:

```text
(2, 4)
(0, '', None)
```

That is silent `ALLOW`, indistinguishable from a genuinely waiting pause. This is the dangerous #99 shape restored for hand-edited plans: the plan changed while paused, but the guard goes quiet because the net outstanding count did not fall. A similar stale-stamp case with more outstanding than pause time also goes quiet.

What I attacked and found sound:

- `--tick` still refuses a paused plan, preserves the plan bytes, names `--resume`, and repeats the pause reason.
- `--resume` clears both `paused:` and `paused_unticked:` on the normal route.
- `--finish` removes sentinel and state.
- A stamp without `paused:` does not stand the guard down; the paused branch is keyed by `paused`.
- Double `--pause` with a readable plan is last-key-wins and `--resume` strips all copies via `strip_field`.
- `gh` no-PR handling fails noisy on reword/empty/nonmatching stderr and only quiets the measured vendor sentence.
- `_skip_reason` still short-circuits before the network for default branch / detached / no upstream.
- Added mutation evidence is real: the relevant begin-plan mutations ran at 10-12, check-ci-watched at 82-83, check-plan-progress at 421-424 in the full delivered mutation run.

Verification run:

```sh
python3 scripts/check-ci-watched.py --self-test
# 28/28 self-test cases passed

python3 scripts/check-plan-progress.py --self-test
# 42/42 self-test cases passed

python3 scripts/begin-plan.py --self-test
# 53/53 self-test cases passed

python3 scripts/check-plan-code.py --mutate .
# OK — delivered scripts mutated: 52 file(s), 890 mutation(s), 890 killed, 890 attributed to the case each names, 0 survivor(s)
```

VERDICT: NOT CONVERGED
