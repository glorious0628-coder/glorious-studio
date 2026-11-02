// Public prototype: preset dialogue, no external AI requests, no asset caching.
import { mockTurn } from './releases/ec2bec52fb940900/npc/mock.mjs';
import { normalize } from './releases/ec2bec52fb940900/npc/schema.mjs';
import { NPCS } from './releases/ec2bec52fb940900/npc/canon.mjs';
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
