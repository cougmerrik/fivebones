import {test,expect} from '@playwright/test';

test('private Dexterity cheating, DM adjudication and phase-only Hold labels',async({browser})=>{
 const contexts=await Promise.all(Array.from({length:4},()=>browser.newContext()));
 try{
  const [gm,alice,bob,cara]=await Promise.all(contexts.map(c=>c.newPage()));
  await gm.goto('/');await gm.getByText('Host a table',{exact:true}).click();await gm.getByRole('button',{name:'Create table as GM'}).click();await expect(gm.getByText('Connected',{exact:true})).toBeVisible();
  const host=await gm.evaluate(()=>JSON.parse(localStorage.getItem('fivebones:http://localhost:18000')!));
  const frames:any[]=[];
  cara.on('websocket',ws=>ws.on('framereceived',frame=>{try{frames.push(JSON.parse(String(frame.payload)))}catch{}}));
  for(const [page,name] of [[alice,'Alice'],[bob,'Bob'],[cara,'Cara']] as const){
   await page.goto(host.joiningUrl);await page.getByLabel('Character name',{exact:true}).fill(name);await page.getByLabel('Dexterity score',{exact:true}).fill('16');await page.getByRole('button',{name:'Join table',exact:true}).click();await expect(page.getByText('Connected',{exact:true})).toBeVisible();
  }
  await gm.getByRole('button',{name:'settings',exact:true}).click();await gm.getByRole('button',{name:'Start next hand',exact:true}).click();
  await expect(bob.locator('.seat.current')).toContainText('Bob');
  await expect(bob.locator('.dice small')).toHaveCount(0);
  await bob.getByRole('button',{name:'Cheat & roll Dexterity',exact:true}).click();
  const inbox=gm.locator('.dm-cheats > .dm-notice');await expect(inbox).toHaveCount(1);await expect(inbox).toContainText('Bob · Loaded die');await expect(inbox).toContainText('Dexterity check:');await expect(inbox).toContainText('Applied immediately');await expect(inbox.locator('h3')).toHaveCSS('font-size','13px');await expect(gm.locator('.dm-cheats')).not.toContainText('Cheat checks report attempts');
  await expect(bob.locator('.private-cheats')).toContainText('Loaded die · applied');
  await expect.poll(()=>frames.filter(f=>f.type==='snapshot').length).toBeGreaterThan(0);
  const snapshots=frames.filter(f=>f.type==='snapshot').map(f=>f.state);
  expect(snapshots.every(s=>s.cheatRequests.length===0&&s.diceChanges.length===0)).toBe(true);
  expect(snapshots.every(s=>s.seats.filter((p:any)=>p.id!==s.seatId).every((p:any)=>!('abilities' in p)&&!('loadedIndexes' in p)&&!('dice' in p)))).toBe(true);
  await bob.reload();await expect(bob.getByText('Connected',{exact:true})).toBeVisible();await expect(bob.locator('.private-cheats')).toContainText('Loaded die · applied');await expect(bob.getByRole('button',{name:'Cheat & roll Dexterity',exact:true})).toHaveCount(0);
  await gm.getByText("Change a player's die",{exact:true}).click();await gm.getByLabel('Player to adjust',{exact:true}).selectOption({label:'Bob'});await gm.getByLabel('Die position',{exact:true}).selectOption('1');await gm.getByLabel('Set face',{exact:true}).selectOption('6');await gm.getByLabel('Reason for dice change',{exact:true}).fill('A spilled drink dislodges the die');await gm.getByRole('button',{name:'Apply dice change',exact:true}).click();
  await expect(bob.getByRole('button',{name:'Die 2: 6',exact:true})).toBeVisible();await expect(bob.locator('.private-cheats')).toContainText('A spilled drink dislodges the die');await expect(cara.locator('.private-cheats')).not.toContainText('spilled drink');
  await bob.getByRole('button',{name:'Check',exact:true}).click();await expect(cara.locator('.seat.current')).toContainText('Cara');
  await cara.getByLabel('Cheat action',{exact:true}).selectOption('other');await cara.getByLabel('What do you do?',{exact:true}).fill('Distract the dealer with a story');await cara.getByRole('button',{name:'Send action to DM',exact:true}).click();
  const other=inbox.filter({hasText:'Cara · Other'});await expect(other).toContainText('Distract the dealer with a story');await expect(other).toContainText('No check rolled');await other.getByRole('button',{name:'Roll Dexterity for Cara',exact:true}).click();await expect(other).toContainText('Dexterity check:');await expect(bob.locator('.private-cheats')).not.toContainText('Distract the dealer');
  await other.getByLabel('DM note for Cara',{exact:true}).fill('Narrative distraction resolved at the table');await other.getByRole('button',{name:'Record adjudication',exact:true}).click();await expect(cara.locator('.private-cheats')).toContainText('Other · adjudicated');
  await cara.getByRole('button',{name:'Check',exact:true}).click();await expect(alice.locator('.seat.current')).toContainText('Alice');
  await alice.getByLabel('Cheat action',{exact:true}).selectOption('changeDie');await alice.getByLabel('New face',{exact:true}).selectOption('4');await alice.getByRole('button',{name:'Cheat & roll Dexterity',exact:true}).click();await expect(alice.getByRole('button',{name:'Die 1: 4',exact:true})).toBeVisible();await alice.getByRole('button',{name:'Check',exact:true}).click();
  await expect(bob.locator('.table')).toHaveAttribute('data-phase','REROLL');await expect(bob.locator('.dice small')).toHaveCount(5);await expect(bob.locator('.dice small').first()).toHaveText('Hold');
  await bob.getByRole('button',{name:'Reroll 0 / stand pat',exact:true}).click();await cara.getByRole('button',{name:'Reroll 0 / stand pat',exact:true}).click();await alice.getByRole('button',{name:'Reroll 0 / stand pat',exact:true}).click();
  await expect(bob.locator('.table')).toHaveAttribute('data-phase','BETTING_2');await expect(bob.locator('.dice small')).toHaveCount(0);
 }finally{for(const c of contexts)await c.close()}
});
