<!-- codex-review: model=gpt-6.1-sol -->

Found three issues:

- **Low — stale severity documentation:** `docs/explainers/2026-10-23-topic-decision-ladder.fragment.html:320` still places trigger 4 in the FAIL loop; line 367 labels it FAIL. The published `.html` repeats these at lines 420 and 467. Neither explains the suspension, so readers receive incorrect current behavior.

- **Low — the tests do not protect “NOT a pass”:** `scripts/check-decision-scheme.py:2993` checks for the backlog reference, but not the suspension wording or “NOT a pass.” I removed only `; NOT a pass` in an isolated in-memory copy: **274/274 still passed**. The whole-suffix mutation catches deletion of the reference, but leaves this explicitly claimed requirement unprotected.

- **Low — misleading plain-language measurement:** `docs/dashboard-entries.md:17490–17491` says “The last 5 pieces it tracked also took 4.” Executed historical data gives **[4,7,4,5,4]**: their **median** was 4. State that explicitly.

Executed evidence:

- `python3 scripts/check-decision-scheme.py --self-test`: **274/274 passed**.
- Live CLI: **exit 0**, warnings 6/8/10/11; trigger 4 silent.
- Read logs directly from `origin/master` and `65e9263a`: confirmed **4 qualifying subjects / empty window** versus **[4,7,4,5,4]**.
- Executed historical `main()` with `65e9263a`’s script, baseline and log: **exit 1, FAIL trigger 4**.
- Applied each new manifest mutation independently in memory: each produced **272/274**, failing exactly the two named median-4/9 cases. No ambient masking observed.
- Manifest contains **128 entries**. I did **not** independently rerun the full 128-mutation sweep.

Other checks: grep found no severity dependency in `check-goal-status.py` or the goals generator. Trigger 9 depends on the shared window and median, so its exclusion remains valid; trigger 4 still reports deferral composition. The summary line does not report a pass.

Restoration is **manual**: nothing reads #327’s status or expires the suspension. It can remain indefinitely. The comment instructs restoration, but the backlog/dashboard should explicitly describe it as a required manual follow-up. Split/defer counting can favor fewer rounds by terminating tracked work while residual work continues; the measured window supports no stronger causal conclusion.

VERDICT: NOT CONVERGED
