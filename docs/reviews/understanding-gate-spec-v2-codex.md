<!-- codex-review: model=gpt-5.5 -->

Blocking — The enforced gate records a claim about understanding, not evidence of understanding.  
Failure scenario: code PR touches `lib/`; agent writes `Understanding check: 4/5 against <head>` into the PR body without the human taking the quiz, or after an agent answers for them; `check-understanding-record.py` can observe line presence and SHA freshness, but cannot observe who answered, what they answered, or whether the score is true, so it passes in both worlds. Anchor: `docs/understanding-gate-spec.md:270`, `docs/understanding-gate-spec.md:284`, U3 at `docs/understanding-gate-spec.md:378`.

Blocking — U5 is a manual mutation check with no runnable isolation boundary.  
Failure scenario: first real explainer’s quiz is answered “with the explainer closed,” but the human has already read the explainer, the diff, review summaries, or chat context; alternatively an agent answers from the code. The named observation, “can score >=4/5 with only PR title,” is not instrumented and cannot be independently reproduced. Anchor: M2 mutation check at `docs/understanding-gate-spec.md:183`, U5 at `docs/understanding-gate-spec.md:380`.

High — “Independent quiz author” is asserted by metadata the system cannot verify.  
Failure scenario: the explainer author also writes the quiz, or a “fresh Claude subagent” inherits conversation context containing the explainer; the HTML header says `Quiz author: codex` or “distinct,” and the PR line says “quiz by codex.” No proposed script reads an audit trail proving blindness to the explainer. Anchor: `docs/understanding-gate-spec.md:167`, header field at `docs/understanding-gate-spec.md:264`, D2 at `docs/understanding-gate-spec.md:397`.

High — D4 turns the gate into a normalizable override with no stopping rule.  
Failure scenario: after 20 time-pressured PRs, most bodies say `Understanding check: OVERRIDDEN ... reason: urgent`, CI remains green, and the only defense is a printed count nobody is required to act on. This has the same shape as a known-red suite becoming accepted state: visible, counted, still non-blocking. Anchor: grading override at `docs/understanding-gate-spec.md:195`, M5 counting rule at `docs/understanding-gate-spec.md:284`, D4 at `docs/understanding-gate-spec.md:406`.

High — The spec adds a second merge-orientation mechanism without proving current merge artifacts are insufficient.  
Failure scenario: a PR already has full review, convergence trail, PR body, merge tick, and human merge gate; the new explainer re-summarizes the same change rather than filling a demonstrated missing observation. The spec cites PR #67 size and review count, but not evidence that the human made a wrong merge decision or lacked the model after existing Phase 5/whole-branch review. Anchor: concern table at `docs/understanding-gate-spec.md:69`, existing Phase 5 gate at `docs/dev-process.md:86`, human merge gate at `docs/dev-process.md:105`, whole-branch review emphasis at `docs/review-method.md:277`.

Medium — The renderer’s refusal rules can still admit trivially passable quizzes.  
Failure scenario: five questions ask “which file/function changed?”, “what route is affected?”, or “which config flag gates this?” with equal-length options, balanced positions, and per-option explanations. The renderer passes all four shape checks, but the quiz is answerable by diff search or filename recognition, not by a mental model. Anchor: M3 refusal list at `docs/understanding-gate-spec.md:217`, “SHAPE, not TRUTH” caveat at `docs/understanding-gate-spec.md:224`.

Medium — The renderer can reject legitimate comprehension questions because correctness is often longer than distractors.  
Failure scenario: a good edge-case question has one precise correct answer naming condition, actor, and consequence; shorter distractors are wrong because they omit one clause. The “correct option is longest” and 40% length-median rules force either rejection or artificial padding of wrong answers, degrading the question to satisfy the proxy. Anchor: `docs/understanding-gate-spec.md:219`, `docs/understanding-gate-spec.md:221`.

Medium — The CI/`gh` coupling leaves workflow gaps unstated.  
Failure scenario: repo has no remote so Phase 5 allows direct commit, or a code change lands by direct push/web edit, or `gh` cannot identify the intended PR in CI; the spec says code-touching PRs require the gate but does not define the non-PR/direct-commit equivalent. “Cannot run” fails closed only when the script is invoked; it does not cover code changes outside PR events. Anchor: direct-commit path at `docs/dev-process.md:99`, script/`gh` dependence at `docs/understanding-gate-spec.md:284`, CI PR-only wiring at `docs/understanding-gate-spec.md:426`.

Low — U2’s external-reference detector is overbroad and under-specified.  
Failure scenario: a code block or explanatory text legitimately includes `src=`/`https://` and must be excluded by parsing HTML/code blocks correctly; conversely obfuscated external references, CSS `url(...)`, forms/actions, meta refreshes, or entity-encoded URLs may bypass a naive substring scan. The spec names tokens, not a DOM/CSS parsing strategy. Anchor: U2 at `docs/understanding-gate-spec.md:377`, safety/output constraints at `docs/understanding-gate-spec.md:138` and `docs/understanding-gate-spec.md:251`.

NOT CONVERGED — I checked the proposed M1-M5 mechanisms, U1-U5 gates, the existing Phase 5/6 process, the spec-content rules, portable-practice lessons, plugin fallback rule, glossary claims, and both checker contracts; the central understanding gate is still mostly a PR-body assertion rather than an observable guard.
