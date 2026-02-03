#!/usr/bin/env python3
"""
自动登录 smstome.com 并获取 cookies

使用 curl_cffi 模拟 Chrome 浏览器，绕过 Cloudflare 并捕获登录后的 cookies
"""

import json
import re
import sys
from urllib.parse import unquote
from curl_cffi import requests
from bs4 import BeautifulSoup


def login_and_get_cookies(email: str, password: str, test_uk: bool = True) -> dict:
    """
    登录 smstome.com 并返回所有 cookies
    
    Args:
        email: 登录邮箱
        password: 登录密码
        test_uk: 是否测试访问 UK 页面验证登录成功
    
    Returns:
        dict: 包含 smstome_session, XSRF-TOKEN, remember_website_* 等 cookies
    """
    session = requests.Session(impersonate="chrome")
    
    print("Step 1: 获取登录页面...")
    resp = session.get("https://smstome.com/sign-in", timeout=30)
    
    if resp.status_code != 200:
        print(f"❌ 获取登录页面失败: {resp.status_code}")
        return {}
    
    # 检查是否被 Cloudflare 阻止
    if "checking your browser" in resp.text.lower() or "just a moment" in resp.text.lower():
        print("❌ 遇到 Cloudflare 挑战，需要手动验证")
        return {}
    
    # 解析页面获取表单字段
    soup = BeautifulSoup(resp.text, 'lxml')
    
    # 获取 _token (Laravel CSRF)
    token_input = soup.find('input', {'name': '_token'})
    csrf_token = token_input.get('value') if token_input else None
    print(f"   _token: {csrf_token[:30] if csrf_token else 'None'}...")
    
    # 获取 csrf_v (隐藏验证字段)
    csrf_v_input = soup.find('input', {'name': 'csrf_v'})
    csrf_v = csrf_v_input.get('value') if csrf_v_input else None
    print(f"   csrf_v: {csrf_v}")
    
    # 获取 XSRF-TOKEN cookie
    xsrf_token = session.cookies.get('XSRF-TOKEN')
    print(f"   XSRF-TOKEN: {xsrf_token[:30] if xsrf_token else 'None'}...")
    
    # 查找验证问题 "What is X + Y?"
    match = re.search(r'What is (\d+) \+ (\d+)', resp.text)
    if match:
        answer = int(match.group(1)) + int(match.group(2))
        print(f"   验证问题: {match.group(1)} + {match.group(2)} = {answer}")
    else:
        answer = 9
        print(f"   未找到验证问题，使用默认值: {answer}")
    
    print(f"\nStep 2: 发送登录请求...")
    
    # 构建登录数据 (注意字段名是 captcha 不是 answer)
    login_data = {
        '_token': csrf_token,
        'csrf_v': csrf_v,
        'email': email,
        'password': password,
        'captcha': str(answer),
    }
    
    # 设置请求头
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://smstome.com',
        'Referer': 'https://smstome.com/sign-in',
    }
    
    if xsrf_token:
        headers['X-XSRF-TOKEN'] = unquote(xsrf_token)
    
    # 发送登录请求
    resp = session.post(
        "https://smstome.com/sign-in",
        data=login_data,
        headers=headers,
        timeout=30,
        allow_redirects=True
    )
    
    print(f"   状态码: {resp.status_code}")
    print(f"   最终 URL: {resp.url}")
    
    # 检查登录是否成功
    if "Hi," in resp.text:
        match = re.search(r'Hi,\s*(\w+)', resp.text)
        username = match.group(1) if match else "未知"
        print(f"✅ 登录成功! 用户: {username}")
    else:
        print("❌ 登录失败")
        soup2 = BeautifulSoup(resp.text, 'lxml')
        errors = soup2.find_all(class_='alert')
        for e in errors:
            print(f"   错误: {e.get_text().strip()[:100]}")
        return {}
    
    # 测试访问 UK 页面
    if test_uk:
        print("\nStep 3: 测试访问 UK 页面...")
        resp = session.get("https://smstome.com/country/united-kingdom", timeout=30)
        soup = BeautifulSoup(resp.text, 'lxml')
        
        phone_links = soup.find_all('a', href=re.compile(r'/phone/'))
        print(f"   找到手机号: {len(phone_links)} 个")
        
        if phone_links:
            for link in phone_links[:3]:
                print(f"   - {link.get_text().strip()}")
    
    # 获取所有 cookies
    all_cookies = dict(session.cookies)
    
    print(f"\nStep 4: 获取到的 Cookies ({len(all_cookies)} 个):")
    for name, value in all_cookies.items():
        display_value = value[:40] + "..." if len(value) > 40 else value
        marker = "✅" if name in ['smstome_session', 'XSRF-TOKEN'] or name.startswith('remember_') else "-"
        print(f"   {marker} {name}: {display_value}")
    
    # 保存到文件
    with open('smstome_cookies.json', 'w') as f:
        json.dump(all_cookies, f, indent=2)
    print(f"\n💾 Cookies 已保存到 smstome_cookies.json")
    
    return all_cookies


def main():
    print("="*60)
    print("  SMSToMe.com 自动登录工具")
    print("="*60)
    
    # 从命令行参数获取账号信息，或使用默认值
    if len(sys.argv) >= 3:
        email = sys.argv[1]
        password = sys.argv[2]
    else:
        # 默认账号
        email = "915281792@qq.com"
        password = "w264747477"
    
    print(f"\n账号: {email}")
    print()
    
    cookies = login_and_get_cookies(email, password)
    
    if cookies.get('smstome_session'):
        print("\n" + "="*60)
        print("✅ 登录成功，cookies 已保存")
        print("   现在可以运行 API 服务: python api_server.py")
        print("="*60)
    else:
        print("\n⚠️  登录失败")
        print("   可能原因:")
        print("   1. 账号或密码错误")
        print("   2. Cloudflare 阻止了请求")
        print("   3. 网站验证码变化")


if __name__ == "__main__":
    main()
