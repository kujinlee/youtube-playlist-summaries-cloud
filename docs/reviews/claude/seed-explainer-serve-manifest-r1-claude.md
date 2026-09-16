# Adversarial review — `seed-explainer-serve-manifest`, round 1, CLAUDE half

Subject: commit `7915f6ed` on `seed-explainer-serve-manifest`, base `756c41fa`.
Tree verified clean (`git status --short` empty) at start and at end. Nothing was staged or committed.

**Verdict: NOT CONVERGED.** Two High and four Medium findings, every one measured.

**Lead conclusion, stated first because it governs how to read the rest:** *the branch is correct and
is a real improvement.* All 17 entries are honest in the sense that matters most — each one's `expect`
matched **exactly one** red case, so all 17 are genuinely attributed, and the debt ratchet still fires
in both directions. Nothing here is Blocking. What the findings say is that the manifest's **17 entries
sit almost entirely in the pure-helper layer**, and that the commit's prose makes two claims about the
world that measurement contradicts.

---

## How everything below was measured

`scripts/` + `docs/` + `.github/` + `.claude/hooks` were copied to a scratch workspace outside the
repo; `explainer-serve.py` was mutated **there**, never in the tree, and restored from a pristine copy
with an md5 check after every run. Control in that workspace: **149/149**, matching the repo.

> ⚠ A scripts-only copy gave a **red control** (`148/149`, `...and every declared source is a real
> file in the repo`). That is `HARNESS_TREE`'s own recorded lesson reproducing on the first try.

Baselines confirmed green before any mutation:

| Command | Result |
|---|---|
| `explainer-serve.py --self-test` | `149/149 passed` |
| same under `HOME=$(mktemp -d)/.home` | `149/149 passed` |
| `check-plan-code.py --self-test` | `128/128 passed` |
| `check-ratchet-contract.py --self-test` | `41/41 passed` |
| `check-ratchet-contract.py` (bare) | `ratchet contract OK`, rc=0 |
| `check-selftest-counts.py` | `39 script(s) … every one verified by running it`, rc=0 |
| `check-docs.py` / `check-fixture-variation.py` | OK, rc=0 |
| `gen-backlog-page.py --self-test` | `165/165 passed` |

Verdicts below are read off the `N/M passed` line, never a grep for FAIL-shaped tokens.

---

## HIGH 1 — The `/src/` security verdict rests on FOUR clauses. This branch cased one and left two measurably unguarded — the same instance-not-class move its own headline is about

**`scripts/explainer-serve.py:238-241`** states the verdict in one sentence:

> Not judged a security finding … `safe_path` resolves BEFORE the containment test so `..` and
> symlinks collapse, `SERVABLE` excludes `.env*` by suffix, **the listener is 127.0.0.1**, and **no
> CORS header is emitted** — so a cross-origin page can cause a request but cannot read the response
> BODY.

The branch's headline discovery is that clause 2 *"had no case at all"*. That is true and the fix is
right. But the sentence has four clauses, and the branch stopped at the one it tripped over.

**Measured** — each mutation applied alone to the workspace copy, control green first:

