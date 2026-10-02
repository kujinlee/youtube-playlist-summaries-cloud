---
name: a-case-can-pass-for-an-ambient-reason
description: "FIRES-WHEN: writing or reviewing a case whose premise depends on the surrounding world — ⭐⭐ FOUR times on one file — a case whose premise depends on the surrounding world asserts the WORLD, not the code. One was visible only on Linux"
metadata:
  type: feedback
---

Four times while seeding one file's mutation manifest (PR #311), a case passed while asserting
nothing, because its premise depended on the environment rather than on state it built:

| case | why it asserted nothing |
|---|---|
| `~` expands | the harness sets `$HOME` to a dir it **deliberately never creates**, so `~` was not a directory |
| two `/_stale` cases | driven against the REAL `ROOT` (`~/explainers/`); under the harness that is empty, so the handler returned `fresh` before reaching the mutated lines — **two mutations SURVIVED behind green cases** |
| `/questions` | would have written to the reader's real file *and* asserted the ambient world |
| ⭐ `no command under the missing checkout` | **passed on macOS for a SYMLINK reason**: `_gone` is `.resolve()`d to `/private/var/…` while `$HOME` stays `/var/…`, so the substring test missed on path spelling, not on the property. **Linux has no such symlink → CI's CONTROL run went red** |

**Why:** "use the real thing, it is more honest" is a good instinct that **inverts when the real
thing is absent at test time** — and the failure is silent, because a handler that bails early
returns a perfectly plausible answer.

**How to apply:**
- ⛔ **BUILD the world the case needs** — sandbox dirs, patched module globals, restored in a
  `finally`. Do not borrow the ambient one.
- **Run every suite three ways before believing it:** normal, under a **non-existent** `$HOME`
  (`HOME=$(mktemp -d)/.home`), and with `$HOME` **inside the resolved repo root** (CI's shape).
  The last one reproduces the Linux-only failure on a Mac.
- ⭐ **Know which instrument sees what:** the local suite proves logic; `--mutate .` proves the cases
  can fail; **only CI proves it holds on a machine that is not yours.** The fourth defect above was
  invisible to the first two by construction.
- A guard disagreeing with a green local run **is the finding**, not noise. Three of these four
  surfaced exactly that way.

See [[a-measurement-is-only-as-good-as-its-corpus]], [[measure-the-population-the-code-actually-sees]],
[[a-check-result-is-not-the-claim]], [[a-mutation-loses-its-binding]].
