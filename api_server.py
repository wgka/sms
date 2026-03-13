#!/usr/bin/env python3
"""
多数据源 SMS HTTP API 服务

支持的数据源:
- receivesmscc: Receive-SMS.cc (免费，无需登录)
- getsmscc: GetSMS.cc (免费，无需登录)
- sms24me: SMS24.me (免费，无需登录)
- smstome: SMSToMe.com (需要登录)

提供 RESTful API 接口获取手机号列表和短信
"""

import json
import os
from typing import Optional, List
from dataclasses import asdict

from flask import Flask, jsonify, request
from flask_cors import CORS

# 导入数据源
from providers.smstome.smstome_api import SMSToMeAPI, PhoneNumber as SMSToMePhone
from providers.receivesmscc.receivesmscc_api import (
    ReceiveSMSCCAPI, 
    PhoneNumber as ReceiveSMSCCPhone,
    PhoneDetail as ReceiveSMSCCDetail
)
from providers.getsmscc.getsmscc_api import GetSMSCCAPI
from providers.sms24me.sms24me_api import SMS24MeAPI

app = Flask(__name__)
CORS(app)  # 启用跨域支持

# 全局 API 实例
smstome_api = SMSToMeAPI(auto_refresh=True)
receivesmscc_api = ReceiveSMSCCAPI()
getsmscc_api = GetSMSCCAPI()
sms24me_api = SMS24MeAPI()

CACHE_FILE = "phone_url_cache.json"
PHONES_PER_PAGE = 20


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


# ============================================================
# 通用接口
# ============================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    provider = request.args.get('provider', 'receivesmscc')
    
    if provider == 'smstome':
        connected = smstome_api.test_connection()
    elif provider == 'getsmscc':
        connected = getsmscc_api.test_connection()
    elif provider == 'sms24me':
        connected = sms24me_api.test_connection()
    else:
        connected = receivesmscc_api.test_connection()
    
    return jsonify({
        'status': 'ok' if connected else 'error',
        'connected': connected,
        'provider': provider
    })


@app.route('/api/providers', methods=['GET'])
def get_providers():
    """获取支持的数据源列表"""
    return jsonify({
        'providers': [
            {
                'id': 'receivesmscc',
                'name': 'Receive-SMS.cc',
                'description': '免费短信接收服务，无需登录',
                'requires_login': False,
                'countries': ['US', 'UK', 'Canada', 'Netherlands', 'Finland', 'Belgium']
            },
            {
                'id': 'getsmscc',
                'name': 'GetSMS.cc',
                'description': '免费短信接收服务，支持多国家',
                'requires_login': False,
                'countries': ['US', 'UK', 'France', 'Sweden', 'Finland', 'Netherlands']
            },
            {
                'id': 'sms24me',
                'name': 'SMS24.me',
                'description': '免费短信接收服务，支持45+国家',
                'requires_login': False,
                'countries': ['US', 'UK', 'Russia', 'Ukraine', 'Germany', 'France', 'Canada', '...']
            },
            {
                'id': 'smstome',
                'name': 'SMSToMe.com',
                'description': '需要登录的短信接收服务',
                'requires_login': True,
                'countries': ['UK', 'Poland', 'Netherlands', 'Sweden', 'Finland', 'Belgium', 'Slovenia']
            }
        ]
    })


# ============================================================
# Receive-SMS.cc 接口
# ============================================================

@app.route('/api/receivesmscc/countries', methods=['GET'])
def receivesmscc_get_countries():
    """获取 Receive-SMS.cc 支持的国家列表"""
    countries = receivesmscc_api.get_countries()
    return jsonify({
        'provider': 'receivesmscc',
        'countries': [asdict(c) for c in countries]
    })


