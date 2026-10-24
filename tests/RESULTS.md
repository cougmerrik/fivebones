# Verification report

Implementation completed through the standalone MVP and built MV3 overlay. This report distinguishes automated simulation from live Roll20/Edge verification.

## Passed

- `PYTHONPATH=server .venv/bin/pytest server/tests -q`: **38 passed**, one upstream Starlette/AnyIO deprecation warning. Covers all rank categories/kickers, Widowmaker permutations/exception/refund/uncontested outcomes, fixed-limit raises, betting legality, reroll count/index/turn rules, dealer order, ties/remainders, NPC authorization/privacy, 50 randomized hands with conservation after every action, the 125→135 GP example, API roles/redaction, hashed credentials, invite and seat limits, durable retries, stale versions, concurrent retry transactions, malformed authentication/origin rejection, CSV and deletion.
- `pnpm exec tsc`: passed.
- `pnpm build`: standalone and MV3 bundle passed; outputs `apps/web/dist` and `apps/extension/dist`.
- `docker compose config --quiet`: passed.
- `docker compose build`: both images built successfully.
- `docker compose up -d --no-build` and `.venv/bin/python tests/container_smoke.py`: passed against running containers, including an actual API process restart, identical private snapshot recovery, durable retry of an already-applied wager, authenticated CSV export, and deletion of the test room. `docker compose ps` confirms web/API are running at loopback ports 5173/8000.
- Multi-context browser acceptance passed (including clipboard copy): GM + five independent human contexts + NPC completed three hands. Exercises check/bet/raise/call, stand pat, reroll five, NPC Widowmaker, refresh recovery, closing an actor's page, explicit GM force-fold confirmation, reconnect to the same seat, and CSV totals summing to zero.
- Built MV3 Chromium smoke passed on a **simulated** `https://app.roll20.net/editor/` page: one closed Shadow DOM, initially minimized, keyboard position persistence, resize and unchanged fake sheet GP field. No live Roll20 account or sheet was accessed. The expanded targeted test also passed with an overlay human seat and standalone GM synchronized to the same live local API; extension session recovery after reload and absence of tokens in page localStorage were checked.

## Execution environment and commands

The environment provided `python3`, `uv`, Node 24 and Corepack, but no `python` or direct `pnpm` executable. Actual setup used:

```bash
UV_CACHE_DIR=/tmp/fivebones-uv uv venv .venv
UV_CACHE_DIR=/tmp/fivebones-uv uv pip install --python .venv/bin/python -r server/requirements.txt
COREPACK_HOME=/tmp/fivebones-corepack corepack pnpm install --store-dir /tmp/fivebones-pnpm
UV_CACHE_DIR=/tmp/fivebones-uv uv pip freeze --python .venv/bin/python > server/requirements.lock
PYTHONPATH=server .venv/bin/pytest server/tests -q
COREPACK_HOME=/tmp/fivebones-corepack corepack pnpm exec tsc
COREPACK_HOME=/tmp/fivebones-corepack corepack pnpm build
COREPACK_HOME=/tmp/fivebones-corepack CHROMIUM_EXECUTABLE=/home/merrik/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome corepack pnpm test
docker compose config --quiet
docker compose build
docker compose up -d --no-build
.venv/bin/python tests/container_smoke.py
docker compose ps
```

Dependency downloads needed network-enabled execution. API TestClient startup hung inside this environment's restricted sandbox before reaching application startup; running outside that restriction passed. Chromium and local listener tests likewise used network-enabled execution. Browser testing used an existing Chromium executable instead of downloading one. Initial browser failures found a missing accessible NPC selector label and test assumptions about turn changes at settlement/phase boundaries; these were corrected. Initial engine test fixture expectations were corrected for high-bones hands and insufficient funds after folding. The expanded overlay connection test initially encountered Chromium's public-origin-to-loopback restriction. A test-process-only browser flag resolved it; the final targeted overlay test passed. No unresolved automated scenario remains.

## Remaining manual gates and limitations

