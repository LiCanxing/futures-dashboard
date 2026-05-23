#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""期货双维分类看板 — 重写版 v6"""

import json, os, sys
from datetime import datetime

# ─── 配置 ─────────────────────────────────────────────────
CLASS_FILE = '/tmp/futures_classification_v3.json'
DATA_FILE  = '/tmp/futures_dashboard_data.json'
OUTPUT     = os.path.expanduser('~/.qclaw/workspace-futures-assistant/futures_dashboard.html')

PRICE_TREND_THRESH = 2.0   # 价格趋势阈值 (%)
OI_TREND_THRESH    = 5.0   # 持仓趋势阈值 (%)
TREND_DAYS         = 15    # 趋势观察窗口

# ─── 数据加载 ─────────────────────────────────────────────
def load_data():
    with open(CLASS_FILE) as f: clf = json.load(f)
    with open(DATA_FILE) as f:   d = json.load(f)
    V = d['varieties']
    H = d['historical']
    cmap = {v['code']: v for v in clf}
    EXCLUDED = {'PS8888.GFE','SI8888.GFE','PD8888.GFE','PT8888.GFE','LC8888.GFE','EC8888.INE','PG8888.DCE'}
    V = [v for v in V if v['code'] not in EXCLUDED]
    for v in V:
        v['name'] = v.get('name','').replace('加权','')
        c = cmap.get(v['code'], {})
        for k in ['price_level','price_pct','oi_level','oi_pct','oi_min','oi_max']:
            if k not in v: v[k] = c.get(k, 0)
    # 计算最新数据日期
    latest_date = ''
    for h in H.values():
        pd = h.get('price_dates', [])
        if pd and pd[-1][:10] > latest_date:
            latest_date = pd[-1][:10]
    return V, H, latest_date

# ─── 趋势计算 ─────────────────────────────────────────────
def calc_trend(v, H):
    code = v['code']
    h = H.get(code, {})
    pv = h.get('price_values', [])
    ov = h.get('oi_values', [])
    if len(pv) < TREND_DAYS + 1 or not ov or len(ov) < TREND_DAYS + 1:
        return None
    p_chg = (pv[-1] - pv[-TREND_DAYS-1]) / pv[-TREND_DAYS-1] * 100 if pv[-TREND_DAYS-1] > 0 else 0
    o_chg = (ov[-1] - ov[-TREND_DAYS-1]) / ov[-TREND_DAYS-1] * 100 if ov[-TREND_DAYS-1] > 0 else 0
    p_dir = '↑' if p_chg > PRICE_TREND_THRESH else ('↓' if p_chg < -PRICE_TREND_THRESH else '—')
    o_dir = '↑' if o_chg > OI_TREND_THRESH else ('↓' if o_chg < -OI_TREND_THRESH else '—')
    return {'p_chg': round(p_chg,1), 'o_chg': round(o_chg,1), 'p_dir': p_dir, 'o_dir': o_dir}

