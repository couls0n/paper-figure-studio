# Intent-first routing / 先理解图意，再选择图型

本页是 skill 的语义路由协议。`scripts/route.py` 处理已经理解过的结构化意图，不是关键词分类器。它不需要网络、模型API或额外绘图库。执行它之前，使用当前对话、用户数据、所给参考图来理解意图；单独把自然语言放进 `request` 字段不会自动完成分类。

## 操作流程

1. **确定表达目的。** 用一句话写出“读者看完应理解什么”。辨别用户要解释系统、展示具体案例、比较数值，还是看分布。保留用户明确指定和明确否定的图型。
2. **确定内容结构。** 列出主体、关系、变量、顺序和数据来源。图中的线表示控制流、先后动作、父子关系、字段对应，还是数值变化？数字是计数、比例、坐标、指标还是单元格数值？
3. **判断组合。** “流程＋结果”“a/b面板”“按模型×条件分面”需要先拆面板，每个面板分别路由。多个方法或多个模型本身不意味着要拆面板：一张分组柱也可比较多个模型。
4. **形成 `intent.json`。** 使用下表的字段；证据不足时填 `unknown`，不要为了得到一个路由而猜。每个判断都应能指向用户原话、输入列或参考图内容。
5. **运行路由并审查结果。** 若出现冲突，先检查是不是自己把用户意图解析错了；能从现有材料修正时直接修正。只有仍存在实质歧义时才问用户一个简短问题。
6. **只加载选中的类型方法与模板。** 按返回的 `reference` 阅读具体画法，以 `template` 为起点填写真实内容。多面板读取每个子面板参考文件和 [组合方法](composition.md)。

```bash
python scripts/route.py --intent intent.json --out route.json
# 或：cat intent.json | python scripts/route.py
```

退出码 `0` 表示已确定图型（可能还缺绘制数据）；`3` 表示仍需澄清图意；`2` 表示结构化输入格式错误。不要把 `exit 0` 或 `status: needs_inputs` 当作可以直接用示例数据出论文图。

## 从用户语言到语义字段

`purpose` 是想完成的表达任务，`relationship` 是图中要编码的关系，`evidence` 是主要输入结构。它们应互相验证，而不是将同一关键词机械地填三次。

| 用户真正要表达的内容 | purpose | relationship | 典型evidence | 图型 |
| --- | --- | --- | --- | --- |
| 系统如何组成、信息怎样流动、在哪里检查/反馈 | `explain_system` | `directed_flow` | `nodes_edges` | `architecture` |
| 同一对象在两个条件下哪里不同 | `compare_cases` | `qualitative_contrast` | `text_cases` / `text_code` / `screenshots` | `comparison` |
| 一次真实执行发生了哪些步骤、动作与结果 | `show_execution` | `event_sequence` | `step_records` / `screenshots` | `trajectory` |
| 让读者阅读一段提示词、代码、JSON或BNF | `present_text` | `verbatim` | `text_code` | `text_card` |
| 类别怎样包含或对应、字段如何解释 | `organize_categories` | `hierarchy` / `category_mapping` | `category_tree` / `category_mapping` | `taxonomy` |
| 组成一个整体的各部分占多少 | `show_composition` | `part_to_whole` | `counts` | `proportion` |
| 哪个类别或方法更高、更低 | `compare_values` | `category_magnitude` | `category_values` | `bar` |
| 随连续/有序条件变化的数值走势 | `show_change` | `ordered_numeric` | `ordered_values` | `line` |
| 行列交叉位置的数值或关系 | `show_pairwise_values` | `matrix` | `matrix` | `matrix` |
| 每个观测的两个数值如何关联，点云如何分开 | `show_relationship` | `coordinate` | `point_coordinates` | `scatter` |
| 观测值落在哪里，分布是否偏斜/多峰 | `show_distribution` | `sample_distribution` | `raw_samples` | `distribution` |
| 同一组指标上的整体形状、长短板 | `compare_profiles` | `profile` | `metric_profiles` | `radar` |

这些是默认语义匹配。用户明确指定兼容的形式时优先遵从，例如多维指标也可明确要求分组柱或矩阵。不能仅因有多个指标就自动选雷达，也不能仅因数字是百分比就选饼图。

### 易混淆请求怎样判断

| 容易混淆的说法 | 需要核对的事实 | 路由 |
| --- | --- | --- |
| “画时间线” / “show the sequence” | 是真实截图与动作先后，还是y随时间变化？ | 前者 `trajectory`；后者 `line` |
| “先检索再规划再执行” | 描述设计机制还是某一次执行的证据？ | 机制 `architecture`；实际日志 `trajectory` |
| “画关系图” / “relationship diagram” | 边表示调用、包含、字段映射，还是两个数值关系？ | 分别 `architecture` / `taxonomy` / `taxonomy` / `scatter` |
| “对比这两种方法” | 比较数值高低，还是展示具体输出差异？ | 数值 `bar`；案例 `comparison` |
| “这几个类别都有数字” | 数字是否为同一整体中的互斥组成部分？ | 是则 `proportion`；独立得分/排名则 `bar`；不清楚则澄清 |
| “双环图” | 两环是否为独立分类，还是确有父子数据？ | 独立边际分布走 `proportion`，分别归一化；层级关系不能伪造 |
| “分布/分离情况” | 输入是逐样本标量，还是已有二维嵌入坐标？ | 标量频数/密度 `distribution`；坐标点云 `scatter` |
| “相关性” | 一组观测的x/y关系，还是变量两两相关系数表？ | 前者 `scatter`；后者 `matrix` |
| “整体表现” | 关注总体排名还是多个同尺度维度的轮廓？ | 排名 `bar`；轮廓 `radar` |
| “不需要雷达图” | 否定词修饰哪个图型？ | 将 `radar` 写入 `excluded_types`，不能因出现“雷达”而选中它 |
| “照参考图，但换成我的结果” | 用户要沿用版式，还是沿用不适合新数据的编码？ | 保留明确偏好；对会改变含义的冲突先核对，不静默替换 |
| “画架构和结果” | 是否要求在同一张图内表达两个互补目的？ | `multipanel`，每面板单独选型 |

