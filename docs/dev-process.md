# Development Process — Project-Specific

The global process (phases, gates, tools, TDD policy, adversarial review) is defined in `~/.claude/CLAUDE.md` under **Development Process**.
This file captures only what is specific to this project.

---

## Sub-Projects

Two sequential sub-projects. Sub-project 2 does not begin until Sub-project 1 is fully verified and merged.

| Sub-project | Scope |
|---|---|
| 1 — Backend | Types, lib layer, API routes, ingestion pipeline, deep-dive pipeline |
| 2 — Frontend | React components, SSE consumption, Obsidian URI, PDF viewer |

---

## Mocking Boundaries

| Boundary | What is mocked |
|---|---|
| `lib/gemini.ts` | All Gemini API calls |
| `lib/youtube.ts` | YouTube Data API + transcript fetching |
| API route level | E2E tests mock here, not at the lib boundary |

---

## Adversarial Review Precedent

The Codex review of `docs/design-spec.md` and `docs/implementation-plan.md` (between Tasks 2 and 3) caught five significant gaps: SSE job identity, path traversal risk, deep-dive transcript fallback underspecification, output folder ambiguity, and Obsidian vault URI semantics. These were architectural decisions that would have affected Tasks 3–10 if left vague.