# ─── CSS ──────────────────────────────────────────────────
CSS = r'''*{margin:0;padding:0;box-sizing:border-box}
:root{color-scheme:light dark;--bg:#0b0f19;--bg2:#111827;--bg3:#0f172a;--border:#1e293b;--text:#e2e8f0;--text2:#cbd5e1;--text3:#94a3b8;--text4:#64748b;--text5:#475569;--tag-bg:#1e293b;--tag-border:#334155;--tag-text:#cbd5e1;--tag-hover-bg:#2563eb;--tag-hover-border:#3b82f6;--ins-border:#1e293b;--table-shadow:0 4px 30px rgba(0,0,0,.4),0 0 0 1px #1e293b;--modal-bg:rgba(0,0,0,.75);--md-bg:#0f172a;--fn-bg:#0f172a;--th-text:#cbd5e1;--th-border:#1e293b;--td-empty-bg:#0b0f19;--td-empty-color:#34455;--badge-bg4:rgba(148,163,184,.08);--wl-empty:#334155;--no-chart-bg:#111827;--no-chart-color:#475569}
@media(prefers-color-scheme:light){:root{--bg:#f1f5f9;--bg2:#ffffff;--bg3:#f8fafc;--border:#e2e8f0;--text:#0f172a;--text2:#334155;--text3:#475569;--text4:#64748b;--text5:#94a3b8;--tag-bg:#f1f5f9;--tag-border:#cbd5e1;--tag-text:#334155;--ins-border:#e2e8f0;--table-shadow:0 4px 24px rgba(0,0,0,.06),0 0 0 1px #e2e8f0;--modal-bg:rgba(0,0,0,.4);--md-bg:#ffffff;--fn-bg:#f8fafc;--th-text:#0f172a;--th-border:#cbd5e1;--td-empty-bg:#f1f5f9;--td-empty-color:#94a3b8;--badge-bg4:rgba(148,163,184,.15);--wl-empty:#94a3b8;--no-chart-bg:#f8fafc;--no-chart-color:#94a3b8}}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);padding:28px 32px;min-height:100vh}
.wrap{max-width:1620px;margin:0 auto}
h1{font-size:24px;font-weight:700;margin-bottom:6px;letter-spacing:-.5px}
h1 span{background:linear-gradient(135deg,#60a5fa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sub{font-size:12px;color:var(--text4);margin-bottom:18px}
.badges{display:flex;gap:8px;margin-bottom:22px;flex-wrap:wrap}
.badge{display:inline-block;padding:4px 12px;border-radius:14px;font-size:11px;font-weight:600;border:1px solid}
.bg1{background:rgba(34,197,94,.1);color:#86efac;border-color:rgba(34,197,94,.2)}
.bg2{background:rgba(245,158,11,.1);color:#fcd34d;border-color:rgba(245,158,11,.2)}
.bg3{background:rgba(59,130,246,.1);color:#93c5fd;border-color:rgba(59,130,246,.2)}
.bg4{background:var(--badge-bg4);color:var(--text3);border-color:rgba(148,163,184,.2)}
/* 主题切换 */
.theme-switch{cursor:pointer;display:flex;align-items:center;gap:6px;background:var(--bg2);border:1px solid var(--border);border-radius:20px;padding:5px 14px;font-size:12px;color:var(--text3);transition:.15s;user-select:none;white-space:nowrap;flex-shrink:0;margin-top:2px}
.theme-switch:hover{background:var(--bg3);border-color:var(--text3)}
.ts-icon{font-size:16px}.ts-label{font-weight:500}
[data-theme="dark"]{--bg:#0b0f19!important;--bg2:#111827!important;--bg3:#0f172a!important;--border:#1e293b!important;--text:#e2e8f0!important;--text2:#cbd5e1!important;--text3:#94a3b8!important;--text4:#64748b!important;--text5:#475569!important;--tag-bg:#1e293b!important;--tag-border:#334155!important;--tag-text:#cbd5e1!important;--ins-border:#1e293b!important;--table-shadow:0 4px 30px rgba(0,0,0,.4),0 0 0 1px #1e293b!important;--modal-bg:rgba(0,0,0,.75)!important;--md-bg:#0f172a!important;--fn-bg:#0f172a!important;--th-text:#cbd5e1!important;--td-empty-bg:#0b0f19!important;--td-empty-color:#334155!important;--badge-bg4:rgba(148,163,184,.08)!important;--wl-empty:#334155!important;--no-chart-bg:#111827!important;--no-chart-color:#475569!important}
[data-theme="light"]{--bg:#f1f5f9!important;--bg2:#ffffff!important;--bg3:#f8fafc!important;--border:#e2e8f0!important;--text:#0f172a!important;--text2:#334155!important;--text3:#475569!important;--text4:#64748b!important;--text5:#94a3b8!important;--tag-bg:#f1f5f9!important;--tag-border:#cbd5e1!important;--tag-text:#334155!important;--ins-border:#e2e8f0!important;--table-shadow:0 4px 24px rgba(0,0,0,.06),0 0 0 1px #e2e8f0!important;--modal-bg:rgba(0,0,0,.4)!important;--md-bg:#ffffff!important;--fn-bg:#f8fafc!important;--th-text:#0f172a!important;--td-empty-bg:#f1f5f9!important;--td-empty-color:#94a3b8!important;--badge-bg4:rgba(148,163,184,.15)!important;--wl-empty:#94a3b8!important;--no-chart-bg:#f8fafc!important;--no-chart-color:#94a3b8!important}
/* 矩阵表格 */
table{width:100%;border-collapse:collapse;border-radius:14px;overflow:hidden;box-shadow:var(--table-shadow);margin-bottom:18px}
th{background:var(--bg3);color:var(--th-text);padding:16px 10px;font-size:12px;font-weight:600;text-align:center;border-bottom:2px solid var(--border)}
th .th-sub{font-size:10px;color:var(--text4);font-weight:400;display:block;margin-top:2px}
.th-corner{width:100px}.corner-top{font-size:11px;color:var(--text3)}.corner-bot{font-size:11px;color:var(--text3);margin-top:12px}
.corner-div{font-size:9px;color:var(--text5)}
td{border:1px solid var(--border)}
td.td-empty{background:var(--td-empty-bg);color:var(--td-empty-color);text-align:center;padding:24px;font-size:13px}
.td-cell{padding:8px 6px;vertical-align:top;background:var(--bg3);min-width:140px}
.td-label{text-align:center;font-size:13px;font-weight:700;border:1px solid var(--border)}
.td-sub{color:var(--text4);font-size:10px;font-weight:400;display:block}
.td-emoji{font-size:14px;display:block;margin-bottom:2px}
.th-emoji{font-size:14px;display:block;margin-bottom:2px}
/* 标签 */
.tag{display:inline-block;background:var(--tag-bg);border:1px solid var(--tag-border);border-radius:6px;padding:5px 10px;margin:2px;font-size:11px;cursor:pointer;transition:all .15s;white-space:nowrap;font-weight:500;color:var(--tag-text)}
.tag:hover{background:var(--tag-hover-bg);border-color:var(--tag-hover-border);color:#fff;transform:translateY(-1px);box-shadow:0 4px 12px rgba(59,130,246,.25)}
.tag.ch{border-color:#f59e0b}.tag.ch:hover{background:#d97706;border-color:#f59e0b}
/* 弹窗 */
.mo{display:none;position:fixed;inset:0;background:var(--modal-bg);backdrop-filter:blur(6px);z-index:1000;justify-content:center;align-items:center;padding:20px}
.mo.on{display:flex}
.md{background:var(--md-bg);border:1px solid var(--border);border-radius:16px;width:min(900px,95vw);max-height:90vh;overflow-y:auto}
.md-h{padding:18px 24px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;background:var(--md-bg);z-index:1}
.md-h h2{font-size:16px;color:var(--text)}
.md-x{background:none;border:none;font-size:22px;cursor:pointer;color:var(--text5);width:36px;height:36px;border-radius:8px;display:flex;align-items:center;justify-content:center;transition:.15s}
.md-x:hover{background:var(--border);color:var(--text)}
.md-b{padding:20px 24px 24px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px}
.sc{background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:16px}
.sc-l{font-size:10px;color:var(--text4);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.sc-v{font-size:24px;font-weight:700;color:var(--text)}
.sc-r{font-size:11px;color:var(--text4);margin-top:4px}
/* 分位条 */
.bar-w{margin-top:12px}.bar-l{display:flex;justify-content:space-between;font-size:10px;color:var(--text3);margin-bottom:4px}
.bar-b{height:6px;background:var(--border);border-radius:3px;overflow:hidden;position:relative}
.bar-f{height:100%;border-radius:3px;transition:width .3s}.bar-f.hi{background:#ef4444}.bar-f.mi{background:#f59e0b}.bar-f.lo{background:#22c55e}
.bar-p{position:absolute;top:-2px;width:3px;height:10px;background:var(--text);border-radius:2px}
/* 走势图 */
.charts{display:flex;flex-direction:column;gap:16px;margin-top:16px}
.cx{background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:18px}
.cx h4{font-size:13px;margin-bottom:10px;color:var(--text3);font-weight:500}
.cw{height:280px}
.no-chart{text-align:center;padding:36px;color:var(--no-chart-color);font-size:13px;background:var(--no-chart-bg);border:1px dashed var(--border);border-radius:12px}
/* 分位便签 */
.cb-hp{background:rgba(239,68,68,.12);color:#fca5a5;border:1px solid rgba(239,68,68,.25)}
.cb-mp{background:rgba(245,158,11,.12);color:#fcd34d;border:1px solid rgba(245,158,11,.25)}
.cb-lp{background:rgba(34,197,94,.12);color:#86efac;border:1px solid rgba(34,197,94,.25)}
.cb-ho{background:rgba(239,68,68,.12);color:#fca5a5;border:1px solid rgba(239,68,68,.25)}
.cb-mo{background:rgba(245,158,11,.12);color:#fcd34d;border:1px solid rgba(245,158,11,.25)}
.cb-lo{background:rgba(34,197,94,.12);color:#86efac;border:1px solid rgba(34,197,94,.25)}
/* AI观察 */
.ai-note{background:linear-gradient(135deg,rgba(59,130,246,.08),rgba(139,92,246,.06));border:1px solid rgba(59,130,246,.2);border-radius:10px;padding:14px 18px;margin-bottom:16px;font-size:13px;line-height:1.7;color:var(--text3)}
.ai-badge{display:inline-block;background:rgba(59,130,246,.15);color:#60a5fa;border-radius:5px;padding:2px 10px;font-size:11px;font-weight:600;margin-bottom:8px}
/* 洞察卡 */
.ins{display:grid;grid-template-columns:repeat(4,1fr);gap:0;margin-bottom:24px;border-radius:14px;overflow:hidden;border:1px solid var(--ins-border)}
.ins-card{background:var(--bg2);padding:18px 20px;border-right:1px solid var(--ins-border)}
.ins-card:last-child{border-right:none}.ins-card:hover{background:var(--bg3)}
.ins-head{font-size:14px;font-weight:600;margin-bottom:6px;color:var(--text)}
.ins-head span{font-size:11px;background:var(--tag-bg);padding:1px 8px;border-radius:10px;color:var(--text3);font-weight:400}
.ins-desc{font-size:11px;color:var(--text3);margin-bottom:4px}
.ins-names{font-size:10px;color:var(--text4);margin-top:4px}
/* 分布栏 */
.al-bar{display:flex;gap:12px;margin-bottom:22px}
.al{flex:1;background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:12px 16px;font-size:11px;color:var(--text3);line-height:1.6}
.al-dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px;vertical-align:middle}
/* Watchlist */
.wl-section{margin:28px 0 24px}
.wl-title{font-size:18px;font-weight:600;color:var(--text);margin-bottom:14px}
.wl-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
.wl-card{background:var(--bg2);border:1px solid var(--border);border-radius:14px;padding:18px 20px;display:flex;flex-direction:column;transition:border-color .2s}
.wl-card:hover{border-color:var(--text3)}
.wl-card-h{font-size:14px;font-weight:600;margin-bottom:8px;color:var(--text)}
.wl-card-sub{font-size:11px;color:var(--text4);margin-bottom:14px}
.wl-card-list{display:flex;flex-wrap:wrap;gap:5px}
.wl-empty{color:var(--wl-empty);font-size:11px;padding:8px}
.wl-tag-btn{display:inline-block;background:var(--tag-bg);border:1px solid var(--tag-border);border-radius:5px;padding:4px 10px;font-size:11px;color:var(--tag-text);font-weight:500;cursor:pointer;transition:.12s;white-space:nowrap}
.wl-tag-btn:hover{background:var(--tag-hover-bg);border-color:var(--tag-hover-border);color:#fff}
.wl-alert-tag{border-color:#ef4444;color:#ef4444}
.wl-alert-tag:hover{background:#fee2e2;border-color:#ef4444;color:#dc2626}
.wl-long{border-top:3px solid #dc2626}
.wl-short{border-top:3px solid #f59e0b}
.wl-bottom{border-top:3px solid #2563eb}
.wl-alert{border-top:3px solid #dc2626}
/* 底部 */
.fn{margin-top:20px;padding:14px 18px;background:var(--fn-bg);border:1px solid var(--border);border-radius:10px;font-size:11px;color:var(--text5)}
@media(max-width:900px){.wl-grid{grid-template-columns:1fr}}
'''

