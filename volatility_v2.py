#!/usr/bin/env python3
"""
期货品种波动率强度分析 v2
使用东方财富公开K线API，无需认证
计算各品种加权指数的历史波动率、分位数、收敛强度
"""
import urllib.request
import json
import math
import time
from datetime import datetime

# 期货品种: (品种名, 东方财富市场代码, 加权指数代码, 交易所)
# 市场代码: 113=上期所, 114=大商所, 115=郑商所, 8=能源中心, 225=中金所, 229=广期所
VARIETIES = [
    # 上期所 SHFE (113)
    ("螺纹钢", 113, "RB8888", "上期所"),
    ("热卷", 113, "HC8888", "上期所"),
    ("沪铜", 113, "CU8888", "上期所"),
    ("沪铝", 113, "AL8888", "上期所"),
    ("沪锌", 113, "ZN8888", "上期所"),
    ("沪铅", 113, "PB8888", "上期所"),
    ("沪镍", 113, "NI8888", "上期所"),
    ("沪锡", 113, "SN8888", "上期所"),
    ("沪银", 113, "AG8888", "上期所"),
    ("沪金", 113, "AU8888", "上期所"),
    ("橡胶", 113, "RU8888", "上期所"),
    ("纸浆", 113, "SP8888", "上期所"),
    ("不锈钢", 113, "SS8888", "上期所"),
    # 能源中心 INE (8)
    ("原油", 8, "SC8888", "能源中心"),
    ("20号胶", 8, "NR8888", "能源中心"),
    ("低硫燃油", 8, "LU8888", "能源中心"),
    # 大商所 DCE (114)
    ("铁矿石", 114, "I8888", "大商所"),
    ("焦煤", 114, "JM8888", "大商所"),
    ("焦炭", 114, "J8888", "大商所"),
    ("豆粕", 114, "M8888", "大商所"),
    ("豆油", 114, "Y8888", "大商所"),
    ("棕榈油", 114, "P8888", "大商所"),
    ("豆一", 114, "A8888", "大商所"),
    ("豆二", 114, "B8888", "大商所"),
    ("玉米", 114, "C8888", "大商所"),
    ("淀粉", 114, "CS8888", "大商所"),
    ("鸡蛋", 114, "JD8888", "大商所"),
    ("生猪", 114, "LH8888", "大商所"),
    ("塑料", 114, "L8888", "大商所"),
    ("PVC", 114, "V8888", "大商所"),
    ("聚丙烯", 114, "PP8888", "大商所"),
    ("乙二醇", 114, "EG8888", "大商所"),
    ("苯乙烯", 114, "EB8888", "大商所"),
    ("纤维板", 114, "FB8888", "大商所"),
    # 郑商所 ZCE (115)
    ("PTA", 115, "TA8888", "郑商所"),
    ("甲醇", 115, "MA8888", "郑商所"),
    ("纯碱", 115, "SA8888", "郑商所"),
    ("玻璃", 115, "FG8888", "郑商所"),
    ("白糖", 115, "SR8888", "郑商所"),
    ("棉花", 115, "CF8888", "郑商所"),
    ("菜粕", 115, "RM8888", "郑商所"),
    ("菜油", 115, "OI8888", "郑商所"),
    ("尿素", 115, "UR8888", "郑商所"),
    ("短纤", 115, "PF8888", "郑商所"),
    ("烧碱", 115, "SH8888", "郑商所"),
    ("对二甲苯", 115, "PX8888", "郑商所"),
    ("花生", 115, "PK8888", "郑商所"),
    ("苹果", 115, "AP8888", "郑商所"),
    ("红枣", 115, "CJ8888", "郑商所"),
    ("硅铁", 115, "SF8888", "郑商所"),
    ("锰硅", 115, "SM8888", "郑商所"),
    # 广期所 GFEX (229)
    ("碳酸锂", 229, "LC8888", "广期所"),
    ("工业硅", 229, "SI8888", "广期所"),
    # 中金所 CFFEX (225)
    ("中证500股指", 225, "IC8888", "中金所"),
    ("沪深300股指", 225, "IF8888", "中金所"),
    ("中证1000股指", 225, "IM8888", "中金所"),
    ("上证50股指", 225, "IH8888", "中金所"),
    ("30年国债", 225, "TL8888", "中金所"),
    ("10年国债", 225, "T8888", "中金所"),
    ("5年国债", 225, "TF8888", "中金所"),
    ("2年国债", 225, "TS8888", "中金所"),
]

KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

def fetch_kline(market_code, symbol, days=250):
    """获取期货K线数据"""
    secid = f"{market_code}.{symbol}"
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",  # 日K
        "fqt": "1",    # 前复权
        "end": "20500101",
        "lmt": str(days),
    }
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{KLINE_URL}?{qs}"
    
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read().decode("utf-8"))
    
    if data.get("data") and data["data"].get("klines"):
        klines = data["data"]["klines"]
        prices = []
        for line in klines:
            parts = line.split(",")
            # f51=日期, f52=开盘, f53=收盘, f54=最高, f55=最低, f56=成交量, f57=成交额, f58=振幅, f59=涨跌幅, f60=涨跌额, f61=换手率
            close = float(parts[2])
            if close > 0:
                prices.append(close)
        return prices
    return None


def calc_volatility(prices, window=20):
    """计算历史波动率及相关指标"""
    if len(prices) < window + 10:
        return None
    
    # 对数收益率
    log_returns = []
    for i in range(1, len(prices)):
        log_returns.append(math.log(prices[i] / prices[i-1]))
    
    if len(log_returns) < window:
        return None
    
    # 当前窗口（最近window天）年化波动率
    recent = log_returns[-window:]
    mean_r = sum(recent) / len(recent)
    var_r = sum((r - mean_r)**2 for r in recent) / (len(recent) - 1)
    current_hv = math.sqrt(var_r) * math.sqrt(250) * 100  # 年化百分比
    
    # 滚动波动率序列
    rolling_vols = []
    for i in range(window, len(log_returns) + 1):
        w = log_returns[i-window:i]
        m = sum(w) / len(w)
        v = sum((r - m)**2 for r in w) / (len(w) - 1)
        rolling_vols.append(math.sqrt(v) * math.sqrt(250) * 100)
    
    # 分位数
    sorted_vols = sorted(rolling_vols)
    rank = sum(1 for v in sorted_vols if v <= current_hv)
    percentile = (rank / len(sorted_vols)) * 100
    
    # 波动率变化趋势（近10日 vs 前10日）
    if len(rolling_vols) >= 20:
        recent_10_avg = sum(rolling_vols[-10:]) / 10
        prev_10_avg = sum(rolling_vols[-20:-10]) / 10
        if prev_10_avg > 0:
            vol_change = (recent_10_avg / prev_10_avg - 1) * 100
        else:
            vol_change = 0
    elif len(rolling_vols) >= 10:
        recent_5_avg = sum(rolling_vols[-5:]) / 5
        prev_5_avg = sum(rolling_vols[-10:-5]) / 5
        if prev_5_avg > 0:
            vol_change = (recent_5_avg / prev_5_avg - 1) * 100
        else:
            vol_change = 0
    else:
        vol_change = 0
    
    # 收敛强度分级
    if percentile < 10 and vol_change < -3:
        zone = "🔴 极值收敛"
        zone_score = 5
    elif percentile < 20 and vol_change < 0:
        zone = "🟠 强收敛"
        zone_score = 4
    elif percentile < 35 and vol_change < 0:
        zone = "🟡 弱收敛"
        zone_score = 3
    elif percentile < 20:
        zone = "🟡 低位横盘"
        zone_score = 2
    elif vol_change > 15:
        zone = "🟢 快速扩张"
        zone_score = -2
    elif vol_change > 5:
        zone = "🟢 温和扩张"
        zone_score = -1
    elif percentile > 85:
        zone = "⚪ 高波区"
        zone_score = 0
    else:
        zone = "⚪ 正常"
        zone_score = 0
    
    # 近5日波动率变化
    if len(rolling_vols) >= 5:
        vol_5d_change = (rolling_vols[-1] / rolling_vols[-5] - 1) * 100
    else:
        vol_5d_change = 0
    
    return {
        "hv": round(current_hv, 2),
        "percentile": round(percentile, 1),
        "vol_change_10d": round(vol_change, 1),
        "vol_change_5d": round(vol_5d_change, 1),
        "zone": zone,
        "zone_score": zone_score,
        "data_points": len(prices),
        "rolling_vols": rolling_vols,
    }


