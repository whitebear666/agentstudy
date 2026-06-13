# skills/price_fetcher.py
from __future__ import annotations

import json
import re
import time
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple, Callable
from collections import defaultdict
from dataclasses import dataclass, asdict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup


@dataclass
class PriceInfo:
    """价格信息"""
    price: float
    unit: str
    source: str
    updated_at: str
    store: str = "农业农村部"


class PriceFetcher:
    """
    农业农村部官方价格获取器
    数据源：http://ncpscxx.moa.gov.cn（重点农产品市场信息平台）
    """

    CACHE_FILE = "data/price_cache.json"
    CACHE_EXPIRE_HOURS = 12  # 12小时过期

    # 食材名称映射（农产品标准名称）
    PRODUCT_MAPPING = {
        # 蔬菜类
        "白菜": "大白菜", "菠菜": "菠菜", "生菜": "生菜", "油菜": "油菜",
        "芹菜": "芹菜", "韭菜": "韭菜", "西兰花": "西兰花", "菜花": "菜花",
        "西红柿": "西红柿", "番茄": "西红柿", "黄瓜": "黄瓜", "冬瓜": "冬瓜",
        "南瓜": "南瓜", "苦瓜": "苦瓜", "茄子": "茄子", "土豆": "土豆",
        "马铃薯": "土豆", "胡萝卜": "胡萝卜", "萝卜": "白萝卜", "洋葱": "洋葱",
        "豆角": "豆角", "青椒": "青椒", "辣椒": "辣椒", "蘑菇": "蘑菇",
        "香菇": "香菇", "金针菇": "金针菇",

        # 肉蛋类
        "猪肉": "猪肉", "牛肉": "牛肉", "羊肉": "羊肉", "鸡肉": "白条鸡",
        "鸡蛋": "鸡蛋", "鸭蛋": "鸭蛋", "白条鸡": "白条鸡",

        # 水产品
        "鱼": "鲤鱼", "鲤鱼": "鲤鱼", "草鱼": "草鱼", "鲫鱼": "鲫鱼",
        "虾": "对虾", "对虾": "对虾",

        # 粮油类
        "大米": "大米", "面粉": "面粉", "玉米": "玉米", "大豆": "大豆",
        "花生油": "花生油", "豆油": "豆油",
    }

    # 默认参考价（爬取失败时使用）
    DEFAULT_PRICES = {
        "大白菜": 2.0, "菠菜": 4.5, "生菜": 4.0, "油菜": 3.5, "芹菜": 4.0,
        "韭菜": 4.5, "西兰花": 7.0, "菜花": 5.0, "西红柿": 5.0, "黄瓜": 4.0,
        "冬瓜": 3.0, "南瓜": 3.5, "苦瓜": 6.0, "茄子": 4.5, "土豆": 3.0,
        "胡萝卜": 3.5, "白萝卜": 2.5, "洋葱": 3.0, "豆角": 6.0, "青椒": 6.0,
        "辣椒": 8.0, "蘑菇": 10.0, "香菇": 12.0, "金针菇": 8.0,
        "猪肉": 25.0, "牛肉": 50.0, "羊肉": 55.0, "白条鸡": 18.0,
        "鸡蛋": 5.5, "鲤鱼": 12.0, "草鱼": 12.0, "对虾": 35.0,
        "大米": 5.0, "面粉": 4.0, "玉米": 3.0, "大豆": 6.0,
        "花生油": 15.0, "豆油": 10.0,
    }

    def __init__(self):
        self.cache = self._load_cache()
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        })
        return session

    def _load_cache(self) -> Dict:
        try:
            with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                expire_time = datetime.now() - timedelta(hours=self.CACHE_EXPIRE_HOURS)
                return {k: v for k, v in data.items()
                        if datetime.fromisoformat(v['updated_at']) > expire_time}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_cache(self) -> None:
        try:
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存缓存失败: {e}")

    def _normalize_name(self, name: str) -> str:
        """标准化为农产品标准名称"""
        name = name.strip()
        return self.PRODUCT_MAPPING.get(name, name)

    def _fetch_price_from_moa(self, product_name: str) -> Optional[PriceInfo]:
        """
        从农业农村部平台获取价格
        数据源：重点农产品市场信息平台
        """
        try:
            # 方案1：尝试通过搜索API获取
            search_url = "http://ncpscxx.moa.gov.cn/api/product/search"
            params = {"keyword": product_name}

            resp = self.session.get(search_url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('data') and len(data['data']) > 0:
                    price_data = data['data'][0]
                    price = price_data.get('price') or price_data.get('avgPrice')
                    if price:
                        return PriceInfo(
                            price=float(price),
                            unit="元/公斤",
                            source="moa_api",
                            updated_at=datetime.now().isoformat(),
                            store="农业农村部"
                        )

            # 方案2：爬取价格列表页面
            list_url = "http://ncpscxx.moa.gov.cn/price/list"
            resp = self.session.get(list_url, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # 查找包含该农产品的价格行
                for row in soup.select('table.price-table tr'):
                    cells = row.find_all('td')
                    if len(cells) >= 2 and product_name in cells[0].get_text():
                        price_text = cells[1].get_text()
                        price_match = re.search(r'(\d+(?:\.\d+)?)', price_text)
                        if price_match:
                            return PriceInfo(
                                price=float(price_match.group(1)),
                                unit="元/公斤",
                                source="moa_crawler",
                                updated_at=datetime.now().isoformat(),
                                store="农业农村部"
                            )

            return None

        except Exception as e:
            print(f"农业农村部API获取失败 [{product_name}]: {e}")
            return None

    def _fetch_from_crawler_alternative(self, name: str) -> Optional[PriceInfo]:
        """备用爬虫：从农业农村部数据频道获取"""
        try:
            # 数据频道首页有批发价格200指数
            url = "http://data.moa.gov.cn"
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # 查找价格指数
                index_pattern = re.compile(r'(\d+(?:\.\d+)?)')
                # 这里简化处理，实际需要根据页面结构调整

            # 尝试通过特定品种页面
            detail_url = f"http://data.moa.gov.cn/data/{name}"
            resp = self.session.get(detail_url, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                price_text = soup.find('span', class_='price')
                if price_text:
                    price_match = re.search(r'(\d+(?:\.\d+)?)', price_text.text)
                    if price_match:
                        return PriceInfo(
                            price=float(price_match.group(1)),
                            unit="元/公斤",
                            source="data_moa",
                            updated_at=datetime.now().isoformat(),
                            store="农业农村部"
                        )
            return None
        except Exception as e:
            print(f"备用爬虫失败 [{name}]: {e}")
            return None

    def _get_default_price(self, name: str) -> PriceInfo:
        normalized = self._normalize_name(name)
        price = self.DEFAULT_PRICES.get(normalized, 5.0)
        return PriceInfo(
            price=price,
            unit="元/公斤",
            source="default",
            updated_at=datetime.now().isoformat(),
            store="参考价"
        )

    def get_price(self, name: str, force_refresh: bool = False) -> PriceInfo:
        """
        获取食材价格
        优先级：缓存 → 农业农村部API → 备用爬虫 → 默认价
        """
        name = self._normalize_name(name)

        # 1. 缓存
        if not force_refresh and name in self.cache:
            data = self.cache[name]
            return PriceInfo(**data)

        # 2. 农业农村部API
        moa_price = self._fetch_price_from_moa(name)
        if moa_price:
            self.cache[name] = asdict(moa_price)
            self._save_cache()
            return moa_price

        # 3. 备用爬虫
        crawler_price = self._fetch_from_crawler_alternative(name)
        if crawler_price:
            self.cache[name] = asdict(crawler_price)
            self._save_cache()
            return crawler_price

        # 4. 默认价格
        default_price = self._get_default_price(name)
        self.cache[name] = asdict(default_price)
        self._save_cache()
        return default_price

    def get_prices_batch(self, names: List[str], force_refresh: bool = False) -> Dict[str, PriceInfo]:
        """批量获取价格"""
        results = {}
        for name in names:
            results[name] = self.get_price(name, force_refresh)
            time.sleep(random.uniform(0.3, 0.8))
        return results

    def create_price_input_dialog(root, name):
        """创建价格输入对话框（需要在UI层实现）"""
        # 这是一个占位函数，如果不需要用户手动输入价格，可以暂时返回 None
        return None