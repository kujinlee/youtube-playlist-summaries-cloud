<!-- codex-review: model=gpt-6.1-sol -->

1. **High — pinned resize can leave the threshold stale even AFTER returning to flow.** `scripts/page_chrome.py:1028`, `:1035`.

   Concrete input: compose the unchanged `2026-10-06-brief-dev-process-speed.fragment.html`. In Chromium:

   - Load at 1280×900; scroll to 1800.
   - Resize to 320×568 while pinned.
   - Scroll to 0, wait, then scroll to 231.

   After 1200ms, the bar remains **unpinned**, and the theme button occupies **−31.02 to −1.39px**, entirely offscreen. `--chrome-h` remains **62.125px**, although the in-flow bar is **132.1875px** tall.

   The resize’s `sync` returns while pinned. Returning to flow does not necessarily change the bar’s content-box dimensions, so `ResizeObserver` never invokes another measurement. The old **16.25px** margin survives indefinitely.

   **Inside the declared subject:** an unchanged repository fragment and ordinary viewport resizing. The accepted caveat is insufficient: it promises recovery upon returning to flow, which does not happen. Even before returning, the stale anchor clearance places a section at y≈62 beneath a bar ending at y≈133.

2. **High — collecting stylesheet bodies re-created the “element’s OWN ID is invisible” defect.** `scripts/page_chrome.py:434`.

   Concrete input:

   ```python
   page = (
       '<html><body><style id="chrome-theme">'
       ':root[data-theme="light"]{--bg:white}'
       ':root[data-theme="dark"]{--bg:black}'
       + chrome_css() + '</style>'
       + chrome_bar('', 'now', refresh=False)
       + '<script>' + chrome_script() + '</script></body></html>'
   )
   ```

   `assert_wired(page, "test")` accepts this. `_Scan.ids` contains only the button’s ID because the new `style` branch returns before recording attributes.

   Chromium’s `getElementById('chrome-theme')` returns **STYLE**. Clicking the visible button leaves `data-theme` unchanged and `aria-pressed="false"`.

   Running the same input against `cbf0e294^` records **two** IDs and correctly refuses it.

   **Inside the declared subject:** an accidental duplicate ID in authored markup—the exact mistake the duplicate-ID guard claims to catch. This is the CSS fold recreating the class already fixed for `<template>` and `<noscript>`.

3. **Medium — the composer can generate two slots, and the pin script silently chooses the stamp-only one.** `scripts/page_chrome.py:959`; `scripts/brief-compose.py:764`.

   Concrete fragment: valid palettes and chrome CSS, `<h1>Owned chrome</h1>`, followed by:

   ```html
   <div class="chrome-slot"><div class="chrome">
     <!-- theme_control() -->
   </div></div>
   <p style="height:3000px">prose</p>
   <!-- chrome_script() -->
   ```

   Supply complete light values for `brief-compose.shim_dark_tokens()` so palette completeness is independently satisfied. There is deliberately no `.chrome-when`.

   `compose()` accepts this and inserts a separate `stamp_bar()` under the title. The script selects that first slot, finds no control, and never establishes pinning for the second slot. Chromium at scrollY=1800: both bars remain `.chrome`; the theme button ends at **−1659.19px**.

   **Inside the declared subject:** the composer explicitly supports fragments bringing their own wired chrome without a stamp. No duplicate control or malformed HTML is required.

4. **Medium — inserting immediately after `</h1>` can put every control inside a navigation link.** `scripts/page_chrome.py:1111`.

   Concrete input:

   ```python
   place_bar(
       '<a href="#destination"><h1>Title</h1></a><p>Intro</p>',
       chrome_bar('', 'now', refresh=False, textstyle=True),
   )
   ```

   The inserted slot becomes a descendant of the anchor, introducing interactive buttons inside a link. In Chromium, clicking Theme both changes the theme **and navigates to `#destination`**, moving the page.

   **Inside the declared subject:** a linked heading is ordinary, valid fragment markup before insertion. It does not involve the excluded implicit or reopened heading shapes. Shielding establishes that a heading is live; it does not establish a safe insertion parent.

5. **Medium — five positive substring assertions still have ambient suppliers; theme persistence can disappear with 201/201 green.** `scripts/page_chrome.py:1400`, `:1401`, `:1664`, `:1730`, `:1731`.

   The current duplicate counts are:

   | Assertion substring | Occurrences |
   |---|---:|
   | `localStorage.getItem` | 2 |
   | `localStorage.setItem` | 2 |
   | `aria-pressed` | 3 |
   | `window.IntersectionObserver` | 2 |
   | `getBoundingClientRect` | 4 |

   Concrete severance, leaving assertions unchanged:

   ```js
   var s=localStorage.getItem(K); → var s=null;
   localStorage.setItem(K,n);    → void 0;
   ```

   The suite still reports **201/201 passed**. Theme persistence is gone; switcher persistence supplies both asserted substrings.

   **Inside the declared subject:** these cases claim to defend the emitted chrome’s behavior. The threshold assertions were strengthened, but the broader five-assertion problem remains.

Verification reproduced **201/201**, **149/149**, and **178/178**. The shipped scoped mutation harness reproduced **96 killed, 96 attributed, zero survivors**. Chromium confirmed baseline pinning on all five producers, zero stationary flips at dashboard positions 160–168, and correct fresh-load phone pinning. Those green results coexist with the failures above.

The emitted script parses. With Node removed from PATH, both parse cases report named `CANNOT RUN` failures and the suite reports **199/201**, so missing Node does fail loudly. I did not establish a separate accessibility defect from moving the real fragments’ switchers.

**NOT CONVERGED — the cache fix restores unreachable controls after ordinary resizing, and the CSS fold recreates the previously fixed own-ID omission.**
