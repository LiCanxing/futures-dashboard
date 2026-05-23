# Task: 看板发布上线与自动化

## 背景
老板要求将期货双维分类看板发布到公网，随时随地可访问。

## 做了什么
1. **GitHub Pages部署** → https://licanxing.github.io/futures-dashboard/
2. **凭据配置** → git credential store + PAT token，后续push免密
3. **页面优化**：
   - 重点关注 2×2 网格（做多/做空上排，底部/风险下排）
   - 品种按钮化、点击弹窗复用
   - 做多红顶、做空绿顶（A股涨红跌绿）

## 待完成
- 15个品种缺K线走势图（API配额不足），明天0点补拉
- 每日cron + git push自动化需验证首跑
