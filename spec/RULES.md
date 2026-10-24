# Five Bones game rules — canonical decisions and documented gaps

This is a fantasy **five six-sided-dice poker** game, not standard poker and not a skill-contested outcome system. Ordinary rolls remain server-authored. The user-authorized private cheating update below is an explicit exception to the original no-dice-manipulation rule.

## CONFIRMED gameplay

1. Seats ante the fixed table ante to enter a hand.
2. Each active seat secretly throws five fair d6. NPC may use a GM-prepared predetermined starting roll and reroll replacement sequence, with GM-only audit trail.
3. First fixed-limit betting round.
4. Every remaining active seat has a single reroll opportunity: select any 0–5 of their five dice to reroll (including standing pat). The **number** of rerolled dice is public; their face values and choices are private until showdown. Do not offer repeated rerolls.
5. Second fixed-limit betting round.
6. Remaining seats reveal at showdown. Best ranked hand wins the pot, subject to the cursed Widowmaker exception. Folded hands stay secret.
7. Dealer rotates each hand; ante and action order follow the dealer under a documented MVP convention.
8. Fixed-limit tables: **1sp/2sp**, **1gp/2gp**, **10gp/20gp** (small bet / big bet); max **two raises per betting round**. Define whether raises are capped per round total, not per player (default: per round total).
9. **No all-ins and no side pots.** Seats without adequate funds for required action must not enter a hand or must take a legal fold/check path. State behavior before ante.
10. One optional private cheat action per seat per hand, on its turn. The GM performs NPC cheats using the same engine and that NPC’s Dexterity. Loaded die and Change die apply immediately and notify the DM with a server-rolled Dexterity check. Other sends a description for out-of-game DM adjudication; a check is optional and DM-triggered. See README for the implemented campaign amendment. Other named skill systems remain deferred.
11. Riverboat tournament may use predetermined NPC hands; advancement may depend on **total winnings**, not simply hand victories. This is future scope, not required MVP.

## Rank order (high to low)

1. Five of a kind
2. Four of a kind
3. Full house
4. Straight (five consecutive dice: 1-2-3-4-5 or 2-3-4-5-6)
5. Three of a kind
6. Two pair
7. One pair
8. High bones (all other hands)

**Widowmaker:** exactly the multiset **6,6,6,1,1** *automatically loses at showdown against any other hand*, despite normally forming a full house. It **may win by everyone else folding**, because no showdown occurs. Never allow it to win a tied showdown against another hand, including another Widowmaker. If only Widowmakers remain, apply a documented GM adjudication / configured special default, not an unearned ordinary rank victory.

## Explicit MVP house conventions (not previously confirmed; editable)

- Ante equals the **small bet** for the selected table, and must be affordable upfront.
- First betting round uses small bet increment; second uses big bet increment.
- Standard clockwise action from seat left of dealer; each betting round starts to dealer's left among active seats.
- Actions: check (when no amount to call), bet (when no prior bet), call, raise (up to two raises *total in round*), fold. Round ends when all remaining seats have acted and equalized commitments or folded.
- A legal raise requires sufficient game balance; no partial calls, no credit, no negative balances. If underfunded, fold (or check if no call outstanding).
- Reroll stage proceeds in seat order; public count exposed only after selection submitted; reveal only at showdown.
- Tie resolution among best non-Widowmaker hands uses lexicographic rank kickers (see next section), then equal winners split pot into integer copper pieces; remainder goes to earliest qualifying winner clockwise from dealer. Document and test. This is an adjustable house rule.
- A player disconnected on their turn pauses action; GM may force-fold after an explicit confirmation, without inventing a timer-based action.
- For a showdown of all Widowmakers, flag GM adjudication and pause settlement (default); for one surviving player prior to showdown, uncontested pot is theirs even if holding Widowmaker.

## Tie-break convention (proposed, adjustable)

- Five-kind: face of five.
- Four-kind: quad face, then kicker.
- Full house: triple face, then pair face.
- Straight: highest die (6 high beats 5 high).
- Trips: trip face, then remaining dice descending.
- Two pair: higher pair face, lower pair face, kicker.
- Pair: pair face, remaining dice descending.
- High bones: five dice descending.
- Widowmaker is flagged separately and loses to any non-Widowmaker at showdown even if other hand ranks below full house.

## NPC behavior

- GM can supply a queued set of up to 10 explicit initial 5d6 arrays and optional replacement dice stream per NPC, for scenario scripting. Alternatively server RNG.
- Validate each die as integer 1..6 and cap sequence length. Never broadcast unrevealed NPC values.
- NPC betting strategy should be understandable (tight, loose, bold), but GM can override NPC actions only while explicitly acting in an authorized GM role. The separate, user-authorized DM dice-change action can edit current active dice with a private reason/audit record; completed history cannot be changed.

## Monetary accounting

- Store all balances, antes, commitments, pot and payouts in integer **copper pieces (cp)**; 1 gp = 100 cp, 1 sp = 10 cp. Default UI displays denomination selected by table with equivalent GP where useful.
- Keep *in-game* balance in service; record separately the **Roll20 starting GP snapshot**. Do not auto-edit Roll20 balances.
- Define net settlement as payouts minus buy-ins/antes/bets across the session, not the sum of winning pots alone.
- Treat stakes as fictional in-game money only.

## User-authorized cheating amendment

Dexterity only: check = server d20 + floor((Dexterity − 10) / 2). Loaded die immediately replaces one chosen die using exactly 33% for face 5 and 13.4% for each other face. The swap notifies the DM; it never waits for DM approval. The selected slot stays loaded for that hand, including the normal reroll, then resets. Change die sets the chosen face immediately and reports its Dexterity check privately. Other waits for narrative DM adjudication, with one optional DM-triggered Dexterity check. Requests and dice corrections are visible only to their owner and the DM; changes are audited, and current human dice can be corrected by the DM with a reason. Ordinary winning/ranking, ledger conservation, single normal reroll and showdown redaction rules remain in force.

Dexterity is fixed for the room session after join/initialization; it cannot be edited between hands or during play. Missing legacy scores can be initialized once. NPC gold and Dexterity are chosen independently by the GM when seating the NPC. NPC cheat checks are GM-only and audited, with the same on-turn/per-hand limits and probabilities as human cheats.
