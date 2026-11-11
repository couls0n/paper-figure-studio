# 统计分布图 (`distribution`)

## 路由判据

比较样本的形状、离散程度与尾部，而不是仅比较均值。

语料锚点：AGENTIF Figure 1a；TAI3 Figure 9；AgentPoison Figures 5/10。它们是形式研究依据，不随skill分发原论文图片。

## 可复用模板

[可运行JSON](../../assets/templates/distribution.json)。其中 `data_status: illustrative` 的数值只演示结构；生成的图会标明示例数据。替换真实数据后使用 observed/transcribed/digitized，并在source中记录来源。

```bash
python scripts/render.py assets/templates/distribution.json --out output/distribution
```

## 输入与变体

统一顶层：`type`, `title`, `width`, `height`, `data_status`, `source`, `data`。默认1000×650像素；字体保留为SVG文字。

`data.groups` 各含`name`与非空有限数`samples`。`kind`为histogram/kde。直方图 `bins`是整数或严格递增边界，所有组共享同一分箱；`density`控制计数/密度。KDE可给正数 `bandwidth`，单位与x相同；默认用Silverman正态参考带宽。常数样本需显式带宽。
支持 `x_range`, `x_label/y_label`；`y_scale:"log"`可画对数频数，但须解释零频数不可显示。

## 具体绘制方法

1. 获取逐样本数据，记录变换和排除规则；不得从均值和SD虚构样本。
2. 直方图选明确共享bin边界；比较不同样本量时明确使用count还是density。
3. KDE保留带宽与核函数：本实现为高斯核；检查边界泄漏与不可能负值区域。
4. 画半透明叠加或将不同组分面；确认尾部没有因随意裁切而消失。
5. 若源图只给分箱计数，使用明确的分箱图（先按已知边界构造bar），不能声称恢复KDE所需原样本。

## 语义检查

KDE是平滑估计，不是观测频数；对数坐标不等于先取log后估计密度。不要混淆两种变换。

## 输出和组合

`scripts/plots.py` 的 `render_plot(spec)` 返回可编辑SVG。根入口统一导出PDF/PNG和布局记录。多面板时将本spec放入panel，显式指定row/column/span；可比图必须保持维度顺序、指标单位、色域或量程一致。
