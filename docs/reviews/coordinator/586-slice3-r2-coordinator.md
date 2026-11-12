# Round 2 — `586-slice3` — coordinator — Codex NOT CONVERGED on one fix-induced Major; fixed

REVIEW GAP: claude — alternation (round 2 runs ONE half; both halves ran in round 1).

Subject: PR #567 (DRAFT), branch `586-slice3`, reviewed head `e2fe1d29`.
Half: `docs/reviews/codex/586-slice3-r2-codex.md`, one Major.

```yaml
round: 2
fixes_nontrivial: true
subject: 586-slice3
halves:
  claude: gap
  codex: ran
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: true, component: cross-run-record, disposition: fixed}
```

`fix_induced`: yes. Round 1's fold introduced the SHADOW argument, a labelled open's own argument that is kept for the
cross-run check. That fold also exempted SHADOW from the `..` and `/proc` checks. Round 1 had no fix-induced findings,
so this is the first consecutive round with one, and THRASHING is not armed.

## X1: a SHADOW argument holding `..` hides a peer's symlink

A SHADOW argument is compared by its TEXT across runs. A peer plants `.home/cur`, and the target opens
`docs/../.home/cur` (the kernel labels it `docs/b.md`). The text `docs/../.home/cur` never equals or nests under
`.home/cur`, so both runs were `complete` and the flow was lost. The same happens with the split
`<unfinished>`/`resumed` form. A `/proc/self/cwd/...` argument has the same gap.

**Fix (refuse, as round 1's rule says):** `_resolve` takes `cross`. It is True only from `record_from_log`, the one
caller that compares `every` across runs. With `cross` set, a SHADOW argument holding `..` refuses as
`unresolved ..`, and a SHADOW `/proc` magic link refuses as `unresolved /proc path`. The read view (`cross` False)
still takes the kernel's label, as slice 2 always has. A first attempt applied the refusal in `_cwd_pass` for every
caller, and it broke two slice-2 cases ("a successful .. open is resolved by its label", and the same for
`/proc/*/fd`). Those cases are why the refusal is scoped to the cross-run view.

## How the fix was proved

- **Before → after.** Two new cases: Codex's input (U plants the symlink, T opens through `docs/../`; the expected
  result is `peer trace incomplete` / `unresolved ..`), and a SHADOW `/proc` argument. Both failed at `e2fe1d29`
  (282/284). After the fix: **284/284**, with the slice-2 label cases unchanged.
- **Mutations.** 203 → **206**. Three were added: the SHADOW `..` refusal disabled, the SHADOW `/proc` refusal disabled,
  and `record_from_log` calling without `cross`. One anchor was re-bound (the resolver-refusal mutation now names
  `cross=True`). One was re-targeted: "a socket path skips the /proc check (taken for a shadow)" no longer reddens
  its case, because a SHADOW `/proc` path now refuses in the cross-run view too. What it still breaks is the link
  checks, so it is now "…skips the link checks" and names the r1 X3 pre-existing-link case. The pin
  `expected_mutations.py` is now 206. `check-plan-code.py --mutate . --only scripts/strace_reads.py`: **206 killed,
  206 attributed, 0 survivors**.
- `check-selftest-counts.py` and the CI check list ran locally at the fixed head (results in the PR).

## Next

Round 3 runs the Claude half (alternation), and it is the last full round under the cap.
