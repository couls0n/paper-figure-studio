import {readFile,stat,lstat,readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
export async function verify(skillRoot=root){
  const manifest=JSON.parse(await readFile(join(skillRoot,'references/source-manifest.json'),'utf8'));
  const errors=[];let checked=0,bytes=0;
  for(const entry of manifest.files){
    const file=join(skillRoot,'assets/figureforge',entry.path);
    try{if((await lstat(file)).isSymbolicLink())throw Error('symbolic link');
      const b=await readFile(file);
      if(b.length!==entry.size||createHash('sha256').update(b).digest('hex')!==entry.sha256)throw Error('checksum mismatch');
      checked++;bytes+=b.length;
    }catch(e){errors.push(entry.path+': '+e.message);}
  }
  const catalog=JSON.parse(await readFile(join(skillRoot,'assets/figureforge/forge/data/figures.json'),'utf8'));
  const figures=Array.isArray(catalog)?catalog:catalog.figures;
  for(const figure of figures){try{await stat(join(skillRoot,'assets/figureforge',figure.image));}catch{errors.push('Missing catalog image: '+figure.image);}}
  const ids=JSON.parse(await readFile(join(skillRoot,'assets/figureforge/forge/data/ids.json'),'utf8'));
  for(const name of ['image_emb.bin','text_emb.bin']){
    const s=await stat(join(skillRoot,'assets/figureforge/forge/data',name));
    if(s.size!==ids.length*512*4)errors.push(name+': embedding dimensions do not match catalog');
  }
  if(ids.length!==figures.length)errors.push('Catalog/index length mismatch');
  let bundleFiles=0;
  try{
    const bundle=JSON.parse(await readFile(join(skillRoot,'references/bundle-manifest.json'),'utf8'));
    for(const entry of bundle.files){
      const file=join(skillRoot,entry.path);
      try{if((await lstat(file)).isSymbolicLink())throw Error('symbolic link');
        // Snapshot bytes were already verified above against source-manifest.
        if(!entry.path.startsWith('assets/figureforge/')){
          const b=await readFile(file);if(b.length!==entry.size||createHash('sha256').update(b).digest('hex')!==entry.sha256)throw Error('checksum mismatch');
        }
        bundleFiles++;
      }catch(e){errors.push(entry.path+': '+e.message);}
    }
  }catch(e){if(e.code!=='ENOENT')errors.push('bundle manifest: '+e.message);}
  return {ok:errors.length===0,sourceCommit:manifest.source_commit,files:checked,bytes,figures:figures.length,bundleFiles,errors};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){const result=await verify(process.argv[2]);console.log(JSON.stringify(result,null,2));if(!result.ok)process.exitCode=1;}
