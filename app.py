# app.py
# Web 应用入口

from flask import Flask, render_template, request, jsonify
from models import get_session, Fund, Stock, Holding, FundHistory, StockPrice, init_db
from fetcher import FundFetcher
from scheduler_service import start_scheduler
from datetime import datetime, date

app = Flask(__name__)

# 启动定时任务
scheduler = start_scheduler()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/fund/add', methods=['POST'])
def add_fund():
    code = request.json.get('code')
    if not code or len(code) != 6:
        return jsonify({'success': False, 'message': '请输入6位基金代码'})
    
    session = get_session()
    try:
        # 查重
        exists = session.query(Fund).filter_by(code=code).first()
        if exists:
            return jsonify({'success': False, 'message': '该基金已存在'})

        # 获取数据
        data = FundFetcher.get_fund_details(code)
        if not data:
            return jsonify({'success': False, 'message': '无法获取基金信息，请确认代码是否正确'})
        
        # 保存基金
        fund = Fund(code=data['code'], name=data['name'])
        session.add(fund)
        session.flush() # 获取ID
        
        # 保存持仓
        for item in data['holdings']:
            # item: {code, name, ratio}
            stock_code = item['code']
            stock_name = item['name']
            ratio = item['ratio']
            
            # 查找或创建 Stock
            stock = session.query(Stock).filter_by(code=stock_code).first()
            if not stock:
                stock = Stock(code=stock_code, name=stock_name)
                session.add(stock)
                session.flush()
            
            # 创建关联
            holding = Holding(fund_id=fund.id, stock_id=stock.id, ratio=ratio)
            session.add(holding)
            
        session.commit()
        return jsonify({'success': True, 'message': f"成功添加: {data['name']}"})
        
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        session.close()

@app.route('/api/fund/refresh_holdings', methods=['POST'])
def refresh_fund_holdings():
    """手动更新某个基金的持仓信息"""
    fund_id = request.json.get('id')
    code = request.json.get('code')
    
    session = get_session()
    try:
        fund = None
        if fund_id:
            fund = session.get(Fund, fund_id)
        elif code:
            fund = session.query(Fund).filter_by(code=code).first()
            
        if not fund:
            return jsonify({'success': False, 'message': '未找到该基金'})
            
        # 重新获取数据
        print(f"正在重新获取基金 {fund.code} 的持仓...")
        data = FundFetcher.get_fund_details(fund.code)
        if not data:
            return jsonify({'success': False, 'message': '无法从外部接口获取数据'})
            
        # 更新名称
        if data.get('name') and data['name'] != f"基金{fund.code}":
            fund.name = data['name']
            
        # 只有当抓取到持仓时才更新
        if data.get('holdings'):
             # 清除旧持仓
            session.query(Holding).filter_by(fund_id=fund.id).delete()
            
            # 写入新持仓
            for item in data['holdings']:
                stock_code = item['code']
                stock_name = item['name']
                ratio = item['ratio']
                
                # 查找或创建 Stock
                stock = session.query(Stock).filter_by(code=stock_code).first()
                if not stock:
                    stock = Stock(code=stock_code, name=stock_name)
                    session.add(stock)
                    session.flush()
                
                # 创建关联
                holding = Holding(fund_id=fund.id, stock_id=stock.id, ratio=ratio)
                session.add(holding)
            
            session.commit()
            return jsonify({'success': True, 'message': f"成功更新持仓，共 {len(data['holdings'])} 只股票"})
        else:
            return jsonify({'success': False, 'message': '接口返回的持仓列表为空，未进行更新'})

    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        session.close()

