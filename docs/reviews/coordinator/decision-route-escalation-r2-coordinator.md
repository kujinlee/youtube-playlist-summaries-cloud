# Round 2, coordinator — `decision-route-escalation`

```yaml
round: 2
fixes_nontrivial: true
subject: decision-route-escalation
halves:
  codex: ran
  claude: "GAP: rounds 2+ ALTERNATE by docs/plugins.md — a concurrent pair never reviews the FIXES, and the fixes are the subject of this round. The Claude half is OWED and is r3's dispatch, not a skip."
findings:
  - {id: YH1, severity: High, aim: deliverable, fix_induced: true, component: corpus-cannot-run, disposition: filed}
  - {id: YH2, severity: High, aim: deliverable, fix_induced: true, component: starvation-ratchet, disposition: filed}
  - {id: YM3, severity: Medium, aim: deliverable, fix_induced: true, component: starvation-ratchet, disposition: filed}
  - {id: YM4, severity: Medium, aim: deliverable, fix_induced: true, component: log-schema, disposition: filed}
  - {id: YM5, severity: Medium, aim: instrument, fix_induced: true, component: coverage, disposition: fixed}
  - {id: YM6, severity: Medium, aim: instrument, fix_induced: true, component: coverage, disposition: filed}
  - {id: YL7, severity: Low, aim: deliverable, fix_induced: true, component: log-schema, disposition: filed}
  - {id: YL8, severity: Low, aim: instrument, fix_induced: true, component: coverage, disposition: filed}
```

**Codex half only, by the alternation rule.** Verdict: **NOT CONVERGED** — 2 High, 4 Medium, 2 Low.

## ⛔ YM5 is fixed first because it refutes a claim I made about my own measurements

The manifest entry *"rows are grouped by SUBJECT only"* declared `unit_key partitions on
(subject, unit)…` as an expectation, and the mutation changes `group_by_unit`, not `unit_key` — so
that label never reddens and `check-plan-code`'s contract (**every** `expect` entry must equal
**exactly one** red case) refuses the entry.

⭐ **My probe accepted it because the probe was weaker than the harness on BOTH axes:** `any()`
where the contract is `all()`, and SUBSTRING containment where the contract is EQUALITY on the case
name. So the "34/34, 0 survivors" I reported was **33/34**. The harness's own comment records that
substring matching once "certified an untouched guard because a sibling case went red" — I rebuilt
that defect inside the apparatus doing the measuring. Corrected labels were DERIVED by running the
mutation and reading the red case names. Re-verified under the real contract: **34/34 and 19/19**.

## The rest are filed, not fixed, and the reason is the next section

| id | what | why filed |
|---|---|---|
| YH1 | `rglob` silently skips an unreadable subtree, so `_corpus_now` returns a partial measurement with **no `error` key** and `main()` prints `all triggers quiet` | the r1 fix keyed on `error`; this is a corpus failure that produces none |
| YH2 | `subjects_starved` still intersects **filenames**, so a round document MOVED since arming makes a historical subject look new | third iteration of this rule |
| YM3 | `tree_at` splits `git ls-tree` output on newlines; `core.quotePath` returns `\303\251` for `é`, so an unchanged subject is named | needs `-z`, unquoted |
| YM4 | `t4_no_improvement` takes `list(dict)[-5:]`, but a dict **update does not move a key to the end** — so "the last 5 subjects" is not what it computes | reproduced with a 9-row log |
| YM6 | replacing `tree_at`'s `sha` with `"HEAD"` leaves **113/113 green** — the positive test asserts only that the set is large | coverage gap in new code |
| YL7 | `derive_outcome` treats `scope_tally`'s **appearance counts** as round numbers, so a component in rounds 1 and 5 reads as "stopped" after round 4 | ⭐ the reviewer notes its lack of production wiring is *prudent*: wiring it as documented would overwrite an authored `continued` with a wrong `stopped` |
| YL8 | the recorded `IndexError` rejection reason is **obsolete** — the fold removed the indexed expression, and that mutation now dies with three named failures | a rejection note that outlived its subject |

## Why these are FILED rather than folded into r3

**Three of the eight (YH2, YM3, YM6) are in `starvation-ratchet`, and all three are caused by the
r1 fold's own fix.** That component has now produced findings in two consecutive rounds. ⚠ The
arming condition in `dev-process.md` is *two consecutive rounds whose findings came from the
previous round's fix, in one component* — and **r1's findings were not fix-induced** (nothing
preceded round 1), so the condition is **not yet met**: this is the FIRST fix-induced round, not the
second. The determination is recorded here so r3 can answer it from evidence rather than from recall.

## ⭐⭐ THE MECHANISM WAS CONSULTED AND IT CONTRADICTED ME. That is the entry worth keeping.

The paragraph that stood here argued: *`starvation-ratchet` has been through ACCRETE and REDESIGN,
the stream did not stop, so the next route is SPLIT — and three independent doors in one rule is the
evidence.* Then I ran the procedure instead of trusting that:

```
ROUND_OWED — r1 produced a Blocking
  rounds=2  tree_reviewed=False
  scope-rank: NO LEAD — 4 components tied at 2 appearance(s)
              tied: corpus-cannot-run, coverage, log-schema, starvation-ratchet
  thrashing_component: None
```

**It refuses to name `starvation-ratchet`, and it is right to.** With two rounds, every recurring
component has exactly two appearances; there is no lead to report. My argument was about
**CONSEQUENCE** — three doors in one rule — and the ranker measures **APPEARANCES**. Those are
different claims, and backlog #136 is precisely the row saying consequence is the axis this process
throws away at decision time: *"counts ran 19 → 14 → 2 → 4 while consequence ran …"*. So this is a
measured datum FOR #136, not a defect in the ranker.

⛔ **Therefore no route change is taken here.** `thrashing_component` is `None` — correctly, because
r1's findings were not fix-induced, so this is the FIRST fix-induced round and the arming condition
needs two consecutive. The SPLIT inclination is recorded as an inclination, unsupported by the
evidence the tool reads, and r3 — the owed Claude half — decides with a third round of data.

⚠ Had I not run it, I would have written a route change into this document and cited "three doors"
as though it were a count. The procedure's value here was entirely in declining to confirm me.
