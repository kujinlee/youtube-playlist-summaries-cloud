Reviewed head: 87e190d3eb177d0aad87823ca8962fc6677f457b

# Adversarial review — `harness-ships-elsewhere` slice B, round 1 (Claude half)

**Subject:** PR #594, `65e6f562..87e190d3` (head `87e190d3`) — marketplace-inventory plan Tasks 1-4:
`docs/portable-practices.md` D8 corrections, `scripts/mkt_isolate.py`, `scripts/mkt_stage.py`, the packaging spike
(`docs/marketplace/spike-record.md`, GO).
**Mandate:** refute "slice B is done and correct".

## Verdict: **NOT CONVERGED** — 0 BLOCKER, 3 MAJOR, 3 MINOR

The GO itself survives: I re-ran the spike's serve path in a fresh world (five-file payload, free port via
`EXPLAINER_SERVE_PORT`) and got start rc 0, `GET /` 200 with the sentinel token, `--stop` rc 0. The five-file
closure is complete for the spike's operations: the detached server's own audit events, which no record contains
(M1), show Python opening nothing outside the world and the interpreter's stdlib other than `/dev/null` and the
five staged scripts and their `.pyc`s. What fails is the instrument's account of what it saw, and two leak paths
that the spike happened not to take.

## Gates run (results)

