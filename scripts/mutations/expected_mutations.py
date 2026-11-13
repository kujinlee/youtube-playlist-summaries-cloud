# THE MUTATION PINS — DATA. This file is never imported and never executed (backlog #533).
#
# `scripts/check-plan-code.py` reads it with `pin_display`, which parses the ONE module-level
# `EXPECTED_MUTATIONS = {...}` display below with `ast` and accepts only string keys and int values.
# `scripts/check-merge-ready.py` reads it the same way, at the merge base and at the head, and HOLDS
# a pin that falls. Any other statement in this file is ignored, never run. A second assignment to the
# name, a computed value, a duplicate key, or a missing file is refused (CANNOT RUN), never read as {}.
#
# ⟳ 2026-11-06, backlog #533: the pins MOVED HERE from `check-plan-code.py`, each with the history
# comment that stood beside it. Nearly every PR that adds or retires a mutation bumps a pin, and while
# the pins lived inside the sweep harness every bump was a harness change, so CI swept the WHOLE
# manifest (18 shards). Measured 2026-11-06 on PR #516, PR #522, PR #524 and PR #525: four of five PRs went full
# only for a pin bump, about 90 shard-jobs where about 23 were needed. This file is NOT a harness file.
# `select_manifests` treats a change to it like any other path under `scripts/`: it selects the targets
# that name it or read its directory, and the changed manifest beside it selects its own target. A pin
# that disagrees with its manifest is still refused in EVERY shard by `pin_drift`, which reads every
# manifest whatever the selection.

