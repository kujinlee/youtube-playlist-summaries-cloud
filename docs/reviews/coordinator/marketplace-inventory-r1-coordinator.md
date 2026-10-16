# marketplace-inventory — round 1 coordinator record

**Verdict: NOT CONVERGED.** Both halves ran. Round 2 is dispatched against the folded tree.

| | Blocking | High | Medium | Low | total |
|---|---|---|---|---|---|
| CODEX (`gpt-6.1-sol`) | 4 | 6 | 1 | 0 | 11 |
| CLAUDE | 3 | 6 | 6 | 2 | 17 |
| **distinct after de-duplication** | **4** | **6** | **6** | **2** | **18** |

- `docs/reviews/codex/marketplace-inventory-r1-codex.md` — 13,573 chars, `gate_ran: true`
- `docs/reviews/claude/marketplace-inventory-r1-claude.md` — 699 lines
- Subject: `marketplace-inventory` at `a3fbb197` (the spec, the walkthrough page, and the
  `anchors.md` / `features.md` / `backlog.md` / `dashboard-entries.md` edits).

⭐ **This was the spec's FIRST review.** It was built, committed and opened as PR #376 on 2026-10-15
with no round at all — found 2026-10-16 while serving the walkthrough page for the Phase 1 human
gate. The page was about to be walked through with four Blocking defects standing in the document
behind it, which is precisely what `document-approval-is-interactive`'s *run the review before the
page* clause exists to prevent.

---

## Both halves independently found the same four core defects

That is the signal worth recording. The halves were dispatched concurrently from one brief, with no
shared state, and converged on:

| Defect | CODEX | CLAUDE |
|---|---|---|
| Effort (1)'s scope omits `recall-llm.py`, the mechanism that ships | 1 (Blocking) | B1 (Blocking) |
| `CANNOT RUN` does not cover a set that resolves **successfully and incompletely** | 2 (Blocking) | B3 (Blocking) |
| The pass condition cannot establish C4, yet permits `SHIP` | 5 (Blocking) | B2 (Blocking) |
| `24 = 17 + 3 + 4` is unobtainable from §3's prose | 1 | M1 |
| D3 proves the route, not this artifact's installability | 10 | M5 |
| The recall headline merges two experiments | 9 | M2 |
| §6 must create the artifact §10 forbids | 7 | H2 |
| C2/C3 are not decidable by counting | 4 | H4 |

**What each half found alone** — the reason both are run:

- **CODEX only, and it is a Blocking:** the install experiment can **inherit the author's
  machine** and pass. Verified by importing `brief-compose.py` and calling its source lookup against
  a clean-home path. This is an *environment* attack; the Claude half attacked the *document*.
- **CLAUDE only, and it is the most useful finding in either half:** H1 refuted the spec's own
  headline (below). Also H5 (the coupling is mislocated), H6 (`346s` reinstated), L1/L2.

---

## Disposition, per distinct finding

`fix_induced` = introduced by an earlier fix in this branch. All are `false`: this is round 1.

