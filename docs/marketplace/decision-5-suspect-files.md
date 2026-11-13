# Decision 5 — memory files to check before they ship as example content

Prepared 2026-11-13 at the owner's request ("prepare a list if suspected files for me to check").
Scanned all 193 files in `docs/memory/` (the plan's count of 159 is older). Method: grep for emails, tokens,
key/password lines, long high-entropy strings, production hosts and project refs, local paths, and
business or pricing terms. Then each hit was read in context.

**No credential VALUES were found**: no API keys, no passwords, no token values. The two emails are
`@example.com` placeholders. What is left is about context, so each row needs your yes or no.

| # | Why it is on the list | Files |
|---|---|---|
| A | **Names production infrastructure**: the Supabase project ref, the Fly URL, the `claude_ro` role and its grants | `launch-roadmap-state.md`, `staging-supabase-project.md`, `anon-execute-is-the-default-not-a-decision.md`, `rls-denial-is-indistinguishable-from-absence.md`, `anchor-name-and-stable-id-handoff.md`, `slice-history.md` |
| B | **Business plans and costs**: tiers, pricing, per-video cost | `access-tiers-vision.md`, `cost-per-video-analysis.md`, `reservation-release-slice-state.md`, `playlist-sidebar-ux-branch-state.md` |
| C | **Your local machine**: home-directory paths, the memwatch watchdog, the token file's location | `process-conventions.md`, `mutation-harness-home-redirect-state.md`, `memwatch-watchdog-fseventsd.md`, `stranger-token-h2-done.md`, `local-manual-test-env.md`, `local-cloud-validation-run.md` |
| D | **Your own words and working preferences**: quotes, usage budget, priorities | `how-to-shape-a-message-to-me.md`, `the-user-does-not-follow-in-real-time.md`, `a-budget-stop-is-soft-with-a-reserve.md`, `owner-priority-order-1102.md`, `owner-decisions-1113-marketplace-ff-392.md`, `route-agents-by-task-model.md` (also cites prices from a pasted third-party article) |

**Suggested default:** ship no file in A–C; for D, ship only if you are happy for your quoted words to be
public. Everything else (the ~170 lesson files such as `a-check-result-is-not-the-claim.md`) is
process lessons with no infrastructure or personal content.

⚠ Bound: a grep finds only what it was told to look for. A file can mention something private in plain
words that no pattern matches. This list narrows your skim; it does not replace it.

## Answered

The owner answered on 2026-11-13 11:25, by one selection card per group:

| # | Answer | What it means when the shipped corpus is built |
|---|---|---|
| A (6 files) | **SHIP REDACTED** | The Supabase project ref, the Fly URL and the role names are replaced with placeholders |
| B (4 files) | **EXCLUDE** | Not in the shipped corpus |
| C (6 files) | **EXCLUDE** | Not in the shipped corpus |
| D (6 files) | **SHIP WITH QUOTES PARAPHRASED** | The rules stay; the owner's quotes are replaced with neutral wording |
| the ~170 other lesson files | **ship as they are** | no change |

So the shipped corpus is 193 files, less the 10 in B and C. The redaction (A) and the paraphrase (D) happen when the
corpus is built (plan Task 18, step "Build the shipped corpus"), each with a check that greps the output for the
original strings and fails if any is found. The list above is kept as the record of what was asked.
