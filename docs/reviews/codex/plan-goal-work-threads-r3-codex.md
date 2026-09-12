# Plan review — goal work threads — round 3 — Codex

**Subject:** plan v2 at `2958b820`. **Model:** gpt-5.5 via `scripts/codex-review.py`.
Mandate: attack round 2's fixes only. Proof of subject supplied and correct.

---

<!-- codex-review: model=gpt-5.5 -->

`def pr_fanout(histories) -> dict[str, int]:`

**Findings**

Blocking — `docs/superpowers/plans/2026-09-11-goal-work-threads.md:683-695`

The round-2 “no rel” renderer fix is internally inconsistent: the plan says “`.get` throughout,” but the proposed renderer still indexes `d["rel"]`.

```python
parts.append(f'<div class="prline"><span class="t">{side}</span>'
             f'<a href="/src/{esc(d["rel"])}">{esc(d["name"])}</a></div>')
...
parts.append(f'<div class="prline"><span class="absent">⚠ extra document '
             f'on this stem</span>'
             f'<a href="/src/{esc(d["rel"])}">{esc(d["name"])}</a></div>')
```

Concrete failing scenario: the new round-2 test itself supplies `{"spec": {"name": "s.md"}}` at lines 639-642. `render_threads()` reaches the spec branch first and raises `KeyError: 'rel'` before it can prove the extra-document branch. If the implementer changes only the side branch to `.get`, an extra doc with no `rel` still crashes at line 695.

High — `docs/superpowers/plans/2026-09-11-goal-work-threads.md:528,536`

`pr_fanout(hist_cache.values())` is not actually fed every anchored document’s history; it is fed only histories demanded by `thread_prs()`, and `thread_prs()` only asks for `spec` and `plan`.

```python
"threads": [thread_prs(t, history) for t in pair_documents(ds)],
...
fan = pr_fanout(hist_cache.values())
```

with:

```python
for side in ("spec", "plan"):
    d = thread.get(side)
```

Concrete failing scenario: an anchored collision thread has three docs: spec `s-design.md`, plan `s.md`, and extra doc `s-plan.md`. `pair_documents()` keeps the extra in `t["docs"]`, and Task 5 renders it, but Task 4 never calls `history("s-plan.md")`. A PR touching only that extra document is omitted from the thread and omitted from fan-out. A PR touching all three documents is rendered as “on 2 documents,” not 3.

High — `docs/superpowers/plans/2026-09-11-goal-work-threads.md:243-244`

The anchored `DOC_PATH` fix catches root `CONTEXT.md`/`AGENTS.md`/`CLAUDE.md`, but misses nested project instruction documents.

```python
DOC_PATH = re.compile(
    r"^(docs/|\.remember/|\.agents/|(README(\.md)?|CONTEXT\.md|AGENTS\.md|CLAUDE\.md)$)")
```

Concrete failing scenario: a PR that touches only `worker/CONTEXT.md` or `packages/api/AGENTS.md` is tagged `touched code`, because those paths match none of the documentation branches. This is the same class as the round-2 regex fix: documentation outside `docs/` becomes code by omission. `docs` without slash and `.remember` without slash are less compelling as git paths, but nested instruction docs are a real miss.

**Checked, Not Filed**

`hist_cache` is populated after the per-anchor `out.append` loop has evaluated all thread comprehensions; the normal anchored spec/plan loop is complete before `pr_fanout(hist_cache.values())`.

A document reachable from no anchor does not enter `hist_cache`, but the spec explicitly bounds this view to anchor-declaring documents.

`{p["num"] for p in prs}` is okay for normal histories because `prs_from_log()` already dedupes by PR number per document.

`re.findall` is in scope because `scripts/gen-goals-page.py` imports `re`; the `_h` fixture has two PRs and the expected list of `["docs only", "touched code"]` matches that fixture.

The chained `and` test is coarse, but it still fails if any one of the four path classifications returns `False`.

`_r` remains function-local, and `"unknown"[:8]` renders as `unknown`, which is sensible.

The count chain is correct by direct `eq(` count: `15 -> 25 -> 34 -> 38 -> 45 -> 59 -> 62`.

NOT-CONVERGED
