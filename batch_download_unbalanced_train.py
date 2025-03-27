#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
import time
import sys
import concurrent.futures
from msal import PublicClientApplication, SerializableTokenCache
from config import (
    CLIENT_ID, AUTHORITY, SCOPE, 
    DOWNLOAD_PATH, TOKEN_CACHE_FILE
)

class UnbalancedTrainBatchDownloader:
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
        
        # SharePoint站点信息
        self.site_id = None
        self.drive_id = None
        self.clap_folder_id = None
        self.a_t5_folder_id = None
        self.unbalanced_train_id = None
        
        # 站点URL
        self.site_hostname = "techn365.sharepoint.com"
        self.site_path = "/sites/clap"
        self.relative_path = "/CLAP_audio_dataset/a_t5/unbalanced_train"
        
        # 并行下载设置
        self.max_workers = 5  # 最大并行下载数量
        
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
    
    def get_site_id(self):
        """获取SharePoint站点ID"""
        if self.site_id:
            return self.site_id
            
        print(f"正在获取SharePoint站点ID: {self.site_hostname}{self.site_path}")
        endpoint = f"/sites/{self.site_hostname}:{self.site_path}"
        site_info = self._make_api_request(endpoint)
        
        if not site_info or "id" not in site_info:
            raise Exception("无法获取SharePoint站点ID")
            
        self.site_id = site_info["id"]
        print(f"已获取站点ID: {self.site_id}")
        return self.site_id
    
    def get_drive_id(self):
        """获取SharePoint文档库的驱动器ID"""
        if self.drive_id:
            return self.drive_id
            
        # 先获取站点ID
        site_id = self.get_site_id()
        
        # 获取文档库信息
        print("正在获取SharePoint文档库信息...")
        endpoint = f"/sites/{site_id}/drives"
        drives_info = self._make_api_request(endpoint)
        
        if not drives_info or "value" not in drives_info or not drives_info["value"]:
            raise Exception("无法获取SharePoint文档库信息")
            
        # 查找名为"datasets"的文档库或使用第一个文档库
        for drive in drives_info["value"]:
            print(f"找到文档库: {drive.get('name', '未命名')} (ID: {drive.get('id', '无ID')})")
            if drive.get("name") == "datasets" or "datasets" in drive.get("name", "").lower():
                self.drive_id = drive["id"]
                print(f"已选择datasets文档库 (ID: {self.drive_id})")
                return self.drive_id
                
        # 如果没有找到datasets文档库，使用第一个
        self.drive_id = drives_info["value"][0]["id"]
        print(f"未找到datasets文档库，使用第一个文档库 (ID: {self.drive_id})")
        return self.drive_id
    
    def navigate_to_folder(self, path_parts):
        """通过路径定位目标文件夹"""
        # 先获取驱动器ID
        drive_id = self.get_drive_id()
        
        # 检查路径是否为空
        if not path_parts:
            return None
            
        current_folder = None
        current_path = ""
        
        # 导航到每一级文件夹
        for folder_name in path_parts:
            if not folder_name:  # 跳过空文件夹名
                continue
                
            # 更新当前路径用于显示
            if current_path:
                current_path += "/" + folder_name
            else:
                current_path = folder_name
                
            print(f"正在查找文件夹: {current_path}")
            
            # 获取当前文件夹的子项目
            if current_folder:
                endpoint = f"/drives/{drive_id}/items/{current_folder}/children"
            else:
                endpoint = f"/drives/{drive_id}/root/children"
                
            folder_items = self._make_api_request(endpoint)
            
            if not folder_items or "value" not in folder_items:
                raise Exception(f"无法获取文件夹内容: {current_path}")
                
            # 在子项目中查找目标文件夹
            found = False
            for item in folder_items["value"]:
                if (item.get("folder") and 
                    (item.get("name").lower() == folder_name.lower() or 
                     folder_name.lower() in item.get("name", "").lower())):
                    current_folder = item["id"]
                    print(f"  找到文件夹: {item.get('name')} (ID: {current_folder})")
                    found = True
                    break
                    
            if not found:
                print(f"文件夹不存在: {current_path}")
                print("可用文件夹:")
                for item in folder_items["value"]:
                    if item.get("folder"):
                        print(f"  - {item.get('name')}")
                raise Exception(f"无法找到文件夹: {folder_name}")
                
        return current_folder
    
    def get_unbalanced_train_id(self):
        """获取unbalanced_train文件夹的ID"""
        if self.unbalanced_train_id:
            return self.unbalanced_train_id
            
        # 解析相对路径
        path_parts = self.relative_path.strip("/").split("/")
        print(f"路径组成部分: {path_parts}")
        
        # 导航到目标文件夹
        folder_id = self.navigate_to_folder(path_parts)
        
        if not folder_id:
            raise Exception(f"无法获取目标文件夹ID: {self.relative_path}")
            
        self.unbalanced_train_id = folder_id
        return self.unbalanced_train_id
    
    def get_item_info(self, item_id, drive_id=None):
        """获取项目信息"""
        if not drive_id:
            drive_id = self.get_drive_id()
            
        endpoint = f"/drives/{drive_id}/items/{item_id}"
        return self._make_api_request(endpoint)
    
    def list_items(self, item_id, drive_id=None):
        """列出指定项目中的所有子项目"""
        if not drive_id:
            drive_id = self.get_drive_id()
            
        endpoint = f"/drives/{drive_id}/items/{item_id}/children"
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
    
    def get_all_files(self):
        """获取unbalanced_train目录中所有文件"""
        # 获取目标文件夹ID
        folder_id = self.get_unbalanced_train_id()
        drive_id = self.get_drive_id()
        
        print(f"\n正在获取unbalanced_train目录中的文件 (ID: {folder_id})...")
        # 获取目录内容
        folder_items = self.list_items(folder_id, drive_id)
        if not folder_items or "value" not in folder_items:
            raise Exception("无法获取unbalanced_train目录内容")
        
        # 过滤出所有文件
        files = [item for item in folder_items["value"] if not item.get("folder")]
        print(f"找到 {len(files)} 个文件")
        
        return files
    
    def split_into_batches(self, files, batch_count=6):
        """将文件分成指定数量的批次"""
        if not files:
            return []
            
        batches = []
        files_per_batch = len(files) // batch_count
        remainder = len(files) % batch_count
        
        start_idx = 0
        for i in range(batch_count):
            # 如果有余数，前remainder个批次每个多分配一个文件
            batch_size = files_per_batch + (1 if i < remainder else 0)
            end_idx = start_idx + batch_size
            
            batches.append(files[start_idx:end_idx])
            start_idx = end_idx
        
        return batches
    
    def download_file(self, file_item, local_path):
        """下载单个文件"""
        # 获取下载链接
        item_id = file_item["id"]
        drive_id = self.get_drive_id()
        download_info = self.get_item_info(item_id, drive_id)
        
        if not download_info or "@microsoft.graph.downloadUrl" not in download_info:
            print(f"无法获取文件 {file_item['name']} 的下载链接")
            return False
            
        download_url = download_info["@microsoft.graph.downloadUrl"]
        
        # 创建本地目录（如果不存在）
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # 下载文件
        try:
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            file_size = int(response.headers.get("Content-Length", 0))
            print(f"正在下载: {file_item['name']} ({self._format_size(file_size)})")
            
            with open(local_path, "wb") as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # 显示下载进度
                        progress = (downloaded / file_size) * 100 if file_size > 0 else 0
                        print(f"\r{file_item['name']}: 进度 {progress:.1f}%", end="")
            
            print(f"\n{file_item['name']} 下载完成")
            return True
        except Exception as e:
            print(f"\n{file_item['name']} 下载失败: {str(e)}")
            return False
    
    def download_file_worker(self, file_info):
        """线程工作函数，用于并行下载"""
        file_item, local_path = file_info
        return self.download_file(file_item, local_path)
    
    def download_batch_parallel(self, batch_number):
        """并行下载指定批次的文件"""
        if batch_number < 1 or batch_number > 6:
            print("批次号必须在1到6之间")
            return
        
        print(f"准备下载第{batch_number}批次的文件")
        
        # 获取所有文件
        files = self.get_all_files()
        if not files:
            print("没有找到文件")
            return
            
        # 分批
        batches = self.split_into_batches(files)
        if batch_number > len(batches):
            print(f"只有{len(batches)}个批次可用")
            return
            
        batch = batches[batch_number - 1]
        print(f"第{batch_number}批次包含{len(batch)}个文件")
        
        # 创建批次特定的下载文件夹
        batch_dir = os.path.join(DOWNLOAD_PATH, f"batch_{batch_number}")
        os.makedirs(batch_dir, exist_ok=True)
        
        # 准备下载任务
        download_tasks = []
        skipped_files = []
        for file_item in batch:
            local_path = os.path.join(batch_dir, file_item["name"])
            if os.path.exists(local_path):
                file_size = os.path.getsize(local_path)
                print(f"文件已存在，跳过: {file_item['name']} ({self._format_size(file_size)})")
                skipped_files.append(file_item)
                continue
                
            download_tasks.append((file_item, local_path))
        
        if not download_tasks:
            print("所有文件已下载完成")
            return
            
        print(f"开始并行下载 {len(download_tasks)} 个文件 (最大并行数: {self.max_workers})")
        
        # 使用线程池并行下载
        successful_files = []
        failed_files = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self.download_file_worker, task): task[0]
                for task in download_tasks
            }
            
            # 处理完成的任务
            completed = 0
            for future in concurrent.futures.as_completed(future_to_file):
                file_item = future_to_file[future]
                filename = file_item['name']
                try:
                    success = future.result()
                    completed += 1
                    print(f"完成进度: {completed}/{len(download_tasks)} ({completed/len(download_tasks)*100:.1f}%)")
                    
                    if success:
                        successful_files.append(file_item)
                    else:
                        failed_files.append(file_item)
                        
                except Exception as e:
                    print(f"{filename} 下载时发生错误: {str(e)}")
                    failed_files.append(file_item)
        
        # 生成下载报告
        self._generate_download_report(batch, successful_files, failed_files, skipped_files, batch_number)
        
        print(f"第{batch_number}批次下载完成！")
        
        # 返回是否有失败的文件
        return len(failed_files) == 0
    
    def _generate_download_report(self, all_files, successful_files, failed_files, skipped_files, batch_number):
        """生成下载报告"""
        total_count = len(all_files)
        success_count = len(successful_files)
        failed_count = len(failed_files)
        skipped_count = len(skipped_files)
        
        print("\n" + "="*60)
        print(f"批次 {batch_number} 下载报告")
        print("="*60)
        print(f"总文件数: {total_count}")
        print(f"成功下载: {success_count} ({success_count/total_count*100:.1f}%)")
        print(f"下载失败: {failed_count} ({failed_count/total_count*100:.1f}%)")
        print(f"已存在跳过: {skipped_count} ({skipped_count/total_count*100:.1f}%)")
        print("-"*60)
        
        if failed_count > 0:
            print("\n下载失败的文件:")
            for i, file_item in enumerate(failed_files, 1):
                size = file_item.get("size", "未知大小")
                if isinstance(size, (int, float)):
                    size = self._format_size(size)
                print(f"  {i}. {file_item['name']} ({size})")
            
            # 保存失败文件列表到文件
            report_path = os.path.join(DOWNLOAD_PATH, f"batch_{batch_number}_failed_files.txt")
            try:
                with open(report_path, "w") as f:
                    f.write(f"批次 {batch_number} 下载失败的文件列表\n")
                    f.write(f"创建时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("-"*60 + "\n")
                    for file_item in failed_files:
                        size = file_item.get("size", "未知大小")
                        if isinstance(size, (int, float)):
                            size = self._format_size(size)
                        f.write(f"{file_item['name']} ({size})\n")
                print(f"\n下载失败文件列表已保存到: {report_path}")
            except Exception as e:
                print(f"保存失败文件列表出错: {str(e)}")
        
        print("="*60)
    
    def verify_batch(self, batch_number):
        """验证指定批次的下载情况"""
        if batch_number < 1 or batch_number > 6:
            print("批次号必须在1到6之间")
            return
        
        print(f"开始验证第{batch_number}批次的文件...")
        
        # 获取所有文件
        files = self.get_all_files()
        if not files:
            print("没有找到文件")
            return
            
        # 分批
        batches = self.split_into_batches(files)
        if batch_number > len(batches):
            print(f"只有{len(batches)}个批次可用")
            return
            
        batch = batches[batch_number - 1]
        print(f"第{batch_number}批次应包含{len(batch)}个文件")
        
        # 检查批次目录
        batch_dir = os.path.join(DOWNLOAD_PATH, f"batch_{batch_number}")
        if not os.path.exists(batch_dir):
            print(f"批次目录不存在: {batch_dir}")
            return
        
        # 验证每个文件
        existing_files = []
        missing_files = []
        for file_item in batch:
            local_path = os.path.join(batch_dir, file_item["name"])
            if os.path.exists(local_path):
                # 检查文件大小是否正确
                local_size = os.path.getsize(local_path)
                remote_size = file_item.get("size", 0)
                
                if remote_size > 0 and abs(local_size - remote_size) > 100:  # 允许小误差
                    missing_files.append((file_item, f"大小不匹配 (本地: {self._format_size(local_size)}, 远程: {self._format_size(remote_size)})"))
                else:
                    existing_files.append(file_item)
            else:
                missing_files.append((file_item, "文件不存在"))
        
        # 生成验证报告
        print("\n" + "="*60)
        print(f"批次 {batch_number} 验证报告")
        print("="*60)
        print(f"总文件数: {len(batch)}")
        print(f"存在且正确: {len(existing_files)} ({len(existing_files)/len(batch)*100:.1f}%)")
        print(f"缺失或错误: {len(missing_files)} ({len(missing_files)/len(batch)*100:.1f}%)")
        print("-"*60)
        
        if missing_files:
            print("\n缺失或错误的文件:")
            for i, (file_item, reason) in enumerate(missing_files, 1):
                size = file_item.get("size", "未知大小")
                if isinstance(size, (int, float)):
                    size = self._format_size(size)
                print(f"  {i}. {file_item['name']} ({size}) - {reason}")
            
            # 保存缺失文件列表到文件
            report_path = os.path.join(DOWNLOAD_PATH, f"batch_{batch_number}_missing_files.txt")
            try:
                with open(report_path, "w") as f:
                    f.write(f"批次 {batch_number} 缺失或错误的文件列表\n")
                    f.write(f"创建时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("-"*60 + "\n")
                    for file_item, reason in missing_files:
                        size = file_item.get("size", "未知大小")
                        if isinstance(size, (int, float)):
                            size = self._format_size(size)
                        f.write(f"{file_item['name']} ({size}) - {reason}\n")
                print(f"\n缺失文件列表已保存到: {report_path}")
            except Exception as e:
                print(f"保存缺失文件列表出错: {str(e)}")
        
        print("="*60)
        
        return missing_files
    
    def download_batch(self, batch_number, use_parallel=True):
        """下载指定批次的文件，支持选择是否使用并行下载"""
        if use_parallel:
            return self.download_batch_parallel(batch_number)
            
        # 以下是原来的顺序下载代码
        if batch_number < 1 or batch_number > 6:
            print("批次号必须在1到6之间")
            return
        
        print(f"准备下载第{batch_number}批次的文件")
        
        # 获取所有文件
        files = self.get_all_files()
        if not files:
            print("没有找到文件")
            return
            
        # 分批
        batches = self.split_into_batches(files)
        if batch_number > len(batches):
            print(f"只有{len(batches)}个批次可用")
            return
            
        batch = batches[batch_number - 1]
        print(f"第{batch_number}批次包含{len(batch)}个文件")
        
        # 创建批次特定的下载文件夹
        batch_dir = os.path.join(DOWNLOAD_PATH, f"batch_{batch_number}")
        os.makedirs(batch_dir, exist_ok=True)
        
        # 下载每个文件
        for file_item in batch:
            local_path = os.path.join(batch_dir, file_item["name"])
            if os.path.exists(local_path):
                file_size = os.path.getsize(local_path)
                print(f"文件已存在，跳过: {file_item['name']} ({self._format_size(file_size)})")
                continue
                
            self.download_file(file_item, local_path)
            # 添加短暂延迟以避免API限制
            time.sleep(0.5)
        
        print(f"第{batch_number}批次下载完成！")
    
    def list_all_batches(self):
        """列出所有批次及其包含的文件"""
        # 获取所有文件
        files = self.get_all_files()
        if not files:
            print("没有找到文件")
            return
            
        # 分批
        batches = self.split_into_batches(files)
        
        # 显示每个批次的文件
        for i, batch in enumerate(batches, 1):
            print(f"\n批次 {i} (包含 {len(batch)} 个文件):")
            for j, file_item in enumerate(batch, 1):
                size = file_item.get("size", "未知大小")
                if isinstance(size, (int, float)):
                    size = self._format_size(size)
                print(f"  {j}. {file_item['name']} ({size})")
    
    def set_max_workers(self, workers):
        """设置最大并行下载数量"""
        self.max_workers = max(1, min(20, workers))  # 限制在1-20之间
        print(f"设置最大并行下载数量为: {self.max_workers}")
    
    def download_missing_files(self, batch_number):
        """下载指定批次中缺失的文件"""
        if batch_number < 1 or batch_number > 6:
            print("批次号必须在1到6之间")
            return False
            
        print(f"开始检查第{batch_number}批次中缺失的文件...")
        
        # 先验证批次，找出缺失的文件
        missing_files = self.verify_batch(batch_number)
        
        if not missing_files:
            print("没有发现缺失文件，所有文件已正确下载")
            return True
            
        print(f"发现{len(missing_files)}个缺失或错误的文件，准备下载...")
        
        # 创建批次特定的下载文件夹
        batch_dir = os.path.join(DOWNLOAD_PATH, f"batch_{batch_number}")
        os.makedirs(batch_dir, exist_ok=True)
        
        # 准备下载任务
        download_tasks = []
        for file_item, reason in missing_files:
            local_path = os.path.join(batch_dir, file_item["name"])
            
            # 如果是大小不匹配，先删除现有文件
            if "大小不匹配" in reason and os.path.exists(local_path):
                try:
                    os.remove(local_path)
                    print(f"已删除大小不匹配的文件: {local_path}")
                except Exception as e:
                    print(f"删除文件失败: {local_path}, 错误: {str(e)}")
                    continue
                    
            download_tasks.append((file_item, local_path))
        
        if not download_tasks:
            print("没有需要下载的文件")
            return True
            
        print(f"开始并行下载 {len(download_tasks)} 个缺失文件 (最大并行数: {self.max_workers})")
        
        # 使用线程池并行下载
        successful_files = []
        failed_files = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self.download_file_worker, task): task[0]
                for task in download_tasks
            }
            
            # 处理完成的任务
            completed = 0
            for future in concurrent.futures.as_completed(future_to_file):
                file_item = future_to_file[future]
                filename = file_item['name']
                try:
                    success = future.result()
                    completed += 1
                    print(f"完成进度: {completed}/{len(download_tasks)} ({completed/len(download_tasks)*100:.1f}%)")
                    
                    if success:
                        successful_files.append(file_item)
                    else:
                        failed_files.append(file_item)
                        
                except Exception as e:
                    print(f"{filename} 下载时发生错误: {str(e)}")
                    failed_files.append(file_item)
        
        # 生成下载报告
        print("\n" + "="*60)
        print(f"缺失文件下载报告")
        print("="*60)
        print(f"总计尝试下载: {len(download_tasks)}个文件")
        print(f"成功下载: {len(successful_files)}个")
        print(f"下载失败: {len(failed_files)}个")
        print("-"*60)
        
        if failed_files:
            print("\n以下文件下载失败:")
            for i, file_item in enumerate(failed_files, 1):
                size = file_item.get("size", "未知大小")
                if isinstance(size, (int, float)):
                    size = self._format_size(size)
                print(f"  {i}. {file_item['name']} ({size})")
        
        print("="*60)
        
        return len(failed_files) == 0

