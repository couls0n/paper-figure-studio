// Appended to the bundled module at load time. The source snapshot is untouched.
// This adapter exposes existing operations; it does not replace any prompt,
// retrieval algorithm, generation function, repair loop, or exporter.
const skillProviderBases=Object.fromEntries(Object.entries(MAN.providers).map(([id,value])=>[id,value.base]));
const skillSet = (id, value) => {
  const el = document.getElementById(id);
  if (!el) throw Error('Unknown FigureForge field: '+id);
  if (el.tagName === 'SELECT' && ![...el.options].some(o=>o.value===String(value)))
    throw Error('Unsupported '+id+': '+value);
  el.value=String(value);
};
const skillModel = (id, value) => {
  const el=document.getElementById(id);
  if (![...el.options].some(o=>o.value===value)) el.add(new Option(value,value));
  el.value=value;
};
async function skillRecords() {
  await revisionGallery.ready;
  return new Promise((resolve,reject)=>{
    const request=indexedDB.open('figureforge-revisions',1);
    request.onsuccess=()=>{
      const db=request.result;
      if(!db.objectStoreNames.contains('versions')){db.close();resolve([]);return;}
      const q=db.transaction('versions').objectStore('versions').getAll();
      q.onsuccess=()=>{db.close();resolve(q.result);};q.onerror=()=>{db.close();reject(q.error);};
    };request.onerror=()=>reject(request.error);
  });
}
function skillStatus() {
  const state=ensureExportState();
  return {mode,passMode,boot:retrievalBoot.state,figureCount:data.N,
    selected:[...refs],paper:$('#paper').value,target:$('#target').value,
    analysis:analysis?.j||null,source:state.source||null,hasSvg:!!state.svg,hasBitmap:!!state.bitmap,
    nodeCount:state.scene?.nodes?.length||0,reconPending:!!state.reconPending,reconFailed:!!state.reconFailed,reconError:state.reconError||'',
    reconstruction:state.recon?.audit||null,qualityState:state.recon?.qualityState||null,
    error:$('#genErr').hidden?'':$('#genErr').textContent,
    revisionError:document.querySelector('.ff-revision-error')?.textContent||'',
    versions:[...document.querySelectorAll('.ff-version')].map(el=>({id:el.dataset.versionId,label:el.querySelector('strong').textContent})),
    reviewPending:!!document.querySelector('[data-revision-accept]')};
}
function skillConfigure(o={}) {
  if(o.mode && !['svg','image'].includes(o.mode)) throw Error('mode must be svg or image');
  if(o.pass && !['two','direct'].includes(o.pass)) throw Error('pass must be two or direct');
  const previousMode=mode;
  mode=o.mode||mode;passMode=o.pass||passMode;
  // Preserve the built-in Codex SVG path and OpenAI-compatible bitmap path.
  // Their model HTTP calls are fulfilled by the host agent transport, never an API key.
  const provider=o.provider||(o.mode?(mode==='image'?'oai':'codex'):$('#provider').value)||(mode==='image'?'oai':'codex');
  if(!MAN.providers[provider])throw Error('Unknown bundled provider profile: '+provider);
  if(![...$('#provider').options].some(x=>x.value===provider))$('#provider').add(new Option(provider,provider));
  $('#provider').value=provider;
  if(provider==='codex'||(o.mode&&!o.provider))MAN.providers[provider].base=location.origin+'/agent/v1';
  else if(o.provider)MAN.providers[provider].base=skillProviderBases[provider];
  const vision=o.visionModel||$('#parseModel').value||'agent-vision';
  MAN.providers[provider].chat=[vision];MAN.providers[provider].vision=[vision];
  $('#useRelay').checked=false;$('#baseOverride').value='';$('#key').value='agent-local-transport';
  skillModel('model',mode==='image'?(o.imageModel||(previousMode===mode?$('#model').value:'')||'gpt-image-2'):vision);
  for(const id of ['parseModel','analyzeModel','reconModel'])skillModel(id,vision);
  syncCodexReasoning(provider);
  const fields={paper:'paper',target:'target',targetDescription:'targetDesc',ratio:'figureRatio',resolution:'imageResolution',pattern:'pattern',venue:'venue',year:'year',tier:'tier',contentMode:'contentMode',contentQuery:'contentQuery'};
  for(const [key,id] of Object.entries(fields)) if(o[key]!==undefined)skillSet(id,o[key]);
  if(o.font!==undefined){skillSet('exportFont',o.font);applyExportFont(o.font);}
  if(o.language)GAL_I18N.setLang(o.language);
  return skillStatus();
}
window.FigureForgeSkill={
  status:skillStatus,configure:skillConfigure,
  async search(o={}) {
    if(o.query!==undefined)skillSet('paper',o.query);
    for(const k of ['pattern','venue','year','tier'])if(o[k]!==undefined)skillSet(k,o[k]);
    await search();
    return {boot:retrievalBoot.state,total:results.length,results:results.slice(0,o.limit||24)};
  },
  select(ids) {
    if(!Array.isArray(ids)||ids.length>MAX_REFS)throw Error('Select at most '+MAX_REFS+' references');
    for(const id of ids)if(!referenceFigure(id))throw Error('Unknown reference ID: '+id);
    refs=new Set(ids);analysis=null;patchAllCards();updateCount();renderRefsStrip();
    return [...refs].map(id=>referenceFigure(id));
  },
  analyze:()=>analyzeReferences(),
  async generate(){await $('#genBtn').onclick();await revisionGallery.ready;await new Promise(r=>setTimeout(r,0));
    if(!$('#genErr').hidden)throw Error($('#genErr').textContent);return skillStatus();},
  async importSvg(svg){await window.__ffRenderSVG(svg);return skillStatus();},
  async reconstruct(){
    if($('#reconBtn').disabled)throw Error('Reconstruction is unavailable; load a bitmap and choose a recognition profile first');
    $('#reconBtn').click();
    while(ensureExportState().reconPending)await new Promise(r=>setTimeout(r,50));
    const st=ensureExportState();if(st.reconFailed||!st.svg)throw Error(st.reconError||'Reconstruction did not complete');return skillStatus();
  },
  audit(){const st=ensureExportState();return {geometry:st.source==='svg'?auditGeometry(st.svg):null,reconstruction:st.recon||null};},
  async snapshot(){
    const st=ensureExportState();
    const fields={};for(const id of ['paper','target','targetDesc','figureRatio','imageResolution','pattern','venue','year','tier','contentMode','contentQuery'])fields[id]=$('#'+id).value;
    const uploads=[];for(const [id,f] of uploadedRefs)uploads.push({...f,localURL:await fileToDataURI(await(await fetch(f.localURL)).blob())});
    return {schema:'figureforge-skill-project-v1',fields,mode,passMode,provider:$('#provider').value,base:baseURL(),visionModel:$('#parseModel').value,imageModel:mode==='image'?$('#model').value:null,analysis,refs:[...refs],uploads,
      state:structuredClone(st),records:await skillRecords(),uploadedExportBitmap,lastGeneratedImage:window.__ffLastGeneratedImage||'',pdfContext,pdfText,pdfImgs};
  },
  restore(s){
    skillConfigure({mode:s.mode,pass:s.passMode,provider:s.provider,visionModel:s.visionModel,imageModel:s.imageModel});
    if(s.base&&new URL(s.base).hostname==='127.0.0.1')MAN.providers[$('#provider').value].base=location.origin+'/agent/v1';
    for(const [id,value] of Object.entries(s.fields||{}))skillSet(id,value);
    for(const f of s.uploads||[])uploadedRefs.set(f.id,f);
    refs=new Set(s.refs||[]);analysis=s.analysis||null;
    if(s.pdfContext){pdfContext=s.pdfContext;pdfContext.buf=Uint8Array.from(atob(pdfContext.dataUri.split(',')[1]),c=>c.charCodeAt(0)).buffer;pdfText=s.pdfText;pdfImgs=s.pdfImgs;}
    if(s.state){
      window.__ffExportState=structuredClone(s.state);
      // A stopped browser cannot retain an in-flight reconstruction promise.
      if(window.__ffExportState.reconPending)Object.assign(window.__ffExportState,{reconPending:false,reconFailed:true,reconError:'Previous runtime stopped during reconstruction; the source bitmap is retained. Run reconstruct to resume.'});
      uploadedExportBitmap=s.uploadedExportBitmap||'';
      if(s.lastGeneratedImage)markStep3Output(s.lastGeneratedImage);
      else if(!('lastGeneratedImage'in s)&&s.state.bitmap)markStep3Output(s.state.bitmap);
      renderEditableExportCard();
    }
    updateCount();renderRefsStrip();return skillStatus();
  },
  async preview(scale=2){
    const st=ensureExportState();if(!st.svg)throw Error('No editable SVG to render');
    const v=readViewBox(new DOMParser().parseFromString(st.svg,'image/svg+xml').documentElement);
    const img=await loadImage('data:image/svg+xml;charset=utf-8,'+encodeURIComponent(st.svg));
    const canvas=document.createElement('canvas');canvas.width=Math.round((v?.w||img.naturalWidth)*scale);canvas.height=Math.round((v?.h||img.naturalHeight)*scale);
    const ctx=canvas.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);
    return canvas.toDataURL('image/png');
  },
  exportState:()=>structuredClone(ensureExportState()),
  async restoreRecords(records){
    await skillRecords();return new Promise((resolve,reject)=>{const r=indexedDB.open('figureforge-revisions',1);r.onerror=()=>reject(r.error);r.onsuccess=()=>{const db=r.result,tx=db.transaction('versions','readwrite'),s=tx.objectStore('versions');for(const record of records)s.put(record);tx.oncomplete=()=>{db.close();resolve();};tx.onerror=()=>{db.close();reject(tx.error);};};});
  }
};
skillConfigure();
