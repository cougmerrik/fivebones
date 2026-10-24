import {test,expect,Page} from '@playwright/test';

test('GM, five humans and NPC play three hands; reconnect and ledger reconcile',async({browser,request})=>{
 const contexts=await Promise.all(Array.from({length:6},()=>browser.newContext()));
 const pages=await Promise.all(contexts.map(c=>c.newPage()));const [gm,...players]=pages;
 await gm.goto('/');await gm.getByText('Host a table',{exact:true}).click();await gm.getByRole('button',{name:'Create table as GM'}).click();await expect(gm.getByText('Connected',{exact:true})).toBeVisible();
 const host=await gm.evaluate(()=>JSON.parse(localStorage.getItem('fivebones:http://localhost:18000')!));
 for(let i=0;i<players.length;i++){
  const page=players[i];await page.goto(host.joiningUrl);await page.getByLabel('Character name',{exact:true}).fill('Player '+i);await page.getByLabel('Dexterity score',{exact:true}).fill('16');await page.getByRole('button',{name:'Join table',exact:true}).click();await expect(page.getByText('Connected',{exact:true})).toBeVisible();
 }
 await gm.getByRole('button',{name:'settings',exact:true}).click();await gm.getByRole('button',{name:'Seat NPC with 125 GP',exact:true}).click();await expect(gm.locator('.seat')).toHaveCount(6);
 await gm.getByText('Authorize scripted NPC rolls (audit logged)',{exact:true}).click();await gm.getByLabel('NPC',{exact:true}).selectOption({label:'Tavern keeper'});
 // Audited NPC Widowmaker; all humans stand pat, ensuring it is evaluated at showdown.
 await gm.getByRole('button',{name:'Authorize NPC queue',exact:true}).click();
 for(let hand=1;hand<=3;hand++){
  await gm.getByRole('button',{name:'Start next hand',exact:true}).click();await expect(gm.locator('.table .hand-number')).toHaveText('Hand '+hand);
  let count=0;let bet=false,raised=false,rerolled=false;
  while(true){
   await expect(gm.locator('.table .hand-number')).toHaveText('Hand '+hand);
   const label=(await gm.locator('.table').getAttribute('data-phase'))!;if(label==='READY_NEXT_HAND')break;
   if(++count>100)throw Error('Hand stuck: '+await gm.locator('.tabletop').innerText());
   const current=gm.locator('.seat.current');const name=(await current.locator('strong').innerText()).split(' · ')[0];const actor=name==='Tavern keeper'?gm:players[Number(name.split(' ')[1])];
   await expect(actor.locator('.actions').getByRole('button',{name:'Fold',exact:true})).toBeVisible();
   const previousVersion=await gm.locator('.table').getAttribute('data-version');
   if(hand===2&&count===1){await actor.reload();await expect(actor.getByText('Connected',{exact:true})).toBeVisible();}
   if(label.includes('REROLL')){
    if(hand===2&&!rerolled){for(let i=1;i<=5;i++)await actor.getByRole('button',{name:new RegExp('Die '+i+':')}).click();rerolled=true;}
    await actor.getByRole('button',{name:/Reroll \d \/ stand pat/}).click();
   }else if(hand===2&&!bet){await actor.getByRole('button',{name:/^Bet /}).click();bet=true;}
   else if(hand===2&&!raised){await actor.getByRole('button',{name:/^Raise /}).click();raised=true;}
   else if(hand===3&&count===1){const ctx=actor.context();await actor.close();await expect(gm.locator('.seat.current')).toContainText('Disconnected');gm.once('dialog',dialog=>dialog.accept());await gm.getByRole('button',{name:'Confirm force fold',exact:true}).click();const reconnected=await ctx.newPage();players[Number(name.split(' ')[1])]=reconnected;await reconnected.goto('/');await expect(reconnected.getByText('Connected',{exact:true})).toBeVisible();}
   else {const call=actor.getByRole('button',{name:/^Call /});if(await call.count())await call.click();else await actor.getByRole('button',{name:'Check',exact:true}).click();}
   await expect(gm.locator('.table')).not.toHaveAttribute('data-version',previousVersion!);
  }
 }
 await gm.getByRole('button',{name:'ledger',exact:true}).click();await expect(gm.getByRole('heading',{name:'Session ledger'})).toBeVisible();
 const response=await request.get('http://localhost:18000/api/v1/rooms/'+host.roomId+'/ledger.csv',{headers:{Authorization:'Bearer '+host.seatToken}});expect(response.ok()).toBeTruthy();const csv=await response.text();const totals=csv.split('\r\n').filter(l=>l.startsWith('TOTAL,'));expect(totals).toHaveLength(6);expect(totals.reduce((n,l)=>n+Number(l.split(',')[7]),0)).toBe(0);
 await gm.context().grantPermissions(['clipboard-read','clipboard-write'],{origin:'http://localhost:15173'});await gm.bringToFront();await gm.getByRole('button',{name:'Copy settlement',exact:true}).first().click();expect(await gm.evaluate(()=>navigator.clipboard.readText())).toContain('Player 0: starting 125.00 gp');
 await gm.screenshot({path:'test-results/table-ledger.png',fullPage:true});
 for(const context of contexts)await context.close();
});
