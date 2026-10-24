# Product and UX specification

## Audience / setting

Private LW5 Amber Forest campaign with 5 players. Fantasy tavern Five Bones tables in Bellwether and possibly a riverboat tournament. Desktop-first, low-friction for friends. No real-money play.

## Surfaces

A. Standalone website: primary, supported experience, desktop browser URL. B. Chrome/Edge MV3 extension: optional overlay inside an open Roll20 game, showing exact same React application and connecting to same Five Bones service. Optional sheet import is read only.

## Core user flow

- GM opens app, creates room, picks stake preset / GM-configurable rule defaults, receives invite code/link, and starts seat management.
- Player joins by link, chooses character display name, enters their current GP or optionally imports visible Roll20 2014 sheet values. No Roll20 account/access is sent to server.
- GM assigns an NPC seat, optionally preloads GM-only dice. Seats view other players' public statuses and wagers, but never their dice until showdown.
- Table starts: ante, hidden dice roll, fixed-limit betting, exactly one reroll selection, second betting, showdown, payouts. Show public dice only for eligible showdown participants.
- Player ledger panel displays starting GP, current table balance, committed bet and net P/L. At session end, each player copies a settlement line and manually updates the Roll20 character sheet.
- GM can export CSV and readable summary of all hands/transactions and per-player net amounts.

## Overlay specifics

- One extension-added 'Five Bones' launcher in a low-impact corner of Roll20 viewport, shadow-root CSS scoped, fixed/z-index controlled, draggable/resizable panel, minimize, close, optional theme scale, keyboard accessible, preserves position in extension local storage.
- Never cover chat/map by default: start minimized or in small right-side position. No interference with pointer events outside panel. Avoid global keyboard shortcuts while Roll20 inputs are active.
- App can be run without extension. Extension disconnect/reload returns to last table safely.
- Optional 'Import name + GP from open character sheet' button looks for `input[name="attr_character_name"]`, `input[name="attr_gp"]`; if names are not exposed or iframe is isolated, show precise human-readable manual fallback. Only perform an explicit read after user's action.
- Extension should not require Roll20 API privileges, API/mod scripts, account cookies or tabs/history/unrelated site permissions.
- In an isolated content script, use `MutationObserver` only as needed; avoid DOM polling and unrelated sheet text extraction. `all_frames` only if necessary after testing, frame results communicated via minimal message passing. Prefer a small top-frame-only MVP with manual entry to keep host permissions minimal.

## UI anatomy

Header: room / seat / connection state / minimize. Table: turn indicator, seats with commitments, pot, dice with accessible values and held state, current action controls and phases. Footer tabs: Hand Log / Session Ledger / Table Settings (GM only). GM-only controls: seating, start next hand, table stakes, scripted NPC queue, settle/export. Show explicit status on disconnected client, rejected bet, and showdown.

## Usability / accessibility

Keyboard control of dice and actions, visible focus, contrast, reduced-motion animations, readable at 1280x720 overlay, no animations required to understand the result, clear confirmation for ending session or GM-forced fold. No reliance on sound or color alone.

## Scope guardrails

No voice/video, Roll20 token control, character sheet edits, roll chat injection, platform automation, monetization, real funds, or initial tournament bracket UI. Preserve future extension points for skill actions/tournament.
