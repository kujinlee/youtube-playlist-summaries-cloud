<!-- codex-review: model=gpt-6.1-sol -->

Found two issues:

- **MEDIUM — `scripts/goal-tree.py:2067,2082`: malformed answers can prevent the page being written.** `{"answers":null}` and `{"answers":42}` raise uncaught `TypeError`. An otherwise valid entry with `"asked":7` passes validation, then raises `AttributeError` during rendering. These bypass the promised filename warning and page-write fallback. Reproduced all three.
- **LOW — `scripts/goal-tree.py:3248`: answer escaping is not protected by the new tests.** Replacing `html.escape(p.strip())` with `p.strip()` still gives **458/458 passing**. An answer containing `<img src=x onerror=alert(1)>` would then become executable HTML. The test exercises angle brackets in the question, but only plain text in the answer.

Other requested checks:

- **Ask path:** the lifted tray posts `{doc: location.pathname…, text: body}` to `/questions`. `explainer-serve.py:1118,1574` records the page name and question in `~/explainers/questions.md`. The Refresh route regenerates through the same generator, which lifts the tray again; it can degrade to the explicitly warned tray-less page.
- **Current escaping:** malicious markup remained escaped in thread/owner-quote rendering and answer rendering. No unescaped insertion found in those paths.
- **Collapsed answers:** goal/thread markers and the single Older questions section are emitted closed.
- **Ledger observation confirmed, pre-existing — MEDIUM, `scripts/goal-tree.py:359,533`:** matching discards reference kinds and intersects all referenced numbers. Thus `PR #558` collides with `backlog #558`; mentions of `#586` also attach both entries to unrelated sibling threads sharing that backlog number. Both mechanisms operate. Running the matcher against master reproduced the erroneous attachments. This PR adds intended destinations but does not repair the existing matcher.
- **Claim 3:** with the current ledger, `s1-phase6` and `decision-tags` match declared threads and leave “no goal.” This does not establish correct exclusive placement.

`python3 scripts/goal-tree.py --self-test`: **“458/458 self-test cases passed.”**

In-memory mutation checks: removing the lift produced **457/458**; removing collapse produced **454/458**; removing answer-body escaping remained **458/458**.

## Loosening answers
LOOSENING-CHECK 6f409fec68b9: not a loosening
LOOSENING-CHECK 6b028c4b7f85: not a loosening
VERDICT: NOT CONVERGED
