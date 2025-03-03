# core/cognition/ai_brain.py
import os
import json
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
import httpx

class AIBrain:
    """AI决策引擎，基于大语言模型"""
    
    def __init__(self, model="gpt-4o-mini", api_key=None, base_url="https://api.openai-proxy.org/v1"):
        """初始化AI决策引擎"""
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or "sk-aVnMX4wIWhH0KQS2iaFKULUFJ8Zh1ZAxn2QEb8Op60FjCz0b"
        self.model = model
        self.base_url = base_url
        self._init_llm_client()
        
        # 用于重试逻辑
        self.max_retries = 3
        self.base_wait_time = 2  # seconds

    def _init_llm_client(self):
        """初始化大语言模型客户端"""
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=httpx.Client(
                timeout=60.0,
                follow_redirects=True
            )
        )

    def _make_request(self, messages, temperature=0.7, max_tokens=None):
        """向OpenAI API发送请求"""
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens if max_tokens else None
                )
                
                return response.choices[0].message.content
                
            except Exception as e:
                print(f"请求失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self.base_wait_time * (2 ** attempt)
                    print(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"所有API请求尝试均失败: {str(e)}")
    
    def make_decision(self, context, objective, history=None):
        """根据当前上下文和目标做出决策
        
        Args:
            context: 当前上下文，包含屏幕信息等
            objective: 任务目标
            history: 历史操作记录
            
        Returns:
            dict: 决策结果，包含下一步操作
        """
        # 构建提示信息
        system_message = {
            "role": "system",
            "content": """你是一个移动设备自动化助手，可以帮助用户完成移动应用中的各种任务。
            你需要根据屏幕内容和任务目标，决定执行什么操作。
            返回的操作应该是JSON格式，包括action_type和相关参数。
            
            注意：对于可能不包含文字的UI元素（如图标、按钮等），你可以使用视觉语义搜索功能。
            设置 "use_visual_search": true 将启用多模态搜索，可以找到与描述语义相关的视觉区域。"""
        }
        
        # 添加历史操作记录的文本表示
        history_text = ""
        if history:
            history_text = "历史操作记录:\n"
            for i, action in enumerate(history[-5:], 1):  # 只保留最近5步
                history_text += f"{i}. {action['action_type']}: {json.dumps(action, ensure_ascii=False)}\n"
        
        # 构建当前屏幕的文本表示
        screen_text = "当前屏幕文本元素:\n"
        for i, elem in enumerate(context.get("text_elements", []), 1):
            screen_text += f"{i}. '{elem['text']}' (位置: {elem['center']})\n"
        
        user_message = {
            "role": "user",
            "content": f"""
            目标任务: {objective}
            
            {screen_text}
            
            {history_text}
            
            请决定下一步操作，可选的操作类型有:
            1. click - 点击指定的文本或坐标
            • 对于没有文字或难以识别的元素，可添加 "use_visual_search": true
            2. swipe - 向指定方向滑动
            3. input - 输入文本
            4. back - 返回上一页
            5. home - 返回主页
            
            以JSON格式返回你的决策，例如:
            ``json
            {{
                "action_type": "click",
                "target": "登录",
                "reasoning": "点击登录按钮以进入账号"
            }}
``
            或使用视觉搜索:
            ``json
            {{
                "action_type": "click",
                "target": "购物车图标",
                "use_visual_search": true,
                "reasoning": "尝试通过视觉搜索找到购物车图标并点击"
            }}
            ``
            """
        }
        
        messages = [system_message, user_message]
        
        # 发送请求并解析响应
        response_content = self._make_request(messages, temperature=0.2)
        
        # 提取决策内容
        # response_content = response["choices"][0]["message"]["content"]
        
        # 尝试从响应中提取JSON
        try:
            # 从可能的markdown代码块中提取JSON
            if "```json" in response_content:
                json_str = response_content.split("```json")[1].split("```")[0].strip()
            elif "```" in response_content:
                json_str = response_content.split("```")[1].strip()
            else:
                json_str = response_content.strip()
                
            decision = json.loads(json_str)
            return decision
            
        except Exception as e:
            print(f"解析决策失败: {str(e)}")
            print(f"原始响应: {response_content}")
            
            # 返回一个默认的决策
            return {
                "action_type": "error",
                "error": "无法解析决策",
                "original_response": response_content
            }
    
    def analyze_screen(self, screen_data):
        """分析屏幕内容，提取关键信息
        
        Args:
            screen_data: 包含屏幕截图和文本元素的数据
            
        Returns:
            dict: 分析结果
        """
        # 构建提示信息
        system_message = {
            "role": "system",
            "content": """你是一个屏幕内容分析专家。你的任务是分析移动应用屏幕上的内容，
            识别关键元素，并提供结构化的分析结果。请关注页面类型、主要内容区域和可交互元素。"""
        }
        
        # 构建屏幕文本描述
        screen_text = "屏幕文本元素:\n"
        for i, elem in enumerate(screen_data.get("text_elements", []), 1):
            screen_text += f"{i}. '{elem['text']}' (位置: {elem['center']})\n"
        
        user_message = {
            "role": "user",
            "content": f"""
            请分析以下屏幕内容:
            
            {screen_text}
            
            请提供以下分析:
            1. 页面类型（如登录页、商品列表、详情页等）
            2. 主要内容区域
            3. 可交互元素（按钮、链接等）
            4. 其他重要信息
            
            以JSON格式返回分析结果。
            """
        }
        
        messages = [system_message, user_message]
        
        # 发送请求并解析响应
        response_content = self._make_request(messages, temperature=0.2)
        
        # 提取分析结果
        # response_content = response["choices"][0]["message"]["content"]
        
        # 尝试从响应中提取JSON
        try:
            if "```json" in response_content:
                json_str = response_content.split("```json")[1].split("```")[0].strip()
            elif "```" in response_content:
                json_str = response_content.split("```")[1].strip()
            else:
                json_str = response_content.strip()
                
            analysis = json.loads(json_str)
            return analysis
            
        except Exception as e:
            print(f"解析分析结果失败: {str(e)}")
            
            # 返回一个简单的分析结果
            return {
                "page_type": "unknown",
                "elements": [e["text"] for e in screen_data.get("text_elements", [])]
            }
    
    def verify_completion(self, objective, current_state, history):
        """验证任务是否完成
        
        Args:
            objective: 任务目标
            current_state: 当前状态
            history: 历史操作
            
        Returns:
            bool: 任务是否完成
        """
        # 构建提示信息
        system_message = {
            "role": "system",
            "content": """你的任务是判断当前任务是否已经完成。请基于任务目标、当前屏幕内容和历史操作做出判断。
            只回答"已完成"或"未完成"。"""
        }
        
        # 构建当前屏幕的文本表示
        screen_text = "当前屏幕文本元素:\n"
        for i, elem in enumerate(current_state.get("text_elements", []), 1):
            screen_text += f"{i}. '{elem['text']}'\n"
        
        # 构建历史操作的文本表示
        history_text = "历史操作:\n"
        for i, action in enumerate(history[-5:], 1):
            history_text += f"{i}. {action['action_type']}\n"
        
        user_message = {
            "role": "user",
            "content": f"""
            目标任务: {objective}
            
            {screen_text}
            
            {history_text}
            
            请判断任务是否已经完成？仅回答 "已完成" 或 "未完成"。
            """
        }        
        messages = [system_message, user_message]
        
        # 发送请求并解析响应
        completion_check = self._make_request(messages, temperature=0.1)
        # completion_check = response["choices"][0]["message"]["content"].strip()
        
        return "已完成" in completion_check
