# Round 8 — `push-hook-quoted` (PR #542, backlog #428) — coordinator — NOT CONVERGED; one fail-open folded

REVIEW GAP: claude — alternation

```yaml
round: 8
fixes_nontrivial: true
subject: push-hook-quoted
halves:
  codex: ran
  claude: gap
findings:
  - {id: X-F1, severity: Blocking, aim: deliverable, fix_induced: false, component: hook-adapter, disposition: fixed}
```

Codex (`docs/reviews/codex/push-hook-quoted-r8-codex.md`) reviewed `beaccd20`. **NOT CONVERGED — one BLOCKER, with
a repro.** In the hook, `deny` passed the refusal reason to `jq` as an argument (`--arg reason "$1"`). The detector's
`option` refusal quotes the unknown option in full. So an unknown option of ~1.1 MB pushed jq's argument list past the
OS limit, jq never ran, and `deny` exited 0 with empty stdout. Empty stdout means ALLOW. Master denies all four repro
payloads (an oversized option followed by `--force`, `--no-verify`, `master` or `HEAD:master`). The fault predates
round 7's fold, so it is not fold-induced. Neither existing suite saw it. Codex ran **230** other crafted file-based
comparisons and found no loosening. All seven flagged ids answered `finding` (`a37789af0a0d`, `19e3cb6a182b`,
`1c483d300bca`, `0639175f96f3`, `6ed1cdc83491`, `475f8e419a00`, `b4c2d38505b1`) name this one cause. The other eleven
are answered `not a loosening`.

**Fold.** `deny` now fails closed by construction (`.claude/hooks/block-default-branch-push.sh`):
1. The reason never goes in an argv. It reaches jq on stdin (`jq -Rsc`), bounded first to `REASON_MAX` (4000)
   characters with a truncation marker.
2. If jq's output does not start with the deny object, for any reason (a failure, a kill, empty output), `deny`
   prints a fixed literal deny instead, the same shape as the no-jq refusal. Every exit from `deny` emits a deny.

The audit of every other argv site that carries payload-derived text found none that can fail open:
- The payload reaches `jq -ser` on stdin, and the command reaches `push-command.py decide` on stdin. Both use
  `printf`, a builtin with no argv limit.
- `decide`'s arguments are the current branch, the default branch and `0|1`. All three come from git, not the
  payload.
- The floor gets its payload on stdin.
- Master's messages interpolate only `${default_branch}`.
- The only other payload-derived values that reach a message are `${reason}`, `${detected}` and `${rule}`. All three
  now pass through the bounded `deny`.

On the detector side, the four 1.1 MB repros are refused as `option` in ~0.55 s. A 1.1 MB **feature** push with no
unknown option is **refused, not allowed**, and that is accepted. Master's own hook, run as the floor, does not finish
even a 50 KB push line inside its 2.5 s budget (`floor-not-run`). At 1.1 MB, `decide` itself passes its 3 s deadline
(exit 142), and the hook refuses on that deadline. Both outcomes are NOT CHECKED refusals, never allows.

The hook self-test went from **65 to 71** cases:
- the four Codex payloads, built as files in the fixture and run concurrently, for ~2 s of wall time;
- a case that the oversized reason is truncated with its marker;
- a stub `jq` that reads the payload but cannot serialize, which must still produce the literal deny.

Reverting `deny` to the `--arg` form reddens all six (65/71). `push-command.py` is unchanged: 352 cases, and the
mutation count is unchanged.
