<!-- codex-review: model=gpt-6.1-sol -->

1. **Medium — Replacement coverage bypasses the child’s timeout adapter.** `scripts/compaction-state.py:1847`, production boundary at **:836**. **Fix-induced: yes**, through the retained skip.

   Two NEW mutants at line 836 independently refute the claim:

   ```python
   # Mutant A: shorten gh’s actual timeout
   ss._run(c, w, min(timeout, 1) if c[0] == "gh" else timeout, own_group=False)

   # Mutant B: shorten git’s actual timeout
   ss._run(c, w, min(timeout, 0.1) if c[0] == "git" else timeout, own_group=False)
   ```

   Concrete input: real CR1’s slow git followed by hung gh.

   | Mutant | Marker set | Marker unset |
   |---|---|---|
   | A: child gh capped at 1 s | **106/106 survives** | **107/108 killed** |
   | B: child git capped at 0.1 s | **106/106 survives** | **107/108 killed** |

   Both fail the real CR1 timeout assertion. The recording case injects its runner directly into `snapshot()`, bypassing `_child`’s adapter. The event case kills before these shortened calls finish.

   The coverage table at **:916–924** names existing cases, but its completeness claim is false: residue includes actual child timeout plumbing, beyond bash and `__main__`. Add every-mode coverage through that adapter.

2. **Medium — CI guard mistakes matrix data for an executable step.** `scripts/compaction-state.py:964–975`. **Fix-induced: yes**; the replacement parser retains a false green.

   Concrete input:

   ```yaml
   jobs:
     verify:
       runs-on: ubuntu-latest
       strategy:
         matrix:
           include:
             - name: compaction-state self-test
               run: python3 scripts/compaction-state.py --self-test
       steps:
         - run: echo no self-test
   ```

   `ci_runs_real_time()` returns **`None`**, approving this workflow. GitHub executes only `echo`; the apparent self-test is unused matrix data. The parser searches anywhere inside `verify` and treats a suitably indented list item as a step without requiring membership in `steps:`.

   Against the real workflow, the parser passes. Adding `if: ${{ true }}` is rejected as documented. A multiline `run: |` containing the command is also rejected, conservatively.

All four required suites ran in the foreground:

| Suite | Marker unset | Marker set |
|---|---:|---:|
| compaction-state | 108/108 | 106/106 |
| check-plan-code | 249/249 | 249/249 |

Other NEW mutants ran both ways: zero stdin wait, reversed publish-margin arithmetic, and snapshot gh capped at 3 seconds were killed in both modes. SIGTERM replacing SIGKILL, omitted timeout reap, `GIT_TIMEOUT=1`, and child git capped at 1 second survived both; they do not independently refute the claim.

The exact fd-0 case passed 30 repetitions normally and 20 with four CPU workers: **0.101–0.111 s**, leaving about **0.89 s** below its assertion. No observed descriptor leak; fd 0 was restored. Forcing a 60-second read wait returned after **3.007 s** through the writer-close safeguard, without an observed leak.

`child_env` stripped an inherited marker; `mutation_env` restored it; the caller’s environment retained it. Both rebound entries have exactly one matching anchor. The six-second sleep and AST restriction are present. No marker leak was demonstrated.

**NOT CONVERGED**
