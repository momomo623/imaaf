# core/device/adb_controller.py
import subprocess
import os
import time
import random
import cv2
import numpy as np

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
    
    def __init__(self, device_id=None, emulator_path=None):
        """初始化ADB控制器"""
        self.device_id = device_id
        self.emulator_path = emulator_path
        self.adb_path = f"{emulator_path}/Contents/MacOS/MuMuEmulator.app/Contents/MacOS/tools/adb" if emulator_path else "adb"
        self._init_connection()
    
    def _init_connection(self):
        """初始化设备连接"""
        # 检查ADB路径
        if self.emulator_path and not os.path.exists(self.adb_path):
            raise Exception(f"未找到ADB工具: {self.adb_path}")
            
        # 如果未指定设备ID，尝试自动检测
        if not self.device_id:
            result = self._adb_command("devices")
            lines = result.stdout.strip().split('\n')[1:]
            if lines and '\t' in lines[0]:
                self.device_id = lines[0].split('\t')[0]
                print(f"自动选择设备: {self.device_id}")
            else:
                # 尝试连接模拟器默认端口
                self.device_id = "127.0.0.1:16384"
                self._adb_command(f"connect {self.device_id}")
    
    def _adb_command(self, cmd):
        """执行ADB命令"""
        try:
            # 构建完整命令
            full_cmd = f"{self.adb_path} {cmd}"
            
            # 对于需要指定设备的命令，添加设备ID
            if self.device_id and not cmd.startswith(('connect', 'disconnect', 'start-server', 'devices')):
                full_cmd = f"{self.adb_path} -s {self.device_id} {cmd}"
            
            # 执行命令
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            
            # 检查是否有错误输出
            if result.returncode != 0 and result.stderr:
                print(f"ADB命令警告: {result.stderr}")
                
            return result
            
        except subprocess.CalledProcessError as e:
            print(f"ADB命令执行失败: {str(e)}")
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
        """输入文字"""
        # 将文本中的空格替换为%s
        text = text.replace(" ", "%s")
        self._adb_command(f"shell input text '{text}'")