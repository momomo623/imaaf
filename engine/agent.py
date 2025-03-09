# engine/agent.py
import logging
import time
from core.device.adb_controller import ADBController
from core.perception.visual_engine import VisualEngine
from core.cognition.ai_brain import AIBrain
from core.memory.state_tracker import StateTracker

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
        """改进的应用启动流程 - 使用APP抽屉方式
        
        Args:
            app_name: 要启动的应用名称
            tool_name: 可选，工具名称（用于自定义启动检查）
        """
        logging.info(f"开始启动应用: {app_name}")
        
        # 第一步：返回主屏幕
        self.device.press_home()
        time.sleep(1.5)
        
        # 第二步：尝试打开应用抽屉(多种方式)
        app_drawer_found = False
        
        # 方式1: 上滑打开
        for attempt in range(2):
            self.device.adaptive_swipe("up", distance_factor=0.4+attempt*0.1)
            time.sleep(1.5)
            
            # 检查是否出现应用列表
            screenshot = self.device.capture_screenshot()
            text_elements = self.vision.extract_text(screenshot)
            
            # 先尝试直接在应用抽屉中查找目标应用
            app_matches = self.vision.find_text(app_name, text_elements)
            if app_matches:
                logging.info(f"在应用抽屉中直接找到应用: {app_name}")
                app_drawer_found = True
                break
            
            # 检查是否有搜索应用的入口
            search_matches = self.vision.find_text("搜索", text_elements)
            if search_matches or any("应用" in elem["text"] for elem in text_elements):
                app_drawer_found = True
                break
        
        # 方式2: 如果上滑失败，尝试点击应用抽屉图标
        if not app_drawer_found:
            logging.info("尝试通过点击应用抽屉图标打开")
            # 屏幕底部中心区域可能有应用抽屉图标
            width, height = self.device.get_screen_size()
            self.device.tap(width//2, height-100)  # 点击底部中心
            time.sleep(1.5)
            
            # 再次检查是否成功打开
            screenshot = self.device.capture_screenshot()
            text_elements = self.vision.extract_text(screenshot)
            app_matches = self.vision.find_text(app_name, text_elements)
            if app_matches:
                app_drawer_found = True
            
        # 如果无法打开应用抽屉，则尝试在主屏幕上查找
        if not app_drawer_found:
            logging.warning("无法打开应用抽屉，尝试在主屏幕上查找应用")
            screenshot = self.device.capture_screenshot()
            text_elements = self.vision.extract_text(screenshot)
            app_matches = self.vision.find_text(app_name, text_elements)
            
            if not app_matches:
                logging.error(f"无法找到应用: {app_name}")
                return False
        else:
            # 应用抽屉已打开，在这里搜索应用
            logging.info("应用抽屉已打开，搜索应用")
            screenshot = self.device.capture_screenshot()
            text_elements = self.vision.extract_text(screenshot)
            app_matches = self.vision.find_text(app_name, text_elements)
            
            # 如果没有立即找到，尝试滑动几次查找
            page_count = 0
            while not app_matches and page_count < 3:
                self.device.adaptive_swipe("up", distance_factor=0.3)
                time.sleep(1)
                screenshot = self.device.capture_screenshot()
                text_elements = self.vision.extract_text(screenshot)
                app_matches = self.vision.find_text(app_name, text_elements)
                page_count += 1
        
        # 如果找到了应用，点击它
        if app_matches:
            best_match = app_matches[0]
            x, y = best_match["center"]
            logging.info(f"找到应用图标，位置: ({x}, {y})")
            self.device.tap(x, y)
            
            # 等待应用启动
            start_time = time.time()
            while time.time() - start_time < self.app_launch_timeout:
                try:
                    if tool_name and hasattr(self.registry.get_tool(tool_name), 'check_app_launched'):
                        tool_class = self.registry.get_tool(tool_name)
                        if tool_class.check_app_launched(self):
                            logging.info(f"应用 {app_name} 启动成功（自定义检查）")
                            return True
                    else:
                        # 默认检查
                        screenshot = self.device.capture_screenshot()
                        text_elements = self.vision.extract_text(screenshot)
                        matches = self.vision.find_text(app_name, text_elements)
                        if matches:
                            logging.info(f"应用 {app_name} 启动成功（默认检查）")
                            return True
                    
                    time.sleep(1)
                    
                except Exception as e:
                    logging.error(f"启动检查时出错: {str(e)}")
            
            logging.warning(f"应用 {app_name} 启动超时")
            return False
        else:
            logging.error(f"无法找到应用: {app_name}")
            return False
    
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
