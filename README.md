# ScrapWorkshop web game

Game entry: https://glorious.ai.kr/

ScrapWorkshop prototype: https://glorious.ai.kr/games/scrap-workshop/

On 2026-11-01 the user requested this domain contain only ScrapWorkshop. The root now redirects straight to the game. The old studio/Roblox landing page and its unused image/font assets have been removed from the current site. The separate Roblox game project is unaffected. Do not restore the old landing page or add a back link to it.

GitHub Pages publishes the static files on `main` using the repository's existing Pages configuration; `CNAME` retains the custom domain. `.nojekyll` serves the game artifacts as-is.

## Updating the game

Finish and verify the Unity WebGL build in the separate ScrapWorkshop working folder first. Do not run a second Unity build during another developer's build.

```powershell
python scripts/prepare-game.py C:/path/to/ScrapWorkshop
python -m http.server 8177 --bind 127.0.0.1
```

Open `http://127.0.0.1:8177/games/scrap-workshop/` or use the project's headless CDP driver and `scripts/deploy-smoke.json`. Check the prepared game, the homepage link, and `git diff` before committing and pushing to `main`. Publishing is an explicit operation; the preparation script never pushes.

`prepare-game.py` copies only the completed WebGL loader, framework, data and WASM, plus the existing preset NPC dialogue and its normalization rules. Artifacts live under a content-derived release path; `release.json` records SHA-256 checksums. Keep older release folders while open tabs may still use them. No Unity project, personal planning documents, logs, credentials, environment files, server configuration or API keys are published.

## Public dialogue mode

GitHub Pages cannot run the local Node/Claude API server. This public prototype uses the project's existing deterministic mock dialogue, adapted into browser modules. A module service worker handles **only** same-scope NPC POST requests; it does not cache assets, intercept other sites, or contact Anthropic. NPC purpose, allowed choices, emotions and memory rules still come from the game and existing dialogue normalization. The page and game identify this as preset/mock dialogue.

Local development with the real Claude provider is unaffected. Enabling real AI on the public website requires a separate server-side deployment with protected credentials and usage limits. Do not add an API key to the browser or this repository.

## Prototype limitations

- PC keyboard controls; no touch controls.
- Korean start, English available with L.
- Refresh resets progress; no persistent save or offline progression.
- Temporary world art; this deployment does not establish play feel, sound quality or fun.

The Unity project lives separately at `D:/Game/Web/ScrapWorkshop`. This checkout is at `D:/Game/Web/publishing/glorious-studio` and tracks the game entry, prepared game artifacts and repeatable publishing tools.
