# Adversarial review — round 6 — Claude half — `explainer-src-root-self-configures` (PR #295)

## Verdict

**FINDINGS — one new High.**

r5's fix is correct and I verified it independently rather than trusting either the commit
message or Codex: all six pins are live in the **effective** dict, each is genuinely examined,
and each fails **by name** when its parameter is deleted. `_duplicate_ratchet_keys` reaches all
three literals and produces no false positive I could construct. The guards are in CI. On the
question six rounds have been asking, this branch has converged.

The new High is somewhere no round has looked: **the restart feature itself, exercised
concurrently.** `POST /_restart` is a new endpoint, `respawn()` is a new function, and `--restart`
is a new flag — and the branch puts a button that calls them on five page types whose design
explicitly anticipates several stale tabs being open at once. Two of those tabs pressing Restart
leaves the pidfile naming a **dead** process, after which the two commands the page's own fallback
`<details>` tells the reader to run both fail — one permanently, one by reporting success about a
server that is still running and then deleting the last pointer to it.

I found this by running the server end to end under a redirected `HOME` on a non-default port,
not by reading it. It reproduced on 4 of 5 concurrent-restart attempts and deterministically via
the isolated root cause.

---

## Findings

### [High] Two concurrent restarts leave the pidfile naming a dead pid, and both documented recovery commands then fail

**Where:** `scripts/explainer-serve.py:1139` (`Handler._restart`), `:1307` (`respawn`),
`:1264` (`start`), and the commands embedded by `scripts/page_chrome.py:149` (`restart_commands`)

**What:**

`_restart` spawns a detached child per request, with nothing serialising it — and note the
contrast with its sibling one screen below, which *was* given a lock:

```python
    def _restart(self) -> None:
        ...
        pid = os.getpid()
        self._send(200, json.dumps({"ok": True, "pid": pid}).encode(), "application/json")
        ...
        subprocess.Popen([sys.executable, str(pathlib.Path(__file__).resolve()),
                          "--respawn", str(pid)],
                         start_new_session=True, ...)
```

```python
    def _regenerate(self, payload: dict) -> None:
        ...
        with REGEN_LOCKS_GUARD:
            lock = REGEN_LOCKS.setdefault(want, threading.Lock())
```

`REGEN_LOCKS` is the only lock in the file (`:124-125`). Concurrent *regenerate* was thought
about; concurrent *restart* was not.

The damage lands in `start()`, whose success test asks the wrong question:

```python
def start() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    if port_busy(HOST, PORT):            # (1) pre-check
        ...
        return 0
    pid = os.fork()
    if pid > 0:
        PIDFILE.write_text(str(pid))     # (2) pidfile written before the child has bound
        for _ in range(20):
            if port_busy(HOST, PORT):    # (3) "is A listener there", not "is MY child listening"
                break
            ...
        if not port_busy(HOST, PORT):
            print(f"FAIL: forked pid {pid} but nothing is listening ...")
            return 1
        print(f"serving {ROOT} on http://{HOST}:{PORT}  (pid {pid})")
```

Two `--respawn` children both pass (1) in the window after the old server dies and before the
winner binds. The loser forks a grandchild that dies of `EADDRINUSE`, but (2) has already written
that dead pid over the winner's, and (3) sees the **winner's** socket and reports success for it.

**Measured**, isolated from `_restart` entirely — two concurrent `start()` calls, fake `HOME`,
port 7893:

```
--- A said --- serving ... on http://127.0.0.1:7893  (pid 1110)
--- B said --- serving ... on http://127.0.0.1:7893  (pid 1109)
--- actually listening: 1109 ---
   pid 1110: DEAD — but start() printed 'serving' for it
--- pidfile: 1110 ---
```

Via the button, reproduced on 4 of 5 attempts (`pidfile=98403 listening=98402`,
`pidfile=395 listening=392`, `pidfile=427 listening=426`, `pidfile=466 listening=464`).

**Why it matters:** the consequences fall squarely on the recovery path this branch exists to
build. With the pidfile naming a dead pid, both commands in `restart_commands`' `<details>` — the
ones its docstring calls *"the one to remember: works up OR down"* — are broken:

```
$ python3 scripts/explainer-serve.py --restart
2026-09-15 11:35:42 NOT RESTARTED — port 7893 was still busy 20s after SIGTERM to pid 98403.
Something else may be holding it; check with: lsof -nP -iTCP:7893 -sTCP:LISTEN
rc=1
--- still the SAME old server? --- {"pid": 98402}
```

`respawn` skips the kill because `pid_alive(98403)` is false, then burns 20s waiting for a port
held by the server it was supposed to replace, and blames *"something else"*. This does not heal:
every subsequent `--restart` fails the same way, 20s each time.

```
$ python3 scripts/explainer-serve.py --stop
not running
rc=0
--- but is it still serving? --- {"pid": 98402}
--- pidfile after --stop: --- (unlinked)
```

