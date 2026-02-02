# models.py
# 数据库模型定义

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import os

Base = declarative_base()

# 数据库路径：data/fund_monitor.db
DB_DIR = os.path.join(os.path.dirname(__file__), 'data')
DB_PATH = os.path.join(DB_DIR, 'fund_monitor.db')

# 确保data目录存在
os.makedirs(DB_DIR, exist_ok=True)

# 创建数据库引擎
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)

class Fund(Base):
    """基金信息表"""
    __tablename__ = 'funds'

    id = Column(Integer, primary_key=True)
    code = Column(String(10), unique=True, nullable=False, index=True) # 基金代码
    name = Column(String(100), nullable=False) # 基金名称
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    holdings = relationship("Holding", back_populates="fund", cascade="all, delete-orphan")
    histories = relationship("FundHistory", back_populates="fund", cascade="all, delete-orphan")

class Stock(Base):
    """股票信息表"""
    __tablename__ = 'stocks'

    id = Column(Integer, primary_key=True)
    code = Column(String(10), unique=True, nullable=False, index=True) # 股票代码 (如 000001, 600519)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    # 关联
    holdings = relationship("Holding", back_populates="stock")
    prices = relationship("StockPrice", back_populates="stock")

class Holding(Base):
    """基金持仓关联表 (只存前十大重仓)"""
    __tablename__ = 'holdings'

    id = Column(Integer, primary_key=True)
    fund_id = Column(Integer, ForeignKey('funds.id'), nullable=False)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False)
    ratio = Column(Float, nullable=False)  # 持仓占比 (0.05 代表 5%)
    created_at = Column(DateTime, default=datetime.now)

    fund = relationship("Fund", back_populates="holdings")
    stock = relationship("Stock", back_populates="holdings")

class FundHistory(Base):
    """基金历史估值记录 (每5分钟一条)"""
    __tablename__ = 'fund_histories'

    id = Column(Integer, primary_key=True)
    fund_id = Column(Integer, ForeignKey('funds.id'), nullable=False)
    estimated_change = Column(Float, nullable=False)  # 预估涨跌幅 (百分比)
    timestamp = Column(DateTime, default=datetime.now, index=True)

    fund = relationship("Fund", back_populates="histories")

class StockPrice(Base):
    """股票价格历史 (可选，用于回溯计算)"""
    __tablename__ = 'stock_prices'

    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False)
    price = Column(Float, nullable=False)
    prev_close = Column(Float, nullable=False)
    change_percent = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    
    stock = relationship("Stock", back_populates="prices")

def init_db():
    """初始化数据库表结构"""
    Base.metadata.create_all(engine)
    print(f"数据库初始化完成: {DB_PATH}")

def get_session():
    return Session()
