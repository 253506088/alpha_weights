# scheduler_service.py
# 定时任务服务

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import time
from sqlalchemy.orm import Session
from models import get_session, Fund, Stock, Holding, FundHistory, StockPrice, init_db
from fetcher import StockFetcher

def update_job():
    """核数据更新任务"""
    now = datetime.now()
    current_time = now.time()
    
    # 定义时间范围
    start_vm = datetime.strptime("09:30:00", "%H:%M:%S").time()
    end_vm = datetime.strptime("11:30:00", "%H:%M:%S").time()
    start_pm = datetime.strptime("13:00:00", "%H:%M:%S").time()
    end_pm = datetime.strptime("15:00:00", "%H:%M:%S").time()
    
    is_trading = (start_vm <= current_time <= end_vm) or (start_pm <= current_time <= end_pm)
    
    session = get_session()
    try:
        if is_trading:
            print(f"[{now}] 交易时间，执行更新...")
            _perform_update(session)
        else:
            # 非交易时间
            if current_time > end_pm:
                # 15:00 以后，检查今日是否已存档收盘数据
                # 这里的逻辑是：如果今天(Now.date)已经有一条 15:00 之后的数据，就不再更新
                
                # 获取数据库中最新的历史记录时间
                last_record = session.query(FundHistory).order_by(FundHistory.timestamp.desc()).first()
                
                need_update = True
                if last_record:
                    is_today = last_record.timestamp.date() == now.date()
                    is_after_close = last_record.timestamp.time() >= end_pm
                    if is_today and is_after_close:
                        need_update = False
                
                if need_update:
                    print(f"[{now}] 收盘后补全收盘数据...")
                    _perform_update(session)
                else:
                    print(f"[{now}] 已有收盘数据，跳过更新.")
            else:
                # 9:30 之前或 11:30-13:00，跳过
                print(f"[{now}] 非交易时间(盘前或午休)，跳过更新.")
                
    except Exception as e:
        print(f"定时任务异常: {e}")
    finally:
        session.close()

def _perform_update(session: Session):
    """执行具体的数据更新逻辑"""
    # 1. 获取所有基金
    funds = session.query(Fund).all()
    if not funds:
        return

    # 2. 收集所有需要的股票代码
    all_stock_codes = set()
    fund_holdings_map = {} # {fund_id: [(stock_code, ratio), ...]}
    
    for fund in funds:
        holdings = fund.holdings
        h_list = []
        for h in holdings:
            # h.stock 是对象，我们需要 code
            # 此时 h.stock 可能未加载（lazy loading），小心 N+1
            # 只有当 h.stock_id 存在时
            stock = session.query(Stock).get(h.stock_id)
            if stock:
                all_stock_codes.add(stock.code)
                h_list.append((stock.code, h.ratio))
        fund_holdings_map[fund.id] = h_list

    if not all_stock_codes:
        return

    # 3. 批量获取股票行情
    price_map = StockFetcher.get_batch_prices(list(all_stock_codes))
    if not price_map:
        return # 网络错误或无数据

    # 4. 计算每个基金的涨跌幅并存储
    timestamp = datetime.now()
    
    for fund in funds:
        h_list = fund_holdings_map.get(fund.id, [])
        est_change = 0.0
        
        for code, ratio in h_list:
            p_data = price_map.get(code)
            if p_data:
                # 涨跌幅 * 占比
                est_change += p_data['pct'] * ratio
        
        # 存入历史表
        history = FundHistory(
            fund_id = fund.id,
            estimated_change = round(est_change, 2),
            timestamp = timestamp
        )
        session.add(history)
    
    # 5. 更新股票价格历史(可选，如果需要股票维度的历史)
    # 鉴于需求主要看基金，这里可以简单只存，为了性能也可以不存，
    # 但原来的models设计里有StockPrice，我们顺手存一下最新的
    for code, data in price_map.items():
        # 找到stock对象
        stock = session.query(Stock).filter_by(code=code).first()
        if stock:
            sp = StockPrice(
                stock_id = stock.id,
                price = data['price'],
                prev_close = data['prev_close'],
                change_percent = data['pct'],
                timestamp = timestamp
            )
            session.add(sp)
            
    session.commit()
    print("数据更新完成.")

def start_scheduler():
    init_db() # 确保库存在
    scheduler = BackgroundScheduler()
    # 每5分钟执行一次
    scheduler.add_job(update_job, 'interval', minutes=5, next_run_time=datetime.now())
    scheduler.start()
    return scheduler
