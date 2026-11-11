<!-- codex-review: model=gpt-6.1-sol -->

- **R2-1 — High — [scripts/check-compaction-boundary.py:350](scripts/check-compaction-boundary.py#L350): Filter arguments can carry independent work.** `tail -n 0 -F ~/explainers/questions.md | cat /tmp/ci-events.fifo` returns `True`. Bash reads CI events from the FIFO instead of the watcher’s stdin. Reproduced delivery of `CI_JOB_RUNNING` while `signals()` returned `[]`, allowing compaction during active work.

- **R2-2 — High — [scripts/check-compaction-boundary.py:305](scripts/check-compaction-boundary.py#L305): Redirect recognition loses token adjacency and quoting.** `tail -F ~/explainers/questions.md 2 >&1` returns `True`. Bash treats the separated `2` as another filename and `>&1` as stdout redirection; the checker strips all three tokens as stderr redirection. Reproduced bash following a CI log named `2`. Quoted `'2'>&1` also passes. This is introduced by the round-1 tokenizer rewrite.

- **R2-3 — Medium — [scripts/check-compaction-boundary.py:323](scripts/check-compaction-boundary.py#L323): One lexical path can expand into multiple watched files.** `tail -F /tmp/{questions,ci}/explainers/questions.md` returns `True`; bash expands it into two paths. Reproduced output from both files, including CI events. Wildcards likewise bypass the single-file restriction.

Validation: **99/99 self-tests passed**; the exact documented §5 watcher matches. Independently applied all **18 new mutations** in temporary copies: all were killed by their named cases. The standard mutation harness could not run because `node_modules/typescript` is missing; its full gate remains unverified.

VERDICT: NOT CONVERGED
