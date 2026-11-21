# Round 2 — `rm-backup` — coordinator — ⟳ NOT CONVERGED (Claude: 6 MAJOR, 7 MINOR); all FOLDED, the `mktemp` exemption DROPPED

REVIEW GAP: codex — alternation (round 2 runs ONE half; both halves were owed in round 1). Round 3 is Codex.

Subject: PR #608, branch `rm-backup-hook`, reviewed head `644942d0`. Half: `docs/reviews/claude/rm-backup-r2-claude.md`.
The fold was written by a subagent (`rm-r2-fold`) in a scratch repo, not by the coordinator.

```yaml
round: 2
fixes_nontrivial: true
subject: rm-backup
halves:
  claude: ran
  codex: gap
findings:
  - {id: R2-1, severity: Major, aim: deliverable, fix_induced: false, component: scan, disposition: fixed}
  - {id: R2-2, severity: Major, aim: deliverable, fix_induced: true, component: command-position, disposition: fixed}
  - {id: R2-3, severity: Major, aim: deliverable, fix_induced: false, component: variables, disposition: fixed}
  - {id: R2-4, severity: Major, aim: deliverable, fix_induced: false, component: cwd, disposition: fixed}
  - {id: R2-5, severity: Major, aim: deliverable, fix_induced: true, component: exemptions, disposition: fixed}
  - {id: R2-6, severity: Major, aim: deliverable, fix_induced: false, component: variables, disposition: fixed}
  - {id: R2-7, severity: Minor, aim: deliverable, fix_induced: false, component: cwd, disposition: fixed}
  - {id: R2-8, severity: Minor, aim: deliverable, fix_induced: false, component: variables, disposition: fixed}
  - {id: R2-9, severity: Minor, aim: deliverable, fix_induced: false, component: command-position, disposition: fixed}
  - {id: R2-10, severity: Minor, aim: deliverable, fix_induced: true, component: scan, disposition: fixed}
  - {id: R2-11, severity: Minor, aim: deliverable, fix_induced: false, component: scan, disposition: fixed}
  - {id: R2-12, severity: Minor, aim: deliverable, fix_induced: true, component: scan, disposition: fixed}
  - {id: R2-13, severity: Minor, aim: test, fix_induced: false, component: self-test, disposition: fixed}
  - {id: S15, severity: Medium, aim: deliverable, fix_induced: true, component: variables, disposition: fixed}
  - {id: S16, severity: Medium, aim: deliverable, fix_induced: true, component: scan, disposition: fixed}
  - {id: S17, severity: High, aim: deliverable, fix_induced: true, component: exemptions, disposition: fixed}
  - {id: S18, severity: High, aim: deliverable, fix_induced: true, component: scan, disposition: fixed}
  - {id: S19, severity: Medium, aim: deliverable, fix_induced: false, component: variables, disposition: fixed}
  - {id: S20, severity: High, aim: deliverable, fix_induced: true, component: variables, disposition: fixed}
  - {id: S21, severity: Medium, aim: deliverable, fix_induced: true, component: exemptions, disposition: fixed}
  - {id: S22, severity: Medium, aim: deliverable, fix_induced: true, component: variables, disposition: fixed}
```

