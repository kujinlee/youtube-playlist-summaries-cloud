<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

**B1 — The fold repairs two ambiguous anchors and orphans another.** `scripts/mutations/begin-plan.json:241` still targets:

```python
    body = _TOTAL_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}{n}{m.group(5)}", body)
```

The fold replaces that statement with the loop at `scripts/begin-plan.py:260–270` without updating the mutation.

Independent population derivation:

| Snapshot | Mutations | Edit anchors |
|---|---:|---:|
| `74a44551` | 1408 | 1416 |
| `1506073d` | 1413 | 1421 |
| `f0d58536` | 1417 | 1425 |

On the reviewed tree, **1424 anchors match once; one matches zero times**. The two original pause anchors are unique again.

Reproduced through `mutate_delivered` on a pruned copy containing both affected manifests, with green controls, under **both interpreters**:

> anchor NOT FOUND  
> NOT MEASURED — 43 of 44 declared mutations produced a verdict

The corresponding master control passes **35/35**. Thus the branch still breaks mutation coverage; the affected CI shard cannot produce a measured pass.

“Multiplied relative to master” is insufficient: this orphan has count **0 on master and 0 on the reviewed tree**, because its subject originated in the slice. Validate every current anchor’s existence, uniqueness, and intended binding, including entries added earlier on the branch.

## High

None additionally established.

## Medium

**M1 — Fence protection still rewrites literal examples.** `scripts/begin-plan.py:262` toggles a boolean on every line starting with three backticks. It neither recognizes tilde fences nor remembers delimiter length.

Measured after appending to a plan with one real checkbox:

- A `~~~` fenced example changes from `Step 1 of 9` to `Step 1 of 3`.
- Inside a four-backtick fence, an embedded three-backtick line incorrectly closes protection; the example again becomes `of 3`.
- An inline literal on a real checkbox line also changes: `real with literal **Step 8 of 9** — example` becomes `Step 8 of 2`.

The rewrite therefore still exceeds the claimed step-prefix scope. Track fence character and length, and restrict replacement to the checkbox’s leading step label.

**M2 — New CANNOT RUN text falsely says paused sessions cannot stop.** `scripts/check-plan-progress.py:419–430` unconditionally says **“REFUSES EVERY STOP”** for missing plans and zero-checkbox plans.

Both counterexamples reproduce:

| Broken plan | Paused | `decide` |
|---|---|---|
| Missing | Yes | `WARN` = 3 |
| Zero checkboxes | Yes | `WARN` = 3 |

The pause deliberately preserves a nonblocking escape. The new text instead tells the reader that ending the session requires repairing or deleting the sentinel. The added tests cover only unpaused failures and encode an overgeneralization. Make the consequence conditional on pause state.

**M3 — `PARKED_DONE` substitutes another unjustified completion claim.** At `scripts/check-plan-progress.py:441–449`, every fully ticked paused plan is described as waiting on unseen work.

With `paused: hand back to human` and every box ticked, the result says:

> Waiting on: hand back to human  
> if that has finished …  
> if it has not: leave the sentinel alone

A completed handoff is legitimate finished work. This is a new wrong answer: the old code asserted completion for every pause; the fold assumes every pause denotes unfinished external work.

Completion needs three possibilities: **finished, waiting, and unconfirmed**. With the current unrestricted reason field, use an unconfirmed verdict for ambiguous paused plans and repeat “Paused because,” rather than asserting external work exists. An explicit handoff state could distinguish finished handoffs reliably.

**M4 — `_auto_slug` still raises on valid prose titles under the CI interpreter.** `scripts/begin-plan.py:175` calls `Path.exists()` on an unbounded filename. A title of 300 ASCII letters raises **`OSError: File name too long` on Python 3.12.9**. Only `ValueError` from normalization is caught.

Python 3.14 returns that overlong slug instead, leaving the eventual write to fail. Bound generated filename length while retaining the complete title in plan content.

**M5 — The fold still lacks a regression test of `cmd_add`’s repaired create path.** The new cases exercise `_auto_slug`, rather than its connection to the verb.

On the controlled copy, replacing:

```python
return cmd_begin(_auto_slug(title), [step_arg])
```

with:

```python
return cmd_begin(normalise_slug(title), [step_arg])
```

restores both slash-title crashes and collision overwrites, yet **93/93 tests still pass** under Python 3.12.

This contradicts the fold’s claim that its new cases address the previously untested verb branches. Round-1 Claude M4 is not resolved by these helper tests. Add an isolated `cmd_add` case asserting actual creation and preservation of an existing plan.

