# Marketplace inventory — what this harness can ship to a stranger, and what cannot

> **Anchor:** `harness-ships-elsewhere` — **ADR:** none
> **Goal:** The harness this project built can be installed and used by someone who has never seen this repository.

**Status: SPEC, awaiting review. Nothing here is implemented.** This document is the Phase 1 artifact
for a milestone whose deliverable is a *decision*, not a published plugin.

⭐ **It is also the claiming document `docs/backlog.md` row 290 asked for.** That row recorded that
registering the comprehensibility suite in `docs/anchors.md` cannot be a one-line edit, because
`check-anchors.py` **R4** refuses a registry name no document claims, and named three candidate
claimants. This spec is candidate (a), and it claims `harness-ships-elsewhere` — which is broader
than the suite alone, because the owner asked for all three efforts to be inventoried.

---

## 1. Why this exists

The owner, 2026-10-15, in their words:

> *"I have been focusing on development process speed enhancement and comprehensibility for me about
> what you are doing… Now is the time to evaluate the efforts. Goal is to publish the features in
> marketplace. Not all of them may not be suitable for publish but let's take inventory and establish
> a milestone."*

Three efforts have been running in parallel. Each was justified on its own terms; none has ever been
asked *"could someone else use this?"* against a stated bar. That question is Deliverable 2's whole
content — **a battle-tested harness and reproducible framework for NEW projects** — and it has been
answered only informally, for one file, once.

**This milestone answers it for every component, with evidence, and records what the answer costs.**

---

## 2. Decisions of record — settled 2026-10-15 by selection card. Do not re-open.

| # | Decision | What it rules out |
|---|---|---|
| **D1** | **Audience: public strangers, full support bar.** Works in any repo, documented for a newcomer, failure modes handled without the author | Rules out "good enough for my next project". Coupling becomes a **release blocker**, not a tidiness note |
| **D2** | **Decomposition: one evaluation spec across all three efforts, then a spec per publishable unit** | Rules out going straight at the comprehensibility suite and deferring the other two with a shallow verdict |
| **D3** | **Route: a self-published marketplace repo**, installed with `/plugin marketplace add <repo>` | Rules out aiming at `claude-plugins-official`, whose acceptance gate would make "done" undefinable. Official submission may become a *later, separate* milestone |
| **D4** | **Method: a mechanical scan across all components, plus one real install experiment** on the comprehensibility suite (effort 3), where the experiment calibrates the scan | Rules out verdicts resting on reading the code and judging it |

**Why D3 is safe to commit to:** the route is proven on this machine, not theorised —
`~/.claude/plugins/marketplaces/` holds `omc`, a third-party self-published marketplace, alongside
the official one. A marketplace is a git repo carrying `.claude-plugin/marketplace.json`.

**Why D4 matters more than it looks.** This repository has measured that *review is the wrong
instrument for a surface*: six review rounds produced roughly seven edge cases where a single corpus
run produced 5,287. *"Can a stranger use this?"* is a surface question over **24 components** (17 + 3 + 4, enumerated in §3 — derived 2026-10-15, not estimated). Judgement
alone will miss things, and the misses are precisely the ones a stranger meets first.

---

## 3. Scope — the components, derived from disk rather than recalled

⚠ **Derived 2026-10-15 by enumeration.** The counts below are a dated measurement, not a live number.

### Effort (3) — comprehensibility

| Component | Lines |
|---|---|
| `explain-diff` / `brief` / `explain-findings` / `explain-topic` (SKILL.md) | 158 / 195 / 156 / 95 |
| `.claude/skills/shared/` — `explainer-delivery.md`, `corpus-search.md`, `handoff-path.md` | — |
| `scripts/brief-compose.py` | 1,780 |
| `scripts/explainer-serve.py` | 2,907 |
| `scripts/page_chrome.py` / `scripts/page_markup.py` | 450 / 438 |
| `scripts/gen-dashboard.py` / `scripts/gen-goals-page.py` | 3,546 / 1,252 |
| `.claude/hooks/regen-{backlog-page,dashboard,features-page,goals-page}.sh` | — |

