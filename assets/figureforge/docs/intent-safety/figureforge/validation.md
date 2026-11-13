# 验证记录

已通过：

- `node scripts/test-serve-codex.mjs`：消息和参考图传递、免 Key 对话、SSE 响应、本机来源限制、输入检查。
- `node scripts/test-serve-nonelinear.mjs`：原有本地服务回归。
- `node forge/test-editable-export.mjs`：原有可编辑导出检查。
- `node --test forge/test-chat-api.mjs forge/test-svg-chat-response.mjs forge/test-retrieval-boot.mjs`：16 项通过。
- `git diff --check`、`node --check scripts/serve-codex.mjs`。
- Chrome 中使用真实 Codex 登录，完成四张图的两阶段生成、案例图自动版式修复、具体方法图两次原生修订，以及四组 SVG / PPTX 原生导出。
- 四个 SVG XML 解析成功，四个 PPTX ZIP 结构完整；每个 PPTX 都有独立形状和文字，详见 `provenance.json`。已目视核对四张 PNG 预览。

未完成的仓库检查：

- `node scripts/check-forge-workflow-lock.mjs`：运行时缺少 `.github/forge-workflow-lock.json`（ENOENT）。该文件及其他 `.github` 文件在工作区已处于暂存删除状态，不是本次修改造成；未恢复、重建或更新锁清单。
- `node forge/test-step3-svg-request.cjs`：测试默认依赖 Windows 上的 Playwright 路径，在此 macOS 环境无法启动。真实页面的生成和导出已通过上述浏览器流程验证。
