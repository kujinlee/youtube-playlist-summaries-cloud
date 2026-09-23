# banner-unheralded — round 2, Codex half (the FIXES)

Subject: `26aa25c7` on `banner-work-without-banner` — the round-1 fold.
Model: gpt-5.5 via `scripts/codex-review.py`. Verdict: `docs/reviews/verdicts/banner-unheralded-r2-codex.verdict.json`.

REVIEW GAP: claude — rounds 2+ ALTERNATE by design; the Claude half runs as round 3, scoped to whether its own round-1 findings are closed

⚠ That is a DESIGN alternation, not a reviewer that could not run — `docs/plugins.md`: *"a
concurrent pair never reviews the FIXES"*. Round 1 ran both halves concurrently, which is why
round 2 is one half.

⭐ **Calibration note, recorded because it is the difference between this round and the last.**
This reviewer returned CONVERGED with zero findings in round 1 over a diff carrying four
single-edit mutations that left the suite green. The round-2 brief told it so. This pass
applied each intended edit and named which case goes red — the verification whose ABSENCE was
round 1's H1. The verdict is the same word; the evidence behind it is not.

<!-- codex-review: model=gpt-5.5 -->

No findings.

**Review Result**
Blocking: none  
High: none  
Medium: none  
Low: none  

M2 looks correct to me. The new `if armed or paused:` at [scripts/check-banner-armed.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-banner-armed.py:598) matches the sibling guard’s pause semantics: `check-plan-progress.py` stands down while still speaking loudly for malformed paused states at [scripts/check-plan-progress.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-progress.py:173), [scripts/check-plan-progress.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-progress.py:182), and [scripts/check-plan-progress.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-progress.py:203). A real `--pause` also cannot create “paused but no sentinel”; `begin-plan.py` refuses that at [scripts/begin-plan.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/begin-plan.py:398).

Commands run:

```bash
python3 scripts/check-banner-armed.py --self-test
```

Relevant output:

```text
140/140 self-test cases passed
```

Focused banner mutation run, using the repo’s own mutation harness in a temp-staged tree with only `check-banner-armed.json` present:

```text
RESULT ok= True
VERDICT Measured
declared 27
mutations_recorded 27
survivors []
attributed 27
```

The new cases are falsifiable by the intended single edits:

```text
W11/W12 hoist: rc 1; W11 and W12 fail
H2a/H2b reread: rc 1; H2a and H2b fail
P10 prefix: rc 1; P10 fails
P11 withdraw: rc 1; P11 fails
P12 invert: rc 1; P12 fails
W-INT hardcode detail: rc 1; W-INT log/count case fails
```

M2 edge probes:

```text
paused_missing_plan seed_rc= 0 judge_rc= 0 log= ''
paused_zero_steps seed_rc= 0 judge_rc= 0 log= ''
unreadable_sentinel seed_rc= 2 judge_rc= 2 log= ''
```

So paused malformed/zero-checkbox states are not banner-warned, but the progress guard is the loud integrity channel. An actually unreadable sentinel does not get silenced by `paused`; banner returns CANNOT RUN.

`_drive_changing` does not introduce an ordering dependency that I could find. It clears the journal before each leg, snapshots the log before each assertion, and unlinks the sentinel after H2b at [scripts/check-banner-armed.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-banner-armed.py:1938). There are no later redirected-temp cases depending on its leftover journal state.

L1: definite split answer. Yes, a hand-seeded existing journal can reach `sample_for`’s previous-slot branch through `run_decide`:

```text
hand_seed_prev_paused rc= 0 log_exists= False
```

But from a clean journal using normal `run_decide` state transitions, the judged turns I drove only consumed current samples:

```text
normal stop 1 rc= 0
normal stop 2 rc= 1
normal stop 3 rc= 0
normal continuation rc= 0
sample_slots= [('t1', 'current'), ('t2', 'current')]
```

That supports the round-1 suspicion in the ordinary end-to-end path: `prev_paused` is reachable via externally supplied/preexisting journal state, but I do not see a clean run-generated path where it matters before `last_judged_uuid` or non-judgability makes it irrelevant.

VERDICT: CONVERGED