@app.route('/api/receivesmscc/phones', methods=['GET'])
def receivesmscc_get_phones():
    """
    获取 Receive-SMS.cc 手机号列表
    
    Query params:
        country: 国家代码 (默认 US)
        page: 页码 (默认 1)
        all: 是否获取首页所有号码 (true 则忽略 country)
    """
    country = request.args.get('country', 'US')
    page = request.args.get('page', 1, type=int)
    get_all = request.args.get('all', 'false').lower() == 'true'
    
    if get_all:
        phones = receivesmscc_api.get_all_phones_from_home()
    else:
        phones = receivesmscc_api.get_phone_list(country, page=page)
    
    return jsonify({
        'provider': 'receivesmscc',
        'country': country if not get_all else 'all',
        'page': page,
        'count': len(phones),
        'phones': [asdict(p) for p in phones]
    })


@app.route('/api/receivesmscc/phones/<country>', methods=['GET'])
def receivesmscc_get_phones_by_country(country: str):
    """
    获取 Receive-SMS.cc 指定国家的手机号列表
    
    Query params:
        page: 页码 (默认 1)
    """
    page = request.args.get('page', 1, type=int)
    phones = receivesmscc_api.get_phone_list(country, page=page)
    
    return jsonify({
        'provider': 'receivesmscc',
        'country': country,
        'page': page,
        'count': len(phones),
        'phones': [asdict(p) for p in phones]
    })


@app.route('/api/receivesmscc/sms/<phone>', methods=['GET'])
def receivesmscc_get_sms(phone: str):
    """
    获取 Receive-SMS.cc 指定手机号的短信
    
    Query params:
        country: 国家代码 (默认 US)
        pages: 获取页数 (默认 1)
        limit: 返回条数限制 (默认 0，全部)
    """
    country = request.args.get('country', 'US')
    max_pages = request.args.get('pages', 1, type=int)
    limit = request.args.get('limit', 0, type=int)
    
    phone = phone.replace('+', '').replace(' ', '').strip()
    
    detail = receivesmscc_api.get_messages_by_phone(phone, country, max_pages)
    
    if not detail:
        return jsonify({
            'error': 'Phone not found or failed to get messages',
            'phone': phone,
            'country': country,
            'provider': 'receivesmscc'
        }), 404
    
    messages = detail.messages
    if limit > 0:
        messages = messages[:limit]
    
    return jsonify({
        'provider': 'receivesmscc',
        'phone': detail.phone,
        'country': detail.country,
        'country_code': detail.country_code,
        'total_pages': detail.total_pages,
        'sms_count': len(messages),
        'total_sms': len(detail.messages),
        'messages': [asdict(m) for m in messages]
    })


@app.route('/api/receivesmscc/phone/<country>/<phone>/sms', methods=['GET'])
def receivesmscc_get_phone_sms(country: str, phone: str):
    """
    获取 Receive-SMS.cc 指定手机号的短信 (带国家)
    
    Query params:
        pages: 获取页数 (默认 1)
        limit: 返回条数限制 (默认 0，全部)
    """
    max_pages = request.args.get('pages', 1, type=int)
    limit = request.args.get('limit', 0, type=int)
    
    phone = phone.replace('+', '').replace(' ', '').strip()
    
    detail = receivesmscc_api.get_messages_by_phone(phone, country, max_pages)
    
    if not detail:
        return jsonify({
            'error': 'Phone not found or failed to get messages',
            'phone': phone,
            'country': country,
            'provider': 'receivesmscc'
        }), 404
    
    messages = detail.messages
    if limit > 0:
        messages = messages[:limit]
    
    return jsonify({
        'provider': 'receivesmscc',
        'phone': detail.phone,
        'country': detail.country,
        'country_code': detail.country_code,
        'total_pages': detail.total_pages,
        'sms_count': len(messages),
        'total_sms': len(detail.messages),
        'messages': [asdict(m) for m in messages]
    })


# ============================================================
# GetSMS.cc 接口
# ============================================================

