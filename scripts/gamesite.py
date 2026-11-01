"""Shared pieces of the ScrapWorkshop publishing tools (prepare, deploy, roll back).

Only completed Unity WebGL builds and the cost-free preset dialogue are published. Nothing here builds Unity or calls an
AI API. Each build lives in games/scrap-workshop/releases/<version>/ (version = content hash), so a new deploy never
changes a file an open tab is still loading; the entry files (index.html, sw.js, release.json) point at one release.
"""
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import urllib.request
from datetime import datetime, timezone

SITE = pathlib.Path(__file__).resolve().parents[1]
DEST = SITE / 'games' / 'scrap-workshop'
REPO = 'glorious0628-coder/glorious-studio'
LIVE_ROOT = 'https://glorious.ai.kr/'
LIVE_GAME = LIVE_ROOT + 'games/scrap-workshop/'
NAMES = ['WebGL.loader.js', 'WebGL.framework.js.unityweb', 'WebGL.data.unityweb', 'WebGL.wasm.unityweb']
# Game paths whose state the published build must match (a public version always maps to a game commit).
GAME_SOURCES = ['Assets', 'Packages', 'ProjectSettings', 'Tools/npc-server']


def git(*args, cwd=SITE, check=True):
    r = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if check and r.returncode:
        raise SystemExit(f'git {" ".join(args)} failed: {r.stderr.strip()}')
    return r.stdout.strip()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def build_inputs(source):
    build = source / 'Build' / 'WebGL' / 'Build'
    npc = source / 'Tools' / 'npc-server'
    files = [build / n for n in NAMES]
    files += [npc / 'canon.mjs', npc / 'schema.mjs', npc / 'providers' / 'mock.mjs', source / 'Assets/ScrapWorkshop/Fonts/hud_font.txt']
    for p in files:
        if not p.is_file() or not p.stat().st_size:
            raise SystemExit(f'Missing build input: {p.name}')
    log = (source / 'Logs/build_webgl.log').read_text(encoding='utf-8', errors='replace')
    if 'SW_BUILD_RESULT Succeeded' not in log or log.rfind('SW_BUILD_RESULT Succeeded') < log.rfind('SW_BUILD_BEGIN'):
        raise SystemExit('The current Unity build has no success marker. Wait for it to finish.')
    return files


def worker_js(version):
    return """// Public prototype: preset dialogue, no external AI requests, no asset caching.
import { mockTurn } from './releases/VERSION/npc/mock.mjs';
import { normalize } from './releases/VERSION/npc/schema.mjs';
import { NPCS } from './releases/VERSION/npc/canon.mjs';
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
const endpoint = new URL('api/npc/turn', self.registration.scope).href;
const json = value => {
  const body = JSON.stringify(value);
  return new Response(body, {headers: {'Content-Type':'application/json; charset=utf-8', 'Content-Length':String(new TextEncoder().encode(body).length)}});
};
self.addEventListener('fetch', event => {
  if (event.request.method !== 'POST' || event.request.url !== endpoint) return;
  event.respondWith((async () => {
    let req = {};
    try {
      req = await event.request.json();
      if (!NPCS[req.npc] || !(req.turn >= 0 && req.turn < 100)) throw Error('bad_request');
      const result = await mockTurn(req);
      const clean = normalize(result.raw, req, Object.keys(NPCS[req.npc].purposes), NPCS[req.npc].topics);
      if (!clean || clean.blocked) throw Error('invalid_output');
      const { issues, ...game } = clean;
      return json({ ok: true, requestId: req.requestId, provider: 'mock', model: 'mock', ...game, ms: 0, inTokens: 0, outTokens: 0 });
    } catch {
      return json({ ok: false, requestId: req.requestId || '', provider: 'mock', model: 'mock', error: 'invalid_request' });
    }
  })());
});
""".replace('VERSION', version)


def write_entry(manifest):
    """Points the public game at one release: sw.js, index.html (fallback version baked in), release.json, and a copy
    of the manifest inside the release folder (used by a roll back)."""
    version = manifest['version']
    release = DEST / 'releases' / version
    if not all((release / n).is_file() for n in NAMES):
        raise SystemExit(f'Release {version} is not complete in {release}')
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + '\n'
    (release / 'release.json').write_text(text, encoding='utf-8')
    (DEST / 'release.json').write_text(text, encoding='utf-8')
    (DEST / 'sw.js').write_text(worker_js(version), encoding='utf-8')
    template = (SITE / 'scripts/game-page.html').read_text(encoding='utf-8')
    page = template.replace('__VERSION__', version).replace('__PUBLISHED__', manifest.get('publishedUtc') or manifest['preparedUtc'])
    (DEST / 'index.html').write_text(page, encoding='utf-8')
    (SITE / '.nojekyll').touch()


