# 热图与矩阵图 (`matrix`)

## 路由判据

表达双轴组合的量、跨源目标迁移、成对相关性或真值/预测计数。

语料锚点：TAI3 Figures 7/10/11；AgentPoison Figures 3/7/8；AgentDAM Figure 6；AgentAuditor Figure 9。它们是形式研究依据，不随skill分发原论文图片。

## 可复用模板

[可运行JSON](../../assets/templates/matrix.json)。其中 `data_status: illustrative` 的数值只演示结构；生成的图会标明示例数据。替换真实数据后使用 observed/transcribed/digitized，并在source中记录来源。

```bash
python scripts/render.py assets/templates/matrix.json --out output/matrix
```

## 输入与变体

统一顶层：`type`, `title`, `width`, `height`, `data_status`, `source`, `data`。默认1000×650像素；字体保留为SVG文字。

`data.values` 是矩形二维数组，配 `row_labels`, `column_labels`。`mask`同形boolean，true表示不显示；`null`为缺失，也被屏蔽。`kind` 为general/transfer/correlation/confusion。相关矩阵需相同行列、对称值且值域[-1,1]；混淆矩阵须方阵且非负。
`vmin/vmax`固定色域，`unit`标色条单位，`format: ".2f"`控制格内注值，`mask_label: "—"`标空白；`cmap`可指定matplotlib色图。

## 具体绘制方法

1. 先说明行、列含义；迁移图为source→target，混淆图为true→predicted。
2. 从真实数据构造矩阵；均值行/列在数据阶段计算并有明确标签。
3. 明确屏蔽对角与缺失项；不要填零。
4. 为可比面板固定色域和单位；注值按底色亮度选择黑白文字。
5. 核对色条与单元标注使用同一比例/百分数，不把0–1与0–100混写。

## 语义检查

从各模型总成功率无法反推相关矩阵，需要逐任务配对标签。平均混淆计数不是百分比。泛化时不能复制源图的单位冲突。

## 输出和组合

`scripts/plots.py` 的 `render_plot(spec)` 返回可编辑SVG。根入口统一导出PDF/PNG和布局记录。多面板时将本spec放入panel，显式指定row/column/span；可比图必须保持维度顺序、指标单位、色域或量程一致。
