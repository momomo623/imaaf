# core/cognition/ai_brain.py
import json
import logging
from typing import Dict, List, Any, Optional
from .llm_client import LLMClient
from .prompt_templates import PromptTemplates

class AIBrain:
    """AI决策引擎，基于大语言模型"""
    
    def __init__(self, model="gpt-4o-mini"):
        """初始化AI决策引擎"""
        self.llm = LLMClient(model=model)
        self.templates = PromptTemplates()


    
    def _make_request(self, messages, temperature=0.7):
        """发送请求到LLM并获取回复
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            
        Returns:
            str: 模型返回的内容
        """
        return self.llm.chat_completion(messages, temperature=temperature)
        
    def decide_next_action(self, current_state, history, objective):
        """决定下一步行动
        
        Args:
            current_state: 当前屏幕状态
            history: 历史操作
            objective: 任务目标
            
        Returns:
            dict: 下一步行动决策
        """
        # 使用决策制定模板
        system_message = self.templates.decision_making()
        
        # 构建当前屏幕的文本表示
        screen_text = "当前屏幕文本元素:\n"
        for i, elem in enumerate(current_state.get("text_elements", []), 1):
            screen_text += f"{i}. '{elem['text']}' ({elem['center'][0]},{elem['center'][1]})\n"
        
        # 构建历史操作的文本表示
        history_text = "最近操作历史:\n"
        for i, action in enumerate(history[-5:] if len(history) > 5 else history, 1):
            action_detail = f"类型:{action['action_type']}"
            if "target" in action:
                action_detail += f", 目标:{action['target']}"
            history_text += f"{i}. {action_detail}\n"
        
        user_message = {
            "role": "user",
            "content": f"""
            任务目标: {objective}
            
            {screen_text}
            
            {history_text}
            
            请决定下一步最合适的操作，以JSON格式返回，包含以下字段:
            - action_type: 操作类型(click/swipe/input/back/home)
            - target: 操作目标(文本/坐标/方向)
            - reason: 选择该操作的理由
            """
        }
        
        messages = [system_message, user_message]
        
        # 发送请求并解析响应
        response = self._make_request(messages)
        
        try:
            # 尝试解析JSON响应
            action = json.loads(response)
            return action
        except json.JSONDecodeError:
            # 如果响应不是有效的JSON，尝试从文本中提取
            logging.warning("LLM返回的不是有效JSON，尝试从文本中提取")
            try:
                import re
                json_pattern = r'\{.*\}'
                match = re.search(json_pattern, response, re.DOTALL)
                if match:
                    action = json.loads(match.group(0))
                    return action
            except:
                pass
            
            # 兜底返回一个默认操作
            return {
                "action_type": "back",
                "target": None,
                "reason": "无法解析AI响应，执行返回操作作为后备计划"
            }
    
    def analyze_screen(self, text_elements):
        """分析屏幕内容
        
        Args:
            text_elements: 屏幕上的文本元素列表
            
        Returns:
            dict: 分析结果
        """
        system_message = self.templates.screen_analysis()
        
        # 构建元素表示
        elements_text = "屏幕文本元素:\n"
        for i, elem in enumerate(text_elements, 1):
            elements_text += f"{i}. '{elem['text']}' 位置:({elem['center'][0]},{elem['center'][1]})\n"
        
        user_message = {
            "role": "user",
            "content": f"""
            {elements_text}
            
            请分析此屏幕，识别关键UI元素和可能的交互点。
            返回JSON格式的分析结果，包括:
            - screen_type: 屏幕类型(如登录页/商品列表/详情页等)
            - key_elements: 关键元素列表(按钮/输入框/标签等)
            - suggested_actions: 建议操作列表
            """
        }
        
        messages = [system_message, user_message]
        response = self._make_request(messages)
        
        try:
            return json.loads(response)
        except:
            logging.warning("无法解析屏幕分析结果")
            return {"error": "无法解析分析结果"}
    
    def is_task_completed(self, current_state, history, objective):
        """检查任务是否完成"""
        system_message = self.templates.task_completion_check()
        
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
        
        completion_check = self._make_request(messages, temperature=0.1)
        
        return "已完成" in completion_check

    def analyze_screen_with_vision(self, screenshot, text_elements):
        """使用多模态模型分析屏幕内容
        
        Args:
            screenshot: 屏幕截图
            text_elements: 屏幕上的文本元素列表
            
        Returns:
            dict: 分析结果
        """
        # 构建元素表示
        elements_text = "屏幕文本元素:\n"
        for i, elem in enumerate(text_elements, 1):
            elements_text += f"{i}. '{elem['text']}' 位置:({elem['center'][0]},{elem['center'][1]})\n"
        
        prompt = f"""
        请分析这个移动应用屏幕截图，识别关键UI元素和可能的交互点。
        以下是OCR已识别的文本元素:
        {elements_text}
        
        请综合图像和文字信息，返回JSON格式的分析结果，包括:
        - screen_type: 屏幕类型(如登录页/商品列表/详情页等)
        - key_elements: 关键元素列表(按钮/输入框/标签等)，包括位置描述
        - suggested_actions: 建议操作列表
        - additional_visual_elements: OCR可能未捕获的视觉元素(如图标/图片等)
        """
        
        try:
            response = self.llm.multimodal_chat_completion(prompt, screenshot)
            
            # 尝试解析JSON响应
            try:
                result = json.loads(response)
                return result
            except json.JSONDecodeError:
                # 如果响应不是有效的JSON，尝试从文本中提取
                logging.warning("多模态模型返回的不是有效JSON，尝试从文本中提取")
                try:
                    import re
                    json_pattern = r'\{.*\}'
                    match = re.search(json_pattern, response, re.DOTALL)
                    if match:
                        result = json.loads(match.group(0))
                        return result
                except:
                    pass
                
                return {"error": "无法解析分析结果", "raw_response": response}
        except Exception as e:
            logging.error(f"多模态分析失败: {str(e)}")
            return {"error": f"多模态分析失败: {str(e)}"}

    def query_model(self, template_name, prompt, images=None, format_args=None, temperature=0.7):
        """根据模板名称动态查询大模型
        
        Args:
            template_name: 提示词模板名称，对应PromptTemplates中的方法名
            prompt: 用户提示文本
            images: 可选，图片(单张或列表)
            format_args: 可选，用于格式化系统提示词的参数字典
            temperature: 温度参数
            
        Returns:
            str: 模型返回的内容
            
        Raises:
            ValueError: 如果提示词模板不存在
        """
        # 1. 获取模板方法
        if not hasattr(self.templates, template_name):
            raise ValueError(f"提示词模板 {template_name} 不存在")
        
        template_method = getattr(self.templates, template_name)
        system_template = template_method()
        
        # 2. 格式化系统提示词(如果需要)
        system_content = system_template["content"]
        if format_args:
            system_content = system_content.format(**format_args)
        
        system_message = {
            "role": system_template["role"],
            "content": system_content
        }
        
        # 构建用户消息
        user_message = {
            "role": "user",
            "content": prompt
        }
        
        # 构建完整消息列表
        messages = [system_message, user_message]
        
        # 3. 根据是否有图片选择请求方式
        if images is not None:
            # 使用多模态模型
            try:
                logging.info(f"使用模板 {template_name} 进行多模态请求")
                
                # 发送多模态请求 - 使用messages参数传递完整的消息结构
                response = self.llm.multimodal_chat_completion(
                    messages=messages,
                    images=images,
                    temperature=temperature
                )
                return response
                
            except Exception as e:
                logging.error(f"多模态请求失败: {str(e)}")
                # 如果多模态失败，尝试退回到文本模式(不含图片)
                logging.warning("多模态请求失败，尝试退回到纯文本模式")
        
        # 纯文本请求
        try:
            logging.info(f"使用模板 {template_name} 进行文本请求")
            
            response = self.llm.chat_completion(
                messages=messages,
                temperature=temperature
            )
            return response
            
        except Exception as e:
            logging.error(f"文本请求失败: {str(e)}")
            return f"请求失败: {str(e)}"

