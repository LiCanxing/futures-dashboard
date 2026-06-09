#!/usr/bin/env python3
"""
期货品种波动率强度综合分析 v3
数据源: 新浪财经连续合约K线 (无需API Key)
"""
import urllib.request
import json
import math
import time
from datetime import datetime

# 期货品种: (新浪代码, 品种名, 交易所)
VARIETIES = [
    # 上期所 SHFE
    ("RB0", "螺纹钢", "上期所"), ("HC0", "热卷", "上期所"),
    ("CU0", "沪铜", "上期所"), ("AL0", "沪铝", "上期所"),
    ("ZN0", "沪锌", "上期所"), ("PB0", "沪铅", "上期所"),
    ("NI0", "沪镍", "上期所"), ("SN0", "沪锡", "上期所"),
    ("AU0", "沪金", "上期所"), ("AG0", "沪银", "上期所"),
    ("RU0", "橡胶", "上期所"), ("SP0", "纸浆", "上期所"),
    ("SS0", "不锈钢", "上期所"), ("BU0", "沥青", "上期所"),
    ("FU0", "燃油", "上期所"),
    # 能源中心 INE
    ("SC0", "原油", "能源中心"), ("NR0", "20号胶", "能源中心"),
    ("LU0", "低硫燃油", "能源中心"), ("BC0", "国际铜", "能源中心"),
    # 大商所 DCE
    ("I0", "铁矿石", "大商所"), ("JM0", "焦煤", "大商所"),
    ("J0", "焦炭", "大商所"), ("M0", "豆粕", "大商所"),
    ("Y0", "豆油", "大商所"), ("P0", "棕榈油", "大商所"),
    ("A0", "豆一", "大商所"), ("B0", "豆二", "大商所"),
    ("C0", "玉米", "大商所"), ("CS0", "淀粉", "大商所"),
    ("JD0", "鸡蛋", "大商所"), ("LH0", "生猪", "大商所"),
    ("L0", "塑料", "大商所"), ("V0", "PVC", "大商所"),
    ("PP0", "聚丙烯", "大商所"), ("EG0", "乙二醇", "大商所"),
    ("EB0", "苯乙烯", "大商所"), ("PG0", "液化气", "大商所"),
    # 郑商所 ZCE
    ("TA0", "PTA", "郑商所"), ("MA0", "甲醇", "郑商所"),
    ("SA0", "纯碱", "郑商所"), ("FG0", "玻璃", "郑商所"),
    ("SR0", "白糖", "郑商所"), ("CF0", "棉花", "郑商所"),
    ("RM0", "菜粕", "郑商所"), ("OI0", "菜油", "郑商所"),
    ("UR0", "尿素", "郑商所"), ("PF0", "短纤", "郑商所"),
    ("SH0", "烧碱", "郑商所"), ("PX0", "对二甲苯", "郑商所"),
    ("PK0", "花生", "郑商所"), ("AP0", "苹果", "郑商所"),
    ("CJ0", "红枣", "郑商所"), ("SF0", "硅铁", "郑商所"),
    ("SM0", "锰硅", "郑商所"),
    # 广期所 GFEX
    ("LC0", "碳酸锂", "广期所"), ("SI0", "工业硅", "广期所"),
    # 中金所 CFFEX（金融期货）
    ("IF0", "沪深300股指", "中金所"), ("IC0", "中证500股指", "中金所"),
    ("IM0", "中证1000股指", "中金所"), ("IH0", "上证50股指", "中金所"),
    ("T0", "10年国债", "中金所"), ("TF0", "5年国债", "中金所"),
    ("TS0", "2年国债", "中金所"), ("TL0", "30年国债", "中金所"),
]

SINA_URL = "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_=_/InnerFuturesNewService.getDailyKLine"


def fetch_sina_kline(symbol):
    """从新浪财经获取期货连续合约日K线"""
    url = f"{SINA_URL}?symbol={symbol}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://finance.sina.com.cn/",
    })
    resp = urllib.request.urlopen(req, timeout=15)
    text = resp.read().decode("gbk")
    
    # 提取JSON
    start = text.find("([")
    if start == -1:
        return None
    end = text.rfind("])")
    data = json.loads(text[start+1:end+1])
    
    # 提取收盘价
    prices = []
    for item in data:
        close = float(item["c"])
        if close > 0:
            prices.append(close)
    return prices


