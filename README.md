# 智能移动应用自动化框架 (IMAAF)

IMAAF是一个高度可扩展的移动应用自动化框架，利用Agent技术，它将设备控制、视觉感知和AI决策等核心能力与特定应用场景分离，采用插件化架构使系统能够不断成长。

> 本项目仍在开发中，目前正在开发的功能为：智能收集买菜类APP的商品信息。如打开盒马/小象超市，收集所有的商品名称、价格等信息。

## 主要特点

- **模块化设计**：核心功能与具体应用场景分离
- **插件化架构**：支持添加新工具而不修改核心代码
- **AI驱动**：使用大语言模型和计算机视觉技术进行决策
- **多平台支持**：支持各种Android设备和模拟器
- **批量任务执行**：支持按顺序执行多个任务

## 快速开始

### 安装依赖

```
pip install -r requirements.txt
```

### 运行工具

```
# 列出所有可用工具
python main.py --list-tools

# 运行特定工具
python main.py --tool HemaCrawler --params '{"category": "海鲜水产", "max_pages": 5}'

# 批量执行任务
python main.py --batch tasks.json
```

## 系统架构

IMAAF由以下主要组件构成：

1. **核心框架层**：提供基础功能
   - 设备控制层：与移动设备交互
   - 视觉感知层：识别屏幕内容
   - 认知决策层：决定下一步操作
   - 记忆管理层：管理状态和历史

2. **引擎层**：连接核心功能和工具
   - 代理执行器：执行具体操作
   - 任务管理器：管理和调度任务

3. **工具插件层**：实现特定功能
   - 电商数据采集工具
   - 社交媒体工具
   - 自动化测试工具

## 任务管理器

任务管理器是IMAAF的核心组件之一，负责管理和执行任务。它提供以下功能：

1. **任务执行**：执行单个任务
2. **任务调度**：按顺序执行多个任务
3. **结果持久化**：将任务结果保存到文件
4. **错误处理**：统一处理任务执行过程中的异常
5. **内存优化**：定期清理大型数据，避免内存泄漏

### 批量任务格式

批量任务文件是一个JSON数组，每个元素代表一个任务：

```json
[
  {
    "tool": "HemaCrawler",
    "params": {
      "category": "海鲜水产",
      "max_pages": 5
    },
    "wait_after": 2,
    "stop_on_failure": true
  },
  {
    "tool": "JDMonitor",
    "params": {
      "keywords": ["手机", "电脑"],
      "max_items": 10
    }
  }
]
```

每个任务配置可以包含以下字段：
- `tool`：要运行的工具名称（必需）
- `params`：工具参数（可选）
- `wait_after`：任务完成后等待的时间（秒）（可选，默认2秒）
- `stop_on_failure`：任务失败时是否停止执行后续任务（可选，默认false）
- `max_steps`：最大执行步骤数（可选，默认15）
- `wait_time`：每步操作后等待的时间（秒）（可选，默认1.5秒）

## 工具开发

要创建新工具，请按照以下步骤操作：

1. 创建一个继承自 `BaseTool` 的新类
2. 实现必要的方法：
   - `__init__`: 设置工具基本信息
   - `setup`: 准备工作（可选）
   - `run`: 工具主逻辑（必须）
   - `cleanup`: 清理工作（可选）

### 工具模板

```python
# tools/your_category/your_new_tool.py
from utools.base_tool import BaseTool

class YourNewTool(BaseTool):
    """新工具的描述"""
    
    def __init__(self, agent):
        super().__init__(agent)
        self.name = "YourNewTool"
        self.description = "这是一个新工具的描述"
        self.version = "1.0.0"
    
    def setup(self):
        """设置工具（可选）"""
        pass
    
    def run(self, params=None):
        """运行工具（必须实现）
        
        Args:
            params (dict): 工具参数
            
        Returns:
            dict: 包含执行结果的字典
        """
        # 实现工具的主要逻辑
        return {
            "success": True,
            "message": "工具执行完成"
        }
    
    def cleanup(self):
        """清理工具（可选）"""
        pass
```

### 注册新工具

在 `main.py` 中导入并注册您的新工具：

```python
from utools.your_category.your_new_tool import YourNewTool

# 在工具注册部分添加：
registry.register_tool(YourNewTool)
```

## 示例应用场景

### 电商价格监控

使用框架可以定期采集电商平台的商品价格，监控价格变动，并在价格降低时发送通知。

```python
# 示例：使用命令行运行盒马价格监控
python main.py --tool HemaCrawler --params '{"category": "海鲜水产", "max_pages": 10}'
```

### 社交媒体数据分析

自动采集社交媒体平台的内容，分析热门话题和趋势。

```python
# 示例：使用命令行运行抖音数据采集
python main.py --tool DouyinCollector --params '{"keywords": ["美食", "旅游"], "max_videos": 50}'
```

### 自动化测试

对移动应用进行自动化UI测试，验证功能正常工作。

```python
# 示例：使用命令行运行UI测试
python main.py --tool UITester --params '{"app_package": "com.example.app", "test_cases": ["login", "browse"]}'
```

## 依赖项

```
# 基础依赖
opencv-python==4.8.0.74
numpy==1.24.3
Pillow==9.5.0

# AI模型相关
torch==2.0.1
openai==1.3.5
httpx==0.25.2
scikit-learn==1.3.0

# CLIP
git+https://github.com/openai/CLIP.git

# OCR
paddlepaddle==3.0.0b1
paddleocr==2.7.0.3
```

## 设备连接指南

### 有线连接（推荐）
```bash
# 1. 通过USB连接设备
# 2. 启用USB调试（设置 → 开发者选项）
# 3. 直接运行工具（自动检测设备）
python main.py --tool HemaCrawler
```

### 无线连接
```bash
# 1. 确保设备和电脑在同一WiFi网络
# 2. 在设备上启用无线调试
# 3. 连接设备
python main.py --wifi-device 192.168.1.7:5555 --tool HemaCrawler
```

### 连接状态检查
```bash
# 检查当前连接状态
python main.py --device-id [DEVICE_ID] --check-connection

# 输出示例
# 设备连接正常 (USB连接): emulator-5554
```

## 常见问题解答

### 连接问题排查
1. **Q: 无线连接提示"Connection refused"怎么办？**
   A: 请按顺序执行：
   - 通过USB执行 `adb tcpip 5555`
   - 断开USB线后重试连接
   - 检查防火墙设置

2. **Q: 如何保持无线连接稳定？**
   A: 
   - 在开发者选项中开启"始终保持WiFi连接"
   - 为设备分配静态IP
   - 避免设备进入深度睡眠模式

3. **Q: 同时连接多个设备如何操作？**
   A: 使用`--device-id`参数指定设备：
   ```bash
   python main.py --device-id 192.168.1.100:5555 --tool HemaCrawler
   python main.py --device-id emulator-5554 --tool HemaCrawler
   ```

## 贡献指南

我们欢迎社区贡献新的工具和功能。如果您想贡献代码，请遵循以下步骤：

1. Fork项目仓库
2. 创建功能分支
3. 提交您的更改
4. 确保代码符合项目风格指南
5. 提交Pull Request

所有贡献者都将被列在项目致谢名单中。
