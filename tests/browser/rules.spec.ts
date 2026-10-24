import {test,expect} from '@playwright/test';

test('orientation artwork and accessible hands/rules popup',async({page})=>{
 await page.setViewportSize({width:1280,height:800});await page.goto('/');
 await expect(page.getByRole('heading',{name:'Five Bones',level:1})).toBeVisible();
 const title=page.getByRole('img',{name:'Five Bones',exact:true});await expect(title).toBeVisible();
 expect(await title.evaluate(async image=>{const img=image as HTMLImageElement;await img.decode();return img.naturalWidth>0})).toBe(true);
 await expect(page.locator('header h1')).toHaveText('');
 await expect(page.locator('header')).not.toContainText(/Bellwether|Fortune favors|Fictional campaign|No sheet writes/i);
 const artwork=()=>page.locator('.bones').evaluate(el=>getComputedStyle(el).backgroundImage);
 await expect.poll(artwork).toContain('landscape_bg');
 const loaded=()=>page.locator('.bones').evaluate(async el=>{
  const url=getComputedStyle(el).backgroundImage.match(/url\("?([^"\)]+)"?\)/)?.[1];
  if(!url)return false;const image=new Image();image.src=url;await image.decode();return image.naturalWidth>0;
 });
 expect(await loaded()).toBe(true);
 const opener=page.getByRole('button',{name:'Hands & rules',exact:true});await opener.click();
 const dialog=page.getByRole('dialog',{name:'Hands & rules'});await expect(dialog).toBeVisible();
 await expect(dialog.locator('tbody tr')).toHaveCount(8);
 const diceArt=dialog.locator('.example-dice .pip-image');await expect(diceArt).toHaveCount(40);
 expect(await diceArt.evaluateAll(async images=>{
  await Promise.all(images.map(image=>(image as HTMLImageElement).decode()));
  return images.every(image=>(image as HTMLImageElement).naturalWidth>0);
 })).toBe(true);
 const artworkFaces=await diceArt.evaluateAll(images=>[...new Set(images.map(image=>(image as HTMLImageElement).src.match(/pip([1-6])(?:-|\.png)/)?.[1]))].sort());
 expect(artworkFaces).toEqual(['1','2','3','4','5','6']);
 expect(await dialog.locator('.example-dice').evaluateAll(examples=>examples.every(example=>{
  const values=example.getAttribute('aria-label')!.split(' · ');
  return [...example.querySelectorAll('img')].every((image,i)=>image.src.match(/pip([1-6])(?:-|\.png)/)?.[1]===values[i]);
 }))).toBe(true);

 expect(await dialog.locator('tbody th').allTextContents()).toEqual([
  'Five of a kindAll five dice match.','Four of a kindFour dice match.',
  'Full houseThree matching dice and a pair.','StraightFive consecutive faces: 1–5 or 2–6.',
  'Three of a kindThree dice match; two different kickers.','Two pairTwo different pairs and one kicker.',
  'One pairOne pair and three different kickers.','High bonesNone of the combinations above.',
 ]);
 await expect(dialog).toContainText('The Widowmaker: 6 · 6 · 6 · 1 · 1');
 await expect(dialog).toContainText('at most two raises in total');
 await page.keyboard.press('Escape');await expect(dialog).not.toBeVisible();await expect(opener).toBeFocused();
 await page.setViewportSize({width:390,height:844});await expect.poll(artwork).toContain('portrait_bg');expect(await loaded()).toBe(true);
 await opener.click();await expect(dialog).toBeVisible();
 expect(await dialog.evaluate(el=>el.getBoundingClientRect().width)).toBeLessThanOrEqual(390);
 await page.screenshot({path:'test-results/rules-portrait.png'});
 await dialog.getByRole('button',{name:'Back to the table'}).click();await expect(dialog).not.toBeVisible();
});
