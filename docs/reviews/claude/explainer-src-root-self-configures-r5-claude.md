# Adversarial review — round 5 — Claude half — `explainer-src-root-self-configures` (PR #295)

## Verdict

**FINDINGS.** There is **one new High**. No Blocking.

I do **not** reproduce Codex's CONVERGED. Every check Codex reported, I re-ran and reproduce —
its work is correct as far as it goes. The High is in a place Codex did not look and four rounds
did not look: the **`EXAMINED_KEYS` pins added in r2's remedy are dead code**. Both entries this
branch adds are **duplicate dict keys**, silently overwritten at parse time by pre-existing
entries later in the same literal. The seven pinned parameters — including `repo_root.start`
(the r1 H1 remedy) and `src_root_help.pidfile` (the r2 High seam) — do not exist at runtime.

This is the round-4 pattern again: the production redesign is sound; the defect is in the
**guards proving it**.

---

## Findings

### [High] Both `EXAMINED_KEYS` entries this branch adds are duplicate dict keys, and are silently discarded

**Where:** `scripts/check-fixture-variation.py:281` and `:290` (added by this branch),
overwritten by the pre-existing `:516` and `:476`.

**What:** the branch adds, near the top of the `EXAMINED_KEYS` literal:

```python
    'page_chrome.py': (
        'chrome_bar.restart',
        'repo_root.start',
        'restart_commands.root',
        'restart_control.root',
    ),
    # ⟳ 2026-09-15, PR #295 r2 High. `src_root_help.pidfile` is the seam that made the recovery
    # command falsifiable …
    'explainer-serve.py': (
        'src_root_help.env_value',
        'src_root_help.pidfile',
        'src_root_help.repo',
    ),
```

The same literal already contains `'explainer-serve.py'` at `:476` and `'page_chrome.py'` at
`:516`. In a Python dict literal the **last** binding for a repeated key wins, so both new
tuples are discarded before the module finishes importing.

Measured on the branch as shipped:

```
$ python3 -c "... exec check-fixture-variation.py ...; print(m.EXAMINED_KEYS['page_chrome.py'])"
('assert_wired.page', 'assert_wired.where', 'chrome_bar.refresh', 'chrome_bar.slug',
 'chrome_bar.when', 'has_control.page', 'missing_palettes.page', 'provenance.now',
 'provenance.root', 'stamp.when')
```

No `repo_root.start`. No `chrome_bar.restart`. No `restart_commands.root`. No
`restart_control.root`. The `explainer-serve.py` value is likewise the old 17-key tuple with
**no `src_root*` key at all** — so `src_root`, `src_root_help` and `_gone_checkout_help` are
entirely outside this guard's field of view.

AST sweep of the whole repo, confirming the class is confined to these two additions:

```
scripts/check-fixture-variation.py:272  DUPLICATE 'page_chrome.py' x2 at lines [281, 516]
scripts/check-fixture-variation.py:272  DUPLICATE 'explainer-serve.py' x2 at lines [290, 476]
total duplicate-key sites: 2
```

**Why it matters:** the pins are not decoration — the branch's own comment says exactly what
they are for:

> `repo_root.start` is the r1 H1 REMEDY: it exists so the function can be falsified at all, and
> deleting it takes `repo_root` out of this guard's field of view entirely while `analyse` stays
> silent, because the pin is one-directional.

The pin is the thing that was supposed to stop that. It does not run. **Measured, branch as
shipped** — delete `repo_root`'s `start` parameter (exactly the regression the pin names):

```
fixture variation OK — 531 parameter(s) examined across 51 file(s); …
check-fixture-variation rc=0
```

Silent. Same for removing `src_root_help`'s `pidfile` parameter — `rc=0`, silent. The parameter
count moves 532 → 531 and nothing asserts it.

With the pins merged into the surviving entries instead, the same deletion fires:

```
FAILED — 1 parameter(s) never varied by any case:
  ✗ page_chrome.py: `repo_root.start` was examined and is NOT any more — its function was
    renamed, made private, or lost its last call site. …
rc=1
```

So the mechanism works; only the binding is lost. Nothing in the repo catches this: the guard's
own `analyse` is green, `population_drift` (`:877`) and the self-test population case (`:1474`)
compare **name sets** only — and a collapsed duplicate leaves the name set unchanged — so all
53 keys still reconcile. I ran the thirteen repo-level guards and every one is green with the
pins dead.

