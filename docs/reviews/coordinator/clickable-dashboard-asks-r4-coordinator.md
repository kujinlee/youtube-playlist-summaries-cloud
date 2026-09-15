# clickable-dashboard-asks — round 4, coordinator adjudication

**REVIEW GAP: claude** — as rounds 1–3; this session does not spawn subagents.

* Codex: `docs/reviews/codex/clickable-dashboard-asks-r4-codex.md` (`gpt-5.5`) —
  **0 Blocking, 0 High, 1 Low. CONVERGED.**
* Verdict: `docs/reviews/verdicts/clickable-dashboard-asks-r4-codex.verdict.json`,
  `gate_ran: true`, `head ac642595`, **`dirty: 0`** — it reviewed exactly the tree that
  merges.

## ⛔ THIS ROUND SHOULD NOT HAVE RUN, AND NEITHER SHOULD ROUND 3

Surfaced by the user asking *"what is the stopping condition? if reviews were converged,
why continue?"* — and the answer is in `docs/review-method.md`, which the coordinator had
not re-read:

* `:302` — the loop runs *"until a round reaches **diminishing returns**."*
* `:307` — re-review is required for *"any round that returned a **Blocking** finding, or
  whose fixes were **non-trivial**."*
* `:309` — *"For small, contained changes (single-file logic, config, thin wrappers), one
  round is fine — **do not over-apply this**."*
* `:298` — *"Address all High/P1 findings before showing the user. **Present Medium/P2 for
  a decision.**"*

| round | found | required by the doc? |
|---|---|---|
| r1 | 1 Medium | fix was non-trivial → yes |
| r2 | the stale-floater **High** | High → yes |
| r3 | 1 Low, in the TEST | **no** — diminishing returns |
| r4 | 1 Low, in the TEST | **no** |

⭐ **THE ROOT CAUSE IS A CONFLATION, NOT A RULE.** Two different conditions were merged and
reported as one:

1. **Review convergence** — findings-based, the doc's actual condition. Reached by r3.
2. **`check-review-recorded`'s second question** — *was the MERGING TREE reviewed?* A
   statement about **tree identity**, not about review quality.

Rounds 3 and 4 were run to satisfy (2) while being described as if (1) were unmet. The
gate has cheaper legitimate answers — hold the fixes uncommitted so the reviewer sees what
merges, or declare `NO-REVIEW:` — and **neither was ever put to the human.** The most
expensive option was taken silently, twice.

⚠ This is the mirror image of PR #299, and the inversion is the lesson. There, every round
aimed at the DELIVERABLE found a fail-open, and stopping early would have shipped one.
Here the deliverable produced nothing after r2's High; r3 and r4 were aimed at the
coordinator's own TEST and found test defects. **Same instruction — read the aim, not the
count — opposite verdict.** A rule that says "keep going" is not symmetric with one that
says "you may stop": #299's cost was stopping too early, this branch's was stopping too
late, and only the aim column distinguishes them in advance.

## L1 — the guard tests the FRAGMENT, not the page that ships

**NOT FIXED. Proposed for the backlog, pending the user's agreement** (filing is theirs).

`no emitted rule hides the chooser` scans `<style>` bodies in the fragment `_B(...)`
builds. Production does not ship that fragment: `main` writes it to a temp file and invokes
`brief-compose.py`, which injects `SHIM`, lifted tray CSS and chrome CSS into the FINAL
`<style>`. So a composer or tray rule hiding `.pick` reaches the delivered page unseen by
this guard. Inline `style=` attributes are outside the scan for the same reason.

⭐ **A guard measuring a different artifact than the one that ships** — the named shape
*"a green check over the wrong subject"*. Codex states the bound precisely: *"Current
committed chooser markup has no inline `style=`, so this is a **guard gap, not a present
hidden button**."* Per `:298` a Low is presented, not auto-fixed, and per `:302` this round
is past diminishing returns — so fixing it here would repeat the error this document
records.

Also recorded from r4, unfixed and bounded: `opacity:var(--x)` and `opacity:calc(0)` do not
match the value regex and therefore **fail open**; a lone `.` raises `ValueError` and is
swallowed. Acceptable for invalid CSS, still fail-open for unparseable values.

## Verified

```
gen-dashboard   --self-test  325/325        check-plan-code --self-test  128/128
EXPECTED_MUTATIONS 68 · declared sum 633 · manifest 68 entries — all agree
all four added anchors occur EXACTLY ONCE; every `expect` exactly matches a live case
r4 verdict head == HEAD, dirty 0 — the reviewed tree IS the merging tree
```

**CONVERGED. STOP.** No further round. The one Low is a bounded guard gap, presented for a
decision per `:298`, not fixed.
