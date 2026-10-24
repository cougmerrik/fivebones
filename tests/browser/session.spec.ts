import {test,expect} from '@playwright/test';

test('end an empty session without a spurious hand warning',async({page})=>{
 await page.goto('/');await page.getByText('Host a table',{exact:true}).click();await page.getByRole('button',{name:'Create table as GM'}).click();await expect(page.getByText('Connected',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'settings',exact:true}).click();
 const end=page.getByRole('button',{name:'End session',exact:true});await expect(end).toBeEnabled();
 page.once('dialog',async dialog=>{expect(dialog.type()).toBe('confirm');expect(dialog.message()).toBe('End this session? The final ledger will remain available.');await dialog.dismiss()});
 await end.click();await expect(page.getByRole('button',{name:'Start next hand',exact:true})).toBeEnabled();
 page.once('dialog',async dialog=>{expect(dialog.message()).not.toMatch(/hand/i);await dialog.accept()});await end.click();
 await expect(page.locator('.tabletop')).toContainText('Session ended');await expect(end).toBeDisabled();
 await page.reload();await expect(page.getByText('Connected',{exact:true})).toBeVisible();await expect(page.locator('.tabletop')).toContainText('Session ended');
});
