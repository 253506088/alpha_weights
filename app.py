"""
Flask 应用主程序
"""
from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta

from models import init_db, get_session, Fund, Holding, Stock, FundHistory
from api import FundDataFetcher, StockDataFetcher, calculate_fund_change
from scheduler import start_scheduler

# 创建Flask应用
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


# 初始化数据库
try:
    init_db()
except Exception as e:
    print(f"数据库初始化警告: {e}")


# 启动定时任务
try:
    start_scheduler()
except Exception as e:
    print(f"定时任务启动警告: {e}")


@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')


@app.route('/api/funds', methods=['GET'])
def get_funds():
    """获取所有基金列表"""
    session = get_session()
    try:
        funds = session.query(Fund).order_by(Fund.created_at.desc()).all()

        result = []
        for fund in funds:
            # 获取最新的历史数据
            latest_history = session.query(FundHistory)\
                .filter(FundHistory.fund_id == fund.id)\
                .order_by(FundHistory.timestamp.desc())\
                .first()

            fund_info = {
                'id': fund.id,
                'code': fund.code,
                'name': fund.name,
                'created_at': fund.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': fund.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }

            if latest_history:
                fund_info['estimated_change'] = latest_history.estimated_change
                fund_info['last_update'] = latest_history.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            else:
                fund_info['estimated_change'] = None
                fund_info['last_update'] = None

            result.append(fund_info)

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取基金列表失败: {str(e)}'
        })
    finally:
        session.close()


@app.route('/api/funds', methods=['POST'])
def add_fund():
    """添加基金"""
    try:
        data = request.get_json()
        fund_code = data.get('code', '').strip()

        if not fund_code or len(fund_code) != 6 or not fund_code.isdigit():
            return jsonify({
                'success': False,
                'message': '请输入6位数字基金代码'
            })

        session = get_session()

        # 检查基金是否已存在
        existing_fund = session.query(Fund).filter(Fund.code == fund_code).first()
        if existing_fund:
            return jsonify({
                'success': False,
                'message': f'基金 {fund_code} 已存在'
            })

        # 从东方财富获取基金持仓信息
        fund_info = FundDataFetcher.get_fund_holdings(fund_code)

        if not fund_info:
            return jsonify({
                'success': False,
                'message': f'无法获取基金 {fund_code} 的信息，请检查基金代码'
            })

        # 创建基金记录
        fund = Fund(
            code=fund_info['code'],
            name=fund_info['name']
        )
        session.add(fund)
        session.flush()  # 获取fund.id

        # 创建持仓记录
        for holding_data in fund_info['holdings']:
            # 检查股票是否存在
            stock = session.query(Stock).filter(Stock.code == holding_data['code']).first()
            if not stock:
                stock = Stock(
                    code=holding_data['code'],
                    name=holding_data['name']
                )
                session.add(stock)
                session.flush()

            # 创建持仓记录
            holding = Holding(
                fund_id=fund.id,
                stock_id=stock.id,
                ratio=holding_data['ratio']
            )
            session.add(holding)

        session.commit()

        return jsonify({
            'success': True,
            'message': f'基金 {fund_info["name"]} 添加成功',
            'data': {
                'id': fund.id,
                'code': fund.code,
                'name': fund.name
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'添加基金失败: {str(e)}'
        })
    finally:
        session.close()


@app.route('/api/funds/<int:fund_id>', methods=['DELETE'])
def delete_fund(fund_id):
    """删除基金"""
    session = get_session()
    try:
        fund = session.query(Fund).get(fund_id)
        if not fund:
            return jsonify({
                'success': False,
                'message': '基金不存在'
            })

        fund_code = fund.code
        fund_name = fund.name

        session.delete(fund)
        session.commit()

        return jsonify({
            'success': True,
            'message': f'基金 {fund_name} ({fund_code}) 已删除'
        })

    except Exception as e:
        session.rollback()
        return jsonify({
            'success': False,
            'message': f'删除基金失败: {str(e)}'
        })
    finally:
        session.close()


@app.route('/api/funds/<int:fund_id>/history')
def get_fund_history(fund_id):
    """获取基金历史数据（用于绘制走势图）"""
    session = get_session()
    try:
        fund = session.query(Fund).get(fund_id)
        if not fund:
            return jsonify({
                'success': False,
                'message': '基金不存在'
            })

        # 获取今天的历史数据
        today = datetime.now().date()
        start_time = datetime.combine(today, datetime.min.time())

        histories = session.query(FundHistory)\
            .filter(FundHistory.fund_id == fund_id)\
            .filter(FundHistory.timestamp >= start_time)\
            .order_by(FundHistory.timestamp.asc())\
            .all()

        result = []
        for history in histories:
            result.append({
                'timestamp': history.timestamp.strftime('%H:%M:%S'),
                'estimated_change': history.estimated_change
            })

        return jsonify({
            'success': True,
            'data': result,
            'fund_name': fund.name,
            'fund_code': fund.code
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取历史数据失败: {str(e)}'
        })
    finally:
        session.close()


@app.route('/api/funds/<int:fund_id>/holdings')
def get_fund_holdings(fund_id):
    """获取基金持仓详情"""
    session = get_session()
    try:
        fund = session.query(Fund).get(fund_id)
        if not fund:
            return jsonify({
                'success': False,
                'message': '基金不存在'
            })

        holdings = session.query(Holding).filter(Holding.fund_id == fund_id).all()

        result = []
        for holding in holdings:
            stock = session.query(Stock).get(holding.stock_id)
            if stock:
                result.append({
                    'code': stock.code,
                    'name': stock.name,
                    'ratio': round(holding.ratio * 100, 2)  # 转换为百分比
                })

        # 按持仓占比降序排序
        result.sort(key=lambda x: x['ratio'], reverse=True)

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取持仓数据失败: {str(e)}'
        })
    finally:
        session.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
