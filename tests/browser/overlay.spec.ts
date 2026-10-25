import {test,expect,chromium} from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs/promises';
import os from 'node:os';

test('built MV3 overlay loads in Chromium on a simulated Roll20 editor page',async({request,browser})=>{
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'bones-extension-'));
 const extension='/tmp/fivebones-e2e-extension';
 const context=await chromium.launchPersistentContext(dir,{headless:true,channel:process.env.CHROMIUM_EXECUTABLE?undefined:'chromium',executablePath:process.env.CHROMIUM_EXECUTABLE,args:['--disable-features=LocalNetworkAccessChecks,LocalNetworkAccessChecksWebSockets','--disable-extensions-except='+extension,'--load-extension='+extension],viewport:{width:1280,height:900}});
 try{
  await context.route('https://app.roll20.net/editor/**',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><title>Simulated editor</title><body><h1>Simulated host page</h1><input name="attr_gp" value="999"><div id="map">Map remains accessible</div></body>'}));
  const page=await context.newPage();page.on('console',msg=>{if(msg.type()==='error')console.log('Overlay console:',msg.text())});page.on('requestfailed',req=>console.log('Overlay request:',req.url(),req.failure()?.errorText));await page.goto('https://app.roll20.net/editor/?manual=1');
  await expect(page.locator('#five-bones-overlay')).toHaveCount(1);
  expect(await page.locator('#five-bones-overlay').evaluate(el=>el.shadowRoot)).toBeNull();
  const cdp=await context.newCDPSession(page);
  // Only this test disables public-origin-to-loopback checks: the API is local,
  // while the simulated host uses an HTTPS public origin. Production uses public HTTPS.
  async function nodes(){const {root}=await cdp.send('DOM.getDocument',{depth:-1,pierce:true});const all:any[]=[];const visit=(node:any)=>{all.push(node);for(const n of [...node.children||[],...node.shadowRoots||[]])visit(n)};visit(root);return all}
  async function invoke(className:string,fn:string){const all=await nodes();const node=all.find(n=>{const i=n.attributes?.indexOf('class');return i>=0&&n.attributes[i+1].split(' ').includes(className)});if(!node)throw Error('Missing overlay node '+className);const {object}=await cdp.send('DOM.resolveNode',{nodeId:node.nodeId});const {result}=await cdp.send('Runtime.callFunctionOn',{objectId:object.objectId,functionDeclaration:fn,returnByValue:true});return result.value}
  expect(await invoke('window','function(){return this.hidden}')).toBe(true);
  await invoke('launcher','function(){this.click()}');expect(await invoke('window','function(){return this.hidden}')).toBe(false);
  expect(await invoke('bones','function(){return this.textContent.includes("Take a seat by the fire")}')).toBe(true);
  await expect.poll(()=>invoke('title-art','function(){return this.complete && this.naturalWidth>0}')).toBe(true);
  await invoke('bones',`function(){this.querySelector('.rules-trigger').click()}`);
  expect(await invoke('rules-dialog','function(){return this.open && this.matches(":modal")}')).toBe(true);
  await page.keyboard.press('Escape');expect(await invoke('rules-dialog','function(){return this.open}')).toBe(false);
  const host=await (await request.post('http://localhost:18000/api/v1/rooms',{data:{name:'Overlay table'}})).json();
  async function fill(index:number,value:string){await invoke('bones',`function(){this.querySelectorAll('input')[${index}].focus()}`);await page.keyboard.insertText(value)}
  await fill(0,'Overlay adventurer');await fill(2,host.roomId);await fill(3,host.inviteCode);await fill(4,'16');
  await invoke('bones',`function(){Array.from(this.querySelectorAll('button')).find(b=>b.textContent==='Join table').click()}`);
  await expect.poll(()=>invoke('bones',`function(){return this.textContent}`)).toContain('Overlay adventurer');
  expect(await page.evaluate(()=>Object.keys(localStorage).filter(k=>k.startsWith('fivebones:')))).toEqual([]);
  const standalone=await browser.newPage();await standalone.goto('/');
  await standalone.evaluate(session=>localStorage.setItem('fivebones:http://localhost:18000',JSON.stringify(session)),host);await standalone.reload();
  await expect(standalone.getByText('Connected',{exact:true})).toBeVisible();await expect(standalone.locator('.seat')).toContainText('Overlay adventurer');
  await standalone.getByRole('button',{name:'settings',exact:true}).click();await standalone.getByRole('button',{name:'Seat NPC with 125 GP',exact:true}).click();await expect(standalone.locator('.seat')).toHaveCount(2);
  await standalone.getByRole('button',{name:'Start next hand',exact:true}).click();await expect(standalone.locator('.table')).toHaveAttribute('data-phase','BETTING_1');
  await expect.poll(()=>invoke('table',`function(){return this.dataset.phase==='BETTING_1'}`)).toBe(true);
  expect(await standalone.locator('.seat').filter({hasText:'Overlay adventurer'}).locator('[aria-label$="revealed dice"]').count()).toBe(0);
  await expect.poll(()=>invoke('dice','function(){const images=[...this.querySelectorAll("img.pip-image")];return images.length===5 && images.every(image=>image.complete && image.naturalWidth>0 && /pip[1-6]-/.test(image.src))}')).toBe(true);
  await standalone.close();
  // Header keyboard movement persists through a reload; the extension never reads the sheet input.
  await invoke('handle','function(){this.dispatchEvent(new KeyboardEvent("keydown",{key:"ArrowLeft",bubbles:true}))}');
  const left=await invoke('window','function(){return this.style.left}');
  await page.reload();await expect(page.locator('#five-bones-overlay')).toHaveCount(1);
  await expect.poll(()=>invoke('window','function(){return this.style.left}')).toBe(left);
  await expect.poll(()=>invoke('bones',`function(){return this.textContent.includes('Overlay adventurer')}`)).toBe(true);
  expect(await page.locator('[name="attr_gp"]').inputValue()).toBe('999');
  await invoke('launcher','function(){this.click()}');await invoke('window','function(){this.style.width="700px"}');await expect.poll(()=>invoke('window','function(){return this.offsetWidth}')).toBe(700);
  expect(await invoke('bones','function(){return this.scrollWidth<=this.clientWidth}')).toBe(true);
  await page.screenshot({path:'test-results/overlay.png'});
  await invoke('window','function(){this.style.width="340px"}');
  await expect.poll(()=>invoke('bones','function(){return this.scrollWidth<=this.clientWidth}')).toBe(true);
 }finally{await context.close();await fs.rm(dir,{recursive:true,force:true})}
});

