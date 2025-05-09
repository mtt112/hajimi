import asyncio
import time
from typing import Dict, Any
from app.utils.logging import log

class ActiveRequestsManager:
    """管理活跃API请求的类"""
    
    def __init__(self, requests_pool: Dict[str, asyncio.Task] = None):
        self.active_requests = requests_pool if requests_pool is not None else {}  # 存储活跃请求
    
    def add(self, key: str, task: asyncio.Task):
        """添加新的活跃请求任务"""
        task.creation_time = time.time()  # 添加创建时间属性
        self.active_requests[key] = task
    
    def get(self, key: str):
        """获取活跃请求任务"""
        return self.active_requests.get(key)
    
    def remove(self, key: str):
        """移除活跃请求任务"""
        if key in self.active_requests:
            del self.active_requests[key]
            return True
        return False
    
    def remove_by_prefix(self, prefix: str):
        """移除所有以特定前缀开头的活跃请求任务"""
        keys_to_remove = [k for k in self.active_requests.keys() if k.startswith(prefix)]
        for key in keys_to_remove:
            self.remove(key)
        return len(keys_to_remove)
    
    def clean_completed(self):
        """清理所有已完成或已取消的任务"""
        keys_to_remove = []
        
        for key, task in self.active_requests.items():
            if task.done() or task.cancelled():
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            self.remove(key)
        
        # if keys_to_remove:
        #    log('info', f"清理已完成请求任务: {len(keys_to_remove)}个", cleanup='active_requests')
    
    def clean_long_running(self, max_age_seconds: int = 300):
        """清理长时间运行的任务"""
        now = time.time()
        long_running_keys = []
        
        for key, task in list(self.active_requests.items()):
            if (hasattr(task, 'creation_time') and
                task.creation_time < now - max_age_seconds and
                not task.done() and not task.cancelled()):
                
                long_running_keys.append(key)
                task.cancel()  # 取消长时间运行的任务
        
        if long_running_keys:
            log('warning', f"取消长时间运行的任务: {len(long_running_keys)}个", cleanup='long_running_tasks')

async def check_client_disconnect(http_request, current_api_key: str, request_type: str, model: str):
    """检查客户端是否断开连接"""
    while True:
        if await http_request.is_disconnected():
            extra_log = {'key': current_api_key[:8], 'request_type': request_type, 'model': model, 'error_message': '检测到客户端断开连接'}
            log('info', "客户端连接已中断，等待API请求完成", extra=extra_log)
            return True
        await asyncio.sleep(0.5)