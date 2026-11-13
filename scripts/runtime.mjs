import http from 'node:http';
import {readFile,writeFile,mkdir,access,rename,copyFile} from 'node:fs/promises';
import {createHash,randomUUID} from 'node:crypto';
import {dirname,resolve,join,extname,sep,basename} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require('./vendor/playwright-core');
export const skillRoot=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const engineRoot=join(skillRoot,'assets/figureforge');
const mime={'.html':'text/html; charset=utf-8','.mjs':'text/javascript','.js':'text/javascript','.json':'application/json','.css':'text/css','.wasm':'application/wasm','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.pdf':'application/pdf'};
export async function chromePath(){
  const candidates=[process.env.FIGUREFORGE_BROWSER,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome','/usr/bin/google-chrome-stable','/usr/bin/chromium','/usr/bin/chromium-browser',
    process.env.PROGRAMFILES&&join(process.env.PROGRAMFILES,'Google/Chrome/Application/chrome.exe'),
    process.env['PROGRAMFILES(X86)']&&join(process.env['PROGRAMFILES(X86)'],'Microsoft/Edge/Application/msedge.exe'),
    process.env.LOCALAPPDATA&&join(process.env.LOCALAPPDATA,'Google/Chrome/Application/chrome.exe')].filter(Boolean);
  for(const candidate of candidates){try{await access(candidate);return candidate;}catch{}}
  throw Error('Chrome/Chromium not found. Set FIGUREFORGE_BROWSER to its executable path.');
}
export async function atomicJSON(path,value){const temp=path+'.'+randomUUID()+'.tmp';await writeFile(temp,JSON.stringify(value,null,2)+'\n');await rename(temp,path);}
const safeId=id=>typeof id==='string'&&/^[a-zA-Z0-9_-]+$/.test(id);
async function readBody(req){const chunks=[];let size=0;for await(const b of req){size+=b.length;if(size>128*1024*1024)throw Error('Request exceeds 128 MiB');chunks.push(b);}return Buffer.concat(chunks);}
function json(res,status,value){res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(value));}
function dataURL(bytes,name){return 'data:'+(mime[extname(name).toLowerCase()]||'application/octet-stream')+';base64,'+bytes.toString('base64');}