| # | Sev | Component | Finding | Disposition | fix_induced |
|---|---|---|---|---|---|
| F1 | Blocking | spec §3 | effort (1) omits `scripts/recall-llm.py` (2,550 lines, **on `master`**) | **FIXED** — component table rewritten, counting rule added, branches de-counted | false |
| F2 | Blocking | spec §5, §7 | shipping set can resolve wrong, not CANNOT RUN; no deliverable produced the declaration | **FIXED** — §7 item 2 (declaration as data), symlink resolution, non-zero expected count, required mutation; §3 table now names the real path | false |
| F3 | Blocking | spec §6, §4 | pass condition satisfiable by a hollow page; falsifier keyed on "blocker" only | **FIXED (mechanical half)** — pass condition asserts content, falsifier covers degradation. ⛔ **The `SHIP`-without-C4 half is OPEN for the owner** (§4) | false |
| F4 | Blocking | spec §6 | experiment can inherit the author's `HOME`, server and explainer corpus | **FIXED** — fresh `HOME`, no inherited server/corpus, resource record | false |
| F5 | High | spec §3, §8; page | the headline "3×" is cross-corpus; the figure was correct when written | **FIXED** — same-set 1.81×, re-diagnosed as decay; §8 risk row replaced; page heading, prose and chart corrected | false |
| F6 | High | spec §6, §10 | §6 requires the marketplace repo §10 forbids | **FIXED** — "published" qualifier both sides | false |
| F7 | High | spec §4, §5, §7; `features.md`; page | "nine `scripts/check-*` references" false in form; 5 of 9 invisible to both detectors | **FIXED at all four sites** + detector 4 (bare names) | false |
| F8 | High | spec §4 | C2/C3 not decidable by counting; no-"unknown" rule manufactures rows for libraries | **FIXED** — role table (`entry-point`/`library`/`data`), scanned region stated | false |
| F9 | High | spec §4, §5 | "concentrated in one file" false; `explainer-delivery.md` carries 3 CWD-relative invocations; per-component vs per-unit unstated | **FIXED** — shipping set declared per publishable unit; claim corrected | false |
| F10 | High | page | `346s` produced by nothing, already filed by a prior review half | **FIXED** — `1,758s → 353s` with its bound (`ci.yml:664-668`) | false |
| F11 | Medium | spec §3 | `24 = 17 + 3 + 4` unobtainable | **FIXED** — counting rule + per-effort enumeration. ⚠ Total unchanged, **membership changed** | false |
| F12 | Medium | spec §3; page | recall figures wrong and merged | **FIXED** — 3/20 lexical; 20/20 brief vs 19/20 shipped prompt, stated separately; 5.0% bound | false |
| F13 | Medium | spec §3; page | "604 lines of skills" omits 630 lines of shared contracts | **FIXED** — 10,373 + 604 + 630 = 11,607 | false |
| F14 | Medium | spec §2 | D4's justification compares unlike units | **FIXED** — stated as an order-of-magnitude contrast, not a ratio | false |
| F15 | Medium | spec §2, §7, §9 | D3 proves the route, not installability | **FIXED** — §7 item 0 packaging spike; named in §9 as the assumption | false |
| F16 | Medium | page | "15 document guards" denominator exists nowhere | **FIXED** — claim removed from the page; guard results recorded here instead | false |
| F17 | Low | page | gate claims measured two commits behind the page | **FIXED** — state block re-stamped | false |
| F18 | Low | hook | `regen-features-page.sh` not executable, unlike its three siblings | **NOT FIXED — DEFERRED** (below) | false |

**17 of 18 fixed. One deferred, one half deliberately open.**

### F18 — deferred rather than fixed, with the reason

`chmod +x` on a hook is a one-character change and I did not make it, because this spec's own §7
states that PR 1 **fixes no coupling and repairs no component** — evaluation is kept independent of
repair, which is the decision (option A) the owner made to avoid manufacturing a false green. A hook
whose mode differs from its siblings is exactly the kind of thing the inventory should *record*, not
quietly repair while judging it. ⚠ **It is therefore a finding the inventory must carry**, and if the
inventory does not mention it, that is a defect in the inventory.

### F3 — the half that is the owner's, not mine

May a component be recorded `SHIP` on C1–C3 alone, with C4 untested? §6's bound gives efforts (1)
and (2) no install experiment, so under the original text their components could reach `SHIP` with no
C4 evidence while D1 sets a *"full support bar"*. Two coherent answers — require demonstrated C4 (so
efforts 1 and 2 cap at `NEEDS-WORK`), or introduce `SHIP (untested support)` and relax D1 explicitly.
**This changes what the milestone promises, not how it is reached**, so it is stated as an open
question in §4 and is not folded. Phase 1 is the human gate; this is the kind of thing it is for.

---

## ⭐ The transferable finding: a review refuted the document's own headline, and the refutation was worth more than the fix

The spec led with a ⛔ banner: *"the D2 index undercounts its own subject by roughly 3×"*, and the
page rendered it as its only chart — including an `aria-label` asserting *"about one third of the real
size"*.

It was a correct measurement over the wrong corpus:

| Comparison | Ratio |
|---|---|
| 3,599 vs 3,737 — same nine files, at the commit that wrote the figure (`100cf498`, 2026-09-07) | **accurate within 3.7%** |
| 3,599 vs 6,525 — same nine files, today | **1.81× low** |
| 3,599 vs 10,977 — as the spec stated it | 3.05×, **different sets** |

