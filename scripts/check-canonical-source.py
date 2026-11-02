#!/usr/bin/env python3
"""A mechanism described in more than one place drifts. This refuses the second copy.

WHY THIS EXISTS
---------------
The handoff-path hint mechanism and the corpus cross-check instruction were each written out at
SIX sites — the vendored skill, the enforcing hook's refusal, this directory's guard comment,
`docs/plugins.md`, `docs/process-rationale.md` and a memory note. Nothing compared them. Across
five consecutive review rounds a reviewer found, every single round, at least one copy that had
drifted: a withdrawn claim left standing as a paragraph's bolded headline, a count with no unit,
a provenance qualification applied at one site and not its neighbour, and — the one that settled
it — a round-5 correction that reached the skill and never reached the hook, so the hook's refusal
printed a claim AND its own withdrawal in the same message.

That is this repository's most-measured defect, `a second implementation of one rule drifts`
(17 recorded instances), applied to prose instead of code.

⛔ IT DOES NOT GENERALISE `check-explainer-delivery.py`, AND SAYING SO WAS AN INSTANCE OF THIS
FILE'S OWN SUBJECT (r6 CLAUDE H5). The claim stood at three sites. The two guards share a PATTERN
— a canonical file, a marker, declared citing sites, a guard — and they are not one rule, because
the thing each forbids is different in KIND:

  * that one forbids a RUNNABLE PROCEDURE, so its oracle is a FENCED CODE BLOCK containing a
    delivery command (or a `Monitor({` arming block), scoped to `.agents/skills/*/SKILL.md`;
  * this one forbids a SYMBOL, so its oracle is a token substring over four directories and three
    extensions.
  * and only that one asserts ENUMERATION COMPLETENESS: a skill that produces a page but is absent
    from its `PAGE_SKILLS` escapes the check. Nothing here replaces that, so folding it into this
    file would DELETE a falsifier.

⭐ MEASURED, which is what settles it rather than taste: in THIS guard's population
`explainer-serve.py` carries 34 non-exempt sites and `brief-compose.py` 26 — fourteen of them the
scripts that call or test the tool. A token oracle for the delivery procedure would fire on its own
implementation. The fence oracle is not a weaker version of this one; it is the correct one there.

⚠ WHAT IS STILL NOT GUARDED, because a stated bound beats a discovered one: the delivery procedure
restated in a file that is NOT a `SKILL.md` is invisible to both guards — that one does not look
outside skills, and this one has no `CANONS` entry for it (`shared/explainer-delivery.md` carries no
`<!-- canon: -->` marker at all).

WHAT IT ACTUALLY ASSERTS (and what it deliberately does not)
------------------------------------------------------------
It flags a RESTATED MECHANISM, not a mention. A retrospective is free to *discuss* the history —
`docs/process-rationale.md` exists to explain why five versions of a sentence were each refuted,
and that history is the most valuable thing on the branch. What a site may not do is hand the
reader the mechanism again: the SYMBOLS for `handoff-path`, the COMMAND FORMS for `corpus-search`.
Counting bare mentions would have forced deleting measured history to satisfy a checker, which is
the check driving the docs rather than the other way round.

⛔⛔ THE BOUND THAT MATTERS MOST, AND IT IS NOT AN EXEMPTION (r7 CODEX M1). A citing site may
RESTATE a mechanism as long as it CITES the canon — `hit and not _cites(...)` — so this guard
cannot detect a restatement that cites the canon and CONTRADICTS it. Measured: round 6's L9
corrected the delivery fingerprint in the canon to *where `cksum` exists* (the vendor falls back to
`wc -c`, a byte count), and THREE reader-facing sites kept the unconditional "fingerprinted on
CONTENT" for a full round while `audit()` returned `[]`. The permissiveness is deliberate — a
retrospective must be able to DISCUSS history — and this is its price: the guard enforces *one
place*, never *one claim*. ⭐ The only remedy that works is the one the three sites took: DELETE the
recital and keep the citation. A citation cannot drift; a recital can. Filed as backlog #289.

⚠ TWO STRUCTURAL CONSEQUENCES OF THE TOKEN DESIGN, stated because both are invisible until they
fire:
  1. TOKENS MATCH AS SUBSTRINGS, so `REMEMBER_HANDOFF` also matches `REMEMBER_HANDOFF_STATE`. A file
     discussing only the DELIVERY RECORD would be required to cite a canon about the PATH.
     Measured at THIS commit by importing `_walked_textfiles` and `EXEMPT`: LATENT, not live —
     **5 live non-exempt sites, bare counts 1-4**, every one with at least one bare occurrence, so
     none is required to cite solely because of a `_STATE` match; and a constructed state-only
     mention does get flagged.
     ⟳ r7 CLAUDE M2: this read "7 sites, bare counts 1-3", which were the PARENT tree's figures —
     measured before the edit and written after it, in a file inside the population it measures.
     The commit stating them deleted two recitals (the hook and `docs/plugins.md`) and added the
     sentence that took this file's own bare count to 4. The LATENT verdict was right; the numbers
     were stale at commit time by the commit's own diff.
  2. A CANON'S SELF-CITATION IS STRUCTURAL, NOT PROSE — and the sentence that stood here claimed the
     opposite and offered a falsifier that PASSES.
     ⛔⛔ r7 CLAUDE M1, and this is the correction that matters most of the three. It said
     `shared/corpus-search.md` "is cited exactly ONCE here" and that "deleting that one citation
     reddens the guard against ITSELF". All of it is wrong: the path occurs TWICE (this docstring
     and `CANONS[1]["file"]`); deleting the prose mention leaves the guard GREEN (verified on a copy,
     green control -> sever -> green); and adding a third `CANONS` entry with NO prose citation
     anywhere is also green, because `_cites()` expands leftwards over path characters and resolves
     the candidate, so the entry's own `"file"` VALUE satisfies the citation requirement.
     ⭐ The real behaviour is BETTER than the claim: self-citation cannot be lost by editing prose.
     ⚠ The lesson is not the wrong sentence, it is that I WROTE A FALSIFIER AND DID NOT RUN IT. A
     bound whose falsifier passes is worse than no bound: it tells the next editor that an inert
     line is load-bearing. Stating the observation that would make a claim fail is not making it.

⚠ EXEMPTIONS, STATED RATHER THAN HIDDEN. `docs/reviews/**` is frozen testimony and is never
edited. `docs/dashboard-entries.md` holds DATED entries: a record of what was true on a day, not
a rule a reader follows at the moment of need — which is exactly the distinction this branch's own
narrowing turned on. Both are exempt, and that means drift inside them is NOT caught here.

FAILS IF
--------
  * a canonical file is missing, or its `<!-- canon: NAME -->` marker is absent;
  * that marker appears in more than one file (two canons for one mechanism);
  * a declared citing site does not cite the canonical path;
  * any non-exempt file RESTATES a mechanism (carries its tokens) without citing its canon.

  --self-test  runs 28 cases over synthetic trees, including that each failure mode is DETECTED.
"""
from __future__ import annotations
import contextlib
import io
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Hardcoded on purpose, per `hardcode-only-what-fails-loudly`: a missing canonical file is an
# error below, so this list going stale announces itself. A derived list would silently shrink.
CANONS: list[dict] = [
    {
        "name": "handoff-path",
        "file": ".agents/skills/shared/handoff-path.md",
        # Mechanism SYMBOLS. A site carrying these is handing the reader the mechanism again.
        #
        # ⛔⛔ THE FIRST THREE WERE THE PATH-RESOLUTION HALF ONLY, AND THE HALF THE BRANCH EXISTS
        # FOR WAS NOT IN THE LIST (r6 CLAUDE H3). The ⛔ RULE — *where a handoff goes and why that
        # path is the one that gets read* — rests on two more symbols, and measured at the round-6
        # tip they stood at SIX and FIVE non-exempt live sites with this guard exiting 0 over all
        # of them: `REMEMBER_HANDOFF` in `.agents/skills/handoff/SKILL.md`,
        # `.claude/hooks/enforce-handoff-path.sh`, `scripts/check-handoff-path.py`,
        # `docs/plugins.md`, `docs/process-rationale.md` and
        # `docs/memory/a-vendored-line-number-has-no-owner.md`; `=== LAST HANDOFF ===` at the
        # first five of those and — the tell — ZERO times in the canon, so the one file that was
        # supposed to be the superset was not even a superset.
        #
        # ⚠ They had not drifted yet: all four sub-claims checked out against the installed 0.33.0
        # hook. That is the point, not a mitigation — this branch's thesis is that six uncompared
        # copies drift WITHIN one review round, and a guard that waits for the drift is a guard
        # that reports the damage.
        #
        # ⭐ WHY THESE TWO AND NOT THE PROSE. The sub-claims are PARAPHRASED at every site
        # (`injected **before**` / `ahead of` / `injected BEFORE`), so no claim search polices
        # them — a case-sensitive, markup-literal matcher returns 0 for a claim written at five
        # sites. The SYMBOL and the BANNER are stable strings, so they are what a token oracle can
        # actually hold, and holding them forces the paraphrases to one file.
        "tokens": [
            "REMEMBER_ROOT",
            "PER_SESSION_HANDOFF",
            "_resolve_memory_project_dir",
            "REMEMBER_HANDOFF",
            "=== LAST HANDOFF ===",
        ],
        "cites": [
            ".agents/skills/handoff/SKILL.md",
            ".claude/hooks/enforce-handoff-path.sh",
            "scripts/check-handoff-path.py",
            "docs/plugins.md",
            # ⟳ r6 CLAUDE H3: these two carry the delivery symbols and cited the canon ZERO times.
            # Both are retrospectives, which this guard deliberately allows to DISCUSS the history
            # — what they may not do is hand the reader the mechanism again with no link to the
            # one file that owns it.
            "docs/process-rationale.md",
            "docs/memory/a-vendored-line-number-has-no-owner.md",
        ],
    },
    {
        "name": "corpus-search",
        "file": ".agents/skills/shared/corpus-search.md",
        # COMMAND FORMS. Prose may name the cross-check; it may not reprint the commands.
        "tokens": ["git grep --cached", "rg --hidden", "-RSl"],
        "cites": [
            ".agents/skills/handoff/SKILL.md",
            ".claude/hooks/enforce-handoff-path.sh",
            "scripts/check-handoff-path.py",
            "docs/process-rationale.md",
            "docs/memory/a-vendored-line-number-has-no-owner.md",
        ],
    },
]

