<!-- codex-review: model=gpt-6-astra -->

1. **Major — changing the import context hides live launches.** `scripts/check-fixture-git-isolation.py:359`, `:331`.

   The child strips `CI`, replaces HOME and argv, and invents the module name. Branches skipped under those conditions are not necessarily dead branches.

   **Reproduction:** place this in `scripts/x.py` in a temporary copy:

   ```python
   import subprocess, sys

   def self_test():
       import fixture_git
       with fixture_git.isolated():
           return 0

   if "--self-test" in sys.argv:
       subprocess.run(["git", "init", "-q", "build"])
       subprocess.run(["git", "config", "fixture.escape", "yes"])
   ```

   Master returns **1**; this branch returns **0**, including the script in its isolated population. Import it from another interpreter whose argv contains `--self-test`, with `GIT_DIR` pointing at a temporary victim: import exits **0**, and the victim gains `fixture.escape=yes`.

   Independently reproduced the same master-1/branch-0 escape with conditions on original HOME, `CI=true`, and the ordinary imported module name.

   **Fix:** stop treating one sampled context as proof of import-time inactivity. Either restrict and enforce permitted import-time behavior, or narrow the contract and BET to the measured context. Explicitly document these conditional launches; they are outside the stated dead-branch relaxation.

2. **Major — interpreter startup can prevent hook installation silently.** `scripts/check-fixture-git-isolation.py:330`, `:359`, `:361`.

   Inherited `PYTHONPATH` permits `sitecustomize` to run before `_CHILD`. An existing audit hook can veto installation without making `sys.addaudithook` raise to its caller.

   **Reproduction:** put this in a temporary `sitecustomize.py` and export its directory through `PYTHONPATH`:

   ```python
   import sys

   def veto(event, args):
       if event == "sys.addaudithook":
           raise RuntimeError("no additional hooks")

   sys.addaudithook(veto)
   ```

   Check a target that calls `os.system("git init …")` and `os.system("git --git-dir=<victim> config fixture.escape yes")` at import. Master returns **1**; this branch returns **0**, reports no launch, and the victim changes **during checking**.

   Separately, launches directly from `sitecustomize` and a temporary virtual environment’s `.pth` file changed the victim without being reported.

   **Fix:** start with `-I -S`, install and verify the hook before enabling any required external import paths. Tested that change in memory: the veto reproduction becomes refused, and all **84 real files still pass**. `PYTHONSTARTUP` did not escape in testing.

3. **Major — native calls launch processes inside the observed import without detection.** `scripts/check-fixture-git-isolation.py:314`.

   Auditing selected symbol lookups does not observe every native invocation.

   **Reproduction:** this macOS probe obtains `system` through libc’s `dlsym`:

   ```python
   import ctypes
   CMD = ["git", "init"]
   lib = ctypes.CDLL(None)
   lookup = lib.dlsym
   lookup.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
   lookup.restype = ctypes.c_void_p
   system = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p)(
       lookup(ctypes.c_void_p(-2), b"system")
   )
   system(b"git --git-dir=<temporary-victim> config fixture.escape yes")
   ```

   Master returns **1**; this branch returns **0**. The victim changes. Independently, CFFI’s `ffi.dlopen(None).system(...)` changed the victim during checking while the guard returned **0**.

   **Fix:** enforce or observe process creation outside the target interpreter if retaining the BET. More symbol names cannot establish that guarantee. LIMITS already acknowledges unaudited C extensions, but that exception contradicts the unrestricted BET being reviewed.

4. **Minor — the published guarantees exceed the measurement.** `scripts/check-fixture-git-isolation.py:140`; `docs/backlog.md:364`; `docs/dashboard-entries.md:18020`; PR #424 body.

   **Reproduction:** findings 1–3 produce green checks with actual launches. The dashboard additionally says no self-test can reach the real repository or personal settings, despite the acknowledged isolation escapes.

   **Fix:** describe successful checks as observations under the specific child context and observer. Carry the native-call, startup, conditional-context, and daemon-thread limitations into the BET and user-facing claims.

Verification completed in temporary copies:

- Guard suite **130/130**; watcher suite **88/88**.
- All **84** real files passed the import observer; **79** population scripts passed structural isolation checks. No delivered-script false refusal found.
- All **28 fixed probes**, including every r1/r2 shape, rerun through both guards; all refused here.
- **48/48 guard mutations** and **42/42 watcher mutations** killed; each named expected case appeared exactly once among failures.
- `EXPECTED_MUTATIONS` matches actual per-target counts and total: **2,354**.
- Real temporary-repository `--decide`, `--watching`, and `--clear` invocations matched pre-redesign behavior.
- Fork, multiprocessing fork, direct `_posixsubprocess`, ordinary ctypes lookup, atexit, and non-daemon-thread probes refused. Early exits and timeout returned **CANNOT CHECK**.
- Delayed daemon-thread escape reproduced; already documented. Symlinked `.py` checked; non-`.py` excluded.
- Repository unchanged.

VERDICT: NOT CONVERGED
