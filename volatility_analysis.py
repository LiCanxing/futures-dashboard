#!/usr/bin/env python3
"""
期货品种加权指数波动率强度分析
计算各品种历史波动率(HV)、波动率分位数、收敛/扩张状态
"""

import os
import json
import secrets
import urllib.request
import math
import sys
from datetime import datetime, timedelta

API_KEY = os.environ.get("IWENCAI_API_KEY", "")
API_URL = "https://openapi.iwencai.com/v1/query2data"

# 主要期货品种列表（加权指数代码）
# 格式: (问财查询名称, 品种中文名, 品种代码)
FUTURES_VARIETIES = [
    # 黑色系
    ("螺纹钢指数", "螺纹钢", "RB"),
    ("热卷指数", "热卷", "HC"),
    ("铁矿石指数", "铁矿石", "I"),
    ("焦煤指数", "焦煤", "JM"),
    ("焦炭指数", "焦炭", "J"),
    ("硅铁指数", "硅铁", "SF"),
    ("锰硅指数", "锰硅", "SM"),
    # 有色系
    ("沪铜指数", "沪铜", "CU"),
    ("沪铝指数", "沪铝", "AL"),
    ("沪锌指数", "沪锌", "ZN"),
    ("沪铅指数", "沪铅", "PB"),
    ("沪镍指数", "沪镍", "NI"),
    ("沪锡指数", "沪锡", "SN"),
    ("沪银指数", "沪银", "AG"),
    ("沪金指数", "沪金", "AU"),
    # 能化系
    ("原油指数", "原油", "SC"),
    ("PTA指数", "PTA", "TA"),
    ("甲醇指数", "甲醇", "MA"),
    ("纯碱指数", "纯碱", "SA"),
    ("玻璃指数", "玻璃", "FG"),
    ("PVC指数", "PVC", "V"),
    ("聚丙烯指数", "聚丙烯", "PP"),
    ("塑料指数", "塑料", "L"),
    ("乙二醇指数", "乙二醇", "EG"),
    ("苯乙烯指数", "苯乙烯", "EB"),
    ("尿素指数", "尿素", "UR"),
    # 农产品
    ("豆粕指数", "豆粕", "M"),
    ("豆油指数", "豆油", "Y"),
    ("棕榈油指数", "棕榈油", "P"),
    ("菜粕指数", "菜粕", "RM"),
    ("白糖指数", "白糖", "SR"),
    ("棉花指数", "棉花", "CF"),
    ("玉米指数", "玉米", "C"),
    ("鸡蛋指数", "鸡蛋", "JD"),
    ("生猪指数", "生猪", "LH"),
    ("苹果指数", "苹果", "AP"),
    ("花生指数", "花生", "PK"),
    # 广期所
    ("碳酸锂指数", "碳酸锂", "LC"),
    ("工业硅指数", "工业硅", "SI"),
]


def query_wencai(query_text, page="1", limit="50", call_type="normal"):
    """调用问财API查询数据"""
    trace_id = secrets.token_hex(32)
    
    payload = {
        "query": query_text,
        "page": page,
        "limit": limit,
        "is_cache": "1",
        "expand_index": "true"
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "X-Claw-Call-Type": call_type,
        "X-Claw-Skill-Id": "hithink-futures-query",
        "X-Claw-Skill-Version": "1.0.0",
        "X-Claw-Plugin-Id": "none",
        "X-Claw-Plugin-Version": "none",
        "X-Claw-Trace-Id": trace_id,
    }
    
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
    response = urllib.request.urlopen(request, timeout=30)
    return json.loads(response.read().decode("utf-8"))