- Actual Roll20 game pages, real account embedding/CSP behavior and Edge unpacked installation require manual verification. Automated host-page simulation is not live Roll20 testing.
- Optional sheet importer is deferred: manual identity and GP entry works on both surfaces. No sheet DOM extraction is implemented.
- Public HTTPS/WSS with real DNS/certificates has deployment instructions but is not deployed to a public service here.
- The localhost extension integration test disables Chromium's LocalNetworkAccessChecks and WebSocket counterpart in its own test browser because the simulated HTTPS host calls a loopback API. Real overlay use should use a public HTTPS API. No extension manifest permission or production security setting was weakened.
- NPC betting is explicitly GM-controlled; automatic strategies, skills and tournaments remain deferred.
- Single API process/instance only. SQLite is durable; socket routing and rate limits are process-local. Retention is an explicit offline maintenance command.
- Snapshot frames contain sequenced public history rather than a separate incremental event stream.

Final outcomes: **38 Python tests, 2 passing browser scenarios, successful TypeScript/build checks, and a passing real-container restart smoke test**. The last browser scenarios passed across the full multiplayer run and the final targeted overlay run. No failed scenario remains unresolved. The app was left running at http://localhost:5173; stop it with `docker compose stop`. The container smoke emitted a WebSocket-library deprecation warning about its synchronous test connection helper; it did not affect results.

## Backgrounds and rules popup update

- Added the provided landscape/portrait images to both bundles, with orientation-based selection and local extension image resources.
- Removed the extra header copy and added a native, keyboard-accessible Hands & rules dialog with ordered hand examples, Widowmaker, play sequence, and current table house settings.
- `node node_modules/typescript/bin/tsc`: passed.
- `node node_modules/vite/bin/vite.js build apps/web && node apps/extension/build.mjs`: passed.
- `CHROMIUM_EXECUTABLE=/home/merrik/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome node node_modules/@playwright/test/cli.js test`: **3 passed**. Checks both images decode in the appropriate orientation, popup rankings and responsive sizing, Escape/focus restoration, modal operation inside the built extension, and the existing full multiplayer scenario.
- `docker compose build web`: passed. Updated web image restarted with `docker compose up -d --no-build`.

## Dexterity cheating and DM dice-edit update

The latest user clarification is authoritative: Dexterity only; loaded die has an exact 33% chance of five and applies immediately, with a private swap check and no DM approval gate. Other faces each have 13.4% chance. This feature explicitly amends the original no-human-dice-edit rule; ordinary commands still cannot supply arbitrary outcomes.

- `PYTHONPATH=server .venv/bin/pytest server/tests -q`: **51 passed**, one existing upstream deprecation warning. Added exact enumeration of all 500 loaded-die RNG buckets, private role projections, d20/Dex modifier boundaries, turn and per-hand limits, loaded-slot normal reroll/reset behavior, direct face changes, GM-only edits with reason and before/after audits, narrative actions/optional checks, validation, legacy score entry, durable retry behavior and public CSV redaction.
- `node node_modules/typescript/bin/tsc`: passed.
- `node node_modules/vite/bin/vite.js build apps/web && node apps/extension/build.mjs`: passed.
- Full browser run on new isolated ports: existing multiplayer, artwork/rules and built-extension scenarios passed. The new cheat scenario found missing accessible selector labels; after fixing those, `CHROMIUM_EXECUTABLE=/home/merrik/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome node node_modules/@playwright/test/cli.js test tests/browser/cheats.spec.ts` passed. **All four browser scenarios are passing across those runs.** The cheat scenario checks join-time Dexterity, immediate loaded action/private d20 notification, opponent WebSocket redaction, reload without repeat attempts, DM correction visible only to its owner, Other text plus DM-requested Dexterity roll/adjudication, chosen-face change and Hold captions only during REROLL.
- Browser tests now use ports **18000/15173**, their own SQLite database, and `/tmp/fivebones-e2e-extension`. They no longer replace the running application API or normal extension build.
- `docker compose build`: API and web images passed. Updated stack applied using `docker compose up -d --no-build` with the existing persistent volume.

Implementation conventions are recorded in README and spec/RULES.md: one optional cheat per hand; a loaded slot lasts for the current hand (including its regular reroll) and resets next hand; Change die applies immediately with a private Dexterity check; DM adjudication never auto-resolves success or detection. Direct GM edits are restricted to live, nonfolded hands and cannot alter settled history, winners, balances or payouts. No live Roll20 testing was performed for this update.
- Deployed-container smoke passed: temporary room joined with Dexterity scores, Loaded die applied immediately with a private Dexterity check, DM received the notification and made an audited dice edit, and the running production bundle contains the new controls. The verification room was deleted afterward; existing rooms were not modified.

## Top ledger, room panel and NPC Dexterity update

