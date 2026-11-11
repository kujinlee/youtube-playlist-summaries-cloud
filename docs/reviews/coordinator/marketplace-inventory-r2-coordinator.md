# marketplace-inventory — round 2 coordinator record

**Verdict: NOT CONVERGED.** Codex half ran against `b748812e`/`8a19f4ce`. Round 3 (Claude half)
dispatched against the r2 fold — **alternating, not concurrent**, per `review-method.md`: a
concurrent pair never reviews the fixes.

| | Blocking | High | Medium | Low | total |
|---|---|---|---|---|---|
| CODEX (`gpt-6.1-sol`) | 1 | 7 | 1 | 1 | 10 |

`docs/reviews/codex/marketplace-inventory-r2-codex.md` — 13,955 chars, 167 lines, `gate_ran: true`.

---

## ⚠ THE THRASHING WATCH IS NOW ARMED AT ONE OF TWO

`dev-process.md`'s architecture-review trigger is **two consecutive rounds whose findings came from
the previous round's own fix, in one component.** Round 2's own attribution, which the brief
required it to supply:

| Attribution | Findings | Count |
|---|---|---|
| **INTRODUCED BY ROUND 1'S FIX** | 1 (Blocking), 2, 3, 9 | **4** |
| introduced by round 1's review RECORD | 10 | 1 |
| PARTLY introduced by the fix | 6 | 1 |
| PRESENT BEFORE; fix incomplete or absent | 4, 5, 7, 8 | 4 |

⛔ **Round 2 is the FIRST of the two. If round 3 again carries findings caused by round 2's fix in
the same component, the architecture review fires** — and the answer to *thrashing or prose floor?*
must be written in round 3's document with per-finding evidence, not decided by a count.

⚠ **Stated against myself: four fix-induced findings out of ten is not a good ratio.** The specific
mechanism, visible in finding 1, is that **I folded the spec thoroughly and the page partially** —
so the fix created a *contradiction between two artifacts* that neither artifact contained before.

---

## Disposition, per finding

| # | Sev | Attribution | Finding | Disposition |
|---|---|---|---|---|
| 1 | **Blocking** | **fix-induced** | the gate page still presented rules the folded spec rejects — `countable`, "invokes `scripts/check-*`", "any blocker" — and mentioned **none** of the new machinery | **FIXED** — page contract rebuilt from the folded spec, not patched. Verified by execution: 0 `countable` pills, claim gone, 9 new elements render |
| 2 | High | **fix-induced** | "non-empty" accepts a page of wrong facts and refuses legitimately empty results | **FIXED** — seeded repository with known facts; *correctly empty* distinguished from *missing capability* |
| 3 | High | **fix-induced** | inheritance had no aggregation, coverage or provenance rule | **FIXED** — mixed inherits the FAILURE; orphan is `none`; cycles resolved at the boundary; dual role permitted; an `inherited` grade must name the exercising scenario |
| 4 | High | present before | the companion accepts the right number of **wrong** files | **FIXED** — identity comparison member-for-member; declaration derived independently; three mutations (empty, substituted, omitted-with-matching-count) |
| 5 | High | present before (+ new terminology conflict) | "component" meant two things; generators omitted while their hooks are components | **FIXED** — evaluation component vs installable package separated; every artifact maps to one or to a written exclusion; **24 is now a lower bound, not a derived total** |
| 6 | High | partly fix-induced | mentions confused with dependencies; runtime prerequisites uncovered | **FIXED** — mention candidates reported separately; **detector 6** for imports/executables/config; fixtures exempted by behaviour, not location |
| 7 | High | present before | fresh `HOME` is not isolation; the resource record had no mechanism | **FIXED** — declared baseline (PATH, interpreter, packages, git config, network); named capture mechanism that **states what it cannot see** |
| 8 | High | present before | a successful invocation cannot establish C4 | **FIXED** — one useful operation through installed paths, one recovery scenario, an entry-point coverage matrix bounding conclusions |
| 9 | Medium | **fix-induced** | round 1 dated the figure's origin wrongly | **FIXED** — three-stage history (below) |
| 10 | Low | fix-induced (review record) | F18 named a file that is executable | **CORRECTED, finding STANDS** — see below |

**10 of 10 addressed.** One correction is to round 1's own record rather than to the spec.

### Finding 10 — round 2 was right about the file and wrong about the claim

