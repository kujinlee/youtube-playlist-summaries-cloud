# Round 1 — `subject-status-386` — coordinator — NOT CONVERGED (both halves); all findings folded

Both halves reviewed `3b924595` (`git diff origin/master...3b924595`): backlog #386 (`subject_status.py`'s stale
case) and backlog #700 (`load_map` in `check-shipping-sets.py` raising on wrong-typed values).

What held, in both halves: the stale-premise diagnosis (c517faa0 added migration 0027, so SHIPPED was correct);
the ci.yml step sits in job `verify`, which runs on pull requests; all five new or re-bound mutations are killed by
the case each names; both suites pass.

Findings and the fold:
- **C1 (Claude MAJOR).** `load_map` was not total: 100,000 nested `[` raised `RecursionError` while a refusal
  message was built, and 200,000 inside `json.loads`. Fold: `RecursionError` from the parse is CANNOT RUN, and an
  iterative depth walk (bound 32, as `check-inventory._read_json`; the real map nests 4, measured) runs before
  any rule. Two cases, one mutation.
- **C2 (Claude MAJOR).** The new UNSHIPPED fixture could not catch the ⭐ bug it cites (counting tables the
  schema only references). Fold: the fixture now references and alters `jobs`. Measured: a mutant that counts
  `references` / `alter table` names was 18/18 on the old fixture, 16/18 on the new.
- **C3 (Claude MINOR) = Codex MINOR.** The totality case let ACCEPTED through unexamined and skipped
  `measured_at`. Fold: a second case pins the exact accepted set (five substitutions, each valid by the rules);
  `measured_at` joins the loop and gets a type check, with a mutation.
- **C4 (Claude MINOR).** The `shared_with` type clause had no mutation. Fold: entry added; pin 217 → 220.
- **C5 (Claude NIT) = Codex NIT.** The module docstring called the schema unshipped, said the schema gates are
  not in CI, and showed a three-argument call. Fold: all three corrected.

Each new mutation was killed by hand on a scratch copy by the case it names; every manifest anchor resolves once.

```yaml
round: 1
fixes_nontrivial: true
subject: subject-status-386
halves:
  codex: ran
  claude: ran
findings:
  - {id: C1, severity: Major, aim: deliverable, fix_induced: false, component: check-shipping-sets, disposition: folded}
  - {id: C2, severity: Major, aim: deliverable, fix_induced: false, component: subject_status, disposition: folded}
  - {id: C3, severity: Minor, aim: deliverable, fix_induced: false, component: check-shipping-sets, disposition: folded}
  - {id: C4, severity: Minor, aim: deliverable, fix_induced: false, component: check-shipping-sets, disposition: folded}
  - {id: C5, severity: Nit, aim: deliverable, fix_induced: false, component: subject_status, disposition: folded}
```

Reviews: `docs/reviews/codex/subject-status-386-r1-codex.md`, `docs/reviews/claude/subject-status-386-r1-claude.md`.
