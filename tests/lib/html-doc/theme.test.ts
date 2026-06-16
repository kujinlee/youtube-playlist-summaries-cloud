import {
  themeStyleBlock,
  THEME_HEAD_SCRIPT,
  THEME_TOGGLE_BUTTON,
  THEME_TOGGLE_SCRIPT,
  type Palette,
} from '../../../lib/html-doc/theme';

const LIGHT: Palette = { page: '#ffffff', card: '#fafafa', ink: '#111111', shadow: '0 1px 3px rgba(0,0,0,.08)' };
const DARK: Palette = { page: '#0f1115', card: '#16181d', ink: '#e3e6ea', shadow: '0 1px 3px rgba(0,0,0,.5)' };

describe('themeStyleBlock', () => {
  const css = themeStyleBlock(LIGHT, DARK);

  it('emits light vars on :root', () => {
    expect(css).toContain(':root{--page:#ffffff;--card:#fafafa;--ink:#111111;--shadow:0 1px 3px rgba(0,0,0,.08)}');
  });

  it('emits an explicit light override selector', () => {
    expect(css).toContain('[data-theme="light"]{--page:#ffffff');
  });

  it('emits an explicit dark override selector', () => {
    expect(css).toContain('[data-theme="dark"]{--page:#0f1115;--card:#16181d;--ink:#e3e6ea');
  });

  it('emits the system-dark media query for un-toggled documents', () => {
    expect(css).toContain('@media(prefers-color-scheme:dark){:root:not([data-theme]){--page:#0f1115');
  });

  it('styles the fixed toggle button using theme vars', () => {
    expect(css).toContain('#theme-toggle{');
    expect(css).toContain('position:fixed');
    expect(css).toContain('background:var(--card)');
    expect(css).toContain('color:var(--ink)');
  });

  it('gates the color transition behind a post-load readiness class (no load fade)', () => {
    expect(css).toContain('html.theme-ready');
    expect(css).toContain('transition:background-color .2s,color .2s');
  });

  it('forces the LIGHT palette and hides the toggle when printing', () => {
    expect(css).toContain('@media print{:root,[data-theme="light"],[data-theme="dark"]{--page:#ffffff');
    expect(css).toContain('#theme-toggle{display:none}');
  });

  it('does not throw on an empty palette', () => {
    expect(() => themeStyleBlock({}, {})).not.toThrow();
    expect(themeStyleBlock({}, {})).toContain(':root{}');
  });
});

describe('THEME_HEAD_SCRIPT', () => {
  it('reads only the dark/light values from localStorage inside try/catch', () => {
    expect(THEME_HEAD_SCRIPT).toContain("localStorage.getItem('html-doc-theme')");
    expect(THEME_HEAD_SCRIPT).toContain("t==='dark'||t==='light'");
    expect(THEME_HEAD_SCRIPT).toContain('try{');
    expect(THEME_HEAD_SCRIPT).toContain('catch');
    expect(THEME_HEAD_SCRIPT).toContain("setAttribute('data-theme',t)");
  });
});

describe('THEME_TOGGLE_BUTTON', () => {
  it('is an accessible, typed button', () => {
    expect(THEME_TOGGLE_BUTTON).toContain('id="theme-toggle"');
    expect(THEME_TOGGLE_BUTTON).toContain('type="button"');
    expect(THEME_TOGGLE_BUTTON).toContain('aria-label=');
  });
});

describe('THEME_TOGGLE_SCRIPT', () => {
  it('computes effective theme from system when unset and persists toggles', () => {
    expect(THEME_TOGGLE_SCRIPT).toContain('prefers-color-scheme: dark');
    expect(THEME_TOGGLE_SCRIPT).toContain('matchMedia');
    expect(THEME_TOGGLE_SCRIPT).toContain("setItem('html-doc-theme',next)");
    expect(THEME_TOGGLE_SCRIPT).toContain('try{');
  });

  it('enables transitions only after first paint (requestAnimationFrame → theme-ready)', () => {
    expect(THEME_TOGGLE_SCRIPT).toContain('requestAnimationFrame');
    expect(THEME_TOGGLE_SCRIPT).toContain("classList.add('theme-ready')");
  });
});
