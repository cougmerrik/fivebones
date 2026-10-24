import {test,expect} from '@playwright/test';

test('compact top ledger, collapsed player room, locked Dexterity and NPC gold/checks',async({browser})=>{
 const contexts=await Promise.all(Array.from({length:3},()=>browser.newContext()));
 try{
  const [gm,alice,bob]=await Promise.all(contexts.map(c=>c.newPage()));
  await gm.goto('/');await gm.getByText('Host a table',{exact:true}).click();await gm.getByRole('button',{name:'Create table as GM'}).click();await expect(gm.getByText('Connected',{exact:true})).toBeVisible();
  const host=await gm.evaluate(()=>JSON.parse(localStorage.getItem('fivebones:http://localhost:18000')!));
  for(const [page,name] of [[alice,'Alice'],[bob,'Bob']] as const){
   await page.goto(host.joiningUrl);await page.getByLabel('Character name',{exact:true}).fill(name);await page.getByLabel('Dexterity score',{exact:true}).fill('16');await page.getByRole('button',{name:'Join table',exact:true}).click();await expect(page.getByText('Connected',{exact:true})).toBeVisible();
   await expect(page.locator('.room')).not.toHaveAttribute('open','');
   await expect(page.getByRole('button',{name:'Leave this device',exact:true})).not.toBeVisible();
   await expect(page.locator('.private-cheats')).toContainText('Dexterity 16 · modifier 3 · locked for this session');
   await expect(page.locator('.private-cheats input')).toHaveCount(0);
   await expect(page.locator('footer')).toHaveCount(0);
  }
  await expect(gm.locator('.room')).toHaveAttribute('open','');await expect(gm.locator('.room')).not.toContainText('Five Bones');
  await expect(alice.locator('.room>summary .notice')).toHaveText('Connected');
  await expect(alice.locator('.room>summary .notice')).toHaveCSS('text-align','right');
  const privateBox=await alice.locator('.private-panels').boundingBox(),roomPanel=await alice.locator('.room').boundingBox();expect(roomPanel!.y).toBeGreaterThanOrEqual(privateBox!.y+privateBox!.height);
  await expect(alice.locator('.ledger-box').filter({hasText:'Alice'})).toHaveText('Alice 125g (0g)');
  await alice.evaluate(()=>window.scrollTo(0,0));
  await expect(alice.getByRole('img',{name:'Five Bones',exact:true})).toBeInViewport();
  await expect(alice.locator('.private-cheats h2')).toBeInViewport();
  await expect(alice.getByRole('button',{name:'Cheat & roll Dexterity',exact:true})).toBeInViewport();
  expect(await alice.locator('.title-art').evaluate(el=>el.getBoundingClientRect().width)).toBe(450);
  await expect(alice.locator('.bones>header')).toHaveCSS('border-bottom-width','0px');
  await expect(alice.locator('.table .rules-trigger')).toBeVisible();
  const chip=alice.locator('.phase-tracker li[aria-current="step"]>span:first-child'),rules=alice.locator('.table .rules-trigger');
  expect(await rules.evaluate(el=>getComputedStyle(el).fontSize)).toBe(await chip.evaluate(el=>getComputedStyle(el).fontSize));
  expect(Math.abs((await rules.boundingBox())!.height-(await chip.boundingBox())!.height)).toBeLessThan(1);
  await expect(alice.locator('.phase-tracker li[aria-current="step"]')).toHaveText('Ante→');
  const tracker=await alice.locator('.phase-tracker').boundingBox(),hand=await alice.locator('.hand-number').boundingBox(),table=await alice.locator('.table').boundingBox();
  expect(hand!.y).toBeGreaterThanOrEqual(tracker!.y+tracker!.height);
  expect(Math.abs(hand!.x+hand!.width/2-table!.x-table!.width/2)).toBeLessThan(2);
  await alice.screenshot({path:'test-results/compact-player.png'});

  await alice.locator('.room>summary').click();await expect(alice.getByRole('button',{name:'Leave this device',exact:true})).toBeVisible();await alice.locator('.room>summary').click();
  await gm.getByRole('button',{name:'settings',exact:true}).click();await gm.getByLabel('NPC name',{exact:true}).fill('Lucky Jack');await gm.getByLabel('NPC starting GP',{exact:true}).fill('-1');await expect(gm.getByRole('button',{name:'Seat NPC with -1 GP',exact:true})).toBeDisabled();
  await gm.getByLabel('NPC starting GP',{exact:true}).fill('240.50');await gm.getByLabel('New NPC Dexterity',{exact:true}).fill('18');await gm.getByRole('button',{name:'Seat NPC with 240.50 GP',exact:true}).click();
  await expect(gm.locator('.ledger-box').filter({hasText:'Lucky Jack'})).toHaveText('Lucky Jack 240.5g (0g)');
  await gm.getByRole('button',{name:'Start next hand',exact:true}).click();await expect(bob.locator('.seat.current')).toContainText('Bob');
  await expect(gm.getByRole('button',{name:'End session',exact:true})).toBeDisabled();
  await expect(bob.locator('.dice .pip-image')).toHaveCount(5);
  await expect(bob.locator('.phase-tracker li[aria-current="step"]')).toHaveText('Betting 1→');
  const centered=await bob.locator('.seat').filter({hasText:'Bob'}).evaluate(seat=>{
   const images=[...seat.querySelectorAll('.seat-dice img')];const first=images[0].getBoundingClientRect(),last=images[images.length-1].getBoundingClientRect(),box=seat.getBoundingClientRect();
   return Math.abs((first.left+last.right)/2-(box.left+box.right)/2)<2;
  });expect(centered).toBe(true);

  expect(await bob.locator('.dice button').evaluateAll(async buttons=>{
   await Promise.all(buttons.map(button=>button.querySelector('img')!.decode()));
   return buttons.every(button=>{
    const face=button.getAttribute('aria-label')!.match(/Die \d+: (\d)/)![1];
    return button.querySelector('img')!.src.match(/pip([1-6])(?:-|\.png)/)?.[1]===face;
   });
  })).toBe(true);

  await expect(gm.getByText('Finish or adjudicate the current hand to end the session.',{exact:true})).toBeVisible();
  const roomBox=await alice.locator('.room').boundingBox(),noticeBox=await alice.locator('.room .notice').boundingBox();expect(noticeBox!.x+noticeBox!.width).toBeGreaterThan(roomBox!.x+roomBox!.width/2);
  const bobTotal=alice.locator('.ledger-box').filter({hasText:'Bob'});await expect(bobTotal).toHaveText('Bob 124g (-1g)');await expect(bobTotal.locator('.ledger-net')).toHaveCSS('color','rgb(255, 116, 116)');
  await bob.getByRole('button',{name:'Check',exact:true}).click();
  const npc=gm.getByRole('region',{name:'NPC private actions'});await expect(npc).toContainText('Lucky Jack');await expect(npc).toContainText('Dexterity 18 · modifier 4');
  await npc.getByRole('button',{name:'Cheat & roll Dexterity',exact:true}).click();await expect(npc).toContainText('Loaded die · applied');await expect(npc).toContainText('Dexterity check:');await expect(npc.locator('.check-result')).toContainText('+ 4 =');
  await expect(alice.locator('.private-cheats')).not.toContainText('Loaded die · applied');await expect(alice.locator('.private-cheats')).not.toContainText('Dexterity check:');
  await gm.getByRole('button',{name:'Check',exact:true}).click();await expect(alice.locator('.seat.current')).toContainText('Alice');await alice.getByRole('button',{name:'Fold',exact:true}).click();
  await expect(bob.locator('.table')).toHaveAttribute('data-phase','REROLL');await bob.getByRole('button',{name:'Fold',exact:true}).click();
  await expect(gm.locator('.table')).toHaveAttribute('data-phase','READY_NEXT_HAND');
  const npcTotal=alice.locator('.ledger-box').filter({hasText:'Lucky Jack'});await expect(npcTotal).toHaveText('Lucky Jack 242.5g (+2g)');await expect(npcTotal.locator('.ledger-net')).toHaveCSS('color','rgb(103, 255, 128)');
  await alice.reload();await expect(alice.getByText('Connected',{exact:true})).toBeVisible();await expect(alice.locator('.room')).not.toHaveAttribute('open','');await expect(alice.locator('.private-cheats input')).toHaveCount(0);
  await alice.screenshot({path:'test-results/top-ledger.png',fullPage:true});
  await alice.setViewportSize({width:390,height:844});expect(await alice.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  gm.once('dialog',dialog=>{expect(dialog.message()).toBe('End this session? The final ledger will remain available.');return dialog.accept()});await gm.getByRole('button',{name:'End session',exact:true}).click();await expect(gm.locator('.tabletop')).toContainText('Session ended');
 }finally{for(const c of contexts)await c.close()}
});
