<!-- codex-review: model=gpt-5.5 -->

**REVIEW GAP:** claude — not invoked for this round, by design. Rounds 2+ alternate
(`docs/review-method.md`, Round topology), and the Claude half authored round 3 — the round
whose repair this reviews.

VERDICT: NOT CONVERGED — 0 Blocking, 1 High.

The repair is very close. The generic key rule converges the line-visible scalar space, and the refusal predicate itself is quiet on this repo’s workflows. The remaining High is ordering: `verdict()` can report `rc 1` “pins differ” before it reaches the new unreadable-scalar `rc 2`.

| round-3 finding | status | evidence |
|---|---:|---|
| B1 quoted-key class not closed | FIXED | 7,200/7,200 generated valid YAML fixtures agree with Psych; quoted escaped/doubled cases covered. |
| B2 explicit-key silently dropped | PARTIAL | `unreadable_scalar_openers()` sees `: |`, docs mention it, but `verdict()` does not always turn it into `rc 2`. See High. |
| H1 remaining valid spellings false-green | FIXED | Generated differential: `FALSE_GREEN 0`, `MISS 0`, `DISAGREE 0`. |
| M1 inverted causal story survives in `CONTEXT.md` | FIXED | Live prose now says the earlier “correct about a step” story was false; remaining hits are historical review docs. |
| M2 stale backlog counts | FIXED | Suite `99`, manifest `46`, declared sum `875`. |
| M3 dashboard says class closed | FIXED | No live dashboard/backlog stale “all four are closed now” copy found outside historical r3 review. |
| L1 backlog says optional `(?:-\s+)?` | NOT FIXED | `docs/backlog.md:182` still says `_BLOCK_SCALAR` accepts an optional `(?:-\s+)?`, but the live rule is `(?:-\s+)*` plus the generic key rule. |
| L2 stale `86/86` code comment | FIXED | The code now says no count quoted because `86/86` went stale. |

**New Findings**

High — unreadable scalar refusal is preempted by the disagreeing-pins failure.

Command run:

```text
python3 - <<'PY'
# builds three explicit-key fixtures and calls declared_pins,
# unreadable_scalar_openers, and verdict()
PY
```

Real output:

```text
--- one real pin + explicit scalar same fake pin
declared_pins ['3.12', '3.12']
unreadable ['        : |']
rc 2
CANNOT RUN — a line opens a block scalar in a shape this scan cannot read:
--- one real pin + explicit scalar different fake pin
declared_pins ['3.12', '9.9']
unreadable ['        : |']
rc 1
FAILED — workflows pin DIFFERENT Python versions: 3.12, 9.9.
--- no real pin + explicit scalar fake pin
declared_pins ['9.9']
unreadable ['        : |']
rc 2
CANNOT RUN — a line opens a block scalar in a shape this scan cannot read:
```

So the new refusal exists, but `verdict()` asks `len(pins) > 1` before `unreadable_scalar_openers`. An unreadable scalar body that merely mentions a different `python-version` is still read as structure long enough to produce the wrong failure. It is fail-closed, not a false green, but it violates the stated repair: “verdict turns any into rc 2 CANNOT RUN.”

**Standing Question**

Not settled. The line-visible scalar matcher has converged: my generated-space differential over 7,200 valid YAML fixtures returned:

```text
cases 7200 valid 7200 invalid 0
AGREE 7200 FALSE_GREEN 0 MISS 0 REFUSED 0 DISAGREE 0
disagreement_rate_valid 0.0
```

But convergence also required “every unclassifiable shape refuses.” The explicit-key shape is identified by `unreadable_scalar_openers()`, yet `verdict()` can return `rc 1` first. What remains is ordering the unreadable-scalar refusal before any decision that trusts `declared_pins()`.

**Checked Sound**

`python3 scripts/check-python-pin.py --self-test`:

```text
99/99 passed
```

Counts:

```text
manifest 46
EXPECTED_MUTATIONS check-python-pin 46
mutation manifests 52
declared sum 875
```

`python3 scripts/check-plan-code.py --mutate .`:

```text
OK — delivered scripts mutated: 52 file(s), 875 mutation(s), 875 killed, 875 attributed to the case each names, 0 survivor(s)
```

Workflow quietness:

```text
workflow files 2
structural lines 282 loose 5 strict 5 refusals 0
```

Duplicate anchor pair is pre-existing:

```text
HEAD entries 46
duplicate old edit anchors 1
  [42, 45] '        if (opens_steps and len(opens_steps.group(1)) == job_steps_indent\n                and not job_key[idx]):'
master entries 39
duplicate old edit anchors 1
  [35, 38] '        if (opens_steps and len(opens_steps.group(1)) == job_steps_indent\n                and not job_key[idx]):'
```

I also attacked the requested over-fire probes: quoted `: |`, one-line `run:` pipes, URLs, matrix values, `if:` expressions, shell redirects, and full-line comments. No valid workflow-shaped false refusal found. The loose matcher is a superset of the strict matcher over the sampled strict space: `strict_not_loose 0`.