def calc_volatility(prices, window=20):
    """计算历史波动率指标"""
    if len(prices) < window + 10:
        return None
    
    log_returns = [math.log(prices[i]/prices[i-1]) for i in range(1, len(prices))]
    if len(log_returns) < window:
        return None
    
    # 当前年化波动率
    recent = log_returns[-window:]
    mean_r = sum(recent) / len(recent)
    var_r = sum((r-mean_r)**2 for r in recent) / (len(recent)-1)
    current_hv = math.sqrt(var_r) * math.sqrt(250) * 100
    
    # 滚动波动率
    rolling_vols = []
    for i in range(window, len(log_returns)+1):
        w = log_returns[i-window:i]
        m = sum(w)/len(w)
        v = sum((r-m)**2 for r in w)/(len(w)-1)
        rolling_vols.append(math.sqrt(v)*math.sqrt(250)*100)
    
    # 分位数
    sorted_vols = sorted(rolling_vols)
    rank = sum(1 for v in sorted_vols if v <= current_hv)
    percentile = (rank/len(sorted_vols))*100
    
    # 波动率趋势
    n = len(rolling_vols)
    if n >= 20:
        r10 = sum(rolling_vols[-10:])/10
        p10 = sum(rolling_vols[-20:-10])/10
        vol_change_10d = (r10/p10-1)*100 if p10 > 0 else 0
    elif n >= 10:
        r5 = sum(rolling_vols[-5:])/5
        p5 = sum(rolling_vols[-10:-5])/5
        vol_change_10d = (r5/p5-1)*100 if p5 > 0 else 0
    else:
        vol_change_10d = 0
    
    if n >= 5:
        vol_change_5d = (rolling_vols[-1]/rolling_vols[-5]-1)*100
    else:
        vol_change_5d = 0
    
    # 波动率最低值（用于判断是否接近历史极低）
    min_hv = min(rolling_vols)
    # 当前HV相对最低HV的距离
    hv_vs_min = (current_hv/min_hv-1)*100 if min_hv > 0 else 0
    
    # 收敛强度分类
    if percentile < 8 and vol_change_10d < -3:
        zone = "🔴 极值收敛"
        zone_order = 5
    elif percentile < 18 and vol_change_10d < 0:
        zone = "🟠 强收敛"
        zone_order = 4
    elif percentile < 30 and vol_change_10d < 0:
        zone = "🟡 弱收敛"
        zone_order = 3
    elif percentile < 18:
        zone = "🟡 低位横盘"
        zone_order = 2
    elif vol_change_10d > 20:
        zone = "🟢 快速扩张"
        zone_order = -2
    elif vol_change_10d > 5:
        zone = "🟢 温和扩张"
        zone_order = -1
    elif percentile > 85:
        zone = "⚪ 高波区"
        zone_order = 0
    else:
        zone = "⚪ 正常"
        zone_order = 0
    
    return {
        "hv": round(current_hv, 1),
        "percentile": round(percentile, 1),
        "vol_change_10d": round(vol_change_10d, 1),
        "vol_change_5d": round(vol_change_5d, 1),
        "hv_vs_min": round(hv_vs_min, 1),
        "min_hv": round(min_hv, 1),
        "zone": zone,
        "zone_order": zone_order,
        "data_points": len(prices),
        "data_years": round(len(prices)/250, 1),
    }


def color_percentile(p):
    """根据分位数返回颜色标记"""
    if p < 15: return "🔴"
    if p < 30: return "🟠"
    if p < 50: return "🟡"
    if p < 70: return "⚪"
    return "🔵"