# ─── JS ───────────────────────────────────────────────────
def build_js(vj, hj, notes_json):
    return f'''<script>
var V={vj},H={hj};
var _N={notes_json};
function cycleTheme(){{var t=document.documentElement,m=['auto','light','dark'],c=t.getAttribute('data-theme')||'auto',i=m.indexOf(c),n=m[(i+1)%3];t.setAttribute('data-theme',n);localStorage.setItem('theme',n);var ic={{'auto':'🌓','light':'☀️','dark':'🌙'}},lb={{'auto':'跟随系统','light':'日间','dark':'夜间'}};document.getElementById('tsi').textContent=ic[n];document.getElementById('tsl').textContent=lb[n];}}
(function(){{var s=localStorage.getItem('theme')||'auto';document.documentElement.setAttribute('data-theme',s);var ic={{'auto':'🌓','light':'☀️','dark':'🌙'}},lb={{'auto':'跟随系统','light':'日间','dark':'夜间'}};document.getElementById('tsi').textContent=ic[s];document.getElementById('tsl').textContent=lb[s];}})();
document.querySelectorAll('.tag').forEach(t=>t.addEventListener('click',()=>show(t.dataset.code)));
function show(c){{
var v=V[c];if(!v)return;
document.getElementById('mt').textContent=v.name;
var pl=v.price_level||'N/A',pc=pl==='高'?'#fca5a5':pl==='中'?'#fcd34d':pl==='低'?'#86efac':'#94a3b8',pcl=pl==='高'?'cb-hp':pl==='中'?'cb-mp':'cb-lp';
var pMin=v.price_min||0,pMax=v.price_max||1,pPct=Math.min(100,v.price_pct||0);
var ol=v.oi_level||'N/A',oc=ol==='高'?'#fca5a5':ol==='中'?'#fcd34d':ol==='低'?'#86efac':'#94a3b8',ocl=ol==='高'?'cb-ho':ol==='中'?'cb-mo':'cb-lo',om=!ol||ol==='N/A';
var oMin=v.oi_min||0,oMax=v.oi_max||1,oPct=Math.min(100,v.oi_pct||0);
var b='';
var ai=_N[c]||'';
if(ai){{b+='<div class="ai-note"><span class="ai-badge">🤖 AI近期观察</span>'+ai+'</div>';}}
b+='<div class="stats">';
b+='<div class="sc"><div class="sc-l">当前价格</div><div class="sc-v">'+Number(v.cur_price||0).toLocaleString()+'</div><div class="sc-r">历史: '+Number(pMin).toLocaleString()+' ~ '+Number(pMax).toLocaleString()+'</div>';
b+='<div class="bar-w"><div class="bar-l"><span>低点</span><span>'+pPct+'% · <b style="color:'+pc+'">'+pl+'位</b></span><span>高点</span></div><div class="bar-b"><div class="bar-f '+(pl==='高'?'hi':pl==='中'?'mi':'lo')+'" style="width:'+pPct+'%"></div><div class="bar-p" style="left:'+pPct+'%"></div></div></div></div>';
b+='<div class="sc"><div class="sc-l">当前持仓量</div><div class="sc-v">'+Number(v.cur_oi||0).toLocaleString()+' 手</div>';
if(om){{b+='<div class="sc-r" style="color:#f59e0b">历史持仓区间暂无</div>';}}
else{{b+='<div class="sc-r">历史: '+Number(oMin||0).toLocaleString()+' ~ '+Number(oMax||0).toLocaleString()+'</div>';
b+='<div class="bar-w"><div class="bar-l"><span>低点</span><span>'+oPct+'% · <b style="color:'+oc+'">'+ol+'位</b></span><span>高点</span></div><div class="bar-b"><div class="bar-f '+(ol==='高'?'hi':ol==='中'?'mi':'lo')+'" style="width:'+oPct+'%"></div><div class="bar-p" style="left:'+oPct+'%"></div></div></div>';}}
b+='</div><div class="sc"><div class="sc-l">定位</div><div class="sc-v" style="font-size:16px">价格<span class="'+pcl+'">'+pl+'位</span> · 持仓<span class="'+ocl+'">'+(om?'待补':ol+'位')+'</span></div><div class="sc-r">'+v.name+'</div></div></div>';
var h=H[c];
if(h&&h.price_dates&&h.price_dates.length>1){{
b+='<div class="charts"><div class="cx"><h4>近一年价格走势</h4><div class="cw"><canvas id="cp"></canvas></div></div>';
if(h.oi_dates&&h.oi_dates.length>1)b+='<div class="cx"><h4>近一年持仓量走势</h4><div class="cw oi"><canvas id="co"></canvas></div></div>';
b+='</div>';
window._d={{pd:h.price_dates,pv:h.price_values,pMin:Number(pMin),pMax:Number(pMax),od:h.oi_dates||[],ov:h.oi_values||[],oMin:Number(oMin),oMax:Number(oMax)}};
window._hc=true;
}}else{{b+='<div class="no-chart">走势图暂不可用<br><small>API配额用完，改天自动补拉</small></div>';window._hc=false;}}
document.getElementById('mb').innerHTML=b;
document.getElementById('mo').classList.add('on');
if(window._hc)setTimeout(render,150);
}}
Chart.defaults.color='#94a3b8';Chart.defaults.borderColor='#1e293b';
function render(){{
var d=window._d;
if(window._pc)window._pc.destroy();if(window._oc)window._oc.destroy();
var pc=document.getElementById('cp');
if(pc){{window._pc=new Chart(pc,{{type:'line',data:{{labels:d.pd,datasets:[{{label:'收盘价',data:d.pv,borderColor:'#60a5fa',backgroundColor:'rgba(59,130,246,.06)',fill:true,tension:.3,pointRadius:0,borderWidth:2}}]}},options:{{responsive:true,maintainAspectRatio:false,interaction:{{intersect:false,mode:'index'}},plugins:{{legend:{{position:'bottom',labels:{{boxWidth:12,font:{{size:10}},padding:14,usePointStyle:true}}}}}},scales:{{x:{{ticks:{{maxTicksLimit:8,font:{{size:9}}}},grid:{{color:'rgba(51,65,85,.3)'}}}},y:{{ticks:{{font:{{size:9}}}},grid:{{color:'rgba(51,65,85,.3)'}}}}}}}}}});}}
var oc=document.getElementById('co');
if(oc&&d.od.length>1){{window._oc=new Chart(oc,{{type:'line',data:{{labels:d.od,datasets:[{{label:'持仓量',data:d.ov,borderColor:'#a78bfa',backgroundColor:'rgba(139,92,246,.06)',fill:true,tension:.3,pointRadius:0,borderWidth:2}}]}},options:{{responsive:true,maintainAspectRatio:false,interaction:{{intersect:false,mode:'index'}},plugins:{{legend:{{position:'bottom',labels:{{boxWidth:12,font:{{size:10}},padding:14,usePointStyle:true}}}}}},scales:{{x:{{ticks:{{maxTicksLimit:8,font:{{size:9}}}},grid:{{color:'rgba(51,65,85,.3)'}}}},y:{{ticks:{{font:{{size:9}}}},grid:{{color:'rgba(51,65,85,.3)'}}}}}}}}}});}}
}}
function closeModal(){{document.getElementById('mo').classList.remove('on');if(window._pc){{window._pc.destroy();window._pc=null}}if(window._oc){{window._oc.destroy();window._oc=null}}}}
document.getElementById('mo').addEventListener('click',function(e){{if(e.target===this)closeModal()}});
document.addEventListener('keydown',function(e){{if(e.key==='Escape')closeModal()}});
</script>'''

