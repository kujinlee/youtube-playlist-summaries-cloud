# Plan review — goal work threads — round 1 — coordinator adjudication

Adjudicates `docs/reviews/codex/plan-goal-work-threads-r1-codex.md` and
`docs/reviews/claude/plan-goal-work-threads-r1-claude.md`. **This is not a third half.**

Subject: `docs/superpowers/plans/2026-09-11-goal-work-threads.md` at `6debfde6`.
Both halves returned **NOT-CONVERGED**. Both supplied a correct proof of subject.

---

## The one refutation

**Codex Blocking — REFUTED, by reading the file.** Codex claimed Task 5's `_broken` fixture omits
`"prs"`, so `render_threads` raises `KeyError` at `sum(1 for p in t["prs"] ...)`.

Plan `:513-514` reads:

```python
    _broken = [{"stem": "s", "spec": {"name": "s-design.md", "rel": "r"}, "plan": None,
                "docs": [], "prs": [], "pr_error": True}]
```

The key is present. No `KeyError`. Recorded rather than dropped, because a refuted Blocking that
vanishes silently is indistinguishable from one that was quietly accepted.

⚠ **Codex's Blocking was wrong and its Highs were right.** Severity from one reviewer is not a
ranking — this repo's memory already says a decaying severity curve from a single reviewer is not
convergence, and here the *shape* of the error is the lesson: Codex reasoned about the fixture, the
Claude half **ran** it.

## Where the halves agreed, and it is the finding that matters

**Codex High-1 = Claude B3 = the coordinator's own measurement.** Three independent derivations of
one defect: `files_are_code` tags **PR #147 `code` on 22 of 47 anchored documents**. #147 is the
ADR-0010 anchor-header backfill — it added `> **Anchor:**` to ~26 documents and also touched
`ci.yml`, `check-anchors.py` and `gen-backlog-page.py`.

The coordinator measured the same thing from a different angle before reading either half: **46 of
47 documents reach a `code`-tagged PR whose file paths share no word with the document's own stem.**
The Claude half sharpened it further — for **5 documents #147 is the *only* code-tagged PR**, so
those cards would assert `1 code PR(s)` naming a PR that implemented none of them, *and* suppress
the `⚠ no code PR yet` flag that is the true finding for them.

**Adjudication: the spec's v3 claim is retracted, not patched.** Both halves independently proposed
the same two options — (a) demote the tag to a claim about the commit, (b) discount high-fan-out PRs
by a threshold. Both independently recommended (a). The coordinator tested (b) and it fails: a `≤2`
document threshold excludes #147 but also kills **#176**, a genuine implementation touching 3
documents; the distribution is 40/12/3/1/1, so any threshold catching #147 is tuned to a single
outlier. **(a) is adopted, plus the fan-out rendered as a field** — `#147 · touched code · on 22
docs` lets the reader judge, where a filter would hide the ambiguity.

⚠ **This is the same shape as the retraction recorded in yesterday's handoff** — *"the fix that
finally held was a RETRACTION, not a fourth partial mechanism."* The thread-level `n_code` summary
and the `⚠ no code PR yet` flag are **deleted**, because they are where the false confidence was
loudest.

## Findings carried into remediation

| id | sev | source | disposition |
|---|---|---|---|
| B1 | Blocking | claude | FIX — union fixture's `"d"`/`"e"` dates sort reverse; got `['2','1']`, want `['1','2']`. Real dates + assert newest-first |
| B2 | Blocking | claude | FIX — `# 15 cases` at `:6` never updated; `check-selftest-counts` runs in CI (`ci.yml:275`), red from Task 1's commit |
| B3 | Blocking | claude + codex + coordinator | FIX — retraction above |
| H1 | High | claude + codex(M) | FIX — `render_threads` never reads `t["docs"]`, so Task 1's collision safety is invisible on the page |
| H2 | High | claude | FIX — Task 6's render step is a bare f-string fragment, not an edit into `build`'s single `return f"""…"""` |
| H3 | High | claude | FIX — `DOC_PATH` misses `CONTEXT.md`, `AGENTS.md`, `CLAUDE.md`, `.agents/**`; **10 real instances** in the last 400 PRs. F7 has already fired |
| — | High | codex | SCOPE — Plan 1 renders no direct work. Claude cleared the adjacent Backlog-band worry by measurement. Direct work is genuinely owed by spec §5 and is moved to the plan's explicit scope-out |
| M1 | Med | claude | FIX — Task 5's grep counts PRs, not threads |
| M2 | Med | claude | FIX — 61 pairs is GLOBAL; anchor-scoped is **6 of 41**. Label it, and watch the pairing rate |
| M3 | Med | claude | FIX — `.tag.unknown` 2.45:1 light / 3.47:1 dark, both fail WCAG AA |
| M4 | Med | claude | FIX — git is a sixth page source and no hook can watch a merge; render the HEAD sha |
| M5 | Med | claude | FIX — `.split()` where `.splitlines()` is meant; the two halves of one insertion disagree |
| M6 | Med | claude | FIX — `_raises` does not exist here, and the fallback is printed after its first use |
| B-perf | Med | claude | FIX — "doubles the cost" is unmeasured and wrong; measured ≈2.4s → ~10s (**4.5×**) |
| V1–V5 | Med | claude + codex | FIX the vacuous ones; declare the pair-dependencies for the two that are only rescued by a sibling |
| L1–L6 | Low | claude + coordinator | FIX — `parse_roots` ends `:141` not `:160`; CSS `:228-300`; Documents band `:362-369`; `build` `:372-407`; counts `187`/`47`; `--follow` inert today |

**The coordinator found L3 independently before either half returned** (`:362-368` is off by one —
the replacement block ends in the `return` that already occupies `:369`). Codex reported **nothing**
about line numbers; the Claude half checked all thirteen and found five wrong. A category one
reviewer is entirely silent on is the argument for running both halves.

## Cleared — round 2 should not re-open these

Taken from the Claude half's §9, spot-checked by the coordinator:

- Every identifier resolves; no new import; `from __future__ import annotations` (`:45`) makes the
  Interfaces' `Sequence`/`Iterable` annotations harmless.
- `None` vs `[]` survives every hop, `git_pr_history` → `history()` → `thread_prs` →
  `render_threads`. `TimeoutExpired ⊂ SubprocessError`, so `timeout=20` is caught.
- Removing the Documents band does **not** orphan the Backlog band — it renders `if a["backlog"]` and
  10 of 11 cards have no backlog today regardless.
- `"docs": ds` is correctly retained for `build`'s `:374` count.
- **0 anchor disagreements** between any spec and its plan.
- F7's two fixtures behave as claimed: `#186` code, `#187` docs only.

## Verdict

**NOT-CONVERGED.** Round 2 required after remediation.

REVIEW GAP: none — both halves ran.