Round 1's Claude half filed F18 as *"`regen-features-page.sh` is not executable, unlike its three
siblings"*. Round 2 checked that file at three commits, found mode `100755` at all of them, and
directed that the finding be **withdrawn**.

⛔ **Verified independently, and BOTH halves are partly wrong:**

```
100755  regen-backlog-page.sh
100644  regen-dashboard.sh      <-- the odd one out
100755  regen-features-page.sh
100755  regen-goals-page.sh
```

**The finding stands; only its subject was wrong.** `regen-dashboard.sh` is mode `100644`.

⭐ **And the way round 2 got there is itself the defect this repository names most often.** It
verified **the file the finding named** instead of **the claim the finding made** — *one of the four
differs from its siblings*. A reviewer refuting a reviewer committed *measure the population the
code actually sees*. Had the direction been followed, a true finding would have been withdrawn on
correct evidence about the wrong subject.

⚠ It remains **DEFERRED**, unchanged: §7 repairs nothing by design, so this is a finding the
inventory must carry, now with the right filename.

---

## ⭐ The transferable finding: a republished number loses the fact that it is inherited

Round 1 corrected the spec's headline ratio and **got the history wrong in the correction**. Round 2
re-derived it:

| Stage | Commit | The same nine files | Verdict |
|---|---|---|---|
| originally measured | `cacbac17`, 2026-09-03 | **3,599** | **exactly right** |
| republished into the index | `100cf498`, 2026-09-07 | 3,737 | already **3.7% stale** |
| today | `HEAD` | **6,525** | **1.81x** low |

Verified here by summing the nine enumerated files at `cacbac17` with `git show`: **3,599 exactly.**

⛔ **So there are two failure modes, and the second is new.** The count decayed (1.75x growth). It
also **arrived in `portable-practices.md` already stale**, because it was copied from an earlier
measurement into a fresh-looking declaration without being re-measured. ⭐ **A republished figure
inherits staleness AND loses the fact that it is inherited** — the new document reads as a new
measurement. The rule that follows is sharper than *date your counts*: **a count copied from
elsewhere must carry the commit it was measured at, not the commit it was written into.**

⚠ This is the third successive correction to the same paragraph (original → r1 → r2). On a paragraph
*about* number provenance. The paragraph is kept on the record at each stage rather than rewritten,
because the sequence is the evidence.

## ⭐ A release criterion neither review had evaluated

Round 2's NOT VERIFIED section names it: **whether the memory corpus can be redistributed at all** —
private content, credentials, redistribution rights. Round 2 is explicit that this is *"an
unexamined release criterion, not a claim that sensitive material is present"*. **Neither half had
looked.** It is now recorded on the page and belongs in the inventory's criteria; effort (1) ships a
corpus of 157 files authored as private working notes, so this is not hypothetical.

---

## What round 2 checked and could not fault

- **10,373 + 604 + 630 = 11,607** reproduces over the explicitly named files.
- The **symlink failure reproduces**: `.agents/skills/` → 6 files, `.claude/skills/` walk → 0, with
  the known positive confirmed first.
- The named recall scripts and hook are **landed on `master`**; line counts reproduce; the manifest
  holds **96** entries by `len(json.loads(...))`.
- The page **correctly bounds** `1,758s → 353s` as one shard on one machine, against `ci.yml`.
- The evidence-grade proposal **was** clearly marked as a recommendation, not as a decision.
- The local-versus-published marketplace distinction **resolves** r1's artifact contradiction.

## NOT VERIFIED by round 2, in its own words

- No scanner, spike or isolated experiment exists; the counterexamples test the **written contract**.
- Historical timing and recall results were checked against repository records, **not rerun**.
- **No live browser or Ask-channel test** was performed. ⚠ The coordinator did perform one: the page
  was executed after every recomposition, and both reader questions round-tripped.

## Method notes

- `--timeout 2700`; completed well inside it. Success confirmed by reading the capture and
  `gate_ran: true`, never by `rc=0`.
- Round 2's attribution requirement (*was this introduced by round 1's fix?*) was added to the brief
  deliberately, because **nothing else can supply that distinction** and it is the input the
  thrashing trigger needs. It worked: the attribution is per finding and specific.
- The owner answered the round-1 open question while round 2 was in flight. It is now **D5** in §4b,
  a decision of record, and the page presents it as settled rather than recommended.
