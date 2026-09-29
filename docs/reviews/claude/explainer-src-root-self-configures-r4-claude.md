# Adversarial review — round 4 — CLAUDE half — `explainer-src-root-self-configures` (PR #295)

Subject: `d94db572` (the redesign) + `87a4ebf2` (the r4 Codex fixes). Everything below was measured
by mutating a throwaway copy of the tree and running `--self-test`; no claim here rests on reading.

Control, unmutated, `HOME` redirected: **128/128 passed, rc=0**. `page_chrome.py --self-test`
**76/76**. `check-fixture-variation`, `check-ratchet-contract`, `check-selftest-counts`,
`check-gate-falsifiability`, `check-guard-coverage` — `--self-test` OK and live run rc=0, all five.

## Verdict

**FINDINGS** — 1 High, 3 Medium, 1 Low. **None of them is the class.** All five are in the
instrument or in coverage; the deliverable is clean, and I believe it is clean structurally rather
than by luck. See the mandate-1 section, which is the part of this document that matters.

---

## Mandate 1 — is the class gone, or relocated?

**GONE from production code. Not relocated.** I tried to find it relocated and could not.

The class: *the reason for a failure is INFERRED rather than CARRIED.*

Three independent lines of evidence.

**(a) By reading, at every site.** `src_root_help` (`:514-555`) and `_gone_checkout_help`
(`:558-588`) draw every value from `observed.*`, the `pidfile` parameter, or the module constant
`SRC_ROOT_ENV` — which is a *name*, not a read. There is no `os.environ`, no `.is_dir()`, no
`__file__`, no `REPO`, no `SCRIPTS` anywhere in either body. The caller (`:1111-1119`) takes one
observation and passes it:

```python
observed = src_root()
root = observed.root
if root is None:
    body = src_root_help(observed)
```

Nothing is re-probed between the decision and the render. That is the whole architectural claim, and
it holds.

**(b) By a falsifier strictly stronger than the one shipped.** I built the falsifier the shipped one
should be — the existing 13 `Path` methods, *plus* `os.stat/lstat/access/listdir/scandir/open/
readlink/getcwd/statvfs`, *plus* `builtins.open`, *plus* the raising `os.environ`, *plus* a third
fixture so all three renderable arms are exercised — and ran the **unmutated** code under it:

```
=== widened falsifier + third arm fixture | NO mutation ===
  rc=0   self-test: 128/128 passed   traceback=False
```

Production renders every arm with the filesystem and the environment fully denied. That is a real
result, not a restatement of the author's: it passes a test the branch does not yet contain.

**(c) By trying to smuggle the class back in.** Nineteen mutations. Every re-derivation I injected
into production was caught by *something* — the two that survived the whole suite survived because
of gaps in the guard (findings 1 and 2), not because production had a second reader. Notably the
environment half is now airtight: `os.getenv`, `os.environ.get`, `dict(os.environ)`,
`subprocess(env=dict(os.environ))` and `pathlib.Path.home()` all die through the class case, each
naming its exact route. The `_Forbidden` `copy`/`__iter__`/`__len__` additions are doing real work.

**What would have had to be true for me to find the class still present:** a renderer reaching past
`observed` for any of {the env var, the fallback's state, a path derived from `__file__`/`cwd`/a
module global}. I mutated each of those five routes in turn into both renderers. The three that
represent the historical defects (`Path(__file__).parent`, `SCRIPTS`, `REPO`) are all killed by
`help: every emitted command parses to the real script path` — so even the paths the class falsifier
misses are covered by a property case, just not by the case that advertises the class.

**The honest caveat.** The redesign removed the class from the *deliverable*, and for the second
round running the surviving defects are in the *guard that proves it*. Finding 1 is literally the
r4 Codex finding one fixture over — a class falsifier reporting the class intact while it is
violated — which makes this the **sixth** instance of the half-covered-guard shape and the **third**
inside the guards written to stop it. I do not think that argues for another redesign; the
production shape is right and the remaining work is bounded and mechanical. But it should be named
plainly rather than filed as polish.