@app.route('/api/getsmscc/phones', methods=['GET'])
def getsmscc_get_phones():
    """
    获取 GetSMS.cc 手机号列表
    
    Query params:
        country: 国家名称 (默认 US)
    """
    country = request.args.get('country', 'US')
    phones = getsmscc_api.get_phone_list(country)
    
    return jsonify({
        'provider': 'getsmscc',
        'country': country,
        'count': len(phones),
        'phones': [asdict(p) for p in phones]
    })


@app.route('/api/getsmscc/phones/<country>', methods=['GET'])
def getsmscc_get_phones_by_country(country: str):
    """获取 GetSMS.cc 指定国家的手机号列表"""
    phones = getsmscc_api.get_phone_list(country)
    
    return jsonify({
        'provider': 'getsmscc',
        'country': country,
        'count': len(phones),
        'phones': [asdict(p) for p in phones]
    })


@app.route('/api/getsmscc/sms/<phone>', methods=['GET'])
def getsmscc_get_sms(phone: str):
    """
    获取 GetSMS.cc 指定手机号的短信
    
    Query params:
        pages: 获取页数 (默认 1)
        limit: 返回条数限制 (默认 0，全部)
    """
    max_pages = request.args.get('pages', 1, type=int)
    limit = request.args.get('limit', 0, type=int)
    
    phone = phone.replace('+', '').replace(' ', '').strip()
    
    detail = getsmscc_api.get_messages_by_phone(phone, max_pages=max_pages)
    
    if not detail:
        return jsonify({
            'error': 'Phone not found or failed to get messages',
            'phone': phone,
            'provider': 'getsmscc'
        }), 404
    
    messages = detail.messages
    if limit > 0:
        messages = messages[:limit]
    
    return jsonify({
        'provider': 'getsmscc',
        'phone': detail.phone,
        'country': detail.country,
        'status': detail.status,
        'total_pages': detail.total_pages,
        'sms_count': len(messages),
        'total_sms': detail.sms_count,
        'messages': [asdict(m) for m in messages]
    })


# ============================================================
# SMS24.me 接口
# ============================================================

@app.route('/api/sms24me/countries', methods=['GET'])
def sms24me_get_countries():
    """获取 SMS24.me 支持的国家列表"""
    countries = sms24me_api.get_countries()
    return jsonify({
        'provider': 'sms24me',
        'count': len(countries),
        'countries': [asdict(c) for c in countries]
    })


@app.route('/api/sms24me/phones', methods=['GET'])
def sms24me_get_phones():
    """
    获取 SMS24.me 手机号列表
    
    Query params:
        country: 国家代码 (默认 us)
        page: 页码 (默认 1)
    """
    country = request.args.get('country', 'us')
    page = request.args.get('page', 1, type=int)
    phones = sms24me_api.get_phone_list(country, page=page)
    
    return jsonify({
        'provider': 'sms24me',
        'country': country,
        'page': page,
        'count': len(phones),
        'phones': [asdict(p) for p in phones]
    })


@app.route('/api/sms24me/phones/<country>', methods=['GET'])
def sms24me_get_phones_by_country(country: str):
    """
    获取 SMS24.me 指定国家的手机号列表
    
    Query params:
        page: 页码 (默认 1)
    """
    page = request.args.get('page', 1, type=int)
    phones = sms24me_api.get_phone_list(country, page=page)
    
    return jsonify({
        'provider': 'sms24me',
        'country': country,
        'page': page,
        'count': len(phones),
        'phones': [asdict(p) for p in phones]
    })


