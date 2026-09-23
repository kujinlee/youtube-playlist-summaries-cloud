# Review Method

How adversarial review is run here, and the classification passes that go between rounds.

**Read this when a review round is about to start**, not at session start — that is why it is not in
`docs/dev-process.md`. The spine says *when* a review gate applies; this says *how* to run one.

> **Why it is a separate file (2026-08-08).** These sections grew to ~190 lines — a third of the
> process document — almost entirely in the two days after round 6. Every addition was justified by a
> measured defect, and the aggregate was unreadable, which is the *"individually thoughtful, fail as
> a set"* verdict these very reviews keep producing, applied to their own documentation.

---

## 0. The decision procedure — read this, do not recall it

**Measured 2026-09-14 (PR #302): a contained single-file change ran FOUR rounds; two were owed.**
Every rule below already existed, spread across five sections of this file and two others, and was
recalled instead of read. ⛔ **Consulting this card is the step. If you are about to decide from
memory, that is the defect.** `scripts/check-review-decision.py` answers Q1, Q4 and Q5 from the
recorded evidence — run it rather than reasoning.

### Q1 · Full loop, or one round?

Keyed on the **changed path set**, not on judgement.

| The diff touches | Answer |
|---|---|
| anything that is **not prose** — code, config, tests, tooling, CI, and the executable gates that live under `docs/` | **full loop** |
| prose only | **ONE round** |

`scripts/check-review-decision.py` answers this by delegating to
`check-review-recorded.is_prose()` — the classifier hardened over four rounds of PR #299,
which already knows that *"a gate script does not stop being code by living in a
documentation directory"*. **It owns no path list of its own**, because three successive
hand-kept lists each scored something dangerous as one-round: a money route, a paid-attempt
guard, and an executable schema gate.

⚠ **This is NARROWER than `:415`'s *"single-file logic, config, thin wrappers"*, and the
narrowing is deliberate.** `tests/`, `.claude/` and `.agents/` were one-round and are now
full loop.

✅ **DECIDED 2026-09-15 by the user, after it was surfaced as an open policy question:
they stay full-loop.** The reasoning is recorded so the next person does not re-litigate
it: `.claude/hooks/` holds the gate hooks, so a change there can switch a guard off, and
deleting the test that proves a spend guard fires is a real loss of protection. Against a
standing tax on ordinary test edits, the asymmetry decides it — **a wrong `full-loop` costs
one review round; a wrong `one-round` merges unreviewed risky code.** The same asymmetry
settled three earlier findings on the branch that built this.

### Q2 · Round 1 — both halves at once

1. Dispatch **both halves concurrently**; isolation per the measured table at `:277`.
2. ⛔ **Neither half is committed until both finish** (`:349`) — a committed first half leaks
   its grade to the second through `git log` and the diff.
3. Codex's final message **is** its review; it writes no file. File each half under
   `docs/reviews/<writer>/`.
4. A half that cannot run is recorded `REVIEW GAP: <half>` **with its reason**, never omitted.
5. ⛔ **EVERY FINDING NAMES A SAMPLE, NOT A SCOPE — say what you did about that.** A finding's
   boundary is the evidence the reviewer happened to have, never the extent of the defect. **Each
   finding must state whether siblings were searched for, HOW, and what turned up** — "grepped the
   other `text/html` producers in this file: one more, same defect" or "no sibling: this is the only
   call site". *Not searched* is an acceptable answer; **silence is not**, because it is
   indistinguishable from *searched and found nothing*.

   ⭐ **MEASURED, which is why this is a numbered step and not advice.** Six real misses across
   three branches were replayed on their own pre-fix trees. All six were eventually caught **by a
   reviewer, never by the author** — and three of the six had a bounded, zero-noise query that
   would have named the sibling at the moment of the fix. `scripts/peer-sites.py --diff <ref>`
   answers those three mechanically; **the other three lived in the clauses of an English sentence
   and in the levels of an encoding**, where no script reaches and a reader does. That split is the
   reason both this step and that script exist, and neither replaces the other.

   ⛔ **AND THE SCRIPT ANSWERS THEM ON A NARROWER SET THAN THAT SENTENCE IMPLIES — r1 High/Medium,
   measured by replaying it over 200 master commits, so ASK THE THREE QUESTIONS YOURSELF EVEN WHEN
   IT IS SILENT.** It reads **python only**, three shapes only, and **only where your edit lands on
   a member's HEAD line** — an edit inside an arm's *body* is invisible, which was **79 of the 84**
   partially-touched containers in the replay. It is also not a zero-noise oracle: one idiom
   (`if ok: … else: print("[FAIL]")`) accounted for 4 of its 12 `branches` reports. **A green run is
   not an answer to this step**; it is one cheap input to it. The script's own docstring carries the
   full bound list.

   ⚠ The three questions worth asking in order, because each found a real miss: another **LEVEL**
   (an encoding, a nesting, an indirection)? another **SITE** doing the same job? another **COPY**
   of the same sentence?

### Q3 · Disposition — decided here, not by asking

⟳ **Replaces the instruction at `:404` to present every Medium to the user** (user decision,
2026-09-14). That line was the mandated interruption.

| Finding | Do |
|---|---|
| **Blocking / High** | **FIX** |
| **Medium / Low**, inside the delta, fix touches only files already in the diff and adds no mechanism | **FIX** |
| **Medium / Low** needing a new mechanism, script, schema, or a policy call | **FILE** |

Record the disposition **and its reason, per finding**, in the round document; the human overturns
it afterwards. ⚠ A reviewer's *proposed* fix is unverified code — see `:352`.

### Q4 · Is another round owed? — TWO questions, and they are not the same one

**(a) Convergence — has discovery dried up?**

| Observation | Answer |
|---|---|
| a **Blocking or High** | **CONTINUE** |
| a finding **in the deliverable** | **CONTINUE** |
| non-trivial fixes — recorded as `fixes_nontrivial: true` in the round header, so the tool enforces it rather than the reader remembering it | **CONTINUE** |
| **two consecutive rounds** with neither, every finding aimed at the **instrument** | **STOP** |

⭐ **Judge by AIM, not severity** — `:238` says a clean severity column describes the reviewers,
not the design. On PR #302 severity read "converged" from round 1 and was useless; aim separated the
rounds cleanly. Inverted, it is why PR #299 was right to run seventeen.

**(b) Tree identity — has a round seen the code that MERGES?** A different question. Cheapest first:

1. land the editorial fixes **ahead of** the final round (`:372`);
2. keep the last fixes uncommitted so the reviewer sees what ships — `:358` calls this the
   documented way;
3. declare `NO-REVIEW: <reason>` in the PR body;
4. run another round — **last**.

> ⛔ **Never spend a round on (b) before offering 1–3 to the human.** That is exactly what PR #302
> cost, twice.

### Q5 · Thrashing → architecture review

Per finding, answer **in the round document**: *did the previous round's fix cause this?*

| Shape | Then |
|---|---|
| fix-induced findings, two rounds running, one component | **ARCHITECTURE REVIEW** |
| *"the rule doesn't say what happens in case X"* | **FIX** + an exhaustiveness pass |
| findings drifting to *under-specified* while the artifact improves | **STOP REVIEWING — go build** |

Apply the single test at `:173`, never the symptom list; using the list as a checklist produced a
measured false escalation on 2026-08-14. Reaching four rounds **obliges asking**, and does not fire.

### Q6 · Record the call

Write the reason and the per-finding evidence into the round document (`:458`), and carry the
header defined in [`docs/round-header-template.md`](round-header-template.md) so
the counters Q4 and Q5 need are derived rather than remembered (`:391`).

---

## Two rules for PREMISES, not findings (added 2026-08-08)

Both were bought with a full review round. The existing discipline — *a finding you MEASURED beats
one you reasoned about* — was applied to findings and never to the premises a design rests on.

**1. Quote the code you rely on; do not characterise it.**
A design decision that depends on how existing code behaves must paste the relevant lines, with a
`file:line`. Measured cost of not doing it: a spec comment asserted *"worker_id is stable config"*,
`worker/main.ts:69` says
`` `${os.hostname()}-${process.pid}-${randomUUID().slice(0, 8)}` ``, and an entire ownership
mechanism was built on the false half. Quoting forces a read; characterising lets you write from
memory. Where a premise genuinely cannot be verified, label it **unverified** in the same sentence —
what must never happen is a premise sitting in a table beside measured facts in the same voice.

**2. Ask "what caller reaches this state?" of every measured defect.**
A rolled-back probe can construct any state you can type, including states no caller can reach.
Round 8 measured a doubly-lost worker being refused and graded it Blocking; two rounds then designed
against it; round 10 established the state cannot occur. *"Is this refused?"* and *"can a caller BE
here?"* are different questions, and only the second decides whether a fix is needed.

> A defect with no reachable caller is a fact about the schema's expressiveness, not about the
> system. It may still be worth a guard — but it is not worth a mechanism.

## The stop condition: when to stop fixing and start redesigning (added 2026-08-09)

Adversarial review answers *"is this correct?"* — a **local** question, and a local question can
always be answered *yes* by patching. So a wrong shape never fails a round; it emits a stream of
defects that get fixed, and **each fix makes the gates greener**. The process does not merely
tolerate patching a bad design — it rewards it.

> **If a component produces findings caused by the PREVIOUS round's fixes in two consecutive rounds,
> it escalates from FIX to REDESIGN, and the next round is a design review — not another defect hunt.**

**Two, not three.** The stable-blob-addressing reservation hit it at round 9 and ran to round 12
anyway; two would have cost four rounds instead of six.

### ⚠ It is a HEURISTIC, not a fact — and it has one known false positive (added 2026-08-14)

The counter detects *"fixes generating the next round's defects"*, which is a **proxy** for *"the shape
is wrong."* Proxies misfire, and this one misfires in a specific, recognisable way. Say so, because a
rule believed to be a fact gets either obeyed mechanically or quietly ignored, and both are worse than
being argued with.

**Ask what KIND of finding the fixes generated.**

| The fixes keep producing | Meaning | Action |
|---|---|---|
| **Mechanism** defects — the rule cannot be satisfied, the credential is stale, two requirements contradict | the shape is wrong | **REDESIGN.** This is what the rule is for |
| **Branch-coverage** defects — *"the rule doesn't say what happens in case X"*, where X is a branch of code the rule GOVERNS but does not OWN | the shape is fine and under-specified | **FIX**, plus an exhaustiveness pass |

**⚠ THE SYMPTOM LIST IS A PROMPT, NOT THE TEST. There is one test, and it is this:**

> ### Can a redesign remove it?

If a different shape would dissolve the finding, it is a mechanism defect and the redesign is owed. If
the same finding would survive every reasonable reshaping — because it lives in code the design merely
*governs*, or because it is a sentence that outlived the decision it described — it is not.

**Measured 2026-08-14, round 13, and this is why the sentence above exists.** Applying the symptom list
as a checklist produced a **false REDESIGN** in one reviewer and a true one in the other, on the same
document:

| Finding | Symptom matched | Redesign removes it? | Actually |
|---|---|---|---|
| `promoteIfAbsent` typed `Promise<void>` while two other lines still demand it *return* `'already-exists'` | *"two requirements contradict"* ✓ | **No** — it is one stale signature reference; the fix is six words | editorial |
| `sourceMd` required as an ownership credential, but `reconcileCloudBase` byte-copies the envelope and never rewrites it, so it is **stale by construction** on the cloud path | *"a credential is stale"* ✓ | **Yes** — a different credential (`sourceMdHash`, or an invariant enforced at `remap`) dissolves it entirely | **mechanism** |

Both matched a listed symptom. Only the second is a mechanism defect. **Quote the test, not the list.**

**A third outcome the two-way split does not cover: STALE CROSS-REFERENCE.** *"A decision changed and
some sentences still state the old one."* Round 13 produced four. It is neither mechanism nor
branch-coverage, and its remedy is neither a redesign nor an exhaustiveness pass — it is:

> **When a decision is reversed, grep for every place that stated the old one.** A rewritten section
> does not rewrite its own cross-references.

**The branch-coverage case, for completeness.** If the branches live in code the design merely governs
— `decideCompanion` already has two `ship` branches, `SupabaseBlobStore.promote` already has three
success paths — then no redesign can delete them. It can only fail to mention them, which is the defect
you already have. Redesigning is then pure cost.

**Measured 2026-08-14, backlog #36 §3.6.** The counter reached 2 across rounds 11 and 12. Every one of
the five findings was branch-coverage; the mechanism (R1–R4) was attacked head-on in round 12 —
no-clobber measured true on both backends, the alias relation re-derived, `promote`'s caller set and
the `resolve.ts` hard-return confirmed — and held. The round-10 design review that *did* earn its keep
found a **mechanism** defect: a credential that was stale by construction.

**Overriding is allowed. Overriding silently is not.** Record the override in the artifact, with a
condition that would prove it wrong — e.g. *"fires to REDESIGN if the next round produces a fix-induced
finding in this component that is a mechanism defect rather than a branch-coverage gap."* An override
with no falsifier is the round-8 failure wearing a better argument.

**And treat the recurring branch-coverage shape as its own finding.** It has one remedy, and it is not
a design review: **for every rule, enumerate the branches of the function it governs and state the rule
per branch.** This subsystem has already learned the same lesson one level up — §3.6 was rewritten
against two *patterns* instead of N writers because the writer count had been wrong seven times. The
discipline was never applied to the branches inside each pattern.

**The evidence was already being collected and no rule acted on it.** The standing shape list tracks
*"a fix that moved or reintroduced a defect"* — counted to nine, then ten, then eleven across rounds
8–12, carried forward as **trivia in a prompt** because nothing said what to do when the number went
up. The fix is not a new measurement. It is permission for the existing one to conclude something.

**What a design review asks instead:**

1. **What already serves this concern?** — answered with a `file:line`, not a characterisation. The
   reservation's 2800-line spec never mentions `jobs` once, which already had exclusivity,
   idempotency, leases and a durable money guard.
2. **Which coordination pattern is this?** — append-only-plus-merge, mutual exclusion, or idempotency
   key. A design holding two of them cannot be repaired locally: that fence had to be PERMISSIVE so a
   reclaimed writer could still record paid work and STRICT so a stranger could not complete a
   generation. Five successive credentials failed on that contradiction.
3. **Who are the writers, and what identity does each carry?** — if two writer classes cannot present
   the same credential, it is a broker or merge problem and a lock will never converge on it. One
   four-minute read (`sync-run.ts:380-394` — sync *replicates*, it does not produce) would have ended
   the credential search on day one.

**Convergence is not enough on its own.** *"No new Blocking or High"* is a statement about the
REVIEWERS, not the design. A locally-repairable design passes it forever.
## Premise tags, and the asymmetry they exist to fix (added 2026-08-08)

**The diagnosis, which is sharper than "my instruments only look at the schema":** the validation
stack was **asymmetric**. Heavy automated verification on the TARGET layer (122 assertions, 57
mutations, guard coverage) and *nothing at all* on the ASSUMPTIONS layer — the external runtime code
the design rests on. That asymmetry manufactures false confidence: a green 57/57 feels like maximum
rigour while the whole premise sits in one unread line of another file.

So every foundational statement in a spec, review brief or ADR carries a tag:

| Tag | Means |
|---|---|
| `[VERIFIED: path/to/file:line]` | read from the CURRENT head, this round |
| `[ASSUMPTION]` | believed, not read this round |

**A safety fence, credential, or invariant may not be designed on an `[ASSUMPTION]`.** Upgrade it to
`[VERIFIED]` first, or design for both branches. A tag that was `[VERIFIED]` three rounds ago is an
`[ASSUMPTION]` today — the point is not that someone once checked, it is that someone checked *this*
round.

**And when a fence depends on caller behaviour, write a CONTRACT TEST at the runtime boundary.**
Prose in a design doc is a rule that depends on remembering, which is the failure mode this whole
document exists to remove. See `tests/lib/blob-addressing-caller-contract.test.ts`: it asserts the
properties `…-stable-blob-addressing-design.md` §12b relies on, lives in the CI-covered suite, and is
itself mutation-checked so it cannot pass vacuously. A future refactor that adds auto-reconnect or
job resumption then fails *there*, instead of silently invalidating a schema nobody thought to
re-read.

## Running agents concurrently — classify the OPERATION, not the agent (added 2026-09-09)

> ### ⛔ SPAWNING A SUBAGENT IS THE DEFAULT. The table below is the ONLY restriction (2026-09-20).
>
> **Measured cost of assuming otherwise:** a session ran under an instruction not to spawn subagents
> unless asked, and PR #325 shipped after **SIX review rounds with only the Codex half** — every
> "claude half" document on that branch is a coordinator self-review, which by construction cannot
> find what the author did not think to look for. `docs/plugins.md` records what a skipped half once
> cost: a Codex-only round cleared a money guard the Claude half caught in one pass.
>
> ⚠ **The gap was one question wide and was never asked.** It was recorded as a `REVIEW GAP:` in all
> six round documents and a ❌ row in every status table — six mentions, zero escalations. *An
> escalation has no closer: only a REPLY closes it.* A reviewer that CANNOT run is a **decision**
> (`docs/plugins.md`), so it belongs in a selection card on round one, not a caveat on round six.
>
> **Reliability is not a reason to decline.** A fork can review the wrong subject or never report —
> both measured here. Those argue for *"agent output is a LEAD, not a finding — verify every
> load-bearing claim by hand"*, which this repo already requires. The asymmetry decides it: a fork
> that fails costs a RETRY; not spawning costs the entire second reviewer, permanently.

**Read this before dispatching two halves at once.** Backlog #67; the goal in the user's words:
*"find a safe method to run multiple agents concurrently, and when no safe method exists, then they
must be serialised for the dangerous operation. This is balancing of speed and safety."*

**Serialising whole agents is the expensive answer and buys safety this project does not need.**
Only a few operations are dangerous. Serialise those; run the rest in parallel without ceremony.

### ✅ Safe to run concurrently — MEASURED, never inferred

| Operation | Why it is safe | Evidence |
|---|---|---|
| **Both review halves at once** (a Codex half and a Claude half) | they read files and each writes only its own review path | 2026-09-09: three overlapping processes produced **byte-identical red-set data for all 23 manifest entries**. Independent runs agreeing is the strongest available evidence of non-interference |
| **`check-plan-code.py --mutate .`** | `stage_tree()` copies into a fresh `TemporaryDirectory`; `child_env` redirects `$HOME` into it, so two runs share no mutable state | 2026-09-09: two full runs launched together, both `rc=0`, verdict lines byte-identical |

**The safe method already exists and is already implemented** — per-run temp tree plus a `$HOME`
redirect. Anything adopting that shape can join this table; anything that cannot, does not.

⚠ **Both rows were settled by RUNNING them, and that is the rule, not the ceremony.** This section
exists because a concurrency *inference* was wrong **twice** — a **Blocking** finding was filed
against what turned out to be contamination (23/63, then 63/63 alone; the prior instance 23/44 vs
44/44). **The near-identical ratio is the tell.** `--mutate .` "should obviously be safe by the same
argument as the reviewers" was not accepted either; it was launched twice and observed.

### ⛔ Must be serialised — each measured, and **none mechanically enforced**

| # | Operation | Why a clone or a temp dir does NOT save you |
|---|---|---|
| 1 | Anything touching local Postgres **roles** | roles are **cluster-wide**. `grant service_role to anon` rewrites `pg_auth_members` and changes `has_table_privilege('anon', …)` in *every* clone at once. A role-scoped mutation must create and drop its **own** role, never grant an existing one |
| 2 | **`git` in the main working tree** | a subagent's `stash` / `checkout` / `add` can take the coordinator's uncommitted work into a stash nobody knows exists. Measured: a `/brief` agent ran `git stash` / `git stash pop` mid-edit and completed cleanly **by luck** |
| 3 | **Writes to the TOP LEVEL of `docs/reviews/` while a Codex run is in flight** | the wrapper snapshots that directory **non-recursively**, and its failure-path `quarantine()` **moved a concurrently-written half out of the repo**. Mitigated by convention only — file under `docs/reviews/<writer>/` — not by a mechanism (backlog #92) |

⛔ **"None is mechanically enforced" is the honest state, not an omission.** Three named hazards,
three conventions. Do not read the table as protection.

### What the dispatcher does

- **Commit before spawning.** Hazard 2 has no mechanism; a clean tree is the only protection.
- **Put the constraint in the BRIEF, not only in the harness.** A reviewer told to *"verify by
  execution"* will reach for the shared harness — so the brief must name what it may touch: scratch
  dirs and throwaway repos only, no schema gates, no local Postgres, never `git` in the main tree.

⚠ **`pg_try_advisory_lock` was considered and REJECTED by the user**, and stays rejected: a
writer-only lock does not protect readers, and extending it to readers would block `--prod` and
`--database <scratch>` reads that cannot be corrupted — restriction bought with no safety.

---

## Round topology — concurrent r1, alternating r2+ (added 2026-09-13)

**A different question from the section above.** That table asks whether two agents can run at once
without *interfering*; this one asks whether the code that merges was ever *looked at*. Both halves
concurrently is still safe. It is also, on its own, not enough.

### What was measured, and what it refutes

The premise "two reviewers on one diff is duplicated effort" was tested over three rounds on two
consecutive branches (backlog #296, #297):

| round | first half | second half | overlapping findings |
|---|---|---|---|
| #296 r1 | Codex: 0 Blocking/High/Medium, 1 Low | Claude: 1 Medium, 3 Low | **0** |
| #296 r2 | Claude: converged, 2 Low | Codex: no findings | 0 |
| #297 r1 | Claude: 2 Blocking, 1 High, 5 Medium, 4 Low | Codex: 1 High, 1 Medium, 1 Low | 0 |

**Zero duplicate findings.** The halves do different work: Codex *executes* (rebuilt the database,
ran 15/15 gates, re-derived every number); the Claude half *designs experiments* (neutered
`unexpected()` to expose four false greens). So the effort is not duplicated and neither half is the
saving. **What IS duplicated is environment construction** — each reviewer built its own container
and ran the same suite. Dedupe that, not the reading.

**The real argument for alternating is elsewhere: both defects that survived furthest were
introduced by a FIX.** #296's repair shipped a comment claiming more reach than its one writer and
one reader delivered. #297's new guard — written to close a review finding — had a population that
missed two of the fifteen gates. A concurrent pair reviewing one frozen tree cannot find either:
nobody is looking at the repair.

### The protocol

1. **Round 1 concurrently**, isolated per the table above.
2. **Hold both halves UNCOMMITTED until both finish.** Measured on #296 r2: the Claude half
   disclosed it could not avoid learning Codex's grade, because r1 was already committed on the
   branch under review — `git log` and the diff both carried it. This is the whole fix for leakage.
3. Fix. **Treat a reviewer's proposed fix as unverified code**: twice in one session a proposed fix
   was weaker than the finding it closed (a cleanup block running after the bound it protects; an
   exit-status check where `drop … if exists <wrong-name>` succeeds). Findings arrive measured; the
   sentence after *"Fix."* never does.
4. **Rounds 2+ alternate**, scoped to the delta, sent to the half that did NOT author the fix.
   Match the reviewer to the risk: reproduction and execution → Codex; experiment design → Claude.
5. **Stop when a round has seen the tree that will merge** and no code change follows it. Holding
   the last round's fixes uncommitted so the reviewer sees the final state satisfies this and is the
   documented way to do it.

Step 5 is the only step with a machine behind it: `scripts/check-review-recorded.py` reads what each
Codex run records at dispatch — the commit, and the **git tree entry** of every file handed over
uncommitted — and refuses a branch where guarded code was committed after **every** round. Its own
two review rounds are why it compares entries and not something weaker: r1 reproduced "review `x`
dirty, then edit `x` again and commit", which a path match certifies; r2 then reproduced the same
class one layer in, a **mode-only** change that a content match certifies. No usable round is
**CANNOT RUN**, cleared by a `REVIEW GAP:` naming **codex** — the half that leaves the testimony,
since a gap about the other half explains a different absence. Steps 1–4 are convention. Do not
read them as protection.

⚠ **Batch the editorial fixes BEFORE the last round.** The rule is deliberately strict: any change
to guarded code after the final round makes that round stale, and a docstring lives in guarded code.
Measured while building it — a converged round left one stale-prose Low, fixing it cost another
round, and that round found three more spellings of the same thing. There is no "docstring-only"
escape and there should not be: every loosening this rule survived (path, then content, then the
tree entry) was a loosening that certified unreviewed code. Fix the Lows, THEN run the round that
sees the final tree.

### ⚠ The observations that would RETIRE this section

A rule with no falsifier is a decision wearing a checkbox. Both of these are read at the architecture review, not
by a script — they need judgement about whether two findings are *the same finding*, which is
exactly what a script cannot do:

- **Retire alternating** if five consecutive rounds produce **no finding inside a fix delta**. Then
  it is buying nothing and costing wall clock; go back to concurrent-only.
- **Revisit the whole shape** if the two halves of one round report the **same finding twice in
  five rounds**. The independence premise has weakened, and concurrent-plus-dedup becomes cheaper.

The evidence for both is derivable, not remembered: `docs/reviews/verdicts/*.json` names every
Codex round and the commit it saw; the halves are in `docs/reviews/<writer>/`. Do not maintain a
hand-written tally of it — this project has measured what those do.

---

## Adversarial Review

Dispatch Codex (`codex:rescue`) with an explicit adversarial mandate at every phase.

### ⛔ A VERIFICATION agent must be told to REFUTE — the review halves already have a mandate; these do not

⟳ **This section's first draft claimed "nothing says how to prompt a Claude subagent". That was
FALSE and is withdrawn.** Measured: **33 documents** under `docs/reviews/` carry a reviewer line of
the form *"Claude (adversarial mandate)"*, and [`plugins.md`](plugins.md) specifies one explicitly
for the fallback path — *"a fresh subagent with full file access and an explicit adversarial
mandate"*. Claude review halves have been dispatched adversarially for months.

**The real gap is a different population.** The dual-review protocol covers the two REVIEW HALVES.
It says nothing about the agents dispatched to **map a subject or check a finding** — and those are
prompted with verbs like *"map the family"*, *"answer these questions"*, *"is this right?"*, which
are **confirming by construction**.

**So: when you dispatch an agent to CHECK A FINDING, instruct it to REFUTE the finding and to
default to *refuted* when uncertain.** A prompt that asks *"is this right?"* buys agreement, which
is the cheapest output an agent has.

**MEASURED 2026-09-23** across four dispatches on one architecture review — all four were `Explore` agents, i.e. exactly the population this section is about, not review halves:

| Prompt shape | Result |
|---|---|
| *"map the observer-log family"* (confirming) | its **summary contradicted its own table** — concluded a docstring's referrer list was *"still accurate"* including a `block-idle-stop.sh` comment, while its own 19-file table omitted that hook. Re-measured: **0** references |
| *"try to break this, default to refuted"* | **refuted a sub-claim already published to backlog #164** — the example rested on `step` being a parameter of `check-banner-armed.decide` (`:503`), and it is not |
| *"try to break this"* (second) | main claim SURVIVED, and it supplied a **better control than the coordinator's**: `check-fixture-variation.analyse` returns `(findings, examined_keys)` as a SET (`:703-708`) so *"did not fire"* and *"no longer examined"* are distinguishable. The original run never reported it |
| the same discipline turned inward | a review finding's *"nothing states which rule is correct"* was too strong — `begin-plan.py:518-520` states a great deal |

⭐ **The asymmetry is the argument.** A confirming agent that is wrong leaves a false green nobody
revisits. A refuting agent that is wrong costs five minutes of re-measurement. The expected values
are not close.

**How:** say *"your job is to REFUTE this, not confirm it; default to refuted if uncertain"*; **name
the failure mode you most fear** and ask them to hunt it (*"is my synthetic fixture representative
of the real callee?"* is what found the #164 error); hand over the claim **with** its evidence so
they attack the reasoning instead of re-deriving it. ⚠ **Record which shape you ran** — a survived
refutation is a far stronger result than a confirmation, and a reader cannot tell them apart later.

⚠ **NOT MECHANISABLE, and that is stated rather than hidden.** Nothing persists a subagent's prompt
where a guard could read it, so no script can assert this was done. It is a convention, and this
project's own doctrine says a convention catches only what you READ. ⛔ It is written here because
the alternative was measured on the day: the pattern was observed, called *"worth keeping"* twice in
chat, and **nothing was built** — until the user asked *"have you done something to keep the
pattern?"* and the answer was no. That is the failure the same day's architecture review documented
at length: naming a class does not stop it.
- **Spec:** architectural gaps, underspecified behaviour, security risks, contradictions, edge cases
- **Plan:** missing tasks, wrong order, underspecified acceptance criteria, implementation risks
- **Code:** per-task (Claude + Codex independently). Both must complete before marking a task done.

Address all High/P1 findings before showing the user. ⟳ **SUPERSEDED 2026-09-14 — Medium/P2 is no longer presented for a decision; §0 Q3 disposes of it by rule and records the disposition per finding.** This sentence is kept because five merged review documents cite it; it states what the process USED to do.

### Iterative Re-Review (big / critical changes) — required

One review round is not the gate; **convergence** is. After addressing a round's Blocking/High findings, **re-run the full dual adversarial review (Codex + Claude) on the *revised* artifact**, and repeat until a round reaches **diminishing returns**. Fixes routinely introduce new defects or expose deeper ones that the first pass could not see — a single round gives false confidence.

**When this is required** (any one triggers it):
- Schema / identity / idempotency changes; concurrency, leasing, or locking; auth / RLS / multi-tenant isolation; money-spending or irreversible paths.
- Refactors that touch already-merged, shared code (e.g. a function used by both local and cloud).
- **Any round that returned a Blocking finding, or whose fixes were non-trivial** (more than a reworded line). A Blocking fix is itself a new, unreviewed design — it must be re-reviewed.

For small, contained changes (single-file logic, config, thin wrappers), one round is fine — do **not** over-apply this.

**The loop:**
1. Review (Codex + Claude, independent) → group Blocking/High/Medium/Low.
2. Address all Blocking/High. ⟳ Medium is **disposed by §0 Q3**, not presented — see the supersession above.
3. **Re-review the revised artifact** — both passes again, explicitly scoped to (a) verify each prior finding is *genuinely* fixed, not reworded, and (b) hunt for defects the fixes introduced.
4. Repeat from 2.

### ⚠ Non-convergence means different things on a DOCUMENT and on CODE — added 2026-08-28

⟳ **CORRECTED 2026-09-14.** `docs/dev-process.md` no longer arms the architecture review on a
COUNT — it arms on **thrashing**, and reaching four rounds obliges asking rather than firing. The
paragraph below describes the count trigger it USED to carry; the distinction it draws is why the
count lost. That trigger was bought with the stable-blob-addressing spec — but it was written from
one shape of failure and reads as if it covers every shape. **It does not, and the difference decides
whether a fifth round is worth running.**

**The distinction is the CAUSE of the non-convergence, not the count of findings.**

| Shape | Tell | What it means | Do |
|---|---|---|---|
| **Thrashing** | findings are **introduced by the previous round's own fix**; severity stays put | the design is fighting itself — a real architecture problem | **the architecture review.** This is the shape the trigger was bought for, and since 2026-09-14 it is the ARMING CONDITION itself |
| **Prose floor** | findings shift from *"this cannot work"* to *"this is under-specified"*; each round is right and the artifact keeps improving | the review has reached the limit of what can be settled **without an executable subject** | **Stop reviewing prose. Write the code or the plan, and review THAT** |

**Why the second shape exists at all.** A spec review has nothing to run. A reviewer can verify a
citation, refute a premise, and find an ambiguity — but *"define what malformed means"* and
*"what happens on the third edge case"* are questions whose answers are only checkable once something
executes them. Rounds spent on them produce true findings and never terminate, because the artifact
cannot answer back. Continuing is not diligence at that point; it is reviewing the wrong subject.

**⛔ RAW BLOCKING COUNT IS A BAD DISCRIMINATOR, AND THIS WAS MEASURED.** The dashboard spec ran three
rounds: Blocking totals **4 → 5 → 4**. Flat. By count that looks like thrashing and would argue for
the architecture review. By cause it was the prose floor — round 1 said *"the first chart is built on a file that
does not contain what you claim"* and *"bundled is not loadable"*; round 3 said *"define malformed"*
and *"say how a needs-you item stops needing you"*. **The number said one thing and the character said
the other.** Do not read the trigger off a count.

⚠ **And do not use this as an escape hatch.** The same spec ALSO showed thrashing twice — round 2
found that round 1's fix had produced an untested primary while asserting the opposite, and round 3
found that the scope cut had silently dropped a fix round 1 had won. **Both shapes can be present at
once.** The question to answer, out loud and per finding, is: *did the previous fix cause this?* If
yes for a meaningful share of the round, it is thrashing and the count is irrelevant.

**How to record the call.** Whichever way it goes, write the reason in the round's review doc — the
shape you judged it to be, and the per-finding evidence. A decision to stop reviewing is exactly the
kind that looks arbitrary six weeks later.

**Four rules for the loop** — evidence for each in `docs/process-rationale.md`:
- **At fix time, list the consumers.** Before a fix that changes what state *means*, name every reader
  — including the same code in a **different process**. `grep` for the field name is usually the job.
- **Reviewer disagreement is the signal.** Never resolve a split by majority or by trusting a CONVERGED
  verdict. Adjudicate by reading the code, and **record the adjudication in the review doc**.
- **Each gate re-derives ONE inherited assumption** — chosen because this gate has information the
  earlier one lacked (per-task review re-derives what produces each variant of the types it consumes).
  One question, not a re-review.
- **Convergence measures the prompt too.** Carry a standing list of root-cause *shapes* into each
  round's prompt and ask for siblings by shape, not another read-through. List: rationale doc.

### Between rounds: classify the rules, then cross-derive them (added 2026-08-06)

**Do this after round 2, before dispatching round 3.** Two rounds of review on the stable-blob-addressing
spec produced a reviewer verdict that no individual finding could have: *"the fixes are individually
thoughtful and most of them land. They fail **as a set** — each was written into its own section and
none was re-derived against the others. Every Blocking is an interaction between two fixes, not a
defect in either one."* A review round is the expensive way to learn that.

**Step 1 — classify every rule the artifact now states.** Three kinds:

| | Meaning |
|---|---|
| **P — Physical** | Imposed by the database, the platform or a vendor. Not negotiable |
| **I — Invariant we chose** | Load-bearing but **ours**. Changing it has a cost, not an impossibility |
| **H — Heuristic** | A tuned value or default. Expected to move; must never block a design |

**The whole point is separating I from P.** Measured on that spec: of roughly 30 findings across two
rounds, **~9 dissolved outright when a rule was reclassified** — and they were specifically the ones
that **kept coming back**. Ordinary defects (a missing FK target, a stale citation, judgments written
into frontmatter) had nothing to do with premises and were simply fixed.

> **So the trigger is recurrence, not volume.** When a *third* finding lands in the same area, stop
> patching and ask which rule there is a choice wearing the costume of a constraint. Both clusters below
> were on their third appearance before anyone questioned the premise underneath them.

- *"The workspace id must never equal a uid"* — sounded physical, was a choice, and forced a
  whole-corpus migration of paid content. Restated as an **I about a predicate** (*no predicate may
  compare the path segment to `auth.uid()`*) it dissolved a Blocking and made the migration incremental.
- *"The manifest is mutable state protected by a conditional write"* — a choice. Deriving `current`
  instead deleted a CAS, a limbo state, a requeue protocol and a whole table, and closed three findings.
- *"Everything in the bucket is an artifact the manifest tracks"* — a choice. Reclassifying assets as
  **sources** closed two more.

Note the mirror: the openly-heuristic rules (a 0.8 threshold, a 90-day retention) **never caused a
problem**. *Visible tuning knobs are safe; invisible ones are the dangerous kind*, because nobody
thinks to question them.

**Step 2 — cross-derive.** Check each rule against every other and record the conflicts. On that spec
this found **five**, all between rules written within hours of each other — including one **new**
defect introduced inside a fix (an eligibility test that read a blob, silently reintroducing
absent-vs-failed in the fix that removed a different instance of it).

**Step 3 — evaluate the I rules.** For each, ask **not** *"is it true?"* but ***"is what it buys still
worth what it forbids?"*** Name what it forbids explicitly — a rule whose cost is unwritten cannot be
re-evaluated. Expect refinements rather than deletions: on that spec, 8 of 12 were sound as written,
2 were right in substance and wrong in wording (one had an undocumented exception **already in
production**), and 1 was a relaxation candidate whose stated justification no longer held.

**Why it goes here rather than in the review prompt.** The reviewer can only see the artifact. Which
rules are *chosen* is authorial knowledge, and re-deriving your own fixes against each other is cheap,
while paying a review round to discover the same interaction is not.

### Step 4 — classify the GUARDS: SHAPE or SEQUENCE (added 2026-08-07)

Steps 1–3 classify the **rules**. This classifies the **enforcement**, and it is a different pass with
a different yield. Run it over *every* guard — constraints, unique indexes, foreign keys, trigger
raises, early returns — including the boring ones.

| | Asks | A violation means | Must |
|---|---|---|---|
| **SHAPE** | is this well-formed and referentially sound? | the **caller is wrong** | **reject** |
| **SEQUENCE** | who got here first? has this already happened? is this in flight? | **concurrency** — the caller did nothing wrong, and may already have spent money | **reconcile**: an upsert, a no-op, or a typed outcome. **Never a raw rejection** |

**The one question to ask of each guard: what does this do when the caller is merely SECOND?**

That is deliberately *not* "is this guard correct?" Both defects this found were **plainly correct**
guards — a reviewer reads them, agrees, and moves on. Seven rounds of adversarial review with
unlimited depth missed both; one shallow pass over all 32 found them in an hour.

**Measured on the blob-addressing schema (2026-08-07):** 32 guards, 26 SHAPE, 6 SEQUENCE. Every CHECK
and FK was SHAPE and correct, so the pass concentrates attention on ~6 items out of 32 — most of its
value. Of the six, three were already reconcilers (including the one predicted broken), one was a
deliberate fence, and **two were rejecters**: an entire *kind* of write was unreachable (every
re-render failed with a raw `23505`), and the retention sweep **could never run at all**, because its
safety rule aborted the batch and the row it tripped on was permanently in that state.

**When to run it:** before a review round on anything with a write protocol, and *always* before
promoting a schema into `supabase/migrations/`. It is cheap, total, and mechanical — the opposite
axis from adversarial review, which is deep and selective. **Depth and coverage do not substitute for
each other**, and a project buying a lot of depth should notice when it has bought no coverage.

**⟳ IT IS NOW A RATCHET, NOT A DISCIPLINE (added 2026-08-07).** A rule that depends on remembering is
the shape this project's own reviews keep finding in the *code*; running the classification by hand
would have been the same defect in the *process*. Two mechanical checks:

| Check | What it enumerates | Fails when |
|---|---|---|
| `scripts/check-guard-coverage.py` | every constraint, unique index, FK and trigger, read from **`pg_catalog`** | a guard is unclassified, a classification is stale, or a SEQUENCE guard has no mutation |
| the coverage assertion in `schema/05_assert.sql` | every value of the `artifact_kind` enum × free/paid | any kind is never written a **second** time to the same slot |

The population comes from the live catalog and the enum, never from a hand-maintained list — so a
guard added tomorrow cannot be silently skipped. **Both earned their place on the first run:**
the first found four guards nobody had ever inventoried (two auto-named `state` CHECKs among them),
and the second, verified by deletion, reproduces the exact free-render defect that survived seven
rounds. The machine count also corrected the manual one — 28 SHAPE / 4 SEQUENCE, not 26 / 6.

**Both are LOCAL gates today**, alongside `verify-schema.sh`, because they need a live Postgres and
CI has none while this schema is still outside `supabase/migrations/`. Wiring them into CI is part of
the promotion slice, not a separate task — a gate that only runs when someone remembers is halfway
back to a discipline.

**Two rules that fall out, both learned by getting them wrong:**
- **A promise like "this never refuses" is a NEGATIVE property over every guard on its write path.**
  Count them before believing it. `record_artifact` promised exactly that across **32** rejection
  mechanisms; each new guard was a new way to break it, and one added a day later did.
- **Never convert a rejecter into a silent no-op.** Move the test into a predicate the caller selects
  *through*, and keep the rejecter as a backstop. Suppressing the write quietly tells the caller it
  succeeded — shape #5, and worst on delete paths, which have no undo.

*(Origin: round 7's `B1` was a decision that had an assertion **and** a passing mutation and broke
anyway. Asking why led here — see `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md`
§5.2.5.)*

### And apply the Enumerated Behaviors table to DECISIONS, not only to tasks (added 2026-08-07)

The Per-Task Checklist already demands an **Enumerated Behaviors** table before tests are written.
Nothing demanded one for a **decision** — and a decision is exactly where it is most needed, because
a decision is recorded as prose and defended by a test written against *the scenario that prompted
it*.

Measured: the user decision *"the reservation guards spending, not recording"* had an assertion naming
it and a mutation confirming that assertion was load-bearing. Both passed. It broke anyway, because
the assertion passed a *different* generation id and *supplied* the span — the one configuration where
the implementation happened to be correct. Three other arrivals at the same function violated the same
promise with no assertion at all.

> **Mutation testing proves a guard is LOAD-BEARING. It never proves the assertion set is COMPLETE.**
> It answers *"does deleting this code break a test?"*, not *"does the test cover the promise?"*

So: when a decision is made — especially one made **against** a recommendation — enumerate the ways a
caller can reach the code it constrains, and assert the property at each. For `record_artifact` that
was four cells (holder vs lost token × same vs different generation × args supplied vs omitted ×
generation pending vs completed-by-another). Three were broken.

**Related but different:** the `zoom-out` skill orients you in unfamiliar **code** (a map of modules and
callers). This orients you in your own **assumptions**. Both are "go up a level"; only one questions
whether a constraint is real.

---

**Where review effort belongs:** per-task review is structurally blind to composition defects. Keep it
light for internally-simple tasks; spend the budget on whole-branch rounds.

**Before deferring a finding, try to turn it into an assertion.** "Unverified — check at deploy" is a
bet that a manual check happens later. If the claim can be expressed as a test using scaffolding that
already exists, write it NOW: it is usually minutes, it either promotes the finding to a fixed bug or
retires it, and either way it leaves a regression guard. Applies hardest to money and data-loss paths,
where the alternative first evidence is a production incident. Determine external behaviour by probing
the live system, not by reading vendor types.
*(Why: a suspected double-charge sat as a roadmap line for a day; one test measured it at 6¢→12¢ —
`docs/process-rationale.md`.)*

**Stop (diminishing returns) when** a full re-review round returns **no new Blocking or High** — only Low/nits, or findings already known-and-accepted (recorded as deferred with an owner). That round is the gate; then get human approval. Do **not** stop merely because you are tired of reviewing or the artifact "feels done."

**Keep going when** a round surfaces a *new* Blocking/High (common after a big rewrite) — that is proof the loop is still earning its cost; another round is mandatory.

**Save every round** to `docs/reviews/` with a version/round suffix (e.g. `-v2-rereview.md`) so the convergence trail is auditable.

*(Empirical basis — Stage 1E-b and Stage 3 cloud-sync: `docs/process-rationale.md`.)*

