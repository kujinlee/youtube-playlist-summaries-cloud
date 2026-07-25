import { readFileSync, readdirSync } from 'fs';
import { join } from 'path';

// #13 deploy guard: the dev-login flag must NOT be enabled by any in-repo production config.
// This catches config drift (someone committing DEV_LOGIN_ENABLED to fly.toml/Dockerfile/CI).
// It does NOT catch a runtime `fly secrets set DEV_LOGIN_ENABLED=true` — that path is covered
// by the URL defense-in-depth in the gate and the post-deploy /dev-login 404 smoke check in
// docs/deploy.md.
const root = join(__dirname, '..', '..');

describe('in-repo production config must NOT enable dev-login', () => {
  it('fly.toml does not set DEV_LOGIN_ENABLED', () => {
    expect(readFileSync(join(root, 'fly.toml'), 'utf8')).not.toMatch(/DEV_LOGIN_ENABLED/);
  });
  it('Dockerfile does not set DEV_LOGIN_ENABLED', () => {
    expect(readFileSync(join(root, 'Dockerfile'), 'utf8')).not.toMatch(/DEV_LOGIN_ENABLED/);
  });
  it('no CI workflow sets DEV_LOGIN_ENABLED', () => {
    const dir = join(root, '.github', 'workflows');
    let files: string[] = [];
    try { files = readdirSync(dir); } catch { files = []; } // no workflows dir → vacuously safe
    for (const f of files) {
      expect(readFileSync(join(dir, f), 'utf8')).not.toMatch(/DEV_LOGIN_ENABLED/);
    }
  });
});
