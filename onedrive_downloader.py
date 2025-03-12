#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
import time
from msal import PublicClientApplication, SerializableTokenCache
from config import (
    CLIENT_ID, AUTHORITY, SCOPE, 
    DOWNLOAD_PATH, TOKEN_CACHE_FILE
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
        
        # 初始化MSAL应用 - 使用PublicClientApplication进行设备代码流程
        self.app = PublicClientApplication(
            client_id=CLIENT_ID,
            authority=AUTHORITY,
            token_cache=self.token_cache
        )
        
        # 获取访问令牌
        self.access_token = self._get_access_token()
        
    def _save_token_cache(self):
        """保存令牌缓存到文件"""
        with open(TOKEN_CACHE_FILE, "w") as f:
            f.write(self.token_cache.serialize())
    
    def _get_access_token(self):
        """获取访问令牌，如果需要则进行交互式登录"""
        accounts = self.app.get_accounts()
        result = None
        
        if accounts:
            # 尝试使用缓存的令牌
            result = self.app.acquire_token_silent(SCOPE, account=accounts[0])
        
        if not result:
            # 需要交互式登录
            flow = self.app.initiate_device_flow(scopes=SCOPE)
            if "user_code" not in flow:
                raise Exception("无法创建设备流: " + json.dumps(flow, indent=4))
            
            print(flow["message"])
            
            # 等待用户完成登录
            result = self.app.acquire_token_by_device_flow(flow)
        
        if "access_token" not in result:
            raise Exception("无法获取访问令牌: " + json.dumps(result, indent=4))
        
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