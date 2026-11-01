# ScrapWorkshop web game

Game entry: https://glorious.ai.kr/

ScrapWorkshop prototype: https://glorious.ai.kr/games/scrap-workshop/

On 2026-11-01 the user requested this domain contain only ScrapWorkshop. The root now redirects straight to the game. The old studio/Roblox landing page and its unused image/font assets have been removed from the current site. The separate Roblox game project is unaffected. Do not restore the old landing page or add a back link to it.

GitHub Pages publishes the static files on `main` using the repository's existing Pages configuration; `CNAME` retains the custom domain. `.nojekyll` serves the game artifacts as-is.

## Updating the game (checked deploy)

The user approved (2026-11-01) deploying every checked game update to this site without asking again. That approval does not cover paid API calls, or generating or applying art before its own approval.

When a finished change unit to game code or approved art is committed in the game repo, its checks pass and a Unity WebGL build has succeeded (not after every edit; no Unity build for documentation-only changes):

```powershell
python D:/Game/Web/publishing/glorious-studio/scripts/deploy-game.py
```

The script runs, and stops at the first failure:

1. Preflight: one deploy at a time (`.deploy.lock`), `gh` logged in, this checkout clean on `main` and up to date, no Unity process with the game project open, no uncommitted game sources (`Assets`, `Packages`, `ProjectSettings`, `Tools/npc-server`), and no game source newer than the build.
2. Prepare (`gamesite.prepare`, also `prepare-game.py`): the four Unity files and the preset dialogue go to `games/scrap-workshop/releases/<version>/` (version = content hash). `release.json` records the files' SHA-256, the game commit and the publish time. The newest three releases stay in the site; older ones remain in git history.
3. Local check: a local server, then headless Chrome with `deploy-smoke.json` (game flow) and `homepage-smoke.json` (root entry), using `Tools/cdp/drive.mjs` from the game. The page must run the new release. On failure the site files are put back and nothing is pushed.
4. Commit and push to `main`.
5. GitHub Pages: waits for `pages/builds/latest` to report `built` for that commit.
6. Live check: the live `release.json` shows the new version, the four files match byte for byte, and the same two smoke runs pass on `https://glorious.ai.kr/`.
7. If step 5 or 6 fails, it rolls the entry back to the previous release and pushes that (checked the same way).

`--dry-run` stops after the local check and puts the files back. `--allow-same-build` redeploys page or tool changes with the same build. Results go to `D:/Game/Web/publishing/checks/<time>-<version>/`; every deploy appends a line to `D:/Game/Web/publishing/deploy-history.jsonl`.

**Roll back** (no Unity build needed):

```powershell
python D:/Game/Web/publishing/glorious-studio/scripts/rollback-game.py --list
python D:/Game/Web/publishing/glorious-studio/scripts/rollback-game.py               # the release before the current one
python D:/Game/Web/publishing/glorious-studio/scripts/rollback-game.py --to <version>
```

A pruned release is restored from git history. `git revert <deploy commit>` and a push also works.

**Stale files:** Unity files never change in place (new folder per build). The game page reads `release.json` past every cache, so a page cached before a deploy still opens the newest build; the version baked into `index.html` is only a fallback. The dialogue service worker is registered as `sw.js?v=<version>` with `updateViaCache: 'none'`, installs at once and takes over. Nobody has to clear browser data. A tab left open during a deploy shows a notice with the new deploy time and a reload button; it is never reloaded by force (progress is not saved). The page header shows the public version and the deploy time in Korean.

No Unity project, personal planning documents, logs, credentials, environment files, server configuration or API keys are published. `git` and `gh` use the login already on this PC; never put a token in a file.

## Public dialogue mode

GitHub Pages cannot run the local Node/Claude API server. This public prototype uses the project's existing deterministic mock dialogue, adapted into browser modules. A module service worker handles **only** same-scope NPC POST requests; it does not cache assets, intercept other sites, or contact Anthropic. NPC purpose, allowed choices, emotions and memory rules still come from the game and existing dialogue normalization. The page and game identify this as preset/mock dialogue.

Local development with the real Claude provider is unaffected. Enabling real AI on the public website requires a separate server-side deployment with protected credentials and usage limits. Do not add an API key to the browser or this repository.

## Prototype limitations

- PC keyboard controls; no touch controls.
- Korean start, English available with L.
- Refresh resets progress; no persistent save or offline progression.
- Temporary world art; this deployment does not establish play feel, sound quality or fun.

The Unity project lives separately at `D:/Game/Web/ScrapWorkshop`. This checkout is at `D:/Game/Web/publishing/glorious-studio` and tracks the game entry, prepared game artifacts and repeatable publishing tools.
