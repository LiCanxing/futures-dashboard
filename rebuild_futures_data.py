#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重建期货看板数据文件
当 /tmp/futures_dashboard_data.json 和 /tmp/futures_classification_v3.json 丢失时运行
"""

import json, secrets, urllib.request, time, os, sys
from datetime import datetime

WORK      = os.path.expanduser('~/.qclaw/workspace-futures-assistant')
API_KEY   = os.environ.get('IWENCAI_API_KEY', '')
BASE_URL  = 'https://openapi.iwencai.com/v1/query2data'
DATA_DIR  = os.path.join(WORK, 'data')
DATA_FILE = os.path.join(DATA_DIR, 'dashboard_data.json')
CLASS_FILE = os.path.join(DATA_DIR, 'classification.json')

# 所有期货品种加权指数（排除广期所的 PS/SI/PD/PT/LC 和 EC/PG）
ALL_VARIETIES = [
    # 上期所
    ("CU8888.SHF", "沪铜"), ("AL8888.SHF", "沪铝"), ("ZN8888.SHF", "沪锌"),
    ("PB8888.SHF", "沪铅"), ("NI8888.SHF", "沪镍"), ("SN8888.SHF", "沪锡"),
    ("AU8888.SHF", "沪金"), ("AG8888.SHF", "沪银"), ("RB8888.SHF", "螺纹钢"),
    ("HC8888.SHF", "热卷"), ("SS8888.SHF", "不锈钢"), ("BU8888.SHF", "沥青"),
    ("RU8888.SHF", "橡胶"), ("SP8888.SHF", "纸浆"), ("FU8888.SHF", "燃料油"),
    ("BR8888.SHF", "丁二烯胶"), ("AO8888.SHF", "氧化铝"),
    # 大商所
    ("I8888.DCE", "铁矿石"), ("J8888.DCE", "焦炭"), ("JM8888.DCE", "焦煤"),
    ("M8888.DCE", "豆粕"), ("Y8888.DCE", "豆油"), ("A8888.DCE", "豆一"),
    ("P8888.DCE", "棕榈油"), ("B8888.DCE", "豆二"), ("C8888.DCE", "玉米"),
    ("CS8888.DCE", "淀粉"), ("JD8888.DCE", "鸡蛋"), ("L8888.DCE", "塑料"),
    ("PP8888.DCE", "聚丙烯"), ("V8888.DCE", "PVC"), ("EG8888.DCE", "乙二醇"),
    ("EB8888.DCE", "苯乙烯"), ("LH8888.DCE", "生猪"), ("RR8888.DCE", "粳米"),
    ("FB8888.DCE", "纤维板"), ("BB8888.DCE", "胶合板"),
    # 郑商所
    ("TA8888.ZCE", "PTA"), ("MA8888.ZCE", "甲醇"), ("FG8888.ZCE", "玻璃"),
    ("SA8888.ZCE", "纯碱"), ("UR8888.ZCE", "尿素"), ("SR8888.ZCE", "白糖"),
    ("CF8888.ZCE", "棉花"), ("CY8888.ZCE", "棉纱"), ("OI8888.ZCE", "菜油"),
    ("RM8888.ZCE", "菜粕"), ("PK8888.ZCE", "花生"), ("AP8888.ZCE", "苹果"),
    ("CJ8888.ZCE", "红枣"), ("PF8888.ZCE", "短纤"), ("SM8888.ZCE", "锰硅"),
    ("SF8888.ZCE", "硅铁"), ("SH8888.ZCE", "烧碱"), ("PX8888.ZCE", "对二甲苯"),
    # 中金所金融期货已排除（商品期货看板不需要）
]

BATCH_SIZE = 1  # 每次查询1个品种（批量不work，需要逐个）

def hithink_query(q):
    trace_id = secrets.token_hex(32)
    payload = {'query': q, 'page': '1', 'limit': '5', 'is_cache': '0', 'expand_index': 'true'}
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
        'X-Claw-Call-Type': 'normal',
        'X-Claw-Skill-Id': 'hithink-futures-query',
        'X-Claw-Skill-Version': '1.0.0',
        'X-Claw-Plugin-Id': 'none',
        'X-Claw-Plugin-Version': 'none',
        'X-Claw-Trace-Id': trace_id,
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(BASE_URL, data=data, headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))

def pull_all():
    varieties = []
    historical = {}
    pulled = 0
    failed = 0
    
    print(f'共 {len(ALL_VARIETIES)} 个品种待拉取')
    
    for code, name in ALL_VARIETIES:
        try:
            r = hithink_query(f'{name}加权指数 历史每日收盘价 持仓量')
            hdata = r.get('datas', [])
            if not hdata:
                failed += 1
                print(f'  {name}: 无数据 (跳过)')
                continue
            
            item = hdata[0]
            price_pts, oi_pts = [], []
            for k, val in item.items():
                if val is None: continue
                try: fval = float(val)
                except: continue
                if '收盘价[' in k:
                    date_str = k.split('[')[1].split(']')[0]
                    price_pts.append((date_str, fval))
                elif '持仓量[' in k:
                    date_str = k.split('[')[1].split(']')[0]
                    oi_pts.append((date_str, fval))
            
            price_pts.sort(); oi_pts.sort()
            
            if not price_pts:
                failed += 1
                print(f'  {name}: 解析失败 (跳过)')
                continue
            
            # 品种基础数据
            v = {
                'code': code, 'name': name,
                'cur_price': price_pts[-1][1],
                'price_min': min(x[1] for x in price_pts),
                'price_max': max(x[1] for x in price_pts),
                'price_pct': round((price_pts[-1][1] - min(x[1] for x in price_pts)) / max(max(x[1] for x in price_pts) - min(x[1] for x in price_pts), 1) * 100, 1),
            }
            v['price_level'] = '高' if v['price_pct'] >= 67 else ('低' if v['price_pct'] <= 33 else '中')
            
            if oi_pts:
                v['cur_oi'] = oi_pts[-1][1]
                v['oi_min'] = min(x[1] for x in oi_pts)
                v['oi_max'] = max(x[1] for x in oi_pts)
                v['oi_pct'] = round((oi_pts[-1][1] - v['oi_min']) / max(v['oi_max'] - v['oi_min'], 1) * 100, 1)
                v['oi_level'] = '高' if v['oi_pct'] >= 67 else ('低' if v['oi_pct'] <= 33 else '中')
                if oi_pts[-1][1] < 1000 and v['oi_max'] > 10000:
                    v['oi_level'] = '数据存疑'
                    v['oi_note'] = f'⚠️ API数据存疑（OI仅{oi_pts[-1][1]:.0f}手，可能为单合约而非加权指数）'
            else:
                v['oi_level'] = 'N/A'
                v['oi_pct'] = 0
            
            varieties.append(v)
            historical[code] = {
                'price_dates': [x[0] for x in price_pts],
                'price_values': [x[1] for x in price_pts],
                'oi_dates': [x[0] for x in oi_pts] if oi_pts else [],
                'oi_values': [x[1] for x in oi_pts] if oi_pts else [],
            }
            
            pulled += 1
            print(f'  {name} ({code}): {len(price_pts)}价/{len(oi_pts)}仓 ✓ [价格{v["price_level"]}位 {v["price_pct"]}%]')
            time.sleep(0.4)
            
        except Exception as e:
            err = str(e)
            if '401' in err or '403' in err:
                print(f'  ⛔ 配额耗尽！已拉取 {pulled} 个，剩余 {len(ALL_VARIETIES) - pulled - failed} 个待补')
                break
            failed += 1
            print(f'  {name}: ERROR - {err[:80]}')
            time.sleep(0.5)
    
    return varieties, historical, pulled, failed

def main():
    print(f'🔨 期货数据重建 — {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    
    if not API_KEY:
        print('❌ IWENCAI_API_KEY 未设置')
        sys.exit(1)
    
    varieties, historical, pulled, failed = pull_all()
    
    # 构建分类文件
    classification = []
    for v in varieties:
        c = {'code': v['code'], 'name': v['name']}
        for k in ['cur_price','price_min','price_max','price_pct','price_level',
                   'cur_oi','oi_min','oi_max','oi_pct','oi_level','oi_note']:
            if k in v: c[k] = v[k]
        classification.append(c)
    
    # 保存数据文件
    os.makedirs(DATA_DIR, exist_ok=True)
    dd = {'varieties': varieties, 'historical': historical}
    with open(DATA_FILE, 'w') as f:
        json.dump(dd, f, ensure_ascii=False)
    with open(CLASS_FILE, 'w') as f:
        json.dump(classification, f, ensure_ascii=False)
    
    print(f'\n✅ 保存完成: {DATA_FILE} ({len(varieties)} 品种)')
    print(f'✅ 保存完成: {CLASS_FILE} ({len(classification)} 品种)')
    print(f'拉取成功: {pulled} | 失败: {failed} | 总计: {len(ALL_VARIETIES)}')

if __name__ == '__main__':
    main()