# ⚠ `\.remember/` WAS AN UNREACHABLE ALTERNATIVE and is gone (r6 CLAUDE H4). The walk can
# only ever yield the repo root plus `.agents/`, `.claude/`, `docs/` and `scripts/`, so that
# branch matched nothing and no case covered it — an exemption written against an imagined
# population, which is the same defect as measuring one.
EXEMPT = re.compile(r"^(docs/reviews/|docs/dashboard-entries\.md$)")
SEARCHED = ("*.md", "*.py", "*.sh")
MARKER = "<!-- canon: {} -->"


# ⛔⛔ THE REPO ROOT IS IN THE WALK, AND LEAVING IT OUT WAS THE WORST MISS (r6 CLAUDE H4).
# Measured on a copy, green control before and after: a root `CLAUDE.md` carrying a mechanism's
# token with NO citation gave rc=0 while the same text under `.agents/` gave rc=1. `CLAUDE.md`
# `@`-imports `AGENTS.md`, `docs/dev-process.md` and `docs/plugins.md`, so those two files are the
# surfaces a session reads FIRST and ALWAYS — and `docs/plugins.md`, a DECLARED citing site, is
# reachable only through them. A guard that cannot see the entry point to its own citing sites is
# measuring the wrong population.
#
# ⚠ AND THE BOUND IS NOW STATED WHERE IT IS TRUE. The docstring used to name two EXEMPTIONS and
# imply everything else was covered; the real population was `{.agents,.claude,docs,scripts}` x
# `{md,py,sh}`, which is a far larger exclusion than the exemptions and was written nowhere. What
# is STILL not covered, said plainly rather than discovered later: `*.html` (so a generated
# explainer page can carry a seventh copy), `*.txt`, `*.json`, `*.yml`, and any directory outside
# the five below — `tests/`, `lib/`, `.github/`. Widening to those is backlog #282's subject; what
# this fixes is the entry point, which is the one no reader can avoid.
ROOT_GLOBS = ("*.md",)


