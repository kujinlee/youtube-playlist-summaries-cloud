# Codex adversarial review — review-identity-176, round 1

**Subject:** the FOLD — `bd784721` (round 1's fold of its Claude half: 1 Blocking, 1 High, 5 Medium,
2 Low, plus one pre-existing gate failure). Mandate: refute, not confirm.

**Verdict: NOT CONVERGED — 0 Blocking, 1 High, 1 Medium, 1 Low.**

⚠ **DISPATCHED AS `r2-codex` AND RENAMED TO `r1-codex` BEFORE COMMIT — a label I chose wrongly, not
rewritten testimony.** A ROUND is one pass with BOTH halves over one subject; this repo's pattern is
*Claude half → fold → Codex half reviews the fold*, both carrying the round's number (PR #342 r3, r4
and r5 all ran that way). Naming this one r2 left round 1 with a single half and round 2 with the
other, and `check-review-rounds` refused the branch in CI for exactly that. The file was untracked
at the time, and the verdict's `review` join key was corrected with it — a rename that moved the
file and not the field would have broken the join this very slice exists to fix.

⚠ **Captured from the final message — Codex writes no file** (`docs/plugins.md` output contract).
⭐ The wrapper FILED this half itself at `docs/reviews/codex/` and wrote its testimony to a clean
`<review-id>.verdict.json` — **backlog #176 working end to end on its first live dispatch**, with no
derivation from `--out` and no hand promotion.

---

<!-- codex-review: model=gpt-5.5 -->

Subject: `review-identity-176` HEAD `bd784721f11fbc3ec8993788ae9115299e355524` tree `319775264f61d3b043e0e511beb5a44d625ae9ae`; base `origin/master` `b2e10e39c8676daa341486d6f1167c53d06c110b` tree `b98862f1c36aa11ec6abd56740038198ca259828`.

**Verdict: NOT CONVERGED** with 0 Blocking · 1 High · 1 Medium · 1 Low.

What I verified GREEN:

```
$ git rev-parse HEAD && git rev-parse origin/master
bd784721f11fbc3ec8993788ae9115299e355524
b2e10e39c8676daa341486d6f1167c53d06c110b

$ python3 scripts/codex-review.py --self-test
155/155 passed

$ python3 scripts/check-review-rounds.py --self-test
43/43 self-test cases passed

$ python3 scripts/check-plan-code.py --self-test
131/131 passed

$ python3 scripts/check-anchors.py
anchors: 13 registered, all claimed; every spec/plan dated >= 2026-08-25 declares one; floor 22 held

$ python3 scripts/check-docs.py
Documentation integrity OK

$ PGCONTAINER=m4_schema_gates M4_PHASE=post python3 scripts/check-guard-coverage.py
✅ every BLOB-ADDRESSING SCHEMA guard classified; every SEQUENCE guard reconciles and is mutation-covered

$ PGCONTAINER=m4_schema_gates M4_PHASE=post python3 scripts/check-vocabulary-collisions.py
✅ no unjustified duplicate mechanism

$ PGCONTAINER=m4_schema_gates M4_PHASE=post ./scripts/check-schema-gates.sh
✅ all schema gates green
```

I also verified the live verdict corpus supports the era caveat:

```
$ python3 - <<'PY'
...
PY
total 184
schemas {2: 99, 1: 85}
refused-values {('NoneType', 'None'): 184}
truthy-refused 0
weird []
```

And `check-review-rounds.py` prints the caveat before the current red round:

```
$ python3 scripts/check-review-rounds.py
  ⚠ verdict corpus: 184 read — 0 meaningfully checked below, 184 PRE-CUTOVER (...), 0 refusal record(s) (...)
FAILED — 1 review round(s) with one half and no stated reason:
  ✗ review-identity-176 round 1: only claude — codex neither ran nor recorded a `REVIEW GAP:` line
```

Findings:

**High — `refused` is truthy, not boolean, so a current-schema non-refusal can bypass both join directions**

Premise: the consumer treats any truthy `refused` value as authoritative.

`scripts/check-review-rounds.py:231-235`:
```python
    for src, rec in records:
        if rec.get("refused"):
            continue
        if (rec.get("schema") or 0) < TRUSTED_SCHEMA:
            continue
```

`scripts/check-review-rounds.py:270-273`:
```python
        if not isinstance(rec, dict) or "gate_ran" not in rec:
            bad.append(f"{p.name}: no `gate_ran` field — cannot tell whether the gate ran")
            continue
        records.append((p.name, rec))
```

