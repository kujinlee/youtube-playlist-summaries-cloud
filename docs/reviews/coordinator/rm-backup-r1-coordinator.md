# Round 1 — `rm-backup` — coordinator — ⟳ NOT CONVERGED (Codex: 3 BLOCKER, 3 MAJOR, 1 MINOR); all FOLDED

REVIEW GAP: claude — the reviewer sat 46 min on an unanswered permission prompt for an `rm -rf` of its own temp dir (the ceremony this PR removes) and was stopped at 17:34 with no file written; its probe results were salvaged from its transcript as C1–C5 below, and the Claude half runs in round 2.

```yaml
round: 1
fixes_nontrivial: true
subject: rm-backup
halves:
  codex: ran
  claude: "GAP: stopped on an unanswered permission prompt; probes salvaged as C1–C5"
findings:
  - {id: R1-1, severity: High, aim: deliverable, fix_induced: false, component: scan, disposition: fixed}
  - {id: R1-2, severity: High, aim: deliverable, fix_induced: false, component: scan, disposition: fixed}
  - {id: R1-3, severity: High, aim: deliverable, fix_induced: false, component: exemptions, disposition: fixed}
  - {id: R1-4, severity: Medium, aim: deliverable, fix_induced: false, component: exemptions, disposition: fixed}
  - {id: R1-5, severity: Medium, aim: deliverable, fix_induced: false, component: prune, disposition: fixed}
  - {id: R1-6, severity: Medium, aim: deliverable, fix_induced: false, component: command-position, disposition: fixed}
  - {id: R1-7, severity: Low, aim: test, fix_induced: false, component: self-test, disposition: fixed}
  - {id: S1, severity: High, aim: deliverable, fix_induced: false, component: command-position, disposition: fixed}
  - {id: S2, severity: High, aim: deliverable, fix_induced: false, component: scan, disposition: fixed}
  - {id: S3, severity: Medium, aim: deliverable, fix_induced: false, component: variables, disposition: fixed}
  - {id: S4, severity: High, aim: deliverable, fix_induced: true, component: scan, disposition: fixed}
  - {id: S5, severity: Medium, aim: deliverable, fix_induced: true, component: scan, disposition: fixed}
  - {id: S6, severity: Medium, aim: deliverable, fix_induced: true, component: scan, disposition: fixed}
  - {id: S7, severity: Medium, aim: deliverable, fix_induced: false, component: find, disposition: fixed}
  - {id: S8, severity: Medium, aim: deliverable, fix_induced: true, component: command-position, disposition: fixed}
  - {id: S9, severity: Medium, aim: deliverable, fix_induced: false, component: exemptions, disposition: fixed}
  - {id: C1, severity: High, aim: deliverable, fix_induced: false, component: scan, disposition: fixed}
  - {id: C2, severity: Medium, aim: deliverable, fix_induced: false, component: targets, disposition: fixed}
  - {id: S10, severity: High, aim: deliverable, fix_induced: true, component: scan, disposition: fixed}
  - {id: S11, severity: High, aim: deliverable, fix_induced: true, component: scan, disposition: fixed}
  - {id: S12, severity: High, aim: deliverable, fix_induced: false, component: find, disposition: fixed}
  - {id: S13, severity: Medium, aim: deliverable, fix_induced: true, component: variables, disposition: fixed}
  - {id: S14, severity: Medium, aim: deliverable, fix_induced: true, component: exemptions, disposition: fixed}
  - {id: C3, severity: Medium, aim: deliverable, fix_induced: false, component: targets, disposition: fixed}
  - {id: C4, severity: High, aim: deliverable, fix_induced: false, component: command-position, disposition: fixed}
  - {id: C5, severity: High, aim: deliverable, fix_induced: false, component: find, disposition: fixed}
```

Codex on `ab4b70e6` reproduced every BLOCKER by running bash on a victim file. Two automated push-time security
reviews (the `security-guidance` plugin, not a review half) added S1–S8: S1–S3 against the pushed head, S4–S8 against
the in-progress fold commit in a scratch copy — S4, S5, S6 and S8 were caused by that fold's first draft and never reached
the branch.

**Fixes, each with a case and a mutation killed by it:**

