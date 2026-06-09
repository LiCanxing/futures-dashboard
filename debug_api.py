#!/usr/bin/env python3
"""调试：查看问财API返回的原始数据格式"""
import os, json, secrets, urllib.request

API_KEY = os.environ["IWENCAI_API_KEY"]
API_URL = "https://openapi.iwencai.com/v1/query2data"

def query(query_text):
    trace_id = secrets.token_hex(32)
    payload = {"query": query_text, "page": "1", "limit": "5", "is_cache": "1", "expand_index": "true"}
    headers = {
        "Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json",
        "X-Claw-Call-Type": "normal", "X-Claw-Skill-Id": "hithink-futures-query",
        "X-Claw-Skill-Version": "1.0.0", "X-Claw-Plugin-Id": "none",
        "X-Claw-Plugin-Version": "none", "X-Claw-Trace-Id": trace_id,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
    resp = urllib.request.urlopen(req, timeout=30)
    return json.loads(resp.read().decode("utf-8"))

# 测试几个查询
for q in ["螺纹钢指数 近20个交易日 收盘价", "沪铜指数 收盘价 近20日", "螺纹钢指数 波动率"]:
    print(f"\n{'='*60}")
    print(f"查询: {q}")
    try:
        r = query(q)
        datas = r.get("datas", [])
        print(f"code_count: {r.get('code_count')}")
        print(f"datas count: {len(datas)}")
        if datas:
            print(f"第一条所有key: {list(datas[0].keys())}")
            print(f"第一条内容: {json.dumps(datas[0], ensure_ascii=False, indent=2)[:500]}")
        else:
            print("无数据返回")
    except Exception as e:
        print(f"错误: {e}")
