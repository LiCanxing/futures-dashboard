#!/usr/bin/env python3
"""
波动率收敛 → 大行情 回测分析
验证：波动率变化百分比与后续大行情的统计关系
"""
import urllib.request, json, math, time
from datetime import datetime
from collections import defaultdict

SINA_URL = "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_=_/InnerFuturesNewService.getDailyKLine"

# 重点品种
FOCUS_VARIETIES = [
    ("RB0", "螺纹钢"), ("I0", "铁矿石"), ("CU0", "沪铜"),
    ("SR0", "白糖"), ("M0", "豆粕"), ("P0", "棕榈油"),
    ("SA0", "纯碱"), ("TA0", "PTA"), ("MA0", "甲醇"),
    ("FG0", "玻璃"), ("AU0", "沪金"), ("AG0", "沪银"),
    ("SC0", "原油"), ("CF0", "棉花"), ("AP0", "苹果"),
    ("PK0", "花生"), ("RM0", "菜粕"), ("Y0", "豆油"),
    ("LC0", "碳酸锂"), ("SI0", "工业硅"),
]

def fetch_prices(symbol):
    url = f"{SINA_URL}?symbol={symbol}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn/",
    })
    resp = urllib.request.urlopen(req, timeout=15)
    text = resp.read().decode("gbk")
    start = text.find("([")
    if start == -1: return None
    end = text.rfind("])")
    data = json.loads(text[start+1:end+1])
    prices = [(item["d"], float(item["c"])) for item in data if float(item["c"]) > 0]
    return prices


def run_backtest(prices, vol_window=20, fwd_window=20, big_move_threshold=2.0):
    """
    回测逻辑:
    - 在每个交易日 t，计算:
      1. 过去 vol_window 天的年化波动率
      2. 波动率变化: vol_change_10d (近10日 vs 前10日)
      3. 波动率分位数
      4. 未来 fwd_window 天的价格变化幅度（绝对值）
    - 判断是否发生"大行情": |fwd_return| > big_move_threshold × 当前年化HV × sqrt(fwd_window/250)
    """
    if len(prices) < vol_window + fwd_window + 20:
        return []
    
    closes = [p[1] for p in prices]
    dates = [p[0] for p in prices]
    N = len(closes)
    
    # 对数收益率
    log_returns = [math.log(closes[i]/closes[i-1]) for i in range(1, N)]
    
    # 滚动波动率
    rolling_vols = []
    for i in range(vol_window, len(log_returns)+1):
        w = log_returns[i-vol_window:i]
        m = sum(w)/len(w)
        v = sum((r-m)**2 for r in w)/(len(w)-1)
        rolling_vols.append(math.sqrt(v)*math.sqrt(250)*100)
    
    # 计算所有滚动波动率的分位数（用于后期分析）
    all_vols_sorted = sorted(rolling_vols)
    
    records = []
    # 从有足够历史且有足够未来数据的位置开始
    start_idx = 20  # 需要前20个滚动vol来做10日变化
    end_idx = len(rolling_vols) - fwd_window
    
    for i in range(start_idx, end_idx):
        current_hv = rolling_vols[i]
        
        # 波动率变化 10日
        r10 = sum(rolling_vols[i-10:i])/10
        p10 = sum(rolling_vols[i-20:i-10])/10
        vol_change_10d = (r10/p10-1)*100 if p10 > 0 else 0
        
        # 波动率变化 20日
        r20 = sum(rolling_vols[i-20:i])/20
        if i >= 40:
            p20 = sum(rolling_vols[i-40:i-20])/20
            vol_change_20d = (r20/p20-1)*100 if p20 > 0 else 0
        else:
            vol_change_20d = None
        
        # 分位数
        rank = sum(1 for v in all_vols_sorted if v <= current_hv)
        percentile = (rank/len(all_vols_sorted))*100
        
        # 未来 N 天价格变化
        future_start_price = closes[vol_window + i]
        future_end_price = closes[vol_window + i + fwd_window]
        fwd_return = (future_end_price/future_start_price - 1) * 100  # 百分比
        
        # 大行情阈值
        threshold = big_move_threshold * current_hv * math.sqrt(fwd_window/250) / 100
        # 其实是: N倍标准差 × HV × √(fwd/250) = N × daily_vol × √fwd
        # 简化：当前HV是年化的，日波动 = HV/√250，前向波动 = 日波动×√fwd = HV×√(fwd/250)
        daily_vol = current_hv / math.sqrt(250)
        fwd_vol = daily_vol * math.sqrt(fwd_window)
        is_big_move = abs(fwd_return) > big_move_threshold * fwd_vol
        
        records.append({
            "date": dates[vol_window + i],
            "hv": current_hv,
            "percentile": percentile,
            "vol_change_10d": vol_change_10d,
            "vol_change_20d": vol_change_20d,
            "fwd_return": fwd_return,
            "fwd_abs_return": abs(fwd_return),
            "fwd_vol_expected": fwd_vol,
            "is_big_move": is_big_move,
            "move_ratio": abs(fwd_return)/fwd_vol if fwd_vol > 0 else 0,
        })
    
    return records


