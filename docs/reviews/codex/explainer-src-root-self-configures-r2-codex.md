<!-- codex-review: model=gpt-5.5 -->

## Verdict
FINDINGS

## Findings
### [Medium] No-fallback help still prints a stop command inside the missing checkout in the real call path
**Where:** `scripts/explainer-serve.py:525`

**What:** `live = shlex.quote(str(pathlib.Path(__file__).resolve()))`

Actual caller passes the same root derived from that file:

`scripts/explainer-serve.py:110`
`SCRIPTS = pathlib.Path(__file__).resolve().parent`

`scripts/explainer-serve.py:115`
`REPO = SCRIPTS.parent`

`scripts/explainer-serve.py:1058`
`body = src_root_help(os.environ.get(SRC_ROOT_ENV, "").strip(), REPO)`

**Why it matters:** The new test uses `src_root_help("", pathlib.Path("/tmp/gone"))`, while `__file__` still points at the live checkout, so it proves only that a fake missing repo does not appear after `"Stop it with:"`. In production, the no-fallback arm is reached when `src_root()` returns `None` because `REPO.is_dir()` is false. But `REPO` is `Path(__file__).resolve().parent.parent`, so the emitted stop command is `python3 {REPO}/scripts/explainer-serve.py --stop`, exactly inside the checkout just described as moved or deleted. If that directory is gone, the command fails with `[Errno 2]` again.

This also invalidates the comment’s premise that the interpreter’s own file “necessarily exists”; the process can keep running after its source path has been moved or unlinked.

**Suggested fix:** Use a stop instruction that does not depend on the vanished checkout path, probably the pidfile location already outside the checkout (`~/explainers/.serve.pid`) plus `kill`, or omit a pasteable stop command in this arm and give a non-source-dependent recovery path. Then make the test assert the real invariant: when `repo == Path(__file__).resolve().parent.parent`, the no-fallback arm must not emit a command under `repo`.
