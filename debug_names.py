#!/usr/bin/env python3
"""调试各品种查询名称"""
import os, json, secrets, urllib.request

API_KEY = os.environ["IWENCAI_API_KEY"]
API_URL = "https://openapi.iwencai.com/v1/query2data"

def query(q):
    trace_id = secrets.token_hex(32)
    payload = {"query": q, "page": "1", "limit": "3", "is_cache": "1", "expand_index": "true"}
    headers = {
        "Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json",
        "X-Claw-Call-Type": "normal", "X-Claw-Skill-Id": "hithink-futures-query",
        "X-Claw-Skill-Version": "1.0.0", "X-Claw-Plugin-Id": "none",
        "X-Claw-Plugin-Version": "none", "X-Claw-Trace-Id": trace_id,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
    resp = urllib.request.urlopen(req, timeout=30)
    r = json.loads(resp.read().decode("utf-8"))
    datas = r.get("datas", [])
    if datas:
        name = datas[0].get("合约简称", datas[0].get("指数简称", "?"))
        code = datas[0].get("合约代码", datas[0].get("指数代码", "?"))
        return f"✅ {name} ({code}), count={r['code_count']}"
    return f"❌ 无数据"

# 测试各种命名
tests = [
    "螺纹钢指数", "沪铜指数", "沪铜加权", "CU指数", "铜指数",
    "铁矿石指数", "豆粕指数", "原油指数", "沪金指数",
    "PTA指数", "纯碱指数", "碳酸锂指数",
]
for t in tests:
    print(f"  {t:16s} → ", end="")
    try:
        print(query(f"{t} 近5日 收盘价"))
    except Exception as e:
        print(f"错误: {e}")
