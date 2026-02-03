#!/usr/bin/env python3
"""
Cookie 设置助手

简化 cookie 配置流程：
1. 运行此脚本
2. 从浏览器复制 cookie 字符串
3. 粘贴到终端并按 Enter
"""

import json

def parse_cookie_string(cookie_string: str) -> dict:
    """解析 cookie 字符串为字典"""
    cookies = {}
    for item in cookie_string.split(';'):
        item = item.strip()
        if '=' in item:
            name, value = item.split('=', 1)
            cookies[name.strip()] = value.strip()
    return cookies

def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║              SMSToMe.com Cookie 设置助手                      ║
╚══════════════════════════════════════════════════════════════╝

请按以下步骤操作：

1. 在 Chrome 浏览器中打开 https://smstome.com
2. 如果有 Cloudflare 验证，完成验证
3. 登录你的账号（如果需要访问 UK/France）
4. 按 F12 打开开发者工具
5. 切换到 "Network"（网络）标签
6. 刷新页面
7. 点击第一个请求（smstome.com 或 country/...）
8. 在右侧找到 "Request Headers"（请求标头）
9. 找到 "cookie:" 一行，复制整个值

或者使用 Application 标签：
1. 切换到 "Application"（应用）标签
2. 左侧点击 Cookies -> https://smstome.com
3. 右键 -> Copy all as cURL
4. 从复制的内容中提取 cookie 部分

""")
    
    print("请粘贴 cookie 字符串（格式: name1=value1; name2=value2）:")
    print("（粘贴后按 Enter）")
    print("-" * 60)
    
    cookie_string = input().strip()
    
    if not cookie_string:
        print("\n❌ 未输入任何内容")
        return
    
    # 解析 cookies
    cookies = parse_cookie_string(cookie_string)
    
    if not cookies:
        print("\n❌ 无法解析 cookie 字符串")
        return
    
    print(f"\n✅ 解析到 {len(cookies)} 个 cookies:")
    for name in cookies:
        value_preview = cookies[name][:30] + "..." if len(cookies[name]) > 30 else cookies[name]
        print(f"   • {name}: {value_preview}")
    
    # 保存到文件
    filename = "smstome_cookies.json"
    with open(filename, 'w') as f:
        json.dump(cookies, f, indent=2)
    
    print(f"\n💾 Cookies 已保存到 {filename}")
    print("\n现在可以运行:")
    print("   python smstome_api.py --country uk")
    print("   python smstome_api.py --country france")

if __name__ == "__main__":
    main()
