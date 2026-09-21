<!-- CLAUDE half of review round 3 — branch `budget-slack-warning`, subject `git diff a5837b84..e23bd63a` (the ACCOUNTED_MENTIONS ratchet and its widening to `github.event_name`). Written 2026-09-20. -->

# `check-merge-ready.py` — round 3, Claude half

**Verdict: NOT safe to merge**, on one Medium. The widening itself is correct and every reason in
the allow-list is true; what is wrong is the *file scope* the ratchet runs over, which reproduces
r1's Medium ("the FILE SCOPE was the hand-written part") one level down — in the glob pattern
instead of the filename.

## Gates run (rc captured before any pipe)

| Command | rc |
|---|---|
| `check-merge-ready.py --self-test` | 0 — 51/51 |
| `check-docs.py` | 0 |
| `check-docs.py --self-test` | 0 — 22/22 |
| `check-plan-code.py --self-test` | 0 — 128/128 |
| `check-ratchet-contract.py` | 0 — 38 guards |
| `check-selftest-counts.py` | 0 — 43 scripts |
| `check-fixture-variation.py` | 0 — 575 params / 55 files |

`--mutate .` deliberately NOT run (781 mutations; controller verified 11/11 attributed).

---

## 🟠 Medium — the ratchet scans `*.yml`, but GitHub Actions also runs `*.yaml`

