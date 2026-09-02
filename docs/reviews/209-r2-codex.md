# PR #209 — review round 2 (Codex half), scoped to round 1's own fixes

**Subject:** `feat/page-staleness-visible` at `ebe6e540`, i.e. round 1's fixes, not the original change.
**Model:** `gpt-5.5` — `gpt-5.6-sol`, `-terra`, `-luna` each returned HTTP 400 again; the wrapper's
fallthrough handled it. **Verdict file:** `docs/reviews/verdicts/209-r2-codex.verdict.json`
(`gate_ran=true`, 1745 chars).

**REVIEW GAP:** claude — not invoked; the session instruction forbids spawning subagents unless the user asks. One reviewer, not two, for the second round running.

**Why this round was scoped at the fixes.** `docs/plugins.md` and this project's own history record
that the next round's findings are usually regressions from the previous round's fix. The brief said
so explicitly and named the three fixes as the primary target.

**Codex executed:** `explainer-serve.py --self-test` (80/80 at the time), live `curl` probes
returning `stale docs/backlog.md`, `stale docs/dashboard-entries.md`, `fresh` for goals and `fresh`
for junk input. Not a reading-only pass.

---

## VERDICT: CONVERGED — no Blocking, no High. One Low, and it was right.

### Low — the soundness guard named ONE EXAMPLE instead of the failure CLASS  ✅ FIXED

`scripts/explainer-serve.py` — `_js_code_only` and its precondition case.

Round 1 added `_js_code_only` (strip `//` line comments) so a check about code could not be
answered by prose, and guarded its one unsound assumption with:

```python
case("_js_code_only is safe here: RELOAD_JS holds no '//' inside a string literal",
     lambda: "://" not in RELOAD_JS)
```

**Codex's counterexample, verified rather than argued:**

```js
var path = '//local'; say('')
```

contains no `://`, so the guard stays green — while `_js_code_only` truncates the line to
`var path = '`, deleting a `say('')` that has just reintroduced the round-1 High. The regression
case would pass over the exact defect it exists to catch. Codex confirmed the truncation in Python;
so did I.

⛔ **This is the same defect class as the finding it was written to prevent** — a check that answers
a narrower question than the one it claims. `://` is one instance; the class is *"a `//` the helper
thinks is a comment and is not"*.

**Fix:** replaced with `_js_strip_is_sound(js)`, which asks the helper's actual question — is any
line's first `//` preceded by an odd number of quote characters, i.e. inside an open string
literal? Conservative by design: a `//` inside a *balanced* pair on the same line also reports
unsound, which fails closed.

**CONTROL — the new guard was run against the old guard's blind spot:**

| Input | `_js_strip_is_sound` | note |
|---|---|---|
| `var path = '//local'; say('')` | `False` | the round-2 counterexample |
| `var u = "//cdn"; say('')` | `False` | double-quoted variant |
| `var x = 'https://a'; say('')` | `False` | the URL case the OLD guard caught — nothing lost |
| `var a = '';   // owned by poll()` | `True` | ordinary trailing comment |
| `window.addEventListener('focus', check);` | `True` | no comment at all |

And the old guard, on the counterexample: `"://" not in "var path = '//local'; say('')"` → **`True`**.
It passed. That is the hole, executed rather than asserted.

**The guard now has its own falsifier**, because a predicate with no negative case can return a
constant and nothing notices:

```python
case("that soundness check REJECTS the round-2 counterexample and ACCEPTS real code",
     lambda: _js_strip_is_sound("var path = '//local'; say('')") is False
             and _js_strip_is_sound("var a = '';   // owned by poll()") is True)
```

⚠ **Residual, stated in the docstring rather than implied:** `_js_strip_is_sound` does not model
escaped quotes (`\'`) or template literals. `RELOAD_JS` contains neither today. If it grows them,
the helper returns a confident answer about a question it can no longer see — the docstring says
**replace it, do not widen it**.

Counts: `explainer-serve --self-test` 80 → **81** (one case replaced by two); declaration updated,
`check-selftest-counts.py` green.

---

## Found by the author during this round, NOT filed

**A NUL byte in any query closes the connection with no response.** `GET /_stale?p=%00` →
`curl` exit 52, Python `RemoteDisconnected`. Reproduced.

⚠ **Checked before claiming it, and it is NOT this branch's:** `/_rev?p=%00`, `/%00` and
`/dashboard%00` behave identically, and `/_rev` predates #209 (`git show master:…` contains it).
**Pre-existing and server-wide.**

Everything else in a hostile-input sweep failed closed to `fresh` — traversal attempts, empty `p`,
wrong case, a space, an embedded query. `fresh` is the safe direction: this endpoint's job is
raising a banner, and a false banner teaches the reader to ignore true ones.

Not filed to `docs/backlog.md` — filing is the user's step. Recorded here so it is not rediscovered
as new. Severity if filed: Low. It is a 127.0.0.1-only server, it fails closed, the server survives
(each request is its own thread), and a NUL byte in a URL is not a path any real reader takes.

## Disposition

**Round 2 converged.** The one Low is fixed, with a control proving the old guard's blind spot and
a falsifier on the new guard. Two rounds have now run on this PR, both Codex-only; the missing
Claude half is recorded on each rather than papered over.
