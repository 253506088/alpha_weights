"""
数据获取 API 模块
"""
import requests
from lxml import html
import time
from typing import List, Dict, Optional


class FundDataFetcher:
    """基金数据获取器"""

    @staticmethod
    def get_fund_holdings(fund_code: str) -> Optional[Dict]:
        """
        从东方财富获取基金前十大重仓股

        Args:
            fund_code: 6位基金代码

        Returns:
            包含基金信息和持仓的字典，格式：
            {
                'name': '基金名称',
                'holdings': [
                    {'code': '000001', 'name': '平安银行', 'ratio': 8.52},
                    ...
                ]
            }
            如果获取失败返回 None
        """
        try:
            # 东方财富基金持仓API
            url = f"https://fundf10.eastmoney.com/ccmx_{fund_code}.html"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'utf-8'

            if response.status_code != 200:
                print(f"获取基金持仓失败: HTTP {response.status_code}")
                return None

            # 解析HTML
            tree = html.fromstring(response.text)

            # 获取基金名称
            fund_name = None
            try:
                fund_name_elem = tree.xpath('//div[@class="fundDetailTit"]/div[@class="detail-title"]/h1/text()')
                if fund_name_elem:
                    fund_name = fund_name_elem[0].strip()
            except:
                pass

            # 获取前十大重仓股表格
            holdings = []
            try:
                # 查找重仓股表格
                tables = tree.xpath('//table[contains(@class, "w782")]')
                for table in tables:
                    # 检查是否是重仓股表格
                    table_text = ''.join(table.itertext())
                    if '前十大重仓股' in table_text or '重仓股' in table_text:
                        rows = table.xpath('.//tr')[1:]  # 跳过表头

                        for row in rows[:10]:  # 只取前十大
                            cols = row.xpath('.//td/text()')
                            if len(cols) >= 5:
                                code = cols[0].strip()
                                name = cols[1].strip()
                                ratio_str = cols[2].strip()

                                # 解析持仓占比
                                try:
                                    ratio = float(ratio_str.replace('%', ''))
                                    # 转换为小数（如 8.52% -> 0.0852）
                                    ratio = ratio / 100.0

                                    holdings.append({
                                        'code': code,
                                        'name': name,
                                        'ratio': ratio
                                    })
                                except ValueError:
                                    continue

                        if holdings:
                            break

            except Exception as e:
                print(f"解析持仓数据出错: {e}")

            if not fund_name:
                # 如果从HTML中没获取到名称，尝试其他方式
                fund_name = f"基金{fund_code}"

            if not holdings:
                print(f"未获取到基金 {fund_code} 的持仓数据")
                return None

            return {
                'code': fund_code,
                'name': fund_name,
                'holdings': holdings
            }

        except requests.RequestException as e:
            print(f"请求东方财富API失败: {e}")
            return None
        except Exception as e:
            print(f"获取基金持仓数据出错: {e}")
            return None


class StockDataFetcher:
    """股票数据获取器"""

    @staticmethod
    def get_stock_realtime_batch(stock_codes: List[str]) -> Dict[str, Dict]:
        """
        批量获取股票实时行情（新浪财经API）

        Args:
            stock_codes: 股票代码列表，格式如 ['000001', '000002']

        Returns:
            字典，键为股票代码，值为股票信息：
            {
                '000001': {
                    'code': '000001',
                    'name': '平安银行',
                    'price': 12.34,
                    'prev_close': 12.10,
                    'change_percent': 1.98
                },
                ...
            }
        """
        result = {}

        if not stock_codes:
            return result

        try:
            # 新浪财经API批量请求
            # 格式: sh600000,sz000001,... (上海股票前缀sh，深圳股票前缀sz)
            codes_with_prefix = []
            for code in stock_codes:
                if code.startswith('6'):
                    codes_with_prefix.append(f'sh{code}')
                else:
                    codes_with_prefix.append(f'sz{code}')

            url = f"http://hq.sinajs.cn/list={','.join(codes_with_prefix)}"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'http://finance.sina.com.cn'
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'gbk'

            if response.status_code != 200:
                print(f"获取股票行情失败: HTTP {response.status_code}")
                return result

            # 解析返回数据
            lines = response.text.strip().split('\n')

            for i, line in enumerate(lines):
                if not line.startswith('var hq_str_'):
                    continue

                # 提取股票代码（去掉前缀）
                var_name = line.split('=')[0]
                code = var_name.replace('var hq_str_', '').replace('sh', '').replace('sz', '')

                # 提取数据部分
                data_str = line.split('"')[1].strip()

                if not data_str:
                    continue

                data = data_str.split(',')

                if len(data) < 4:
                    continue

                # 数据格式：
                # 0: 股票名称
                # 1: 今开
                # 2: 昨收
                # 3: 当前价
                # 4: 最高
                # 5: 最低
                # ...

                name = data[0]
                prev_close = float(data[2]) if data[2] else 0.0
                current_price = float(data[3]) if data[3] else 0.0

                if prev_close == 0:
                    continue

                # 计算涨跌幅
                change_percent = ((current_price - prev_close) / prev_close) * 100

                result[code] = {
                    'code': code,
                    'name': name,
                    'price': current_price,
                    'prev_close': prev_close,
                    'change_percent': round(change_percent, 2)
                }

            # 添加延迟避免被限流
            time.sleep(0.5)

            return result

        except requests.RequestException as e:
            print(f"请求新浪财经API失败: {e}")
            return result
        except Exception as e:
            print(f"获取股票行情出错: {e}")
            return result


def calculate_fund_change(holdings_data: List[Dict], stock_prices: Dict[str, Dict]) -> float:
    """
    计算基金预估涨跌幅

    Args:
        holdings_data: 持仓数据列表 [{'code': '000001', 'ratio': 0.0852}, ...]
        stock_prices: 股票价格数据 {'000001': {'change_percent': 1.98}, ...}

    Returns:
        基金预估涨跌幅（百分比）
    """
    total_change = 0.0

    for holding in holdings_data:
        stock_code = holding['code']
        ratio = holding['ratio']

        if stock_code in stock_prices:
            stock_change = stock_prices[stock_code]['change_percent']
            total_change += stock_change * ratio
        else:
            print(f"股票 {stock_code} 的行情数据未获取到")

    return round(total_change, 2)
