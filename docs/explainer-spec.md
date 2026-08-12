# Design Note — the explain-diff skill

**Not a spec.** It began as one (`docs/understanding-gate-spec.md` → `docs/explainer-spec.md`) and two
dual adversarial review rounds removed everything a spec would have specified. The filename keeps
"spec" only because the four review documents cite it; a third rename would dangle them for no gain.

**Status: the skill exists and is in use.** This note records why it is the shape it is, and what would
retire it.

---

## What exists

| | |
|---|---|
| Skill | `.agents/skills/explain-diff/SKILL.md`, symlinked at `.claude/skills/explain-diff` (that directory is a symlink farm — the real tree is `.agents/skills/`) |
| Output | `~/explainers/YYYY-MM-DD-explanation-<slug>-<short-sha>.html` — outside the repo, so no `.gitignore` entry and nothing to commit by accident |
| Indexed | `docs/available-skills.md`, via `python3 scripts/regen-skills-doc.py` |
| Enforcement | **none.** No gate, no CI check, no script, no required scope |

Adapted from Geoffrey Litt's `explain-diff`
([gist `a29df1b5`](https://gist.github.com/geoffreylitt/a29df1b5f9865506e8952488eac3d524), from the talk
*Understanding is the new bottleneck*), which carries no licence. Sections 3 (*Boundaries touched*) and
4 (*Decisions this change encodes*) are this project's additions.

## Why

Every quality mechanism here aims at **correctness** — dual adversarial review, mutation-checked guards,
six ratchets, gate falsifiability. None produces any observation about whether the human understands
what was built. Litt's argument is that as agents absorb correctness-checking, the reason to understand
shifts from *verifying* to *participating*. Phase 6 of `docs/dev-process.md` arrives at the same place
from inside this repo, ending with *"what did we decide this milestone that isn't written down?" — the
one failure no tool can see.*

### ⚠ The premise is UNMEASURED

Both round-1 reviewers said so independently and they were right. PR #67 being 39 commits over 7 review
rounds shows the model was **absent**; it does not show the absence **cost** anything. No defect reached
master for want of it, no merge is known to have been wrong.

By `docs/portable-practices.md:14-16` an unmeasured belief does not earn a mechanism. So nothing is
enforced, and the experiment below is the attempt to measure it.

## Aimed at behaviour and decisions, not implementation

Settled 2026-08-12. The dual review already owns implementation correctness and duplicating it would be
a second mechanism for a served concern. The expensive defects here were never code-comprehension
failures — B5's unfalsifiable gate sentence, the daily cap drifting 500→5000 by direct SQL, SHAPE-vs-
SEQUENCE misclassification, an RLS denial read as an absence, the reservation protocol re-solving what
addressing had dissolved. Each is a wrong belief about behaviour at a boundary, or a decision nobody
wrote down.

`docs/process-checklists.md:64-68` already makes cross-module nullable/union values a **mandatory**
behaviours category, bought with 4 Blocking/High from one `| null` that survived six plan rounds. The
skill aims where that rule already points.

*Accepted cost:* the explainer will not help audit implementation quality, and the dual review now
carries that alone — a mechanism with a known failure rate (reviewers split three times; the
finding-reporting reviewer was right all three, twice against a CONVERGED verdict).

*Terminology:* the section is **Boundaries touched**, not "Seams" — `CONTEXT.md:29` uses **Storage Seam**
for a specific product concept, and the glossary legislates against bare unqualified reuse four separate
times.

## What two review rounds removed

Round 1 on v2: **26 findings**, 5 Blocking. Round 2 on v3: **20 findings**, 3 Blocking. Both rounds
NOT CONVERGED. Reviews: `docs/reviews/understanding-gate-spec-v2-{codex,claude}.md`,
`docs/reviews/explainer-spec-v3-r2-{codex,claude}.md`.

Sorting round 1's findings by target was the actual result: **the explainer itself drew none; every
Blocking and High landed on the enforcement layer.** Patching them would have been
`docs/review-method.md:40-43` in action — *"a local question can always be answered yes by patching…
a wrong shape never fails a round."*

| Removed | Killed by |
|---|---|
| PR-body record + `check-understanding-record.py` | **Unsatisfiable ordering.** Agent opens the PR with `PENDING`; human edits the body to record a score; `edited` is not a default `pull_request` activity type and `.github/workflows/ci.yml:14-18` sets no `types:`, so no run fires. Re-triggering means pushing, which moves the head, which invalidates the SHA just written |
| Mandatory scope | The premise is unmeasured |
| The comprehension quiz | **Gradeable by exhaustion.** A per-option explanation on every question, feedback on click, one self-contained file — the answer key ships inside the thing being graded |
| Blind-author guarantee | Attested by a name in a header, not observable |
| `render-explainer.py` + its refusal rules | Three of four were quiz rules; the position-balance rule audited the renderer's **own output**, so it could never fire |
| Override valve + counter | **The counted exit was the expensive one** — a false `4/5` is cheaper to type than a defensible override reason, so the counter reads zero and looks healthy |
| U1–U5 | Four gated the removed machinery; U2's asset scan named no instrument and was over-broad enough that a conforming page fails it |
| A process-checklists amendment + `.gitignore` entry | **No activation path.** `CLAUDE.md` @-includes only `AGENTS.md`, `dev-process.md`, `plugins.md`; `process-checklists.md` is read *"when you are working a gate"*, and this is not one |

**Round 2's own lesson, recorded:** several of its findings were caused by round 1's fixes, which is one
of the two consecutive rounds `docs/review-method.md:45-46` escalates on. Removal is itself an unreviewed
design change.

**Method note:** in round 1 the file was edited *while both reviewers read it*. The Claude reviewer
detected the change (451 → 475 lines) and re-anchored. Round 2 froze the file and both halves verified
the md5 first. Freeze before dispatching.

## The experiment

Nothing is enforced, so the only question that matters is whether the thing earns its keep.

> **Re-examine after 5 explainers or on 2026-09-30, whichever comes first.**
> **RETIRE THE SKILL** unless at least one explainer has produced: a **boundary** nobody had written
> down; a **decision that became an ADR**; a **corrected belief** — something believed about the system
> that wasn't true; or a **defect the dual review missed**.

Round 2 filed this as decorative because nothing counted the explainers. Putting them in `~/explainers/`
fixed that by accident: `ls ~/explainers | wc -l` is the counter. Not enforced — observable, which is the
honest bar for a thing with no gate. The date half still depends on someone looking.

### Run 1 — PR #78 (`5cbedcf`), backlog #34

`~/explainers/2026-08-12-explanation-absence-protection-enforced-5cbedcf.html`. 13 files inspected,
**7 not in the diff**. Scored honestly:

- **ADR candidate — yes.** The serve path's money guard depends on the storage policy granting at the
  *owner path segment* (`0007_storage_and_rpcs.sql:12-15`, the `split_part(name,'/',1)` clause at `:14`), so no policy can
  hide the magazine model while revealing the markdown. Grepping that migration for *serve / money /
  charge / reserve* returns only "preserves" and "preserved", and `split_part` appears in no other
  migration. The dependency lives solely in a comment in `lib/html-doc/serve-doc.ts`, which a migration
  author has no reason to open. **ADR-0005's lesson inverted:** there, code looked wrong without the ADR;
  here the migration looks *fine*, and tightening its grant would silently disarm a money guard.
- **A boundary nobody had written down — partially.** It is written down, on one side. What is
  undocumented is the coupling seen from the migration.
- **A corrected belief — yes, the author's.** This project's notes had been treating the 6¢→12¢
  double-charge as the defect PR #78 fixed. It isn't: the application was never losing money. The defect
  was that the protection was **ordering** — accidental, required by no signature, pinned by no test, and
  contradicted by the blob store's own comment claiming a 404 *was* provable absence.
- **A defect the dual review missed — no.**

What produced the finding was not the writing but the skill's requirement to read *outside* the diff. An
explainer built from the diff alone would have restated two good code comments.

## Deferred, with the findings that killed them

**The quiz.** Litt's speed-regulator argument is the strongest thing in the talk and dropping it gives
that up. A later attempt starts from these, not from the gist — round 1 produced five quiz findings and
all five must be answered, not the two that have known fixes:

| Finding | Content |
|---|---|
| Claude B2 | Answer key ships in the graded artifact → **first-click lock, score from first attempts only** |
| Claude H1 | "Answer with the explainer closed" is unrunnable by the same human twice → **a blind third agent answers; ≥4/5 means the quiz tests recognition**. Round 2 M4 warns this is uncalibrated in both directions: a frontier model scores above chance from plausibility priors, and a question answerable by `grep`-ing the diff scores *low* blind and so passes |
| Claude H4 / Codex H1 | Author blindness attested by a name in a header, not observable. **Deferred with the quiz — not moot;** the moment a quiz returns, so does the question of who wrote it |
| Codex M1 | "Which file changed?" questions pass every shape check and are answerable by diff search |
| Codex M2 / Claude H2 | "Correct option is longest" forces padding of distractors; "no position used more than twice" still allows one position to be correct 40% of the time against a 25% baseline |

**The micro-world.** Litt's second technique. It does **not** get its own trigger — v2 armed it at four
non-converging rounds and `docs/review-method.md:45-46` already escalates to REDESIGN after **two**. If a
REDESIGN round's findings are ordering-shaped, build a steppable simulation instead of reading again. It
is never a gate: it simulates the protocol, it does not execute it.

## Round-2 findings knowingly not addressed

- Nothing distinguishes an explainer that explored surrounding code from one that restated the diff. The
  `Inspected: N files, M outside the diff` header is written by the same agent. **No instrument; stated,
  not claimed.**
- "No external fonts, CDNs, images or network access" has no instrument either. Same status.
- The prompt-injection clause is guidance, not a control.
- The annotated sample covers the *Boundaries* section only; sections 4 and 6 are free prose.

## Provenance

All primary sources read 2026-08-12: the [talk](https://www.youtube.com/watch?v=WkBPX-oDMnA), the
[36-post thread](https://threadreaderapp.com/thread/2072522251300409556.html), the
[gist](https://gist.github.com/geoffreylitt/a29df1b5f9865506e8952488eac3d524), and its 14 comments via
`gh api` — where @Butanium and @fm1randa report the shipped quiz was passable by picking the longest
option, @yudhiesh-oc supplies fairness rules, @ankitg12 argues for a renderer, @ehsan-ami raises prompt
injection.

**Not used:** the Gemini transcript in `AI Augments Human Understanding in Development.docx` that started
this. Its reconstruction pins a three-generation-stale model and interpolates a diff into a
double-quoted shell string — the command-substitution footgun `docs/plugins.md` records being measured on
2026-08-04. The talk summary held up; the implementation advice did not.
