# tools/tool_registry.py
class ToolRegistry:
    """工具注册中心"""
    
    _instance = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.tools = {}
        return cls._instance
    
    def register_tool(self, tool_class):
        """注册工具类"""
        tool_name = tool_class.__name__
        self.tools[tool_name] = tool_class
        print(f"工具已注册: {tool_name}")
    
    def get_tool(self, tool_name):
        """获取指定名称的工具类"""
        if tool_name not in self.tools:
            raise ValueError(f"未找到工具: {tool_name}")
        return self.tools[tool_name]
    
    def list_tools(self):
        """列出所有已注册工具"""
        return [
            {"name": name, "description": cls.__doc__ or "无描述"}
            for name, cls in self.tools.items()
        ]