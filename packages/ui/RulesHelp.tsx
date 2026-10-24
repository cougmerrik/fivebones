import React, {useRef} from 'react';
import type {State} from '../contracts';
import {DieFace} from './DieFace';

const hands = [
 ['Five of a kind', '6 · 6 · 6 · 6 · 6', 'All five dice match.'],
 ['Four of a kind', '5 · 5 · 5 · 5 · 2', 'Four dice match.'],
 ['Full house', '4 · 4 · 4 · 2 · 2', 'Three matching dice and a pair.'],
 ['Straight', '2 · 3 · 4 · 5 · 6', 'Five consecutive faces: 1–5 or 2–6.'],
 ['Three of a kind', '3 · 3 · 3 · 5 · 1', 'Three dice match; two different kickers.'],
 ['Two pair', '5 · 5 · 2 · 2 · 1', 'Two different pairs and one kicker.'],
 ['One pair', '4 · 4 · 6 · 3 · 1', 'One pair and three different kickers.'],
 ['High bones', '6 · 5 · 4 · 2 · 1', 'None of the combinations above.'],
];

export function RulesHelp({state,assetUrl}:{state:State|null;assetUrl?:(url:string)=>string}) {
 const dialog = useRef<HTMLDialogElement>(null);
 const money = (cp:number) => `${(cp / 100).toFixed(2)} gp`;
 return <>
  <button className="rules-trigger" onClick={()=>dialog.current?.showModal()}>Hands &amp; rules</button>
  <dialog ref={dialog} className="rules-dialog" aria-labelledby="rules-title">
   <div className="rules-heading"><h2 id="rules-title">Hands &amp; rules</h2><form method="dialog"><button aria-label="Close rules">Close</button></form></div>
   <h3>Which hand wins?</h3>
   <p>Strongest first. Each hand beats every hand below it, except for the Widowmaker curse.</p>
   <div className="rankings"><table><thead><tr><th scope="col">Rank</th><th scope="col">Hand</th><th scope="col">Example</th></tr></thead><tbody>
    {hands.map(([name,example,description],i)=><tr key={name}><td>{i+1}</td><th scope="row">{name}<small>{description}</small></th><td className="hand-example"><span className="example-dice" role="img" aria-label={example}>{example.split(' · ').map((d,i)=><DieFace key={i} value={Number(d)} assetUrl={assetUrl} decorative/>)}</span></td></tr>)}
   </tbody></table></div>
   <aside className="widowmaker"><h3>The Widowmaker: 6 · 6 · 6 · 1 · 1</h3><p>This exact combination loses to every other hand at showdown. It can still win if everyone else folds. If only Widowmakers remain, play pauses for GM adjudication; this table refunds each player's contributions after the GM records a reason.</p></aside>
   <h3>How to play a hand</h3>
   <ol className="play-rules">
    <li><strong>Ante.</strong> Each eligible seat pays the table ante. The server rolls five hidden six-sided dice for each entrant.</li>
    <li><strong>First betting round.</strong> Act clockwise from the dealer's left. Check when nothing is owed, open with a bet, call to match, raise, or fold. Bets and raises use the small bet.</li>
    <li><strong>One reroll.</strong> On your turn, choose any 0–5 dice to replace and submit once. Choose zero to stand pat. Everyone can see how many dice you rerolled; your choices and faces stay private.</li>
    <li><strong>Second betting round.</strong> Use the same actions, now with the big bet. Each betting round allows at most two raises in total across the table.</li>
    <li><strong>Showdown.</strong> Remaining players reveal their hands. The strongest hand takes the pot, subject to the Widowmaker curse. Folded hands remain hidden. If only one player remains before showdown, that player wins without revealing.</li>
    <li><strong>Next hand.</strong> The dealer rotates. The GM starts the next hand when everyone is ready.</li>
   </ol>
   <h3>Private cheating</h3>
   <p>Enter your Dexterity score when joining. Once per hand, on your turn, you may use a loaded die, change a die's face, or describe another action to the DM.</p>
   <p>Loaded die swaps and rolls one die immediately: a 5 has a 33% chance and every other face has a 13.4% chance. That die stays loaded for this hand's normal reroll, then resets. Change die immediately sets your selected face. Both send a private server roll of 1d20 + your Dexterity modifier to the DM, without waiting for approval.</p>
   <p>Other sends your description for out-of-game adjudication. The DM may request a Dexterity check or change an active player's dice, with a private audit reason. Attempts, checks, and edits stay private to you and the DM; the DM decides detection and consequences out of game.</p>
   <h3>{state?'This table’s house rules':'Default house rules'}</h3>
   <p>{state?`Ante: ${money(state.ante)}. Small bet: ${money(state.small)}. Big bet: ${money(state.small*2)}.`:'The ante defaults to the small bet. Stake presets are 1 sp / 2 sp, 1 gp / 2 gp, and 10 gp / 20 gp. The host can choose a different ante when creating a table.'}</p>
   <p>{state?.ties==='category'?'Matching hand categories split the pot; faces and kickers do not break ties.':'Matching categories compare faces: five-kind face; four-kind face then kicker; full-house triple then pair; straight high die; triple then descending kickers; higher pair, lower pair, then kicker for two pair; pair then descending kickers; or descending faces for high bones. Exact ties split the pot.'} Spare copper goes to tied winners in {state?.remainder==='counterclockwise'?'counterclockwise':'clockwise'} order from the dealer. These tie and ante conventions are configurable house rules.</p>
   <p>No all-ins, side pots, credit, or partial calls. You need enough coins for the ante to enter; if you cannot afford an outstanding call, fold. You may check when nothing is owed. A disconnect pauses your turn; the GM may explicitly confirm a force-fold.</p>
   <p>The session ledger tracks your net change and expected final GP. Copy your settlement at the end and update your character sheet manually.</p>
   <form method="dialog"><button>Back to the table</button></form>
  </dialog>
 </>;
}