def _cites(body: str, cite_token: str, canon_abs: Path, citing_abs: Path,
           repo_root: Path) -> bool:
    """True if `body` carries a path ending in `cite_token` that RESOLVES to the canon.

    ⛔ WHY A PLAIN `in` IS NOT ENOUGH (r6 CLAUDE H4). `cite_token` is a relative reference such as
    `shared/handoff-path.md`, so `cite_token in body` is satisfied by
    `See docs/nowhere/shared/handoff-path.md.` — a citation that reads as compliance and sends the
    reader nowhere.

    ⚠ THREE WRONG REPAIRS BEFORE THIS ONE, each recorded because each looked right and the next
    measurement refuted it:
      1. resolve the token from the REPO ROOT — a relative reference does not point there; the real
         repository went red, 9/15, including "the REAL repository is clean";
      2. require the token NOT be preceded by a path character — the real citations are full paths
         ending in the token, so `/` precedes them too; that rejected all nine citing sites, 10/15;
      3. accept the canon's own repo-relative path OR a bare token — still rejected
         `.agents/skills/handoff/SKILL.md`, which cites `../shared/handoff-path.md`, a path relative
         to the CITING FILE. 10/15 again, one site.
    ⭐ Each repair was written from the illegitimate example and never checked against the
    legitimate ones. The property is not a spelling: **a citation is a path, and the question is
    where it resolves.** So expand each occurrence leftwards over path characters and resolve the
    candidate against the citing file's own directory AND the repo root; a different path ending in
    the same token resolves to neither.
    """
    pathish = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_./-")
    canon = canon_abs.resolve()
    start = 0
    while True:
        i = body.find(cite_token, start)
        if i < 0:
            return False
        a = i
        while a > 0 and body[a - 1] in pathish:
            a -= 1
        cand = body[a:i + len(cite_token)]
        # ⚠ BOTH BASES ARE PASSED IN, NOT DERIVED. A fourth wrong attempt derived the repo root as
        # `canon_abs.parents[-1]`, which is the FILESYSTEM root — every candidate then resolved
        # somewhere outside the tree and the BUILT-world case went red. Deriving a root from a file
        # path is exactly the "defined, not derived" trap this repo keeps paying for.
        for base in (citing_abs.parent, repo_root):
            try:
                if (base / cand).resolve() == canon:
                    return True
            except (OSError, ValueError):
                pass
        start = i + 1


