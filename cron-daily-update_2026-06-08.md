# 期货看板每日更新 — 2026-06-08 16:30

## 执行摘要
- 看板生成：✅ 成功（5154KB，45品种，45个图表，45条AI备注）
- Git 提交：✅ `9a0abc9` 每日数据刷新 06-08 16:32
- Git 推送：✅ 已推送至 origin/main
- 看板链接：https://licanxing.github.io/futures-dashboard/

## 数据拉取统计
- 总计品种：45 个
- 成功拉取：12 个（热卷、橡胶、淀粉、聚丙烯、PVC、粳米、纤维板、玻璃、白糖、菜粕、红枣、短纤）
- 无数据跳过：33 个（大部分品种，推测 IWENCAI_API_KEY 未设置导致）

## 已知问题
1. **基本面注入失败**：`inject_fundamentals.py` 第157行 `ZeroDivisionError: float division by zero`
   - 原因：某个品种价格列表含零值，计算 mom5 时除零
   - 需要定位并修复
2. **数据覆盖率低**：仅 12/45 品种有行情数据，建议检查 IWENCAI_API_KEY 配置
3. **futures_dashboard.html 未提交**：生成后留在工作区但未 stage，需要确认是否需要一并推送
