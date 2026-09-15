# Adversarial review — round 2, CLAUDE half — `explainer-src-root-self-configures` (PR #295)

Subject: `5e64d68b` (r1 fixes), `0037c6f4` (r1 ratchet), `b56a5a10` (r2 M1 fix-to-a-fix).
Everything below was **run**, on a copy at
`…/1d12d1a5-…/scratchpad/r2c/`, never in the worktree.

## Verdict

FINDINGS — 1 High, 1 Medium, 4 Low.

The delivered *code* in `b56a5a10` is correct: I could not break the emitted
`kill "$(cat …)"` line under eight hostile `HOME` values in a real `/bin/sh`. The High is that
**its guard is inverted** — the new cases go green on the broken code and red on the correct code.
That is the r1 H1 defect and the r1 B1 defect re-committed inside the r2 fix, in the one file that
did not receive the branch's own remedy.

---

## Findings

### [High] The new `kill` line's shell-quoting is guarded by a substring test — it passes on the unquoted code and FAILS on the quoted code

**Where:** `scripts/explainer-serve.py:543`, guarded by `scripts/explainer-serve.py:1755-1757`

**What:**

```python
543:            f"  kill \"$(cat {shlex.quote(str(PIDFILE))})\"\n\n"
```

```python
1755:        case("help: its recovery command is the pidfile, which lives outside every checkout",
1756:             lambda: (str(PIDFILE) in _arm and str(_gone) not in str(PIDFILE)))
```

`str(PIDFILE) in _arm` is the exact instrument `restart_commands`' own new comment condemns in the
same branch (`scripts/page_chrome.py:605-609`): *"every assertion above is `str(...) in ...` — which
is true of a line no shell can run … a hostile input asserted with a substring test proves nothing
about hostility."* `page_chrome` got the `shlex.split`-and-compare-ARGV treatment. `explainer-serve`,
which grew a **new** pasteable command in the very next commit, did not.

**Measured, three ways:**

1. **Mutation — delete `shlex.quote` from `:543`** (`f"  kill \"$(cat {PIDFILE})\"\n\n"`):

   ```
   self-test: 114/114 passed
   ```

   Green. No case can tell the quoted line from the unquoted one.

2. **The mutant is broken in production.** With `HOME=/tmp/fake home` (a space in the home
   directory is ordinary on macOS, this project's stated platform, and is the exact fixture r1 B1
   used), the mutant emits `kill "$(cat /tmp/fake home/explainers/.serve.pid)"`, and a real
   `/bin/sh` gives:

   ```
   cat: /tmp/fake: No such file or directory
   cat: home: No such file or directory
   cat: r2/explainers/.serve.pid: No such file or directory
   PID            <- i.e. kill ""
   ```

   The delivered line gives `PID 4242`. Both suites: **114/114**, under that same `HOME`.

3. **The oracle is INVERTED, not merely blind.** With `HOME=/tmp/it's home`:

   | tree | result |
   |---|---|
   | **delivered (correct, quoted)** | `FAIL: help: its recovery command is the pidfile` — **113/114** |
   | **mutant (broken, unquoted)** | **114/114 passed** |

   `shlex.quote` emits `'/tmp/it'"'"'s home/…'`, so the raw `str(PIDFILE)` is no longer a substring.
   The case rewards the absence of the fix and punishes its presence.

**Why it matters:** this is the branch's own two findings, recombined. r1 B1 (Blocking) was
"a pasteable command interpolates an unquoted path"; r1 H1 (High) was "the guard passes on the exact
broken value". The r2 commit message claims the new cases *"pin the PRODUCTION relationship"* — they
pin the *path*, and are silent about the *quoting*, which is the axis a reviewer already called
Blocking once on this branch. Nothing in `scripts/mutations/` covers `explainer-serve.py` either
(declared, honestly, in `0037c6f4`), so `--mutate .` cannot see this.

Blast radius today is a loud failure (`kill ""` exits 1, verified), not a silent one — that is why
this is High and not Blocking. But the *guard* is at the same standard the branch just rejected
twice, on code one commit old.

**Suggested fix (hypothesis, not verified end-to-end):** apply this branch's own r1 H1 remedy —
make the fixture injectable, then assert ARGV.

```python
def src_root_help(env_value: str, repo: pathlib.Path,
                  pidfile: pathlib.Path = PIDFILE) -> str:
```

