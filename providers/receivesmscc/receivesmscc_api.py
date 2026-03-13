#!/usr/bin/env python3
"""
Receive-SMS.cc HTTP 协议爬虫

使用 curl_cffi 模拟浏览器 TLS 指纹获取手机号和短信
无需登录，完全免费

URL 结构:
- 首页: https://receive-sms.cc/
- 国家列表: https://receive-sms.cc/Countries/
- 国家手机号: https://receive-sms.cc/{Country}-Phone-Number/
- 手机号详情: https://receive-sms.cc/{Country}-Phone-Number/{phone}
- 短信分页: https://receive-sms.cc/{Country}-Phone-Number/{phone}_{page}.html
"""

import re
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
from urllib.parse import urljoin

from curl_cffi import requests
from bs4 import BeautifulSoup


@dataclass
class PhoneNumber:
    """手机号数据模型"""
    country: str
    country_code: str  # URL 中的国家代码，如 US, UK
    phone: str
    sms_count: int
    last_update: str
    detail_url: str


@dataclass
class SMSMessage:
    """短信数据模型"""
    sender: str
    received_time: str
    message: str


@dataclass
class PhoneDetail:
    """手机号详情数据模型"""
    phone: str
    country: str
    country_code: str
    messages: List[SMSMessage]
    total_pages: int = 1


@dataclass
class Country:
    """国家数据模型"""
    name: str
    code: str  # URL 中使用的代码，如 US, UK, Belgium
    phone_count: int
    url: str