`--stop` reports *"not running"* about a server that **is** running, exits 0, and unlinks the
pidfile — destroying the last record of the pid, so nothing in the tool can find it again. A
reader now has a docs server serving stale code, a CLI that says it is stopped, and a restart
command that says something else holds the port. That is this project's own
*"a green check over the wrong subject"* shape, in the product.

I also observed a straggler `--respawn` child, having waited out its 20s, **bind the port ~20s
after a deliberate kill** — so a `--stop` can be silently undone by a loser from an earlier
restart.

**Novelty — this is new to the branch, and I checked rather than assumed.** `start()` is
byte-identical to master (`diff` of the function across `origin/master...HEAD`: no output).
Master has **no** `respawn`, no `--restart`, no `/_restart`, and exactly one caller of `start()`
— the CLI default path. The latent TOCTOU is old; this branch is what makes `start()` re-entrant,
by putting a button that calls it into five pages and adding a second CLI entry point.

Not Blocking: page serving is unaffected, and pressing the button once more *does* recover the
state (verified — `_restart` uses `os.getpid()`, not the pidfile, so it is immune to the pidfile
it corrupts). High because the failure is reproducible, silent at the moment it happens, and
disables the documented fallback precisely for the reader who has reached for it.

**Suggested fix** *(hypothesis, not verified)* — two parts, because the lock alone leaves the lie
in place:

1. Serialise `_restart`. The competing requests are two threads of one `ThreadingHTTPServer`, so
   a module-level `RESTART_LOCK` plus an in-flight flag is sufficient: the second caller gets the
   same `{"ok": true, "pid": …}` without spawning a second child, and the button's `rwait` is
   satisfied by the one restart that does happen.
2. Make `start()` verify **its own** child. `port_busy` cannot distinguish "my child bound" from
   "somebody's did". Either `waitpid(pid, WNOHANG)` to notice the child died, or have the child
   report its bind result through a pipe, and only then write the pidfile — so a failed bind
   prints the existing `FAIL:` line instead of a false `serving`.

---

### [Low] `_duplicate_ratchet_keys` raises `TypeError` on a chained assignment target

**Where:** `scripts/check-fixture-variation.py:891` (`_duplicate_ratchet_keys`)

**What:**

```python
        names = {getattr(t, "id", None) for t in node.targets}
        ...
                    dupes.append(f"{sorted(names)[0] if names else '?'}: {k.value!r} "
```

For `obj.attr = EXEMPT = {...}`, `names` is `{None, "EXEMPT"}` — the `Attribute` target yields
`None` — and `sorted()` over a mixed `str`/`None` set raises. Measured:
`EXCEPTION: TypeError: '<' not supported between instances of 'str' and 'NoneType'`.

**Why it matters:** barely. The shape appears nowhere in the file, and the failure is a loud
crash inside the self-test, not a silent pass — the opposite of the r5 defect. Reported only
because the function is the sole guard for its class.

**Suggested fix** *(hypothesis)*: `sorted(n for n in names if n)`.

---

### [Low] The duplicate check also scans the self-test's own fixture literals

**Where:** `scripts/check-fixture-variation.py:891`, read against `_self_test`'s
`global EXEMPT, KNOWN_UNVARIED, EXAMINED_KEYS   # blocks below swap these`

**What:** `ast.walk` descends into function bodies, so the literals the suite assigns to those
three names as *fixtures* are scanned with the same rule as the real ratchets.

**Why it matters:** no false positive today (measured: the real file reports `[]`). But a future
case that deliberately builds a fixture containing a repeated key — the natural way to test this
very function against a realistic literal — would be reported as a defect in the file.

