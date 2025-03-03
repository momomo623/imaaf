# main.py

import os
import sys
import argparse
import json
import logging
logging.basicConfig(level=logging.DEBUG)

# 确保可以正确导入项目模块
# current_dir = os.path.dirname(os.path.abspath(__file__))
# if current_dir not in sys.path:
#     sys.path.insert(0, current_dir)

from engine.agent import Agent
from engine.task_manager import TaskManager
# ToolRegistry
from utools.tool_registry import ToolRegistry
from utools.ecommerce.hema_crawler import HemaCrawler

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="智能移动应用自动化框架")
    parser.add_argument('--tool', type=str, help='要运行的工具名称')
    parser.add_argument('--list-tools', action='store_true', help='列出所有可用工具')
    parser.add_argument('--emulator', type=str, default="/Applications/MuMuPlayer.app", help='模拟器路径')
    parser.add_argument('--device-id', type=str, help='设备ID')
    parser.add_argument('--params', type=str, help='工具参数，JSON格式')
    parser.add_argument('--batch', type=str, help='批量任务文件路径')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细日志')
    return parser.parse_args()

def main():
    """主程序入口"""
    # 解析命令行参数
    print("开始解析命令行参数")
    args = parse_args()
    print(args)
    print("命令行参数解析完成")

    
    # 配置日志
    # import logging
    # log_level = logging.DEBUG if args.verbose else logging.INFO
    # logging.basicConfig(
    #     level=log_level,
    #     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    # )
    
    # 打印系统信息
    if args.verbose:
        import platform
        logging.info(f"Python版本: {sys.version}")
        logging.info(f"平台信息: {platform.platform()}")
        logging.info(f"处理器架构: {platform.machine()}")
        logging.info(f"当前工作目录: {os.getcwd()}")
    
    # 初始化工具注册中心
    registry = ToolRegistry()
    print("注册工具前的工具列表:", registry.tools)
    registry.register_tool(HemaCrawler)
    print("注册工具后的工具列表:", registry.tools)
    
    # 显示工具列表
    if args.list_tools:
        print("可用工具列表:")
        for i, tool in enumerate(registry.list_tools()):
            print(f"{i+1}. {tool['name']}: {tool['description']}")
        return 0
    
    # 初始化代理和任务管理器
    agent = Agent(device_id=args.device_id, emulator_path=args.emulator)
    task_manager = TaskManager(agent)
    
    # 批量执行任务
    if args.batch:
        try:
            with open(args.batch, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
            
            print(f"开始执行批量任务，共 {len(tasks)} 个任务")
            results = task_manager.schedule_tasks(tasks)
            
            # 保存结果
            task_manager.save_task_results(results)
            
            # 统计成功/失败数量
            success_count = sum(1 for r in results if r.get("success", False))
            print(f"批量任务完成: {success_count}/{len(results)} 成功")
            
            return 0 if success_count == len(results) else 1
            
        except Exception as e:
            print(f"批量任务执行失败: {str(e)}")
            return 1
    
    # 运行单个工具
    if args.tool:
        try:
            # 解析参数
            params = {}
            if args.params:
                params = json.loads(args.params)
            
            # 创建任务配置
            task_config = {
                "tool": args.tool,
                "params": params
            }
            
            # 通过任务管理器执行任务
            result = task_manager.execute_task(task_config)
            print(f"任务执行结果: {result}")
            
            return 0 if result.get("success", False) else 1
            
        except Exception as e:
            print(f"错误: {str(e)}")
            return 1
    
    # 如果没有指定工具，显示交互式菜单
    tools = registry.list_tools()
    print("请选择要运行的工具:")
    for i, tool in enumerate(tools):
        print(f"{i+1}. {tool['name']}: {tool['description']}")
    
    choice = input("请输入工具编号: ")
    try:
        index = int(choice) - 1
        if 0 <= index < len(tools):
            tool_name = tools[index]["name"]
            print(f"选择了工具: {tool_name}")
            
            # 通过任务管理器执行任务
            result = task_manager.execute_task({"tool": tool_name})
            print(f"任务执行结果: {result}")
            
            return 0 if result.get("success", False) else 1
        else:
            print("无效的选择")
    except:
        print("请输入有效的数字")
    
    return 0

if __name__ == "__main__":
    exit(main())