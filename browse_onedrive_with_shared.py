#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
import time
import sys
from msal import PublicClientApplication, SerializableTokenCache
from config import (
    CLIENT_ID, AUTHORITY, SCOPE, 
    DOWNLOAD_PATH, TOKEN_CACHE_FILE
)

class OneDriveSharedBrowser:
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
    
    def list_shared_items(self):
        """列出所有共享项目"""
        endpoint = "/me/drive/sharedWithMe"
        return self._make_api_request(endpoint)
    
    def list_items(self, item_id, drive_id=None):
        """列出指定项目中的所有子项目"""
        if drive_id:
            # 如果提供了驱动器ID，使用drives端点
            endpoint = f"/drives/{drive_id}/items/{item_id}/children"
        else:
            # 否则使用默认驱动器
            endpoint = f"/me/drive/items/{item_id}/children"
        return self._make_api_request(endpoint)
    
    def get_item_info(self, item_id, drive_id=None):
        """获取项目信息"""
        if drive_id:
            # 如果提供了驱动器ID，使用drives端点
            endpoint = f"/drives/{drive_id}/items/{item_id}"
        else:
            # 否则使用默认驱动器
            endpoint = f"/me/drive/items/{item_id}"
        return self._make_api_request(endpoint)
    
    def browse_directory(self, item_id=None, drive_id=None, path=""):
        """浏览目录并显示文件和文件夹数量"""
        if item_id is None:
            # 如果没有指定item_id，则浏览共享根目录
            print("\n浏览OneDrive共享项目")
            shared_items = self.list_shared_items()
            if not shared_items or "value" not in shared_items:
                print("无法获取共享项目列表")
                return
            
            full_path = "共享项目"
            print(f"\n当前目录: {full_path}")
            
            # 获取共享项目数量
            items = shared_items["value"]
            folders = [item for item in items if item.get("remoteItem", {}).get("folder")]
            files = [item for item in items if not item.get("remoteItem", {}).get("folder")]
            
            folder_count = len(folders)
            file_count = len(files)
            
            print(f"该目录包含 {folder_count} 个文件夹和 {file_count} 个文件")
            
            # 显示所有文件夹
            if folder_count > 0:
                print("\n文件夹:")
                for idx, folder in enumerate(folders, 1):
                    print(f"  {idx}. {folder['name']}")
            
            # 显示所有文件
            if file_count > 0:
                print("\n文件:")
                for idx, file in enumerate(files, 1):
                    remote_item = file.get("remoteItem", {})
                    size = remote_item.get("size", "未知大小")
                    if isinstance(size, (int, float)):
                        size = self._format_size(size)
                    print(f"  {idx}. {file['name']} ({size})")
        else:
            # 获取指定项目信息
            item_info = self.get_item_info(item_id, drive_id)
            if not item_info:
                print(f"无法获取项目信息: {item_id}")
                return
            
            item_name = item_info.get("name", "未命名项目")
            full_path = f"{path}/{item_name}" if path else item_name
            
            # 获取子项目
            items_result = self.list_items(item_id, drive_id)
            if not items_result or "value" not in items_result:
                print(f"无法获取项目内容: {item_id}")
                return
            
            print(f"\n当前目录: {full_path}")
            
            # 计算文件和文件夹数量
            items = items_result["value"]
            folders = [item for item in items if item.get("folder")]
            files = [item for item in items if not item.get("folder")]
            
            folder_count = len(folders)
            file_count = len(files)
            
            print(f"该目录包含 {folder_count} 个文件夹和 {file_count} 个文件")
            
            # 显示所有文件夹
            if folder_count > 0:
                print("\n文件夹:")
                for idx, folder in enumerate(folders, 1):
                    print(f"  {idx}. {folder['name']}")
            
            # 显示所有文件
            if file_count > 0:
                print("\n文件:")
                for idx, file in enumerate(files, 1):
                    size = file.get("size", "未知大小")
                    if isinstance(size, (int, float)):
                        size = self._format_size(size)
                    print(f"  {idx}. {file['name']} ({size})")

        # 模拟终端提示符和命令处理
        while True:
            command = input(f"\n{full_path}> ").strip()
            
            if not command:
                continue
                
            cmd_parts = command.split()
            cmd = cmd_parts[0].lower()
            
            if cmd == "help" or cmd == "?":
                print("\n可用命令:")
                print("  ls             - 列出当前目录内容")
                print("  cd <序号>       - 进入指定序号的文件夹")
                print("  cd ..          - 返回上级目录")
                print("  exit/quit      - 退出程序")
                print("  help/?         - 显示帮助信息")
                
            elif cmd == "ls":
                # 重新显示当前目录内容
                print(f"该目录包含 {folder_count} 个文件夹和 {file_count} 个文件")
                
                if folder_count > 0:
                    print("\n文件夹:")
                    for idx, folder in enumerate(folders, 1):
                        print(f"  {idx}. {folder['name']}")
                
                if file_count > 0:
                    print("\n文件:")
                    for idx, file in enumerate(files, 1):
                        if item_id is None:  # 在根目录
                            remote_item = file.get("remoteItem", {})
                            size = remote_item.get("size", "未知大小")
                        else:
                            size = file.get("size", "未知大小")
                        if isinstance(size, (int, float)):
                            size = self._format_size(size)
                        print(f"  {idx}. {file['name']} ({size})")
                
            elif cmd == "cd":
                if len(cmd_parts) < 2:
                    print("请指定要进入的文件夹序号或 '..' 返回上级")
                    continue
                    
                if cmd_parts[1] == "..":
                    # 返回上级目录
                    if item_id is not None:  # 只有非根目录可以返回
                        return
                    else:
                        print("已在根目录，无法返回上级")
                else:
                    # 尝试解析序号并进入子文件夹
                    try:
                        folder_idx = int(cmd_parts[1]) - 1
                        if 0 <= folder_idx < folder_count:
                            selected_folder = folders[folder_idx]
                            
                            # 处理共享项目和常规项目的区别
                            if item_id is None:  # 在根目录
                                remote_item = selected_folder.get("remoteItem", {})
                                subfolder_id = remote_item.get("id", selected_folder.get("id"))
                                subfolder_drive_id = remote_item.get("parentReference", {}).get("driveId")
                            else:  # 在子目录
                                subfolder_id = selected_folder["id"]
                                subfolder_drive_id = selected_folder.get("parentReference", {}).get("driveId", drive_id)
                            
                            self.browse_directory(subfolder_id, subfolder_drive_id, full_path)
                        else:
                            print("无效的文件夹序号")
                    except ValueError:
                        print("请输入有效的数字或 '..'")
                
            elif cmd == "exit" or cmd == "quit":
                print("退出程序")
                sys.exit(0)
                
            else:
                print(f"未知命令: {cmd}")
                print("输入 'help' 或 '?' 获取帮助")
    
    def _format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes is None:
            return "未知大小"
            
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

def main():
    try:
        browser = OneDriveSharedBrowser()
        
        # 从共享根目录开始浏览，而不是直接进入指定目录
        browser.browse_directory()
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 