⚠ **`shlex.split` cannot be used directly on this line, and that is a real trap** — verified:
`shlex.split('kill "$(cat \'/tmp/it\'"\'"\'s home/…\')"')` raises
`ValueError: No closing quotation`, because `shlex` does not re-open a quoting context inside `$( )`
the way `sh` does, while `/bin/sh` parses the same string correctly (`PID 777`). Split the
substitution out first:

```python
def _inner_argv(line):            # the argv a shell builds inside $( … )
    return shlex.split(line[line.index("$(") + 2:line.rindex(")")])

for _p in (pathlib.Path("/tmp/plain/x.pid"), pathlib.Path("/tmp/fake home/x.pid"),
           pathlib.Path("/tmp/it's home/x.pid"), pathlib.Path("/tmp/x; echo PWNED/x.pid")):
    _kill = [l.strip() for l in src_root_help("", _gone, _p).splitlines()
             if l.strip().startswith("kill ")][0]
    case(f"the kill line's substitution is exactly `cat <pidfile>` for {_p.parent.name!r}",
         _inner_argv(_kill), ["cat", str(_p)])
```

I ran `_inner_argv` over six hostile homes (space, apostrophe, `; echo PWNED`, `$(touch …)`,
embedded `"`, backslash): all six return `["cat", <the path>]`, matching what `/bin/sh` builds; and
it goes red on the unquoted mutant (`['cat', '/tmp/fake', 'home/explainers/.serve.pid']`).

A parameter also brings `src_root_help.pidfile` under `check-fixture-variation.py`, which today
examines `src_root_help.env_value` and `src_root_help.repo` and cannot see the pidfile at all
because it is a module global.

---

### [Medium] The SIBLING arm of the same function still emits commands under a directory that may not exist — the r2 M1 defect, one arm up

**Where:** `scripts/explainer-serve.py:500-508`

**What:**

```python
500:    script = shlex.quote(str(repo / "scripts" / "explainer-serve.py"))
501:    stop = f"python3 {script} --stop"
502:    start = f"python3 {script}"
503:    if env_value:
504:        return (f"no source root — {SRC_ROOT_ENV} is set to {env_value!r}, which is not a "
505:                f"directory.\n\n"
506:                f"Unset it to serve sources from the repo this server runs from ({repo}):\n\n"
507:                f"  {stop}\n"
...
```

`b56a5a10`'s reasoning is that `repo / "scripts" / "explainer-serve.py"` **is** `__file__` in
production, so a command naming it is guaranteed `[Errno 2]` when `repo` is gone. That reasoning
applies verbatim here — this arm was simply not re-read after the fix.

The arm is reachable with a missing `repo`: `src_root()` returns `None` for a set-but-bad env var
*without ever consulting `REPO`* —

```python
472:    v = os.environ.get(SRC_ROOT_ENV, "").strip()
473:    if not v:
...
478:        return REPO if REPO.is_dir() else None
479:    p = pathlib.Path(v).expanduser()
480:    return p if p.is_dir() else None
```

— and the caller is unconditional: `src_root_help(os.environ.get(SRC_ROOT_ENV, "").strip(), REPO)`
(`:1071`). So with `EXPLAINER_DOCS_ROOT` set to a stale path **and** the checkout moved (the
scenario the sibling arm exists for, and the one `repo_root`'s docstring says happens routinely with
worktrees), the reader is handed two `[Errno 2]` lines plus the sentence *"the repo this server runs
from"* about a directory that is not there.

**Why it matters:** compound trigger, so not Blocking — but this is the project's own
*after fixing, SEARCH for the class* rule, and the class is one function body wide. The r2 fix
established a recovery route that works when every checkout path is dead; this arm does not use it.

**Suggested fix (hypothesis):** guard the arm on `repo.is_dir()` and fall through to the pidfile
text when it is false — one branch, and it makes both arms share one story about what survives.

---

### [Low] The pidfile is now the SOLE recovery anchor, and it can legitimately be absent while the server is up

**Where:** `scripts/explainer-serve.py:543`, with `:1218-1224`, `:1247-1256`

**What:** `start()` returns early on a busy port and does **not** write the pidfile:

```python
1220:    if port_busy(HOST, PORT):
1221:        pid = read_pid(PIDFILE)
1222:        print(f"already serving on http://{HOST}:{PORT}" + (f" (pid {pid})" if pid else ""))
```