@app.route('/api/sms24me/sms/<phone>', methods=['GET'])
def sms24me_get_sms(phone: str):
    """
    获取 SMS24.me 指定手机号的短信
    
    Query params:
        country: 国家代码 (默认 us)
        pages: 获取页数 (默认 1)
        limit: 返回条数限制 (默认 0，全部)
    """
    country = request.args.get('country', 'us')
    max_pages = request.args.get('pages', 1, type=int)
    limit = request.args.get('limit', 0, type=int)
    
    phone = phone.replace('+', '').replace(' ', '').strip()
    
    detail = sms24me_api.get_messages_by_phone(phone, country, max_pages)
    
    if not detail:
        return jsonify({
            'error': 'Phone not found or failed to get messages',
            'phone': phone,
            'country': country,
            'provider': 'sms24me'
        }), 404
    
    messages = detail.messages
    if limit > 0:
        messages = messages[:limit]
    
    return jsonify({
        'provider': 'sms24me',
        'phone': detail.phone,
        'country': detail.country,
        'country_code': detail.country_code,
        'total_pages': detail.total_pages,
        'sms_count': len(messages),
        'messages': [asdict(m) for m in messages]
    })


# ============================================================
# SMSToMe.com 接口 (保持向后兼容)
# ============================================================

def search_phone_all_pages(country: str, phone: str) -> Optional[str]:
    """搜索手机号，遍历所有页面"""
    print(f"🔍 开始搜索手机号 {phone}，国家: {country}")
    page_num = 0
    total_phones_checked = 0
    
    while True:
        page_num += 1
        print(f"   📱 正在搜索第 {page_num} 页...")
        
        phones = smstome_api.get_phone_list(country, page=page_num)
        
        if not phones:
            if page_num == 1:
                print(f"   ❌ 无法获取手机号列表")
            break
        
        total_phones_checked += len(phones)
        
        for p in phones:
            if phone in p.phone.replace('+', ''):
                print(f"   ✅ 在第 {page_num} 页找到!")
                return p.detail_url
        
        if len(phones) < PHONES_PER_PAGE:
            break
    
    print(f"   ❌ 搜索完成，共检查 {total_phones_checked} 个号码，未找到 {phone}")
    return None


def find_phone_url(country: str, phone: str) -> Optional[str]:
    """查找手机号的详情页 URL"""
    phone = phone.replace('+', '').strip()
    country_slug = smstome_api.COUNTRIES.get(country.lower(), country.lower())
    
    # 从缓存查找
    cache = load_url_cache()
    cache_key = f"smstome_{phone}"
    if cache_key in cache:
        return cache[cache_key]
    
    # 搜索所有页面
    url = search_phone_all_pages(country_slug, phone)
    
    if url:
        cache[cache_key] = url
        save_url_cache(cache)
    
    return url


@app.route('/api/smstome/countries', methods=['GET'])
@app.route('/api/countries', methods=['GET'])
def smstome_get_countries():
    """获取 SMSToMe 支持的国家列表"""
    return jsonify({
        'provider': 'smstome',
        'countries': list(smstome_api.COUNTRIES.keys()),
        'country_slugs': smstome_api.COUNTRIES
    })


@app.route('/api/smstome/phones/<country>', methods=['GET'])
@app.route('/api/phones/<country>', methods=['GET'])
def smstome_get_phone_list(country: str):
    """获取 SMSToMe 指定国家的手机号列表"""
    page = request.args.get('page', 1, type=int)
    pages_param = request.args.get('pages', '')
    get_all = request.args.get('all', 'false').lower() == 'true'
    
    country_slug = smstome_api.COUNTRIES.get(country.lower(), country.lower())
    
    pages_to_fetch = []
    if pages_param:
        for part in pages_param.split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-', 1)
                pages_to_fetch.extend(range(int(start), int(end) + 1))
            else:
                pages_to_fetch.append(int(part))
    
    if get_all:
        all_phones = []
        page_num = 1
        
        while True:
            phones = smstome_api.get_phone_list(country_slug, page=page_num)
            all_phones.extend(phones)
            
            if len(phones) < PHONES_PER_PAGE:
                break
            
            page_num += 1
        
        return jsonify({
            'provider': 'smstome',
            'country': country_slug,
            'total_phones': len(all_phones),
            'total_pages': page_num,
            'phones': [asdict(p) for p in all_phones]
        })
    elif pages_to_fetch:
        all_phones = []
        fetched_pages = []
        
        for p in pages_to_fetch:
            phones = smstome_api.get_phone_list(country_slug, page=p)
            if phones:
                all_phones.extend(phones)
                fetched_pages.append(p)
        
        return jsonify({
            'provider': 'smstome',
            'country': country_slug,
            'pages': fetched_pages,
            'total_phones': len(all_phones),
            'phones': [asdict(p) for p in all_phones]
        })
    else:
        phones = smstome_api.get_phone_list(country_slug, page=page)
        
        return jsonify({
            'provider': 'smstome',
            'country': country_slug,
            'page': page,
            'count': len(phones),
            'has_more': len(phones) >= PHONES_PER_PAGE,
            'phones': [asdict(p) for p in phones]
        })


