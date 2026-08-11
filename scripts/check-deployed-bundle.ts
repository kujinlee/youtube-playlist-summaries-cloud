/** Fetch what the DEPLOYED app actually serves and assert no server-only credential is in it.
 *
 *  This replaces M1.4's B5, which asked `check-service-confinement.ts` to "pass against the real
 *  deployed environment". It cannot: that script is static, walks the source import graph, and
 *  emits byte-identical output everywhere. Someone runs it, sees OK, and ticks a box believing
 *  production was verified. This one reads the live server, so it is capable of failing.
 *
 *  Usage:  npm run check:deployed-bundle -- [baseUrl]
 *          DEPLOY_URL=https://… npm run check:deployed-bundle
 */
import { extractScriptUrls, findLeakedSecrets, type Leak } from '../lib/security/bundle-secret-scan';

const DEFAULT_URL = 'https://youtube-playlist-summaries.fly.dev';
/** A page that renders logged-out, so the check needs no session. */
const ENTRY_PATH = '/login';

async function get(url: string): Promise<string> {
  const res = await fetch(url, { redirect: 'follow' });
  if (!res.ok) throw new Error(`GET ${url} → ${res.status}`);
  return res.text();
}

function report(source: string, leaks: Leak[]): void {
  for (const l of leaks) console.error(`  LEAK ${l.kind} at offset ${l.index} in ${source} (${l.hint})`);
}

async function main(): Promise<number> {
  const baseUrl = (process.argv[2] || process.env.DEPLOY_URL || DEFAULT_URL).replace(/\/$/, '');
  console.log(`scanning deployment: ${baseUrl}`);

  const html = await get(baseUrl + ENTRY_PATH);
  const scripts = extractScriptUrls(html, baseUrl);

  // FAIL-OPEN GUARD. If the markup ever changes shape and the extractor matches nothing, this
  // would scan one HTML page, find no secrets, and report success — a green gate that checked
  // almost nothing. A real Next.js page always ships chunks, so zero is a broken check, not a
  // clean deployment. This project has shipped that exact failure before; refuse instead.
  if (scripts.length === 0) {
    console.error(`FAILED: no same-origin <script src> found on ${ENTRY_PATH}.`);
    console.error('The check could not do its job — treat this as NOT RUN, not as a pass.');
    return 1;
  }

  let total = 0;
  const found: Array<[string, Leak[]]> = [];

  const htmlLeaks = findLeakedSecrets(html);
  if (htmlLeaks.length) found.push([ENTRY_PATH, htmlLeaks]);
  total += html.length;

  for (const url of scripts) {
    const body = await get(url);
    total += body.length;
    const leaks = findLeakedSecrets(body);
    if (leaks.length) found.push([url.slice(baseUrl.length), leaks]);
  }

  console.log(`scanned ${ENTRY_PATH} + ${scripts.length} script(s), ${total} bytes`);

  if (found.length) {
    console.error('SERVER-ONLY CREDENTIAL SERVED TO THE BROWSER:');
    for (const [source, leaks] of found) report(source, leaks);
    return 1;
  }

  console.log('deployed bundle clean — no service_role JWT, no sb_secret_* key');
  return 0;
}

main().then(
  (code) => process.exit(code),
  (err) => {
    // A fetch/network failure is NOT a pass. Same reasoning as the zero-scripts guard.
    console.error(`FAILED to complete the scan: ${err instanceof Error ? err.message : String(err)}`);
    console.error('Treat this as NOT RUN.');
    process.exit(1);
  },
);
