# Phase 6 architecture review — the `quiet-window` component of `scripts/agent-watchdog.py` (backlog #657)

- Subject: `observe`, `_entry`, `fingerprint` and the window logic in `main`, PR #596, read at head `e3f11ad8`.
- Armed by THRASHING: round 2 carried R2M1 and R2M2 and round 3 carried R3m1, each caused by the previous round's
  fold, all in the component `quiet-window` (`docs/reviews/coordinator/agent-watchdog-r2-coordinator.md`,
  `...-r3-coordinator.md`).
- Read first: `CONTEXT.md` (guard, cannot-run, falsifier), `docs/adr/` (ADR-0014, *a guard's main is drivable*, is the
  only one this path touches; nothing here re-opens it), the three coordinator documents, the four review halves, and
  `docs/review-method.md` → *The stop condition* and *Can a redesign remove it?*.
- No tracked code was changed. Every probe and every mutant ran on copies in the session scratchpad.
- Every claim is tagged **[M]** (measured here: a command was run and its output read) or **[I]** (inferred).

## Verdict

1. **The fingerprint design is right in kind.** "Any change in a hash of every observed entry, timed on a monotonic
   clock" answers "has the builder done anything since the last poll" for every input tried. No probe found a miss
   outside the bounds the docstring already states.
2. **The thrashing changed character between the two rounds, and only the first was a mechanism defect.** Round 2's
   findings were dissolved by the redesign the round 2 fold already made. Round 3's R3m1 is a missing witness: no
   reshaping of the code removes it, because the name must stay in the entry. A reshaping of the TEST removes it,
   and removes its whole class.
3. **One field of the entry cannot be witnessed by any input: `kind`.** It is the same defect as R3m1 one field to
   the left, and a fold that adds only a rename case leaves it for round 4.
4. **Recommendation: (b), a small restructure inside the round 3 fold, then stop.** A three-field named entry
   without `kind`, and ONE class case that loops an independent literal of the field names with an identity case.
   After that fold, further `quiet-window` findings are filed, not folded.

## 1. Is the design right in kind? The attempts to refute it

Probe: `probe.py` in the scratchpad, run against an unmodified copy of the script, on real temp worktrees (APFS). **[M]**

| Input | Seen as activity? | Reading |
|---|---|---|
| a rename, its directory's time put back | yes | the name field does its job in the code; only its witness is missing |
| two observations of an untouched tree | same fingerprint | no false activity from observing |
| this worktree, observed twice 20 s apart with nothing running in it | same fingerprint (5546 entries, 0.045 s) | no ambient writer; cost is negligible against a 60 s poll |
| a symlink to a FILE retargeted, parent time put back | yes | the link's own `lstat` time moves |
| a same-size rewrite in place, file time put back | no | stated bound |
| an atomic replace, same size, file and directory times put back | no | stated bound |
| a `gitdir:` pointer retargeted to a twin git directory, same length, time put back | no | stated bound (same shape) |
| `chmod` only | no | inside "names, modification times and sizes"; a builder's `chmod` comes with a transcript line |
| a symlink to a DIRECTORY retargeted to a same-length target, parent time put back | no | **the link is not an entry at all**, see below |

Three things the probes did surface. None of them makes the design wrong in kind.

**(a) `kind` is in the fingerprint and no input can witness it. [M] + [I]** Replacing `kind` with a constant passes
`73/73`, the same result R3m1 reported for the name. **[M]** It cannot be killed: a `tree` name is always the worktree
path joined with something, a `git` name is one of `HEAD`, `index`, `logs/HEAD`, and the transcript's name is the
empty string, so two entries of different kinds never share a name and `(kind, name)` carries nothing `name` does
not. **[I]** A field that no observation can distinguish is not evidence of anything. It is also the next round's
R3m1.

**(b) A symlink to a directory is never an entry. [M]** `os.walk` lists it under `dirs` and does not descend, and
`observe` stats only each `root` and its `files`. Its creation and retargeting are seen through the parent
directory's time alone. The docstring's "every file and directory in its worktree" overstates this by one clause.
It matters for the fold: the case R3m2 proposes ("a looping and a dangling symlink, each an entry") holds for a
loop and a dangling link (both are listed under `files`) and would be false for a link to a directory.

