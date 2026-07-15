/** Location-like interface used by initDigControls and wireDigLinks. */
export interface NavLocation {
  pathname: string;
  search: string;
}

/**
 * Extract videoId and outputFolder from the current page URL.
 * The summary HTML is served at /api/html/[id]?outputFolder=<enc>&type=summary.
 */
function parsePageUrl(loc: NavLocation): { videoId: string; outputFolder: string } | null {
  const parts = loc.pathname.split('/');
  // pathname = /api/html/<videoId>  → parts[0]='' [1]='api' [2]='html' [3]=<id>
  const videoId = parts[3];
  if (!videoId) return null;
  const outputFolder = new URLSearchParams(loc.search).get('outputFolder');
  if (!outputFolder) return null;
  return { videoId, outputFolder };
}

/** Build the "view detail ↓" href for a dug section (no ?dig param). */
function viewDetailHref(videoId: string, outputFolder: string, startSec: number): string {
  const u = new URLSearchParams();
  u.set('outputFolder', outputFolder);
  u.set('type', 'dig-deeper');
  return `/api/html/${videoId}?${u.toString()}#t=${startSec}`;
}

/** Build the "dig deeper ▶" href for an un-dug section (includes ?dig=N to auto-trigger). */
function digDeeperHref(videoId: string, outputFolder: string, startSec: number): string {
  const u = new URLSearchParams();
  u.set('outputFolder', outputFolder);
  u.set('type', 'dig-deeper');
  u.set('dig', String(startSec));
  return `/api/html/${videoId}?${u.toString()}#t=${startSec}`;
}

/**
 * Mark a summary-side dig control as "dug" (view-detail nav-link state).
 * Same-tab navigation — no target="_blank".
 */
function applyDugState(el: HTMLAnchorElement, videoId: string, outputFolder: string, startSec: number): void {
  el.textContent = 'view detail ↓';
  el.setAttribute('href', viewDetailHref(videoId, outputFolder, startSec));
  el.removeAttribute('target');
  el.removeAttribute('rel');
  el.dataset.state = 'dug';
}

/** Mark a control as the un-dug nav-link state ("dig deeper ▶" with href). */
function applyIdleState(el: HTMLAnchorElement, videoId: string, outputFolder: string, startSec: number): void {
  el.textContent = 'dig deeper ▶';
  el.setAttribute('href', digDeeperHref(videoId, outputFolder, startSec));
  el.removeAttribute('target');
  el.removeAttribute('rel');
  el.dataset.state = 'idle';
}

/**
 * Apply dug/idle nav-link state to all summary-side `.dig[data-section]` controls.
 * Fetches dig-state; fails open (un-dug nav href) on any error.
 */
async function applyDigStateFromFetch(
  controls: HTMLAnchorElement[],
  videoId: string,
  outputFolder: string,
): Promise<void> {
  let dugSectionIds: number[] = [];
  try {
    const resp = await fetch(
      `/api/videos/${videoId}/dig-state?outputFolder=${encodeURIComponent(outputFolder)}`,
    );
    if (resp.ok) {
      const data = await resp.json() as { sectionIds: number[] };
      dugSectionIds = data.sectionIds ?? [];
    }
  } catch {
    // fail-open — controls get the un-dug nav href
  }

  for (const el of controls) {
    const startSec = Number(el.dataset.section);
    if (dugSectionIds.includes(startSec)) {
      applyDugState(el, videoId, outputFolder, startSec);
    } else {
      applyIdleState(el, videoId, outputFolder, startSec);
    }
  }
}

/**
 * Wire summary-side `.dig[data-section]` controls as same-tab nav links.
 *
 * - On load: fetches GET dig-state and marks already-dug controls as "view detail ↓"
 *   (href to dig-deeper page, same tab) and un-dug controls as "dig deeper ▶"
 *   (href to dig-deeper page with ?dig=N, same tab).
 * - dig-state fetch failure → fail-open: controls still get the un-dug nav href.
 * - On pageshow with event.persisted (bfcache restore): re-fetches dig-state and
 *   re-applies dug/un-dug labels+hrefs.
 * - No POST, no EventSource, no ⏳ loading state, no force-redig button.
 */