This is the branch's signature class one level up: a remedy that *reads* as coverage, asserted
in a comment, with nothing executing it. The r2 finding it answers is therefore still open.

**Suggested fix (hypothesis, not verified beyond the run above):** delete the two new entries
and merge their members into the existing `'page_chrome.py'` (`:516`) and `'explainer-serve.py'`
(`:476`) tuples, keeping the new comments at the surviving site. I ran exactly this for
`page_chrome.py` — guard stays green, and the falsifier fires on the deletion, as quoted above.
Separately, and more durably: `check-fixture-variation.py --self-test` has no case asserting
that its own three ratchet literals contain no repeated key. An `ast`-based case over
`EXAMINED_KEYS` / `KNOWN_UNVARIED` / `EXEMPT` would have caught this at the moment it was
written, and would generalise — the repo sweep above shows the check is cheap and currently
finds exactly these two.

---

### [Medium] `respawn()`'s failure message asserts a SIGTERM that was never sent, and prints `pid None`

**Where:** `scripts/explainer-serve.py:1327-1336` (new in this branch).

**What:**

```python
    if pid_alive(old_pid):
        assert old_pid is not None
        os.kill(old_pid, signal.SIGTERM)
    deadline = time.monotonic() + 20
    while port_busy(HOST, PORT) and time.monotonic() < deadline:
        time.sleep(0.1)
    if port_busy(HOST, PORT):
        note = (f"{_dt.datetime.now():%Y-%m-%d %H:%M:%S} NOT RESTARTED — port {PORT} was "
                f"still busy 20s after SIGTERM to pid {old_pid}. Something else may be "
                f"holding it; check with: lsof -nP -iTCP:{PORT} -sTCP:LISTEN\n")
```

The kill is **conditional**; the message that names it is **unconditional**. Measured live, on a
real server, with the pidfile removed while the server was up:

```
2026-09-15 11:05:35 NOT RESTARTED — port 7399 was still busy 20s after SIGTERM to pid None.
```

and with a stale pidfile (`999999`):

```
… still busy 20s after SIGTERM to pid 999999. …
```

In both runs `pid_alive` was False, so **no signal was sent to anything**.

**Why it matters:** this is the class the branch exists to dissolve — *the reason for a failure
inferred rather than carried* — reached in new code one file over from where it was fixed four
times. `_gone_checkout_help`'s docstring states the rule this violates:

> ⛔ IT DESCRIBES WHAT WAS OBSERVED AND DOES NOT NAME A CAUSE — r3 M3. This text used to say the
> checkout "has moved or been deleted", which is a diagnosis the code cannot make…

and `page_chrome`'s `_why` fix, cited in the same docstring: *"A failure message that names the
wrong cause sends the next reader to the wrong place."* Here the message names an **action the
code did not take**. The reader's real problem is "the pidfile does not identify the running
server, so nothing was asked to stop" — a different diagnosis with a different remedy from "the
server ignored SIGTERM". A stale or absent pidfile is ordinary (a `kill -9`, a crash, a cleared
home), and I hit it in two of four trials. `pid None` in user-facing output also just reads as a
bug.

I considered High and did not go there: the refusal itself is correct and safe, the failure is
loud, it is written to `RESTART_LOG`, and the `lsof` hint is accurate and leads to the truth
fairly quickly. Nothing in the suite asserts this message — the three `respawn` cases cover
ordering and boundedness only.

**Suggested fix (hypothesis):** carry the observation rather than restate it — e.g. record
whether a signal was sent and to what, and branch the note on it: *"port N still busy 20s after
SIGTERM to pid P"* when one was sent, versus *"the pidfile named pid P, which is not running, so
nothing was signalled; port N is held by another process"* when it was not. Same shape as
`SrcRoot.reason`.

---

### [Low] A recorded "second, independent reason" is false, and the comment calls it the stronger one

**Where:** `scripts/check-plan-code.py:3170-3174`.

**What:**

```python
    # ⟳ r2 review supplied a SECOND, independent reason this entry could never have been
    # admitted, and it is the stronger one: removing `--` reddens FIVE cases, so `expect`
    # would be refused for matching more than one.
```

**Why it matters:** the refusal rule is per-`expect`-string cardinality over red **case names**,
not the number of red cases a mutation produces — `check-plan-code.py:1287`:

