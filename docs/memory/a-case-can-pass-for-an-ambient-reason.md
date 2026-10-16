---
name: a-case-can-pass-for-an-ambient-reason
description: "FIRES-WHEN: writing or reviewing a case whose premise depends on the surrounding world, OR whose NAME and BODY have drifted apart — ⭐⭐⭐ FOUR on one file (PR #311), then FIVE MORE on check-doc-citations.py 2026-10-15, the fifth written WHILE FIXING the defect it was meant to witness. The tell: the name describes a mechanism, the body tests something adjacent"
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

---

## ⭐⭐⭐ 2026-10-15 — FIVE MORE on one file, and the tell is NAME vs BODY

Building `scripts/check-doc-citations.py` (backlog #49) produced **five** ambient cases across three
review rounds. The ambient-world shape above is one species; these were a second:

> **the case's NAME describes a mechanism, and the case's BODY tests something adjacent that the
> mechanism happens to influence.** The name is the hypothesis, the body is the experiment, and when
> they drift apart the case passes forever while measuring nothing.

| the case | what it actually asserted |
|---|---|
| *"a unique suffix resolves"* using `a.ts:1` | `a.ts` has no `/`, so it never matched the citation grammar — it asserted that a NON-citation yields no finding, true of any string |
| *"the +++ header is never content"* | contained no citation, so it could not fire under any mutation — **and it ENDORSED a fail-open**: an added line beginning `++` is emitted as `+++` |
| *"a second +++ header RE-SCOPES"* | asserted silence after scoping OUT of scope, which is also what happens if headers are ignored entirely |
| *"git hands it over unquoted via `-z`"* | called `in_scope` on a Python **string** — never ran git, so deleting `-z` failed ZERO cases while silently disabling the whole guard |
| *"added content beginning `++` IS examined"* | used **two** plus signs where a real diff emits **three** (marker + the author's two) — passed whether or not the fail-open was present |

⛔ **THE FIFTH WAS WRITTEN WHILE FIXING THE FIRST OF THESE, by someone who had just written three
commit messages about this exact failure mode, with the corrected sibling case directly above it.**
Knowing the failure mode did not prevent it. Every one of the five was caught by **running a
falsifier**, never by reading.

## How to apply — one line, and it is cheap

**Flip the thing the case NAMES, and check that case goes red.** Not "state a falsifier" — run it.
Measured here: it caught 3 of the 5, including one where the suite stayed green at 37/37 *and* the
live gate returned rc=0 over a repository full of real defects.

⚠ This is mechanically detectable and is a candidate guard, not merely a discipline: compare the
identifiers in a case's name against the symbols its body actually touches. See
[[a-test-that-cannot-fail]] (run the FAILS IF against HEAD as you write it) and
[[fixing-a-premise-is-not-covering-the-branch]].

