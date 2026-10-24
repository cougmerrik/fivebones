import {test,expect} from '@playwright/test';

test('six ordered stages track play and a paused Widowmaker showdown',async({page})=>{
 await page.goto('/');await page.getByText('Host a table',{exact:true}).click();await page.getByRole('button',{name:'Create table as GM'}).click();await expect(page.getByText('Connected',{exact:true})).toBeVisible();
 expect(await page.locator('.phase-tracker li>span:first-child').allTextContents()).toEqual(['Ante','Betting 1','Reroll','Betting 2','Showdown','Next Hand']);
 const active=()=>page.locator('.phase-tracker li[aria-current="step"]>span:first-child');
 await expect(active()).toHaveText('Ante');
 await page.getByRole('button',{name:'settings',exact:true}).click();
 for(const name of ['Jack','Mara']){
  await page.getByLabel('NPC name',{exact:true}).fill(name);await page.getByRole('button',{name:'Seat NPC with 125 GP',exact:true}).click();await expect(page.locator('.seat').filter({hasText:name})).toBeVisible();
 }
 await page.getByText('Authorize scripted NPC rolls (audit logged)',{exact:true}).click();
 for(const name of ['Jack','Mara']){
  await page.getByLabel('NPC',{exact:true}).selectOption({label:name});await page.getByLabel('Up to 10 queued rolls',{exact:true}).fill('[{"initial":[6,6,6,1,1]}]');
  await page.getByRole('button',{name:'Authorize NPC queue',exact:true}).click();await expect(page.getByRole('button',{name:'Start next hand',exact:true})).toBeEnabled();
 }
 await page.getByRole('button',{name:'Start next hand',exact:true}).click();await expect(page.locator('.hand-number')).toHaveText('Hand 1');
 for(const phase of ['Betting 1','Reroll','Betting 2']){
  await expect(active()).toHaveText(phase);
  for(let i=0;i<2;i++){
   const old=await page.locator('.table').getAttribute('data-version');
   await page.getByRole('button',{name:phase==='Reroll'?'Reroll 0 / stand pat':'Check',exact:true}).click();
   await expect(page.locator('.table')).not.toHaveAttribute('data-version',old!);
  }
 }
 await expect(page.locator('.table')).toHaveAttribute('data-phase','ADJUDICATION');await expect(active()).toHaveText('Showdown');
 page.once('dialog',dialog=>dialog.accept('Refund all Widowmakers'));await page.getByRole('button',{name:'Adjudicate: refund hand',exact:true}).click();
 await expect(active()).toHaveText('Next Hand');await expect(page.locator('.hand-number')).toHaveText('Hand 1');
});
