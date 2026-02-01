"""
数据库模型定义
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

Base = declarative_base()

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'fund_monitor.db')
# 确保data目录存在
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# 创建数据库引擎
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)


class Fund(Base):
    """基金模型"""
    __tablename__ = 'funds'

    id = Column(Integer, primary_key=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联持仓股票
    holdings = relationship("Holding", back_populates="fund", cascade="all, delete-orphan")
    # 关联历史数据
    histories = relationship("FundHistory", back_populates="fund", cascade="all, delete-orphan")


class Stock(Base):
    """股票模型"""
    __tablename__ = 'stocks'

    id = Column(Integer, primary_key=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    # 关联持仓
    holdings = relationship("Holding", back_populates="stock")


class Holding(Base):
    """基金持仓模型"""
    __tablename__ = 'holdings'

    id = Column(Integer, primary_key=True)
    fund_id = Column(Integer, ForeignKey('funds.id'), nullable=False)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False)
    ratio = Column(Float, nullable=False)  # 持仓占比（百分比）
    created_at = Column(DateTime, default=datetime.now)

    # 关联
    fund = relationship("Fund", back_populates="holdings")
    stock = relationship("Stock", back_populates="holdings")


class FundHistory(Base):
    """基金历史数据模型"""
    __tablename__ = 'fund_histories'

    id = Column(Integer, primary_key=True)
    fund_id = Column(Integer, ForeignKey('funds.id'), nullable=False)
    estimated_change = Column(Float, nullable=False)  # 预估涨跌幅（百分比）
    timestamp = Column(DateTime, default=datetime.now, index=True)

    # 关联
    fund = relationship("Fund", back_populates="histories")


class StockPrice(Base):
    """股票价格历史模型"""
    __tablename__ = 'stock_prices'

    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False)
    price = Column(Float, nullable=False)  # 当前价格
    prev_close = Column(Float, nullable=False)  # 昨日收盘价
    change_percent = Column(Float, nullable=False)  # 涨跌幅（百分比）
    timestamp = Column(DateTime, default=datetime.now, index=True)


def init_db():
    """初始化数据库"""
    Base.metadata.create_all(engine)
    print(f"数据库已初始化: {DB_PATH}")


def get_session():
    """获取数据库会话"""
    return Session()