---

## Findings

### [High] The class falsifier never renders one of the three arms — and a probe on its own denylist survives there

**Where:** `scripts/explainer-serve.py:1801-1805`

**What:**

```python
_obs_bad = SrcRoot(None, "BAD_ENV", "/nope", root, True)
_obs_gone = SrcRoot(None, "MISSING_FALLBACK", "", root, False)
case("the help renders with NO environment and NO filesystem — it carries, not re-derives",
     lambda: _renders_without_the_world(_obs_bad)
             and _renders_without_the_world(_obs_gone))
```

There are three renderable arms, not two. `_gone_checkout_help`'s `why` (`:576-580`) is a
conditional on `observed.env_value`:

```python
why = (f"{SRC_ROOT_ENV} is set to {observed.env_value!r} and the fallback "     # arm 2b
       f"{observed.fallback} is not a readable directory"
       if observed.env_value else
       f"{SRC_ROOT_ENV} is unset and the fallback {observed.fallback} is not "  # arm 2a
       f"a readable directory")
```

`_obs_bad` reaches the script arm; `_obs_gone` reaches arm 2a. **Nothing reaches arm 2b** — which is
the arm r2's Medium added, the newest code in the function.

**Why it matters:** MEASURED. `observed.fallback.exists()` — and `exists` is the *second entry* of
`_PROBES` — inserted into arm 2b:

```
=== ARM-2b: Path.exists in the stale-env gone arm ===
  rc=0   self-test: 128/128 passed   [FAIL] lines=0
  CLASS falsifier caught it: NO
```

The identical probe in the sibling arm 2a:

```
=== ARM-2a: Path.exists in the unset gone arm ===
  rc=1   self-test: 127/128
  [FAIL] the help renders with NO environment and NO filesystem … AssertionError:
         src_root_help called Path.exists() — it must carry, not re-derive
```

So this is not a denylist gap — the denylist names the exact probe and is powerless, because the
code holding it is never executed. A full third of the render surface is outside the falsifier while
the case name asserts the whole property. That is the r4 Codex finding reproduced with a different
cause, and it is the higher-severity of the two because it defeats *any* future strengthening of
`_PROBES`.

**Suggested fix** (hypothesis — but I ran it, and it kills the mutation above):

```python
_obs_stale = SrcRoot(None, "BAD_ENV", "/stale", root, False)
case("the help renders with NO environment and NO filesystem — it carries, not re-derives",
     lambda: all(_renders_without_the_world(o)
                 for o in (_obs_bad, _obs_gone, _obs_stale)))
```

Worth stating in the comment *why there are three*, since the arm count is the thing that was wrong.

---

### [Medium] The denylist covers `pathlib.Path` only — the whole `os` module is an open road

**Where:** `scripts/explainer-serve.py:1780-1800`

**What:**

```python
_PROBES = ("is_dir", "exists", "is_file", "stat", "lstat", "iterdir", "glob",
           "open", "read_text", "read_bytes", "resolve", "samefile", "owner")
```

with the comment: *"Every probing entry point a renderer could reach is named; a new one is a gap,
and naming them here is the only place a reader can see the boundary."*

**Why it matters:** the comment is false as written, and the case name still says "NO … filesystem".
Measured, each inserted at the top of `_gone_checkout_help` — an arm the falsifier *does* reach:

| Mutation | Suite | Class case |
|---|---|---|
| `os.path.isdir(str(observed.fallback))` | **128/128 green** | NO |
| `os.path.exists(str(observed.fallback))` | **128/128 green** | NO |
| `os.access(str(observed.fallback), os.R_OK)` | **128/128 green** | NO |
| `os.stat(str(observed.fallback))` | 123/128 | **NO** — killed only incidentally |
| `os.scandir(...)` / `os.listdir(...)` | 123/128 | **NO** — killed only incidentally |