**(c) A directory that becomes a FILE while the walk runs is CANNOT RUN for a working builder. [M]** `_walk_error`
and the walk's `lstat` treat only `FileNotFoundError` as "the builder deleted something". A directory replaced by a
file between the listing and the next step raises `NotADirectoryError`, which becomes CANNOT RUN and ends the
watchdog with exit 2. Measured with one thread flipping `src/flip` between a directory and a file while `observe`
ran in a loop for 20 s: `8391 ok`, `850 CannotRun: cannot list /wt/src/flip: Not a directory`. The rate is inflated
by the continuous flipping. In use it needs a `git checkout` or a rebuild to cross the 0.05 s walk, once a minute.
It is loud, never silent, and costs one false wake and a re-arm. The class "ordinary mid-walk change" is
enumerated by one exception type where it has at least two members. Proposed as a backlog row below, not as part
of this fold.

Considered and rejected: fingerprinting `st_ctime_ns` in place of time and size. It would close the "time put back"
bounds (measured: an `os.utime` restore itself moves the change time **[M]**), but an extended-attribute write moves
it too while leaving the modification time alone (`(True, False)` **[M]**), so anything on the machine that tags
files would count as builder activity. Whether a system service does that in a worktree was not measured. **[I]**
The present bounds need a writer that deliberately restores times; a builder does not.

## 2. Design problem or witness problem?

*Can a redesign remove it?* applied to each fix-induced finding:

| Finding | A different shape dissolves it? | Kind |
|---|---|---|
| R2M1: writes below a retained maximum and deletions unseen | Yes, and the round 2 fold did it: a fingerprint has no maximum to hide under | mechanism, already redesigned |
| R2M2: a wall-clock step moves the window | Yes, same fold: elapsed time on `time.monotonic` | mechanism, already redesigned |
| R3m1: the name has no witness | No reshaping of the CODE. The name must be in the entry (rename probe above) | witness |
| (a) above: `kind` cannot have a witness | Yes: remove the field | a decorative field, found by asking R3m1's question of every field |

So the arming condition fired correctly on the record, and by cause the second half of it is the method doc's
*branch-coverage* row: **fix, plus an exhaustiveness pass.** The structure that produced R3m1 is that the entry is
an anonymous four-tuple whose fields are witnessed one hand-written case at a time. The round 2 fold wrote a case
for size and a case for time and nothing asked "is that all of them?".

### The exhaustiveness pass: one class case

Prototyped in the scratchpad (`classcase.py`) against a restructured copy and run. **[M]**

**Code shape.** Three lines change in the script, and the suite is `73/73` on the restructured copy before any new
case is added: **[M]**

```python
class Entry(NamedTuple):
    name: str
    mtime_ns: int
    size: int

def _entry(name: str, st: os.stat_result) -> Entry:
    return Entry(name, st.st_mtime_ns, st.st_size)
```

The four call sites lose their first argument. Dropping `kind` is safe for the reason in (a).

**Test shape.** One case, in the suite:

- `FIELDS = ("name", "mtime_ns", "size")`, an independent literal, never read from the code. The case first asserts
  `Entry._fields == FIELDS`. A field added to the entry with no witness makes the case red before anything else runs.
- A literal table of one world change per field, plus the identity:
  - `name`: in EACH of two directories, two files with different (time, size) exchange names, and both directories'
    times are put back. Only the pairing of a full path with a (time, size) changes.
  - `mtime_ns`: `os.utime` on one file.
  - `size`: append to one file and put its time back.
  - identity: nothing is touched.
- For each row the case observes before and after and asserts two things: a CONTROL, that the two observations are
  equal once that one field is projected out and differ with it in (the fixture changed that field and nothing
  else), and the PROPERTY, that the fingerprints differ. For the identity row the fingerprints are equal.

The control earned its place during prototyping: a first name witness that moved a file ACROSS directories failed it,
because each directory's own size changed with its entry count. Without the control that witness would have passed
for the wrong reason.

Mutants run against the class case alone: **[M]**

| Mutant | Present suite | Class case |
|---|---|---|
| name constant in `_entry` (R3m1) | 73/73, survives | red |
| time constant | 59/73 | red |
| size constant | 72/73 | red |
| the tree name is the basename only | 73/73, survives | red |
| the tree name is the directory only | 73/73, survives | red |
| a fourth field added to `Entry` | 73/73, survives | red |
| every poll is a change (a clock mixed into the hash) | 49/73 | red (identity row) |
| the git name is a constant | 73/73, survives | **passes** |

