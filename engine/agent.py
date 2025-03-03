# engine/agent.py
import logging
import time
from core.device.adb_controller import ADBController
from core.perception.visual_engine import VisualEngine
from core.cognition.ai_brain import AIBrain
from core.memory.state_tracker import StateTracker

class Agent:
    """代理执行器，集成所有核心功能"""
    
    def __init__(self, device_id=None, emulator_path=None):
        """初始化代理"""
        # 初始化核心组件
        self.device = ADBController(device_id, emulator_path)
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
        
        print(f"Agent初始化完成，设备ID: {device_id}, 模拟器路径: {emulator_path}")
    
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
                    # 语义搜索匹配文本
                    matches = self.vision.semantic_search(
                        target, 
                        current_screen["screenshot"],
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
        """执行基于视觉语义搜索的操作"""
        target = action.get("target", "")
        if not target:
            return {"success": False, "message": "未指定搜索目标"}
        
        # 获取当前屏幕
        current_screen = self.capture_and_analyze()
        
        # 使用混合语义搜索
        matches = self.vision.hybrid_semantic_search(
            query_text=target,
            image=current_screen["screenshot"],
            text_elements=current_screen["text_elements"]
        )
        
        if not matches:
            return {"success": False, "message": f"未找到与'{target}'匹配的元素"}
        
        best_match = matches[0]
        
        # 根据匹配类型处理点击操作
        if best_match["type"] == "text":
            # 文本匹配结果
            x, y = best_match["data"]["center"]
            self.device.tap(x, y)
            return {
                "success": True,
                "message": f"点击文本 '{best_match['data']['text']}' 位置 ({x}, {y})",
                "match_type": "text",
                "match": best_match["data"]
            }
        else:
            # 视觉区域匹配结果
            x, y = best_match["data"]["center"]
            self.device.tap(x, y)
            return {
                "success": True,
                "message": f"点击视觉区域中心 ({x}, {y})",
                "match_type": "visual",
                "match": best_match["data"]
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
        """通用应用启动流程
        
        Args:
            app_name: 要启动的应用名称
            tool_name: 可选，工具名称（用于自定义启动检查）
        """
        logging.info(f"开始启动应用: {app_name}")
        
        # 第一步：返回主屏幕
        self.device.press_home()
        time.sleep(1.5)
        
        # 第二步：多次尝试上滑调出搜索框
        for attempt in range(3):
            self.device.adaptive_swipe("up", distance_factor=0.4+attempt*0.1)
            time.sleep(1.5)
            
            # 检查是否出现搜索框
            screenshot = self.device.capture_screenshot()
            matches = self.vision.hybrid_semantic_search("搜索", screenshot)
            if matches:
                print(f"第{attempt+1}次滑动成功调出搜索框")
                
                # 点击搜索框
                best_match = matches[0]
                x, y = best_match["data"]["center"]
                print(f"点击搜索框位置: ({x}, {y})")
                self.device.tap(x, y)
                time.sleep(1)
                break
        else:
            print("三次滑动尝试均未调出搜索框")
            return False
        
        # 第三步：输入应用名称
        self.device.input_text(app_name)
        
        # 第四步：视觉识别应用图标
        screenshot = self.device.capture_screenshot()
        height, width = screenshot.shape[:2]
        logging.info(f"屏幕尺寸: {width}x{height}")
        # 获取并记录搜索框区域
        search_box_region = self._detect_search_box(screenshot)
        logging.info(f"搜索框区域: {search_box_region}")
        # 在搜索框下方搜索应用图标
        matches = self.vision.hybrid_semantic_search(
            query_text=app_name,
            image=screenshot,
            exclude_regions=[search_box_region]
        )
        
        logging.info(f"找到 {len(matches)} 个匹配项")
        for i, match in enumerate(matches[:3]):
            logging.info(f"匹配项 {i+1}: 类型={match['type']} "
                        f"分数={match['score']:.3f} "
                        f"位置={match['data']['center']}")
        
        if not matches:
            print(f"未找到应用: {app_name}")
            return False
        
        # 选择最佳匹配项
        best_match = matches[0]
        x, y = best_match["data"]["center"]
        
        # 第五步：点击应用图标
        logging.info(f"点击应用图标位置: ({x}, {y})")
        self.device.tap(x, y)
        
        # 第六步：等待应用启动
        start_time = time.time()
        while time.time() - start_time < self.app_launch_timeout:
            try:
                if tool_name:
                    # 使用传入的工具名称获取工具类
                    tool_class = self.registry.get_tool(tool_name)
                elif self.current_tool:
                    # 使用当前工具
                    tool_class = self.registry.get_tool(self.current_tool.name)
                else:
                    # 没有工具信息时使用默认检查
                    tool_class = None
                
                # 如果有工具类且定义了启动检查方法，使用它
                if tool_class and hasattr(tool_class, 'check_app_launched'):
                    if tool_class.check_app_launched(self):
                        logging.info(f"应用 {app_name} 启动成功（自定义检查）")
                        return True
                else:
                    # 使用默认的视觉检查
                    screenshot = self.device.capture_screenshot()
                    matches = self.vision.hybrid_semantic_search(
                        query_text=app_name,
                        image=screenshot
                    )
                    if matches and matches[0]["score"] > 0.7:
                        logging.info(f"应用 {app_name} 启动成功（默认检查）")
                        return True
                
                time.sleep(1)
                
            except Exception as e:
                logging.error(f"启动检查时出错: {str(e)}")
                # 继续尝试检查，而不是直接失败
                
        logging.warning(f"应用 {app_name} 启动超时")
        return False
    
    def _detect_search_box(self, screenshot):
        """检测搜索框区域"""
        height, width = screenshot.shape[:2]
        
        # 使用视觉搜索定位搜索框
        search_box_matches = self.vision.hybrid_semantic_search(
            "搜索", 
            screenshot,
            exclude_regions=[]
        )
        
        if search_box_matches:
            best_match = search_box_matches[0]
            x1, y1, x2, y2 = best_match["data"]["bbox"]
            # 扩大搜索框区域，确保完全覆盖
            y2 = min(y2 + 50, height)  # 向下扩展50像素，但不超过屏幕高度
            return (x1, y1, x2, y2)
        
        # 默认返回顶部区域
        return (0, 0, width, 300)
