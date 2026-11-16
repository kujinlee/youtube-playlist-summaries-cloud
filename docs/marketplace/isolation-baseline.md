# Isolation baseline — what a stranger is assumed to have

Spec §7 item 0b. Measured 2026-11-15 on the building machine (macOS, Darwin 25.5.0) by commands run in the session that
wrote `scripts/mkt_isolate.py` (marketplace-inventory plan, Task 2). Every version below is the output of the command
beside it; none is recalled.

## The world

`scripts/mkt_isolate.py` builds it under an empty root: `home/` (the stranger's `HOME`), `tmp/` (`TMPDIR`), `bin/` (one
symlink per allow-listed command and nothing else — the whole `PATH`), `hook/` (the audit hook), and `pyvenv.cfg`
(`include-system-site-packages = false`, so a Python started as `bin/python3` is a virtual environment without the
author's site-packages). The environment is built from nothing: `HOME`, `TMPDIR`, `PATH`, `LANG=C.UTF-8`,
`PYTHONPATH=hook/`, `GIT_CONFIG_NOSYSTEM=1`, plus one per-run token (`MKT_ISOLATE_RUN`) that `run_isolated` adds.
Preflight refuses to start if the author's environment would reach in — any env key or VALUE other than the world's,
a world root inside a checkout, a Python whose `sys.path` holds anything outside the world and its stdlib, a git that
reports a `credential.*` or URL-rewrite key — and `run_isolated` refuses a cwd outside the world (the script's
docstring lists every reason). `run_isolated` repeats the env/layout checks and the two measured ones (Python's
`sys.path`, git's config) on every run (r2 Codex 4); the HOME and bindir entry checks and the explainer port are
preflight's alone. Whether a path is inside a checkout is the filesystem's answer (`_reaches`: object identity up
the ancestors, never a compare of spellings), so a case alias of the checkout on a case-insensitive volume is refused
too. Each measured probe is bounded by the caller's `timeout` (at most 60 s; r3 F5).

## Interpreter and packages

| What | Value | Measured by |
|---|---|---|
| Interpreter | Python 3.14.4 | `python3 -V` |
| Package set | none: `importlib.metadata.distributions()` in the world is `[]` | measured 2026-11-15 11:27 by `run_isolated` in a fresh world. It is VERIFIED per run, not assumed: `run_isolated` itself asks the world's `python3` for its `sys.path` before starting the command and refuses one that holds anything outside the world and its stdlib, or any installed distribution, whether or not `preflight` was called (r1 Codex 2, Claude m2; r2 Codex 4). Bound: only the allow-listed Pythons in `bin/` are asked; an interpreter the command reaches by a path of its own is not |
| Rejected interpreter | macOS's `/usr/bin/python3` shim | it re-execs the Command Line Tools Python, which does not see the world's `pyvenv.cfg`; if it is the allowed `python3`, preflight's probe sees the foreign `sys.path` and refuses |

## Allow-listed commands, with versions

| Command | Version | Measured by |
|---|---|---|
| `git` | git version 2.49.0 | `git --version` |
| `claude` | 2.1.323 (Claude Code) | `claude --version` |
| `gh` | gh version 2.88.1 (2026-03-12) | `gh --version` |
| `node` | v20.18.2 | `node -v` |
| `python3` | Python 3.14.4 | `python3 -V` |

The allow-list is per run (`--allow`), so a run states its own; this table is the set the plan's tasks name.

## Network policy

Allowed only for `claude` model calls and the tier-B clone. Nothing else. **Not enforced by the tool** — nothing here
captures sockets (see below); the policy is kept by what the tasks run, and a run that needs the network says so.

## What the capture cannot see

Every `RunRecord` carries these four `ALWAYS:` entries, plus one entry per non-Python program and one for Python
processes that never loaded the hook:

- file access by non-Python processes (`git`, `node`, `gh`, `cat`, …) — the audit hook runs only inside Python;
- network access;
- anything before a Python interpreter imports `sitecustomize` (startup, the stdlib imported before it);
- the OS user's keychain — bound (e) below.

A record holds only its own run's events: each event carries the run's token, the log is appended to and never
truncated, and a process that outlives the record (a detached server) is named as such rather than dropped (r1
Claude M1).

## Stated deviations from a real stranger's machine

- **(a) The audit hook SHADOWS the interpreter's own `sitecustomize`.** The world's `PYTHONPATH` puts
  `hook/sitecustomize.py` first, so the one Homebrew Python ships is not imported inside the world. The one shadowed,
  measured by `python3 -c "import sitecustomize; print(sitecustomize.__file__)"`:
  `/usr/local/Cellar/python@3.14/3.14.4_1/Frameworks/Python.framework/Versions/3.14/lib/python3.14/sitecustomize.py`.
  CI pins Python 3.12, whose runner image may ship none.
- **(b) `claude -p` in the world runs with `--permission-mode bypassPermissions`** (`bypassPermissions` present in
  `claude --help`, measured 2026-11-15). A fresh `HOME` has no settings and would refuse Bash and Write; a stranger
  answers those prompts themselves, so a permission refusal is a baseline artifact, never a suite defect.
- **(c) The system git config is SWITCHED OFF.** `HOME` is fresh, so `~/.gitconfig` is not read, and
  `GIT_CONFIG_NOSYSTEM=1` stops git reading `$(prefix)/etc/gitconfig` — on this machine `/usr/local/etc/gitconfig`,
  which sets `credential.helper=osxkeychain` (r1 Codex 3, Claude m2). A stranger's git WOULD read their own system
  file; the world reads none, so a world never borrows the author's credentials or `insteadOf` rewrites. Preflight
  verifies it in the world's own git (`config --show-origin --get-regexp` over `credential.*` and `url.*.insteadof`);
  measured 2026-11-15: rc 1, nothing reported.
- **(d) macOS adds `__CF_USER_TEXT_ENCODING`** to a child's environment in-process (CoreFoundation). It is not passed
  by the tool and carries no author state; the self-test's environment case drops `__CF_` keys for that reason.
- **(e) The OS keychain is NOT isolated, and cannot be from here.** The world runs as the author's OS user; a fresh
  `HOME` does not change which login keychain macOS answers from. No credential helper reaches it any more (c), and
  `claude auth status` → `loggedIn: false` and `gh auth status` → not logged in, measured in a world (Claude r1 m2).
  That is ALL that was measured: neither tool reported an identity. Whether either one — or anything else a world
  starts — reads the keychain is UNVERIFIED (r2 Codex 5); nothing here observes keychain access. A program that asks
  the keychain directly would be answered as the author.
  **The observation that would show it:** a world run that succeeds at something needing the author's identity —
  `claude auth status` reporting `loggedIn: true`, a private clone succeeding, `security find-generic-password`
  returning an item. Removing the bound needs a second OS user; every `RunRecord` states it as `ALWAYS:`.
