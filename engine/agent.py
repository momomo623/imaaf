# engine/agent.py
import logging
import time
from core.device.adb_controller import ADBController
from core.perception.visual_engine import VisualEngine
from core.cognition.ai_brain import AIBrain
from core.memory.state_tracker import StateTracker
from engine.tools.app_launcher import AppLauncher

class Agent:
    """代理执行器，集成所有核心功能"""
    
    def __init__(self, device_id=None, emulator_path=None, wifi_device=None):
        """初始化代理"""
        # 初始化核心组件
        self.device = ADBController(device_id, emulator_path, wifi_device)
        self.vision = VisualEngine()
        self.brain = AIBrain()
        self.memory = StateTracker()
        
        # 导入工具注册中心
        from utools.tool_registry import ToolRegistry
        self.registry = ToolRegistry()  # 添加registry属性
        
        # 导入配置管理器
        from uutils.config_manager import ConfigManager
        self.config = ConfigManager()
        
        # 初始化应用启动器
        self.app_launcher = AppLauncher(
            device=self.device,
            vision=self.vision,
            brain=self.brain,
            config=self.config
        )
        
        # 内部状态
        self.running = False
        self.current_tool = None
        
        # 添加应用启动相关参数
        self.app_launch_timeout = 10  # 应用启动超时时间（秒）
        
        print(f"Agent初始化完成，设备ID: {device_id}, WiFi设备: {wifi_device}, 模拟器路径: {emulator_path}")
    
    def execute_action(self, action):
        """执行单个动作
        
        Args:
            action: 要执行的动作
            
        Returns:
            dict: 执行结果
        """
        action_type = action.get("action_type", "").lower()
        result = {"success": False, "message": "未知操作"}
        
        if action_type == "click":
            # 如果指定使用视觉搜索
            if action.get("use_visual_search", False):
                result = self._execute_visual_search_action(action)
            else:
                target = action.get("target", "")
                # 处理坐标点击
                if isinstance(target, (list, tuple)) and len(target) == 2:
                    x, y = target
                    self.device.tap(x, y)
                    result = {"success": True, "message": f"点击坐标 ({x}, {y})"}
                # 处理文本点击
                elif isinstance(target, str):
                    current_screen = self.capture_and_analyze()
                    # 查找匹配文本
                    matches = self.vision.find_text(
                        target, 
                        current_screen["text_elements"]
                    )
                    
                    if matches:
                        best_match = matches[0]
                        x, y = best_match["center"]
                        self.device.tap(x, y)
                        result = {
                            "success": True, 
                            "message": f"点击文本 '{best_match['text']}' 位置 ({x}, {y})",
                            "match": best_match
                        }
                    else:
                        result = {"success": False, "message": f"未找到目标: {target}"}
        
        # 滑动操作
        elif action_type == "swipe":
            direction = action.get("direction", "up")
            self.device.adaptive_swipe(direction)
            result = {"success": True, "message": f"滑动方向: {direction}"}
        
        # 文本输入
        elif action_type == "input":
            text = action.get("text", "")
            self.device.input_text(text)
            result = {"success": True, "message": f"输入文本: {text}"}
        
        # 返回键
        elif action_type == "back":
            self.device.press_back()
            result = {"success": True, "message": "按下返回键"}
        
        # Home键
        elif action_type == "home":
            self.device.press_home()
            result = {"success": True, "message": "按下Home键"}
        
        # 记录操作历史
        self.memory.add_action(action, result)
            
        return result
    
    def _execute_visual_search_action(self, action):
        """执行基于OCR文本匹配的操作"""
        target = action.get("target", "")
        if not target:
            return {"success": False, "message": "未指定搜索目标"}
        
        # 获取当前屏幕
        current_screen = self.capture_and_analyze()
        
        # 使用文本匹配查找目标
        matches = self.vision.find_text(
            query_text=target,
            text_elements=current_screen["text_elements"]
        )
        
        if not matches:
            return {"success": False, "message": f"未找到与'{target}'匹配的元素"}
        
        best_match = matches[0]
        
        # 执行点击操作
        x, y = best_match["center"]
        self.device.tap(x, y)
        return {
            "success": True,
            "message": f"点击文本 '{best_match['text']}' 位置 ({x}, {y})",
            "match": best_match
        }
    
    def capture_and_analyze(self):
        """捕获并分析屏幕
        
        Returns:
            dict: 包含截图、文本元素和时间戳的字典
        """
        screenshot = self.device.capture_screenshot()  # 截图
        self.memory.add_screenshot(screenshot)  # 保存截图
        
        # 提取文本元素
        text_elements = self.vision.extract_text(screenshot)
        
        # 返回分析结果
        return {
            "screenshot": screenshot,
            "text_elements": text_elements,
            "timestamp": time.time()
        }
    
    def run_tool(self, tool_name, params=None):
        """运行指定的工具
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            
        Returns:
            dict: 工具执行结果
        """
        try:
            # 使用实例属性registry而不是重新创建
            tool_class = self.registry.get_tool(tool_name)
            
            # 创建工具实例
            tool_instance = tool_class(self)
            self.current_tool = tool_instance
            
            # 设置工具
            print(f"设置工具: {tool_name}")
            tool_instance.setup()
            
            # 运行工具
            print(f"运行工具: {tool_name}")
            result = tool_instance.run(params)
            
            # 清理工具
            print(f"清理工具: {tool_name}")
            tool_instance.cleanup()
            
            return result
            
        except Exception as e:
            print(f"工具执行错误: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_task(self, objective, max_steps=15, wait_time=1.5):
        """执行任务（兼容旧接口，推荐使用TaskManager）
        
        Args:
            objective: 任务目标
            max_steps: 最大执行步骤数
            wait_time: 每步等待时间
            
        Returns:
            dict: 执行结果
        """
        print("警告: 直接使用Agent.execute_task已弃用，推荐使用TaskManager")
        
        # 创建任务管理器
        from engine.task_manager import TaskManager
        task_manager = TaskManager(self)
        
        # 如果objective是字符串，假设它是一个工具名称
        if isinstance(objective, str):
            return task_manager.execute_task({"tool": objective})
        
        # 如果objective是字典，直接作为任务配置
        if isinstance(objective, dict):
            return task_manager.execute_task(objective)
        
        # 否则返回错误
        return {
            "success": False,
            "error": "无效的任务目标格式"
        }
    
    def launch_app(self, app_name, tool_name=None):
        """启动应用(委托给应用启动器)
        
        Args:
            app_name: 要启动的应用名称
            tool_name: 可选，工具名称（用于自定义启动检查）
        
        Returns:
            bool: 是否成功启动应用
        """
        return self.app_launcher.launch_app(
            app_name=app_name, 
            tool_name=tool_name,
            tool_registry=self.registry
        )
    
    def _detect_search_box(self, screenshot):
        """检测搜索框区域"""
        height, width = screenshot.shape[:2]
        
        # 使用OCR定位搜索框
        text_elements = self.vision.extract_text(screenshot)
        search_matches = self.vision.find_text("搜索", text_elements)
        
        if search_matches:
            best_match = search_matches[0]
            x1, y1, x2, y2 = best_match["bbox"]
            # 扩大搜索框区域，确保完全覆盖
            y2 = min(y2 + 50, height)  # 向下扩展50像素，但不超过屏幕高度
            return (x1, y1, x2, y2)
        
        # 默认返回顶部区域
        return (0, 0, width, 300)