@app.route('/api/fund/list', methods=['GET'])
def get_fund_list():
    session = get_session()
    try:
        funds = session.query(Fund).all()
        result = []
        for f in funds:
            # 获取最新估值
            last_hist = session.query(FundHistory)\
                .filter_by(fund_id=f.id)\
                .order_by(FundHistory.timestamp.desc())\
                .first()
            
            est_change = 0.0
            last_time = ""
            last_timestamp = None
            if last_hist:
                est_change = last_hist.estimated_change
                last_time = last_hist.timestamp.strftime("%H:%M")
                last_timestamp = last_hist.timestamp

            # 检查是否过期，例如如果是昨天的，今天开盘前显示0？
            # 暂时简单处理：如果是今天的数据才显示？或者一直显示最新一条
            # 需求通常希望看到最新的有效状态。如果过了一夜，可能希望看到昨收盘？
            # 既然有 update_time，前端自己判断
                
            result.append({
                'id': f.id,
                'code': f.code,
                'name': f.name,
                'est_change': est_change,
                'update_time': last_time
            })
        return jsonify({'success': True, 'data': result})
    finally:
        session.close()

@app.route('/api/fund/history/<int:fund_id>', methods=['GET'])
def get_fund_history(fund_id):
    session = get_session()
    try:
        # 只取当天的
        today = date.today()
        # Sqlite date compare needs care, try filtering by range
        start_of_day = datetime.combine(today, datetime.min.time())
        
        # 1.获取基金和它的持仓结构
        fund = session.get(Fund, fund_id)
        if not fund:
            return jsonify({'success': False, 'message': 'Fund not found'})
            
        # 预加载持仓，构建 stock_id -> {ratio, name} 映射
        holdings_map = {}
        for h in fund.holdings:
            # 确保stock加载
            s = session.get(Stock, h.stock_id) 
            if s:
                holdings_map[h.stock_id] = {
                    'code': s.code,
                    'name': s.name,
                    'ratio': h.ratio
                }
        
        stock_ids = list(holdings_map.keys())
        
        # 2. 获取基金估值历史
        histories = session.query(FundHistory)\
            .filter(FundHistory.fund_id == fund_id)\
            .filter(FundHistory.timestamp >= start_of_day)\
            .order_by(FundHistory.timestamp.asc())\
            .all()
            
        times = [h.timestamp.strftime("%H:%M") for h in histories]
        values = [h.estimated_change for h in histories]
        
        # 3. 获取对应的股票价格历史
        # 为了避免查询过多，我们查询 stock_id在列表中，且时间在今天的
        # 然后在内存里进行匹配
        stock_prices = session.query(StockPrice)\
            .filter(StockPrice.stock_id.in_(stock_ids))\
            .filter(StockPrice.timestamp >= start_of_day)\
            .all()
            
        # 将价格按 timestamp 分组: { timestamp_str: [price_record, ...] }
        # 注意 timestamp 需要和 history 里的完全匹配，或者我们用 strftime 匹配
        prices_by_time = {}
        for sp in stock_prices:
            t_str = sp.timestamp.strftime("%H:%M") # 分钟级匹配
            if t_str not in prices_by_time:
                prices_by_time[t_str] = []
            prices_by_time[t_str].append(sp)
            
        # 4. 构建每个时间点的详情
        details = []
        for h in histories:
            t_str = h.timestamp.strftime("%H:%M")
            point_detail = []
            
            # 找到这个时间点的所有股票价格
            sps = prices_by_time.get(t_str, [])
            
            for sp in sps:
                # 找到这只股票在基金里的权重信息
                h_info = holdings_map.get(sp.stock_id)
                if h_info:
                    point_detail.append({
                        'code': h_info['code'],
                        'name': h_info['name'],
                        'ratio': h_info['ratio'],
                        'pct': sp.change_percent,
                        'price': sp.price
                    })
            
            # 按权重排序
            point_detail.sort(key=lambda x: x['ratio'], reverse=True)
            details.append(point_detail)
        
        return jsonify({
            'success': True,
            'data': {
                'times': times,
                'values': values,
                'details': details 
            }
        })
    finally:
        session.close()

@app.route('/api/trigger', methods=['POST'])
def manual_trigger():
    # 手动触发更新（调试用）
    from scheduler_service import update_job
    try:
        update_job()
        return jsonify({'success': True, 'message': '已触发更新'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    # 纯本地使用，开启debug方便看日志
    app.run(host='0.0.0.0', port=5000, debug=False)
