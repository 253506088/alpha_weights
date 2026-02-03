# fetcher.py
# 数据抓取模块：负责从网络获取基金持仓和股票行情

import requests
from lxml import html
import time
import json
import re
from typing import List, Dict, Optional

class FundFetcher:
    """基金数据抓取"""
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'http://fundf10.eastmoney.com/'
    }
    # 强制不使用系统代理，避免用户电脑上有残留的代理设置导致连接 127.0.0.1 失败
    PROXIES = {"http": None, "https": None}

    @staticmethod
    def get_fund_details(fund_code: str) -> Optional[Dict]:
        """
        获取基金详情（名称、重仓股）
        使用 PC 端接口 FundArchivesDatas.aspx
        """
        print(f"\n[FundFetcher] 开始获取基金详情: {fund_code}")
        
        # 1. 尝试 PC Web API 获取持仓
        data = None
        try:
            data = FundFetcher._fetch_from_pc_api(fund_code)
            if data and data.get('holdings'):
                print(f"[FundFetcher] API (PC) 获取持仓成功: {len(data['holdings'])} 只股票")
        except Exception as e:
            print(f"[FundFetcher] PC API attempt failed for {fund_code}: {e}")

        # 2. 如果API失败，尝试Fallback (虽然后来证明不好用，但留着也不坏)
        if not data:
            try:
                data = FundFetcher._fetch_from_web_fallback(fund_code)
            except Exception as e:
                print(f"[FundFetcher] Web fallback attempt failed for {fund_code}: {e}")

        if not data:
            return None

        # 3. 尝试获取准确的基金名称 (如果是占位符的话)
        if data['name'] == f"基金{fund_code}" or not data['name']:
            real_name = FundFetcher._get_fund_name(fund_code)
            if real_name:
                print(f"[FundFetcher] 获取到真实名称: {real_name}")
                data['name'] = real_name
        
        return data

    @staticmethod
    def _get_fund_name(fund_code: str) -> Optional[str]:
        """
        通过搜索接口获取准确的基金中文名称
        """
        url = "http://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx"
        params = {'m': '1', 'key': fund_code}
        try:
            resp = requests.get(url, params=params, headers=FundFetcher.HEADERS, proxies=FundFetcher.PROXIES, timeout=5)
            if resp.status_code == 200:
                # 返回格式通常是 JSON: {"Datas": [{"CODE": "...", "NAME": "...", ...}], ...}
                info = resp.json()
                if 'Datas' in info and len(info['Datas']) > 0:
                    return info['Datas'][0].get('NAME')
        except Exception as e:
            print(f"[FundFetcher] 获取名称失败: {e}")
        return None

    @staticmethod
    def _fetch_from_pc_api(fund_code: str) -> Optional[Dict]:
        """
        接口: http://fundf10.eastmoney.com/FundArchivesDatas.aspx
        返回 JS: var apidata = { content: "<html>...", ... }
        """
        url = "http://fundf10.eastmoney.com/FundArchivesDatas.aspx"
        params = {
            'type': 'jjcc',   # 基金持仓
            'code': fund_code,
            'topline': '10',  # 前10
            'year': '',
            'month': '',
            'rt': time.time()
        }
        
        print(f"  [API REQ] GET {url}")
        
        resp = requests.get(url, params=params, headers=FundFetcher.HEADERS, proxies=FundFetcher.PROXIES, timeout=8)
        resp.encoding = 'utf-8'
        
        print(f"  [API RES] Status: {resp.status_code}")
        
        if resp.status_code != 200: return None
        
        content = ""
        try:
            match = re.search(r'content:"(.*?)",aryLastDate', resp.text, re.DOTALL)
            if match:
                content = match.group(1)
            else:
                match = re.search(r'content:"(.*)"', resp.text, re.DOTALL)
                if match:
                    content = match.group(1)
        except Exception as e:
            print(f"  [API RES] 正则提取 content 失败: {e}")
            return None

        if not content:
            print("  [API RES] 未找到 content 内容")
            return None
        
        # 打印一下提取到的HTML片段头部，方便确认
        print(f"  [API RES] Content HTML Head: {content[:100]}...")

        html_content = content.replace(r'\"', '"').replace(r'\/', '/')
        tree = html.fromstring(html_content)
        
        holdings = []
        tables = tree.xpath('//table')
        
        print(f"  [API RES] 找到表格数量: {len(tables)}")

        for tbl in tables:
            # 尝试通过表头动态定位列索引
            # 通常第一行是表头
            rows = tbl.xpath('.//tr')
            if not rows: continue
            
            headers = [ ''.join(col.itertext()).strip() for col in rows[0].xpath('.//td|.//th') ]
            print(f"  [API RES] 表格头: {headers}")
            
            # 定位关键列索引
            idx_code = -1
            idx_name = -1
            idx_ratio = -1
            
            for i, h in enumerate(headers):
                if '代码' in h: idx_code = i
                elif '名称' in h: idx_name = i
                elif '占比' in h or '比例' in h: idx_ratio = i
            
            if idx_code != -1 and idx_name != -1 and idx_ratio != -1:
                print(f"  [API RES] 命中关键列索引: 代码={idx_code}, 名称={idx_name}, 占比={idx_ratio}")
                
                # 遍历数据行
                # 从第二行开始
                for row in rows[1:]:
                    cols = row.xpath('.//td')
                    if len(cols) <= max(idx_code, idx_name, idx_ratio):
                        continue
                        
                    c_code = ''.join(cols[idx_code].itertext()).strip()
                    c_name = ''.join(cols[idx_name].itertext()).strip()
                    c_ratio_str = ''.join(cols[idx_ratio].itertext()).strip().replace('%', '')
                    
                    if c_code and c_ratio_str:
                        try:
                            ratio = float(c_ratio_str) / 100.0
                            holdings.append({
                                'code': c_code,
                                'name': c_name,
                                'ratio': ratio
                            })
                        except: continue
                
                if holdings: 
                    # 只取前10
                    holdings = holdings[:10]
                    break
            else:
                print(f"  [API RES] 未在表头中找到所有关键列")

        print(f"  [API RES] 解析到持仓: {len(holdings)} 只股票")
        
        # 为了简单，我们先用占位符
        fund_name = f"基金{fund_code}"
        
        return {
            'code': fund_code,
            'name': fund_name,
            'holdings': holdings
        }

    @staticmethod
    def _fetch_from_web_fallback(fund_code: str) -> Optional[Dict]:
        """备用：直接抓取HTML（可能不含动态数据）"""
        url = f"http://fundf10.eastmoney.com/ccmx_{fund_code}.html"
        print(f"  [WEB REQ] GET {url}")
        try:
            resp = requests.get(url, headers=FundFetcher.HEADERS, proxies=FundFetcher.PROXIES, timeout=8)
            resp.encoding = 'utf-8'
            tree = html.fromstring(resp.text)
            
            # 尝试拿名字
            name = f"基金{fund_code}"
            try:
                title_nodes = tree.xpath('//div[@class="fundDetailTit"]/div/h1/text()')
                if title_nodes:
                    name = title_nodes[0].split('(')[0].strip()
            except: pass
            
            return {'code': fund_code, 'name': name, 'holdings': []}
        except:
            return None