test('extension defaults to belwether and remembers isolated player and DM access',async({request,browser})=>{
 const access=await (await request.post('http://localhost:18000/api/v1/campaigns/belwether/dm-access',{data:{hostSecret:''}})).json();
 const gm=await browser.newPage();
 await gm.goto('/?room=belwether&isdm=1');await gm.evaluate(token=>localStorage.setItem('fivebones:campaign:http://localhost:18000:belwether:dm',JSON.stringify(token)),access.dmToken);await gm.reload();
 const status=await (await request.get('http://localhost:18000/api/v1/campaigns/belwether')).json();
 if(status.available){await expect(gm.getByText('Connected',{exact:true})).toBeVisible();if(!status.ended){await gm.getByRole('button',{name:'settings',exact:true}).click();gm.once('dialog',d=>d.accept());await gm.getByRole('button',{name:'End session',exact:true}).click()}await expect(gm.getByRole('button',{name:'Start fresh belwether session',exact:true})).toBeEnabled();gm.once('dialog',d=>d.accept());await gm.getByRole('button',{name:'Start fresh belwether session',exact:true}).click()}
 else{await expect(gm.getByRole('button',{name:'Start belwether session',exact:true})).toBeEnabled();await gm.getByRole('button',{name:'Start belwether session',exact:true}).click()}
 await expect(gm.getByText('Connected',{exact:true})).toBeVisible();await expect(gm.locator('.seat')).toHaveCount(0);
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'bones-campaign-extension-'));
 const extension='/tmp/fivebones-e2e-extension';
 const context=await chromium.launchPersistentContext(dir,{headless:true,channel:process.env.CHROMIUM_EXECUTABLE?undefined:'chromium',executablePath:process.env.CHROMIUM_EXECUTABLE,args:['--disable-features=LocalNetworkAccessChecks,LocalNetworkAccessChecksWebSockets','--disable-extensions-except='+extension,'--load-extension='+extension],viewport:{width:1280,height:900}});
 try{
  await context.route('https://app.roll20.net/editor/**',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><title>Controlled editor</title><input name="attr_gp" value="999">'}));
  const page=await context.newPage();await page.goto('https://app.roll20.net/editor/?room=belwether');await expect(page.locator('#five-bones-overlay')).toHaveCount(1);
  const cdp=await context.newCDPSession(page);
  async function invoke(className:string,fn:string){const {root}=await cdp.send('DOM.getDocument',{depth:-1,pierce:true});const all:any[]=[];const visit=(node:any)=>{all.push(node);for(const n of [...node.children||[],...node.shadowRoots||[]])visit(n)};visit(root);const node=all.find(n=>{const i=n.attributes?.indexOf('class');return i>=0&&n.attributes[i+1].split(' ').includes(className)});if(!node)throw Error('Missing '+className);const {object}=await cdp.send('DOM.resolveNode',{nodeId:node.nodeId});const {result}=await cdp.send('Runtime.callFunctionOn',{objectId:object.objectId,functionDeclaration:fn,returnByValue:true});return result.value}
  await expect.poll(()=>invoke('bones','function(){return this.textContent}')).toContain('Join Belwether');expect(await invoke('window','function(){return this.hidden}')).toBe(false);
  expect(await invoke('bones','function(){return this.querySelectorAll("input").length}')).toBe(3);
  async function fill(index:number,value:string){await invoke('bones',`function(){this.querySelectorAll('input')[${index}].focus()}`);await page.keyboard.insertText(value)}
  await fill(0,'One-click adventurer');await fill(2,'16');await invoke('bones',`function(){Array.from(this.querySelectorAll('button')).find(b=>b.textContent==='Join belwether').click()}`);
  await expect.poll(()=>invoke('bones','function(){return this.textContent}')).toContain('Connected');await expect(gm.locator('.seat')).toContainText('One-click adventurer');
  await page.reload();await expect.poll(()=>invoke('bones','function(){return this.textContent}')).toContain('Connected');await expect(gm.locator('.seat')).toHaveCount(1);
  expect(await page.evaluate(()=>Object.keys(localStorage).filter(k=>k.startsWith('fivebones:')))).toEqual([]);
  await page.goto('https://app.roll20.net/editor/?room=belwether&isdm=1');await expect.poll(()=>invoke('bones','function(){return this.textContent}')).toContain('DM access key');
  await invoke('bones',`function(){Array.from(this.querySelectorAll('button')).find(b=>b.textContent==='Remember DM access').click()}`);
  await expect.poll(()=>invoke('bones','function(){return this.textContent}')).toContain('DM private actions');
  await page.goto('https://app.roll20.net/editor/?room=belwether');await expect.poll(()=>invoke('bones','function(){return this.textContent}')).toContain('DM private actions');expect(await invoke('bones','function(){return this.textContent.includes("DM access key")}')).toBe(false);
  expect(await page.evaluate(()=>Object.keys(localStorage).filter(k=>k.startsWith('fivebones:')))).toEqual([]);expect(await page.locator('[name="attr_gp"]').inputValue()).toBe('999');
 }finally{await gm.close();await context.close();await fs.rm(dir,{recursive:true,force:true})}
});
