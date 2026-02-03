#!/usr/bin/env python3
"""
SMSToMe.com HTTP API 服务

提供 RESTful API 接口获取手机号列表和短信
"""

import json
import os
from typing import Optional, List
from dataclasses import asdict

from flask import Flask, jsonify, request
from flask_cors import CORS
from smstome_api import SMSToMeAPI, PhoneNumber

app = Flask(__name__)
CORS(app)  # 启用跨域支持

# 全局 API 实例 (启用自动刷新)
api = SMSToMeAPI(auto_refresh=True)
CACHE_FILE = "phone_url_cache.json"
PHONES_PER_PAGE = 20  # 每页手机号数量


def load_url_cache() -> dict:
    """加载 URL 缓存"""
    try:
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}


def save_url_cache(cache: dict):
    """保存 URL 缓存"""
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def search_phone_all_pages(country: str, phone: str) -> Optional[str]:
    """
    搜索手机号，遍历所有页面直到找到或页面没有足够数量的手机号
    
    Args:
        country: 国家代码
        phone: 手机号 (不含+)
    
    Returns:
        手机号详情页 URL，未找到返回 None
    """
    print(f"🔍 开始搜索手机号 {phone}，国家: {country}")
    page_num = 0
    total_phones_checked = 0
    
    while True:
        page_num += 1
        print(f"   📱 正在搜索第 {page_num} 页...")
        
        phones = api.get_phone_list(country, page=page_num)
        
        if not phones:
            print(f"   ⚠️ 第 {page_num} 页无数据")
            # 如果第一页就没数据，可能是网络问题，不要立即放弃
            if page_num == 1:
                print(f"   ❌ 无法获取手机号列表，请检查网络或 cookies")
            break
        
        total_phones_checked += len(phones)
        
        # 检查是否找到
        for p in phones:
            if phone in p.phone.replace('+', ''):
                print(f"   ✅ 在第 {page_num} 页找到!")
                return p.detail_url
        
        # 如果这页手机号不足 PHONES_PER_PAGE，说明已经是最后一页
        if len(phones) < PHONES_PER_PAGE:
            print(f"   📄 第 {page_num} 页仅有 {len(phones)} 个号码，已到最后一页")
            break
        
        # 每10页输出进度
        if page_num % 10 == 0:
            print(f"   已搜索 {page_num} 页，共检查 {total_phones_checked} 个号码...")
    
    print(f"   ❌ 搜索完成，共检查 {total_phones_checked} 个号码，未找到 {phone}")
    return None


def find_phone_url(country: str, phone: str) -> Optional[str]:
    """
    查找手机号的详情页 URL
    
    优先级:
    1. URL 缓存
    2. 搜索所有页面
    """
    phone = phone.replace('+', '').strip()
    
    # 转换国家代码
    country_slug = api.COUNTRIES.get(country.lower(), country.lower())
    print(f"📱 查找手机号: {phone}, 国家: {country} -> {country_slug}")
    
    # 1. 从缓存查找
    cache = load_url_cache()
    if phone in cache:
        print(f"   ✅ 从缓存找到")
        return cache[phone]
    
    print(f"   📭 缓存未命中，开始搜索...")
    
    # 2. 搜索所有页面
    url = search_phone_all_pages(country_slug, phone)
    
    if url:
        # 保存到缓存
        cache[phone] = url
        save_url_cache(cache)
        print(f"   💾 已缓存 URL")
    
    return url


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    connected = api.test_connection()
    return jsonify({
        'status': 'ok' if connected else 'error',
        'connected': connected
    })


@app.route('/api/countries', methods=['GET'])
def get_countries():
    """获取支持的国家列表"""
    return jsonify({
        'countries': list(api.COUNTRIES.keys()),
        'country_slugs': api.COUNTRIES
    })


