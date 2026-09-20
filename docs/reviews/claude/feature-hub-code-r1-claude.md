<!-- Claude half of code round 1. Filed 2026-09-20. -->

# Feature hub — code review r1, Claude half

⚠ **WHAT THIS HALF SAW, stated because the two halves of this round saw DIFFERENT TREES and filing
them as one round without saying so would be the misleading part.**

| Half | Range reviewed | HEAD at the time |
|---|---|---|
| **claude** (this file) | `e693f36a..118ef831` — the whole branch as it stood when all six tasks were complete | `118ef831` |
| **coordinator/codex** | the same branch three commits later, after two doc-only commits and one docs+counts commit | `eca53b8d` |

The three commits between them (`102c2502`, `60059fd5`, `eca53b8d`) were reviewed separately by a
scoped re-review over `118ef831..102c2502`; the other two are documentation only. **Neither half saw
`8df15f6f`**, which is the fix wave for the Codex half's own findings and therefore could not have
been seen by either.

⭐ **The two halves did not overlap, which is this repo's recorded expectation rather than a
surprise.** This half found three Important issues about composition — a page-producer family that
grew to five while five inventories still said four, four copies of grammars their owners already
had, and a tree whose completeness nothing measures. The Codex half found a **Blocking** and a
**High** that this half missed entirely: the parser exempted `>` and `<!--` so a status token could
ride into a node unchecked, and duplicate fields were last-write-wins so forbidden content could be
overwritten before any rule read it. Both are cases where the gate could be made to PASS input it
exists to refuse — and eight Claude reviews across six tasks did not find either.

**Preceding per-task reviews** (six tasks, each with a spec + quality verdict, three of which
required a fix round) ran in `.superpowers/sdd/2026-09-19-feature-hub/`, which is git-ignored. That
is precisely why `check-review-recorded.py` refused this branch: the reviews were real and found
real defects, but the repository could not show that any of them had seen the code. Recorded here so
it can.

---

# Final whole-branch review — `feature-hub-spec` @ `118ef831` vs `origin/master` `e693f36a`

19 commits · 24 files · 4,347 insertions · 1 deletion. Reviewed for **composition**, not per-task
correctness (all six tasks passed their own spec+quality review).

**VERDICT: READY TO MERGE.** Nothing found here blocks. The one gate that is red is the already-owned
dashboard entry. Four follow-ups below should ride in this same PR because four of them are one-word
or one-clause edits and one of them is the same defect class this branch already paid two fix rounds
for.

---

## 1. Gates — run by me, exit codes captured BEFORE any pipe

| Gate | rc |
|---|---|
| `check-docs.py` | 0 |
| `check-features.py` | 0 — *26 nodes (24 built, 2 absent); 13 anchors and 21 areas claimed exactly once* |
| `check-features.py --self-test` | 0 — 25/25 |
| `gen-features-page.py --self-test` | 0 — 8/8 |
| `check-ratchet-contract.py` | 0 — 37 guards discovered, `check-features.py` among them |
| `check-selftest-counts.py` | 0 — 42 scripts, every declared count verified by running it |
| `check-fixture-variation.py scripts/check-features.py` | 0 — 6 parameters |
| `check-fixture-variation.py scripts/gen-features-page.py` | 0 — 7 parameters |
| `check-fixture-variation.py --self-test` | 0 — 67/67 |
| `check-plan-code.py --self-test` | 0 — 128/128 |
| `check-anchors.py` | 0 — 13 registered, all claimed, floor 22 held |
| `check-review-rounds.py` | 0 — 279 parsed, 0 silent gaps |
| `check-backlog-closure.py` | 0 — WARN on #117, pre-existing, unrelated |
| `check-explainer-delivery.py` | 0 |
| `check-vocabulary-collisions.py --self-test` | 0 — 10/10 |
| `explainer-serve.py --self-test` | 0 — **202/202**, unchanged by the registration |
| `check-dashboard-entry.py` | **1** — known, owned, task #24 |

No TypeScript touched, so `tsc --noEmit` not run (correct — the branch is Python, Markdown, one
bash hook, one YAML, one JSON).

**I independently reproduced all 27 mutations** (17 `check-features` + 10 `gen-features-page`) by
applying each edit to a copy of the delivered file and running its suite. Every anchor matched
**exactly once**; every mutation went red **via the case it names**; zero survivors. Two red more
than one case — see M3 below, which is the finding.

---

## 2. Findings

### Important

