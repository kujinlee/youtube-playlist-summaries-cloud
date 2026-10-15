# Round 1 — CLAUDE half — branch `plugins-handoff-citations` @ `55975f92`

Subject: `git diff origin/master..55975f92` — 8 files, +169/−14.
Mandate: **refute**, not confirm. Seven priority questions from the brief, each answered below with
what was run.

The branch's thesis is sound and the subject is real: five sibling documents, authored in one commit
on **2026-08-27** (`24ff8694`), cited line numbers inside a vendored file, and the vendor shipped
**0.33.0** on 2026-09-15. Removing the numbers rather than re-pointing them is the right call and I
did not try to argue the other way (the brief ruled it out of scope, and I agree with the ruling).

**What the round found is that the correction repeated the defect one layer in.** The four stale
LINE NUMBERS were replaced, in part, by a stale BEHAVIOURAL CLAIM taken from a comment in the same
vendored file — and that claim is measurably false against the code it describes. One sibling site
of the original five was also missed, and it is the one the refusal text sends the blocked reader to.

---

## Blocking

### B1 — The ⭐ lesson "the hook refuses to degrade quietly" is MEASURED FALSE. The hook does the opposite, and its own comment says silence was tried and reverted as wrong.

Three sites make the claim. `docs/process-rationale.md:384-388`:

> ⭐ **The hook refuses to degrade quietly, and that is worth copying.** A `per_session` request with
> no resolvable session id falls back to the shared file and **withholds the hint**, so the transcript
> shows *no hint was given* rather than a namespaced path that never applied.

`docs/dashboard-entries.md:14856-14858`, for a non-technical reader:

> Worth keeping: the plugin, when asked for per-session notes but unable to work out which session it
> is in, deliberately says nothing rather than naming a destination that was never really in use.

