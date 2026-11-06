# Round 1 — `import-py-spelling` (backlog #498) — coordinator — NOT CONVERGED, both fixed

REVIEW GAP: claude — weekly usage 99% on the last night before the reset. Codex: `docs/reviews/codex/import-py-spelling-r1-codex.md`, on `e9c6251e`.

```yaml
round: 1
fixes_nontrivial: true
subject: import-py-spelling
halves:
  codex: ran
  claude: gap
findings:
  - id: MAJOR
    component: mutations
    verdict: accepted
    fix: the stem and filename spellings are two statements, so the PR #496 stem mutation and the #498 filename mutation have distinct anchors
  - id: MINOR
    component: self-test
    verdict: accepted
    fix: the declared case count is 310
```

Both mutations are killed by their named cases (measured); the self-test passes 310/310.
