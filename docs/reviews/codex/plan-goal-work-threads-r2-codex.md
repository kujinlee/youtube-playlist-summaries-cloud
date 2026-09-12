# Plan review — goal work threads — round 2 — Codex

**Subject:** plan v2 + spec v4 at `c460f015`. **Model:** gpt-5.5 via `scripts/codex-review.py`.
Proof of subject supplied and correct.

---

<!-- codex-review: model=gpt-5.5 -->

Proof of subject: `PR number -> how many threads reach it. PURE.`

**Findings**

Blocking — `docs/superpowers/specs/2026-09-11-goal-backlog-pr-join-design.md:327` still specifies the retracted tri-state claim.

Quote:

```md
Expanded WORK replaces the flat PR list (§3.2a). Document-led work renders as a
`spec → plan → PR` thread with a state — **shipped**, **in flight**, **not started** —
```

Concrete failure: an implementer following the spec, not just the plan, can reintroduce the exact round-1 error: a PR found through `git log --follow` becomes evidence that the thread is “shipped”. That contradicts v4’s retraction that the page cannot tell which PR implemented the thread.

High — `docs/superpowers/plans/2026-09-11-goal-work-threads.md:472` counts threads, then `:668` renders documents.

Quote:

```python
def pr_fanout(threads: list[dict]) -> dict[str, int]:
    """PR number -> how many threads reach it. PURE.
```

and:

```python
fan = f'<span class="t">on {n} documents</span>' if n > 1 else ""
```

Concrete failure: PR `#999` touches both `s-design.md` and `s.md` in the same thread. `thread_prs()` dedupes that PR inside the thread; `pr_fanout()` increments once; the page either suppresses fan-out or says `on 1 documents`, even though two anchored documents were touched. The advertised remediation is document fan-out, but the code computes thread fan-out.

High — `docs/superpowers/plans/2026-09-11-goal-work-threads.md:236` makes `README` a prefix, so code can be tagged docs-only.

Quote:

```python
DOC_PATH = re.compile(r"^(docs/|\.remember/|\.agents/|README|CONTEXT\.md|AGENTS\.md|CLAUDE\.md)")
```

Concrete failure: a PR touching only `README-generator.ts` returns `files_are_code(["README-generator.ts"]) == False`, so the implementation renders `docs only`. `docs-site/` and `.agentsomething/` are safe because their branches include `/`, but `README-generator.ts`, `CONTEXT.md.bak`, `AGENTS.md.ts`, and `CLAUDE.md.old` are misclassified.

Medium — `docs/superpowers/plans/2026-09-11-goal-work-threads.md:695` is the only new git call without error handling.

Quote:

```python
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                      capture_output=True, text=True).stdout.strip() or "unknown"
```

Concrete failure: if `git` cannot be executed, `FileNotFoundError` aborts the page build. The other git derivers catch `OSError` / `SubprocessError` and preserve a renderable “cannot run” state; this one does not. A nonzero `rev-parse` return does become `"unknown"`, but an execution failure crashes.

Medium — `docs/superpowers/specs/2026-09-11-goal-backlog-pr-join-design.md:311`, `:316`, and `:328` leave stale rendered/design strings from the retracted model.

Quotes:

```md
PR #176  2026-08-29  Retire the plan-as-CI-dependency…   [code]
```

```md
blob-addressing-reservation                  ⚠ no code PR yet
```

```md
with a state — **shipped**, **in flight**, **not started** —
```

Concrete failure: these are not merely historical notes. They sit in the target card sketch and feature bullets, so a reader can still infer that `code` means implementation and that absence of a code PR means not shipped.

Medium — `docs/superpowers/plans/2026-09-11-goal-work-threads.md:570` is too literal to protect the retraction.

Quote:

```python
eq("the tag makes no implementation claim", "implement" in _h.lower(), False)
```

Concrete failure: rendering `shipped`, `done`, or `landed` next to a `touched code` PR preserves the same false claim but passes because none contains `implement`. This case can fail if the exact substring appears, but it cannot fail for equivalent wording.

Low — `docs/superpowers/plans/2026-09-11-goal-work-threads.md:577` only forbids one misspelling of the one-document fan-out.

Quote:

```python
eq("a PR touching one document does not claim a fan-out",
   "on 1 documents" in _h, False)
```

Concrete failure: a renderer that says `on 1 document` still claims one-document fan-out and passes. The positive `on 22 documents` case is useful, but this negative is narrower than its label.

Low — `docs/superpowers/plans/2026-09-11-goal-work-threads.md:657` crashes on malformed doc records.

Quote:

```python
named = {d["rel"] for d in (t.get("spec"), t.get("plan")) if d}
for d in t.get("docs", []):
    if d["rel"] not in named:
```

Concrete failure: `render_threads([{"stem":"s","spec":{"name":"s.md"},"plan":None,"docs":[],"prs":[],"pr_error":False}], {})` raises `KeyError`. Production `collect()` records include `rel`, so this is low, but the new pure renderer is not robust to the exact malformed shape called out in review.

**Q1 Notes**

`pr_fanout` after `out.sort(...)` is not itself ordering-sensitive. First call is fine once every anchor has `"threads"`. Empty threads produce `{}` and render through `a.get("fanout", {})`. The defect is not ordering; it is the thread-vs-document count mismatch.

**Q3 Notes**

Count chain is arithmetically correct: `15 + 10 = 25`, `+8 = 33`, `+4 = 37`, `+6 = 43`, `+12 = 55`, `+3 = 58`.

Cases I would name as weak or partly non-failing:

`no threads means no fan-out` can pass under a trivial `return {}` and is only protected by the sibling fan-out count case.

`the tag makes no implementation claim` can fail only for the substring `implement`, not for the claim.

`a PR touching one document does not claim a fan-out` can fail only for `on 1 documents`, not `on 1 document`.

The extra-document case can fail for the intended omission, but it does not cover missing `"rel"` and therefore misses the crash path above.

NOT-CONVERGED
