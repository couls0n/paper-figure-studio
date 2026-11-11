# 散点图与嵌入点云 (`scatter`)

## 路由判据

表达两个数值变量的关系、效用风险折衷、前后位移或真实投影点云。

语料锚点：Task Shield Figure 3；AgentDojo Figures 6/9；MELON Figures 1/3；AgentPoison Figures 2/11。它们是形式研究依据，不随skill分发原论文图片。

## 可复用模板

[可运行JSON](../../assets/templates/scatter.json)。其中 `data_status: illustrative` 的数值只演示结构；生成的图会标明示例数据。替换真实数据后使用 observed/transcribed/digitized，并在source中记录来源。

```bash
python scripts/render.py assets/templates/scatter.json --out output/scatter
```

## 输入与变体

统一顶层：`type`, `title`, `width`, `height`, `data_status`, `source`, `data`。默认1000×650像素；字体保留为SVG文字。

`data.series`各含`name`, `points: [[x,y],...]`；可含等长`labels`或全图唯一的`point_ids`。可调`size`和`alpha`。
`pairs` 用 `{from_id,to_id,label?}`绑定已有点，或明确 `{from:[x,y],to:[x,y]}`；渲染箭头方向为from→to。`x_reference/y_reference`为显式参考线，`diagonal: true`为y=x。坐标标签应写清好坏方向。

## 具体绘制方法

1. 输入真实二维坐标；若是嵌入，先保存投影方法、参数与seed，避免把独立投影误当共同坐标。
2. 颜色和形状对应明确系列；标签多时分面或用图例。
3. 前后比较通过pair_id或point_id建立对应，不能靠最近邻猜配对。
4. 理想点、阈值、中位线必须由定义或数据得出；不要凭视觉选择Pareto点。
5. 点云演化由multipanel按“嵌入器×轮次”排布，稳定各条件的编码和坐标说明。

## 语义检查

本模板不自动t-SNE/UMAP，也不产生随机点云补数据。它画提供的坐标。大规模点云仍使用完整数据，是否栅格化由输出需求另行决定。

## 输出和组合

`scripts/plots.py` 的 `render_plot(spec)` 返回可编辑SVG。根入口统一导出PDF/PNG和布局记录。多面板时将本spec放入panel，显式指定row/column/span；可比图必须保持维度顺序、指标单位、色域或量程一致。
