Reviewed head: 1da76dd215cb471bed98e73e01b3d2515dd77641

# dashboard-retire-s2 — review round 3, Claude half

Scope: `git show 1da76dd2` only (scripts/check-merge-ready.py, scripts/mutations/check-merge-ready.json).
Every run below was made in scratch copies (`git archive HEAD` and a `git clone --shared` at 1da76dd2).
Nothing was run in, or written to, the PR worktree.

## Change 1 — the new `replayed_gates` case at two body paths (scripts/check-merge-ready.py:2433)

The claim is that `body_file` reaches the review gate's argv at two distinct paths, and only there.

The case gives `/a/b.md` and `/c.md`. For each one it filters the labels whose argv contains that
path and expects `["review recorded"]` both times. `replayed_gates` (scripts/check-merge-ready.py:191-201)
puts `str(body_file)` only in the `review recorded` argv. The case passes: 463/463.

Hand mutations, each run against the full self-test:

| Mutation | Result |
|---|---|
| M1: ignore `body_file` (hard-code `"/x"` in the review argv) | the new case goes RED, `([], [])`. 462/463 |
| M2: route the body file to `ask store` instead of `review recorded` | the new case goes RED, `(['ask store'], ['ask store'])`, and so does the ci.yml step-parity case. 461/463 |
| M3: give the body file to BOTH `ask store` and `review recorded` | the new case goes RED, `(['ask store','review recorded'], …)`, and so does the parity case. 461/463 |

So the "and only there" part of the claim holds. The case fails if the path is ignored, sent to the
wrong gate, or sent to an extra gate. Using two distinct paths also catches a constant that happens to
match one input. That is what check-fixture-variation asked for.

## Change 2 — the retargeted mutation expect (scripts/mutations/check-merge-ready.json:467-479)

The mutation swaps `.get("NO-REVIEW:") is not None` for `.get("NO-ENTRY:") is not None`. It hits
exactly one site, scripts/check-merge-ready.py:2305. Run by hand (M4): exactly one case goes red,
`⭐ main() HOLDS a READY PR whose body declares NO-REVIEW:, rc=3`, which got `(0, False)`. 462/463. The
new `expect` names exactly that case.

Why this case is the one that dies: `granted_escapes` (scripts/check-merge-ready.py:2091-2101) only
produces keys from `GATE_ESCAPE.values()`, and that set is now `NO-REVIEW:` alone. So
`.get("NO-ENTRY:")` is always `None`. The mutant can therefore never hold on a NO-REVIEW body. It also
never holds on a NO-ENTRY body, so the old expect could not kill it. The retarget is correct.

## The NO-ENTRY case that stays behind (scripts/check-merge-ready.py:4314-4316)

The case is `⭐ main() does NOT hold a PR whose body declares only NO-ENTRY: (owner: NO-REVIEW only)`
and expects `(0, False)`. The shipped mutation can no longer make it fail. It fails only if `main()`
holds on a NO-ENTRY body. That happens only if `NO-ENTRY:` comes back as a granted escape (a
`GATE_ESCAPE` entry, or the matcher treating it as NO-REVIEW), or if some other path matches the literal
token. Those are exactly the regressions the slice wants to rule out. So the case still has a reason to
exist: it guards against reintroduction, not against the swap.

It is now killed by no manifest entry, though. A guard with no mutation that proves it is load-bearing
is weaker than the rest of the suite. **LOW, file, not fix:** a mutation that adds `"NO-ENTRY:"` back
into the `GATE_ESCAPE` values (or into `granted_escapes`' marker set), expecting this case, would bind
it again. This is not a defect in this commit, and the round cap says to file it.

## Gates run

- `python3 scripts/check-merge-ready.py --self-test` → **463/463**, rc 0. The docstring now says 463,
  which matches.
- `python3 scripts/check-selftest-counts.py`: the first run was in the `git archive` copy, which has no
  `.git` and no `node_modules`. It reported reds in check-shipping-sets, check-paid-caller-arrival,
  check-publishability, check-plan-code and regen-pages. I re-ran them in a real clone at 1da76dd2:
  regen-pages 123/123 and check-publishability 177/177 (the archive copy had no git). With
  `node_modules` linked in, check-shipping-sets went 170/170 and check-paid-caller-arrival 32/32. So all
  of those reds came from the environment. None comes from this commit, and none involves
  check-merge-ready. The full count check re-run in the clone: see the last section.

## Findings

No BLOCKER, HIGH or MEDIUM findings.

- LOW (file, not fix): scripts/check-merge-ready.py:4315. No mutation in the manifest kills the
  NO-ENTRY non-hold case any more. Failing input: none, because no mutant currently reaches it. The fix
  to file is a mutation that re-grants `NO-ENTRY:`.

## Count check re-run (clone with node_modules)

`python3 scripts/check-selftest-counts.py` in the `git clone --shared` copy at 1da76dd2 with `node_modules` → rc 0:
"self-test counts: 97 script(s) declare a count, every one verified by running it (4 at a time)". No ✗ lines.

VERDICT: CONVERGED
