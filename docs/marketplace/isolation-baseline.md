# Isolation baseline — what a stranger is assumed to have

Spec §7 item 0b. Measured 2026-11-15 on the building machine (macOS, Darwin 25.5.0) by commands run in the session that
wrote `scripts/mkt_isolate.py` (marketplace-inventory plan, Task 2). Every version below is the output of the command
beside it; none is recalled.

## The world

`scripts/mkt_isolate.py` builds it under an empty root: `home/` (the stranger's `HOME`), `tmp/` (`TMPDIR`), `bin/` (one
symlink per allow-listed command and nothing else — the whole `PATH`), `hook/` (the audit hook). The environment is built
from nothing: `HOME`, `TMPDIR`, `PATH`, `LANG=C.UTF-8`, `PYTHONPATH=hook/`. Preflight refuses to start if the author's
environment would reach in (see the script's docstring for every reason).

## Interpreter and packages

| What | Value | Measured by |
|---|---|---|
| Interpreter | Python 3.14.4 | `python3 -V` |
| Package set | the standard library only — nothing is installed into the world | (by construction: no `pip` step exists) |

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

Every `RunRecord` carries these three `ALWAYS:` entries, plus one entry per non-Python program and one for Python
processes that never loaded the hook:

- file access by non-Python processes (`git`, `node`, `gh`, `cat`, …) — the audit hook runs only inside Python;
- network access;
- anything before a Python interpreter imports `sitecustomize` (startup, the stdlib imported before it).

## Stated deviations from a real stranger's machine

- **(a) The audit hook SHADOWS the interpreter's own `sitecustomize`.** The world's `PYTHONPATH` puts
  `hook/sitecustomize.py` first, so the one Homebrew Python ships is not imported inside the world. The one shadowed,
  measured by `python3 -c "import sitecustomize; print(sitecustomize.__file__)"`:
  `/usr/local/Cellar/python@3.14/3.14.4_1/Frameworks/Python.framework/Versions/3.14/lib/python3.14/sitecustomize.py`.
  CI pins Python 3.12, whose runner image may ship none.
- **(b) `claude -p` in the world runs with `--permission-mode bypassPermissions`** (`bypassPermissions` present in
  `claude --help`, measured 2026-11-15). A fresh `HOME` has no settings and would refuse Bash and Write; a stranger
  answers those prompts themselves, so a permission refusal is a baseline artifact, never a suite defect.
- **(c) The system git config is not isolated.** `HOME` is fresh, so `~/.gitconfig` is not read, but git still reads
  its system-level config (`$(prefix)/etc/gitconfig`) — as a stranger's git would.
- **(d) macOS adds `__CF_USER_TEXT_ENCODING`** to a child's environment in-process (CoreFoundation). It is not passed
  by the tool and carries no author state; the self-test's environment case drops `__CF_` keys for that reason.
