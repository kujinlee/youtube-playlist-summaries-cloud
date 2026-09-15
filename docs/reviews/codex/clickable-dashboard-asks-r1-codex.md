<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Medium** - `choose` is hidden in local-file mode even though the tray has a Copy path.  
`scripts/gen-dashboard.py:579-580` exits immediately on `file:` and adds `body.nosend`; `scripts/gen-dashboard.py:1309-1312` then hides every `.needs .pick`. But the emitted page itself advertises file mode as usable via copy at `scripts/gen-dashboard.py:1342-1344`, and the composed tray confirms that local mode changes Send to Copy and writes the composed question to the clipboard (`/tmp/review-dashboard.html:6856`, `/tmp/review-dashboard.html:6949-6960`). That means opening the dashboard as a file removes the new answerable control even though the same selection-driven path could still open the tray and let the user copy. I’d keep the chooser visible on `file:` and let the tray’s existing Copy behavior handle delivery.

**Checked Attacks**

No finding on the 40ms timer against the currently emitted tray: `PICK_SCRIPT` dispatches `mouseup` and then schedules its 40ms click (`scripts/gen-dashboard.py:590-606`), while the tray’s `mouseup` handler schedules floater creation after 10ms (`/tmp/review-dashboard.html:6916-6936`). Because the tray timer is registered during the dispatched event before the 40ms timer is registered, this is not a race with today’s lifted tray. It would be more robust as a short poll, but I don’t think that is blocking.

No finding on selecting the wrong `.askbtn`: the query is for `button.askbtn[style*="fixed"]` (`scripts/gen-dashboard.py:600-602`). Heading buttons get inline `right/top/opacity/transition`, not inline `position:fixed` (`/tmp/review-dashboard.html:6900-6904`); the selection floater is the one with `floater.style.position = 'fixed'` (`/tmp/review-dashboard.html:6924-6926`).

No finding on the `h4` section resolution. The new question heading is emitted immediately before the options list (`scripts/gen-dashboard.py:945-949`), and `nearestHeading()` walks DOM previous siblings looking for `H1`-`H4` (`/tmp/review-dashboard.html:6869-6879`). Resetting `.needs h4.q` to `display:inline` is styling only; it does not change sibling traversal (`scripts/gen-dashboard.py:1294-1298`). Also, in the currently composed tray, heading ask buttons are injected only into `h2, h3`, not `h4` (`/tmp/review-dashboard.html:6898-6904`), so the claimed extra h4 ask button does not appear in this emitted page.

Low residual UX concern, not filed as a defect: `PICK_SCRIPT` does clobber the user’s current selection and does not restore it (`scripts/gen-dashboard.py:584-590`). Given the control’s whole job is to drive the tray’s selection entry point, and clicking a button commonly disturbs selection anyway, I would not block on this.

The new self-tests are not vacuous in the obvious deletion cases. `_section()` slices from the requested `h2` to the next `h2` (`scripts/gen-dashboard.py:1745-1750`), and the added assertions bind to actual option buttons, `.otext`, `h4.q`, and PR-row state inside that slice (`scripts/gen-dashboard.py:1767-1793`). Deleting the feature would fail them.

The collapsed-title repair slice is correct for the emitted CSS shape: the source f-string `.entry .title{{` emits `.entry .title{` (`scripts/gen-dashboard.py:1248-1249`), and the test finds that emitted selector then slices to the next `}` (`scripts/gen-dashboard.py:1992-1998`). There are no nested braces in that rule. It is still a tiny hand parser, but it is narrower than the previous page-wide substring assertion.

Mutation metadata: static checks passed. The new anchors are unique in the manifest, the new `expect` names exactly match case names, `scripts/gen-dashboard.py` is 67 in `EXPECTED_MUTATIONS`, and the declared sum is 632 (`scripts/mutations/gen-dashboard.json:762-800`, `scripts/check-plan-code.py:572`, `scripts/check-plan-code.py:3142-3146`). The runner enforces exact equality for `expect`, not substring matching (`scripts/check-plan-code.py:1266-1287`). I started the full `--mutate .` sweep but stopped it at 160/632 because it was still in unrelated manifests; full attribution remains unverified by me.

**Verification**

Ran `python3 scripts/gen-dashboard.py --self-test`: `323/323 passed`.  
Ran `python3 scripts/check-plan-code.py --self-test`: `128/128 passed`.

CONVERGED.
