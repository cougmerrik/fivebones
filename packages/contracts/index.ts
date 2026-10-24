export interface DiceChange {id:number;hand:number;seatId:string;dieIndex:number;before:number;after:number;reason:string;requestId:string|null;actor:string}
export interface CheatRequest {id:string;hand:number;phase:string;seatId:string;kind:'loadedDie'|'changeDie'|'other';status:string;dieIndex?:number;face?:number;description?:string;reason?:string;change?:DiceChange;check:{ability:'dexterity';score:number;roll:number;modifier:number;total:number}|null}
export interface Session {roomId:string; seatToken:string; inviteCode?:string; joiningUrl?:string}
export interface Seat {nextHand?:boolean;removed?:boolean;id:string;name:string;npc:boolean;connected?:boolean;handRank?:string;abilities?:{dexterity:number}|null;loadedIndexes?:number[];opening:number;balance:number;folded:boolean;contribution:number;commitment:number;rerollCount:number|null;dice?:number[];queue?:unknown[]}
export interface State {lastTurn?:string;cheatRequests?:CheatRequest[];diceChanges?:DiceChange[];name:string;small:number;ante:number;ties:string;remainder:string;phase:string;version:number;hand:number;actor:string|null;pot:number;role:'gm'|'player'|'spectator';seatId:string|null;seats:Seat[];target:number;raises:number;ended:boolean;events:Record<string,unknown>[];ledger:{hand:number;seatId:string;amountCp:number;kind:string}[]}
export function parseState(value:unknown):State {
 const s=value as State;
 if(!s || !Array.isArray(s.seats)||!Array.isArray(s.events)||!Array.isArray(s.ledger)||!Number.isInteger(s.version)||typeof s.phase!=='string'||!['gm','player','spectator'].includes(s.role))throw Error('Invalid server snapshot');
 for(const seat of s.seats) if(typeof seat.id!=='string'||typeof seat.name!=='string'||!Number.isInteger(seat.balance)||seat.dice&&(!Array.isArray(seat.dice)||seat.dice.some(d=>!Number.isInteger(d)||d<1||d>6)))throw Error('Invalid seat');
 return s;
}
