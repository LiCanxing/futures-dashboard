# fix: inject_fundamentals.py 零值除零保护

**时间**: 2026-06-09 21:40
**触发**: 每日定时任务报 inject_fundamentals.py:157 除零错误

## 修复内容

1. **动量计算** (line ~157): `mom5/20/60` 用 `safe_mom()` 函数包装，`prev==0` 时返回0
2. **OI变化率** (line ~140): `chg30oi/60oi` 加除数零值检查
3. **展示涨幅** (line ~231, ~278): `yr_high/p_cur` 加 `p_cur > 0` 保护

## 验证

运行 `python3 inject_fundamentals.py` → 45品种全部成功注入，git push 正常。