# ─── AI 观察生成 ─────────────────────────────────────────
def gen_ai_note(v, H):
    code = v['code']
    h = H.get(code, {})
    pv = h.get('price_values', [])
    ov = h.get('oi_values', [])
    if len(pv) < 16:
        return ''
    pp = v.get('price_pct', 50)
    op = v.get('oi_pct', 50)
    
    p15 = (pv[-1] - pv[-16]) / pv[-16] * 100 if pv[-16] > 0 else 0
    o15 = (ov[-1] - ov[-16]) / ov[-16] * 100 if ov and len(ov) > 16 and ov[-16] > 0 else 0
    up, down = p15 > 2, p15 < -2
    oi_up, oi_down = o15 > 10, o15 < -10
    p30 = (pv[-1] - pv[-31]) / pv[-31] * 100 if len(pv) > 30 and pv[-31] > 0 else 0
    
    parts = []
    if up and oi_up:
        parts.append(f"近15日量价齐升（价+{p15:.1f}%，仓+{o15:.0f}%），资金持续流入推动上涨，多头趋势明确。")
    elif up and not oi_up:
        parts.append(f"近15日价格上涨+{p15:.1f}%但持仓增幅有限（+{o15:.0f}%），量能配合不足，需观察持续性。")
    elif down and oi_up:
        parts.append(f"近15日价跌仓增（价{p15:.1f}%，仓+{o15:.0f}%），资金在低位吸筹，属于下跌蓄势阶段，不宜追空。")
    elif down and oi_down:
        parts.append(f"近15日量价齐跌（价{p15:.1f}%，仓{o15:.0f}%），资金流出、趋势走弱，等待企稳信号。")
    elif oi_up:
        parts.append(f"近15日价格变化{p15:+.1f}%但持仓大增+{o15:.0f}%，资金大规模进场但价格尚未启动，属于蓄力阶段。")
    elif oi_down:
        parts.append(f"近15日价格变化{p15:+.1f}%，持仓减少{o15:.0f}%，资金在撤退，谨慎对待。")
    else:
        parts.append(f"近15日价格变化{p15:+.1f}%，持仓变化{o15:+.0f}%，处于震荡整理格局。")
    
    if pp >= 67:
        parts.append(f"当前价格处于历史{pp:.0f}%高位，注意追高风险。")
    elif pp <= 33:
        parts.append(f"当前价格处于历史{pp:.0f}%低位，具备均值回归空间。")
    else:
        parts.append(f"当前价格处于历史{pp:.0f}%中位。")
    
    if op >= 67:
        parts.append(f"持仓量处于历史{op:.0f}%高位，市场博弈激烈。")
    elif op <= 33:
        parts.append(f"持仓量处于历史{op:.0f}%低位，市场关注度不足。")
    
    if p30 > 5:
        parts.append(f"近30日累计上涨+{p30:.1f}%，中期多头趋势延续。")
    elif p30 < -5:
        parts.append(f"近30日累计下跌{p30:.1f}%，中期偏弱。")
    
    return ' '.join(parts)