- Connection status is left-aligned. Compact ledger boxes directly beneath it display name, current gold and signed net; losses are red, gains bright green, and zero neutral. Full ledger/export remains available.
- The room panel has no duplicate title and defaults closed in player views (including reload), while the host can access its expanded invite controls. Removed the bottom footer.
- NPC seating now has independent starting GP and Dexterity fields. NPC private actions reuse the same server cheat engine, exact loaded-die odds, per-turn/per-hand limits and d20 + Dexterity modifier. Only the GM can trigger or read NPC cheats; actions are privately audited and idempotent.
- Human and NPC Dexterity is immutable after join/one-time initialization, including between hands. Legacy missing values can be initialized once under the documented authorization/phase checks.
- `PYTHONPATH=server .venv/bin/pytest server/tests -q`: **58 passed**, one existing upstream deprecation warning. Added NPC gold/score validation, atomic rejection, locked stats across all live/between-hand phases, GM-only NPC checks, redaction, audit, durable retry and legacy NPC initialization tests.
- `node node_modules/typescript/bin/tsc`: passed.
- `node node_modules/vite/bin/vite.js build apps/web && node apps/extension/build.mjs`: passed.
- `CHROMIUM_EXECUTABLE=/home/merrik/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome node node_modules/@playwright/test/cli.js test`: **5 passed**. New UI acceptance checks collapsed/expandable room controls, no duplicate title/footer, read-only Dexterity, valid/invalid custom NPC GP, NPC check modifier, private results, changing loss/gain ledger values and colors, persistence on reload, and narrow-screen layout. Existing cheating, rules/artwork, built-extension simulation and GM + five humans + NPC three-hand scenarios pass.
- `docker compose build`: both images passed. `docker compose up -d --no-build` applies the update using the existing SQLite volume.
- Live-container smoke passed after deployment: the UI serves ledger/NPC controls without the footer, a temporary NPC joined with 240.50 GP and Dexterity 18, and a GM-triggered loaded-die attempt produced a private check with modifier +4. The temporary verification room was deleted afterward.

## Title artwork, room status and End session update

- Replaced the visible text heading with the supplied `title.png`; retained its accessible Five Bones heading/alt text. Website, extension image resources and Docker build include the original asset.
- Connection status now sits at the right edge of the Connection & room summary, visible while the panel is collapsed. The ledger remains directly below this panel.
- Removed the unconditional “Complete the current hand first” confirmation copy. End session now gives a normal confirmation in LOBBY and READY_NEXT_HAND, preserves the final ledger, and is disabled during a live hand with phase-appropriate help text. Server rules already allowed ending an idle session; no backend rule change was needed.
- `node node_modules/typescript/bin/tsc`: passed.
- `node node_modules/vite/bin/vite.js build apps/web && node apps/extension/build.mjs`: passed.
- `CHROMIUM_EXECUTABLE=/home/merrik/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome node node_modules/@playwright/test/cli.js test`: **6 passed**. Checks the supplied title decodes in website/extension, right-aligned visible status inside a collapsed room, ledger placement, active-hand end guard, ending between hands, ending an empty lobby, cancelling confirmation and ended-state recovery after reload, plus all previous gameplay scenarios.
- `docker compose build web`: passed. Updated web container applied with `docker compose up -d --no-build web`; API/game rules and stored sessions are unchanged.

## Supplied dice artwork update

- Added a shared DieFace renderer mapping server values 1–6 to the original `pip1.png`–`pip6.png` files. Private-hand buttons, legally visible roster hands and rules examples now use the supplied art. Image styling preserves transparency and selected-button highlighting; only the reroll phase shows Hold/Reroll captions. Button labels retain die position/value and selection state for accessibility.
- PNG imports are bundled locally by Vite and the MV3 build. Existing scoped extension image resources cover the new files. Docker includes the six root assets. No server RNG, game rules, money, permissions or privacy projection changed.
- `node node_modules/typescript/bin/tsc`: passed.
- `node node_modules/vite/bin/vite.js build apps/web && node apps/extension/build.mjs`: passed.
- Full browser suite: cheating/reroll interaction, built-extension loading, session ending and multiplayer scenarios passed. Two new mapping checks initially assumed hashed production filenames and were corrected to accept Vite development URLs too. Targeted `... node node_modules/@playwright/test/cli.js test tests/browser/layout.spec.ts tests/browser/rules.spec.ts`: **2 passed** afterward. All **six browser scenarios** pass across those runs; no unresolved failures remain. Checks decode every face, validate value/file mapping, verify actual hand images and extension PNG loading, and cover narrow-screen layout.
- `docker compose build web`: passed; `docker compose up -d --no-build web` applies the updated web image. Existing game data and the API remain unchanged. No live Roll20 session testing was performed.

