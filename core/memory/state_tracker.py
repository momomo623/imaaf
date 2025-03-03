# core/memory/state_tracker.py
import time
from typing import List, Dict, Any
import json

class StateTracker:
    """状态跟踪器，管理操作历史和屏幕状态"""
    
    def __init__(self, max_history=20):
        """初始化状态跟踪器
        
        Args:
            max_history: 最大历史记录数
        """
        self.action_history = []  # 操作历史
        self.screenshots = []  # 截图历史
        self.max_history = max_history  # 最大历史记录数
    
    def add_action(self, action, result):
        """添加操作记录
        
        Args:
            action: 执行的操作
            result: 操作结果
        """
        # 记录操作历史
        self.action_history.append({
            "action_type": action.get("action_type", "unknown"),
            "action": action,
            "result": result,
            "timestamp": time.time()
        })
        
        # 限制历史记录数量
        if len(self.action_history) > self.max_history:
            self.action_history = self.action_history[-self.max_history:]
    
    def add_screenshot(self, screenshot):
        """添加截图记录
        
        Args:
            screenshot: 屏幕截图
        """
        self.screenshots.append(screenshot)
        
        # 限制历史记录数量
        if len(self.screenshots) > self.max_history:
            self.screenshots = self.screenshots[-self.max_history:]
    
    def get_recent_actions(self, count=5):
        """获取最近的操作记录
        
        Args:
            count: 获取的记录数量
            
        Returns:
            list: 最近的操作记录
        """
        return self.action_history[-count:] if self.action_history else []
    
    def get_last_screenshot(self):
        """获取最近的截图
        
        Returns:
            object: 最近的截图，如果没有则返回None
        """
        return self.screenshots[-1] if self.screenshots else None
    
    def clear_history(self):
        """清空历史记录"""
        self.action_history = []
        self.screenshots = []
    
    def optimize_memory(self):
        """优化内存使用"""
        # 压缩历史操作中的图像数据
        for action in self.action_history:
            if 'screenshot' in action:
                # 删除不必要的图像数据
                del action['screenshot']
        
        # 手动触发垃圾回收
        import gc
        gc.collect()
    
    def save_history(self, filename="action_history.json"):
        """保存操作历史到文件
        
        Args:
            filename: 保存的文件名
        """
        # 创建可序列化的历史记录
        serializable_history = []
        for action in self.action_history:
            # 复制一份，避免修改原始数据
            action_copy = action.copy()
            
            # 移除不可序列化的数据
            if 'screenshot' in action_copy:
                del action_copy['screenshot']
            
            serializable_history.append(action_copy)
        
        # 保存到文件
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(serializable_history, f, ensure_ascii=False, indent=2)