def prepare(source):
    """Copies the completed build and the preset dialogue into releases/<version>/ and points the entry at it."""
    source = pathlib.Path(source).resolve()
    inputs = build_inputs(source)
    snapshot = {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in inputs}
    version = hashlib.sha256(b''.join(p.read_bytes() for p in inputs)).hexdigest()[:16]
    release = DEST / 'releases' / version
    release.mkdir(parents=True, exist_ok=True)
    build = source / 'Build' / 'WebGL' / 'Build'
    npc = source / 'Tools' / 'npc-server'
    for name in NAMES:
        shutil.copyfile(build / name, release / name)
    public_npc = release / 'npc'
    public_npc.mkdir(exist_ok=True)
    shutil.copyfile(npc / 'canon.mjs', public_npc / 'canon.mjs')
    mock = (npc / 'providers/mock.mjs').read_text(encoding='utf-8')
    mock = mock.replace("process.env.NPC_MOCK_EARLY_PERSONAL === '1'", 'false')
    (public_npc / 'mock.mjs').write_text(mock, encoding='utf-8')
    schema = (npc / 'schema.mjs').read_text(encoding='utf-8')
    schema = re.sub(r"^import .* from 'node:[^']+';\r?\n", '', schema, flags=re.M)
    codes = []
    for line in (source / 'Assets/ScrapWorkshop/Fonts/hud_font.txt').read_text(encoding='utf-8-sig').splitlines()[1:]:
        try:
            code = int(line.split(' ')[0])
            if code > 0:
                codes.append(code)
        except ValueError:
            pass
    start = schema.index('const here = ')
    end = schema.index('const PUNCT = ', start)
    schema = schema[:start] + 'const glyphs = new Set(' + json.dumps(codes) + '.map(c => String.fromCodePoint(c)));\nfunction loadGlyphs() { return glyphs; }\n\n' + schema[end:]
    if 'node:' in schema or 'process.env' in mock:
        raise SystemExit('Server-only imports remain in browser dialogue assets')
    (public_npc / 'schema.mjs').write_text(schema, encoding='utf-8')
    commit = git('rev-parse', 'HEAD', cwd=source, check=False)
    dirty = git('status', '--porcelain', '--', *GAME_SOURCES, cwd=source, check=False)
    manifest = {'version': version, 'preparedUtc': now_utc(), 'dialogue': 'preset-mock-no-external-api',
                'source': {'commit': commit, 'uncommittedGameSources': bool(dirty)},
                'files': {n: {'bytes': (release / n).stat().st_size, 'sha256': hashlib.sha256((release / n).read_bytes()).hexdigest()} for n in NAMES}}
    write_entry(manifest)
    if any((p.stat().st_size, p.stat().st_mtime_ns) != snapshot[p] for p in inputs):
        raise SystemExit('Inputs changed while preparing. Wait for development work to finish, then run again.')
    return manifest


def current_manifest():
    p = DEST / 'release.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else None


def deployed_versions():
    """Versions the public entry has pointed at, newest first (from the history of release.json)."""
    seen = []
    for sha in git('log', '--format=%H', '--', 'games/scrap-workshop/release.json').splitlines():
        try:
            v = json.loads(git('show', f'{sha}:games/scrap-workshop/release.json'))['version']
        except (SystemExit, ValueError, KeyError):
            continue
        if v not in seen:
            seen.append(v)
    return seen


def history_manifest(version):
    """The root release.json as it was while `version` was public, from git history (newest such commit). Releases
    published before per-release manifests existed (e.g. 0d485cb91c3cccfa) only have this one."""
    for sha in git('log', '--format=%H', '--', 'games/scrap-workshop/release.json').splitlines():
        try:
            m = json.loads(git('show', f'{sha}:games/scrap-workshop/release.json'))
        except (SystemExit, ValueError):
            continue
        if m.get('version') == version:
            return m
    return None


def release_manifest(version):
    """The manifest of a release that can be put back in public: the copy in its folder, else the historical root
    manifest. The folder is restored from history if pruned, and every Unity file must match the manifest's length and
    SHA-256, with the three dialogue modules present. Raises SystemExit when the release cannot be used. The historical
    values (preparation time, game commit if recorded) are kept as they were; nothing is filled in from today."""
    restore_release(version)
    folder = DEST / 'releases' / version
    own = folder / 'release.json'
    manifest = json.loads(own.read_text(encoding='utf-8')) if own.is_file() else history_manifest(version)
    if not manifest or manifest.get('version') != version or set(manifest.get('files', {})) != set(NAMES):
        raise SystemExit(f'No usable manifest for release {version}')
    for name, f in manifest['files'].items():
        data = (folder / name).read_bytes()
        if len(data) != f['bytes'] or hashlib.sha256(data).hexdigest() != f['sha256']:
            raise SystemExit(f'Release {version}: {name} does not match its manifest')
    for module in ('canon.mjs', 'mock.mjs', 'schema.mjs'):
        if not (folder / 'npc' / module).is_file():
            raise SystemExit(f'Release {version}: dialogue module npc/{module} is missing')
    return manifest


def restore_release(version):
    """Brings back a release folder removed from the working tree, from the last commit that still had it."""
    folder = DEST / 'releases' / version
    if folder.is_dir() and all((folder / n).is_file() for n in NAMES):
        return
    rel = f'games/scrap-workshop/releases/{version}'
    last = git('rev-list', '-n', '1', 'HEAD', '--', rel)
    if not last:
        raise SystemExit(f'Release {version} is not in the repository history')
    has = git('ls-tree', '-r', '--name-only', last, '--', rel)
    git('checkout', last if has else last + '^', '--', rel)


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={'Cache-Control': 'no-cache', 'User-Agent': 'glorious-deploy-check'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()
