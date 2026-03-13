#!/usr/bin/env python3
"""
SMS24.me HTTP 协议爬虫

免费短信接收服务，无需登录

URL 结构:
- 首页: https://sms24.me/en
- 国家列表: https://sms24.me/en/countries
- 国家手机号: https://sms24.me/en/countries/{country_code}
- 所有号码: https://sms24.me/en/numbers
- 手机号详情: https://sms24.me/en/sms/receive-free-sms-online-on-{phone}
"""

import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urljoin

from curl_cffi import requests
from bs4 import BeautifulSoup


@dataclass
class PhoneNumber:
    """手机号数据模型"""
    country: str
    country_code: str
    phone: str
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
    code: str
    url: str


class SMS24MeAPI:
    """SMS24.me HTTP API 客户端"""
    
    BASE_URL = "https://sms24.me"
    
    # 国家代码映射 (ISO 代码)
    COUNTRIES = {
        "us": "us",
        "usa": "us",
        "uk": "gb",
        "gb": "gb",
        "canada": "ca",
        "ca": "ca",
        "france": "fr",
        "fr": "fr",
        "germany": "de",
        "de": "de",
        "netherlands": "nl",
        "nl": "nl",
        "finland": "fi",
        "fi": "fi",
        "sweden": "se",
        "se": "se",
        "russia": "ru",
        "ru": "ru",
        "ukraine": "ua",
        "ua": "ua",
        "poland": "pl",
        "pl": "pl",
        "spain": "es",
        "es": "es",
        "italy": "it",
        "it": "it",
        "australia": "au",
        "au": "au",
        "india": "in",
        "in": "in",
        "china": "cn",
        "cn": "cn",
        "japan": "jp",
        "jp": "jp",
        "brazil": "br",
        "br": "br",
        "mexico": "mx",
        "mx": "mx",
        "belgium": "be",
        "be": "be",
        "austria": "at",
        "at": "at",
        "switzerland": "ch",
        "ch": "ch",
    }
    
    def __init__(self):
        """初始化 API 客户端"""
        self.session = requests.Session(impersonate="chrome")
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        })
    
    def _get_country_code(self, country: str) -> str:
        """转换国家名称为 ISO 代码"""
        return self.COUNTRIES.get(country.lower(), country.lower())
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            resp = self.session.get(f"{self.BASE_URL}/en", timeout=30)
            if resp.status_code == 200 and "SMS24" in resp.text:
                print("✅ SMS24.me 连接正常")
                return True
            return False
        except Exception as e:
            print(f"❌ SMS24.me 连接失败: {e}")
            return False
    
    def get_countries(self) -> List[Country]:
        """获取支持的国家列表"""
        url = f"{self.BASE_URL}/en/countries"
        
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return []
        
        soup = BeautifulSoup(resp.text, 'lxml')
        countries = []
        
        for link in soup.select('a.callout'):
            try:
                href = link.get('href', '')
                if '/en/countries/' not in href:
                    continue
                
                # 提取国家代码
                match = re.search(r'/countries/([a-z]{2})$', href)
                if not match:
                    continue
                
                code = match.group(1)
                
                # 获取国家名称
                name_elem = link.select_one('span.h5')
                name = name_elem.get_text(strip=True) if name_elem else code.upper()
                
                countries.append(Country(
                    name=name,
                    code=code,
                    url=urljoin(self.BASE_URL, href)
                ))
            except:
                continue
        
        print(f"✅ 找到 {len(countries)} 个国家")
        return countries
    
    def get_phone_list(self, country: str, page: int = 1) -> List[PhoneNumber]:
        """
        获取指定国家的手机号列表
        
        Args:
            country: 国家代码 (如 'us', 'gb')
            page: 页码
        """
        country_code = self._get_country_code(country)
        
        if page == 1:
            url = f"{self.BASE_URL}/en/countries/{country_code}"
        else:
            url = f"{self.BASE_URL}/en/countries/{country_code}/{page}"
        
        print(f"📱 正在获取 {country_code.upper()} 第 {page} 页手机号列表...")
        
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return []
        
        soup = BeautifulSoup(resp.text, 'lxml')
        phones = []
        
        # 解析手机号卡片 - SMS24.me 的格式
        # <a href="/en/numbers/15077130214" class="callout m-2">
        #   <div class="fw-bold text-primary placeholder">+15077130214</div>
        # </a>
        for card in soup.select('a.callout'):
            try:
                href = card.get('href', '')
                if '/en/numbers/' not in href:
                    continue
                
                # 获取手机号 - 在 div.fw-bold 中
                phone_elem = card.select_one('div.fw-bold')
                phone = phone_elem.get_text(strip=True) if phone_elem else ''
                
                # 获取国家名称
                country_name_elem = card.select_one('h5')
                country_name = country_name_elem.get_text(strip=True) if country_name_elem else country_code.upper()
                
                if phone:
                    phones.append(PhoneNumber(
                        country=country_name,
                        country_code=country_code,
                        phone=phone,
                        last_update='',  # SMS24.me 列表页没有显示时间
                        detail_url=urljoin(self.BASE_URL, href)
                    ))
            except:
                continue
        
        print(f"✅ 找到 {len(phones)} 个手机号")
        return phones
    
    def get_phone_messages(self, phone_url: str, max_pages: int = 1) -> Optional[PhoneDetail]:
        """
        获取手机号短信详情
        
        Args:
            phone_url: 手机号详情页 URL
            max_pages: 最大获取页数
        """
        print(f"📨 正在获取短信详情: {phone_url}")
        
        try:
            resp = self.session.get(phone_url, timeout=30)
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return None
        
        soup = BeautifulSoup(resp.text, 'lxml')
        
        # 获取手机号 - 在 h2.placeholder 中
        phone = ""
        phone_elems = soup.select('h2.placeholder')
        for elem in phone_elems:
            text = elem.get_text(strip=True)
            if text.startswith('+') and text[1:].replace(' ', '').isdigit():
                phone = text
                break
        
        # 获取国家 - 从链接中提取
        country = ""
        country_code = ""
        country_link = soup.select_one('a[href*="/countries/"]')
        if country_link:
            href = country_link.get('href', '')
            match = re.search(r'/countries/([a-z]{2})', href)
            if match:
                country_code = match.group(1)
            # 获取国家名称
            country_text = country_link.get_text(strip=True)
            if 'Phone Number' in country_text:
                country = country_text.replace(' Phone Number', '')
            else:
                country = country_text
        
        all_messages = []
        
        # 解析短信
        messages = self._parse_messages(soup)
        all_messages.extend(messages)
        
        # SMS24.me 的分页需要通过 API 或 JS 加载，这里只获取第一页
        total_pages = 1
        
        print(f"✅ 找到 {len(all_messages)} 条短信")
        
        return PhoneDetail(
            phone=phone,
            country=country,
            country_code=country_code,
            messages=all_messages,
            total_pages=total_pages
        )
    
    def _parse_messages(self, soup: BeautifulSoup) -> List[SMSMessage]:
        """解析短信列表"""
        messages = []
        
        # SMS24.me 使用 dl/dt/dd 结构
        # <dl id="sms_msg">
        #   <dt><div data-created="2026-02-03T15:20:30.000000Z"></div></dt>
        #   <dd>
        #     <label><a>From: +18668494336</a></label>
        #     <span class="placeholder text-break">消息内容</span>
        #   </dd>
        # </dl>
        
        # 获取所有 dl 元素
        for dl in soup.select('dl'):
            # 获取 dt 和 dd 配对
            dts = dl.select('dt')
            dds = dl.select('dd')
            
            for i, dd in enumerate(dds):
                try:
                    # 获取发送者
                    sender_elem = dd.select_one('label a')
                    sender = ""
                    if sender_elem:
                        sender_text = sender_elem.get_text(strip=True)
                        # 移除 "From: " 前缀
                        if sender_text.startswith('From:'):
                            sender = sender_text[5:].strip()
                        else:
                            sender = sender_text
                    
                    # 获取消息内容 - 在 span.text-break 中
                    content_elem = dd.select_one('span.text-break')
                    message = ""
                    if content_elem:
                        message = content_elem.get_text(strip=True)
                    
                    # 获取时间
                    received_time = ""
                    if i < len(dts):
                        time_div = dts[i].select_one('div[data-created]')
                        if time_div:
                            created = time_div.get('data-created', '')
                            if created:
                                # 简化时间格式
                                try:
                                    from datetime import datetime
                                    dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                                    received_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                                except:
                                    received_time = created
                    
                    if message:
                        messages.append(SMSMessage(
                            sender=sender,
                            received_time=received_time,
                            message=message
                        ))
                except Exception as e:
                    continue
        
        return messages
    
    def get_messages_by_phone(self, phone: str, country: str = "us", max_pages: int = 1) -> Optional[PhoneDetail]:
        """
        通过手机号获取短信
        
        Args:
            phone: 手机号 (不含 +)
            country: 国家代码
            max_pages: 最大页数
        """
        phone = phone.replace('+', '').replace(' ', '').strip()
        
        # 构建 URL - SMS24.me 的格式是 /en/numbers/{phone}
        phone_url = f"{self.BASE_URL}/en/numbers/{phone}"
        
        return self.get_phone_messages(phone_url, max_pages)


def main():
    """测试代码"""
    api = SMS24MeAPI()
    
    print("\n" + "="*60)
    print("  SMS24.me HTTP 协议爬虫")
    print("="*60)
    
    if not api.test_connection():
        return
    
    countries = api.get_countries()
    print(f"\n支持 {len(countries)} 个国家")
    for c in countries[:5]:
        print(f"  - {c.name} ({c.code})")
    
    phones = api.get_phone_list("us")
    
    if phones:
        print(f"\n美国手机号 (共 {len(phones)} 个):")
        for p in phones[:3]:
            print(f"  - {p.phone} - {p.last_update}")


if __name__ == "__main__":
    main()
