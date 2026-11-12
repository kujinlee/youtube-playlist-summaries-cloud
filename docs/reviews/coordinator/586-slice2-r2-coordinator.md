# Round 2 — `586-slice2` — coordinator — Codex CONVERGED with one Minor; the Minor is fixed

REVIEW GAP: claude — alternation (round 2 runs ONE half; Claude ran in round 1 and runs in round 3).

Subject: PR #565 (DRAFT), branch `586-slice2`, reviewed head `39c45123` (the round-1 fold). Half:
`docs/reviews/codex/586-slice2-r2-codex.md` — no Major, no BLOCKER; one Minor (a non-terminating closure). Codex also
judged the fold's one deliberate loosening (a non-following call on a /proc magic link is admitted) sound for every
admitted final-component operation.

```yaml
round: 2
fixes_nontrivial: true
subject: 586-slice2
halves:
  claude: gap
  codex: ran
findings:
  - {id: X1, severity: Minor, aim: deliverable, fix_induced: true, component: strace-parser, disposition: fixed}
```

`fix_induced: true` — the closure loop predates round 1, but the round-1 fold made `_runtime_links` the place every
`link*`/rename path meets, so it is counted against the fold to keep the thrashing signal honest.

## Why a Minor was fixed rather than filed

Under the review's rubric a non-terminating parse is Minor: it never yields an undersized read set. But it is not a
refusal either — it stalls the CI job that calls it until the job's own timeout, and the fix is three lines.

## How the fix was proved

- `_runtime_links` runs at most `len(moves) + 1` passes — an acyclic chain of moves closes within `len(moves)` — and
  past that returns the new refusal `rename cycle` (added to `REASONS` beside `through a runtime link`).
- Codex's exact input is now a self-test case expecting `rename cycle`: **135/135** pass. On the round-1 head that input
  did not terminate (Codex: killed at a 3 s timeout), so the case could not have passed there.
- One new mutation (`return links, None` in place of the refusal) — the bounded closure then holds `A/C/L` and the log is
  refused as `through a runtime link`, so the case goes red. `check-plan-code.py --mutate . --only
  scripts/strace_reads.py`: **83 killed, 83 attributed, 0 survivors**; pin 82 → 83.

## Next

Round 3 (the cap's last full round), the Claude half, on the fixed head.