`scripts/check-merge-ready.py:412` and `:427` (and the self-test's own corpus case at `:636`) all
iterate `WORKFLOW_DIR.glob("*.yml")`. GitHub's own documentation: a workflow file "must have either
a `.yml` or a `.yaml` file extension." Both are live.

So a file `.github/workflows/release.yaml` containing

```yaml
      - name: gate
        if: github.event_name == 'pull_request'
        run: python3 scripts/some-new-pr-only-gate.py
```

is invisible to *all three* mechanisms: `pr_only_steps()` never reads it, `job_level_gates()` never
reads it, and `unaccounted_mentions()` never reads it — so no stray, no `CANNOT RUN`, and the
script prints `READY — every gate CI will run has been run here, including the PR-only ones`.

Measured: `list(WORKFLOW_DIR.glob("*.yaml")) == []` today, so this is not a live miss.

**Why it is worse than the residual risk the commit already admits.** The stated bound is about the
*form of the condition* — "a gate keyed on something other than `github.event_name` … would escape
both." This escapes with the **most ordinary spelling there is**, the exact equality both the parser
and the scan were built to catch. It is outside the bound the comment states, and it is squarely
inside the claim the ratchet's own header makes at `:199`: *"EVERY `pull_request` MENTION IN EVERY
WORKFLOW."* That header is false as written, and it is new in this diff.

It is also the likeliest arrival path for a new PR-only gate. A new gate added to an existing
workflow is caught; a new gate added in a *new* workflow is the case the ratchet exists for, and a
new workflow is exactly where the extension is a coin flip.

Fix is one character in three places: `glob("*.yml")` → `glob("*.y*ml")` (or union the two globs),
plus a self-test case whose fixture file is named `.yaml`.

## 🔵 Low — an allow-list reason's truth depends on the `on:` block, which is not part of the key

`ACCOUNTED_MENTIONS[("schema-gates.yml", "if: github.event_name != 'schedule'")]` reasons:
*"true on a pull request AND on a push, so it is not pull-request-only."* That is **true today** —
verified against `schema-gates.yml:on:` = `pull_request`, `push`, `schedule`, `workflow_dispatch`
(the reason omits that it is also true on `workflow_dispatch`, which does not change the verdict).

But the key is the `if:` line alone. Delete or narrow the `push:` trigger and that same line becomes
a PR-only(+dispatch) gate on a job that runs `scripts/check-schema-gates.sh`, while the key is
unchanged, the allowance is unchanged, `PR_ONLY_COND` still does not match it, and `job_level_gates`
still will not name it. Nothing refuses; `READY` is printed.

This is the r3 Codex finding's own class surviving one layer in: the fix made the *line* accounted,
but PR-only-ness by exclusion is a property of (line × trigger set), and only the line is keyed.
Low because it needs a trigger deletion, which is rare and conspicuous. Worth one sentence in the
bound paragraph rather than a mechanism.

---

## What I attacked and found CLEAN

### 1. Escape forms (probed against the live functions, not reasoned about)

| Form | Genuinely PR-only? | parser | scan | In the stated bound? |
|---|---|---|---|---|
| `startsWith(github.ref, 'refs/pull/')` | yes | — | — | ✅ named explicitly |
| `github.head_ref != ''` | yes (unset on `push`) | — | — | ✅ "something other than `github.event_name`" |
| `github.base_ref == 'master'` | yes (unset on `push`) | — | — | ✅ same |
| `github.event.number` | yes | — | — | ✅ same |
| `github.ref != 'refs/heads/master'` | yes, given `push: branches:[master]` | — | — | ✅ same |
| `github.event.pull_request != null` | yes | — | **CAUGHT** | n/a |
| `contains(github.event_name, 'pull')` | yes | — | **CAUGHT** | n/a |
| a `uses:` composite action carrying its own gate | possible | — | — | ✅ named explicitly |

The four unnamed escapes (`head_ref`, `base_ref`, `event.number`, `github.ref` inequality) all fall
inside the general class the sentence states — it states a class with examples, not an enumeration —
so the bound is **honest, not incomplete**. The `.yaml` case above is the one that falls outside it.

### 2. The measured claim "neither workflow contains any such form today" — TRUE

Every `github.ref` / `head_ref` / `base_ref` / `github.event.` occurrence across both workflows:
`ci.yml:22` and `schema-gates.yml:172` are concurrency keys (not conditions); `ci.yml:419,444` are
`BODY:` env (allow-listed); `ci.yml:435` and `schema-gates.yml:92,167` are `#` comments. Every
`uses:` in both files is a first-party GitHub JS action (`actions/checkout@v4`,
`actions/setup-node@v4`, `actions/setup-python@v5`) — no `uses: ./`, no composite action. The
complete non-comment `if:` inventory is six lines: `ci.yml:417,442` (the two PR-only steps),
`schema-gates.yml:183,229` (allow-listed), `schema-gates.yml:221,283` (`always()`).

### 3. The four new allow-list reasons — all TRUE

- `group: schema-gates-…${{ github.event_name }}…` — a concurrency **key**. It selects a group; it
  cannot skip a job. Correct, and `schema-gates.yml:167` documents why the field is in the key.
- `if: github.event_name != 'schedule'` (job `schema-gates`, `:183`) — true on `pull_request`,
  `push` *and* `workflow_dispatch`; not PR-only. See the Low above for the standing caveat.
- `if: github.event_name == 'schedule' || … == 'workflow_dispatch'` (job `prod-drift`, `:229`) —
  the inverse; never runs on a PR. Correct.
- `schema-gates.yml: pull_request:` (1, trigger) — correct; that file has no PR-only step or job.

The pre-existing three re-verified too: `ci.yml: pull_request:` is the trigger; the two
`if: github.event_name == 'pull_request'` lines are `ci.yml:417` (`dashboard entry ratchet` →
`check-dashboard-entry.py`) and `:442` (`check-review-recorded (PR only)`), which are exactly the
two gates `main()` invokes; the two `BODY:` lines are their env. Counts match exactly — the live
scan returns `[]` for both files, so no allowance carries unused slack.

### 4. False `CANNOT RUN` from the widening — none today, and the direction is right

Probed: `run: echo ${{ github.event_name }}`, `- name: report github.event_name` and an `env:` value
all produce a stray, i.e. a refusal. Neither workflow contains any such line today, so the widening
bought no false refusal. The cost is one allow-list line per future mention, which is the
over-approximation the design argues for and cannot be called a defect without arguing against the
design. Worth knowing: the common `if: github.event_name == 'push'` deploy idiom will refuse on
first sight — correct but surprising, and the block message already says what to do.

### 5. The comment-skip rule — no gate can hide behind it

`s.startswith("#")` only skips lines whose *stripped* form begins with `#`. A YAML comment cannot be
a condition, and inside a `run: |` body a `#` line is inert shell. Probed: a `run: |` block whose
shell comment reads `# gate on github.event_name == 'pull_request'` is skipped, correctly — it gates
nothing. The false-refusal direction is reachable (non-comment shell prose mentioning
`github.event_name` refuses) but is the same over-approximation as (4). `pr_only_steps()` is
independently immune: `re.match(r"\s*-?\s*if:")` cannot match a `#`-prefixed line, asserted at
`:547`.

### 6. The re-anchored mutations and the collateral edits

Both re-anchored entries in `scripts/mutations/check-merge-ready.json` now name a *live* property
(the key-indent restriction; the folded-scalar follow) rather than a deleted line shape, and the two
new ones bracket the widening from both sides — one narrowing the scan back to `pull_request` only,
one removing the comment skip. `EXPECTED_MUTATIONS` 8→11 and the declared sum 778→781 are consistent
and the ratchet rose. `check-docs.py`'s `budget_verdict` correction checks out by hand:
`budget_warn_slack(1) = min(max(FLOOR,0), max(1,0)) = 1`, so remaining `1 <= 1` is `tight`, and
budget 2 gives slack 1 with remaining 2 → `ok`. 2 is indeed the smallest budget with an `ok`, and
`260 → 18` is right (`round(260*0.07)=18`, `260//3=86`).
