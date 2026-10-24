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
