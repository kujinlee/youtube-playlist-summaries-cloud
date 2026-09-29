# Adversarial review — round 1 — Claude half — `explainer-src-root-self-configures` (PR #295)

Subject: `git diff origin/master...HEAD -- scripts/` at `3d2728c6`, merge base `939c97b4`.
Three files, +463/−10: `scripts/explainer-serve.py`, `scripts/page_chrome.py`,
`scripts/gen-dashboard.py`.

**Verification posture.** Everything below marked *measured* was run in the worktree or in a
copy under my own scratch. No tracked file was modified; the one mutation was applied to
`cp -R scripts` in a temp tree. Guards run green on the branch as delivered:
`page_chrome --self-test` 68/68, `explainer-serve --self-test` 109/109, `gen-dashboard` 325/325,
`gen-goals-page` 75/75, `gen-backlog-page` 165/165, `brief-compose` 125/125,
`check-fixture-variation`, `check-selftest-counts`, `check-ratchet-contract`, `check-docs`,
`check-gate-falsifiability`, `check-theme-token-coverage` all rc=0.

## Verdict

**FINDINGS** — 1 Blocking, 1 High, 4 Medium, 3 Low.

The Blocking is the branch's own central claim failing on a common input, and failing *silently
wrong* rather than loudly: for any repo path containing a space, the pasted remedy runs a
different checkout's `explainer-serve.py`. The High is that the one guard written for the
measured worktree defect cannot fail on that defect — proven by mutation.

---

## Findings

### [Blocking] The pasted commands are not shell-quoted — a repo path with a space makes the paste run a DIFFERENT checkout's server script

**Where:** `scripts/page_chrome.py:145`, `scripts/explainer-serve.py:470-471`

**What:**

```python
# page_chrome.py:145
    return f"cd {root}\npython3 scripts/explainer-serve.py --restart"
```

```python
# explainer-serve.py:470-471
    stop = f"python3 {repo}/scripts/explainer-serve.py --stop"
    start = f"python3 {repo}/scripts/explainer-serve.py"
```

The path is interpolated raw. `_html.escape` at `page_chrome.py:163` makes it safe for *HTML*;
nothing makes it safe for the *shell* it is explicitly written to be pasted into
(`page_chrome.py:136` — *"The exact terminal commands that bring the server back"*;
`explainer-serve.py:461` — *"a remedy that can be PASTED"*).

**Why it matters — measured, not reasoned.** I built two checkouts, one at a path containing a
space, and pasted the two embedded lines verbatim into `bash` while standing in the other:

```
$ cd /Users/…/scratchpad/elsewhere
$ cd /Users/…/scratchpad/My Repos/yps
bash: line 1: cd: /Users/…/scratchpad/My: No such file or directory
$ python3 scripts/explainer-serve.py --restart
!! THE WRONG SCRIPT IN THE CURRENT DIRECTORY RAN !!
```