def _walked_textfiles(root: Path) -> list[Path]:
    """Text files found by WALKING the tree. ⛔ It never consults git, and the old name said it did.

    r6 CLAUDE L4: the old name was `_tracked_text` + `files`, and it was the only thing claiming a
    tracked corpus. Demonstrated: an untracked `docs/sneak-*.md` carrying a mechanism token with no
    citation IS flagged. Two consequences a reader needs, neither of which the old name admitted:

      * a LOCAL red can come from a scratch file that will never be committed; and
      * a CI green says nothing about untracked content, because CI has none.

    ⚠ Renaming was the honest fix rather than a docstring alone, and it is safe here only because
    it was CHECKED first: the symbol appeared in TWO places in this file and in ZERO mutation anchors
    across all 60 manifests. A rename that orphans an anchor voids a ratchet silently — a sibling
    branch paid for exactly that this week.
    """
    out: list[Path] = []
    for pat in ROOT_GLOBS:
        out += sorted(root.glob(pat))          # top level only: CLAUDE.md, AGENTS.md, README.md
    for sub in (".agents", ".claude", "docs", "scripts"):
        d = root / sub
        if not d.is_dir():
            continue
        for pat in SEARCHED:
            out += sorted(d.rglob(pat))
    return out


def audit(root: Path, canons: list[dict] | None = None) -> list[str]:
    """Findings; empty means every mechanism is described exactly once and cited elsewhere."""
    canons = CANONS if canons is None else canons
    problems: list[str] = []
    files = _walked_textfiles(root)

    for canon in canons:
        name, rel = canon["name"], canon["file"]
        path = root / rel
        if not path.is_file():
            problems.append(f"{rel} is MISSING — {name} has no canonical source")
            continue
        # A citation is matched on the `shared/<name>.md` SUFFIX, not the repo-relative path:
        # a markdown link from inside `.agents/skills/handoff/` correctly writes
        # `../shared/handoff-path.md`, and demanding the long form would reject a correct link.
        # Same shape as `check-explainer-delivery.py`, which matches `shared/explainer-delivery.md`.
        cite_token = "/".join(Path(rel).parts[-2:])
        marker = MARKER.format(name)
        if marker not in path.read_text(encoding="utf-8", errors="replace"):
            problems.append(f"{rel} does not carry its marker {marker!r}")

        # ⛔⛔ `EXEMPT` APPLIES HERE TOO, AND IT DID NOT — found 2026-10-21 by running the FULL
        # `ci.yml` guard list instead of a subset. This module's docstring states that
        # `docs/reviews/**` is *"frozen testimony … never edited"* and is exempt, and the CITING
        # check at the loop below honours that. **This rule did not**, so a review document that
        # QUOTED a marker inside its own test output became a second canon site:
        #
        #   marker <the handoff-path canon marker> appears in 2 files —
        #     .agents/skills/shared/handoff-path.md,
        #     docs/reviews/codew/decision-route-escalation-r4-codex.md
        #
        # ⚠ THE MARKER IS DESCRIBED AND NOT WRITTEN OUT ABOVE, ON PURPOSE. The first version of
        # this comment pasted it literally and INSTANTLY recreated the defect one directory over —
        # `appears in 2 files — .agents/skills/shared/handoff-path.md, scripts/check-canonical-
        # source.py`. A guard that cannot quote its own subject is the sharpest possible proof that
        # the subject is a live token rather than a string, and the `codew` typo above is also
        # deliberate so this block cannot be grepped into a third one.
        #
        # ⭐ AND THE QUOTE WAS THE REVIEWER'S EVIDENCE: Codex pasted the `[FAIL]` line proving a
        # mutation worked, and that line necessarily contains the marker. So the guard punished a
        # review for showing its working — and it went red on a branch where NO CI RUN EXISTS
        # (CI triggers on pull requests to master; this branch has no pull request), which is why
        # six guard failures sat undiscovered behind a subset that reported green.
        #
        # ⚠ THIS IS NOT A LOOSENING. The exemption was already DECIDED and DOCUMENTED; one of the
        # module's two rules simply never read it. The rationale is unchanged and is the same one
        # the citing check already accepts: nobody follows a frozen review document as a rule, so
        # a marker quoted there is not a second place the mechanism LIVES. Drift inside
        # `docs/reviews/**` is still NOT caught here, exactly as the docstring says.
        holders = [
            f for f in files
            if marker in f.read_text(encoding="utf-8", errors="replace")
            and not EXEMPT.match(str(f.relative_to(root)))
        ]
        if len(holders) > 1:
            where = ", ".join(sorted(str(f.relative_to(root)) for f in holders))
            problems.append(f"marker {marker!r} appears in {len(holders)} files — {where}")

        for cite_rel in canon["cites"]:
            cp = root / cite_rel
            if not cp.is_file():
                problems.append(f"{cite_rel} is declared a citing site but does not exist")
                continue
            if not _cites(cp.read_text(encoding="utf-8", errors="replace"), cite_token,
                          root / rel, cp, root):
                problems.append(f"{cite_rel} does not cite {rel}")


        for f in files:
            frel = str(f.relative_to(root))
            if frel == rel or EXEMPT.match(frel):
                continue
            body = f.read_text(encoding="utf-8", errors="replace")
            hit = next((t for t in canon["tokens"] if t in body), None)
            if hit and not _cites(body, cite_token, root / rel, f, root):
                problems.append(
                    f"{frel} restates {name} (carries {hit!r}) without citing {rel}"
                )
    return problems


