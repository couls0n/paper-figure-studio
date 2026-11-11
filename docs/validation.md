# 验证记录

验证日期：2026-11-11。环境：Python 3.12.14，完整依赖版本见 [requirements-lock.txt](../requirements-lock.txt)。

最终行为测试：68 项通过。另有 52 条结构化路由案例和 24 个独立自然语言请求演练；这两个案例数不与测试函数数相加。

## 路由与入口

- `skill-creator` 的 `quick_validate.py` 检查通过：技能名称、frontmatter 与入口结构有效。
- 52 个中英案例验证结构化意图派发，覆盖 12 类、否定、冲突、缺数据以及 28 面板完整保留。
- [独立流程演练](forward-evaluation.md) 从 24 个新的自然语言请求开始，经代理解析再调用路由；本次类型和状态均符合语义审查。该结果不代表总体自然语言准确率。

## 论文风格强化

案例、流程和执行轨迹新增三组 paper profile、六种可运行版式，分别对照 TAI3/BadAgent、TAI3/Task Shield、AgentDAM/ShieldAgent 原图。增加内容对齐、词边界换行、跨行高亮、同一步骤标注对齐、表格单元和几何回归；实际查看六份 SVG 经 PDF 转换后的 PNG。独立视觉审查与修复复验见 [taste-independent-review.md](taste-independent-review.md)。

## 渲染与组合

全部 12 个默认模板、3 个额外论文版式和 2 个组合示例已实际导出 SVG、PDF、PNG，并查看图像。图集包含混合四面板与 7×4 的 28 面板。示例内容均明确标注为 illustrative。

实际检查中修复了分类坐标标签被重置、SVG 引用丢失、字体与透明度导出差异，以及子 SVG 位置在 PDF 转换时被忽略的问题。组合器采用显式缩放、平移和裁剪；回归测试将 28 个彩色面板转成 PDF 再取像素，检查每个面板实际落在对应位置。

独立演练另生成中文架构、中文柱图、长文本/代码卡和 a/b 组合。架构图中发现的边标签压节点、反馈线穿节点已修复，四份新图完成视觉复验。其输入规格、初次观察与复验状态记录在 [forward-evaluation.json](forward-evaluation.json)。

## 如何复跑

在已安装依赖的仓库目录执行：

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/build_gallery.py --out output/gallery
```

行为检查涉及数值轴真实间距、缺失值与零的区别、误差定义、雷达轴顺序、独立环的归一化、配对端点、文本和节点保留、布局越界以及意图路由。导出成功不能代替最终视觉检查；布局记录中的网格检查也不等于所有子图的绘图区已精确对齐。

## 范围

模板提供每类可运行基线和扩展方法。它们不是对全部论文图片的逐像素重制。实际研究结果仍需要用户提供数据、截图或可追溯的数字化值；本 skill 不会从聚合统计补造逐样本观测。