@app.route('/api/phones/<country>', methods=['GET'])
def get_phone_list(country: str):
    """
    获取指定国家的手机号列表
    
    Query params:
        page: 页码 (默认 1)
        pages: 页码数组，如 1,2,3 或 1-5 (可选)
        all: 是否获取所有页 (默认 false)
    """
    page = request.args.get('page', 1, type=int)
    pages_param = request.args.get('pages', '')
    get_all = request.args.get('all', 'false').lower() == 'true'
    
    country_slug = api.COUNTRIES.get(country.lower(), country.lower())
    
    # 解析 pages 参数
    pages_to_fetch = []
    if pages_param:
        for part in pages_param.split(','):
            part = part.strip()
            if '-' in part:
                # 范围格式: 1-5
                start, end = part.split('-', 1)
                pages_to_fetch.extend(range(int(start), int(end) + 1))
            else:
                pages_to_fetch.append(int(part))
    
    if get_all:
        # 获取所有页的手机号
        all_phones = []
        page_num = 1
        
        while True:
            phones = api.get_phone_list(country_slug, page=page_num)
            all_phones.extend(phones)
            
            if len(phones) < PHONES_PER_PAGE:
                break
            
            page_num += 1
        
        return jsonify({
            'country': country_slug,
            'total_phones': len(all_phones),
            'total_pages': page_num,
            'phones': [asdict(p) for p in all_phones]
        })
    elif pages_to_fetch:
        # 获取指定的多页
        all_phones = []
        fetched_pages = []
        
        for p in pages_to_fetch:
            phones = api.get_phone_list(country_slug, page=p)
            if phones:
                all_phones.extend(phones)
                fetched_pages.append(p)
        
        return jsonify({
            'country': country_slug,
            'pages': fetched_pages,
            'total_phones': len(all_phones),
            'phones': [asdict(p) for p in all_phones]
        })
    else:
        # 获取单页
        phones = api.get_phone_list(country_slug, page=page)
        
        return jsonify({
            'country': country_slug,
            'page': page,
            'count': len(phones),
            'has_more': len(phones) >= PHONES_PER_PAGE,
            'phones': [asdict(p) for p in phones]
        })


@app.route('/api/phones', methods=['GET', 'POST'])
def get_phones_batch():
    """
    批量获取手机号列表
    
    GET Query params:
        country: 国家代码，多个用逗号分隔 (默认 uk)
        pages: 页码，如 1 或 1,2,3 或 1-5 (默认 1)
    
    POST JSON body:
        {
            "countries": ["uk", "poland"],  // 可选，默认 ["uk"]
            "pages": [1, 2, 3]              // 可选，默认 [1]
        }
    """
    if request.method == 'POST':
        data = request.get_json() or {}
        countries = data.get('countries', ['uk'])
        pages = data.get('pages', [1])
    else:
        # GET 请求
        countries_param = request.args.get('country', 'uk')
        countries = [c.strip() for c in countries_param.split(',')]
        
        pages_param = request.args.get('pages', '1')
        pages = []
        for part in pages_param.split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-', 1)
                pages.extend(range(int(start), int(end) + 1))
            else:
                pages.append(int(part))
    
    result = {}
    total_phones = 0
    
    for country in countries:
        country_slug = api.COUNTRIES.get(country.lower(), country.lower())
        country_phones = []
        
        for page in pages:
            phones = api.get_phone_list(country_slug, page=page)
            country_phones.extend(phones)
        
        result[country_slug] = [asdict(p) for p in country_phones]
        total_phones += len(country_phones)
    
    return jsonify({
        'total_phones': total_phones,
        'countries': list(result.keys()),
        'pages': pages,
        'data': result
    })


