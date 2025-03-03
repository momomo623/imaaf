# tools/base_tool.py
from typing import Optional, ClassVar

class BaseTool:
    """所有工具插件的基类"""
    
    # 将required_app定义为类属性
    required_app: ClassVar[Optional[str]] = None
    
    def __init__(self, agent):
        """初始化工具
        Args:
            agent: 代理实例，提供核心功能访问
        """
        self.agent = agent
        self.name = self.__class__.__name__
        self.description = self.__doc__ or "无描述"
        self.version = "1.0.0"
    
    def get_info(self):
        """获取工具信息"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "required_app": self.__class__.required_app  # 使用类属性
        }
    
    def setup(self):
        """设置工具，可在子类中重写"""
        return True
    
    def cleanup(self):
        """清理工具，可在子类中重写"""
        return True
    
    def run(self, params=None):
        """运行工具，必须由子类实现"""
        raise NotImplementedError("工具必须实现run方法")

    @classmethod
    def get_tool_info(cls):
        """获取工具元信息"""
        return {
            "required_app": cls.required_app,
            # ...其他元信息...
        }

    @classmethod
    def validate(cls):
        """验证工具类配置"""
        if cls.required_app is not None and not isinstance(cls.required_app, str):
            raise TypeError(f"{cls.__name__}.required_app 必须是字符串类型")