Three re-derivations survive the entire suite. The `os.stat`/`scandir`/`listdir` rows are worse than
they look: the class case passes, and the five red cases are red only because the fixture paths
(`/tmp/another checkout`, `/tmp/gone`, …) happen not to exist, so a raise leaks out. Point those
fixtures at real directories and those mutations go green too. Nothing there is asserting a
property.

Would a real implementer write these? Yes — `os.path.isdir(p)` is the single most common spelling of
this check in Python, the file already imports `os` and uses `os.path` elsewhere, and the historical
r3 M1 defect was *literally* a re-probe of `is_dir`. This is not an exotic escape.

I checked whether a mechanism better than a denylist exists, because a denylist that must be
maintained is the weaker answer. It does not: `sys.addaudithook` fires for `os.listdir`, `os.scandir`
and `open`, but **not** for `stat`, `access`, `os.path.isdir` or any `Path` method (measured,
CPython 3.14.4). So the denylist is the right mechanism — it just has only half the surface.

**Suggested fix** (hypothesis — measured: with this plus the arm fixture from finding 1, all four
survivors die via the class case, each naming its route, and the control stays 128/128):

```python
_OS_PROBES = ("stat", "lstat", "access", "listdir", "scandir", "open", "readlink",
              "getcwd", "statvfs")
# ... in _renders_without_the_world, alongside the Path patching:
_saved_os = {n: getattr(os, n) for n in _OS_PROBES if hasattr(os, n)}
_saved_open = builtins.open
```

`os.path.isdir` / `os.path.exists` / `os.path.isfile` need no separate entry — they route through
`os.stat` (confirmed via `inspect.getsource(genericpath.isdir)`; they are not C-accelerated on this
build). `os.access` does need its own, being a direct syscall wrapper.

And the comment should stop claiming totality. Something like *"the `Path` and `os` entry points a
renderer could reach; a route through neither — `subprocess`, `ctypes`, a C extension — is outside
this boundary and would have to be caught by reading"* is defensible and, unlike the present text,
true.

---

### [Medium] r4's eager-fixture repair fixed the two instances and left the class

**Where:** `scripts/explainer-serve.py:1514` and `scripts/explainer-serve.py:1581`

**What:** `87a4ebf2` made `_arm` and `_both` lazy, correctly. Two other collection-time expressions
call production code outside any thunk:

```python
:1514  _rev_branch_src = inspect.getsource(Handler.do_GET).split('if path == "/_rev":', 1)[1] \
:1581  rev_before = revision(rev_file)
```

**Why it matters:** MEASURED, both reachable by plausible mutations, both reproducing exactly the
failure `87a4ebf2` names:

```
=== revision() raises — eager at :1581 ===
  rc=1   NO SUMMARY LINE   [FAIL] lines=0   traceback=True
=== /_rev branch literal renamed — eager at :1514 ===
  rc=1   NO SUMMARY LINE   [FAIL] lines=0   traceback=True   IndexError: list index out of range
```

The `:1514` one is the more likely of the two: it is an `[1]` index on a source split, so any
mutation that touches the `/_rev` dispatch literal aborts the suite instead of failing a case.

**Mitigating, and I want to be fair about it:** this is not a false green. `check-plan-code.py:1316`
refuses precisely this shape — *"the suite went RED but printed no `[FAIL] <case>` line, so NOTHING
COULD SEE THE KILL"* — and sets `ok = False` with a per-file diagnosis. And `explainer-serve.py` is
a declared member of `WIDENED_MANIFEST_DEBT` in `check-ratchet-contract.py:381`, so nothing runs
mutations against it today at all. The cost is bounded to a confusing run whenever the file is
eventually enrolled.