export async function initDigControls(
  doc: Document,
  loc: NavLocation,
): Promise<void> {
  const parsed = parsePageUrl(loc);
  if (!parsed) return;
  const { videoId, outputFolder } = parsed;

  // Collect all summary-side controls (have data-section, no data-type)
  const controls = Array.from(doc.querySelectorAll<HTMLAnchorElement>('a.dig[data-section]'))
    .filter((el) => !el.dataset.type);

  if (controls.length === 0) return;

  // Initial state application
  await applyDigStateFromFetch(controls, videoId, outputFolder);

  // pageshow: re-fetch on bfcache restore
  doc.defaultView?.addEventListener('pageshow', (ev: PageTransitionEvent) => {
    if (ev.persisted) {
      void applyDigStateFromFetch(controls, videoId, outputFolder);
    }
  });
}

/** Parse the `t=<sec>s` start time out of a ▶ link URL. */
export function startSecFromTsUrl(url: string): number | null {
  const m = url.match(/[?&]t=(\d+)s/);
  return m ? Number(m[1]) : null;
}

/**
 * The summary-side dig control (same-tab nav link). Omits `data-type`; uses `data-section`
 * so initDigControls can identify the section to fetch dig-state for.
 */
export function digControl(startSec: number): string;
/**
 * The cross-doc "back to summary" nav control (muted trailing link), emitted by the
 * dig-deeper doc. `targetType` must be 'summary'. href computed client-side by
 * wireDigLinks via `data-type`.
 */
export function digControl(targetType: 'summary', startSec: number): string;
export function digControl(targetTypeOrStartSec: 'summary' | number, startSec?: number): string {
  if (typeof targetTypeOrStartSec === 'number') {
    // Summary-side: nav-link control
    const sec = targetTypeOrStartSec;
    return ` <a class="dig" data-section="${sec}" data-t="${sec}">dig deeper ▶</a>`;
  }
  // Cross-doc: "↑ summary" link back to the summary doc (emitted by the dig-deeper doc)
  return ` <a class="dig" data-type="${targetTypeOrStartSec}" data-t="${startSec}">↑ summary</a>`;
}

/** Rebuild each .dig href from the current serve URL: swap `type`, set `#t=`, inherit id+outputFolder. */
export function wireDigLinks(doc: Document, loc: { href: string }): void {
  doc.querySelectorAll('a.dig').forEach((a) => {
    const el = a as HTMLAnchorElement;
    // Summary-side controls have data-section but NO data-type; their href is owned by
    // initDigControls (nav-link state machine) — leave them untouched to avoid injecting type=undefined.
    if (!el.dataset.type) return;
    const u = new URL(loc.href);
    u.searchParams.set('type', el.dataset.type);
    u.hash = 't=' + el.dataset.t;
    el.setAttribute('href', u.pathname + u.search + u.hash);
  });
}