`stop()` unlinks it (`:1250`, `:1255`), `respawn()` unlinks it (`:1299`), and nothing re-creates it
for a server that is already listening. In that state the emitted instruction degrades to `kill ""`
(verified: bash `kill: \`': not a pid or valid job spec`, zsh `illegal pid:`, rc=1 in both) and the
reader — whose checkout is gone, so `--stop` is not available either — has no second route. The
failure is loud, which is the good half.

Related, and pre-existing rather than introduced here: `kill` sends SIGTERM to whatever holds that
number, with no check that it is the server. `stop()` is no better (`pid_alive` only asks whether
*a* process exists), so this is not a regression — but the pasted command also does not clean the
pidfile up afterwards the way `stop()` does.

**Why it matters:** this arm's whole claim is *"the one anchor that survives"*. One anchor with no
fallback is a single point of failure in a message that exists for the moment everything else failed.

**Suggested fix (hypothesis):** add the line `respawn()` already knows is the right one when the
pid route fails — `lsof -nP -iTCP:{PORT} -sTCP:LISTEN` (`:1290`) — as a second sentence: *"if that
prints nothing, find it with …"*.

---

### [Low] A manifest mutation makes `page_chrome`'s suite ABORT, so attribution survives only by tuple order

**Where:** `scripts/page_chrome.py:611-618`, `scripts/mutations/page_chrome.json` (`the pasted cd
stops being shell-quoted`)

**What:** applying the manifest's own entry (drop `shlex.quote`) and running the suite:

```
  [FAIL] `cd` parses to exactly one operand for 'some repo': got ['cd', '--', '/tmp/some', 'repo'] …
Traceback (most recent call last):
  File ".../page_chrome.py", line 618, in self_test
    shlex.split(_line), ["cd", "--", str(_hostile)])
ValueError: No closing quotation
```

The mutation is still attributed **only because `/tmp/some repo` is first in the tuple and prints its
`[FAIL]` line before `/tmp/it's here` raises.** Everything after `:618` — roughly 58 cases — is
unmeasured under that mutant, and `check-plan-code.py` would have reported
*"the suite went RED but printed no `[FAIL] <case>` line … NOTHING COULD SEE THE KILL"* had the
fixtures been ordered the other way. rc is 1 either way, so `caught` is right; only `attributed` is
load-bearing here.

**Why it matters:** this is the repo's own *a report format is a CONTRACT* shape, one fixture-order
swap away. Any future manifest entry whose `expect` names a case defined after `:618` would be
unattributable under this mutation.

**Suggested fix (hypothesis):** wrap the call —
`try: _got = shlex.split(_line) except ValueError as e: _got = f"UNPARSEABLE: {e}"` — so a mutant
produces a `[FAIL]` line for every fixture instead of a traceback.

---

### [Low] `repo_root.start` — the H1 remedy itself — is examined but not pinned in `EXAMINED_KEYS`

**Where:** `scripts/page_chrome.py:106`, `scripts/check-fixture-variation.py:272` (`'page_chrome.py'` entry)

**What:** running `check-fixture-variation.analyse()` over the delivered tree and over the branch
base `4b2eff05`:

```
== scripts/page_chrome.py
   already examined-but-unpinned BEFORE the branch: ['chrome_bar.restart', 'restart_commands.root', 'restart_control.root']
   NEWLY examined by this branch: ['repo_root.start']
```

The pin is one-directional (`:829-834` only reports `pinned - examined`), so an added key is never
required — the drift is **pre-existing**, and I say so rather than blaming it on this branch. But
`start` is not an ordinary parameter: it is the r1 H1 *remedy*, added precisely so the function can
be falsified. Deleting it takes `repo_root` out of the guard's field of view entirely — the r8 B1
scenario the file's own comment describes — and no `EXAMINED_KEYS` entry would notice.

Partial cover exists: if the parameter stops being *varied*, `analyse` reports it directly; if the
worktree cases are deleted, `check-selftest-counts.py` catches the 76→74 drift. The uncovered path
is parameter-and-cases removed together with the count updated.

**Suggested fix (hypothesis):** add `'repo_root.start', 'restart_commands.root',
'restart_control.root', 'chrome_bar.restart'` to `EXAMINED_KEYS['page_chrome.py']` and
`'src_root_help.env_value', 'src_root_help.repo'` to the `explainer-serve.py` entry, in this branch,
since it is the branch that made them matter.

---

### [Low] The r2 comment's own line reference was invalidated by the commit that wrote it