**Suggested fix** (hypothesis): make both lazy the same way, `_rev_branch_src = lambda: …` and
`rev_before = lambda: revision(rev_file)`. The more durable version is a rule rather than three
repairs — e.g. a case asserting that `_self_test`'s collection phase contains no call to a module
symbol outside a lambda — but that is a larger piece of work than this round, and I would file it
rather than build it here.

---

### [Medium] `src_root()`'s `MISSING_FALLBACK` arm has no case at all — `fallback_ok = True` survives

**Where:** `scripts/explainer-serve.py:505` (production) and `:1743-1744` (the case that should
cover it)

**What:**

```python
:505   fallback_ok = REPO.is_dir()
:1743  case("src_root: the fallback's state is observed ONCE, and travels with the reason",
:1744       lambda: with_env(None, src_root).fallback_ok is True)
```

The case asserts only the `True` side. **Measured: `fallback_ok = REPO.is_dir()` → `fallback_ok =
True` passes 128/128, rc=0.**

**Why it matters:** `fallback_ok` is load-bearing twice over — it selects the root in `src_root`
(`REPO if fallback_ok else None`) and selects the arm in `src_root_help` (`:545`). I demonstrated
the consequence directly, rebinding `REPO` to a missing checkout with the env unset:

```
--- CORRECT code ---
  src_root() -> reason='MISSING_FALLBACK' root=None  fallback_ok=False
  caller renders help: True
--- the SURVIVING mutation ---
  src_root() -> reason='OK' root=/tmp/yps-definitely-gone-2026  fallback_ok=True
  caller renders help: False   <-- the gone-checkout remedy is NEVER reached
```

A reader whose checkout has moved gets `no such source file` instead of the gone-checkout remedy —
the exact user-visible failure the `MISSING_FALLBACK` arm exists to prevent — and the suite is
green. The root cause is that **every `MISSING_FALLBACK` case in the file feeds `src_root_help` a
hand-built `SrcRoot`**; not one goes through `src_root`. The suite proves the renderer handles the
reason and proves nothing about whether the probe ever produces it. That is r2 M1's own lesson —
*ask the caller's relationship, not a fixture's* — one level further up than r2 applied it.

**Suggested fix** (hypothesis; the seam is verified — the two runs above are exactly this):
temporarily rebind the module global `REPO` to a missing path and assert the producer, e.g.

```python
def _with_repo(p, fn):
    import sys
    mod = sys.modules[__name__]
    real = mod.REPO
    try:
        mod.REPO = p
        return fn()
    finally:
        mod.REPO = real

case("src_root: a MISSING fallback with no env var yields MISSING_FALLBACK and no root",
     lambda: (lambda o: o.reason == "MISSING_FALLBACK" and o.root is None
                        and o.fallback_ok is False)(
         _with_repo(pathlib.Path("/tmp/yps-no-such-checkout"),
                    lambda: with_env(None, src_root))))
```

---

### [Low] `EXPLAINER_DOCS_ROOT=~unknownuser/x` kills the connection instead of rendering the help — PRE-EXISTING

**Where:** `scripts/explainer-serve.py:509`, reached from `:1112`

**What:**

```python
p = pathlib.Path(v).expanduser()
```

**Why it matters:** MEASURED live, against a real `ThreadingHTTPServer` on an ephemeral port:

```
/src/scripts/explainer-serve.py    -> RemoteDisconnected: Remote end closed connection without response
/latest                            -> HTTP 404  b'no explainers yet'
  RuntimeError: Could not determine home directory.
    explainer-serve.py:1112 in do_GET  ->  explainer-serve.py:509 in src_root
```

`do_GET` has no exception wrapper, so this escapes to `handle_one_request` and the socket closes
with no response. It is the one `EXPLAINER_DOCS_ROOT` value that defeats the entire help path this
branch exists to build — a misconfigured env var producing *no* explanation rather than the good
one. It is also the same symptom the repo already paid for and guarded once: backlog #87, *"a NUL
byte must not escape the resolver … `GET /_stale?p=%00` gave curl exit 52"*, in this file.

