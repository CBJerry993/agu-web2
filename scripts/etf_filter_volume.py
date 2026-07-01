# encoding:gbk
"""
ETF 成交额过滤脚本 — 过滤掉日成交额 < MIN_AMOUNT 的不活跃 ETF
用法：直接在国信iQuant中运行此脚本
"""
import time

MIN_AMOUNT = 2000000  # 最小日成交额：200万

def init(ContextInfo):
    # 完整 ETF 列表（与主策略一致）
    ContextInfo.raw_codes_yi = [
        "159001", "159105", "159121", "159138", "159140", "159150", "159175", "159181", "159191", "159196",
        "159222", "159255", "159259", "159263", "159299", "159311", "159316", "159328", "159361", "159369",
        "159530", "159532", "159540", "159545", "159558", "159565", "159566", "159572", "159597", "159606",
        "159633", "159686", "159696", "159715", "159781", "159787", "159788", "159798", "159807", "159819",
        "159837", "159847", "159895", "159901", "159915", "159934", "161115", "161116", "161117", "161118",
        "161119", "161121", "161122", "161123", "161124", "161125", "161126", "161127", "161128", "161129",
        "161130", "161131", "161132", "161133", "180105", "180605", "501203", "501222", "502003", "502006",
        "502010", "502048", "506002", "508033", "510100", "510130", "510310", "510580", "510900", "511110",
        "511800", "512010", "512030", "512070", "512090", "512560", "512570", "513000", "513010", "513040",
        "513050", "513070", "513090", "513200", "513210", "513320", "513850", "515110", "515180", "515810",
        "516070", "516080", "516090", "516310", "516350", "516510", "516570", "516590", "517010", "517030",
        "517330", "520810", "520850", "520870", "530060", "530100", "530180", "530380", "551500", "560160",
        "560370", "560390", "562900", "562910", "562920", "562930", "562950", "562960", "562970", "562990",
        "563000", "563010", "563020", "563030", "563050", "563060", "563080", "563090", "563510", "563530",
        "563600", "563700", "588020", "588080", "588210", "588270", "588500", "588550", "588730", "589030",
        "589130", "589800", "589960"
    ]

    ContextInfo.raw_codes_other = [
        "513310", "159866", "513080", "513030", "159687", "520830", "159329", "159941", "159561", "159529", "159518"
    ]

    # 转换为带市场后缀的标的
    stocks_yi = [c + ".SZ" if c[0] in "1" else c + ".SH" for c in ContextInfo.raw_codes_yi]
    stocks_other = [c + ".SZ" if c[0] in "1" else c + ".SH" for c in ContextInfo.raw_codes_other]
    all_stocks = stocks_yi + stocks_other

    # 订阅所有标的
    ContextInfo.set_universe(all_stocks)
    print(">>> 已订阅 {} 只ETF，开始查询成交额...".format(len(all_stocks)))


def handlebar(ContextInfo):
    """只运行一次，获取最新日线成交额数据"""
    if not ContextInfo.is_last_bar():
        return

    all_codes = list(ContextInfo.universe)

    # 用 get_market_data 获取日线数据（注意：不带 _ex）
    # fields: amount(成交额), close(收盘价)
    try:
        df = ContextInfo.get_market_data(
            ['amount', 'close'],
            all_codes,
            period='1d',
            count=1,
            dividend_type='none',
            fill_data=True
        )
    except Exception as e:
        print("[ERROR] get_market_data 失败: {}".format(e))
        print("[提示] 尝试使用 get_history_data 替代...")
        return

    keep_list = []   # 保留（活跃）
    remove_list = [] # 剔除（不活跃）

    print("\n" + "=" * 80)
    print("  ETF 成交额过滤结果（阈值: {}万）".format(MIN_AMOUNT / 10000))
    print("=" * 80)

    for code in all_codes:
        if code not in df or df[code].empty:
            continue

        amount_val = float(df[code]['amount'].iloc[-1])  # 最新成交额（元）
        close_val = float(df[code]['close'].iloc[-1])
        name = ContextInfo.get_stock_name(code) or ""
        amount_wan = amount_val / 10000  # 转为万元

        info = {
            'code': code[:6],
            'name': name,
            'amount': amount_wan,
            'close': close_val
        }

        if amount_val >= MIN_AMOUNT:
            keep_list.append(info)
        else:
            remove_list.append(info)

    # 按成交额排序
    keep_list.sort(key=lambda x: x['amount'], reverse=True)
    remove_list.sort(key=lambda x: x['amount'], reverse=True)

    # 打印结果
    print("\n【保留】共{}只（活跃，日成交额>= {}万）:".format(len(keep_list), MIN_AMOUNT / 10000))
    print("{:<8} {:<22} {:>12} {:>10}".format("代码", "名称", "成交额(万)", "收盘价"))
    print("-" * 55)
    for item in keep_list:
        print("{:<8} {:<22} {:>12.2f} {:>10.4f}".format(
            item['code'], item['name'], item['amount'], item['close']
        ))

    print("\n【剔除】共{}只（不活跃，日成交额< {}万）:".format(len(remove_list), MIN_AMOUNT / 10000))
    print("{:<8} {:<22} {:>12} {:>10}".format("代码", "名称", "成交额(万)", "收盘价"))
    print("-" * 55)
    for item in remove_list:
        print("{:<8} {:<22} {:>12.2f} {:>10.4f}".format(
            item['code'], item['name'], item['amount'], item['close']
        ))

    print("\n" + "=" * 80)
    print("  总计: {}只 | 保留: {}只 | 剔除: {}只".format(
        len(keep_list) + len(remove_list), len(keep_list), len(remove_list)))
    print("=" * 80)

    # 输出保留的代码列表（方便复制到主策略）
    yi_keep = [item['code'] for item in keep_list if item['code'] in [c[:6] for c in ContextInfo.raw_codes_yi]]
    other_keep = [item['code'] for item in keep_list if item['code'] in [c[:6] for c in ContextInfo.raw_codes_other]]

    print("\n--- 易方达保留代码 ---")
    print(",".join(yi_keep))
    print("\n--- 其他品牌保留代码 ---")
    print(",".join(other_keep))
