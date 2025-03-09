import time
import logging

class AppLauncher:
    """专用应用启动器，处理所有与应用启动相关的功能"""
    
    def __init__(self, device, vision, brain, config):
        """初始化应用启动器
        
        Args:
            device: 设备控制器
            vision: 视觉引擎
            brain: AI大脑
            config: 配置管理器
        """
        self.device = device
        self.vision = vision
        self.brain = brain
        self.config = config
        
        # 启动超时设置
        self.app_launch_timeout = 10  # 应用启动超时时间（秒）
    
    def launch_app(self, app_name, tool_name=None, tool_registry=None):
        """智能应用启动流程，优先使用配置信息，失败则回退到视觉方式
        
        Args:
            app_name: 要启动的应用名称
            tool_name: 可选，工具名称（用于自定义启动检查）
            tool_registry: 可选，工具注册中心实例
        
        Returns:
            bool: 是否成功启动应用
        """
        logging.info(f"开始启动应用: {app_name}")
        
        # 查询应用配置
        app_info = self.config.get_app_info(app_name)
        
        # 尝试使用配置信息直接启动
        if app_info:
            package = app_info.get("package")
            component = app_info.get("component")
            
            logging.info(f"找到应用配置 - 包名: {package}, 组件: {component}")
            
            # 优先使用组件名启动
            if component:
                if self.device.launch_app_by_component(component):
                    logging.info(f"使用组件名成功启动应用: {app_name}")
                    return self._verify_app_launched(app_name, tool_name, tool_registry)
            
            # 如果组件名启动失败，尝试使用包名启动
            if package:
                if self.device.launch_app_by_package(package):
                    logging.info(f"使用包名成功启动应用: {app_name}")
                    return self._verify_app_launched(app_name, tool_name, tool_registry)
        
        logging.info(f"无有效配置或配置启动失败，使用视觉方式启动: {app_name}")
        
        # 如果配置启动失败，使用现有的视觉方式启动
        if self._visual_launch_app(app_name, tool_name, tool_registry):
            # 启动成功，获取并保存应用信息
            current_app = self.device._get_current_activity()
            if current_app:
                package, activity = current_app.split('/')
                component = current_app
                
                # 保存到配置
                self.config.save_app_info(app_name, package, component)
                logging.info(f"已保存新的应用配置: {app_name} -> {component}")
            
            return True
        
        return False
    
    def _visual_launch_app(self, app_name, tool_name=None, tool_registry=None):
        """使用视觉方式启动应用（原有的启动方法）
        
        Args:
            app_name: 要启动的应用名称
            tool_name: 可选，工具名称（用于自定义启动检查）
            tool_registry: 可选，工具注册中心实例
            
        Returns:
            bool: 是否成功启动应用
        """
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
            
            return self._verify_app_launched(app_name, tool_name, tool_registry)
        else:
            logging.error(f"无法找到应用: {app_name}")
            return False
    
    def _verify_app_launched(self, app_name, tool_name=None, tool_registry=None):
        """验证应用是否成功启动
        
        Args:
            app_name: 应用名称
            tool_name: 工具名称
            tool_registry: 工具注册中心实例
            
        Returns:
            bool: 是否成功启动
        """
        start_time = time.time()
        while time.time() - start_time < self.app_launch_timeout:
            try:
                # 检查是否有自定义启动验证方法
                # if tool_name and tool_registry:
                #     tool_class = tool_registry.get_tool(tool_name)
                #     if hasattr(tool_class, 'check_app_launched'):
                #         if tool_class.check_app_launched(self):
                #             logging.info(f"应用 {app_name} 启动成功（自定义检查）")
                #             return True
                
                # 使用多模态模型进行应用识别
                screenshot = self.device.capture_screenshot()
                is_app_launched = self.check_app_identity(app_name, screenshot)
                if is_app_launched:
                    print(f"应用 {app_name} 启动成功（多模态识别）")
                    logging.info(f"应用 {app_name} 启动成功（多模态识别）")
                    return True
                
                time.sleep(1)
                
            except Exception as e:
                logging.error(f"启动检查时出错: {str(e)}")
        
        logging.warning(f"应用 {app_name} 启动超时")
        return False
    
    def set_launch_timeout(self, timeout_seconds):
        """设置应用启动超时时间
        
        Args:
            timeout_seconds: 超时时间(秒)
        """
        self.app_launch_timeout = timeout_seconds

    def check_app_identity(self, app_name, screenshot):
        """检查屏幕是否为特定应用

        Args:
            app_name: 应用名称
            screenshot: 屏幕截图

        Returns:
            bool: 是否是目标应用
        """
        try:
            # 使用应用识别模板
            format_args = {"app_name": app_name}
            prompt = f"请分析这个屏幕截图，判断它是否是{app_name}应用。"
            print("-------------------------")

            response = self.brain.query_model(
                template_name="app_identification",
                prompt=prompt,
                images=screenshot,
                format_args=format_args,
                temperature=0.1  # 低温度以获得确定性结果
            )
            print("-------------------------1111")

            print(f"回复{response}")

            # 提取结果
            if "####" in response:
                # 如果响应包含分隔符，提取最终答案
                final_answer = response.split("####")[-1].strip()
            else:
                final_answer = response.strip()

            # 判断是否识别为目标应用
            is_target_app = "是" in final_answer

            logging.info(f"应用识别结果: {app_name} - {is_target_app}")
            return is_target_app

        except Exception as e:
            logging.error(f"应用识别失败: {str(e)}")
            return False