def _built_world(base: Path, complete: bool = True) -> Path:
    """Construct a tree satisfying the LIVE `CANONS`, so a case can drive `main()` over a world it
    built rather than over the real repository. `complete=False` drops one citation, which is the
    failure shape that actually recurred: a fix that reached one site and not its neighbour."""
    for canon in CANONS:
        f = base / canon["file"]
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(MARKER.format(canon["name"]) + "\n" + "\n".join(canon["tokens"]) + "\n")
        # ⚠ THE FIXTURE CITES THE CANON'S FULL REPO-RELATIVE PATH, as real citing sites do. It used
        # to write the bare two-segment token, which satisfied the old substring test and resolves
        # from NEITHER base under the new one — so the stricter rule turned this constructed world
        # red, correctly. A fixture that cites in a way no real site does is a fixture that tests a
        # rule nobody is subject to.
        for i, rel in enumerate(canon["cites"]):
            c = base / rel
            c.parent.mkdir(parents=True, exist_ok=True)
            body = "" if (not complete and i == 0) else f"see {canon['file']}\n"
            c.write_text(c.read_text() + body if c.exists() else body)
    return base

# ── self-test ────────────────────────────────────────────────────────────────────────────────
def _tree(base: Path, canon_body: str, sites: dict[str, str]) -> list[str]:
    (base / ".agents/skills/shared").mkdir(parents=True, exist_ok=True)
    (base / "docs").mkdir(parents=True, exist_ok=True)
    if canon_body is not None:
        (base / ".agents/skills/shared/c.md").write_text(canon_body)
    for rel, body in sites.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    spec = [{
        "name": "c", "file": ".agents/skills/shared/c.md",
        "tokens": ["MECHTOKEN"], "cites": ["docs/site.md"],
    }]
    return audit(base, spec)


