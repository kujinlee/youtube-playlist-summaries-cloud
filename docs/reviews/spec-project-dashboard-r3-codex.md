<!-- codex-review: model=gpt-5.5 -->

**Ready: No.** Shortest required changes first: define the entry grammar as a real parser contract, specify first-run/absent-file and branch/PR behavior for `docs/dashboard-entries.md`, restore the 14-day window control or explicitly accept the older H4 regression, and fix stale path/count citations.

**VERIFIED**

Severity: Blocking  
Quoted claim: “Format, specified because round 2 found ‘fields, not a grammar’ was not enough” and the `## 2026-08-28 [needs-you]` block.  
What I checked: [spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-28-project-dashboard-design.md:120), [r2 Codex](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/reviews/spec-project-dashboard-r2-codex.md:11).  
What is actually true: v4 improved “fields” into an example format, but it is not yet a grammar. It does not define valid date regex/calendar validation, exact `[needs-you]` token rules, whether typos are errors or unflagged entries, escaping for literal `<!--plain-->` / `<!--tech-->`, how to handle `##` inside technical Markdown, whether `<!--tech-->` is required or optional, stable ordering for same-date entries, first-ever empty file behavior, or absent-file behavior. “Malformed block rendered as error in place” is not falsifiable until those boundaries are defined.

Severity: Blocking  
Quoted claim: “`docs/dashboard-entries.md`, in the repo, append-only.”  
What I checked: [spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-28-project-dashboard-design.md:120), [dev-process](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/dev-process.md:92), `test -f docs/dashboard-entries.md` returned absent.  
What is actually true: r2 already found the repo-backed store right-shaped but under-specified against the repo’s own branch + PR process. v4 still does not say whether the dashboard reads the working tree, current branch, or default branch; docs changes are batched PRs and merges are a human gate. That means the rank-1 entries can be invisible from the rendered ref, or visible before review, depending on unstated implementation choice.

Severity: High  
Quoted claim: “One bar per day for the last 14 days” and “Activity window — 14 days is a guess; adjust after use.”  
What I checked: [spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-28-project-dashboard-design.md:105), [r1 Claude H4](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/reviews/spec-project-dashboard-r1-claude.md:202), [r2 Claude closure table](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/reviews/spec-project-dashboard-r2-claude.md:29).  
What is actually true: this was fixed in v3 by making the window a parameter with a widening control. v4 silently drops that fix while keeping the chart as navigation. This reintroduces the earlier failure for absences longer than two weeks, which the problem statement explicitly allows: “a day or a week” is not the upper bound, and r1 used three weeks as the counterexample.

Severity: High  
Quoted claim: “Continuity is rank 1 and is delivered by entries” plus “An entry exists only if I write it… This is the single largest risk.”  
What I checked: [spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-28-project-dashboard-design.md:36), [spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-28-project-dashboard-design.md:139), [r1 Codex](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/reviews/spec-project-dashboard-r1-codex.md:57).  
What is actually true: the design is worth building only as a deliberately modest “log plus missing-log alarm,” not as a reliable continuity mechanism. The spec says the rank-1 mechanism fails exactly under load and offers no recovery. That honesty is good, but the implementation plan must stop presenting entries as delivering continuity unless it adds a stronger habit/gate/reminder or reframes success around exposing gaps.

Severity: Medium  
Quoted claim: “One prerequisite remains (§6), where v3 had five.”  
What I checked: [spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-28-project-dashboard-design.md:60), [v3](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-28-project-dashboard-design.md:144), `git show 4897947:...` lines 203-307, 324-350.  
What is actually true: the dissolved Mermaid/progress/request prerequisites are gone, but v4 still has more than one prerequisite in practice: fold survival, creating and parsing the entry store, adding `/dashboard` to `PAGE_SKILLS`, and defining how `gh` failure/open PR derivation works. §6 is the only section titled prerequisite; it is not the only prerequisite to implement.

Severity: Medium  
Quoted claim: “Two stale numbers found and left for their owners…”  
What I checked: [spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-28-project-dashboard-design.md:207), `.agents/skills/shared/explainer-delivery.md:68`, `.agents/skills/brief/SKILL.md:162`, `python3 scripts/brief-compose.py --self-test` → 30/30.  
What is actually true: there are at least two stale 14-case claims, but v4 names only one, and the cited path is wrong: `explainer-delivery.md` lives at `.agents/skills/shared/explainer-delivery.md`, not `docs/explainer-delivery.md`. The brief skill also still says 14.

Severity: Low  
Quoted claim: “`regen-goals-page.sh:4-10` records…” and “`explainer-delivery.md` §5b.”  
What I checked: `rg --files`, `.claude/hooks/regen-goals-page.sh:4-10`, `.agents/skills/shared/explainer-delivery.md:147`.  
What is actually true: both cited files exist, but not at the paths v4 gives. The claims are substantively true; the citations are stale.

**INFERRED**

The five “dissolved” Blocking findings are actually dissolved: progress chart, Mermaid, external Mermaid asset delivery, licence audit for redistributed Mermaid, and the page-class exemption are absent from v4’s design. I found no remaining hidden Mermaid asset or milestone data source.

The cut did remove one load-bearing accepted fix: the adjustable activity window. It also intentionally removed recurring mistakes, which r1 Claude argued was the only requested section that does not rot. That deletion is a product decision, not an implementation blocker, but it weakens the design’s answer to the admitted entry-writing failure.

§7’s `PAGE_SKILLS` statement is correct: `scripts/check-explainer-delivery.py` audits only the hardcoded list at line 53, so an absent dashboard skill is invisible until manually added.

NOT CONVERGED