def main():
    print("=" * 90)
    print("🔬 期货品种加权指数波动率强度分析")
    print(f"📅 分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"📊 计算方法: 20日年化历史波动率 | 数据源: 东方财富")
    print("=" * 90)
    
    results = []
    errors = []
    
    for name, market, code, exchange in VARIETIES:
        print(f"  {name:10s} ({code}) ...", end=" ", flush=True)
        
        try:
            prices = fetch_kline(market, code, days=250)
            if prices is None or len(prices) < 25:
                print(f"❌ 数据不足 ({len(prices) if prices else 0}点)")
                errors.append((name, code, f"数据不足"))
                continue
            
            vol = calc_volatility(prices)
            if vol is None:
                print("❌ 计算失败")
                errors.append((name, code, "计算失败"))
                continue
            
            print(f"✅ HV={vol['hv']:.1f}% 分位={vol['percentile']:.1f}% → {vol['zone']}")
            
            results.append({
                "name": name,
                "code": code,
                "exchange": exchange,
                "market": market,
                **vol,
            })
            
        except Exception as e:
            print(f"❌ {str(e)[:40]}")
            errors.append((name, code, str(e)[:40]))
        
        time.sleep(0.15)  # 避免请求过快
    
    print()
    print("=" * 90)
    print("📋 波动率收敛状态分类汇总")
    print("=" * 90)
    
    # 按收敛区分组
    zones_order = ["🔴 极值收敛", "🟠 强收敛", "🟡 弱收敛", "🟡 低位横盘", "⚪ 正常", "⚪ 高波区", "🟢 温和扩张", "🟢 快速扩张"]
    zones_group = {}
    for r in results:
        z = r["zone"]
        if z not in zones_group:
            zones_group[z] = []
        zones_group[z].append(r)
    
    for zone in zones_order:
        if zone in zones_group:
            items = zones_group[zone]
            print(f"\n  【{zone}】共 {len(items)} 个品种:")
            for item in sorted(items, key=lambda x: x["percentile"]):
                print(f"    {item['name']:8s} {item['code']:8s} | "
                      f"HV: {item['hv']:6.1f}% | "
                      f"分位: {item['percentile']:5.1f}% | "
                      f"10日Δ: {item['vol_change_10d']:+6.1f}% | "
                      f"5日Δ: {item['vol_change_5d']:+6.1f}%")
    
    # 全排名表
    print()
    print("=" * 90)
    print("📊 全品种波动率强度排名（按分位数从低到高 → 收敛越强越靠前）")
    print("=" * 90)
    print(f"{'排名':<4} {'品种':<10} {'代码':<8} {'交易所':<6} {'HV(年化)':<10} {'分位数':<8} {'10日变化':<10} {'5日变化':<10} {'状态'}")
    print("-" * 90)
    
    sorted_results = sorted(results, key=lambda x: (x["zone_score"], x["percentile"]), reverse=True)
    for i, r in enumerate(sorted_results, 1):
        print(f"{i:<4} {r['name']:<10} {r['code']:<8} {r['exchange']:<6} "
              f"{r['hv']:>8.1f}% {r['percentile']:>6.1f}% "
              f"{r['vol_change_10d']:>+8.1f}% {r['vol_change_5d']:>+8.1f}% "
              f"{r['zone']}")
    
    # 统计
    convergence_count = sum(1 for r in results if r["zone_score"] > 0)
    expansion_count = sum(1 for r in results if r["zone_score"] < 0)
    normal_count = sum(1 for r in results if r["zone_score"] == 0)
    
    print()
    print(f"📈 统计: 共分析 {len(results)} 个品种")
    print(f"  收敛品种: {convergence_count} 个 | 扩张品种: {expansion_count} 个 | 正常: {normal_count} 个")
    print(f"  数据错误: {len(errors)} 个品种")
    if errors:
        for e in errors:
            print(f"    - {e[0]} ({e[1]}): {e[2]}")
    
    # 保存JSON
    output = {
        "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "stats": {
            "total": len(results),
            "convergence": convergence_count,
            "expansion": expansion_count,
            "normal": normal_count,
            "errors": len(errors),
        },
        "results": sorted_results,
        "errors": [{"name": e[0], "code": e[1], "reason": e[2]} for e in errors],
    }
    
    output_path = "/Users/licanxing/.qclaw/workspace-futures-assistant/volatility_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n💾 详细结果已保存至: {output_path}")


if __name__ == "__main__":
    main()