And the commit message of `678a35db` repeats it verbatim ("…falls back to the shared file and
WITHHOLDS the hint").

**MEASURED.** I drove the live hook three ways in an isolated tree (temp `HOME`, temp
`CLAUDE_PROJECT_DIR`, real `CLAUDE_PLUGIN_ROOT`), varying only `.handoff_mode` and the presence of
`session_id` on stdin. Transcript of the degrade case — `handoff_mode: per_session`, stdin
`{"source":"startup"}`, no `session_id`:

```
=== HANDOFF ===
Write next handoff to: <…>/proj/.remember/remember.md
(handoff_mode is "per_session", but no session_id reached this hook -- writing to the shared file above, not a per-session one.)
```

The hint is **not withheld**. It fires, with the correct shared path, followed by an explicit
degradation notice. For contrast, the same two runs that bracket it:

| run | `.handoff_mode` | `session_id` | `=== HANDOFF ===` block | path printed |
|---|---|---|---|---|
| A | absent (default `single`) | `abc123` | **not emitted** | — |
| B | `per_session` | `abc123` | emitted | `…/.remember/remember.abc123.md` |
| C | `per_session` | **absent** | **emitted + degrade notice** | `…/.remember/remember.md` |

**Where the false claim came from, which is the part that matters.** The hook carries a comment block
at `session-start-hook.sh:1153-1163` that describes exactly the withholding behaviour the branch
asserts ("*the hint below is withheld rather than pointed at it*"). That comment is stale. Fifty
lines later, at `:1181-1200`, the hook says so itself:

> NOT withheld on degrade. An earlier version of this hook suppressed the hint outright whenever
> `per_session` was requested but had no usable session id… That reasoning was wrong in external
> mode… **The honest fix is not silence, it is a visible line.** A reviewer of #363 caught this
> before it shipped.

And the code at `:1544` matches the second comment, not the first:
`if [ "$REMEMBER_ROOT" != "$PROJECT_DIR" ] || [ -n "$PER_SESSION_HANDOFF" ] || [ -n "$HANDOFF_MODE_DEGRADED" ]`.

**Why this is Blocking rather than a Medium.** It is not a stray figure. It is published as a ⭐
design lesson *to copy*, and as the one paragraph of the dashboard entry addressed to the reader as
transferable wisdom. It also asserts the lesson is "*cannot-run-is-not-a-pass* implemented in a
vendored dependency — the same rule this repo enforces in `check-schema-gates.sh` and
`check-plan-file-tags.py`", which binds a false observation to two of this repo's real mechanisms.
The branch exists to stop citing a vendored file from memory; this paragraph cites a vendored file's
**comment** from memory, which is the same defect with the line number taken out.

⭐ **The cheap repair is strictly better than the claim it replaces.** The real behaviour is a
sharper lesson than the invented one: *the hook does not go silent and does not lie — it prints the
true path and a second line saying the mode you asked for did not apply.* And the hook's own history
records that silence was tried, reviewed, and rejected. That is a more useful thing to copy than
"deliberately says nothing", and it costs the same number of lines.

**Falsifier for the fix:** re-run case C above; the fixed paragraph must predict a printed hint plus
a degradation line. If it predicts silence, it is still wrong.

---

## High

### H1 — There is a FIFTH live site, it is git-tracked, it was authored in the SAME commit as the four, and it is the file the refusal text tells a blocked reader to open.

`docs/process-rationale.md:359-368`, the memory file at `:8-15`, the dashboard tech block, and both
commit messages all enumerate **four** live sites and then explicitly account for the one deliberate
exception (`velocity-177-r5-claude.md:161`, left as a record). The enumeration is short by one.

`.agents/skills/handoff/SKILL.md:13` — unchanged by this branch:

> See `session-start-hook.sh`: `REMEMBER_HANDOFF="$REMEMBER_DIR/remember.md"` (**:795**), emitted as
> `=== LAST HANDOFF ===` and **injected before identity and memory, specifically so it survives
> context-preview truncation** (**:809-812**). Delivery is fingerprinted and non-destructive
> (**:814-825**), so a session that reads it without writing one back does not consume it.

Measured properties of that site:

* **Tracked.** `git ls-files .agents` lists it; `git check-ignore` does not match it. It is not
  behind the bare-`*` `.gitignore` the brief warned about — `.claude/.gitignore` does not exist in
  this worktree, and `.claude/skills/handoff` is a **symlink** to `../../.agents/skills/handoff`, so
  this is one file reachable under two paths, not two files.
* **Same origin as the four.** `git log -S':795' -- .agents/skills/handoff/SKILL.md` and
  `git log -S'session-start-hook.sh:795' -- docs/plugins.md` both bottom out at **`24ff8694`,
  2026-08-27**. The five citations were written together; four were fixed.
* **Named by this branch's own governance table as part of this mechanism.** `docs/plugins.md:100`
  (final text) lists `.agents/skills/handoff/SKILL.md` as **Layer 3** of the three-layer handoff
  guard. The inventory excluded a file the same document enumerates two screens below the RULE box.
* **It is the repair target the refusal text prints.** `.claude/hooks/enforce-handoff-path.sh:77`
  tells a blocked reader `$EDITOR .agents/skills/handoff/SKILL.md`. So the branch's own strongest
  argument — "the one moment someone needed the locator was the moment it sent them to the wrong
  line" — applies a second time, to the file the refusal hands them next.
* **No guard can see it.** `scripts/check-handoff-path.py` reads this exact file, but only for the
  presence of the string `.remember/remember.md`. I confirmed the guard is green on the current
  content: the stale locators sit beside a correct path, so the gate passes.
* **Its SUBSTANTIVE half is stale too**, not just the numbers. `SKILL.md:15` still carries the
  pre-correction single-trigger story — "*it means external mode*" — which is the very sentence the
  branch rewrote in the other four places.

This refutes "Four live sites carried them, not one" and the deliberate-exception framing: there were
five live sites and one record.

---

## Medium

### M2 — "Every citation pointed into the wrong third of the file" is false for the headline citation.

Stated at `docs/process-rationale.md:364`, `docs/memory/a-vendored-line-number-has-no-owner.md:6`
(bolded), and implied by the dashboard's "they point into a different part of the file entirely".

Arithmetic over a 2,027-line file (thirds: 1–676, 677–1351, 1352–2027):

| cited | third | actual | third | crosses? |
|---|---|---|---|---|
| `:795` → `REMEMBER_HANDOFF` | **2** | `:1171` | **2** | **no** |
| `:809-812` → emit | 2 | `:1666` | 3 | yes |
| `:814-825` → delivery | 2 | `:1571-1640` | 3 | yes |
| `:800-802` → hint | 2 | `:1546` | 3 | yes |

3 of 4, not 4 of 4 — and the one that does not cross is the one the sentence leads with and that the
code comment, the dashboard and both commit messages single out. "Every" is the wrong quantifier.
The weaker true statement ("stale by 376–857 lines; three of the four now sit in a different third")
costs nothing and survives the next version bump.

### M3 — The "a review half had ALREADY flagged exactly this" attribution does not survive reading the cited line.

`docs/process-rationale.md:369-373`, memory file `:22-24`, dashboard ("A review half had already
noticed this exact risk weeks ago and nothing was done with the observation").

`docs/reviews/claude/velocity-177-r5-claude.md:160-162` in full context is a **"Siblings —
searched."** paragraph supporting a finding about the *scope* of a documentation invariant:

> **Siblings — searched.** `grep -oE '[A-Za-z…]:[0-9]+'` over `docs/dev-process.md` (0 cross-file
> locators) and `docs/plugins.md` (1: `session-start-hook.sh:795`). `review-method.md` is by far the
> heaviest user and the only one containing a rule that mandates the form.

It counts locators to establish how far an invariant reaches. It does not say `:795` was stale, does
not mention the `remember` plugin's version, and does not identify vendored-line drift as a class. It
is an **inventory**, and the branch promotes it to a **finding that was ignored** — which then
carries a second claim ("the *finding with no row* shape, one layer out") that rests on it.

This matters beyond accuracy: it assigns a process failure ("the observation was filed and nothing
consumed it") to a round that filed no such observation. "An earlier round had already inventoried
this locator, which is where to look next time" is true and makes the same point.

*Dating checks out: that doc landed 2026-09-24 (`91f38afe`), so "weeks ago" is right.*

### M4 — The new code comment and memory file both rest on `check-withdrawal`, which does not exist in this repo at this commit.

`scripts/check-handoff-path.py:46-47` (new):

> ⚠ This comment is in CODE, so `check-withdrawal` (which globs `docs/`) cannot see a stale figure
> here — it was found by grepping every mention of the hook, which is the only thing that would.

Same assertion in `docs/memory/a-vendored-line-number-has-no-owner.md:12-13` ("**a CODE COMMENT,
which `check-withdrawal` cannot see**… so **no guard could ever have caught it**") and in the
dashboard tech block.

**MEASURED:** `scripts/check-withdrawal.py` is absent from this worktree and absent from
`origin/master` (`git ls-tree origin/master scripts/`). Scanning every local and remote ref, it
exists on exactly one: **`refs/heads/backlog-249-260-fixes`**, unmerged.

So the sentence that explains *why no guard could have caught this* names a guard that is not in the
repo. The claim about its glob may well be true on that branch; it is not checkable from here, and a
reader at this commit who greps for it finds nothing. This is the same shape as the defect being
fixed: an assertion about a file with no owner at this commit.

### M5 — The enumeration that makes the unconditional rule safe is an enumeration of the wrong set.

`docs/process-rationale.md:380-382`, the dashboard tech block and both commit messages justify
"correct for this install" with: *"the default is `single`, **neither settings file** configures
otherwise, `.remember/` holds only `remember.md`, and handoffs are in fact delivered."*

Both of the checkable clauses are wrong about what they name.

**"Neither settings file."** `.handoff_mode` is not read from any Claude Code settings file. It comes
from `config_into HANDOFF_MODE ".handoff_mode" "single"` (`:1164`), which reads
`$REMEMBER_CONFIG` — a tmpfile deep-merged by `lib-memory-dir.sh:294-349` from **three** layers, in
precedence order:

```
ABSENT  <plugin root>/0.33.0/config.json          (bundled; only config.example.json ships)
ABSENT  ~/.remember/config.json                   (user-global)
ABSENT  <repo>/.remember/config.json              (per-project)
```

All three are absent, so the merge falls to `echo '{}'` and the default stands. That is **stronger**
evidence than the claim made, and it names the files that actually decide. Two unnamed "settings
files" is both the wrong count and the wrong set.

**"`.remember/` holds only `remember.md`."** It holds **102** entries — `archive.md`, `now.md`,
`recent.md`, `logs/`, `tmp/`, ~70 `today-*.done.md`. Exactly one matches `remember*`, which is the
intended claim; as written it describes a store that does not exist and invites a reader to conclude
the directory is empty.

*The conclusion itself survives refutation — see "Checked and found SOUND" #1. This is about the
evidence being misdescribed, which is the thing this branch is about.*

### M6 — The refusal text's two-trigger sentence is wrong in the one case where it will be read by someone who can see the contradiction.

`.claude/hooks/enforce-handoff-path.sh:72-74`, rendered (full transcript in Instruments):

```
If a session-start block printed 'Write next handoff to: <path>', obey THAT path.
Two things print it: external mode, and per_session mode (.handoff_mode), where
the hook reads remember.<session-id>.md and NOT the shared name above.
```

Measured: **three** things print it (run C above), and in the third the hook reads **exactly the
shared name above**. A reader in the degraded state sees `Write next handoff to:
…/.remember/remember.md` on screen while the refusal tells them the printed path means "NOT the
shared name". The *instruction* ("obey THAT path") stays safe, because the printed path is right; the
*explanation* contradicts what they are looking at. The brief is correct that a wrong word costs more
here than in a doc.

Same error, same wording, in `docs/plugins.md:86-87`: "⟳ **TWO triggers, external AND `per_session`**".

### M7 — `docs/plugins.md`'s replacement dropped the sentence that made the ABSENCE of a hint informative, and the referent it put in its place is ambiguous.

Removed:

> **If a session-start block prints `=== HANDOFF === / Write next handoff to: <path>`**, you are in
> external mode — obey that path instead. **It is absent in legacy mode by design** (`:800-802`).

Added:

> **If a session-start block prints `Write next handoff to: <path>`**, obey it — ⟳ **TWO triggers,
> external AND `per_session`**, where this path is NOT read → [`process-rationale.md`].

Three things changed, and only the first was intended:

1. The line number went. Correct, and in scope.
2. **"It is absent in legacy mode by design" went.** That was the clause that told a reader *no hint
   ⇒ you are in the world this rule describes*. Its removal is what the brief asked about: the
   correction keeps the rule and deletes part of its justification. The new text adds the knowledge
   that two worlds exist without leaving the reader any way to tell which one they are in, inside the
   RULE box.
3. **"where this path is NOT read" has two available referents** — the `<path>` just printed (wrong;
   that is the one to use) or `.remember/remember.md` (intended). In the box whose entire job is
   naming one path, that is the worst place for the ambiguity.

The reader is then sent to `process-rationale.md` to resolve the condition — and that is where **B1**
lives, so the one document that explains when the rule does not hold describes that case wrongly.

### M8 — "that file grew by a thousand lines" / "more than twice as long" is an inference presented as a measurement, and it is not verifiable on this machine.

Commit subject `678a35db`: "…and that file grew by a thousand lines". Dashboard entry: "It is now
more than twice as long." Both sit immediately beside genuinely measured figures ("Measured against
the live 0.33.0 hook, which is 2,027 lines"), which lends them provenance they do not have.

`ls /Users/kujinlee/.claude/plugins/cache/claude-plugins-official/remember/` → **`0.33.0` only**. No
earlier copy of the hook exists locally and a vendored cache has no git history, so the old line
count is not recoverable here. The growth figure is derived from where the old citations pointed
(max `:825`), which bounds the old file from below and not at all from above.

It is *plausible* — today's handoff machinery spans `:1164-1666`, i.e. ~57–82% of the file, and
`825 / 0.82 ≈ 1,006`, giving growth ≈ 1,000. But that is a proportional-structure argument, not a
measurement, and this repo's own rule is to derive or label. State it as "the citations' subject moved
from `:795-825` to `:1164-1666`" — which is measured, is the thing that matters, and needs no guess
about the old total.

### M9 — `a-harness-cannot-read-a-cause-from-a-childs-text.md` gives no resolvable provenance, and "r9–r12" is ambiguous across at least five subjects on this branch.

The file makes three specific measured claims (a fabricated second exception, `os._exit(1)` read as
"the suite RAN", a traceback forging a `[FAIL]` line) and names four repairs. Provenance is
"`check-plan-code.py` (r9–r12, 2026-10-13)" — no PR, no branch, no SHA.

Measured at this commit:

* **None of the four named repairs exists.** `grep` over `scripts/check-plan-code.py` for
  `isidentifier`, a `File "` structural marker, a "0 bytes is not evidence of execution" message, and
  any stdout-only failure-name rule → **0 hits each**. The file describes code that is not in this
  branch (expected; it was measured on the #371 branch).
* **"r9–r12" does not identify a subject.** `docs/reviews/*/` on this branch holds rounds in that
  range for at least five different subjects: `closing-table`, `harness-progress`, `main-drivable`,
  `record-review-topology`, `shard-mutation-sweep`. A future reader cannot resolve the reference.

A memory recording a lesson whose evidence is unreachable is exactly
`[[a-retrospective-number-needs-provenance]]`, which the sibling memory file cites approvingly. One
PR number fixes it.

---

## Low

### L1 — Two checkable numbers in the dashboard tech block are wrong.

* "`Mode gate: config_into HANDOFF_MODE …` … **`:1165`**" (`docs/dashboard-entries.md:14872`). Actual
  **`:1164`**. (`:1168` and `:1171` in the same sentence are both right.)
* "`docs/plugins.md` (net zero lines … **the correction had to replace eight lines with eight**)"
  (`:14863-14864`), repeated in the commit message. `git diff --numstat` says **5 added / 5 removed**.
  Net zero is right; eight is not.

Low because nothing depends on either. Noted because the branch's subject is wrong numbers in prose,
and both of these are one command away.

### L2 — The new memory file's `[[link]]` points at a file that is uncommitted in the main checkout — the exact pile the commit says it is avoiding.

`a-harness-cannot-read-a-cause-from-a-childs-text.md:24` links
`[[printing-more-evidence-weakens-substring-cases]]`. Of the six `[[links]]` across both new files,
five resolve; this one does not — no such file in `docs/memory/` on this branch, and `git log` has
never seen it. It exists only as an **uncommitted** file in the main checkout (created today 07:04).

A dangling `[[link]]` is tolerated by the convention. What makes it worth a line is the commit's own
reasoning: these two files "ride here rather than joining that pile" of six uncommitted memory files
— and the link's target is in that pile. Either carry it, or drop the link.

### L3 — Both new `MEMORY.md` rows exceed the ~200-char limit the file itself states, and the index is already over budget and truncated on load.

Measured: the two new rows are **230** and **210** characters. `docs/memory/MEMORY.md`'s own header
says "Keep index entries to one line under ~200 chars". File size **25,884 → 26,336 bytes** (+452).

The harness reports this index as over its limit and **partially loaded** ("Only part of it was
loaded"). `docs/memory/` is the live store — `~/.claude/projects/<slug>/memory` is a symlink to it —
so this lands immediately, and 452 bytes of other rows move past the cut. 35 of 139 existing rows are
also over 200, so the convention is widely broken already; this is a nudge in the wrong direction on
a file that is actively being truncated, not a new defect.

### L4 — The dashboard entry describes commit 1 and is silent about commit 2.

`55975f92` adds two memory files and two `MEMORY.md` rows; one of them
(`a-harness-cannot-read-a-cause-from-a-childs-text.md`) is about the mutation harness and has nothing
to do with this branch's subject. The `## 2026-10-13` section — prose and `<!--tech-->` block — covers
only the citation work and the four files of `678a35db`. `check-dashboard-entry.py` is satisfied by an
entry existing, so nothing catches this. A reader who was away learns about four files out of eight.

### L5 — "Name the SYMBOL and give the command" is followed at two of the four corrected sites, and the command that is given is not pasteable.

The prescription is the memory file's own (`:19`). Measured across the four:

| site | symbol | command |
|---|---|---|
| `.claude/hooks/enforce-handoff-path.sh` | ✅ | ✅ |
| `scripts/check-handoff-path.py` | ✅ | ✅ |
| `docs/plugins.md` | ✅ | ✗ |
| `docs/process-rationale.md` | ✅ | ✗ |

And the command itself is `grep -n 'REMEMBER_HANDOFF=' <the hook>` — no path, so a blocked reader
cannot paste it; the file lives at
`~/.claude/plugins/cache/claude-plugins-official/remember/<version>/scripts/session-start-hook.sh`.
Run against the real file it returns **two** hits (`:1168` per-session, `:1171` shared) and the text
does not say which is the one being named. A pasteable, self-disambiguating form exists and is no
longer:
`grep -rn 'REMEMBER_HANDOFF=' ~/.claude/plugins/cache/*/remember/*/scripts/session-start-hook.sh`.

### L6 — The branch's own CANNOT-RUN disclosure names one affected guard; three are affected, and `check-selftest-counts` reports two reds, not one.

The commit's ⚠ note attributes the `check-selftest-counts.py` red solely to `check-plan-code.py`'s
`HARNESS_TREE` case. Measured in this worktree (full table in CANNOT RUN below), the missing
`node_modules/typescript` reds **three** things:

* `check-plan-code.py --self-test` → 175/178, 3 failures, all `node_modules/typescript`
* `check-paid-caller-arrival.py --self-test` → **12/32**, 20 failures, all `ERR_MODULE_NOT_FOUND`
* `check-selftest-counts.py` → names **both** of the above, not one

Plus `check-test-counts.py`, which cannot run for an unrelated environmental reason (no
`jest-results.json`) and is not mentioned at all. Everything here is environmental, pre-existing and
outside the diff — the disclosure is honest in kind and short in extent, which is the thing
`[[a-bound-enumerates-what-is-witnessed]]` is about.

---

## Checked and found SOUND

1. ⛔ **Priority question #1 — `per_session` CANNOT be active on this install, so the ⛔ RULE is
   latent-conditional, not live-wrong. I tried three ways to make it fire and failed.** This was the
   brief's Blocking candidate and it does not stand.
   * Every file that can set `.handoff_mode` is **absent**: all three config layers listed in M5.
     `config_into` (`log.sh:633`) reads only `$REMEMBER_CONFIG`, which `lib-memory-dir.sh:358` points
     at a merged tmpfile; with zero sources the merge is `echo '{}'`.
   * **No env var can reach it.** `handoff_mode` has no env override anywhere in the plugin
     (`grep -i handoff_mode` over the whole 0.33.0 tree: config, docs, tests, the hook — never an
     env read). The only env lever is `REMEMBER_CONFIG` itself, which Claude Code does not set.
   * **Driven, not reasoned:** run A (default, with a session id) emits **no** `=== HANDOFF ===`
     block at all, so nothing competes with the rule's path.
   * **Independent instrument:** `remember`'s own `doctor.sh`, against the real repo, reports
     `Storage mode: legacy (in-project: …/.remember)` and `REMEMBER_DIR = <repo>/.remember`. Legacy
     and in-project ⇒ `REMEMBER_ROOT == PROJECT_DIR` ⇒ the external trigger is off too.
   * The live `.remember/` contains exactly one `remember*` file and no `remember.<session-id>.md`.
2. **The refusal heredoc renders correctly — nothing expands, nothing truncates.** Driven through a
   stub guard returning rc=1, with `TMPDIR` and `EDITOR` set to loud sentinels. rc=**2**, stdout
   empty, stderr 27 lines, **zero sentinel leakage**: `\$TMPDIR` and `\$EDITOR` survive as literals,
   `$VERDICT_OUT` interpolates as intended, and the new lines introduce no new expansion (`<the hook>`
   is inert inside a heredoc, `'…'` quotes are literal, no backticks). Full transcript in Instruments.
3. **`grep -c '^## '` on `docs/dashboard-entries.md` RISES: 306 → 307.** The keep-both fusion did not
   happen on this branch, and the commit's ⚠ flag about PR #371 also adding a `## 2026-10-13` section
   is accurate and correctly places the obligation on whichever merges second.
4. **No mutation anchor was orphaned.** Every `edits[][0]` across `scripts/mutations/*.json` still
   binds: **1,416 edits checked, 0 orphaned**. The `check-handoff-path.json` manifest's five entries
   all target code, not the comment block this diff rewrote, so the comment edit could not unbind
   them — but I verified rather than assumed, because a nearby edit is the usual cause.
5. **`check-docs.py` is green and the 260-line budget claim is true.** `docs/plugins.md` is exactly
   260 lines on both `origin/master` and HEAD (5/5, net zero). ⚠ One nuance the commit's "check-docs.py
   OK, 260 lines" omits: the guard emits `TIGHT (0 line(s) of runway)` and a ⚠ WARN naming a **human
   decision** (raise the budget, or prioritise and retire). rc=0, so "OK" is literally right; the
   standing warning is pre-existing and this branch did not consume runway.
6. **The mechanical description of the two modes is correct**, and I confirmed each half by execution
   rather than reading: `single`/absent → `remember.md`; `per_session` + resolvable id →
   `remember.<session-id>.md` (run B). `:1168`, `:1171`, `:1666`, `:1546` and `:1571-1640` all resolve
   to the objects named. Fingerprinting is on **content** — `cksum < "$1"` at
   `session-start-hook.sh:1641-1642` — so "fingerprinted on CONTENT so a read-only session does not
   consume the next one's note" is right, and is a better phrasing than the "non-destructive" it
   replaced because it says *why*.
7. **"stale by 370–870 lines" is a valid bound.** Actual deltas 376, 857, 757, 746 — contained, and
   stated as a range rather than a point. (Contrast M2, where the quantifier is "every".)
8. **The removed-not-updated decision, and leaving `velocity-177-r5-claude.md:161` untouched.** Not
   argued against, per the brief. The reasoning ("no owner, no guard, invalidated with no commit") is
   correct and the vendor shipped 0.33.0 on **2026-09-15**, 19 days after the citations were written
   — the mechanism is demonstrated, not hypothetical. Treating merged review docs as records is
   consistent with how this repo has handled every previous one.
9. **`.claude/` was checked on the filesystem, not through `git status`**, per the brief's backlog-#86
   warning. In this worktree `.claude/.gitignore` does not exist, `.claude/skills/*` are 21 symlinks
   into `.agents/skills/`, and the only `.claude/` file carrying a citation is the hook in the diff.

---

## CANNOT RUN — ⛔ treat every row as NOT RUN, not as a pass

Every `python3 scripts/*.py` invocation in `.github/workflows/ci.yml` was extracted mechanically
(`grep -oE 'python3 scripts/[A-Za-z0-9_.-]+\.py( --self-test)?'`) and run — **57 invocations, no
subset**, per `docs/CLAUDE.md` rule 1. **51 exited 0.** The six that did not:

| invocation | rc | verdict |
|---|---|---|
| `check-plan-code.py --self-test` | 1 | **NOT RUN** — 175/178; 3 failures all `node_modules/typescript is missing … TREAT THIS AS NOT CHECKED`. Environmental, pre-existing, outside the diff (CI installs deps). Confirms the brief. |
| `check-paid-caller-arrival.py --self-test` | 1 | **NOT RUN** — 12/32; 20 failures, `ERR_MODULE_NOT_FOUND` from `scripts/ts-comment-spans.mjs`, which the script documents as having **no fallback** (`:181`). Same root cause. ⚠ Not named in the branch's disclosure — see L6. |
| `check-selftest-counts.py` | 1 | **NOT RUN** — a consequence of the two above; it names **both**. |
| `check-test-counts.py` | 1 | **NOT RUN** — `FAIL (cannot run): no jest results at …/jest-results.json`. Its own message says to treat it as not run. CI produces the file. |
| `check-review-recorded.py` | 1 | **STILL RED after this half was written — re-run to check, and it did not clear.** "2 guarded path(s) changed and no review round was recorded: `.claude/hooks/enforce-handoff-path.sh`, `scripts/check-handoff-path.py`". ⛔ It reads the **committed** tree, so both halves sitting uncommitted in the worktree are invisible to it: `git status --porcelain` shows all three review artefacts (`claude/`, `codex/`, `verdicts/`) as `??`. **It clears when the halves are COMMITTED, not when they are written** — the coordinator must not read my rc=0 on `check-review-rounds.py` as this gate being satisfied too; they disagree on purpose. ⚠ The CI step runs this PR-only with arguments; my bare run exercises the default path. |
| `check-review-rounds.py` | 1 | **CLEARED by this document — re-run after writing gives rc=0.** Before it: "`plugins-handoff-citations` round 1: only codex — claude neither ran nor recorded a `REVIEW GAP:` line". This guard reads the working tree, which is why it clears while `check-review-recorded.py` above does not. |

**Also NOT RUN, and not a pass:**

* **Every measured claim in `a-harness-cannot-read-a-cause-from-a-childs-text.md`.** The code it
  describes is not in this branch (M9). I could neither reproduce nor refute the fabricated-exception,
  `os._exit(1)` or forged-`[FAIL]` instances. ⛔ They are unverified here — I am not endorsing them,
  and M9 is about the provenance gap, not about the claims being wrong.
* **The pre-0.33.0 hook length** (M8). Only `0.33.0` is cached; no earlier copy exists on this
  machine and a vendored cache has no history. "Grew by a thousand lines" is neither confirmed nor
  refuted — it is unmeasurable from here, which is the point.
* **`check-withdrawal`'s actual glob** (M4). The script is not in this repo at this commit, so the
  assertion about what it can and cannot see could not be exercised; only its absence was measured.
* **First-run behaviour of the real session-start hook against the live `.remember/`.** Deliberately
  not executed. It writes a delivery record and would mark the user's pending handoff as delivered,
  which could suppress it for their next real session. Substituted a faithful replica (temp `HOME`,
  temp project, real plugin root) plus the read-only `doctor.sh` report. ⚠ Stated rather than hidden:
  the replica shares the plugin and the interpreter but not the live store, so it is evidence about
  the resolution logic, not about this store's contents — which is why the three-layer file check and
  the `ls` of `.remember/` carry that half instead.

---

## Instruments

**Worktree:** `…/scratchpad/wt-plugins` @ `55975f92`. No `git` write command was issued anywhere, and
nothing in the main checkout was touched. Only file written: this document.

**1. The hook probe (B1, SOUND #1, SOUND #6).** Isolated tree at `…/scratchpad/hookprobe`:
`HOME=<temp>`, `CLAUDE_PROJECT_DIR=<temp>/proj`, `CLAUDE_PLUGIN_ROOT=<real 0.33.0>`, payload on stdin.
Three runs varying only `.handoff_mode` (written to `<temp>/proj/.remember/config.json`) and
`session_id`. Run C transcript is quoted verbatim in B1; the table there is the full result set. Known
positive before trusting the negative: run B proves the probe can produce a per-session path, so run
A's silence is a measurement and not a broken harness.

**2. The refusal render (SOUND #2, M6).** Replica at `…/scratchpad/refusal`: the hook copied into
`<temp>/.claude/hooks/`, a 2-line Python stub at `<temp>/scripts/check-handoff-path.py` printing a
recognisable verdict and exiting 1, driven with
`{"tool_name":"Skill","tool_input":{"skill":"mattpocock:handoff"}}` and
`TMPDIR=SENTINEL_TMPDIR EDITOR=SENTINEL_EDITOR`. Result: rc=2, stdout empty, stderr 27 lines,
`grep SENTINEL` → no match. The stub is what makes this a render of the *blocked* path rather than the
happy one.

**3. Site inventory (H1).** Filesystem greps, not `git grep`, over `docs/ scripts/ .claude/ .agents/`
for `session-start-hook`, `REMEMBER_HANDOFF`, `\.remember/remember\.md`, and
`:(795|809-812|814-825|800-802)`. Tracking confirmed with `git ls-files` + `git check-ignore`; origin
with `git log -S` on two files independently; the symlink with `ls -l`.

**4. Guard sweep (CANNOT RUN).** Invocation list extracted from `ci.yml` by grep, then each run and
its rc logged to `…/scratchpad/docs-r1/guards.log`.
⚠ **The first sweep was void and said so loudly:** I wrapped each call in `timeout`, which macOS does
not ship, and all 57 returned **rc=127** — 57 identical "failures" with one cause. Re-run without the
wrapper. Recording it because a sweep that reds everything is the shape that gets believed.
⚠ `check-plan-code.py` with no argument (rc=2, "CANNOT RUN — nothing to do … Plan mode was RETIRED")
is an **artefact of my extraction**, which drops arguments; CI runs it as `--mutate .`. Not a branch
defect, and not counted among the six.
⚠ One near-miss worth recording: my first direct run of `check-paid-caller-arrival.py --self-test`
was piped to `tail`, and I read `$?` from the pipe — **rc=0 over a suite that had failed 20 cases**.
Re-run unpiped to a file for the real rc=1.

**5. Mutation anchors (SOUND #4).** All of `scripts/mutations/*.json` parsed; every `edits[][0]`
substring-tested against its `file` on disk. 1,416 / 0.

**6. Arithmetic (M2, M8).** Third boundaries and deltas computed, not estimated.

**⚠ Contamination to declare, because the halves are meant to be independent.** The Codex half had
already filed `docs/reviews/codex/plugins-handoff-citations-r1-codex.md` into this worktree before I
ran instrument 3, and my repo-wide grep for the stale-number pattern **matched inside it**, so three
of its bullets appeared in my terminal. H1 and M2 were already derived at that point (H1 from the
`session-start-hook` grep one step earlier; M2 from my own arithmetic), and I have not opened the
file. But I cannot claim M3 is fully uncontaminated: its line was among the three I saw, and although
I read `velocity-177-r5-claude.md:145-175` myself and quote it here, I may have been primed. Flagging
it rather than quietly presenting four findings as independent. **I did not read the Codex half.**

**7. Round-gate re-verification, after writing this file** (appended to `guards.log`):
`check-review-rounds.py` **1 → 0**, so `docs/reviews/claude/plugins-handoff-citations-r1-claude.md`
is the basename and directory the round-1 pairing wants. `check-docs.py` still **0**.
`check-review-recorded.py` still **1**, and that is the honest result, not a stale reading — it reads
the committed tree and both halves are uncommitted. ⛔ I did not commit anything.