**M6 — The wrapper’s failure reporting remains incomplete.** `.claude/hooks/report-plan-state.sh:30–37` merges stderr into stdout before checking emptiness and buffers unlimited output without a deadline.

Controlled probes:

| Reader | Wrapper result |
|---|---|
| Normal stdout | Correct pass-through |
| Whitespace only | CANNOT RUN |
| Exit 0, no output | CANNOT RUN |
| Exit 0, stderr-only `boom` | Exit 0, stdout `boom`; **no CANNOT RUN** |
| Sleeping reader | No output before intentional termination |
| Prints 10 MB | **No output after 35 seconds**, then intentionally terminated |

A stderr-only failure bypasses the empty-stdout safeguard, while a nonreturning reader never reaches the diagnostic. Preserve stdout separately and bound execution and capture.

## Low

**L1 — Backlog #284 proposes a safeguard that already exists.** `docs/backlog.md:276` and `docs/roadmap-to-launch.md:2324` recommend refusing when executed mutations differ from `len(shard_slice(...))`.

That check already operates through `declared = len(shard_muts)` and `Measured.__post_init__`. Directly constructing **605 results for 706 declared mutations** raises:

> 605 verdict(s) for 706 declared mutation(s) — a mutation that never ran cannot be counted as caught

The row needs evidence identifying which denominator or population changed, rather than proposing this existing check. Its 707/706 figures match the **slice’s 1413 entries**; the fold has **709/708**. Preserve the exact measured snapshot and invocation provenance.

## Checked and found SOUND

- **Five named mutations:** reproduced **5/5 named kills, zero survivors**, on both interpreters, with initial and restored green controls. Catching the slug exception does not weaken the named assertion: the raised mutation produces `None`, which fails the required nonempty-string check.
- **Anchor binding:** no anchor present on both master and the reviewed tree moved its first occurrence into another function in my function-owner comparison. The newly added comments quoting pause anchors do **not** match their complete newline-terminated anchors. No current ambiguous anchor was found.
- **Nonempty-message premise:** all six verdict labels—UNARMED, LIVE, PARKED, PARKED_DONE, STALE, NOT_RUN—return nonempty messages. Missing-plan and zero-checkbox variants remain nonempty with or without a pause.
- **Slug controls:** empty, punctuation-only and symbol-only titles receive dated names; an existing dated filename receives a suffix; 2000 collisions produce suffix `-2001`. An absent plan directory is created successfully. An armed plan receives an append rather than an automatic-name overwrite. A read-only directory permits name selection but actual creation raises `PermissionError`.
- **Fence boundaries:** ordinary three-backtick and tested indented-list fences preserve examples. An unterminated fence preserves existing fenced text, although the appended task consequently remains inside the open fence.
- **Known-open indices:** independently reproduced `1 of 4, 1 of 4, 2 of 4, 4 of 4`. This confirms the disclosed L4 limitation; it is not a new finding.
- **Declared counts:** begin-plan **93/93**, plan-progress **82/82**, plan-code **178/178**, on both Python versions. Manifest counts are **24** and **20**; declared mutation sum is **1417**.
- **Guard population:** the legacy `check-*.py` grep yields **48** commands. Broader discovery yields **53 runnable unique single-line Python commands**, excluding the Jest-results check. My runner asserted discovered equals completed: **53 discovered, 53 RAN, zero nonzero exits**, using Python 3.12. The absent-corpus memory-link result is excluded from substantive evidence.
- **Shard partition:** round-robin slices are disjoint and exhaust the loaded population. Current two-shard sizes are **709/708**, including both allegedly omitted target files. CI assigns shards separate jobs; staging also uses a per-run temporary directory. These support the qualified CI-isolation argument, not the alleged local narrowing.

## CANNOT RUN

These are verification failures; **treat this as NOT RUN**:

- The full 59-manifest mutation execution. The measured two-manifest refusal is affirmative evidence for B1, not a complete sweep.
- Backlog #284’s concurrent narrowing. I did not launch concurrent mutation shards. Its observed 605-result success remains independently unverified.
- The author’s exact historical rerun and its discovered-equals-RAN assertion: that runner was not available in the reviewed changes. My independent sweep establishes its own population only.
- Jest-results validation, PR-only gates, and the TypeScript/unit/integration/e2e suites.

## Instruments

Reviewed `f0d58536`, the fold message and diff, and both round-1 halves. Used **Python 3.14.4 and 3.12.9**. Every guard received closed stdin.

Mutations ran sequentially in isolated copies; the working-tree copy used `tar` excluding `.venv` and `node_modules`, with the dependency symlink restored. Controls preceded mutations. No Git command ran in the main checkout.

**No review file was written. Final tracked Git status was clean.**
