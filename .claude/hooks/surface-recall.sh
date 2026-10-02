#!/usr/bin/env bash
# PostToolUse(Bash, begin-plan.py) — surface the memory entry for the step that is now current.
#
# This is the CALLER for scripts/recall-llm.py (backlog #191). A matcher nothing invokes is the
# inert field this design spent a day arguing about.
#
# ⛔ M2 — AND THIS COMMENT USED TO CLAIM `check-ratchet-contract.py` REFUSES A CALLER-LESS
# GUARD, WHICH IS FALSE OF THIS FILE. That check applies R3 (a caller) only over
# `discover_guards()`, whose population is `GUARD_PATH_RE.fullmatch` — `check-*.py`. Verified
# by running it: `guards discovered (41)` lists every `check-*.py` and NOT `recall-llm.py`,
# which gets R4 only, and the code says so in as many words. **So deleting this hook and its
# `.claude/settings.json` entry would leave that gate green.** The caller exists by design,
# not by enforcement, and nothing currently protects it — said plainly rather than implied by
# a citation that does not reach. This is quote-the-code-don't-characterise-it applied to a
# comment: the sentence was true of the guard in general and false of the file it sat in.
#
# ⛔ WHY IT TRIGGERS ON `begin-plan.py` AND NOT ON EVERY Bash CALL. The refuted lexical matcher hung
# off PreToolUse(Bash) and fired ~275 times a session, on 52.7% of real commands with an 11.7%
# false-fire rate. Measured 2026-09-29, that is the failure and not the goal: the cost of a fire is
# the reader's attention, not compute. A STEP TRANSITION is the moment a lesson is useful, and
# `begin-plan.py` is the only event that marks one — arming a plan, or `--tick` moving to the next
# step. That is ~15 firings a day against ~275, and each one is a different situation.
#
# ⛔ IT MAKES NO MODEL CALL, DELIBERATELY. `--arm` costs 16.1s (measured, opus, 15,336-char prompt)
# and is the only path that spends money. Putting it here would block a Bash call for 16s and would
# spawn a nested `claude -p` from inside a hook, which nothing has tested. So this hook runs ONLY
# `--fire`, a cache lookup measured at 0.12s. When the cache is absent it says so in one line — a
# READ-TRIGGER, which is the mechanism this repo has actually measured to work, rather than relying
# on the author remembering to arm it, which is the failure #191 was filed about.
#
# ⛔ NEVER BLOCKS, NEVER FAILS THE CALL. `exit 0` unconditionally. Surfacing a memory entry is advice
# about a moment, not a verdict about a command. ⚠ The corollary, stated rather than discovered: this
# hook's exit code carries NO information — do not read it as a verdict on the matching.
#
# ⛔ STRUCTURED JSON, NOT PLAIN STDOUT. Measured 2026-09-29: a hook's plain stdout at exit 0 reaches
# the USER'S TRANSCRIPT, not the model's context. The matcher's audience is the model, so plain
# stdout puts it in the one place it cannot work. This repo has a name for that defect — a gate's
# channel can be weaker than the gate.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# ⭐ THE ONE SEAM, AND IT EXISTS SO THIS HOOK CAN BE TESTED WHERE IT SHIPS.
# ⛔ IT IS ARGV, NOT AN ENVIRONMENT VARIABLE, AND THAT WAS ROUND 7 M1. The first version read
# `${RECALL_MATCHER:-…}`, which any ambient variable in the session could set — giving either
# SILENT TOTAL DISABLEMENT (rc=0, no output, no diagnostic) or arbitrary text in
# `additionalContext` at every step transition. An env var is also invisible to a diff, so
# `git status`, the guards and CI were all blind to it. `.claude/settings.json:57` invokes this
# file as `bash .claude/hooks/surface-recall.sh` and passes NO argument, so `$1` is unreachable in
# production BY CONSTRUCTION rather than by convention — and the guard that must override it is a
# caller, which is exactly who should be able to.
# ⛔ WHY A SEAM RATHER THAN A STAGED COPY — round 7 B2, measured. `check-rc-contract.py` used to
# observe this hook by staging a MINIMAL tree (this file plus a stub matcher) and running it there.
# A staged tree is a PROXY FOR THE REPO, and the set of things a shell script can read — files,
# env, $HOME, tools on PATH — is open, so the proxy has a boundary like every other. Reproduced: an
# arm branching on `$REPO_ROOT/.claude/settings.json` rendered a dangling `Detail:` in the real repo
# while the guard reported CLEAN, because the staged tree had no settings.json. Staging more files
# is the same enumeration trap one layer down.
# ⭐ So `scripts/check-surface-recall.py` runs THIS FILE, IN THIS REPO, and substitutes only the
# matcher through this variable. There is no fabricated world left to be unfaithful.
MATCHER="${1:-$REPO_ROOT/scripts/recall-llm.py}"
[ -f "$MATCHER" ] || exit 0

