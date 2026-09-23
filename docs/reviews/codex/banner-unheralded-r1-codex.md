# banner-unheralded — round 1, Codex half

Subject: `ffc85be8` on `banner-work-without-banner`. Model: gpt-5.5, via `scripts/codex-review.py`.
Prompt: the round-1 adversarial brief (corpus method, the `reason` change, the `paused` change,
unfalsifiable cases). Verdict file: `docs/reviews/verdicts/banner-unheralded-r1-codex.verdict.json`.

<!-- codex-review: model=gpt-5.5 -->

No Blocking / High / Medium / Low findings.

I verified rather than only reading:

- `python3 scripts/check-banner-armed.py --self-test` passes: `133/133`.
- Targeted mutation run for `scripts/check-banner-armed.py`: `22 measured, 0 survivors`.
- Direct probes confirmed:
  - `decide([], armed=False, tool_uses=25)` warns as `unheralded`.
  - paused large turns stay quiet.
  - armed/bannerless edited large turns remain `unbannered`, not `unheralded`.
  - `run_decide` logs `unheralded` with `25 tool calls`.
  - pausing after a subject turn ended does not retroactively excuse that turn.

The framing around calibration also looks honest to me: “fires on unbannered turns” is an upper-bound volume estimate, not a false-positive rate, because historical armed/paused state is unrecoverable. The corrected `entrypoint == "cli"` corpus split is more legitimate than the earlier `StructuredOutput` proxy.

Residual risk is the known one: the threshold is still a proxy for “multi-step job,” so warn-only remains the right mode.

VERDICT: CONVERGED