The last row is the bound of this case, stated and not hidden: a constant git name is unseen only when `index` and
`logs/HEAD` exchange their exact time and size between two polls. It belongs in the pin comment beside
`GITFILE_MAX` as not mutated, with that reason.

## 3. Recommendation

**(b) Restructure inside the round 3 fold, then stop.**

1. `Entry` as above, `kind` removed. ⚠ The manifest mutation *only the NEWEST time is compared again* indexes the
   tuple (`e[2]`); with three fields the time is `e[1]`, or better `e.mtime_ns`. It is a two-file edit.
2. R3m1 is folded as the class case, not as a lone rename case. Manifest: name constant, tree name the basename,
   tree name the directory, and the identity mutant, each naming the class case. The size and time mutations keep
   the `main`-level cases they name today.
3. R3m2 as the reviewer wrote it, with the claim "each an entry" limited to a looping and a dangling link, and one
   clause added to BOUNDS: a symlink to a directory is seen only through its parent's time.
4. R3m3 as written (`shlex.quote`).
5. The docstring's "a hash over the name, modification time (ns) and size" already describes three fields; the
   signature comment `(kind, name, mtime_ns, size)` in `observe` and in the round documents' prose does not need
   chasing beyond the script.

**Stop condition.** This fold changes code, so the round it closes is no longer `fixes_nontrivial: false`. Round 4 is
under the round cap: its findings are FILED unless a BLOCKER. A third consecutive fix-induced finding in
`quiet-window` after this fold would mean this review misjudged the cause, and should be read that way rather than
folded.

**What would make this recommendation wrong:** an input, inside what a builder does without restoring times, whose
fingerprint does not change. None was found in the nine probes above; the probes are a sample, not a proof.

## Proposed backlog rows (not written to `docs/backlog.md` by this review)

1. **`agent-watchdog.py`: a directory that becomes a file mid-walk is reported CANNOT RUN for a working builder.**
   `_walk_error` and the walk's `lstat` skip only `FileNotFoundError`; `NotADirectoryError` is the same ordinary
   event. Measured 850 of 9241 observations under a continuous flip. Loud, one false wake and a re-arm. Fix: skip
   both at both sites, with a staged case (substitute the walk, as the vanished-directory case does) and a mutation
   per site. Falsifier: the flip probe reports any CannotRun.
2. **`check-review-decision.py` answers CANNOT RUN for a subject whose round documents use Major/Minor.** Recorded by
   the round 3 coordinator: the thrashing detector decided nothing for this subject and the condition was read by
   hand. Either the severity vocabulary of a round document is refused at writing time, or the detector reads
   both. May belong under backlog #117 rather than as a new row; the coordinator should check before filing.

## What was decided this milestone and is not written down

- An orchestrator's own `git status` in a builder's worktree can restart that builder's window once (round 3, Claude
  half, INFO). It is inside "anything writing counts" and no document says so in those words.
- The witness rule this review applies: every field of an observed record has a case that changes that field alone,
  enumerated from an independent literal. It is an instance of the repository's existing class-fix practice and
  needs no new rule, only this pointer.

## Bound of this review

| Claim | Basis |
|---|---|
| `kind` constant survives 73/73; name constant survives 73/73 | **[M]** mutants on a scratch copy |
| `kind` cannot be witnessed | **[I]** from the three name spaces being disjoint by construction |
| the nine probe rows | **[M]** `probe.py`, APFS only; no Linux filesystem was tried |
| the mid-walk race | **[M]** real threads, 20 s, rate not representative of use |
| the restructure keeps 73/73; the class case and its eight mutants | **[M]** `classcase.py` run from outside the script, not yet a `case()` inside it, and not run through `check-plan-code.py --mutate` |
| a system service writing extended attributes in a worktree | **[I]** not measured |
| the walk's cost and idle stability | **[M]** this worktree, one 20 s interval |

Not examined: the `gitdir` and `report` components beyond what the fold items touch, and the convention that the
orchestrator starts the watchdog at all (the script's NO-CALLER line).