def main():
    try:
        downloader = UnbalancedTrainBatchDownloader()
        
        if len(sys.argv) < 2:
            # 如果没有提供参数，显示用法信息
            print("用法:")
            print("  python batch_download_unbalanced_train.py list  - 列出所有批次及其包含的文件")
            print("  python batch_download_unbalanced_train.py <批次号>  - 下载指定批次的文件 (1-6)")
            print("  python batch_download_unbalanced_train.py <批次号> <并行数量>  - 设置并行下载数量并下载")
            print("  python batch_download_unbalanced_train.py verify <批次号>  - 验证指定批次的下载情况")
            print("  python batch_download_unbalanced_train.py missing <批次号>  - 只下载指定批次中缺失的文件")
            return
            
        command = sys.argv[1].lower()
        
        if command == "list":
            # 列出所有批次
            downloader.list_all_batches()
        elif command == "verify" and len(sys.argv) > 2 and sys.argv[2].isdigit():
            # 验证指定批次
            batch_number = int(sys.argv[2])
            downloader.verify_batch(batch_number)
        elif command == "missing" and len(sys.argv) > 2 and sys.argv[2].isdigit():
            # 下载缺失文件
            batch_number = int(sys.argv[2])
            # 检查是否提供了并行数量参数
            if len(sys.argv) > 3 and sys.argv[3].isdigit():
                workers = int(sys.argv[3])
                downloader.set_max_workers(workers)
            downloader.download_missing_files(batch_number)
        elif command.isdigit():
            # 下载指定批次
            batch_number = int(command)
            
            # 检查是否提供了并行数量参数
            if len(sys.argv) > 2 and sys.argv[2].isdigit():
                workers = int(sys.argv[2])
                downloader.set_max_workers(workers)
                
            # 使用并行下载
            downloader.download_batch(batch_number)
        else:
            print("无效的命令")
            print("用法:")
            print("  python batch_download_unbalanced_train.py list  - 列出所有批次及其包含的文件")
            print("  python batch_download_unbalanced_train.py <批次号>  - 下载指定批次的文件 (1-6)")
            print("  python batch_download_unbalanced_train.py <批次号> <并行数量>  - 设置并行下载数量并下载")
            print("  python batch_download_unbalanced_train.py verify <批次号>  - 验证指定批次的下载情况")
            print("  python batch_download_unbalanced_train.py missing <批次号>  - 只下载指定批次中缺失的文件")
            
    except Exception as e:
        print(f"发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 