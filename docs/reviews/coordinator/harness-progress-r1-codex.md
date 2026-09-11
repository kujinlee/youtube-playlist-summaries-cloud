<!-- codex-review: model=gpt-5.5 -->

**Proof**
`git log --oneline origin/master..HEAD`:

```text
e017b163 The mutation harness says where it is, instead of going silent for minutes
28de2088 Round 5: CONVERGED — and the last defect found was a number of mine
8577e525 Round 4: both ends of an override must name a tray part
ded5bbe7 Round 3: delete the repair machinery rather than fix it a third time
51b0803f Round 2: the marked region is verbatim, and the repair is guarded
d9878eeb Round 1: the marker region goes back to being verbatim
370144b1 Backlog #106: composing a page twice now produces the same page
```

`git diff backlog-106-compose-idempotence...HEAD --stat`:

```text
 docs/dashboard-entries.md              |  35 +++++++++++
 scripts/check-plan-code.py             | 107 ++++++++++++++++++++++++++++++---
 scripts/mutations/check-plan-code.json |  39 ++++++++++++
 3 files changed, 172 insertions(+), 9 deletions(-)
```

**Blocking**
Empty.

**High**
Empty.

**Medium**
1. Nested `--self-test` now leaks progress to stderr, despite the safety rationale saying nested runs must stay quiet. `mutate_delivered` unconditionally calls `stderr_progress` in both control loops at [scripts/check-plan-code.py:876](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:876) and [scripts/check-plan-code.py:904](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:904), and passes it into `run_mutations` at [scripts/check-plan-code.py:888](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:888). But `_self_test` directly invokes `mutate_delivered` repeatedly at [scripts/check-plan-code.py:1797](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1797) and [scripts/check-plan-code.py:1808](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1808), and also calls `main(["--mutate", ...])` while capturing only stdout at [scripts/check-plan-code.py:1953](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1953) and [scripts/check-plan-code.py:1976](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1976). I measured `python3 scripts/check-plan-code.py --self-test > /tmp/cpc.out 2> /tmp/cpc.err`: rc 0, stdout `105/105 passed`, stderr 542 bytes of progress. That means the default is safe only for `run_mutations`, not for the whole nested mutator path the comment names at [scripts/check-plan-code.py:949](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:949). Make `mutate_delivered(..., progress=None)` too, and have `main --mutate` supply `stderr_progress`.

2. `flush=True` is claimed as load-bearing but is not guarded. The production line is [scripts/check-plan-code.py:1195](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1195); the docstring claims a pipe otherwise buffers progress away at [scripts/check-plan-code.py:1192](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1192). Removing only `, flush=True` leaves the suite green: I mutated that line to `print(progress_line(done, total, label), file=sys.stderr)` and got rc 0, `105/105 passed`. Also, on current CPython, normal `sys.stderr` is visible before exit through a pipe even without explicit flush; stdout is the stream that block-buffers in the simple pipe case. A constructed case where flush matters is a replaced/block-buffered `sys.stderr`, e.g. `contextlib.redirect_stderr(open(...))` or a custom `TextIOWrapper`; there, bytes remain hidden until flush/close. So either add the mutation/case for flush, or soften the claim to the actual measured environment.

**Low**
1. The three new manifest entries do cover their named content, but not the flush clause. I verified:
`progress is written to stdout...` at [scripts/mutations/check-plan-code.json:410](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/check-plan-code.json:410) makes `progress goes to stderr...` fail.
`the progress reporter is accepted and never called` at [scripts/mutations/check-plan-code.json:423](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/check-plan-code.json:423) makes `the caller is told once per mutation...` fail.
`a progress line reports position without its total...` at [scripts/mutations/check-plan-code.json:436](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/check-plan-code.json:436) makes `a progress line states position...` fail. It also fails the stderr-format case because both share `progress_line`.
The sixth “guard exists, content unguarded” instance is flush.

2. Unbounded labels are probably okay for correctness. The label is passed raw from mutation names at [scripts/check-plan-code.py:948](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:948) into `[done/total] {label}` at [scripts/check-plan-code.py:1183](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1183). I found manifest names up to 232 chars, so terminals/logs will wrap, but nothing in this patch parses progress lines. If this becomes machine-consumed later, prefix-only parsing or escaping becomes necessary.

**Stream**
Progress reaches stderr via [scripts/check-plan-code.py:1195](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1195), and the stdout stream for successful `--mutate` stays the final tally at [scripts/check-plan-code.py:2478](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:2478). CI invokes the commands directly at [.github/workflows/ci.yml:358](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.github/workflows/ci.yml:358) and [.github/workflows/ci.yml:364](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.github/workflows/ci.yml:364); I didn’t find an in-repo parser using `2>&1` for this command. If a caller manually merges `2>&1`, progress will precede the verdict, so whole-output parsers break; last-line parsers still survive.

**Not Measured**
The author did not measure nested `--self-test` stderr, removal of `flush=True`, time-to-first-progress in CI/log aggregation, failure-path progress shape, or maximum progress-line length/wrapping.

NOT CONVERGED: make `mutate_delivered` progress-injected like `run_mutations`, default quiet, and pass `stderr_progress` only from the real `--mutate` entry point.