**Explicitly flagged as pre-existing:** `expanduser()` arrived with `#149` and is on `master`
unchanged. Not introduced here, and reasonable to file rather than fix in this PR — but it is in
scope for the round because the branch's subject is *this failure path explaining itself*.

**Suggested fix** (hypothesis): catch `RuntimeError` alongside the existing behaviour and route it
to `BAD_ENV`, which already has the right text — `EXPLAINER_DOCS_ROOT is set to '~unknownuser/x',
which is not a directory` is true and actionable.

---

## Checked and clean — stated so the boundary of this review is visible

- **Mandate 3, the lazy fixtures are right.** Every call site was updated: `_arm()` at `:1893` and
  `:1923`, `_both()` at `:1933` and `:1935` (grep-verified; no bare `_arm`/`_both` reference
  remains). `src_root_help` is pure, so recomputation cannot change an answer, and no case asserts
  identity across calls. `:1935` now evaluates `_both()` twice — harmless. No case changed meaning.
- **Mandate 4, the refusals cannot 500 the request path.** `raise ValueError` is unreachable from
  the caller *by construction*: in `src_root`, `root is None` ⟺ `reason ∈ {BAD_ENV,
  MISSING_FALLBACK}` on both arms, and `:1114` only calls the renderer when `root is None`. So
  neither the unknown-reason nor the `OK` refusal can fire in `do_GET`. Both are nonetheless
  load-bearing: deleting the unknown-reason guard goes red via `an unknown reason is refused, not
  defaulted into an arm`; deleting the `OK` guard goes red via `a SUCCESSFUL observation is refused`.
  Raising is the right call here.
- **`SrcRoot` as a NamedTuple.** Nothing indexes it, iterates it, or truth-tests it; the one
  comparison (`.root == root`) is on a field. `root` being falsy-when-`None` is never relied on —
  the caller tests `is None` explicitly. No hazard found.
- **`fallback_ok = REPO.is_dir()` evaluated for both arms.** No reachable behaviour change: when the
  env var names a real directory the root is non-`None` either way and the renderer is never called.
  Cost is one extra `stat` per `/src/` request. The granularity concern from the brief is a
  non-issue *because the prose declares it* — `_gone_checkout_help` says "it may simply not be
  readable right now — this server cannot tell which", so "not a directory" vs "not readable" is
  named rather than conflated silently. That is r3 M3 correctly applied.
- **The report-format change (`FAIL: ` → `[FAIL] `) works end-to-end.** Verified by running
  `check-plan-code.parse_fail_names` over this file's genuine red output:
  `parse_fail_names -> ['a SUCCESSFUL observation is refused — there is nothing to explain']`.
  r3 M4 is real and closed.
- **The six new cases are real.** The two refusals and the class falsifier are mutation-killed via
  the case each names; `src_root: every reason it can return is a declared member` goes red when
  `src_root` returns an undeclared reason. The exception is `the fallback's state is observed ONCE`
  — that one passes for a weaker reason than its name claims, which is Medium #4 above.
- **`page_chrome`** — 76/76, untouched by `87a4ebf2`, no interaction found.
- **Context, not a finding:** `explainer-serve.py` has no `scripts/mutations/*.json` manifest and is
  a declared member of `WIDENED_MANIFEST_DEBT` (`check-ratchet-contract.py:381`). So the class
  falsifier — the centrepiece of this redesign — has no mechanical protection in CI today; if it
  were weakened or deleted, nothing would fire. The debt is tracked and declared, which is why this
  is context rather than a finding, but it is worth knowing while judging how much the falsifier's
  strength buys.

## What I did not check

Concurrency on the `/src/` path, the restart/respawn machinery, `md_render`, and the reload client —
all untouched by these two commits and outside the class under review.
