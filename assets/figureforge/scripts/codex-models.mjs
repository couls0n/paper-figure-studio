import { spawn } from 'node:child_process';
import { tmpdir } from 'node:os';

// Use the installed CLI's discovery API, so the picker follows its current login
// and model catalog instead of a hard-coded list or another account's disk cache.
export async function readCodexModels({ bin = process.env.CODEX_BIN || 'codex', timeoutMs = 15000 } = {}) {
  const child = spawn(bin, ['app-server', '--listen', 'stdio://'], { cwd: tmpdir(), stdio: ['pipe', 'pipe', 'ignore'] });
  const pending = new Map();
  let nextId = 0, buffer = '', failure;
  const fail = error => {
    failure = error;
    for (const call of pending.values()) call.reject(error);
    pending.clear();
  };
  const send = message => child.stdin.write(JSON.stringify(message) + '\n');
  const request = (method, params) => new Promise((resolve, reject) => {
    if (failure) { reject(failure); return; }
    const id = ++nextId;
    pending.set(id, { resolve, reject });
    send({ id, method, params });
  });
  child.on('error', fail);
  child.stdin.on('error', fail);
  child.on('close', code => fail(new Error(`Codex model discovery exited (${code})`)));
  child.stdout.setEncoding('utf8');
  child.stdout.on('data', chunk => {
    buffer += chunk;
    let end;
    while ((end = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, end); buffer = buffer.slice(end + 1);
      let message;
      try { message = JSON.parse(line); } catch { continue; }
      const call = pending.get(message.id);
      if (!call) continue;
      pending.delete(message.id);
      if (message.error) call.reject(new Error(message.error.message || 'Codex model discovery failed'));
      else call.resolve(message.result);
    }
  });
  const timer = setTimeout(() => {
    fail(new Error('Codex 模型列表读取超时，请确认本机 Codex 已登录后刷新。'));
    child.kill();
  }, timeoutMs);
  try {
    await request('initialize', { clientInfo: { name: 'figureforge', version: '1.0.0' } });
    send({ method: 'initialized' });
    const [first, config] = await Promise.all([
      request('model/list', { includeHidden: false, limit: 100 }),
      request('config/read', { includeLayers: false }),
    ]);
    const models = [...first.data];
    let cursor = first.nextCursor;
    while (cursor) {
      const page = await request('model/list', { includeHidden: false, limit: 100, cursor });
      models.push(...page.data); cursor = page.nextCursor;
    }
    const data = [...new Map(models.filter(m => !m.hidden).map(m => {
      const efforts = m.supportedReasoningEfforts.map(e => e.reasoningEffort);
      const modalities = m.inputModalities ?? ['text', 'image'];
      const reason = !efforts.includes('max') ? '不支持 max' : !modalities.includes('image') ? '不支持参考图输入' : '';
      return [m.model, { id: m.model, object: 'model', owned_by: 'local-codex', display_name: m.displayName,
        supported_reasoning_efforts: efforts, input_modalities: modalities,
        available: !reason, unavailable_reason: reason, is_default: m.isDefault }];
    })).values()];
    const available = data.filter(m => m.available);
    if (!available.length) throw new Error('本机 Codex 未提供同时支持 max 和图像输入的模型。');
    const preferred = available.find(m => m.id === config.config?.model) || available.find(m => m.is_default) || available[0];
    return { data, default_model: preferred.id, reasoning_effort: 'max' };
  } finally {
    clearTimeout(timer);
    child.stdin.end();
    child.kill();
  }
}
