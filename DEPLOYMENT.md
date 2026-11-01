# ScrapWorkshop deployment verification

Prepared on 2026-10-31 from a successful Unity WebGL build (`SW_BUILD_RESULT Succeeded`, 0 errors). Build release: `0d485cb91c3cccfa`, 16,609,092 bytes across the four Unity artifacts.

Local static-server verification, headless Chrome, no foreground windows:

- 28/28 game steps: WebGL startup in Korean, yard/workshop/shop switches, Min opening dialogue, purpose choice and response, return to yard, attack input.
- The game used the browser preset provider (`source=mock`), with 0 external AI requests. No local NPC backend was running for these checks.
- Final run: no browser errors, exceptions or warnings reported by the driver.
- 7/7 homepage steps: existing Halo & Horns content, new playable-game link, Korean toggle, and 390px layout without horizontal overflow.
- Generated public files scanned for Anthropic/GitHub credential patterns: 0 matches.
- Original Unity working files and other developers' changes were left untouched.

## Live deployment

Published commit `e524ee1` to the existing `main` branch. GitHub Pages reported `built` with no build error. The existing domain and Pages source (`main`, `/`) were preserved.

- https://glorious.ai.kr/ — homepage play link and existing content verified; 7/7 headless checks passed, including the Korean toggle and mobile-width layout.
- https://glorious.ai.kr/games/scrap-workshop/ — HTTP 200; the same 28/28 game checks passed against the public HTTPS URL. Korean startup, all three spaces, Min's portrait/dialogue, a purpose choice and response, and return to the yard were verified.
- All four Unity files were downloaded from the public domain: byte lengths and SHA-256 hashes match `release.json`.
- Public game startup took 6.4 seconds in this one automated run; this is not a performance average. No browser errors, exceptions or warnings were reported. The game reported preset/mock dialogue and 0 external AI requests.
- The public Min dialogue screenshot was visually inspected. Screenshot and raw test reports remain in the local publishing checks folders, outside this public repository.

Play feel, actual sound listening, and user fun evaluation were not performed. No real Claude API was called during this deployment.

## 2026-11-01: game-only entry

The user requested removal of the former game/studio homepage so this domain opens only ScrapWorkshop. The root entry now redirects straight to `/games/scrap-workshop/`. The former landing-page HTML and its 19 dedicated image/font files are removed from the current site. Its Git history remains available; the separate Roblox project is untouched.

The game page and its generation template no longer link back to the former homepage. The domain configuration, prepared dialogue service worker and published Unity release are unchanged. No new AI images or Claude API calls were made.

Local headless verification: 7/7 root-entry checks (redirect, Korean game load, absence of old content/back link, 390px layout) and 28/28 game-flow checks (roles, Min dialogue and choice, return to yard, attack). `scripts/homepage-smoke.json` now tests direct game entry rather than the removed studio landing page.

## 2026-11-01: checked deploy flow and first deploy with it

The user approved deploying every checked game update to this site without asking each time (not paid API calls,
not art before its own approval). `scripts/deploy-game.py` now runs preflight, prepare, local check, push, GitHub Pages
and the live check in one go and rolls back on a failed live check; `scripts/rollback-game.py` points the site at an
earlier release. See README.

First run, release `2fec2c230a50b027` from game commit `3d1a53b` (silhouette fix, local server Content-Length, Ieum
craft test A reduced prototype; previous public release `0d485cb91c3cccfa`), site commit `c5681f9`:

- Dry run first (local only): 28/28 game flow, 7/7 root entry; the site files were put back.
- Local check: 28/28 and 7/7, the page ran the new release.
- GitHub Pages reported `built` for `c5681f9` about 30 s after the push.
- Live: `release.json` showed the new version; the four Unity files matched byte length and SHA-256; 28/28 game flow
  and 7/7 root entry on https://glorious.ai.kr/. The craft-test steps (231, debug stock) also passed on the live game.
- The game page header shows the public version and the deploy time in Korean. The root still opens the game
  directly (game-only entry kept).

Automated input only; no player feel, listening or fun evaluation. No Claude API call. Each deploy adds about 16 MB of
Unity files to the git history (the site keeps the newest three releases; older ones stay in history for roll back).
