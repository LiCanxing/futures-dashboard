#!/usr/bin/env python3
"""测试批量查询：一次查询多个品种"""
import os, json, secrets, urllib.request, time

API_KEY = os.environ["IWENCAI_API_KEY"]
API_URL = "https://openapi.iwencai.com/v1/query2data"

def query(q, call_type="normal"):
    trace_id = secrets.token_hex(32)
    payload = {"query": q, "page": "1", "limit": "50", "is_cache": "1", "expand_index": "true"}
    headers = {
        "Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json",
        "X-Claw-Call-Type": call_type, "X-Claw-Skill-Id": "hithink-futures-query",
        "X-Claw-Skill-Version": "1.0.0", "X-Claw-Plugin-Id": "none",
        "X-Claw-Plugin-Version": "none", "X-Claw-Trace-Id": trace_id,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
    resp = urllib.request.urlopen(req, timeout=30)
    r = json.loads(resp.read().decode("utf-8"))
    return r

# 测试批量查询 - 逗号分隔多个品种
batch_queries = [
    "螺纹钢指数,沪铜加权,铁矿石加权 近250个交易日 收盘价",
    "螺纹钢加权,沪铜加权,铁矿石加权,豆粕加权 近250个交易日 收盘价",
]

for q in batch_queries:
    print(f"\n查询: {q[:60]}...")
    try:
        r = query(q)
        datas = r.get("datas", [])
        print(f"  返回: {len(datas)} 条, code_count={r.get('code_count')}")
        for d in datas[:3]:
            name = d.get("合约简称", "?")
            code = d.get("合约代码", "?")
            price_keys = [k for k in d if "收盘" in k]
            print(f"  {name} ({code}): {len(price_keys)} 个价格点")
            if price_keys:
                print(f"    最新: {price_keys[0]} = {d[price_keys[0]]}")
                print(f"    最早: {price_keys[-1]} = {d[price_keys[-1]]}")
    except Exception as e:
        print(f"  错误: {e}")
    time.sleep(0.3)
