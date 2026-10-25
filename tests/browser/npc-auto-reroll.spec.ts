import {test,expect} from '@playwright/test';

test('queued NPC selections reroll automatically in order and leave human and betting turns manual',async({browser})=>{
 const gmContext=await browser.newContext(),humanContext=await browser.newContext();
 const gm=await gmContext.newPage(),human=await humanContext.newPage();
 try{
  await gm.goto('/');await gm.getByText('Host a table',{exact:true}).click();await gm.getByRole('button',{name:'Create table as GM',exact:true}).click();await expect(gm.getByText('Connected',{exact:true})).toBeVisible();
  const session=await gm.evaluate(()=>JSON.parse(localStorage.getItem('fivebones:http://localhost:18000')!));
  await human.goto('/?'+new URL(session.joiningUrl).searchParams.toString());await human.getByLabel('Character name',{exact:true}).fill('Human');await human.getByLabel('Dexterity score',{exact:true}).fill('14');await human.getByRole('button',{name:'Join table',exact:true}).click();await expect(human.getByText('Connected',{exact:true})).toBeVisible();
  await gm.getByRole('button',{name:'settings',exact:true}).click();
  for(const name of ['Scripted','Standing']){await gm.getByLabel('NPC name',{exact:true}).fill(name);await gm.getByRole('button',{name:'Seat NPC with 125 GP',exact:true}).click();await expect(gm.locator('.seat').filter({hasText:name})).toBeVisible()}
  await gm.getByText('Authorize scripted NPC rolls (audit logged)',{exact:true}).click();await expect(gm.locator('.queue-instructions')).toContainText('rerollIndexes');await expect(gm.locator('.queue-instructions')).toContainText('automatically');
  for(const [name,rerollIndexes,replacements] of [['Scripted',[3,4],[6,6]],['Standing',[],[]]] as const){
   await gm.getByLabel('NPC',{exact:true}).selectOption({label:name});await gm.getByLabel('Up to 10 queued rolls',{exact:true}).fill(JSON.stringify([{initial:[2,2,2,4,6],rerollIndexes,replacements}]));await gm.getByRole('button',{name:'Authorize NPC queue',exact:true}).click();await expect(gm.getByText('1 queued hands remaining',{exact:true})).toBeVisible();
  }
  await gm.getByRole('button',{name:'Start next hand',exact:true}).click();await expect(gm.locator('.seat.current')).toContainText('Scripted');await expect(gm.getByText('Automatic reroll: dice 4, 5',{exact:true})).toBeVisible();await expect(gm.getByText('Automatic stand pat',{exact:true})).toBeVisible();await expect(human.getByText('Automatic stand pat',{exact:true})).toHaveCount(0);
  await gm.getByRole('button',{name:'Check',exact:true}).click();await expect(gm.locator('.seat.current')).toContainText('Standing');await gm.getByRole('button',{name:'Check',exact:true}).click();await expect(human.locator('.seat.current')).toContainText('Human');
  await human.getByRole('button',{name:'Check',exact:true}).click();await expect(human.locator('.table')).toHaveAttribute('data-phase','REROLL');await expect(human.locator('.seat.current')).toContainText('Human');
  await expect(gm.locator('.seat').filter({hasText:'Scripted'})).toContainText('Rerolled 2');await expect(gm.locator('.seat').filter({hasText:'Standing'})).toContainText('Rerolled 0');
  for(const name of ['Scripted','Standing'])await expect(human.locator('.seat').filter({hasText:name}).locator('.seat-dice')).toHaveCount(0);
  const dice=gm.locator('.seat').filter({hasText:'Scripted'}).locator('.pip-image');await expect(dice.nth(3)).toHaveAttribute('src',/pip6/);await expect(dice.nth(4)).toHaveAttribute('src',/pip6/);
  await expect(human.getByLabel('What just happened',{exact:true})).toContainText('Scripted rerolled 2 dice.');await expect(human.getByLabel('What just happened',{exact:true})).toContainText('Standing stood pat.');
  await gm.reload();await expect(gm.getByText('Connected',{exact:true})).toBeVisible();await expect(gm.locator('.seat').filter({hasText:'Scripted'})).toContainText('Rerolled 2');
  await human.getByRole('button',{name:'Reroll 0 / stand pat',exact:true}).click();await expect(gm.locator('.table')).toHaveAttribute('data-phase','BETTING_2');await expect(gm.locator('.seat.current')).toContainText('Scripted');await expect(gm.getByRole('button',{name:'Check',exact:true})).toBeEnabled();
  await gm.getByRole('button',{name:'Check',exact:true}).click();await expect(gm.locator('.seat.current')).toContainText('Standing');await gm.getByRole('button',{name:'Check',exact:true}).click();await expect(human.locator('.seat.current')).toContainText('Human');await human.getByRole('button',{name:'Check',exact:true}).click();await expect(gm.locator('.table')).toHaveAttribute('data-phase','READY_NEXT_HAND');
 }finally{await gmContext.close();await humanContext.close()}
});
