# Round 5 — `derived-mutation-total` (PR #455, backlog #359) — Claude adversarial half — NOT CONVERGED

Reviewed head `0eec9d38`, diff `8db213ae..HEAD` (F2's fix, two fixture-variation cases, two mutation entries
plus one rebound, the bound text). HOLD triage read `git diff origin/master...HEAD` (merge base `0de20abb`).

**The claim I was asked to refute:** "check-merge-ready can no longer exit with rc 0 or READY without a verdict
because of anything the working-tree check-plan-code.py does at import or during `pin_display`; and the stated
bound is honest."

**Result.** F2's fix holds for everything that RAISES. But Codex's exact F2 input, applied to the OTHER file
check-merge-ready imports in-process (`check-dashboard-entry.py`), still ends `main()` at **rc 0 with no verdict on
a head whose pin falls 5 -> 4**. That is the DEFER row's named failure observation. It is not fix-induced, and
master has the same hole. The non-raising sabotage inputs (`os._exit`, rebinding the caller) are honestly out of
scope, but neither script's bound text says so.

## Method

- **Driver.** `scratchpad/r5/driver.py` loads the REAL `scripts/check-merge-ready.py` and installs it as
  `sys.modules["__main__"]`, as a direct run does. It replaces only `_run` with a fake: gates pass, CI is green,
  mergeability is CLEAN. The fake's `git show` returns a base pin of 5 and a head pin of 4. It points
  `PINS_READER` at a scratch copy of the real `check-plan-code.py` with one attack appended. Then it calls
  `sys.exit(mod.main(["--pr", "15"]))`, the real entry's shape.
- **Isolation.** Each attack runs in its own subprocess, so the result is the real process exit code. The right
  answer for every input is **HOLD, rc 3**.
- **Control.** The unmodified reader gives `rc=3`, a HOLD verdict and 1 hold line.

## Findings

### F1 — High — the F2 class, in the sibling importer: `_dashboard_gate` lets a module-level `SystemExit` escape `main()` as rc 0

- **Where.** `scripts/check-merge-ready.py:464-477` (`_dashboard_gate`). Its call sites are `:1189` (the NO-REVIEW
  matcher in `main()`, guarded only by `except Exception`) and `:1141` (the escape cross-check, also
  `except Exception`).
- **Fix-induced: no.** It is pre-existing on master. It is the same class as r4 Codex F2, which r4 fixed for one
  importer only. That makes it instance-not-class.

**Input.** Append Codex's exact F2 text to `scripts/check-dashboard-entry.py`, in a scratch `git archive` of each
revision:

```python
if __name__ != "__main__":
    raise SystemExit(0)
```

**Measured through the real `main()`** (scratch trees `r5/t-HEAD`, `r5/t-origin_master`):

| tree | input | rc | verdict line | HOLD lines |
|---|---|---|---|---|
| HEAD `0eec9d38` | unmodified (control), plain body, pin 5 -> 4 | **3** | HOLD | 1 (the pin fall) |
| HEAD `0eec9d38` | the append, body `NO-REVIEW: x`, pin 5 -> 4 | **0** | *(none)* | 0 |
| HEAD `0eec9d38` | the append, plain body, pin 5 -> 4 | **0** | *(none)* | 0 |
| origin/master `0de20abb` | the append, body `NO-REVIEW: x` | **0** | *(none)* | 0 |

**Why it matters here.**
- On HEAD it defeats the new falling-pin HOLD as well as the waiver HOLD. `pin_pair` succeeds at `:1180`, then
  `granted_escapes` at `:1189` imports the dashboard gate. The `SystemExit` passes `except Exception`, and the
  process exits 0 before `hold_reasons` runs.
- The house rule merges on rc 0 (`check-merge-ready.py --pr N` READY ⇒ squash).
- This is literally the DEFER row's bet and named failure observation: "no input ends check-merge-ready without
  a verdict or with rc 0 on a falling display pin … Named failure observation: any such input."

**The repair** (one rule, one place):
- Add one helper, `_import_sibling(name, module_name)`, holding r4's catch: `BaseException` except
  `KeyboardInterrupt`, then `sys.modules.pop`, then raise.
- Use it from both `_dashboard_gate` and `_pins_reader`.
- Wrap the `exemption_reason` CALL the way `pins_at` wraps `pin_display`, because the call can raise
  `SystemExit` too.
- `main()`'s `:1189` handler then reports CANNOT RUN.
- Mutation entries mirror r4's two.

**If the coordinator prefers to defer it,** the deferral is honest only with the DEFER row scored against this
input, because master is equally exposed. I recommend the fold: it is about ten lines, and it is the class the
r4 fix already named.

### F2 — Low — the bound text does not state the non-raising class

- **Where.** `scripts/check-merge-ready.py:848-851` and the `_pins_reader` docstring (`:877-884`, "FAILS CLOSED").
  Also `scripts/check-plan-code.py:2856-2857`.
