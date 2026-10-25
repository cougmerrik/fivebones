# Acceptance and verification checklist

## Unit tests — engine

- [ ] All eight hand categories correctly ranked; full house > straight > three-of-kind.
- [ ] Both straights recognized; duplicate faces not straight.
- [ ] Equal-rank hands use documented kicker comparison, including exact ties.
- [ ] 6-6-6-1-1 recognized order-independently as Widowmaker and loses at showdown to any non-Widowmaker, even weakest high bones.
- [ ] Widowmaker wins pot uncontested when every opponent folds; folded dice not revealed.
- [ ] Two or more remaining Widowmakers enter configured special adjudication, not normal full-house win.
- [ ] Exactly one reroll submission per active seat (including zero), only indices 0..4, cannot reroll again; broadcast count only.
- [ ] At most two raises in EACH betting round, correct small and big bet amounts, call/check legality, no negative balances.
- [ ] Underfunded seat cannot join hand / illegal bet rejected without money movement.
- [ ] Pot = sum of committed antes and bets until payout, no rake, total player money conserved.
- [ ] NPC scripted rolls validate die domain, private queue remains GM only, action override audited.
- [ ] Fixed dealer rotation and deterministic first actor after folds.

## API + security

- [ ] Player cannot create GM command / edit another seat / impersonate session.
- [ ] Snapshot/event payload has no unrevealed opponent dice, even for GM.
- [ ] Client dice/payout values ignored and rejected.
- [ ] Duplicate command ID produces one transaction and same result after retry.
- [ ] Stale expectedVersion handled without partial side effects.
- [ ] Reconnecting after wager/reroll returns accurate private snapshot, no extra reroll.
- [ ] Host restarts mid-session: room recovers (SQLite persistence).
- [ ] Room invite alone cannot grant GM access; joining seat cannot guess another seat token.
- [ ] Inactive/unknown room errors are readable, no user-facing stack trace.
- [ ] CSV ledger includes per-hand seat profit/loss and final totals, balances reconcile.

## Manual end-to-end

- [ ] GM + 5 player sessions and 1 NPC can join on localhost with independent browser contexts.
- [ ] Play 3 hands, fold, call, raise, stand pat, reroll 5, showdown and tie.
- [ ] One player disconnects during action; GM explicitly resolves, reconnect recovers.
- [ ] Player entering 125gp, losing 10gp and winning 20gp sees net +10gp and 135gp suggested final. Copy settlement works.
- [ ] Standalone UI remains functional without installed extension or Roll20 account.
- [ ] Extension loads unpacked in Chrome/Edge, launcher appears once on actual Roll20 game page (manual verification necessary).
- [ ] Overlay does not block Roll20 chat/map when minimized; moves/resizes and position persists on refresh; no console errors.
- [ ] Optional import of visible 2014 sheet name/GP works when DOM accessible; otherwise guided manual fallback. Verify NO network/cookie extraction and NO Roll20 data writes.
- [ ] Extension session and standalone tab can join same room and see synchronized state.
- [ ] Accessibility: keyboard reachability, dialog focus, readable contrast, reduced-motion setting.

## Required Codex output

Show command lines that were run; report number of passing tests; describe any test requiring user-run Roll20 UI. Do not report unperformed tests as passed. Track all MVP house-rule defaults in a README section.


## Queued automatic NPC rerolls

- [ ] GM can queue initial faces, unique zero-based selected slots, and matching replacements; invalid shapes/indices/counts reject atomically.
- [ ] Consecutive planned NPCs reroll/stand pat automatically once, in order; human and manual NPC turns wait for input and betting stays manual.
- [ ] Plans are GM-only, public counts are correct, loaded-slot replacement pairing is stable, and folded/removed/sitting-out seats behave correctly.
- [ ] Lost acknowledgments, reload/reconnect and server recovery cannot duplicate an automatic reroll; current plans survive future queue edits.


## Belwether quick joining

- [x] Player link and default extension panel retain name/GP/Dexterity with no manual room/invite entry.
- [x] DM flag alone cannot authorize control; the host key authorizes remembered server credentials.
- [x] Refresh and lost join responses recover the same seat without duplicate entry or changed balances/stats.
- [x] Concurrent fresh-session requests create one session; finished-session histories remain available behind unchanged links.
- [x] Built extension keeps player/DM credentials isolated from Roll20 page storage and leaves sheet values unchanged in the controlled browser test.
- [ ] Verify the updated extension and stable links in the actual Roll20 campaign and Edge after rollout.
