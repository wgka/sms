#!/usr/bin/env python3
"""
SMSToMe.com HTTP 协议爬虫

使用 curl_cffi 模拟浏览器 TLS 指纹，绕过 Cloudflare 检测
支持保存和加载 cookies 实现持久化登录

使用方法:
1. python smstome_api.py          # 首次运行，手动获取 cookies
2. python smstome_api.py --load   # 使用保存的 cookies
"""

import json
import re
import os
import argparse
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
from urllib.parse import urljoin

from curl_cffi import requests
from bs4 import BeautifulSoup


@dataclass
class PhoneNumber:
    """手机号数据模型"""
    country: str
    phone: str
    added_time: str
    detail_url: str
    is_new: bool = False


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
    region: str
    added_time: str
    messages: List[SMSMessage]


class SMSToMeAPI:
    """SMSToMe.com HTTP API 客户端"""
    
    BASE_URL = "https://smstome.com"
    COOKIES_FILE = "smstome_cookies.json"
    ACCOUNT_FILE = "smstome_account.json"
    
    # 支持的国家 (从网站获取的实际列表)
    COUNTRIES = {
        "uk": "united-kingdom",
        "poland": "poland",
        "netherlands": "netherlands",
        "sweden": "sweden",
        "finland": "finland",
        "belgium": "belgium",
        "slovenia": "slovenia",
    }
    
    def __init__(self, auto_refresh: bool = True):
        """
        初始化 API 客户端
        
        Args:
            auto_refresh: 是否在 cookies 失效时自动刷新
        """
        # 使用 curl_cffi 模拟 Chrome 浏览器
        self.session = requests.Session(impersonate="chrome")
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        self.auto_refresh = auto_refresh
        self._refreshing = False  # 防止递归刷新
    
    def save_cookies(self, filename: str = None):
        """保存 cookies 到文件"""
        filename = filename or self.COOKIES_FILE
        cookies_dict = dict(self.session.cookies)
        with open(filename, 'w') as f:
            json.dump(cookies_dict, f, indent=2)
        print(f"💾 Cookies 已保存到 {filename}")
    
    def load_cookies(self, filename: str = None) -> bool:
        """从文件加载 cookies"""
        filename = filename or self.COOKIES_FILE
        try:
            with open(filename, 'r') as f:
                cookies_dict = json.load(f)
            
            # 过滤掉注释和说明字段
            skip_keys = ['_comment', '_instructions']
            loaded_count = 0
            
            for name, value in cookies_dict.items():
                if name in skip_keys:
                    continue
                # 跳过占位符值
                if isinstance(value, str) and ('在这里粘贴' in value or 'paste' in value.lower()):
                    continue
                self.session.cookies.set(name, value)
                loaded_count += 1
            
            if loaded_count > 0:
                print(f"🍪 已加载 {loaded_count} 个 cookies")
                return True
            else:
                print(f"⚠️  {filename} 中没有有效的 cookies")
                return False
        except FileNotFoundError:
            print(f"⚠️  未找到 {filename}")
            return False
        except Exception as e:
            print(f"⚠️  加载 cookies 失败: {e}")
            return False
    
    def set_cookies_from_string(self, cookie_string: str):
        """
        从浏览器复制的 cookie 字符串设置 cookies
        
        格式: "name1=value1; name2=value2; ..."
        """
        for item in cookie_string.split(';'):
            item = item.strip()
            if '=' in item:
                name, value = item.split('=', 1)
                self.session.cookies.set(name.strip(), value.strip())
        print("🍪 已设置 cookies")
    
    def set_cookies_from_dict(self, cookies: Dict[str, str]):
        """从字典设置 cookies"""
        for name, value in cookies.items():
            self.session.cookies.set(name, value)
        print("🍪 已设置 cookies")
    
    def load_account(self) -> Dict[str, str]:
        """加载保存的账号信息"""
        try:
            with open(self.ACCOUNT_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def save_account(self, email: str, password: str):
        """保存账号信息"""
        with open(self.ACCOUNT_FILE, 'w') as f:
            json.dump({'email': email, 'password': password}, f, indent=2)
    
    def auto_login(self, email: str = None, password: str = None) -> bool:
        """
        自动登录获取 cookies
        
        Args:
            email: 邮箱，如果不提供则从保存的账号读取
            password: 密码，如果不提供则从保存的账号读取
        
        Returns:
            是否登录成功
        """
        from urllib.parse import unquote
        
        # 如果没有提供账号，从文件加载
        if not email or not password:
            account = self.load_account()
            email = email or account.get('email')
            password = password or account.get('password')
        
        if not email or not password:
            print("⚠️  没有保存的账号信息，无法自动登录")
            return False
        
        print(f"🔄 自动登录中... ({email})")
        
        try:
            # 创建新 session 用于登录
            login_session = requests.Session(impersonate="chrome")
            
            # Step 1: 获取登录页面
            resp = login_session.get(f"{self.BASE_URL}/sign-in", timeout=30)
            
            if resp.status_code != 200:
                print(f"❌ 获取登录页面失败: {resp.status_code}")
                return False
            
            if "checking your browser" in resp.text.lower():
                print("❌ 遇到 Cloudflare 挑战")
                return False
            
            soup = BeautifulSoup(resp.text, 'lxml')
            
            # 获取表单字段
            token_input = soup.find('input', {'name': '_token'})
            csrf_token = token_input.get('value') if token_input else None
            
            csrf_v_input = soup.find('input', {'name': 'csrf_v'})
            csrf_v = csrf_v_input.get('value') if csrf_v_input else None
            
            xsrf_cookie = login_session.cookies.get('XSRF-TOKEN')
            
            # 解析验证问题
            match = re.search(r'What is (\d+) \+ (\d+)', resp.text)
            answer = int(match.group(1)) + int(match.group(2)) if match else 9
            
            # Step 2: 提交登录
            login_data = {
                '_token': csrf_token,
                'csrf_v': csrf_v,
                'email': email,
                'password': password,
                'captcha': str(answer),
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': self.BASE_URL,
                'Referer': f'{self.BASE_URL}/sign-in',
            }
            
            if xsrf_cookie:
                headers['X-XSRF-TOKEN'] = unquote(xsrf_cookie)
            
            resp = login_session.post(
                f"{self.BASE_URL}/sign-in",
                data=login_data,
                headers=headers,
                timeout=30,
                allow_redirects=True
            )
            
            # 检查登录是否成功
            if "Hi," not in resp.text:
                print("❌ 登录失败，请检查账号密码")
                return False
            
            # 提取用户名
            username_match = re.search(r'Hi,\s*(\w+)', resp.text)
            username = username_match.group(1) if username_match else '未知'
            print(f"✅ 登录成功! 用户: {username}")
            
            # 更新 cookies 到主 session
            all_cookies = dict(login_session.cookies)
            
            self.session.cookies.clear()
            for name, value in all_cookies.items():
                self.session.cookies.set(name, value)
            
            # 保存 cookies
            self.save_cookies()
            
            return True
            
        except Exception as e:
            print(f"❌ 自动登录出错: {e}")
            return False
    
    def refresh_cookies_if_needed(self, response_text: str) -> bool:
        """
        检测是否需要刷新 cookies，如果需要则自动刷新
        
        Args:
            response_text: 响应文本
        
        Returns:
            是否刷新成功
        """
        if not self.auto_refresh or self._refreshing:
            return False
        
        # 检测 cookies 失效的特征
        needs_refresh = any([
            "Required To Register Or Log In" in response_text,
            "Please login" in response_text,
            "you have been blocked" in response_text.lower(),
            "checking your browser" in response_text.lower(),
        ])
        
        if needs_refresh:
            print("⚠️  检测到 Cookies 失效，尝试自动刷新...")
            self._refreshing = True
            success = self.auto_login()
            self._refreshing = False
            return success
        
        return False
    
    def test_connection(self) -> bool:
        """测试连接是否正常"""
        try:
            resp = self.session.get(self.BASE_URL, timeout=30)
            if resp.status_code == 200:
                if "you have been blocked" in resp.text.lower():
                    print("❌ 被 Cloudflare 封锁")
                    return False
                if "checking your browser" in resp.text.lower():
                    print("❌ 遇到 Cloudflare 挑战")
                    return False
                if "Receive SMS Online" in resp.text:
                    print("✅ 连接正常")
                    return True
                print("⚠️  页面内容异常")
                return False
            else:
                print(f"❌ 状态码: {resp.status_code}")
                return False
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    def debug_request(self, url: str):
        """调试请求，输出响应信息"""
        try:
            resp = self.session.get(url, timeout=30)
            print(f"URL: {url}")
            print(f"状态码: {resp.status_code}")
            print(f"响应长度: {len(resp.text)}")
            print(f"前500字符:\n{resp.text[:500]}")
            return resp
        except Exception as e:
            print(f"请求失败: {e}")
            return None
    
    def get_phone_list(self, country: str, page: int = 1) -> List[PhoneNumber]:
        """
        获取指定国家的手机号列表
        
        Args:
            country: 国家代码 (如 'uk', 'poland') 或完整名称 (如 'united-kingdom')
            page: 页码
        
        Returns:
            手机号列表
        """
        # 转换国家代码
        country_slug = self.COUNTRIES.get(country.lower(), country.lower())
        
        url = f"{self.BASE_URL}/country/{country_slug}"
        if page > 1:
            url += f"?page={page}"
        
        print(f"📱 正在获取 {country_slug} 第 {page} 页...")
        
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return []
        
        # 检查是否需要登录，如果是则自动刷新 cookies 并重试
        if "Required To Register Or Log In" in resp.text:
            print(f"⚠️  {country_slug} 需要登录才能访问")
            if self.refresh_cookies_if_needed(resp.text):
                # 刷新成功，重新请求
                print("🔄 重新获取数据...")
                try:
                    resp = self.session.get(url, timeout=30)
                except Exception as e:
                    print(f"❌ 重试请求失败: {e}")
                    return []
            else:
                return []
        
        # 检查是否被封锁
        if "you have been blocked" in resp.text.lower():
            print("❌ 被 Cloudflare 封锁")
            if self.refresh_cookies_if_needed(resp.text):
                print("🔄 重新获取数据...")
                try:
                    resp = self.session.get(url, timeout=30)
                except:
                    return []
            else:
                return []
        
        # 检查是否是挑战页面
        if "checking your browser" in resp.text.lower() or "just a moment" in resp.text.lower():
            print("❌ 遇到 Cloudflare 挑战")
            if self.refresh_cookies_if_needed(resp.text):
                print("🔄 重新获取数据...")
                try:
                    resp = self.session.get(url, timeout=30)
                except:
                    return []
            else:
                return []
        
        soup = BeautifulSoup(resp.text, 'lxml')
        phones = []
        
        # 查找所有手机号文章
        articles = soup.find_all('article')
        
        for article in articles:
            try:
                # 获取手机号链接
                link = article.find('a')
                if not link:
                    continue
                
                phone_text = link.get_text(strip=True)
                phone_href = link.get('href', '')
                
                # 获取添加时间
                time_text = ""
                is_new = False
                
                # 查找包含时间的 div
                for div in article.find_all('div'):
                    text = div.get_text(strip=True)
                    if 'Added' in text or 'ago' in text:
                        if 'NEW' in text:
                            is_new = True
                            time_text = text.replace('NEW', '').strip()
                        else:
                            time_text = text
                        break
                
                phones.append(PhoneNumber(
                    country=country_slug,
                    phone=phone_text,
                    added_time=time_text,
                    detail_url=urljoin(self.BASE_URL, phone_href),
                    is_new=is_new
                ))
            except Exception as e:
                continue
        
        print(f"✅ 找到 {len(phones)} 个手机号")
        return phones
    
    def get_total_pages(self, country: str) -> int:
        """获取指定国家的总页数"""
        country_slug = self.COUNTRIES.get(country.lower(), country.lower())
        url = f"{self.BASE_URL}/country/{country_slug}"
        
        try:
            resp = self.session.get(url, timeout=30)
            soup = BeautifulSoup(resp.text, 'lxml')
            
            # 查找分页链接
            max_page = 1
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'page=' in href:
                    match = re.search(r'page=(\d+)', href)
                    if match:
                        page_num = int(match.group(1))
                        max_page = max(max_page, page_num)
            
            return max_page
        except Exception as e:
            print(f"❌ 获取页数失败: {e}")
            return 1
    
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
            # 不检查状态码，因为有些页面返回404但内容有效
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return None
        
        # 检查是否有有效内容
        if "Phone Number" not in resp.text and "table" not in resp.text:
            print(f"❌ 页面无有效内容")
            return None
        
        if "blocked" in resp.text.lower():
            print("❌ 被封锁")
            return None
        
        soup = BeautifulSoup(resp.text, 'lxml')
        
        # 获取基本信息
        h1 = soup.find('h1')
        heading_text = h1.get_text(strip=True) if h1 else ""
        
        phone_match = re.search(r'\+?\d+', heading_text)
        phone = phone_match.group(0) if phone_match else ""
        
        # 获取地区和时间
        info_p = soup.find('p')
        info_text = info_p.get_text(strip=True) if info_p else ""
        
        region_match = re.search(r'Region:\s*(\w+)', info_text)
        region = region_match.group(1) if region_match else ""
        
        time_match = re.search(r'Added:\s*(.+)', info_text)
        added_time = time_match.group(1).strip() if time_match else ""
        
        # 获取国家
        country_match = re.search(r'smstome\.com/([^/]+)/phone', phone_url)
        country = country_match.group(1) if country_match else ""
        
        all_messages = []
        
        for page_num in range(1, max_pages + 1):
            if page_num > 1:
                page_url = f"{phone_url}?page={page_num}"
                try:
                    resp = self.session.get(page_url, timeout=30)
                    soup = BeautifulSoup(resp.text, 'lxml')
                except:
                    break
            
            # 获取短信表格
            table = soup.find('table')
            if table:
                tbody = table.find('tbody')
                if tbody:
                    for row in tbody.find_all('tr'):
                        cells = row.find_all('td')
                        if len(cells) >= 3:
                            sender = cells[0].get_text(strip=True)
                            received = cells[1].get_text(strip=True)
                            message = cells[2].get_text(strip=True)
                            
                            if sender and message:
                                all_messages.append(SMSMessage(
                                    sender=sender,
                                    received_time=received,
                                    message=message
                                ))
        
        print(f"✅ 找到 {len(all_messages)} 条短信")
        
        return PhoneDetail(
            phone=phone,
            country=country,
            region=region,
            added_time=added_time,
            messages=all_messages
        )
    
    def get_all_phones(self, country: str, max_pages: Optional[int] = None) -> List[PhoneNumber]:
        """获取指定国家所有页的手机号"""
        total_pages = self.get_total_pages(country)
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        print(f"📊 共 {total_pages} 页")
        
        all_phones = []
        for page in range(1, total_pages + 1):
            phones = self.get_phone_list(country, page)
            all_phones.extend(phones)
        
        return all_phones
    
    @staticmethod
    def save_to_json(data, filename: str):
        """保存数据到 JSON 文件"""
        def convert(obj):
            if hasattr(obj, '__dataclass_fields__'):
                return asdict(obj)
            return obj
        
        with open(filename, 'w', encoding='utf-8') as f:
            if isinstance(data, list):
                json.dump([convert(item) for item in data], f, ensure_ascii=False, indent=2)
            else:
                json.dump(convert(data), f, ensure_ascii=False, indent=2)
        
        print(f"💾 数据已保存到 {filename}")


def interactive_cookie_setup(api: SMSToMeAPI):
    """交互式设置 cookies"""
    print("\n" + "="*60)
    print("  Cookie 设置向导")
    print("="*60)
    print("""
请按以下步骤获取 cookies:

1. 在浏览器中打开 https://smstome.com
2. 完成 Cloudflare 验证（如果有）
3. 登录账号（UK/France 需要登录）
4. 按 F12 打开开发者工具
5. 切换到 "Application" (应用) 标签
6. 左侧找到 Cookies -> https://smstome.com
7. 复制所有 cookie（可以右键 -> Copy all as cURL）

或者直接复制 cookie 字符串（格式: name1=value1; name2=value2）
""")
    
    print("\n请粘贴 cookie 字符串 (输入完成后按两次 Enter):")
    
    lines = []
    while True:
        line = input()
        if line:
            lines.append(line)
        else:
            break
    
    cookie_string = ' '.join(lines)
    
    if cookie_string.strip():
        api.set_cookies_from_string(cookie_string)
        api.save_cookies()
        return True
    else:
        print("❌ 未输入 cookies")
        return False


def main():
    parser = argparse.ArgumentParser(description='SMSToMe.com 爬虫')
    parser.add_argument('--load', action='store_true', help='加载保存的 cookies')
    parser.add_argument('--setup', action='store_true', help='设置 cookies')
    parser.add_argument('--country', default='uk', help='国家代码 (uk, poland, sweden, etc.)')
    parser.add_argument('--pages', type=int, default=1, help='获取页数')
    parser.add_argument('--phone', type=str, help='获取指定手机号的短信 (如: 447454410449 或 +447454410449)')
    parser.add_argument('--sms-pages', type=int, default=1, help='获取短信的页数')
    parser.add_argument('--url', type=str, help='直接指定手机号详情页 URL')
    parser.add_argument('--search-pages', type=int, default=0, help='搜索手机号时最多搜索的页数 (0=无限制，自动搜索到最后一页)')
    args = parser.parse_args()
    
    api = SMSToMeAPI()
    
    print("\n" + "="*60)
    print("  SMSToMe.com HTTP 协议爬虫")
    print("="*60)
    
    # 尝试加载 cookies
    if args.load or os.path.exists(api.COOKIES_FILE):
        api.load_cookies()
    
    # 设置 cookies
    if args.setup:
        interactive_cookie_setup(api)
    
    # 测试连接
    print("\n🔗 测试连接...")
    if not api.test_connection():
        print("\n需要设置 cookies，启动设置向导...")
        if not interactive_cookie_setup(api):
            return
        
        if not api.test_connection():
            print("❌ 连接仍然失败，请检查 cookies")
            return
    
    # 如果直接指定了 URL
    if args.url:
        print(f"\n📱 直接访问 URL...")
        detail = api.get_phone_messages(args.url, max_pages=args.sms_pages)
        
        if detail and detail.messages:
            print(f"\n📞 手机号: {detail.phone}")
            print(f"📍 国家: {detail.country}")
            print(f"⏰ 添加时间: {detail.added_time}")
            print(f"📨 短信数量: {len(detail.messages)}")
            
            print("\n所有短信:")
            for i, msg in enumerate(detail.messages, 1):
                print(f"\n   [{i}] 📨 来自: {msg.sender}")
                print(f"       时间: {msg.received_time}")
                print(f"       内容: {msg.message}")
        else:
            print("❌ 未获取到短信")
        return
    
    # 如果指定了手机号，直接获取该手机号的短信
    if args.phone:
        phone = args.phone.replace('+', '').strip()
        country_slug = api.COUNTRIES.get(args.country.lower(), args.country.lower())
        
        import glob
        phone_url = None
        cache_file = "phone_url_cache.json"
        
        # 1. 先从 URL 缓存文件查找
        try:
            with open(cache_file, 'r') as f:
                url_cache = json.load(f)
            if phone in url_cache:
                phone_url = url_cache[phone]
                print(f"📱 从缓存找到手机号 +{phone}")
        except:
            url_cache = {}
        
        # 2. 从 phones_*.json 文件查找
        if not phone_url:
            for json_file in glob.glob("phones_*.json"):
                try:
                    with open(json_file, 'r') as f:
                        phones_data = json.load(f)
                    for p in phones_data:
                        if phone in p.get('phone', '').replace('+', ''):
                            phone_url = p.get('detail_url')
                            print(f"📱 从缓存找到手机号 +{phone}")
                            break
                    if phone_url:
                        break
                except:
                    continue
        
        # 3. 如果缓存都没有，搜索页面查找
        if not phone_url:
            print(f"📱 正在搜索手机号 +{phone}...")
            max_search_pages = args.search_pages  # 0 表示无限制
            phones_per_page = 20  # 每页正常应有的手机号数量
            page_num = 0
            
            while True:
                page_num += 1
                
                # 如果设置了限制且超过限制，停止
                if max_search_pages > 0 and page_num > max_search_pages:
                    break
                
                phones = api.get_phone_list(args.country, page=page_num)
                
                # 如果页面没有手机号，停止
                if not phones:
                    print(f"   📄 第 {page_num} 页无数据，搜索结束")
                    break
                
                # 检查是否找到
                for p in phones:
                    if phone in p.phone.replace('+', ''):
                        phone_url = p.detail_url
                        print(f"   ✅ 在第 {page_num} 页找到!")
                        break
                
                if phone_url:
                    break
                
                # 如果这页手机号数量不足，说明是最后一页
                if len(phones) < phones_per_page:
                    print(f"   📄 第 {page_num} 页仅有 {len(phones)} 个号码，已到最后一页")
                    break
                
                if page_num % 10 == 0:
                    print(f"   已搜索 {page_num} 页...")
        
        # 4. 保存到缓存
        if phone_url:
            url_cache[phone] = phone_url
            with open(cache_file, 'w') as f:
                json.dump(url_cache, f, indent=2)
            print(f"   💾 已缓存 URL")
        
        if phone_url:
            print(f"\n📱 获取手机号 +{phone} 的短信...")
            detail = api.get_phone_messages(phone_url, max_pages=args.sms_pages)
            
            if detail and detail.messages:
                print(f"\n📞 手机号: {detail.phone}")
                print(f"📍 国家: {detail.country}")
                print(f"⏰ 添加时间: {detail.added_time}")
                print(f"📨 短信数量: {len(detail.messages)}")
                
                print("\n所有短信:")
                for i, msg in enumerate(detail.messages, 1):
                    print(f"\n   [{i}] 📨 来自: {msg.sender}")
                    print(f"       时间: {msg.received_time}")
                    print(f"       内容: {msg.message}")
            else:
                print("❌ 未获取到短信")
        else:
            print(f"❌ 未找到手机号 {phone}")
        return
    
    # 获取手机号列表
    print(f"\n📱 获取 {args.country} 的手机号...")
    phones = api.get_phone_list(args.country, page=1)
    
    if phones:
        print("\n📱 手机号列表:")
        for i, phone in enumerate(phones[:10], 1):
            new_tag = "🆕 " if phone.is_new else ""
            print(f"   {i}. {new_tag}{phone.phone} - {phone.added_time}")
        
        print(f"\n共 {len(phones)} 个手机号 (第 1 页)")
    else:
        print("❌ 未获取到手机号")
        print("\n可能原因:")
        print("  1. Cookies 已过期，需要重新设置")
        print("  2. 该国家需要登录 (UK/France)")
        print("  3. 网络问题")
        print("\n运行 'python smstome_api.py --setup' 重新设置 cookies")


if __name__ == "__main__":
    main()