- **Fix-induced: yes.** The text was written in r4.
- **What the text says.** "Anything its import or its reader RAISES is CANNOT RUN". That is accurate. Read as the
  claim under test ("anything … DOES"), it is false. The coordinator's r4 doc has a further bound, "a working-tree
  `pin_display` that returns plausible wrong numbers is not caught; same trust as its own source". That sentence
  appears in neither script.

**Inputs, each appended to a scratch copy of the real reader and run through the real `main()`:**

| attack (module level of `check-plan-code.py`) | rc | verdict printed | class |
|---|---|---|---|
| control (unmodified) | 3 | HOLD | — |
| `os._exit(0)` (guarded `__name__ != "__main__"`) | **0** | none | deliberate |
| `atexit.register(os._exit, 0)` | **0** | HOLD printed, rc says READY | deliberate |
| `raise ValueError` after `atexit.register(os._exit, 0)` | **0** | **CANNOT RUN** printed, rc 0 | deliberate (Q3) |
| thread started at import: `sleep(1); os._exit(0)` | **0** | HOLD printed | deliberate |
| `signal.setitimer` + SIGALRM handler `sys.exit(0)` | **0** | none (escapes `main()` outside the try) | deliberate |
| SIGUSR1 handler `sys.exit(0)` fired at `main()`'s next `print` | **0** | none | deliberate |
| `sys.modules["__main__"].pin_falls = lambda o, n: []` | **0** | READY | deliberate |
| `sys.modules["__main__"].hold_reasons = lambda *a, **k: []` | **0** | READY | deliberate |
| `sys.modules["__main__"].final_verdict = lambda c, l, h: (0, "READY …")` | **0** | READY | deliberate |
| `sys.exit = lambda *a: None` | 3 | HOLD | refuted: `sys.exit(main(...))` binds the callee BEFORE `main()` imports the reader |
| `__del__` raising `SystemExit(0)` | 3 | HOLD | refuted: "Exception ignored while calling deallocator" |
| `atexit.register(lambda: sys.exit(0))` | 3 | HOLD | refuted: "Exception ignored in atexit callback" |
| a non-daemon thread sleeping 5s | 3 | HOLD (late) | delay only |
| `sys.stdout.close()` | 1 | none (traceback) | fails closed (rc 1 = NOT READY) |
| `os.close(1)` | 120 | none | fails closed |
| `raise KeyboardInterrupt` | -2 (SIGINT) | none | fails closed (Q2) |

**Ordinary edit or deliberate sabotage?** Every rc-0 row needs code whose only purpose is to kill the process or
rebind the caller. None arises from an ordinary helper edit:
- an `argparse` at import exits via `SystemExit` and is caught;
- a missing import raises `ImportError` and is caught;
- a cleanup `atexit` that raises is ignored by CPython.

**The trust is not new.**
- `check-merge-ready.py` is itself working-tree PR code, run from the PR's worktree. Adding the same `os._exit(0)`
  there is an ADDED line, which `failure_path_removals` does not see.
- Master already executes a working-tree sibling in-process (`_dashboard_gate`, F1).
- I judge these inputs out of scope, honestly.

**The text should say so.** Suggested sentence, in both bound blocks: "Code that ends the process without raising
(`os._exit`, an `atexit`/thread/signal hook) or rebinds this script's globals is not caught. It is the same trust
this script extends to its own source, which the same PR can edit."

### F3 — Info — two lines of the F2 fix are unwitnessed and unobservable

- **Where.** `scripts/check-merge-ready.py:894` (`sys.modules.pop(...)`) and `:890` (the `mod.pin_display` probe).
- **Fix-induced: yes.**
- **Measured.** In a scratch archive of HEAD, deleting either line leaves `--self-test` at **234/234**.
- **Why that is safe, and why it means nothing is guarding it.**
  - The probe is redundant: `pins_at`'s own `BaseException` catch turns the later `AttributeError` into CANNOT RUN.
  - The pop is unobservable in production. Nothing imports `_cpc_for_merge_ready` by name, and `lru_cache` does not
    cache a raised call, so a failed import is never reused. (Q3, below.)
- **Recommendation.** Delete them, or keep them and do not count them as witnessed behaviour. Not blocking.

## Asked questions

**Q1 — inputs.** See the F2 table. Six input kinds give rc 0. All six are deliberate, and all are out of scope
honestly for the reason given in F2. The text does not say that, which is F2. The one ordinary-equivalent input,
Codex's own F2 shape, still reaches rc 0 through the OTHER importer: F1.

**Q2 — excluding KeyboardInterrupt is sound.**
- A module-level `raise KeyboardInterrupt` gives `rc=-2` (Python re-delivers SIGINT): no verdict, never 0 or 3, so
  nothing merges on it.
- Catching it would turn an operator's Ctrl-C into a CANNOT RUN verdict that nobody asked for.
- The only cost is a traceback in place of a verdict line. That is fail-closed.

**Q3 — sys.modules cleanup.**
- **Can a half-built module be REUSED? No.**
  - `lru_cache` does not memoise a raised call, so a failed import re-executes on the next call.
  - In `main()`, the first failure propagates through `pin_pair` to `:1182`, and nothing calls the reader again.