## 输入示例

### 单图：真实执行轨迹

```json
{
  "schema_version": 1,
  "request": "把五步截图、每步动作和首次泄露的位置画出来。",
  "purpose": "show_execution",
  "relationship": "event_sequence",
  "evidence": "screenshots",
  "data_status": "partial",
  "missing_inputs": ["第4步原始截图"],
  "semantic_notes": ["真实运行记录，不能用重建界面代替"]
}
```

输出为 `trajectory`、`status: needs_inputs`；它不会因为缺图就改成架构流程图，也不会自动填入假截图。

### 组合：方法与定量结果

```json
{
  "request": "左边方法架构，右边安全与效用的散点结果，组成a/b图。",
  "composition": true,
  "panels": [
    {
      "id": "a",
      "intent": {
        "purpose": "explain_system",
        "relationship": "directed_flow",
        "evidence": "nodes_edges",
        "data_status": "ready"
      }
    },
    {
      "id": "b",
      "intent": {
        "purpose": "show_relationship",
        "relationship": "coordinate",
        "evidence": "point_coordinates",
        "data_status": "ready"
      }
    }
  ]
}
```

输出的 `primary_type` 为 `multipanel`；`panel_routes` 保留每个 `id` 和自己的模板。顶层 `excluded_types` 约束所有面板。嵌套多面板须扁平为叶子面板，再在绘制规格中用行列跨度表达，避免内容被悄悄丢弃。

### 明确图型与歧义

- 用户说“用雷达图，数据稍后给”：`explicit_type: radar`、`data_status: missing`。图型已确定，只列所需数据。
- 用户说“画个图比较几个东西”：目的与材料均 `unknown`。先问“你要比较数值高低，还是展示具体案例差异？”；不要随便选柱图。
- 用户既要求又否定同一种图，或“饼图”与明确父子关系矛盾：先检查原句和参考图，再只澄清冲突部分。
- 没有数据但图意清楚：仍输出确定的图型和所缺输入。可以交付布局规格；不能用示例模板中的数值当作用户实验结果。

## 接口与返回值

完整字段枚举和JSON结构见 [intent.schema.json](intent.schema.json)。默认 `data_status` 为 `missing`；模板的 `data_status: illustrative` 属于绘图规格，不是这个路由接口的数据可用状态。

| 输出 | 含义 |
| --- | --- |
| `primary_type` | 十二类之一、`multipanel`，或尚不能确定时的 `null` |
| `panel_routes` | 多面板逐项路由；保留原panel ID，不按数组长度截断 |
| `reasons` / `reason_codes` | 可读理由及稳定机器原因码 |
| `needs_clarification` / `clarification_question` | 是否仍有改变图义的歧义；不是“缺源数据”的替代标签 |
| `missing_inputs` | 绘制尚缺材料；组合时带面板ID前缀，顶层缺项另保留 |
| `template` / `reference` | 应使用的可复用模板和具体绘制方法 |
| `confidence` | `high` / `medium` / `ambiguous`，表示规则证据强弱，不是校准概率 |
| `status` | `ready` / `needs_inputs` / `needs_clarification` |
| `render_ready` | 只表示所声明材料已齐备且路由清楚；还需模板自己的数据校验 |
| `alternatives` | 冲突或排除时的候选，不能当作已选定类型 |

`explicit_type` 只记录用户明确要求。`purpose` 与 `relationship` 相互冲突时，默认提示澄清；不要把冲突丢掉后取第一项。已知材料结构与图义冲突时也会保留问题。单独提供无歧义二维矩阵、类别树或标量样本可以由结构选择默认类型，泛泛的“数字”或“节点边”不足以判定。

## 路由验证的边界

[52条案例](../assets/routing_cases.json)包含中英原句、人工核对的结构化意图和期望路由，覆盖十二类、否定、冲突、缺数据和多面板。单元测试验证**结构化意图到模板的派发行为**，不能据此宣称“自然语言理解准确率100%”。

验收 skill 时还要做请求原文盲测：给独立代理原始请求、少量数据和 `SKILL.md`，不提供期望类型与gold intent；观察它能否正确提取 purpose/relationship/evidence、保留否定、拆分面板，再调用路由。失败若出在理解步骤，应修改本协议或入口说明，而非只增加一个硬编码关键词。

可用的新请求验证边界：

- “横轴是训练轮次，每个点是一次模型检查；我想看损失是否稳定。”
- “不是看成功率走势，我要展示三次真实操作分别点击了哪里。”
- “两组百分比不共用分母，也没有父子关系，要放成同心环。”
- “画错误类型排名，旁边展示其中一个错误案例。”
- “这些是每个样本的二维投影，不要把横坐标做分箱。”

这些请求中出现的“点”“走势”“百分比”等词只是上下文线索。最终路由依据是用户希望保留的关系和数据结构。
