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

class OneDriveBrowser:
    def __init__(self):
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
    
    def list_items(self, folder_path, is_shared_item=False, shared_item_id=None, remote_item=None):
        """列出指定文件夹中的所有项目"""
        if remote_item:
            # 如果是remoteItem类型的共享项目
            drive_id = remote_item.get("parentReference", {}).get("driveId")
            item_id = remote_item.get("id")
            
            if drive_id and item_id:
                endpoint = f"/drives/{drive_id}/items/{item_id}/children"
            else:
                print("无法获取共享项目的驱动器ID或项目ID")
                return None
        elif is_shared_item and shared_item_id:
            # 如果是共享项目，使用项目ID访问
            endpoint = f"/me/drive/items/{shared_item_id}/children"
        elif folder_path.startswith("/"):
            folder_path = folder_path[1:]
            
            if folder_path:
                endpoint = f"/me/drive/root:/{folder_path}:/children"
            else:
                endpoint = "/me/drive/root/children"
        else:
            if folder_path:
                endpoint = f"/me/drive/root:/{folder_path}:/children"
            else:
                endpoint = "/me/drive/root/children"
        
        return self._make_api_request(endpoint)
    
    def list_shared_items(self):
        """列出所有共享项目"""
        endpoint = "/me/drive/sharedWithMe"
        return self._make_api_request(endpoint)
    
    def _format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes is None:
            return "未知大小"
            
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def browse_folder(self, folder_path=""):
        """浏览文件夹内容"""
        current_path = folder_path
        is_in_shared_items = False
        current_shared_item_id = None
        current_remote_item = None
        shared_items_cache = []
        
        while True:
            if is_in_shared_items and current_shared_item_id is None and current_remote_item is None:
                # 显示共享项目列表
                print("\n=== 共享项目 ===\n")
                
                if not shared_items_cache:
                    shared_items = self.list_shared_items()
                    if shared_items and "value" in shared_items:
                        shared_items_cache = shared_items["value"]
                    else:
                        shared_items_cache = []
                
                if not shared_items_cache:
                    print("没有共享项目")
                    is_in_shared_items = False
                    current_path = ""
                    continue
                
                # 显示共享项目
                for i, item in enumerate(shared_items_cache):
                    name = item.get("name", "未命名项目")
                    remote_item = item.get("remoteItem", {})
                    
                    # 尝试获取共享者信息
                    if remote_item and "shared" in remote_item:
                        shared_by = remote_item.get("shared", {}).get("owner", {}).get("user", {}).get("displayName", "未知用户")
                    else:
                        shared_by = "未知用户"
                    
                    # 确定项目类型
                    if remote_item and "folder" in remote_item:
                        item_type = "📂 文件夹"
                    elif "folder" in item:
                        item_type = "📂 文件夹"
                    else:
                        item_type = "📄 文件"
                    
                    print(f"  {i+1}. {item_type} {name} (由 {shared_by} 共享)")
            else:
                # 显示普通文件夹内容
                if is_in_shared_items:
                    print(f"\n=== 共享项目: {current_path or '根目录'} ===\n")
                else:
                    print(f"\n=== 当前位置: {current_path or '根目录'} ===\n")
                
                items = self.list_items(current_path, is_in_shared_items, current_shared_item_id, current_remote_item)
                
                if not items or "value" not in items:
                    print("⚠️ 无法获取文件夹内容")
                    input("按Enter键返回上一级...")
                    
                    # 返回上一级目录
                    if is_in_shared_items:
                        if current_shared_item_id or current_remote_item:
                            current_shared_item_id = None
                            current_remote_item = None
                        else:
                            is_in_shared_items = False
                    elif "/" in current_path:
                        current_path = current_path.rsplit("/", 1)[0]
                    else:
                        current_path = ""
                    continue
                
                # 整理文件夹和文件
                folders = []
                files = []
                
                for item in items["value"]:
                    if item.get("folder"):
                        folders.append(item)
                    else:
                        files.append(item)
                
                # 显示文件夹
                print("文件夹:")
                if not folders:
                    print("  (无文件夹)")
                else:
                    for i, folder in enumerate(sorted(folders, key=lambda x: x["name"])):
                        print(f"  {i+1}. 📂 {folder['name']}")
                
                # 显示文件
                print("\n文件:")
                if not files:
                    print("  (无文件)")
                else:
                    for i, file in enumerate(sorted(files, key=lambda x: x["name"])):
                        size = file.get("size", None)
                        print(f"  {i+1}. 📄 {file['name']} ({self._format_size(size)})")
            
            # 用户操作
            print("\n操作:")
            print("  cd <编号> - 进入文件夹或共享项目")
            print("  cd .. - 返回上一级")
            print("  shared - 查看共享项目")
            print("  home - 返回个人根目录")
            print("  path - 显示当前完整路径")
            print("  download - 下载当前文件夹")
            print("  exit - 退出浏览器")
            
            choice = input("\n请输入命令: ").strip()
            
            if choice.lower() == "exit":
                break
            elif choice.lower() == "path":
                if is_in_shared_items:
                    if current_shared_item_id or current_remote_item:
                        print(f"\n共享项目路径: {current_path}")
                        if current_remote_item:
                            drive_id = current_remote_item.get("parentReference", {}).get("driveId", "未知")
                            item_id = current_remote_item.get("id", "未知")
                            print(f"驱动器ID: {drive_id}")
                            print(f"项目ID: {item_id}")
                        else:
                            print(f"项目ID: {current_shared_item_id}")
                        print("注意: 这是共享项目中的路径，下载时需要使用特殊格式")
                    else:
                        print("\n当前位置: 共享项目列表")
                else:
                    print(f"\n完整路径: {current_path}")
                input("按Enter键继续...")
            elif choice.lower() == "shared":
                is_in_shared_items = True
                current_shared_item_id = None
                current_remote_item = None
                current_path = ""
            elif choice.lower() == "home":
                is_in_shared_items = False
                current_shared_item_id = None
                current_remote_item = None
                current_path = ""
            elif choice.lower() == "download":
                if is_in_shared_items:
                    if current_remote_item:
                        drive_id = current_remote_item.get("parentReference", {}).get("driveId")
                        item_id = current_remote_item.get("id")
                        print(f"\n要下载的共享文件夹信息:")
                        print(f"驱动器ID: {drive_id}")
                        print(f"项目ID: {item_id}")
                        print("请使用以下命令下载:")
                        print(f"python onedrive_downloader_shared.py")
                        print(f"然后输入驱动器ID和项目ID: {drive_id} {item_id}")
                    elif current_shared_item_id:
                        print(f"\n要下载的共享文件夹ID: {current_shared_item_id}")
                        print("请使用以下命令下载:")
                        print(f"python onedrive_downloader_shared.py")
                        print(f"然后输入共享项目ID: {current_shared_item_id}")
                    else:
                        print("\n请先选择一个共享项目")
                else:
                    print(f"\n要下载的文件夹路径: {current_path}")
                    print("请使用以下命令下载:")
                    print(f"python onedrive_downloader.py")
                    print(f"然后输入: {current_path}")
                input("按Enter键继续...")
            elif choice.lower() == "cd ..":
                # 返回上一级目录
                if is_in_shared_items:
                    if current_shared_item_id or current_remote_item:
                        current_shared_item_id = None
                        current_remote_item = None
                        current_path = ""
                    else:
                        is_in_shared_items = False
                elif "/" in current_path:
                    current_path = current_path.rsplit("/", 1)[0]
                else:
                    current_path = ""
            elif choice.lower().startswith("cd "):
                try:
                    item_index = int(choice[3:].strip()) - 1
                    
                    if is_in_shared_items and current_shared_item_id is None and current_remote_item is None:
                        # 选择共享项目
                        if 0 <= item_index < len(shared_items_cache):
                            selected_item = shared_items_cache[item_index]
                            
                            # 检查是否是remoteItem类型
                            if "remoteItem" in selected_item:
                                current_remote_item = selected_item["remoteItem"]
                                current_shared_item_id = None
                            else:
                                current_shared_item_id = selected_item.get("id")
                                current_remote_item = None
                                
                            current_path = selected_item.get("name", "")
                        else:
                            print("无效的项目编号")
                            input("按Enter键继续...")
                    else:
                        # 选择普通文件夹
                        if not folders:
                            print("当前目录下没有文件夹")
                            input("按Enter键继续...")
                            continue
                            
                        # 获取排序后的文件夹列表
                        sorted_folders = sorted(folders, key=lambda x: x["name"])
                        folders_count = len(sorted_folders)
                        
                        if item_index >= folders_count:
                            print(f"错误：找不到编号 {item_index + 1} 的文件夹")
                            print(f"当前文件夹数量为: {folders_count}")
                            input("按Enter键继续...")
                        elif 0 <= item_index < folders_count:
                            selected_folder = sorted_folders[item_index]
                            folder_name = selected_folder["name"]
                            folder_id = selected_folder["id"]
                            
                            if is_in_shared_items:
                                # 在共享项目中导航
                                if current_remote_item:
                                    # 如果当前是remoteItem，则更新remoteItem
                                    if "remoteItem" in selected_folder:
                                        current_remote_item = selected_folder["remoteItem"]
                                    else:
                                        current_remote_item = selected_folder
                                else:
                                    # 否则更新shared_item_id
                                    current_shared_item_id = folder_id
                                
                                if current_path:
                                    current_path = f"{current_path}/{folder_name}"
                                else:
                                    current_path = folder_name
                            else:
                                # 在个人OneDrive中导航
                                if current_path:
                                    current_path = f"{current_path}/{folder_name}"
                                else:
                                    current_path = folder_name
                        else:
                            print("无效的文件夹编号")
                            input("按Enter键继续...")
                except ValueError:
                    print("无效的命令格式")
                    input("按Enter键继续...")
            else:
                print("无效的命令")
                input("按Enter键继续...")

def main():
    try:
        browser = OneDriveBrowser()
        browser.browse_folder()
        
    except Exception as e:
        print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    main() 