def analyze_thresholds(all_records):


    print("=" * 100)
    print("📊 波动率收敛强度 → 后续大行情概率 回测分析")
    print("=" * 100)
    print(f"方法: 20日HV, 未来20日回报 | 大行情定义: |回报| > 2×预期波动")
    print(f"总样本: {len(all_records):,} 个交易日 | 总品种: {len([r for r in all_records if r])} 个")
    print()
    
    # ===== 分析1: 波动率变化(10日) vs 后续大行情概率 =====
    print("━" * 100)
    print("📈 分析1: 波动率10日变化率 与 后续20日大行情概率")
    print("━" * 100)
    
    # 按波动率变化分桶
    buckets = [
        ("暴跌 -40%以下", -100, -40),
        ("大幅收敛 -40%~-20%", -40, -20),
        ("中等收敛 -20%~-10%", -20, -10),
        ("小幅收敛 -10%~-5%", -10, -5),
        ("微收敛 -5%~0%", -5, 0),
        ("微扩张 0%~5%", 0, 5),
        ("小幅扩张 5%~10%", 5, 10),
        ("中等扩张 10%~20%", 10, 20),
        ("大幅扩张 20%~40%", 20, 40),
        ("暴涨 40%以上", 40, 500),
    ]
    
    print(f"{'波动率变化区间':<24} {'样本数':>8} {'大行情概率':>10} {'平均|回报|':>12} {'平均收益':>10} {'正收益率':>10} {'均值/预期波':>12}")
    print("-" * 100)
    
    for label, lo, hi in buckets:
        subset = [r for r in all_records if lo <= r["vol_change_10d"] < hi]
        if len(subset) < 50:
            continue
        
        n = len(subset)
        big_pct = sum(1 for r in subset if r["is_big_move"]) / n * 100
        avg_abs_ret = sum(r["fwd_abs_return"] for r in subset) / n
        avg_ret = sum(r["fwd_return"] for r in subset) / n
        pos_pct = sum(1 for r in subset if r["fwd_return"] > 0) / n * 100
        avg_ratio = sum(r["move_ratio"] for r in subset) / n
        
        bar = "█" * int(big_pct / 2) if big_pct < 60 else "█" * 30
        print(f"{label:<24} {n:>8,} {big_pct:>9.1f}% {avg_abs_ret:>11.2f}% {avg_ret:>9.2f}% {pos_pct:>9.1f}% {avg_ratio:>11.2f}x {bar}")
    
    # ===== 分析2: 分位数 + 变化率 交叉分析 =====
    print()
    print("━" * 100)
    print("📈 分析2: 低分位 + 收敛 = 大行情催化剂？")
    print("━" * 100)
    print(f"{'条件':<40} {'样本数':>8} {'大行情概率':>10} {'平均|回报|':>12} {'平均收益':>10} {'正收益率':>10}")
    print("-" * 100)
    
    conditions = [
        ("分位<10% 且 10日Δ<-20% (极值+暴跌收敛)", lambda r: r["percentile"]<10 and r["vol_change_10d"]<-20),
        ("分位<10% 且 10日Δ<-10% (极值+大幅收敛)", lambda r: r["percentile"]<10 and r["vol_change_10d"]<-10),
        ("分位<15% 且 10日Δ<-10% (强收敛)", lambda r: r["percentile"]<15 and r["vol_change_10d"]<-10),
        ("分位<20% 且 10日Δ<0   (低位+收敛中)", lambda r: r["percentile"]<20 and r["vol_change_10d"]<0),
        ("分位<20% 且 10日Δ<-10% (低位+大幅收敛)", lambda r: r["percentile"]<20 and r["vol_change_10d"]<-10),
        ("分位<25% 且 10日Δ<0   (偏低+收敛中)", lambda r: r["percentile"]<25 and r["vol_change_10d"]<0),
        ("--- 对照组 ---", None),
        ("所有样本 (基准)", lambda r: True),
        ("分位>85% (高波区)", lambda r: r["percentile"]>85),
        ("10日Δ>20% (快速扩张)", lambda r: r["vol_change_10d"]>20),
    ]
    
    for label, cond in conditions:
        if cond is None:
            print(f"  {label}")
            continue
        subset = [r for r in all_records if cond(r)]
        if len(subset) < 20:
            print(f"{label:<40} {len(subset):>8} {'(样本太少)':>10}")
            continue
        n = len(subset)
        big_pct = sum(1 for r in subset if r["is_big_move"]) / n * 100
        avg_abs = sum(r["fwd_abs_return"] for r in subset) / n
        avg_ret = sum(r["fwd_return"] for r in subset) / n
        pos_pct = sum(1 for r in subset if r["fwd_return"] > 0) / n * 100
        print(f"{label:<40} {n:>8,} {big_pct:>9.1f}% {avg_abs:>11.2f}% {avg_ret:>9.2f}% {pos_pct:>9.1f}%")
    
    # ===== 分析3: 精确阈值扫描 =====
    print()
    print("━" * 100)
    print("📈 分析3: 最优阈值扫描 — 不同vol_change阈值下的大行情概率")
    print("━" * 100)
    
    print(f"{'阈值条件':<30} {'样本数':>8} {'大行情概率':>10} {'提升幅度':>10} {'平均|回报|':>12}")
    print("-" * 100)
    
    baseline = [r for r in all_records]
    base_big_pct = sum(1 for r in baseline if r["is_big_move"]) / len(baseline) * 100
    
    thresholds = [-5, -10, -15, -20, -25, -30, -40]
    for t in thresholds:
        subset = [r for r in all_records if r["vol_change_10d"] <= t]
        if len(subset) < 30: continue
        n = len(subset)
        big_pct = sum(1 for r in subset if r["is_big_move"]) / n * 100
        boost = big_pct - base_big_pct
        avg_abs = sum(r["fwd_abs_return"] for r in subset) / n
        bar = "█" * int(big_pct / 2)
        print(f"10日Δ ≤ {t:>+4}%                    {n:>8,} {big_pct:>9.1f}% {boost:>+9.1f}% {avg_abs:>11.2f}% {bar}")
    
    # 同时加分位条件
    print()
    print(f"{'阈值条件':<40} {'样本数':>8} {'大行情概率':>10} {'提升幅度':>10} {'平均|回报|':>12}")
    print("-" * 100)
    
    for pct_th in [10, 15, 20]:
        for vol_th in [-5, -10, -15, -20]:
            subset = [r for r in all_records if r["percentile"] <= pct_th and r["vol_change_10d"] <= vol_th]
            if len(subset) < 20: continue
            n = len(subset)
            big_pct = sum(1 for r in subset if r["is_big_move"]) / n * 100
            boost = big_pct - base_big_pct
            avg_abs = sum(r["fwd_abs_return"] for r in subset) / n
            label = f"分位≤{pct_th}% 且 Δ≤{vol_th:+d}%"
            print(f"{label:<40} {n:>8,} {big_pct:>9.1f}% {boost:>+9.1f}% {avg_abs:>11.2f}%")


def main():
    print("🔄 正在加载各品种历史数据并回测...")
    print()
    
    all_records = []
    
    for sym, name in FOCUS_VARIETIES:
        print(f"  {name:6s} ({sym}) ...", end=" ", flush=True)
        try:
            prices = fetch_prices(sym)
            if not prices or len(prices) < 100:
                print(f"❌ 数据不足")
                continue
            records = run_backtest(prices, vol_window=20, fwd_window=20, big_move_threshold=2.0)
            if records:
                print(f"✅ {len(records):,} 个样本")
                all_records.extend(records)
            else:
                print(f"❌ 回测失败")
        except Exception as e:
            print(f"❌ {str(e)[:30]}")
        time.sleep(0.1)
    
    print(f"\n📊 汇总: {len(all_records):,} 个有效样本\n")
    
    if len(all_records) < 100:
        print("样本不足，无法分析")
        return
    
    analyze_thresholds(all_records)


if __name__ == "__main__":
    main()
