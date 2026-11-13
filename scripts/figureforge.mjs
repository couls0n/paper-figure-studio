#!/usr/bin/env node
import {readFile,writeFile,mkdir,open} from 'node:fs/promises';
import {resolve,join,dirname,extname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawn} from 'node:child_process';
import {createRuntime,chromePath,skillRoot} from './runtime.mjs';
import {verify} from './verify.mjs';
const args=process.argv.slice(2),command=args.shift();
const print=value=>console.log(JSON.stringify(value,null,2));
const flag=name=>{const index=args.indexOf(name);return index<0?undefined:args[index+1];};
async function connect(project){
  const connection=JSON.parse(await readFile(join(project,'.figureforge/connection.json'),'utf8'));
  const u=new URL(connection.origin);if(u.hostname!=='127.0.0.1')throw Error('Runtime must be local');
  return async(action,input)=>{
    const response=await fetch(u.origin+'/control/'+action,{method:input?'POST':'GET',headers:{Authorization:'Bearer '+connection.token,...(input?{'Content-Type':'application/json'}:{})},body:input?JSON.stringify(input):undefined,signal:AbortSignal.timeout(60000)});
    const result=await response.json();if(!response.ok)throw Error(result.error||'Runtime error');return result;
  };
}
function compact(state){return {...state,jobs:state.jobs?.map(j=>({id:j.id,action:j.action,state:j.state,error:j.error,resultFile:join(state.project,'jobs',j.id+'.json')}))};}
try{
  if(command==='doctor'){print({node:process.version,minimumNode:20,browser:await chromePath(),skillRoot,transport:'host-agent request/response; no Codex CLI or API key required'});}
  else if(command==='verify'){const result=await verify();print(result);if(!result.ok)process.exitCode=1;}
  else if(command==='--daemon'){
    const runtime=await createRuntime(args[0]);console.log('FigureForge skill ready: '+runtime.project);
    for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>void runtime.close().then(()=>process.exit(0)));
  }else if(command==='start'){
    if(!args[0])throw Error('start requires a project directory');const project=resolve(args[0]);
    try{const call=await connect(project);const state=await call('status');print({alreadyRunning:true,...compact(state)});process.exit(0);}catch{}
    await mkdir(join(project,'.figureforge'),{recursive:true});
    const log=await open(join(project,'.figureforge/runtime.log'),'a');
    const child=spawn(process.execPath,[fileURLToPath(import.meta.url),'--daemon',project],{cwd:project,detached:true,stdio:['ignore',log.fd,log.fd]});child.unref();await log.close();
    const deadline=Date.now()+55000;let started=false;
    while(Date.now()<deadline){await new Promise(r=>setTimeout(r,500));try{
      const call=await connect(project),state=await call('status');if(state.pid!==child.pid)continue;
      print({started:true,...compact(state)});started=true;break;
    }catch{try{process.kill(child.pid,0);}catch{throw Error('Runtime exited; inspect '+join(project,'.figureforge/runtime.log'));}}}
    if(!started)throw Error('Startup is still pending; inspect runtime.log, then run status.');
  }else if(['run','status','requests','respond','fail','export','review','accept-review','reject-review','stop'].includes(command)){
    if(!args[0])throw Error(command+' requires a project directory');const project=resolve(args.shift()),call=await connect(project);
    if(command==='status'||command==='requests'){const state=await call('status');print(command==='requests'?state.pending:compact(state));}
    else if(command==='run'){
      const action=args.shift();if(!action)throw Error('run requires an action');const file=flag('--input');
      print(await call('run',{action,options:file?JSON.parse(await readFile(resolve(file),'utf8')):{}}));
    }else if(command==='export')print(await call('run',{action:'export',options:{formats:(flag('--formats')||'svg,png,pptx').split(',')}}));
    else if(command==='respond'){
      const id=args.shift(),file=flag('--file');if(!id||!file)throw Error('respond requires REQUEST_ID --file PATH');
      const bytes=await readFile(resolve(file));const input={id,actualModel:flag('--actual-model'),actualReasoningEffort:flag('--actual-effort')};
      if(args.includes('--image')){const extension=extname(file).toLowerCase(),type={'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp'}[extension];if(!type)throw Error('Use PNG, JPEG or WebP');input.imageData='data:'+type+';base64,'+bytes.toString('base64');}
      else input.text=bytes.toString('utf8');print(await call('respond',input));
    }else if(command==='fail'){const id=args.shift();print(await call('respond',{id,error:flag('--message')||'Host agent could not complete this inference request'}));}
    else if(command==='stop')print(await call('stop',{force:args.includes('--force')}));
    else print(await call(command,{}));
  }else{
    console.log('FigureForge standalone skill\n  doctor | verify\n  start PROJECT\n  run PROJECT ACTION [--input OPTIONS.json]\n  status PROJECT | requests PROJECT\n  respond PROJECT REQUEST_ID --file RESPONSE [--image] [--actual-model NAME] [--actual-effort LEVEL]\n  fail PROJECT REQUEST_ID --message MESSAGE\n  export PROJECT [--formats svg,png,pptx,drawio,vsdx]\n  accept-review PROJECT | reject-review PROJECT\n  stop PROJECT [--force]\nActions: configure, search, select, upload-references, parse-pdf, analyze, generate, import-svg, import-bitmap, reconstruct, audit, revise, export');
    if(command)process.exitCode=1;
  }
}catch(error){console.error(error.message);process.exitCode=1;}
