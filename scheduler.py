"""
定时任务调度器
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging

from models import get_session, Fund, Holding, Stock, FundHistory, StockPrice
from api import StockDataFetcher, calculate_fund_change

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FundMonitorScheduler:
    """基金监控定时任务调度器"""

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone='Asia/Shanghai')

    def start(self):
        """启动调度器"""
        # 每5分钟执行一次数据更新
        self.scheduler.add_job(
            func=self.update_fund_data,
            trigger=IntervalTrigger(minutes=5),
            id='update_fund_data',
            name='更新基金数据',
            replace_existing=True
        )

        # 立即执行一次
        self.update_fund_data()

        self.scheduler.start()
        logger.info("定时任务调度器已启动，每5分钟自动更新基金数据")

    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        logger.info("定时任务调度器已停止")

    def update_fund_data(self):
        """更新基金数据（定时任务核心逻辑）"""
        logger.info(f"开始更新基金数据 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        session = get_session()
        try:
            # 获取所有基金
            funds = session.query(Fund).all()

            if not funds:
                logger.info("暂无基金需要监控")
                return

            # 收集所有需要查询的股票代码
            all_stock_codes = set()
            fund_stock_map = {}  # 基金ID -> 持仓股票列表

            for fund in funds:
                holdings = session.query(Holding).filter(Holding.fund_id == fund.id).all()

                stock_list = []
                for holding in holdings:
                    stock = session.query(Stock).get(holding.stock_id)
                    if stock:
                        all_stock_codes.add(stock.code)
                        stock_list.append({
                            'code': stock.code,
                            'ratio': holding.ratio
                        })

                fund_stock_map[fund.id] = stock_list

            if not all_stock_codes:
                logger.info("没有持仓股票需要查询")
                return

            # 批量获取股票实时行情
            logger.info(f"查询 {len(all_stock_codes)} 只股票的实时行情")
            stock_prices = StockDataFetcher.get_stock_realtime_batch(list(all_stock_codes))

            if not stock_prices:
                logger.warning("未能获取到任何股票行情数据")
                return

            logger.info(f"成功获取 {len(stock_prices)} 只股票的行情数据")

            # 为每只基金计算预估涨跌幅
            for fund in funds:
                fund_id = fund.id
                stock_list = fund_stock_map.get(fund_id, [])

                if not stock_list:
                    continue

                # 计算基金预估涨跌幅
                estimated_change = calculate_fund_change(stock_list, stock_prices)

                logger.info(f"基金 {fund.code} ({fund.name}) 预估涨跌: {estimated_change:.2f}%")

                # 保存历史数据
                history = FundHistory(
                    fund_id=fund_id,
                    estimated_change=estimated_change
                )
                session.add(history)

                # 保存股票价格历史
                for holding in stock_list:
                    stock_code = holding['code']
                    if stock_code in stock_prices:
                        stock_price = stock_prices[stock_code]
                        stock = session.query(Stock).filter(Stock.code == stock_code).first()

                        if stock:
                            price_record = StockPrice(
                                stock_id=stock.id,
                                price=stock_price['price'],
                                prev_close=stock_price['prev_close'],
                                change_percent=stock_price['change_percent']
                            )
                            session.add(price_record)

            session.commit()
            logger.info("基金数据更新完成")

        except Exception as e:
            logger.error(f"更新基金数据时出错: {e}")
            session.rollback()
        finally:
            session.close()


# 全局调度器实例
scheduler = None


def start_scheduler():
    """启动全局调度器"""
    global scheduler
    if scheduler is None:
        scheduler = FundMonitorScheduler()
        scheduler.start()
    return scheduler


def stop_scheduler():
    """停止全局调度器"""
    global scheduler
    if scheduler is not None:
        scheduler.stop()
        scheduler = None