@app.route('/api/phone/<phone>/sms', methods=['GET'])
def get_phone_sms(phone: str):
    """
    获取指定手机号的短信
    
    Query params:
        country: 国家代码 (默认 uk)
        pages: 短信页数 (默认 1)
        limit: 返回短信条数限制 (默认返回全部)
        latest: 是否只返回最新一条 (默认 false)
    """
    country = request.args.get('country', 'uk')
    sms_pages = request.args.get('pages', 1, type=int)
    limit = request.args.get('limit', 0, type=int)  # 0 表示不限制
    latest = request.args.get('latest', 'false').lower() == 'true'
    
    phone = phone.replace('+', '').strip()
    
    # 查找手机号 URL
    phone_url = find_phone_url(country, phone)
    
    if not phone_url:
        return jsonify({
            'error': 'Phone not found',
            'phone': phone,
            'country': country
        }), 404
    
    # 获取短信
    detail = api.get_phone_messages(phone_url, max_pages=sms_pages)
    
    if not detail:
        return jsonify({
            'error': 'Failed to get SMS',
            'phone': phone,
            'phone_url': phone_url
        }), 500
    
    messages = detail.messages
    
    # 处理 latest 参数
    if latest:
        messages = messages[:1] if messages else []
    # 处理 limit 参数
    elif limit > 0:
        messages = messages[:limit]
    
    return jsonify({
        'phone': detail.phone,
        'country': detail.country,
        'region': detail.region,
        'added_time': detail.added_time,
        'sms_count': len(messages),
        'total_sms': len(detail.messages),
        'messages': [asdict(m) for m in messages]
    })


@app.route('/api/sms/<phone>', methods=['GET'])
def get_sms_simple(phone: str):
    """
    简化的短信获取接口
    
    Query params:
        country: 国家代码 (默认 uk)
        limit: 返回短信条数 (默认 1，即最新一条)
    
    示例:
        GET /api/sms/447454414630           -> 返回最新 1 条
        GET /api/sms/447454414630?limit=5   -> 返回最新 5 条
        GET /api/sms/447454414630?limit=0   -> 返回全部
    """
    country = request.args.get('country', 'uk')
    limit = request.args.get('limit', 1, type=int)  # 默认 1 条
    
    phone = phone.replace('+', '').strip()
    
    # 查找手机号 URL
    phone_url = find_phone_url(country, phone)
    
    if not phone_url:
        return jsonify({
            'error': 'Phone not found',
            'phone': phone,
            'country': country
        }), 404
    
    # 获取短信 (如果只要少量短信，只获取第一页)
    max_pages = 1 if limit > 0 and limit <= 20 else 5
    detail = api.get_phone_messages(phone_url, max_pages=max_pages)
    
    if not detail:
        return jsonify({
            'error': 'Failed to get SMS',
            'phone': phone
        }), 500
    
    messages = detail.messages
    
    # 处理 limit
    if limit > 0:
        messages = messages[:limit]
    
    # 简化返回格式
    return jsonify({
        'phone': phone,
        'count': len(messages),
        'messages': [
            {
                'sender': m.sender,
                'time': m.received_time,
                'content': m.message
            } for m in messages
        ]
    })


@app.route('/api/search/<country>/<phone>', methods=['GET'])
def search_phone(country: str, phone: str):
    """
    搜索手机号
    
    Returns:
        手机号信息和详情页 URL
    """
    phone = phone.replace('+', '').strip()
    country_slug = api.COUNTRIES.get(country.lower(), country.lower())
    
    # 查找 URL
    phone_url = find_phone_url(country, phone)
    
    if phone_url:
        return jsonify({
            'found': True,
            'phone': phone,
            'country': country_slug,
            'detail_url': phone_url
        })
    else:
        return jsonify({
            'found': False,
            'phone': phone,
            'country': country_slug
        }), 404


@app.route('/api/cache', methods=['GET'])
def get_cache():
    """获取 URL 缓存"""
    return jsonify(load_url_cache())