⛔ **A FINDING BEFORE THE WORK STARTS: the D2 index undercounts its own subject by roughly 3×.**
`docs/portable-practices.md` describes the suite as *"9 files / 3,599 lines"*. The Python machinery
alone is **10,373 lines across six files**, before 604 lines of skills. That figure has been quoted as
settled since 2026-09-07. **Correcting it is in scope for this milestone**, and it is the first
evidence that an inventory was needed rather than a recollection.

⚠ Two further claims in that same block are stale and must be corrected with it: it says the registry
*"registers 10 anchors"* (it held **13** before this spec, and **14** after it, since this document allocates one) and that *"a second anchor is owed"* for the present-tense
reader (`explanation-on-demand` now exists).

### Effort (2) — development velocity

CI mutation sharding (39 references in `.github/workflows/ci.yml`), `scripts/check-plan-code.py`, and
the three velocity documents (spec, plan, `docs/velocity-evidence-2026-09-24.md`). **Q0 is designed in
form and not built** and is one of two items `check-roadmap-consistency` still reports open.

### Effort (1) — recall

`scripts/check-surface-recall.py` + `.claude/hooks/surface-recall.sh`, **157** memory files, and two
unmerged branches: `c5-recall-matcher` (6 commits) and `backlog-117-parser-substrate` (10).

⭐ **The measured result that must drive this effort's verdict, because it inverted:** lexical scoring
scored **2/20**; the same paraphrases read by an LLM scored **19–20/20**, with 0 false fires in 60.
Whatever ships here, it cannot be the lexical matcher.

---

## 4. The criteria

Criteria 1 and 2 are `docs/portable-practices.md`'s existing filters. D1's public bar adds 3 and 4.

| # | Criterion | Decidable by |
|---|---|---|
| **C1** | **Measured** — it works, with evidence, not a confident belief | existing self-tests and manifests |
| **C2** | **Project-independent** — runs with no Supabase, no Gemini, no Fly | **mechanically countable** |
| **C3** | **Self-contained** — does not depend on parts of this repo that are not shipping | **mechanically countable** |
| **C4** | **Supportable** — a stranger can install it, use it, and recover from failure without the author | ⛔ **not countable** — this is what the install experiment is for |

**C3 is expected to be the main killer, and the shape is already known.** `brief/SKILL.md`'s
ground-truth command list calls `scripts/check-*` — guards that are part of *this* repo's process, not
of any plugin. A component can be perfectly project-independent in its prose and still unusable
because it invokes a neighbour that is not shipping.

**Verdicts are per component, and there are exactly three:** `SHIP`, `NEEDS-WORK` (with the named
defect), `DON'T-SHIP` (with the reason). A fourth verdict — "unknown" — is not permitted; a component
that cannot be assessed is `NEEDS-WORK` whose named defect is *"no way to assess it"*.

---

## 5. The scan — `scripts/check-publishability.py`

Built as a guard because this repo's rule is *before adding a rule, ask whether it can be a script*.
It carries the usual contract: `--self-test` with a declared count verified by running it, a mutation
manifest, a caller, and no fail-open handler.

**Per component it reports:**

1. **project-specific references** — matches against a derived vocabulary (`supabase`, `gemini`,
   `fly`, `youtube-playlist`, repo-rooted paths), not a hand-written list;
2. **cross-repo dependencies** — invocations of files outside the component's declared shipping set;
3. **presence of a self-test and of user-facing documentation.**

⛔ **It must report CANNOT RUN rather than a clean score when it cannot resolve a component's shipping
set.** A zero over a set it failed to build is this repository's single most-measured failure.

