<!-- codex-review: model=gpt-5.5 -->

**Findings**

BLOCKING: `check-surface-recall.py` has a fourth instance of the wiring class: the `coverage(...)` result can be discarded and no named case goes red.

Evidence:
- `scripts/check-surface-recall.py:270`: `defined = _defined_codes()`
- `scripts/check-surface-recall.py:271`: `problems = coverage(defined, DECLARED_RENDER)`
- `scripts/check-surface-recall.py:465`: `case("equal sets agree", coverage(D, DECLARED_RENDER), [])`
- `scripts/check-surface-recall.py:466`: `case("a defined code with NO declared sentence is refused",`
- `scripts/check-surface-recall.py:470`: `case("a declared sentence for a code nothing defines is refused",`
- `scripts/mutations/check-surface-recall.json:80`: `"name": "the coverage check stops reporting a DEFINED code with no declared sentence, so a new rc arrives with nobody having approved what the reader sees"`
- `scripts/mutations/check-surface-recall.json:84`: `"    for code in sorted(set(defined.values()) - set(declared)):"
- `scripts/mutations/check-surface-recall.json:135`: `"name": "the net's result is never READ at the call site, so the literals go unchecked while the function that checks them still runs"`

The manifest covers the internals of `coverage`, and covers the wiring of `declaration_dangles`, but not the call-site consumption of `coverage`.

Reproduction I ran in a temp copy:
- Replaced `problems = coverage(defined, DECLARED_RENDER)` with `problems = []`.
- Result: `python3 scripts/check-surface-recall.py --self-test` still printed `43/43 self-test cases passed`.
- Result: `python3 scripts/check-surface-recall.py` still exited 0 and printed `surface-recall OK`.

What would prove this wrong:
- A temp mutation that severs only this call site must make a named self-test case red, or a manifest entry must target this exact call-site wiring and be killed.

HIGH: repo-path fixtures can make `check-ratchet-contract.py` falsely see `check-surface-recall.py` as called.

Evidence:
- `scripts/check-surface-recall.py:320`: `path = HOOK.parent / f"_selftest-{_os.getpid()}.sh"`
- `scripts/check-surface-recall.py:334`: `marker = HOOK.parent / f"_selftest-{_os.getpid()}.marker"`
- `scripts/check-surface-recall.py:336`: `marker.write_text("a file the FIXTURE owns, so the arm means the same thing in the real `
- `scripts/check-surface-recall.py:338`: `path.write_text(text, encoding="utf-8")`
- `scripts/check-ratchet-contract.py:868`: `caller_sources: list[Path] = [ci_path]`
- `scripts/check-ratchet-contract.py:870`: `caller_sources += sorted((ROOT / ".claude" / "hooks").glob("*"))`
- `scripts/check-ratchet-contract.py:883`: `blob_for[rel] = "\n".join(`
- `scripts/check-ratchet-contract.py:884`: `p.read_text(errors="ignore") for p in caller_sources`

Reproduction I ran in a temp copy:
- Removed the two CI `run:` lines for `scripts/check-surface-recall.py`.
- Without fixture: `python3 scripts/check-ratchet-contract.py` exited 1 with `scripts/check-surface-recall.py [R3_no_caller]`.
- Added `.claude/hooks/_selftest-999999.sh` containing `python3 scripts/check-surface-recall.py`.
- With fixture: `python3 scripts/check-ratchet-contract.py` exited 0 with `ratchet contract OK`.

This is more than SIGKILL debris. During a normal concurrent self-test, the fixture exists long enough for a peer guard to read it as caller evidence.

What would prove this wrong:
- `check-ratchet-contract.py` ignores `_selftest-*`, or `_fixture_hook` writes outside the caller-source glob, and the same temp reproduction stays red with the fixture present.

HIGH: `check-rc-contract.observe` got the stderr refusal but not the scrubbed environment, so the sibling instance of round 7 L1 remains.

Evidence:
- `scripts/check-rc-contract.py:286`: `proc = subprocess.run(["bash", str(hook)], capture_output=True, text=True, timeout=30)`
- `scripts/check-rc-contract.py:299`: `if proc.stderr.strip():`
- Compare the fixed sibling:
- `scripts/check-surface-recall.py:139`: `env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "TMPDIR", "LANG")}`
- `scripts/check-surface-recall.py:147`: `proc = subprocess.run(["bash", str(target), str(stub)], capture_output=True,`

Reproduction I ran:
- `PYTHONVERBOSE=1 python3 scripts/check-rc-contract.py --self-test`
- Exit: `1`.
- Diagnostic included: `CannotRun: the hook wrote to STDERR at rc=0 ... Round 6 H1 / round 7 H2 — NOT RUN.`

This is the same ambient-env class the new surface guard fixed, but in the older staged observer.

What would prove this wrong:
- Running `PYTHONVERBOSE=1 python3 scripts/check-rc-contract.py --self-test` stays `55/55`, and the subprocess at `observe` is shown to receive only the env it needs.

**Direct Answers**

Can `$1` arrive non-empty in production? I could not reach that in the current production wiring. `.claude/settings.json:57` is exactly `"command": "bash .claude/hooks/surface-recall.sh"`, and I found no production wrapper or `$@` propagation path that invokes it with an argument. Worst reachable case is a deliberate or future caller passing a Python file path: `.claude/hooks/surface-recall.sh:60` sets `MATCHER="${1:-$REPO_ROOT/scripts/recall-llm.py}"`, line 63 runs `python3 "$MATCHER" --fire`, and line 112 forwards payload into `additionalContext`. It is arbitrary Python execution by a caller already able to alter the hook command or call it manually, not direct shell command injection.

Is there a fourth instance of the wiring class? Yes. The fourth is `coverage(...)` in `scripts/check-surface-recall.py:271`; severing the call site leaves the direct `coverage` cases green and the live guard green.

**Counts Derived**

- `check-rc-contract.py --self-test`: observed `55/55`.
- `check-surface-recall.py --self-test`: observed `43/43`.
- `scripts/mutations/check-rc-contract.json`: parsed JSON length `15`.
- `scripts/mutations/check-surface-recall.json`: parsed JSON length `14`.
- `EXPECTED_MUTATIONS`: parsed AST literal in `scripts/check-plan-code.py`; 57 files, sum `1167`, with `check-rc-contract.py = 15` and `check-surface-recall.py = 14`.
- Live runs: both rc 0.

**Could Not Establish**

- I could not verify the dispatch fingerprint. My `sha256(git diff --binary)` was `e3d335b61e3f29d895ac8e61b89838616ddb24040386723618ff21c073f79416`, not `21d3fc49b51e117c3f74770a9e695acadfed557c46cf9665416500398326cf2a`. The fingerprint recipe is not stated, so this may be a method mismatch rather than tree drift.
- I did not find a remaining import fail-open in `_defined_codes`; failures I inspected read as rc 2 or raw failure, not pass.
- I did not find #210’s mechanism wrong. `scripts/check-plan-code.py:1693` is `rc, out = run_suite(d, fname)`, with `fname = mut.get("file", "")` at line 1654, so current schema still couples mutation target and suite.

NOT CONVERGED