**I1 — The branch is the 5th page generator, 4th `brief-compose` caller and 4th regen hook, and every
place that states those counts still says the old number.** Confidence: **high**, all measured.

| Location | Says | Is |
|---|---|---|
| `CONTEXT.md:100` | "The repo generates **four** local HTML pages … the dashboard, the backlog table, the goals view, and the explainer viewer" | five; `/features` is not in the list |
| `CONTEXT.md:107-108` | "`scripts/page_markup.py`, the single implementation of inline markup for all **four** generators" | five importers (measured: `gen-features-page`, `gen-backlog-page`, `gen-dashboard`, `gen-goals-page`, `explainer-serve`) |
| `scripts/gen-goals-page.py:1225` | "one tray, **three** page-producing callers" | four — and `gen-features-page.py:649` correctly says **four**, so the two comments now contradict each other |
| `scripts/page_chrome.py:117,122` | present tense, "**five** pages that deliberately differ" | six `chrome_css`/`chrome_bar` consumers |
| `docs/portable-practices.md:15-16` | "plus the **three** hook-regenerated pages (`regen-backlog-page.sh`, `regen-dashboard.sh`, `regen-goals-page.sh`)" | four on disk; `regen-features-page.sh` is absent from the list |

The last one is the costly one: `docs/portable-practices.md` is **deliverable #2's shippable
inventory** — the file whose opening paragraph the user asked for by name so the suite could be
published. It now under-reports the suite by one page and one hook.

The failure this causes is not runtime. It is that "one renderer for four pages" — the *rationale*
for the shared seam — is now stated over the wrong denominator in the glossary a Phase 6 review is
instructed to read first. Five one-word edits.

