# 雷达图 (`radar`)

## 路由判据

在固定共同量程下展示同一组多个能力或风险维度的轮廓。

语料锚点：GuardAgent Figure 4；SkillSafetyBench Figure 4；AgentAuditor Figures 4/10。它们是形式研究依据，不随skill分发原论文图片。

## 可复用模板

[可运行JSON](../../assets/templates/radar.json)。其中 `data_status: illustrative` 的数值只演示结构；生成的图会标明示例数据。替换真实数据后使用 observed/transcribed/digitized，并在source中记录来源。

```bash
python scripts/render.py assets/templates/radar.json --out output/radar
```

## 输入与变体

统一顶层：`type`, `title`, `width`, `height`, `data_status`, `source`, `data`。默认1000×650像素；字体保留为SVG文字。

`data.axes`是至少3个不重复维度；`series`含`name`, `values`，按axes顺序；若系列另给`axes`必须完全相同。`range:[min,max]`为共同量程，所有值须落在范围内。
`unit`描述度量；不同单位应事先定义归一化方法并写入来源说明，不能由渲染器悄悄归一化。

## 具体绘制方法

1. 判断每个维度能否共享同一量程和“越高越好”方向。
2. 固定维度顺序，顶部起点，顺时针；数据闭合仅用于形状显示。
3. 使用低透明填充和清楚轮廓；不把多边形面积作为默认指标。
4. 系列过多用小多图，每面板保持同一角度、范围、标签。
5. 三轴Likert与八轴成功率用不同range；始终显示实际标尺。

## 语义检查

原始尺度不同的维度不能直接拼雷达。若任务强调精确差值或排名，bar通常更合适；尊重用户显式图型并说明所需数据处理。

## 输出和组合

`scripts/plots.py` 的 `render_plot(spec)` 返回可编辑SVG。根入口统一导出PDF/PNG和布局记录。多面板时将本spec放入panel，显式指定row/column/span；可比图必须保持维度顺序、指标单位、色域或量程一致。
