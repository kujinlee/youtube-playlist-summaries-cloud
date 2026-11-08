Reviewed head: e23240e9c558a8ba96119abdbfea8e4d2e8af177

# suite-cost-b, round 4: Claude adversarial review (Codex fallback)

> **Why Claude.** This round would have been the Codex half. The Codex run was stopped for low system memory,
> so a fresh Claude subagent ran it with an adversarial mandate. It reviews `git diff origin/master...HEAD`,
> weighted on `e23240e9` (the r3 fold and the Phase 6 redesign in
> `docs/reviews/architecture-review-2026-11-08-sweep-deadline.md`). Nothing under `.claude/plans/` was read.

**Summary.** No BLOCKER on this head. The real `ci.yml` passes `sweep_limit_pin`. js-yaml and Ruby Psych both
resolve the alias to the job's own expression text. `ci_deadline` refuses every non-integer value. Every one of
the 7 mutation entries I spot-checked dies by the harness's rule. But **the claim that the job's kill and the
budget are "one node by construction" rests on the pin, and the pin's comment stripper can hide a second
`&sweep-limit`.** A ci.yml edit that redefines the anchor between the job's limit and the alias passes the pin, and
both parsers then give the step a different value (R4-F1). The same stripper, together with two key spellings the
pin does not know, lets a step-level `timeout-minutes` through (R4-F2). Both need an edit no editor would make by
accident, so under §0 Q4c they are FILED, not BLOCKING. I set out the reasoning under R4-F1 so the coordinator can
overrule it.

## What was run (MEASURED, this head, 2026-11-08)

| Check | Result |
|---|---|
| `python3 scripts/check-plan-code.py --self-test` | `418/418 passed`, rc 0, 24.9 s |
| `python3 scripts/check-merge-ready.py --self-test` | `348/348 self-test cases passed`, rc 0 |
| `python3 scripts/gates-for-pr.py --self-test` | `37/37 cases passed`, rc 0 (this includes its "live ci.yml … prints its mutation-sweep job" case) |
| `sweep_limit_pin(real ci.yml)` | `[]` |
| js-yaml (`node_modules/js-yaml`) and Ruby Psych on the real ci.yml | job `timeout-minutes` and step `SWEEP_TIMEOUT_MINUTES` are both `"${{ github.event_name == 'schedule' && 60 || 30 }}"`; no step-level limit |
| 7 mutation entries, harness rule (below) | 7/7 rc 1, each `expect` named exactly once |

## Findings

### R4-F1 — Medium — a second `&sweep-limit` inside a quoted `#` passes the pin, and the alias then binds to it

- **Where:** `scripts/check-plan-code.py:1359`, `every = [re.sub(r"(?:^|\s)#.*", "", ln) for ln in lines]`. The
  anchor-count check at `:1364` (`once = whole.count(f"&{LIMIT_ANCHOR}") == 1`) and the alias count both read
  `whole`, which is built from these stripped lines. The stripper treats any whitespace-`#` as a comment, **including
  one inside a quoted scalar**, so it drops the rest of that line.
- **Input:** the real ci.yml with one line added to the sweep job's `Install dependencies` step (that step sits
  between the job's `timeout-minutes: &sweep-limit` at `ci.yml:1064` and the alias at `ci.yml:1282`):
  ```yaml
        env: {NOTE: "see #558", LIMIT: &sweep-limit 60}
  ```
- **Result:**
  - `sweep_limit_pin(...)` returns `[]` (a pass).
  - js-yaml 3.14.2 reads the job's `timeout-minutes` as `"${{ … && 60 || 30 }}"` and the step's
    `SWEEP_TIMEOUT_MINUTES` as `60`.
  - Ruby Psych reads the same: job is the expression, alias is `60`.
  - On a pull request the job is killed at 30 min. `ci_deadline` accepts `60` and gives a budget of 3,480 s, which
    runs past the kill with no stop report. That is the stop condition's first BLOCKER shape, a budget that is not
    the job's limit and is not refused.
- **Why this is not graded BLOCKER:**
  - (a) This head's ci.yml has no such line. I measured that no CI run of THIS head gets a wrong budget.
  - (b) The edit has to define an anchor with this exact name a second time, and hide it behind a quoted `#` on the
    same line. A plain redefinition is caught by the count, and the pin's own fixture covers that case (one
    defined BEFORE the job, `:2865`).
  - (c) The arch review puts "a workflow other than ci.yml that writes a FALSE literal" out of scope, and this is
    the same deliberate falsification made inside ci.yml.
  - **The coordinator may disagree:** the arch review's §3 says the pin "does not carry the run-time guarantee: the
    equality comes from the single node". That sentence is false as written. Which node the alias binds to is
    decided by anchor uniqueness, and only the pin enforces it.