The `cd` fails, the shell continues, and because line 2 is a **relative** invocation the paste
silently restarts the server from whatever checkout the reader happened to be standing in. This
is precisely the outcome `repo_root`'s own docstring names as worse than saying nothing
(`page_chrome.py:112-115`: *"a dead path within the hour, which is worse than no instruction,
because it fails after the reader has already trusted it"*) — reached through the quoting axis
instead of the worktree axis.

`src_root_help` fails the same way. Measured with `repo=/Users/kujinlee/My Repos/yps`:

```
  python3 /Users/kujinlee/My Repos/yps/scripts/explainer-serve.py --stop
```

→ `can't open file '/Users/kujinlee/My': [Errno 2] No such file or directory`.

**The fixtures walked past it.** Both suites use space-containing paths and assert only
containment: `page_chrome.py:562` `_root = pathlib.Path("/tmp/some repo")`, `:577`
`_root2 = pathlib.Path("/tmp/another checkout")`, `explainer-serve.py:1650`
`_other = pathlib.Path("/tmp/another checkout")`. Every case asks *"is the string in the
output?"*; none asks *"would a shell run it?"*. The variation `check-fixture-variation` forced
is real, but it varied the value and not the property.

Paths with spaces are ordinary on macOS, which is this project's stated platform, and this
project's own scratch paths contain them.

**Suggested fix (hypothesis, not verified):** `shlex.quote(str(root))` at both sites, and add a
falsifying case per site that is not a substring test — e.g. assert
`shlex.split(line) == ["cd", str(root)]` for the `cd` line and
`shlex.split(stop)[1] == f"{repo}/scripts/explainer-serve.py"`, driven by a fixture root
containing a space, a single quote and a `$`. A substring test cannot express this property, so
adding one would repeat the miss.

---

### [High] Both self-test cases written for the measured worktree defect pass unchanged when the entire fix is deleted

**Where:** `scripts/page_chrome.py:596-599`, guarding `repo_root` at `:105-133`

**What:**

```python
# page_chrome.py:596-599
    case("the default root is a checkout that outlives a worktree",
         (repo_root() / "scripts" / "explainer-serve.py").is_file(), True)
    case("…and it is not the linked worktree this may be running from",
         ".git" in str(repo_root()), False)
```

**Why it matters.** The defect these cite is named one screen up (`page_chrome.py:110-116`):
building from a worktree embedded `/…/scratchpad/wt`. Check both assertions against that exact
broken value — measured in this worktree:

```
here (the broken fallback) = /Users/…/62196080-…/scratchpad/wt
  (here/"scripts"/"explainer-serve.py").is_file() = True     # case 1 expects True  → PASSES
  ".git" in str(here)                             = False    # case 2 expects False → PASSES
```

A linked worktree is a full checkout, so it has `scripts/explainer-serve.py`; and its path does
not contain `.git` — `--git-common-dir` is what contains `.git`, never the worktree directory.
Case 2's predicate is about the string the *fixed* code produces an ancestor of, not about
anything the broken code produces.

Proven by mutation. I copied `scripts/` to a temp tree and inserted one line that deletes the
whole git resolution:

```python
    here = pathlib.Path(__file__).resolve().parent.parent
    return here  # MUTATION: the measured worktree defect
    try:
```

Result: **`68/68 passed`.** `repo_root()` returned the loaded location. No case died.

So the branch's answer to the worktree defect is, by this repo's own standard, unguarded: the
mechanism can be removed without a red. `scripts/mutations/page_chrome.json` has 11 entries and
I read all of them — none touches `repo_root`, `restart_commands` or `restart_control`, so the
`--mutate .` harness does not cover it either. This is the *"Fixing a PREMISE is not covering
the BRANCH"* / *"unfalsifiable guard"* shape, in the fix for a defect the branch says it
measured.

**Suggested fix (hypothesis, not verified):** make `repo_root` take the starting directory as a
parameter (`repo_root(here: pathlib.Path)`), so the suite can create a real `git worktree add`
under `tmp_path` and assert `repo_root(wt) == main and repo_root(wt) != wt`. That is a case the
mutation above kills. The current cases cannot be repaired by rewording, because neither
predicate can distinguish the two candidate answers.

---

### [Medium] `src_root_help`'s no-fallback arm prints two commands inside a directory it has just said does not exist — and reintroduces the `<placeholder>` the function exists to remove

**Where:** `scripts/explainer-serve.py:482-485`

**What:**

```python
# :482-485
    return (f"no source root — {SRC_ROOT_ENV} is unset and the fallback {repo} is not a "
            f"directory, so there is nothing to serve sources from.\n\n"
            f"  {stop}\n"
            f"  {SRC_ROOT_ENV}=<an-existing-checkout> {start}\n")
```

`stop` and `start` are `python3 {repo}/scripts/explainer-serve.py …` (`:470-471`). This arm is
reached only when `REPO.is_dir()` is False (`:456`), so **both printed commands name a file
inside a directory the same sentence declares absent**. Measured:

```
no source root — EXPLAINER_DOCS_ROOT is unset and the fallback /Users/kujinlee/moved-away/yps
is not a directory, so there is nothing to serve sources from.

  python3 /Users/kujinlee/moved-away/yps/scripts/explainer-serve.py --stop
  EXPLAINER_DOCS_ROOT=<an-existing-checkout> python3 /Users/kujinlee/moved-away/yps/scripts/explainer-serve.py
```

Both lines are guaranteed `[Errno 2]`. And `<an-existing-checkout>` is the same unfilled
placeholder as the `<dir>` this function was written to kill (`:464-465`).

The suite scopes around it rather than catching it: `:1641` is
`case("help: the common arm leaves no unfilled <placeholder>", lambda: "<" not in src_root_help("/nope", root))`
— the *common* arm only. There is no case on the other arm's runnability.

**Why it matters.** This arm is the one a reader meets when their checkout has moved or been
deleted — the state in which they have the least context to repair a broken instruction. The
branch's whole thesis is that an instruction the reader cannot act on is a failure description
wearing the shape of a remedy; this arm is that, twice.

**Suggested fix (hypothesis, not verified):** in this arm, name the running interpreter's own
script by `pathlib.Path(__file__).resolve()` (which *does* exist — the process is running from
it) rather than `{repo}/scripts/…`, and drop the placeholder by telling the reader the shape of
what to supply in prose rather than in a line they are invited to paste.

---

### [Medium] `repo_root()` and `REPO` are two different answers to "which checkout", and following the page's own instruction changes what `/src/` serves

**Where:** `scripts/page_chrome.py:105-133` vs `scripts/explainer-serve.py:109`, `:456`

**What:** `repo_root()` deliberately resolves to the **main** checkout
(`:133 return main if common.name == ".git" and (main / "scripts").is_dir() else here`), while
the running server's `REPO = SCRIPTS.parent` is the copy it was **loaded from**, and
`src_root()` now falls back to exactly that (`:456 return REPO if REPO.is_dir() else None`).

Measured in this worktree:

```
page_chrome.repo_root() = /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
explainer-serve REPO    = /Users/…/62196080-…/scratchpad/wt
```

**Why it matters.** The page served by the worktree server tells the reader to `cd` to the main
checkout and restart. Doing so replaces a server whose `/src/` serves the worktree with one
whose `/src/` serves main — so every `/src/` link to a file that exists only on the branch
starts 404-ing, as a side effect of pressing a button labelled "Restart server". Nothing in the
page, the log, or `--status` says the checkout changed. Two functions in one PR now disagree
about a term the PR introduced.

Second, transitional half, measured: `git show origin/master:scripts/explainer-serve.py |
grep -c -- '--restart'` → **0**. Until this branch merges, every page generated from a worktree
embeds `cd <main checkout>` + `--restart` against a `master` copy that has no such flag, so the
paste dies in `argparse`. That resolves on merge; the structural half above does not.

**Suggested fix (hypothesis, not verified):** have `restart_control` take the root from the
*server's* notion of itself rather than deriving a second one — or, if the main checkout is
genuinely the right target, say so in the page text (*"restarts from the main checkout"*) so the
consequence is visible rather than surprising.

---

### [Medium] `--restart` does not "work whether or not the server is up" when the pidfile is stale — and `start()` can manufacture exactly that state

**Where:** `scripts/explainer-serve.py:1203-1240`, `:1158-1185`, claim at `page_chrome.py:138-142`

**What:** the page asserts one command covers every case:

```python
# page_chrome.py:138-140
    ⚠ ONE command, and it is the same one whether the server is running or dead —
    `--restart` skips the kill when nothing is alive and goes straight to starting.
```

`respawn` has three inputs, not two:

```python
# :1221-1229
    if pid_alive(old_pid):
        assert old_pid is not None
        os.kill(old_pid, signal.SIGTERM)
    deadline = time.monotonic() + 20
    while port_busy(HOST, PORT) and time.monotonic() < deadline:
        time.sleep(0.1)
    if port_busy(HOST, PORT):
        … return 1
```

`--restart` passes `read_pid(PIDFILE)` (`:1726-1727`). `read_pid` returns `None`
on any `OSError`/`ValueError` (`:703-707`) and `pid_alive(None)` is `False` (`:710-712`,
asserted at `:1462`). So with a **live server and a missing or stale pidfile**, nothing is
SIGTERMed, the port stays busy, and the command blocks for 20 s and returns 1 — neither
restarting nor reporting the real cause. `status()` already knows this state exists (`:1248`
prints `⚠ stale — that pid is gone`), so it is not hypothetical; `stop()` shares the limitation
(`:1187-1193`) but `stop()` never claimed to cover both cases.

The state is also reachable from this branch's own new concurrency. Quoted, `start()`:

```python
# :1166-1174
    pid = os.fork()
    if pid > 0:
        PIDFILE.write_text(str(pid))
        for _ in range(20):
            if port_busy(HOST, PORT):
                break
```

`PIDFILE` is written *before* anything verifies that this fork is the process that bound the
port. Two Restart presses (two tabs; the `rs.disabled=true` guard at `page_chrome.py:298` is
per-document) spawn two detached `--respawn` children; both wait out the same port release, both
call `start()`, one loses the bind, and the loser's parent sees `port_busy` True on the first
iteration — because the *winner* holds it — and reports success having already written the dead
child's pid. **UNVERIFIED:** I did not race it; the check-then-bind window is milliseconds and I
did not want to bind port 7391 on this machine. The `PIDFILE.write_text`-before-verification
ordering is quoted fact, and the stale-pidfile consequence above is fully determined by quoted
code.

**Suggested fix (hypothesis, not verified):** when `port_busy` is true and `pid_alive(old_pid)`
is false, resolve the listener rather than waiting blind (`lsof -nP -iTCP:{PORT} -sTCP:LISTEN`
is already in the failure note at `:1228-1230`) — or fail fast with that message instead of after
20 s. Separately, move `PIDFILE.write_text` after the port check in `start()`, and write the pid
that actually bound.

---

### [Medium] The module comment still documents `/src/` as off by default, 240 lines above the code that turned it on for every checkout

**Where:** `scripts/explainer-serve.py:209-213` vs `:456`

**What:**

```python
# :209-213  — unchanged by this branch
# OPTIONAL second read-only root, for pages that want to link at the SOURCE they were derived from.
# Off unless `EXPLAINER_DOCS_ROOT` names a directory, so this file stays project-independent — it
# still knows nothing about any particular repo, only that it may be pointed at one (backlog #40).
```

`:456` now returns `REPO` when the env var is unset, so the sentence *"Off unless
`EXPLAINER_DOCS_ROOT` names a directory"* is false as of this commit. The correction lives only
in `src_root`'s docstring (`:429-453`), which a reader arriving at the constant does not see.

**Why it matters, measured.** This is not a cosmetic doc nit — the comment is the only statement
of the subsystem's *reach*, and the reach changed from nothing to the whole repo. Walking the
worktree with `SERVABLE = {".html",".md",".css",".js",".svg",".png"}` (`:207`): **1,342 files
are now reachable at `/src/`** without anyone opting in (1,287 under `docs/`, 40 under
`.agents/`, 2 under `.claude/`). `git ls-files --others --ignored` matching those extensions:
0 here, but `node_modules/` is not installed in this worktree and would be reachable in a real
checkout.

I do not think this is a security finding: `safe_path` (`:219-244`) resolves before the
containment test so `..` and symlinks are collapsed, `SERVABLE` excludes `.env*` (`.env.local`
has suffix `.local`), the listener is `127.0.0.1` (`:103`), and `_send` (`:925-932`) emits no
CORS header. It is a *silent widening* finding — the exact mirror of the bug being fixed, where
a subsystem changed state and no sentence changed with it.

**Suggested fix (hypothesis, not verified):** rewrite `:209-213` to state the new default and
what it reaches, and say the env var's remaining job is pointing at a *different* checkout — the
sentence at `:448-449` already drafts.

---

### [Low] `POST /_restart` is unauthenticated, bodyless and preflight-free, so any page in the browser can restart the server

**Where:** `scripts/explainer-serve.py:1125-1126` (route), `:1033-1072` (handler), `:929-930`

**What:** the route is matched before any body handling:

```python
# :1125-1126
        if route == "/_restart":
            return self._restart()
```

and `_restart`'s docstring argues its safety from parameterlessness:

```python
# :1047-1049
        ⚠ Takes NO parameters — no path, no argument, no command. The allow-list argument
    `_regenerate` makes is stronger here by having nothing to allow.
```

That answers argument injection, not invocation. A cross-origin `fetch(…, {mode:'no-cors'})` or
an auto-submitted `<form action="http://127.0.0.1:7391/_restart" method="POST">` is a *simple
request* — no preflight — and the side effect lands even though the response is opaque. The
comment at `:929-930` (*"no CORS header is needed — and its absence is what stops any OTHER site
… from reading private source"*) is about reading, and is correct about reading.

Impact is bounded: a local docs server is killed and respawned. The class is pre-existing
(`/regenerate` and `/questions` are equally reachable by a `text/plain` form POST, since the
handler never checks `Content-Type`), but `/_restart` is the first endpoint that needs **no body
at all**, which is what makes it a one-liner. **UNVERIFIED:** not exploited; I did not run a
browser against the live server.

**Suggested fix (hypothesis, not verified):** reject POSTs whose `Origin` header is present and
is not `http://127.0.0.1:7391`. Same-origin `fetch` sends `Origin` on POST, so the button still
works and a foreign page is refused; a header-less curl is unaffected, which is the correct
trade for a loopback tool.

---

### [Low] `.restart.log` has no reader — the trace exists, nothing points a person at it

**Where:** `scripts/explainer-serve.py:1200`, `:1217-1219`, `:1243-1250`, `page_chrome.py:305-306`

**What:** the design argument is explicit (`:1217-1219`): *"a restart that did not happen must
leave a trace somewhere a person can look"*, writing `RESTART_LOG = ROOT / ".restart.log"`.
Nothing tells them where. `status()` prints four lines and the log is not one:

```python
# :1243-1250
    print(f"listening : …"); print(f"pidfile   : …")
    print(f"explainers: {n} in {ROOT}"); print(f"questions : {QUESTIONS}…")
```

and the page's failure text is `'restart FAILED: '+e.message+' — run the commands below'`
(`page_chrome.py:305-306`) — it names the commands, never the log. The file is a dotfile in
`~/explainers` with a non-servable extension, so it appears in no index either.

**Why it matters.** The one failure this branch cannot report in-band is the one it writes to a
file nobody is told exists. That is this project's *"a gate's CHANNEL can be weaker than the
gate"* shape: the record is real and the delivery is zero.

**Suggested fix (hypothesis, not verified):** one line in `status()` — print `RESTART_LOG` with
its last line and mtime when the file exists — and append *"see ~/explainers/.restart.log"* to
the page's failure string.

---

### [Low] The new `<details>` is a flex item in the chrome bar, so expanding it re-centres every sibling control — UNVERIFIED

**Where:** `scripts/page_chrome.py:169-172` (markup), `:225-232` (CSS), `:195-196` (`.chrome`)

**What:** `.chrome{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap;…}` (`:195-196`),
and `restart_control` appends the `<details>` directly into that row (`:169-172`), before the
stamp, which is pushed right by `.chrome-when{margin-inline-start:auto}` (`:221`). Open, the
details grows to a two-line `<pre>`; with `align-items:center` its flex siblings — the theme and
refresh buttons — centre against that taller item.

**UNVERIFIED — I did not render it in a browser.** I state it because the branch adds no case
about the bar's layout at all, and this module's history (`:197-216`, backlog #79/#80) is of
chrome regressions that were only ever found by measuring rather than by reading. The existing
suite asserts only presence of ids.

**Suggested fix (hypothesis, not verified):** put the `<details>` outside the flex row (a sibling
of `<div class="chrome">`), or give the row `align-items:flex-start`; then look at it in both
themes before merging, per this project's Phase 4 rule.

---

## What I checked and did NOT find a defect in

Stated so the round reports its coverage, not only its hits.

- **Other positional `<summary>`/`<details>` reads.** Grepped `scripts/`, `.claude/`, `tests/`
  for `index("<summary>")`, `index("<details`, `count("<details`, `split("<summary>")`. Three
  sites in `gen-dashboard.py` (`:2189`, `:2221`, `:2542`) and one in `page_chrome.py` (`:590`).
  All three dashboard sites now slice a *card fragment* obtained by `_fragment(...)` or an
  explicit `<article …>` anchor, so no chrome `<details>` can reach them; `:590` slices `_rc`,
  the control's own string. `gen-dashboard.py:2365`
  `case("every details has an id", ht.count("<details id="), ht.count("<details"))` keeps
  passing because the new element is `<details id="chrome-restart-help" …>`. The F3 fix at
  `:2220-2222` is correct and `_fragment` raising on a missing card is the right ratchet.
- **Path escape.** `safe_path` (`:219-244`) resolves *then* tests `relative_to(root.resolve())`,
  so `..`, percent-encoding and symlinks-out are all collapsed first; the extension allowlist is
  applied after resolution. The `env`-set-but-wrong → `None` (not the fallback) rule holds on
  every branch I could construct, including a value naming a **file** (`:1624-1625` covers it) and a
  missing path; a relative value resolves against the server's cwd consistently in both
  `src_root` and `safe_path`.
- **Duplicate control ids via `brief-compose`.** `brief-compose.py:756-769` takes the
  `has_control` arm for a fragment that already carries a bar and adds nothing, so a composed
  dashboard does not get two `id="chrome-restart"` buttons. Suite green at 125/125.
- **The `<details>` fallback genuinely survives a dead server** — it is static markup with no
  script and no fetch, and `chrome_script` refuses `file://` with a reason
  (`page_chrome.py:296-297`). That part of the design holds.
- **`/_alive` pid-comparison logic.** `j.pid!==was` (`page_chrome.py:294`) with `again` wired as
  the rejection handler on both `.then` arms (`:292-294`) degrades correctly across the window
  where nothing is listening, and the 25 s deadline is bounded.
- **Declared counts.** `explainer-serve.py:67` says 109 and runs 109; `page_chrome.py:4` says 68
  and runs 68. `check-selftest-counts.py` green over 39 scripts.
