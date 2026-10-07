<!-- codex-review: model=gpt-5.5 -->

**Verification**

Ran from `/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud`, ignoring `docs/explainers/questions.md` and the untracked r3 Claude review as instructed.

```text
$ python3 scripts/check-rc-contract.py --self-test
rc contract: 6 code(s) defined, 4 handled by an arm, 2 declared unhandled
rc contract OK — every defined code is handled or declared, and no arm is dead. What the READER sees is check-surface-recall.py's rule, not this one

56/56 self-test cases passed

$ python3 scripts/check-surface-recall.py --self-test
surface-recall: 6 declared sentence(s), run against the REAL hook in the REAL repo
surface-recall OK — every declared code renders exactly its approved sentence

59/59 self-test cases passed

$ python3 scripts/check-plan-code.py --self-test
161/161 passed

$ python3 scripts/check-plan-code.py --mutate . --shard 5/8
OK — delivered scripts mutated: 54 file(s), 150 mutation(s), 150 killed, 150 attributed to the case each names, 0 survivor(s) — measured over shard 5 of 8 (round-robin)
```

Not run: unsharded `--mutate .`, per instruction. Full shard `8/8` was not run; I applied the surface-recall fold entries directly in staged copies instead. Conclusion for shard 8 as a whole is **NOT MEASURED**.

**Findings**

**Medium — The new property case can pass when the import never happened, so it is still falsifiable for the wrong reason.**

Finding: both new probes redirect the import command’s stdout/stderr to `/dev/null` and do not assert that the import succeeded. If the import fails, no `__pycache__` appears, so the bytecode property returns `[]`. That is exactly the feared false pass.

Concrete exhibiting inputs, in staged copies:

```text
check-rc-contract.py:
  remove PYTHONDONTWRITEBYTECODE from SUBPROCESS_ENV_KEYS
  change hook probe: import _pycprobe -> import _missing_pycprobe

result:
  rc=0
  56/56 self-test cases passed
```

```text
check-surface-recall.py:
  remove PYTHONDONTWRITEBYTECODE from both guard constants, keeping agreement green
  change surface probe hook: import _pycprobe -> import _missing_pycprobe

result:
  rc=0
  59/59 self-test cases passed
```

So the key can be absent and the case can still pass, because the probe observes “no cache” without proving “the import ran under the scrubbed production spawn.”

Proposed fix — **UNVERIFIED**: make the probe assert a positive import witness as well as absence of `.pyc`: for example, have the imported module write a sentinel file, remove the import stderr redirection or add `set -e`, assert `observe(...) == "probe-detail"` / `_render_once(...) == "probe-detail"`, and assert the sentinel exists before checking `__pycache__`.

**Low — The probe leaks temp directories on every self-test run.**

Finding: `_production_spawn_writes_cache()` uses `tempfile.mkdtemp()` and never removes the directory. Running the two self-tests created new temp dirs; my residue check saw `8` new temp dirs, with probe residue such as `_pycprobe.py` and `__pycache__` in several of them.

Concrete exhibiting output:

```text
new temp dirs 8
probe residue ['/var/.../tmpv0k9rpya', '/var/.../tmpj3hfm_db', ...]
```

This is not a correctness failure for the mutation verdict, but it is real instrument residue.

Proposed fix — **UNVERIFIED**: use `with tempfile.TemporaryDirectory() as _probe:` and convert to `Path(_probe)` inside the hook string.

**Answers To The Five Questions**

1. **Falsifiable for the right reason?** Partly. Removing the key from the constant or bypassing the constant at the call site fails when the import succeeds. But the case can pass for the ambient/probe reason “the import never happened,” as shown above. Parent `python3 -B` did not create a false pass; child `python3` still wrote bytecode. `PYTHONPYCACHEPREFIX` did not look reachable through this scrub because it is not allow-listed. Read-only/noexec temp behavior is **NOT MEASURED**.

2. **Residue / collision?** Temp dirs leak per self-test run. I found no `.claude/hooks/_selftest-*` residue in the real repo after the run; `_fixture_hook` unlinks its hook and marker in `finally`. It does write into the real repo during normal self-test execution. Its pid-based name should not collide across separate mutation staged trees; same-process concurrent calls would share a pid, but I did not find a current concurrent caller.

3. **Attribution and duplicate substance?** Applied each relevant entry in staged copies:
```text
rc entry 16 constant removal: rc=1, [FAIL] bytecode case, 55/56
rc entry 17 call-site inline: rc=1, [FAIL] bytecode case, 55/56
surface entry 20 constant removal: rc=1, [FAIL] agreement + [FAIL] bytecode case, 57/59
surface entry 21 call-site inline: rc=1, [FAIL] bytecode case, 58/59
```
The two entries per file are not duplicates: constant removal checks the allowlist’s value; call-site inline checks that production code reads the constant. Neither strictly subsumes the other. Surface entry 20 remains confounded by the sibling agreement case, but entry 21 is clean.

4. **Anchor integrity?** The four relevant anchors each resolve once in the delivered tree. The new call-site anchors are not substrings of the constant-removal anchors, and I found no order dependency between the paired entries.

5. **Sibling claims?** The round-8 agreement case still means tuple equality between the two allowlists. The surface constant is multi-line and rc’s is one-line, but the imported tuple comparison still measures semantic agreement. The retargeted surface divergence entry still measures divergence; removing only surface’s key trips both the agreement case and the bytecode property.

**What I Tried To Refute And Could Not**

I could not refute the required self-test results, shard 5 mutation result, uniqueness of the new anchors, or the claim that the new call-site entries fail via the named case. I also could not make parent `-B` alone hide the defect; the child process still wrote bytecode.

| Severity | Aims At | Deliverable Or Instrument | Caused By Fold Itself? |
|---|---|---|---|
| Medium | Probe can pass when the hook import fails silently | Instrument | Yes |
| Low | Probe leaks temp directories | Instrument | Yes |

**Verdict: NOT CONVERGED**
