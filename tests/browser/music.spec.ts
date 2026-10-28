import {test,expect} from '@playwright/test';

test('background music loops, starts after interaction, and can be disabled and resumed',async({page})=>{
 await page.goto('/');
 const music=page.locator('audio');
 await expect(music).toHaveAttribute('loop','');
 await expect(music).toHaveAttribute('src',/music.*\.mp3/);
 const disable=page.getByRole('button',{name:'Disable music',exact:true});
 await expect(disable).toBeVisible();
 const bounds=await disable.boundingBox();
 expect(bounds!.x).toBeLessThan(25);expect(bounds!.y).toBeLessThan(25);
 // A real user gesture also permits playback when the initial autoplay was blocked.
 await page.getByLabel('Character name',{exact:true}).click();
 await expect.poll(()=>music.evaluate((audio:HTMLAudioElement)=>!audio.paused&&audio.currentTime>0)).toBe(true);
 await disable.click();
 await expect(music).toHaveJSProperty('paused',true);
 const enable=page.getByRole('button',{name:'Enable music',exact:true});
 await expect(enable).toHaveAttribute('aria-pressed','true');
 // Other interactions must leave music disabled.
 await page.getByLabel('Character name',{exact:true}).click();
 await expect(music).toHaveJSProperty('paused',true);
 await enable.click();
 await expect.poll(()=>music.evaluate((audio:HTMLAudioElement)=>!audio.paused)).toBe(true);
 await expect(disable).toHaveAttribute('aria-pressed','false');
});
