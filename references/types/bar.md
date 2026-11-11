# 柱状图与条形图 (`bar`)

## 路由判据

比较离散类别或方法的数值大小、排名；不存在连续x意义。

语料锚点：TAI3 Figure 6；SkillSafetyBench Figure 6；OS-Harm Figures 5/7。它们是形式研究依据，不随skill分发原论文图片。

## 可复用模板

[可运行JSON](../../assets/templates/bar.json)。其中 `data_status: illustrative` 的数值只演示结构；生成的图会标明示例数据。替换真实数据后使用 observed/transcribed/digitized，并在source中记录来源。

```bash
python scripts/render.py assets/templates/bar.json --out output/bar
```

## 输入与变体

统一顶层：`type`, `title`, `width`, `height`, `data_status`, `source`, `data`。默认1000×650像素；字体保留为SVG文字。

`data.categories` 是不重复的类别；`series` 每项含 `name`, `values`，与类别一一对齐。缺失值用 `null`（留空而非零）。可加 `errors` 非负对称半宽；必须同时填 `data.uncertainty` 说明SD/SE/CI、重复单位和n。
`orientation` 为 `vertical`/`horizontal`；`annotate: true`标数；`format: "%.1f"`控制标签精度。`x_label/y_label`带单位，`x_range/y_range`设标度。

## 具体绘制方法

1. 明确每类的分母与指标方向，输入“类别×系列”值矩阵。
2. 保持组内系列顺序；柱从零开始，支持负值时零线处上下分离。
3. 长类别标签优先横条；同一比较使用同一纵轴和相同误差定义。
4. 绘制柱、误差帽、图例和必要注值；检查误差不被坐标范围裁掉。
5. 若忠实复刻的源图确实截断柱轴，必须显式设置 `allow_truncated_baseline: true` 和 `baseline_note`；改绘新图默认零基线。

## 语义检查

误差数值不是误差定义；须由真实重复或明确定义的区间提供。不能用柱高度近似编造实验值。缺失与真实零区分。

## 输出和组合

`scripts/plots.py` 的 `render_plot(spec)` 返回可编辑SVG。根入口统一导出PDF/PNG和布局记录。多面板时将本spec放入panel，显式指定row/column/span；可比图必须保持维度顺序、指标单位、色域或量程一致。
