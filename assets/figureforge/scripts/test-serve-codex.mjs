import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createCodexServer, prepareCodexInput, runCodex } from './serve-codex.mjs';
import { readCodexModels } from './codex-models.mjs';

const directory = await mkdtemp(join(tmpdir(), 'test-figureforge-codex-'));
try {
  // Exercise the actual stdio discovery and exec transport with a local fixture.
  // No account, network request or model quota is needed for these tests.
  const bin = join(directory, 'codex-fixture.mjs');
  await writeFile(bin, '#!/usr/bin/env node\n' + String.raw`
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createInterface } from 'node:readline';
const args=process.argv.slice(2);
const model=(id,efforts=['max'],input=['text','image'])=>({id,model:id,displayName:id,hidden:false,isDefault:id==='model-a',supportedReasoningEfforts:efforts.map(reasoningEffort=>({reasoningEffort})),inputModalities:input});
if(args[0]==='app-server'){
  for await(const line of createInterface({input:process.stdin})){
    const m=JSON.parse(line);let result;
    if(m.method==='initialize')result={};
    else if(m.method==='model/list'){
      assert.equal(m.params.includeHidden,false);
      result=m.params.cursor?{data:[model('model-b'),model('weak',['high']),model('text-only',['max'],['text'])],nextCursor:null}:{data:[model('model-a'),{...model('hidden'),hidden:true}],nextCursor:'second'};
    }else if(m.method==='config/read')result={config:{model:'model-b'}};
    else continue;
    console.log(JSON.stringify({id:m.id,result}));
  }
}else{
  assert.equal(args[0],'exec');
  const selected=args[args.indexOf('--model')+1];assert.equal(selected,'model-b');
  assert.ok(args.includes('model_reasoning_effort="max"'));
  const image=args[args.indexOf('--image')+1];assert.equal(await readFile(image,'utf8'),'image fixture');
  let input='';for await(const chunk of process.stdin)input+=chunk;
  assert.ok(input.includes('Exact design contract'));
  await writeFile(args[args.indexOf('--output-last-message')+1],'<svg data-model="'+selected+'" data-effort="max"/>');
  console.log(JSON.stringify({type:'turn.completed'}));
}
`, { mode: 0o755 });
  const catalog = await readCodexModels({ bin });
  assert.deepEqual(catalog.data.map(m => m.id), ['model-a', 'model-b', 'weak', 'text-only']);
  assert.equal(catalog.default_model, 'model-b');
  assert.equal(catalog.data[2].unavailable_reason, '不支持 max');
  assert.equal(catalog.data[3].available, false);

  const bytes = Buffer.from('image fixture');
  const messages = [{ role: 'system', content: 'Exact design contract' }, { role: 'user', content: [
    { type: 'text', text: 'Before reference' },
    { type: 'image_url', image_url: { url: 'data:image/png;base64,' + bytes.toString('base64') } },
    { type: 'text', text: 'After reference' },
  ] }];
  const input = await prepareCodexInput(messages, directory);
  assert.deepEqual(await readFile(input.images[0]), bytes);
  assert.ok(input.prompt.includes('Exact design contract'));
  assert.ok(input.prompt.includes('Before reference\\n[Attached image 1]\\nAfter reference'));
  await assert.rejects(prepareCodexInput([{ role: 'user', content: [{ type: 'image_url', image_url: { url: 'https://example.com/private' } }] }], directory), /inline/);

  const archiveRoot = join(directory, 'runs');
  const generated = await runCodex({ model: 'model-b', reasoning_effort: 'low', messages }, undefined, { bin, archiveRoot });
  assert.equal(generated, '<svg data-model="model-b" data-effort="max"/>');
  const archive = join(archiveRoot, (await readdir(archiveRoot))[0]);
  const archived = JSON.parse(await readFile(join(archive, 'request.json'), 'utf8'));
  assert.equal(archived.model, 'model-b');
  assert.equal(archived.reasoning_effort, 'max');

  const calls = [];
  let discoveries=0;
  const server = createCodexServer({ listModels: async () => { discoveries++; return catalog; }, complete: async body => { calls.push(body); return '<svg>generated</svg>'; } });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  try {
    const page = await (await fetch(origin + '/forge/')).text();
    assert.ok(page.includes('window.FF_CODEX_BASE=location.origin+"/api/codex/v1"'));
    assert.ok(page.includes("providerIds.unshift('codex')"));
    const list = await (await fetch(origin + '/api/codex/v1/models')).json();
    assert.equal(list.default_model, 'model-b');
    assert.equal(list.data[0].id, 'model-a');
    assert.equal(list.reasoning_effort, 'max');
    const body = { model: 'model-a', messages };
    const options = { method: 'POST', headers: { 'Content-Type': 'application/json', Origin: origin }, body: JSON.stringify(body) };
    const response = await fetch(origin + '/api/codex/v1/chat/completions', options);
    assert.equal(response.status, 200);
    assert.equal((await response.json()).choices[0].message.content, '<svg>generated</svg>');
    assert.deepEqual(calls[0], { ...body, reasoning_effort: 'max' });
    const stream = await fetch(origin + '/api/codex/v1/chat/completions', { ...options, body: JSON.stringify({ ...body, stream: true }) });
    assert.match(stream.headers.get('content-type'), /text\/event-stream/);
    assert.match(await stream.text(), /data: \[DONE\]/);
    for (const request of [
      { ...body, model: 'model-b', reasoning_effort: 'medium' },
      { ...body, model: 'model-b', reasoning_effort: 'xhigh' },
      { ...body, model: 'codex-session' },
    ]) {
      const response = await fetch(origin + '/api/codex/v1/chat/completions', { ...options, body: JSON.stringify(request) });
      assert.equal(response.status, 200);
      assert.equal((await response.json()).model, 'model-b');
      assert.equal(calls.at(-1).reasoning_effort, 'max');
      assert.equal(calls.at(-1).model, 'model-b');
    }
    assert.equal((await fetch(origin + '/api/codex/v1/models', { headers: { Origin: 'https://example.com' } })).status, 403);
    assert.equal((await fetch(origin + '/api/codex/v1/chat/completions', { ...options, body: '{bad' })).status, 400);
    assert.equal((await fetch(origin + '/api/codex/v1/chat/completions', { ...options, body: JSON.stringify({ ...body, model: '--dangerous-argument' }) })).status, 400);
    for (const model of ['weak', 'text-only', 'hidden']) {
      assert.equal((await fetch(origin + '/api/codex/v1/chat/completions', { ...options, body: JSON.stringify({ ...body, model }) })).status, 400);
    }
    assert.equal((await fetch(origin + '/api/codex/v1/images/generations', options)).status, 404);
    assert.equal(calls.length, 5);
    assert.ok(discoveries > 1, 'Refresh discovery instead of retaining an account catalog indefinitely');
  } finally { await new Promise(resolve => server.close(resolve)); }
  console.log('PASS Codex provider: live paginated discovery, selected CLI model, max for all requests, legacy alias, capability checks, prompt/image preservation and local transport');
} finally { await rm(directory, { recursive: true, force: true }); }
