# scheduler_service.py
# 定时任务服务

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import time
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session
from models import get_session, Fund, Stock, Holding, FundHistory, StockPrice, SystemConfig, init_db
from fetcher import StockFetcher

from log_utils import log

_scheduler_instance = None
DEFAULT_INTERVAL = 60 # seconds

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
            log("交易时间，执行全量更新...")
            _perform_update(session)
        else:
            # 非交易时间
            if current_time > end_pm:
                # 15:00 以后，逐个检查基金是否已有今日收盘数据
                all_funds = session.query(Fund).all()
                target_funds = []
                
                # 构造今日15:00的时间点
                close_time = datetime.combine(now.date(), end_pm)
                
                for f in all_funds:
                    # 检查该基金在收盘后是否有记录
                    exists = session.query(FundHistory)\
                        .filter(FundHistory.fund_id == f.id)\
                        .filter(FundHistory.timestamp >= close_time)\
                        .first()
                    
                    if not exists:
                        target_funds.append(f)
                
                if target_funds:
                    log(f"发现 {len(target_funds)} 个基金需要补全收盘数据...")
                    _perform_update(session, target_funds)
                else:
                    log("所有基金已有收盘数据，跳过更新.")
            else:
                # 9:30 之前或 11:30-13:00，跳过
                log("非交易时间(盘前或午休)，跳过更新.")
                
    except Exception as e:
        log(f"定时任务异常: {e}")
    finally:
        session.close()

def _perform_update(session: Session, target_funds: list = None):
    """
    执行具体的数据更新逻辑
    :param target_funds: 指定要更新的基金列表，如果为None则更新所有
    """
    # 1. 获取目标基金
    if target_funds is None:
        funds = session.query(Fund).all()
    else:
        funds = target_funds
        
    if not funds:
        return

    # 2. 收集所有需要的股票代码
    all_stock_codes = set()
    fund_holdings_map = {} # {fund_id: [(stock_code, ratio), ...]}
    
    for fund in funds:
        holdings = fund.holdings
        h_list = []
        for h in holdings:
            # h.stock 可能未加载
            stock = session.get(Stock, h.stock_id) # Replace query.get with session.get
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
    
    # 5. 更新股票价格历史 (只存本次涉及到的股票)
    for code, data in price_map.items():
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
    log(f"为 {len(funds)} 个基金 更新数据完成.")

def start_scheduler():
    global _scheduler_instance
    init_db() # 确保库存在
    
    # 从数据库读取配置
    interval = DEFAULT_INTERVAL
    session = get_session()
    try:
        config = session.query(SystemConfig).filter_by(key='update_interval').first()
        if config:
            try:
                val = int(config.value)
                # 迁移逻辑：如果值很小（例如 < 30），认为是旧的分钟单位，自动转换为秒
                if val < 30:
                    val = val * 60
                
                interval = val
            except: pass
    finally:
        session.close()
            
    # 安全兜底
    if interval < 30:
        interval = 30
            
    log(f"启动定时任务，当前间隔: {interval} 秒")

    scheduler = BackgroundScheduler()
    # 改为 seconds
    scheduler.add_job(update_job, 'interval', seconds=interval, id='update_job', next_run_time=datetime.now())
    scheduler.start()
    
    _scheduler_instance = scheduler
    return scheduler

def change_interval(seconds: int):
    """修改定时任务间隔"""
    global _scheduler_instance
    if not _scheduler_instance:
        return False, "Scheduler not running"
    
    if seconds < 30:
        seconds = 30
        
    try:
        _scheduler_instance.reschedule_job('update_job', trigger='interval', seconds=seconds)
        
        # 持久化
        session = get_session()
        try:
            config = session.query(SystemConfig).filter_by(key='update_interval').first()
            if not config:
                config = SystemConfig(key='update_interval', value=str(seconds))
                session.add(config)
            else:
                config.value = str(seconds)
            session.commit()
        finally:
            session.close()
            
        return True, f"已调整更新频率为 {seconds} 秒/次"
    except Exception as e:
        return False, str(e)