# How many mutations each delivered script is covered by. EXACT, not a floor: adding a
# mutation should also be a visible act, and a floor drifts downward the moment somebody
# adds one without saying so.
#
# ⚠ This lives in the RUNNER, deliberately, not in the manifest. A count stored beside the
# entries it counts gets edited in the same breath as deleting one, which is no guard at all.
# ⟳ 2026-11-06, backlog #533: it no longer lives in the runner, and it is still not in a manifest.
# What the paragraph above guarded against — a pin lowered in the same breath as its entries — is
# now caught at merge by `check-merge-ready.py`, which HOLDS a pin that falls between the merge base
# and the head (backlog #359). This file is separate from every manifest, so the old reason holds.
#
# ⛔ backlog #359: THERE IS NO TYPED TOTAL. `declared_total()` derives it from these pins, so a
# change records the PER-FILE move and its reason, never a "declared sum A -> B" — the sum
# transitions in the comments below are history from when a literal pinned it, and every pair of
# open PRs that added a mutation collided on that one line.
EXPECTED_MUTATIONS = {
    # ⟳ 2026-08-30, backlog #71: gen-dashboard 61 -> 49. TWELVE entries did not disappear, they
    # MOVED to scripts/page_markup.py with the code they guard. The sum below is unchanged at 73,
    # which is the point — a seam that relocates coverage must not be able to look like coverage
    # that was deleted, and only the per-file split can tell those two apart.
    # ⟳ 2026-08-30, backlog #74: this file joins the manifest. It is 1,696 lines, every mutation
    # verdict in the project passes through it, and it was the ONLY member of the stack with
    # cases and no mutations — the layer nothing checked back. Adding it found THREE guards whose
    # deletion left the suite green: the after-sequence control, the duplicate-anchor refusal,
    # and `check()`'s redirected-home mkdir. Not circular — the orchestrating process is this
    # copy, the mutated target is the temp copy, and the nested spawn inherits `child_env`.
    # ⟳ 2026-08-31, ask-choices slice: gen-dashboard 47 -> 56, check-dashboard-entry
    # 12 -> 18. The new entries cover the derived badge, the malformed-ask tray row,
    # the cleared-entry exemption, the Worth-knowing NOT-CHECKED branch, the PR token
    # and its budget, gh shape validation, and — on the gate — the decision grammar
    # including the NESTING rule, whose absence silently dropped every option after a
    # 4-space nest.
    # ⟳ 2026-09-01, the block-start divergence: gen-dashboard 67 -> 68. The ENTRY
    # GATE's count does NOT move in the same change, and the asymmetry is the point.
    # `BLOCK` RELOCATED into check-dashboard-entry.py, so its existing mutation was
    # retargeted there (a retarget, not an addition — same count, 29); what is NEW
    # is a mutation on the seam itself, restoring the page's private copy of the
    # rule. That copy is what the defect WAS, and scanning the manifest to repair
    # the orphaned anchor showed the page's `BLOCK` had never had a mutation at all
    # — the regex at the centre of the bug was the one thing nothing measured.
    # ⟳ 70 -> 73, comprehensibility slice A (backlog #83). THREE entries, one per new
    # behaviour: the settled class, the settled CSS, the resolver back-reference. Each
    # names the case it must go red through, so a mutation caught by a SIBLING case
    # cannot be credited — the round-5 M1 defect where `expect` matched 7 case names.
    # ⟳ 2026-09-06, backlog #96: this guard joins the manifest — one of the 23 R4 debts,
    # paid down here because the slice rewrote its decision path. MANIFEST_BASELINE in
    # check-ratchet-contract.py drops 23 -> 22 in the SAME commit, which R4 requires as an
    # EXACT match: paying a debt down fails the gate until the constant follows.
    # ⟳ 2026-09-06, backlog #97: 7 -> 8. The new entry guards the OBSERVATION LINE'S CONTENT,
    # not whether a line appeared. Found by the Codex half of code review r1: `flush_line`
    # rewritten to a constant string passed 94/94, because the F11 cases counted lines and never
    # read one. The counts ARE the evidence, so a line that has lost them records that something
    # happened while destroying what was measured — the recorded *a guard's own output is a
    # CONTRACT* shape, one layer in from the log-format defect this whole slice is about.
    # ⟳ 2026-10-16: check-claim-propagation.py joins the manifest at 10, raising the declared
    # sum by 10. It is the mechanical half of `one-rule-one-place` for documents, built after
    # two adversarial rounds on `marketplace-inventory` produced 4 then 14 fix-induced findings
    # with ONE mechanism behind thirteen of them: a rule stated in several places, and the fold
    # updating the site the finding named. A convention had already failed at it twice in two
    # rounds, which is why this is a guard and not a checklist.
    # ⟳ 2026-10-17, ADR-0015: 32 -> 15. ⛔ THIS IS A RATCHET FALL, which is permitted ONLY when
    # the entries are RETIRED WITH THEIR SUBJECT, and that is what these are: the prose-matching
    # half of the guard is deleted, so the retired anchors name code that no longer exists.
    # ⟳⟳ 2026-10-17, r5 CODEX Low: the count here said **19** and the arithmetic did not close —
    # 32 - 19 is 13, not 15. The real figure is **17 retired**, and 19 was the INTERMEDIATE value
    # from the first pass, before two entries were restored as retargets. ⭐ It is now DERIVED by
    # diffing the manifest against `8a583f7c^` rather than retyped, which is the only form of this
    # number that cannot drift: 32 before, 15 after, 4 retargeted, 32 - 17 = 15. Precedent and
    # shape are `retire-plan-mode` (44 -> 23, declared sum 392 -> 371), where 20 anchors stopped
    # resolving because the code they named was gone.
    # ⚠ FOUR WERE RETARGETED RATHER THAN RETIRED, and checking that was the point: their anchors
    # broke while the RULES they measure survived — the empty-registry refusal (its condition went
    # from a three-way disjunction to one), the `wanted |= …DERIVED…` line (now the FIRST
    # assignment, so the witness is stronger), the `audited_sites` witness (its token half retired,
    # its DERIVED half kept) and the self-closing-not-pushed rule in `_Carriers`. Retiring those
    # four would have dropped live coverage silently, which is this repo's recorded failure mode
    # for exactly this operation.
    # ⟳⟳ 2026-10-17, r5 CODEX M3: 15 -> 18. Three surviving branches of `_Carriers` that no
    # case pinned — stripped accumulation, the VOID vocabulary beyond `img`, and an unmatched
    # end tag. The reviewer found them by applying each mutation and getting 41/41 GREEN.
    # ⟳⟳⟳ 2026-10-17, r5 CLAUDE H1 — THE VOID VOCABULARY, as opposed to six of its fourteen
    # members. The comment on the previous case asserted it covered the set; the code supplied a
    # hardcoded 6-tuple and dropping all 8 unpinned members was 49/49 GREEN.
    # ⟳ r6 CODEX Low: THIS COMMENT SAID `18 -> 19` AND NO NINETEENTH MUTATION EXISTS. The fix
    # EXTENDED an existing entry's `expect` list, because the harness refused a second entry on
    # the same anchor as measuring nothing new — so the count did not move, and the arithmetic
    # comment below correctly says `18 -> 18`. ⚠ The executable count is right; the audit trail
    # was wrong, in the one number this round was asked to verify. Corrected, not raised.
    "scripts/check-claim-propagation.py": 18,
    "scripts/check-anchors.py": 5,
    "scripts/check-arch-findings.py": 5,
    # ⟳ 2026-09-22, the third warning class: 8 -> 22. THREE of the eight are not about the new
    # branch's rules at all but about it being WIRED and LABELLED — `run_decide` ceasing to count
    # the turn, the log re-deriving the class from its output, and the class reporting its
    # sibling's reason. That split is deliberate: the two older classes shipped with their rules
    # covered and their wiring not, and the comment on H3 in the suite records three log mutations
    # surviving on exactly that gap. The threshold entry is the fourth of that kind — every other
    # case derives _BIG/_SMALL from LARGE_TURN and so moves with it, leaving the calibrated value
    # unfalsifiable until one case pinned it as a literal.
    # ⟳ 2026-09-23, backlog #166 + #170 — A SANCTIONED RATCHET FALL, and the only kind there is.
    # ⟳⟳ r2 M1 REWROTE THIS ACCOUNT, because it was off by one entry and mislabelled another. It
    # said "THREE anchors stopped resolving" and listed five; **SIX entry names left the three
    # adapters and three arrived**, and the sixth was unaccounted for. The count is now DERIVED
    # rather than recalled — `git show origin/master:scripts/mutations/<f>.json` against the branch
    # copy, names diffed as sets — and every removal is in exactly ONE of the three classes below.
    #
    #   ⑴ RETIRED WITH THEIR SUBJECT — 3. The code they name is GONE, moved into
    #     `scripts/observer_log.py` with the record grammar, and each property is mutation-covered
    #     in its new home. This is the only sanctioned kind of fall:
    #       ci      fields stop being sanitised  -> observer_log "col stops removing the TAB"
    #       ci      sanitiser empties the field  -> observer_log "col strips a TAB" + content
    #       closing empty-session fallback       -> observer_log "the EMPTY sentinel is blanked"
    #
    #   ⑵ RENAMED AND RETARGETED, NOT RETIRED — 2, so they appear in BOTH the removed and the
    #     added set and net to zero. ⛔ THEY WERE BRIEFLY IN CLASS ⑴ AND THAT WAS WRONG (r1 Codex,
    #     round 2 on the folded tree):
    #       banner  flush_line freezes session   -> NOT covered by "record puts `session` third"
    #       banner  flush_line freezes timestamp -> NOT covered by "record puts `when` second"
    #     Those cases prove `record()` PRESERVES arguments it is GIVEN; they say nothing about
    #     whether the ADAPTER passes its own through. Measured with mutant adapters: the
    #     observer_log cases stayed true while the adapter property failed.
    #
    #   ⑶ REPLACED BY A DIFFERENT PROPERTY — 1, and THIS IS THE ONE THE OLD ACCOUNT LOST. ci's
    #     *"the log line drops its SESSION column, so entries stop being attributable"* became
    #     *"the log line drops a PAYLOAD column, so a record loses a field"*. Calling that a
    #     retarget was loose: the old property is *this adapter passes `session` through*, the new
    #     one is *this adapter emits its payload fields*, and they are different claims. The reason
    #     the swap is correct is that `session` is now the shared module's POSITIONAL 3, so what
    #     remains the adapter's own is its payload; the reason it needed saying is that the
    #     passthrough property still exists and still needs an owner — which is ⑵'s whole lesson,
    #     accepted for `flush_line` and then not searched for over its two siblings.
    #
    # ⭐ **SO THE SEARCH WAS RUN, AND IT CLOSES THE CLASS** (r2 M1): neither `check-ci-watched`'s
    # nor `check-closing-table`'s `log_line` had a session- or timestamp-passthrough entry. FOUR
    # were added (ci 27 -> 29, closing 46 -> 48), each MEASURED first by freezing the argument in
    # the delivered adapter and reading which named case went red — 49/57, 56/57, and two clean
    # closing-table failures. The properties were never uncovered; the RATCHET is what proves the
    # cases can fail, and for two of three adapters nothing held it.
    #
    # Net: banner 47->47, ci 29->29, closing 47->48, +16 for the new owner. ⚠ THIS LINE PREVIOUSLY
    # READ `47->45 … +14` — the pre-withdrawal numbers — for three commits after the withdrawal
    # above it. r2 B1: the correction had landed in the COMMIT MESSAGE and not in the file, and a
    # justification that disagrees with its own pins is not a justification.
    # Every surviving anchor was re-verified to resolve exactly once AFTER the code was final.
    # ⟳ r3 M4, 2026-09-23: 47 -> 48. The fold rewired this file's WARN write to
    # `observer_log.append_or_raise` and ratcheted NOTHING at the new call site — it applied *the
    # ratchet is what proves the cases can fail* to the passthrough properties it found missing, and
    # not to the delegation it introduced in the same commit. Measured: neutering the call reds 9
    # named cases, no crash.
    # ⟳ 2026-10-22: 48 -> 64, the THREAD class (`unarmed-thread`). Sixteen entries, one per
    # firing branch and per quiet rule, every `expect` read from a real run of the mutant. ⚠ The
    # seventeenth — deleting the hook's `BANNER_RC == 4 -> exit 2` mapping — is NOT here: a
    # manifest's entries must all target the manifest's own file, and the hook is shell. F6d
    # covers it structurally; nothing mutates it.
    # ⟳ same day, 64 -> 65: BANNER_RE itself now accepts the `[mm-dd hh:mm]` stamp, so the
    # thread class's private copy `STEP_BANNER_RE` is gone and its entry is RETIRED WITH ITS
    # SUBJECT (-1). Two entries pin the one pattern instead (+2): reverting it to the unstamped
    # form (the 2026-10-16 blindness, killed by an ORIGINAL class's stamped case) and making the
    # stamp mandatory (killed by the unstamped cases). The fence-skip entry was RE-ANCHORED from
    # `STEP_BANNER_RE` to `BANNER_RE`, not retired — its subject still exists.
    # ⟳ r1 fold, same day, 65 -> 77: the thread class was REDESIGNED by the coordinator's
    # decision (compare against `.claude/plans/` files, read the real row shapes, rows only under
    # a banner, CommonMark fence closing). The 15 `thread class:` entries were removed and 27
    # added. ⟳ r2 Codex 5 — CORRECTED: that is NOT "all 15 retired with their subject". Only the
    # sentinel comparison and the journalled slug were deleted; BLOCK, last-row selection, fence
    # exclusion and unreadable-is-quiet SURVIVED, and their entries were REWRITTEN against the new
    # code under new names, not retired. Net +12 either way. The two BANNER_RE entries were kept.
    # ⟳ r2 fold, 77 -> 87. Six entries lost their anchors to this round's rewrites: FIVE were
    # RE-ANCHORED to the same property in the new code (`SWITCHED to plan`, guessing between two
    # destinations, the `switched` label, run_decide ignoring THREAD_BLOCK, run_decide dropping the
    # known set), and ONE was RETIRED WITH ITS SUBJECT — the r1 suppression is gone (Codex 3), and
    # its replacement entry asserts the opposite: re-introducing the suppression is killed. Eleven
    # are new: precedence (explicit > `plan` > leading, conflicts unreadable), the `also=` field and
    # its wiring, the every-checkout union, its notes and its CANNOT RUN. Net -6 +16 = +10.
    # ⟳ r3 fold, 87 -> 91. Four entries lost their anchors and were RE-ANCHORED to the same
    # property in the new code (`SWITCHED to plan`, the dropped known set, the r1 suppression —
    # now expressed at the log step, since the thread check runs BEFORE decide() — and the
    # leading-slug arrow). Four are new: an arrow in prose is not a destination (r3 F7, two
    # entries), a turn with no saved record is still judged (F1), and the partial-read notes reach
    # the warning (F6). Net +4.
    # ⟳ 94 -> 100 (backlog #331(a) / #357, PR #440 r1): the CANNOT RUN refusals for a corrupt, undecodable or
    # non-object input. ⟳ 100 -> 97 (PR #440 r2): the payload and transcript READ moved to `bounded_read.py`, so
    # six entries on `transcript_lines` and the stdin read retire with their subject (re-entered in that file's
    # manifest) and three are new — the bounded stdin read, the reader's refusal dropped at the turn rule, and the
    # turn filter's own refusal.
    # ⟳ 97 -> 98 (PR #440 r3 C4): the CANNOT RUN message must carry the reader's reason.
    "scripts/check-banner-armed.py": 98,
    # ⟳ PR #440 r2: THE ONE bounded reader for the five guards' untrusted input, pinned in the commit that creates
    # it. Two of its entries moved here from `check-ci-watched` with the stdin read; the rest are the r1/r2 classes.
    # ⟳ 22 -> 29 (PR #440 r3): the stdin bound's VALUES and exact-cap edge (C3, four), the non-regular refusal's
    # NAME (C4), and the `--stdin` mode the registered Stop hook now reads its payload through (C5, two).
    "scripts/bounded_read.py": 29,
    # ⟳ 2026-09-23, backlog #166 + #170. The ONE owner of the observer-log record. Pinned in
    # the commit that creates it, with its manifest — `check-ratchet-contract` REFUSED the
    # module until both existed (R4W_no_mutation_manifest), which is the contract working on
    # a file minutes old. ⭐ Mutation 2 is the load-bearing one: it swaps `splitlines()` for
    # `split("\n")`, which is the EXACT historical defect one file over — a hand-written line
    # rule that covered 2 of the 11 characters `splitlines()` honours.
    # ⟳ r1 HIGH 4, same day: 14 -> 15. The review measured that the retired R5-646c property
    # (a frozen `when` column) had NO replacement mutation and no case that could fail —
    # `record defaults `when` to now()` asserted `!= ""`, which `col(x) or EMPTY` can never
    # be. A case and a mutation were both added. A RISE needs a reason as much as a fall.
    # ⟳ r3 H1 + M2, same day: 16 -> 19. THREE entries, all on lines this round changed:
    #   * `encoding=` deleted from `append_or_raise` — ⛔ THE DOCSTRING SAID THIS COULD NOT BE
    #     COVERED. r3 H1 refuted that by building the case: the locale default is an INPUT fixed
    #     before interpreter start, so a child under `LC_ALL=C` reports US-ASCII and the missing
    #     argument raises. A self-authored exemption sitting in the one line the whole consolidation
    #     concentrates value into.
    #   * the whitespace-only guard in `col` reverted — r3 M2, the sentinel was DEFEATED for this
    #     grammar's own primary separator (`SEP` becomes a space, and a space is truthy).
    #   * that guard returning `out.strip()` instead of TESTING it — the fix's cheapest wrong form,
    #     which every other case passes.
    # ⟳ r2 H3, same day: 15 -> 16. M9 was fixed as an INSTANCE — one hand-rolled write delegated,
    # `encoding=` hand-added to a second — and TWO hand-rolled writes stayed in the tree, each with
    # its own `mkdir` + `open`. The API forced that: `append` returns a bool and two callers need
    # `{e}`. `append_or_raise` is the class fix, and the new entry is the FAIL-OPEN direction on it
    # (it swallows the error itself, so no caller can report one). ⚠ TWO EXISTING ANCHORS WERE
    # RETARGETED, NOT RETIRED: the write body moved from `append`'s `try:` to module indent, so
    # `append truncates` and `append stops creating missing parents` bound to 8-space text that no
    # longer exists — a silent orphan of exactly the kind this repo has paid for seven times in one
    # session. Both re-verified to resolve exactly once AFTER the code was final.
    "scripts/observer_log.py": 19,
    # ⟳ 2026-09-07, R4 manifest debt 8 -> 7. FIVE of the seven cover rules the 15 shipped cases
    # already asserted; the other two are the gaps writing them found, and both are the same
    # shape — a claim about coverage that nothing executed:
    #   * `_moved_problems_for`'s unreadable-harness branch was driven by NO case, so `return []`
    #     in its place was a fail-open. "Cannot run" reported as clean is the failure this repo
    #     has now paid for four times, and it was sitting inside the script whose entire purpose
    #     is to stop "covered elsewhere" claims going unverified.
    #   * the ACL regex is written TWICE (EXCLUDED and MOVED_COVERAGE) and nothing checked the
    #     two agree. The case that looked like it did — `any("relacl" in pat …)` — is a SUBSTRING
    #     test on the pattern text, so either copy could narrow while it stayed green.
    "scripts/check-catalog-coverage.py": 7,
    # ⟳ 2026-09-20, the closing-table guard. Ten entries, and the one that earned the file is
    # "an unreadable transcript passes quietly" — the fail-open direction, which is the failure
    # this repo has now paid for more than four times. Two others exist only because writing the
    # suite found the defects: `relative_to` raising on a redirected log (a warn-only observer
    # turning into a traceback), and judging the LIVE turn instead of the previous one, which
    # would have made the guard silently unable to see any closing message at all.
    # ⟳ r2 M1, 2026-09-23: 46 -> 48, the same two passthrough entries as its ci sibling, and for
    # the same reason — the search Codex's `flush_line` Blocking implied was never run over the
    # other two adapters. Measured first: freezing session reds *log: the session is the THIRD
    # field, verbatim*, freezing `when` reds *log: the timestamp is the SECOND field*.
    # ⟳ 49 -> 51 (backlog #331(a) / #357, PR #440 r1): the CANNOT RUN refusals for a corrupt, undecodable or
    # non-object input. PR #440 r2: both retargeted onto `bounded_read`, the count unchanged.
    # ⟳ 51 -> 52 (PR #440 r3 C4): the CANNOT RUN message must carry the reader's reason.
    "scripts/check-closing-table.py": 52,
    # ⟳ 2026-11-03, backlog #470: 68 -> 70. the PR option link through key_link, and its un-nested text (+2).
    "scripts/gen-dashboard.py": 70,
    # ⟳ 2026-09-12. gen-goals-page.py was the last PAGE-PRODUCING generator with no
    # manifest — gen-dashboard, gen-backlog-page, brief-compose, page_chrome and page_markup
    # all had one. ⚠ IT WAS NOT "the ONE generator with no manifest", which both round-1
    # halves flagged and round 2 repeated: `scripts/gen-m4-manifest.py` has none either and
    # is still outside `scripts/mutations/`. The narrower sentence is the true one; the wider
    # one made a reader sizing manifest debt from this dict believe the class was closed.
    # The gap predates the work-threads branch, but that branch added 532 lines to it (`git
    # show --numstat 58d82658`), making it the largest unmutated surface of its kind here.
    # ⚠ NOT "~540 lines of new rules", which stood here for three rounds: 540 is `--stat`'s
    # CHANGED-line total (532 insertions + 8 deletions), read as if it were insertions.
    # ⟳ 2026-09-12, review rounds 1 and 2: 14 -> 25. ⚠ AN EARLIER VERSION OF THIS PARAGRAPH CITED A
    # MEASUREMENT NO COMMITTED ARTIFACT CONTAINS — "Claude staged the tree, applied 24
    # candidate weakenings and measured 11 SURVIVING" — and used it as the justification for
    # this number. TWO agents wrote to one review path and the later overwrote the earlier;
    # the coordinator committed the survivor without re-reading it and wrote the commit
    # message from the lost one. The surviving `docs/reviews/claude/goal-page-mutations-r1-
    # claude.md` says nothing of the kind, and its High is `parse_adr`, not the seam.
    # WHAT IS ON THE RECORD: the CANNOT-RUN producer being unnamed is CODEX's round-1 High
    # (`docs/reviews/codex/goal-page-mutations-r1-codex.md`), independently reproduced by the
    # coordinator before any code changed. `git_pr_history` and `git_show_files` had no seam, so
    # every rule inside them was unreachable from any case and a mutation on one would have
    # survived. Their absence from the first fourteen was untestability, not completeness —
    # and `git_pr_history` returning None is the ONLY thing in that file that can set
    # `pr_error`, which TWO of those fourteen entries already defended downstream of (a third
    # defends the same None-IS-NOT-False discipline, but through `git_show_files`, not this
    # sentinel — the earlier "three" bound that count to `pr_error` and was wrong under its
    # own grammar).
    # The other two close unfalsifiable fixtures: a `tag` class the case matched but never
    # captured, and a fan-out threshold whose boundary value was absent from the fixture.
    # ⟳ 2026-10-22: 15 -> 16, the Refresh button.
    # ⟳ 2026-10-22 (work-lines backfill): 16 -> 21 — a reconstructed link is read only under a
    # parent, drawn distinctly, explained by the caveat, labelled on a started line, and escaped.
    # ⟳ 2026-10-22, backlog option A for banners: 21 -> 24 — the third link kind (drawn,
    # tooltip, caveat).
    # ⟳ 2026-10-22, banner-thread-armed r2 fold, 16 -> 23: `plan_dirs` (every checkout's plans,
    # owner's decision option A) and the union `read_plans_noted`. Seven entries, one per branch —
    # git's order kept, a missing checkout named, the git fallback named, the union itself,
    # duplicate slugs labelled, a duplicated parent re-pointed at the child's own checkout, and
    # the page showing its notes — every `expect` read from a real `git worktree add` run.
    # ⟳ r3 fold, 23 -> 28. The missing-checkout entry is RETIRED WITH ITS SUBJECT — the rule
    # inverted (r3 F2: a gone folder is skipped SILENTLY), and a new entry re-adds the note and is
    # killed. Two were RE-ANCHORED (differing copies labelled; the parent resolver, now `row_for`).
    # Six are new: byte-identical copies collapse (F4), short labels, the not-listed directory's
    # label (F6), another checkout's unreadable plans named (F6), and inherited GIT_* dropped.
    # Net -1 +6 = +5.
    # ⟳ r4 fold, 28 -> 28: the byte-identical collapse was REMOVED (r4 Codex, Major — it merged
    # children of different parents), and its ONE entry is RETIRED WITH THE CODE. Two entries were
    # RE-ANCHORED to the replacement loop (copies labelled; short labels). ONE is new: it
    # RE-INTRODUCES a collapse and is killed by WT10, Codex's own fixture. Net -1 +1 = 0.
    # ⟳ r6 fold, 28 -> 30: identity is now the KEY `(checkout, slug)` (r6 Codex, Major — the
    # display label was the dict key, so a file NAMED `kid @ main.md` overwrote the generated label
    # and an unfinished plan vanished). Four entries lost their anchors to the re-keying and were
    # RE-ANCHORED to the same property (dangling parent, cycle cut, the asking checkout in
    # `row_for`, the checkout label); two are NEW: `build_forest` re-keyed by label (killed by
    # WT11, Codex's fixture) and `row_for` returning a label. Net +2.
    # ⟳ 2026-10-23, merging master (PR #386) into the backfill: 24 + 14 = 38 — both
    # branches' entries kept, none retired; the render line now prints `label(n)`.
    # ⟳ backlog #389: 38 -> 25 — the PAGE retired, the plan reader stays. Fourteen entries RETIRE with
    # the renderer they pinned (sort order, badge, escaping x3, open-line count, Refresh button, the
    # three link kinds and their caveats, the not-read notes); one new pins the retired main's exit 2.
    "scripts/gen-work-lines.py": 25,
    # ⟳ 2026-10-28, backlog #363: the logged goal tree joins at 25 — one entry per refusal in the
    # threads grammar, per derived-state rule (merged first, CANNOT RUN, closed, the subject tail),
    # per log rule (fingerprint, incomplete refused), per exit code, and the page's ordering and links.
    # ⟳ same day, the 03:52 follow-up: 25 -> 36 — NEEDS YOU (the answered/last-marker/closed rule,
    # unreadable entries and lines named, the main checkout's ledger, NOT READ is not an all-clear, the
    # live list over the snapshot's) and the log moved to the main checkout's git-ignored .claude/.
    # One RETIRED with its subject: the hand-rolled `--git-common-dir` read became
    # `session-state.main_checkout`, whose refusal the new no-main-checkout entry now pins; and one
    # for the backlog title escaped twice, found on the real page. Net +11.
    # ⟳ same day, round-1 fold (PR #433): 36 -> 50 — two retired with their subject (unreadable records
    # are no longer items but a NOT READ source, X1), sixteen new: X1 per source, X2 consolidation and its
    # two refusals plus the caller's items untouched, X4 actions, C4 stated-or-several, C2 the flag
    # (and a `PR #N` in the tail is not a row, found on the real backlog).
    # ⟳ round-2 REDESIGN to structure: 51 -> 55 — six RETIRED with the free-text heuristics they pinned
    # (row-mention consolidation x3, the plural/count cues x2, the bare-#N row reading), ten new: the
    # explicit identity (two-token refusal, kind in the key, ledger and dashboard declarations), each
    # source keeping its count, conflicting counts flagged, the `(answers-open: N)` annotation x2,
    # `backlog #N` alone for the flag, and the page saying it replays a snapshot.
    # ⟳ round-3 fold (architecture review SPLIT): 55 -> 59 — the dashboard-identity entry re-anchored on
    # the whole-entry rewrite; four new: a disagreeing identity token is a conflict, not the identity (Z1),
    # and the count is read from the whole entry — display text, dashboard body, ledger text (Z2).
    # ⟳ round-4 (terminal) fold: 59 -> 64 — a declared 0 kept, compared and shown, in text and HTML (W2).
    # ⟳ backlog #389 (work-lines retired into the goal tree): 64 -> 71 — the absorbed plan list (only
    # owing plans, newest first, progress in the timeline), plans NOT READ vs a missing directory, and
    # the link to the frozen archive, and a vanished parent named rather than dropped.
    # ⟳ #389 round-1 fold: 72 -> 75 — a worktree's plans still read when the main checkout has no
    # .claude/plans/ (X3), and plans keyed by (checkout, slug) in the snapshot and timeline (X4, x2); the
    # missing-directory entry re-anchored on the rewrite.
    # ⟳ backlog #484: 75 -> 83 — a SUPERSEDED / WITHDRAWN Status cell beats the merge state: read at all,
    # its own forward pointer, the ✅-only negative, the title is not the Status cell, SUPERSEDED beats
    # WITHDRAWN, and an unread or partly unread backlog is CANNOT RUN, never ✅.
    # ⟳ backlog #484 round-1 fold: 83 -> 102 — the fate is read only from a MARKER (r1 H1/M1: six entries
    # replaced by fourteen on the marker grammar, pointer, code span, `Previously:`, emphasis glyph, bold and
    # the Items table), plus each ref's own state (r1 M2/M3, Codex 4: ten) and a missing row (Codex 3).
    # ⟳ backlog #484 round-2 fold: 102 -> 112 — code spans by matching backtick runs, the cut at the FIRST
    # `Previously:` and its order after the strip (r2 X1/X2: four), a fate beside an unlisted PR (r2 X3),
    # and a later bold REOPENED cancelling a marker (r2 note: five). Five r1 entries were re-anchored.
    # ⟳ 2026-11-03, backlog #470: 112 -> 115. the PR-href mutation moved to page_markup.json (-1); four thread-id mutations (+4).
    # ⟳ 2026-11-04, backlog #497: 115 -> 130 — merge time (blank/unread, zone, latest-of-several, git and gh reads: 5),
    # the buckets (48 h edge, unread age, parked: 3), parked not in flight and landed-parked grouping (2), and the
    # folds (nothing folds, text lists leaves, goal not folded, fold drawn open, page bucketed at snapshot time: 5).
    # ⟳ same day, the owner's 01:14 request (numbered goal blocks): 130 -> 135 — numbering origin, the text's
    # number, anchors on past trees, the folded goal's heading, the heading colour.
    # ⟳ same day, review round 1's fold: 135 -> 150 — in-flight work lifts a landed thread, PR mentions in text,
    # the title-resolved PR (X1: 3), mergedAt first on both paths (X2: 2), numbering by time and slug anchors
    # (X3: 2), queued fix/blocker and the later wording (C2: 2), negation and clause-leading `parked` (C3: 2),
    # --ink-soft on the fold summary and counts (C5: 2), and the closed PR's age (C6: 2).
    # ⟳ same day, review round 2's fold: 150 -> 152 — recency judged across EVERY ref, not the aggregate's time,
    # and an unread ref time never folds (X1: 2).
    # ⟳ 2026-11-06, backlog #504 r3 fold: 312 -> 314 — a lone CR ends a line for reader and writers alike (N1),
    # and the blank repair's blank is the reader's (N2); four blank-repair entries re-anchored onto the rewrite.
    # ⟳ 2026-11-06, merging master (backlog #518, PR #516: 298 -> 300) into backlog #504: 316, the merged manifest's count.
    # ⟳ 2026-11-06, backlog #496: 316 -> 325 — a decision recorded in prose after the NEEDS-OWNER marker is flagged
    # (clause 1 only: own words, after the marker, upper case, both phrases, negation x3, `not yet`, over a
    # cross-reference). The r1-r3 history reader (clause 2) was built, measured, and REMOVED in the r4 fold
    # (Phase 6 review): its 25 entries went with it, so this branch adds 9 net.
    # ⟳ 2026-11-07, backlog #406 (suite cost): 325 -> 327 — the sibling import loses its memo, and its key loses the
    # file stamp (a rewritten sibling served stale).
    # ⟳ 2026-11-08, PR #537 round 1's fold: 327 -> 333, none retired; the two above RE-BOUND to the new key (the memo
    # never consulted; a hit that checks nothing). Six new: the hit skips the sibling's own bytes, never keys the files its
    # import loaded, the audit hook not installed, the hook blind to `open`, the real pycache_prefix kept (a stale
    # .pyc), and the memo keyed on the name instead of the path.
    # ⟳ 2026-11-08, PR #537 round 3 fold (Phase 6, architecture-review-2026-11-08-goal-tree-sibling-cache): 337 -> 336.
    # The cache was REDESIGNED: it lives only inside `_sibling_sweep()` (the self-test), so the audit hook, the
    # read-list stack, the lock and the bytecode-settings swap are gone, and so are their 12 mutations. Eleven replace
    # them, each on the new code: the memo never consulted / never stored; ON by default; keyed on the name; the
    # sibling read through its .pyc; compiled under goal-tree's `from __future__` flags; the sweep restore out of
    # finally / never run; a nested sweep with its own memo; the outside probe taken inside the sweep; the body run
    # outside any sweep. Above master's 325 by eleven.
    # ⟳ 2026-11-11, side job goal-tree-ask: 336 -> 338, none retired. Two new: the Ask tray's lift removed (the tray-less
    # fragment page overwrites the composed one), and the missing-tray reason cut to its headline. Then 338 -> 342
    # (owner 11-11 06:18, answers collapsed): an answer rendered open, an orphaned answer dropped, a thread's
    # answers never attached, and an answers entry missing a field skipped rather than refused. Then 342 -> 354 (PR #558
    # round 1 fold), none retired, two re-bound to `_ledger_refs`: four escapes dropped (answer body, `asked`, Older key,
    # the answers-file error), the tray asked of the exit code, a non-list `answers` and a non-text `asked` let through,
    # a thread marker drawn inside its fold and the two hoisted draws dropped, and the ledger match by bare number twice.
    # Then 354 -> 355 (PR #558 round 2 fold): an unpaired surrogate in an answer no longer refused by name. Then
    # 355 -> 360 (round 3 fold): the UTF-8 check skipping each of its four fields, and an unreadable file raising.
    # Then 360 -> 364 (PR #559, agenda group titles + r1 fold): group labels as plain text, by indentation again,
    # a title unescaped, the title's accent rule removed; one re-bound to `agenda_step_items`.
    "scripts/goal-tree.py": 368,  # 364 -> 368 (backlog #610, + r1 alias): only regen-pages' clone writes the served page
    # ⟳ 2026-10-22, the work-lines backfill: one entry per decision branch of the replay (the
    # sentinel rule, the Stop-hook clear, unreadable output, other checkouts, overlap, banners,
    # the birth check, the dry run, mtime, the last-plan fingerprint, CANNOT RUN).
    # ⟳ same day, the owner's option A for banners: 25 -> 33 — both clear sites remember the
    # plan they cleared, a fresh start is no clear, the banner must name EXACTLY that plan, an
    # ARMED parent is never overridden, the `banner` label, the banner's own time, and --write.
    # ⟳ same day, review round 1 fold: 33 -> 48 — loops and reserved words, sentinel writes in
    # command order, checkouts attributed separately, live banners only, an UNKNOWN start, the
    # checkpoints (status, reads, the Clearing message, an inferred --finish), and atomic --write.
    # ⟳ same day, review round 2 (the allow-list): 48 -> 53 — three entries retired with the read
    # checkpoints and the heredoc detector they guarded; three more retired as EQUIVALENT under
    # the allow-list (an unstripped `do` is itself opaque; `/dev/null` and sed's script operand
    # reach no sentinel either way — measured: each survived with the suite green); eleven added.
    # ⟳ same day, round 3 (the reviewed-code line): 53 -> 62 — four allow-list entries rebound
    # onto SAFE / tracked-script code; nine added for the tracked-script rule, a tracked NAME
    # outside scripts/, heredoc-fed interpreters, git clean/stash, sort -o, uniq's output,
    # export, and `$P`. (A tenth, `-c` read as a path, was EQUIVALENT — measured surviving: a
    # flag never resolves to `<checkout>/scripts/<tracked>.py` — and was not kept.)
    # ⟳ same day, round 4 (inline code INSPECTED): 62 -> 76 — two rebound onto the inspected
    # interpreter branch; fourteen added: the token list, an unterminated body, `Path(` writes,
    # computed vs literal `open()` paths, a `$` in `-c`, both clean inline shapes, interpreter
    # flags, heredoc order, `timeout`, `pwd`, `find -delete/-exec`, `mktemp` under `.claude/`.
    # ⟳ same day, round 5 (the premise: an accident NAMES the sentinel, a plan tool, or a
    # whole-tree delete): 76 -> 78 — three entries RETIRED WITH THE CHECKS THEY GUARDED (`Path(`
    # write methods, `open()` to a computed path, `open()` to a literal path); the token-list
    # entry rebound; five added, one per remaining token and one pinning `subprocess` OFF it.
    # ⟳ same day, round-3 (Claude) fold: 78 -> 90 — background and long-running commands
    # hold their windows (the window itself, a background end, completion records, TaskStop, a
    # shell `&` to the session's end, the foreground stream exemption, pipeline-scoped `&`),
    # hookless sessions clear nothing, hook-attachment evidence, comments, `export`, `nohup`.
    # ⟳ 2026-10-23, round-4 (Codex) fold: 90 -> 101 — five entries rebound onto the session-
    # keyed END and Stop-evidence code; eleven added: Stop-hook-only evidence grouped by session,
    # terminal statuses, quoted notices, the queue-operation and queued_command forms, the
    # tool-use-id match, END after START, a failed TaskStop, auto-backgrounded results, and a
    # foreground command with no result.
    # ⟳ 2026-10-23, round-5 (Claude) fold: 101 -> 107 — a task's END found across sessions by
    # its tool-use id, the session-id grouping, the real tick count and "all ticked", and the
    # --backup copy (content and mtimes). The backup's exists-refusal has no entry: removing it
    # still refuses, through copytree's own FileExistsError (measured equivalent).
    # ⟳ 2026-10-23, round-6 (Codex) fold: 107 -> 108 — ONE entry RETIRED WITH THE CODE it
    # guarded (the cross-session tool-use-id END match, removed as thrashing's answer); four
    # rebound onto the simplified lookup and the per-form notice rule; two added for the
    # one-notice user-message rule.
    "scripts/backfill-work-lines.py": 108,
    # ⟳ 2026-11-03, backlog #470: 25 -> 28. goal-card id, qualified backlog chip, PR link (+3).
    # ⟳ 2026-11-03, backlog #470 review round 1: 28 -> 29. a chip naming a missing row is marked text (+1).
    "scripts/gen-goals-page.py": 29,
    # ⟳ 2026-09-19, the feature hub. TEN. ⚠ The plan assumed this file would need the
    # `NO-MUTATIONS:` escape instead — "it renders; it decides nothing" — and that was wrong on
    # its own terms: seven of the ten revert a DECISION the renderer makes (which band a fragment
    # lands in, whether a `####` node is nested or duplicated, whether the build time is read from
    # the clock), and the tenth guards `sev_glyphs`, which earned a mutation only after review
    # round 1 found its "derived" comment sitting above a hand-written literal. A renderer that
    # decides nothing is a claim worth testing before it is used to skip coverage.
    # ⟳ 2026-10-27, backlog #381 — 10 -> 15. Five on the per-tag match: the raw cell read as one
    # tag, the first tag only, un-normalised `areas:`, a row listed once per tag, and `collect`
    # bypassing `match_rows` at its CALL SITE.
    # ⟳ 2026-11-03, backlog #470 review round 1: 15 -> 16. a linked row's text keeps its keys as text,
    # so no `<a>` nests in the row's `<a>` (+1).
    "scripts/gen-features-page.py": 16,
    # ⟳ 2026-09-10, backlog #110 review round 4. A SEED, not a full manifest, and the reason is
    # measured: `gen-backlog-page.py` is 3,000 lines with 160 cases and had ZERO mutations, so
    # `--mutate .` never touched it and no machine had ever asked whether any of those cases could
    # go red. Four review rounds each found a fresh crop of unfalsifiable ones — 1, then 9, then 8,
    # then 15 — every one found by a human reading, none by CI. These five revert THAT BRANCH'S OWN
    # fixes: the report gate narrowing below the read gate (#110's defect verbatim), the unread list
    # being emptied behind two source-shape proxies, half the drift qualification, the ⚠ prefix the
    # Refresh button collects, and the delimiter cell's end anchor. Five that can only rise beats
    # zero; the rest is its own slice.
    # ⟳ 2026-10-27, backlog #381 — 5 -> 15. Ten on the Bundle-cell grammar this file now owns for
    # three readers: a group dropped, the comma separator, normalisation, de-duplication, the
    # malformed cell dropped and its drift note lost, nearest-vs-first claim, a bare prefix taken
    # for a family, the filter's per-tag count and the card's per-tag chips.
    # ⟳ 2026-10-27, backlog #381 r1 — 15 -> 16: a `|` inside a tag group accepted again (Codex M1).
    # The comma entry was RETARGETED onto a substring of the rewritten `TAG_CELL` line, not added.
    # ⟳ 2026-10-27, backlog #381 r2 — 16 -> 18: the table-header SCHEMA check dropped, and loosened to
    # width only (Codex X1, a `Bundel` header that emptied every row's tags).
    # ⟳ 2026-10-27, backlog #381 r4 — 18 -> 20: the block-header check dropped, and any non-`#`
    # header accepted as a legend (Codex X1, a `| No |` table whose row master's gate saw).
    # ⟳ 2026-10-27, backlog #381 DEFER probes — 20 -> 21: an empty tag group dropped in silence.
    # ⟳ 2026-10-28, backlog #394 (one kind per row, explicit parents): 21 -> 33 — the marker's grammar
    # (unknown kind, `kind:` first, parent shape, must END the cell, one marker), missing kinds
    # reported, the three parent refusals, the marker stripped from the text, the card's kind, and
    # parse reading it.
    # ⟳ 2026-11-03, backlog #470: 64 -> 65. the word diff keeps a key whole (+1).
    # ⟳ 2026-11-03, backlog #470 review round 1: 65 -> 67. publish_rows: the rows that exist, and its warning (+2).
    "scripts/gen-backlog-page.py": 77,
    # ⟳ 2026-09-10, backlog #106. This file had NO manifest while composing every page the
    # reader ever sees, and the cost was measurable rather than theoretical: it grew each page
    # by 1,515 bytes on every recompose until `goals.html` was 95.5% duplicate bytes and
    # `backlog-table.html` stood at composition generation 872. Eight entries, one per clause
    # the fix decides. THREE are on wiring rather than logic — `main` passing `exclude`, the
    # end marker being written, and the begin marker being read with `rfind` — because the
    # extraction rules can each be perfectly correct and never reached.
    # ⟳ r1 Codex Medium: 8 -> 10. A page-specific `#tray …` override was migrating INTO the
    # tray region and freezing there for every page later composed from it; the second entry
    # guards the fix's own failure mode, which is subtracting the tray away entirely.
    # ⟳ 2026-10-18, the r5 fold: 19 -> 20. The composer's resting place for the bar moved
    # from the END of <body> to under the title, which is the line that CAUSED backlog #300
    # (y=6445 of 6475). `place_bar` being unit-correct proves nothing about this path, so
    # the entry severs the CALL SITE — the between-two-tested-pieces gap, measured here
    # three times before.
    # ⟳ 2026-10-19, the r8 fold: 22 -> 25. THREE, all the ambient-assertion SWEEP r7 did
    # not do: `:where(` occurs four times in SHIM (two inside its own comments),
    # `html { --rule:` twice (light and dark), and `chrome-theme` four times across the
    # suite's strings while the subject is the BINDING call.
    # ⟳ 2026-10-19: 25 -> 26. `compose.title` — same shape as above: varied in the source
    # text, unwitnessed by any case, so a caller asking for "Quarterly review" would have
    # got "T" with every gate passing.
    # ⟳ 2026-10-27: 27 -> 35, backlog #376 — the text-style switcher by default: one entry per
    # clause of the wrap (supplied, not nested, only with a switcher), of the decision to add it,
    # and of the `--em` refusal (called, reads @media, ground-keyed, fails closed on zero blocks).
    # ⟳ 2026-10-27, r1 fold: 35 -> 49 — the palette reader became a CLOSED GRAMMAR with a value
    # check; one entry per rule of it (three earlier entries retargeted onto the new code).
    # ⟳ 2026-10-27, r2 REDESIGN. The grammar became a strict FORMAT lint: 6 entries
    # RETIRED WITH THEIR SUBJECT — merging, the root-prefix match, the `:where`/`@layer`/compound
    # branches (one canonical-block rule now), and "@media is skipped", which can no longer fail
    # open because a token declared outside a canonical block is refused as stray. 5 added
    # (whitespace normalisation, !important, the page ground, both tokens per block, the
    # per-state shim pair), then 1 for `themed`; 8 retargeted onto the new code. Net 49 -> 49.
    # ⟳ 2026-10-27, r3 SPLIT (thrashing → architecture-review-2026-10-27-em-guard): 49 -> 45.
    # The per-state model, the var() chain, `!important`-as-its-own-rule and the page-ground
    # rule are REMOVED, so 6 entries are RETIRED WITH THEIR SUBJECT (per-state, `themed`, the
    # var-chain follow, the hex gate before contrast, `!important`, the ground). 2 added for
    # the literal-colour rule (prefix match, a var() admitted); 3 retargeted onto the new code.
    # ⟳ 2026-11-03, backlog #470 review round 2: 45 -> 46 — the tray markup is lifted CLOSED (a composed
    # page left `#tray` open at `</body>`, outside the page subset).
    # ⟳ 2026-11-11, backlog #603: 46 -> 58 — the decision tags (numbering, placement, the answered
    # state and its escaping, the derived counter, its link and colour, its place under the title,
    # the call site, the stylesheet's gating, and both theme halves of the tag colours).
    # ⟳ 2026-11-11, backlog #603 review round 1: 58 -> 77 — the refusals (inside an unrendered
    # element, hidden/inert, ON a table row/option/raw-text/void element, the refusal itself, the
    # ancestor stack's pop), the raw-text list that makes 3.12 parse like 3.14, `<details>` opened,
    # the id collision, the label, `text-transform: none`, and the r1 survivors (first open, the
    # answered count, whitespace-only, the position guard, OS-dark values, answered colour, contrast x2).
    # Three 603 entries retargeted onto the rewritten loop.
    # ⟳ 2026-11-11, backlog #603 review round 2: 77 -> 86 — the <details> auto-open REMOVED (its
    # mutation with it) and replaced by a refusal (on, inside, deeper, the first-summary exemption,
    # a second summary), the implicit </p> (the call, the scope boundary, the formatting guard), and
    # the contrast instrument refusing what it cannot evaluate (alpha, a hex prefix, Codex 4's 00).
    # ⟳ 2026-11-11, backlog #603 review round 3: 86 -> 94 — the r3 Claude survivors pinned (the
    # formatting check's `hidden`, `object` as a p scope stop, `li`/`hr`/`h2` closing a p) and the
    # SVG/MathML refusal (on, inside, and `svg`/`math` as p scope stops).
    "scripts/brief-compose.py": 94,
    # ⟳ 2026-09-10. A guard created and manifested in ONE commit — `check-ratchet-contract` flagged
    # it `[R4_no_mutation_manifest]` the moment it hit disk, which is the ratchet doing its job. Six
    # entries, one per clause it decides, plus the fail-open path: a guard whose CANNOT-RUN branch
    # returns empty instead of raising is the failure this repo counts as worse than a red.
    "scripts/check-selection-card.py": 13,
    # ⟳ 2026-09-11: backlog #90's grouping policy gets its guard, and the guard gets its
    # manifest in the SAME commit — a policy guard with no mutations is a rule nothing
    # checks back, which is the shape `check-ratchet-contract` refuses by name (R4).
    "scripts/check-group-claims.py": 11,

    # ⟳ 2026-11-03, backlog #470: 14 -> 23. key_link / link_keys / link_html: nine new decision
    # lines, incl. the PR-without-repo mutation MOVED here from goal-tree.json.
    # ⟳ 2026-11-03, backlog #470 review round 1: 23 -> 36. link_html rebuilt on ONE html.parser tokenizer
    # (stack across comments, exempt set, closing, the marked class, in_a, the open-at-end report,
    # decoding, the raw tail), missing rows (no link, marked, scan's branch), the g- goal id,
    # render_unlinked (+13).
    # ⟳ 2026-11-03, backlog #470 review round 2: 36 -> 72. The SUPPORTED SUBSET (`subset_problems`): one
    # entry per rule — token spans, the strict stack, void and foreign self-closing, every implied end
    # tag modelled, raw text / RCDATA, table and select, comments, declarations, `;`-less references,
    # the 3.12 AssertionError wrap, and link_html's refusal (+34); the real exempt stack (r2 5b) and the
    # `;`-terminated decode piece (r2 7) (+2). Two rules only 3.12's parser reaches are driven on either
    # Python by making the parser behave as 3.12's (the RCDATA set emptied; an AssertionError raised).
    # ⟳ 2026-11-03, backlog #470 review round 3: 72 -> 79. A URL ending in half a reference (F1, +2), no link
    # of any kind inside a link's text (F2 and its property, +2), the whole p-closer set, HTML whitespace
    # and the button-scope list (F3, +3). The table-text anchor rebound to `x.strip(ASCII_WHITESPACE)`.
    "scripts/page_markup.py": 79,
    # ⟳ 2026-11-03, backlog #470: the key-link guard gets its manifest in the commit that creates it.
    # ⟳ 2026-11-03, backlog #470 review round 1: 16 -> 30. rule 2 read from the syntax tree (self-test
    # BODIES only, docstrings, `+` chains, unparseable files); rule 1 through the shared tokenizer; rules
    # 1b (no <a> in an <a>), 4 (unique ids) and 5 (scripts parse, no node = CANNOT RUN). 7 old regex-era
    # entries rebound or replaced; the AST prefilter (+14).
    # ⟳ 2026-11-03, backlog #470 review round 2: 30 -> 39. Rule 0 read and its page excluded from the
    # other rules (+2); rule 2 reads `%`, `.format` (positional, named), `"".join`, f-string constant
    # parts, and a literal's parts are not reported again alone (+7).
    # ⟳ 2026-11-03, backlog #470 review round 3: 39 -> 44. The generators' renderers property: a raise is
    # reported, so is an <a> in an <a>, the corpus is seeded and holds the review's inputs, and every
    # renderer in the table is read (+5).
    "scripts/check-page-links.py": 44,
    # ⟳ 2026-09-01, backlog #78: 18 -> 23. The entry gate now answers TWO questions
    # instead of one — "does this branch owe an entry?" (unchanged) and "is the entry
    # it added well-formed?" (new, and previously fail-open on the entry-only branch,
    # which is the most common way an entry is written). THREE of the five mutations
    # are on the WIRING, not the predicate: `added_entry_problems` can be perfectly
    # correct and never called, and the pure cases stay green either way.
    # ⟳ 2026-09-01, the block-start divergence: 29 -> 30. The BLOCK mutation was a
    # RETARGET (count unmoved, so a relocation cannot read as new coverage); this +1
    # is a genuinely new guard, added by the Claude review half after the Codex half
    # rated the agreement case Low. It restores a HAND-WRITTEN `ENTRY_ISH`, which the
    # BLOCK mutation provably cannot reach: corrupting the shared rule moves both
    # sides together and leaves the agreement case green. Only breaking the
    # DERIVATION separates them, and that is the regression the seam exists to stop.
    # ⟳ 34 -> 42 and gen-dashboard 73 -> 65, backlog #82: parse_entries RELOCATED into the
    # gate, and its eight mutations moved WITH it. THE SUM IS UNCHANGED AT 107 on purpose —
    # only the per-file split can tell a relocation apart from deleted coverage, which is
    # the same reason #71 held its sum at 73. `run_suite(d, fname)` runs only the mutated
    # file's suite, so the killing cases moved too.
    # ⟳ 2026-09-08, R4 manifest debt 6 -> 5. ⚠ `state in UNRESOLVED` is NOT a target and must not
    # become one: the two state lists are disjoint, so that disjunct always implies the second and
    # NO input can distinguish it. It is defensive (it catches a future edit that wrongly moves a
    # pending state into the resolved list), not decisive — mutating it would be unkillable-by-
    # construction, the `check-storage-grant-pin` case-5 shape.
    # ⟳ r2 M1, 2026-09-23: 27 -> 29. `log_line` had NO entry for either of the two arguments it
    # passes through to the shared record — session and the timestamp — while its banner sibling
    # had both. The gap is the shape of the fall above it: `session` moving into `observer_log`'s
    # positional 3 retired the adapter's SANITISING entries correctly and took the PASSTHROUGH
    # entry with them, which is a different property. Both measured on the delivered adapter
    # before being added: freezing session -> 49/57, freezing `when` -> 56/57.
    # ⚠ **BOTH ANCHOR ON A SUBSTRING, NOT THE WHOLE `return` LINE, AND THE HARNESS IS WHY.** The
    # first draft gave the two NEW entries the same find-string as the PRE-EXISTING entry already on
    # that line, and `--mutate .` REFUSED the manifest with `NOT MEASURED`: `load_manifests` builds
    # `seen_anchors` from the find-strings ALONE, so a differing replacement does not distinguish two
    # entries, and its `EXACT TUPLE EQUALITY` note names the escape — a distinct substring each.
    # ⭐ This is the OTHER HALF of r2 H1, which established that different substrings of one line ARE
    # accepted; identical ones are not, and both halves had to be learned by running it.
    # ⚠ **THE THIRD ENTRY ON EACH LINE KEEPS ITS FULL-LINE ANCHOR, DELIBERATELY** (r3 addendum L1):
    # it is the pre-existing payload-column entry, and the whole line IS its subject. So the count is
    # 3 entries per line, of which 2 per line were retargeted — 4 across the two files, each
    # RE-MEASURED after retargeting, because a moved anchor is a different mutation until something
    # proves otherwise.
    # ⛔ r3 H3 / addendum H1: THE TWO LINE CITATIONS THAT USED TO BE IN THIS PARAGRAPH BROKE THEMSELVES.
    # They were correct when typed and wrong as delivered, because this comment is long enough to push
    # its own targets down — an eight-line insertion moves every citation below it by eight. Symbols
    # now. That is the repo's standing rule and this file cites its own lines nineteen times, so the
    # class is open and nothing guards it.
    # ⟳ r3 M4, 2026-09-23: 29 -> 30, the sibling call site. ⛔ AND IT COULD NOT HAVE HAD AN ENTRY
    # BEFORE ONE CHANGE TO THE SUITE: neutering the write made this suite die by `IndexError`, not
    # by a named case, and the harness requires death VIA THE CASE AN ENTRY NAMES. Two cases indexed
    # `_drive_log`'s result with no `len(...) == 1` guard while their three siblings had one, so
    # `and` short-circuited for the siblings and raised for these. The second instance was found by
    # grepping for the class, not by the first fix. Now 10 named reds, no crash.
    # ⟳ backlog #382 r2: 41 -> 42, the sentinel resolved on first use, not at import.
    # ⟳ 42 -> 50 (backlog #331(a) / #357, PR #440 r1): the CANNOT RUN refusals for a corrupt, undecodable or
    # non-object input. ⟳ 50 -> 52 (PR #440 r2): +7 for a NON-EMPTY KNOWN status (X3) and the parse through
    # `bounded_read` (X2); -5 because the stdin read (closed, TTY, deadline, collect) and the hand-kept exception
    # union moved to `bounded_read.py`, whose manifest carries them now.
    "scripts/check-ci-watched.py": 52,
    "scripts/codex-frontier-model.py": 7,
    # ⟳ 2026-09-08, R4 manifest debt 5 -> 4. Two findings, both about a rule with no single owner:
    #   * `range(a, b + 1)`'s INCLUSIVE bound was unfalsifiable — every range case writes both
    #     endpoints (`B1-B5`), and ident_re matches each on its own, so expansion only ever
    #     supplied the interior. A range written `B1-5` is the only shape where the top member
    #     exists solely by expansion; that case is now present.
    #   * `open_items` did not exist: the "what counts as still open" rule was written TWICE, once
    #     for the verdict and once for the sentence main() prints. Byte-identical with nothing
    #     holding them so — drift would fail the check while printing "every checkbox is ticked".
    "scripts/check-roadmap-consistency.py": 12,
    # ⟳ 2026-09-08, R4 manifest debt 4 -> 3. TWO VACUOUS ABSENCE-ASSERTIONS, same shape: both
    # `both halves pass` and `halves in per-writer subdirectories pair normally` assert
    # `problems == []`, and deleting the scan they depend on produces exactly that empty list.
    # "Nothing went wrong" was satisfied by "nothing happened", so the flat and nested scans were
    # each unguarded. Companion cases now assert stats["rounds"] == 1 — the pair was SEEN.
    # ⟳ 2026-09-12. THE GUARD THAT DEMANDS MANIFESTS HAD NEVER BEEN ASKED FOR ONE. R4's escape is
    # a written `NO-MUTATIONS: <why>`, and its regex matched line 16 of check-ratchet-contract's
    # OWN docstring — "a mutation manifest, or `NO-MUTATIONS:` ENFORCED — R1 asks whether …" —
    # taking "` ENFORCED — …" as the reason. Measured across all 34 guards: it was the only file
    # affected. The regex now requires a space then a LETTER, and this manifest is the answer to
    # the question it had been dodging. ⚠ It ALSO hit the failure-line trap — FIVE printers said
    # `  FAIL {name}`, which `parse_fail_names` cannot see, so every mutation here would have been
    # killed and unattributed. ⛔ AN ORDINAL FOR THAT IS DELIBERATELY NOT WRITTEN: PR #293 retired
    # the count one commit earlier, after three hand-written versions were each wrong, and the
    # first draft of THIS comment resurrected it as "the TENTH file" — the retired number walking
    # straight back in at the next opportunity. Derive it:
    #     git log -S'[FAIL] ' --reverse --format='%h %as %s' -- scripts/<file>
    "scripts/check-ratchet-contract.py": 16,
    # ⟳ 2026-09-23, folding review-identity-176 round 1: 12 -> 17, AND ONE EXISTING ENTRY WAS
    # RETARGETED — its anchor `if rec.get("gate_ran"):` was unbound by the restructure that added
    # the reverse clause, the exact *an anchor is unbound by ANY nearby edit* shape this repo has
    # paid for seven times in one session. Found by sweeping every manifest anchor against the
    # tree, NOT by `--self-test`, which loads the manifests without resolving them. The consumer
    # also gained the
    # three rules r1 found missing from it, and each entry names the case that reds for it:
    # a REFUSAL is not testimony about a gate (B1 — without it a re-dispatch that touched
    # nothing makes CI tell the reader to delete a real review); the ERA BOUNDARY is a
    # number in the record rather than a date in a comment (M2 — the prose caveat had no
    # falsifier and deleting it went green everywhere); the REVERSE direction of the join,
    # `gate_ran: true` naming a review that is not filed (M1 — the shape #176 was convened
    # over, `continue`d until the era gate made it safe to read); and two on the derived
    # era counts (M3 — the figure that stood in prose was wrong at the denominator).
    # ⟳ 2026-09-24, folding round 2: 19 -> 24, AND SIX EXISTING ENTRIES WERE RETARGETED — five of
    # them because the round-2 fix moved the line they named, which is the finding that convened
    # this fold. TWO of the five had already gone silently orphaned on the previous fold and were
    # caught by CI, not by `--self-test`, which loads the manifests without resolving them.
    #   ⑴ RETARGETED — 6. `r1 B1` and `r1 M3 (refusals)` moved when `refused` became `is True` at
    #     both sites; `r1 M2` and `r1 M3 (era counts)` moved when the era gate became `schema_of`;
    #     the two `gate_ran` entries moved when H1's fix made that field `is not True` as well.
    #     ⚠ The re-derivation entry was retargeted to a DIFFERENT text from its neighbour on
    #     purpose: a bare `rec.get("gate_ran")` anchor now survives the fix while measuring
    #     something the case it names cannot see, and identical anchor tuples are refused.
    #   ⑵ ADDED — 5. TWO hold H1 (`gate_ran` read by identity in the join, and refused as a
    #     non-bool on the read side); ONE holds M1, the third site of the same idiom, whose
    #     hardening left the suite at 49/49 until the case beside it existed; TWO hold L1's
    #     `schema_of` in both directions — a field that is not a version is unreadable, and an
    #     ABSENT field is the oldest era rather than unreadable, which is the direction that would
    #     turn the whole 184-record pre-cutover corpus into a CANNOT RUN.
    # ⟳ 2026-09-24, backlog #176 round 3 fold, 25 -> 29. FOUR entries, and none of them is the
    #   fifth patch's own line twice: H1 splits into the TYPE clause (an unhashable `review` raised
    #   out of the check as rc 1 with stdout empty) and the BLANK clause (an empty string is a key
    #   nothing on disk matches), attributed to different cases; L1 restores the `(unnamed)`
    #   sentinel, which made a record CARRYING it indistinguishable from one with no field; M2
    #   collapses the new `unreadable` era bucket back into `pre_cutover`, which is what
    #   `(schema_of(rec) or 0)` did silently. ⚠ The `verdict_problems` arm of M2 carries NO entry
    #   on purpose: both answers skip there, so a mutation of it would survive, and shipping an
    #   unkillable entry to make the count look fuller is the shape this table exists to refuse.
    #   SIX anchors in these two files were RE-TARGETED in the same commit because the fix moved
    #   their text; the sweep is what found them, and it is still in no local suite.
    # ⟳ 2026-10-24, backlog #339: 34 -> 35 — the solo-half failure names the PAIRING rule; r1 fold
    #   35 -> 36 — the hint is neutral between the two readings and skips round 1.
    "scripts/check-review-rounds.py": 36,
    # ⟳ 2026-09-08, R4 manifest debt 3 -> 2. ⚠ ONE MUTATION SURVIVED FIRST: I removed the words
    # "Produce one with" from the absent-results refusal, but the case asserts that `--outputFile=`
    # appears in the message and that token is on the NEXT fragment. The mutation READ like the one
    # the case names and touched a different string. Retargeted to the fragment carrying the claim.
    "scripts/check-test-counts.py": 11,
    # ⟳ 2026-09-08, R4 manifest debt 2 -> 1. Every target is in the PURE half, and the two most
    # valuable pin defects this guard has already paid for: r9 M1 (schema qualification unstripped,
    # so an ordinary READABLE relation derived as OUT OF REACH) and r9 M3 (the grantee side used a
    # different normaliser from the relation side, so `to "anon"` matched nothing). Both are now
    # mutation-covered rather than merely commented.
    "scripts/check-anon-exposure.py": 13,
    # ⟳ 2026-09-08, R4 manifest debt 1 -> 0. THE LAST ONE. Also closed a MEASURED coverage gap:
    # `idx` joined ATTRIBUTABLE_KINDS on 2026-08-28 because `create unique index rev_uq on
    # video_artifacts (video_id)` PASSED — and no case arrived with the fix. Removing "idx" from
    # that tuple survived all 117 cases; the drift table now carries an INDEX row, so it does not.
    "scripts/check-live-schema.py": 12,
    # ⟳ r2 M2, 2026-09-23: 43 -> 44. Backlog #168's remedy — the sentence in this guard's refusal
    # telling the reader that editing the PR body cannot re-arm the gate and they must PUSH — was
    # an UNTESTED SENTENCE: the suite was 148/148 with it present or absent. The entry deletes the
    # clause and the new case reds. ⭐ Worth naming the shape: #168 is *the knowledge lives where
    # the person in trouble is not looking*, and it shipped with its own remedy unmeasured.
    "scripts/check-dashboard-entry.py": 44,
    # ⟳ backlog #91: check-plan-code 35 -> 30, and the FIVE did not disappear — they MOVED
    # to scripts/coverage_verdict.py with the clauses they guard. The sum below is unchanged
    # at 359, which is the point: a seam that relocates coverage must not be able to look
    # like coverage that was deleted, and only the per-file split can tell those apart.
    # ⟳ 2026-09-08, the plan-mode retirement: HELD AT 44, and the hold is the point. The
    # refusal made `main()`'s plan-mode tail (L3529-3581) UNREACHABLE — every path there needs
    # `a.plan` truthy and the refusal intercepts exactly that — so the mutation anchored to its
    # `not_measured_line(verdict, f"{mode}: ")` print could no longer be killed by any case.
    # CI's `--mutate .` caught it as 1 survivor of 383; the local suite could not, because the
    # case had been rewritten off the CLI onto `evidence()` and stayed green at 229/229. That is
    # the recorded shape: A SUITE PASSING IS NOT EVIDENCE ITS MUTATION STILL BINDS.
    # RETARGETED, not deleted, onto `evidence()`'s `not_measured_line(v)` — the printer that
    # same case now drives, guarding the identical property (a NOT MEASURED refusal must not
    # leak a survivor count). The count is therefore UNCHANGED: a retarget must not read as
    # lost coverage, and a deletion here would have shrunk the ratchet inside the very PR whose
    # message says it only rises. The retirement of this entry belongs to the deletion slice,
    # with the case it serves.
    # ⛔ ⟳ 2026-09-09, THE DELETION SLICE — THIS NUMBER FALLS, DELIBERATELY, AND A FALL IS
    # NORMALLY A DEFECT. The comment above says the retirement of a plan-mode entry "belongs
    # to the deletion slice, with the case it serves", and this is that slice. 21 of the 44
    # entries were anchored INSIDE the seven plan-mode functions; when the function goes, the
    # anchor cannot resolve, so the entry is retired rather than orphaned. Retired one commit
    # at a time WITH its function, so a reviewer sees which coverage left with which code.
    #   verify_evidence 1 · evidence 5 · check 7 · extract 8   = 21   (44 -> 23)
    # ⚠ HOW THE 21 WAS MEASURED, because the first two attempts both answered 0. The question
    # is NOT "does the anchor text mention a doomed function" — the retargeted `r3 B2` entry
    # reads `not_measured_line(v)` and lives at evidence():1541, invisible to a name match.
    # It is "is the anchor LOCATED INSIDE one": `src.find(anchor)` -> line -> enclosing def.
    # And the anchor is `edits[i][0]`, not a key called `anchor`; reading the wrong key gives
    # `find("") == 0`, which attributes all 44 entries to line 1 and answers 0 a second way.
    # ⟳ 2026-09-09, round 1 F9+F10: 32 -> 33. NOT a new behaviour — a SPLIT of one entry that
    # was silently carrying two. Entry 11's edit was `!=` -> `==`, an INVERSION, so it broke
    # count_drift's mismatch branch AND its match branch at once and reddened FOUR cases under a
    # name claiming one. Retargeted to `!= actual and False` (2 reds, the named case still fires)
    # and the match branch given its own entry. Measured by the reviewer on a staged copy: the
    # two directions are INDEPENDENTLY breakable, and breaking the match branch alone does NOT
    # fire 'count_drift reports a mismatch' — so this was two properties, not one with symptoms.
    # ⟳ 2026-09-09, backlog #98: a NEW guard arrives with its manifest in the SAME commit.
    # The ratchet offered to raise MANIFEST_BASELINE to 1 instead; taking that would be how
    # paid-down debt gets silently re-accrued, which is the thing the baseline exists to stop.
    "scripts/check-backlog-closure.py": 6,
    # ⟳ 2026-09-10, backlog #106: 33 -> 34. The harness always REFUSED a suite whose red could
    # not be attributed to any case; what it did not do was say WHY, and that silence cost two
    # branches in one day — both diagnosed by hand from an empty list at the bottom of a
    # 420-mutation log. The new entry guards the DIAGNOSIS, not the refusal.
    # ⟳ r1 of the progress round: 39 → 48. Nine, for the six new clauses plus the one whose case
    # could not fail (B1) — and ONE RETARGET: bounding the line rewrote `progress_line`'s return,
    # orphaning the anchor that guarded it. An anchor binds by TEXT, so improving code breaks it
    # and the suite stays green; `--mutate .` refuses an unresolved anchor, which is the only
    # reason that was caught here rather than merged.
    # ⟳ r9: 27 → 29. FOUR added for star-args, kwargs keying and the key-set pin;
    # TWO retired with their subject — the per-file COUNT comparison they mutated was
    # replaced by a key-set comparison, so their anchors named code that is gone. That
    # is the one sanctioned kind of fall: recorded here with its count and its reason.
    # ⟳ r10: 43 → 42. One RETIRED WITH ITS SUBJECT — widening the suite's scope made the
    # underscore test unable to decide anything, measured by its mutation surviving a full
    # suite. The clause stays as a defence; the entry cannot fire, so it goes.
    "scripts/check-fixture-variation.py": 42,
    # ⟳ 2026-09-17: `check-python-pin.py` JOINS with 11 entries, in the commit that creates it —
    # `check-ratchet-contract.py` refused the file until it did, which is the manifest half of the
    # contract doing its job. ⭐ Two of the eleven found AMBIENT cases on the first pass: the
    # empty-corpus case asserted only an exit code that the NO-PINS prong returns by another route
    # (backlog #137's `declared_not_derived` defect, recurring), and the jobs-block case used a
    # fixture key the regex rejected anyway. Both repaired rather than exempted.
    # ⟳ r1 (codex) 1 Blocking + 2 High: 11 -> 12. ⭐ The High that mattered was a FALSE GREEN —
    # `declared_pins` matched ANY line shaped like `python-version:`, so one inside a shell
    # heredoc or an unrelated action's `with:` made a job with NO setup-python read as PINNED.
    # The predicate is now "a pin attached to an actions/setup-python step", with the reviewer's
    # two reproduction fixtures as cases. ⚠ A step-boundary clause written alongside it was
    # MEASURED INERT (deleting it left the suite green, the dedent test already covering it) and
    # was DELETED rather than kept with an entry that could not fail.
    # ⟳ r1 (claude) 3 High + 3 Medium + 4 Low: 12 -> 18. ⭐ HIGH 1 was the branch's own central
    # claim: "the pin TOOK EFFECT" compared major.minor, and the runner's AMBIENT python3 is
    # already 3.12.3 — so the comparison was satisfied by the exact pre-branch world the guard
    # exists to end, and `update-environment: false` would have kept it green while 45 guards ran
    # unpinned. It now asserts PROVENANCE via `pythonLocation`, which only setup-python exports.
    # HIGH 2: four legitimate YAML job shapes were INVISIBLE, and an invisible job passes — the
    # guard was calibrated on its own corpus. Tails loosened (measured free), indent kept
    # (measured load-bearing), and a jobless workflow now REFUSES rather than passing.
    # HIGH 3: the single line arming the assertion had no case and no mutation; extracted.
    # ⟳ r2 High (codex): 18 -> 19. The pin must be the input the ACTION READS —
    # `with.python-version`. Scoping it to "inside the setup-python step" was the SECOND version
    # of this predicate and still too loose: a `python-version:` under `env:` in that same step
    # made a job whose setup-python declared nothing report `python pin OK`. Third iteration, and
    # each time the span was narrowed instead of the THING being named.
    # ⟳ r2 (claude) 3 Medium + 5 Low: 19 -> 24. Medium 1: the jobless refusal only fired on an
    # ALL-OR-NOTHING file, so one readable job beside an unreadable one (a QUOTED job key, which
    # GitHub accepts) restored both r1 Highs at once — it now COUNTS unreadable keys. Medium 3:
    # r1's inline-comment fix had no case and no entry, so deleting it left the suite green.
    # Low 2: three clauses of `pin_took_effect` were undriven and the first is FAIL-OPEN — an
    # EMPTY `pythonLocation` makes `startswith("/")` true for every absolute path on earth.
    "scripts/check-python-pin.py": 52,
    # ⟳ 2026-10-05, backlog #217: 77 -> 92. FIFTEEN entries, one per clause of `--shard I/N`,
    # ⟳⟳ 2026-10-06, ROUND 5 M2 — AND THE LINE ABOVE WAS LEFT NARRATING 92 WHILE THE VALUE
    # BELOW REACHED 95. Three later entries (the `.pyc` read/write pair and the stale-`expect`
    # retarget) landed without extending this note, so the only record of them was the number
    # itself — which is the one thing a reader cannot attribute. Corrected to 95; thethree 
    # intervening deltas are in their own commits.
    # added in the same commit as the flag. Every `expect` was derived by APPLYING the mutation
    # in a staged tree and reading which case reddened — not written from memory, which is how
    # this file's r2 fold shipped three behaviours with zero entries. Four of the fifteen pin
    # the partition itself (stride, offset, the empty-shard refusal in both of its two callers),
    # because a partition that drops an entry makes N green jobs report success over work
    # nobody did — strictly worse than the slow sweep they replace.
    # ⟳ 2026-10-21 r5: 110 -> 112. `sweep_skipped_hole`, so the CI SKIP message can say
    # WHICH of two different situations produced the same `changed=false` (r5 CLAUDE M1).
    # ⟳ 2026-10-21 r6: 112 -> 114. `changed_from_nul`, both arms — the parse that let a
    # C-quoted path skip the whole gate (r6 CODEX finding 2, a VERDICT defect).
    # ⟳ 2026-10-21: 114 -> 117. `sweep_verdict` — the three-way decision moved OUT of
    # ci.yml's run: block, where it was unmeasurable (ZERO mutation entries target .github/).
    # Three entries: losing the RUN-UNPARSED state, conflating the two causes of a None
    # change-set, and inverting the parsed verdict outright.
    # ⟳ 2026-10-25: 117 -> 128, the LOCAL SWEEP BUDGET, --allow-long-local and --only (backlog #208):
    #   eleven entries added, none retired. ⟳ r1 fold: 128 -> 131 — four anchors this branch orphaned
    #   REBOUND (r1 CLAUDE H2, plus two of its own), three added for main()'s --only wiring and CI=true.
    #   ⟳ r2 fold: 131 -> 133 — a failed control is reported before, and priced out of, a budget refusal.
    # ⟳ 2026-10-31, backlog #407: 137 -> 139 — the harness's own suite runs carry the mutation-run marker
    # (`mutation_env`), and the BORROWED `child_env` does not. ⟳ r1 fold: 139 -> 140 — `child_env` STRIPS an inherited one.
    # ⟳ 2026-10-31, backlog #359: 140 -> 142 — the TOTAL is derived (`declared_total`), and the two
    # entries are the two ways it stops being: a typed literal again, and a manifest dropped from the sum.
    # ⟳ r1 fold: 142 -> 147 — three for the pins' SHAPE that makes PIN_LINE complete (a duplicate key,
    # a write outside the display, a pin line PIN_LINE cannot read), one for the AST total scan, and
    # one for a total line printed over pins that match.
    # ⟳ r2 REDESIGN: 147 -> 147 — the three SHAPE entries are RETIRED WITH THEIR SUBJECT
    # (`pin_shape_problems` is deleted: it proved a runtime value from source text, and Codex r2 walked
    # around it three ways). Three added: `--print-pins` printing a constant, `--print-pins` beside
    # `--mutate` accepted, and the total scan no longer asking whether the total is mentioned. The
    # AST-scan entry is REBOUND to the new comparison test.
    # ⟳ r3 (Claude F1): 147 -> 149 — `--print-pins` is deleted, and its two entries (printing a constant,
    # accepted beside `--mutate`) are RETIRED WITH THEIR SUBJECT. Four added: the pins-are-the-display
    # assertion removed from `--mutate`, the same removed from `--self-test`, a duplicate display key
    # resolved instead of refused, and the display-versus-held comparison inverted to refuse only a RISE.
    # (An inversion that refuses AGREEING pins is stopped by the top-of-suite refusal, which is CANNOT
    # RUN, and the harness rightly does not count a cannot-run as a catch — measured on the first sweep.)
    # ⟳ 2026-11-04, backlog #330: 149 -> 168. The binary skip is RETIRED with its nine entries
    # (`sweep_needed`, `SWEEP_RELEVANT_ROOTS`/`SWEEP_SKIP_ROOTS`, `sweep_skipped_hole`, `sweep_verdict`);
    # 28 added for the per-manifest selector, its log, select-then-shard, the empty-selected-shard
    # pass, and main()'s --event/--changed wiring. Seven anchors REBOUND to the edited lines.
    # ⟳ 2026-11-04, PR #496 r1: 168 -> 174, one per selector fix (X1, C2 twice, C3, C5 twice).
    # ⟳ PR #496 r2 X2: 174 -> 177 — a walker of `scripts/` is selected: the rule, the loop-variable
    # dataflow, and the one-file-path negative.
    # ⟳ 2026-11-06, backlog #533: 178 -> 182, none retired. The pins moved into this file: the pins file
    # as a harness file again (1), an unreadable pins file read as agreement (1), importing the harness
    # needing the pins (1), and the read's reason dropped (1).
    # ⟳ 2026-11-06 backlog #506: 178 -> 199 — the seed-varied sweep (`--seeds`): the seed reaching the
    # child, `seed_outcome`'s four verdicts, `parse_seeds`' three refusals, the control under EVERY seed,
    # and the wiring through `run_mutations`, `mutate_delivered`, `main` and the tally.
    # ⟳ 2026-11-06 #506 r1 fold: 199 -> 205 — the stopped-early seed (Codex M2), the NAMED-case comparison and its
    # no-expect fallback and wiring (Claude M1), the per-seed tree copy and its cannot-copy refusal (Codex M1).
    # ⟳ 2026-11-06 #506 r1 fold, COST: 205 -> 215 — one tree per seed for the WHOLE run: seed_runs using the run's
    # trees, run_mutations / mutate_delivered / both controls sharing them, the mutant applied to every tree, a
    # tree it cannot be written to, a tree that cannot be restored, and the run stopping on it.
    # ⟳ 2026-11-06 backlog #506 r2 Codex M1: 215 -> 224 — the summary LINE rule (`summary_total`): seed completion and
    # control greenness each reverted to the substring `passed`, whole-line -> search, last -> first, and one per
    # SUMMARY_LINE arm (`passed`, `N of M`, `self-test: `, the `cases` words, `N cases, N passed, N failed`).
    # The r4 M1 control entry was re-bound.
    # ⟳ 2026-11-06, merging PR #523 (backlog #506) into backlog #533: 182 + 46 = 228. The two lines above are
    # each PR measured from the common 178; the merged manifest holds both sets (4 + 46 added, none retired).
    # ⟳ 2026-11-07 backlog #231 + #558: 228 -> 254 — seven for `_walks_dir`'s scope index (class body, def
    # scopes, module seed, sibling isolation, the fixpoint, the `ls-files` prefilter, a carried name) and
    # nineteen for the per-target suite limit (`suite_limit`'s three arms and two pins, `run_suite_parts`'
    # two, the message, and every hand-off from the control to the mutant and re-control runs). Eight
    # existing entries were re-bound to the threaded `limit=` text, none retired.
    # ⟳ 2026-11-08 suite-cost-b r1 fold (backlog #558): 254 -> 280 — twenty-five for the shard's time budget
    # (`sweep_budget`'s reading of ci.yml, its headroom pin, `run_suite_parts`' cap, and every stop and its
    # last line in `run_mutations`, `mutate_delivered` and `main`) and one for r1 F2 (the seeded, tree-less
    # call forwards its limits). Three entries were RETARGETED for r1 F3 — the re-control is flat again, so
    # the two that dropped `control_parts`' limit (now removed) and the one that dropped the re-control's
    # became "the control/re-control runs under the CEILING / the mutant's limit" — and seven re-bound to
    # moved text. None retired.
    # ⟳ 2026-11-08 suite-cost-b r2 fold (backlog #558): 280 -> 300 — twenty for the deadline's inputs: the
    # workflow reader that refuses rather than searches (six, r2 F2), the job-start epoch, event and job read
    # from the runner (`ci_deadline`, eleven, r2 F1 + F3), and the report printed before teardown (three).
    # Seven r1 entries re-bound to the rewritten reader and `main`, two of them renamed; none retired.
    # ⟳ 2026-11-08 suite-cost-b r3 fold (architecture review 2026-11-08, sweep-deadline): 300 -> 301. The job's
    # limit now arrives as an integer in the step's env, aliased from the job's own `timeout-minutes` node, so the
    # YAML reader (`_yaml_entries`, `workflow_value`), `sweep_budget` and the GITHUB_JOB lookup are DELETED, and the
    # 14 entries on that code are RETIRED with it (only deleted code): the six r2 F2 reader entries, five r1 F1
    # reader/expression entries, the r2 F3 event-feeds-the-budget entry and both r2 GITHUB_JOB entries. Two r1 F1
    # entries are re-bound to the new limit (headroom; a missing limit guessed). Fifteen added: three for
    # `ci_deadline`'s limit (padding/zero accepted, the limit ignored, the variable renamed) and twelve for
    # `sweep_limit_pin` (its anchor, alias, ONE-timeout-minutes — R3-F1's first-key spelling — epoch, job-end,
    # comment and refusal clauses). Every added or re-bound entry hand-checked by the harness's rule.
    # ⟳ 2026-11-11 backlog #495 (owner 19:25): 301 -> 310 — nine for the SURVIVOR re-run: never re-run, a kill
    # re-run anyway, FLAKY turns red, FLAKY counted as killed, a plain re-run kill or a NONDETERMINISTIC re-run not
    # read as FLAKY, survive-twice read as FLAKY, the report and the tally not naming it. Each verified red on a
    # temp copy via the case it names.
    # ⟳ 2026-11-11 backlog #495 r1 fold: 310 -> 319. Seven of the nine re-bound to the moved re-run (it now runs only
    # for a survivor, in a FRESH tree); two dropped ("a plain re-run kill / a NONDETERMINISTIC re-run not read as
    # FLAKY" — a seed split is now refused). Eleven added: the re-run kill held to the first-run rule (`rerun_kill`:
    # the named case missing, red twice, no summary line, no [FAIL] line, a seed split, a re-run that did not
    # complete, every red case named instead of the expected one), the fresh tree (`rerun_from=d`), the budget
    # before the re-run, the unmutated re-run, the unseeded re-run. Each verified red on a temp copy via its case.
    # ⟳ 2026-11-11 backlog #495 r2 fold (Codex 1): 319 -> 320 — the re-run snapshot preserving symlinks again (an
    # absolute link into the tree shares the first run's count). Verified red via its case on a temp copy.
    # ⟳ 2026-11-13 backlog #619 R1: 320 -> 328 — the shard RECORD: its shard not the one sliced by, a not-measured
    # run recorded complete, a truthy non-True flaky counted, a failed write left green, its directory not made, no
    # record built for --record, and --record accepted without --mutate or with --only.
    # ⟳ 328 -> 329, #619 r1 fold (Claude m2): a not-measured run's record dropping the FLAKY names it reached.
    "scripts/check-plan-code.py": 329,   # ⟳ 2026-10-21 r4: +2, SWEEP_RELEVANT_ROOTS — one
    # entry for the collapse back to `scripts/` only (the hole Codex PROVED with
    # .agents/skills/shared/handoff-path.md, 25/25 -> 24/25) and one for dropping the `docs`
    # exclusion, which would revert backlog #173's pinned decision and its whole saving.
    # ⟳ 2026-09-08 r2 M1: +3, then r3: +8. The r2 fold
    # added THREE behaviours and ZERO manifest entries — cases guarded them, nothing in CI
    # did, and a case is held only by the self-test COUNT ratchet, which sees the number
    # move rather than the coverage leave.
    # ⟳⟳ 2026-09-08, r3 M1 — AND THE ANCHOR NOTE ABOVE IT WAS TRUE ON THE WRONG AXIS, which
    # the reviewer measured on a copy BEFORE the fix rather than predicting it. r2's anchors
    # avoided the branch expression and landed on `mut_unreadable = any(…)` instead — a
    # PREDICATE ASSIGNMENT, indented 8 spaces inside `if not files:`, and r3 H1's fix deletes
    # that line outright. Two entries were orphaned by this fold (that one, and the honest-zero
    # predicate for the FOURTH time on this branch); both are retargeted here, not adjusted.
    # The lesson that survives: there is no anchor a rewrite of its own subject cannot break,
    # so the ratchet is the instrument — every new entry quotes a problem MESSAGE or a whole
    # statement, and `--mutate .` in CI is what will say if one stops resolving.
    "scripts/coverage_verdict.py": 6,
    # ⟳ 2026-09-10: the zero-round gate joins the manifest in the SAME commit that adds it. Five
    # PRs merged unreviewed on 2026-09-09 because a guard existed and nothing ran it; shipping its
    # replacement as manifest debt would repeat the shape at one remove.
    # ⟳ 2026-09-13, 6 -> 23: the final-tree rule, over FOUR review rounds. TWELVE of the seventeen
    # exist because its own reviews found them, and both rounds' Blockings were the SAME class one
    # layer apart — r1: subtracting dirty PATHS credited a file edited again after the round; r2:
    # comparing CONTENT credited a mode-only change. The entry is now mode+blob. Also here: the
    # `guarded_changes` call that no case could reach, the CANNOT-RUN exit code, and the REVIEW GAP
    # escape in both directions including whose absence it is allowed to explain, and the reviewed
    # DELETION that had no entry to compare against — absence is a tree state, and dropping it
    # failed the careful path for the crime of deleting code.
    # ⟳ 2026-09-14, r11: 23 -> 35. TWELVE entries, and every one of them aims at a rule that used to
    # live inside the git-reading gatherer where no case could reach it — measured, eight decision
    # points all surviving mutation with the suite at 77/77, two of them turning a live refusal into
    # a live pass. The rules are now `classify_verdict`, `reviewed_map`, `tail_candidates`,
    # `second_question`, `readable_docs` and `split_nul`; these entries are the proof they can fail.
    # Two of the twelve are the r11 Blocking and High, which are ONE expression pulling opposite
    # ways: the union (a reverted overlay must still be compared) and the intersection (the base's
    # commits must not be charged to this branch).
    # ⟳ 2026-10-20 — AND THE RUNNING TALLY THAT USED TO BE HERE IS DELETED ON PURPOSE.
    # r1 Claude CM2 found this comment claiming "10 -> 17" and "sum 1580" while the code said 21
    # and 1595. I then changed the pin FOUR MORE TIMES in one session and the narrative drifted
    # again each time — a comment that recites a sequence of edits is a second implementation of
    # the number, and this repository has measured that shape drifting seventeen times.
    # So: no intermediate values, only what is true now and why.
    #
    # check-review-decision.py — the ranker's margin/abstention, its reader, and the two
    # entries that pin `review_scope`'s order as the thing the reader prints (it had no
    # non-test caller at all, while two process docs named it).
    # check-decision-scheme.py — the route-escalation promise. Its bulk is the r1 REDESIGN:
    # `routes_tried` is DERIVED from each unit's earlier rows, so a retry is inexpressible
    # rather than refused, and the derivation, the per-unit triggers, the CANNOT-RUN paths and
    # the re-derived starvation ratchet each carry their own entries.
    # ⛔ THREE candidate mutations were REJECTED rather than counted, reasons in the manifests:
    # one equivalent by construction (n1 is the maximum), one killing by IndexError with zero
    # [FAIL] lines, and one equivalent-in-environment (a shallow-clone branch on a full clone,
    # since replaced by the drivable `shallow_refusal`).
    # ⟳ 2026-10-21 r4: 21 -> 22. ONE added (convergence_unreachable re-deriving the clean-round
    # rule instead of calling `round_blocker`, the drift that made the two readers contradict
    # each other from birth). The r4 extraction also ORPHANED FOUR anchors by moving the rule's
    # indentation out of `converged`; those were RE-POINTED, not retired, so they do not change
    # this count — a re-point must be invisible here, and a fall would mean coverage was lost.
    # ⟳ 2026-10-21 r5: 22 -> 23. The FORBIDDEN half of `unreachable_message_sound`,
    # which is the half r5 CODEX proved was absent — my r4 assertions checked only what
    # a message DOES say and passed over one asserting the opposite.
    # ⟳ 2026-10-21 r5 (2nd): 23 -> 25. The prose-matching apparatus was REPLACED by
    # structured tokens after r5 CLAUDE H1+H2 showed a one-token negation passed it and
    # its own list had no falsifier. Net +2: ONE entry RETIRED WITH ITS SUBJECT
    # (`unreachable_message_sound`, deleted), THREE added on the tokens and the renderer,
    # and one RE-POINTED rather than retired because its rule moved rather than died.
    # ⟳ 2026-10-21 ARCH F1: 25 -> 27. The two SHIPPED renderings, pinned.
    # ⟳ 2026-10-21 r6: 27 -> 28. The OUTPUT pin — r6 edited three unpinned body
    # literals and the suite stayed 111/111 while the reader was told the opposite.
    # ⟳ 2026-10-24, backlog #318: 28 -> 30 — `refuted` is in the vocabulary AND answers a finding;
    #   two #329 anchors re-pointed onto the new `ANSWERED` constant, nothing retired.
    "scripts/check-review-decision.py": 30,
    # ⟳ 2026-10-23: check-decision-scheme 86 -> 106. Trigger 3 changed its question (route
    # collapse -> a lost bet whose next route was never logged) and the `missed-escalation`
    # acknowledgment row joined. TWO entries RETIRED WITH THEIR SUBJECT — the collapse floor and
    # the collapse trigger's prospective filter, both in the deleted `t3_routes_collapsed` — and
    # THREE re-pointed (t2's last-BET read, the summary line's acknowledgment clause, and its
    # retroactive count), so they do not move this number. TWENTY-TWO added on `lost_bets`,
    # t3/t10 and their wiring, the acknowledgment's validation, and the readers taught to skip it.
    # ⟳ 2026-10-23 r1 fold: 106 -> 113. The acknowledgment became a CLOSING statement and moved
    # off `kind`: SEVEN added (a continued DEFER left to trigger 2, twice; a bet after an
    # acknowledgment; a second acknowledgment; its round count, twice; the acknowledged/unlogged
    # split). Nine RE-POINTED with the rename, and t10's retroactive WARN branch — unreachable
    # from any valid log — went with no entry of its own to retire.
    # ⟳ 2026-10-23 r2 fold: 113 -> 128. An acknowledgment now counts only while the review
    # corpus ON DISK shows its subject ended, converged, at the round it names. FIFTEEN added
    # (each refutation branch of `acknowledgment_rejection`, the rejected class and its reader,
    # main's corpus read and its CANNOT RUN, `review_rounds`' two refusals, and `half_verdict`'s
    # last-line and bold-line rules). Seven RE-POINTED to the signatures that gained `rounds`.
    # Two candidates REJECTED as equivalent: dropping `w != "coordinator"` (a coordinator entry's
    # verdict is always None, so the `v is not None` clause already excludes it) and reading
    # coordinator documents in `review_rounds` (their verdict is never read).
    # ⟳ 2026-10-23 r3 fold: 128 -> 107 — the ONE permitted kind of fall. Rounds 2 and 3 were
    # consecutive fold-induced rounds in the acknowledgment, THRASHING, and it was REMOVED.
    # THIRTY-FIVE entries RETIRED WITH THEIR SUBJECT: the acknowledgment row and its validation,
    # `acknowledgment_rejection`, `review_rounds`, `half_verdict`, main's corpus read, the
    # acknowledged/rejected classes and their trigger-10 reader, and trigger 2's last-BET read
    # (the only non-bet row it skipped is gone). EIGHT re-pointed — three of them back to the
    # text they had on master. FOURTEEN added on its replacement: the closed pin list in
    # `baseline.json` (`pinned_lost_bets`), trigger 3's exemption, and trigger 10's two halves.
    # ⟳ 2026-10-23 r4 fold: 107 -> 111. A pin names ONE BET, (subject, unit, route), so a later
    # loss on a pinned unit is not excused; and a PRESENT null pin list is refused. FOUR added
    # (the route carried by `lost_bets`, the route check, the three-part key, null-vs-absent);
    # THREE re-pointed to the parser's new presence test.
    # ⟳ 2026-10-23 r5 fold: 111 -> 119, the owner's option A. A `continued` DEFER that records
    # `rounds_at_termination` CLOSES its unit: trigger 2 FAILs only OPEN exhausted units, the new
    # trigger 11 WARNs on closed ones, and `validate_row` refuses a bet after a close. EIGHT added
    # (both triggers' filters, t11's guard and wiring, `closes_unit`, the named closed refusal,
    # and the field's two shape rules). Dropping the `continued` clause of `closes_unit` was first
    # written off here as equivalent; ⟳ r6 Codex measured it is NOT — a stopped DEFER followed by a
    # new unit then warns trigger 12 — and two existing cases already go red on it (269/271).
    # ⟳ 2026-10-23 r5 fold, second containment: 119 -> 125. A NEW unit on a subject after one of
    # its units was CLOSED is trigger 12's WARN (a restarted ladder, seen, not forbidden). SIX
    # added: the closure record, the began-after test, the same-subject test, the first-row
    # rule, t12's guard and its wiring. An `unit == closed` exclusion was DELETED rather than
    # mutated: the closed unit's first row is never after its own closing row, so it was dead.
    # ⟳ 2026-10-25: 125 -> 129 — trigger 4 SUSPENDED to a WARN by the owner pending backlog #327;
    #   four entries: back on the FAIL list, suffix dropped, "NOT a pass" dropped, discarded. None retired.
    "scripts/check-decision-scheme.py": 129,
    "scripts/check-goal-status.py": 7,
    # ⟳ 2026-09-16, backlog #137: 43 -> 47. The anti-drift falsifier changed AUTHORITY — it used to
    # read `schema-gates.yml`'s `docs/` path filters, and that file no longer has path filters,
    # because a workflow-level filter is what made the `schema-gates` check unrequireable. TWO
    # entries were RETIRED WITH THEIR SUBJECT (both mutated `workflow_docs_globs`, which is deleted)
    # and SIX added for the reader that replaced it. ⚠ The orphans were found by RUNNING the anchor
    # check, not by the keyword grep that preceded it — that grep missed both, which is this repo's
    # recorded "a refactor ORPHANS the mutation guarding it", anchors binding by TEXT.
    # ⚠ One of the six SURVIVED on first measurement and the case it named was the reason: a
    # whole-line shell comment is rejected by the `NAME=` match, not by the comment strip, so the
    # case passed for an AMBIENT reason while the clause it appeared to test was unfalsifiable. A
    # case driving a TRAILING comment on a real assignment was added and kills it.
    # ⟳⟳ 2026-09-16, r1 High (codex): 47 -> 50. The suffix ALLOW-LIST fail-open'd by
    # OMISSION — a new gate reading a `docs/…/rules.json` was invisible while the existing
    # gates kept the result non-empty, so the CANNOT-RUN guard passed and coverage shrank
    # silently. Reproduced by the reviewer, not argued. Fixed as a CLASS: `.md` answers *is
    # it prose* and an INJECTED existence check answers *is it a path*, the job the allow-list
    # had been doing by accident. Plus `_joined_path`, because a `pathlib` join holds no
    # `docs/…` literal at all. ⚠ TWO entries were re-anchored (the fix moved their text) and
    # ONE was DELETED rather than kept: `len(parts) > 1` is INERT — mutating it to `> 0` left
    # the suite green, because a one-constant join returns what the per-constant scan already
    # finds. A clause whose removal changes nothing cannot carry a mutation.
    # ⟳⟳⟳ 2026-09-16, r1 BLOCKING 1 (claude): 50 -> 49, and the count was WRONG IN A WAY
    # NOTHING CHECKED. Three entries mutated three clauses of ONE LINE, so all three shared
    # one anchor; `:1019` keys the duplicate refusal on the `old` half alone, refused two,
    # and `--mutate .` returned BEFORE STAGING — zero of 719 mutations ran, in the required
    # `verify` job. ⚠ Declared 50 while the LOADER ACCEPTED 48: this pin had never been
    # compared against the accepted population, only against the file. One entry is gone
    # for cause — the reviewer measured it strictly WEAKER than the entry it collided with
    # (it removed `suffix and` too, which Low 12 showed is unfalsified) and naming the same
    # case, so it added no coverage even once split. The predicate is now one clause per
    # line (`is_gate_data`) so each mutation has its own anchor.
    # ⟳ r1 High 2 fix: 49 -> 52. THREE entries for the completeness falsifier, and the
    # first of them is the one the reviewer pointed out did not exist at all: NOTHING
    # targeted `_gate_sources`' discovery loop, so deleting it left the suite green at
    # 153/153 while two of three gate directories vanished and the gate reported success.
    # ⟳ 2026-09-16: 52 -> 56. FOUR entries for the path-SHAPE guard, which exists because CI
    # and this machine DISAGREED on the same commit (`99f4da56`): 723 attributed locally,
    # 722 in CI, one mutation "RED but printed no `[FAIL]` line". A gate script DOCSTRING
    # mentioning a `docs/` path yields components up to 1450 bytes, and `Path.is_file()`
    # RAISES ENAMETOOLONG on those — except on Python 3.13+, which swallows that errno.
    # Shape is now decided before the disk is touched, so no python version can crash it.
    # ⟳ r2 (claude) 1 High + 5 Medium + 3 Low: 56 -> 61. FIVE entries — the `review_added`
    # DIRECTORY clause (High 1: dropping `p.startswith(REVIEW_DIR)` left the suite green, so
    # ANY added `.md` would have recorded a review round), the retired extension-less rule
    # (Medium 3), the bare-`docs` skip (Medium 2), the TOTAL path bound (Medium 4), and the
    # anti-drift ORDER — which needed `antidrift_verdict` extracted out of `main` first,
    # because the call site was unfalsifiable and the entry written for it SURVIVED
    # (Medium 6). ⚠ One entry was RENAMED rather than re-anchored: it claimed to re-admit
    # the shape that crashed CI, and measured, whitespace already rejects that (Low 8).
    # ⟳ r3 (claude) 1 High + 4 Medium + 3 Low: 61 -> 64. The empty-derivation CANNOT-RUN guard
    # (Medium 2: its case asserted only the exit code, which the COMPLETENESS prong returns by
    # another route, so deleting the guard left the suite green), `PATH_LIMIT`'s VALUE (Medium 5a:
    # the two bracketing cases left a 4,545-byte window, so 4096 — Linux's PATH_MAX, the wrong
    # value for the platform that raised — survived), and `.gitignore` (Low 6: the two prose
    # branches mutually masked, each surviving alone). ⚠ My first PATH_LIMIT cases built their
    # input FROM the constant, so the input moved with the mutation and could never pin the value:
    # literal lengths now.
    # ⟳ r4 (claude) 7 Low: 64 -> 66. The root-`.md` prose fallback (Low 4 — the OTHER half of a
    # mutual mask this lineage has now visited three rounds running: r2 L7 -> r3 L6 -> r4 L4) and
    # `verdict.pr_body` (Low 1 — the SAME "constant wearing a signature" shape this branch closed
    # for `prose_exceptions_cover.declared`, still live in the same file: closing one instance and
    # leaving the only other one is instance-not-class).
    # ⟳ 2026-09-24, backlog #176 round 3 fold, 66 -> 68. The r3 H2 pair, both on rules this file
    #   already had and read by truthiness or identity: `gate_ran` read with `not`, which credited
    #   `"gate_ran": "false"` with having seen the final tree, and `dirty` tested by `is None`,
    #   which let `[]` — a shape a COMMITTED verdict actually carries — classify as a real head
    #   with an empty overlay. Distinct from the two `if False:` entries already on those lines:
    #   those delete the rule, these weaken it, and the four are attributed to disjoint cases.
    # ⟳ 2026-11-03, backlog #426 + its r1 fold, 68 -> 90: the master-delta clear (+9), then the r1
    #   fold (+13) — a failed HEAD `ls-tree` raising, the merged-tree lookup's failure branch, the
    #   shared `merge_onto`, and every merge-attribute source neutralised for `merge-tree`.
    # ⟳ 2026-11-03, r2 fold, 90 -> 94: the per-source `-c` flags and the `info/attributes` refusal
    #   (-6) give way to running the merge in an ISOLATED repository (+10: its environment, its
    #   GIT_DIR, its borrowed objects, its PATH, and its failure to build).
    # ⟳ 2026-11-03, r3 fold, 94 -> 102: both tree lookups list the WHOLE tree and select exact
    #   names (+7: each lookup as a pathspec again, `-r`, `-t`, the precompose `-c`, the exact
    #   selection, the isolated runner's decoding), and the temp dir removed on a crash (+1).
    # ⟳ 2026-11-03, r4 fold, 102 -> 109: every git read captured as BYTES (+6: the shared reader,
    #   `_git`, the isolated runner, both branch-level diffs, `git_text`'s error handler), and the
    #   absent == absent arm of `master_explains` restored (+1).
    "scripts/check-review-recorded.py": 109,
    # ⟳ 2026-09-14, r11: this file JOINS the manifest — R4 widened-debt 8 -> 7, removed from
    # `WIDENED_MANIFEST_DEBT` in this same commit, which that rule requires as an identity and not
    # a ceiling. It is the producer half of the mechanism the file above consumes, and it had gone
    # from zero mutations to zero while gaining `reviewed_state`. r11 found THREE of its new rules
    # surviving mutation — two of them regressions of findings earlier rounds had already paid for
    # (r3's "a deletion is RECORDED, not skipped" and the producer half of r2's mode contract) —
    # plus a case that could not fail at all, because the fixture held no file matching its own
    # subject. Nine entries: the two the earlier rounds bought back, the destination-mode read, the
    # throwaway index, the unchanged-file rule, the null-vs-empty distinction, the recorded prompt,
    # and repository redirection in both directions.
    # ⟳ 2026-09-23, THE VERDICT-PATH COLLISION — 12 -> 16, and it is the THIRD measured
    # instance of one defect: `verdict_path` DERIVES the verdict name from `--out`'s basename,
    # so the namespace has no allocator and two reviews choosing the same output name write the
    # same file. A round-3 run with `--out codex-r3.md` overwrote a COMMITTED
    # `codex-r3.verdict.json` from an earlier session; both records honestly said
    # `"review": "codex-r3.md"`, so the stem cannot tell them apart. ⛔ `check-review-recorded`
    # catches a MISSING verdict and the overwritten file shows as MODIFIED, not ADDED — so
    # nothing in the repo could see it. FOUR entries, because the rule has four directions and
    # three of them are ways to be wrong in the SAFE-LOOKING direction:
    #   * the refusal dropped (the defect itself);
    #   * `tracked is None` read as answerable — the RULE's fail-open;
    #   * ⭐ git's rc=128 read as "not tracked" — the FETCH's fail-open, which SURVIVED 101/101
    #     until a case drove it. git answers three ways and the first two cases drove two of
    #     them. ⟳ r4 M1: the reason first written here — "`--out` lives outside the repo, where
    #     rc=128 is what you get" — is FALSE at the call site, because the query is made on
    #     `vpath`, which is always joined under `REPO_ROOT`. What reaches it is `REPO_ROOT` not
    #     being a git repository: this very harness stages a `copytree` with no `.git`.
    #   * the explicit `--verdict` escape removed — the OVER-refusal direction, which would
    #     break the legitimate replacement and teach callers to route around the guard.
    # ⟳ 2026-09-23, backlog #176: 28 -> 29, AND THE CARDINALITY IS THE LEAST INTERESTING PART OF
    # THIS MOVE — THIRTEEN ENTRIES WERE RETIRED AND FOURTEEN ADDED. A pin that only counted would
    # have read +1 and said nothing about a manifest whose membership changed by 93%.
    #
    #   ⑴ RETIRED WITH THEIR SUBJECT — 13, the only sanctioned kind of fall. Every one of them
    #     mutated the ALLOCATOR for a namespace derived from `--out`'s basename: `run_token` and
    #     its three inputs, `TOKEN_HEX`'s width, `verdict_collision` in three directions,
    #     `path_is_tracked`'s fail-open, `refusal_verdict_path`, and `build_probe_repo`, which
    #     existed only to build the world `path_is_tracked`'s cases needed. That namespace is
    #     GONE — the caller supplies the review's identity — so the code the anchors name does not
    #     exist and the entries are retired with it rather than orphaned. ⚠ The four entries
    #     recorded immediately above (2026-09-23, "THE VERDICT-PATH COLLISION") are among them:
    #     they were correct about the instance in front of them and the architecture review
    #     convened on THRASHING found the root one layer down.
    #
    #   ⑵ ADDED FOR THE NEW BEHAVIOUR — 14, and they are not a translation of the old ones. Three
    #     hold the IMPORTED filing grammar (a private suffix rule, a defaulted writer, the
    #     coordinator counted as a half); two hold the CI JOIN KEY, which is the whole point of
    #     #176 and whose killing case is driven through the shipped `check-review-rounds.
    #     verdict_problems` rather than a copy of it; two hold the PROMOTION's destination; three
    #     hold the one overwrite policy in its three directions; one holds the second call site
    #     asking the filesystem again; one holds the promoted file's CONTENT; and two hold the CLI
    #     — the retired `--verdict` naming its retirement, and `--review-id` staying REQUIRED.
    # Every anchor was verified to resolve exactly once AFTER the code was final, and all 29 were
    # driven against a green control: 29 killed, 29 attributed via the case each names.
    # ⟳ 2026-09-23, folding review-identity-176 round 1: 29 -> 40. ELEVEN added, none retired.
    # FOUR restore r4 M5, whose entry this slice retired under an argument that covered the
    # deleted ALLOCATOR and not the invariant — *a refusal must not write to the path it is
    # protecting* — which the slice then violated with a new refusal: the refusal namespace
    # collapsing onto the protected path, the selection ignoring `refused`, the record
    # dropping the field the consumer reads, and `main`'s refusal branch dropping the flag
    # (that last one killed through a SANDBOXED end-to-end drive, because a call site is
    # exactly what pure cases cannot reach). THREE hold the one-segment rule on --review-id
    # (H1) at the predicate, its two clauses, and the gate that applies it. THREE hold the
    # --out location refusal (M5) in both directions plus its wiring — the condition three
    # texts asserted the quarantine safety on and nothing enforced. ONE holds the exit code
    # that separates "the gate ran and the review is not filed" from CANNOT RUN (M4).
    #   ⚠ THE TWO --out ENTRIES OVERLAP THEIR ANCHORS ON PURPOSE, and they are different
    #     behaviours verified by ATTRIBUTION rather than by assertion: one DROPS the
    #     subdirectory arm (under-refusal — 2 red cases) and one refuses the COMPLEMENT
    #     (over-refusal — 9, including the documented scratch shape, which is the direction
    #     that would teach callers to route around the guard). The r11 `tail_candidates`
    #     split is the precedent for clearing the duplicate-anchor rule this way.
    # ⟳ 2026-09-24, folding round 2: 42 -> 45. FOUR ADDED, ONE RETIRED WITH ITS SUBJECT, AND THREE
    # RETARGETED — one of which had gone orphaned on the previous fold and was caught by CI.
    #   ⑴ RETIRED — 1, A SANCTIONED RATCHET FALL. `r2: reserved device names stop disqualifying an
    #     id` is gone because the RULE is gone (r2 Claude half, M2). It was wrong in both
    #     directions — measured, `aux-tokens-r1-codex`, `com1-migration-r1-codex` and
    #     `prn-cache-r1-claude` were REFUSED while the genuinely reserved `CON.md-r1-codex` and
    #     `NUL.json-r1-codex` were ADMITTED, because `split("-")[0]` is not the Windows rule, which
    #     keys on the base before the first PERIOD — and its stated justification was false: all
    #     three `runs-on` lines in `.github/workflows/` are `ubuntu-latest`. ⚠ The entry was KILLED
    #     THROUGH THE CASE THAT ENCODED THE ERROR, so it was a green guard over a property the code
    #     did not have; repairing the token would have kept a rule protecting nothing measured. The
    #     same reason is written above `MAX_ID_LEN` in `scripts/codex-review.py`, at the code.
    #   ⑵ RETARGETED — 3. `r1 H1: the relative components` and `r2: whitespace` moved when the
    #     predicate became `segment_problem`, which RETURNS THE RULE IT BROKE (M3); `r1 H1:
    #     review_identity stops applying the one-segment rule` moved with its call site.
    #   ⑶ ADDED — 4. TWO hold M4's boundary, which the previous fold stated as VERIFIED and was
    #     not: its "AT the cap" case was 199 against a cap of 200, and the reviewer drove
    #     `> 200 -> >= 200` SURVIVING at 162/162 — one entry mutates the comparison, the other
    #     moves `MAX_ID_LEN` so the two cases cannot silently agree with a cap that shifted. TWO
    #     hold M3: the reason returning the WRONG rule, and the reason being computed and dropped,
    #     which is the state the message was in before this fold.
    # ⟳ 2026-10-29, backlog #121: 45 -> 49 — the head is the REVIEWED tree's, named in the record;
    #   r1 (PR #439) 49 -> 57 — Codex runs there, under the same git environment, and the --out
    #   refusal and the watch cover that tree's docs/reviews. r2 57 -> 60 — `--out` is resolved
    #   through its symlinks before `..` (four added), the lexical-spelling entry retires with the
    #   comparison it mutated, and two M5 entries are rebound. r3 60 -> 64 — the --out refusal
    #   also compares by IDENTITY (`same_dir_or_inside`), for a case-folding volume. r4 64 -> 66 —
    #   the refusal is ONE identity rule over each whole checkout, so the r1 M5 "only the root" and
    #   r2 X5 "trees unresolved" entries retire with the comparisons they mutated; four added for
    #   the exclusive-create-and-rename capture (X2, X3) and the device half of identity (X4).
    #   r6 66 -> 67 — the refusal also compares each checkout's RESOLVED docs/reviews (X1, a
    #   regression against master when docs/reviews is a symlink out of the checkout).
    #   r7 67 -> 71 — master's rule is kept VERBATIM beside the identity rule and either refuses
    #   (X1, a symlink nested in docs/reviews): the OR's master branch, its reviewed-root half, its
    #   lexical reading, and main asking it before --out is resolved.
    #   backlog #508 71 -> 76 — the reviewer's answers to the merge gate's flagged lines: the finding-wins
    #   rule, the whole-line match, the block appended in main(), the answers in the OK verdict, the field.
    #   ⟳ #508 r1 76 -> 84 — the parser: loose dissent (2: the line rule, the id's case), strict assent
    #   outside quotes (fence and comment: 6 — the gate, the comment open, its continuation, its close,
    #   the fence close, the fence character).
    #   ⟳ #508 r2 84 -> 87 — the free-text parser is REPLACED by one answers section: the mention rule and
    #   the six fence/comment entries are deleted with their code (-7); three re-anchored; ten added (a
    #   malformed line skipped, only its ids, the id's case, the FIRST section, no VERDICT: stop, a blank
    #   line, a loose heading, no section read whole, an empty finding, no right-strip).
    #   ⟳ #508 r3 87 -> 91 — ONE heading (r3 m1): a second heading not malformed, an id after VERDICT: not
    #   malformed, the malformed tail judged only in the loop, findings only before VERDICT:. Five re-anchored.
    "scripts/codex-review.py": 91,
    # ⟳ new (review-round cap, 2026-10-31): a Claude half's verdict — one entry per refusal, plus the
    # three fields a consumer reads (gate_ran, the full head, the clean overlay). ⟳ PR #457 r2: 19 -> 21,
    # the fixed-position reads (the `\n` split, the unstripped first line); seven retargeted.
    # ⟳ backlog #508: 21 -> 23, the filed review's answers into the record (call site and field).
    "scripts/record-review-verdict.py": 23,
    # ⟳ 2026-09-07, R4 manifest debt 7 -> 6. Writing these found FIVE of the guard's 16 cases
    # unable to fail via the mechanism they are named after — all one shape: the FIXTURE used an
    # input that a DIFFERENT rule filters first, so the named rule was never reached.
    #   * `lib/…` and `parse.ts:42` are stopped by the lowercase-prose rule, not by the path and
    #     file:line guards those two cases are named for. Both only bite when the first segment is
    #     CAPITALISED (`MyModule/index.ts` -> `MyModule`, `Parse.ts:42` -> `Parse`).
    #   * `epsilon` and `omega` are lowercase, so the mode-reset and prose-termination branches
    #     could both be deleted and the cases stayed green. MEASURED, then capitalised.
    #   * `all(t > num for t in owners)` was unfalsifiable: every fixture symbol had exactly ONE
    #     producer, and with one owner `all`/`any` agree and `>`/`>=` agree.
    "scripts/check-plan-task-order.py": 9,
    # ⟳ 2026-09-08, the plan-mode retirement. A NEW file, 8 entries. It fences the tag grammar
    # this very script used to parse, and it exists because retiring plan mode removed the only
    # reader those tags ever had — so `no plan embeds code` went from enforced to merely true.
    # ⚠ Three of the eight are on the FENCE RULE, and that is where the defect actually was: the
    # first version had no fence rule at all, on a claim about `extract()` written from reading
    # it. Its first live run flagged a committed review document, and running `extract()` on
    # those exact bytes returned `files=[]` — the parser had never seen the tag. The mutations
    # pin each branch of the rule that replaced the guess (column-0 opens, indented does not,
    # the skip ends at the closing fence), because a rule derived from a measurement is only as
    # durable as the case that re-takes it.
    "scripts/check-plan-file-tags.py": 18,
    # ⟳ 2026-10-29, backlog #393: the plan-leak push gate joins at 32, declared sum 2512 -> 2544,
    # pinned in the commit that creates it. Each entry is killed by the case it names.
    # ⟳ same day, the owner's 8-word window and the LOCAL-only phrase: +6 for the phrase channel, -> 38.
    # ⟳ PR #443 r1, the REDESIGN onto git's pre-push hook: the entries are rebuilt over the new rule and
    # entry points (one per Codex input X1-X11, the installer and --status), -> 54; then +11 for the
    # security review's folds (commit/tag/path metadata, the SessionStart enable-or-warn), -> 65; then the
    # second pass (added paths from --diff-filter=A, tags peeled): -2 header-path entries, +5, -> 68.
    # ⟳ PR #443 r2 (SPLIT): +8 for the folds — forced diff prefixes and the unreadable-path refusal (F1),
    # GIT_NO_REPLACE_OBJECTS (F4), the absolute hooks path and its upgrade (F3), the redacted NAME hit (F5) -> 76.
    "scripts/check-plan-leak.py": 76,
    # ⟳ 2026-11-01, backlog #438: the per-PR battery runner joins at 23, pinned in the commit that creates it.
    # Each entry is killed by the case it names: the three FAILS-IF lines of the row, CANNOT RUN, the tracer.
    # ⟳ PR #465 r1 fold: 23 -> 10. The skip ledger, its tracer and its digest are DELETED (both halves reproduced
    # false greens through them; the skip saved ~50 s of 8m39s), so 17 entries are retired with their subject,
    # not orphaned; 6 survive (exit status, NOT_LOCAL, empty set, --base, moved manifest) and 4 are new (the
    # run's exit code twice, the other ci.yml jobs printed OUT OF SET, an untracked manifest counting as moved).
    # backlog #402 (PR #450 r1): 10 -> 12, the count check runs SCOPED locally and a stale SCOPED_LOCALLY name refuses.
    "scripts/gates-for-pr.py": 12,
    # ⟳ 2026-08-31, backlog #76/#77: the shared page chrome. Adding it found TWO
    # vacuous cases of my own — a "dirty tree" assertion compared against a
    # NON-repo, so it differed by the UNKNOWN text and never by the dirty flag,
    # and the git-cannot-launch branch was unreachable from a temp dir.
    # ⟳ 2026-10-18 (backlog #300): 11 -> 20. Nine entries for the reachability guard;
    # one of them — "the has_control gate is dropped from reachability" — exists only
    # because it SURVIVED first, masked by a fixture that tripped the next gate.
    # ⟳ 2026-10-18, r1 fold: 20 -> 31. The r1 redesign ORPHANED 7 of the 20 (the pin
    # moved from sticky to a script-applied fixed class), and SIX new behaviours had no
    # mutation at all — the duplicate-id refusal, the consumer refusal and the
    # comment-stripping all survived deletion with 111/111 green.
    # ⟳ 2026-10-18, the r5 fold: 45 -> 51. SIX entries whose subject is THE DECLARED BOUND
    # rather than a behaviour — five tighten the scan to handle one of r5's out-of-scope
    # shapes, the sixth deletes the subject sentence from `assert_wired`'s docstring. They
    # exist because the bound is the fix: the owner chose "narrow the subject", and a bound
    # nothing can falsify is a sentence. ⚠ Every one was measured as a sever BEFORE being
    # written here, and two of the first five did NOT redden — the nested-<noscript> sever
    # was patching a branch the nesting does not happen in, and the CSS-comment case was
    # asking the REGEX while the fix would land on the GUARD, so it stayed green at 163/163.
    # Both are now pointed at what the code actually sees.
    # ⟳⟳ 2026-10-18, the 2b fold: 51 -> 59. Eight entries for "under the title AND
    # pinned": the top edge, the slot's reservation, the slot wrapper, a DOUBLE bar (rounds
    # 2 and 4's duplicate-id defect, now mutated rather than argued), the conditional pin,
    # the measure-while-unpinned feedback guard, place_bar's insertion point and its shield.
    # ⚠ Three EXISTING entries were re-anchored, not added — `bottom:0`, the <body>
    # reservation and `classList.add` are spellings this fold removed, and an entry whose
    # anchor is gone reports NOT MEASURED rather than failing, which is how two orphans rode
    # this branch unnoticed until the real harness named them.
    # ⟳ 2026-10-19, the r6 fold: 60 -> 64 net. FIVE added (the pin threshold, the tail's
    # source, the re-arm, the comment strip and its space-not-deletion rule) and ONE
    # RETIRED WITH ITS SUBJECT: "CSS comments are stripped AT THE GUARD" described a
    # TIGHTENING, and round 6 applied that tightening, so the behaviour it mutated is now
    # the delivered one. Its inverse carries the coverage. That is the one sanctioned kind
    # of fall — the entry is retired because its subject is gone, not orphaned.
    # ⟳ 2026-10-19, r6 CLAUDE fold: 71 -> 70. ONE entry retired on the reviewer's argument —
    # `ctls=[]` exercised the `m===Infinity?0:` fallback, which is unreachable on the
    # delivered path, and never tested the property its name claimed; it was killed purely
    # by a substring vanishing. The whole tail computation is now covered by an entry that
    # severs it as ONE exact expression, which is what the reviewer's two green severances
    # showed was missing.
    # ⟳⟳ 2026-10-19, the r7 fold: 74 -> 83. NINE, each measured as a sever against the
    # delivered file BEFORE being written here, and five are round 7's own findings: no
    # re-measure on unpin (the bound I had written was FALSE), the pin's state guard, the
    # own-id helper plus its two reported elements, slot selection, interactive ancestors,
    # and the TWO theme-persistence statements the switcher's identical calls were hiding —
    # the reviewer deleted theme persistence entirely with the suite at 201/201 green.
    #
    # ⚠ FOUR OF THE NINE ANCHORS WERE DERIVED, NOT TYPED, and that is a lesson about this
    # file rather than about these entries: every exact-expression CASE added here creates a
    # SECOND occurrence of the emitted text it asserts, which silently breaks any anchor
    # keyed on that text. Hand-anchoring failed four times in one session before the anchor
    # was computed by widening backwards until the block occurs exactly once.
    # ⟳ 2026-10-19, the r8 fold: 83 -> 88. FIVE — the slot-vs-bar question r7's own fix got
    # one `.chrome` wrong, its fallback, the interactive DECREMENT that had no shield while
    # its increment did (the comment demanding exactly that guard is the line after the
    # counter's declaration), the refresh assertion the sibling span was satisfying, and the
    # interactive set itself.
    # ⟳ 2026-10-19, the r8-codex fold: 87 -> 89. The per-slot reserve (r8 High: a
    # document-level reserve consumed by a CLASS selector inflated a slot nested inside the
    # bar being measured — 225 -> 1965px in two seconds) and `assert_wired`'s label, which
    # the reviewer severed while the suite stayed green: dropping it from KNOWN_UNVARIED was
    # lexically correct and the parameter was still indistinguishable from a constant.
    "scripts/page_chrome.py": 114,
    # ⟳ 2026-09-16 — `peer-sites.py` arrives WITH its manifest rather than as debt, which is
    # backlog #122's lesson applied at birth: that file spent months unratcheted and seeding it
    # immediately found two live defects. Probing these seven before shipping found three more in
    # the new script itself, one of them a fail-open (`changed_lines` returned an empty set on a
    # git failure, indistinguishable from "nothing changed").
    "scripts/peer-sites.py": 25,
    # ⟳ 2026-09-16, backlog #122 — `explainer-serve.py` joins the manifest. It was the largest
    # UNRATCHETED file in `scripts/`: 149 real cases, none ever shown able to fail, on a server
    # that emits pasteable shell commands. Seeding it immediately found TWO surviving mutations —
    # `SERVABLE` could be widened to serve `.env.local`, and `SRC_REASONS` could gain a member —
    # both now cased. ⚠ The 17 entries are deliberately NOT one-per-function: an entry is admitted
    # only when its kill is ATTRIBUTABLE, which `check-plan-code` decides by matching `expect`
    # against a parsed case name by EXACT EQUALITY.
    # ⟳ CORRECTED 2026-09-16 by round 1's review, which MEASURED the claim this comment first made
    # — that a raise-dying case "can never be named". **False.** Feeding the real `parse_fail_names`
    # and the real matcher an `expect` carrying the full `{name} — AssertionError: {msg}` string
    # attributes fine, because `_Forbidden`'s message is built from two call-site literals and is
    # deterministic. The honest bound is narrower and survives being checked: naming a raise kill
    # means embedding the exception type AND message, which is unattributable the moment that
    # message carries runtime data — the same sweep produced a `ValueError` naming a machine-
    # specific temp path — and couples the entry to one failure mode of the case even when it does
    # not. That still supports converting the raise to a value (the case `driving /src/ never
    # consults the environment`), which is why the decision stands and only its reason changed.
    # ⟳ 2026-10-22 (work lines, always current): 46 -> 48 — the `work-lines` Refresh allow-list
    # entry, and the STALE_EXEMPT set that makes its empty source list a stated decision.
    # ⟳ backlog #389: 48 -> 48 net — two entries RETIRED with the work-lines page (its Refresh
    # allow-list key and its STALE_EXEMPT entry no longer exist), two NEW for the redirect from its
    # url to the frozen archive (the do_GET branch, the .html url).
    # ⟳ #389 round-1 fold: 48 -> 50 — retirement moves from URL spellings to the CANONICAL page
    # (X2 + C1): the url-map entry retires, three new pin the canonical match, the index filter and the
    # root-only scope; the redirect and the no-extension rule are re-anchored on `page_candidates`.
    # ⟳ #389 round-2 REDESIGN to identity: 50 -> 54 — three round-1 entries retire with the canonical-path
    # rule they pinned (raw url, name-only index, subdirectory); seven new pin `retired_as`: (a) the name,
    # its casefold, its normalisation, its root-only scope; (b) samefile, its symlink exclusion; and the
    # index calling it. The decode-before-extension entry re-anchored (its line is now repeated).
    # ⟳ #389 round-3 (route SPLIT): 54 -> 59 — the symlink chain is walked link by link in ONE classifier.
    # Two r2 entries retire with the name-or-final-file rule (the bare name check, the name-only index);
    # seven new pin every traversed name, the walk itself, the root bound, the hop bound, the 403, the
    # index's call and the no-file name; (b) now pins hard links, and its symlink exclusion is re-anchored.
    # ⟳ #389 round-4 (terminal) fold: 59 -> 61 — classification and serving share ONE selection
    # (`served_candidate`): the named mismatch mutation, and serving a non-file candidate.
    # ⟳ #389, CI red on PR #434 (Python 3.12 raises RuntimeError from resolve() on a loop): 61 -> 62 —
    # every serve/index resolve goes through `resolve_or_none`; one entry pins RuntimeError in it, and the
    # raw-containment entry is re-anchored onto the helper's call.
    # ⟳ backlog #497 (the owner 2026-11-04 01:07, refresh on a click): 62 -> 64 — the goal tree's own
    # 60 s rebuild bound, and the timeout reply naming the bound it actually waited.
    # ⟳ same day, review round 2's fold: 64 -> 65 — the rebuild gets only what is LEFT of the click's bound (X2).
    # ⟳ backlog #408: 68 -> 69 — a Refresh press routes through regen-pages.py `--page <key>`, each key as itself.
    # ⟳ its review round 1 (Codex X3): 69 -> 72 — the runner in a process group of its own, SIGTERM before
    # SIGKILL on a Refresh timeout, and the press wired through `run_in_group`.
    # ⟳ its review round 2 (F4): 72 -> 73 — the post-SIGKILL drain of a Refresh timeout is BOUNDED.
    # ⟳ backlog #627: 73 -> 87 — the serve-source rule (overlay only on master's base, an unedited page is
    # master's), the fetch's rate limit, bound, failure recorded and cleared, the footer, the yellow bar, preview
    # detection, master's bytes for an overlay, the no-copy notice, a merged page served, the suite refusal armed,
    # and (87) no fetcher built inside the suite.
    # ⟳ #627 review round 1: 87 -> 105, none retired (nine re-anchored to the one chooser) — the handler's fetch
    # note, poke, ?source=local, /_rev's resolver, kind and failed flag, the suite whitelist, an unreadable object,
    # / and /latest from master, a local link, the merge-base ancestor, case folding, the bar's quoted href, a poke
    # never waiting on another's fetch, a running fetch said, the port range, the 'committed' label, the base prefix.
    # ⟳ #627 review round 2: 105 -> 112, none retired (four re-anchored: the fetcher guard, the page poke, the
    # index's page list, the port range) — a local retired verdict losing to master's page and the retired name
    # asked first (Codex M1), the fetcher's copy guard (M2), the index's poke and its fetch note (M3), and
    # port_from's ASCII shape and caught int() (m4).
    "scripts/explainer-serve.py": 112,
    # ⟳ 2026-09-01, backlog #79: the theme-token coverage guard joins the manifest in the same
    # commit that adds it, rather than as a follow-up. Its four entries cover both ratchet
    # directions (a token stops being forced OUT of the allowlist; the allowlist may name a
    # token that no longer exists), the cannot-run arm (a missing shim block reading as an
    # empty palette — the fail-open that would make it pass about nothing), and the
    # declaration parser (counting a MENTION as a declaration, which would let a page
    # "cover" a token by talking about it).
    "scripts/check-theme-token-coverage.py": 4,
    # ⟳ 2026-09-01, backlog #69 follow-on (task #203): the external count observer joins the
    # manifest. Its eight entries cover the printed-total parser (first-match vs last-match — the
    # defect it found in ITSELF), the `passed` requirement, the `N of M` arm, BOTH directions of
    # the population ratchet, the borrowed-name refusal, and both arms of `declares`.
    # ⚠ ADDING IT FOUND TWO DEFECTS IN THE SUITE IT WAS MEASURING, both of the same shape as the
    # ones this file already records: (1) `a ratio on a line without the word is ignored` was
    # VACUOUS — the stray ratio sat BEFORE the real summary, so last-match-wins discarded it and
    # deleting the `passed` filter still returned 8; (2) the borrowed-name case re-derived the
    # comprehension instead of calling it, so deleting the real rule left the case green. A
    # second implementation of one rule, tested against itself.
    # backlog #402 (2026-10-30): 8 -> 21, the scoped mode — the dependency rule, the three change
    # sources, the --only refusal, and `only` scoping the runs but never the population ratchet.
    # PR #450 r1 fold: 21 -> 23. +3 (a rename counts both names at two diff sources; propagation reaches a fixed point),
    # -1 ("string references are closed transitively too" is retired with its subject: closure is now the rule).
    # backlog #487: 23 -> 29, the suite pool — pool width, completion-order reporting, a raising
    # worker, a timed-out suite, a shared home, and the core-count cap.
    # PR #487 r1 fold: 29 -> 36, a timeout kills the suite's whole process group (own session,
    # SIGKILL after SIGTERM), a signal-killed suite is CANNOT RUN, a CANNOT RUN hides no red suite,
    # and `main`'s --jobs wiring and its refusal of 0.
    # ⟳ 2026-11-06 backlog #506 r2: 36 -> 34 — its three printed_total/RATIO entries moved to check-plan-code.json
    # with the rule (`summary_total`); one entry pins that printed_total still reads the borrowed rule.
    "scripts/check-selftest-counts.py": 34,
    "scripts/check-sentinel-meanings.py": 5,
    # ⟳ 2026-09-07. First of the four guards that PR #247 made stageable: their subjects
    # live outside scripts/, so before HARNESS_TREE their control could never be green.
    # One mutation per case — the suite has exactly six, and each is now killed by one.
    "scripts/check-storage-grant-pin.py": 6,
    # ⟳ 2026-09-13: the CI storage fixture's falsifier, pinned in the commit that creates it.
    # Its predecessor was a grep inside the workflow that survived 3 of 5 mutations, so this
    # manifest exists to prove the replacement does not.
    "scripts/check-storage-independence.py": 16,
    # ⟳ 2026-09-06, backlog #99: the Stop guard and its driver BOTH join the manifest, in the
    # commit that changes their decision paths. Only ONE of them is R4 debt — begin-plan.py is
    # not a `check-*` guard, so `discover_guards` never saw it and it was never counted as owed.
    # MANIFEST_BASELINE therefore drops 22 -> 21, not 20, and the number came from running
    # check-ratchet-contract.py rather than from arithmetic (this file's own recorded lesson:
    # a second implementation of the population rule drifted by one).
    #
    # The ten check-plan-progress entries exist because the defect being fixed was a guard that
    # went QUIET, so the mutations are weighted at what the guard SAYS, not only at what it
    # returns: dropping the count, dropping the human's pause reason, and — the one that matters
    # most — collapsing WARN from 3 onto 1, which would make a Python traceback indistinguishable
    # from a pause warning and turn the fail-closed path in block-idle-stop.sh into a fail-open
    # one. Two more assert the pause escape still cannot BLOCK on either cannot-run arm.
    #
    # The seven begin-plan entries split the same way: three on the refusal happening at all and
    # on the plan staying byte-identical when it does, two on the refusal's TEXT (a refusal that
    # stops naming `--resume` strands the reader in #99's own state with no discoverable exit),
    # and two on `--resume` — one for a write-back that never clears, one for a clear that takes
    # the `plan:` pointer with it.
    # ⟳ 2026-10-22 (work lines, always current): 17 -> 22 — the record at the Stop hook's clear
    # (Option A's first clear site), the page rebuild there, the rebuild never changing the
    # stop's verdict, the fully-ticked rule, and an unknown branch being omitted.
    # ⟳ 2026-10-22, work-lines-always-on r1 fold: 22 -> 29 — the optional-step boundary (its
    # breadth, and the record running inside it), the branch taken from the SENTINEL rather than
    # from git at clear time (asked, ignored, stripped at the clear site), an undecodable branch
    # name, and the lookup answering None. Two r1 anchors re-anchored onto the boundary's call.
    # ⟳ 2026-10-22, owner's option A (the parent holds within ONE session): 29 -> 31 — the
    # session copied into the record, and a failed new record removing the old one.
    # ⟳ 2026-10-22, work-lines-always-on r2 fold: 31 -> 34 — record BEFORE the clear, the
    # rebuild as its own optional step, and the clear never querying the branch. Four entries
    # re-anchored onto the split `run_optional` calls.
    # ⟳ backlog #389: 35 -> 32 — the Stop hook's work-lines rebuild retired with the page: its three
    # entries (the rebuild call, its never-raises boundary, its separation from the recorder) go with
    # it; the mandatory-clear entry is RE-ANCHORED, since the clear it pins remains.
    "scripts/check-plan-progress.py": 32,
    # ⟳ 2026-09-07. Five targets in the PURE rules: the ternary probe's optional-chain
    # exclusion, the alias fullmatch, ALIAS_RHS's repeat quantifier, and the `||` and `??`
    # patterns. Verified through check-plan-code's OWN run_mutations, not a copy of it.
    "scripts/check-producer-enumeration.py": 5,
    # ⟳ 2026-10-22 (work lines, always current): 25 -> 35 — Option A (the last finished plan as
    # parent, merged -> started, cannot-decide -> no marker, the --finish record), the rebuild
    # after a state change, the banner's Line row (printed, rendered, no invented head), and two
    # unanswerable `gh` replies.
    # ⟳ 2026-10-22, coordinator verification of 7fdd335c: 35 -> 41. The merged-only query read
    # "no merged PR" as "still open"; the rule now needs an OPEN PR. Three entries re-anchored
    # with the code they guard, six added — one per decision branch of `gh_pr_line_state` and its
    # caller, plus the old `--state merged` query itself.
    # ⟳ 2026-10-22, work-lines-always-on r1 fold: 41 -> 49 — the branch written at ARM time
    # (omitted, looked up as None, stripped at --finish), both optional steps inside the boundary,
    # the open question asked directly (gh's 30-result default), the 8s timeout, and the escaped
    # Line words. Four anchors re-anchored onto the rewritten `gh_pr_line_state` and `cmd_finish`.
    # ⟳ 2026-10-22, owner's option A: 49 -> 53 — a different session starts a line (no `gh`),
    # an unknown session records no marker, the fingerprint check, and `session:` at arm time.
    # The arm-time `branch:` entry re-anchored onto `render_sentinel`, whose call it shared.
    # ⟳ 2026-10-22, work-lines-always-on r2 fold: 53 -> 56 — OPEN in the second `gh` answer,
    # the full CommonMark escape set, and --finish never querying the branch.
    # ⟳ 2026-10-22, work-lines backfill: 56 -> 58 — a re-arm keeps a reconstructed link's
    # `parent-source:` label (read on re-arm, and written by render_plan).
    # ⟳ 2026-10-22, banner-thread-armed r3 fold, 56 -> 57: the banner `Line:` resolves a slug
    # held in two checkouts through `gen-work-lines.row_for` (r3 Claude F5); the new entry puts the
    # bare-stem lookup back and is killed by the two-checkout case.
    # ⟳ r6 fold, 57 -> 58: `work_line` re-keyed by the display label is killed by F5c.
    # ⟳ 2026-10-23, merging master (PR #386) into the backfill: 58 + 2 = 60, both kept.
    # ⟳ backlog #389: 69 -> 68 — the after-every-command work-lines rebuild retired with the page.
    "scripts/begin-plan.py": 68,
    # ⟳ 2026-09-06, backlog #78 half (2) follow-on: the FIRST payment against the R4
    # manifest debt (21 -> 20). Its FAIL-line format had to be fixed in the same change —
    # it printed `  ✗ {label}: got …`, which this file's attribution parser cannot see,
    # so every mutation here would have killed the suite UNATTRIBUTABLY.
    "scripts/check-gate-falsifiability.py": 5,
    # ⟳ 2026-09-07. Four targets in `backlog_shape_errors`, the PURE half: CELL_SPLIT's
    # escaped-pipe lookbehind, the column-count comparison, the delimiter-row threshold, and
    # the prev_was_row flag a split table depends on.
    "scripts/check-docs.py": 5,
    "scripts/check-explainer-delivery.py": 5,
    # ⟳ 2026-10-21: 5 -> 6. EXEMPT reaching the duplication rule.
    # ⟳ 2026-11-11, marketplace-inventory merged with master: 6 -> 11. The branch's five (the `*.html`
    # widening, the citing-site stageability rule and its three predicate arms) join master's EXEMPT one;
    # both sides grew from the same base 5, so the merge is additive. `.githooks/` joined STAGEABLE_PREFIXES
    # because master added it to HARNESS_TREE, and the identity case went red until it did.
    "scripts/check-canonical-source.py": 11,   # r6 redesign: the inverted-restatement mutation
    # ⟳ 2026-09-19, the feature hub. SEVENTEEN, one per rule `check_nodes`/`check_cross`/
    # `backlog_areas` decide — the plan's own draft said five, which left both cross-file anchor
    # directions, the claimed-twice rules, the wrapped-line refusal, the `now` exclusion, the area
    # CELL INDEX and the escaped-pipe lookbehind with no falsifier at all. Two of the seventeen red
    # TWO cases apiece — the cell index (`cells[-3]` -> `cells[-4]`) and the trunk carry-down — and
    # both are allowed because `expect` is matched by EQUALITY against one of them, not by the size
    # of the red set.
    # ⟳ 2026-09-20, code review r1 (Codex) — 17 -> 20. The first review to read the CODE rather than
    # the plan found the parser passing input it should refuse, and all three entries restore a way
    # a line could reach no rule at all: the exemption tuple that let `>`, `<!--` and a bare `#322`
    # sit unread inside a node (its Blocking), and the two halves of the duplicate-field refusal —
    # dropping the refusal, and reporting it while still applying last-write-wins. The second half
    # needed its own entry because the first cannot reach it: with the refusal gone BOTH cases red,
    # so a repair that reports a duplicate and overwrites anyway would have been indistinguishable
    # from a correct one. ⚠ The wrapped-continuation entry was RETARGETED in the same commit (its
    # anchor was the line the fix rewrote) — a retarget, not an addition, so it is not in the +3.
    # ⟳ 2026-10-27, backlog #381 — 22 -> 27, and two RETARGETS that are not in the +5: the stale-
    # alias and unclaimed-area lines were rewritten to compare per tag. The five: item rows only,
    # every tag of a cell in use, the malformed cell reported, `areas:` normalised, and a family
    # area over its leaves not called stale.
    # ⟳ 2026-10-27, backlog #381 r1 — 27 stays 27, by one retirement and one addition. RETIRED
    # with its subject: the escaped-pipe entry anchored `check-features`' own `CELL_SPLIT`, which is
    # gone — rows are read through `gen-backlog-page.parse` now (Codex M2). ADDED: a `ShapeError`
    # swallowed into no problems. Five entries were RETARGETED onto the rewritten lines, and the
    # exact-match stale entry was REPLACED by one reverting to any-descendant (Claude M1). Then
    # 27 -> 28: an unreadable backlog treated as an empty one, burying its cause under 22 stale lines.
    # ⟳ 2026-10-27, backlog #381 r3 — 28 -> 30: the parser's unread lines ignored, and `unread=` no
    # longer handed to it (Codex X1 = Claude C1, a decorated row number dropped from the gate).
    # ⟳ 2026-10-28, backlog #394: 30 -> 32 — a bad parent fails the gate; a missing kind is warned.
    "scripts/check-features.py": 32,
    # ⟳ 2026-09-07. Second of PR #247's four. Its `--self-test` printed `❌ {label}` — no
    # `[FAIL] ` prefix and no `: got ` — so all six mutations first reported CRASH with zero
    # parseable failure lines, indistinguishable from no coverage. Contract (1) was fixed
    # BEFORE these were registered, which is the order the loop requires and I got wrong once.
    "scripts/check-function-revokes.py": 6,
    "scripts/check-guard-coverage.py": 10,
    # ⟳ 6 -> 7 (backlog #331(a) / #357): the CANNOT RUN refusals for a corrupt, undecodable or non-object input.
    # ⟳ 7 -> 8 (PR #440 r2): the SKILL.md is read by `bounded_read`, so a FIFO there cannot hang the hook.
    # ⟳ 8 -> 9 (PR #440 r3 C4): the SKILL.md refusal must carry the reader's reason, so a FIFO is not "empty".
    "scripts/check-handoff-path.py": 9,
    "scripts/check-diff-coverage.py": 37,
    # ⟳ 25 -> 29 (backlog #361's PR): the ledger read AND written in the MAIN checkout through `main_checkout`, its
    # refusal of a non-path answer, and the fallback said aloud.
    # ⟳ 29 -> 30: an owner wait is the explicit `WAITS-ON-OWNER:` marker, and its word-match revert is an entry.
    # ⟳ 30 -> 32 (PR #425 r2 verification): a call runs in its own group, killed when it ends for any reason.
    # ⟳ 32 -> 34 (r3): the bounded post-kill drain (XR3), and `own_group=False` honoured (CR1).
    # ⟳ 34 -> 40 (r4): the `mark` on three failure lines, `fetch` taking the caller's main checkout, and an exited call
    # reported as exited (twice); four anchors retargeted onto the rewritten `render` and `_run` lines.
    # ⟳ 40 -> 46 (context floor): the compact block (off, path, owner entry, titles, one-line PR) and collect()'s call.
    # ⟳ 46 -> 56 (context floor r1): the wider owner matcher (text, bare token, card, OWNER), sort by `at`, hidden ids, the
    # absolute ledger path (render and collect), and the marker normalised by --add (two).
    # ⟳ 56 -> 73 (context floor r2, the REDESIGN): owner relevance is a DECLARED `kind`. Four entries RETIRE with their
    # subject (the text matcher the compact block used: approval text, bare token, OWNER prefix, the title-width cap) and
    # are re-bound on the fallback and on `_line`; the rest are new: the fallback's four readings, the declared kind
    # governing, `--add`'s kind (stored, validated, defaulted), the full shape, and the migration (propose, keep, override,
    # backup, no second apply, bad override).
    # ⟳ 73 -> 85 (context floor r3): `--add` stores what the text looks like; the compact block is CAPPED (owner entries
    # accepted against a reserved notice, waits first, the PR list and the problems bounded, the overflow named and counted,
    # the cap above the real ledger's owner text); and `--override`/`--apply`/`--kind` that cannot be used are refused.
    # ⟳ 2026-11-04, PR #496 r1 C4: 85 -> 94, the open `sweep-red` issues in the block — the CANNOT READ arm, its
    # mark, the names, the cap, collect()'s wiring, and the reader's command, directory, failure and element checks.
    # ⟳ backlog #408 r2: 109 -> 111 — `main_checkout` honours the runner's REGEN_MAIN_CHECKOUT (ignored; trusted as text).
    # ⟳ backlog #408 r3 (R3-F2): 111 -> 114 — the name is honoured only for THIS repository: the same-repository check
    # skipped, any alternates file passing, and a shared common dir not recognised.
    "scripts/session-state.py": 114,
    # ⟳ 2026-11-04, PR #496 r2 X1: the sweep-red alert, moved out of shell into a tested helper — an older green
    # closing, ancestry misread, the marker dropped, unreadable ancestry closing, a failed gh swallowed.
    # ⟳ 5 -> 6, PR #496 r3: auto-close REMOVED, and the two ancestry mutations with it — a green closes, comments on
    # only the first issue, or is handled as red; the marker dropped; a second red opens another issue; gh swallowed.
    # ⟳ 6 -> 14, backlog #495 r1 (Codex 4 / Claude M1): a FLAKY mutant FILED — never filed, scanned before the red
    # alert, a missing directory read as none, no comment on the open issue, a name listed twice, one shard read,
    # the names left out of the body, and a write with nothing to file.
    # ⟳ 14 -> 20, backlog #495 r2 fold (Codex 2+3): a missing shard file read as none, the shard count not read from
    # the matrix, two matrix lines or an empty one accepted, a name cut at its first `: `, a line without the tail
    # read at a guess. Four r1 entries re-bound (the call in two, the unset-directory guard, the shard loop).
    # ⟳ 20 -> 23, backlog #495 r3 fold (Claude M1): one missing shard file discards the present files' names, the
    # raise runs before the filing, and "no FLAKY mutation" printed for unread shards. Five entries re-bound to the
    # split read/raise (the filing call, the red-alert order, the unset guard, the missing raise, the shard loop).
    # ⟳ 39 -> 33, backlog #619 R1 (architecture review 2026-11-13, #629): the log grep, the per-job-index shard files
    # and `ci_flaky_contract` RETIRED with their 24 entries (dedupe, one file read, a missing shard file, shard_count
    # x3, flaky_names x2, the contract x16). 18 added for the records: an extra
    # key, another schema, a bool as an int, shard 0, a non-bool `complete`, an empty name, no record, totals that
    # disagree, two records for one shard, an incomplete shard not a problem or its names dropped, a missing shard,
    # a name listed twice, file order, the top level only, an unparseable record skipped, and a pull request that
    # files or is not red. Five entries re-bound: the filing order, the unset guard (now RECORD_DIR), the three M1.
    # ⟳ 33 -> 37, #619 r1 fold: a duplicate JSON key kept at its last value and an unreadable record's reason lost
    # (Codex); a shard above the total and a non-list `flaky` accepted (Claude m1).
    "scripts/sweep-red-alert.py": 37,
    # backlog #534 (2026-11-06): the batch full sweep — assemble, judge, land — pinned in the commit that creates it.
    # The branch name (1), readiness (6), the union resolver (7), membership (1), attribution and bisection (5),
    # assembly (1), landing (6), the batch/* refusal (1). Not mutated, on purpose: `merge_into`'s outside-UNION_FILES check, which
    # `resolve_text` backs up (a mutation there is masked by design), and `_refresh`'s own tree check, which the
    # per-step tree assertion after each merge backs up.
    # ⟳ 28 -> 68, batch-ci r1 fold, none retired (6 re-bound: four anchors and three expects moved with the code).
    # The 11 survivors R1-F7 named (11); check-merge-ready admission and its re-ask in land (R1-F1, 8); the base
    # re-read (C2, 2); master unmoved and the predicted squash (C1/R1-F3, 2); the latest run and what is a verdict
    # (C3/R1-F4, 5); Schema gates required and the coverage line (R1-F6, 2); whole-block union and its policies
    # (C4/R1-F2, 5); the import closure and its call site (C5/R1-F5, 5). `_refresh`'s pre-push tree check is mutated
    # (Codex r1). Not mutated: `_run`'s timeout, which only a real hung subprocess exercises.
    # ⟳ 68 -> 83, batch-ci r2 fold: 4 RETIRE with their subject (the home-grown import closure's regexes, harness
    # and transitivity — attribution now uses `check-plan-code.select_manifests`), 5 re-bound (the union rewrite
    # moved four anchors; the call site's moved), and 19 added: the union keeps each line in its section (R2-F1, 4),
    # the harness's reach and an unrunnable selector (R2-F2, 3), re-run a red that names nothing (R2-F4, 3),
    # answer-bound members never refreshed (R2-F3, 6), and the UNKNOWN re-read and the plan clean-up (R2-F5, 3).
    # ⟳ 83 -> 95, batch-ci r3 fold (the Phase 6 redesign of the docs union): 2 RETIRE with their subject (`_moved`,
    # the hunk-level section check, deleted), and 14 added: the whole-file postcondition's call site on the clean
    # path and its verdict (2), each clause P1, P2, P3, P4, P6 and P7 deleted (6), P4's re-sectioned base line (1),
    # P6 over the whole result (1), the prefix cut applied to the result (1), the one-side skip (1), several merge
    # bases (1), and the worktree created inside plan's clean-up (R3-F3, 1). Not added: the review's "cut = n",
    # which is EQUIVALENT — dropping the shared heading relabels its section to None in all four lists alike.
    # ⟳ 2026-11-11 backlog #495 r1 Codex 5: 95 -> 96 — a FLAKY line read as a failing mutation (`failures`).
    "scripts/batch-ci.py": 96,
    # backlog #397 (2026-11-09): the CI-duration tripwire, pinned in the commit that creates it. 25: the 25%
    # threshold in three directions, both sample minimums, the median, the zero baseline, the slowest-shard group
    # row and its derivation, the skipped-job filter, the idempotent append, the run picker, the week step, the
    # fetch's skip / budget / incomplete-run branches, the two CANNOT RUN exits, and the report and CLI wiring.
    # ⟳ 25 -> 44 (r1 fold): 19 added, one or more per finding — the timeout-kill kept, a non-timeout cancel voiding
    # the group row, the annotation test and its fetch wiring (R1-F1); none-recorded and the stale log (R1-F2); the
    # default week (R1-F3); the CLI and record_main crash wrappers, a real ISO week, field types and merged_at
    # (R1-F4); both halves of combine_rc (R1-F6); the truncated percentage (R1-F7); the per-call timeout (R1-F8);
    # and the PR / jobs / runs truncation refusals (R1-F9). Six entries re-anchored to the moved code, none retired.
    # ⟳ 44 -> 61 (r2 fold): 17 added — a PR is a snapshot written whole and checked on read: the unmeasured list,
    # the no-timestamp shard voiding its group (R2-F4), the complete / torn classes and their three torn clauses,
    # the retry-and-replace of an incomplete snapshot and the torn refusal (R2-F2), any unrecorded PR is rc 2 and an
    # unmeasured job is NOT MEASURED (R2-F1), an empty jobs list (R2-F3), the lock (R2-F5), the week checked against
    # the merge date (R2-F6), and the constant --since (R2-F7). One expect renamed with its case, none retired.
    "scripts/ci-durations.py": 61,
    # backlog #361 (2026-10-28): the compaction snapshot/audit/print, pinned in the commit that creates it.
    # ⟳ 18 -> 21 (the automated review of a13f0b8f, MEDIUM): the prefix-only answer fallback RETIRES with its subject
    # (the behaviour is now forbidden), and four are added — the fallback restored, pasted content shown, the real
    # transcript's `</pasted_content id=…>` closer unmatched, a tool_result-carrying turn read as a prompt. Four
    # anchors retargeted onto rewritten lines.
    # ⟳ 21 -> 23: the ledger read from the MAIN checkout (a worktree's own is empty), and the fallback said aloud.
    # ⟳ 23 -> 22: the main-checkout rule MOVED to session-state.main_checkout (one copy), so the entry that re-pointed
    # this file's read retires with its subject; session-state's manifest now holds it.
    # ⟳ 22 -> 39, PR #425 round 1 (Codex): +19 for XB1 (question and result provenance, one answer per question, the
    # RECORDED heading), XB2 (fail closed: one block, matching ids, withhold to the end), XM3 (one deadline, no waiting
    # executor), XM4 (the receipt: session, nonce, written first), XM5 (UNAVAILABLE keys) and Xm6 (bounded keys); two
    # retire with their subject (the age-only audit pairing; the closer-id regex, now `withhold_pasted`); four retargeted;
    # and the audit's NOT CHECKED lines placed before the dropped list the cap cuts (found folding Xm6).
    # ⟳ 39 -> 59, PR #425 round 2 REDESIGN: the manifest is REBUILT against the rewritten file. The in-process
    # deadline entries (SNAPSHOT_BUDGET, `bounded`, the waiting executor) RETIRE with their subject, replaced by the
    # capture CHILD killed with its process group; per-session files, XM1 session binding and typed flags, CM1/Cm2
    # name matching, CM3/CM4/XM5 completeness and Xm6's owner-wait and final-size bounds each gain an entry.
    # ⟳ 59 -> 59: the capture child's group is killed after it exits too, for ANY reason (+1); that kill subsumes the
    # timeout path's own group kill, so "only the child is killed" retires as an equivalent mutant (-1).
    # ⟳ 59 -> 69, PR #425 round 3 SPLIT. RETIRED with their subject (the code is DELETED): the backlog-word PR exclusion,
    # "dropped" reporting, the "names everything" sentence, the audit's receipt-epoch check, the COMPACTION HAPPENED
    # heading, and `mentioned` (two entries) — each replaced by an entry on the code that replaced it. RETARGETED onto
    # rewritten lines: the print's checks, `_off`, the bad-session-id guard (now `open_session_dir` alone), the audit's
    # nonce and omitted lines. ADDED: Xr8 null flags, found/not-found, the disclaimer, the fixed bound, `PR` required,
    # `read_in`'s type and size checks, the audit and print children's kills, O_NOFOLLOW, CR1's caller-group calls,
    # and the NOT CAPTURED tagging.
    # ⟳ 69 -> 55, PR #425 round 4 DEFER. RETIRED with their subject (21): the AUDIT is deferred to its own backlog row
    # and its code deleted (14 entries: found/not-found, the disclaimer, `PR` required, the PR and ask boundaries, the
    # bracketed ids, the audit's nonce, its omitted and NOT CAPTURED lines, its compact_summary refusal, its child's
    # kill, the print's audit nonce, the old audit.md deletion), and with it the keys' variable-length lists
    # (`bound_keys` x3, the PR list, the ledger list, `omitted`) and `tag_uncaptured`. ADDED (7): the stdin byte cap on
    # a pipe and on text, the children inside the hook's absolute deadline, NOT CAPTURED placed by `render(mark=)` and
    # never found by search, the main checkout asked once, the snapshot shown at all. RETARGETED: the freshness
    # boundary (age < 0, age >= 30 min), the print child's kill onto the deadline, five expects renamed.
    # 55 -> 54: the snapshot's final `fit` retires as an EQUIVALENT mutant — with the keys line now four fixed fields,
    # every section is capped and the owner section takes only the room left, so no input reaches the backstop.
    # ⟳ 54 -> 58 (context floor): the print's digest (whole snapshot, path, owner section, NOT CAPTURED line).
    # ⟳ 58 -> 63 (context floor r1): the owner's words kept whole, the title block, a cut that keeps NOT CAPTURED, a
    # heading level that must not end the section, and the other sections' bodies left in the file.
    # ⟳ 63 -> 73 (context floor r2): the snapshot selects by the declared kind, owner text is never cut (decisions, what,
    # on_done, /compact instructions, title block), the cap makes room for it, the digest puts it first, and the in-flight
    # block says where the owner entries went.
    # ⟳ 73 -> 75 (context floor r3): the print's cut names the owner decisions it took (the ids, and the reader of the
    # digest's whitespace-cleaned lines). The reserved room for the notice has NO mutation: the case's lines are short
    # enough that the cut's own slack hides it.
    # ⟳ 2026-10-30, backlog #407 (counted on its own branch from 54, merged after the context floor): +4 — the
    # real-time cases' marker (1), CI's real-time step (2), the hook modes never reading it (1); the CR1 own-group
    # entry RETARGETED onto the event-ordered case.
    # ⟳ r1 fold: +6 — the stdin deadline's wiring in `main` and gh's own 8 s, in every run (the two mutants r1
    # proved survived the skip); the CI step's `if:`/`continue-on-error` on the step and the job, and its job (3); no
    # hook mode naming the marker, statically (1).
    # ⟳ r2 fold: +4 — the child adapter's gh and git timeouts (Codex A, B), and the self-test step only directly under
    # `steps:` (matrix data; a nested list item). Merged with the context floor's 75: 75 + 14 = 89.
    "scripts/compaction-state.py": 89,
    # backlog #440 (2026-11-01): the PreCompact boundary hook — the ceiling, idle and block order, the three
    # mid-work signals' detectors, W's precedence and fail-open, the snapshot chained only on ALLOW, the log path.
    # ⟳ r1 fold: +13 — the sentinel's `paused:`/`session:`, the ceiling's clamp under the model limit, a completed
    # foreground result, the agent lease, activity beyond assistant records, malformed records, a non-string cwd,
    # non-blocking opens, undecodable snapshot output. 28 + 13 = 41.
    # ⟳ r2 fold: +4 — a report quoting the launch phrase, the ceiling's floor at W, its `no-headroom` label, a
    # nested repo's checkout. 41 + 4 = 45.
    # ⟳ backlog #537 (2026-11-06): the explainer question watcher is not a monitor signal — the flag ignored, one
    # watcher silencing a CI monitor, -F, the chaining test, quote stripping, the path's two boundaries, the flag
    # never recorded: +8. 47 + 8 = 55.
    # ⟳ r1 fold (backlog #537): the denylist became an allowlist over shlex tokens — 5 regex entries retired, 18 added,
    # one per clause (-F, one path, the path's two boundaries, the first program, the filter allowlist, a later stage's
    # operator, the newline, the substitution scan and its four clauses, `#`, an unparsable command, each redirect).
    # 55 - 5 + 18 = 68.
    # ⟳ r2 fold: the 18 shlex-clause entries retired, 14 added, one per template clause. 68 - 18 + 14 = 64.
    # ⟳ r3 fold: +3, each widening the path position (a space, `$`, `~user`) and each expecting the r3 F1 case. 64 + 3 = 67.
    "scripts/check-compaction-boundary.py": 67,
    # backlog #455 (2026-11-01): a subagent's foreground Bash call that can block past 270 s is refused. Pinned in the
    # commit that creates it (21). ⟳ r1 fold: the sleep and watch rules removed, the effective timeout read the way
    # the harness reads it — one entry per clause of that reading, the exemptions, the deny JSON and NOT CHECKED: 29.
    "scripts/check-agent-long-call.py": 36,
    # backlog #457 (2026-11-01): a subagent's read of more than 300 lines, or a re-read of an unchanged file, is
    # refused. Pinned in the commit that creates it — one entry per clause of the Read and Bash readers, the
    # exemptions, the re-read record and NOT CHECKED: 51. ⟳ security fix: + the state directory's symlink, owner and
    # mode checks. 51 + 3 = 54. ⟳ r1 fold: the re-read rule and its state removed (-10); the notebook/PDF/image
    # exemption, `sed` as one stream with `q`, globs, a later stage's own files, `-`, `|&`, subshells, `sed -s`,
    # `head -q`, exact `head -n -K` and the cwd check added — one entry per clause: 77. ⟳ r2 fold: Bash narrowed to a
    # SIMPLE command; the pipeline, heredoc, subshell and assignment entries removed (-19), one entry per clause of
    # `simple_command`, `-` as stdin and the 18-digit number bound added (+25): 83. ⟳ backlog #465: a `;`/`&&` list
    # summed — one entry per clause of `split_list` and `list_spans` (+15); the `cd DIR &&` prefix of
    # `simple_command` became a list part (-4, +1 for the list's `cd` test): 95.
    "scripts/check-agent-large-read.py": 107,
    "scripts/check-hook-commands.py": 34,
    # backlog #364 (2026-10-27): the launcher's own test, pinned in the commit that creates it. Its
    # Python rules only — the launcher's shell mutants are killed inside its `--self-test`.
    # backlog #388 (2026-10-30): 12 -> 18, the uncrowded world base (the bound, its ancestors, `top`, the pick) and a timed-out launch as a red world.
    "scripts/check-run-hook.py": 18,
    # backlog #373 (2026-10-27): the fixture-git guard and the helper it enforces. 17 -> 36 and 6 -> 12 in the
    # round-1 REDESIGN (isolated(), the closed entry shape, the import-time capture rules); 36 -> 45 in round 2's
    # SPLIT (one argument-free item, the subcommand rule, GIT_SUITES). `fixture_git.py` is a LIBRARY, so the literal list below is its outside observer.
    # ⟳ backlog #382 (2026-10-27): 45 -> 32. Every `--self-test` is wrapped, so the BUILDER DETECTOR and GIT_SUITES are
    # deleted and their 19 entries retire with their subject; 6 are added for the population rule (the entries
    # `check-main-drivable.suite_entries` reads, a flag test with no entry, a file with no self-test, the named refusal);
    # 32 -> 35 for rule 5, no process launch at import, which replaces the deleted module-level-build refusal.
    # 35 -> 48 in the r1 fold (Codex XM1-XM4): the literal population, named entries, undecorated sync entries, and
    # rule 5 over every file with class bodies, except types, TryStar, rebinding, __import__, getattr and asyncio.
    # r2 fold: rule 5 EXECUTES each import under an audit hook, so its 10 static spelling entries retire with their
    # subject and 10 are added (the events, the timeout and crash as CANNOT CHECK, the named event, exit-time launches,
    # ctypes, effects reported, EXEMPT files imported) — 48 -> 48.
    # r3 fold (SPLIT): 48 -> 55, the -I -S audit child and rule 5's static direct-launcher half.
    "scripts/check-fixture-git-isolation.py": 55,
    # ⟳ 2026-10-30, backlog #407: 12 -> 13, the mutation harness's run marker passed through isolated().
    # ⟳ 2026-11-07, backlog #512: 13 -> 19, the block's own temp directory (TMPDIR, tempfile.tempdir set and given
    # back, removed on every exit, the fresh HOME inside it). r1 fold: 19 -> 23, the restore of TMPDIR and the
    # cache EXACTLY, from an unset TMPDIR and a None cache, on a refused block too (Codex R1-F1, Claude R1-F1).
    "scripts/fixture_git.py": 23,
    # ⟳ 2026-09-07. Third of PR #247's four, and the money one — backlog #26's trigger. Six
    # targets in the PURE halves: the per-occurrence line scan (the r12 blocking defect), the
    # comment/code bucket, the SQL string blanker, block-comment NESTING, the SQL line-comment
    # blanker, and the ledger's file ordering. TWO first attempts were WRONG and the harness
    # said so: disabling the dollar-quote branch SURVIVED (that case is actually killed by the
    # STRING branch — its fixture puts the create inside quotes), and dropping "scripts" from
    # PRODUCTION_DIRS CRASHED, because the fixture mkdirs from that same tuple.
    # ⟳ 2026-09-27: 12 -> 16. Four mutations for the ESCAPE CROSS-CHECK, which explains why a
    # refusing gate did not see the `NO-ENTRY:`/`NO-REVIEW:` the author believes they wrote. One
    # per distinguishable state (misdirected, invisible, inert-other) plus one that makes it run
    # on gates that did NOT refuse — the shape that would turn an explanation into an accusation.
    # ⟳ 2026-10-25: 16 -> 30 — the house rule's HOLD stage (`hold_reasons`, `final_verdict`, and
    #   main()'s wiring over a fake `_run`): fourteen entries added, none retired.
    # ⟳ 2026-10-25 r1 fold: 30 -> 41 — a deleted gate, old-side distance, the hooks' `deny`/`exit 2`,
    #   gate CALLERS, a removed pin, and main() on NO-ENTRY. Eleven added; one anchor rebound, none retired.
    # ⟳ 2026-10-25 r2 REDESIGN (one parser, `diff_files`): 41 -> 45 — six anchors rebound onto the
    #   new parser with the same mutation each; four added (rename paths, scope exits, comments as
    #   invocations, an in-scope rename as an exit). None retired.
    # ⟳ 2026-10-25 r3 SPLIT (path identity): 45 -> 50 — two anchors rebound, five added (C-quoting,
    #   the tab delimiter, binary deletion, copies, a gate's role across a rename). None retired.
    # ⟳ 2026-10-25 backlog #353 (paths from `git diff --name-status -z -M`): 50 -> 56 — two anchors
    #   rebound, six added (headers as path source, the count join, a gained role, main()'s wiring,
    #   an add's old path, an incomplete entry), then +1 for changed_paths' old path. None retired.
    # ⟳ 2026-10-25 r5 (a positional FALSE READY): 57 -> 59 — the positional join is DELETED, so its
    #   count-mismatch entry is RETIRED WITH ITS SUBJECT (the one permitted kind of fall); three
    #   anchors rebound onto per-file patches; three added (--no-textconv, --no-ext-diff, literal pathspecs).
    # ⟳ 2026-10-25 r6 (two more FALSE READYs, per-path patches): 59 -> 63 — hunks now diff EXACT BLOBS;
    #   the two `patch_cmd` entries RETIRED WITH THEIR SUBJECT; six added (the blob pair, --text, a
    #   gitlink, the gate-root restriction both ways, add/delete signs); then the `--no-textconv` entry
    #   RETIRED WITH ITS FLAG, which a pathless blob diff makes dead (it survived, measured).
    # ⟳ 2026-10-25 r7 (two adversarial FALSE READYs): 62 -> 68 — git read as BYTES (`git_reader`,
    #   `as_text`) and a gate symlink's changed target judged as the gate; six added, none retired.
    # ⟳ 2026-10-25 r8 (three HONEST false READYs): 68 -> 71 — every script is gate code (helpers) and any
    #   non-zero status is a failure path; one anchor rebound, three added. The semantic bound is a CASE.
    # ⟳ 2026-10-25 r9 (two HONEST-SYNTACTIC false READYs): 71 -> 73 — moves keep indentation, and any
    #   non-zero int, `raise` and `assert` are failure statements; six anchors rebound, two added.
    # ⟳ 2026-10-25 r10: 73 -> 75 — sys.exit with any non-zero argument; main() fails closed on ANY error.
    # ⟳ 2026-10-31, backlog #359: 85 -> 84, RETIRED WITH ITS SUBJECT — the entry flipped the proxy for a
    # falling typed mutation TOTAL, and there is no typed total any more; the proxy and its two cases
    # are deleted with it. A falling per-file pin is still held, under its own entry.
    # ⟳ r2 REDESIGN: 84 -> 87 — a falling pin is read from the EFFECTIVE dicts (`pin_pair`), not from
    # `PIN_LINE` over the diff, which is deleted. Its two entries are REBOUND to `pin_falls`; three
    # added: a non-JSON side failing open, the base-only import fallback answering for the head, and
    # main() never reading the pins.
    # ⟳ r3 (Claude F1): 87 -> 87 — the pins are read from each side's DISPLAY by `pin_display`, so the
    # subprocess is deleted. Two entries RETIRED WITH THEIR SUBJECT (a non-JSON `--print-pins` failing
    # open, and the base-only import fallback answering for the head); two added, both fail-open
    # directions of the new read: a display `pin_display` refuses read as `{}`, and a failing
    # `git ls-tree` read as an answer. Three entries are REBOUND to the renamed cases.
    # ⟳ r4 (Codex F2): 87 -> 89 — importing THIS file for its reader fails CLOSED: the import's catch
    # and the reader call's catch, each narrowed to `Exception`, let a `SystemExit` out as rc 0.
    # ⟳ r6 (Codex F1): 91 -> 92 — the error text built from a sibling's exception is sibling code too:
    # `_describe` guards `str(exc)`, and an unguarded one lets a `__str__` that exits leave rc 0.
    # ⟳ r7 (Claude F1-F3): 92 -> 96 — what a sibling RETURNS or RAISES is reduced to exact builtins in
    # `_cross` before it leaves: isinstance in `_exact_pins`, its key/value check dropped, an unchecked
    # exemption value, and an uncoerced class name each go red. Three entries are RE-BOUND to `_cross`.
    # ⚠ Returning the original object instead of the copy is an EQUIVALENT mutant (measured: the exact-
    # type checks already refuse every subclass), so it is not pinned.
    # ⟳ 2026-11-06, backlog #533: 97 -> 99, none retired, two RE-BOUND into `pins_home`. The display moved to
    # this file: a revision read only from it, so a base before the move pins nothing (1), and the harness
    # read before it (1).
    # ⟳ 2026-11-06, sweep-pin-select r1 (Claude F1): 99 -> 102, none retired. HEAD's harness must bind the
    # pins file this script reads: the check skipped (1), a second write allowed (1), a nested binding (1).
    # ⟳ 2026-11-06, sweep-pin-select r2 (Codex F2): 102 -> 104, none retired. The binding scan counts only module
    # bindings: walking the whole tree (1), and ignoring a function's `global` (1).
    # ⟳ 2026-11-06, backlog #536 (the THRASHING architecture review, r4 fold): 104 -> 102. The static binding proof is
    # DELETED with its 5 mutations (3 from r1, 2 from r2); the held-versus-display comparison in `pin_pair` adds 3:
    # skipped (1), inverted (1), and reading only the held side's keys (1).
    # ⟳ backlog #508: 97 -> 112 — the rising-count exemption (4: skipped, any change, the prefix, the
    # suffix) and the reviewer's answers (11: the occurrence in the id, a null overlay, the exact tree,
    # the overlay read, finding-wins, the exact answer, hold_reasons, main's call site, the tree check,
    # a gate that did not run, --flagged-block).
    # ⟳ #508 r1: 112 -> 127 — the unstripped rising count (1); every tree entry compared (2: gitlinks, an
    # added path); the round's own records (3: coordinator, decision log, the baseline NOT exempt); the
    # working-tree block (2: the stash commit, the status head); an earlier tree's finding (2: the rule,
    # the call site); the block's file:line (5: the offset, the row, both hunk parsers, main's call site).
    # ⟳ #508 r2: 127 -> 141 — exact record names (3: the coordinator pattern, fullmatch, the half's own
    # directory); a finding retired only by a later round of the same subject and half on this tree (8);
    # one budget of added lines for the move and rising-count exemptions (3). Twelve re-anchored.
    # ⟳ #508 r3: 141 -> 143 — the budget is ORDER-INDEPENDENT (r3 M1): moves claimed before rises
    # (the greedy order restored), and a claimed move skipped (2). Four re-anchored.
    # ⟳ 2026-11-06, MERGE of backlog #508 with backlog #533/#536 (PR #526): both sides moved this pin from the
    # base's 97 — #508 to 143 (+46, none retired) and #533/#536 to 102 (+5, none retired) — over disjoint
    # entries, so the merged manifest holds 97 + 46 + 5 = 148 (per-entry 3-way merge: 0 missing, 0 extra,
    # 0 duplicate names).
    # ⟳ 2026-11-06, backlog #534: 102 -> 106, none retired. The advisory batch line: a green master run read as a
    # batch (1), a red batch read as green (1), the line moving the verdict (1), a diverged batch read as containing (1).
    # ⟳ 2026-11-06, batch-ci r1 fold (R1-F8): 106 -> 110, none retired. The advisory line's bounds: uncapped compares
    # (1), the run list's timeout (1), a compare's timeout (1), a refused compare read as "does not contain" (1).
    # ⟳ 2026-11-06, MERGE of origin/master (#508, PR #522) into batch-ci (#534): the merge-base pins 102; #508 moved it
    # to 148 (+46) and batch-ci to 110 (+8), over disjoint entries, so the merged manifest holds 102 + 46 + 8 = 156.
    # ⟳ 2026-11-08, backlog #544: 156 -> 163, none retired. An answer bound to its flagged FILE: the deleted-file
    # exact-tree branch (1), a deleted file bound to nothing (1), a symlink target dropped (1), an absent file read
    # as identical (1), a record clearing ids it is not bound for (1), a finding retired by a round bound for
    # another id (1), the call site binding nothing (1). Four entries re-bound to the new text, same subjects.
    # ⟳ 2026-11-08, answer-binds-file r1 CLAUDE F1: 163 -> 164, none retired — `gather`'s `via` key renamed, killed
    # by the real-git case that edits a gate symlink's TARGET after the round.
    # ⟳ 2026-11-08, backlog #538: 156 -> 162, none retired. The held side is HEAD's, materialised: the working-tree
    # harness read again (1), the isolation dropped at the call (1), its sys.path half (1) and its hidden-module half
    # (1), a failing `git archive` read as an archive (1), an archive that does not unpack passed over (1).
    # ⟳ 2026-11-08, backlog #538 r1: 162 -> 176, none retired; the two archive entries are RETARGETED to the raw-blob
    # read that replaced `git archive` (a failing `git ls-tree`, an entry that does not parse). New: the displays
    # parsed by the working-tree harness (C-F1) (1), materialised on every call (1), an empty listing (1), a
    # symlink/submodule (1), a path leaving scripts/ (1), a file written over (1), a failing `git cat-file` (1), an
    # answer that is not the blob (1), bytes not hashed against the id (X-F1) (1), more than asked (1), every
    # fileless module trusted (X-F2) (1), and the restore's three halves (C-F2) (3).
    # ⟳ 2026-11-08, MERGE of origin/master (backlog #544, PR #543) into held-pins-head (backlog #538): the merge-base
    # pins 156; #544 moved it to 164 (+8, none retired) and #538 to 176 (+20, none retired), over disjoint entries,
    # so the merged manifest holds 156 + 8 + 20 = 184 (per-entry 3-way merge: 0 missing, 0 extra, 0 duplicate names).
    # ⟳ 2026-11-08, backlog #538 r2 (a REDESIGN: HEAD's harness is read in a CHILD process): 184 -> 181 = 184 - 8 + 5.
    # RETIRED (8), their code deleted with `_isolated_import`, `_lib_roots`, the lazy `_head_harness` getter and the
    # suite's compile memo — the parent now imports nothing to read the pins, so there is no isolation to weaken:
    # the import WITHOUT isolation, its sys.path filter, its hidden-module filter (their subject, a working-tree module
    # reaching HEAD's harness, is the new `-I` entry); "every FILELESS module trusted" (`own()` is gone); the
    # restore's three halves (nothing to restore: the X-F3 case asserts sys.path and sys.modules UNCHANGED across a
    # pin_pair, killed by the re-bound C-F1 entry); "materialised on EVERY call" (one child per pin_pair; the
    # count case stays). NEW (5): the child without `-I`, committed bytecode skipped not refused, the exit code
    # unchecked, the JSON schema unchecked, no timeout. RE-BOUND (5), same subjects: the working-tree harness read
    # again, the displays parsed by the working-tree harness (C-F1), the held-versus-display comparison (#536,
    # re-indented), a refused display read as nothing (`_child_pins`), and pin_display's SystemExit (the driver's
    # BaseException catch; its case now names SystemExit).
    # ⟳ 2026-11-08, backlog #538 Phase 6 (`docs/reviews/architecture-review-2026-11-08-held-pins-child.md`): 181 -> 187
    # = 181 + 6, none retired, none re-bound. A stdlib-named HEAD `scripts/` name is refused (module, package, not
    # over-broad) (3), the group kill (1), the bounded post-kill wait (1), and the duplicate-key refusal (1). The NaN
    # refusal is deleted: the schema check already refuses every non-int, so its only observable was a message.
    "scripts/check-merge-ready.py": 188,
    "scripts/check-paid-caller-arrival.py": 6,
    "scripts/check-vocabulary-collisions.py": 5,
    # ⟳ 2026-09-29, backlog #191: the LLM recall matcher joins the manifest in the commit that
    # creates it, over a file whose CENTRAL mechanism — a model call — cannot be mutated at all.
    # That is why the mutations are dense everywhere else: the answer to an untestable core is to
    # shrink it and cover everything it touches, not to accept the gap. SIX of them mutate the
    # PROMPT TEXT rather than code, deliberately — the prompt is the measured artefact (20/20
    # must-fire, 0/60 false fires, 2026-09-29), so deleting one of its five load-bearing clauses
    # invalidates the measurement exactly as a code defect would.
    # ⛔ M1, round 1: this comment SAID "41 entries" twice, beside the number it sits next to — and
    # it was already 53 when the review read it. A count in prose has no owner and drifts from the
    # literal below it; the only count that cannot is the literal, which the suite pins. So the
    # figure is NOT restated here. The same rule is written at the top of EXPECTED_MUTATIONS and
    # this comment was the counter-example to it.
    # ⟳ 2026-09-30, review rounds 1 and 2 folded. ⛔ NO COUNT HERE — and the previous version of
    # THIS line, added to fix round-1 M1, said "53 → 74" three lines after declaring that the
    # figure is not restated. It was 80 by the time the reviewer read it. A rule stated and
    # broken in the same comment is worse than one never stated: the literal below is the count.
    # ⟳ 2026-09-30, backlog #201/#202: the guard that reconciles the matcher's exit codes with the
    # hook's `case` arms. Five entries, registered in the same commit that creates it — R4 refused
    # the file until they existed, which is the population half of the contract doing its job on a
    # guard added minutes earlier.
    # ⟳ 2026-09-30, round 3 M1: 5 -> 9. The arm reader's indentation, the soundness check over
    # unmodelled arm shapes, the structural-line string tracking, and the `case` block bound.
    # ⟳⟳ 2026-09-30, THE ARMING CONDITION FIRED AND THIS IS THE ONE SANCTIONED RATCHET FALL:
    # 16 -> 9. FOURTEEN entries were RETIRED WITH THEIR SUBJECT — the 114-line hand-rolled bash
    # lexer (`case_block`, `structural_lines`, `unmodelled_quoting`, `arm_soundness`, and the
    # lexical `handled_codes` / `unguarded_detail_arms`) is GONE, replaced by adjudicating the
    # hook with bash itself. Every entry named code that no longer exists, so they are retired
    # rather than orphaned. SEVEN were added against the observer. Reason at the retirement site
    # in that file; the self-test count falls 51 -> 40 in the same commit for the same reason.
    # ⚠ Round 3 B2, round 4 Codex H1 and round 4 B1/M1/M2 were all findings in that one component
    # across two consecutive rounds, every one caused by the previous round's fix — which is
    # `dev-process.md:108`'s condition, met for the first time in this fold.
    # ⟳ 2026-10-15: the reference-namespace guard arrives with a manifest rather than
    # manifest DEBT. `check-ratchet-contract` offered `MANIFEST_BASELINE = 1`, which would
    # have ACCEPTED the debt; six entries take it to 0 instead.
    # ⟳ 2026-10-15, backlog #49. Seven entries rather than manifest debt; the blank-line,
    # out-of-range, ambiguous-suffix, two scope clauses, the CANNOT-RUN code and the
    # injected reader each have a case that names them.
    "scripts/check-doc-citations.py": 37,
    # ⟳ 2026-10-29, backlog #394: 9 -> 14 — the marker-only exemption: applied, byte-identical, not for a
    # new row, not for an unmarked line, and only against the SAME file's removed lines.
    # ⟳ 2026-10-29, PR #442 r1: 14 -> 15 — an invalid marker is judged, never raised; 15 -> 16 — removed
    # lines are keyed on `--- a/`, so a deleted file's lines are never credited to another (M1).
    # ⟳ 2026-10-30, PR #442 r2: 16 -> 20 — the exemption reads the BASE FILE of the same path, never
    # removed diff text. Two retired with their subject (the removed-lines dict and its `--- a/` key);
    # six added: every path read, the head read as the base, an absent path holding its own lines, an
    # unconsumed budget, the head's unmarked copies not subtracted, and added lines read outside a hunk.
    # ⟳ 2026-10-30, PR #442 r3: 20 -> 22 — both sides now come from the one-path diff. Three anchors
    # rebound (every path's diff, the sides swapped, the hunk sign), none retired; two added: the head
    # read as raw worktree bytes under `eol=crlf` (F2), and `splitlines()` for `split("\n")` (F3).
    "scripts/check-reference-namespace.py": 22,
    # ⟳ 6 -> 9 (backlog #331(a) / #357, PR #440 r1). ⟳ 9 -> 7 (PR #440 r2): #331(a)'s `if not records` moved to
    # `bounded_read.stop_transcript`, and the None-mapping entry is now masked by `judge`'s try, so both retire;
    # r2 X1 / #331(e)'s mutant — the reader's refusal answered QUIET — is the no-transcript entry's, which names
    # that case too.
    # ⟳ 7 -> 8 (PR #440 r3 C4): the CANNOT RUN message must carry the reader's reason.
    "scripts/check-transcript-references.py": 8,
    "scripts/check-rc-contract.py": 17,
    # ⟳ 2026-10-01 — THE HOOK'S OWN GUARD, pinned in the commit that creates it. R3 moved here
    # from `check-rc-contract` because its subject is the HOOK'S RENDERED TEXT, not the cross-file
    # contract: every Blocking in rounds 3-7 landed on R3 while R1/R2 produced none, and round 7
    # B2 showed why — the cross-file guard observes the hook by STAGING A MINIMAL TREE, and a
    # staged tree is a proxy for the repo. This guard runs the REAL hook IN THE REAL REPO through
    # the one ARGV seam (`surface-recall.sh:60`), so there is no fabricated world to be unfaithful.
    # Measured: an arm branching on `.claude/settings.json` renders a dangling `Detail:` for a
    # reader — this guard returns [5], the staged observer returned [].
    # ⚠ FOUR OF THE 11 ARE RELOCATED, NOT NEW — they came from `check-rc-contract`'s manifest with
    # the rule, retargeted onto the code that now owns it. Its 20 -> 14 and this 0 -> 11 are ONE
    # move, and the declared sum rises 1158 -> 1163 net of two retirements whose subject is gone.
    "scripts/check-surface-recall.py": 21,
    # ⟳⟳ 2026-09-30, round 3 H1: 91 -> 94. `unanswerable_if_armed` and its two boundaries —
    # `prepared_prompt` and `do_arm` — because #202 fixed the conjunction on `--fire` and left it
    # alive on `--arm`, which is B1's error a third time.
    "scripts/recall-llm.py": 96,
    # ⟳ 2026-10-28, owner decision D3 (backlog #363): every generated page rebuilt on merge — the
    # merge match, the threads path, the per-generator timeout, the advisory exit codes, a crashed
    # generator named, and silence on an unrelated command.
    # ⟳ same day, round-1 fold: 8 -> 12 — the regex entry retired with the regex; five for the
    # executed-command match (X3): quoted text, merge-base, NAME=value, separators, newlines.
    # ⟳ round-2 (Y5): 12 -> 17 — the NAME=value entry re-anchored on the rewrite; six new for the
    # static "may merge" match: compound-syntax words, quoted separators (non-POSIX), here-document
    # bodies and their end, quoted command words.
    # ⟳ round-3 fold (architecture review SPLIT): 17 -> 9 — the shell tokenizer is DELETED, and the ten
    # entries that pinned it (quote-aware split, separators, newlines, NAME=value, compound words, POSIX
    # mode, here-documents x2, quoted command words, the old regex) retire with their subject; two new pin
    # the substring trigger that replaced it, in both directions.
    # ⟳ round-4 (terminal) fold: 9 -> 10 — the registration reader keys on the Bash matcher (W1). The
    # REGISTRATION ITSELF is data in .claude/settings.json, which this harness cannot mutate; its falsifier
    # is the case reading the real file, which goes red if either event loses the runner.
    # ⟳ backlog #408: 10 -> 31 — every page is built from a FRESH origin/master tree: the fetch, the ref, the
    # three own-worktree guards (the one between `checkout --force` and the main checkout's edits), the
    # read-back, the lock, the GIT_* scrub, the generator's script path and cwd, the hook/command exit
    # split on CANNOT RUN, and `--page`'s output, exit code, key check and provenance line.
    # ⟳ review round 1's fold: 31 -> 45. The reuse design is GONE (its `checkout --force` + `clean -fd` destroyed
    # work in four reproduced ways), so its three own-worktree guards and the in-place move were retargeted
    # onto what replaced them — the read-back's git-dir check (main's own, another repository's) and the add's
    # refusal of an existing path (no `--force`) — and 14 are new: the removal (entry, directory, the call), the
    # literal-path match that a swapped-in symlink cannot redirect, the temp root, the process group, its
    # ending, the inherited lock, the stop signal and the live registry, the lock-file hint, `--after-edit`,
    # and the suite's refusal of this repository (safe to mutate now: its cases hand `fresh` a decoy git).
    # ⟳ review round 2's fold: 45 -> 53. Round 1's linked-worktree design is GONE (a swapped `<common>/worktrees`
    # symlink and an edited `gitdir` text each made its cleanup delete somebody else's data), replaced by a
    # private `clone --shared`. Its nine worktree-specific entries are retargeted one for one onto the clone
    # (no origin URL, `--shared`, origin/master in the clone, the git-dir read-back, the descriptor deletion,
    # the private dir's rmdir and identity, deletion by path), and 8 are new: the SIGKILL escalation against a
    # child that ignores SIGTERM (r2 F6), `lstat` not `stat`, the clone -> main-checkout map, its hand-off and its
    # removal, a failed step inside the clone, a failed clone, and origin's URL.
    # ⟳ review round 3's fold: 53 -> 58, none retired (three anchors rebound onto the exact-path read-back and the
    # widened `_env`): the `lstat` before the in-clone verbs and the exact path compare (R3-F1), the inherited
    # REGEN_MAIN_CHECKOUT stripped (R3-F2), and `_git`'s stop-signal SIGTERM grace and bounded drain (R3-F3).
    # ⟳ PR #536's CI sweep: 58 -> 60, none retired — four kills went red with no `[FAIL]` name because the suite
    # RAISED between cases; the crash guard that now names such a red has two: its `[FAIL]` print, and its
    # catching a non-zero sys.exit.
    # ⟳ backlog #627: 60 -> 64 — the serve copy checked out at the built sha, the server's fetch really fetching
    # and refusing this repository inside the suite, and main() printing the serve-copy line.
    # ⟳ #627 review round 1: 64 -> 65 — the fetch's second guard: only a repo inside the suite's own temp dir.
    # ⟳ #627 review round 2 (Codex M2): 65 -> 72 — every WRITER refuses a destination outside the suite's temp dir:
    # the fetch target, the clone, a run's private dir, the tree lock, the serve copy, the shared check itself, and
    # Codex's own mutant (serve_copy_path answering an outside dir), killed by an identity case.
    "scripts/regen-pages.py": 72,
    # ⟳ 2026-10-02, ADR-0014's rule D2: this guard is created and registered in the SAME commit —
    # R4 refuses the file until a manifest exists, which is the contract doing its job on a guard
    # written minutes earlier. ⭐ TWO of the eighteen are the ADR's own argument rather than
    # coverage: one severs the unpinned-guard verdict and one severs `main`'s consumption of the
    # finished list, and NEITHER is reachable by a unit case — they go red only through the case
    # that drives `main()` over a constructed tree. That is the residue #213's per-call-site
    # detector cannot see, measured on the guard that enforces the rule.
    # ⟳ 2026-10-05, ROUND 10's FOLD: 163 -> 183. Nineteen entries, and NINE RETARGETS that are not
    # additions — the Blocking replaced a leaf-level PROXY with a rule that reads what an
    # expression HANDS BACK, which moved or dissolved nine anchors. ⭐ FIVE of the nineteen were
    # SURVIVORS on a first run and are here only because the run said so: the case each one
    # needed did not exist, and two of those six exposed a case of the fold's own that could not
    # fail — a branched binding answered by `_is_restore_value` before the rule under test, and a
    # callee-scope substitution no input distinguished. Every `expect` below was derived by
    # RUNNING its mutation against a green control, never written from the finding.
    # ⟳ 2026-10-30, backlog #401: 183 -> 189. Six entries for the node-identity memo that took
    # the suite from ~68s to ~8s — a key coarser than identity, an entry that stops holding its
    # nodes, a key that drops the name, and each of the three freezes — plus ONE RETARGET: the r9
    # nested-class anchor moved, unchanged, into `_class_methods`.
    # ⟳ 2026-10-30, PR #449 round 1's fold: 189 -> 194. Five entries, no retargets — the memo
    # that never reuses, the case-folded key, the cap that never evicts, eviction by insertion
    # rather than use, and the entry that drops its arguments (asserted on the node, not the
    # allocator).
    # ⟳ 2026-10-30, PR #449 round 2's fold: 194 -> 196, declared sum 2549 -> 2551 (read with
    # `ast`). Two entries, no retargets — the cap that evicts the SECOND entry, and `>=` for `>`.
    # ⟳ 2026-10-31, PR #443 shard 8: 196 -> 197, declared sum 2807 -> 2808 (read with `ast`). One
    # entry, no retargets — the live reconcile's wall-clock deadline never armed.
    # ⟳ 2026-10-31, PR #443 round 7's fold: 197 -> 201, declared sum 2808 -> 2812 (read with `ast`).
    # Four entries, no retargets — the call site's deadline (passed huge; reverted to an undeadlined
    # assess), the alarm escaping the disarm, and the handler never restored.
    # ⟳ 2026-11-07, backlog #231 (suite cost): 201 -> 208. Seven entries, no retargets — each of the
    # five newly memoised tree helpers loses its memo, `classify` loses its memo, and the named
    # real-guard cases classify under a path the live reconcile does not use.
    "scripts/check-main-drivable.py": 208,
    # ⟳ 2026-10-19: check-memory-index-budget joins at 7, declared sum 1545 -> 1552; then
    # 7 -> 12 -> 14 -> 16 and 1552 -> 1561 folding r1 CODEX #2a/#2b/#2c/#6/#7, then r1 CLAUDE
    # H3/L3, then r1 CLAUDE N1's two, then r2 CODEX's six, then r2 CLAUDE's six over the
    # ⟳ 2026-10-20: check-review-decision and the new check-decision-scheme join. ⚠ No
    # delta is quoted here either — see the note at EXPECTED_MUTATIONS for why a recited
    # tally drifts. ⟳ backlog #359: the total is no longer stated at all — `declared_total()`.
    # readable subjects where the counts TIE, chosen by the alphabet, and had no caller outside
    # its own self-test.
    # facts/render REDESIGN (22 -> 28, 1567 -> 1573) —
    # seven mutations the two halves found SURVIVING that I had not written,
    # SURVIVING that I had not written, three of which let the guard measure the WRONG FILE. It guards the
    # one quantity that decides whether an index row ARRIVES, and the index had been over the
    # harness's injection limit — truncated in silence — with every other memory signal green.
    # ⚠ Its 4th entry (bytes -> characters) is the reason the suite has 18 cases and not 16: run
    # against the delivered script it reddened NOTHING, because the live index is under budget on
    # either count. The docstring argued bytes-vs-chars was load-bearing and no case witnessed it.
    "scripts/check-memory-index-budget.py": 28,
    "scripts/check-memory-link.py": 8,
    # backlog #410 (2026-10-30): the stalled-work detector joins with 31 entries — 22, plus 9 for the
    # untrusted-gh-text fold (cross-repo PRs dropped, every printed gh string held to a shape).
    # ⟳ r1 fold: 31 → 58. NINE retired WITH THEIR SUBJECT — the no-upstream exclusion, the age window,
    # the checkout-mtime filters (two), the main-checkout skip, `updatedAt` (two) and SAFE_REF_RE (two,
    # now `shape`) are gone, F5/F6/F7 removed them. 36 entered against the r1 code, which re-covers
    # each retired subject's replacement and has at least one per finding F1-F10.
    # ⟳ cap-and-cache: 58 → 79. 21 for the hook block's 8-line cap and its summary, the uncapped
    # CLI, and the 10-minute cache (hit, expiry, malformed, atomic write, age, key, main checkout).
    # ⟳ r2 REDESIGN: 79 → 105. THREE retired WITH THEIR SUBJECT — gh's own budget (one deadline now)
    # and the squash heuristic (two: its match and its empty-diff guard), all gone. 29 entered: the
    # cache's schema (one per refusal), shaping at render, ages recomputed from now, the candidate
    # window, whitespace-exact MERGED, and the one deadline (expired, killed, shared by every call).
    # ⟳ r3: 105 → 112. ONE retired as EQUIVALENT, not with its subject: `--verbatim` → `--stable` now
    # survives (measured, 233/233 green) because `git merge-tree` refuses the whitespace case on its own.
    # 8 entered: the merge-tree requirement and its conflict rule, the orphan merge base, the cache's
    # tip-moved check and its packed-refs read, the hook's catch-all, the bounded drain, a list `kind`.
    # ⟳ SPLIT (r3 decision): 112 → 80. The cache left this file whole (it is preserved on the branch
    # `stalled-work-cache` and filed as its own backlog row), and 32 entries were RETIRED WITH THEIR
    # SUBJECT: the cache's read, expiry, key, atomic write and schema (21), the age line, `_clip`, the
    # candidate window, ages-from-measurement, the tip-moved check, its packed-refs read and the list
    # `kind` (11). Nothing was retargeted; every one that remains is run against the suite below.
    # ⟳ r4 (F1): 80 → 84. `own_prs` REFUSES a malformed gh node instead of dropping it: six entries
    # pin the validation (2 retired: the old drop-based filter's two anchors no longer exist).
    # ⟳ backlog #545 (2026-11-07): 84 -> 103. 19 for DIRTY-NO-CI — a PR conflicting with master whose
    # head has no check run: the query's two fields, the `mergeable` refusal, CONFLICTING vs UNKNOWN,
    # `head_has_run` (inverted, head-oid check), the fact and item plumbing (4), the item's three
    # conditions, the draft precedence, its age and wording, and its stalled state and hook tier.
    # Nothing retired; three existing anchors re-bound to the same edit (a trailing `,` and one
    # extended past a line `head_has_run` now shares).
    # ⟳ resumed build (2026-11-08): 103 -> 106. The DIRTY line carries its age (2: the age, and an
    # unknown date said as unknown), and a fresh DRAFT that conflicts is reported (1, PR #537).
    # ⟳ backlog #545 r1 fold (2026-11-08): 106 -> 122. 16 new: a run is a `pull_request` workflow suite (push
    # event, any suite, truncation, a missing key: 4), DIRTY-NO-CI's own first hook tier (1), UNKNOWN-MERGE (own_prs,
    # the item, its head-run test, its stalled state, pr_fact, items_from: 6), the mergeable enum (1), the master
    # base (test, refusal, query: 3), the future-date floor (1). Nothing retired; 14 existing anchors re-bound to
    # the same edit on the reshaped lines.
    # ⟳ backlog #545 r2 fold (2026-11-08): 122 -> 133. 11 new: an unseen run is DIRTY-UNSEEN, never the no-CI
    # diagnosis (the item, its stalled state, its hook tier: 3), a malformed suite page is unmeasured (2), the
    # UNKNOWN-MERGE grace (gone, given to an undated head, its last second, its width: 4), the base-ref refusal (2).
    # Nothing retired; 12 existing anchors re-bound to the same edit on the reshaped lines.
    # ⟳ backlog #545 Phase 6 fold (2026-11-08, `docs/reviews/architecture-review-2026-11-08-dirty-pr-states.md`):
    # 133 -> 133. 10 RETIRED with the code they named, which the fold deletes: DIRTY-UNSEEN's branch, stalled state
    # and tier (3), UNKNOWN-MERGE's branch, head-run test and stalled state (3), the MERGE_GRACE_S grace (4). 10 new:
    # the one UNMEASURED line (both OK points, the UNKNOWN arm, never hiding a stale or undated draft, never a stalled
    # state, never a hook tier: 7), and r3 Claude R3-F1's well-formed suite node (3). Re-bound to the reshaped lines:
    # 5 (head_has_run inverted, the head-run test, the NOT MEASURED wording, DIRTY-NO-CI's stalled state and tier);
    # 3 expects renamed with their cases, one of them (the missing checkSuites key) stale since r2.
    "scripts/check-stalled-work.py": 133,
    # backlog #399 (2026-10-30): the usage pacing hook's rules, its override and its two hook paths.
    # ⟳ PR #446 r1 fold: 27 -> 63. One retired with its subject (the REFUSE text no longer names the
    # override, so "drops the override hint" became its inverse) and 37 new: the timestamp bounds, the
    # regular-file read, the expiring main-checkout override, the two readers, and the SendMessage gate.
    # Then 63 -> 74: the absent-cache notice said once per session, and the stale message's path.
    # ⟳ PR #446 r2 fold: 74 -> 85. Two retired with their subject (the wake gate no longer reads the
    # recipient's name, so "a name CONTAINING main" and "a [ref] suffix" have nothing to mutate) and 13
    # new: the caller's agent_id (5), integers parsed as floats and the parser's RecursionError (3), the
    # read's deadline (3), and stripping every GIT_* variable (2).
    # ⟳ PR #446 r3 fold: 85 -> 94, none retired. The reader thread as a DAEMON, killed only by a case that
    # runs the checker as a child process (1), and the control messages allowed at REFUSE (8).
    # ⟳ PR #446 r4 fold: 94 -> 102, none retired. The stdin read's deadline at both call sites, as a daemon,
    # failing toward the gate (4), its byte bound through real stdin (2), the control type as a string (1), and
    # the missing-cache case's precondition (1).
    # ⟳ backlog #525 r1 fold: 148 -> 153, none retired. The next-stop choice for a tie, a past rise end and the 99% branch (3),
    # seconds on a non-aligned forecast and minutes on an aligned one (2).
    # ⟳ backlog #525 r2 fold: 153 -> 155, none retired. A fractional forecast rounded up (1), and the seconds test on the rounded value (1).
    # ⟳ backlog #501: 155 -> 164, none retired, 7 re-bound to the new signatures. The meter log's TAIL read: the seek
    # (1), the partial-line drop (1), the byte before the window (1), the out-of-window refusal (1), the cut flag itself
    # (1), an earlier window's row reaching midnight (1), main() passing the cut flag to evaluate (1), the tail's
    # non-blocking open (1) and its missing-file answer (1).
    # ⟳ PR #531 r1 fold: 164 -> 171, none retired. A cut part out of time order refused (1), equal times in order (1),
    # the order check advancing (1), a whole log never refused for order (1), an earlier window's row after midnight
    # proving the cut (1), read_meter's 3-tuple failure (1) and the tail's lenient decode (1).
    # ⟳ PR #531 r2 fold: 171 -> 178, none retired, 1 re-bound (the r1 F3 entry, to the new earlier-window line). The
    # order check scoped to the horizon (1), the horizon's boundary (1), the horizon's width (1), a resets_at that goes
    # back refused (1), that check advancing (1), an earlier window's row counted only before this window's first (1),
    # and this window's first row being marked (1).
    # ⟳ PR #531 r3 fold (the Phase 6 redesign, docs/reviews/architecture-review-2026-11-07-meter-log-tail-proof.md):
    # 178 -> 174. 13 retired with the code they mutated: the earlier-window row (2: marking it, and the r1 F3 clause),
    # the old order check (4: removed, equal times, advancing, a whole log refused), and the r2 horizon and resets_at
    # order (7). 1 re-bound (the witness removed, was "a cut read is never refused when it misses midnight"). 9 new:
    # the canary removed, the witness's strict < and its skew, `before[0]` and the window bound's slack, the running
    # maximum, `min_at` over every window, a whole log refused for a breach, and the witness applied to a whole log.
    # ⟳ 2026-11-07, backlog #231 (suite cost): 174 -> 175, none retired, none re-bound. `meter_row` loses its memo.
    # ⟳ 2026-11-10, the owner's elastic DAY BAND (11-09) replaces the 1.5× pace line: 175 -> 188. 3 retired-and-replaced
    # with the line's code (its 97 cap, its front-load factor, its last-day suppression -> the floor cap, DAY_FLOOR,
    # the last-day USE IT ALL branch); 3 re-bound (an unknown band silent, the band moving the stop, the five-hour
    # WARN anchor). 13 new: A/B swapped, a constant base, BAND_LOW, BAND_HIGH, the override ignored and read for any
    # window, both zone boundaries inclusive, the zone WARN dropped and NORMAL warning, TREND_BASE, TREND_PER_DAY, and
    # USE IT ALL said beside a refusal.
    # ⟳ 2026-11-10, pace-band r1 fold: 188 -> 196, none retired. 7 re-bound by the fold's own edits (the zone WARN set
    # gained BAND_UNKNOWN: 3 anchors; the unknown band's return value; the last-day test is now `on_last_day`: 3
    # anchors) and 2 expects renamed (the trend case's tighter edges). 8 new: U1 (UNKNOWN back to OK), C2 (the last
    # day exclusive again), L5 (no age bound; the bound two midnights back), L1 (today's key and the window's key in
    # UTC: Claude r1's surviving mutation and its twin), L2 (the trend line ±0.05: Claude r1's survivor and its twin).
    "scripts/check-usage-pace.py": 202,
    # ⛔ 2026-09-02: `explainer-serve.py` and `gen-backlog-page.py` STILL HAVE NO MUTATION
    # COVERAGE, and this slice tried and failed to give them some. Manifests were written,
    # then removed, because `mutate_delivered` copies ONLY `scripts/` into its temp tree
    # while BOTH suites read repo files outside it — `gen-backlog-page --self-test` opens
    # `docs/backlog.md`, and explainer-serve's new source-coverage case stats `docs/`.
    # MEASURED: `FileNotFoundError: .../tmpw8okpx8z/docs/backlog.md`, 9 files mutated,
    # 0 mutations run.
    #
    # That is a REASON, not an excuse, and it is why neither file was ever in here. Making
    # them mutable means making their suites runnable outside a checkout — a separate piece
    # of work. Recorded rather than papered over: shipping a manifest whose suite cannot
    # execute would report coverage that does not exist, which is the exact failure this
    # harness was built to prevent.
    # ⟳ 2026-11-08 (backlog #428): the push gate's DETECTION, moved out of the shell hook so it can be
    # mutated. EIGHTEEN on arrival: the quote/backslash normalisation (3), the strict and fail-closed
    # layers (3), the word boundaries of `git` and `push` (5), the segment's stop at a separator and a
    # line end (2), the three `GITOPTS` branches (3), and the CLI contract the hook reads (2). Each was
    # hand-checked in a `stage_tree` copy: rc 1, and `parse_fail_names` names its expected case once.
    # ⟳ 2026-11-08, PR #542 round 1 fold: 18 -> 32. FOURTEEN new — the line continuation (C-F1, 1); the
    # non-push exemption (C-F2: stash, commit, never consulted, a later git word, a bare `git` word, 5); strict
    # mode's segment set (C-F2: bare chunks dropped, git chunks kept, 2); redirections (glued, fd digits,
    # separate target, 3); the deadline (X-F1: not armed, SIGALRM ignored, 2); `-c` skipping its value (1).
    # The 18 existing entries were REBOUND to the rewritten code, intent and name unchanged (the regex
    # `GITOPTS` became the token scan `_reach`). Each of the 32 hand-checked in a `stage_tree` copy: rc 1,
    # and `parse_fail_names` names every expected case exactly once.
    # ⟳ 2026-11-08, PR #542 round 2 fold: 32 -> 47. The tokenizer was REPLACED by a quote-aware lexer (`lex`),
    # so 16 entries were REBOUND to it, name and intent unchanged (the quote/backslash removal, the separator
    # and line end, the bare-flag and `-c` skips, the segment's leading word, the line continuation, the
    # exemption, the later-git-word rule — now the `$(` refusal —, the command-word rule, and the three
    # redirection rules). FIFTEEN new: the quote-aware separator (X-F1) and redirection (X-F2), the subcommand
    # position (X-F4), judging every invocation (X-F1), the comment at a word start and only there (2), the
    # unresolved constructs (backtick, subshell, unbalanced quote, ANSI-C, `eval`/`sh -c`, the both-words
    # condition: 6), the assignment and reserved-word skips (2), and the loose reading's quote deletion (1).
    # Each of the 47 hand-checked ONE AT A TIME in a `stage_tree` copy: rc 1, and `parse_fail_names` names
    # every expected case exactly once.
    # ⟳ 2026-11-08, PR #542 round 3 fold (Phase 6 design (b), level 1): 47 -> 79. ALL 47 RETIRED: every anchor was
    # in code the fold DELETES (`normalize` as a reader, the r2 `lex`, `_command_word`, `_subcommand`, `_runs_code`,
    # `_segment`, `_judge`, `segments`, the four modes and the loose layer), so none can bind. Lowering the
    # ratchet to 0 before re-raising it is deliberate and written here, per `CONTEXT.md` -> *Ratchet*. 79 NEW, one
    # per decision branch of `decide`: the trigger (3), rule 3 before the lexer (4), rule 1's switches (3), the
    # lexer's OUTSIDE classes (15), quotes and separators (2), redirections (3), parameters (4), the command word
    # (4), git's global options (5), unknown-valued words in git (4), subcommands (3), push's options (8),
    # destinations (10), code runners and text commands (7), the CLI and the deadline (4).
    # ARITHMETIC: 47 - 47 + 79 = 79. Each of the 79 hand-checked ONE AT A TIME in a `stage_tree` copy: rc 1, and
    # `parse_fail_names` names every expected case exactly once.
    # ⟳ 2026-11-08, PR #542 round 4 fold (Codex X-F1..X-F3): 79 -> 99. TWENTY new, none retired: `&>` never takes a
    # descriptor (X-F1, 1); the branch-change composition rule, its movers (BRANCH_MOVERS, `stash branch`,
    # `branch -m`, `gh … checkout`, an unreadable git option), its rule-1 switches, and the UNKNOWN current branch
    # after `cd`, `-C` and `GIT_DIR=` for `HEAD`/`@` and for no refspec (X-F2, 12); push-option values, separate and
    # `=`, naming the default branch, beginning with `-`, mentioning force, and both escapes (X-F3, 7).
    # ARITHMETIC: 79 + 20 = 99. Each of the 20 hand-checked ONE AT A TIME in a `stage_tree` copy: rc 1, and
    # `parse_fail_names` names its expected case exactly once; 16 existing entries whose code the fold touched
    # re-checked the same way, all still killed and attributed.
    # ⟳ 2026-11-08, PR #542 round 5 fold (Claude C-F1, C-F2, C-F5): 99 -> 107. EIGHT new, none retired: master's
    # hook as a FLOOR (6: `verdict` runs it, `main` prints `verdict`, its bytes checked against master's blob, a
    # missing floor, a stalled floor, master's deny read as `floor`); `NAME+=value` as an assignment prefix and
    # `GIT_DIR+=` as a repository change (C-F5, 2). Three existing entries whose anchors `main` changed ("the
    # deadline is not armed", "decide prints only the verdict…", "decide ignores its has_remote argument") were
    # RE-ANCHORED on the new lines with the same mutation, not retired.
    # ARITHMETIC: 99 + 8 = 107. Each of the 8 new and the 3 re-anchored hand-checked ONE AT A TIME in a
    # `stage_tree` copy: rc 1, and `parse_fail_names` names its expected case exactly once.
    "scripts/push-command.py": 108,
    # backlog #589 (2026-11-09): prune-merged-worktrees.py, NEW; REWRITTEN at the r1 fold (archive, never
    # delete). The 18 deletion-era entries are replaced, not re-anchored: their allowlist, ignored-content and
    # .remember rules no longer exist. One mutation per rule a case turns red: open PR, fork, reuse x2, tracked,
    # unpushed, gone remote, locked, cwd, lsof busy, detached, lsof rc, lsof empty, merged < 2 h, mergedAt
    # missing, cross-device, collision suffix, gh rc, truncation, dry-run, unwritable log, log before move,
    # deadline caught in the loop, CANNOT RUN wording after a move, loop stop near the deadline, archive-size
    # line, half-moved message. ARITHMETIC: 27.
    # r2 fold: the gone-remote entry DROPPED with its rule (F2); the half-moved entry re-anchored; 13 ADDED:
    # post-move check, prunable return, zone-less mergedAt, warn boundary, GIT_DIR drop, one-shot stop,
    # hook cap (F5, 7: main's duplicate cap was removed, not tested); placeholder, absolute undo (F1/F10);
    # repair advice (F4); refusal kept + refusal recorded (F6); by-peer (F7). ARITHMETIC: 27 - 1 + 13 = 39.
    # r3 fold (the cap): 4 RE-ANCHORED (post-move check, refusal kept, refusal recorded, by-peer: their code
    # changed), 13 ADDED: F1 old-path absence, F1 verdict, F1 rc, F1/F4 hook line, F6 O_EXCL, F4 write catch,
    # F2 live HEAD x2, F3 registration + its HEAD, F5 expiry, F7 quoting + non-printable withheld.
    # ARITHMETIC: 39 + 13 = 52.
    "scripts/prune-merged-worktrees.py": 52,
    # ⟳ 2026-11-12, backlog #586 slice 2: the strace-log path resolver, pinned in the commit that creates it.
    # One entry per refusal and per cwd-model rule, the #602 location rule's allowed roots one each.
    # ⟳ 2026-11-12, backlog #586 slice 3: the default-deny classifier and record assembly. One entry per measured-
    # constant comparison, denied family, ioctl/open/mmap write rule, record field, seed-merge rule, cross-run rule
    # and exempt write path. ARITHMETIC: 85 + 99 = 184.
    # ⟳ 2026-11-12, slice 3 round 1 fold: 22 anchors re-bound in place (the resolver refactor), 19 added for the new
    # branches (SHADOW argument, the cross-run view, `_meets` both directions, `_cross_forms`, bare descriptors).
    # ARITHMETIC: 184 + 19 = 203. ⟳ round 2 fold: 3 added (a SHADOW `..`, a SHADOW /proc link, the `cross` flag) = 206; 1 re-bound (the resolver refusal, now `cross=True`), 1 re-targeted (a socket SHADOW now names the link check). ⟳ round 3 fold: 2 re-bound (the SHADOW `..` and /proc lines moved into the shared branch), 1 added (a SHADOW argument skips the link checks), 1 re-targeted (a socket taken for a SHADOW no longer reddens a link case; it drops the socket from the READ view, now a case) = 207.
    "scripts/strace_reads.py": 207,
}
