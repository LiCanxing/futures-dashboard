# 期货看板基本面跟踪 Tab - V2 修复

## 问题
V1 版本在修改 HTML 时丢失了 `var V=` K线数据块（1.5MB），导致看板失去所有历史走势图功能。

## 修复方案
采用行级分段编辑：
- 识别文件结构：350行，行172=CSS结束，行176=副标题，行299=弹窗div，行302=数据
- 将文件分为三个区段：prefix(0-176)、matrix(177-299)、tail(300-349)
- 对 prefix 注入 Tab CSS + 替换标题为 Tab 按钮
- 对 matrix 包裹 tab-content div + 插入基本面面板 HTML
- 对 tail 注入 fundamentals JS（switchTab/initFundamentals/buildCard/showFundDetail）

## 验证结果
- 括号平衡：440/440 ✅
- var V= 数据：1,536,008 字符 ✅
- price_dates 数据完整 ✅
- Modal 在 tab-content 之外 ✅
- 2个 tab-content div ✅
- HTML 正确闭合 ✅
- 文件大小：1,567,885 字节 ✅

## 数据覆盖
10个核心品种（按持仓量排名）：豆粕、螺纹钢、热卷、玻璃、菜粕、PVC、豆油、甲醇、聚丙烯、鸡蛋

分析基于：
- 本地K线数据库（2009年以来4168个交易日）
- 四层漏斗框架（宏观→供需→现货→盘面）
- 来源角标系统（0=本地K线、4=统计局、8=外汇中心、9=文华财经）

## 已知限制
- 外部API暂时限流，第二层基本面数据（库存/基差/利润）较薄
- 仅覆盖10个TOP品种，其余35个待扩展