`portable-practices.md` *enumerates* its nine files; `gen-dashboard.py` and `gen-goals-page.py`
(**4,798 lines, 46% of the Python total**) are not among them.

⛔ **The diagnosis mattered more than the number.** The spec concluded the figure was *written from
recall* and wired that lesson into three places — §3's framing, §8's risk row, and §7's correction
item. But `portable-practices.md:17` says *"Enumerated in `docs/backlog.md` row 89, not recalled"*,
and row 89 contains the enumeration. **It was derived, dated and correct; its subject then grew
1.75×.** The real failure mode is *a dated count decaying*, which §3's own banner already handles —
so the risk row was mitigating a failure this case is not an instance of, and the planned correction
would have recorded the wrong reason.

⚠ **And the paragraph committed the exact defect it was written to shame.** It is left on the record
in §3 rather than quietly rewritten, because it is the best available evidence for why §5's
CANNOT-RUN rule needed the companion that F2 forced.

## ⭐ The second transferable finding: three failures in one branch all had the shape "a measurement that cannot come back wrong"

- **F2** — `CANNOT RUN` fires when a set *cannot be resolved*. A set that resolves **successfully and
  empty** scores clean. Reproduced against the spec's own stated paths: the entries under
  `.claude/skills/shared/` are git symlinks (mode `120000`) and `grep -r` does not follow a symlink
  met during a walk, so `grep -rl 'check-' .claude/skills/` → **0** against `.agents/skills/` → **6**.
  A known positive was confirmed first, so the zero is a real zero.
- **F3** — the pass condition asserted *mechanism* (a page is produced and served) and so could not
  fail on *content*. All nine ground-truth items can return nothing and the page still composes.
- **F4** — the experiment asserted a different working *directory*, which is not a different
  *environment*. `~/explainers/` is a symlink into this repository.

**In each case the check was real, ran, and could not report the failure that mattered.** That is the
same class as `a-test-that-cannot-fail` and `a-forced-choice-test-cannot-fail`, reached three
different ways in one 213-line document.

---

## What round 1 checked and could not fault

Recorded because it is how a thorough round is told from a shallow one.

- The **17** for effort (3) reproduces exactly: 4 skills + 3 shared contracts + 6 Python files + 4
  regen hooks.
- **10,373** across the six Python files reproduces exactly; **604** for the four skills and **630**
  for the three shared contracts both reproduce.
- D1/D2 and their "rules out" clauses survived both halves.
- §9b's existing self-disclosures (the invented "~13 components", the ambiguous "strongest
  candidate") are accurate.
- `.claude-plugin/marketplace.json` is present in all three installed marketplaces, so §2's
  definition of a marketplace holds on this machine.
- The walkthrough page's Ask channel works end-to-end: tray opens, Send posts, the question reaches
  the session with its section attribution.

## Method notes

- Round 1 ran **concurrently** (measured-safe per `review-method.md`); rounds 2+ alternate, because
  a concurrent pair never reviews the fixes.
- The Codex half was dispatched with `--timeout 2700`. It completed in well under that — a 213-line
  spec is far cheaper than a code review, and a fast completion was verified by reading the capture
  and the verdict file rather than trusting `rc=0`.
- Every figure written into the fold was re-derived by command in this session. Two the backlog's own
  prose supplied were **stale and not used**: it says `recall-llm.py` has 128 self-test cases and 53
  mutations; the file declares **201** (verified by running it: `201/201 passed`) and its manifest
  holds **96**.
- ⚠ `172–239s` was **not** written into the page, although a round-1 direction suggested it. Its
  provenance is another review document about a different commit, and copying it would repeat the
  defect F10 reports one level down. The page cites `ci.yml`'s own `1,758s → 353s` with its stated
  bound instead.

## Guard results

Recorded here rather than asserted on the page, where a guard result decays in minutes. Run against
the folded tree at the commit this document lands in; the command list is derived from `ci.yml`'s
`python3 scripts/check-*` steps, not from memory.

See the dashboard entry for the measured result.