@app.route('/api/cache/<phone>', methods=['DELETE'])
def delete_cache(phone: str):
    """删除指定手机号的缓存"""
    phone = phone.replace('+', '').strip()
    cache = load_url_cache()
    
    if phone in cache:
        del cache[phone]
        save_url_cache(cache)
        return jsonify({'deleted': True, 'phone': phone})
    
    return jsonify({'deleted': False, 'phone': phone}), 404


@app.route('/api/cookies', methods=['GET'])
def get_cookies():
    """获取当前 cookies 配置"""
    try:
        with open(api.COOKIES_FILE, 'r') as f:
            cookies = json.load(f)
        # 隐藏部分值
        masked = {}
        for key, value in cookies.items():
            if key.startswith('_'):
                continue
            if isinstance(value, str) and len(value) > 20:
                masked[key] = value[:10] + '...' + value[-10:]
            else:
                masked[key] = value
        return jsonify({
            'cookies': masked,
            'cookie_count': len([k for k in cookies if not k.startswith('_')])
        })
    except:
        return jsonify({'cookies': {}, 'cookie_count': 0})


@app.route('/api/cookies', methods=['POST'])
def set_cookies():
    """设置 cookies"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    cookies = {}
    
    # 支持两种格式：
    # 1. { "cf_clearance": "xxx", "smstome_session": "xxx" }
    # 2. { "cookie_string": "cf_clearance=xxx; smstome_session=xxx" }
    
    if 'cookie_string' in data:
        # 解析 cookie 字符串
        cookie_str = data['cookie_string']
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                name, value = item.split('=', 1)
                cookies[name.strip()] = value.strip()
    else:
        # 直接使用提供的 cookies
        cookies = {k: v for k, v in data.items() if v and not k.startswith('_')}
    
    if not cookies:
        return jsonify({'error': 'No valid cookies provided'}), 400
    
    # 保存到文件
    try:
        with open(api.COOKIES_FILE, 'w') as f:
            json.dump(cookies, f, indent=2)
    except Exception as e:
        return jsonify({'error': f'Failed to save cookies: {str(e)}'}), 500
    
    # 重新加载 cookies 到 session
    api.session.cookies.clear()
    for name, value in cookies.items():
        api.session.cookies.set(name, value)
    
    # 测试连接
    connected = api.test_connection()
    
    return jsonify({
        'success': True,
        'cookie_count': len(cookies),
        'connected': connected
    })


@app.route('/api/cookies/test', methods=['GET'])
def test_cookies():
    """测试当前 cookies 是否有效"""
    connected = api.test_connection()
    return jsonify({
        'connected': connected,
        'message': '连接正常' if connected else 'Cookies 已失效，请更新'
    })


@app.route('/api/login', methods=['POST'])
def login_and_refresh_cookies():
    """
    使用账号密码登录并刷新 cookies
    
    Request body:
        email: 登录邮箱
        password: 登录密码
    """
    import re
    from urllib.parse import unquote
    from curl_cffi import requests as curl_requests
    from bs4 import BeautifulSoup
    
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': '请提供邮箱和密码'}), 400
    
    email = data['email']
    password = data['password']
    
    try:
        session = curl_requests.Session(impersonate="chrome")
        
        # Step 1: 获取登录页面
        resp = session.get("https://smstome.com/sign-in", timeout=30)
        
        if resp.status_code != 200:
            return jsonify({'error': f'获取登录页面失败: {resp.status_code}'}), 500
        
        # 检查 Cloudflare 挑战
        if "checking your browser" in resp.text.lower() or "just a moment" in resp.text.lower():
            return jsonify({'error': '遇到 Cloudflare 挑战，请稍后重试'}), 503
        
        soup = BeautifulSoup(resp.text, 'lxml')
        
        # 获取表单字段
        token_input = soup.find('input', {'name': '_token'})
        csrf_token = token_input.get('value') if token_input else None
        
        csrf_v_input = soup.find('input', {'name': 'csrf_v'})
        csrf_v = csrf_v_input.get('value') if csrf_v_input else None
        
        xsrf_cookie = session.cookies.get('XSRF-TOKEN')
        
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
            'Origin': 'https://smstome.com',
            'Referer': 'https://smstome.com/sign-in',
        }
        
        if xsrf_cookie:
            headers['X-XSRF-TOKEN'] = unquote(xsrf_cookie)
        
        resp = session.post(
            "https://smstome.com/sign-in",
            data=login_data,
            headers=headers,
            timeout=30,
            allow_redirects=True
        )
        
        # 检查登录是否成功
        if "Hi," not in resp.text:
            # 解析错误信息
            soup2 = BeautifulSoup(resp.text, 'lxml')
            errors = soup2.find_all(class_='alert')
            error_msg = errors[0].get_text().strip() if errors else '登录失败，请检查账号密码'
            return jsonify({'error': error_msg}), 401
        
        # 提取用户名
        username_match = re.search(r'Hi,\s*(\w+)', resp.text)
        username = username_match.group(1) if username_match else '未知'
        
        # 获取所有 cookies
        all_cookies = dict(session.cookies)
        
        # 保存到文件
        with open(api.COOKIES_FILE, 'w') as f:
            json.dump(all_cookies, f, indent=2)
        
        # 重新加载到 API session
        api.session.cookies.clear()
        for name, value in all_cookies.items():
            api.session.cookies.set(name, value)
        
        # 测试连接
        connected = api.test_connection()
        
        return jsonify({
            'success': True,
            'username': username,
            'cookie_count': len(all_cookies),
            'connected': connected,
            'message': f'登录成功！欢迎 {username}'
        })
        
    except Exception as e:
        return jsonify({'error': f'登录出错: {str(e)}'}), 500


@app.route('/api/account', methods=['GET'])
def get_account():
    """获取保存的账号信息"""
    account_file = 'smstome_account.json'
    try:
        with open(account_file, 'r') as f:
            account = json.load(f)
        # 隐藏密码
        if 'password' in account:
            account['password'] = '*' * len(account['password'])
        # 添加自动刷新状态
        account['auto_refresh_enabled'] = api.auto_refresh
        account['has_account'] = bool(account.get('email'))
        return jsonify(account)
    except:
        return jsonify({
            'email': '', 
            'password': '',
            'auto_refresh_enabled': api.auto_refresh,
            'has_account': False
        })


@app.route('/api/account', methods=['POST'])
def save_account():
    """保存账号信息"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    account_file = 'smstome_account.json'
    
    # 如果密码是掩码，保留原密码
    if data.get('password', '').startswith('*'):
        try:
            with open(account_file, 'r') as f:
                old_account = json.load(f)
            data['password'] = old_account.get('password', '')
        except:
            pass
    
    with open(account_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    return jsonify({'success': True})


def init_api():
    """初始化 API"""
    # 加载 cookies
    if os.path.exists(api.COOKIES_FILE):
        api.load_cookies()
    
    # 测试连接
    print("\n🔗 测试连接...")
    if not api.test_connection():
        print("⚠️  连接失败，请确保 cookies 有效")
        print("   运行 python setup_cookies.py 设置 cookies")


if __name__ == '__main__':
    init_api()
    
    print("\n" + "="*60)
    print("  SMSToMe.com API 服务")
    print("="*60)
    print("\nAPI 接口:")
    print("  GET  /api/health              - 健康检查")
    print("  GET  /api/countries           - 获取支持的国家")
    print("  GET  /api/phones/<country>    - 获取手机号列表")
    print("  GET  /api/phone/<phone>/sms   - 获取手机号短信")
    print("  GET  /api/search/<country>/<phone> - 搜索手机号")
    print("  GET  /api/cookies             - 查看 cookies")
    print("  POST /api/cookies             - 设置 cookies")
    print("  GET  /api/cookies/test        - 测试 cookies")
    print("\n" + "="*60)
    
    app.run(host='0.0.0.0', port=5001, debug=True)
