import {test,expect,Page} from '@playwright/test';
const prefix='fivebones:campaign:http://localhost:18000:belwether:';

async function dm(page:Page){
 await page.goto('/?room=belwether&isdm=1');
 await expect(page.getByLabel('DM access key',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Remember DM access',exact:true}).click();
 const status=await (await page.request.get('http://localhost:18000/api/v1/campaigns/belwether')).json();
 if(status.available){
  await expect(page.getByText('Connected',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'settings',exact:true}).click();const end=page.getByRole('button',{name:'End session',exact:true});
  if(await end.isEnabled()){page.once('dialog',d=>d.accept());await end.click()}
 }
}

async function fresh(page:Page){
 const first=page.getByRole('button',{name:'Start belwether session',exact:true});
 if(await first.count()){await expect(first).toBeEnabled();await first.click()}
 else{const button=page.getByRole('button',{name:'Start fresh belwether session',exact:true});await expect(button).toBeEnabled();page.once('dialog',d=>d.accept());await button.click()}
 await expect(page.getByText('Connected',{exact:true})).toBeVisible();await expect(page.locator('.hand-number')).toHaveText('Hand 0');
}

test('stable campaign link keeps the player form, remembers DM access and switches fresh sessions',async({browser})=>{
 const gmContext=await browser.newContext(),playerContext=await browser.newContext(),strangerContext=await browser.newContext();
 const gm=await gmContext.newPage(),player=await playerContext.newPage(),stranger=await strangerContext.newPage();
 try{
  await dm(gm);
  await player.goto('/?room=belwether');await expect(player.getByRole('heading',{name:'Join Belwether',exact:true})).toBeVisible();
  await expect(player.getByLabel('Room ID',{exact:true})).toHaveCount(0);await expect(player.getByLabel('Invite code',{exact:true})).toHaveCount(0);await expect(player.getByRole('button',{name:'Join belwether',exact:true})).toBeDisabled();
  await stranger.goto('/?room=belwether&isdm=1');await expect(stranger.getByLabel('DM access key',{exact:true})).toBeVisible();await expect(stranger.locator('.table')).toHaveCount(0);
  await fresh(gm);await expect(player.getByText('Room setup is ready. Enter your character details and join.',{exact:true})).toBeVisible();
  await player.getByLabel('Character name',{exact:true}).fill('Campaign Merrik');await player.getByLabel('Starting GP (manual snapshot)',{exact:true}).fill('105');await player.getByLabel('Dexterity score',{exact:true}).fill('16');await player.getByRole('button',{name:'Join belwether',exact:true}).click();await expect(player.getByText('Connected',{exact:true})).toBeVisible();await expect(gm.locator('.seat')).toContainText('Campaign Merrik');
  const old=await player.evaluate(key=>JSON.parse(localStorage.getItem(key)! ),prefix+'player');
  await gm.reload();await expect(gm.getByText('Connected',{exact:true})).toBeVisible();await expect(gm.getByLabel('DM access key',{exact:true})).toHaveCount(0);await expect(gm.locator('.seat')).toContainText('Campaign Merrik');
  await player.reload();await expect(player.getByText('Connected',{exact:true})).toBeVisible();await expect(player.getByRole('button',{name:'Join belwether',exact:true})).toHaveCount(0);
  await gm.getByRole('button',{name:'settings',exact:true}).click();gm.once('dialog',d=>d.accept());await gm.getByRole('button',{name:'End session',exact:true}).click();await expect(player.getByRole('region',{name:'Final session summary',exact:true})).toBeVisible();
  await fresh(gm);await expect(gm.locator('.seat')).toHaveCount(0);await expect(player.getByRole('button',{name:'Join new belwether session',exact:true})).toBeVisible();await player.getByRole('button',{name:'Join new belwether session',exact:true}).click();
  await player.getByLabel('Character name',{exact:true}).fill('Campaign Merrik');await player.getByLabel('Starting GP (manual snapshot)',{exact:true}).fill('90');await player.getByLabel('Dexterity score',{exact:true}).fill('16');await player.getByRole('button',{name:'Join belwether',exact:true}).click();await expect(player.getByText('Connected',{exact:true})).toBeVisible();
  const current=await player.evaluate(key=>JSON.parse(localStorage.getItem(key)! ),prefix+'player');expect(current.roomId).not.toBe(old.roomId);await expect(gm.locator('.ledger-strip')).toContainText('90g');
  await gm.getByText('Previous session summaries',{exact:true}).click();await expect(gm.locator('.campaign-history')).toContainText('Campaign Merrik: started 105.00 gp, finished 105.00 gp');
  expect(await gm.evaluate(()=>location.search)).toBe('?room=belwether&isdm=1');
 }finally{await gmContext.close();await playerContext.close();await strangerContext.close()}
});

test('lost join response recovers the same player seat after refresh',async({browser})=>{
 const gmContext=await browser.newContext(),playerContext=await browser.newContext();const gm=await gmContext.newPage(),player=await playerContext.newPage();
 try{
  await dm(gm);await fresh(gm);await player.goto('/?room=belwether');
  await player.getByLabel('Character name',{exact:true}).fill('Retry adventurer');await player.getByLabel('Dexterity score',{exact:true}).fill('12');
  await player.route('**/api/v1/campaigns/belwether/join',async route=>{const response=await route.fetch();expect(response.status()).toBe(200);await route.abort()});
  await player.getByRole('button',{name:'Join belwether',exact:true}).click();await expect(gm.locator('.seat')).toHaveCount(1);
  await player.unroute('**/api/v1/campaigns/belwether/join');await player.reload();await expect(player.getByLabel('Character name',{exact:true})).toHaveValue('Retry adventurer');await player.getByRole('button',{name:'Join belwether',exact:true}).click();await expect(player.getByText('Connected',{exact:true})).toBeVisible();await expect(gm.locator('.seat')).toHaveCount(1);
 }finally{await gmContext.close();await playerContext.close()}
});
