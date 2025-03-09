# core/device/adb_controller.py
import subprocess
import os
import time
import random
import cv2
import numpy as np
import logging

class DeviceController:
    """设备控制基类，定义通用接口"""
    
    def tap(self, x, y, random_offset=10):
        """点击指定坐标"""
        raise NotImplementedError
    
    def swipe(self, start_x, start_y, end_x, end_y, duration=300):
        """滑动操作"""
        raise NotImplementedError
    
    def capture_screenshot(self):
        """截取屏幕"""
        raise NotImplementedError
    
    def input_text(self, text):
        """输入文本"""
        raise NotImplementedError
    
    def press_back(self):
        """按返回键"""
        raise NotImplementedError
    
    def press_home(self):
        """按Home键"""
        raise NotImplementedError


class ADBController(DeviceController):
    """基于ADB的设备控制实现"""
    
    def __init__(self, device_id=None, emulator_path=None, wifi_device=None):
        """初始化ADB控制器
        
        Args:
            device_id: 设备ID，如"emulator-5554"或"192.168.1.100:5555"
            emulator_path: 模拟器路径，用于定位adb工具
            wifi_device: WiFi设备信息，格式为"IP:PORT"，如"192.168.1.100:5555"
        """
        self.device_id = device_id
        self.emulator_path = emulator_path
        self.wifi_device = wifi_device
        
        # 确定ADB路径
        if emulator_path and os.path.exists(f"{emulator_path}/Contents/MacOS/MuMuEmulator.app/Contents/MacOS/tools/adb"):
            self.adb_path = f"{emulator_path}/Contents/MacOS/MuMuEmulator.app/Contents/MacOS/tools/adb"
        else:
            # 尝试使用系统ADB
            self.adb_path = "adb"
            
        # 初始化设备连接
        self._init_connection()
    
    def _init_connection(self):
        """初始化设备连接"""
        # 检查ADB是否可用
        try:
            version_result = self._adb_command("version", include_device_id=False)
            logging.debug(f"ADB版本信息: {version_result.stdout}")
        except Exception as e:
            logging.error(f"ADB初始化失败: {str(e)}")
            raise Exception(f"ADB工具不可用: {str(e)}")
        
        # 如果指定了WiFi设备，尝试连接
        if self.wifi_device:
            if self.connect_wifi_device(self.wifi_device):
                self.device_id = self.wifi_device
                return
            else:
                logging.warning(f"WiFi设备连接失败: {self.wifi_device}，将尝试USB连接")
        
        # 检查已连接的USB设备
        usb_devices = self.get_usb_devices()
        if usb_devices:
            if not self.device_id or self.device_id not in usb_devices:
                # 如果没有指定设备ID或指定的设备ID不在USB设备列表中，使用第一个USB设备
                self.device_id = usb_devices[0]
                logging.info(f"使用USB连接设备: {self.device_id}")
            return
        
        # 如果没有USB设备，尝试连接模拟器
        if not self.device_id:
            default_device = "127.0.0.1:16384"
            self._adb_command(f"connect {default_device}", include_device_id=False)
            self.device_id = default_device
            logging.info(f"尝试连接默认模拟器: {default_device}")
    
    def connect_wifi_device(self, device_ip_port, max_retries=3):
        """连接WiFi设备，带重试和增强错误处理"""
        
        for attempt in range(max_retries):
            try:
                # 尝试断开现有连接
                self._adb_command(f"disconnect {device_ip_port}", include_device_id=False)
                
                # 连接到设备
                result = self._adb_command(f"connect {device_ip_port}", include_device_id=False)
                success = "connected to" in result.stdout.lower()
                
                if success:
                    logging.info(f"WiFi设备连接成功: {device_ip_port}")
                    return True
                else:
                    logging.warning(f"连接尝试 {attempt+1}/{max_retries} 失败: {result.stdout}")
                    
                    # 如果连接被拒绝，建议用户检查设置
                    if "connection refused" in result.stdout.lower():
                        logging.error("连接被拒绝，请确保设备已启用无线调试并已设置TCP/IP端口")
                        if attempt == 0:  # 只在第一次尝试时显示提示
                            print("\n请检查以下事项:")
                            print("1. 设备与电脑连接到同一WiFi网络")
                            print("2. 已通过USB连接并执行 'adb tcpip 5555'")
                            print("3. 开发者选项中已启用无线调试")
                            print("4. 对于Android 11+，使用配对码方式连接\n")
                
                    # 短暂等待后重试
                    time.sleep(2)
                
            except Exception as e:
                logging.error(f"连接WiFi设备出错: {str(e)}")
                if attempt == max_retries - 1:
                    return False
        
        return False
    
    def _adb_command(self, cmd, include_device_id=True):
        """执行ADB命令
        
        Args:
            cmd: ADB命令
            include_device_id: 是否包含设备ID
        """
        try:
            # 构建完整命令
            full_cmd = f"{self.adb_path} {cmd}"
            
            # 对于需要指定设备的命令，添加设备ID
            if include_device_id and self.device_id and not cmd.startswith(('connect', 'disconnect', 'start-server', 'devices')):
                full_cmd = f"{self.adb_path} -s {self.device_id} {cmd}"
            
            # 执行命令
            logging.debug(f"执行ADB命令: {full_cmd}")
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            
            # 检查是否有错误输出
            if result.returncode != 0 and result.stderr:
                logging.warning(f"ADB命令警告: {result.stderr}")
                
            return result
            
        except subprocess.CalledProcessError as e:
            logging.error(f"ADB命令执行失败: {str(e)}")
            raise
    
    def tap(self, x, y, random_offset=10):
        """点击指定坐标，可添加随机偏移"""
        x_offset = random.randint(-random_offset, random_offset)
        y_offset = random.randint(-random_offset, random_offset)
        final_x, final_y = x + x_offset, y + y_offset
        self._adb_command(f"shell input tap {final_x} {final_y}")
        return final_x, final_y
    
    def swipe(self, start_x, start_y, end_x, end_y, duration=300):
        """滑动操作"""
        self._adb_command(
            f"shell input swipe {start_x} {start_y} {end_x} {end_y} {duration}"
        )

    def adaptive_swipe(self, direction="up", distance_factor=0.5):
        """改进后的自适应滑动"""
        width, height = self.get_screen_size()
        mid_x = width // 2
        mid_y = height // 2
        
        # 计算滑动参数
        base_ratio = 0.5  # 基础滑动比例
        actual_ratio = base_ratio * distance_factor
        
        if direction == "up":
            start_x, start_y = mid_x, int(height * 0.8)
            end_x, end_y = mid_x, int(start_y - (height * actual_ratio))
        elif direction == "down":
            start_x, start_y = mid_x, int(height * 0.2)
            end_x, end_y = mid_x, int(start_y + (height * actual_ratio))
        elif direction == "left":
            start_x, start_y = int(width * 0.8), mid_y
            end_x, end_y = int(start_x - (width * actual_ratio)), mid_y
        elif direction == "right":
            start_x, start_y = int(width * 0.2), mid_y
            end_x, end_y = int(start_x + (width * actual_ratio)), mid_y
        
        print(f"滑动参数: ({start_x},{start_y}) -> ({end_x},{end_y})")  # 调试输出
        self.swipe(start_x, start_y, end_x, end_y, duration=300)
    
    def capture_screenshot(self, filename=None):
        """捕获屏幕截图"""
        temp_file = filename or f"temp_screen_{int(time.time())}.png"
        self._adb_command(f"exec-out screencap -p > {temp_file}")
        img = cv2.imread(temp_file)
        if not filename:  # 如果是临时文件，则删除
            os.remove(temp_file)
        return img
    
    def get_screen_size(self):
        """获取屏幕尺寸"""
        output = self._adb_command("shell wm size").stdout
        print(f"原始屏幕尺寸输出: {output}")  # 添加调试输出
        
        if "Physical size" in output:
            size_str = output.split("Physical size:")[1].strip()
            width, height = map(int, size_str.split("x"))
            print(f"解析后的屏幕尺寸: {width}x{height}")  # 添加调试输出
            return width, height
        return (1080, 2340)  # 添加默认值
    
    def press_back(self):
        """按返回键"""
        self._adb_command("shell input keyevent 4")
    
    def press_home(self):
        """按Home键"""
        self._adb_command("shell input keyevent 3")

    def input_text(self, text):
        """改进的文本输入，增强输入可靠性
        
        Args:
            text: 要输入的文本
        """
        try:
            # 方法1: 标准输入方式
            text = text.replace(" ", "%s")
            result = self._adb_command(f"shell input text '{text}'")
            
            # 如果有错误，尝试备选方法
            if "Exception" in result.stderr or "error" in result.stderr.lower():
                logging.warning(f"标准输入方式失败，尝试备选方法: {result.stderr}")
                
                # 方法2: 一个字符一个字符地输入
                for char in text:
                    if char == " ":
                        self._adb_command("shell input keyevent 62")  # 空格键
                    else:
                        self._adb_command(f"shell input text '{char}'")
                        time.sleep(0.1)  # 在字符之间添加小延迟
        
        except Exception as e:
            logging.error(f"文本输入失败: {str(e)}")
            
            # 方法3: 最后尝试使用keyevent输入
            try:
                logging.info("尝试使用keyevent方式输入")
                for char in text:
                    # 这里只处理字母、数字和空格，其他特殊字符需要额外映射
                    if char == " ":
                        self._adb_command("shell input keyevent 62")  # 空格键
                    elif char.isalpha():
                        # 将字母转换为相应的keyevent
                        keycode = 29 + ord(char.lower()) - ord('a')
                        self._adb_command(f"shell input keyevent {keycode}")
                    elif char.isdigit():
                        # 将数字转换为相应的keyevent
                        keycode = 7 + ord(char) - ord('0')
                        self._adb_command(f"shell input keyevent {keycode}")
                    time.sleep(0.2)  # 按键之间的延迟更长
            except Exception as e2:
                logging.error(f"所有输入方法都失败: {str(e2)}")

    def get_usb_devices(self):
        """获取已连接的USB设备列表"""
        result = self._adb_command("devices", include_device_id=False)
        usb_devices = []
        
        for line in result.stdout.strip().split('\n')[1:]:
            if '\t' in line:
                device_id, status = line.split('\t')
                # 只包含直接连接的设备（非IP地址格式）
                if ':' not in device_id and status == 'device':
                    usb_devices.append(device_id)
        
        logging.info(f"发现 {len(usb_devices)} 个USB设备: {usb_devices}")
        return usb_devices

    def check_connection(self):
        """检查当前连接状态"""
        try:
            result = self._adb_command("get-state")
            is_connected = result.stdout.strip() == "device"
            
            if is_connected:
                # 检查连接类型
                if ':' in self.device_id:
                    conn_type = "无线连接"
                else:
                    conn_type = "USB连接"
                
                logging.info(f"设备连接正常 ({conn_type}): {self.device_id}")
                return True
                
        except Exception as e:
            logging.error(f"设备连接检查失败: {str(e)}")
        
        return False

    def _get_current_activity(self):
        """获取当前活动的应用包名和Activity名称
        
        Returns:
            str: 格式为"package/activity"的字符串，如果获取失败则返回None
        """
        import re
        try:
            # 获取 adb 命令的结果
            result = self._adb_command("shell dumpsys window | grep mCurrentFocus")
            
            # 确保提取 stdout 作为字符串
            result_str = result.stdout if isinstance(result, subprocess.CompletedProcess) else str(result)
            
            # 使用正则表达式直接提取package/activity部分
            pattern = r'mCurrentFocus=.*\s+([\w.]+)/([\w.]+)'
            match = re.search(pattern, result_str)
            
            if match:
                package_name = match.group(1)
                activity_name = match.group(2)
                full_component = f"{package_name}/{activity_name}"
                logging.info(f"当前应用：{full_component}")
                return full_component
            else:
                # 尝试另一种格式的输出
                alternative_pattern = r'mFocusedApp=.*\s+([\w.]+)/([\w.]+)'
                alt_match = re.search(alternative_pattern, result_str)
                if alt_match:
                    package_name = alt_match.group(1)
                    activity_name = alt_match.group(2)
                    full_component = f"{package_name}/{activity_name}"
                    logging.info(f"当前应用：{full_component}")
                    return full_component
                
                logging.warning(f"无法解析当前Activity，输出: {result_str}")
                return None
        except Exception as e:
            logging.error(f"获取当前Activity失败: {str(e)}")
            return None

    def launch_app_by_component(self, component_name, wait_time=3):
        """通过组件名称启动应用

        Args:
            component_name: 应用组件名称，格式为"package/activity"
            wait_time: 启动后等待时间(秒)

        Returns:
            bool: 是否成功启动
        """
        try:
            # 使用am start命令启动特定activity
            cmd = f"shell am start -n {component_name}"
            logging.info(f"启动应用: {component_name}")

            result = self._adb_command(cmd)

            # 检查启动结果
            if "Error" in result.stdout or "Exception" in result.stdout:
                logging.error(f"应用启动失败: {result.stdout}")
                return False

            # 等待应用启动
            time.sleep(wait_time)

            # 验证应用是否成功启动
            current_app = self._get_current_activity()
            if current_app and current_app.split('/')[0] in component_name:
                logging.info(f"应用启动成功: {component_name}")
                return True
            else:
                logging.warning(f"应用可能未成功启动，当前应用: {current_app}")
                return False

        except Exception as e:
            logging.error(f"启动应用异常: {str(e)}")
            return False

    def launch_app_by_package(self, package_name, wait_time=3):
        """只通过包名启动应用（使用默认Activity）
        
        Args:
            package_name: 应用包名，如"com.tencent.mm"
            wait_time: 启动后等待时间(秒)
        
        Returns:
            bool: 是否成功启动
        """
        try:
            # 使用monkey命令启动应用的默认Activity
            cmd = f"shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
            logging.info(f"启动应用: {package_name}（默认Activity）")
            
            result = self._adb_command(cmd)
            
            # 等待应用启动
            time.sleep(wait_time)
            
            # 验证应用是否成功启动
            current_app = self._get_current_activity()
            if current_app and package_name in current_app:
                logging.info(f"应用启动成功: {package_name}")
                return True
            else:
                logging.warning(f"应用可能未成功启动，当前应用: {current_app}")
                return False
            
        except Exception as e:
            logging.error(f"启动应用异常: {str(e)}")
            return False
