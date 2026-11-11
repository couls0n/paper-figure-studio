# 折线图与趋势图 (`line`)

## 路由判据

表达有序或连续变量变化、优化轮次、预算敏感性。

语料锚点：TAI3 Figures 5/16；AGENTIF Figure 5；FormalJudge Figures 4/6。它们是形式研究依据，不随skill分发原论文图片。

## 可复用模板

[可运行JSON](../../assets/templates/line.json)。其中 `data_status: illustrative` 的数值只演示结构；生成的图会标明示例数据。替换真实数据后使用 observed/transcribed/digitized，并在source中记录来源。

```bash
python scripts/render.py assets/templates/line.json --out output/line
```

## 输入与变体

统一顶层：`type`, `title`, `width`, `height`, `data_status`, `source`, `data`。默认1000×650像素；字体保留为SVG文字。

`data.x`为严格递增数值，默认 `x_kind: "numeric"`；明确分组区间时可用字符串且设置 `"categorical"`。每个 `series` 含 `name`, `y`；`null`保留缺测断点。可加 `lower`/`upper`，须等长并满足 lower≤y≤upper，同时声明 `uncertainty`。
可加 `baseline` 和 `baseline_label`；坐标支持 `x_range/y_range`, `x_label/y_label`。

## 具体绘制方法

1. 判断x是真的数值距离，还是仅有顺序的类别；15、30、60必须按真实间距。
2. 对同一系列连接有序观测；保留未观测区间，不偷偷插值填补。
3. 用点标记实际测量位置；由明确的上下界绘制半透明带。
4. 普通模型的灰线应作为独立系列，不能假装不确定性。
5. 各面板是否共享轴需由多面板规格决定；比较不一致量程时明确轴值。

## 语义检查

错误带不是装饰。一个点不存在合理“趋势”；可切换点误差图或bar。numeric x不是按字符串排序的类别。

## 输出和组合

`scripts/plots.py` 的 `render_plot(spec)` 返回可编辑SVG。根入口统一导出PDF/PNG和布局记录。多面板时将本spec放入panel，显式指定row/column/span；可比图必须保持维度顺序、指标单位、色域或量程一致。
