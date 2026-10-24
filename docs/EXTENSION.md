# Browser extension

The extension mounts the shared React interface in an isolated, closed Shadow DOM on Roll20 editor pages. It requests only local storage permission. Manual player identity and gold entry work without inspecting Roll20 sheets or authentication.

Build an unpacked directory and distributable ZIP from the repository root:

```bash
VITE_API_BASE_URL=https://YOUR-API-DOMAIN \
VITE_WS_BASE_URL=wss://YOUR-API-DOMAIN \
pnpm build:extension
```

Use `extension/dist/` with Chrome/Edge **Load unpacked**. Distribute `extension/fivebones-extension.zip`; recipients extract it and load the folder containing `manifest.json`. Refresh an editor page after installing/updating. This is not a Railway service. Its public API endpoint must match the standalone website's backend and be allowed by the backend's exact Roll20 CORS/WebSocket origins.

Without exported endpoint variables, the build points at localhost:8000 for development. Such a build is not the production distribution. Endpoint changes require a rebuild and player reload. Hosted Roll20/Edge behavior is a manual acceptance step; the browser suite exercises the packaged extension on a controlled origin.

See [RAILWAY_DEPLOY.md](../RAILWAY_DEPLOY.md) for the complete service and domain setup.

Before moving an unpacked extension to a different directory, save seat recovery tokens: Chromium may assign a new unpacked extension identity when its path changes. Resume seats explicitly if local extension storage is no longer available.

## Current Railway deployment

Build for the campaign API (verified 2026-10-24):

```bash
VITE_API_BASE_URL=https://fivebonesapi-production.up.railway.app \
VITE_WS_BASE_URL=wss://fivebonesapi-production.up.railway.app \
pnpm build:extension
```

Load `extension/dist` locally, or extract `extension/fivebones-extension.zip` and load the extracted folder containing `manifest.json`. In Chrome use `chrome://extensions`; in Edge use `edge://extensions`. Enable Developer mode, choose Load unpacked, then refresh the Roll20 game editor. Click the bottom-right Five Bones launcher.

Each player installs their own copy. Join with the room ID and invite code. To use an existing GM/player seat from the standalone website, copy its room ID and private recovery token into Resume a saved seat inside the overlay; website and extension saved sessions are separate. Keep the token private to its owner.

The overlay should show Connected and the same roster/ledger as the website. Test a player turn and recovery after refreshing Roll20. API health and Roll20 CORS can be checked automatically; an actual Roll20 campaign and Edge still require manual verification.