| Check | Result |
|---|---|
| `python3 scripts/mkt_isolate.py --self-test` | `49/49 self-test cases passed`, rc 0 |
| `python3 scripts/mkt_stage.py --self-test` | `LIVE ok: …claude plugin validate…; not in the count below` / `63/63 self-test cases passed`, rc 0 |
| `python3 scripts/check-docs.py` | `Documentation integrity OK` |
| all-manifest anchor resolve (every edit's `old` text counted in its file, all `scripts/mutations/*.json`) | `anchors resolved: 5299/5299, manifests=98` |
| every `expect` of the two new manifests names a case in its script | 34/34, 47/47 |
| hand-applied mutations on temp copies (8) | each rc 1 with the NAMED case red: isolate #0 `drop audit hook`, #2 `the world env inherits the caller's`, #17 `read_audit accepts a line that is not an event`, #29 `run_isolated ignores the cwd it is given`; stage #3 `a declared file is flattened to its base name`, #11 `two declarations on one path: the second silently wins`, #22 `no packages stages an empty marketplace`, #40 `install returns a path that does not exist` |

## Findings

### M1 (MAJOR) — events from a process that outlives `run_isolated` are silently discarded, and the spike record states a false negative from that gap

`scripts/mkt_isolate.py` `run_isolated`: `log.write_text("")` empties the audit log at the start of EVERY run,
and the log is read once, when the top process exits. A detached child (the explainer server `start()` launches)
keeps writing events after its record has been read; the next `run_isolated` (`--stop`) truncates them unread. No
`unobservable` entry names this: the ALWAYS list covers non-Python processes, network and pre-sitecustomize
startup, not "a process that outlived the record".

**Breaking input (run):** world allowing `python3,git`, the five-file payload, `run_isolated(w, ["python3",
"<inst>/explainer-serve.py"], elsewhere, 60)` then `GET /`. The start record's `executed` is
`['<world>/bin/python3']`. The log read after `GET /` holds 111 further events, including
`exec git ['git', 'rev-parse', '--show-toplevel']` (from `source_setup`, reached through `serve_state()` on
`GET /`) and the server's opens of `regen-pages.py`. A following `--stop` record empties the log.

**Wrong output it produced:** `spike-record.md` → *Run 2*, the bound paragraph: *"`git`, which the world allows,
was never launched by these operations (each run's `executed` list is the world's `python3` alone)."* `git` WAS
launched, by the server, on every `GET /`. The row *"Python opens outside the world + stdlib … `/dev/null` only for
start"* likewise describes the launcher only; the server, the process that served `GET /` and loaded
`regen-pages.py`, is in no record. Run 1's `regen-pages.py` miss was found from `.serve.log`, not the capture,
which is this gap showing.

**Fix:** (1) in `run_isolated`, after the top process exits, compare the pids that wrote a `start` event with the
pids still alive; any live one adds an `unobservable` entry ("pid N outlived the record; its later file access is
NOT CAPTURED"), plus a case driving a detached grandchild. Or give each run its own log file instead of truncating
one, and have the record name late events. (2) Correct the spike record: `git rev-parse` IS run by `GET /` (it
falls back to `main` when git is absent, `_git_bytes` returns 127), and the server's opens come from a separate
read of the hook log, or say they were not captured.

### M2 (MAJOR) — `preflight` never checks the working directory, so a `--cwd` inside the repository leaks it and passes

`scripts/mkt_isolate.py` `main`: `cwd = Path(opts.cwd) if opts.cwd else …`, used unchecked; `run_isolated`
takes any `cwd`. The docstring says `preflight` returns *"every reason the author's environment would leak in"*,
and it checks the root, HOME entries, env, PATH, bindir and port, but not cwd.

**Breaking input (run):** `mkt_isolate.py --root <tmp>/w --allow python3,git --cwd <repo>/scripts --port 1 --
python3 -c "import mkt_stage, subprocess; …git rev-parse --show-toplevel…"` → rc 0, preflight clear, stdout
`IMPORTED <repo>/scripts/mkt_stage.py` and `<repo>` as git's toplevel. A stranger has neither. The spike used
`<world>/elsewhere` and is unaffected; Tasks 13-15 (seeded repo, tier A/B) pass cwds and depend on this.

**Fix:** refuse in `run_isolated` (where every caller passes through, not only the CLI) a `cwd` that resolves
inside `REPO`, or one outside `world.root` unless explicitly declared. Add a case and a mutation. Also consider
checking the git common toplevel (`git rev-parse --git-common-dir`'s parent) as well as `REPO`: run from a linked
worktree, `REPO` is the worktree, so a world root or cwd in the MAIN checkout passes `_inside(…, REPO)`.

### M3 (MAJOR) — staging ships untracked and gitignored files, which Task 6 will then bake into the shipping-set declaration

`scripts/mkt_stage.py` `_tree` / `plan`: everything on disk below a declared skill directory is shipped, and a
declared `files` entry is accepted whatever git thinks of it. The docstring states the bound (*"staging ships what
is on DISK … not what git tracks"*), but the consequence is exactly the brief's question: a stranger's run fails
where ours passes. Task 6 derives the shipping-set declaration from the INSTALLED tree, so a local-only file in the
author's checkout becomes a declared member that the published, git-tracked package will not contain.

**Breaking input (run):** a fixture repo with `.agents/skills/k/{SKILL.md,.DS_Store}` and a gitignored
`.env.local`; `stage([PackageSpec("p","0.0.1",[".agents/skills/k"],[".env.local"])], out, repo=…)` succeeds and
writes `p/skills/k/.DS_Store` and `p/.env.local`. "Refuses forbidden sources" covers only absent, absolute, `..`,
outside-the-repo and link cases; a gitignored secret is shipped without a word.

**Fix:** take the file population from `git ls-files` (tracked, at HEAD or in the index) and refuse, CANNOT RUN, any
on-disk file under a declared skill directory, and any declared file, that git does not track, naming it. Add the
two cases above. If disk-not-git staging is wanted for a probe, make it an explicit opt-in flag.

### m1 (MINOR) — the run-1 re-classification is defensible but the record does not say it overrode the plan's literal routing

Plan Task 4 Step 3 routes *"start printing `serving <world HOME>/explainers` with the pidfile pid = listener pid
and then `GET /` erroring"* to a recorded component FAILURE (NO-GO route, H3). Run 1 is that observation exactly.
The record invokes the FAILS IF exception ("a payload missing a member of the script's import closure … is a PLAN
defect"), counting an `importlib` load reached from a route as import closure. I agree with the reading: the
missing file exists in `scripts/`, and the failure says nothing about whether a plugin can install and run. But
the record says only that the plan's falsifier is "narrower" and does not say it chose between two plan clauses
that point opposite ways. **Fix:** one sentence in *The payload…* naming both clauses and why the exception
governs, so the owner can overrule it without re-deriving it.

### m2 (MINOR) — `isolation-baseline.md` claims two things by construction that are measurements of this machine

(a) *"the standard library only — nothing is installed into the world (by construction: no `pip` step exists)"*.
The world runs the author's interpreter with its site-packages on `sys.path`
(`…/Versions/3.14/lib/python3.14/site-packages`); measured there now: `pip`, `wheel`. True today on this machine,
and not by construction. A package the author installs later would be importable in every world. (b) Deviation
(c): system git config is read *"as a stranger's git would"*. Here it is `/usr/local/etc/gitconfig`:
`credential.helper=osxkeychain`, which answers from the AUTHOR's login keychain. The repository is public (`gh repo
view` → `PUBLIC`), so the tier-B clone does not depend on it today. **Fix:** list the world's
`importlib.metadata.distributions()` in the baseline as a measurement, and name the credential helper as a
deviation (or set `GIT_CONFIG_NOSYSTEM=1` and add it to `ENV_KEYS`). Checked and clean: `claude auth status` in a
world → `loggedIn: false`; `gh auth status` → not logged in. The keychain does not leak through either tool.

### m3 (MINOR) — `spend-log.md` rows are incomplete by design but the Task 3 slice has no row

The log is "one row per slice" and has rows for Task 2 and Task 4 but none for Task 3. It is a coordinator file,
so this may be intended at slice end. Note only.

## Numbers in the diff's prose (e)

Re-derived and holding: 49 and 63 case counts; `portable-practices.md` 1,780+2,907+450+438+3,546+1,252 = 10,373;
+604 (four SKILL.md at `a4f6d4b5`) +647 (363+73+211) = 11,624; 17 components = 6+4+3+4; 6,542/3,599 = 1.82;
`explainer-delivery.md` lines 118, 158, 235 at `a4f6d4b5` are the three `python3 scripts/` invocations;
`spike-record.md` citations `explainer-serve.py:101-103`, `:106`, `:110`, `:130`, `:2219-2223` and the 7-file
installed tree (`explain-topic` holds only `SKILL.md`). Not re-derived: the 6,542 for the nine old files, the
"92 Python opens", "6230-byte body", and the pids and timings, which come from one run in another session.

## What I did not check

- Linux/CI behaviour of `mkt_isolate --self-test` (CI pins 3.12 and has no `claude`); CI will answer it.
- The remaining 26 + 39 mutations by hand; I applied 8, all named-red.
- Whether `claude` in the world writes anything outside world HOME (non-Python, uncaptured by design).

VERDICT: NOT CONVERGED