Measurement:

```
$ python3 - <<'PY'
...
PY
problems with refused="false" string: []
era split: {'total': 1, 'refused': 1, 'pre_cutover': 0, 'checked': 0}
reverse problems with refused="false" string: []
reverse era split: {'total': 1, 'refused': 1, 'pre_cutover': 0, 'checked': 0}
```

A schema-3 record with `gate_ran:false`, filed review present, and `"refused": "false"` is silently skipped. The mirror case, `gate_ran:true` naming a missing review, is also silently skipped. That answers the prompt’s attack directly: a non-refusal can carry a truthy malformed `refused` and suppress the check.

Why High: this is the load-bearing field added to prevent B1’s read-side false accusation, and malformed current-era testimony now defeats the same CI join in both directions without being reported as unreadable.

Proposed fix: require `rec.get("refused") is True` for the refusal skip, and make any non-bool present `refused` in schema >= 3 a bad verdict / CANNOT RUN. Structural, not transitional.

**Medium — the linked rationale still documents the old 0/1/2 exit-code contract**

Premise: `docs/plugins.md` now correctly teaches `rc=3`, but it points readers to rationale that still says the wrapper “now enforces” only 0/1/2.

`docs/plugins.md:180`:
```markdown
> review, and **#68(d) — CLOSED 2026-09-01**: each run writes `docs/reviews/verdicts/<review-id>.verdict.json` stating `gate_ran`, read **in CI** by `check-review-rounds.py`, never by the caller who loses it. [`process-rationale.md`](process-rationale.md) → *The review gate that wrote over its own evidence*.
```

`docs/process-rationale.md:408-411`:
```markdown
**Exit codes, and what the wrapper now enforces.** `scripts/codex-review.py` returns **0** (a real
review was captured and written), **1** (no candidate produced one — the gate did NOT run, fall back
to a Claude adversarial review and record the gap), or **2** (REFUSED before contacting any model,
because `--out` already exists — pass `--allow-overwrite` to mean it).
```

But the actual code is now four-way.

`scripts/codex-review.py:71-79`:
```python
Exit codes:  0 = a real review was written and promoted
             1 = no candidate produced one (the gate did NOT run) — fall back to a Claude half
             2 = CANNOT RUN / REFUSED — nothing was measured, nothing was written
             3 = THE GATE RAN AND THE REVIEW IS NOT FILED — a real review exists at `--out` and
```

Why Medium: the loaded rule in `docs/plugins.md` is correct, so this is not the primary instruction path. But the linked rationale is explicitly where a reader goes when questioning the rule, and it still states the old partition that caused M4.

Proposed fix: update `The review gate that wrote over its own evidence` to include rc=3 or point that paragraph forward to `The testimony that named a scratch file`. Transitional docs fix.

**Low — accepted review ids include nonportable / expensive-to-discover filenames**

Premise: `is_single_segment()` only rejects empty, slash/backslash, `.` and `..`.

`scripts/codex-review.py:322-326`:
```python
    if not review_id:
        return False
    if "/" in review_id or "\\" in review_id:
        return False
    return review_id not in (".", "..")
```

Measurement:

```
'/abs-r1-codex' single= False who= None refused= True
'x-r1-codex/' single= False who= None refused= True
'x%2Fy-r1-codex' single= True who= codex refused= False
' x-r1-codex' single= True who= codex refused= False
'C:-r1-codex' single= True who= codex refused= False
'C:foo-r1-codex' single= True who= codex refused= False
'CON-r1-codex' single= True who= codex refused= False
'aaaa...(300 a's)...-r1-codex' single= True who= codex refused= False
```

Why Low: on this POSIX tree these still join under `docs/reviews/<writer>/`; I did not prove traversal. But a very long id can burn a model run before promotion fails, and Windows-reserved / colon-bearing names are not portable despite the function’s cross-platform separator comment.

Proposed fix: bound `review_id` to a portable filename grammar and length after `parse_review_name` succeeds, e.g. visible non-whitespace ASCII excluding `<>:"|?*` and reserved DOS basenames. Structural input validation.

What I could NOT measure:

I did not run `python3 scripts/check-plan-code.py --mutate .`; the prompt forbade it. Therefore the commit-message claim `1011/1011 killed` / declared `1012` is not independently verified by me.

I accidentally probed `python3 scripts/check-schema-gates.py`; it does not exist and returned rc=2. The real gate is `./scripts/check-schema-gates.sh`, and that passed as shown above.
