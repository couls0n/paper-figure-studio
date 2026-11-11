# 案例图 / 成对对照 (`comparison`)

当读者需要看清**同一任务在两个条件下哪里发生了变化**，选择案例图。数值高低走 `bar`；一次执行的完整动作/截图顺序走 `trajectory`。先确定“不变的意图”和“变化的请求、观察或动作参数”，再排图。

## 论文式默认与变体

设置 `style.profile: paper_case`。默认模板采用 TAI3 Figure 1 的扁横向案例语法；第二模板采用 BadAgent Figure 1 的场景行语法。它们使用原创示例文字与矢量小图标。查看 [源图观察与风格匹配](../style/case-study.md)。

| 变体 | 适合的内容 | 可运行模板 |
| --- | --- | --- |
| `paired_dialogue` | 一个任务的原始/变体请求、工具调用和结果，差异集中在少数字段 | [comparison.json](../../assets/templates/comparison.json) |
| `scenario_rows` | 几个匹配场景，用户请求不变，需要逐行比较代理响应 | [comparison_scenarios.json](../../assets/templates/comparison_scenarios.json) |

```bash
python scripts/render.py assets/templates/comparison.json --out output/comparison
python scripts/render.py assets/templates/comparison_scenarios.json --out output/comparison-scenarios
```

没有 `style.profile` 的历史规格仍可使用基础对照渲染器；新论文案例优先选上述有来源锚点的变体。

## 输入

共享规格见 [figure-spec.md](../figure-spec.md)。`data.columns` 至少两项，每项含唯一 `id`、`title`、可选 `status`、`events`。`status` 中 `safe/normal/success` 对应绿，`unsafe/attack/blocked` 对应红，其余中性；状态不会把整列染成红绿卡片。

- `events`: 每项至少 `text`，建议同时提供 `id`、`role`、`kind`。同一个事件 ID 在不同条件下占同一行；缺失事件显示破折号，不补造内容。旧规格无 ID 时按位置对应。
- `kind`: `user`、`tool`、`text`、`outcome`。`tool` 使用等宽文本；`outcome` 使用简短行内结论。未指定时可从常见角色名推断，含糊角色默认普通文字。
- `highlights`: `[{text, color?}]`，标出输入字符串的精确差异；跨换行的高亮继续保留。默认红色。提示词与工具调用是显示内容，不执行。
- `shared_input`、`shared_label` 可选：用紧凑文字交代不变条件。请求内已经明确约束时不用再重复一块大标题。
- `intervention` 可选：短变化标签。`paired_dialogue` 在两条件上方绘制浅紫标签与弧箭头；`scenario_rows` 将它放在末行下方。
- `scenario_rows` 的事件另外可含 `scenario`、`prompt`、`prompt_highlights`、`code`。`text` 表示响应；`code: true` 用等宽字体显示响应。
- `style_reference` 在顶层记录论文/图号/页码以及保留与调整项。它描述设计来源，不把示例数据声明为论文结果。

## 具体画法

1. 列出固定条件、变化条件、关键请求句、工具动作和后果。把论点压在几个可直接核对的词或参数上；冗长背景留给图注。
2. 单案例按“请求 → 工具调用 → 结果”对齐；多案例按场景 ID 对齐两个条件。每行以最高内容为高度，避免同一操作在两侧错位。
3. 用户文本采用暖浅灰气泡，工具调用采用浅蓝气泡和等宽字。小人物/机器人图标表示角色；普通图标仅是辅助，不能替代内容标签。
4. 新增、错误或改变的短语用局部红色，正确参数或保持约束的结果可用绿色。不要给整段正常文字着色来代替差异定位。
5. 默认省去图内大标题，保留小条件标签。分隔线、气泡边缘、变换弧箭头保持细；默认案例是宽而浅的横条，不能为了塞下长证据把字强行缩小。
6. 渲染 SVG/PDF/PNG，并在接近论文最终宽度下与所选原图并排看。检查两侧阅读顺序、局部差异、字符高亮间距、代码引号/缩进、角色和结果是否同时可辨。

## 验收要点

成对事件数量和 ID 不丢失；明示用户意图没有被视觉叙事改写；文字保持可编辑；危险参数与正常参数清楚区分。新增长文本应让高度增长或拆面板，不自动截断。默认采用 Helvetica/Arial 与 Courier 兼容字体度量，使 SVG 高亮片段与 PDF 导出位置一致；若更换字体，需要同步度量并重新检查导出。
