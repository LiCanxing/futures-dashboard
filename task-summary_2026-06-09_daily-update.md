# 期货看板每日更新 — 2026-06-09 16:30

## 执行结果

- ✅ 看板生成成功（45个品种，5154KB）
- ✅ git commit + push 完成
- ⚠️ inject_fundamentals.py 因 ZeroDivisionError 失败（不影响主看板）

## 数据拉取

- 拉取成功：12 个品种（热卷、橡胶、淀粉、聚丙烯、PVC、粳米、纤维板、玻璃、白糖、菜粕、红枣、短纤）
- 跳过：33 个品种（API配额耗尽）

## 待修复

inject_fundamentals.py 第157行：`prices[-1]/prices[-min(5,len(prices))]` 当 prices[-N] 为 0 时触发 ZeroDivisionError。需要进行零值保护。
