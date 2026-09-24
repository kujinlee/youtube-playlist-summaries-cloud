<!-- codex-review: model=gpt-5.5 -->

**Blocking**

`docs/process-checklists.md:543` still says a derivation that reads only `ci.yml` “omits the **fifteen** schema gates entirely.” That is a live repository count inside the adopted rule 4 section. It has to track `.github/workflows/schema-gates.yml` to stay true, so the remedy removed the `33/28/54/4` counts but did not remove the class. This is link three. Blocking.

Searched siblings: I scanned the adopted rules section with `git grep -nE '([0-9]+|:[0-9]+|[0-9]+-[0-9]+)' HEAD -- docs/process-checklists.md` and narrowed `docs/process-checklists.md:428-566`. That also turned up `docs/process-checklists.md:539` (`scripts/check-merge-ready.py:52-55`) and `docs/process-checklists.md:476` (“Rule 3 twenty lines below”), both locator/count-style claims that move with the repo/doc. I also searched changed branch docs with `rg -n "fifteen schema|schema gates|schema-gates|15 schema|\\b15\\b" ...`; the surviving sibling copy in the changed rationale is `docs/development-velocity.md:203`.

What I ran:
`nl -ba docs/process-checklists.md | sed -n '440,570p'`
`nl -ba .github/workflows/schema-gates.yml | sed -n '1,220p'`
`rg -n '^\\s*- name:|^\\s*run:' .github/workflows/schema-gates.yml .github/workflows/ci.yml`
`rg -n "fifteen schema|schema gates|schema-gates|15 schema|\\b15\\b" docs/process-checklists.md docs/development-velocity.md docs/roadmap-to-launch.md docs/backlog.md docs/reviews/architecture-review-2026-09-24-number-populations.md`

**High**

`docs/reviews/architecture-review-2026-09-24-number-populations.md:39` says no process document points at the 2026-09-21 decision. I do not think that claim survives reading the scoped process docs: `docs/roadmap-to-launch.md:1981-1985` already records the same decision in the #153 roadmap entry: “A stale count in its preamble was removed rather than corrected … the file sits inside the corpus it describes.” That is not an ADR, but it is a process/status document in the review’s stated corpus, and it materially weakens the “only reachable by reading a parenthetical” claim.

Searched siblings: I ran `git grep -nE 'stale at the commit|inside the corpus|number is removed rather than corrected' ccc19857 -- CONTEXT.md docs/adr docs/dev-process.md docs/process-checklists.md docs/review-method.md docs/roadmap-to-launch.md`. It found `CONTEXT.md:119` and `docs/roadmap-to-launch.md:1985`; ADR search found nothing.

What I ran:
`git show 5ffe6017:CONTEXT.md | nl -ba | sed -n '1,180p'`
`git show --stat --date=short --pretty=fuller 5ffe6017 -- CONTEXT.md docs/adr`
`find docs/adr -maxdepth 1 -type f -name '*.md' | sort | nl -ba`
`rg -n "stale at the commit|inside the corpus|number is removed rather than corrected|live figure|no live figure" docs/adr docs/ADR.md`
`nl -ba docs/roadmap-to-launch.md | sed -n '1940,1990p'`

**Architecture Claims Verified / Refuted**

Verified: the decision exists in `CONTEXT.md:119`, and `git show 5ffe6017` dates it to 2026-09-21.

Verified: it is not in the thirteen numbered ADR files under `docs/adr/`; `rg` found no match there.

Refuted as written: “no process document points at it” misses `docs/roadmap-to-launch.md:1981-1985`.

Refuted as sufficient: “exactly one violator survived” does not matter for the merge tree because the adopted rule section still has `fifteen schema gates` and line locators.

Rule 4 is still followable after removing the big counts: it tells readers to derive from workflows, distinguish populations, parse `run:` blocks, and prefer `scripts/check-merge-ready.py`. The problem is not loss of teeth; it is that the rule kept live numeric/locator teeth in prose.
