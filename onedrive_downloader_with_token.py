#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
import time
import sys

# 下载设置
DOWNLOAD_PATH = "downloads"  # 下载文件的本地目录

class OneDriveDownloader:
    def __init__(self, access_token):
        """初始化下载器，使用提供的访问令牌"""
        self.access_token = access_token
        
        # 创建下载目录
        os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    
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
    if len(sys.argv) < 2:
        print("用法: python onedrive_downloader_with_token.py <访问令牌> [文件夹路径]")
        print("示例: python onedrive_downloader_with_token.py eyJ0eXAiOiJKV1QiLCJub... Documents/Photos")
        sys.exit(1)
    
    access_token = sys.argv[1]
    folder_path = sys.argv[2] if len(sys.argv) > 2 else ""
    
    try:
        downloader = OneDriveDownloader(access_token)
        
        # 开始下载
        downloader.download_folder(folder_path)
        
        print("所有文件下载完成！")
    except Exception as e:
        print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    main() 