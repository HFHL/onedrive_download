#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import webbrowser
from urllib.parse import parse_qs, urlparse
from msal import ConfidentialClientApplication, SerializableTokenCache
from config import (
    CLIENT_ID, CLIENT_SECRET, AUTHORITY, SCOPE, 
    REDIRECT_URI, TOKEN_CACHE_FILE
)

def get_access_token():
    """获取OneDrive访问令牌"""
    # 初始化令牌缓存
    token_cache = SerializableTokenCache()
    if os.path.exists(TOKEN_CACHE_FILE):
        try:
            token_cache.deserialize(open(TOKEN_CACHE_FILE, "r").read())
            print("已加载令牌缓存")
        except:
            print("令牌缓存文件无效，将创建新的缓存")
    
    # 初始化MSAL应用
    app = ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=AUTHORITY,
        token_cache=token_cache
    )
    
    # 检查缓存中是否有令牌
    accounts = app.get_accounts()
    result = None
    
    if accounts:
        print(f"找到已缓存的账户: {accounts[0]['username']}")
        # 尝试使用缓存的令牌
        result = app.acquire_token_silent(SCOPE, account=accounts[0])
    
    if not result:
        print("需要获取新的访问令牌...")
        
        # 获取授权URL
        auth_url = app.get_authorization_request_url(
            scopes=SCOPE,
            redirect_uri=REDIRECT_URI,
            state="12345"
        )
        
        print("\n请在浏览器中打开以下URL并登录您的Microsoft账户:")
        print(auth_url)
        
        # 尝试自动打开浏览器
        try:
            webbrowser.open(auth_url)
        except:
            pass
        
        # 获取授权码
        redirect_url = input("\n请输入重定向后的完整URL: ")
        
        # 从URL中提取授权码
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)
        
        if 'code' in query_params:
            auth_code = query_params['code'][0]
        else:
            auth_code = input("无法从URL中提取授权码，请手动输入授权码: ")
        
        # 使用授权码获取令牌
        result = app.acquire_token_by_authorization_code(
            code=auth_code,
            scopes=SCOPE,
            redirect_uri=REDIRECT_URI
        )
    
    # 检查结果
    if "access_token" in result:
        # 保存令牌缓存
        with open(TOKEN_CACHE_FILE, "w") as f:
            f.write(token_cache.serialize())
        
        print("\n成功获取访问令牌!")
        print(f"令牌类型: {result.get('token_type', 'Bearer')}")
        print(f"过期时间: {result.get('expires_in', 3600)} 秒")
        
        # 显示令牌的一部分
        token = result["access_token"]
        token_preview = token[:10] + "..." + token[-10:]
        print(f"访问令牌: {token_preview}")
        
        # 返回完整令牌
        return token
    else:
        error_msg = result.get("error_description", json.dumps(result, indent=4))
        print(f"无法获取访问令牌: {error_msg}")
        return None

def main():
    token = get_access_token()
    if token:
        print("\n您可以使用以下命令下载文件:")
        print(f"python onedrive_downloader_with_token.py \"{token}\" [文件夹路径]")

if __name__ == "__main__":
    main() 