- **The pop is cosmetic** (F3).
- **The real leak is not the `sys.modules` entry. It is the half-built module's SIDE EFFECTS**, which survive the
  catch: `atexit` registrations, threads, signal handlers, and globals it rebound. Measured: a module body that
  registers `atexit(os._exit, 0)` and then raises prints **CANNOT RUN** and exits **rc 0**. No `except` can undo
  that. It belongs to F2's deliberate class and should be named in the bound.
- **Minor, self-test only.** Distinct `src` paths share the module name `_cpc_for_merge_ready`. A later
  load overwrites the earlier one's `sys.modules` entry. The cached module objects still work, because
  `pin_display` does no by-name lookup.

**Q5 — the suites, foreground, in `wt-t6`** (`node_modules` was already symlinked):
- `python3 scripts/check-merge-ready.py --self-test`: **234/234 passed** (1.7s).
- `python3 scripts/check-plan-code.py --self-test`: **281/281 passed** (8.6s).
- The worktree is unchanged apart from this file.

## HOLD triage

`check-merge-ready`'s own `failure_path_removals` was run over the real `gather` of `origin/master...HEAD`. It
flags 5 lines in `check-merge-ready.py` and 1 in `check-plan-code.py`. `pin_falls(pin_pair(...))` is `[]`: no pin
falls. Each line, quoted from `git diff origin/master...HEAD`:

### check-merge-ready.py, line 1 of 5 — FALSE HOLD

```
-        code, line = 2, (f"CANNOT RUN — could not read the branch's diff ({exc.__class__.__name__}: {exc}), so the house "
+        code, line = 2, (f"CANNOT RUN — could not read the branch's diff or its mutation pins "
+                         f"({exc.__class__.__name__}: {exc}), so the house "
```

- Still `code = 2`, still CANNOT RUN; only the message wording changed.
- The guarded `try` now also covers `pin_pair` (`+        pins = pin_pair(_run, BASE_REF)`), so this failure path
  covers MORE than before.

### check-merge-ready.py, lines 2 and 3 of 5 — FALSE HOLD

```
-          [r.split(":")[0] for r in hold_reasons([G], _398, None, None, True)],
+          [r.split(":")[0] for r in hold_reasons([G], _398, None, None, True, pins=({}, {}))],
-          hold_reasons(["worker/run.ts"], "", "f00d", "f00d", False), [])
+          hold_reasons(["worker/run.ts"], "", "f00d", "f00d", False, pins=({}, {})), [])
```

- `pins` became a required keyword-only argument, so a caller cannot skip the comparison.
- Each case passes a no-fall pair and keeps its expected value unchanged: `["loosens a gate", "relied on a
  waiver"]` and `[]`.
- Only the call shape changed.

### check-merge-ready.py, lines 4 and 5 of 5 — FALSE HOLD

```
-          has(H([PC], DF(PC, '-    "scripts/a.py": 30,')), "scripts/a.py (30) is removed"), True)
+          has(pin_falls({"scripts/a.py": 30}, {}), "scripts/a.py (30) is removed"), True)
-          has(H([PC], DF(PC, '-    "scripts/b.py": 12,', '+    "scripts/c.py": 12,')), "scripts/b.py (12) is removed"), True)
+          has(pin_falls({"scripts/b.py": 12}, {"scripts/c.py": 12}), "scripts/b.py (12) is removed"), True)
```

- **The subject was replaced.** The diff-line proxy that `H(...)` drove was retired for the display read (r3).
  These cases now drive the pure rule that decides "removed", and they assert the same strings.
- **The wiring is still witnessed elsewhere:**
  - `hold_reasons` → `out.extend(pin_falls(*pins))` by "⭐ main() HOLDS a READY PR whose head's pin falls, rc=3";
  - removal through `pin_pair` by "a head with no check-plan-code.py at all removes every pin" (`:1938-1941`);
  - the `is removed` branch by its mutation entry (`mutations/check-merge-ready.json:479`).
- No failure path was weakened.

### check-plan-code.py, line 1 of 1 — FALSE HOLD

```
-                 _evT.files["scripts/thing.py"]["tail"].strip(), "[FAIL] the value is one")
+                 _evT.files.get("scripts/thing.py", {}).get("tail", "").strip(), "[FAIL] the value is one")
```

- The expected value is unchanged.
- With a missing key, the old line crashed the suite (KeyError, non-zero); the new line returns `""`, which fails
  the comparison, so the case goes red (non-zero).
- Both fail. The new one fails as a NAMED red case, which is stronger.

**HOLD verdict: both "loosens a gate" lines are FALSE HOLDs.** All six rewritten lines change text or call shape
only, and none removes or softens a failure.

## Verdict

**NOT CONVERGED** — one High (F1), one Low (F2), one Info (F3).
- **F1 (High, not fix-induced, pre-existing on master)** is the F2 class at the second in-process importer. It
  reaches rc 0 with no verdict on a falling pin at this head, which is this round's DEFER-row failure observation.
  A shared fail-closed import helper fixes the class.
- **F2 (Low)** is a sentence in two bound blocks.
- **F3 (Info)** is optional.
