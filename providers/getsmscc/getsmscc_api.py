#!/usr/bin/env python3
"""
GetSMS.cc HTTP 协议爬虫

免费短信接收服务，无需登录

URL 结构:
- 首页: https://getsms.cc/
- 国家列表: https://getsms.cc/all
- 国家手机号: https://getsms.cc/temporary-phone-numbers/{Country}
- 手机号详情: https://getsms.cc/info/{phone}
- 短信分页: https://getsms.cc/info/{phone}_{page}.html
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
    phone: str
    last_update: str
    detail_url: str
    sms_count: int = 0


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
    status: str
    sms_count: int
    messages: List[SMSMessage]
    total_pages: int = 1


class GetSMSCCAPI:
    """GetSMS.cc HTTP API 客户端"""
    
    BASE_URL = "https://getsms.cc"
    
    # 国家代码映射
    COUNTRIES = {
        "us": "US",
        "usa": "US",
        "uk": "UK",
        "gb": "UK",
        "france": "France",
        "fr": "France",
        "sweden": "Sweden",
        "se": "Sweden",
        "finland": "Finland",
        "fi": "Finland",
        "netherlands": "Netherlands",
        "nl": "Netherlands",
        "belgium": "Belgium",
        "be": "Belgium",
        "germany": "Germany",
        "de": "Germany",
        "russia": "Russia",
        "ru": "Russia",
        "canada": "Canada",
        "ca": "Canada",
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
    
    def _get_country_name(self, country: str) -> str:
        """转换国家代码为网站使用的名称"""
        return self.COUNTRIES.get(country.lower(), country)
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            resp = self.session.get(self.BASE_URL, timeout=30)
            if resp.status_code == 200 and "GetSMS" in resp.text:
                print("✅ GetSMS.cc 连接正常")
                return True
            return False
        except Exception as e:
            print(f"❌ GetSMS.cc 连接失败: {e}")
            return False
    
    def get_phone_list(self, country: str = None, page: int = 1) -> List[PhoneNumber]:
        """
        获取手机号列表
        
        Args:
            country: 国家名称 (如 'US', 'UK', 'France')
            page: 页码
        """
        if country:
            country_name = self._get_country_name(country)
            url = f"{self.BASE_URL}/temporary-phone-numbers/{country_name}"
        else:
            url = self.BASE_URL
        
        print(f"📱 正在获取 {country or '首页'} 手机号列表...")
        
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return []
        
        soup = BeautifulSoup(resp.text, 'lxml')
        phones = []
        
        # 解析手机号卡片
        for card in soup.select('div.card'):
            try:
                # 获取链接
                link = card.select_one('a.btn-primary')
                if not link:
                    continue
                
                href = link.get('href', '')
                if '/info/' not in href:
                    continue
                
                # 获取国家
                title_elem = card.select_one('h3')
                country_name = title_elem.get_text(strip=True) if title_elem else ''
                
                # 获取手机号
                phone_elem = card.select_one('p.font-weight-bold')
                phone = phone_elem.get_text(strip=True) if phone_elem else ''
                
                # 获取时间
                time_elem = card.select_one('p.small')
                last_update = time_elem.get_text(strip=True) if time_elem else ''
                
                if phone:
                    phones.append(PhoneNumber(
                        country=country_name,
                        phone=phone,
                        last_update=last_update,
                        detail_url=urljoin(self.BASE_URL, href),
                        sms_count=0
                    ))
            except Exception:
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
        print(f"📨 正在获取短信详情...")
        
        try:
            resp = self.session.get(phone_url, timeout=30)
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return None
        
        soup = BeautifulSoup(resp.text, 'lxml')
        
        # 获取手机号
        phone_elem = soup.select_one('h1.btn1')
        phone = phone_elem.get_text(strip=True) if phone_elem else ""
        
        # 获取国家
        country_link = soup.select_one('a.list_title')
        country = ""
        if country_link:
            country = country_link.get_text(strip=True).replace(' Phone Number', '')
        
        # 获取状态
        status_elem = soup.select_one('span.label-success')
        status = status_elem.get_text(strip=True) if status_elem else "Unknown"
        
        # 获取短信数量
        sms_count_elem = soup.select_one('span.badge.bg-light-blue')
        sms_count = 0
        if sms_count_elem:
            try:
                sms_count = int(sms_count_elem.get_text(strip=True))
            except:
                pass
        
        # 获取总页数
        total_pages = 1
        pagination = soup.select('ul.pagination li a')
        for link in pagination:
            href = link.get('href', '')
            match = re.search(r'_(\d+)\.html', href)
            if match:
                page_num = int(match.group(1))
                total_pages = max(total_pages, page_num)
        
        all_messages = []
        
        # 解析第一页短信
        messages = self._parse_messages(soup)
        all_messages.extend(messages)
        
        # 获取更多页
        if max_pages > 1 and total_pages > 1:
            # 从 URL 提取 phone number
            match = re.search(r'/info/(\d+)', phone_url)
            if match:
                phone_num = match.group(1)
                for page_num in range(2, min(max_pages + 1, total_pages + 1)):
                    page_url = f"{self.BASE_URL}/info/{phone_num}_{page_num}.html"
                    try:
                        resp = self.session.get(page_url, timeout=30)
                        page_soup = BeautifulSoup(resp.text, 'lxml')
                        messages = self._parse_messages(page_soup)
                        all_messages.extend(messages)
                    except:
                        break
        
        print(f"✅ 找到 {len(all_messages)} 条短信")
        
        return PhoneDetail(
            phone=phone,
            country=country,
            status=status,
            sms_count=sms_count,
            messages=all_messages,
            total_pages=total_pages
        )
    
    def _parse_messages(self, soup: BeautifulSoup) -> List[SMSMessage]:
        """解析短信列表"""
        messages = []
        
        for msg_div in soup.select('div.direct-chat-msg'):
            try:
                # 获取发送者
                sender_elem = msg_div.select_one('span.direct-chat-name')
                sender = sender_elem.get_text(strip=True) if sender_elem else ""
                
                # 获取时间
                time_elem = msg_div.select_one('time.direct-chat-timestamp')
                received_time = time_elem.get_text(strip=True) if time_elem else ""
                
                # 获取内容
                content_elem = msg_div.select_one('div.direct-chat-text')
                message = content_elem.get_text(strip=True) if content_elem else ""
                
                # 跳过广告
                if sender == "GetSMS" or "adsbygoogle" in message:
                    continue
                
                if message:
                    messages.append(SMSMessage(
                        sender=sender,
                        received_time=received_time,
                        message=message
                    ))
            except:
                continue
        
        return messages
    
    def get_messages_by_phone(self, phone: str, country: str = "US", max_pages: int = 1) -> Optional[PhoneDetail]:
        """
        通过手机号获取短信
        
        Args:
            phone: 手机号 (不含 +)
            country: 国家代码 (未使用，GetSMS.cc 只需手机号)
            max_pages: 最大页数
        """
        phone = phone.replace('+', '').replace(' ', '').strip()
        phone_url = f"{self.BASE_URL}/info/{phone}"
        return self.get_phone_messages(phone_url, max_pages)


def main():
    """测试代码"""
    api = GetSMSCCAPI()
    
    print("\n" + "="*60)
    print("  GetSMS.cc HTTP 协议爬虫")
    print("="*60)
    
    if not api.test_connection():
        return
    
    phones = api.get_phone_list("US")
    
    if phones:
        print(f"\n美国手机号 (共 {len(phones)} 个):")
        for p in phones[:3]:
            print(f"  - {p.phone} - {p.last_update}")
        
        if phones:
            detail = api.get_phone_messages(phones[0].detail_url)
            if detail:
                print(f"\n{detail.phone} 的短信 ({len(detail.messages)} 条):")
                for msg in detail.messages[:3]:
                    print(f"  - [{msg.sender}] {msg.message[:50]}...")


if __name__ == "__main__":
    main()
