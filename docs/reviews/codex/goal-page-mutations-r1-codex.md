# Codex adversarial review — branch `goal-page-mutations`, round 1

**Subject:** `git diff 58d82658..HEAD` — `scripts/mutations/gen-goals-page.json` (14 new entries),
`scripts/gen-goals-page.py` (`eq()` failure printer), `scripts/check-plan-code.py`
(`EXPECTED_MUTATIONS` 524 → 538 plus the pinned membership list), `docs/dashboard-entries.md`.

**PROOF OF SUBJECT** — the `name` field of the LAST entry in `scripts/mutations/gen-goals-page.json`,
verbatim:

    pair_documents drops the extra document instead of keeping it for the renderer

**Gate provenance:** `scripts/codex-review.py`, model `gpt-5.5`, 4708 chars, `gate_ran: true`,
`exit_code: 0`, no intrusions — testimony at
`docs/reviews/verdicts/goal-page-mutations-r1-codex.verdict.json`.

⚠ **Filing note, recorded rather than hidden.** This review was produced on 2026-09-12 and its text
survived only in a session scratchpad; the session ended before it was promoted into the repository.
It is reproduced below **verbatim** from that capture. The subject predates the `run=` injection in
`git_pr_history` / `git_show_files`, which is a *fix for finding 2 below* and belongs to round 2.

**Verdict: NOT-CONVERGED** — 1 High, 3 Medium, 2 Low.

---

## Findings (verbatim)

**Medium** — [`scripts/mutations/gen-goals-page.json:91`](../../../scripts/mutations/gen-goals-page.json): mutation 9 is attributed to the wrong rule. The edit is behavioral, not syntax-only, but the named case says "does not crash" while the mutation actually makes a rel-less extra document disappear:

```json
"named = [x.get(\"rel\") for x in (t.get(\"spec\"), t.get(\"plan\")) if x]\n        for d in t.get(\"docs\", []):\n            if d.get(\"rel\") not in named:"
```

Concrete failing scenario: `_sp2 = {"name": "s.md"}` and `_ex2 = {"name": "other.md"}` do not crash under this mutation; `d.get("rel")` returns `None` for both, so the extra is silently dropped. The case at `scripts/gen-goals-page.py:981` fails because `"extra document"` is absent, not because crash behavior was protected.

**High** — [`scripts/gen-goals-page.py:341`](../../../scripts/gen-goals-page.py): the source CANNOT-RUN predicate in `git_pr_history` is unmutated. The branch says `None IS NOT []`, but no manifest entry targets the actual subprocess failure conversion:

```python
except (OSError, subprocess.SubprocessError):
    return None
if r.returncode != 0:
    return None
return prs_from_log(r.stdout.splitlines())
```

Concrete failing scenario: changing `if r.returncode != 0: return None` to `return []` makes a git failure render as "no pull requests" instead of `pr_error=True`. The manifest covers `thread_prs` handling `history(...) is None`, but not whether `git_pr_history` preserves that sentinel.

**Medium** — [`scripts/gen-goals-page.py:339`](../../../scripts/gen-goals-page.py): the `--follow` rule is explicitly called load-bearing and untested, but no mutation covers it:

```python
["git", "log", "--format=%H\x01%as\x01%s", "--follow", "--", str(path)]
```

Concrete failing scenario: removing `"--follow"` silently loses PRs from before a document rename. The file comment admits today's corpus has no renamed documents, so the self-test cannot observe this and the manifest has no entry for it.

**Medium** — [`scripts/gen-goals-page.py:362`](../../../scripts/gen-goals-page.py): `git_show_files`'s `.splitlines()` rule is also unmutated despite a comment naming the hazard:

```python
return r.stdout.splitlines() if r.returncode == 0 else None
```

Concrete failing scenario: replacing `.splitlines()` with `.split()` makes a doc-only commit touching `docs/superpowers/specs/name with space.md` look like it touched code, because `with` / `space.md` are then independent paths outside `DOC_PATH`.

**Low** — [`scripts/gen-goals-page.py:758`](../../../scripts/gen-goals-page.py): the new `eq` comment points readers at a nonexistent current consumer:

```python
# `check-plan-code.attribute` reads a red case with `startswith("[FAIL] ")` then
```

The actual function is `parse_fail_names` at `scripts/check-plan-code.py:1385`. `brief-compose.py` already records this correction at `scripts/brief-compose.py:951`, so this branch reintroduces stale provenance in the new comment.

**Low** — [`scripts/gen-goals-page.py:762`](../../../scripts/gen-goals-page.py): the comment overstates the provenance of the format trap:

```python
# `gen-backlog-page.py` (5 entries) and `brief-compose.py` (8), both of which paid
# AFTER a convention was written to prevent exactly this.
```

`check-plan-code.py` says `gen-backlog-page.py` was the first failure and `brief-compose.py` paid after `portable-practices` §22 was written from that first one: `scripts/check-plan-code.py:2919`. So "both" is false.

## Checked

No syntax/import-only mutation entries found; all 14 manifest edits compile. The ratchets are arithmetically consistent on disk: 41 manifest files, 538 total entries, and `scripts/gen-goals-page.py` has 14. CI and hooks I found do not parse the new two-line `gen-goals-page.py` failure detail format; the mutation harness parses only the `[FAIL] <case>` line.

**NOT-CONVERGED**