def self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    passed = failed = 0

    def case(label: str, got, want) -> None:
        nonlocal passed, failed
        if got == want:
            passed += 1
        else:
            failed += 1
            print(f"  [FAIL] {label}: got {got!r} want {want!r}")

    CANON = "<!-- canon: c -->\nMECHTOKEN lives here.\n"
    # ⛔ THE ROOT-RELATIVE FORM, AND THE OLD FIXTURE'S RELATIVE ONE NEVER RESOLVED (r6 CLAUDE H4).
    # It read `See ../shared/c.md …` and was commented "the RELATIVE form a real link uses" — but
    # the citing site is `docs/site.md`, so `../shared/c.md` points at `<root>/shared/c.md`, which
    # the fixture never creates. It passed only because the old rule was a substring test. This is
    # the form `docs/plugins.md` actually uses; the `../` form is covered separately below, in a
    # layout where it genuinely resolves, because that is what `.agents/skills/handoff/SKILL.md`
    # writes and a rule that rejected it would have broken a real site.
    CITE = "See .agents/skills/shared/c.md for the mechanism.\n"

    with tempfile.TemporaryDirectory() as td:
        t = Path(td)

        r = _tree(t / "ok", CANON, {"docs/site.md": CITE})
        case("a canon plus a citing site is clean", r, [])

        # ⭐ THE `../` FORM, TESTED DIRECTLY ON `_cites` OVER THE REAL LAYOUT. `_tree` hardcodes
        # its citing site at `docs/site.md`, from which no `../`-relative path reaches
        # `.agents/skills/shared/`, so routing this through `_tree` tested the wrong geometry — my
        # first version of this case failed for that reason, not because the rule was wrong.
        # ⛔ This is the exact pair that exists in the repository: `.agents/skills/handoff/SKILL.md`
        # citing `../shared/handoff-path.md`. My third attempt at the rule rejected it, so the case
        # is a regression guard for a real site a stricter rule would have broken.
        _rel = t / "relgeom"
        (_rel / ".agents/skills/shared").mkdir(parents=True, exist_ok=True)
        (_rel / ".agents/skills/handoff").mkdir(parents=True, exist_ok=True)
        _canon_f = _rel / ".agents/skills/shared/handoff-path.md"
        _canon_f.write_text("canon\n")
        _site_f = _rel / ".agents/skills/handoff/SKILL.md"
        _site_f.write_text("described ONCE, in [`../shared/handoff-path.md`](../shared/x)\n")
        case("a `../` citation relative to the CITING FILE is accepted",
             _cites(_site_f.read_text(), "shared/handoff-path.md", _canon_f, _site_f, _rel), True)
        _bad_f = _rel / ".agents/skills/handoff/BAD.md"
        _bad_f.write_text("see docs/nowhere/shared/handoff-path.md\n")
        case("…and the same token as the tail of ANOTHER path is not",
             _cites(_bad_f.read_text(), "shared/handoff-path.md", _canon_f, _bad_f, _rel), False)
        _root_f = _rel / "CLAUDE.md"
        _root_f.write_text("see .agents/skills/shared/handoff-path.md\n")
        case("…and the repo-root-relative form is accepted too",
             _cites(_root_f.read_text(), "shared/handoff-path.md", _canon_f, _root_f, _rel), True)

        # ⛔ AND THE NEGATIVE THE WHOLE REPAIR EXISTS FOR: a path ending in the same token that
        # resolves somewhere else entirely. Adjacent to the accepted forms, not absurd.
        r = _tree(t / "dangle", CANON,
                  {"docs/site.md": "See docs/nowhere/shared/c.md for the mechanism.\n"})
        case("a citation that resolves NOWHERE is NOT accepted",
             any("does not cite" in x for x in r), True)

        # ⛔ THE REPO ROOT, WHICH THE WALK DID NOT REACH (r6 CLAUDE H4). Measured before the fix,
        # on a copy with green controls: a root `CLAUDE.md` carrying a token with no citation gave
        # rc=0 while the identical text under `.agents/` gave rc=1. These two files are the surfaces
        # a session reads FIRST — `CLAUDE.md` `@`-imports `docs/plugins.md`, a declared citing site.
        r = _tree(t / "rootmiss", CANON, {"docs/site.md": CITE, "CLAUDE.md": "MECHTOKEN again\n"})
        case("a restatement in the repo-root CLAUDE.md is detected",
             any("restates c" in x and "CLAUDE.md" in x for x in r), True)
        r = _tree(t / "rootmiss2", CANON, {"docs/site.md": CITE, "AGENTS.md": "MECHTOKEN again\n"})
        case("…and in AGENTS.md", any("restates c" in x and "AGENTS.md" in x for x in r), True)
        # CONTROL — a root file that DOES cite must stay clean, or the rule above could be a blanket
        # refusal of any root file carrying the token.
        r = _tree(t / "rootok", CANON, {"docs/site.md": CITE, "CLAUDE.md": "MECHTOKEN " + CITE})
        case("CONTROL — a root file that cites the canon is clean",
             [x for x in r if "CLAUDE.md" in x], [])
        # CONTROL — the walk must not reach deeper than the root's own files, or it would start
        # auditing node_modules and every untracked tree.
        r = _tree(t / "deep", CANON, {"docs/site.md": CITE, "tests/deep.md": "MECHTOKEN again\n"})
        case("CONTROL — `tests/` is still outside the walk (a STATED bound, not a silent one)",
             [x for x in r if "tests/deep.md" in x], [])

        r = _tree(t / "nocanon", None, {"docs/site.md": CITE})
        case("a MISSING canonical file is detected", any("is MISSING" in x for x in r), True)

        r = _tree(t / "nomark", "no marker here\nMECHTOKEN\n", {"docs/site.md": CITE})
        case("an absent marker is detected", any("does not carry its marker" in x for x in r), True)

        r = _tree(t / "twomark", CANON, {"docs/other.md": CANON, "docs/site.md": CITE})
        case("a SECOND file holding the marker is detected",
             any("appears in 2 files" in x for x in r), True)

        # ⛔ THE EXEMPTION MUST REACH *BOTH* RULES, and until 2026-10-21 it reached only the citing
        # one — so a review that QUOTED a marker in its own test output became a second canon site.
        # The pre-existing exemption case covers the CITING check; this covers the DUPLICATION
        # check, and without it the fix for that defect would be unguarded. The negative case
        # below is the discriminator: an un-exempt second holder must STILL be caught, or this
        # would have disabled the rule rather than scoping it.
        r = _tree(t / "dupreview", CANON,
                  {"docs/reviews/r9.md": CANON, "docs/site.md": CITE})
        case("⭐ a marker QUOTED in frozen testimony is NOT a second canon site",
             [x for x in r if "appears in" in x], [])
        r = _tree(t / "dupdash", CANON,
                  {"docs/dashboard-entries.md": CANON, "docs/site.md": CITE})
        case("...and the dated dashboard record is exempt from it too",
             [x for x in r if "appears in" in x], [])
        r = _tree(t / "dupreal", CANON,
                  {"docs/notreviews/r9.md": CANON, "docs/site.md": CITE})
        case("...but a second holder OUTSIDE the exempt paths is still caught",
             any("appears in 2 files" in x for x in r), True)

        r = _tree(t / "nocite", CANON, {"docs/site.md": "nothing here\n"})
        case("a citing site that does not cite is detected",
             any("does not cite" in x for x in r), True)

        r = _tree(t / "missingsite", CANON, {})
        case("a declared citing site that does not exist is detected",
             any("does not exist" in x for x in r), True)

        r = _tree(t / "restate", CANON, {"docs/site.md": CITE, "docs/sneak.md": "MECHTOKEN again\n"})
        case("a RESTATEMENT without a citation is detected",
             any("restates c" in x for x in r), True)

        r = _tree(t / "quote", CANON,
                  {"docs/site.md": CITE, "docs/sneak.md": "MECHTOKEN " + CITE})
        case("a restatement that DOES cite is allowed", r, [])

        r = _tree(t / "exempt", CANON,
                  {"docs/site.md": CITE, "docs/reviews/r1.md": "MECHTOKEN\n"})
        case("frozen testimony under docs/reviews/ is exempt", r, [])

        r = _tree(t / "dash", CANON,
                  {"docs/site.md": CITE, "docs/dashboard-entries.md": "MECHTOKEN\n"})
        case("the dated dashboard is exempt", r, [])

        r = _tree(t / "self", CANON, {"docs/site.md": CITE})
        case("the canon itself is never flagged for holding its own tokens",
             any("restates" in x for x in r), False)

        # The real tree must pass — the check is pointless if it cannot measure its own subject.
        case("the REAL repository is clean", audit(ROOT), [])

        # ⛔⛔ THE TWO DELIVERY SYMBOLS ARE BOUND ONE AT A TIME, AND THAT IS NOT PEDANTRY (r6 H3).
        # Neither case above binds the CANONS LITERAL: `_built_world` constructs its tree FROM the
        # live table, and `audit(ROOT)` asserts cleanliness — both are satisfied by a SMALLER token
        # list, so deleting a token leaves the suite 23/23 green and the guard blind again, which is
        # the state round 6 found. A falsifier for a token has to be a COUNTER-EXAMPLE: a site that
        # carries it, cites nothing, and must be DETECTED.
        # ⚠ AND ONE LEAK FILE PER TOKEN, EACH CARRYING ONLY ITS OWN. A single fixture carrying both
        # is still flagged after one token is deleted — the case would be satisfied by the surviving
        # token, this repo's `exercise-the-producer-at-two-distinct-inputs` defect. The assertion
        # NAMES the token for the same reason: a finding raised by a different one must not satisfy
        # it.
        for tok, slug in (("REMEMBER_HANDOFF", "symbol"), ("=== LAST HANDOFF ===", "banner")):
            w = _built_world(t / f"delivery-{slug}", complete=True)
            leak = w / "docs" / "leak.md"
            leak.parent.mkdir(parents=True, exist_ok=True)
            leak.write_text(f"The handoff is {tok} and this file cites nothing at all.\n")
            found = audit(w)
            case(f"a site restating the handoff {slug} with no citation is detected",
                 any("docs/leak.md restates handoff-path" in x and repr(tok) in x
                     for x in found),
                 True)

        # ADR-0014: drive `main()` over a world THIS CASE BUILT, in both directions, so no line of
        # it ships unmeasured. ⚠ Driving it over the real repo only is what `check-main-drivable.py`
        # refuses — "2 suite calls to main(), none over a world the case built" — and it said so
        # here before these two worlds existed.
        # ⚠ The world is built by the statement BEFORE the call, and what `main()` receives is
        # `t / "<name>"` — an expression whose LEAF is the temp dir this case bound. Passing
        # `_built_world(...)` directly reads as INERT to `world_class` (a module-level name it
        # cannot resolve), and INERT alone is not evidence that the case built anything.
        _built_world(t / "world-ok", complete=True)
        with contextlib.redirect_stdout(io.StringIO()):
            rc_ok = main([], root=t / "world-ok")
        case("main() returns 0 over a BUILT world that satisfies every canon", rc_ok, 0)
        _built_world(t / "world-nocite", complete=False)
        with contextlib.redirect_stdout(io.StringIO()):
            rc_bad = main([], root=t / "world-nocite")
        case("...and 1 over a BUILT world where one citation is missing", rc_bad, 1)
        # ⚠ argv VARIED, not decorative: an unknown flag is misuse and says so with rc=2, which is
        # what makes this parameter distinguishable from a constant.
        with contextlib.redirect_stdout(io.StringIO()):
            rc_misuse = main(["--bogus"], root=t / "world-ok")
        case("...and 2 when given an argument it does not take", rc_misuse, 2)

    print(f"{passed}/{passed + failed} passed")
    return 0 if failed == 0 else 1


