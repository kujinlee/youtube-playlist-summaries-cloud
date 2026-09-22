<!-- codex-review: model=gpt-5.5 -->

**REVIEW GAP:** claude — not invoked for this round, by design. `docs/review-method.md`'s
Round topology makes rounds 2+ **alternating**: a concurrent pair never reviews the fixes, so
one half reviews what the other's findings produced. The Claude half wrote round 1 and reviews
this round's repair as round 3.

VERDICT: NOT CONVERGED — 1 Blocking, 0 High.

**R1 Findings**

| Finding | Status | Evidence |
|---|---:|---|
| Codex Blocking: `_BLOCK_SCALAR` misses valid dash-opened block scalar spellings | PARTIAL | Anchor, simple quoted key, nested sequence are fixed; class is not closed. See Blocking below. |
| Codex Medium: live-path self-test overclaimed `pin_took_effect` | FIXED | New comment states the case calls `unpinned_jobs`, not `verdict` / `pin_took_effect`. |
| Codex Low: duplicate mutation anchor | NOT FIXED | Duplicate still exists: same `opens_steps` anchor in entries 39 and 42. |
| Codex Low: causal comment inverted `_structural` / `Step.body` ordering | PARTIAL | Top comment fixed, but old wording remains at `scripts/check-python-pin.py:924-926` and `docs/backlog.md:182`. |
| Claude H1: indent invariant unfalsifiable | FIXED | Moving dash out of `group(1)` now reds the new key-column case. |
| Claude M1: causal story inverted | PARTIAL | Same as Codex causal-comment row; roadmap/dashboard are right, backlog and lower test comment are not. |
| Claude M2: bogus “two callers read trailing comment group” claim | FIXED | Removed from the rewritten `_BLOCK_SCALAR` comment. |
| Claude M3: class not swept | PARTIAL | Three named sibling spellings fixed, but valid YAML spellings still false-green. |
| Claude M4: list-`expect` for vacuous repaired case | FIXED | Stripping the `uses:` line makes the harness report unattributed, not pass. |
| Claude L1: escaped unicode churn in manifest | FIXED | `literal unicode escapes False`. |
| Claude L2: mutation arithmetic wording | FIXED for the named arithmetic | The “39 → 40 + deleted” wording is gone; note backlog still has stale final counts. |
| Claude L3: stale `:880-882` locator | FIXED | Backlog says “was at `:880-882`”. |

**New Findings**

Blocking — `_BLOCK_SCALAR` is still not class-closed; valid YAML block scalar openers can still false-green.

The current regex accepts the three repaired instances, but not quoted keys containing a space or colon, and not explicit-key syntax. Libyaml/Psych parses those as scalar-valued step keys, so the nested `uses:` / `python-version:` lines are scalar content. `declared_pins` reads them as real structure and reports a pin.

Command run:

```text
python3 - <<'PY'
# differential: Ruby Psych oracle vs scripts/check-python-pin.py declared_pins
...
PY
```

Real output excerpt:

```text
quoted key with space: oracle=[] declared=['9.9'] DISAGREE FALSE_GREEN
quoted key with colon: oracle=[] declared=['9.9'] DISAGREE FALSE_GREEN
explicit key: oracle=[] declared=['9.9'] DISAGREE FALSE_GREEN
```

I also checked the prompt’s other probes:

```text
tag: oracle=[] declared=[] OK
anchor+tag: oracle=[] declared=[] OK
tag+anchor: oracle=[] declared=[] OK
unicode key: oracle=[] declared=[] OK
flow style: oracle='INVALID Psych::SyntaxError...' declared=['9.9'] DISAGREE
mismatched quote: oracle='INVALID Psych::SyntaxError...' declared=[] DISAGREE
dash dash flag: oracle=[] declared=[] OK
```

`--flag: |` is valid YAML and is correctly masked; I did not find a false mask there. The false-green direction is real for valid quoted-key and explicit-key forms.

**Other Evidence**

H1 repair is real:

```text
[FAIL] a sibling key at the KEY column ends a dash-opened scalar, so the step's real pin survives: got [] want ['3.12']
89/90 passed
```

The three new “nor behind” cases are not ambient:

```text
--- anchor-fragment rc 1
[FAIL] ...nor does one behind a YAML ANCHOR on the value: got ['9.9'] want []
89/90 passed
--- quoted-key-fragment rc 1
[FAIL] ...nor does one behind a QUOTED key: got ['9.9'] want []
89/90 passed
--- nested-dash-fragment rc 1
[FAIL] ...nor does one inside a NESTED sequence, where the dash prefix repeats: got ['9.9'] want []
89/90 passed
```

List-`expect` mechanism works when the repaired fixture is made vacuous:

```text
control rc 0
control tail [..., '90/90 passed']
ok False
'attributed': False
report:
... `expect` '...and a job holding only those still reports as unpinned' matched 0 red case(s) — it was caught by something else ...
```

Counts re-derived:

```text
90/90 passed
manifest 43
expected 43
declared sum 872
128/128 passed
self-test counts: 45 script(s) declare a count, every one verified by running it
```

**Sound**

The repaired anchor / quoted-key / nested-sequence cases are sound for the exact spellings they name. The four relevant mutations compile and attribute; none merely breaks the regex. The standing #155 extraction is not made harder mechanically, but it is less safe to proceed until this remaining `_BLOCK_SCALAR` class is closed or explicitly refused, because the false-green would be promoted into the shared reader. The mutation set is transferable, but incomplete for the newly found valid spellings.
