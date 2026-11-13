// End-to-end protocol fixtures, not claims of AI drawing quality.
// Real bundled retrieval, prompt construction, audit, revision, reconstruction,
// exporters, image bytes, PDF extraction and restart persistence are exercised.
import assert from 'node:assert/strict';
import {mkdtemp,readFile,writeFile,mkdir,stat} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createRuntime} from './runtime.mjs';
const project=await mkdtemp(join(tmpdir(),'figureforge-skill-test-'));
let runtime=await createRuntime(project);let modelCalls=0;
const transcript=[];
const call=async(action,input)=>{
  const r=await fetch(runtime.origin+'/control/'+action,{method:input?'POST':'GET',headers:{Authorization:'Bearer '+runtime.token,...(input?{'Content-Type':'application/json'}:{})},body:input?JSON.stringify(input):undefined});
  const result=await r.json();assert.equal(r.status,200,JSON.stringify(result));return result;
};
const pause=()=>new Promise(r=>setTimeout(r,100));
async function job(action,options={},handler){
  const {id}=await call('run',{action,options});const deadline=Date.now()+180000;
  while(Date.now()<deadline){
    const state=await call('status');const j=state.jobs.find(j=>j.id===id);
    if(j.state==='failed')throw Error(action+': '+j.error);
    if(j.state==='completed')return j.result;
    for(const p of state.pending){if(!handler)throw Error('Unexpected model request in '+action);
      const request=JSON.parse(await readFile(join(p.directory,'request.json'),'utf8'));transcript.push({action,endpoint:request.endpoint,body:request.body});modelCalls++;
      const response=await handler(request.body,p);
      await call('respond',{id:p.id,...response,actualModel:'offline-test-fixture'});
    }
    if(state.figure?.reviewPending){const review=await call('review');assert.equal(review.images.length>=2,true);await call('accept-review',{});}
    await pause();
  }
  throw Error('Timed out '+action);
}
const svg=title=>`<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900"><rect id="background" data-role="background" data-editable="true" width="1600" height="900" fill="#ffffff"/><text id="title" data-role="label" data-editable="true" x="80" y="100" font-family="Arial" font-size="44" fill="#172b4d">${title}</text><rect id="request" data-role="module" data-editable="true" x="90" y="240" width="550" height="400" rx="12" fill="#e0ecff" stroke="#345ca8" stroke-width="3"/><rect id="authorize" data-role="module" data-editable="true" x="960" y="240" width="550" height="400" rx="12" fill="#e0f1e9" stroke="#287b5c" stroke-width="3"/><text id="input" data-role="label" data-editable="true" x="150" y="330" font-size="30" fill="#172b4d">User intent</text><text id="output" data-role="label" data-editable="true" x="1020" y="330" font-size="30" fill="#172b4d">Authorized action</text><line id="flow" data-role="connector" data-editable="true" x1="665" y1="430" x2="925" y2="430" stroke="#345ca8" stroke-width="3"/></svg>`;
try{
  console.log('Testing real offline CLIP + BM25 retrieval');
  const found=await job('search',{query:'agent authorization intent safety clarification pipeline',limit:8});
  assert.equal(found.boot.phase,'ready');assert.equal(found.results.length,8);assert.ok(found.results.every(f=>Number.isFinite(f.matchScore)));
  const ids=found.results.slice(0,4).map(f=>f.id);
  await job('select',{ids});
  await job('configure',{paper:'Synthetic integration fixture: explicit user intent authorizes actions; clarification resolves uncertain recipients. No empirical results.',target:'pipeline',mode:'svg',pass:'two'});
  const grammar={density:{containers:2,modulesPerPanel:1,solidBorders:2,dashedBorders:0,connectors:1,boxFillPercent:40,nesting:'panel > label',variety:'flow modules',fill:'Simple synthetic fixture.'},strokes:{box:3,arrow:3,connector:3},typography:{title:44,panelHeader:30,label:24,note:18},palette:{background:'#ffffff',primary:'#345ca8',accent:'#287b5c',neutral:'#172b4d',others:[]},layout:'Two groups connected left to right',panels:[],layoutBlueprint:[],topology:{anchor:'flow',zones:'left and right',flow:'left to right',spacing:'large gutter'},styleFingerprint:{background:'white'},elements:'rectangles and labels',hierarchy:'title and two steps',representative:ids,imageRefIds:ids.slice(0,3),refinedPrompt:'Synthetic protocol fixture, not a visual analysis claim.'};
  console.log('Testing original two-pass SVG generation and repair queue');
  let analyzed=false,svgCalls=0;
  const generated=await job('generate',{},async(body,p)=>{
    if(body.messages[0]?.content?.includes('design analyst')){analyzed=true;assert.equal(p.attachments.length,4);return {text:JSON.stringify(grammar)};}
    assert.equal(analyzed,true);assert.equal(body.reasoning_effort,'max');svgCalls++;
    return {text:svgCalls===1?svg('Intent safety fixture').replace('</svg>','<text id="collision" data-role="label" data-editable="true" x="150" y="330" font-size="30">Overlapping label</text></svg>'):svg('Intent safety fixture')};
  });
  assert.equal(generated.hasSvg,true);assert.ok(generated.nodeCount>=7);
  assert.equal(svgCalls,2,'The deliberately overlapping draft must enter the original repair loop once');
  console.log('Testing SVG, PNG, native PPTX, VSDX and draw.io exports');
  const exports=await job('export',{formats:['svg','png','pptx','drawio','vsdx']});
  assert.equal(exports.artifacts.length,5);
  for(const a of exports.artifacts)assert.ok((await stat(a.path)).size>50);
  const pptx=await readFile(exports.artifacts.find(a=>a.format==='pptx').path);assert.ok(pptx.includes(Buffer.from('ppt/slides/slide1.xml')));assert.ok(pptx.includes(Buffer.from('User intent')));assert.ok(!pptx.includes(Buffer.from('<p:pic>')));
  const drawio=await readFile(exports.artifacts.find(a=>a.format==='drawio').path,'utf8');assert.match(drawio,/<mxCell/);
  console.log('Testing original revision, review gate and version activation');
  const revised=await job('revise',{prompt:'Change the title to Verified intent safety fixture. Keep other content.'},async body=>{
    assert.ok(body.messages[0].content.some(p=>p.type==='image_url'));return {text:svg('Verified intent safety fixture')};
  });
  assert.equal(revised.versions.length,2);await job('activate-version',{});
  const second=await job('export',{formats:['svg']});assert.match(await readFile(second.artifacts[0].path,'utf8'),/Verified intent safety fixture/);
  console.log('Testing PDF extraction and host-agent content selection');
  const doc=await runtime.page.context().newPage();await doc.setContent('<h1>Intent Authorization Study</h1><p>'+('An agent must distinguish user authorization from inferred task details. A clarification establishes the intended recipient before sharing a document. This fixture contains no benchmark results. ').repeat(4)+'</p>');
  const pdf=join(project,'fixture.pdf');await doc.pdf({path:pdf});await doc.close();
  const parsed=await job('parse-pdf',{file:pdf,contentMode:'intent'},async body=>{
    const text=JSON.stringify(body);assert.ok(text.includes('Intent Authorization Study')||text.includes('application/pdf'));
    return {text:JSON.stringify({title:'Intent Authorization Study',abstract:'Synthetic document.',selectedSections:[{section:'page 1',summary:'Authorization precedes sharing.',evidence:'page 1'}],figurePrompt:'Synthetic parsed paper: clarify the recipient before sharing.'})};
  });assert.match(parsed.paper,/Synthetic parsed paper/);
  console.log('Testing bitmap generation + current single whole-image reconstruction');
  await job('configure',{mode:'image',pass:'direct',ratio:'16:9',resolution:'1K',paper:'Synthetic bitmap protocol fixture.'});
  const imageData=await runtime.page.evaluate(()=>{const c=document.createElement('canvas');c.width=1280;c.height=720;const x=c.getContext('2d');x.fillStyle='white';x.fillRect(0,0,1280,720);x.fillStyle='#e0ecff';x.fillRect(100,180,450,300);x.fillStyle='#172b4d';x.font='40px Arial';x.fillText('Authorization',130,260);return c.toDataURL();});
  let imageRequests=0,reconstructionRequests=0;
  const bitmap=await job('generate',{},async(body,p)=>{
    if(p.kind==='image'){imageRequests++;assert.equal(body.size,'1280x720');assert.ok(p.attachments.length>0);return {imageData};}
    reconstructionRequests++;assert.equal(body.max_tokens,128000);assert.ok(p.attachments.length>=1);
    return {text:JSON.stringify({canvas:{width:1280,height:720},nodes:[{id:'bg',type:'rect',x:0,y:0,w:1280,h:720,fill:'#ffffff'},{id:'box',type:'rect',x:100,y:180,w:450,h:300,fill:'#e0ecff'},{id:'label',type:'text',x:130,y:220,w:350,h:50,text:'Authorization',fontSize:40,fontFamily:'Arial',fill:'#172b4d'}]})};
  });
  assert.equal(imageRequests,1);assert.equal(reconstructionRequests,1);assert.equal(bitmap.reconstruction.pipeline,'direct-whole-image-v1');assert.equal(bitmap.qualityState,'not-run');
  const bitExports=await job('export',{formats:['svg','png','pptx']});assert.ok(bitExports.artifacts.some(a=>a.path.includes('draft-unverified')));
  console.log('Testing unchanged native Gemini provider request profile');
  await job('configure',{mode:'image',provider:'infistar',imageModel:'gemini-3.1-flash-image-preview',pass:'direct',resolution:'1K'});
  let nativeCalls=0;
  await job('generate',{},async(body,p)=>{
    if(p.kind==='image'){nativeCalls++;assert.ok(body.contents[0].parts.some(x=>x.inlineData));assert.ok(p.attachments.length>0);return {imageData};}
    return {text:JSON.stringify({canvas:{width:1280,height:720},nodes:[{id:'title',type:'text',x:130,y:220,w:350,h:50,text:'Authorization',fontSize:40,fill:'#172b4d'}]})};
  });assert.equal(nativeCalls,1);
  console.log('Testing complete uploaded-reference byte preservation');
  const upload=join(project,'custom-reference.png');const uploadBytes=Buffer.from(imageData.split(',')[1],'base64');await writeFile(upload,uploadBytes);
  await job('upload-references',{files:[upload]});
  console.log('Testing project restart and preserved version history');
  const before=(await call('status')).figure;await runtime.close();runtime=await createRuntime(project);
  const after=(await call('status')).figure;assert.equal(after.versions.length,before.versions.length);assert.equal(after.nodeCount,before.nodeCount);assert.equal(after.selected.length,5);
  const saved=JSON.parse(await readFile(join(project,'.figureforge/state.json'),'utf8'));assert.deepEqual(Buffer.from(saved.uploads[0].localURL.split(',')[1],'base64'),uploadBytes);
  console.log('Testing interrupted recognition and recovery from retained bitmap');
  await call('run',{action:'reconstruct',options:{}});
  let interrupted;
  for(let n=0;n<100;n++){const s=await call('status');if(s.pending.length){interrupted=s.pending[0];break;}await pause();}
  assert.ok(interrupted);await runtime.close();runtime=await createRuntime(project);
  const recovered=(await call('status')).figure;assert.equal(recovered.reconPending,false);assert.equal(recovered.hasBitmap,true);
  assert.equal(JSON.parse(await readFile(join(interrupted.directory,'status.json'),'utf8')).state,'cancelled');
  await job('reconstruct',{},async()=>({text:JSON.stringify({canvas:{width:1280,height:720},nodes:[{id:'label',type:'text',x:130,y:220,w:350,h:50,text:'Authorization',fontSize:40,fill:'#172b4d'}]})}));
  assert.equal((await call('status')).blockedNetwork.length,0);assert.deepEqual((await call('status')).errors,[]);
  const report={ok:true,project,modelCalls,figureCount:after.figureCount,checks:['offline hybrid retrieval','original two-pass SVG generation','geometry repair queue','five export formats','revision and explicit review gate','PDF extraction','bitmap generation','single whole-image recognition','native Gemini request profile','uploaded reference bytes','unverified quality marker retained','restart and history','interrupted recognition recovery'],fixtureResponses:true,externalModelCalls:0};
  await writeFile(join(project,'validation.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
}finally{await runtime.close();}
