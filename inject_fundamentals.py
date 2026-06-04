#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基本面跟踪 + Tab 注入脚本
在 gen_final.py 生成看板后运行，将基本面分析和双Tab结构注入 HTML。
"""

import json, os, re, sys
from collections import defaultdict

WORK = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(WORK, 'futures_dashboard.html')
DATA_FILE = os.path.join(WORK, 'data', 'dashboard_data.json')
FUND_FILE = os.path.join(WORK, 'data', 'fundamentals_data.json')

CATEGORY_MAP = {
    'RB8888.SHF': '黑色系', 'HC8888.SHF': '黑色系', 'I8888.DCE': '黑色系',
    'J8888.DCE': '黑色系', 'JM8888.DCE': '黑色系', 'SM8888.ZCE': '黑色系', 'SF8888.ZCE': '黑色系',
    'CU8888.SHF': '有色金属', 'AL8888.SHF': '有色金属', 'ZN8888.SHF': '有色金属',
    'PB8888.SHF': '有色金属', 'NI8888.SHF': '有色金属', 'SN8888.SHF': '有色金属', 'AO8888.SHF': '有色金属',
    'AU8888.SHF': '贵金属', 'AG8888.SHF': '贵金属',
    'MA8888.ZCE': '能源化工', 'FG8888.ZCE': '能源化工', 'UR8888.ZCE': '能源化工',
    'BU8888.SHF': '能源化工', 'RU8888.SHF': '能源化工', 'SP8888.SHF': '能源化工',
    'L8888.DCE': '能源化工', 'PP8888.DCE': '能源化工', 'V8888.DCE': '能源化工',
    'EG8888.DCE': '能源化工', 'EB8888.DCE': '能源化工', 'PF8888.ZCE': '能源化工',
    'PX8888.ZCE': '能源化工',
    'M8888.DCE': '农产品', 'Y8888.DCE': '农产品', 'A8888.DCE': '农产品',
    'P8888.DCE': '农产品', 'B8888.DCE': '农产品', 'CS8888.DCE': '农产品',
    'JD8888.DCE': '农产品', 'LH8888.DCE': '农产品', 'RR8888.DCE': '农产品', 'FB8888.DCE': '农产品',
    'SR8888.ZCE': '农产品', 'CF8888.ZCE': '农产品', 'CY8888.ZCE': '农产品',
    'OI8888.ZCE': '农产品', 'RM8888.ZCE': '农产品', 'CJ8888.ZCE': '农产品',
}

VARIETY_CONTEXT = {
    'RB8888.SHF': '螺纹钢是国内建筑钢材龙头，直接受房地产新开工和基建投资驱动。当前钢铁行业处于亏损去产能阶段，利润微薄制约供给弹性。PMI 50.0对钢材需求信号中性。',
    'HC8888.SHF': '热卷下游以制造业（汽车/家电/机械）为主，与螺纹钢形成品种内结构分化。制造业PMI的边际变化对热卷需求更为敏感。',
    'I8888.DCE': '铁矿石100%依赖进口，汇率波动是核心变量。四大矿山供给集中度高，国内粗钢产量同比下降-4.1%形成需求压力。',
    'J8888.DCE': '焦炭处于煤焦钢产业链中游，受上游焦煤成本和下游钢厂利润双重挤压。当前钢厂亏损减产导致焦炭需求承压。',
    'JM8888.DCE': '焦煤是黑色系原料端，供给端受安全检查和进口政策影响大。价格低位运行但蒙古煤进口增量压制反弹空间。',
    'SM8888.ZCE': '锰硅是炼钢辅料，需求与粗钢产量高度绑定。粗钢产量同比-4.1%直接压制锰硅消费，价格处于历史低位。',
    'SF8888.ZCE': '硅铁同样是炼钢辅料，且供给端产能过剩问题突出。价格处于17%极低分位，行业大面积亏损，减产预期支撑底部。',
    'CU8888.SHF': '沪铜是全球定价品种，兼具工业属性和金融属性。当前价格处于96%历史高位，主要受供给端扰动和新能源需求支撑。',
    'AL8888.SHF': '沪铝供给端受云南水电季节性波动影响，需求端以建筑和汽车为主。价格93%分位偏高，但库存处于近年低位。',
    'ZN8888.SHF': '沪锌供需相对平衡，LME库存极低。近期价格+6.1%上涨+16.6%增仓，为全品种中趋势最强的有色金属。',
    'PB8888.SHF': '沪铅需求以铅酸蓄电池为主，受锂电池替代趋势长期压制。价格中位震荡，缺乏独立驱动逻辑。',
    'NI8888.SHF': '沪镍供给端印尼镍铁产能持续释放，需求端不锈钢和新能源电池增速放缓。价格39%分位中性，供给过剩格局未改。',
    'SN8888.SHF': '沪锡受半导体和电子焊料需求驱动，缅甸矿供应扰动是核心变量。价格93%分位极高位，持仓+29.5%显示资金看多。',
    'AO8888.SHF': '氧化铝是电解铝原料，国内产能充足但受铝土矿进口依赖制约。价格12%极低分位，存在超跌修复可能。',
    'AU8888.SHF': '沪金受全球央行购金、地缘政治避险和美联储政策三重驱动。价格77%分位偏高，实际利率下行支撑金价中枢。',
    'AG8888.SHF': '沪银兼具贵金属避险和工业属性，光伏用银需求是新增长极。价格57%分位中性，投机资金尚未大规模介入。',
    'MA8888.ZCE': '甲醇国内以煤制为主，进口依赖中东货源。港口库存和MTO装置开工是核心变量。近期价格下跌，资金流出。',
    'FG8888.ZCE': '玻璃下游直接对应房地产竣工端，保交楼政策是需求核心变量。价格11%极低分位，全行业利润为负，冷修出清待观察。',
    'UR8888.ZCE': '尿素是农资品种，需求季节性明显（春耕→夏管→秋收）。价格20%低位，当前农需淡季，出口政策是潜在变量。',
    'BU8888.SHF': '沥青下游对接道路基建和防水材料，原油成本是定价锚。价格81%高位但受原油回调拖累，持仓大增显示抄底资金介入。',
    'RU8888.SHF': '橡胶供需格局长期过剩，东南亚主产国产量是核心变量。价格33%低位、持仓32%低位，等待供给端扰动催化。',
    'SP8888.SHF': '纸浆进口依赖度高，海外浆厂定价权强。价格20%低位但持仓71%高位，资金在底部大量堆积，典型的底部博弈品种。',
    'L8888.DCE': '塑料（LLDPE）下游以包装膜和农膜为主，原油成本端传导是主线。价格22%低位、持仓57%中位，弱势寻底阶段。',
    'PP8888.DCE': '聚丙烯与塑料同为聚烯烃，产能扩张周期下供给压力持续。价格55%中位、持仓83%高位，资金大量沉淀但方向不明。',
    'V8888.DCE': 'PVC下游对应房地产管材型材，是地产竣工链品种。价格7%极低分位、持仓91%极高，最典型的底部博弈品种。',
    'EG8888.DCE': '乙二醇国内煤制产能大量投放，供给过剩压力持续。价格33%低位、持仓65%中位偏上，产能出清缓慢制约反弹。',
    'EB8888.DCE': '苯乙烯上游纯苯成本支撑强，下游以家电和汽车为主。价格61%中位、持仓87%极高，近期大跌后资金仍在流入。',
    'PF8888.ZCE': '短纤下游对接纺织服装，出口订单是需求风向标。价格59%中位、持仓21%低位，市场关注度不足。',
    'PX8888.ZCE': '对二甲苯是PTA上游原料，亚洲产能扩张周期中。价格60%中位、持仓62%中位，近期-13.2%大跌。',
    'M8888.DCE': '豆粕是国内最大的蛋白粕品种，100%依赖进口大豆压榨。CBOT大豆、人民币汇率、生猪存栏是三大核心变量。',
    'Y8888.DCE': '豆油是国内三大油脂之一，与棕榈油、菜油形成替代关系。价格37%偏低位、持仓66%中位偏上。',
    'A8888.DCE': '豆一是国产非转基因大豆，定价相对独立于进口大豆体系。价格63%中位偏上、持仓48%中位。',
    'P8888.DCE': '棕榈油完全依赖进口，季节性产量周期和B35生物柴油政策是核心变量。价格63%中位、持仓40%中位偏低。',
    'B8888.DCE': '豆二是进口大豆压榨标的，直接锚定CBOT大豆和升贴水。价格中位，受国际大豆供需和汇率双重影响。',
    'CS8888.DCE': '玉米淀粉是玉米深加工产物，定价锚玉米成本。价格57%中位、持仓28%低位，缺乏独立驱动。',
    'JD8888.DCE': '鸡蛋是国内最活跃的畜牧品种，供给端受存栏量和补栏节奏影响，需求端季节性规律极强。价格48%中位、持仓88%极高。',
    'LH8888.DCE': '生猪是国内最大的畜牧品种，受猪周期和出栏节奏主导。价格受能繁母猪存栏和消费季节性双重影响。',
    'RR8888.DCE': '粳米是口粮品种，受国家收储政策和最低收购价保护。价格66%中位、持仓67%高位，波动率低。',
    'FB8888.DCE': '纤维板是人造板品种，下游对应家具和装修。价格38%中位、持仓26%低位，市场规模小、流动性偏低。',
    'SR8888.ZCE': '白糖国内供需存在缺口，进口依赖度高。印度/巴西主产国产量和出口政策是核心变量。',
    'CF8888.ZCE': '棉花下游对接纺织服装产业链，出口订单和内需消费是双驱动。价格26%低位、持仓65%中位，低位蓄势。',
    'CY8888.ZCE': '棉纱是棉花加工品，定价锚棉花+加工费。价格37%中位偏下、持仓36%低位，流动性偏低。',
    'OI8888.ZCE': '菜油是国内三大油脂之一，进口菜籽压榨为主。价格47%中位、持仓34%中位偏低。',
    'RM8888.ZCE': '菜粕是水产饲料蛋白来源，与豆粕存在替代关系。价格24%低位、持仓76%高位，底部博弈+资金堆积典型品种。',
    'CJ8888.ZCE': '红枣供给端受天气和种植面积影响，需求季节性集中于秋冬消费旺季。价格10%极低分位、持仓62%中位偏上。',
}

MONTH_NAMES = {'01':'1月','02':'2月','03':'3月','04':'4月','05':'5月','06':'6月',
               '07':'7月','08':'8月','09':'9月','10':'10月','11':'11月','12':'12月'}

def compute_seasonal(dates, prices):
    monthly = defaultdict(list)
    for i in range(20, len(dates)):
        month = dates[i][4:6]
        if prices[i-20] == 0 or prices[i] == 0:
            continue  # 跳过脏数据
        ret = (prices[i] / prices[i-20]) - 1
        monthly[month].append(ret * 100)
    result = {}
    for m, rets in sorted(monthly.items()):
        if not rets:
            continue
        win = sum(1 for r in rets if r > 0)
        result[m] = {'avg': round(sum(rets)/len(rets), 2), 'win_rate': round(win/len(rets)*100, 1), 'count': len(rets)}
    return result

def gen_fundamentals():
    """从 dashboard_data.json 生成 fundamentals_data.json"""
    with open(DATA_FILE) as f:
        db = json.load(f)
    
    varieties = db['varieties']
    historical = db['historical']
    # 从全量历史数据计算最新交易日（与gen_final.py一致）
    today = db.get('updated_at', '')
    if not today:
        latest = ''
        for h in historical.values():
            pd = h.get('price_dates', [])
            if pd and pd[-1] > latest:
                latest = pd[-1]
        today = f'{latest[:4]}-{latest[4:6]}-{latest[6:8]}' if len(latest) >= 8 else '2026-06-02'
    
    output = {"updated_at": today, "varieties": {}}
    
    for vdata in varieties:
        code = vdata['code']
        name = vdata['name']
        cat = CATEGORY_MAP.get(code, '其他')
        hist = historical.get(code, {})
        ctx = VARIETY_CONTEXT.get(code, f'{name}属于{cat}品种。')
        
        dates = hist.get('price_dates', [])
        prices = hist.get('price_values', [])
        oi_vals = hist.get('oi_values', [])
        
        seasonal = compute_seasonal(dates, prices) if dates else {}
        cur_seasonal = seasonal.get('06', {'avg': 0, 'win_rate': 50})
        pp = vdata.get('price_pct', 50)
        op = vdata.get('oi_pct', 50)
        
        # OI trends
        oi_t = '震荡'
        chg30oi = chg60oi = 0
        if len(oi_vals) >= 30:
            chg30oi = (oi_vals[-1] / oi_vals[-min(30,len(oi_vals))] - 1) * 100
            chg60oi = (oi_vals[-1] / oi_vals[-min(60,len(oi_vals))] - 1) * 100
            recent5 = oi_vals[-5:]
            if all(recent5[i] >= recent5[i-1] for i in range(1, len(recent5))):
                oi_t = '持续流入'
            elif all(recent5[i] <= recent5[i-1] for i in range(1, len(recent5))):
                oi_t = '持续流出'
        
        chg30oi = round(chg30oi, 1)
        chg60oi = round(chg60oi, 1)
        
        # Price momentum
        p_cur = vdata.get('cur_price', 0)
        mom20 = mom60 = ytd = 0
        yr_high = yr_low = p_cur
        
        if len(prices) >= 60:
            mom5 = round((prices[-1]/prices[-min(5,len(prices))]-1)*100, 1)
            mom20 = round((prices[-1]/prices[-min(20,len(prices))]-1)*100, 1)
            mom60 = round((prices[-1]/prices[-min(60,len(prices))]-1)*100, 1)
            yr_prices = [p for p, d in zip(prices, dates) if d.startswith('2026')]
            yr_high = max(yr_prices) if yr_prices else p_cur
            yr_low = min(yr_prices) if yr_prices else p_cur
            if yr_prices:
                ytd = round((prices[-1]/yr_prices[0]-1)*100, 1)
        
        sw = cur_seasonal['win_rate']
        sa = cur_seasonal['avg']
        
        # Layer directions
        if oi_t == '持续流入': l4_dir = '偏多'
        elif oi_t == '持续流出': l4_dir = '偏空'
        else: l4_dir = '中性'
        
        if mom20 > 3: l3_dir = '偏多'
        elif mom20 < -3: l3_dir = '偏空'
        elif sw < 40: l3_dir = '中性偏空'
        elif sw > 60: l3_dir = '中性偏多'
        else: l3_dir = '中性'
        
        if pp < 30: l2_dir = '偏多（低位）'
        elif pp > 70: l2_dir = '偏空（高位）'
        else: l2_dir = '中性'
        
        l1_dir = '中性偏多' if cat == '黑色系' else '中性'
        
        # Layer 4 description
        if oi_t == '持续流入' and chg30oi > 15:
            l4_desc = f"持仓量近5个交易日持续增加，30日累计增长{chg30oi:+.1f}%，大资金主动入场迹象明显。持仓分位{op:.0f}%，"
            l4_desc += "仓位仍有提升空间，资金面支撑较强。" if op <= 70 else "但仓位已处于历史高位，后续增仓空间有限。"
        elif oi_t == '持续流入':
            l4_desc = f"持仓量近5日温和增长，30日累计{chg30oi:+.1f}%。持仓分位{op:.0f}%，资金在稳步布局但力度有限。"
        elif oi_t == '持续流出' and chg30oi < -15:
            l4_desc = f"持仓量连续缩减，30日累计流出{abs(chg30oi):.1f}%，多头撤退或空头止盈迹象明显。"
            l4_desc += f"持仓分位{op:.0f}%，仓位已降至历史低位。" if op < 30 else "仍有进一步减仓空间。"
        elif oi_t == '持续流出':
            l4_desc = f"持仓量近5日小幅减少，30日累计{chg30oi:+.1f}%。资金整体呈流出态势但力度温和。"
        else:
            if abs(chg30oi) < 3:
                l4_desc = f"持仓量近5日窄幅波动，30日变化仅{chg30oi:+.1f}%，资金面无明确方向。市场处于观望状态。"
            else:
                l4_desc = f"持仓量近5日震荡，30日变化{chg30oi:+.1f}%，60日变化{chg60oi:+.1f}%。资金短期方向不明。"
        
        # Layer 3 description
        l3_parts = []
        if abs(mom20) > 1:
            l3_parts.append(f"近20个交易日{'上涨' if mom20 > 0 else '下跌'}{abs(mom20):.1f}%")
            if abs(mom20) > 5: l3_parts.append("趋势力度较强")
            elif abs(mom20) > 3: l3_parts.append("趋势温和")
            else: l3_parts.append("趋势偏弱")
        if abs(mom60) > 3:
            l3_parts.append(f"近60日{'上涨' if mom60 > 0 else '下跌'}{abs(mom60):.1f}%，中期{'多头' if mom60 > 0 else '空头'}趋势延续")
        if sw < 35:
            l3_parts.append(f"6月历史胜率仅{sw:.0f}%，季节性偏弱（均值{sa:+.1f}%）")
        elif sw > 65:
            l3_parts.append(f"6月历史胜率{sw:.0f}%，季节性偏强（均值{sa:+.1f}%）")
        else:
            l3_parts.append(f"6月历史胜率{sw:.0f}%（均值{sa:+.1f}%），季节性方向不显著")
        if ytd and abs(ytd) > 3:
            l3_parts.append(f"年内累计{'上涨' if ytd > 0 else '下跌'}{abs(ytd):.1f}%")
        l3_desc = "；".join(l3_parts) + "。"
        
        # Layer 2 description
        if pp < 15:
            l2_desc = f"当前价格{p_cur:.0f}处于历史{pp:.0f}%极低分位，距历史最低{vdata.get('price_min',0):.0f}仅{((p_cur/vdata.get('price_min',1))-1)*100:.0f}%空间。"
            l2_desc += "低位有资金吸筹迹象，底部特征正在累积。" if chg30oi > 0 else "但资金尚未明显流入，底部确认需等待量价配合。"
        elif pp < 30:
            l2_desc = f"当前价格{p_cur:.0f}处于历史{pp:.0f}%低位区间，年内高点{yr_high:.0f}（距当前+{((yr_high/p_cur-1)*100):.0f}%），存在均值回归空间。当前已反映较多悲观预期。"
        elif pp > 85:
            l2_desc = f"当前价格{p_cur:.0f}处于历史{pp:.0f}%极高分位，逼近历史最高{vdata.get('price_max',0):.0f}。"
            l2_desc += "持仓同步下降，高位资金撤退信号需高度警惕。" if chg30oi < 0 else "但持仓未明显下降，高位博弈需严控仓位。"
        elif pp > 70:
            l2_desc = f"当前价格{p_cur:.0f}处于历史{pp:.0f}%偏高区间。"
            if chg30oi > 10: l2_desc += "资金仍在加仓，有继续上行动能但回落风险也在积累。"
            else: l2_desc += "资金流入有限，上行空间受制于高位估值压力。"
        else:
            l2_desc = f"当前价格{p_cur:.0f}处于历史{pp:.0f}%中位区间，估值相对合理。"
            if chg30oi > 10: l2_desc += "持仓增长明显，资金在当前位置积极布局。"
            elif chg30oi < -10: l2_desc += "持仓持续下降，市场参与度降低。"
            else: l2_desc += "量和价均在中性区域，等待方向信号。"
        
        # Layer 1 description
        l1_desc = ctx
        if pp < 30 and chg30oi > 5:
            l1_desc += " 该品种处于价格低位+资金流入的底部蓄势阶段，宏观利空已被定价，关注产业层面边际改善信号。"
        elif pp > 70:
            l1_desc += " 价格处于历史高位区间，任何宏观利空都可能触发获利盘集中了结。"
        elif mom20 < -5:
            l1_desc += " 近期价格大幅下跌，产业层面可能正在交易需求走弱预期，关注超跌修复机会。"
        elif mom20 > 5:
            l1_desc += " 近期价格大幅上涨，产业层面可能有供给端扰动或需求超预期因素，关注持续性。"
        else:
            l1_desc += " 宏观面和产业面均无显著方向性信号，价格在当前位置震荡整理，等待新的驱动因素。"
        
        entry = {
            'code': code, 'name': name, 'category': cat,
            'cur_price': p_cur, 'cur_oi': vdata.get('cur_oi', 0),
            'price_pct': pp, 'oi_pct': op,
            'layer1': {
                'direction': l1_dir,
                'description': l1_desc,
                'data': [
                    {'label': '品种定位', 'value': ctx.split('。')[0] if '。' in ctx else ctx[:60], 'source': '4'},
                    {'label': 'PMI', 'value': '5月50.0（荣枯线）', 'source': '4'},
                    {'label': '汇率', 'value': '美元6.767', 'source': '8'},
                ]
            },
            'layer2': {
                'direction': l2_dir,
                'description': l2_desc,
                'data': [
                    {'label': '最新价', 'value': f"{p_cur:.0f}", 'source': '9'},
                    {'label': '历史分位', 'value': f"{pp:.0f}%（{'极低位' if pp<15 else '低位' if pp<33 else '中位' if pp<67 else '高位' if pp<85 else '极高位'}）", 'source': '0'},
                    {'label': '历史区间', 'value': f"{vdata.get('price_min',0):.0f}~{vdata.get('price_max',0):.0f}", 'source': '0'},
                    {'label': '年内高点', 'value': f"{yr_high:.0f}（距当前+{((yr_high/p_cur-1)*100):.0f}%）" if yr_high > p_cur else '—', 'source': '0'},
                ]
            },
            'layer3': {
                'direction': l3_dir,
                'description': l3_desc,
                'data': [
                    {'label': '20日涨跌', 'value': f"{mom20:+.1f}%", 'source': '0'},
                    {'label': '60日涨跌', 'value': f"{mom60:+.1f}%", 'source': '0'},
                    {'label': '6月历史胜率', 'value': f"{sw:.0f}%（{sa:+.1f}%）", 'source': '0'},
                    {'label': '年内累计', 'value': f"{ytd:+.1f}%" if ytd else '—', 'source': '0'},
                ]
            },
            'layer4': {
                'direction': l4_dir,
                'description': l4_desc,
                'data': [
                    {'label': '30日持仓变化', 'value': f"{chg30oi:+.1f}%", 'source': '0'},
                    {'label': '60日持仓变化', 'value': f"{chg60oi:+.1f}%", 'source': '0'},
                    {'label': '持仓分位', 'value': f"{op:.0f}%", 'source': '0'},
                    {'label': '资金面判断', 'value': oi_t, 'source': '0'},
                ]
            },
        }
        
        dirs = [l1_dir, l2_dir, l3_dir, l4_dir]
        pos = sum(1 for d in dirs if '偏多' in d and '空' not in d)
        neg = sum(1 for d in dirs if '偏空' in d)
        neu = 4 - pos - neg
        entry['overall'] = {'resonance': f"{pos}偏多/{neu}中性/{neg}偏空"}
        if pos >= 3: entry['overall']['judgment'] = '偏多'
        elif neg >= 3: entry['overall']['judgment'] = '偏空'
        elif pos > neg: entry['overall']['judgment'] = '中性偏多'
        elif neg > pos: entry['overall']['judgment'] = '中性偏空'
        else: entry['overall']['judgment'] = '中性'
        
        output['varieties'][code] = entry
    
    output['sources'] = {
        '4': {'name': '国家统计局', 'url': 'https://data.stats.gov.cn/'},
        '8': {'name': '外汇交易中心', 'url': 'https://www.chinamoney.com.cn/'},
        '9': {'name': '文华财经行情', 'url': 'https://www.wenhua.com.cn/'},
        '0': {'name': '本地K线数据库', 'url': None, 'note': '基于2009年以来加权指数历史数据计算'},
    }
    
    os.makedirs(os.path.dirname(FUND_FILE), exist_ok=True)
    with open(FUND_FILE, 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    return output, today


def inject_into_html():
    """将基本面数据 + Tab结构注入 HTML"""
    if not os.path.exists(HTML_FILE):
        print(f'❌ HTML 文件不存在: {HTML_FILE}')
        return False
    if not os.path.exists(FUND_FILE):
        print(f'❌ 基本面数据不存在，先生成...')
        gen_fundamentals()
    
    with open(FUND_FILE) as f:
        fd = json.load(f)
    fd_json = json.dumps(fd, ensure_ascii=False, separators=(',', ':'))
    
    with open(HTML_FILE, 'r') as f:
        lines = f.readlines()
    
    already_injected = 'switchTab' in ''.join(lines)
    
    if already_injected:
        # Just update the data block by finding and replacing the JSON
        text = ''.join(lines)
        marker = '_fd={"updated_at"'
        idx = text.find(marker)
        if idx < 0:
            print('⚠️ 数据块定位失败')
            return False
        # Count braces to find JSON end
        depth = 0
        end = idx + 4  # skip '_fd='
        for i in range(end, len(text)):
            if text[i] == '{': depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        new_text = text[:idx+4] + fd_json + text[end+1:]
        if text == new_text:
            print('✅ 基本面数据已是最新，无需更新')
            return True
        with open(HTML_FILE, 'w') as f:
            f.write(new_text)
        print(f'✅ 基本面数据已更新: {len(new_text):,} bytes')
        return True
    
    # ---- Full injection (first time) ----
    sub_idx = modal_idx = -1
    for i, line in enumerate(lines):
        if '上表：历史分位矩阵' in line and sub_idx < 0: sub_idx = i
        if 'class="mo" id="mo"' in line: modal_idx = i
    
    if sub_idx < 0 or modal_idx < 0:
        print(f'❌ HTML 结构异常 (sub={sub_idx}, modal={modal_idx})')
        return False
    
    prefix = ''.join(lines[:sub_idx+1])
    matrix = ''.join(lines[sub_idx+1:modal_idx])
    tail = ''.join(lines[modal_idx:])
    

    # ---- Full injection (first time) ----
    
    # Tab CSS
    tab_css = '\n/* Tab切换 */\n.tabs{display:flex;gap:0;margin-bottom:20px;border-bottom:2px solid var(--border)}\n.tab-btn{padding:10px 24px;font-size:14px;font-weight:600;color:var(--text4);cursor:pointer;border:none;background:none;border-bottom:2px solid transparent;margin-bottom:-2px;transition:.15s}\n.tab-btn:hover{color:var(--text2)}\n.tab-btn.active{color:#60a5fa;border-bottom-color:#60a5fa}\n.tab-content{display:none}\n.tab-content.active{display:block}\n.ft-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:10px}\n.ft-date{font-size:12px;color:var(--text4)}\n.ft-actions{display:flex;gap:8px}\n.ft-btn{padding:6px 14px;font-size:11px;font-weight:500;border-radius:8px;cursor:pointer;border:1px solid var(--border);background:var(--bg2);color:var(--text3);transition:.15s}\n.ft-btn:hover{background:var(--bg3);border-color:var(--text3);color:var(--text)}\n.cat-group{margin-bottom:20px;border:1px solid var(--border);border-radius:12px;overflow:hidden;background:var(--bg2)}\n.cat-header{padding:14px 20px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;user-select:none;transition:background .15s}\n.cat-header:hover{background:var(--bg3)}\n.cat-title{font-size:15px;font-weight:600;color:var(--text);display:flex;align-items:center;gap:10px}\n.cat-stats{display:flex;gap:12px;font-size:12px;align-items:center}\n.cat-stat{display:flex;align-items:center;gap:4px}\n.cat-stat-dot{width:8px;height:8px;border-radius:50%}\n.cat-stat-dot.up{background:#ef4444}.cat-stat-dot.neu{background:#f59e0b}.cat-stat-dot.dn{background:#22c55e}\n.cat-arrow{font-size:14px;color:var(--text4);transition:transform .2s}\n.cat-group.open .cat-arrow{transform:rotate(90deg)}\n.cat-body{display:none;padding:0 20px 20px;flex-wrap:wrap;gap:14px}\n.cat-group.open .cat-body{display:flex}\n.fund-card{border:1px solid var(--border);border-radius:12px;padding:16px;background:var(--bg3);width:calc(25% - 10.5px);min-width:220px;transition:border-color .15s,box-shadow .15s;cursor:pointer}\n.fund-card:hover{border-color:var(--text3);box-shadow:0 4px 16px rgba(0,0,0,.08)}\n.fund-card.bull{border-left:3px solid #ef4444}\n.fund-card.neutral{border-left:3px solid #f59e0b}\n.fund-card.bear{border-left:3px solid #22c55e}\n.fc-name{font-size:14px;font-weight:700;color:var(--text);margin-bottom:2px}\n.fc-code{font-size:10px;color:var(--text5);margin-bottom:8px}\n.fc-judgment{font-size:12px;font-weight:600;margin-bottom:10px}\n.fc-judgment.bull{color:#ef4444}.fc-judgment.neutral{color:#f59e0b}.fc-judgment.bear{color:#22c55e}\n.fc-layers{display:flex;gap:6px;margin-bottom:10px;font-size:11px;flex-wrap:wrap}\n.fc-layer{padding:2px 6px;border-radius:5px;font-weight:600;font-size:10px}\n.l1b{background:rgba(239,68,68,.12);color:#ef4444}.l1n{background:rgba(245,158,11,.12);color:#f59e0b}.l1r{background:rgba(34,197,94,.12);color:#22c55e}\n.l2b{background:rgba(239,68,68,.12);color:#ef4444}.l2n{background:rgba(245,158,11,.12);color:#f59e0b}.l2r{background:rgba(34,197,94,.12);color:#22c55e}\n.l3b{background:rgba(239,68,68,.12);color:#ef4444}.l3n{background:rgba(245,158,11,.12);color:#f59e0b}.l3r{background:rgba(34,197,94,.12);color:#22c55e}\n.l4b{background:rgba(239,68,68,.12);color:#ef4444}.l4n{background:rgba(245,158,11,.12);color:#f59e0b}.l4r{background:rgba(34,197,94,.12);color:#22c55e}\n.fc-data{font-size:11px;color:var(--text3);line-height:1.7;margin-bottom:6px}\n.fc-data sup{font-size:9px;color:var(--text5);cursor:pointer;margin:0 1px}\n.fc-data sup:hover{color:#60a5fa;text-decoration:underline}\n.fc-signals{font-size:10px;color:var(--text4);margin-bottom:8px;line-height:1.5;max-height:3em;overflow:hidden}\n.fc-detail{font-size:11px;color:#60a5fa;cursor:pointer;font-weight:500}\n.fc-detail:hover{text-decoration:underline}\n.ft-source-block{margin-top:20px;padding:14px 16px;background:var(--bg3);border:1px solid var(--border);border-radius:10px}\n.ft-source-title{font-size:12px;font-weight:600;color:var(--text2);margin-bottom:8px}\n.ft-source-item{font-size:11px;color:var(--text4);line-height:1.8}\n.ft-source-item a{color:#60a5fa;text-decoration:none}\n.ft-source-item a:hover{text-decoration:underline}\n.ft-layer-section{margin-bottom:16px}\n.ft-layer-title{font-size:13px;font-weight:600;color:var(--text);margin-bottom:6px}\n.ft-layer-desc{font-size:12px;color:var(--text3);line-height:1.8;margin-bottom:8px}\n.ft-table{width:100%;border-collapse:collapse;margin:8px 0;font-size:11px}\n.ft-table td{padding:5px 10px;border-bottom:1px solid var(--border);color:var(--text3)}\n.ft-table td:first-child{color:var(--text4);width:120px}\n.ft-table td sup{font-size:9px;color:var(--text5);cursor:pointer}\n.ft-table td sup:hover{color:#60a5fa}\n@media(max-width:1200px){.fund-card{width:calc(33.33% - 9.33px)}}\n@media(max-width:900px){.fund-card{width:calc(50% - 7px)}}\n@media(max-width:600px){.fund-card{width:100%;min-width:auto}}\n'
    prefix = prefix.replace('</style>', tab_css + '\n</style>', 1)
    
    # Title
    prefix = prefix.replace('期货品种加权指数 · 双维分类矩阵', '期货品种看板')
    
    # Tabs
    # 用正则匹配动态品种子符和日期，避免硬编码失效
    sub_re = re.compile(r'(<div class="sub">上表：历史分位矩阵.*?</div>)')
    m = sub_re.search(prefix)
    if m:
        old_sub = m.group(1)
        new_sub = '<div class="tabs">\n<button class="tab-btn active" onclick="switchTab(\'matrix\')">📊 双维分类</button>\n<button class="tab-btn" onclick="switchTab(\'fundamentals\')">📈 基本面跟踪</button>\n</div>\n</div>'
        prefix = prefix.replace(m.group(1), old_sub.replace('</div>', '') + new_sub)
    # 修复日期（用正则匹配任意日期）
    prefix = re.sub(r'数据更新: \d{4}-\d{2}-\d{2}', f'数据更新: {fd["updated_at"]}', prefix)
    
    # Wrap matrix
    matrix = '<div class="tab-content active" id="tab-matrix">\n' + matrix
    matrix = re.sub(r'更新: \d{4}-\d{2}-\d{2}', f'更新: {fd["updated_at"]}', matrix)
    
    # Fundamentals tab
    ft_html = '</div>\n<div class="tab-content" id="tab-fundamentals">\n<div class="ft-header">\n<div><span style="font-size:18px;font-weight:600;color:var(--text)">📊 基本面跟踪</span>\n<span class="ft-date"> · 数据更新: ' + fd['updated_at'] + '</span></div>\n<div class="ft-actions">\n<button class="ft-btn" onclick="var gs=document.querySelectorAll(\'.cat-group\');gs.forEach(function(g){g.classList.add(\'open\')})">展开全部</button>\n<button class="ft-btn" onclick="var gs=document.querySelectorAll(\'.cat-group\');gs.forEach(function(g){g.classList.remove(\'open\')})">收起全部</button>\n</div></div>\n<div id="ft-container"><div class="no-chart">点击「展开全部」加载基本面数据</div></div>\n</div>\n\n'
    matrix += ft_html
    
    # Fund JS (no <script> wrapper)
    fund_js = '\nfunction switchTab(tab){\ndocument.querySelectorAll(".tab-btn").forEach(function(b){b.classList.remove("active")});\ndocument.querySelectorAll(".tab-content").forEach(function(c){c.classList.remove("active")});\ndocument.querySelectorAll(".tab-btn").forEach(function(b){if(b.textContent.indexOf(tab==="matrix"?"双维分类":"基本面跟踪")>=0)b.classList.add("active")});\ndocument.getElementById("tab-"+tab).classList.add("active");\nif(tab==="fundamentals")initFundamentals();\n}\nvar _fd=null,_fi=false;\nfunction initFundamentals(){\nif(_fi)return;_fi=true;\nvar c=document.getElementById("ft-container");if(!c)return;\n_fd=' + fd_json + ';\nvar h="",cats={},order=["黑色系","有色金属","能源化工","农产品","贵金属"];\nfor(var k in _fd.varieties){var v=_fd.varieties[k],cat=v.category;if(!cats[cat])cats[cat]=[];cats[cat].push(v);}\nfor(var i=0;i<order.length;i++){\nvar cn=order[i],vs=cats[cn]||[];if(!vs.length)continue;\nvar up=0,dn=0,neu=0;\nvs.forEach(function(v){var j=v.overall.judgment;if(j.indexOf("偏多")>=0)up++;else if(j.indexOf("偏空")>=0)dn++;else neu++;});\nh+="<div class=\\"cat-group\\" id=\\"cat-"+i+"\\">";\nh+="<div class=\\"cat-header\\" onclick=\\"toggleCat("+i+")\\">";\nh+="<div class=\\"cat-title\\">"+cn+"<span style=\\"font-size:10px;color:var(--text4)\\">"+vs.length+"个品种</span></div>";\nh+="<div class=\\"cat-stats\\">";\nh+="<span class=\\"cat-stat\\"><span class=\\"cat-stat-dot up\\"></span>偏多 "+up+"</span>";\nh+="<span class=\\"cat-stat\\"><span class=\\"cat-stat-dot neu\\"></span>中性 "+neu+"</span>";\nh+="<span class=\\"cat-stat\\"><span class=\\"cat-stat-dot dn\\"></span>偏空 "+dn+"</span>";\nh+="</div><span class=\\"cat-arrow\\">▶</span></div>";\nh+="<div class=\\"cat-body\\">";\nvs.forEach(function(v){h+=buildCard(v);});\nh+="</div></div>";\n}\nh+="<div class=\\"fn\\" style=\\"margin-top:16px\\">数据基于本地K线数据库（2009年以来4168个交易日）计算 · 部分宏观数据来自国家统计局及交易所公开信息 · 分析框架：四层漏斗 · 更新："+_fd.updated_at+"</div>";\nc.innerHTML=h;\n}\nfunction buildCard(v){\nvar j=v.overall.judgment,jc="neutral",ji="➡️";\nif(j.indexOf("偏多")>=0){jc="bull";ji="📈";}else if(j.indexOf("偏空")>=0){jc="bear";ji="📉";}\nvar h="<div class=\\"fund-card "+jc+"\\" onclick=\\"showFundDetail(\'"+v.code+"\')\\">";\nh+="<div class=\\"fc-name\\">"+ji+" "+v.name+"</div>";\nh+="<div class=\\"fc-code\\">"+v.code+" · ￥"+v.cur_price.toFixed(0)+" | 分位"+v.price_pct.toFixed(0)+"%</div>";\nh+="<div class=\\"fc-judgment "+jc+"\\">综合判断："+j+"</div>";\nh+="<div class=\\"fc-layers\\">"+layerBadge(1,v.layer1.direction)+layerBadge(2,v.layer2.direction)+layerBadge(3,v.layer3.direction)+layerBadge(4,v.layer4.direction)+"</div>";\nh+="<div class=\\"fc-signals\\">"+(v.layer1.description||"").substring(0,80)+"…</div>";\nh+="<span class=\\"fc-detail\\" onclick=\\"event.stopPropagation();showFundDetail(\'"+v.code+"\')\\">查看完整分析 →</span></div>";\nreturn h;\n}\nfunction layerBadge(n,dir){var c="l"+n,d="L"+n+":"+dir.substring(0,2);if(dir.indexOf("偏多")>=0)c+="b";else if(dir.indexOf("偏空")>=0)c+="r";else c+="n";return "<span class=\\"fc-layer "+c+"\\">"+d+"</span>";}\nfunction toggleCat(i){var el=document.getElementById("cat-"+i);el.classList.toggle("open");}\nfunction showFundDetail(code){\nvar v=_fd.varieties[code];if(!v)return;\nvar h="<h2>"+v.name+" ("+v.code+") · 四层漏斗分析</h2>";\nh+="<div style=\\"font-size:13px;color:var(--text3);margin-bottom:16px\\">";\nvar j=v.overall.judgment,jc="#f59e0b";\nif(j.indexOf("偏多")>=0)jc="#ef4444";else if(j.indexOf("偏空")>=0)jc="#22c55e";\nh+="综合判断：<span style=\\"font-weight:700;color:"+jc+"\\">"+j+"</span> | 四层共振："+v.overall.resonance+" | 当前价 ￥"+v.cur_price.toFixed(0)+"（分位"+v.price_pct.toFixed(0)+"%）</div>";\nvar layers=[{name:"第一层：宏观周期与产业定位",l:v.layer1},{name:"第二层：供需平衡表与价格估值",l:v.layer2},{name:"第三层：现货层面实时验证",l:v.layer3},{name:"第四层：盘面结构与资金行为",l:v.layer4}];\nlayers.forEach(function(l){\nvar d=l.l.direction,dc="#f59e0b";if(d.indexOf("偏多")>=0)dc="#ef4444";else if(d.indexOf("偏空")>=0)dc="#22c55e";\nh+="<div class=\\"ft-layer-section\\">";\nh+="<div class=\\"ft-layer-title\\">"+l.name+" <span style=\\"color:"+dc+";font-size:12px\\">["+d+"]</span></div>";\nh+="<div class=\\"ft-layer-desc\\">"+(l.l.description||"")+"</div>";\nh+="<table class=\\"ft-table\\">";\nl.l.data.forEach(function(dd){h+="<tr><td>"+dd.label+"</td><td>"+dd.value+" <sup onclick=\\"openSource(\'"+dd.source+"\')\\">"+dd.source+"</sup></td></tr>";});\nh+="</table></div>";});\nh+="<div class=\\"ft-source-block\\"><div class=\\"ft-source-title\\">📚 数据来源</div>";\nfor(var s in _fd.sources){var so=_fd.sources[s];h+="<div class=\\"ft-source-item\\"><sup>"+s+"</sup> "+so.name;if(so.url)h+=" — <a href=\\""+so.url+"\\" target=\\"_blank\\" rel=\\"noopener\\">"+so.url+"</a>";if(so.note)h+=" ("+so.note+")";h+="</div>";}\nh+="</div>";\ndocument.getElementById("mt").innerHTML=v.name+" 基本面分析";\ndocument.getElementById("mb").innerHTML=h;\ndocument.getElementById("mo").classList.add("on");document.body.style.overflow="hidden";\n}\nvar _sourceUrls={"4":"https://data.stats.gov.cn/","8":"https://www.chinamoney.com.cn/","9":"https://www.wenhua.com.cn/","0":null};\nfunction openSource(s){var u=_sourceUrls[s];if(u)window.open(u,"_blank","noopener");}\n'
    
    tail = tail.replace('</script>\n<script src="stats.js">',
        '</script>\n<script>\n' + fund_js + '\n</script>\n<script src="stats.js">')
    
    result = prefix + matrix + tail
    
    with open(HTML_FILE, 'w') as f:
        f.write(result)
    
    print(f'✅ 基本面Tab已注入: {len(result):,} bytes')
    return True


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--data-only':
        fd, today = gen_fundamentals()
        print(f'✅ fundamentals_data.json 已生成: {len(fd["varieties"])}品种, {today}')
    else:
        fd, today = gen_fundamentals()
        print(f'✅ 基本面数据: {len(fd["varieties"])}品种, {today}')
        inject_into_html()
