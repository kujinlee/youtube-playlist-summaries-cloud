# Plan review — goal work threads — round 3 — coordinator adjudication

Adjudicates `docs/reviews/codex/plan-goal-work-threads-r3-codex.md` and
`docs/reviews/claude/plan-goal-work-threads-r3-claude.md`. Subject: plan v2 at `2958b820`,
remediated through `aa40fb0d`. **Both halves ran.** Both returned NOT-CONVERGED.

⭐ **BOTH HALVES INDEPENDENTLY FOUND THE SAME BLOCKING, AND SO DID THE COORDINATOR — BY THREE
DIFFERENT ROUTES.** Codex found it by reading; the Claude half found it by transcribing the plan's
code and running the suite (`KeyError: 'rel'` at `2958b820`, then `63/65` at `aa40fb0d`); the
coordinator found it by extracting the plan's code blocks into a module and executing every case
(39 run, 2 failed). Three routes, one defect. That is the strongest signal this gate has produced.

---

## The Blocking, and why it took two fixes

**Round 2** wrote a case *"a document record with no rel does not crash the renderer"* and the fix
*"`.get` throughout"*. It changed the two membership sites and left the two **render** sites at
`esc(d["rel"])`. The fixture therefore raised `KeyError` on the **spec** branch before reaching the
extra-document branch it existed to exercise.

**Round 3's first fix** changed those renders to `.get`, and created a second defect:

```python
named = {d.get("rel") for d in (t.get("spec"), t.get("plan")) if d}
```

With no `rel`, `.get` returns `None` — so **every rel-less document keys to the same `None`**, the
extra document matched the spec, and it was silently dropped. The case written to prove extras render
now proved the opposite. Measured, not reasoned: `extra document rendered: False`.

**The fix that holds uses no key at all.** `pair_documents` appends the *same dict object* it assigns
to the slot, so identity is exact:

```python
named = [x for x in (t.get("spec"), t.get("plan")) if x]
for d in t.get("docs", []):
    if not any(d is x for x in named):
```

Verified by execution: extra rendered `True`, named `True`, spec not duplicated `True`.

⚠ **Three attempts at one two-line fix, each narrower than the class.** `d["rel"]` → crash;
`d.get("rel")` → collision; identity → correct. The same arc as `DOC_PATH`'s three rounds.

## Other findings — all confirmed, all remediated

| id | sev | source | disposition |
|---|---|---|---|
| — | High | codex | `thread_prs` iterated only `("spec","plan")`, so a collision's third document never got a history and vanished from fan-out. **FIXED** — iterates the thread's whole `docs` |
| — | High | codex | anchored `DOC_PATH` missed `worker/CONTEXT.md`. **FIXED** — `(.*/)?<basename>$`, 0 wrong over 19 paths |
| H1 | High | claude | The plan's verification expected `>no plan<` = **35**; the built page gives **21**, with 14 `>no spec<`. 21+14 is the 35 unpaired. **FIXED** — both arms checked. ⚠ Checking one arm and calling it the pairing rate is a half-measurement passing for a whole one |
| M2 | Med | claude | `"only the three measured tags can be rendered"` rendered **two** of the three; mutation-verified that renaming the `unknown` branch stayed GREEN. **FIXED** — a `code: None` PR added to the fixture, expected list now three |
| — | Low | claude | A rel-less document is skipped in `thread_prs` without setting `pr_error` — a second place where a missing `rel` means "quietly nothing". **DOCUMENTED**, unreachable in production |

## Measured against the real repo — the Claude half's Q2

| | measured | plan said | |
|---|---|---|---|
| build time | **9.7s** (2.4s baseline) | ~10s, ≈4.5× | ✓ |
| threads | 41 | 41 | ✓ |
| threads with both halves | 6 | 6 | ✓ |
| `>no plan<` | **21** | 35 | ✗ → H1 |
| `pr_fanout["147"]` | **22** | 22 | ✓ |
| tags rendered | 72 code / 22 docs-only / 0 unknown | >0 / ≥1 | ✓ |
| case chain | 15→25→35→39→47→62→65 | same | ✓ |

⚠ **`pr_error` and the extra-document branch are exercised by ZERO real records.** Both exist only
under fixtures — and the extra-document branch is the one that was broken through two rounds. A
branch no live data reaches is a branch only its tests defend, which is exactly why the tests for it
have to be right.

## Cleared

`hist_cache` is populated before `pr_fanout` reads it (both halves, independently). `re` is in scope
in `self_test`. `_r` stays function-local. The four chained `and` calls do not mask a single failure
— Codex's list-of-results rewrite closed it anyway. The count chain is correct at both commits.

## Verdict

**NOT-CONVERGED** on findings, **but see the escalation below.** Every finding is remediated and
every fix is verified by executing the plan's own code — 39 cases run by the coordinator, 0 failing.

⛔ **ESCALATED TO THE HUMAN: run round 4, or stop reviewing and build?** Three rounds have produced
4 Blocking / 8 High and a genuinely better design, and **every round's Blocking has been the previous
round's fix**. `docs/dev-process.md` names this exact case: *"on a document, rounds can be right
forever because prose has nothing to execute; that is a signal to go build, not to convene Phase 6."*
Every defect found lives in code that does not exist yet. Once written it has a 65-case suite, a
mutation manifest and a browser pass — instruments strictly stronger than another prose round, and
the two halves that mattered this round only found what they found by *executing* it.
