# PR #211 — review round 1 (Codex half)

**Subject:** `fix/one-fence-scanner`, one commit over `master` (`b3d44f09`) — backlog #85, the
three fence scanners unified behind `fence_closes`.
**Model:** `gpt-5.5`; `gpt-5.6-sol`, `-terra`, `-luna` each returned HTTP 400 and the wrapper's
fallthrough handled it. **Verdict:** `docs/reviews/verdicts/211-r1-codex.verdict.json`
(`gate_ran=true`, 1380 chars).

**REVIEW GAP:** claude — not invoked; the session instruction forbids spawning subagents unless the user asks. One reviewer, not two.

**Why this branch was reviewed rather than merged on green CI.** It edits the gate that guards
every other branch. `docs/dev-process.md` makes the adversarial round a required Phase 3 gate,
so running it was process, not a judgement call; merging remains the human gate.

---

## VERDICT: CONVERGED — no Blocking, no High, no findings at any severity.

**This was an executing review, not a reading one.** Codex ran:

- `check-dashboard-entry.py --self-test` → `127/127 passed`, `13/13 cannot-run cases passed`
- `check-plan-code.py --mutate .` → `7 file(s), 162 mutation(s), 0 survivor(s)` — independently
  reproducing the author's result rather than taking it on trust

## The four things it was pointed at, and what it found

**1 — Did the refactor preserve each consumer's comment-vs-fence PRIORITY?** This was the
question most likely to hide a defect: `_inert_lines` and `exemption_reason` check HTML comments
*before* fences, `fenced_lines` has no comment handling at all, and the backlog row warned that
the obvious unification changes that precedence. Codex diffed HEAD against
`master:scripts/check-dashboard-entry.py` over probes for a fence inside an active HTML comment,
a `<!--` inside an active fence, and same-line comment/fence variants. **Priority behaviour
matched master.**

**2 — Behaviour outside the author's corpus.** The 420-case corpus varies
opener/closer/payload/wrapper and does NOT vary CRLF, tabs, indentation depth, blank lines inside
fences, or fences at the first/last line. Codex probed exactly those. **The only behaviour changes
it reproduced were the intended annotated-closer revocations** — no unintended change surfaced in
the dimensions the corpus could not see.

**3 — The manifest.** All **34** anchors resolve exactly once, and the five fence anchors
(`same_char`, `long_enough`, `no_trailing_text`, the gate's `elif fence_closes(...)` call, and the
`return same_char and long_enough and no_trailing_text` composition) each produce their named red
self-test case.

**4 — The self-test case that admits it is weak.** Confirmed accurate: mutating `no_trailing_text`
does **not** make the scanner-agreement case fail — the direct rule cases and the gate-bypass case
catch it instead. The docstring and manifest note describing that limit are correct, which matters
because an over-claimed guard is worse than an absent one.

## Disposition

Converged on round 1 with nothing to fold in. The branch stands as pushed. One reviewer, not two;
the missing Claude half is recorded above rather than papered over.
