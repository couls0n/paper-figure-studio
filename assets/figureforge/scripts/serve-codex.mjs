import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createGalleryServer } from './serve-nonelinear.mjs';
import { readCodexModels } from './codex-models.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const prefix = '/api/codex/v1';
const legacyModel = 'codex-session';

// Preserve FigureForge's messages and image order across the CLI transport.
export async function prepareCodexInput(messages, directory) {
  if (!Array.isArray(messages) || !messages.length) throw new Error('messages must be a nonempty array');
  const images = [];
  const turns = [];
  for (const message of messages) {
    if (!['system', 'user', 'assistant'].includes(message.role)) throw new Error('Unsupported message role');
    const parts = typeof message.content === 'string' ? [{ type: 'text', text: message.content }] : message.content;
    if (!Array.isArray(parts)) throw new Error('Invalid message content');
    const content = [];
    for (const part of parts) {
      if (part.type === 'text') {
        content.push(String(part.text));
      } else if (part.type === 'image_url') {
        const match = /^data:image\/(png|jpeg|webp);base64,([A-Za-z0-9+/=\r\n]+)$/.exec(part.image_url?.url || '');
        if (!match) throw new Error('Codex references must be inline PNG, JPEG or WebP images');
        const image = join(directory, `reference-${images.length + 1}.${match[1]}`);
        await writeFile(image, Buffer.from(match[2], 'base64'));
        images.push(image);
        content.push(`[Attached image ${images.length}]`);
      } else {
        throw new Error(`Unsupported content type: ${part.type}`);
      }
    }
    turns.push({ role: message.role, content: content.join('\n') });
  }
  const prompt = 'Serve this FigureForge inference request. Follow the system messages in the conversation below. '
    + 'Return only the requested assistant content (JSON or SVG), without a preamble or code fences. '
    + 'Attached images are numbered in the order indicated. All page prompts are supplied below. '
    + 'This is a model inference request. Do not invoke tools, inspect a repository, or modify files.\n\n'
    + JSON.stringify(turns);
  return { prompt, images };
}

