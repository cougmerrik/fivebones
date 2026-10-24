import React from 'react';

const steps = ['Ante','Betting 1','Reroll','Betting 2','Showdown','Next Hand'];
const phaseStep:Record<string,number> = {
 LOBBY:0, ANTE_COLLECTION:0, FIRST_ROLL:0,
 BETTING_1:1, REROLL:2, BETTING_2:3,
 SHOWDOWN:4, ADJUDICATION:4, SETTLEMENT:4, READY_NEXT_HAND:5,
};

export function PhaseTracker({phase,ended}:{phase:string;ended:boolean}) {
 const current=ended?null:phaseStep[phase]??0;
 return <ol className="phase-tracker" aria-label="Hand phases">
  {steps.map((label,index)=><li key={label} aria-current={index===current?'step':undefined} className={index===current?'current-phase':undefined}><span>{label}</span>{index<steps.length-1&&<span className="phase-arrow" aria-hidden="true">→</span>}</li>)}
 </ol>;
}
