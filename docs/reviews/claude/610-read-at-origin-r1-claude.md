# Review — `610-read-at-origin`, round 1, Claude half (adversarial)

Subject: `git diff origin/master...HEAD` at `da32f4b1` (3 commits). Mandate: refute.
Ran: `python3 scripts/goal-tree.py --self-test` → `486/486 self-test cases passed`. Then three constructed inputs,
below, each outside the repository (scratch dir) or read-only against the live remote.

## Findings

### F1 — MAJOR — `scripts/goal-tree.py:1052` (the lag is measured in `root`, not the owner's checkout)

**Failing input:** the Refresh button / `/goal-tree`, i.e. the path the page is normally built by.
`explainer-serve.py` (`REGEN_RUNNER = "regen-pages.py"`) and `.claude/commands/goal-tree.md` both run
`regen-pages.py`, which runs `goal-tree.py` with `cwd=<private clone>`, the clone `checkout --detach <sha>` at the
just-fetched `origin/master` with `refs/remotes/origin/master` set to the same sha (`regen-pages.py` docstring, steps
2-3). In that clone `root` is the clone, so `git rev-list --count HEAD..origin/master` is ~always 0 and the page
says **"this checkout is up to date with it"** about a directory that is deleted a second later, whatever the
owner's main checkout lags.

**Evidence (constructed, scratch dir):** an upstream with 3 commits; `main` cloned and reset 2 behind; a
`clone --shared --no-checkout` of `main` built exactly as `regen-pages.clone_tree` does (detach at sha,
`update-ref refs/remotes/origin/master <sha>`, `origin` set to upstream, then the goal tree's own `git fetch origin
master`):

```
main lag: 2
clone lag: 0
```

So on the primary path the new line is not merely uninformative — it asserts the false "up to date". The dashboard
entry in this diff ("a line under the header says how many commits your checkout is behind") is false for the
Refresh button. Note also that on this path the backlog was ALREADY read at origin/master (the clone is master), so
the half of #610 that the clone path needs is exactly the half that is wrong. The self-test cannot see it: every
lag case uses a fake `run` that answers `["git","rev-list"]` by prefix, never by cwd.
**Fix direction:** run the rev-list in `main` (`_SS.main_checkout`, already computed in `collect`, which honours
`REGEN_MAIN_CHECKOUT`), and name that checkout on the line; when `main_why` is set, say the lag could not be read.

### F2 — MAJOR — `scripts/goal-tree.py:2529` with `:1049-1065` (threads from the checkout, backlog from master: a new mixed-source CANNOT RUN)

**Failing input:** a direct run (`python3 scripts/goal-tree.py`, `--snapshot`, `--print` after a snapshot) in a
branch that files a backlog row and declares a thread for it in `docs/goal-threads.md` — which is what THIS branch
does (rows #611/#612 filed, threads `fix · backlog #611` / `fix · backlog #612` added). `parse_threads` still reads
`root/docs/goal-threads.md` (the branch), while `row_fates` now reads the backlog at origin/master, which lacks the
rows. Before this diff both came from the same tree and resolved.

**Evidence (read-only run of `collect` + `derive` + `render_text` in this worktree, no log written):**

```
read_at origin/master behind 0 fates_error None
611 in fates: False 610: True
⚠ backlog #611 · ... — CANNOT RUN — backlog #611 is not a row of the Items table in docs/backlog.md
⚠ backlog #612 · ... — CANNOT RUN — backlog #612 is not a row of the Items table in docs/backlog.md
```

This is the #610 symptom (a resolvable step shown CANNOT RUN) relocated rather than removed, for the inverse case
(checkout AHEAD of master). The prompt's first question ("is any other file still read from the checkout when it
should be shared?") — yes: `docs/goal-threads.md` (and `gen-backlog-page.publish_rows(root)` at `:2557` reads the
checkout's backlog too). Invisible to the suite: the test `fake` answers `git show origin/master:<rel>` with the
fixture's on-disk file (diff hunk at `_self_test_cases` `fake`), so threads and backlog are always the same tree in
every case. **Fix direction:** read the threads file through the same `read_shared` (the command doc already
claims "the page reads the file from master"), or read both from the same source; add a case where the checkout's
threads name a row only the checkout has.

### F3 — MINOR — `scripts/goal-tree.py:1065` (a git-show read decodes with the locale and `errors="replace"`; the disk read was strict UTF-8)

**Failing input:** a backlog/dashboard blob at origin/master containing a non-UTF-8 byte, or any run under a
non-UTF-8 locale. `_SS._run` is `Popen(..., text=True, errors="replace")` with no `encoding`, so the blob is decoded
with `locale.getpreferredencoding()` and bad bytes become U+FFFD silently. The replaced path,
`read_text(encoding="utf-8")`, raised and the source was NOT READ.

**Evidence (scratch repo, file `a \xff b` + a `✖ **WITHDRAWN**` row, read via `_SS._run(["git","show",...])`):**

```
UTF-8 locale:       git show rc 0 'a � b\n| 8 | x | ✖ **WITHDRAWN** |\n'     disk: UnicodeDecodeError
LC_ALL=ISO8859-1:   git show rc 0 'a � b\n| 8 | x | �\x9c\x96 **WITHDRAWN** |\n'  disk: UnicodeDecodeError
```

The first turns a loud NOT READ into a silent read; the second mangles the `✖` marker `row_fates` looks for, so a
withdrawn row would read as live with no error. Low likelihood (the locale is usually UTF-8), but it is a fail-open
regression of a property the old code had. CRLF is NOT a difference: `text=True` and `read_text` both use universal
newlines. **Fix direction:** run `git show` with bytes and `decode("utf-8")` strictly (or `git show` via a run that
takes `encoding="utf-8", errors="strict"`).

### F4 — MINOR — `scripts/goal-tree.py:618` (the catch-up advice is wrong off `master`)

**Failing input:** a run in a linked worktree on a feature branch (e.g. this one), N > 0 commits behind.
`HEAD..origin/master` counts master commits not in the branch; `git pull --ff-only` there pulls the branch's own
upstream (or fails with no upstream, or on divergence), so it does not "catch up". The line also calls the branch
"this checkout", while the #610 harm was the MAIN checkout. Subsumed by F1's fix if the lag is measured in `main`
and the line names it; otherwise word it per branch (`git merge origin/master` / only advise pull when HEAD is
`master`).

## Not refuted (checked)

- Caching: one `git show` per file per run (case + mutation `the shared read is not cached`).
- Failed fetch: reads the checkout, issues no `git show`/`rev-list`, says so; that snapshot is not logged.
- Lag not stored in the snapshot (`derive` output lacks `behind`/`read_at`); `--page` alone renders no lag line.
- The 8 new mutations are each bound to a case that reads the mutated behaviour; none would survive as written.
  Gap: no mutation/case varies the rev-list's cwd, which is why F1 is invisible.
- `rc 0` fetch with a stale `origin/master`: with the default refspec `git fetch origin master` updates the
  tracking ref; the regen clone keeps the cloned refspec. Not a finding.

VERDICT: NOT CONVERGED
