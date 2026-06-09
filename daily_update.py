#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货看板每日更新流水线
每天拉取全部商品期货加权指数的上市以来全量历史数据，生成看板并推送。

流程：
  1. 检测数据文件 → 缺失时自动全量重建
  2. 逐个拉取所有品种全量历史数据（配额耗尽自动停）
  3. 更新价格/持仓分位
  4. 运行 gen_final.py 生成看板
  5. git commit + push
"""

import json, secrets, urllib.request, time, os, sys, subprocess
from datetime import datetime

# ─── 配置 ─────────────────────────────────────────────────
WORK      = os.path.expanduser('~/.qclaw/workspace-futures-assistant')
DATA_DIR  = os.path.join(WORK, 'data')
API_KEY   = os.environ.get('IWENCAI_API_KEY', '')
BASE_URL  = 'https://openapi.iwencai.com/v1/query2data'
DATA_FILE = os.path.join(DATA_DIR, 'dashboard_data.json')
CLASS_FILE = os.path.join(DATA_DIR, 'classification.json')

EXCLUDED = {
    'PS8888.GFE','SI8888.GFE','PD8888.GFE','PT8888.GFE',  # 广期所新品种
    'LC8888.GFE','EC8888.INE','PG8888.DCE',                # 数据缺失
}

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

# ─── 数据加载/保存 ────────────────────────────────────────
def load_data():
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE) as f: dd = json.load(f)
    with open(CLASS_FILE) as f: clf = json.load(f)
    return dd, clf

def save_data(dd):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(dd, f, ensure_ascii=False)
    with open(CLASS_FILE, 'w') as f:
        json.dump(clf_dict, f, ensure_ascii=False)

# ─── Phase 1: 拉取全量历史 K 线 ────────────────────────────
def pull_all_klines(dd, varieties):
    """逐个拉取所有品种上市以来全量历史数据，配额耗尽自动停止"""
    hist = dd.get('historical', {})
    pulled, skipped, errors = 0, 0, 0
    
    for v in varieties:
        code = v['code']
        name = v['name']
        
        if code in EXCLUDED or code.endswith('.CFE'):
            skipped += 1
            continue
        
        try:
            r = hithink_query(f'{name} 历史每日收盘价 持仓量')
            hdata = r.get('datas', [])
            if not hdata:
                print(f'  {name}: 无数据 (跳过)')
                skipped += 1
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
            
            if not price_pts and not oi_pts:
                print(f'  {name}: 解析失败 (跳过)')
                skipped += 1
                continue
            
            if price_pts:
                hist.setdefault(code, {})
                hist[code]['price_dates'] = [x[0] for x in price_pts]
                hist[code]['price_values'] = [x[1] for x in price_pts]
            
            # OI 数据质量检查：新 OI 峰值远低于现有数据 → 可能是单合约而非加权指数
            oi_ok = True
            if oi_pts:
                new_oi_max = max(x[1] for x in oi_pts)
                old_oi = hist.get(code, {}).get('oi_values', [])
                old_oi_max = max(old_oi) if old_oi else 0
                if old_oi_max > 0 and new_oi_max < old_oi_max * 0.25:
                    oi_ok = False
                    print(f'  {name}: {len(price_pts)}价/{len(oi_pts)}仓 ⚠️ OI存疑(新{new_oi_max:.0f} vs 旧{old_oi_max:.0f}) 保留旧OI')
                else:
                    hist.setdefault(code, {})
                    hist[code]['oi_dates'] = [x[0] for x in oi_pts]
                    hist[code]['oi_values'] = [x[1] for x in oi_pts]
            
            pulled += 1
            if oi_ok:
                print(f'  {name}: {len(price_pts)}价/{len(oi_pts)}仓 ✓')
            time.sleep(0.35)
            
        except Exception as e:
            err = str(e)
            if '401' in err or '403' in err:
                print(f'  ⛔ 配额耗尽，已拉取 {pulled} 个品种')
                break
            print(f'  {name}: ERROR - {err[:60]}')
            errors += 1
            time.sleep(0.5)
    
    dd['historical'] = hist
    return pulled, skipped, errors

# ─── Phase 2: 更新分位数据 ────────────────────────────────
def update_classification(dd, clf, varieties):
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
            if ov[-1] < 1000 and v['oi_max'] > 10000:
                v['oi_level'] = '数据存疑'
                v['oi_note'] = f'⚠️ API数据存疑（OI仅{ov[-1]:.0f}手，可能为单合约而非加权指数）'
        
        updated += 1
    
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
    gen_path = os.path.join(WORK, 'gen_final.py')
    if not os.path.exists(gen_path):
        print(f'❌ gen_final.py not found at {gen_path}')
        return False
    
    result = subprocess.run(['python3', gen_path], capture_output=True, text=True, cwd=WORK)
    print(result.stdout.strip())
    if result.returncode != 0:
        print(f'❌ gen_final.py failed:\n{result.stderr}')
        return False
    
    # 注入基本面跟踪 Tab
    inj_path = os.path.join(WORK, 'inject_fundamentals.py')
    if os.path.exists(inj_path):
        result = subprocess.run(['python3', inj_path], capture_output=True, text=True, cwd=WORK)
        print(result.stdout.strip())
        if result.returncode != 0:
            print(f'⚠️ inject_fundamentals.py failed:\n{result.stderr}')
    
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
    
    if not API_KEY:
        print('❌ IWENCAI_API_KEY 未设置，用现有数据重建看板...')
        rebuild_and_push()
        return
    
    # 数据文件缺失 → 全量重建
    if not os.path.exists(DATA_FILE):
        print('⚠️ 数据文件缺失，触发全量重建...')
        rebuild_script = os.path.join(WORK, 'rebuild_futures_data.py')
        if os.path.exists(rebuild_script):
            r = subprocess.run(['python3', rebuild_script], capture_output=True, text=True, cwd=WORK)
            print(r.stdout.strip())
            if r.returncode != 0:
                print(f'❌ 重建失败:\n{r.stderr}')
                return
        else:
            print(f'❌ 重建脚本不存在: {rebuild_script}')
            return
    
    dd, clf_dict = load_data()
    varieties = dd['varieties']
    active = [v for v in varieties if v['code'] not in EXCLUDED and not v['code'].endswith('.CFE')]
    print(f'品种: {len(active)} 个 | 有K线: {len(dd.get("historical", {}))} 个')
    
    # Phase 1+2: 拉取全量数据 + 更新分位
    print(f'\n📥 拉取全量历史数据（上市以来）...')
    pulled, skipped, errors = pull_all_klines(dd, active)
    print(f'拉取: {pulled} | 跳过: {skipped} | 错误: {errors}')
    
    print(f'\n📊 更新分位数据...')
    updated = update_classification(dd, clf_dict, active)
    print(f'更新: {updated} 个品种')
    
    save_data(dd)
    print('数据已保存')
    
    # Phase 3+4: 看板 + 推送
    print(f'\n🔨 生成看板 + 推送...')
    success = rebuild_and_push()
    
    print(f'\n{"✅ 完成" if success else "⚠️ 部分完成"}（拉取 {pulled}/{len(active)} 个）')

if __name__ == '__main__':
    main()