def main():
    print("=" * 95)
    print("🔬 期货品种连续合约波动率强度综合分析")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  20日年化历史波动率  |  数据: 新浪财经")
    print("=" * 95)
    
    results = []
    errors = []
    total = len(VARIETIES)
    
    for i, (sym, name, exchange) in enumerate(VARIETIES, 1):
        print(f"  [{i:2d}/{total}] {name:8s} ({sym}) ...", end=" ", flush=True)
        
        try:
            prices = fetch_sina_kline(sym)
        except Exception as e:
            print(f"❌ 请求失败")
            errors.append((name, sym, str(e)[:40]))
            continue
        
        if prices is None or len(prices) < 25:
            print(f"❌ 数据不足")
            errors.append((name, sym, "数据不足"))
            continue
        
        vol = calc_volatility(prices)
        if vol is None:
            print(f"❌ 计算失败")
            errors.append((name, sym, "计算失败"))
            continue
        
        print(f"✅ HV={vol['hv']:>6.1f}% 分位={vol['percentile']:>5.1f}% → {vol['zone']}")
        
        results.append({
            "sym": sym, "name": name, "exchange": exchange,
            **vol,
        })
        
        time.sleep(0.1)
    
    # ===== 分类汇总 =====
    print("\n" + "=" * 95)
    print("📋 波动率状态分类汇总")
    print("=" * 95)
    
    zones_order = ["🔴 极值收敛", "🟠 强收敛", "🟡 弱收敛", "🟡 低位横盘",
                   "⚪ 正常", "⚪ 高波区", "🟢 温和扩张", "🟢 快速扩张"]
    zones_group = {}
    for r in results:
        z = r["zone"]
        zones_group.setdefault(z, []).append(r)
    
    total_convergence = 0
    total_expansion = 0
    for zone in zones_order:
        if zone in zones_group:
            items = zones_group[zone]
            is_conv = any(k in zone for k in ["收敛", "低位"])
            is_exp = "扩张" in zone
            if is_conv: total_convergence += len(items)
            if is_exp: total_expansion += len(items)
            
            print(f"\n  【{zone}】共 {len(items)} 个品种:")
            for item in sorted(items, key=lambda x: x["percentile"]):
                print(f"    {item['name']:10s} {item['sym']:6s} | "
                      f"HV: {item['hv']:>6.1f}% | 分位: {item['percentile']:>5.1f}% | "
                      f"10日Δ: {item['vol_change_10d']:>+6.1f}% | 5日Δ: {item['vol_change_5d']:>+6.1f}% | "
                      f"距最低: {item['hv_vs_min']:>+6.1f}%")
    
    # ===== 全排名 =====
    print("\n" + "=" * 95)
    print("📊 全品种波动率强度排名（收敛→扩张，同状态按分位升序）")
    print("=" * 95)
    print(f"{'#':<3} {'品种':<10} {'代码':<6} {'交易所':<6} {'HV(年化)':<10} {'分位':<8} {'10日Δ':<8} {'5日Δ':<8} {'距最低':<8} {'状态'}")
    print("-" * 95)
    
    # 排序: 收敛优先, 然后按分位
    sorted_r = sorted(results, key=lambda x: (-x["zone_order"], x["percentile"]))
    for i, r in enumerate(sorted_r, 1):
        print(f"{i:<3} {r['name']:<10} {r['sym']:<6} {r['exchange']:<6} "
              f"{r['hv']:>8.1f}% {r['percentile']:>6.1f}% "
              f"{r['vol_change_10d']:>+6.1f}% {r['vol_change_5d']:>+6.1f}% "
              f"{r['hv_vs_min']:>+6.1f}% {r['zone']}")
    
    # ===== 板块分析 =====
    print("\n" + "=" * 95)
    print("📊 按板块汇总")
    print("=" * 95)
    exchanges = {}
    for r in results:
        ex = r["exchange"]
        exchanges.setdefault(ex, []).append(r)
    
    for ex, items in sorted(exchanges.items(), key=lambda x: -len(x[1])):
        avg_hv = sum(r["hv"] for r in items) / len(items)
        avg_pct = sum(r["percentile"] for r in items) / len(items)
        conv_count = sum(1 for r in items if r["zone_order"] > 0)
        exp_count = sum(1 for r in items if r["zone_order"] < 0)
        print(f"  {ex:8s} | {len(items):2d}品种 | 均HV: {avg_hv:5.1f}% | 均分位: {avg_pct:4.1f}% | "
              f"收敛{conv_count} 扩张{exp_count}")
    
    # ===== 重点品种 =====
    print("\n" + "=" * 95)
    print("🎯 重点观察（波动率处于收敛区的品种）")
    print("=" * 95)
    convergence = [r for r in sorted_r if r["zone_order"] >= 3]
    if convergence:
        for r in convergence:
            signal = "⚠️ 极低位，关注爆发" if r["percentile"] < 10 else \
                     "📉 强收敛，等待放量" if r["percentile"] < 18 else \
                     "🔍 弱收敛中"
            print(f"  {r['name']:10s} | 分位{r['percentile']:5.1f}% | HV{r['hv']:5.1f}% | {signal} | "
                  f"距历史最低仅{r['hv_vs_min']:+5.1f}%")
    else:
        print("  暂无极值收敛品种")
    
    # ===== 统计 =====
    print("\n" + "=" * 95)
    print(f"📈 汇总: 分析{len(results)}品种 | 收敛{total_convergence} | 扩张{total_expansion} | "
          f"正常{len(results)-total_convergence-total_expansion} | 错误{len(errors)}")
    
    # 保存JSON
    output = {
        "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "data_source": "新浪财经连续合约K线",
        "method": "20日年化历史波动率",
        "stats": {
            "total": len(results),
            "convergence": total_convergence,
            "expansion": total_expansion,
            "normal": len(results)-total_convergence-total_expansion,
            "errors": len(errors),
        },
        "results": sorted_r,
        "errors": [{"name": e[0], "sym": e[1], "reason": e[2]} for e in errors],
    }
    
    outpath = "/Users/licanxing/.qclaw/workspace-futures-assistant/volatility_results.json"
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"💾 结果: {outpath}")


if __name__ == "__main__":
    main()