- **Also notable:** the existing fixture for a redefined anchor places it where it is HARMLESS (before the job, so
  the job's own anchor still comes last). It goes red only because of the count. It does not exercise the order
  that matters, a redefinition between the anchor and the alias.
- **Fix direction (a hypothesis):**
  - Count `&sweep-limit` and `*sweep-limit` over the RAW text, not the stripped text, with a comment allowance that
    only skips lines whose first non-space character is `#`. That fails closed: a comment naming the anchor
    mid-line would red.
  - Or refuse any job-body line holding `#` inside a flow collection.

### R4-F2 — Low — step-level `timeout-minutes` spellings the pin does not count

- **Where:** `scripts/check-plan-code.py:1367`,
  `limits = sum(len(re.findall(r"(?:^|[\s{,])[\"']?timeout-minutes[\"']?\s*:", ln)) for ln in code)`. It runs over
  the comment-stripped `code`.
- **Inputs:** each one is the real ci.yml with one sweep-job step changed. Each result is the pin's output, then
  what js-yaml and Psych both read.
  - **B, an explicit (complex) key:**
    ```yaml
            ? timeout-minutes
            : 1
    ```
    The pin returns `[]`. Both parsers read the step's `timeout-minutes` as `1`.
  - **C, an escaped double-quoted key:** `"timeout\x2dminutes": 1`. The pin returns `[]`. Both parsers read
    `timeout-minutes` as `1`.
  - **D, a flow step whose quoted name holds a `#`:**
    `- {name: "Install #deps", timeout-minutes: 1, run: npm ci}`. The pin returns `[]`. Both parsers read
    `timeout-minutes` as `1`. The stripper from R4-F1 cuts the line at ` #deps`. This is the least contrived of the
    three, because the pin's own flow-mapping fixture differs from it only by the `#`.
- **Result:** the §5 row "a step-level limit below L — ENFORCED absent (`sweep_limit_pin`)" does not hold for these
  spellings. On the `--mutate` step, such a limit kills the step before the budget's stop report.
- **Grade:** Low. Each spelling is one no one writes by accident. B and C are YAML corners. The arch review's §6
  says an unknown shape "reds the PR that introduces it", and these pass instead, so that sentence overstates the
  pin. Whether GitHub's loader accepts B and C is NOT VERIFIED (no network).
- **Fix direction:** the same raw-text rule as R4-F1. Refuse any job-body line containing `timeout`, case-folded
  and outside a whole-line comment, other than the anchored one. Also refuse `? ` keys and `\x`/`\u` escapes in the
  job. That keeps the pin failing toward red.

## The four questions

**1. Can a CI run get a budget that is not its job's evaluated limit without being refused?** On this head, no.
- `main` (`check-plan-code.py:7227-7238`) computes a budget whenever `CI=true` and refuses with rc 2 on any reason.
- `ci_deadline` (`:1286-1323`) refuses an empty, unexpanded, expression, float, padded, zero, leading-zero or
  five-digit value. The self-test covers each, and I read the regex `[1-9][0-9]{0,3}`.
- The value is the same YAML node as the job's limit in both parsers I could run.

Under a hostile or contrived edit to ci.yml, yes: R4-F1. One further route is NOT MEASURED. The pin does not
forbid another writer of `SWEEP_TIMEOUT_MINUTES`, such as an earlier step's `echo SWEEP_TIMEOUT_MINUTES=60 >>
"$GITHUB_ENV"`, while it does require `SWEEP_JOB_START=` once in the file. Whether a step's own `env:` outranks
`$GITHUB_ENV` on the runner I did not verify; I believe it does, so I file nothing. Adding
`whole.count(f"{LIMIT_VAR}") == 1` would settle it without needing to know.

**2. Can `sweep_limit_pin` pass a workflow where the alias and the limit differ, or where a second limit exists?**
Yes to both, by R4-F1 (alias differs) and R4-F2 (second limit). Both depend on the comment stripper or on key
spellings outside its regex. The ten fixtures cover the plain spellings, and each fails as it should.

**3. Mutation spot-check, by the harness's rule.** For each entry: `stage_tree` into a fresh copy, apply `edits`
(each anchor present exactly once), run `--self-test` without `CI`, and require rc 1 with each `expect` named
exactly once by `parse_fail_names`.

| Entry (prefix) | rc | expect named once | other cases also red |
|---|---|---|---|
| arch 11-08: an anchor defined a second time | 1 | yes | none |
| arch 11-08: a QUOTED or literal value | 1 | yes | none |
| R3-F1: the pin counts a timeout-minutes only at a line's start | 1 | yes | none |
| arch 11-08: the pin reads comments as code | 1 | yes | "each broken clause" also red |
| arch 11-08: a job limit with padding, a leading zero, zero or five digits | 1 | yes | none |
| arch 11-08: the runner's limit is ignored | 1 | yes | main()'s budget case also red |
| r1 F1 (re-bound): a missing job limit is GUESSED as 30 minutes | 1 | yes | main()'s refusal case also red |

7/7 killed and attributed. The extra red cases add coverage and do not break attribution.

**4. Other readers of `ci.yml`.**
- `check-merge-ready.py`: its `ACCOUNTED_MENTIONS` key follows the anchored line, and its self-test (which reads
  the live ci.yml) passes, 348/348.
- `gates-for-pr.py` derives only the `verify` job's one-line steps and lists `mutation-sweep` as another job. Its
  live-ci.yml case passes, 37/37.

Neither parses the alias, and neither is affected.

## Still pending, unchanged from the arch review

The first CI run on this head must show every shard's `TIME BUDGET — 1680s … (SWEEP_TIMEOUT_MINUTES=30, event
'pull_request')`. Until then the alias's expansion by GitHub is ESTIMATED. It fails closed if it is wrong.

VERDICT: CONVERGED