```python
        unnamed = [(w, [f for f in fails if w == f]) for w in wants]
        unnamed = [(w, m) for w, m in unnamed if len(m) != 1]
```

Removing `--` does redden five cases, but each has a distinct name, so an `expect` naming one of
them matches exactly one. I ran the real harness on a manifest carrying that entry with a
distinct (two-line) anchor so the first reason could not fire:

```
manifest entries now: 14
OK = True
```

Admitted, no complaint. The **first** reason given (shared edit anchor → `repeats the edit
anchors of an earlier entry`) is real and is what actually refused it; I confirmed the rule
exists at `:999`. Only the "stronger", "independent" second reason is wrong. Non-executable, so
nothing ships broken — but a future author would read it and decline to write a valid entry. It
also sits one screen from `:997`, which says *"a comment asserting a property the code lacks is
this branch's signature defect"*.

**Suggested fix (hypothesis):** delete the r2 paragraph, or restate it as what is true — that
`expect` matches one case name exactly, so a multi-case mutation is admissible and the shared
anchor was the sole bar.

---

### [Low] The stated blocker for giving `explainer-serve.py` a mutation manifest is stale, and this branch removed the other half of it

**Where:** `scripts/check-plan-code.py:914-925` (text pre-existing; the situation is this
branch's).

**What:** the comment explains why `explainer-serve.py` and `gen-backlog-page.py` have no
manifest:

```python
    # then removed, because `mutate_delivered` copies ONLY `scripts/` into its temp tree
    # while BOTH suites read repo files outside it — `gen-backlog-page --self-test` opens
    # `docs/backlog.md`, and explainer-serve's new source-coverage case stats `docs/`.
```

**Why it matters:** `mutate_delivered` has not copied only `scripts/` since HARNESS_TREE
(2026-09-07):

```
HARNESS_TREE = ('scripts', 'supabase', 'docs', 'node_modules/typescript',
                '.claude/hooks', '.github/workflows')
```

I staged it and ran both suites inside the staged tree:

```
stage_tree -> complete
explainer-serve.py: rc=0  self-test: 131/131 passed
gen-backlog-page.py: rc=0  165/165 passed
```

Both run green. The *other* stated obstacle — `explainer-serve.py`'s unparseable failure line —
is what **this branch fixed**, and it paid `page_chrome`'s ratchet 11→13 "citing exactly that
invisibility". So both obstacles are now gone while the comment still records them as live. Left
as-is, it is a documented reason not to do work that is no longer blocked.

**Suggested fix (hypothesis):** update the comment to say the blocker was resolved (HARNESS_TREE
+ the `[FAIL] ` repair), and file the manifest as follow-up work rather than carrying it as a
standing impossibility. Not work for this branch.

---

## Considered and deliberately not filed

- **`POST /_restart` has no Origin/CSRF check.** Any page in the user's browser can trigger it
  (a bodyless cross-origin POST is a simple request; the server ignores `Origin`). But
  `/regenerate` — which runs generator subprocesses — is already reachable the same way, so the
  class is pre-existing and `/_restart` is the *least* powerful of the three POST routes. The
  `_send` comment at `:1032` is correct that the absent CORS header stops cross-origin *reads*;
  it is simply silent about triggering. Not introduced here, and not worth a finding on this
  branch. Worth a backlog item on its own if anyone wants one.
- **Unread request body on `/_restart` + keep-alive desync.** Not reachable:
  `protocol_version` is unset, so HTTP/1.0 — the connection closes per response.
- **`scripts/subject_status.py --self-test` is RED (16/17)** — "the parked schema reports
  UNSHIPPED, not SHIPPED". **Not this branch.** The file is unchanged here, `RUNTIME_DIRS` is
  `lib, app, components, worker, supabase/migrations` (neither `docs/` nor `scripts/`), and the
  cause is `supabase/migrations/0027_stable_blob_addressing.sql` from PR #155 — the parked schema
  shipped and the case still asserts it has not. Pre-existing; flagging it for the roadmap, not
  against this PR.

---

## What I reproduced of Codex's round-5 half

All of it. Re-run independently, not taken on trust:

| Codex's claim | My result |
|---|---|
| baselines 131/131, 76/76 | reproduced (`explainer-serve` 131/131, `page_chrome` 76/76, `gen-dashboard` 325/325) |
| `_probe_with` restores `REPO` in `finally` | reproduced — forced `src_root` to raise under the fake repo: exactly 2 cases red, every `REPO`-dependent case elsewhere still green |
| denylist restores after `src_root_help` raises; later cases do not cascade | reproduced — forced a raise mid-render: 21 `[FAIL]` lines, **0 tracebacks, 0 unrelated reds** |
| arm coverage complete under denial | reproduced, and tested each arm **separately** — a `Path.exists()` probe placed only in `_gone_checkout_help`'s non-empty-`env_value` arm, only in its empty arm, and only in `src_root_help`'s BAD_ENV arm each go red via the class falsifier. The r4 H1 shape is gone |
| the three new `src_root` cases kill `fallback_ok = True` | reproduced — 129/131, and both reds are attributable |
| `rev_before`'s exception-as-value does not make the revision cases vacuous | reproduced by inspection + the suite's own measurement |

Codex did not examine the `EXAMINED_KEYS` pins, the `respawn` failure path, or the restart
control end-to-end. That is where the findings are.

## What else I ran

- **All 13 repo-level guards: green.** `check-fixture-variation`, `check-ratchet-contract`,
  `check-selftest-counts`, `check-docs`, `check-theme-token-coverage`,
  `check-explainer-delivery`, `check-anchors`, `check-vocabulary-collisions`,
  `check-review-rounds`, `check-dashboard-entry`, `check-plan-file-tags`,
  `check-backlog-closure`, `check-producer-enumeration` — all `rc=0`.
  ⚠ They are green **with the High's pins dead**, which is the point of that finding.
- **Every `scripts/*.py --self-test`:** the only red is `subject_status.py` (pre-existing, above).
  Three scripts have no `--self-test` at all (`codex-frontier-model`, `session-skill-report`,
  `skill-usage-audit`) — unchanged, and outside the ratchet contract's population.
- **The full CI mutation gate, `check-plan-code.py --mutate .`, run locally to completion:**
  ```
  OK — delivered scripts mutated: 45 file(s), 645 mutation(s), 645 killed,
       645 attributed to the case each names, 0 survivor(s)
  ```
  This matches the branch's declared `sum(EXPECTED_MUTATIONS.values()) == 645`.
- **Both new mutation-manifest entries, over a control proved green first (76/76):**
  - `repo_root loses its git resolution` → 75/76, red via *"from a linked worktree, repo_root
    resolves to the MAIN checkout"* — the case it names.
  - `the pasted cd stops being shell-quoted` → 72/76, red via *"`cd` parses to exactly one
    operand for 'some repo'"* — the case it names.
- **Task 4 — the `FAIL: ` → `[FAIL] ` change.** Nothing else in the repo parsed the old shape:
  the only other `FAIL: ` in this file is `:1280`, the daemon's "forked pid but nothing is
  listening" message, which no parser reads; the `docs/` hits are historical review documents
  quoting past output. And `parse_fail_names` now attributes for this file — I mutated
  `fallback_ok = REPO.is_dir()` → `= True` and fed the real output to the real function:
  ```
  parse_fail_names -> ['src_root: a missing fallback is MISSING_FALLBACK, root None, fallback_ok False',
                       'src_root: a bad env value ALSO records that the fallback was missing']
  ```
  The r4 mutation that survived at 128/128 is now killed **and** visible.
- **The restart control, end-to-end, on an isolated copy and port** (a live server is running on
  7391 — I did not touch it):
  - `POST /_restart` (empty body) → `200 {"ok": true, "pid": 28089}`; the outgoing server kept
    answering `/_alive` for ~8 more polls, then a gap, then `{"pid": 28624}`. This is direct
    confirmation of the design's central claim — *"success is a different pid, never merely a
    response"* — and of why polling for responsiveness would have reported a restart that never
    happened.
  - `--restart` while running → new pid, `rc=0`. While stopped → starts, `rc=0`. The pasted
    instruction's load-bearing claim ("it works whether or not the server is up") holds.
  - Pages generated for real carry the control, and `cd -- <root>` names the resolved main
    checkout. Generated pages go to `~/explainers/` and are untracked, so the absolute path does
    not reach git.

## What would have had to be true for me to converge

That the `EXAMINED_KEYS` additions bound at runtime. They read correctly, they are in the right
file, they name real parameters, the guard is green, and every self-test and population check
reconciles — the entry is invisible to inspection and to every gate. I found it only by
instrumenting `analyse()` on `page_chrome.py` and noticing the pinned tuple it returned was the
*old* one.