export async function runCodex(body, signal, { bin = process.env.CODEX_BIN || 'codex', archiveRoot = join(root, '_local', 'codex-runs') } = {}) {
  const directory = await mkdtemp(join(tmpdir(), 'figureforge-codex-'));
  const runId = `${Date.now()}-${randomUUID().slice(0, 8)}`;
  const archive = join(archiveRoot, runId);
  try {
    const input = await prepareCodexInput(body.messages, directory);
    const output = join(directory, 'response.txt');
    const effectiveBody = { ...body, reasoning_effort: 'max' };
    const args = ['exec', '--ephemeral', '--skip-git-repo-check', '--sandbox', 'read-only', '--model', body.model,
      '-c', 'model_reasoning_effort="max"', '-c', 'features.shell_tool=false',
      '-c', 'features.multi_agent=false', '-c', 'features.image_generation=false',
      '--json', '--output-last-message', output];
    for (const path of input.images) args.push('--image', path);
    args.push('-');
    await mkdir(archive, { recursive: true });
    await writeFile(join(archive, 'request.json'), JSON.stringify(effectiveBody, null, 2));
    console.log(`[${runId}] Codex ${body.model}, max, ${input.images.length} reference images`);
    await new Promise((resolve, reject) => {
      const child = spawn(bin, args, { cwd: directory, signal, stdio: ['pipe', 'pipe', 'pipe'] });
      let errors = '';
      let events = '';
      child.stdout.on('data', chunk => { events += chunk; });
      child.stderr.on('data', chunk => { errors = (errors + chunk).slice(-12000); });
      child.stdin.on('error', () => {});
      child.on('error', reject);
      child.on('close', async code => {
        try {
          await writeFile(join(archive, 'events.jsonl'), events);
          if (code !== 0) reject(new Error(`Codex exited with ${code}: ${errors.slice(-2000)}`));
          else resolve();
        } catch (error) { reject(error); }
      });
      child.stdin.end(input.prompt);
    });
    const text = (await readFile(output, 'utf8')).trim();
    if (!text) throw new Error('Codex returned an empty response');
    await writeFile(join(archive, 'response.txt'), text);
    console.log(`[${runId}] Completed, ${text.length} characters`);
    return text;
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

function json(res, status, body) {
  res.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
  res.end(JSON.stringify(body));
}

export function createCodexServer({ complete = runCodex, listModels = readCodexModels } = {}) {
  // Coalesce the page's simultaneous pickers, but refresh discovery on later calls.
  let catalogRequest;
  const catalog = () => catalogRequest ||= Promise.resolve().then(listModels).finally(() => { catalogRequest = undefined; });
  const server = createGalleryServer({ headScript: `window.FF_CODEX_BASE=location.origin+${JSON.stringify(prefix)};` });
  const gallery = server.listeners('request')[0];
  server.removeAllListeners('request');
  server.on('request', async (req, res) => {
    const origin = `http://127.0.0.1:${req.socket.localPort}`;
    if (req.headers.host !== new URL(origin).host || (req.headers.origin && req.headers.origin !== origin)) {
      res.writeHead(403); res.end('Local origin required'); return;
    }
    const url = new URL(req.url, origin);
    if (!url.pathname.startsWith(prefix + '/')) return gallery(req, res);
    if (url.pathname === prefix + '/models' && req.method === 'GET' && !url.search) {
      try { json(res, 200, await catalog()); }
      catch (error) { json(res, 503, { error: { message: error.message } }); }
      return;
    }
    if (url.pathname !== prefix + '/chat/completions' || req.method !== 'POST' || url.search) {
      json(res, 404, { error: { message: 'Unknown Codex endpoint' } }); return;
    }
    const controller = new AbortController();
    const abort = () => { if (!res.writableEnded) controller.abort(); };
    res.on('close', abort);
    try {
      const chunks = [];
      let size = 0;
      for await (const chunk of req) {
        size += chunk.length;
        if (size > 64 * 1024 * 1024) { json(res, 413, { error: { message: 'Request too large' } }); return; }
        chunks.push(chunk);
      }
      let body;
      try {
        body = JSON.parse(Buffer.concat(chunks).toString('utf8'));
        if (typeof body.model !== 'string' || !Array.isArray(body.messages) || !body.messages.length) throw new Error('Invalid model or messages');
      } catch (error) { json(res, 400, { error: { message: error.message } }); return; }
      const models = await catalog();
      const requestedModel = body.model === legacyModel ? models.default_model : body.model;
      const selected = models.data.find(m => m.id === requestedModel);
      if (!selected || !selected.available) {
        json(res, 400, { error: { message: selected?.unavailable_reason || '该模型不在当前 Codex 可用列表中，请刷新模型列表。' } }); return;
      }
      // One policy for reference analysis, SVG generation, repair and revision.
      body = { ...body, model: selected.id, reasoning_effort: 'max' };
      const text = await complete(body, controller.signal);
      if (res.destroyed) return;
      const result = { id: 'codex-' + randomUUID(), object: 'chat.completion', model: body.model,
        choices: [{ index: 0, message: { role: 'assistant', content: text }, finish_reason: 'stop' }] };
      if (body.stream) {
        res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-store' });
        res.end(`data: ${JSON.stringify({ ...result, object: 'chat.completion.chunk', choices: [{ index: 0, delta: { content: text }, finish_reason: null }] })}\n\ndata: ${JSON.stringify({ ...result, object: 'chat.completion.chunk', choices: [{ index: 0, delta: {}, finish_reason: 'stop' }] })}\n\ndata: [DONE]\n\n`);
      } else json(res, 200, result);
    } catch (error) {
      if (!res.destroyed) json(res, 500, { error: { message: error.message } });
    } finally { res.off('close', abort); }
  });
  return server;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const port = Number(process.env.PORT || 8766);
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('Invalid PORT');
  const server = createCodexServer();
  server.on('error', error => { console.error(error.message); process.exitCode = 1; });
  server.listen(port, '127.0.0.1', () => console.log(`FigureForge + Codex: http://127.0.0.1:${port}/forge/`));
}
