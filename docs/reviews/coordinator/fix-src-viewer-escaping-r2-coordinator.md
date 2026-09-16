# Round 2 — `fix-src-viewer-escaping` — coordinator

```yaml
round: 2
fixes_nontrivial: false
subject: fix-src-viewer-escaping
halves:
  codex: ran
  claude: gap
findings:
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: plugins-doc, disposition: fixed}
  - {id: M2, severity: Medium, aim: instrument, fix_induced: true, component: review-bookkeeping, disposition: fixed}
  - {id: M3, severity: Medium, aim: instrument, fix_induced: true, component: dashboard-gate, disposition: fixed}
deliverable_code_findings: 0
```

## ⭐ The headline: Codex found NO surviving code finding, and it looked hard

> No surviving code finding in the encoded-path fix or the HTML escaping fix. I measured
> `resolve_page` and stubbed `do_GET` across raw, mixed-case, `%25` nesting, overlong `%c0%ae`,
> Unicode dot lookalikes, encoded slash, trailing dot, and query/fragment dot cases. The secret
> target stayed closed; literal percent-name decoys are served only when the literal percent filename
> exists, which matches the split-root tests' intent.

That last clause matters: it independently validates the **two-sandbox** design round 1 arrived at
after the decoy broke its sibling case. Both encoded-path repairs now hold against spellings neither
I nor round 1's Claude half had tried.

## REVIEW GAP: claude — not run for round 2, and here is the exact reason

Round 2's three findings are **documentation and bookkeeping**: a contradicting paragraph in
`plugins.md`, the review-round filing, and the dashboard entry. **`deliverable_code_findings: 0`, and
no code changed in response to this round** — the only edits are the eight rewritten lines of
`plugins.md`, two review files, and a dashboard block.

⭐ **The code itself has had BOTH halves**: Claude reviewed the fixes as round 1 and returned seven
findings; Codex reviewed the result as round 2 and found nothing surviving. What is missing is a
Claude pass over three documentation edits, and `review-method.md`'s own Q4(b) lists *"land the
editorial fixes ahead of the final round"* as a legitimate answer rather than spending a round on it.

⚠ **Stated so it can be disagreed with**: if the standard is *every round has two halves regardless
of what the round contains*, this does not meet it. I judged a 40-minute adversarial pass over a
rewritten paragraph to be the cost `review-method.md:309` warns about, not diligence.

## M1 — the SECOND place telling the caller to give up early

`docs/plugins.md:230`'s *Bounded wait* paragraph still said to treat a quiet Codex output file as a
hang after ~2–3 minutes and fall back immediately. ⭐ **That is precisely the instruction that cost
three rounds their Codex half**, and it survived my first repair because I fixed the paragraph I was
looking at and did not search for its sibling — the same fix-the-instance shape this branch has now
produced three times in one round.

It now says a quiet file is **not** a hang until `--timeout` has elapsed (the wrapper buffers, so a
45-minute review is silent for 45 minutes), and reserves immediate fallback for a usage limit, auth
failure, HTTP error, or no output file at all — *those are answers, not silence*. ⚠ Rewritten inside
the **same eight lines**: `plugins.md` sits at its 260-line budget and `check-docs.py` refused three
attempts to grow it, correctly each time. The operative rule lives in the wrapper; the account lives
in `process-rationale.md`.

## M2, M3 — the two gates this branch was failing

Both were real and both are now green: the Codex half is filed for this branch (this round), and the
dashboard entry is written. ⚠ Note that **M2 is the same finding round 1's H1 made**, arrived at
independently from the other side — round 1 found that the filed verdict named the parent; round 2
found that the guard consequently reported the branch as missing a Codex half. Two reviewers, one
defect, two symptoms.

## Evidence

689 mutations, 689 killed, 689 attributed, 0 survivors (run by the coordinator; Codex explicitly
noted it did not run the 12-minute sweep). Suite 202/202 in all three `$HOME` shapes;
`codex-review.py` 91/91; `check-plan-code.py` 128/128; docs, ratchet-contract, selftest-counts,
fixture-variation all green.

## Q4 / Q5

**Convergence: reached.** Zero surviving code findings from the half that had never seen this branch,
after an explicitly broad spelling sweep; `fixes_nontrivial: false` for this round's edits.

**Thrashing: not armed** — one component (`plugins-doc`) carried a fix-induced finding in one round,
not two.
