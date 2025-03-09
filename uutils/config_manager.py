import json
import os
import logging
from pathlib import Path

class ConfigManager:
    """配置文件管理工具"""
    
    def __init__(self, config_dir="config"):
        """初始化配置管理器
        
        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = config_dir
        os.makedirs(config_dir, exist_ok=True)
        
        # 应用包信息文件路径
        self.app_packages_file = os.path.join(config_dir, "app_packages.json")
        
        # 初始化应用包信息
        self._init_app_packages()
    
    def _init_app_packages(self):
        """初始化应用包信息文件"""
        if not os.path.exists(self.app_packages_file):
            # 创建默认配置
            default_config = {
                "apps": {
                    "盒马": {
                        "package": "com.whaleshark.meteora",
                        "component": "com.whaleshark.meteora/.MainActivity"
                    },
                    "微信": {
                        "package": "com.tencent.mm",
                        "component": "com.tencent.mm/.ui.LauncherUI"
                    }
                }
            }
            
            with open(self.app_packages_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            
            logging.info(f"已创建默认应用包信息配置: {self.app_packages_file}")
    
    def get_app_info(self, app_name):
        """获取应用包信息
        
        Args:
            app_name: 应用名称
            
        Returns:
            dict: 应用包信息，如果不存在则返回None
        """
        try:
            with open(self.app_packages_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            return config.get("apps", {}).get(app_name)
        except Exception as e:
            logging.error(f"读取应用配置失败: {str(e)}")
            return None
    
    def save_app_info(self, app_name, package, component):
        """保存应用包信息
        
        Args:
            app_name: 应用名称
            package: 应用包名
            component: 应用组件名
            
        Returns:
            bool: 是否成功保存
        """
        try:
            # 读取现有配置
            if os.path.exists(self.app_packages_file):
                with open(self.app_packages_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {"apps": {}}
            
            # 更新应用信息
            if "apps" not in config:
                config["apps"] = {}
                
            config["apps"][app_name] = {
                "package": package,
                "component": component
            }
            
            # 保存配置
            with open(self.app_packages_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            logging.info(f"已保存应用 '{app_name}' 的包信息: {package}")
            return True
            
        except Exception as e:
            logging.error(f"保存应用配置失败: {str(e)}")
            return False 