**Suggested fix** *(hypothesis)*: restrict to module-level nodes (`tree.body`) rather than
`ast.walk`, which is also the population the docstring describes ("this file's three ratchet
literals").

---

### [Low] `restart_control` is the one new function with no mutation entry

**Where:** `scripts/mutations/page_chrome.json` (13 entries), `scripts/page_chrome.py:172`

**What:** the two entries added this round cover `repo_root` and `restart_commands`. Nothing
mutates `restart_control` — in particular its `_html.escape(...)` of the embedded commands.

**Why it matters:** low. The escaping is a single well-understood call and the manifest's
anchor-collision rule is a real constraint the branch already documented. Noted as a stated gap
rather than a demand.

---

## What I verified, and how

**r5's fix, independently.** Read the **effective** dict by importing the module, not by reading
the source — the r5 defect was invisible to anything that read the source:

```
EFFECTIVE explainer-serve.py: src_root_help.observed, src_root_help.pidfile   (19 pins total)
EFFECTIVE page_chrome.py:     chrome_bar.restart, repo_root.start,
                              restart_commands.root, restart_control.root      (14 pins total)
```

Then deleted each pinned parameter, one per throwaway copy, over a control proved green (`rc=0`):

| mutation | rc | named? |
|---|---|---|
| `repo_root` loses `start` | 1 | `` `repo_root.start` was examined and is NOT any more `` |
| `src_root_help` loses `pidfile` | 1 | `` `src_root_help.pidfile` … `` |
| `src_root_help` loses `observed` | 1 | `` `src_root_help.observed` … `` |
| `chrome_bar` loses `restart` | 1 | `` `chrome_bar.restart` … `` |
| `restart_commands` loses `root` | 1 | `` `restart_commands.root` … `` |
| `restart_control` loses `root` | 1 | `` `restart_control.root` … `` |

6 of 6. The r5 High is genuinely fixed.

**`_duplicate_ratchet_keys`, adversarially.** Injected a duplicate key into each of the three
literals in turn — **all three are reached** (`EXEMPT: 'DUPE_TARGET.py' (line 537)`,
`KNOWN_UNVARIED: … (line 151)`, `EXAMINED_KEYS: … (line 274)`), each turning the suite red.
Constructed-source probe, 12 shapes: detects `AnnAssign` (the real shape), plain `Assign`,
implicit string concatenation (`'ex' 'ample.py'` folds to one `Constant` and is caught), and a
duplicate straddling a `**spread`. No false positive on an unrelated dict. Misses `|=`,
`.update()`, `dict(...)`, conditional assignment and nested dicts — none of which the file uses.

**The shape I expected to be a hole, and is not.** A *second whole assignment* of
`EXAMINED_KEYS` — the same "a later definition silently replaces an earlier one" class, one level
up, and the same authoring mistake that produced r5 — is invisible to `_duplicate_ratchet_keys`
(`duplicate report: []`, and `repo_root.start still pinned? False`). But it is caught loudly by
the existing bidirectional population check: the population run goes `rc=1` with 50 findings and
the self-test reports `discovered but NOT pinned: [...]`. Not a finding.

**Class search for the r5 defect.** Parsed all 57 Python files under `scripts/` with `ast` and
compared every dict literal's constant keys: **0 duplicate keys repo-wide.** The guard is
instance-scoped to one file, but the class is currently clean, so that is an observation and not
a finding.

**`__doc__` read / `python -OO`.** `python3 -OO … --self-test` prints `64/64 passed` then
`CANNOT RUN — this file's docstring no longer declares a case count … Treat this as NOT CHECKED.`
and exits **2**. Reports, does not crash.

**CI.** `.github/workflows/ci.yml:287` runs the population check and `:290` runs
`--self-test` — so `_duplicate_ratchet_keys`, which is called only from the suite, does execute in
CI. `check-fixture-variation.py` is also pinned in `check-selftest-counts.py:97`, so the declared
64 is verified by running it.

**The two new mutation entries**, applied to the delivered file over a green control (`76/76`):
both go red via the case they name — `from a linked worktree, repo_root resolves to the MAIN
checkout` (1 red case) and `` `cd` parses to exactly one operand for 'some repo' `` (4 red cases,
the named one among them). `EXPECTED_MUTATIONS["scripts/page_chrome.py"] = 13` matches the
manifest's actual 13 entries.

**The `gen-dashboard` F3 anchor fix, and its class.** The fix binds to `_fragment(_bh2, …)`, which
raises when the card is missing. Searched for the same positional-read shape across every
generator that emits `chrome_bar` (`brief-compose`, `gen-goals-page`, `gen-dashboard`,
`gen-backlog-page`, `page_chrome`): the only other positional `<summary>` reads are
`gen-dashboard.py:2189` and `:2542`, both already slicing a **fragment**, and
`page_chrome.py:648`, which slices `restart_control()`'s own output. No second instance.

**Whole-branch sanity.** Every `--self-test` under `scripts/`: **50 green, 1 red, 6 files with no
suite.** Key suites: `explainer-serve 131/131`, `page_chrome 76/76`, `gen-dashboard 325/325`,
`check-fixture-variation 64/64`, `check-plan-code 128/128`, `check-ratchet-contract 41/41`,
`check-guard-coverage 37/37`, `check-dashboard-entry 148/148 + 13/13`, `check-selftest-counts
18/18`, `check-anchors 15/15`, `check-docs 13/13`, `check-explainer-delivery 8/8`. Nine guard
population runs all `rc=0`.

**The one red, and it is not this branch's.** `scripts/subject_status.py --self-test` is `16/17`,
`rc=1`, on the failing case *"the parked schema reports UNSHIPPED, not SHIPPED"* — the parked
blob-addressing subject, unrelated to anything here. The branch does not touch the file (last
commit to it: `342ac2e1`, PR #118) and it is **not a CI step**, so it is red on master too and CI
never sees it. Flagged for the coordinator because this project treats a red check as a stop, not
as a finding against PR #295.

---

## Sandbox note

The server was exercised only in a throwaway copy with `HOME` redirected to a scratch directory
and `PORT` changed from 7391 to 7893. No `pkill`/`killall` was used at any point — every process
I started was killed by the exact pid I had recorded, and the straggler respawn child was
identified with `ps -p` before being killed. No `git` command mutated the main working tree.
Confirmed after the run: the user's live server is still listening on 7391 as pid **53110**, and
it answers `/_alive` with `not found` — it is running master's code, which has no such endpoint,
which is itself evidence I never touched it.