class ReceiveSMSCCAPI:
    """Receive-SMS.cc HTTP API 客户端"""
    
    BASE_URL = "https://receive-sms.cc"
    
    # 国家代码映射 (简称 -> URL 中的名称)
    COUNTRIES = {
        "us": "US",
        "usa": "US",
        "uk": "UK",
        "gb": "UK",
        "canada": "Canada",
        "ca": "Canada",
        "france": "France",
        "fr": "France",
        "germany": "Germany",
        "de": "Germany",
        "belgium": "Belgium",
        "be": "Belgium",
        "netherlands": "Netherlands",
        "nl": "Netherlands",
        "finland": "Finland",
        "fi": "Finland",
        "sweden": "Sweden",
        "se": "Sweden",
        "russia": "Russia",
        "ru": "Russia",
        "ukraine": "Ukraine",
        "ua": "Ukraine",
        "poland": "Poland",
        "pl": "Poland",
        "spain": "Spain",
        "es": "Spain",
        "italy": "Italy",
        "it": "Italy",
        "australia": "Australia",
        "au": "Australia",
        "india": "India",
        "in": "India",
        "china": "China",
        "cn": "China",
        "japan": "Japan",
        "jp": "Japan",
        "brazil": "Brazil",
        "br": "Brazil",
        "mexico": "Mexico",
        "mx": "Mexico",
    }
    
    def __init__(self):
        """初始化 API 客户端"""
        self.session = requests.Session(impersonate="chrome")
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
    
    def _get_country_code(self, country: str) -> str:
        """将国家名称/代码转换为 URL 中使用的格式"""
        country_lower = country.lower().strip()
        return self.COUNTRIES.get(country_lower, country)
    
    def test_connection(self) -> bool:
        """测试连接是否正常"""
        try:
            resp = self.session.get(self.BASE_URL, timeout=30)
            if resp.status_code == 200:
                if "Receive SMS Online" in resp.text:
                    print("✅ 连接正常")
                    return True
                print("⚠️ 页面内容异常")
                return False
            else:
                print(f"❌ 状态码: {resp.status_code}")
                return False
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    def get_countries(self) -> List[Country]:
        """获取支持的国家列表"""
        url = f"{self.BASE_URL}/Countries/"
        
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return []
        
        soup = BeautifulSoup(resp.text, 'lxml')
        countries = []
        
        # 查找所有国家卡片
        for card in soup.select('a.card[href*="-Phone-Number"]'):
            try:
                href = card.get('href', '')
                
                # 提取国家代码，如 /US-Phone-Number/ -> US
                match = re.search(r'/([A-Za-z]+)-Phone-Number/', href)
                if not match:
                    continue
                
                country_code = match.group(1)
                
                # 获取国家名称
                name_elem = card.select_one('h2')
                name = name_elem.get_text(strip=True) if name_elem else country_code
                
                # 获取手机号数量
                count_elem = card.select_one('span.number')
                count_text = count_elem.get_text(strip=True) if count_elem else "0"
                phone_count = int(re.search(r'\d+', count_text).group()) if re.search(r'\d+', count_text) else 0
                
                countries.append(Country(
                    name=name,
                    code=country_code,
                    phone_count=phone_count,
                    url=urljoin(self.BASE_URL, href)
                ))
            except Exception:
                continue
        
        print(f"✅ 找到 {len(countries)} 个国家")
        return countries
    
    def get_phone_list(self, country: str, page: int = 1) -> List[PhoneNumber]:
        """
        获取指定国家的手机号列表
        
        Args:
            country: 国家代码 (如 'us', 'uk') 或 URL 格式 (如 'US', 'UK')
            page: 页码 (注意: receive-sms.cc 首页直接显示所有国家的号码，
                   国家页面 /US-Phone-Number/ 才有分页)
        
        Returns:
            手机号列表
        """
        country_code = self._get_country_code(country)
        
        # 构建 URL
        if page == 1:
            url = f"{self.BASE_URL}/{country_code}-Phone-Number/"
        else:
            url = f"{self.BASE_URL}/{country_code}-Phone-Number/?page={page}"
        
        print(f"📱 正在获取 {country_code} 第 {page} 页...")
        
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return []
        
        soup = BeautifulSoup(resp.text, 'lxml')
        phones = []
        
        # 查找手机号卡片 - 在 list1 区域内
        for card in soup.select('div.list1 a.card'):
            try:
                href = card.get('href', '')
                if '-Phone-Number/' not in href:
                    continue
                
                # 获取国家信息
                country_elem = card.select_one('p.text-muted')
                country_name = country_elem.get_text(strip=True).replace(' Phone Number', '') if country_elem else ''
                
                # 获取手机号
                phone_elem = card.select_one('h4')
                phone = phone_elem.get_text(strip=True) if phone_elem else ''
                
                # 获取短信数量
                count_elem = card.select_one('span.number')
                sms_count = int(count_elem.get_text(strip=True)) if count_elem else 0
                
                # 获取最后更新时间
                time_elem = card.select_one('span.time')
                last_update = time_elem.get_text(strip=True) if time_elem else ''
                
                # 从 URL 提取国家代码
                url_match = re.search(r'/([A-Za-z]+)-Phone-Number/', href)
                phone_country_code = url_match.group(1) if url_match else country_code
                
                phones.append(PhoneNumber(
                    country=country_name,
                    country_code=phone_country_code,
                    phone=phone,
                    sms_count=sms_count,
                    last_update=last_update,
                    detail_url=urljoin(self.BASE_URL, href)
                ))
            except Exception:
                continue
        
        print(f"✅ 找到 {len(phones)} 个手机号")
        return phones
    
    def get_all_phones_from_home(self) -> List[PhoneNumber]:
        """从首页获取所有显示的手机号（混合多国）"""
        url = self.BASE_URL
        
        print("📱 正在获取首页手机号列表...")
        
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return []
        
        soup = BeautifulSoup(resp.text, 'lxml')
        phones = []
        
        # 查找手机号卡片
        for card in soup.select('div.list1 a.card'):
            try:
                href = card.get('href', '')
                if '-Phone-Number/' not in href:
                    continue
                
                # 获取国家信息
                country_elem = card.select_one('p.text-muted')
                country_name = country_elem.get_text(strip=True).replace(' Phone Number', '') if country_elem else ''
                
                # 获取手机号
                phone_elem = card.select_one('h4')
                phone = phone_elem.get_text(strip=True) if phone_elem else ''
                
                # 获取短信数量
                count_elem = card.select_one('span.number')
                sms_count = int(count_elem.get_text(strip=True)) if count_elem else 0
                
                # 获取最后更新时间
                time_elem = card.select_one('span.time')
                last_update = time_elem.get_text(strip=True) if time_elem else ''
                
                # 从 URL 提取国家代码
                url_match = re.search(r'/([A-Za-z]+)-Phone-Number/', href)
                country_code = url_match.group(1) if url_match else ''
                
                phones.append(PhoneNumber(
                    country=country_name,
                    country_code=country_code,
                    phone=phone,
                    sms_count=sms_count,
                    last_update=last_update,
                    detail_url=urljoin(self.BASE_URL, href)
                ))
            except Exception:
                continue
        
        print(f"✅ 找到 {len(phones)} 个手机号")
        return phones
    
    def get_phone_messages(self, phone_url: str, max_pages: int = 1) -> Optional[PhoneDetail]:
        """
        获取指定手机号的短信详情
        
        Args:
            phone_url: 手机号详情页 URL
            max_pages: 最大获取页数
        
        Returns:
            手机号详情
        """
        print(f"📨 正在获取短信详情...")
        
        try:
            resp = self.session.get(phone_url, timeout=30)
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return None
        
        soup = BeautifulSoup(resp.text, 'lxml')
        
        # 获取手机号
        phone_elem = soup.select_one('h3.f-30')
        phone = phone_elem.get_text(strip=True) if phone_elem else ""
        
        # 获取国家
        country_elem = soup.select_one('h2.f-24 a')
        country = country_elem.get_text(strip=True).replace(' Phone Number', '') if country_elem else ""
        
        # 从 URL 提取国家代码
        url_match = re.search(r'/([A-Za-z]+)-Phone-Number/', phone_url)
        country_code = url_match.group(1) if url_match else ""
        
        # 获取总页数
        total_pages = 1
        pagination = soup.select('ul.pagination li a')
        for link in pagination:
            href = link.get('href', '')
            # 匹配 _40.html 这种格式
            match = re.search(r'_(\d+)\.html', href)
            if match:
                page_num = int(match.group(1))
                total_pages = max(total_pages, page_num)
        
        all_messages = []
        
        # 获取第一页的短信
        messages = self._parse_messages(soup)
        all_messages.extend(messages)
        
        # 获取更多页
        if max_pages > 1 and total_pages > 1:
            base_url = phone_url.rstrip('/')
            
            for page_num in range(2, min(max_pages + 1, total_pages + 1)):
                page_url = f"{base_url}_{page_num}.html"
                try:
                    resp = self.session.get(page_url, timeout=30)
                    page_soup = BeautifulSoup(resp.text, 'lxml')
                    messages = self._parse_messages(page_soup)
                    all_messages.extend(messages)
                except Exception:
                    break
        
        print(f"✅ 找到 {len(all_messages)} 条短信")
        
        return PhoneDetail(
            phone=phone,
            country=country,
            country_code=country_code,
            messages=all_messages,
            total_pages=total_pages
        )
    
    def _parse_messages(self, soup: BeautifulSoup) -> List[SMSMessage]:
        """从页面解析短信列表"""
        messages = []
        
        for item in soup.select('div.list-message div.item'):
            try:
                # 获取发送者
                sender_elem = item.select_one('div.form')
                sender = sender_elem.get_text(strip=True).replace('From ', '') if sender_elem else ""
                
                # 获取时间
                time_elem = item.select_one('span.time')
                received_time = time_elem.get_text(strip=True) if time_elem else ""
                
                # 获取内容
                content_elem = item.select_one('div.con')
                message = content_elem.get_text(strip=True) if content_elem else ""
                
                if message:  # 只添加有内容的短信
                    messages.append(SMSMessage(
                        sender=sender,
                        received_time=received_time,
                        message=message
                    ))
            except Exception:
                continue
        
        return messages
    
    def get_messages_by_phone(self, phone: str, country: str = "US", max_pages: int = 1) -> Optional[PhoneDetail]:
        """
        通过手机号获取短信
        
        Args:
            phone: 手机号 (不含 +)
            country: 国家代码
            max_pages: 最大页数
        
        Returns:
            手机号详情
        """
        phone = phone.replace('+', '').replace(' ', '').strip()
        country_code = self._get_country_code(country)
        
        # 构建 URL
        phone_url = f"{self.BASE_URL}/{country_code}-Phone-Number/{phone}"
        
        return self.get_phone_messages(phone_url, max_pages)
    
    def search_phone(self, phone: str, country: str = None) -> Optional[str]:
        """
        搜索手机号，返回详情页 URL
        
        Args:
            phone: 手机号
            country: 国家代码（可选，如果提供则直接构建 URL）
        
        Returns:
            详情页 URL 或 None
        """
        phone = phone.replace('+', '').replace(' ', '').strip()
        
        if country:
            country_code = self._get_country_code(country)
            url = f"{self.BASE_URL}/{country_code}-Phone-Number/{phone}"
            
            # 验证页面存在
            try:
                resp = self.session.get(url, timeout=30)
                if resp.status_code == 200 and 'list-message' in resp.text:
                    return url
            except Exception:
                pass
            
            return None
        
        # 如果没有指定国家，尝试从首页搜索
        phones = self.get_all_phones_from_home()
        for p in phones:
            if phone in p.phone.replace('+', '').replace(' ', ''):
                return p.detail_url
        
        return None


