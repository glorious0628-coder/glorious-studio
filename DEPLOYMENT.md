# ScrapWorkshop deployment verification

Prepared on 2026-10-31 from a successful Unity WebGL build (`SW_BUILD_RESULT Succeeded`, 0 errors). Build release: `0d485cb91c3cccfa`, 16,609,092 bytes across the four Unity artifacts.

Local static-server verification, headless Chrome, no foreground windows:

- 28/28 game steps: WebGL startup in Korean, yard/workshop/shop switches, Min opening dialogue, purpose choice and response, return to yard, attack input.
- The game used the browser preset provider (`source=mock`), with 0 external AI requests. No local NPC backend was running for these checks.
- Final run: no browser errors, exceptions or warnings reported by the driver.
- 7/7 homepage steps: existing Halo & Horns content, new playable-game link, Korean toggle, and 390px layout without horizontal overflow.
- Generated public files scanned for Anthropic/GitHub credential patterns: 0 matches.
- Original Unity working files and other developers' changes were left untouched.

These checks establish that the prepared static deployment works locally. Live-domain checks remain required after GitHub authentication and push; a completed upload must not be inferred from this record. Play feel, actual sound listening, and user fun evaluation were not performed.