class StockFetcher:
    """股票行情抓取"""

    @staticmethod
    def get_batch_prices(stock_codes: List[str]) -> Dict[str, Dict]:
        """
        批量获取股票实时价格
        """
        print(f"\n[StockFetcher] 批量请求股票行情, 数量: {len(stock_codes)}")
        results = {}
        if not stock_codes: return results
        
        unique_codes = list(set(stock_codes))
        
        CHUNK_SIZE = 50
        for i in range(0, len(unique_codes), CHUNK_SIZE):
            chunk = unique_codes[i:i+CHUNK_SIZE]
            res = StockFetcher._fetch_chunk(chunk)
            results.update(res)
            time.sleep(0.1) 
            
        return results

    @staticmethod
    def _fetch_chunk(codes: List[str]) -> Dict[str, Dict]:
        sina_codes = []
        map_sina_to_raw = {} 
        
        for c in codes:
            prefix = 'sz'
            if c.startswith('6'): prefix = 'sh'
            elif c.startswith('8') or c.startswith('4'): prefix = 'bj'
            
            sc = f"{prefix}{c}"
            sina_codes.append(sc)
            map_sina_to_raw[sc] = c 
            
        url = f"http://hq.sinajs.cn/list={','.join(sina_codes)}"
        headers = {'Referer': 'http://finance.sina.com.cn'}
        
        print(f"  [STOCK REQ] GET {url}")
        
        try:
            # 同样禁用代理
            resp = requests.get(url, headers=headers, proxies={"http": None, "https": None}, timeout=10)
            resp.encoding = 'gbk' 
            
            print(f"  [STOCK RES] Status: {resp.status_code}")
            # print(f"  [STOCK RES] Body Sample: {resp.text[:100]}...")
            
            data_map = {}
            lines = resp.text.strip().split('\n')
            for line in lines:
                if '="' not in line: continue
                left, right = line.split('="')
                var_name = left.strip()
                val_str = right.strip().strip('";')
                
                sina_code = var_name.split('hq_str_')[-1]
                
                if not val_str: continue
                fields = val_str.split(',')
                if len(fields) < 4: continue
                
                try:
                    name = fields[0]
                    prev_close = float(fields[2])
                    price = float(fields[3])
                    
                    if price == 0 and prev_close > 0:
                        price = prev_close
                    
                    pct = 0.0
                    if prev_close > 0:
                        pct = (price - prev_close) / prev_close * 100
                    
                    raw_code = map_sina_to_raw.get(sina_code)
                    if raw_code:
                        data_map[raw_code] = {
                            'name': name,
                            'price': price,
                            'prev_close': prev_close,
                            'pct': round(pct, 2)
                        }
                except:
                    continue
            return data_map
            
        except Exception as e:
            print(f"  [StockFetcher] Batch fetch error: {e}")
            return {}