def main():
    """测试代码"""
    api = ReceiveSMSCCAPI()
    
    print("\n" + "="*60)
    print("  Receive-SMS.cc HTTP 协议爬虫")
    print("="*60)
    
    # 测试连接
    print("\n🔗 测试连接...")
    if not api.test_connection():
        return
    
    # 获取国家列表
    print("\n🌍 获取国家列表...")
    countries = api.get_countries()
    print(f"\n支持的国家: {len(countries)}")
    for c in countries[:10]:
        print(f"   {c.name}: {c.phone_count} 个号码")
    
    # 获取美国手机号列表
    print("\n📱 获取美国手机号列表...")
    phones = api.get_phone_list("US")
    
    if phones:
        print(f"\n美国手机号 (共 {len(phones)} 个):")
        for i, phone in enumerate(phones[:5], 1):
            print(f"   {i}. {phone.phone} - {phone.last_update} ({phone.sms_count} 条短信)")
        
        # 获取第一个手机号的短信
        if phones:
            print(f"\n📨 获取 {phones[0].phone} 的短信...")
            detail = api.get_phone_messages(phones[0].detail_url, max_pages=1)
            
            if detail and detail.messages:
                print(f"\n短信列表 (共 {len(detail.messages)} 条):")
                for i, msg in enumerate(detail.messages[:5], 1):
                    print(f"   [{i}] 来自: {msg.sender}")
                    print(f"       时间: {msg.received_time}")
                    print(f"       内容: {msg.message[:50]}...")


if __name__ == "__main__":
    main()