export async function createRuntime(project){
  project=resolve(project);await mkdir(join(project,'.figureforge'),{recursive:true});
  for(const dir of ['requests','jobs','outputs','inputs'])await mkdir(join(project,dir),{recursive:true});
  const token=randomUUID(),pending=new Map(),jobs=new Map(),errors=[],network=[],uploaded=new Map();
  let page,context,origin,activeJob,closing=false;
  const stateFile=join(project,'.figureforge/state.json');
  const models={data:[{id:'agent-vision',available:true,supported_reasoning_efforts:['max'],input_modalities:['text','image'],is_default:true}],default_model:'agent-vision',reasoning_effort:'max'};
  const status=()=>({project,pid:process.pid,ready:!!page,activeJob:activeJob?.id||null,jobs:[...jobs.values()],pending:[...pending.values()].map(x=>x.info),errors:errors.slice(-12),blockedNetwork:network.slice(-12)});
  async function enqueue(req,res,raw){
    const id='request-'+randomUUID(),directory=join(project,'requests',id);await mkdir(directory);
    const type=req.headers['content-type']||'';
    let body;
    if(type.includes('multipart/form-data')){
      const form=await new Request(origin+req.url,{method:'POST',headers:{'content-type':type},body:raw}).formData();body={};
      for(const [key,value]of form){
        const val=typeof value==='string'?value:dataURL(Buffer.from(await value.arrayBuffer()),value.name);
        if(key in body)body[key]=Array.isArray(body[key])?[...body[key],val]:[body[key],val];else body[key]=val;
      }
    }else body=JSON.parse(raw.toString('utf8'));
    const attachments=[];
    async function materialize(value){
      if(typeof value==='string'){
        if(uploaded.has(value))value=uploaded.get(value);
        const m=/^data:([^;,]+);base64,([\s\S]+)$/.exec(value);
        if(!m)return value;
        const extension={'image/png':'png','image/jpeg':'jpg','image/webp':'webp','application/pdf':'pdf'}[m[1]]||'bin';
        const file=join(directory,'attachment-'+(attachments.length+1)+'.'+extension),bytes=Buffer.from(m[2],'base64');
        attachments.push({number:attachments.length+1,path:file,mime:m[1],bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')});
        await writeFile(file,bytes);return '[ATTACHMENT '+attachments.length+': '+file+']';
      }
      if(Array.isArray(value)){const out=[];for(const v of value)out.push(await materialize(v));return out;}
      if(value&&typeof value==='object'){
        const media=value.mimeType||value.mime_type||value.media_type;
        if(media&&typeof value.data==='string'&&/^(image\/|application\/pdf)/.test(media))return {...value,data:await materialize('data:'+media+';base64,'+value.data)};
        const out={};for(const[k,v]of Object.entries(value))out[k]=await materialize(v);return out;
      }
      return value;
    }
    const nativeGemini=/:generateContent|:streamGenerateContent/.test(req.url),anthropic=/\/messages(?:\?|$)/.test(req.url);
    const readable=await materialize(body),kind=req.url.includes('/images/')||(nativeGemini&&(body.generationConfig?.responseModalities||[]).includes('IMAGE'))?'image':'text';
    await writeFile(join(directory,'wire-body.bin'),raw);
    await atomicJSON(join(directory,'request.json'),{endpoint:req.url,contentType:type,body});
    await atomicJSON(join(directory,'readable-request.json'),readable);
    await atomicJSON(join(directory,'attachments.json'),attachments);
    const prompt='# FigureForge inference request\n\nThe bundled workflow produced this request unchanged. Read every attached image/document in order. Return the requested assistant content only. Model IDs are transport labels; record actual host/tool identity separately.\n\n'+JSON.stringify(readable,null,2)+'\n';
    await writeFile(join(directory,'prompt.md'),prompt);
    const info={id,job:activeJob?.id||null,kind,directory,prompt:join(directory,'prompt.md'),attachments,requestedModel:body.model||null,requestedReasoningEffort:body.reasoning_effort||null,state:'pending'};
    await atomicJSON(join(directory,'status.json'),info);
    pending.set(id,{info,res,body,nativeGemini,anthropic});
    res.on('close',()=>{if(pending.has(id)){pending.delete(id);info.state='cancelled';void atomicJSON(join(directory,'status.json'),info);}});
  }
  async function respond(input){
    if(!safeId(input.id)||!pending.has(input.id))throw Error('No pending request with that ID');
    const item=pending.get(input.id),{info,res,body}=item;
    let envelope;
    if(input.error){envelope={error:{message:String(input.error)}};}
    else if(info.kind==='image'){
      if(!input.imageData?.startsWith('data:image/'))throw Error('Image request requires an image file');
      const match=/^data:([^;]+);base64,(.+)$/s.exec(input.imageData);if(!match)throw Error('Invalid image');
      envelope=item.nativeGemini?{candidates:[{content:{role:'model',parts:[{inlineData:{mimeType:match[1],data:match[2]}}]},finishReason:'STOP'}]}:{created:Math.floor(Date.now()/1000),data:[{b64_json:match[2],mimeType:match[1]}]};
    }else{
      if(typeof input.text!=='string'||!input.text.trim())throw Error('Text request requires nonempty text');
      envelope={id:input.id,object:'chat.completion',model:input.actualModel||'host-agent',choices:[{index:0,message:{role:'assistant',content:input.text},finish_reason:'stop'}]};
      if(item.anthropic)envelope={id:input.id,type:'message',role:'assistant',model:input.actualModel||'host-agent',content:[{type:'text',text:input.text}],stop_reason:'end_turn'};
      if(item.nativeGemini)envelope={candidates:[{content:{role:'model',parts:[{text:input.text}]},finishReason:'STOP'}]};
    }
    await atomicJSON(join(info.directory,'response.json'),{actualModel:input.actualModel||null,actualReasoningEffort:input.actualReasoningEffort||null,envelope});
    if(input.text)await writeFile(join(info.directory,'response.txt'),input.text);
    info.state=input.error?'failed':'answered';await atomicJSON(join(info.directory,'status.json'),info);pending.delete(input.id);
    json(res,input.error?400:200,envelope);return {id:input.id,state:info.state};
  }
  async function save(){
    if(!page||page.isClosed())return;
    const snapshot=await page.evaluate(()=>window.FigureForgeSkill.snapshot());
    await atomicJSON(stateFile,snapshot);
  }
  async function intake(path){
    const source=resolve(path),bytes=await readFile(source);
    const file=join(project,'inputs',createHash('sha256').update(bytes).digest('hex').slice(0,12)+'-'+basename(source));
    await writeFile(file,bytes);return file;
  }
  const evaluate=(name,arg)=>page.evaluate(({name,arg})=>window.FigureForgeSkill[name](arg),{name,arg});
  async function perform(action,o,job){
    switch(action){
      case 'configure':return evaluate('configure',o);
      case 'search':{
        await page.waitForFunction(()=>!window.FigureForgeSkill.status().boot.phase.endsWith('loading'),null,{timeout:310000});
        const found=await evaluate('search',o);
        found.results=found.results.map(f=>({...f,imagePath:join(engineRoot,f.image)}));return found;
      }
      case 'select':return evaluate('select',o.ids);
      case 'upload-references':{
        const paths=[];for(const file of o.files||[])paths.push(await intake(file));
        await page.locator('#refsUpload').setInputFiles(paths);await page.waitForFunction(()=>!document.querySelector('#refsUploadBtn').disabled);
        const error=await page.locator('#refsUploadStatus').textContent();if(error)throw Error(error);return evaluate('status');
      }
      case 'parse-pdf':{
        if(o.contentMode)await evaluate('configure',{contentMode:o.contentMode,contentQuery:o.contentQuery||''});
        await page.locator('#pdfFile').setInputFiles(await intake(o.file));
        await page.waitForFunction(()=>!document.querySelector('#uploadBtn').disabled,null,{timeout:0});
        const error=await page.locator('#parseErr').textContent();if(error)throw Error(error);return evaluate('status');
      }
      case 'analyze':return evaluate('analyze');
      case 'generate':{
        await evaluate('generate');
        // Original bitmap generation launches Step 4 asynchronously. Keep the
        // orchestration job alive until that existing task settles.
        await page.waitForFunction(()=>!window.FigureForgeSkill.exportState().reconPending,null,{timeout:0});
        const state=await evaluate('exportState');if(state.reconFailed)throw Error(state.reconError||'Bitmap preserved; editable reconstruction failed');
        return evaluate('status');
      }
      case 'import-svg':return evaluate('importSvg',await readFile(await intake(o.file),'utf8'));
      case 'import-bitmap':{
        await page.locator('#exportBitmapUpload').setInputFiles(await intake(o.file));
        await page.waitForFunction(()=>!document.querySelector('#exportBitmapUpload').disabled&&!!window.FigureForgeSkill.exportState().bitmap,null,{timeout:30000});
        return evaluate('status');
      }
      case 'reconstruct':return evaluate('reconstruct');
      case 'audit':return evaluate('audit');
      case 'activate-version':{
        const target=o.versionId?page.locator('.ff-version[data-version-id="'+o.versionId.replace(/[^a-zA-Z0-9_-]/g,'')+'"]'):page.locator('.ff-version').last();
        await target.locator('[data-build]').click();
        await page.waitForFunction(()=>!window.FigureForgeSkill.exportState().reconPending,null,{timeout:0});return evaluate('status');
      }
      case 'revise':{
        const target=o.versionId?page.locator('.ff-version[data-version-id="'+o.versionId.replace(/[^a-zA-Z0-9_-]/g,'')+'"]'):page.locator('.ff-version').last();
        await target.locator('[data-modify]').click();
        if(o.attachments?.length){const files=[];for(const f of o.attachments)files.push(await intake(f));await page.locator('.ff-revision-editor [data-files]').setInputFiles(files);}
        if(o.revisionMode)await page.locator('[data-revision-mode]').selectOption(o.revisionMode);
        await page.locator('.ff-revision-editor textarea').fill(o.prompt);
        await page.evaluate(()=>document.querySelector('.ff-revision-editor [data-submit]').onclick());
        const result=await evaluate('status');if(result.revisionError)throw Error(result.revisionError);return result;
      }
      case 'export':{
        const artifacts=[];for(const format of o.formats||['svg','png','pptx']){
          if(!['svg','png','pptx','drawio','vsdx'].includes(format))throw Error('Unsupported export '+format);
          if(format==='png'){
            const uri=await evaluate('preview',o.scale||2),file=join(project,'outputs',job.id+'.png');
            await writeFile(file,Buffer.from(uri.split(',')[1],'base64'));artifacts.push({format,path:file,source:'SVG raster preview'});continue;
          }
          await page.locator('[data-export="'+format+'"]').click();
          const downloadPromise=page.waitForEvent('download',{timeout:60000});
          await page.locator('#exportConfirm').click();const download=await downloadPromise;
          const file=join(project,'outputs',job.id+'-'+download.suggestedFilename());await download.saveAs(file);
          if(await download.failure())throw Error('Export download failed');artifacts.push({format,path:file});
        }
        const state=await evaluate('exportState');await atomicJSON(join(project,'outputs',job.id+'-scene.json'),state.scene);
        return {artifacts,nodeCount:state.scene?.nodes?.length||0,source:state.source,qualityState:state.recon?.qualityState||null};
      }
      default:throw Error('Unknown action: '+action);
    }
  }
  async function launchJob(input){
    if(activeJob)throw Error('Another job is running: '+activeJob.id);
    const job={id:'job-'+randomUUID(),action:input.action,state:'running',startedAt:new Date().toISOString()};jobs.set(job.id,job);activeJob=job;
    await atomicJSON(join(project,'jobs',job.id+'.json'),{...job,input:input.options||{}});
    void(async()=>{try{
      job.result=await perform(input.action,input.options||{},job);await save();job.state='completed';
    }catch(error){job.state='failed';job.error=error.message;try{await save();}catch{}}
      finally{job.finishedAt=new Date().toISOString();activeJob=null;await atomicJSON(join(project,'jobs',job.id+'.json'),job);}
    })();return {id:job.id,state:job.state};
  }
  const server=http.createServer(async(req,res)=>{
    try{
      const url=new URL(req.url,origin||'http://127.0.0.1');
      if(req.headers.host!==new URL(origin).host||(req.headers.origin&&req.headers.origin!==origin)){json(res,403,{error:'Loopback origin required'});return;}
      if(url.pathname.startsWith('/control/')){
        if(req.headers.authorization!=='Bearer '+token){json(res,403,{error:'Invalid control token'});return;}
        const input=req.method==='POST'?JSON.parse((await readBody(req)).toString('utf8')):{};
        let result;
        switch(url.pathname){
          case '/control/status':result={...status(),figure:page?await evaluate('status'):null};break;
          case '/control/run':result=await launchJob(input);break;
          case '/control/respond':result=await respond(input);break;
          case '/control/accept-review':await page.locator('[data-revision-accept]').click();result={accepted:true};break;
          case '/control/reject-review':await page.locator('[data-revision-reject]').click();result={cancelled:true};break;
          case '/control/review':{
            const review=await page.locator('.ff-revision-review').evaluate(el=>({text:el.innerText,images:[...el.querySelectorAll('img')].map(img=>({label:img.alt,data:img.src}))}));
            const images=[];let index=0;
            for(const item of review.images){const match=/^data:([^;]+);base64,([\s\S]+)$/.exec(item.data);if(!match)throw Error('Review contains a non-inline image');
              const extension={'image/svg+xml':'svg','image/png':'png','image/jpeg':'jpg','image/webp':'webp'}[match[1]]||'bin';
              const file=join(project,'outputs',activeJob.id+'-review-'+(++index)+'.'+extension);await writeFile(file,Buffer.from(match[2],'base64'));images.push({label:item.label,path:file});}
            result={text:review.text,images};break;
          }
          case '/control/stop':if(activeJob&&!input.force)throw Error('Job still running; use stop --force only to cancel it');json(res,200,{stopping:true});void close();return;
          default:throw Error('Unknown control command');
        }
        json(res,200,result);return;
      }
      if(url.pathname.startsWith('/agent/v1/')){
        if(url.pathname==='/agent/v1/models'&&req.method==='GET'){json(res,200,models);return;}
        if(url.pathname==='/agent/v1/proxy'&&req.method==='POST'){
          const packet=JSON.parse((await readBody(req)).toString('utf8'));
          await enqueue({url:packet.url,headers:{'content-type':packet.contentType}},res,Buffer.from(packet.bytes,'base64'));return;
        }
        if(req.method!=='POST'||!['/agent/v1/chat/completions','/agent/v1/images/generations','/agent/v1/images/edits'].includes(url.pathname))throw Error('Unsupported agent endpoint');
        await enqueue(req,res,await readBody(req));return;
      }
      if(url.pathname.startsWith('/agent-upload/')&&uploaded.has(url.href)){
        const match=/^data:([^;]+);base64,(.+)$/s.exec(uploaded.get(url.href));res.writeHead(200,{'Content-Type':match[1]});res.end(Buffer.from(match[2],'base64'));return;
      }
      if(req.method!=='GET'&&req.method!=='HEAD'){json(res,405,{error:'GET only'});return;}
      let path=decodeURIComponent(url.pathname);if(path.endsWith('/'))path+='index.html';
      const filename=resolve(engineRoot,'.'+path);
      if(!filename.startsWith(engineRoot+sep)||path.split(/[\\/]/).some(x=>x.startsWith('.'))){json(res,403,{error:'Invalid resource path'});return;}
      let bytes=await readFile(filename);
      if(path==='/forge/index.html'){
        let html=bytes.toString('utf8');
        const bridge=await readFile(join(skillRoot,'scripts/browser-bridge.js'),'utf8');
        const start=html.indexOf('<script type="module">'),end=html.indexOf('</script>',start);
        if(start<0||end<0)throw Error('Bundled module boundary not found');
        html=html.slice(0,end)+'\n'+bridge+'\n'+html.slice(end);
        html=html.replace('<head>','<head><script>window.FF_CODEX_BASE=location.origin+"/agent/v1";</script>');
        bytes=Buffer.from(html);
      }
      res.writeHead(200,{'Content-Type':mime[extname(filename)]||'application/octet-stream','Cache-Control':'no-store'});res.end(req.method==='HEAD'?undefined:bytes);
    }catch(error){if(!res.headersSent)json(res,error.code==='ENOENT'?404:400,{error:error.message});else res.end();}
  });
  async function close(){
    if(closing)return;closing=true;try{await save();}catch{}
    for(const item of pending.values()){
      item.info.state='cancelled';await atomicJSON(join(item.info.directory,'status.json'),item.info);
      if(!item.res.writableEnded)json(item.res,499,{error:{message:'Agent runtime stopped'}});
    }pending.clear();
    await context?.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));
  }
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});origin='http://127.0.0.1:'+server.address().port;
  try{
    const browser=await chromium.launch({headless:true,executablePath:await chromePath()});
    context=await browser.newContext({serviceWorkers:'block',acceptDownloads:true,viewport:{width:1500,height:1000}});
    context.on('close',()=>void browser.close());
    // All resources are local. There is deliberately no gallery/CDN/model fallback.
    await context.route('**/*',async route=>{
      const request=route.request(),u=new URL(request.url());
      if(u.origin===origin||['data:','blob:'].includes(u.protocol))return route.continue();
      // Preserve provider-specific request builders and route selection while
      // delivering their inference payloads to the same local host-agent queue.
      if(request.method()==='GET'&&/\/models$/.test(u.pathname))return route.fulfill({json:models});
      if(request.method()==='POST'&&u.href==='https://nonelinear.com.cn/api/upload-file'){
        const body=request.postDataJSON(),uri='data:image/'+(body.type==='.jpg'?'jpeg':body.type.slice(1))+';base64,'+body.image;
        const href=origin+'/agent-upload/'+randomUUID();uploaded.set(href,uri);return route.fulfill({json:{url:href}});
      }
      if(request.method()==='POST'&&(/\/(chat\/completions|images\/(generations|edits)|v1\/messages)$/.test(u.pathname)||/:generateContent$|:streamGenerateContent$/.test(u.pathname))){
        try{
          const response=await fetch(origin+'/agent/v1/proxy',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:u.href,contentType:request.headers()['content-type']||'application/json',bytes:(request.postDataBuffer()||Buffer.alloc(0)).toString('base64')})});
          return route.fulfill({status:response.status,contentType:'application/json',body:await response.text()});
        }catch{try{return await route.abort();}catch{return;}}
      }
      network.push({url:u.origin+u.pathname,reason:'external network disabled'});return route.abort();
    });
    page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));
    await page.goto(origin+'/forge/',{waitUntil:'domcontentloaded',timeout:60000});
    await page.waitForFunction(()=>!!window.FigureForgeSkill,null,{timeout:60000});
    let prior;try{prior=JSON.parse(await readFile(stateFile,'utf8'));}catch(error){if(error.code!=='ENOENT')throw error;}
    if(prior){
      if(prior.records?.length){await evaluate('restoreRecords',prior.records);await page.reload({waitUntil:'domcontentloaded'});await page.waitForFunction(()=>!!window.FigureForgeSkill);}
      await evaluate('restore',prior);
    }
    await atomicJSON(join(project,'.figureforge/connection.json'),{origin,token,pid:process.pid,skillRoot,startedAt:new Date().toISOString()});
    return {origin,token,status,close,project,page};
  }catch(error){await close();throw error;}
}