OUT="$(python3 "$MATCHER" --fire 2>&1)"; RC=$?

# rc=0 with no output is the common and correct case: no plan armed is rc=2, a paused thread and a
# NONE answer are both a silent rc=0. Only two things are worth the model's attention.
PAYLOAD=""
case "$RC" in
  # ⛔ H4. THIS NO LONGER MATCHES A LITERAL, AND DELETING THE RULE IS THE FIX. It used to test the
  # matcher's stdout for `⭐ recall —`, duplicating `render`'s first line across a file boundary
  # with nothing reconciling them: every mutation entry targets the python file, this hook has no
  # self-test, and no case asserted the pattern. Measured — changing `render`'s literal to
  # `⭐ recall:`, an ordinary wording tweak, left the suite at 128/128 and the hook forwarding
  # NOTHING. The rc contract already carries the distinction: rc 0 WITH output is a match, rc 0
  # with no output is "nothing applies", and that is a fact about the contract rather than about
  # one sentence's spelling.
  0) [ -n "$OUT" ] && PAYLOAD="$OUT" ;;
  # ⛔ M4: `-n "$OUT"` because the matcher now deduplicates the NAG's message while keeping rc 3
  # every time — the contract must not lie about the outcome, but the reader should not be told to
  # run `--arm` on every single begin-plan.py call for the same step.
  3) [ -n "$OUT" ] && PAYLOAD="recall-llm: the recall cache for this plan is absent or stale, so no memory entry was
surfaced for this step. Run \`python3 scripts/recall-llm.py --arm\` to match this plan's steps
(one model call, ~16s, covers every step). Detail: $OUT" ;;
  # ⛔ rc=5 IS NOT SILENCE, AND SPLITTING IT OUT OF rc=2 IS HALF OF B1's FIX. A plan IS armed and
  # the matcher cannot read it — 87 committed plans are in that shape. While this shared rc=2 with
  # "nothing is armed", the catch-all below swallowed it and the reader heard nothing at all, which
  # is the refuted matcher's H3: "nothing fires" and "could not look" arriving as one observation.
  # ⛔ backlog #201 — THE `Detail:` CLAUSE IS NOW CONDITIONAL, AND THE OBVIOUS FIX WAS WRONG.
  # `do_fire` empties the message when its dedupe says the sentence was already said, and this arm
  # forwarded unconditionally, so from the SECOND firing onward the reader got a sentence ending
  # "Detail:" with nothing after it — forever, because the marker persists. Measured with the hook
  # as sole caller: 409 chars, then 148, then 148.
  # ⛔ AND NOT `[ -n "$OUT" ] && PAYLOAD=…` LIKE ITS SIBLINGS: that makes a deduped rc=5 SILENT,
  # which is the conflation B1 split this code out of rc=2 to end. rc=5 IS NOT SILENCE. So the
  # static sentence always goes, and only the detail is conditional.
  5) PAYLOAD="recall-llm: a plan IS armed and the matcher cannot read it, so NO memory entry was
surfaced for this step — this is not 'nothing applies'."
     [ -n "$OUT" ] && PAYLOAD="$PAYLOAD Detail: $OUT" ;;
  # ⛔ backlog #202 — rc=6, THE CORPUS SIDE OF THE SAME CONFLATION. A plan is armed and the cache
  # is valid, and the corpus directory is gone. This was rc=2 until #202, so the catch-all below
  # ate it: measured, a 161-char message ending "NOTHING WAS SURFACED" reached the reader as ZERO
  # bytes against a 290-byte control. Same shape as rc=5, same treatment, same reason.
  6) PAYLOAD="recall-llm: a plan IS armed and the memory corpus cannot be reached, so NO memory
entry was surfaced for this step — this is not 'nothing applies'. The plan is fine; the corpus is
missing."
     [ -n "$OUT" ] && PAYLOAD="$PAYLOAD Detail: $OUT" ;;
  *) : ;;   # rc=2 CANNOT RUN (no plan armed) is a normal state, not this hook's business
esac

[ -n "$PAYLOAD" ] || exit 0

python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":sys.stdin.read()}}))' <<<"$PAYLOAD"
exit 0
