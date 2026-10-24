import {test,expect} from '@playwright/test';

test('next-hand choices, GM removal, reusable NPC presets, turn recap and final summary',async({browser})=>{
 const hostContext=await browser.newContext(),playerContext=await browser.newContext();
 const host=await hostContext.newPage(),player=await playerContext.newPage();
 try{
  await host.goto('/');await host.getByText('Host a table',{exact:true}).click();await host.getByRole('button',{name:'Create table as GM',exact:true}).click();await expect(host.getByText('Connected',{exact:true})).toBeVisible();
  const session=await host.evaluate(()=>JSON.parse(localStorage.getItem('fivebones:http://localhost:18000')!));
  const link=new URL(session.joiningUrl);
  await player.goto('/?'+link.searchParams.toString());await player.getByLabel('Character name',{exact:true}).fill('Merrik');await player.getByLabel('Dexterity score',{exact:true}).fill('16');await player.getByRole('button',{name:'Join table',exact:true}).click();await expect(player.getByText('Connected',{exact:true})).toBeVisible();
  await host.getByRole('button',{name:'settings',exact:true}).click();
  await host.getByLabel('NPC name',{exact:true}).fill('Mara');await host.getByLabel('NPC starting GP',{exact:true}).fill('42.50');await host.getByLabel('New NPC Dexterity',{exact:true}).fill('14');
  await host.getByRole('button',{name:'Save NPC preset',exact:true}).click();await expect(host.getByRole('status').filter({hasText:'NPC preset saved'})).toBeVisible();
  await host.getByRole('button',{name:'Seat NPC with 42.50 GP',exact:true}).click();await expect(host.locator('.seat').filter({hasText:'Mara'})).toBeVisible();
  await player.getByRole('button',{name:'Sit out next hand',exact:true}).click();await expect(player.getByRole('button',{name:'Join next hand',exact:true})).toBeVisible();await expect(host.getByRole('button',{name:'Start next hand',exact:true})).toBeDisabled();
  const toggle=player.locator('.participation-toggle');const rules=player.getByRole('button',{name:'Hands & rules',exact:true});expect((await toggle.boundingBox())!.x).toBeLessThan((await rules.boundingBox())!.x);
  expect(await toggle.evaluate(el=>getComputedStyle(el).backgroundColor)).not.toBe(await rules.evaluate(el=>getComputedStyle(el).backgroundColor));
  await player.reload();await expect(player.getByRole('button',{name:'Join next hand',exact:true})).toBeVisible();await player.getByRole('button',{name:'Join next hand',exact:true}).click();await expect(host.getByRole('button',{name:'Start next hand',exact:true})).toBeEnabled();
  await host.getByText('Authorize scripted NPC rolls (audit logged)',{exact:true}).click();await expect(host.locator('.queue-instructions')).toContainText('sitting out does not consume it');await expect(host.locator('.queue-instructions')).toContainText('replacements');
  await host.getByLabel('NPC',{exact:true}).selectOption({label:'Mara'});await host.getByLabel('Up to 10 queued rolls',{exact:true}).fill('[{"initial":[2,2,2,4,6],"replacements":[2,5]}]');await host.getByRole('button',{name:'Authorize NPC queue',exact:true}).click();await expect(host.getByText('1 queued hands remaining',{exact:true})).toBeVisible();
  await host.getByRole('button',{name:'Start next hand',exact:true}).click();await expect(host.locator('.seat.current')).toContainText('Mara');await host.getByRole('button',{name:'Check',exact:true}).click();await expect(player.locator('.seat.current')).toContainText('Merrik');await expect(player.getByLabel('What just happened',{exact:true})).toContainText('Mara checked.');
  const recap=player.getByLabel('What just happened',{exact:true});expect((await recap.boundingBox())!.y).toBeLessThan((await player.locator('.table-summary').boundingBox())!.y);
  await player.getByRole('button',{name:'Sit out next hand',exact:true}).click();await expect(player.getByRole('button',{name:'Check',exact:true})).toBeVisible();
  await player.getByLabel('Cheat action',{exact:true}).selectOption('other');await player.getByLabel('What do you do?',{exact:true}).fill('Secret distraction');await player.getByRole('button',{name:'Send action to DM',exact:true}).click();await expect(recap).toContainText('Mara checked.');await expect(recap).not.toContainText('Secret');
  host.once('dialog',d=>d.accept());await host.getByRole('button',{name:'Remove Merrik from play',exact:true}).click();await expect(host.locator('.table')).toHaveAttribute('data-phase','READY_NEXT_HAND');await expect(player.getByRole('button',{name:'Removed by GM',exact:true})).toBeDisabled();await expect(recap).toContainText('removed Merrik');await expect(player.getByRole('button',{name:'Check',exact:true})).toHaveCount(0);
  await host.reload();await expect(host.getByRole('button',{name:'Restore Merrik',exact:true})).toBeVisible();await host.getByRole('button',{name:'settings',exact:true}).click();await host.getByRole('button',{name:'Restore Merrik',exact:true}).click();await expect(player.getByRole('button',{name:'Sit out next hand',exact:true})).toBeEnabled();
  await host.getByLabel('Saved NPC preset',{exact:true}).selectOption({label:'Mara'});await host.getByRole('button',{name:'Load NPC preset',exact:true}).click();await expect(host.getByLabel('NPC starting GP',{exact:true})).toHaveValue('42.50');await expect(host.getByLabel('New NPC Dexterity',{exact:true})).toHaveValue('14');
  host.once('dialog',d=>d.accept());await host.getByRole('button',{name:'End session',exact:true}).click();
  for(const page of [host,player]){const summary=page.getByRole('region',{name:'Final session summary',exact:true});await expect(summary).toBeVisible();await expect(summary).toContainText('1 hand played');await expect(summary).toContainText('Merrik');await expect(summary).toContainText('Mara');await expect(summary.getByRole('button',{name:'Copy session summary',exact:true})).toBeVisible()}
  await expect(host.getByRole('button',{name:'Download session CSV',exact:true})).toBeVisible();await expect(player.getByRole('button',{name:'Download session CSV',exact:true})).toHaveCount(0);
  await host.reload();await expect(host.getByRole('region',{name:'Final session summary',exact:true})).toBeVisible();
  // A new room in the same GM browser retains templates, not live balances or dice.
  const next=await (await hostContext.request.post('http://localhost:18000/api/v1/rooms',{data:{name:'Next table'}})).json();
  await host.evaluate(session=>localStorage.setItem('fivebones:http://localhost:18000',JSON.stringify(session)),next);await host.reload();await expect(host.getByText('Connected',{exact:true})).toBeVisible();await host.getByRole('button',{name:'settings',exact:true}).click();
  await host.getByLabel('Saved NPC preset',{exact:true}).selectOption({label:'Mara'});await host.getByRole('button',{name:'Load NPC preset',exact:true}).click();await expect(host.getByLabel('NPC name',{exact:true})).toHaveValue('Mara');await expect(host.getByLabel('NPC starting GP',{exact:true})).toHaveValue('42.50');
 }finally{await hostContext.close();await playerContext.close()}
});
