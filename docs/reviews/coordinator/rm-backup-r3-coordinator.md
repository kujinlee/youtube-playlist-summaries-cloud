# Round 3 — `rm-backup` — coordinator — ⟳ NOT CONVERGED (Codex: 2 MAJOR); FOLDED by a REDESIGN of `variables`

REVIEW GAP: claude — alternation (round 3 runs ONE half; round 2 was Claude). Round 4 is Claude.

Subject: PR #608, branch `rm-backup-hook`, reviewed head `05d57187`. Half: `docs/reviews/codex/rm-backup-r3-codex.md`.
The fold was written by the coordinator in a scratch repo (`fold-r1`, commits r3 … r3g) and copied into this branch.

```yaml
round: 3
fixes_nontrivial: true
subject: rm-backup
halves:
  codex: ran
  claude: gap
findings:
  - {id: R3-1, severity: Major, aim: deliverable, fix_induced: false, component: variables, disposition: fixed}
  - {id: R3-2, severity: Major, aim: deliverable, fix_induced: false, component: variables, disposition: fixed}
  - {id: S23, severity: High, aim: deliverable, fix_induced: true, component: variables, disposition: fixed}
  - {id: S24, severity: High, aim: deliverable, fix_induced: true, component: variables, disposition: fixed}
  - {id: S25, severity: Medium, aim: deliverable, fix_induced: false, component: exemptions, disposition: not-applicable}
```

**Where the S-ids come from.** S23–S25 are automated push-time security reviews (the `security-guidance` plugin, not
a review half) of the round-2 fold. `fix_induced: true` on S23/S24 means caused by the PREVIOUS round's fold: both
come from R2-8's `${S:-x}` / `${S:=x}` default handling.

| Id | Hole | Fix |
|---|---|---|
| R3-1 | `X=good; let X=0; rm $X` deleted `0`, backed up `good` | `let`, `((…))`, `$((…))`, `$[…]`, `[[ -eq ]]` make the command OPAQUE |
| R3-2 | `IFS=:; X=a:b; rm $X` deleted `a` and `b`, backed up nothing | `IFS` anywhere in the command, or a non-default `IFS` in the environment, makes it OPAQUE |
| S23 | `eval S=b.txt; rm -f ${S:-/abs/a.tmp}` — after `eval`, every variable was unset, so the default was used | `eval` makes it OPAQUE; the post-`eval` "every variable unknown" branch is gone |
| S24 | `${X:=v}` assigns; `${a[X=0]}` and `${X:1}` evaluate arithmetic | a `${…}` holding `=`, a computed subscript or `:offset` makes it OPAQUE |
| S25 | a link inside a scratchpad `mktemp` dir | NOT a hole: the case `a link inside a scratchpad mktemp dir is followed` shows the target it leads to is backed up |

**The redesign.** `variables` has drawn a new SETTER in every round: S15/S22 `declare` (r2 draft), R2-6 `read`/
`for`/`printf -v`/`export` (r2), R2-8's defaults → S23/S24 (r3 draft), R3-1 `let`, R3-2 `IFS` (r3). Each fold added the
setter to a denylist and the next review found the next one. **Can a redesign remove it? Yes: stop following
setters.** Variables are now read ONLY in a command whose every variable-setting construct is a plain `NAME=value`
word. If anything else that can set one appears anywhere (an allowlist of the plain form, so an unlisted setter
falls on the refusing side wherever its syntax is one of the listed shapes), the command is OPAQUE and every `$`,
`${…}` or `~` in an `rm` target is refused — a literal target is still backed up. `for`/`select`/`unset` are narrower:
they poison only the names they are given, for the whole command (a non-name word, or `unset -n`, is opaque).

⚠ **Bound, stated rather than claimed closed:** the allowlist is a list of SHAPES (`OPAQUE_WORDS`, `OPAQUE_TEXT`,
`ASSIGNING_BRACE`, option setters, a `$`-built command name). A setter that matches none of them — not found in three
rounds and the replay — would be read as plain. That is the residual of this class, now one regex wide instead of one
branch per setter.

**Measured after the fold (scratch `r3g`, copied into this branch):** self-test 123/123; scoped mutation sweep 92/92
killed, each by the case it names (11 dead mutations of the removed setter branches dropped, 27 added; round 2 had 76). Replay over
18,249 past Bash calls: 184 `rm`s seen, 116 refused, 4 NOT CHECKED (round 2's script over the same calls: 106
refused). Every round-2 refusal is still refused. **The first redesign refused 37 more distinct commands**, mostly
`for f in …` loops and `.` as a `git diff .` argument — too wide, so it was narrowed: `.`/`eval`/`source` count only
in command position, `printf`/`wait`/`compgen` only with their setter flag among their OWN words (the replay caught
`printf … && grep -v x` read as `printf -v`), and `for`/`select`/`unset` poison only their names. **After narrowing,
10 newly refused, each classified by re-running the detectors on the full command:** `unset $v` (a name the hook
cannot read) ×6, `eval "$c"` ×1, `$((…))` ×1, `read` ×1, `IFS=: read` ×1 — every one true by the rule.

**Thrashing — NOT armed by the rule, and the near-miss is recorded.** The rule asks for two CONSECUTIVE rounds whose
findings came from the PREVIOUS round's fix in ONE component. Round 2's fold-induced findings (caused by round 1's
fold) were in `command-position`, `exemptions`, `scan`; round 3's (S23/S24, caused by round 2's fold) are in
`variables`. No component has two in a row. The round-2 coordinator doc predicted `variables` as the one likely to
arm; it drew a previous-fold-induced finding for the first time this round. The redesign above is this round's
answer to "can a redesign remove it" whether or not the rule armed, because the same component found a new setter in
every round.

**Round 4 is the round cap** (`review-method.md` §0 Q4c): from round 4, findings are FILED to the backlog unless a
BLOCKER.