def calculate_historical_volatility(prices, window=20, annualize=True):
    """计算历史波动率 (HV)"""
    if len(prices) < window + 1:
        return None, None, None
    
    log_returns = []
    for i in range(1, len(prices)):
        if prices[i-1] and prices[i] and prices[i-1] > 0:
            log_returns.append(math.log(prices[i] / prices[i-1]))
    
    if len(log_returns) < window:
        return None, None, None
    
    # 当前窗口波动率（最近window天）
    recent_returns = log_returns[-window:]
    if len(recent_returns) < window:
        return None, None, None
    
    mean_return = sum(recent_returns) / len(recent_returns)
    variance = sum((r - mean_return) ** 2 for r in recent_returns) / (len(recent_returns) - 1)
    daily_vol = math.sqrt(variance)
    
    if annualize:
        annual_vol = daily_vol * math.sqrt(250)  # 年化
    else:
        annual_vol = daily_vol
    
    # 计算滚动波动率序列用于分位数计算
    rolling_vols = []
    for i in range(window, len(log_returns) + 1):
        window_returns = log_returns[i-window:i]
        if len(window_returns) >= window:
            mean_r = sum(window_returns) / len(window_returns)
            var_r = sum((r - mean_r) ** 2 for r in window_returns) / (len(window_returns) - 1)
            rolling_vols.append(math.sqrt(var_r) * math.sqrt(250))
    
    # 当前波动率在历史中的分位数
    if rolling_vols and annual_vol is not None:
        sorted_vols = sorted(rolling_vols)
        rank = sum(1 for v in sorted_vols if v <= annual_vol)
        percentile = (rank / len(sorted_vols)) * 100
    else:
        percentile = None
    
    # 波动率变化趋势（最近5日波动率变化方向）
    if len(rolling_vols) >= 10:
        recent_5 = rolling_vols[-5:]
        prev_5 = rolling_vols[-10:-5]
        vol_change_pct = ((sum(recent_5)/5) / (sum(prev_5)/5) - 1) * 100
    else:
        vol_change_pct = None
    
    # 波动率收敛强度
    # 如果波动率在下降（收敛），返回收敛强度
    # 弱收敛: vol在50-70分位, vol_change在-5%到0%
    # 中等收敛: vol在30-50分位, vol_change在-10%到-5%
    # 强收敛: vol在10-30分位, vol_change < -10%
    # 极值收敛: vol < 10分位
    convergence_zone = "正常"
    if percentile is not None and vol_change_pct is not None:
        if percentile < 10:
            convergence_zone = "极值收敛区 🔴"
        elif percentile < 25 and vol_change_pct < -5:
            convergence_zone = "强收敛区 🟠"
        elif percentile < 40 and vol_change_pct < 0:
            convergence_zone = "弱收敛区 🟡"
        elif percentile < 25:
            convergence_zone = "低位横盘 🟡"
        elif vol_change_pct > 10:
            convergence_zone = "扩张中 🟢"
        elif vol_change_pct > 5:
            convergence_zone = "温和扩张 🟢"
        elif percentile > 80:
            convergence_zone = "高波区 ⚪"
    
    return {
        "current_hv": round(annual_vol * 100, 2) if annual_vol else None,  # 百分比
        "percentile": round(percentile, 1) if percentile is not None else None,
        "vol_change_pct": round(vol_change_pct, 1) if vol_change_pct is not None else None,
        "convergence_zone": convergence_zone,
        "rolling_vols": rolling_vols,
    }


def get_futures_index_prices(variety_name):
    """查询期货品种指数的历史收盘价"""
    # 查询最近180个交易日的日线收盘价
    query = f"{variety_name} 近180个交易日 收盘价"
    
    try:
        result = query_wencai(query, limit="200")
        datas = result.get("datas", [])
        
        if not datas:
            # 重试
            result = query_wencai(f"{variety_name} 近半年 收盘价", limit="200", call_type="retry")
            datas = result.get("datas", [])
        
        if not datas:
            return None
        
        # 提取价格数据
        prices = []
        for item in datas:
            close_price = None
            for key in item:
                if "收盘" in key or "close" in key.lower() or "最新价" in key:
                    try:
                        close_price = float(item[key])
                        break
                    except (ValueError, TypeError):
                        continue
            
            if close_price is None:
                # 尝试其他可能的字段名
                for key in item:
                    try:
                        v = float(item[key])
                        if 10 < v < 100000:  # 合理的期货价格范围
                            close_price = v
                            break
                    except (ValueError, TypeError):
                        continue
            
            if close_price is not None:
                prices.append(close_price)
        
        # 问财返回的顺序通常是最新的在前，需要反转
        prices.reverse()
        return prices
        
    except Exception as e:
        print(f"  查询 {variety_name} 出错: {e}", file=sys.stderr)
        return None