/** Scroll to the section whose data-start is the greatest value <= the #t=<sec> in the URL. */
export function scrollToHashSection(doc: Document, loc: { hash: string }): void {
  const m = loc.hash.match(/^#t=(\d+)/);
  if (!m) return;
  const sec = Number(m[1]);
  const starts = Array.from(doc.querySelectorAll('[data-start]'))
    .map((e) => Number((e as HTMLElement).dataset.start));
  const target = Math.max(...starts.filter((s) => s <= sec), -1);
  if (target >= 0) (doc.querySelector(`[data-start="${target}"]`) as HTMLElement | null)?.scrollIntoView();
}

export const NAV_CSS =
  `.dig{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--meta);` +
  `font-size:.8rem;font-weight:400;text-decoration:none;white-space:nowrap;cursor:pointer}` +
  `.dig:hover{text-decoration:underline}`;

// Self-contained inline script (the browser can't import the module) — mirrors
// wireDigLinks + scrollToHashSection + initDigControls above.
// Injected at end-of-body (DOM ready).
// DRIFT WARNING: the inline JS functions (applyDug/applyIdle) intentionally duplicate
// the TS helpers above and must be kept in sync — the inline string is not covered by jsdom tests.
const NAV_SCRIPT = `<script>
(function(){
  // ── cross-doc nav (dig-deeper → summary) ─────────────────────────────────
  document.querySelectorAll('a.dig').forEach(function(a){
    if(!a.dataset.type)return;
    var u=new URL(location.href);
    u.searchParams.set('type',a.dataset.type);
    u.hash='t='+a.dataset.t;
    a.setAttribute('href',u.pathname+u.search+u.hash);
  });
  // ── scroll to #t= hash ────────────────────────────────────────────────────
  var m=location.hash.match(/^#t=(\\d+)/);
  if(m){
    var sec=+m[1];
    var starts=[].slice.call(document.querySelectorAll('[data-start]')).map(function(e){return +e.dataset.start;});
    var t=Math.max.apply(null,starts.filter(function(s){return s<=sec;}).concat([-1]));
    if(t>=0){var el=document.querySelector('[data-start="'+t+'"]'); if(el){el.scrollIntoView();}}
  }
  // ── dig-state machine (summary-side only) ────────────────────────────────
  var parts=location.pathname.split('/');
  var videoId=parts[3];
  var _sp=new URLSearchParams(location.search);
  var outputFolder=_sp.get('outputFolder');
  if(!videoId||!outputFolder)return;
  // ── dig-doc client (dig-deeper page only) ────────────────────────────────
  // Correctness premise: the POST job calls upsertDugSection BEFORE emitting
  // "done", so the re-GET of the current page reflects the new dug section.
  if(_sp.get('type')==='dig-deeper'){
    var _dg=document.querySelector('.dg');
    if(_dg){
      function _applyDigErr(el){el.textContent='\\u26a0 retry';el.dataset.state='error';el.removeAttribute('href');}
      // Non-blocking progress bar means clicks are no longer physically blocked
      // during an expand-all run (the old full-screen overlay masked them). Guard
      // against concurrent generation: a second expand-all or a manual single dig
      // is ignored while a batch is running. Reading aids (toggle) stay allowed.
      var _eaRunning=false;
      // ── Promise-based dig: single POST→SSE→swap core ─────────────────────
      function _startDocDigAsync(trigger){
        return new Promise(function(resolve,reject){
          var startSec=+trigger.dataset.section;
          trigger.textContent='\\u23f3';trigger.dataset.state='loading';trigger.removeAttribute('href');
          fetch('/api/videos/'+videoId+'/dig/'+startSec,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({outputFolder:outputFolder})})
            .then(function(r){if(!r.ok)throw new Error('POST '+r.status);return r.json();})
            .then(function(d){
              var es=new EventSource('/api/videos/'+videoId+'/dig/'+startSec+'/stream?jobId='+encodeURIComponent(d.jobId));
              es.onmessage=function(ev){
                try{var msg=JSON.parse(ev.data);
                  if(msg.type==='done'){
                    es.close();
                    fetch(location.href)
                      .then(function(res){return res.text();})
                      .then(function(html){
                        var dp=new DOMParser();
                        var fd=dp.parseFromString(html,'text/html');
                        var fresh=fd.querySelector('[data-start="'+startSec+'"]');
                        var cur=document.querySelector('[data-start="'+startSec+'"]');
                        if(fresh&&cur&&cur.parentNode){cur.parentNode.replaceChild(document.adoptNode(fresh),cur);}
                        resolve();
                      })
                      .catch(function(err){_applyDigErr(trigger);reject(err);});
                  }else if(msg.type==='error'){es.close();_applyDigErr(trigger);reject(new Error('stream error'));}
                }catch(e){}
              };
              es.onerror=function(){es.close();_applyDigErr(trigger);reject(new Error('SSE error'));};
            })
            .catch(function(err){_applyDigErr(trigger);reject(err);});
        });
      }
      // ── Single-click path: delegate to the async core ─────────────────────
      function _startDocDig(trigger){_startDocDigAsync(trigger).catch(function(){});}
      // ── ⤢ expand all — confirm → serialized loop ──────────────────────────
      var _eaBtn=_dg.querySelector('.dg-expand-all');
      if(_eaBtn){
        var _eaDlg=document.getElementById('_dg-ea-dlg');
        var _eaProg=document.getElementById('_dg-ea-prog');
        var _eaMsg=document.getElementById('_dg-ea-msg');
        var _eaProgMsg=document.getElementById('_dg-ea-prog-msg');
        var _eaFailMsg=document.getElementById('_dg-ea-fail-msg');
        var _eaCancelProg=document.getElementById('_dg-ea-cancel-prog');
        function _eaClose(el){el.removeAttribute('data-open');}
        function _eaOpen(el){el.setAttribute('data-open','');}
        function _eaRunBatch(triggers,N){
          _eaOpen(_eaProg);
          _eaRunning=true;
          var cancelled=false;
          var failures=[];
          var k=0;
          _eaCancelProg.onclick=function(){cancelled=true;};
          function _next(){
            // Collect still-un-dug triggers (may have changed if DOM was swapped).
            // Exclude error-state triggers — they already failed in this batch run.
            var remaining=[].slice.call(document.querySelectorAll('.dig-trigger[data-section], .dig-refresh[data-section]'))
              .filter(function(t){return t.dataset.state!=='error'&&t.dataset.state!=='loading';});
            if(cancelled||remaining.length===0){
              _eaRunning=false;
              if(failures.length>0){
                // Show failure summary in the progress overlay then auto-close.
                _eaProgMsg.textContent='Done with '+failures.length+' failure(s).';
                _eaFailMsg.textContent='Failed sections: '+failures.join(', ');
                _eaFailMsg.style.display='';
                setTimeout(function(){_eaClose(_eaProg);_eaFailMsg.style.display='none';},6000);
              }else{
                _eaClose(_eaProg);
              }
              return;
            }
            k++;
            _eaProgMsg.textContent='Expanding \\u2014 section '+k+' of '+N+'\\u2026';
            var trig=remaining[0];
            _startDocDigAsync(trig)
              .then(function(){_next();})
              .catch(function(){failures.push(trig.dataset.section);_next();});
          }
          _next();
        }
        _eaBtn.addEventListener('click',function(){
          if(_eaRunning)return;
          var triggers=[].slice.call(document.querySelectorAll('.dig-trigger[data-section], .dig-refresh[data-section]'));
          var N=triggers.length;
          if(N===0)return;
          var X=(N*0.05).toFixed(2);
          var Y=Math.ceil(N*30/60);
          _eaMsg.textContent='Expand '+N+' remaining sections? ~$'+X+', ~'+Y+' min (rough estimate)';
          _eaOpen(_eaDlg);
          var _escHandler=function(e){if(e.key==='Escape'){_eaClose(_eaDlg);document.removeEventListener('keydown',_escHandler);}};
          document.addEventListener('keydown',_escHandler);
          _eaDlg.onclick=function(e){if(e.target===_eaDlg){_eaClose(_eaDlg);document.removeEventListener('keydown',_escHandler);}};
          document.getElementById('_dg-ea-confirm').onclick=function(){
            document.removeEventListener('keydown',_escHandler);
            _eaClose(_eaDlg);
            _eaRunBatch(triggers,N);
          };
          document.getElementById('_dg-ea-cancel-dlg').onclick=function(){
            _eaClose(_eaDlg);
            document.removeEventListener('keydown',_escHandler);
          };
        });
      }
      _dg.addEventListener('click',function(e){
        // Toggle (dug → show gist or dug) — zero fetch
        var tog=(e.target.closest?e.target.closest('.dig-toggle'):null);
        if(tog){e.preventDefault();var s=tog.closest('section');if(s){s.classList.toggle('show-gist');tog.textContent=s.classList.contains('show-gist')?'show dig deeper \\u25b6':'show summary \\u2303';}return;}
        // Refresh (stale dug → re-dig in place) — must be before .dig-trigger check
        var refresh=(e.target.closest?e.target.closest('.dig-refresh[data-section]'):null);
        if(refresh){e.preventDefault();if(_eaRunning)return;_startDocDig(refresh);return;}
        // Trigger (un-dug → expand in place)
        var trig=(e.target.closest?e.target.closest('.dig-trigger[data-section]'):null);
        if(!trig)return;
        e.preventDefault();
        if(_eaRunning)return;
        var st=trig.dataset.state;
        if(st==='loading')return;
        _startDocDig(trig);
      });
      // ── ?dig=N auto-trigger ───────────────────────────────────────────────
      // Strip ?dig from URL immediately (keep type, outputFolder, hash) so
      // reload / back-forward never re-fires generation.
      function _stripDigParam(){
        var u2=new URL(location.href);
        u2.searchParams.delete('dig');
        history.replaceState(null,'',u2.pathname+u2.search+(u2.hash||''));
      }
      function _applyDigDocState(dugIds){
        // Re-apply control visibility to reflect current dug state.
        // (Used by pageshow to refresh a bfcache-restored page.)
        dugIds.forEach(function(id){
          var el=document.querySelector('[data-start="'+id+'"]');
          if(el)el.setAttribute('data-dug','true');
        });
      }
      function _handleDigParam(isPageshow){
        var digN=isPageshow?null:_sp.get('dig');
        var digSec=digN!==null&&digN!==''?+digN:null;
        fetch('/api/videos/'+videoId+'/dig-state?outputFolder='+encodeURIComponent(outputFolder))
          .then(function(r){return r.ok?r.json():Promise.resolve({sectionIds:[]});})
          .then(function(data){
            var dugIds=data.sectionIds||[];
            if(isPageshow){
              // bfcache restore: re-apply states only, no auto-trigger
              _applyDigDocState(dugIds);
              return;
            }
            if(digSec===null)return;
            // Strip ?dig immediately regardless of dug state
            _stripDigParam();
            var trigger=document.querySelector('.dig-trigger[data-section="'+digSec+'"]');
            if(!trigger)return; // invalid/unknown N — no-op
            if(dugIds.indexOf(digSec)>=0){
              // Already dug: scroll only, no POST
              var sect=document.querySelector('[data-start="'+digSec+'"]');
              if(sect)sect.scrollIntoView();
            }else{
              // Un-dug: trigger once then scroll after re-GET replaces section
              _startDocDig(trigger);
            }
          })
          .catch(function(){
            if(!isPageshow)_stripDigParam();
          });
      }
      _handleDigParam(false);
      window.addEventListener('pageshow',function(ev){
        if(ev.persisted)_handleDigParam(true);
      });
    }
    return;
  }
  // ── summary-side nav links ────────────────────────────────────────────────
  var controls=[].slice.call(document.querySelectorAll('a.dig[data-section]')).filter(function(a){return!a.dataset.type;});
  if(!controls.length)return;
  function viewHref(sec){
    var p=new URLSearchParams();
    p.set('outputFolder',outputFolder);
    p.set('type','dig-deeper');
    return '/api/html/'+videoId+'?'+p.toString()+'#t='+sec;
  }
  function digHref(sec){
    var p=new URLSearchParams();
    p.set('outputFolder',outputFolder);
    p.set('type','dig-deeper');
    p.set('dig',String(sec));
    return '/api/html/'+videoId+'?'+p.toString()+'#t='+sec;
  }
  function applyDug(el,sec){
    el.textContent='view detail \\u2193';
    el.setAttribute('href',viewHref(sec));
    el.removeAttribute('target');
    el.removeAttribute('rel');
    el.dataset.state='dug';
  }
  function applyIdle(el,sec){
    el.textContent='dig deeper \\u25b6';
    el.setAttribute('href',digHref(sec));
    el.removeAttribute('target');
    el.removeAttribute('rel');
    el.dataset.state='idle';
  }
  function applyControls(dugIds){
    controls.forEach(function(el){
      var sec=+el.dataset.section;
      if(dugIds.indexOf(sec)>=0){applyDug(el,sec);}else{applyIdle(el,sec);}
    });
  }
  function fetchAndApply(){
    fetch('/api/videos/'+videoId+'/dig-state?outputFolder='+encodeURIComponent(outputFolder))
      .then(function(r){return r.ok?r.json():Promise.resolve({sectionIds:[]});})
      .then(function(data){applyControls(data.sectionIds||[]);})
      .catch(function(){applyControls([]);});
  }
  fetchAndApply();
  window.addEventListener('pageshow',function(ev){
    if(ev.persisted)fetchAndApply();
  });
})();
</script>`;

// NAV_SCRIPT keeps its existing verbatim body; navScript only stamps the nonce onto the opening tag.
export function navScript(nonce?: string): string {
  return nonce ? NAV_SCRIPT.replace('<script>', `<script nonce="${nonce}">`) : NAV_SCRIPT;
}

// ── Cloud dig-deeper: poll-based trigger engine ──────────────────────────────
// Cloud dig runs on a separate worker (no in-process job registry), so there is
// no SSE. The trigger POSTs (no body), then polls dig-state until the section's
// blob appears, then re-fetches the page and swaps the section in place — the
// same DOM-swap as the local SSE 'done' handler. DRIFT WARNING: DIG_CLOUD_SCRIPT
// below duplicates these helpers in inline ES5 and must be kept in sync. The inline
// string IS smoke-executed in jsdom (nav-cloud-dig-inline.test.ts), but that covers
// only the ready/error/toggle paths — the poll-timer path is verified only via the
// TS mirror, so keep the two in sync by hand.
export interface CloudDigEnv {
  fetch: typeof fetch;
  now: () => number;
  sleep: (ms: number) => Promise<void>;
  getPageHref: () => string;
  doc: Document;
}

/** Cloud dig timing (see plan Global Constraints). */
const CLOUD_DIG_TIMEOUT_MS = 180000;
const CLOUD_DIG_POLL_START_MS = 2000;
const CLOUD_DIG_POLL_STEP_MS = 2000;
const CLOUD_DIG_POLL_MAX_MS = 10000;

/** Set a trigger to the error state (message + data-state + drop href). */
export function applyCloudDigError(el: HTMLElement, msg: string): void {
  el.textContent = msg;
  el.dataset.state = 'error';
  el.removeAttribute('href');
}

/**
 * Re-fetch the current page and replace the [data-start=sec] <section> in place.
 * Throws if the re-fetched section is missing or NOT actually dug (data-dug!=="true").
 * This guards against dig-state over-reporting (blob malformed/vanished): without the
 * check, a swap would silently no-op and the trigger would stay stuck at ⏳ (H2).
 */
export async function swapDugSection(sec: number, env: CloudDigEnv): Promise<void> {
  const res = await env.fetch(env.getPageHref());
  const html = await res.text();
  const fresh = new DOMParser().parseFromString(html, 'text/html').querySelector(`[data-start="${sec}"]`);
  const cur = env.doc.querySelector(`[data-start="${sec}"]`);
  if (!fresh || fresh.getAttribute('data-dug') !== 'true' || !cur || !cur.parentNode) {
    throw new Error('dig section not present/dug after generation');
  }
  cur.parentNode.replaceChild(env.doc.adoptNode(fresh), cur);
}

/**
 * Poll dig-state until `sec` is present, or the timeout ceiling elapses.
 * The deadline is checked AFTER each sleep so no fetch fires past the ceiling (M1).
 */
export async function pollUntilDug(sec: number, videoId: string, playlist: string, env: CloudDigEnv): Promise<boolean> {
  const deadline = env.now() + CLOUD_DIG_TIMEOUT_MS;
  let delay = CLOUD_DIG_POLL_START_MS;
  for (;;) {
    await env.sleep(delay);
    if (env.now() > deadline) return false;
    let ids: number[] = [];
    try {
      const r = await env.fetch(`/api/videos/${videoId}/dig-state?playlist=${encodeURIComponent(playlist)}`);
      if (r.ok) ids = ((await r.json()) as { sectionIds?: number[] }).sectionIds ?? [];
    } catch { /* keep polling */ }
    if (ids.includes(sec)) return true;
    delay = Math.min(delay + CLOUD_DIG_POLL_STEP_MS, CLOUD_DIG_POLL_MAX_MS);
  }
}

/** Full cloud dig flow for one trigger: POST → (ready | poll) → swap; maps errors to trigger text. */
export async function startCloudDig(trigger: HTMLElement, videoId: string, playlist: string, env: CloudDigEnv): Promise<void> {
  const sec = Number(trigger.dataset.section);
  trigger.textContent = '⏳ generating…';   // spec §4/§7 loading copy (M2)
  trigger.dataset.state = 'loading';
  trigger.removeAttribute('href');
  let resp: Response;
  try {
    resp = await env.fetch(`/api/videos/${videoId}/dig/${sec}?playlist=${encodeURIComponent(playlist)}`, { method: 'POST' });
  } catch { applyCloudDigError(trigger, '⚠ retry'); return; }
  if (resp.status === 403) { applyCloudDigError(trigger, '⚠ Create an account to dig deeper'); return; }
  if (resp.status === 429 || resp.status === 503) { applyCloudDigError(trigger, '⚠ busy — try later'); return; }
  if (!resp.ok) { applyCloudDigError(trigger, '⚠ retry'); return; }
  let data: { status?: string } = {};
  try { data = (await resp.json()) as { status?: string }; } catch { /* treat as enqueued */ }
  if (data.status === 'ready') {
    try { await swapDugSection(sec, env); } catch { applyCloudDigError(trigger, '⚠ retry'); }
    return;
  }
  const done = await pollUntilDug(sec, videoId, playlist, env);
  if (!done) { applyCloudDigError(trigger, '⚠ retry'); return; }
  try { await swapDugSection(sec, env); } catch { applyCloudDigError(trigger, '⚠ retry'); }
}

// Inline ES5 mirror of the cloud dig helpers above (the browser can't import the module).
// Selector uses `a.dig-trigger[data-section]` so the anonymous pre-disabled <span> is inert.
const DIG_CLOUD_SCRIPT = `<script>
(function(){
  var _dg=document.querySelector('.dg');
  if(!_dg)return;
  var videoId=location.pathname.split('/')[3];
  var playlist=new URLSearchParams(location.search).get('playlist');
  if(!videoId||!playlist)return;
  function _err(el,msg){el.textContent=msg;el.dataset.state='error';el.removeAttribute('href');}
  function _swap(sec){
    return fetch(location.href).then(function(res){return res.text();}).then(function(html){
      var fd=new DOMParser().parseFromString(html,'text/html');
      var fresh=fd.querySelector('[data-start="'+sec+'"]');
      var cur=document.querySelector('[data-start="'+sec+'"]');
      if(!fresh||fresh.getAttribute('data-dug')!=='true'||!cur||!cur.parentNode){throw new Error('not dug');}
      cur.parentNode.replaceChild(document.adoptNode(fresh),cur);
    });
  }
  function _poll(sec,trigger){
    var deadline=Date.now()+180000;var delay=2000;
    function tick(){
      if(Date.now()>deadline){_err(trigger,'\\u26a0 retry');return;}
      fetch('/api/videos/'+videoId+'/dig-state?playlist='+encodeURIComponent(playlist))
        .then(function(r){return r.ok?r.json():{sectionIds:[]};})
        .then(function(d){
          var ids=(d&&d.sectionIds)||[];
          if(ids.indexOf(sec)>=0){_swap(sec).catch(function(){_err(trigger,'\\u26a0 retry');});}
          else{delay=Math.min(delay+2000,10000);setTimeout(tick,delay);}
        })
        .catch(function(){delay=Math.min(delay+2000,10000);setTimeout(tick,delay);});
    }
    setTimeout(tick,delay);
  }
  function _start(trigger){
    var sec=+trigger.dataset.section;
    trigger.textContent='\\u23f3 generating\\u2026';trigger.dataset.state='loading';trigger.removeAttribute('href');
    fetch('/api/videos/'+videoId+'/dig/'+sec+'?playlist='+encodeURIComponent(playlist),{method:'POST'})
      .then(function(r){
        if(r.status===403){_err(trigger,'\\u26a0 Create an account to dig deeper');return null;}
        if(r.status===429||r.status===503){_err(trigger,'\\u26a0 busy \\u2014 try later');return null;}
        if(!r.ok){_err(trigger,'\\u26a0 retry');return null;}
        return r.json().catch(function(){return {};});
      })
      .then(function(d){
        if(d===null)return;
        if(d&&d.status==='ready'){_swap(sec).catch(function(){_err(trigger,'\\u26a0 retry');});return;}
        _poll(sec,trigger);
      })
      .catch(function(){_err(trigger,'\\u26a0 retry');});
  }
  _dg.addEventListener('click',function(e){
    var tog=(e.target.closest?e.target.closest('.dig-toggle'):null);
    if(tog){e.preventDefault();var s=tog.closest('section');if(s){s.classList.toggle('show-gist');tog.textContent=s.classList.contains('show-gist')?'show dig deeper \\u25b6':'show summary \\u2303';}return;}
    var trig=(e.target.closest?e.target.closest('a.dig-trigger[data-section]'):null);
    if(!trig)return;
    e.preventDefault();
    if(trig.dataset.state==='loading')return;
    _start(trig);
  });
})();
</script>`;

/** Cloud dig-deeper inline engine (poll-based). Injected in place of navScript for the cloud interactive doc. */
export function digCloudScript(nonce?: string): string {
  return nonce ? DIG_CLOUD_SCRIPT.replace('<script>', `<script nonce="${nonce}">`) : DIG_CLOUD_SCRIPT;
}