⚠ This is the same defect class as the two fix rounds this branch already paid (Task 3's
mechanism-vs-purpose lines, Task 4's `SEV_GLYPH` "derived" comment): **a sentence making a claim its
subject does not support.** The branch caught it twice inside its own files and missed five
instances one file out.

---

**I2 — Four new copies of grammars that other scripts own.** Confidence: **high** on the facts,
**medium** on the severity — all four agree with their owner today, so this is latent, not live.

| New copy | Owner it re-implements |
|---|---|
| `check-features.py:120` `anchor_slugs()` — `r"^\|\s*`([a-z0-9-]+)`\s*\|"` | `check-anchors.py:71` `REGISTRY_ROW` — byte-equivalent |
| `gen-features-page.py:83` `ANCHOR_ROW` | the same registry row, plus the ADR column |
| `gen-features-page.py:84` `DOC_ANCHOR` — `r"^>\s*\*\*Anchor:\*\*\s*`([a-z0-9-]+)`"` | `check-anchors.py:68` `ANCHOR` — the ADR-0010 document-header grammar |
| `check-features.py:102` `CELL_SPLIT = re.compile(r"(?<!\\)\|")` | `check-docs.py:319`, **named as the owner in the plan's own Global Constraints** |

The `CELL_SPLIT` one is the sharpest, because the counter-example is in the same page family:
`gen-backlog-page.py:86-98` has

```python
def _cell_split() -> re.Pattern[str]:
    """Borrow the row splitter from the ratchet that owns it, so there is ONE definition of where a
    table cell ends. …"""
```

…and imports it via `importlib`. `gen-features-page.py` already uses that exact technique twice
(`_load("check-features")`, `_load("gen-backlog-page")`), so the capability was in hand and used for
the severity map and the backlog parser — and not for these four.

**Measured agreement today**, so no live defect: `check-anchors.parse_registry` = 13,
`check-features.anchor_slugs` = 13, `gen-features.anchor_adrs` = 13, sets identical. Over
`docs/superpowers/{specs,plans}`: the strict `check-anchors` grammar sees **51** documents, the loose
`DOC_ANCHOR` sees **51**, symmetric difference **empty**.

The failure it will cause: a change to the registry-row or `> **Anchor:**` grammar turns
`check-anchors` red *and silently drops documents from `/features`* — on a page whose stated premise
(`gen-features-page.py:18-19`) is *"A second copy of a fact can disagree with the first … a link
cannot."*

Sub-case: **two readers of the backlog `(area)` column now ship on one branch** —
`check-features.backlog_areas()`'s positional `cells[-3]` (`:113`) and `gen-backlog-page.parse`'s
`bundle` field, which the page itself uses. Measured equal today (21 vs 21, zero symmetric
difference). The repo's own `a-positional-read-needs-a-verified-shape` lesson is about `cells[-2]`
hitting the wrong cell.

---

**I3 — Coverage is unmeasured by design, and there are real omissions.** Confidence: **high** that
they are unrepresented; **medium** on whether each deserves its own node.

`check-features.py` validates only the edges **into** the tree: every registry anchor and every
in-use backlog area is claimed by exactly one node. Nothing checks the reverse — that every
subsystem *has* a node. So the taxonomy's completeness is exactly as good as the author's recall,
which is the failure the tree exists to fix, one level up. The `absent` state covers absences
somebody **declared**; the undeclared-subsystem case has no mechanism and is not named as
out-of-scope anywhere in the spec.

Measured omissions with no node and no `absent` declaration:

- **Accounts / sign-in / anon-vs-registered tier.** `app/login/page.tsx`, `app/dev-login/page.tsx`,
  `app/auth/auth-error/page.tsx`, `supabase/migrations/0003_provisioning.sql`,
  `profiles.is_anonymous` (4 files reference it). CONTEXT.md gives **Tier** its own glossary entry.
  `access-control`'s `for:` line is about *reachability*, not *identity* — a person signing in, and
  an anonymous visitor being provisioned, is a distinct user-facing feature.
- **Personal review** (personal score + note). `app/api/videos/[id]/review/route.ts`, 151 lines;
  CONTEXT.md gives it a whole glossary section with four defined terms. `browse-the-library` is
  about *finding*, not annotating.
- Lesser, each arguably foldable: **AI ratings** (CONTEXT.md section), **quick view**
  (`app/api/videos/[id]/quick-view/route.ts`, `app/api/quick-view/backfill/route.ts`,
  `lib/quick-view-callout.ts`), **archive** (`lib/archive.ts`,
  `app/api/videos/[id]/archive/route.ts`), **section timestamps** (`lib/summary-section-timestamps.ts`,
  `lib/timestamp-audit.ts`, `lib/timestamp-repair.ts` — a merged slice with no node and no anchor).

This is not a request to add eight nodes. It is the observation that **nothing on this branch can
tell the difference between "the system does not do that" and "nobody remembered it"**, on a page
titled *what this system currently does*.

---

**I4 — `expected-because:` prose is completely unbounded, and both shipped instances already carry
uncheckable code citations.** Confidence: **high** on the facts; this is a **design gap, not a
deviation** — the spec specified the status-token rule for `for:` only.

`check-features.py:83` applies `STATUS_TOKENS` to `n.purpose` and to nothing else. An
`expected-because:` line may contain `#322`, `✅`, `currently` or anything at all, and it is rendered
on the page (`gen-features-page.py:431`).

Both shipped absent nodes use that freedom for **code line-number citations**:

- `docs/features.md:47` — "`listByPlaylist` hard-filters `job_kind = 'summary'`
  (lib/storage/supabase/supabase-job-queue.ts:28)"
- `docs/features.md:63` — "the share route renders with `dig: false` (app/s/[token]/route.ts:110)"

**I verified both, exactly**: `supabase-job-queue.ts:28` is
`.eq('playlist_id', playlistId).eq('job_kind', 'summary')`; `app/s/[token]/route.ts:110` is
`const html = renderMagazineHtml(parsed, model.model, { nonce, dig: false, share: true });`, against
`lib/html-doc/render.ts:62` `const showDig = opts.dig ?? true`. Both correct today.

The problem is that nothing keeps them correct, on the file whose own header (`docs/features.md:7-9`)
says *"This file holds NAMES and PURPOSE, never STATE"*, and in a repo whose backlog **#139** is the
worked example of a stale line citation costing a re-derivation — a citation this very branch's
coordinator had to re-verify by hand. The design's anti-rot argument (*"a sentence that never
mentions state has almost nothing that can become false"*) is made about `for:` and silently
inherited by `expected-because:`, which in practice does the opposite.

---

### Minor

**M3 (the ledger's, CONFIRMED BY MEASUREMENT — fix it).** `scripts/check-plan-code.py:998-999`:

> `# … the area CELL INDEX and the escaped-pipe lookbehind with no falsifier at all. The cell index is the`
> `# one worth naming: `cells[-3]` -> `cells[-4]` reds TWO cases, …`

I applied all 17 mutations over a green control and counted red cases. **Exactly two red two cases:**

| Mutation | Red cases |
|---|---|
| `the backlog area is read from the wrong cell of the row` | `backlog areas are read from the area cell`, `a row with an ESCAPED PIPE is not dropped` |
| `the trunk stops being carried down, so every node looks like it sits outside a trunk` | `trunk is carried down`, `clean tree has no problems` |

"the one worth naming" asserts a uniqueness the code does not have. Same class as I1 and as the two
fix rounds this branch already paid. One clause.

**M2 (the ledger's, confirmed).** `.github/workflows/ci.yml:190-191` — *"Two rules carry the weight,
and both are cross-file"*. Rule 1 is a conjunction: "names a fragment" is decided **locally** in
`check_nodes` (`check-features.py:88`); only "that exists" is cross-file (`check_cross`). One word.

**M5 — `gen-features-page.py:33-34`** claims *"MEASURED 2026-09-19 over 286 PR subjects and 26 nodes:
11 subject matches across 8 nodes."* Measured by me today through the shipped code: **285** subjects,
11 matches across **6** nodes. It is a dated snapshot, which this repo accepts — but it was already
wrong on the branch that ships it, and the sparseness number is the one a reader uses to judge the
band.

**M6 — `check-features.py:243`, `wnodes` assigned and never read** (Task 1 deferred minor,
confirmed). One character (`_`).

**M7 — two `parse_features` problem paths have no case and no mutation** (Task 1 deferred minor,
confirmed): `"sits outside any trunk"` (`:44`) and `"field before any node"` (`:59`). Both emit real
problem strings that nothing can prove still fire. Coverage, not correctness — but the 17-entry
manifest is the natural home for two more.

**M8 — hook `case` arms over-match nested subdirectories** (Task 5 deferred minor, confirmed). Bash
`case` glob `*` matches `/`, so `docs/superpowers/plans/sub/dir/x.md` fires the regen. Inherited
verbatim from `regen-goals-page.sh`; fails in the benign direction (rebuilds more often, never less).

**M9 — hook cost.** `gen-features-page.py` is 0.846s and fires on every write under `docs/reviews/*`
and `docs/superpowers/plans/*`, the two most-written trees in this repo's own process. Accepted as
sub-second and non-blocking. Worth a backlog row with its trigger stated: the cost scales with
26 nodes × 277 fragments and **nothing bounds either**.

**M10 — `check-fixture-variation.py:120-122`** emits an invocation form (`check-features.py` rather
than `scripts/check-features.py`) that exits 2. Pre-existing, out of scope, loud and
self-describing. Backlog row.

### Not findings — checked and clean

- **`gen-features-page.py` is a true peer, not a fifth way.** It uses `page_chrome.chrome_css` /
  `chrome_bar` / `chrome_script` / `provenance` / `assert_wired`, `page_markup.escape` /
  `render_inline`, and composes through `brief-compose.py` — the same five seam points as all three
  siblings, in the same order, with its own local `CSS` block exactly as each sibling has. **4 of 4
  page producers share the seam**; it adds no new serving mechanism, no new hook pattern, no new
  registry idea.
- **The severity map and the backlog parser are genuinely reused**, not copied
  (`sev_glyphs(backlog_page().SEVERITY)`, `backlog_page().parse`). The Task 4 fix round did real work.
- **All four `absent`/`built` spot-checks resolve to real code**: `wake-on-visit` →
  `lib/job-queue/worker-wake.ts`; `correct-a-summary` → `lib/corrections/`;
  `sync-with-a-local-vault` → `lib/cloud-sync/` (12 files); `bounded-serve-path` →
  `lib/serve-budget.ts`; `deploy-verification` → `playwright.prod.config.ts`,
  `tests/e2e/prod-fixture.ts`; `review-loop` → `scripts/check-review-decision.py`.
- **`shared-dig-deeper` is real** — verified above at three call sites. So is `dig-job-recovery`.
- **The `(cloud/money)` / `(cloud / money)` duplicate is real** — 4 rows and 2 rows in
  `docs/backlog.md`, both claimed on `features.md:91`, which is the spec's stated mechanism working.
- **The footer's capitalisation claim holds.** `render()` emits lower-case `not built` exactly twice
  for two absent nodes; the footer's `“Not built”` does not satisfy the case. Measured.
- **The `202/202 → 201/202` claim holds.** I widened `PAGE_SOURCES["features"]` to directories on a
  copy: rc=1, `[FAIL] ...and every declared source is a real file in the repo`, 201/202. Reproduced
  exactly, red via the case it names.
- **`REVIEW_CAP = 6`'s comment holds** — `blob-key-encoding` matches **49** review documents.
- **`explainer-serve.py` registration is complete and cost nothing**: `REGENERABLE` +
  `PAGE_SOURCES`, self-test unchanged at 202/202.

---

## 3. The two decisions I was told not to re-litigate — did either cost anything concrete?

**(a) Clearing the Phase 2 gate on judgement — YES, and it cost exactly what the plan's own falsifier
predicted.** Task 6 measured 1 of 5 registrations named by its own `--self-test`. That is already
headed to the human and I agree with the ledger's sharper reading: the guards caught everything,
both catching guards run in CI, nothing could have shipped broken. **I do not think it understates
the problem — but I would widen the repair.** One word ("guards" not "self-tests") fixes the
sentence; the *shape* is general and already has a name in this repo —
`separate-the-rule-from-the-fetch`. A pure-rules `--self-test` structurally cannot observe a
registration, so the plan should say that rather than correct one sentence. Cost: a wrong sentence
in a plan document. No shipping risk.

**(b) The 7-vs-3 inequality — NO concrete cost.** I reproduced the measurement that justifies it
(above). The residual is stated in three places: `explainer-serve.py:144-153`, the hook header, and
the plan. That is the right number of places for something a reviewer will flag every time.

---

## 4. Merge-blocking triage of the deferred minors

| Item | Blocks merge? | Why |
|---|---|---|
| **M3** — `check-plan-code.py:999` "the one worth naming" | **No — but fix it in this PR.** One clause; I measured it false; it is the same class as two fix rounds already paid on this branch |
| **M2** — `ci.yml:190` "both are cross-file" | **No — ride it with M3.** One word |
| Task 1 — `wnodes` unused | No | One character |
| Task 1 — two untested `parse_features` paths | No | Coverage, not correctness. File it |
| Task 4 — Pyright `importlib` / `Node` type | No | A consequence of the hyphenated-filename convention the whole repo uses |
| Task 4 — 4 further Minors in `task-4-review.md` | No | Already adjudicated by the task reviewer |
| Task 5 — nested-subdirectory over-match | No | Inherited from `regen-goals-page.sh`; benign direction |
| Task 5 — 0.846s hook on the two busiest trees | No | Backlog row with the trigger stated |
| Task 6 M4 — `check-fixture-variation.py:120-122` | No | Pre-existing, out of scope. Backlog row |
| Task 6 M5 — the false list-valued `expect` premise | No | Already recorded; nothing to fix |
| **Branch** — `check-dashboard-entry.py` rc=1 | **Yes, and it is already task #24.** | On content: the entry should name `/features` as a new user-visible page, and say that the taxonomy's completeness is not machine-checked (I3) so a reader does not read the page as exhaustive |

---

## 5. Question 7 — what did this branch decide that is not written down?

**Four things.**

1. **That the page-producer family is now five — and none of the five places that state its size was
   touched.** (I1.) The decision was made and executed; the inventory was not. Most consequential in
   `docs/portable-practices.md`, which is deliverable #2's shippable manifest, and in `CONTEXT.md`,
   which Phase 6 is instructed to read first.

2. **That `check-features.py` and `gen-features-page.py` may re-implement grammars other scripts
   own.** (I2.) The plan wrote a rule down for *one* of them — "never write a second splitter,
   `check-docs.py:319` owns `CELL_SPLIT`" — and the implementation then wrote a second definition of
   that exact regex. Three more copies of the anchor grammar followed, and no spec, plan, ledger
   entry or review records a decision to have them. They were not chosen; they accumulated.

3. **That coverage is out of scope.** (I3.) The spec's Enforcement table lists six rules, all edges
   *into* the tree. "Is anything missing from the tree?" is never named as in scope or out of it.
   The `absent` state was designed for absences someone declares; the *undeclared subsystem* has no
   mechanism, no owner and no written decision — and it is the case that determines whether the
   page's title is true.

4. **That `docs/features.md` may carry code line-number citations in an unbounded prose field.**
   (I4.) The anti-rot argument was made for `for:` and silently extended to `expected-because:`,
   which is where both shipped citations live. Nobody decided that; the grammar just did not reach
   there.

**Recommendation:** merge after the dashboard entry, with M3, M2 and I1's five one-word edits folded
into the same PR. File I2, I3 and I4 as backlog rows — each is a design question, not a defect, and
per this repo's convention filing is the user's step.
