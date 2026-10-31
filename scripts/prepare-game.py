"""Publish only a completed Unity WebGL build and cost-free dialogue assets.

Usage: python scripts/prepare-game.py C:/path/to/ScrapWorkshop
This prepares files; it never builds Unity, commits, pushes, or calls an AI API.
"""
import hashlib
import json
import pathlib
import re
import shutil
import sys
from datetime import datetime, timezone

source = pathlib.Path(sys.argv[1]).resolve()
site = pathlib.Path(__file__).resolve().parents[1]
destination = site / 'games' / 'scrap-workshop'
build = source / 'Build' / 'WebGL' / 'Build'
names = ['WebGL.loader.js', 'WebGL.framework.js.unityweb', 'WebGL.data.unityweb', 'WebGL.wasm.unityweb']
inputs = [build / n for n in names]
npc = source / 'Tools' / 'npc-server'
inputs += [npc / 'canon.mjs', npc / 'schema.mjs', npc / 'providers' / 'mock.mjs', source / 'Assets/ScrapWorkshop/Fonts/hud_font.txt']
for p in inputs:
    if not p.is_file() or not p.stat().st_size:
        raise SystemExit(f'Missing build input: {p.name}')
log = (source / 'Logs/build_webgl.log').read_text(encoding='utf-8', errors='replace')
if 'SW_BUILD_RESULT Succeeded' not in log or log.rfind('SW_BUILD_RESULT Succeeded') < log.rfind('SW_BUILD_BEGIN'):
    raise SystemExit('The current Unity build has no success marker. Wait for it to finish.')
snapshot = {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in inputs}
version = hashlib.sha256(b''.join(p.read_bytes() for p in inputs)).hexdigest()[:16]
release = destination / 'releases' / version
release.mkdir(parents=True, exist_ok=True)
for name in names:
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
worker = """// Public prototype: preset dialogue, no external AI requests, no asset caching.
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
(destination / 'sw.js').write_text(worker, encoding='utf-8')
template = (site / 'scripts/game-page.html').read_text(encoding='utf-8')
(destination / 'index.html').write_text(template.replace('__VERSION__', version), encoding='utf-8')
manifest = {'version': version, 'preparedUtc': datetime.now(timezone.utc).isoformat(), 'dialogue': 'preset-mock-no-external-api', 'files': {n: {'bytes': (release/n).stat().st_size, 'sha256': hashlib.sha256((release/n).read_bytes()).hexdigest()} for n in names}}
(destination / 'release.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
(site / '.nojekyll').touch()
if any((p.stat().st_size, p.stat().st_mtime_ns) != snapshot[p] for p in inputs):
    raise SystemExit('Inputs changed while preparing. Wait for development work to finish, then run again.')
print(json.dumps({'version': version, 'bytes': sum((release/n).stat().st_size for n in names), 'path': str(destination)}))