@app.route('/api/smstome/sms/<phone>', methods=['GET'])
@app.route('/api/sms/<phone>', methods=['GET'])
def smstome_get_sms_simple(phone: str):
    """获取 SMSToMe 指定手机号的短信（简化接口）"""
    country = request.args.get('country', 'uk')
    limit = request.args.get('limit', 1, type=int)
    
    phone = phone.replace('+', '').strip()
    phone_url = find_phone_url(country, phone)
    
    if not phone_url:
        return jsonify({
            'error': 'Phone not found',
            'phone': phone,
            'country': country,
            'provider': 'smstome'
        }), 404
    
    max_pages = 1 if limit > 0 and limit <= 20 else 5
    detail = smstome_api.get_phone_messages(phone_url, max_pages=max_pages)
    
    if not detail:
        return jsonify({
            'error': 'Failed to get SMS',
            'phone': phone,
            'provider': 'smstome'
        }), 500
    
    messages = detail.messages
    if limit > 0:
        messages = messages[:limit]
    
    return jsonify({
        'provider': 'smstome',
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


@app.route('/api/smstome/phone/<phone>/sms', methods=['GET'])
@app.route('/api/phone/<phone>/sms', methods=['GET'])
def smstome_get_phone_sms(phone: str):
    """获取 SMSToMe 指定手机号的短信（详细接口）"""
    country = request.args.get('country', 'uk')
    sms_pages = request.args.get('pages', 1, type=int)
    limit = request.args.get('limit', 0, type=int)
    latest = request.args.get('latest', 'false').lower() == 'true'
    
    phone = phone.replace('+', '').strip()
    phone_url = find_phone_url(country, phone)
    
    if not phone_url:
        return jsonify({
            'error': 'Phone not found',
            'phone': phone,
            'country': country,
            'provider': 'smstome'
        }), 404
    
    detail = smstome_api.get_phone_messages(phone_url, max_pages=sms_pages)
    
    if not detail:
        return jsonify({
            'error': 'Failed to get SMS',
            'phone': phone,
            'phone_url': phone_url,
            'provider': 'smstome'
        }), 500
    
    messages = detail.messages
    
    if latest:
        messages = messages[:1] if messages else []
    elif limit > 0:
        messages = messages[:limit]
    
    return jsonify({
        'provider': 'smstome',
        'phone': detail.phone,
        'country': detail.country,
        'region': detail.region,
        'added_time': detail.added_time,
        'sms_count': len(messages),
        'total_sms': len(detail.messages),
        'messages': [asdict(m) for m in messages]
    })


# ============================================================
# SMSToMe 设置接口
# ============================================================

@app.route('/api/smstome/cookies', methods=['GET'])
@app.route('/api/cookies', methods=['GET'])
def get_cookies():
    """获取当前 cookies 配置"""
    try:
        with open(smstome_api.COOKIES_FILE, 'r') as f:
            cookies = json.load(f)
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


@app.route('/api/smstome/cookies', methods=['POST'])
@app.route('/api/cookies', methods=['POST'])
def set_cookies():
    """设置 cookies"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    cookies = {}
    
    if 'cookie_string' in data:
        cookie_str = data['cookie_string']
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                name, value = item.split('=', 1)
                cookies[name.strip()] = value.strip()
    else:
        cookies = {k: v for k, v in data.items() if v and not k.startswith('_')}
    
    if not cookies:
        return jsonify({'error': 'No valid cookies provided'}), 400
    
    try:
        with open(smstome_api.COOKIES_FILE, 'w') as f:
            json.dump(cookies, f, indent=2)
    except Exception as e:
        return jsonify({'error': f'Failed to save cookies: {str(e)}'}), 500
    
    smstome_api.session.cookies.clear()
    for name, value in cookies.items():
        smstome_api.session.cookies.set(name, value)
    
    connected = smstome_api.test_connection()
    
    return jsonify({
        'success': True,
        'cookie_count': len(cookies),
        'connected': connected
    })


@app.route('/api/smstome/cookies/test', methods=['GET'])
@app.route('/api/cookies/test', methods=['GET'])
def test_cookies():
    """测试当前 cookies 是否有效"""
    connected = smstome_api.test_connection()
    return jsonify({
        'connected': connected,
        'message': '连接正常' if connected else 'Cookies 已失效，请更新'
    })


@app.route('/api/smstome/login', methods=['POST'])
@app.route('/api/login', methods=['POST'])
def login_and_refresh_cookies():
    """使用账号密码登录并刷新 cookies"""
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
        
        resp = session.get("https://smstome.com/sign-in", timeout=30)
        
        if resp.status_code != 200:
            return jsonify({'error': f'获取登录页面失败: {resp.status_code}'}), 500
        
        if "checking your browser" in resp.text.lower() or "just a moment" in resp.text.lower():
            return jsonify({'error': '遇到 Cloudflare 挑战，请稍后重试'}), 503
        
        soup = BeautifulSoup(resp.text, 'lxml')
        
        token_input = soup.find('input', {'name': '_token'})
        csrf_token = token_input.get('value') if token_input else None
        
        csrf_v_input = soup.find('input', {'name': 'csrf_v'})
        csrf_v = csrf_v_input.get('value') if csrf_v_input else None
        
        xsrf_cookie = session.cookies.get('XSRF-TOKEN')
        
        match = re.search(r'What is (\d+) \+ (\d+)', resp.text)
        answer = int(match.group(1)) + int(match.group(2)) if match else 9
        
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
        
        if "Hi," not in resp.text:
            soup2 = BeautifulSoup(resp.text, 'lxml')
            errors = soup2.find_all(class_='alert')
            error_msg = errors[0].get_text().strip() if errors else '登录失败，请检查账号密码'
            return jsonify({'error': error_msg}), 401
        
        username_match = re.search(r'Hi,\s*(\w+)', resp.text)
        username = username_match.group(1) if username_match else '未知'
        
        all_cookies = dict(session.cookies)
        
        with open(smstome_api.COOKIES_FILE, 'w') as f:
            json.dump(all_cookies, f, indent=2)
        
        smstome_api.session.cookies.clear()
        for name, value in all_cookies.items():
            smstome_api.session.cookies.set(name, value)
        
        connected = smstome_api.test_connection()
        
        return jsonify({
            'success': True,
            'username': username,
            'cookie_count': len(all_cookies),
            'connected': connected,
            'message': f'登录成功！欢迎 {username}'
        })
        
    except Exception as e:
        return jsonify({'error': f'登录出错: {str(e)}'}), 500


@app.route('/api/smstome/account', methods=['GET'])
@app.route('/api/account', methods=['GET'])
def get_account():
    """获取保存的账号信息"""
    account_file = 'smstome_account.json'
    try:
        with open(account_file, 'r') as f:
            account = json.load(f)
        if 'password' in account:
            account['password'] = '*' * len(account['password'])
        account['auto_refresh_enabled'] = smstome_api.auto_refresh
        account['has_account'] = bool(account.get('email'))
        return jsonify(account)
    except:
        return jsonify({
            'email': '', 
            'password': '',
            'auto_refresh_enabled': smstome_api.auto_refresh,
            'has_account': False
        })


@app.route('/api/smstome/account', methods=['POST'])
@app.route('/api/account', methods=['POST'])
def save_account():
    """保存账号信息"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    account_file = 'smstome_account.json'
    
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


# ============================================================
# 缓存接口
# ============================================================

@app.route('/api/cache', methods=['GET'])
def get_cache():
    """获取 URL 缓存"""
    return jsonify(load_url_cache())


@app.route('/api/cache/<phone>', methods=['DELETE'])
def delete_cache(phone: str):
    """删除指定手机号的缓存"""
    phone = phone.replace('+', '').strip()
    cache = load_url_cache()
    
    deleted = False
    for key in [phone, f"smstome_{phone}", f"receivesmscc_{phone}"]:
        if key in cache:
            del cache[key]
            deleted = True
    
    if deleted:
        save_url_cache(cache)
        return jsonify({'deleted': True, 'phone': phone})
    
    return jsonify({'deleted': False, 'phone': phone}), 404


# ============================================================
# 初始化
# ============================================================

def init_api():
    """初始化 API"""
    # 加载 SMSToMe cookies
    if os.path.exists(smstome_api.COOKIES_FILE):
        smstome_api.load_cookies()
    
    print("\n🔗 测试连接...")
    
    print("\n   Receive-SMS.cc:")
    receivesmscc_api.test_connection()
    
    print("\n   GetSMS.cc:")
    getsmscc_api.test_connection()
    
    print("\n   SMS24.me:")
    sms24me_api.test_connection()
    
    print("\n   SMSToMe.com:")
    if not smstome_api.test_connection():
        print("   ⚠️  SMSToMe 连接失败，请确保 cookies 有效")


if __name__ == '__main__':
    init_api()
    
    print("\n" + "="*60)
    print("  多数据源 SMS API 服务")
    print("="*60)
    print("\n数据源:")
    print("  📱 Receive-SMS.cc (免费，无需登录)")
    print("  📱 GetSMS.cc (免费，无需登录)")
    print("  📱 SMS24.me (免费，无需登录)")
    print("  📱 SMSToMe.com (需要登录)")
    print("\nReceive-SMS.cc API:")
    print("  GET  /api/receivesmscc/countries        - 获取国家列表")
    print("  GET  /api/receivesmscc/phones           - 获取手机号列表")
    print("  GET  /api/receivesmscc/sms/<phone>      - 获取短信")
    print("\nGetSMS.cc API:")
    print("  GET  /api/getsmscc/phones               - 获取手机号列表")
    print("  GET  /api/getsmscc/phones/<country>     - 获取指定国家手机号")
    print("  GET  /api/getsmscc/sms/<phone>          - 获取短信")
    print("\nSMS24.me API:")
    print("  GET  /api/sms24me/countries             - 获取国家列表")
    print("  GET  /api/sms24me/phones                - 获取手机号列表")
    print("  GET  /api/sms24me/phones/<country>      - 获取指定国家手机号")
    print("  GET  /api/sms24me/sms/<phone>           - 获取短信")
    print("\nSMSToMe.com API:")
    print("  GET  /api/smstome/countries             - 获取国家列表")
    print("  GET  /api/smstome/phones/<country>      - 获取手机号列表")
    print("  GET  /api/smstome/sms/<phone>           - 获取短信")
    print("  POST /api/smstome/login                 - 登录")
    print("\n通用 API:")
    print("  GET  /api/health                        - 健康检查")
    print("  GET  /api/providers                     - 获取数据源列表")
    print("\n" + "="*60)
    
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
