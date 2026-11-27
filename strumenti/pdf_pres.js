const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();
const pg=await b.newPage({viewport:{width:1920,height:1080}});
await pg.goto('http://localhost:8777/presentazione/',{waitUntil:'networkidle'});await pg.waitForTimeout(2500);
await pg.emulateMedia({media:'print'});
await pg.pdf({path:process.argv[2],width:'1920px',height:'1080px',printBackground:true,preferCSSPageSize:true});
await pg.emulateMedia({media:'screen'});
const n=await pg.$$eval('.slot',e=>e.length);
// overflow check: any element extending beyond section bounds
const of=await pg.$$eval('.slot>section',ss=>ss.map(s=>{const r=s.getBoundingClientRect();let m=0;s.querySelectorAll('*').forEach(e=>{const q=e.getBoundingClientRect();if(q.width&&getComputedStyle(e).position!=='absolute'){m=Math.max(m,q.bottom-r.top)}});return [s.id,Math.round(m)]}).filter(x=>x[1]>1080-120));
console.log(n,JSON.stringify(of));
await b.close();})();
