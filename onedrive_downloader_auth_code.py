#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
import time
import webbrowser
from urllib.parse import urlencode, parse_qs, urlparse
from msal import ConfidentialClientApplication, SerializableTokenCache
from config import (
    CLIENT_ID, CLIENT_SECRET, AUTHORITY, SCOPE, 
    REDIRECT_URI, DOWNLOAD_PATH, TOKEN_CACHE_FILE
)

class OneDriveDownloader:
    def __init__(self):
        # 创建下载目录
        os.makedirs(DOWNLOAD_PATH, exist_ok=True)
        
        # 初始化令牌缓存
        self.token_cache = SerializableTokenCache()
        if os.path.exists(TOKEN_CACHE_FILE):
            try:
                self.token_cache.deserialize(open(TOKEN_CACHE_FILE, "r").read())
            except:
                print("令牌缓存文件无效，将创建新的缓存")
        
        # 初始化MSAL应用
        self.app = ConfidentialClientApplication(
            client_id=CLIENT_ID,
            client_credential=CLIENT_SECRET,  # 确保这里使用了client_credential参数
            authority=AUTHORITY,
            token_cache=self.token_cache
        )
        
        # 获取访问令牌
        self.access_token = self._get_access_token()
        
    def _save_token_cache(self):
        """保存令牌缓存到文件"""
        with open(TOKEN_CACHE_FILE, "w") as f:
            f.write(self.token_cache.serialize())
    
    def _get_auth_url(self):
        """获取授权URL"""
        return self.app.get_authorization_request_url(
            scopes=SCOPE,
            redirect_uri=REDIRECT_URI,
            state="12345"  # 可以是任何值，用于防止CSRF攻击
        )
    
    def _extract_code_from_url(self, redirect_url):
        """从重定向URL中提取授权码"""
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)
        
        if 'code' in query_params:
            return query_params['code'][0]
        return None
    
    def _get_access_token(self):
        """获取访问令牌，如果需要则进行交互式登录"""
        accounts = self.app.get_accounts()
        result = None
        
        if accounts:
            # 尝试使用缓存的令牌
            result = self.app.acquire_token_silent(SCOPE, account=accounts[0])
        
        if not result:
            # 需要交互式登录
            auth_url = self._get_auth_url()
            print("请在浏览器中打开以下URL并登录您的Microsoft账户:")
            print(auth_url)
            
            # 尝试自动打开浏览器
            try:
                webbrowser.open(auth_url)
            except:
                pass
            
            # 获取授权码
            redirect_url = input("请输入重定向后的完整URL: ")
            auth_code = self._extract_code_from_url(redirect_url)
            
            if not auth_code:
                auth_code = input("无法从URL中提取授权码，请手动输入授权码: ")
            
            # 使用授权码获取令牌
            result = self.app.acquire_token_by_authorization_code(
                code=auth_code,
                scopes=SCOPE,
                redirect_uri=REDIRECT_URI
            )
        
        if "access_token" not in result:
            error_msg = result.get("error_description", json.dumps(result, indent=4))
            raise Exception(f"无法获取访问令牌: {error_msg}")
        
        # 保存令牌缓存
        self._save_token_cache()
        
        return result["access_token"]
    
    def _make_api_request(self, endpoint, params=None):
        """向Microsoft Graph API发送请求"""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        
        response = requests.get(
            f"https://graph.microsoft.com/v1.0{endpoint}",
            headers=headers,
            params=params
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API请求失败: {response.status_code}")
            print(response.text)
            return None
    
    def list_items(self, folder_path):
        """列出指定文件夹中的所有项目"""
        if folder_path.startswith("/"):
            folder_path = folder_path[1:]
        
        if folder_path:
            endpoint = f"/me/drive/root:/{folder_path}:/children"
        else:
            endpoint = "/me/drive/root/children"
        
        return self._make_api_request(endpoint)
    
    def download_file(self, item, local_path):
        """下载单个文件"""
        if "@microsoft.graph.downloadUrl" in item:
            download_url = item["@microsoft.graph.downloadUrl"]
        else:
            # 如果下载URL不在项目中，则获取它
            file_id = item["id"]
            download_info = self._make_api_request(f"/me/drive/items/{file_id}")
            if not download_info or "@microsoft.graph.downloadUrl" not in download_info:
                print(f"无法获取文件 {item['name']} 的下载链接")
                return False
            download_url = download_info["@microsoft.graph.downloadUrl"]
        
        # 创建本地目录（如果不存在）
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # 下载文件
        try:
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            file_size = int(response.headers.get("Content-Length", 0))
            print(f"正在下载: {item['name']} ({self._format_size(file_size)})")
            
            with open(local_path, "wb") as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # 显示下载进度
                        progress = (downloaded / file_size) * 100 if file_size > 0 else 0
                        print(f"\r进度: {progress:.1f}%", end="")
            
            print("\n下载完成")
            return True
        except Exception as e:
            print(f"\n下载失败: {str(e)}")
            return False
    
    def _format_size(self, size_bytes):
        """格式化文件大小"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def download_folder(self, folder_path, local_base_path=None):
        """递归下载文件夹中的所有内容"""
        if local_base_path is None:
            local_base_path = DOWNLOAD_PATH
        
        print(f"正在处理文件夹: {folder_path}")
        items = self.list_items(folder_path)
        
        if not items or "value" not in items:
            print(f"无法获取文件夹内容: {folder_path}")
            return
        
        for item in items["value"]:
            item_name = item["name"]
            item_path = os.path.join(folder_path, item_name) if folder_path else item_name
            local_path = os.path.join(local_base_path, item_path)
            
            if item.get("folder"):
                # 如果是文件夹，递归下载
                self.download_folder(item_path, local_base_path)
            else:
                # 如果是文件，直接下载
                if os.path.exists(local_path):
                    print(f"文件已存在，跳过: {item_path}")
                    continue
                
                self.download_file(item, local_path)
                # 添加短暂延迟以避免API限制
                time.sleep(0.5)

def main():
    try:
        downloader = OneDriveDownloader()
        
        # 获取用户输入的文件夹路径
        folder_path = input("请输入要下载的OneDrive文件夹路径 (留空表示根目录): ")
        
        # 开始下载
        downloader.download_folder(folder_path)
        
        print("所有文件下载完成！")
    except Exception as e:
        print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    main() 