## Compact layout and phase tracker update

- Centered roster dice groups. Added the six-stage Ante → Betting 1 → Reroll → Betting 2 → Showdown → Next Hand tracker with accessible `aria-current="step"` highlighting and a centered hand number below it. The tracker follows authoritative phases; Ante/ordinary showdown remain atomic operations, and ADJUDICATION highlights Showdown.
- Reduced the title by 25% (450px maximum, 75% width on narrower surfaces), removed its divider, moved Hands & rules to the game area's top right, and moved Connection & room below private actions. Ledger cards remain at the top.
- Added a compact wide-screen layout with private actions beside the table, tighter table/card spacing, shorter inline help and paired cheat fields. The full rules remain in the dialog. App-container queries stack narrow app/extension panels without horizontal overflow, and growing private sidebars scroll independently.
- `node node_modules/typescript/bin/tsc`: passed.
- `node node_modules/vite/bin/vite.js build apps/web && node apps/extension/build.mjs`: passed.
- Full browser run: six prior scenarios passed; the new phase scenario exposed a pre-existing missing accessible name for the NPC script textarea. Added an explicit label, then ran `... node node_modules/@playwright/test/cli.js test tests/browser/phases.spec.ts tests/browser/layout.spec.ts tests/browser/overlay.spec.ts`: **3 passed**. All **seven browser scenarios** pass across those runs. New checks cover six-step ordering, highlighted ante/betting/reroll/paused Showdown/Next Hand, centered hand and roster images, room below private actions, title and cheat controls simultaneously in a 1280×720 viewport, 450px title sizing, removed divider, and no horizontal overflow in 700px/340px extension panels. Scripted NPC Widowmakers use the existing authorized GM controls; no gameplay rule or RNG change was introduced.
- `docker compose build web`: passed. Applied with `docker compose up -d --no-build web`; the API and persistent game state are unchanged. No live Roll20 session testing is claimed.

## GitHub / Railway production preparation (2026-10-23)

Implemented root `/web`, `/server`, `/extension`, `/docs` layout; shared packages preserved. DM notification headings are 13px, body text 12px, the generic DM introduction is removed, and Hands & rules matches the selected phase chip. Added PostgreSQL DATABASE_URL persistence with room row locks, SQLite development compatibility, production configuration guards, PORT-aware startup, readiness/liveness, independent exact socket origins, public API/WSS build variables, extension ZIP packaging, independent Docker/Railway configs, and GitHub Actions checks. Deployment steps are in `RAILWAY_DEPLOY.md`.

Observed verification:

- Before the final documentation/configuration refinements, the expanded Python suite passed **73 tests** against SQLite and real PostgreSQL 16.8. These cover rules, multiplayer sessions, role privacy, idempotent retries, origin validation and health behavior. One upstream Starlette/AnyIO deprecation warning remains.
- The full Chromium browser run completed successfully (`test-results/.last-run.json` reports passed): seven scenarios cover private actions, layout, extension simulation, phases, rules, session ending and multiplayer gameplay. Added notification-size and phase/rules-size assertions; final browser rerun status is recorded below if completed.
- Latest pure engine run: **33 passed**. Latest deployment validation subset: **4 passed** (production settings, origin parsing, startup port and URL selection).
- Latest TypeScript typecheck: passed.
- Public endpoint checks: **12 passed**, including secure WSS derivation and rejection of insecure/credential-bearing endpoint settings.
- Latest `pnpm build` (using a temporary local pnpm launcher because the environment's global pnpm shim is restricted): **passed**, producing the Vite production site, unpacked extension and ZIP. ZIP integrity/manifest/contents: passed, 11 bundled files, storage permission only. This artifact uses local development endpoints; rebuild with the Railway API URL before distribution.
- Railway config field names checked against the downloaded official Railway schema, including dynamic Dockerfile paths, health checks, single replica, deployment drain and app sleeping settings. This is a field check, not full schema validation.
- First `docker compose build` reached dependency installation but the frontend's npm downloads timed out inside Docker. Subsequent Docker access checks could not run because the automatic permission reviewer timed out twice. Therefore the final Docker images/runtime/restart smoke are **not verified** in this revision. Earlier successful Docker checks above refer to previous revisions.
- A new transactional SQLite-to-PostgreSQL migration integration test was added after the 73-test run; its final result is recorded below if a rerun completes. Migration was not run on the user's game data.

Manual gates: commit/push to GitHub and observe hosted CI; create Railway PostgreSQL and two services, set their root/config paths and variables, allocate domains, configure backups, and run the deployed HTTPS/WSS/restart acceptance steps. No GitHub push, Railway deployment, live Roll20, or Edge test has been performed. Existing local game containers/data were not replaced during these checks.

Final verification constraint: the requested expanded PostgreSQL/browser rerun also could not start because automatic permission approval review exceeded its deadline. The new migration integration case therefore remains unrun locally. Latest pure configuration tests still pass (4 passed); TypeScript passes after isolating browser-test environment variables from any production shell settings.

Additional completed build check: Vite and MV3 builds with explicit HTTPS/WSS example domains passed, and generated JavaScript/manifest contained those secure endpoints. Default local web output was rebuilt afterward. The final PostgreSQL rerun was retried once and permission review again timed out; the migration case remains unrun locally. GitHub CI now also builds both Docker images and exercises configurable ports, PostgreSQL-backed authenticated WebSockets, an actual API container restart, durable wager retry, and cleanup using test-only credentials. These new hosted steps have not yet run.

## Live table participation, GM controls and session summary (2026-10-24)

Implemented:

- Left-aligned blue/purple next-hand participation toggle. Preferences survive reload and do not alter an active hand. Server eligibility checks require at least two opted-in, funded, nonremoved entrants. Old room seats default to opted in.
- Per-seat GM removal/restoration. A live removal folds any target (including a noncurrent seat), advances normally and retains committed wagers, balances, credentials and ledger history. Removed seats cannot opt themselves back in; restoring affects future hands only. All-Widowmaker adjudication must be resolved before removing a seat.
- Reusable NPC templates for name, opening GP and Dexterity, persisted across rooms in browser localStorage or isolated extension storage. Loading fills the seating form; the GM still submits the server-authorized seating command. Templates do not copy live balances, private dice, scripts or credentials.
- Durable server-generated last-public-turn recap above the turn indicator. Private cheats/checks/queued faces do not update or appear in this field.
- Main-area finished-session summary with opening/final gold, signed net, copyable text and GM CSV download.
- In-app NPC queue instructions and JSON example, remaining queue count, plus detailed documentation in docs/GAMEPLAY.md. Queue validation rejects malformed structures; an opted-out NPC does not consume a queue entry.

Actual verification:

- `PYTHONPATH=server .venv/bin/pytest server/tests -q`: **79 passed, 1 skipped** (migration case intentionally skipped for SQLite), one existing upstream Starlette/AnyIO warning.
- The same suite with the isolated `TEST_DATABASE_URL`: **90 passed, 1 skipped** across SQLite and PostgreSQL 16.8. This now includes a successful PostgreSQL migration test as well as participation/removal authorization, atomic rejection, out-of-turn removals in all three live phases, money conservation, adjudication guard, legacy defaults, queue preservation, private-action redaction, durable retries and reconnect recovery.
- TypeScript: passed. Endpoint contract checks: **12 passed**.
- Browser acceptance: the initial full run passed six existing scenarios. Updated the empty-room test to expect Start next hand to remain disabled until two eligible seats exist; its targeted rerun passed. The new feature scenario passed after adding the remaining-queue hint and an explicit accessible name to the populated preset selector. **All eight browser scenarios pass across these runs**, including GM + five humans + NPC over three hands and the simulated built MV3 overlay. New checks cover opt-out reload, distinct left-side toggle, current-hand continuity, removal/restoration, private-cheat recap exclusion, saved presets across reload and new rooms, queue instructions, and finished summary for GM/player with GM-only CSV.
- Production website and extension builds with the live public HTTPS/WSS API endpoints passed. Extension ZIP integrity, feature strings, endpoint and storage-only permissions verified. Final rebuilt outputs are ignored build artifacts, not committed source.

No live room was modified, and no Railway deployment or GitHub push was performed. Deploy API and web before reloading the updated extension. Presets are local to each browser/extension installation rather than synchronized between devices; live game state and all balances remain server-authoritative. Live Roll20/Edge acceptance of this feature update remains manual.