**Where:** `scripts/explainer-serve.py:527` (and the same claim in `b56a5a10`'s message)

**What:**

```python
527:    # false.** In production the caller is `src_root_help(..., REPO)` (`:1058`) and `REPO` is
```

Measured: at `0037c6f4` — the parent commit — the caller *was* at `:1058`. The comment block added
by `b56a5a10` is 13 lines long and sits above it, so the same commit moved the caller to **`:1071`**.
The two sibling references in the same sentence, `ROOT` at `:105` and `REPO` at `:115`, are still
correct because they are above the insertion point.

**Why it matters:** small, but it is this branch's own subject — the record of *why* a fix exists is
the artifact, and a reader following `:1058` today lands in the middle of the `/_stale` handler. The
repo already carries the lesson as *cite the SYMBOL, not the line*.

**Suggested fix (hypothesis):** `src_root_help(..., REPO)` at the `/src/` handler — no number.

---

## What I checked and could NOT break

Stated so a clean line is readable as a measurement rather than as silence.

**The `kill` line's quoting is correct.** Eight `HOME` values — plain, space, apostrophe,
`; echo PWNED`, `$(touch /tmp/pwn_r2)`, leading dash, embedded `"`, backslash — emitted through
`shlex.quote` and parsed by a real `/bin/sh`. Every one yielded exactly one operand; the
`$(touch …)` probe file was never created. Single quotes nested inside `"$( … )"` are valid POSIX
and bash/sh/zsh all agree.

**`kill` with a missing or empty pidfile is loud, not silent.** rc=1 in bash, sh and zsh; no signal
sent. `kill ""` is a usage error, not a broadcast.

**`repo_root(start=…)` breaks nothing downstream.** `repo_root` has exactly one caller in the whole
repo — `restart_control` at `scripts/page_chrome.py:187` — which still calls it with no argument;
`restart_control()` is itself called argument-less at `:375`. `grep` over `*.py`/`*.sh`/`*.json`
outside `page_chrome.py` finds no other caller (the `codex-review.py` hits are an unrelated local
variable of the same name). The five page generators reach this only through `chrome_bar`, whose
signature is unchanged.

**Both new manifest entries are real and attributable.** Applied by hand from the JSON onto the
delivered files — both anchors present, each went red **via the case it names**:
`repo_root loses its git resolution` → `[FAIL] from a linked worktree, repo_root resolves to the
MAIN checkout` (75/76); `the pasted cd stops being shell-quoted` → `[FAIL] \`cd\` parses to exactly
one operand for 'some repo'`. The dropped third entry is correctly dropped for a second reason the
commit does not give: removing `--` reddens **five** cases, and `check-plan-code.py:1325` refuses an
`expect` matching more than one.

**The worktree case exercises the intended branch.** `return here` inserted before the `git`
call reddens it, so it is not passing through the fallback.

**The `CANNOT RUN` case is the right call — but its message is wrong in one reachable case.**
Failing when git is unavailable matches the project's stated rule that cannot-run is a failure. With
`GIT_CONFIG_GLOBAL` setting `commit.gpgsign=true` and a broken `gpg.program`, git *is* available and
the fixture's `commit` fails, so the case fires saying *"git is unavailable"*. That environment
already reddens two pre-existing cases, and `check-selftest-counts.py` reports the red suite rather
than a bogus count, so nothing is mis-certified — but the sentence misattributes the cause. Not
filed as a finding; worth one word in the message (`git could not build the fixture`).

**Repo gates on the delivered tree:** `check-docs` rc=0, `check-selftest-counts` 39/39 verified,
`check-ratchet-contract` OK, `check-review-rounds` rc=0, `check-gate-falsifiability` OK,
`check-fixture-variation` OK, `check-explainer-delivery` OK, `check-plan-code --self-test` 128/128,
`explainer-serve --self-test` 114/114, `page_chrome --self-test` 76/76.

**Nit, not filed:** the hostile-fixture case names come from `_hostile.name`, and
`pathlib.Path("/tmp/a$(touch /tmp/pwn)").name` is `'pwn)'` — the fixture is a four-segment path, not
the single hostile component the name implies, and the case name a manifest `expect` must match
exactly is a derived value. Two fixtures sharing a `.name` would silently produce two identically
named cases.

**What would have had to be true for me to find more:** a Blocking here needed the emitted `kill`
line to misparse in a real shell for some reachable `HOME`, or the pidfile route to fail *silently*.
Neither holds — I ran both.
