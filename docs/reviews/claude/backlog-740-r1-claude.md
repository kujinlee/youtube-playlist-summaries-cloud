Reviewed head: 7481f0b60ebaa84ea0ce4a324345fdbf035544a0

# backlog-740 r1 Claude review

## Findings
- NIT, scripts/check-retired-references.py:57 — the pointer to "its own comment above HOME_PATHS" is accurate but that comment (check-page-links.py:101-106) states only the prefilter bound and the joined-literal reach; the "top-level scripts/*.py outside _self_test*" reach lives at the rule-2 code (check-page-links.py:~195-200). Not wrong; the reader must look two places. No failing input.

No other findings.

## Evidence
1. Skip gone: _text_findings on a .sh path refuses all of `*/ fetch("/dashboard");`, `/* a */ // gen-dashboard.py`, `# regen-dashboard.sh`, an indented `# gen-dashboard.py`, `// the /dashboard page` (each one [text] finding). No _whole_line_comment or comment param remains (grep). Python comments unseen by ast: docstring line 45 and ok message state it; case 15.11 "prose and comments pass" stays and covers the Python comment.
2. Cases: 15.5 expects ["workflow","workflow"], 15.11 expects ["hook","workflow","text","text"], G2 second case expects ["text","text"]; comment halves became refusals, none deleted; R3-1 and R3-4 added. No staying case weakened.
3. Mutations: G2 entry removed; K8 text-kind anchor and the "#!" anchor re-bound and resolve; new "comment skipped again" entry killed and attributed to its named case. Manifest length 15 == pin 15. Sweep: 15 killed, 15 attributed, 0 survivors.
4. Prose: ok message built from TEXT_SUFFIXES, EXEMPT_PREFIXES, SELF. Backlog 736, roadmap S3 line, plan K8 scope cite the NOT SCANNED section with no list. check-ask-store.exemption_reason exists (line 186). Rewordings in check-review-recorded, check-main-drivable, page_markup, round-header-template are accurate past tense (gen-dashboard.py replaced by gen-backlog-page.py in the template).

## Gates (last lines)
- check-retired-references --self-test: 75/75 passed
- check-retired-references: rc 0, "check-retired-references: ok — ... docstring's NOT SCANNED section gives each reason)"
- check-plan-code --mutate . --only scripts/check-retired-references.py: OK — 15 mutation(s), 15 killed, 15 attributed, 0 survivor(s)
- check-docs: Documentation integrity OK
- self-tests: check-main-drivable 462/462, check-review-recorded 285/285, page_markup 204/204

VERDICT: CONVERGED