**Where the S-ids come from.** S15–S17 and S20–S22 are automated push-time security reviews (the `security-guidance`
plugin, not a review half) of the fold's draft commits in the scratch repo; S18 and S19 the fold subagent found
itself. None of S15–S22 reached the branch before being fixed. `fix_induced: true` on an S-id means it was caused by
THIS round's draft fold; on an R2-id, by round 1's fold (R2-2 by S1's, R2-5 by R1-3/S14's, R2-10 and R2-12 by fold
11's arithmetic and ANSI-C branches).

**Fixes, each with a case and a mutation killed by the case it names:**

| Id | Hole | Fix |
|---|---|---|
| R2-1 | `<<END-X`: only `END` was the delimiter, so commands after the heredoc were stripped | the full shell word is the delimiter, quote-removed; any quote makes the body literal |
| R2-2 | `nice -n 5 find . -delete`, `env -u H xargs rm` — S1's runner scan found only `rm` | the scan stops at the first word whose basename is `rm`, `xargs` or `find`, and dispatches on it |
| R2-3 | `X="v a"; rm $X` deleted `v` and `a` | an unquoted expansion is split: the whole value and each piece are backed up |
| R2-4 | `cd nope; rm v`, `if …; then cd d; fi; rm v` | a `cd` inside a compound is unknown; a `cd` to a missing dir, or after another command, is trusted only within its `&&`/`\|` chain |
| R2-5 / S17 / S21 | five ways around the `mktemp` exemption (with S13, S14 from round 1) | **exemption DROPPED** — see below |
| R2-6 | `$PWD` after `cd`, `for`, `read`, `export X=v`, `printf -v` | `PWD`/`OLDPWD` seeded from the payload and moved by each tracked `cd`; the other setters make the variable unknown |
| R2-7 | `builtin cd`, `eval cd`, `source` | `builtin` is looked through; `eval`/`source`/`.` make the cwd and every variable unknown |
| R2-8 | `${S:-x}` with an empty `S` | `:-`, `-`, `:=`, `=`, `:?` follow bash |
| R2-9 | `-de""lete`, `{rm,v}`, `/bin/r? v` | the prefilter reads quote-stripped text; a glob or brace command name is refused |
| R2-10 | `${a[x<<y]}` opened a heredoc | `${…}` copied whole, brace-matched |
| R2-11 | `rm ")"` read `)` as an operator | quoted operator characters become placeholders until `expand` |
| R2-12 | `$'\UFFFFFFFF'` crashed (whole call NOT CHECKED) | an out-of-range code point stays literal |
| R2-13 | a case named for `find -H` could not fail for that reason | renamed to what it asserts |
| S15 / S22 | `declare -n/-a/-A/-i/-l/-u/-c` read as plain assignments; the attribute forgotten after the `declare` | the variable is unknown; attributes persist per variable; a nameref's assignment makes every variable unknown |
| S16 | `case x in a) (X=a.tmp; true);; esac` — the subshell's `)` read as a pattern end | a `)` is a pattern only right after `case W in` or `;;`/`;&`/`;;&` |
| S18 | R2-11's placeholders were never restored (keyed by character, not code point): `rm "a;b"` looked up a name that does not exist and backed up nothing | keyed by code point, restored at the end of `expand` |
| S19 / S20 | `X=b; if false; then X=a; fi; rm $X`; a guarded assignment to an UNSET variable stored | under a guard the variable is unknown unless it already held that value; a `&&`-chain assignment holds only for the rest of its chain |

Also fixed outside the review, each with a case: backslash-newline continuation; a `case` pattern is not a command name.

**The redesign (R2-5 / S17 / S21).** The same-command `mktemp` exemption produced holes in BOTH rounds — S13, S14
(round 1), R2-5 and S17 and S21 (round 2) — every one a way the path left in `$T` stops being the fresh directory
(moved into, re-assigned, derived from, used by a mover through a wrapper). Each patch tracked the variable further
and the next review found the next path. **Can a redesign remove it? Yes: dropping the exemption removes the whole
class**, because nothing is then exempt that has to be followed. `T=$(mktemp …)` is an unknown variable and its `rm`
is refused, with a message saying to make temp dirs in the session scratchpad. One narrow helper keeps that advice
true: `T=$(mktemp [-d] /literal/scratchpad/x.XXX)` alone in its word gives `T` the glob of that path, so the existing
scratchpad exemption decides — it tracks no taint.

**Measured after the fold (`7a61b16` → `42a07dd` + `adab93d` in the scratch repo, copied into this branch):**
self-test 112/112; scoped mutation sweep 76/76 killed, each by the case it names (run by the coordinator, not only
the subagent); replay over 18,097 past Bash calls: 185 `rm`s seen, 106 refused, 4 NOT CHECKED (baseline at fold 11:
268 seen, 23 refused). Of the newly refused: ~29 are `mktemp` dirs outside the scratchpad (true by the new rule, the
accepted cost); 5 are `cd D && V=/lit; …; rm $V` (true by S20 — `V` is unset if the `cd` fails); 42 are replay
artifacts (their `cd` targets no longer exist), ~16 of which are true anyway (`; cd D; rm`); 1 is a `;`-chained `cd`.

**Thrashing — not armed, and recorded so round 3 can test it.** The rule asks for two CONSECUTIVE rounds whose
findings came from the PREVIOUS round's fix in one component. Round 1's fix-induced findings came from its own
draft, not a previous round, so round 2 is the first round to qualify: `exemptions` (R2-5), `command-position`
(R2-2), `scan` (R2-10, R2-12). If round 3 finds a hole caused by THIS fold in `scan` or `variables`, it arms — and
`variables` is the likely one (S15, S19, S20, S22 all landed there). `exemptions` cannot recur: it is gone.

**Bounds kept, stated in the docstring:** an `rm` the shell builds at run time inside a quoted string, `eval`,
`bash -c`, a script file or another language; a command NAME from an unknown variable; a glob command word found by
the runner scan (`timeout 5 /bin/r? v`); `unlink`/`rmdir`.
