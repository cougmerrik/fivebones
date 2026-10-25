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

Each player installs their own copy. The panel finds Belwether automatically; enter name, starting GP and Dexterity, then click Join belwether. Website and extension saved sessions are separate. To recover an older manual room or an existing website seat, expand Other room or recovery → Open manual connection, then use its room ID and private recovery token in Resume a saved seat. Keep that token private to its owner.

The overlay should show Connected and the same roster/ledger as the website. Test a player turn and recovery after refreshing Roll20. API health and Roll20 CORS can be checked automatically; an actual Roll20 campaign and Edge still require manual verification.

## Belwether quick join

The extension now finds **belwether** automatically. Players open the Five Bones panel, enter character name, current starting GP and Dexterity, and click **Join belwether**. No room ID, invite code, or recovery-token copying is needed. The panel waits and updates automatically if the DM has not started a session. Saved player credentials reconnect to the same seat on refresh.

For the DM, click **DM access** once, enter the existing Railway `HOST_INVITE_SECRET` in **DM access key**, and click **Remember DM access**. The extension stores a separate DM credential in isolated extension storage; it does not save the host creation secret. Subsequent openings reconnect automatically as DM. **Switch to player** changes the remembered role; **DM access** returns to the remembered controller. Website and extension saved access remain separate.

A Roll20 editor URL with `room=belwether` opens the panel automatically. Add `isdm=1` to choose the DM flow, preserving any existing Roll20 query parameters (`&isdm=1` when there is already a `?`). The flag does not grant control: server-verified DM access is still required.

Stable standalone links:

- Player: `https://fivebonesweb-production.up.railway.app/?room=belwether`
- DM: `https://fivebonesweb-production.up.railway.app/?room=belwether&isdm=1`

After **End session**, the DM can choose **Start fresh belwether session**. The link stays the same, previous rooms and ledgers remain stored, and **Previous session summaries** shows finished campaign totals. Existing players can keep viewing the old summary, then click **Join new belwether session** and enter new character/gold/Dexterity details. New sessions do not reuse old balances automatically. Only the DM may create a fresh session, and a live session must be finished first.

For an older random-ID room, expand **Other room or recovery → Open manual connection**. A Roll20 URL with `manual=1` also selects the previous connection screen. Old rooms are not silently converted or erased when you first set up Belwether.

Anyone with the public Belwether link can request a new player seat, as intended for this private campaign. Existing seats still require their private credential to reconnect, and changing `isdm` never grants GM access.