| Id | Hole | Fix |
|---|---|---|
| R1-1 | `echo foo\ #; rm v` — an escaped blank read as a word end, so `#` hid the `rm` | the scan records the escaped index; `#` opens a comment only after an UNESCAPED word start |
| R1-2 | an unquoted heredoc's `$(rm v)` ran; bodies were dropped | each `$(…)`/backtick in an UNQUOTED body is parsed by `rm_calls`; an `rm` there is refused (quote the delimiter) |
| R1-3 | `T=$(mktemp -d); ln -s /x $T/out; rm $T/out/v` exempt | only the mktemp dir and its DIRECT entries (no trailing `/`) are exempt; deeper paths are refused |
| R1-4 | a link outside the backup root to a path inside it was exempt | containment is judged on the ENTRY `rm` removes: parent resolved, last name not followed; `rm -r link/` backs up the referent |
| R1-5 | prune followed a session symlink out of the root | prune skips linked sessions/stamps and checks each stamp's realpath parent is the root |
| R1-6 / S1 | `sudo -u root rm v`, `timeout 5 rm v` — option values taken as the command | any command not in `NOT_RUNNERS` is a possible runner; a later standalone `rm` word starts an `rm` call (too wide costs a backup) |
| R1-7 | the failed-copy case passed as root | the copy failure is injected (`shutil.copytree` raises); the case asserts the refusal names it |
| S2 | `$'\x72m' v` spelled `rm` | `$'…'` decoded as bash decodes it, after heredoc bodies are removed |
| S3 | `( X=a ); rm $X` used the subshell's value | an assignment inside `(…)` is forgotten when it closes; one in a pipeline/background part is unknown |
| S4 | (fold draft) a `"` inside `"$(…)"` ended the outer string | a substitution inside double quotes is skipped whole, its own quotes its own |
| S5 | (fold draft) ANSI-C decoded before heredoc stripping: body text lexed as shell | decode after stripping; the scan skips `$'…'` spans itself |
| S6 | (fold draft) a word search for `rm` in a substitution, beaten by `r$X` | substitution bodies are parsed by `rm_calls`; the prefilter also passes any command holding `$` |
| S7 | `find -LH` combined flags | leading flags are split; any `L`/`f` refuses |
| S8 | (fold draft) `function`/`for`/`case` listed as non-runners | removed: their bodies run |
| C1 | `echo $((x<<y))` then `rm a.tmp` on the next line: arithmetic `<<` opened a heredoc and swallowed the `rm` | `((…))`, `$((…))` and `$[…]` are copied whole by paren depth, so their `<<` is a shift |
| C2 | `rm f{1..3}`: a brace RANGE (no comma) slipped past the brace-list refusal | a range `{a..b}` is refused like a list `{a,b}` |
| C3 | `rm 'a[1].txt'`: the lexer drops the quotes, so it was globbed as `a1.txt` and nothing was copied | each target is read both as a pattern and as the literal name |
| C4 | `/usr/bin/xargs rm`, `/usr/bin/find . -delete`: a path to the tool was not the tool | the basename is compared |
| C5 | `find . -exec sudo rm {} \;`: only an `rm` right after `-exec` counted | any `rm` word in a find with `-exec`/`-execdir`/`-ok`/`-okdir` refuses |
| S10 | (C1 fold) `(( a[1] ))`: the depth count also counted `[` but never `]`, so the span ran to the end and a later `<<`/`#` went unread | each form counts only its own bracket; any substitution inside the span is read for an `rm`, unclosed spans too |
| S11 | (R1-2 fold) `cat <<EOF` / `$(` / `rm v` / `)`: the body was read line by line, so a substitution spanning lines was missed | the whole body is read when its delimiter comes, and at end of input when it never does |
| S12 | `find -H scratch/link -delete`, `find scratch/link/ -delete`: the start was judged without following it, though `-H` and a trailing `/` follow | the start must be exempt both as the entry and at its `realpath` |
| S13 | (S3 fold) `( T=$(mktemp -d) ); rm -r $T`: a `mktemp` assignment skipped the subshell bookkeeping, so FRESH outlived the subshell | the subshell and pipeline checks run before the `mktemp` rule |
| S14 | (R1-3 fold) `cd $T/sub; rm x`: `cd` into a path below the fresh dir counted as `cd $T` | only `cd $T` itself (`$T`, `${T}`, `$T/`) keeps the exemption; a relative `find` start below the fresh dir under `-H` or through a `/` refuses |
| S9 | `rm lnk/../inner/c`: `normpath` collapsed `lnk/..` lexically, so the copy looked at `./inner/c` while the kernel deleted `dir/inner/c` | no lexical normalisation anywhere: each target's parent is `realpath`-resolved (follows the link, then `..`) and the last name kept |

**Measured after the fold (S10–S14 included):** self-test 88/88; scoped mutation sweep 34/34 killed, each by the case it names (two
survivors on the way were a missing refusal case and a redundant pair of prune guards — the prune mutation now removes
both); replay over 18,013 past Bash calls: 268 `rm`s seen, 23 refused (baseline 19), 4 NOT CHECKED. The 3 refusals S14 added are one pattern, `cd $T && find scripts/mutations … -delete` after an `rsync -a` filled `$T` — a start that could be a copied link, so the refusal is right by the rule. An S10 case first used `(( a[1] ))` then `rm`, which the mutation also passed (an over-run copies text, it never hides it); the case now puts a quoted heredoc after it, whose body must still be stripped. A C1 case first used
literal operands (`1<<2`) and its mutation survived (a digit cannot start a heredoc delimiter); it now uses `x<<y`. A first
C2 draft expanded braces; the existing brace-list refusal was kept and widened instead (less code, same safety). A first draft
refused 33 — every extra one a false positive of the word-search substitution rule (S6), gone once bodies are parsed.

**Not thrashing:** S4–S8 were caused by the fold's own draft, and S10, S11, S13 and S14 by incomplete earlier fixes in this same round, all caught by push-time security reviews before the fold was pushed. Arming needs two consecutive ROUNDS whose findings came from the previous round's fix; this is one round. Round 2 (the Claude half) will show whether the scan component keeps producing them.

**Bounds kept, stated in the docstring:** an `rm` the shell builds at run time inside a quoted string, `eval`, `bash -c`,
a script file or another language; a command NAME from an unknown variable; `unlink`/`rmdir`.
