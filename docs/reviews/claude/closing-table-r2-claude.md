# closing-table — round 2, Claude half

**REVIEW GAP: the independent Claude half could not be dispatched (same reason as round 1).** This
session is instructed not to spawn subagents unless the user asks, so this is a coordinator
self-review and is weaker than an independent half by construction. Re-attempt before merge if a
subagent becomes available.

## Round 2's verdict: NOT CONVERGED — and it was right on every count

The Codex half ran the real harness on a clean `git archive HEAD` copy, which is how it found the
one thing neither my self-review nor my own verifier saw.

| # | Grade | Finding | Status |
|---|---|---|---|
| r2-B1 | Blocking | **Duplicate mutation anchors.** Two pairs of entries shared an edit anchor, and the harness refuses those outright — so `--mutate .` returned `NOT MEASURED` and the "19/19 kill" claim had no harness backing | fixed: the push pair retargeted to the commit pattern, the `--help` entry dropped (its behaviour keeps a self-test case, not a mutation) |
| r2-H1 | High | quote-blind segment splitting | already fixed in the working tree when r2 ran; now committed |
| r2-M1 | Medium | `(GIT_SSH=x git push)` missed — env prefixes were stripped BEFORE the subshell bracket | fixed: brackets first, then assignments |
| r2-M2 | Medium | an unclosed fence suppressed a valid table | already fixed in the working tree; now committed |
| r2-L1 | Low | the warning still CONTAINED the false claim "it is appended to …" even when the append failed — the later sentence repaired the truth but did not remove it | fixed: `decide()` is pure and no longer claims; the caller, which knows the outcome, states it |

## ⭐ The finding that matters beyond this branch: my verifier was weaker than the gate it stood in for

I wrote a scoped mutation verifier to avoid running `--mutate .` against the live checkout (see the
r1 document for why). It checked that every anchor **resolves**. It did not check that anchors are
**distinct** — and the real harness refuses a duplicate because it "measures nothing new": a repeat
keeps the COUNT while silently narrowing coverage.

So my stand-in reported **21/21 green on a manifest CI refused outright.** That is this project's
recorded *a second implementation of one rule DRIFTS* shape, and specifically its sharpest form: a
stand-in weaker than its subject reports a pass the subject REFUSES. Two independent things caught
it — CI, and the Codex half running the real harness — and neither was my own tooling.

The verifier now checks anchor uniqueness and refuses with exit 2. **The general lesson is the one
already written down:** a stand-in for a gate must be measured against the gate, not against my
model of it.

## Verification

| check | result |
|---|---|
| Self-test | ✅ 84/84 |
| Mutations kill via the case each NAMES | ✅ **21/21**, 0 survivors, 0 unattributable, 0 orphaned |
| Mutation anchors are DISTINCT | ✅ asserted before writing the manifest, and by the verifier |
| `check-plan-code` / `check-fixture-variation` / `check-selftest-counts` / `check-ratchet-contract` self-tests | ✅ all rc=0 |
| Those four as gates | ✅ all rc=0 |
| `check-docs` | ✅ rc=0 |
| An independent Claude reviewer ran | ❌ **NO** — see REVIEW GAP |
| Real `--mutate .` on a clean tree | ⏳ run after this commit, on a `git archive` copy — never the checkout |
