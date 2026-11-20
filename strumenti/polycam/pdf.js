// fogli.html -> PDF A3 e un'anteprima JPG per foglio
const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1588,height:1123}});
await p.goto('http://localhost:8768/fogli.html');await p.waitForLoadState('networkidle');await p.evaluate(()=>document.fonts.ready);
await p.pdf({path:process.argv[2],width:'420mm',height:'297mm',printBackground:true,preferCSSPageSize:true});
const fs=await p.$$('section.f');for(let i=0;i<fs.length;i++)await fs[i].screenshot({path:`${process.argv[3]}/f${i+1}.png`});await b.close();})();