| Clause | Mutation | Result |
|---|---|---|
| 1 · resolve-before-contain | (already entry 14) | killed — but see MEDIUM 3 |
| 2 · `SERVABLE` excludes `.env*` | (this branch's new entry) | killed, 148/149 |
| 3 · **listener is 127.0.0.1** | `HOST = "127.0.0.1"` → `"0.0.0.0"` | **`149/149 passed` — SURVIVED** |
| 4 · **no CORS header** | `_send` gains `self.send_header("Access-Control-Allow-Origin", "*")` | **`149/149 passed` — SURVIVED** |

Clause 4 is the sharper of the two. `:1066-1067` states it a second time as a load-bearing decision —
*"no CORS header is needed — and its absence is what stops any OTHER site in the browser from reading
private source through it"* — and `:243-249` spends six lines refining exactly what that absence does
and does not buy. The one line the whole paragraph depends on can be deleted, or inverted into a
wildcard, with nothing going red. Clause 3 is the difference between a loopback dev server and one
reachable from the LAN, over a subsystem the same comment says serves *"the whole tree, dotfiles and
vendored dependencies included"*.

**Why this is High rather than Medium:** it is not "the manifest is incomplete", which the commit
never claimed. It is that the branch found a defect by asking *"what does this security verdict rest
on, and is it cased?"*, got a hit, and did not finish enumerating the sentence it was reading. This
repo's memory calls that **after fixing, SEARCH for the class**.

**Falsifier:** add entries for `HOST` and for a CORS header and show either mutation going red via a
named case. If both still pass at 149/149, this finding stands.

---

## HIGH 2 — `_regenerate` has zero cases and zero entries, and all four of its documented decisions survive — including a timeout reported as a successful rebuild

**`scripts/explainer-serve.py:1166-1209`.** `grep -n "_regenerate\|source_shell" scripts/explainer-serve.py`
returns only definition and call sites — **no case in the 149 ever calls either function.** Stated
precisely, because the near-miss matters: the suite *does* assert over `REGENERABLE` and `PAGE_SOURCES`
(`sorted(PAGE_SOURCES) == sorted(REGENERABLE)`, and that each declared source is a real file), so the
two dicts are covered as **key sets**. The handler that consumes them is not exercised at all.

| Mutation | Result |
|---|---|
| the `504 … NOT REBUILT` timeout arm → `200 {"ok": true}` | **`149/149` — SURVIVED** |
| `warn = [… startswith("⚠")]` → `warn = []` | **`149/149` — SURVIVED** |
| `isinstance(want, str)` → `want is not None` | **`149/149` — SURVIVED** |
| `with lock:` → `if True:` (the per-page lock) | **`149/149` — SURVIVED** |

The first is the one to act on. `:1192-1193` says it in this repo's own house style:

> A timeout is NOT a failure to report as "rebuilt". The reader is told the page may now be
> half-written, because silence here reads as success.

That is `CLAUDE.md`'s *"cannot run" is a FAILURE, never a pass* written into a handler — and the
mutation that turns it back into a pass is invisible to the suite. The second is a **Codex Medium
that was fixed and never cased** (`:1201-1204`: *"exit 0 does NOT mean a clean rebuild … the warning
travels to the button"*); deleting the warning channel restores exactly the degraded-gate-reporting-
success shape the comment was written to close.

The third is a live crash, not just lost coverage: `REGENERABLE.get(["dashboard"])` raises
`TypeError: unhashable type` inside the handler, which is the dropped-connection symptom of backlog
#87 and #123 arriving at a third site.

The fourth (the lock) is genuinely awkward to case and I would not block on it.

**Why High:** four documented decisions, one of them a previous reviewer's finding, in a handler that
`subprocess.run`s a generator — and the manifest that was written to end this file's unratcheted
status does not touch it. `_regenerate` is the highest-consequence function in the file that has no
coverage at all.

**Falsifier:** a case that drives `_regenerate` (the `_drive_src` pattern already in the suite shows
how — `object.__new__(Handler)` plus an `_send` stub, no socket needed) and an entry for the timeout
arm. If the timeout mutation then goes red via that case, this is closed.

---

## MEDIUM 3 — Entry 14's kill is real but its ATTRIBUTION is misleading: the case it names goes red for backlog #87's crash, and the two cases whose names say "traversal" are UNCHANGED by it

This is the coverage-theatre shape, and it is the only instance I found among the 17.

```
"name":   "safe_path tests containment BEFORE resolving"
"expect": "a raw NUL byte does not escape safe_path"
```
— `scripts/mutations/explainer-serve.json:146-154`, against `scripts/explainer-serve.py:290-291`.

The entry's **name** claims the subject is containment order — the property `safe_path`'s own docstring
(`:274-275`) states as *"a prefix test on the raw string is defeated by `..`, symlinks and
percent-encoding"*. The case it **names** is backlog #87's property: that a NUL byte returns `None`
instead of raising.

**Measured** by driving the real and mutated `safe_path` side by side over a temp root:

| Probe | real | mutated | verdict |
|---|---|---|---|
| `/../../etc/passwd` — the case **`refuses traversal with ..`** | `None` | `None` | **unchanged** |
| `/%2e%2e/%2e%2e/etc/passwd` — the case **`refuses ENCODED traversal`** | `None` | `None` | **unchanged** |
| `/../escaped.md` (a traversal to a servable file that exists) | `None` | `<root>/../escaped.md` | CHANGED |
| `/\x00.html` — **the case the entry names** | `None` | `<root>/ .html` | CHANGED |

Both cases that have the word *traversal* in their name stay **green** under a mutation named
*"tests containment BEFORE resolving"* — and they stay green for a reason that has nothing to do with
containment: `passwd` has no suffix, so the `SERVABLE` allowlist rejects them before containment is
ever consulted. The named case goes red because `.resolve()` is what raises on a NUL byte.

So the entry certifies containment using a case about a crash, while the two cases a reader would
assume are doing the work are provably not. This matters because the same commit's `EXPECTED_MUTATIONS`
comment (`check-plan-code.py:827`) says an entry is admitted *"only when its kill is ATTRIBUTABLE"* —
it is attributable here in the mechanical sense the tool checks, and misleading in the sense the tool
cannot check.

⭐ **The fix is free and already in the file.** The mutation *does* redden
`/src/ escape is refused — over a target that really exists outside the root` (confirmed in the red
list for this entry), and that case is about containment, over a real escape target, for the reason
the entry's name gives. Point `expect` at it. The NUL property then deserves its own entry with a
name that says `.resolve()` is what makes the function total.

⚠ Worth carrying forward: this also shows **`refuses traversal with ..` and `refuses ENCODED traversal`
are themselves passing for the wrong reason** — they would pass against a `safe_path` with no
containment test at all. Not introduced by this branch, but now measured.

**A second, milder instance of the same shape — entry 16, so this is a class and not a one-off.**
`"revision stops carrying the file's identity"` (`explainer-serve.json:167-177`) injects
`return "fixed"` at the top of the function, neutering it entirely, and names the case
`revision changes on a same-mtime rewrite (size is load-bearing)` — whose parenthetical is a claim
about **size specifically**. The blunt mutation proves nothing about size. **Measured:** the precise
mutation, `f"{st.st_mtime_ns}:{st.st_size}"` → `f"{st.st_mtime_ns}"`, gives **`148/149`** red via that
same case and nothing else, versus `147/149` and two red cases for the blunt one. The sharper edit is
available for free, kills through the same case, and makes the entry's evidence match the case's own
words. Entry 14 has the same over-broad quality — it drops `.resolve()` from **both** the candidate and
the root, which is two changes, and the NUL kill comes from the first while the name is about the
second.

**Falsifier:** if repointing `expect` to the escape case makes the entry unattributable (two matches,
or zero), I am wrong about the cheap fix — the finding about the current attribution stands either way.
For entry 16, if the precise mutation does not go red via that case, I am wrong; my run says
`148/149`.

---

## MEDIUM 4 — The claimed BOUND is false as stated, and it is stated in four places including the backlog closure

The commit asserts, in `check-plan-code.py:828-831`, `check-ratchet-contract.py:73-76`,
`explainer-serve.py:2073-2076` and the backlog #122 closure:

> a case that dies by RAISING prints `[FAIL] {name} — {ExcType}: {msg}`, so its parsed name carries
> unstable text and **can never be named by a manifest entry**

The first half is exactly right and I reproduced it. The second half is not.

**Measured** — the entry's own mutation applied, the real suite run, its stdout fed to the **real**
`parse_fail_names`, and the **real** matcher (`[f for f in fails if w == f]`, `check-plan-code.py:1299`)
applied to it:

```
parse_fail_names -> 7 names, one of them:
  '/src/ serves a real file from the observed root — AssertionError: do_GET read the
   environment — it must carry, not re-derive'

expect = '/src/ serves a real file from the observed root'
   -> matched 0 red case(s)   ATTRIBUTED=False        # the bare name, as claimed
expect = '<the full string above>'
   -> matched 1 red case(s)   ATTRIBUTED=True         # ← the bound says this is impossible
```

A raise-dying case **can** be named, by naming the full parsed string. And "unstable" does not hold for
the cases the commit cites: `_Forbidden._raise`'s message is
`f"{self._by} read {self._what} — it must carry, not re-derive"` over two call-site literals
(`explainer-serve.py:1776-1778`), so it is fully deterministic.

**The claim is true for a different reason than the one given, and only sometimes.** In the same
sweep I produced a raise kill whose message *is* unstable:

```
[FAIL] /src/ serves a real file from the observed root — ValueError: '/private/var/folders/tg/…/srcroot/srcfix.md' is not in the subpath of '/private/var/folders/tg/…/srcroot/nope'
```

That one genuinely cannot be named — it carries a machine-specific temp path. So the honest statement
is: *a raise kill can be named only by embedding the exception type and message, which is
unattributable whenever that message carries runtime data, and couples the entry to one specific
failure mode of the case even when it does not.* That supports the same design decision the branch
made — converting the raise to a value is still the better move — but for a reason that survives
being checked.

**Why Medium and not Low:** `CLAUDE.md` imports the file carrying one copy of this claim, and the
backlog closure carries another with the word ⛔ in front of it. A future author reads *"cannot be
ratcheted until some case reports it as a returned False"* (`check-ratchet-contract.py:75-76`) as a
structural impossibility and does not check. This repo has a memory note for exactly this — *never
write a claim you did not measure* — and the branch is otherwise an exemplar of it.

**Falsifier:** show an `expect` carrying the full `{name} — AssertionError: {literal msg}` string
failing to attribute. My run says it attributes.

---

## MEDIUM 5 — `md_render`'s quote escaping is credited with closing an attribute break-out, and both halves survive; `source_shell` has no cases at all

`safe_href`'s docstring, `scripts/explainer-serve.py:335-336`:

> Quotes are escaped upstream in `md_render`, which independently closes the attribute break-out
> (`[x](a"onmouseover=…)`); this closes the scheme half.

**Measured:**

| Mutation (`md_render`, `:370-371`) | Result |
|---|---|
| drop `.replace("'", "&#39;")` | **`149/149` — SURVIVED** |
| drop `.replace('"', "&quot;")` | **`149/149` — SURVIVED** |
| drop `.replace("<", "&lt;")` | killed, 148/149 (`md: PLACEHOLDER survives escaping`) |
| escape `&` **last** instead of first | killed, 146/149 |

So a division of labour between two functions is written down, one half of it (`safe_href`) is
hardened and cased, and the half this docstring credits `md_render` with has no case in either
direction. `<` and `&` are covered — by cases that are about *placeholders rendering* and *nested
blockquotes*, which is fortunate rather than designed.

`source_shell` (`:625-676`) compounds it, and it is the function that renders every `/src/` file:

| Mutation | Result |
|---|---|
| the non-markdown `<pre>` arm stops escaping `<` (`:636`) | **`149/149` — SURVIVED** |
| `if rel.lower().endswith(".md")` → `if True` (render everything as markdown) | **`149/149` — SURVIVED** |

The first means every non-`.md` file served through `/src/` — `.html`, `.js`, `.svg`, `.css` from
anywhere in the checkout — has its own markup injected raw into the viewer page. Loopback-only, and
the `:251-254` paragraph already argues the oracle is not worth blocking on; but this one is *content*
execution, not a path oracle, and the reach comment's verdict does not cover it.

**Falsifier:** a case asserting `md_render("a\"b'c")` escapes both quotes, plus one asserting
`source_shell("x.js", "<script>")` contains no raw `<script`. If those exist and are red under these
mutations, closed.

---

## MEDIUM 6 — `start` / `stop` / `status` / `detach_streams` are named by zero cases; a `--status` that reports success with nothing listening survives

| Mutation | Result |
|---|---|
| `status()`: `return 0 if running else 1` → `return 0` | **`149/149` — SURVIVED** |
| `start()`: the `if not port_busy(...)` readiness arm → `if False:` | **`149/149` — SURVIVED** |
| `start()`: drop the `detach_streams()` call (`:1267`) | **`149/149` — SURVIVED** |
| `detach_streams()`: drop `os.dup2(log, 2)` | **`149/149` — SURVIVED** |
| `detach_streams()`: log mode `0o600` → `0o644` | **`149/149` — SURVIVED** |
| `stop()`: leave the pidfile behind after SIGTERM | **`149/149` — SURVIVED** |

The first two are the ones that matter, and they are the same class as HIGH 2: `status()` returning 0
when nothing is listening is *"cannot run" reported as a pass* in the one command a human runs to ask
whether the server is up. The `start()` readiness arm is the guard whose text is literally
`FAIL: forked pid {pid} but nothing is listening … NOT RUNNING.`

`detach_streams`' docstring (`:861-873`) records a defect **measured three times in a row on
2026-08-21** — a daemon wedged on its parent's pipe while `--status` reported it healthy. Both the
call and the stderr half of the redirect can be deleted silently.

⚠ **Deliberately not re-filed:** backlog #125/#126/#127 are the parked restart feature and I have not
touched them. The readiness *case* #125 is about lives on that parked branch; on **this** branch
`start()`'s readiness check has no case at all, which is a different (and smaller) statement.

**Falsifier:** these are hard to case without binding a port. `status()` is not — it is a pure function
of `port_busy` and `read_pid`, both stubbable exactly as `_drive_src` stubs `src_root`. If a
`status()` case exists and reddens, closed.

---

## LOW 7 — `resolve_page`'s "not a second chance" rule survives, and it is a stated rule with a written reason

`scripts/explainer-serve.py:743-744`:

```python
if "." in bare.rsplit("/", 1)[-1]:
    return None                      # it HAD an extension; the fallback is not a second chance
```

Mutating the condition to `if False:` → **`149/149` — SURVIVED**. Behaviourally observable, measured
directly on a temp root:

```
/notes.md      real=None   mutated=<root>/notes.md.html
/secret.env    real=None   mutated=<root>/secret.env.html
```

So a request for a non-servable name gets a second attempt with `.html` glued on, which forces the
suffix allowlist to pass. Nothing escapes containment, and the `/_rev` comment's claim that it
*"rejects `/secret.env`"* still holds (the `.html` file has to exist). It is a real, small widening of
a resolver whose docstring spends four lines saying it must not widen.

## LOW 8 — The new RATCHETABLE case is green on failures its neighbours catch

`scripts/explainer-serve.py:2089-2091`. Its comment says it *"asserts the drive completes without
`_Forbidden` firing"*. It asserts only the second half: `_raises(fn, AssertionError) is False` is also
True when `fn` raises **anything else**, and when the drive completes but serves nothing.

**Measured:**

| Mutation | RATCHETABLE case | suite |
|---|---|---|
| `/src/` raises `ValueError` (`relative_to` a wrong base) | **green** | 147/149 |
| `/src/` always 404s (`target = None`) | **green** | 147/149 |

Both are caught by the two neighbouring cases, so nothing is unguarded — the case is **additive**, it
replaces nothing, and the design intent (make one kill attributable) is sound and I would keep it.
But its own comment overstates it. Asserting `_drive_src(...)[0] == 200` **and**
`_raises(...) is False` in one lambda costs nothing and makes the sentence true.

## LOW 9 — The new `SRC_REASONS` case adds a second literal for "a path that does not exist", and reddens on correct code if that path is created

`scripts/explainer-serve.py:1749` hardcodes `pathlib.Path("/tmp/yps-gone-2026-09-16")`, while
`:1728` already defines `_norepo = pathlib.Path("/tmp/yps-no-such-repo-2026-09-15")` for the same
concept, in scope, four lines earlier.

**Measured:**
```
$ mkdir -p /tmp/yps-gone-2026-09-16 && python3 scripts/explainer-serve.py --self-test
  [FAIL] SRC_REASONS cannot be widened unnoticed — every declared member is reachable
self-test: 148/149 passed
$ rmdir /tmp/yps-gone-2026-09-16 && python3 scripts/explainer-serve.py --self-test
self-test: 149/149 passed
```
(The directory was removed; the workspace returned to 149/149.)

A world-writable path that the case requires to be **absent** is a false-failure channel. The exposure
is pre-existing for `_norepo`, so the class is not new — but the branch added a **second** name for
one concept, which is this repo's *a second implementation of one rule drifts*. Reusing `_norepo` fixes
the duplication and confines the exposure to one literal. Answering the brief's question directly:
the case asserts something **real** — it is a genuine both-directions upgrade over the subset test, and
I would keep it.

## LOW 10 — The rewritten docstring example now shows a path shape the code cannot produce, and one the file says 20 lines later must not be quoted

`scripts/explainer-serve.py:561-562` now reads *"With a repo at `~me/agentic ai docs/repo` the emitted
line handed `python3` the path `~me/agentic`"*. The space — the whole point of the example — survives,
and the `home_escapes` problem is genuinely solved (`HOME_ESCAPES`' tilde pattern is
`expanduser\(\s*["'][^"']*~\w`, a call form, so a bare `~me/` is not flagged; the `/Users/` pattern is
what fired).

Two small costs:

1. `observed.fallback` is `SCRIPTS.parent` where `SCRIPTS = Path(__file__).resolve().parent` — always
   absolute. A `~`-prefixed repo path is a value this code cannot hold.
2. `_gone_checkout_help`'s docstring at `:606-608` says the opposite thing about tildes:
   *"`shlex.quote("~/explainers/.serve.pid")` quotes the tilde, and a quoted tilde does not expand —
   the safety measure would silently destroy the command."* Measured:
   `shlex.quote('~me/agentic ai docs/repo/scripts/explainer-serve.py')` →
   `'~me/agentic ai docs/repo/scripts/explainer-serve.py'`. So the example's *fixed* command is still
   broken, for the second reason the file documents.

An absolute path outside `/Users/` and `/home/` keeps the example correct and still passes
`home_escapes` — e.g. `/srv/me/agentic ai docs/repo`.

⚠ Also cosmetic, from the same edit: the reflow left an orphan line —
*"⚠ The suite had used space-bearing / fixtures since before that bug and / asserted only that…"*
(`:565-567`).

## LOW 11 — `pid_alive`'s falsy-pid guard survives, and what it guards against is `SIGTERM` to the whole process group

`scripts/explainer-serve.py:848-849`. Mutating `if not pid:` → `if pid is None:` → **`149/149` —
SURVIVED**. With a pidfile containing `0`, `read_pid` returns `0`, `pid_alive(0)` becomes True
(`os.kill(0, 0)` succeeds), and `stop()` at `:1280` then issues `os.kill(0, signal.SIGTERM)` — which
POSIX defines as signalling **every process in the caller's process group**. Low because it needs a
zero-valued pidfile; listed because the consequence is out of proportion to the one-token guard.

Same batch, folded in rather than given its own section: `safe_path`'s `candidate.suffix.lower()` →
`candidate.suffix` survives (`/A.HTML` silently 404s); `/latest`'s `302` → `301` survives (a cached
permanent redirect pins the bookmark `/latest` exists to keep moving); `_send` dropping
`Content-Length` survives; `do_POST`'s `length > MAX_BODY` off-by-one survives; the route allowlist
`if route not in ("/questions", "/regenerate")` → `if False:` survives; dropping `isinstance(payload,
dict)` survives; `index_html`'s `page_chrome.assert_wired(...)` call being deleted survives;
`RELOAD_JS` being appended to **every** file rather than only `.html` survives; `/_stale` dropping the
source path from its body survives; `_js_strip_is_sound` checking only single quotes survives (its one
case, `:1606`, asserts only `_js_strip_is_sound(RELOAD_JS)` is True — a one-sided assertion over a
helper whose docstring records a *previous* guard being replaced for being one-sided).

---

## What I checked and found CLEAN — stated so the next round does not re-spend it

**All 17 entries attribute.** Every entry was applied to the workspace copy and its red-case list read
back through the real parser. Each `expect` matched **exactly one** red case: 17 for 17. No anchor
failed to resolve; each appeared exactly once in the delivered file.

⚠ One property of entry 15 worth recording because it is easy to misread later: it is the only entry of
the 17 that mutates **suite** code rather than the deliverable (`_Forbidden` lives inside `_self_test`),
and because `_DECLARED` is derived from `vars(_Forbidden)`, deleting a surface **deletes a case** — the
run reports `147/148`, not `147/149`. The design comment at `:2196` already says so, the floor case
catches it, and `caught` is decided by `rc == 1`, so nothing is wrong. Noted only so a future reader
does not treat the moving denominator as a defect.

**The full `--mutate .` gate: NOT INDEPENDENTLY CONFIRMED by me — treat it as NOT RUN, not as a pass.**
Two attempts, neither yielding a number I read:

1. the first reached `293/660` with no failure reported, and then its output file was deleted out from
   under it by a concurrent agent sharing this session's scratchpad directory;
2. the second, into a private path, reached `~139/660` and **I stopped it deliberately** — by exact
   pid — once `scripts/explainer-serve.py` began being edited in the working tree by another agent
   mid-run. A mutation gate that stages a tree while that tree is changing measures nothing, and
   leaving it to print a confident total would have been worse than stopping it.

I am not reporting a number I did not read. The substantive part for **this** branch is covered above
by the per-entry audit, which measures the same thing for all 17 of its entries, over a control proved
green first.

⚠ **A methodological note that cost me nothing here but is worth recording.** My first wait-loop for
that gate was `grep -qE "…|RATCHET|FAILED|…"` over its log, and it fired immediately — on mutation
**#87**, whose *name* is `THE RATCHET GOES FAIL-OPEN…`. That is this repo's own recorded defect
(*read the `N/M` line, never grep for FAIL-shaped tokens — when the mutation IS that token the grep
miscounts*) reproducing inside the instrument I built to watch for it. Re-armed on process exit.

**The debt ratchet works in both directions after the repointing** — falsified, not read:

| Experiment | Result |
|---|---|
| control (workspace) | `ratchet contract OK`, **rc=0** |
| put `scripts/explainer-serve.py` back into `WIDENED_MANIFEST_DEBT` while its manifest exists | `1 violation(s)`, `RATCHET FAILED`, **rc=1** — a debt cannot be paid silently |
| delete `scripts/gen-m4-manifest.py` from the pin while it still has no manifest | `1 violation(s)`, `RATCHET FAILED`, **rc=1** — a debt cannot be re-accrued silently |
| delete it from the pin and run `--self-test` | `39/41`, both repointed fixture cases red — **the fixtures are live members, exactly as the design comment claims** |

`scripts/mutations/gen-m4-manifest.json` does not exist, so the first repointed fixture
(*"a pinned violator is silent"*) is describing a real violator. The repointing is correct.

**The `[FAIL] ` report contract** — verified as the brief asked and left alone. `parse_fail_names`
(`check-plan-code.py:1502-1526`) reads `startswith("[FAIL] ")` then `[7:]`, truncating at the **last**
`": got "`; `explainer-serve.py`'s runner prints that shape at both report sites and has a case pinning
`count('print(f"  [FAIL] ') == 2`. Mutating the truthy-arm print does destroy the channel the ratchet
reads. Not re-filed.

**Not re-filed, per the brief:** manifest incompleteness as such; the `[FAIL] ` contract being
unratcheted; backlog #123, #125, #126, #127, #128.

---

## Recommendation

**Do not merge on this round.** In priority order:

1. **HIGH 1** — add entries for the `HOST` and CORS clauses, and either case them or state in the
   `:238` paragraph which of its four clauses are ratcheted and which are not. Enumerating the sentence
   is the work; it is small.
2. **HIGH 2** — one case driving `_regenerate` through the existing `object.__new__(Handler)` pattern,
   plus an entry for the timeout arm.
3. **MEDIUM 3** — repoint entry 14's `expect` to `/src/ escape is refused — over a target that really
   exists outside the root`, and give the NUL property its own entry.
4. **MEDIUM 4** — correct the bound in all four places to what is measurably true.
5. **MEDIUM 5 / 6** and the Lows can be one follow-up row rather than blocking this branch, if the
   coordinator prefers — they are pre-existing gaps this manifest simply did not reach, not
   regressions the branch introduced.

---

## State of the tree — stated exactly, because it did not stay clean

**Nothing in this review was measured against a modified tree, and I modified nothing.**

- At start: `git status --short` **empty**, `HEAD` = `7915f6ed`.
- Every mutation was applied to a copy of `scripts/` + `docs/` + `.github/` + `.claude/hooks` in a
  scratch directory **outside the repo**, restored from a pristine copy with an md5 check after each
  run. No `git checkout`, `restore`, `stash`, `reset`, `add` or `commit` was run at any point. No
  server was started and no port was bound.
- **After** my measurements were complete, `scripts/explainer-serve.py` appeared as ` M` in
  `git status` — **+112 lines, 164 cases, one red (`orders newest first`)**. That is **not mine**: the
  md5 of my workspace copy still equals `git show HEAD:scripts/explainer-serve.py`, and the added case
  names (`the listener is loopback — clause 3 of the /src/ reach verdict`, `no CORS header is
  emitted — clause 4…`, `a regenerate TIMEOUT is 504 NOT REBUILT…`, `--status exits NON-ZERO when
  nothing is listening…`, `pid_alive refuses 0…`) map one-to-one onto the findings above, so another
  agent is already acting on them.

⚠ **Flagging rather than fixing:** that in-progress tree is **RED** — `self-test: 163/164`, failing
`orders newest first`. I have not touched it and cannot say whether it is a real regression in the new
code or a fixture collision from concurrent activity. Whoever owns that edit should read it before
treating any of it as done.

The only file I created is this document, and it is deliberately **not staged**.
