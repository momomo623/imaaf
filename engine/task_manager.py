import time
import json
import os
from typing import Dict, Any, List, Optional

class TaskManager:
    """任务管理器，负责管理和执行任务"""
    
    def __init__(self, agent):
        """初始化任务管理器
        
        Args:
            agent: 代理实例，用于执行具体操作
        """
        self.agent = agent
        self.current_task = None
        self.task_history = []
        self.max_task_history = 10
        
    def execute_task(self, task_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务
        
        Args:
            task_config: 任务配置，包含工具名称、参数等
            
        Returns:
            Dict: 任务执行结果
        """
        tool_name = task_config.get("tool")
        params = task_config.get("params", {})
        max_steps = task_config.get("max_steps", 15)
        wait_time = task_config.get("wait_time", 1.5)
        
        if not tool_name:
            return {"success": False, "error": "未指定工具名称"}
        
        # 记录当前任务
        self.current_task = {
            "tool": tool_name,
            "params": params,
            "start_time": time.time()
        }
        
        # 运行工具
        try:
            result = self.agent.run_tool(tool_name, params)
            
            # 更新任务状态
            self.current_task["end_time"] = time.time()
            self.current_task["result"] = result
            self.current_task["success"] = result.get("success", False)
            
            # 添加到历史记录
            self.task_history.append(self.current_task)
            
            # 限制历史记录数量
            if len(self.task_history) > self.max_task_history:
                self.task_history = self.task_history[-self.max_task_history:]
            
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e)
            }
            
            # 更新任务状态
            self.current_task["end_time"] = time.time()
            self.current_task["result"] = error_result
            self.current_task["success"] = False
            
            # 添加到历史记录
            self.task_history.append(self.current_task)
            
            return error_result
    
    def schedule_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """调度执行多个任务
        
        Args:
            tasks: 任务列表
            
        Returns:
            List[Dict]: 所有任务的执行结果
        """
        results = []
        
        for task in tasks:
            print(f"执行任务: {task.get('tool')} - 参数: {json.dumps(task.get('params', {}), ensure_ascii=False)}")
            result = self.execute_task(task)
            results.append(result)
            
            # 如果任务失败且配置为失败时停止，则中断执行
            if not result.get("success", False) and task.get("stop_on_failure", False):
                print(f"任务失败，停止执行后续任务")
                break
                
            # 任务间等待
            wait_time = task.get("wait_after", 2)
            if wait_time > 0 and task != tasks[-1]:  # 不是最后一个任务
                time.sleep(wait_time)
        
        return results
    
    def save_task_results(self, results: List[Dict[str, Any]], output_dir: str = "output") -> str:
        """保存任务执行结果
        
        Args:
            results: 任务执行结果列表
            output_dir: 输出目录
            
        Returns:
            str: 保存的文件路径
        """
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名
        timestamp = int(time.time())
        filename = f"{output_dir}/task_results_{timestamp}.json"
        
        # 保存结果
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"任务结果已保存到: {filename}")
        return filename
    
    def get_task_status(self, task_id: Optional[int] = None) -> Dict[str, Any]:
        """获取任务状态
        
        Args:
            task_id: 任务ID（历史记录索引），None表示当前任务
            
        Returns:
            Dict: 任务状态信息
        """
        if task_id is not None:
            if 0 <= task_id < len(self.task_history):
                return self.task_history[task_id]
            else:
                return {"error": "无效的任务ID"}
        
        return self.current_task if self.current_task else {"error": "当前没有正在执行的任务"}
    
    def optimize_memory(self):
        """优化内存使用"""
        # 清理任务历史中的大型数据
        for task in self.task_history:
            if "result" in task and "data" in task["result"]:
                # 如果结果中包含大量数据，可以选择性地删除或压缩
                if isinstance(task["result"]["data"], list) and len(task["result"]["data"]) > 100:
                    task["result"]["data"] = f"[数据已压缩，原始大小: {len(task['result']['data'])}项]"
        
        # 手动触发垃圾回收
        import gc
        gc.collect()
