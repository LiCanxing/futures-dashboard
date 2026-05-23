#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货看板每日更新流水线
基于 API 配额限制（≈50-60次/天），优先更新高持仓活跃品种

流程：
  Phase 1: 拉取 Top-N 品种最新K线（优先高持仓）
  Phase 2: 更新分类数据（最新价/持仓/分位）
  Phase 3: 运行 gen_final.py 重新生成看板
  Phase 4: git commit + push
"""

import json, secrets, urllib.request, time, os, sys, subprocess
from datetime import datetime

# ─── 配置 ─────────────────────────────────────────────────
WORK = os.path.expanduser('~/.qclaw/workspace-futures-assistant')
API_KEY = os.environ.get('IWENCAI_API_KEY', '')
BASE_URL = 'https://openapi.iwencai.com/v1/query2data'
DATA_FILE = '/tmp/futures_dashboard_data.json'
CLASS_FILE = '/tmp/futures_classification_v3.json'

# 配额限制：每天更新品种数
DAILY_QUOTA = 50  # 每天最多调用次数（配额用尽自动停）

# ─── API ──────────────────────────────────────────────────
def hithink_query(q, skill='hithink-futures-query'):
    trace_id = secrets.token_hex(32)
    payload = {'query': q, 'page': '1', 'limit': '5', 'is_cache': '0', 'expand_index': 'true'}
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
        'X-Claw-Call-Type': 'normal',
        'X-Claw-Skill-Id': skill,
        'X-Claw-Skill-Version': '1.0.0',
        'X-Claw-Plugin-Id': 'none',
        'X-Claw-Plugin-Version': 'none',
        'X-Claw-Trace-Id': trace_id,
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(BASE_URL, data=data, headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))

# ─── 数据加载 ─────────────────────────────────────────────
def load_data():
    with open(DATA_FILE) as f: dd = json.load(f)
    with open(CLASS_FILE) as f: clf = json.load(f)
    return dd, clf

def save_data(dd):
    with open(DATA_FILE, 'w') as f:
        json.dump(dd, f, ensure_ascii=False)
    with open(CLASS_FILE, 'w') as f:
        json.dump(clf_dict, f, ensure_ascii=False)

# ─── Phase 1: 拉取 K 线 ──────────────────────────────────
def pull_klines(dd, varieties):
    """按持仓量排序，优先拉取高持仓品种的最近数据"""
    hist = dd.get('historical', {})
    
    # 按 OI 分位排序（高→中→低），OI 数据缺失的排最后
    level_order = {'高': 0, '中': 1, '低': 2}
    sorted_v = sorted(varieties, 
                      key=lambda v: (level_order.get(v.get('oi_level', '低'), 9), 
                                    -(v.get('oi_pct', 0))))
    
    pulled = 0
    for v in sorted_v[:DAILY_QUOTA]:
        code = v['code']
        name = v['name']
        
        # 跳过已排除品种
        EXCLUDED = {'PS8888.GFE','SI8888.GFE','PD8888.GFE','PT8888.GFE',
                    'LC8888.GFE','EC8888.INE','PG8888.DCE'}
        if code in EXCLUDED: continue
        
        try:
            r = hithink_query(f'{name} 历史每日收盘价 持仓量 近90日')
            hdata = r.get('datas', [])
            if not hdata:
                print(f'  {name}: 无数据')
                continue
            
            item = hdata[0]
            price_pts, oi_pts = [], []
            for k, val in item.items():
                if val is None: continue
                try: fval = float(val)
                except: continue
                if '收盘价[' in k:
                    price_pts.append((k.split('[')[1].split(']')[0], fval))
                elif '持仓量[' in k:
                    oi_pts.append((k.split('[')[1].split(']')[0], fval))
            
            price_pts.sort(); oi_pts.sort()
            
            # 合并到历史数据（新数据覆盖旧的）
            if not price_pts and not oi_pts:
                print(f'  {name}: 解析失败')
                continue
            
            if price_pts:
                hist[code] = hist.get(code, {})
                hist[code]['price_dates'] = [x[0] for x in price_pts]
                hist[code]['price_values'] = [x[1] for x in price_pts]
            if oi_pts:
                hist[code] = hist.get(code, {})
                hist[code]['oi_dates'] = [x[0] for x in oi_pts]
                hist[code]['oi_values'] = [x[1] for x in oi_pts]
            
            pulled += 1
            print(f'  {name}: {len(price_pts)}价/{len(oi_pts)}仓 ✓')
            time.sleep(0.35)  # 避免触发限流
            
        except Exception as e:
            err = str(e)
            if '401' in err or '403' in err:
                print(f'  ⛔ 配额耗尽，已拉取 {pulled} 个品种')
                break
            print(f'  {name}: ERROR - {err[:60]}')
            time.sleep(0.5)
    
    dd['historical'] = hist
    return pulled

# ─── Phase 2: 更新分类数据 ────────────────────────────────
def update_classification(dd, clf, varieties):
    """用最新K线数据更新价格/持仓分位"""
    hist = dd.get('historical', {})
    updated = 0
    
    for v in varieties:
        code = v['code']
        h = hist.get(code, {})
        pv = h.get('price_values', [])
        ov = h.get('oi_values', [])
        
        if pv:
            v['cur_price'] = pv[-1]
            v['price_min'] = min(pv)
            v['price_max'] = max(pv)
            v['price_pct'] = round((pv[-1] - v['price_min']) / max(v['price_max'] - v['price_min'], 1) * 100, 1)
            v['price_level'] = '高' if v['price_pct'] >= 67 else ('低' if v['price_pct'] <= 33 else '中')
        
        if ov:
            v['cur_oi'] = ov[-1]
            v['oi_min'] = min(ov)
            v['oi_max'] = max(ov)
            v['oi_pct'] = round((ov[-1] - v['oi_min']) / max(v['oi_max'] - v['oi_min'], 1) * 100, 1)
            v['oi_level'] = '高' if v['oi_pct'] >= 67 else ('低' if v['oi_pct'] <= 33 else '中')
            # 绝对持仓量过滤：OI < 1000 且历史有过高OI → API可能返回了单合约数据
            if ov[-1] < 1000 and v['oi_max'] > 10000:
                v['oi_level'] = '数据存疑'
                v['oi_note'] = f'⚠️ API数据存疑（OI仅{ov[-1]:.0f}手，可能为单合约而非加权指数）'
        
        updated += 1
    
    # 同步到分类文件
    for cv in clf:
        code = cv['code']
        vv = {v['code']: v for v in varieties}.get(code)
        if vv:
            for k in ['cur_price','price_min','price_max','price_pct','price_level',
                      'cur_oi','oi_min','oi_max','oi_pct','oi_level','oi_note']:
                if k in vv: cv[k] = vv[k]
    
    dd['varieties'] = varieties
    return updated

# ─── Phase 3+4: 生成看板 + 推送 ──────────────────────────
def rebuild_and_push():
    """运行 gen_final.py 然后 git push"""
    gen_path = os.path.join(WORK, 'gen_final.py')
    if not os.path.exists(gen_path):
        print(f'❌ gen_final.py not found at {gen_path}')
        return False
    
    result = subprocess.run(['python3', gen_path], capture_output=True, text=True, cwd=WORK)
    print(result.stdout.strip())
    if result.returncode != 0:
        print(f'❌ gen_final.py failed:\n{result.stderr}')
        return False
    
    # Git push
    dt_str = datetime.now().strftime("%m-%d %H:%M")
    cmds = [
        f'cd {WORK} && cp futures_dashboard.html index.html',
        f'cd {WORK} && git add index.html',
        f'cd {WORK} && git commit -m "每日数据刷新 {dt_str}"',
        f'cd {WORK} && git push',
    ]
    for cmd in cmds:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=WORK)
        if r.returncode != 0 and 'nothing to commit' not in r.stdout + r.stderr:
            print(f'⚠️ {cmd[:60]}: {r.stderr[:80]}')
    
    return True

# ─── Main ─────────────────────────────────────────────────
def main():
    global clf_dict
    print(f'📊 期货看板每日更新 — {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print(f'配额: 每天最多 {DAILY_QUOTA} 次API调用')
    
    if not API_KEY:
        print('❌ IWENCAI_API_KEY 未设置')
        # 仍然尝试重建（用现有数据）
        print('用现有数据重建看板...')
        rebuild_and_push()
        return
    
    dd, clf_dict = load_data()
    varieties = dd['varieties']
    
    # 排除新品种
    EXCLUDED = {'PS8888.GFE','SI8888.GFE','PD8888.GFE','PT8888.GFE',
                'LC8888.GFE','EC8888.INE','PG8888.DCE'}
    active = [v for v in varieties if v['code'] not in EXCLUDED]
    
    hist_count = len(dd.get('historical', {}))
    print(f'活跃品种: {len(active)} | 有K线: {hist_count}')
    
    # Phase 1: 拉K线
    print(f'\n📥 Phase 1: 按持仓优先级拉取K线（最多{DAILY_QUOTA}次API调用）...')
    pulled = pull_klines(dd, active)
    print(f'成功拉取: {pulled} 个品种')
    
    # Phase 2: 更新分类
    print(f'\n📊 Phase 2: 更新分位数据...')
    updated = update_classification(dd, clf_dict, active)
    print(f'更新: {updated} 个品种')
    
    # 保存
    save_data(dd)
    print('数据已保存')
    
    # Phase 3+4: 重建 + 推送
    print(f'\n🔨 Phase 3+4: 重建看板 + 推送...')
    success = rebuild_and_push()
    
    print(f'\n{"✅ 完成" if success else "⚠️ 部分完成"}'  )

if __name__ == '__main__':
    main()