**Its falsifier, which is the point of D4:** any blocker the install experiment hits on a component
the scan scored clean is a **scanner defect**, fixed in the scan, not recorded as a footnote. The scan
is not permitted to be an opinion in script form.

---

## 6. The install experiment

A throwaway repository **outside** this one, with no Supabase, no Gemini, no Fly credentials and no
`scripts/check-*`. The suite is added as a local marketplace and installed the way a stranger would.

**Pass condition, stated so it can fail:** a page is **produced and served**, and the reader can ask a
question inside it, from that repository. Producing a file that cannot be served is not a pass —
serving is the half that carries the Ask channel, and `file://` loses it by design.

**What is recorded:** every failure, its cause, and whether the scan predicted it. The experiment's
output is two lists — defects in the suite, and defects in the scan.

⚠ **Bound, stated rather than hidden:** the experiment covers the comprehensibility suite only. It
says nothing about efforts (1) and (2), whose verdicts therefore rest on C1–C3 plus argument, and
**must be labelled as such in the inventory.** An install experiment for those is out of scope here
and is a candidate follow-up if either survives.

---

## 7. What PR 1 produces

1. This spec, reviewed and committed.
2. `scripts/check-publishability.py` + `--self-test` + mutation manifest + CI registration.
3. The install-experiment record: failures found, and which the scan predicted.
4. **The inventory** — every component of all three efforts with `SHIP` / `NEEDS-WORK` / `DON'T-SHIP`
   and its evidence.
5. A roadmap milestone, and a `docs/backlog.md` row per `NEEDS-WORK` component.
6. `docs/anchors.md` — `harness-ships-elsewhere` registered, claimed by this document. **Closes row 290.**
7. Corrections to `portable-practices.md`'s three stale claims (§3 above).
8. The scoring rubric as a `portable-practices.md` entry — a reusable publishability test is itself a
   D2 contribution, and this milestone is the measurement that earns it.
9. A dashboard entry.

**What PR 1 explicitly does NOT do:** publish anything, create the marketplace repo, or fix any
coupling — including `brief/SKILL.md`'s nine known references. Fixing a component while also judging
it is how this repository has previously manufactured a false green, and the owner chose option A
specifically to keep evaluation independent of repair.

---

## 8. Risks

| Risk | Mitigation |
|---|---|
| The scan becomes an opinion in script form | §5's falsifier: the install experiment can declare the scan defective |
| The inventory is written from recall and drifts, like the 9-files figure | Every count derived by command, dated, and the derivation recorded beside it |
| Efforts (1) and (2) get weaker verdicts than (3) | Stated as a bound in §6 rather than hidden; their verdicts are explicitly labelled argument-based |
| The milestone becomes "publish everything" by momentum | `DON'T-SHIP` is a first-class verdict; a component that fails C1–C4 is recorded as such, and that is a successful outcome of this work |
| ~11,000 lines is too much to assess per line | Assessment is per component against four criteria, not per line |

## 9. Falsifiers

- **For the inventory:** a component marked `SHIP` that the install experiment cannot run.
- **For the scan:** a blocker the experiment hits that the scan scored clean.
- **For this spec:** if the install experiment cannot be made to run at all, D4 is unachievable and the
  method must be re-decided with the owner rather than silently downgraded to paper scoring.

## 9b. What the spec self-review caught in this document

Recorded rather than silently fixed, because this spec argues for derived numbers and was itself
written with an invented one.

- **"~13 components" was invented.** The derived figure is **24** (17 + 3 + 4). Nothing depended on
  13; that is the point — a number with no provenance passed straight into a design document whose
  §8 lists exactly this drift as a risk.
- **"the strongest candidate" was ambiguous** in D4 while §6 named the comprehensibility suite
  explicitly. D4 now names it too.

## 10. Out of scope, named so the gap is not read as closed

Official-marketplace submission (D3); creating the marketplace repository; fixing any coupling;
building Q0; merging the two recall branches; and an install experiment for efforts (1) and (2).
