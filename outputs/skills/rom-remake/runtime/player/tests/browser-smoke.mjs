// Run from a workspace with Playwright installed and the player dev server running.
// ROM_PATH=/path/to/local.nes PLAYER_URL=http://127.0.0.1:4317 node tests/browser-smoke.mjs
import {chromium} from 'playwright';
import assert from 'node:assert/strict';
if(!process.env.ROM_PATH)throw new Error('ROM_PATH must identify a local user-supplied NES ROM');
const browser=await chromium.launch({headless:true});
try{
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(process.env.PLAYER_URL||'http://127.0.0.1:4317');
 await page.locator('#rom').setInputFiles(process.env.ROM_PATH);
 await page.waitForFunction(()=>window.agarstra?.source && /candidate tiles loaded|fallback active/.test(document.getElementById('status').textContent));
 const result=await page.evaluate(()=>{agarstra.pause();agarstra.step(240);return{source:agarstra.source,stats:agarstra.stats,verification:agarstra.verify()}});
 assert.ok(result.stats.sourceInstances>0);assert.equal(result.verification.mismatches,0);
 await page.locator('#view').click();assert.equal(await page.locator('#original').isVisible(),true);
 await page.locator('#view').click();assert.equal(await page.locator('#world').isVisible(),true);
 const before=await page.evaluate(()=>agarstra.stats.loadedAssets);
 await page.locator('#reload').click();await page.waitForTimeout(500);assert.equal(await page.evaluate(()=>agarstra.stats.loadedAssets),before);
 assert.deepEqual(errors,[]);if(process.env.SCREENSHOT)await page.screenshot({path:process.env.SCREENSHOT});console.log(JSON.stringify(result,null,2));
}finally{await browser.close()}
