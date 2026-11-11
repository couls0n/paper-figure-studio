# 饼图与环形图 (`proportion`)

## 路由判据

表达一个总体如何组成；两种独立分类可同心，但不得假装父子层级。

语料锚点：AGENTIF Figure 7；OS-Harm Figure 3。它们是形式研究依据，不随skill分发原论文图片。

## 可复用模板

[可运行JSON](../../assets/templates/proportion.json)。其中 `data_status: illustrative` 的数值只演示结构；生成的图会标明示例数据。替换真实数据后使用 observed/transcribed/digitized，并在source中记录来源。

```bash
python scripts/render.py assets/templates/proportion.json --out output/proportion
```

## 输入与变体

统一顶层：`type`, `title`, `width`, `height`, `data_status`, `source`, `data`。默认1000×650像素；字体保留为SVG文字。

`data.rings` 为1–5个对象，各含 `name`, `labels`, `values`；值为非负数且总和大于零。`unit: "percent"`时每环总和须为100（容许0.11的舍入误差）。可给 `denominator` 记录分母。
`layout: "concentric"` 将独立分布同心显示；`"side_by_side"`并排显示且相同类别跨饼保持颜色。后者支持 `donut: false` 画实心饼。

## 具体绘制方法

1. 确认每个环/饼自己的统计对象、分母和互斥类别。
2. 输入计数或百分比；一环独立归一化，别把多环值连接成树。
3. 固定类别颜色、统一旋转起点；同心图用图例前缀标清各环。
4. 类别过多或需精确比较差值时，优先改用横条图。

## 语义检查

双环并不证明层级关系；从百分比不能无依据恢复原始计数。真正的父子分类走 taxonomy；同一总体的多个重叠标签不能当作饼图组成。

## 输出和组合

`scripts/plots.py` 的 `render_plot(spec)` 返回可编辑SVG。根入口统一导出PDF/PNG和布局记录。多面板时将本spec放入panel，显式指定row/column/span；可比图必须保持维度顺序、指标单位、色域或量程一致。