# ─── HTML 生成 ────────────────────────────────────────────
def build_html(V, H, latest_date=''):
    notes = {}
    for v in V:
        note = gen_ai_note(v, H)
        if note: notes[v['code']] = note
    
    vj = json.dumps({v['code']: v for v in V}, ensure_ascii=False)
    hj = json.dumps(H, ensure_ascii=False)
    nj = json.dumps(notes, ensure_ascii=False)
    JS = build_js(vj, hj, nj)
    
    # 有效品种筛选
    valid = [v for v in V if v.get('price_pct', 0) > 0 or v.get('price_level')]
    n2 = sum(1 for v in valid if v.get('oi_level') and v.get('oi_level') != 'N/A')
    nwh = sum(1 for v in V if v['code'] in H and H[v['code']].get('price_dates'))
    
    # ── 历史分位矩阵 ──
    cells = {}
    for pl in ['高','中','低']:
        for ol in ['高','中','低']:
            cells[(pl, ol)] = []
    for v in valid:
        pl = v.get('price_level', '')
        ol = v.get('oi_level', '')
        if pl in ['高','中','低'] and ol in ['高','中','低']:
            cells[(pl, ol)].append(v)
    
    # ── 趋势矩阵 ──
    trend_cells = {}
    for pd in ['↑','—','↓']:
        for od in ['↑','—','↓']:
            trend_cells[(pd, od)] = []
    for v in V:
        t = calc_trend(v, H)
        if t:
            v['_trend'] = t
            trend_cells[(t['p_dir'], t['o_dir'])].append(v)
    
    # ── 洞察卡 ──
    crowd   = [v for v in valid if v.get('price_level')=='高' and v.get('oi_level')=='高']
    bottom  = [v for v in valid if v.get('price_level')=='低' and v.get('oi_level')=='高']
    weak    = [v for v in valid if v.get('price_level')=='高' and v.get('oi_level')=='低']
    nobody  = [v for v in valid if v.get('price_level')=='低' and v.get('oi_level')=='低']
    
    # ── 重点关注 ──
    watch_long  = []  # 量价齐升：价↑+仓↑
    watch_short = []  # 下跌蓄势：价↓+仓↑
    watch_bottom = [] # 底部布局：价低+仓高
    watch_alert  = [] # 风险预警：价高+仓高+近期异动
    for v in V:
        t = v.get('_trend')
        if not t: continue
        pp, op = v.get('price_pct',50), v.get('oi_pct',50)
        if t['p_dir'] == '↑' and t['o_dir'] == '↑':
            watch_long.append((v['name'], pp, op, t['p_chg'], t['o_chg'], v.get('price_level',''), v.get('oi_level',''), v['code']))
        if t['p_dir'] == '↓' and t['o_dir'] == '↑':
            watch_short.append((v['name'], pp, op, t['p_chg'], t['o_chg'], v.get('price_level',''), v.get('oi_level',''), v['code']))
        if pp <= 33 and op >= 50 and t['o_dir'] == '↑' and not (t['p_dir'] == '↓' and t['o_dir'] == '↑'):
            watch_bottom.append((v['name'], pp, op, t['p_chg'], t['o_chg'], v['code']))
        if pp >= 67 and op >= 50:
            watch_alert.append((v['name'], pp, op, t['p_chg'], t['o_chg'], v.get('price_level',''), v.get('oi_level',''), v['code']))
    
    watch_short.sort(key=lambda x: x[4], reverse=True)
    watch_bottom.sort(key=lambda x: x[4], reverse=True)
    watch_alert.sort(key=lambda x: x[1], reverse=True)
    
    # ── 分布栏 ──
    hi_p = [v for v in valid if v.get('price_level')=='高']
    lo_p = [v for v in valid if v.get('price_level')=='低']
    hi_o = [v for v in valid if v.get('oi_level')=='高']
    lo_o = [v for v in valid if v.get('oi_level')=='低']
    
    # ── 组装 HTML ──
    H2 = []
    H2.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">')
    H2.append('<meta name="robots" content="noai, noimageai"><meta name="ai-content-detection" content="no-ai-training">')
    H2.append('<meta name="google-site-verification" content="no-archive">')
    H2.append('<meta name="viewport" content="width=device-width,initial-scale=1.0">')
    H2.append('<title>期货双维分类</title>')
    H2.append('<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>')
    H2.append(f'<style>{CSS}</style></head><body><div class="wrap">')
    
    # 标题 + 主题切换
    H2.append('<div style="display:flex;justify-content:space-between;align-items:flex-start">')
    H2.append('<h1><span>期货品种加权指数 · 双维分类矩阵</span></h1>')
    H2.append('<div class="theme-switch" onclick="cycleTheme()" title="切换日间/夜间模式">')
    H2.append('<span class="ts-icon" id="tsi">🌓</span><span class="ts-label" id="tsl">跟随系统</span></div></div>')
    
    # 副标题 + 徽章
    H2.append(f'<div class="sub">上表：历史分位矩阵（全部品种） · 下表：近{TREND_DAYS}日趋势矩阵（{nwh}品种有走势数据） · 数据每日更新</div>')
    H2.append(f'<div class="badges"><span class="badge bg1">📊 {len(valid)} 品种</span><span class="badge bg2">✅ {n2} 完整双维</span><span class="badge bg3">📈 {nwh} 有走势图</span>')
    H2.append(f'<span class="badge bg4">🕐 数据更新: {latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:8] if len(latest_date)>=8 else ""}</span></div>')
    
    # ── 重点关注 ──
    H2.append('<div class="wl-section"><h2 class="wl-title">🎯 重点关注</h2><div class="wl-grid">')
    
    # 做多趋势
    H2.append('<div class="wl-card wl-long"><div class="wl-card-h">🚀 做多趋势</div><div class="wl-card-sub">量价共振向上 · 顺势做多</div><div class="wl-card-list">')
    for name, pp, op, pc, oc, pl, ol, cd in watch_long[:5]:
        H2.append(f'<span class="wl-tag-btn tag" data-code="{cd}">{name}</span>')
    if not watch_long: H2.append('<div class="wl-empty">暂无</div>')
    H2.append('</div></div>')
    
    # 下跌蓄势
    H2.append('<div class="wl-card wl-short"><div class="wl-card-h">📉 下跌蓄势</div><div class="wl-card-sub">价格回调 · 资金吸筹</div><div class="wl-card-list">')
    for name, pp, op, pc, oc, pl, ol, cd in watch_short[:5]:
        H2.append(f'<span class="wl-tag-btn tag" data-code="{cd}">{name}</span>')
    if not watch_short: H2.append('<div class="wl-empty">暂无品种</div>')
    H2.append('</div></div>')
    
    # 底部布局
    H2.append('<div class="wl-card wl-bottom"><div class="wl-card-h">🔍 底部布局</div><div class="wl-card-sub">历史低价+资金涌入 · 反转观察</div><div class="wl-card-list">')
    for name, pp, op, pc, oc, cd in watch_bottom[:6]:
        H2.append(f'<span class="wl-tag-btn tag" data-code="{cd}">{name}</span>')
    H2.append('</div></div>')
    
    # 风险预警
    H2.append('<div class="wl-card wl-alert"><div class="wl-card-h">⚠️ 风险预警</div><div class="wl-card-sub">高位异动 · 需警惕</div><div class="wl-card-list">')
    for name, pp, op, pc, oc, pl, ol, cd in watch_alert[:6]:
        H2.append(f'<span class="wl-tag-btn wl-alert-tag tag" data-code="{cd}">{name}</span>')
    H2.append('</div></div>')
    
    H2.append('</div></div>')
    
    # ── 历史分位矩阵标题 + 洞察卡 ──
    H2.append('<h2 style="margin:28px 0 16px;font-size:18px;font-weight:600;color:var(--text)">历史分位矩阵 <span style="font-size:12px;color:var(--text4);font-weight:400">—— 全历史极值百分位</span></h2>')
    
    # 洞察卡
    def make_ins(emoji, title, desc, items, color, n):
        names = ' · '.join([v['name'] for v in items[:3]])
        suffix = f' 等{n}个' if n > 3 else ''
        return f'<div class="ins-card" style="border-top:3px solid {color}"><div class="ins-head">{emoji} {title} <span>{n}个</span></div><div class="ins-desc">{desc}</div><div class="ins-names">{names}{suffix}</div></div>'
    
    H2.append('<div class="ins">')
    H2.append(make_ins('⚠️', '拥挤区', '量价双高，关注反转风险', crowd, '#ef4444', len(crowd)))
    H2.append(make_ins('🔍', '底部博弈', '价格低位但资金大量堆积', bottom, '#22c55e', len(bottom)))
    H2.append(make_ins('📉', '弱趋势', '价格高位但缺乏资金跟进', weak, '#f59e0b', len(weak)))
    H2.append(make_ins('💤', '无人区', '量价双杀，等待催化剂', nobody, '#64748b', len(nobody)))
    H2.append('</div>')
    
    # ── 历史分位矩阵表格 ──
    H2.append('<table><thead><tr>')
    H2.append('<th class="th-corner"><div class="corner-top"><span>→</span> 持仓</div><div class="corner-div">—</div><div class="corner-bot">价格 <span>↓</span></div></th>')
    for ol in ['高','中','低']:
        emoji = {'高':'🔴','中':'🟡','低':'🟢'}[ol]
        H2.append(f'<th><span class="th-emoji">{emoji}</span><br>持仓量{ol}<br><span class="th-sub">{"67-100" if ol=="高" else "33-67" if ol=="中" else "0-33"}%</span></th>')
    H2.append('</tr></thead><tbody>')
    
    for pl in ['高','中','低']:
        pe = {'高':'🔴','中':'🟡','低':'🟢'}[pl]
        H2.append(f'<tr><td class="td-label"><span class="td-emoji">{pe}</span><br>价格{pl}<br><span class="td-sub">{"67-100" if pl=="高" else "33-67" if pl=="中" else "0-33"}%</span></td>')
        for ol in ['高','中','低']:
            items = cells.get((pl, ol), [])
            H2.append('<td class="td-cell">')
            for v in items:
                code = v['code']
                has_chart = ' ch' if code in H and H[code].get('price_dates') else ''
                pp = v.get('price_pct', 0)
                op = v.get('oi_pct', 0)
                pl_v = v.get('price_level', '')
                ol_v = v.get('oi_level', '')
                chart_hint = ' | 📈走势图' if has_chart else ''
                title = f'{v["name"]} | 价格{pl_v}位{pp:.0f}% | 持仓{ol_v} {op:.0f}%{chart_hint}'
                H2.append(f'<span class="tag{has_chart}" data-code="{code}" title="{title}">{v["name"]}</span> ')
            if not items:
                H2.append('<span class="td-empty">—</span>')
            H2.append('</td>')
        H2.append('</tr>')
    H2.append('</tbody></table>')
    
    # ── 趋势矩阵 ──
    H2.append(f'<h2 style="margin:32px 0 16px;font-size:18px;font-weight:600;color:var(--text)">量价趋势矩阵 <span style="font-size:12px;color:var(--text4);font-weight:400">—— 近{TREND_DAYS}交易日</span></h2>')
    
    # 趋势洞察
    up_up = trend_cells.get(('↑','↑'), [])
    dn_up = trend_cells.get(('↓','↑'), [])
    up_dn = trend_cells.get(('↑','↓'), [])
    dn_dn = trend_cells.get(('↓','↓'), [])
    
    H2.append('<div class="ins">')
    H2.append(make_ins('🔥', '量价齐升', '量价共振向上，趋势最健康', up_up, '#3fb950', len(up_up)))
    H2.append(make_ins('📤', '价升量跌', '涨价但资金撤退，动能减弱', up_dn, '#f0883e', len(up_dn)))
    H2.append(make_ins('📥', '价跌量增', '跌价但资金涌入，蓄势待发', dn_up, '#3b82f6', len(dn_up)))
    H2.append(make_ins('❄️', '量价齐跌', '双杀格局，等待企稳', dn_dn, '#64748b', len(dn_dn)))
    H2.append('</div>')
    
    # 趋势表格
    H2.append('<table><thead><tr>')
    H2.append('<th class="th-corner"><div class="corner-top"><span>↑↓</span> 持仓趋势</div><div class="corner-div">—</div><div class="corner-bot">价格趋势 <span>↑↓</span></div></th>')
    for od in ['↑','—','↓']:
        H2.append(f'<th><span class="th-emoji">{od}</span><br>持仓{ "上升" if od=="↑" else "持平" if od=="—" else "下降" }</th>')
    H2.append('</tr></thead><tbody>')
    
    for pd in ['↑','—','↓']:
        labels = {'↑':'↑ 价格上升','—':'— 价格持平','↓':'↓ 价格下降'}
        H2.append(f'<tr><td class="td-label" style="color:#93c5fd;text-align:center;font-size:13px;font-weight:600;border:1px solid var(--border);background:rgba(59,130,246,.06);border-left:3px solid #3b82f6">{labels[pd]}</td>')
        for od in ['↑','—','↓']:
            items = trend_cells.get((pd, od), [])
            H2.append('<td class="td-cell">')
            for v in items:
                t = v.get('_trend', {})
                has_chart = ' ch' if v['code'] in H and H[v['code']].get('price_dates') else ''
                title = f'{v["name"]} | 价{t["p_chg"]:+.1f}% 仓{t["o_chg"]:+.1f}%'
                H2.append(f'<span class="tag{has_chart}" data-code="{v["code"]}" title="{title}">{v["name"]}</span> ')
            if not items:
                H2.append('<span class="td-empty">—</span>')
            H2.append('</td>')
        H2.append('</tr>')
    H2.append('</tbody></table>')
    
    # ── 底部注释 ──
    excluded = '多晶硅、工业硅、钯、铂、碳酸锂、欧线集运、LPG'
    missing_oi = '苹果加权、胶合板加权'
    H2.append(f'<div class="fn">未纳入: {missing_oi} (API无历史持仓聚合) · 排除: {excluded} (新品种/数据缺失) · 数据源: 同花顺hithink + Sina K线 · 更新: {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>')
    H2.append('</div>')
    
    # ── 弹窗 ──
    H2.append('<div class="mo" id="mo"><div class="md"><div class="md-h"><h2 id="mt"></h2><button class="md-x" onclick="closeModal()">✕</button></div><div class="md-b" id="mb"></div></div></div>')
    
    # ── JS ──
    H2.append(JS)
    H2.append('<script src="stats.js"></script></body></html>')
    
    return '\n'.join(H2), notes

# ─── 主流程 ───────────────────────────────────────────────
def main():
    V, H, latest_date = load_data()
    html, notes = build_html(V, H, latest_date)
    
    with open(OUTPUT, 'w') as f:
        f.write(html)
    
    # 把AI观察也写回数据文件
    with open(DATA_FILE) as f: d = json.load(f)
    d['ai_notes'] = notes
    with open(DATA_FILE, 'w') as f: json.dump(d, f, ensure_ascii=False)
    
    valid = [v for v in V if v.get('price_pct', 0) > 0 or v.get('price_level')]
    nwh = sum(1 for v in V if v['code'] in H and H[v['code']].get('price_dates'))
    print(f'OK: {OUTPUT} ({len(html)//1024}KB) | {len(valid)} varieties | {nwh} with charts | {len(notes)} AI notes')

if __name__ == '__main__':
    main()
