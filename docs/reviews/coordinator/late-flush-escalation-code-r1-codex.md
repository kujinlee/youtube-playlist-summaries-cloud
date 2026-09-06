# Code review r1 — late-flush escalation (backlog #97) — Codex half

Dispatched via `scripts/codex-review.py` on branch `backlog-97-late-flush`.
Model fell through `gpt-5.6-sol`/`-terra`/`-luna` (HTTP 400) to **gpt-5.5**.
⚠ The wrapper's intrusion warning names `r1-run.log` — the coordinator's own stdout
redirect, created before the run. Adjudicated as NOT an agent write (backlog #92 shape).

<!-- codex-review: model=gpt-5.5 -->

Medium — `scripts/check-banner-armed.py:1392`

Concrete failure: F11’s self-test proves only that one observation line was added, not that the observation record contains the promised `before`/`after` counts. A trivial formatter that destroys the evidence still passes.

Quoted code:

```python
return (rc,
        len(_flushtext().splitlines()) - before_obs,
        len(_logtext().splitlines()) - before_warn)
```

The asserted cases consume only line deltas:

```python
_flush_scenario("fl-text", "text") == (QUIET, 1, 0)
```

But the required evidence format is implemented separately at `scripts/check-banner-armed.py:485`:

```python
return f"{when}\t{session or '-'}\t{before}\t{after}\n"
```

Verified by mutating a temp copy only:

```text
tmp=$(mktemp -d); cp -R scripts/. "$tmp/scripts/"
# changed flush_line to: return "constant-observation\n"
python3 "$tmp/scripts/check-banner-armed.py" --self-test
```

Output:

```text
94/94 self-test cases passed
rc=0
```

That means F11 is no longer vacuous on “was an observation emitted”, but it is still vacuous on “did the observation record preserve the measured counts”.

Requested checks run:

```text
python3 scripts/check-banner-armed.py --self-test
96/96 self-test cases passed

python3 scripts/check-selftest-counts.py
self-test counts: 14 script(s) declare a count, every one verified by running it

python3 scripts/check-ratchet-contract.py
summary: 22 violation(s), baseline 0
  (of which 22 are R4 manifest debt, baseline 22)
at baseline — not growing.

python3 scripts/check-guard-coverage.py --self-test
16/16 passed

python3 scripts/check-plan-code.py --mutate "$temp_root"
OK — delivered scripts mutated: 8 file(s), 186 mutation(s), 0 survivor(s)
```

Verdict: NOT CONVERGED.

---

## The other half

**REVIEW GAP: claude — the Agent tool is disabled for this session, so no independent Claude
reviewer could be dispatched.**

⚠ **This is recorded as a GAP rather than filed as a Claude half, deliberately.** The author did
self-review, and it found one thing (below) — but a review written by the change's author is not an
independent half, and filing it under `docs/reviews/claude/` would let a decaying severity curve
from one-and-a-half reviewers read as convergence. That is the recorded *dual review halves are not
redundant* shape: Codex-only rounds once cleared a money guard that the skipped Claude half caught
in a single pass.

**What the author's self-review found, kept here because the work is real even though the
independence is not:** the branch ADDED an error path — `_log_flush` failing maps to CANNOT RUN —
and asserted nothing about it, while the sibling journal-write failure has had falsifier F7 since
round 1. The asymmetry was the tell. It matters more than it looks: `block-idle-stop.sh:29` allows
a QUIET stop **silently**, so "the instrument could not record" is invisible unless the exit code
carries it. Closed by case **F97c** (unwritable observation log -> CANNOT RUN, never silence),
which is a control/treatment pair against F11a — the identical `"text"` scenario returns QUIET when
the log is writable.

Self-test 97 -> 98.
