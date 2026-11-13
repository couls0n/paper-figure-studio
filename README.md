# Paper Figure Studio · FigureForge Skill

一个完整、独立运行的 **FigureForge 绘图 skill**。Agent 读取 [SKILL.md](SKILL.md)，使用包内的参考图库、原始提示词、生成流程、修订逻辑和可编辑导出器，从论文或绘图需求完成整套出图任务。

本仓库的技能名是 **`figureforge`**。当前 `main` 已整体替换为独立 FigureForge skill；此前的十二类模板版本保留在 Git 历史中。

## 安装与调用

首次安装到 Codex 的技能目录：

```bash
git clone https://github.com/couls0n/paper-figure-studio.git ~/.codex/skills/figureforge
```

其他支持目录型 skill 的 agent，可将整个仓库放入其技能目录，并读取根目录的 `SKILL.md`。运行需要 **Node.js 20+、Chrome/Chromium**，以及 agent 的文件、脚本和视觉理解能力。位图生成路线还需要宿主 agent 的生图/改图工具。浏览器驱动、图库、检索模型和导出资源均已随仓库提供。

调用示例：

> 使用 $figureforge，根据这份论文生成一组案例图、问题图和方法图，交付 PNG、SVG 和 PPTX。

AI 分析与生成由使用 skill 的 agent 完成，模型请求通过本地任务队列交给它处理。无需原 FigureForge 仓库、线上网站、Codex CLI 登录或额外 API Key。技能会自行启动专用的无界面浏览器，用户无需操作网页。

## 完整工作流

`论文/绘图需求 → CLIP + BM25 检索 → 参考图选择 → 版式分析与设计约束 → SVG 或位图生成 → 检查与修订 → 可编辑导出`

- SVG 路线保留原始提示词、参考图输入、几何检查及修复逻辑。
- 位图路线保留原始生图请求构建、尺寸检查，以及当前版本的单次整图可编辑重建。
- 修改保留原图、参考截图、候选结果确认和版本历史。
- 导出支持 SVG、原生可编辑 PPTX、VSDX、draw.io；PNG 为 SVG 的渲染预览。
- 任务材料、模型请求与回复、参考图、场景和版本保存在独立项目目录，支持重启恢复。

详细操作见 [命令与 agent 协议](references/commands.md)；源码对应关系及当前 Step 4 的具体行为见 [工作流一致性说明](references/workflow.md)。

## 资源与独立性

仓库包含固定到 `a9b7c3a8c4e783278a935e7744f688a7a2eece90` 的完整原始代码与资源快照：

- **3,784 个原始文件**，全部保留原始字节内容。
- **3,449 张实际索引参考图**及完整元数据。
- CLIP ONNX 模型、分词器、图文向量、BM25 索引和 WASM 运行库。
- PDF 读取组件、导出模板、原始工作流模块、示例与署名文件。
- 独立执行器和已随包提供的 Playwright 驱动。

完整资源约 628 MB，因此首次克隆需要传输较多数据。运行时从本仓库加载资源，不回退到原作者图库或其他开发者的本机目录。

## 验证与维护

```bash
node scripts/figureforge.mjs doctor
node scripts/verify.mjs
node scripts/test-runtime.mjs
```

完整性校验检查原始文件的 SHA-256、图库图片、向量维度和独立技能文件。集成测试使用真实本地检索、渲染与导出，模型回复使用明确标注的测试夹具，覆盖生成、修复、修订、PDF、位图重建、版本恢复和中断恢复。见 [验证记录](references/validation.md)。

生成可搬走的完整技能包：

```bash
python3 scripts/package.py /absolute/output/figureforge.skill.zip
```

包内保留完整资源；打包器排除 Git、编辑器及本地运行环境文件，并生成资源清单及 ZIP 校验值。绘图项目应保存在技能目录之外。

原项目来源与许可保留在 [代码许可](LICENSE)、[原始署名](assets/figureforge/NOTICE.md) 和 [图片使用说明](assets/figureforge/IMAGES_POLICY.md)。浏览器驱动的许可与第三方声明保留在其 vendored 目录中。