def main(argv: list[str], root: Path = ROOT) -> int:
    # ADR-0014's D1 shape, `def main(argv, root=ROOT)`, and BOTH parameters are load-bearing —
    # three guards each refused a different shortening of this signature, which is why it looks
    # the way it does:
    #   * `check-main-drivable.py` requires the world to be a parameter main DECLARES, and
    #     `_passes_extra_world` reads `positional[1:] | kwonly` — so dropping `argv` and leaving
    #     `main(root=…)` destroyed the PARAM route and sent this guard to identity DEBT;
    #   * `check-fixture-variation.py` requires every parameter to be VARIED by some case, and an
    #     `argv` that only ever receives `[]` is indistinguishable from a constant;
    #   * so `argv` carries real behaviour — this check takes no arguments, and saying so is worth
    #     an exit code rather than silently ignoring a typo'd flag.
    # ⚠ The `--self-test` dispatch lives in `__main__`, not here, so no case re-enters this suite.
    if argv:
        print(f"unexpected argument(s): {' '.join(argv)} — this check takes none, or --self-test")
        return 2
    problems = audit(root)
    if problems:
        print("⛔ a mechanism is described in more than one place, or a citation is missing:")
        for p in problems:
            print(f"  ✗ {p}")
        print("\nEach mechanism lives in ONE file and every other site cites it. See the module")
        print("docstring for why, and `.agents/skills/shared/` for the canonical sources.")
        return 1
    names = ", ".join(c["name"] for c in CANONS)
    print(f"canonical sources OK — {len(CANONS)} mechanism(s) described once each ({names})")
    return 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv[1:] else main(sys.argv[1:]))