def query_volatility_direct(variety_name):
    """直接查询期货品种的波动率数据"""
    query = f"{variety_name} 20日历史波动率 近1年"
    
    try:
        result = query_wencai(query, limit="200")
        datas = result.get("datas", [])
        
        if not datas:
            return None
        
        # 提取波动率数据
        vol_data = []
        for item in datas:
            vol_val = None
            date_val = None
            for key in item:
                if "波动率" in key or "vol" in key.lower():
                    try:
                        vol_val = float(item[key])
                    except (ValueError, TypeError):
                        continue
                if "日期" in key or "date" in key.lower():
                    date_val = item[key]
            
            if vol_val is not None:
                vol_data.append({"date": date_val, "volatility": vol_val})
        
        return vol_data
        
    except Exception as e:
        print(f"  查询 {variety_name} 波动率出错: {e}", file=sys.stderr)
        return None


def main():
    print("=" * 80)
    print("期货品种加权指数波动率强度分析")
    print(f"分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    print()
    
    results = []
    
    for query_name, cn_name, code in FUTURES_VARIETIES:
        print(f"正在分析: {cn_name} ({code})...", end=" ", flush=True)
        
        # 获取历史价格
        prices = get_futures_index_prices(query_name)
        
        if prices is None or len(prices) < 25:
            print("❌ 数据不足")
            continue
        
        # 计算波动率
        vol_info = calculate_historical_volatility(prices, window=20)
        
        if vol_info["current_hv"] is None:
            print("❌ 无法计算波动率")
            continue
        
        print(f"✅ HV={vol_info['current_hv']}% 分位={vol_info['percentile']}% 变化={vol_info['vol_change_pct']}% → {vol_info['convergence_zone']}")
        
        results.append({
            "code": code,
            "name": cn_name,
            "current_hv": vol_info["current_hv"],
            "percentile": vol_info["percentile"],
            "vol_change_pct": vol_info["vol_change_pct"],
            "convergence_zone": vol_info["convergence_zone"],
            "data_points": len(prices),
        })
    
    # 按收敛区分类统计
    print()
    print("=" * 80)
    print("波动率收敛状态分类汇总")
    print("=" * 80)
    
    zones = {}
    for r in results:
        zone = r["convergence_zone"]
        if zone not in zones:
            zones[zone] = []
        zones[zone].append(r)
    
    zone_order = ["极值收敛区 🔴", "强收敛区 🟠", "弱收敛区 🟡", "低位横盘 🟡", "正常", "温和扩张 🟢", "扩张中 🟢", "高波区 ⚪"]
    
    for zone in zone_order:
        if zone in zones:
            items = zones[zone]
            print(f"\n【{zone}】共 {len(items)} 个品种:")
            for item in sorted(items, key=lambda x: x["percentile"]):
                print(f"  {item['name']:6s} ({item['code']:4s}) | HV: {item['current_hv']:6.2f}% | "
                      f"分位: {item['percentile']:5.1f}% | 变化: {item['vol_change_pct']:+6.1f}%")
    
    # 按波动率分位排序的总表
    print()
    print("=" * 80)
    print("全品种波动率强度排名（按分位数从低到高）")
    print("=" * 80)
    print(f"{'排名':<4} {'品种':<8} {'代码':<6} {'HV(年化)':<10} {'分位数':<8} {'波动率变化':<10} {'状态'}")
    print("-" * 80)
    
    sorted_results = sorted(results, key=lambda x: x["percentile"])
    for i, r in enumerate(sorted_results, 1):
        print(f"{i:<4} {r['name']:<8} {r['code']:<6} {r['current_hv']:>8.2f}% "
              f"{r['percentile']:>6.1f}% {r['vol_change_pct']:>+8.1f}% {r['convergence_zone']}")
    
    # 保存JSON结果
    output_path = "/Users/licanxing/.qclaw/workspace-futures-assistant/volatility_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "results": results,
            "zones": {k: [{"name": r["name"], "code": r["code"], "current_hv": r["current_hv"], 
                          "percentile": r["percentile"], "vol_change_pct": r["vol_change_pct"]} 
                         for r in v] for k, v in zones.items()}
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 结果已保存至: {output_path}")
    print(f"\n📊 分析品种数: {len(results)} | 收敛区品种数: {sum(len(v) for k,v in zones.items() if '收敛' in k)}")


if __name__ == "__main__":
    main()
